"""Subject management logic (create, list, delete, approve)."""
from __future__ import annotations

import json
from pathlib import Path

from .models import ProgressState


def _save_progress(subject_root: Path, state: ProgressState) -> None:
    """Persist ProgressState as progress_state.json in the subject directory."""
    (subject_root / "progress_state.json").write_text(state.model_dump_json(indent=2))


def create_subject(workspace_root: Path, subject_id: str, topic: str) -> Path:
    """Create a new subject directory structure and return subject_root.

    Creates::

        <workspace>/subjects/<id>/
            source_reference_data/
            session_logs/
            progress_state.json   ← initial intake state

    Returns the *subject_root* so callers can continue to write into it.
    """
    from .logging import log_session_event

    subject_root = workspace_root / "subjects" / subject_id
    subject_root.mkdir(parents=True, exist_ok=True)
    (subject_root / "source_reference_data").mkdir(exist_ok=True)
    (subject_root / "session_logs").mkdir(exist_ok=True)

    _save_progress(
        subject_root,
        ProgressState(subject_id=subject_id, topic=topic, phase="intake", approval_status=False),
    )

    # Side-effect: log the creation event
    log_session_event(subject_root, "subject_created", {"topic": topic})
    return subject_root


def list_subjects(workspace_root: Path) -> list[tuple[str, str]]:
    """Return ``[(subject_id, topic), ...]`` for all subjects in workspace.

    Subjects are returned in **sorted** order by *subject_id*.
    Only directories that contain a valid ``progress_state.json`` are listed.
    """
    subjects_dir = workspace_root / "subjects"
    if not subjects_dir.is_dir():
        return []

    results: list[tuple[str, str]] = []
    for entry in sorted(subjects_dir.iterdir()):
        ps_file = entry / "progress_state.json"
        if not ps_file.exists() or not entry.is_dir():
            continue
        try:
            data = json.loads(ps_file.read_text())
            results.append((data["subject_id"], data["topic"]))
        except (json.JSONDecodeError, KeyError):
            continue  # skip corrupt entries silently

    return results


def delete_subject(subject_root: Path) -> None:
    """Remove *subject_root* directory and all its contents."""
    if subject_root.exists():
        import shutil
        shutil.rmtree(subject_root)


def approve_draft(subject_root: Path) -> None:
    """Mark the draft as approved so recall can begin.

    Updates progress_state.json with approval_status=True and phase="draft_approved".
    The draft file (learning_draft.md) must exist for this to succeed.
    """
    from .storage import load_progress, save_progress

    if not (subject_root / "learning_draft.md").exists():
        raise FileNotFoundError(
            f"learning_draft.md not found in {subject_root}. "
            "Generate a draft first with `study subjects draft`."
        )

    state = load_progress(subject_root)
    state.approval_status = True
    state.phase = "draft_approved"
    save_progress(subject_root, state)

    # Side-effect: log the approval event
    from .logging import log_session_event
    log_session_event(subject_root, "approved", {})


def verify_exit_conditions(
    subject_id: str,
    workspace_root: Path | None = None,
    *,
    subject_root: Path | None = None,
) -> dict[str, bool]:
    """Verify all exit conditions are met for a subject.

    Loads *progress_state.json* from the subject directory and checks four
    boolean criteria that together determine whether a study session is
    considered complete (no seed drift).

    Parameters
    ----------
    subject_id : str
        Identifier of the subject to check.
    workspace_root : pathlib.Path, optional
        Workspace root path — used when *subject_root* is not provided.
    subject_root : pathlib.Path, optional
        Direct path to the subject directory (preferred over workspace + id).

    Returns
    -------
    dict[str, bool]
        A dictionary with exactly four keys:

        - ``draft_approved`` — True if approval_status is True in progress_state.json.
        - ``first_recall_complete`` — True if phase is "recall_first_pass" or
          "recall_adaptive" AND next_recursors_cursor > 0.
        - ``weakness_loop_active`` — True if len(weak_points) > 0 (**key for X3 drift fix**).
        - ``subject_state_complete`` — True if all required files exist AND session_logs/
          has at least one .jsonl log file.

    """
    # Resolve subject_root from workspace + id or direct path
    if subject_root is None:
        assert workspace_root is not None, "Either workspace_root or subject_root must be provided"
        subject_root = workspace_root / "subjects" / subject_id

    ps_file = subject_root / "progress_state.json"

    # Graceful handling when progress_state.json is missing
    if not ps_file.exists():
        return {
            "draft_approved": False,
            "first_recall_complete": False,
            "weakness_loop_active": False,
            "subject_state_complete": False,
        }

    try:
        from .storage import load_progress
        state = load_progress(subject_root)
    except Exception:
        return {
            "draft_approved": False,
            "first_recall_complete": False,
            "weakness_loop_active": False,
            "subject_state_complete": False,
        }

    # 1. draft_approved — check approval_status flag
    draft_approved = state.approval_status is True

    # 2. first_recall_complete — phase in recall states AND cursor > 0
    if state.phase in ("recall_first_pass", "recall_adaptive") and state.next_recursors_cursor > 0:
        first_recall_complete = True
    else:
        first_recall_complete = False

    # 3. weakness_loop_active — KEY FOR X3 FIX!
    # If weak_points has entries, the system can loop back for targeted retesting.
    weakness_loop_active = len(state.weak_points) > 0

    # 4. subject_state_complete — required files AND at least one log file
    draft_exists = (subject_root / "learning_draft.md").exists()
    progress_exists = ps_file.exists()  # already checked above but explicit

    # Check for .jsonl log files in session_logs/
    logs_dir = subject_root / "session_logs"
    has_log_files = False
    if logs_dir.is_dir():
        has_log_files = any(logs_dir.glob("*.jsonl"))

    subject_state_complete = draft_exists and progress_exists and has_log_files

    return {
        "draft_approved": draft_approved,
        "first_recall_complete": first_recall_complete,
        "weakness_loop_active": weakness_loop_active,
        "subject_state_complete": subject_state_complete,
    }


__all__ = ["approve_draft", "create_subject", "delete_subject", "list_subjects", "verify_exit_conditions"]
