"""Session event logging for study harness.

All functions receive ``subject_root: pathlib.Path`` — no bare root paths.
"""
from __future__ import annotations

import json
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path


def log_session_event(subject_root: Path, event_type: str, payload: dict) -> None:
    """Append a structured session event to ``session_logs/<event_type>.jsonl``.

    Creates the *session_logs* directory if it does not exist (with parents).

    Parameters
    ----------
    subject_root : pathlib.Path
        Root of the study subject directory.
    event_type : str
        Logical type identifier (e.g. ``"subject_created"``, ``"draft_generated"``).
    payload : dict
        Arbitrary JSON-serializable metadata for this event.

    Returns
    -------
    None — side effect only (append to jsonl file).
    """
    log_dir = subject_root / "session_logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    entry = {
        "session_log_id": str(_uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "payload": payload,
    }

    log_file = log_dir / f"{event_type}.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


__all__ = ["log_session_event"]
