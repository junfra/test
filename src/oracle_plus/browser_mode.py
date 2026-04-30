"""Browser-mode orchestration for Oracle-Plus."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from oracle_plus import config
from oracle_plus.host import detect_host_ip
from oracle_plus.oracle_resolver import resolve_oracle_bin, resolve_oracle_command
from oracle_plus.ports import LockBusyError, PortLock, acquire_port_lock, build_candidate_ports, probe_port
from oracle_plus.run_state import initialize_run_state, record_run_state, _sanitize_slug
from oracle_plus.subprocess_runner import run_subprocess


@dataclass
class BrowserPlan:
    url: str
    port: int | None
    passthrough: tuple[str, ...]
    remote_host: str | None = None
    remote_token: str | None = None
    session_slug: str | None = None


class BrowserModeError(RuntimeError):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


BUSY_OUTPUT_PATTERNS = (
    re.compile(r"^ERROR: busy$", re.MULTILINE),
    re.compile(r"^User error \(browser-automation\): busy$", re.MULTILINE),
)


def _extract_flag_value(needle: str, args: Iterable[str]) -> str | None:
    items = list(args)
    for index, arg in enumerate(items):
        if arg == needle and index + 1 < len(items):
            return items[index + 1]
        if arg.startswith(f"{needle}="):
            return arg.split("=", 1)[1]
    return None


def _has_flag(args: Iterable[str], needle: str) -> bool:
    return any(arg == needle for arg in args)


def _has_prefixed_flag(args: Iterable[str], needle: str) -> bool:
    return any(arg.startswith(f"{needle}=") for arg in args)


def _strip_flag_with_value(needle: str, args: Iterable[str]) -> list[str]:
    items = list(args)
    result: list[str] = []
    index = 0
    while index < len(items):
        arg = items[index]
        if arg == needle:
            index += 2
            continue
        if arg.startswith(f"{needle}="):
            index += 1
            continue
        result.append(arg)
        index += 1
    return result


def _read_prompt_file(path_value: str) -> str:
    path = Path(path_value).expanduser()
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise BrowserModeError(2, f"--prompt-file path does not exist: {path_value}") from exc
    except UnicodeDecodeError as exc:
        raise BrowserModeError(2, f"--prompt-file must be UTF-8 text: {path_value}") from exc
    except OSError as exc:
        raise BrowserModeError(2, f"unable to read --prompt-file {path_value}: {exc}") from exc


def _normalize_prompt_file_args(args: Iterable[str]) -> list[str]:
    items = list(args)
    prompt_file_value: str | None = None
    prompt_file_count = 0
    prompt_present = False

    for index, arg in enumerate(items):
        if arg in {"-p", "--prompt"} or arg.startswith("--prompt="):
            prompt_present = True
            continue
        if arg == "--prompt-file":
            prompt_file_count += 1
            if index + 1 >= len(items):
                raise BrowserModeError(2, "--prompt-file requires a file path")
            prompt_file_value = items[index + 1]
            continue
        if arg.startswith("--prompt-file="):
            prompt_file_count += 1
            prompt_file_value = arg.split("=", 1)[1]

    if prompt_file_count == 0:
        return items
    if prompt_file_count > 1:
        raise BrowserModeError(2, "--prompt-file can only be specified once")
    if prompt_present:
        raise BrowserModeError(2, "--prompt-file and -p/--prompt cannot be used together")

    prompt_text = _read_prompt_file(prompt_file_value or "")
    normalized: list[str] = []
    index = 0
    while index < len(items):
        arg = items[index]
        if arg == "--prompt-file":
            normalized.extend(["-p", prompt_text])
            index += 2
            continue
        if arg.startswith("--prompt-file="):
            normalized.extend(["-p", prompt_text])
            index += 1
            continue
        normalized.append(arg)
        index += 1
    return normalized


def is_control_command(args: Iterable[str]) -> bool:
    items = list(args)
    first = items[0] if items else ""
    if first in {"serve", "status", "session", "help", "--help", "-h", "--version", "version", "completion"}:
        return True
    if _has_flag(items, "--render") or _has_prefixed_flag(items, "--render"):
        return True
    if _has_flag(items, "--render-markdown") or _has_prefixed_flag(items, "--render-markdown"):
        return True
    return False


def uses_browser_engine(args: Iterable[str]) -> bool:
    engine = _extract_flag_value("--engine", args)
    mode = _extract_flag_value("--mode", args)
    if engine == "browser" or mode == "browser":
        return True
    if engine == "api" or mode == "api":
        return False
    return not os.environ.get("OPENAI_API_KEY")


def describe_candidate_ports(ports: Iterable[int] | None = None) -> str:
    values = list(ports if ports is not None else build_candidate_ports())
    return ",".join(map(str, values))


def _resolve_effective_remote_host(args: list[str]) -> tuple[str | None, bool, list[str]]:
    forwarded = list(args)
    auto_select_enabled = False
    explicit_remote_host = _extract_flag_value("--remote-host", forwarded)
    env_remote_host = config.get_remote_host()
    if explicit_remote_host:
        if ":" in explicit_remote_host:
            return explicit_remote_host, False, forwarded
        return explicit_remote_host, True, _strip_flag_with_value("--remote-host", forwarded)
    if env_remote_host:
        if ":" in env_remote_host:
            return env_remote_host, False, forwarded
        return env_remote_host, True, forwarded
    auto_select_enabled = True
    return None, auto_select_enabled, forwarded


def _build_output_capture_path(session_slug: str) -> Path:
    capture_dir = Path(os.environ.get("ORACLE_LOG_DIR", os.getcwd()))
    capture_dir.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(
        prefix=f"oracle_final_capture_{_sanitize_slug(session_slug)}_",
        suffix=".md",
        dir=str(capture_dir),
    )
    os.close(fd)
    return Path(path)


def _busy_output_matches(text: str) -> bool:
    return any(pattern.search(text) for pattern in BUSY_OUTPUT_PATTERNS)


def _is_busy_output_file(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    return _busy_output_matches(path.read_text(encoding="utf-8"))


def _build_forwarded_args(
    args: list[str],
    *,
    remote_host: str | None,
    remote_token: str | None,
    codex_project_url: str | None,
) -> list[str]:
    forwarded = list(args)
    if remote_host:
        if not _has_flag(forwarded, "--remote-host") and not _has_prefixed_flag(forwarded, "--remote-host"):
            forwarded = ["--remote-host", remote_host, *forwarded]
    if remote_token and not _has_flag(forwarded, "--remote-token") and not _has_prefixed_flag(forwarded, "--remote-token"):
        forwarded = ["--remote-token", remote_token, *forwarded]
    if (
        codex_project_url
        and remote_host
        and remote_host.endswith(f":{config.CODEX_PROJECT_REMOTE_PORT}")
        and not has_chatgpt_url_override(forwarded)
    ):
        forwarded = ["--chatgpt-url", codex_project_url, *forwarded]
    return forwarded


def _run_command(
    command: list[str],
    args: list[str],
    *,
    output_file: Path | None = None,
    inactivity_timeout_seconds: int | None = None,
) -> int:
    return run_subprocess(
        command,
        args,
        output_file=output_file,
        inactivity_timeout_seconds=inactivity_timeout_seconds,
    )


def get_codex_url() -> str | None:
    return os.environ.get("CODEX_PROJECT_URL") or os.environ.get(
        "ORACLE_CODEX_PROJECT_CHATGPT_URL", config.CODEX_PROJECT_CHATGPT_URL
    )


def has_chatgpt_url_override(args: Iterable[str]) -> bool:
    for arg in args:
        if arg in {"--chatgpt-url", "--browser-url"}:
            return True
        if arg.startswith("--chatgpt-url=") or arg.startswith("--browser-url="):
            return True
    return False


def is_preview_request(args: Iterable[str]) -> bool:
    for arg in args:
        if arg in {"--dry-run", "--preview", "--render", "--render-markdown"}:
            return True
        if arg.startswith("--dry-run=") or arg.startswith("--preview="):
            return True
        if arg.startswith("--render=") or arg.startswith("--render-markdown="):
            return True
    return False


def handle_write_output(_existing: str | None, _session_slug: str | None) -> tuple[Path | str | None, list[str] | None]:
    value = os.environ.get("WRITE_OUTPUT")
    if value is None:
        return None, None
    if value == "":
        return "", None
    path = Path(value).expanduser().resolve()
    return path, ["--write-output", str(path)]


def build_oracle_command(oracle_bin: str, args: list[str], *, output_file: Path | None = None) -> list[str]:
    command = [oracle_bin, *args]
    if output_file is not None:
        command.extend(["--write-output", str(output_file)])
    return command


def _has_flag(args: Iterable[str], needle: str) -> bool:
    return needle in list(args)


def should_inject_codex_project_url(remote_host: str | None, args: Iterable[str]) -> bool:
    if remote_host is None:
        return False
    if has_chatgpt_url_override(args):
        return False
    if ":" not in remote_host:
        return False
    try:
        port = int(remote_host.rsplit(":", 1)[1])
    except ValueError:
        return False
    return port == config.CODEX_PROJECT_REMOTE_PORT


def build_oracle_args(
    *,
    url: str,
    port: int | None,
    passthrough: tuple[str, ...],
    remote_host: str | None = None,
    remote_token: str | None = None,
) -> list[str]:
    args: list[str] = []
    if remote_host:
        args.extend(["--remote-host", remote_host])
    if remote_token:
        args.extend(["--remote-token", remote_token])
    if (
        get_codex_url()
        and not has_chatgpt_url_override(passthrough)
        and (
            should_inject_codex_project_url(remote_host, passthrough)
            or port == config.CODEX_PROJECT_REMOTE_PORT
        )
    ):
        args.extend(["--chatgpt-url", get_codex_url() or ""])
    if url:
        args.append(url)
    args.extend(list(passthrough))
    return args


def select_oracle_port(start_port: int | None) -> int:
    ports = build_candidate_ports(start_port)
    for port in ports:
        if port is None:
            continue
        try:
            lock = acquire_port_lock(port)
        except LockBusyError:
            continue
        lock.release()
        return port
    raise LockBusyError("all candidate ports are busy")


def _candidate_ports(start_port: int | None = None) -> list[int]:
    return build_candidate_ports(start_port)


def run_browser_mode(
    *,
    url: str,
    port: int | None,
    passthrough: tuple[str, ...],
    oracle_bin: str | list[str] | None = None,
    host_ip: str | None = None,
    remote_host: str | None = None,
    remote_token: str | None = None,
    session_slug: str | None = None,
    output_file: Path | None = None,
    capture_output_file: Path | None = None,
) -> int:
    session_slug = _sanitize_slug(session_slug or "oracle-run")
    remote_token = remote_token or config.get_remote_token()
    host_ip = host_ip or detect_host_ip()
    oracle_bin_resolved = oracle_bin or resolve_oracle_bin()
    if oracle_bin_resolved is None:
        raise RuntimeError("unable to resolve Oracle binary")
    if isinstance(oracle_bin_resolved, list):
        command = oracle_bin_resolved
    else:
        command = [oracle_bin_resolved]

    if remote_host and ":" not in remote_host:
        remote_host = f"{remote_host}:{port or config.CODEX_PROJECT_REMOTE_PORT}"

    if remote_host is None and port is not None:
        remote_host = f"{host_ip}:{port}"

    args = build_oracle_args(
        url=url,
        port=port,
        passthrough=passthrough,
        remote_host=remote_host,
        remote_token=remote_token,
    )
    if output_file is None:
        existing = _extract_flag_value("--write-output", passthrough) or os.environ.get("WRITE_OUTPUT")
        if existing:
            output_file = Path(existing).expanduser().resolve()
        elif not is_preview_request(passthrough):
            capture_dir = Path(os.environ.get("ORACLE_LOG_DIR", os.getcwd()))
            capture_dir.mkdir(parents=True, exist_ok=True)
            fd, path = tempfile.mkstemp(
                prefix=f"oracle_final_capture_{session_slug}_",
                suffix=".md",
                dir=str(capture_dir),
            )
            os.close(fd)
            output_file = Path(path)
    if output_file is not None and _extract_flag_value("--write-output", passthrough) is None:
        args = [*args, "--write-output", str(output_file)]

    if remote_host is None:
        remote_host = f"{host_ip}:{port or config.CODEX_PROJECT_REMOTE_PORT}"

    if should_inject_codex_project_url(remote_host, args):
        codex_url = get_codex_url()
        if codex_url and "--chatgpt-url" not in args and "--browser-url" not in args:
            args = [*args, "--chatgpt-url", codex_url]

    if output_file is not None:
        initialize_run_state(session_slug, host_ip, ",".join(map(str, _candidate_ports(port))), base_dir=config.cache_root)
        record_run_state(session_slug, "capture_path", str(output_file), base_dir=config.cache_root)

    return run_subprocess(
        command,
        args,
        output_file=capture_output_file or output_file,
        inactivity_timeout_seconds=config.BROWSER_INACTIVITY_TIMEOUT_SECONDS,
    )


def run_browser_with_busy_fallback(
    *,
    url: str,
    passthrough: tuple[str, ...],
    oracle_bin: str | list[str] | None = None,
    host_ip: str | None = None,
    remote_host_base: str | None = None,
    remote_token: str | None = None,
    session_slug: str | None = None,
) -> int:
    session_slug = _sanitize_slug(session_slug or "oracle-run")
    remote_token = remote_token or config.get_remote_token()
    host_ip = host_ip or detect_host_ip()
    ports = build_candidate_ports()
    if remote_host_base and ":" in remote_host_base:
        return run_browser_mode(
            url=url,
            port=int(remote_host_base.rsplit(":", 1)[1]),
            passthrough=passthrough,
            oracle_bin=oracle_bin,
            host_ip=host_ip,
            remote_host=remote_host_base,
            remote_token=remote_token,
            session_slug=session_slug,
        )

    if remote_host_base:
        host_ip = remote_host_base

    initialize_run_state(session_slug, host_ip, ",".join(map(str, ports)), base_dir=config.cache_root)
    last_error: int | None = None
    reachable = 0
    busy = 0
    reserved = 0

    for port in ports:
        remote_host = f"{host_ip}:{port}"
        if not probe_port(host_ip, port):
            record_run_state(session_slug, "fallback_reason", f"{port}=unreachable", base_dir=config.cache_root)
            continue
        reachable += 1
        try:
            lock = acquire_port_lock(port, slug=session_slug, remote_host=remote_host)
        except LockBusyError:
            reserved += 1
            record_run_state(session_slug, "fallback_reason", f"{port}=local_lock_reserved", base_dir=config.cache_root)
            continue

        record_run_state(session_slug, "selected_port", str(port), base_dir=config.cache_root)
        record_run_state(session_slug, "selected_remote_host", remote_host, base_dir=config.cache_root)
        busy_capture_file = _build_output_capture_path(f"{session_slug}-{port}-busy")
        try:
            output = run_browser_mode(
                url=url,
                port=port,
                passthrough=passthrough,
                oracle_bin=oracle_bin,
                host_ip=host_ip,
                remote_host=remote_host,
                remote_token=remote_token,
                session_slug=session_slug,
                capture_output_file=busy_capture_file,
            )
        finally:
            lock.release()

        if output == 0:
            busy_capture_file.unlink(missing_ok=True)
            record_run_state(session_slug, "status", "completed", base_dir=config.cache_root)
            return 0
        if output == 13 or _is_busy_output_file(busy_capture_file):
            busy_capture_file.unlink(missing_ok=True)
            busy += 1
            record_run_state(session_slug, "fallback_reason", f"{port}=remote_busy", base_dir=config.cache_root)
            last_error = output
            continue
        busy_capture_file.unlink(missing_ok=True)
        record_run_state(session_slug, "status", "failed", base_dir=config.cache_root)
        record_run_state(session_slug, "exit_code", str(output), base_dir=config.cache_root)
        return output

    if reachable == 0:
        record_run_state(session_slug, "status", "no_reachable_endpoint", base_dir=config.cache_root)
        raise BrowserModeError(
            10,
            f"no reachable Oracle serve endpoints found for ports {','.join(map(str, ports))}; start Windows serve or set ORACLE_REMOTE_HOST explicitly"
        )
    if reserved > 0 and busy == 0:
        record_run_state(session_slug, "status", "all_reachable_endpoints_reserved", base_dir=config.cache_root)
        raise BrowserModeError(
            11,
            f"reachable Oracle serve endpoints for ports {','.join(map(str, ports))} are already reserved by another local run"
        )
    if busy > 0:
        record_run_state(session_slug, "status", "all_reachable_endpoints_busy", base_dir=config.cache_root)
        raise BrowserModeError(
            13,
            f"reachable Oracle serve endpoints for ports {','.join(map(str, ports))} all returned busy; retry later or use a different Oracle serve pool"
        )
    if last_error is not None:
        return last_error
    record_run_state(session_slug, "status", "no_candidate_selected", base_dir=config.cache_root)
    return 12


def run_browser_cli(argv: list[str]) -> int:
    """Run the full browser/direct CLI flow from raw argv."""
    if is_control_command(argv):
        command = resolve_oracle_command()
        return _run_command(command, argv)

    argv = _normalize_prompt_file_args(argv)
    command = resolve_oracle_command()
    if not uses_browser_engine(argv):
        return _run_command(command, argv)

    session_slug = _extract_flag_value("--slug", argv) or ""
    remote_token = _extract_flag_value("--remote-token", argv) or config.get_remote_token()
    effective_remote_host, auto_select_enabled, forwarded = _resolve_effective_remote_host(argv)
    codex_url = get_codex_url()

    if auto_select_enabled:
        host_base = effective_remote_host
        if host_base is None:
            host_base = detect_host_ip()
        return run_browser_with_busy_fallback(
            url="",
            passthrough=tuple(forwarded),
            oracle_bin=command,
            host_ip=host_base,
            remote_host_base=effective_remote_host,
            remote_token=remote_token,
            session_slug=session_slug,
        )

    # Fixed host:port path
    if effective_remote_host and ":" not in effective_remote_host:
        raise RuntimeError("fixed-port execution requires host:port")

    forwarded_args = _build_forwarded_args(
        forwarded,
        remote_host=effective_remote_host,
        remote_token=remote_token if not _has_flag(argv, "--remote-token") and not _has_prefixed_flag(argv, "--remote-token") else None,
        codex_project_url=codex_url,
    )
    return _run_command(
        command,
        forwarded_args,
        inactivity_timeout_seconds=config.BROWSER_INACTIVITY_TIMEOUT_SECONDS,
    )


# ── SESSION CONTRACT (Oracle session accountability, v1) ────────────────

SESSION_CONTRACT = """\
SESSION CONTRACT

You own this Oracle session as one complete unit.

You must:
1. Treat launch, result review, retry or follow-up, and closure as one owned session.
2. Do not stop after only producing an intermediate result if the task still needs review or follow-up.
3. If the result is incomplete, blocked, or needs correction, state that clearly and identify the next action.
4. End your final response with exactly one terminal SESSION RECEIPT block.
5. The SESSION RECEIPT block must be the final non-whitespace content in the output.

Required terminal format:

<<<SESSION_RECEIPT
receipt_status: complete|incomplete
receipt_outcome: success|failure|needs_followup|blocked|unknown
receipt_summary: <one-line summary of what happened in this Oracle session>
receipt_next_action: <one-line next action, or "none">
>>>
"""


def inject_session_contract(prompt: str) -> str:
    return f"{SESSION_CONTRACT.rstrip()}\n\n--- USER PROMPT ---\n\n{prompt}"


# ── SESSION RECEIPT PARSER ──────────────────────────────────────────────

SESSION_RECEIPT_RE = re.compile(
    r"<<<SESSION_RECEIPT\s*\n(?P<body>.*?)\n>>>\s*\Z",
    re.DOTALL,
)

VALID_RECEIPT_STATUS = {"complete", "incomplete"}
VALID_RECEIPT_OUTCOME = {
    "success", "failure", "needs_followup", "blocked", "unknown"
}
RECEIPT_FIELDS = ("receipt_status", "receipt_outcome", "receipt_summary", "receipt_next_action")


@dataclass(frozen=True)
class SessionReceipt:
    receipt_status: str
    receipt_outcome: str
    receipt_summary: str
    receipt_next_action: str
    strict_failure_opt_in: bool = False
    parse_warning: str | None = None

    @property
    def should_fail_strictly(self) -> bool:
        return self.strict_failure_opt_in and self.receipt_status == "incomplete"


class OracleSessionReceiptError(RuntimeError):
    pass


def _warning_receipt(reason, *, strict_failure_opt_in=False):
    return SessionReceipt(
        receipt_status="incomplete", receipt_outcome="unknown",
        receipt_summary=f"SESSION RECEIPT warning: {reason}",
        receipt_next_action="review_output_and_decide_retry_or_followup",
        strict_failure_opt_in=strict_failure_opt_in, parse_warning=reason)


def parse_session_receipt(captured_output, *, strict_failure_opt_in=False):
    match = SESSION_RECEIPT_RE.search(captured_output or "")
    if not match:
        return _warning_receipt("missing receipt", strict_failure_opt_in=strict_failure_opt_in)
    values = {}
    for line in match.group("body").splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        if k.strip() in RECEIPT_FIELDS:
            values[k.strip()] = v.strip()
    missing = [f for f in RECEIPT_FIELDS if not values.get(f)]
    if missing:
        return _warning_receipt(f"missing fields: {', '.join(missing)}")
    return SessionReceipt(
        **{k: values[k] for k in RECEIPT_FIELDS},
        strict_failure_opt_in=strict_failure_opt_in,
    )


# ── SESSION ACCOUNTABILITY WRAPPER ──────────────────────────────────────

def run_browser_mode_session(
    prompt: str,
    *,
    url: str = "",
    port: int | None = None,
    passthrough: tuple[str, ...] = (),
    oracle_bin: str | list[str] | None = None,
    host_ip: str | None = None,
    remote_host: str | None = None,
    remote_token: str | None = None,
    session_slug: str | None = None,
    output_file: Path | None = None,
    capture_output_file: Path | None = None,
) -> int:
    """Run browser-mode with SESSION_CONTRACT injection and receipt recording."""
    injected_prompt = inject_session_contract(prompt)

    # Build args with the injected prompt
    args = build_oracle_args(
        url=url,
        port=port,
        passthrough=passthrough,
        remote_host=remote_host,
        remote_token=remote_token,
    )
    if not _has_flag(args, "--prompt") and not any(a.startswith("--prompt=") for a in args):
        # Inject prompt into args; prefer --prompt-file to avoid shell escaping issues
        import tempfile as _tf

        tmp_fd, tmp_path = _tf.mkstemp(suffix=".md", prefix=f"oracle_prompt_{session_slug}_")
        os.close(tmp_fd)
        Path(tmp_path).write_text(injected_prompt, encoding="utf-8")
        args.extend(["--prompt-file", tmp_path])

    exit_code = run_browser_mode(
        url=url,
        port=port,
        passthrough=tuple(args),
        oracle_bin=oracle_bin,
        host_ip=host_ip,
        remote_host=remote_host,
        remote_token=remote_token,
        session_slug=session_slug,
        output_file=output_file,
        capture_output_file=capture_output_file,
    )

    # Parse and persist receipt from captured output file
    if output_file is not None and output_file.exists():
        try:
            captured = output_file.read_text(encoding="utf-8")
            receipt = parse_session_receipt(captured)
            record_session_receipt(
                _sanitize_slug(session_slug or "oracle-run"),
                receipt,
                base_dir=config.cache_root,
            )
            if receipt.should_fail_strictly:
                raise OracleSessionReceiptError(
                    f"strict session failure: {receipt.receipt_summary}"
                )
        except (OSError, UnicodeDecodeError):
            pass

    return exit_code
