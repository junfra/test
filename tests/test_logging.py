"""Tests for study.logging — written BEFORE implementation (TDD fail-first)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    """A clean temporary workspace root."""
    ws = tmp_path / "workspace"
    ws.mkdir(exist_ok=True)
    return ws


# --------------------------------------------------------------------------- #
# 1. test_log_session_event_creates_file_and_entry
# --------------------------------------------------------------------------- #

class TestLogSessionEvent:
    def log_session_event(self, subject_root: Path, event_type: str, payload: dict):
        from study.logging import log_session_event as _lse
        return _lse(subject_root, event_type, payload)

    def test_log_creates_file_and_writes_entry(self, tmp_workspace: Path) -> None:
        """log_session_event creates the session_logs dir and appends a JSON line."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})

        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        assert log_file.exists(), "Log file should be created in session_logs/"

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1, f"Expected exactly 1 line, got {len(lines)}"

        entry = json.loads(lines[0])
        assert entry["event_type"] == "subject_created"
        assert entry["payload"]["topic"] == "Math"
        assert "session_log_id" in entry
        assert "timestamp" in entry

    def test_log_generates_uuid(self, tmp_workspace: Path) -> None:
        """The session_log_id is a valid UUID string."""
        import uuid as _uuid
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})

        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        entry = json.loads(log_file.read_text().strip())
        
        # Should be parseable as UUID
        parsed = _uuid.UUID(entry["session_log_id"])
        assert str(parsed) == entry["session_log_id"]

    def test_log_appends_multiple_entries(self, tmp_workspace: Path) -> None:
        """Calling log_session_event multiple times appends new lines."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})
        self.log_session_event(subject_root, "draft_generated", {"version_hash": "abc123"})

        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1, "First event only in subject_created file"

        draft_file = subject_root / "session_logs" / "draft_generated.jsonl"
        draft_lines = draft_file.read_text().strip().split("\n")
        assert len(draft_lines) == 1, "One entry in draft_generated file"


# --------------------------------------------------------------------------- #
# 2. test_log_session_event_multiple_types
# --------------------------------------------------------------------------- #

class TestLogSessionEventMultipleTypes:
    def log_session_event(self, subject_root: Path, event_type: str, payload: dict):
        from study.logging import log_session_event as _lse
        return _lse(subject_root, event_type, payload)

    def test_two_different_types_create_separate_files(self, tmp_workspace: Path) -> None:
        """Different event types result in separate .jsonl files."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})
        self.log_session_event(subject_root, "draft_generated", {"version_hash": "abc123"})

        created_file = subject_root / "session_logs" / "subject_created.jsonl"
        draft_file = subject_root / "session_logs" / "draft_generated.jsonl"
        
        assert created_file.exists()
        assert draft_file.exists()

    def test_events_are_ordered_by_timestamp(self, tmp_workspace: Path) -> None:
        """Entries within a single file are in chronological order."""
        import time
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})
        time.sleep(0.01)  # tiny delay to ensure timestamp ordering
        self.log_session_event(subject_root, "subject_created", {"topic": "Physics"})

        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        lines = [json.loads(l) for l in log_file.read_text().strip().split("\n")]
        
        assert len(lines) == 2
        # Timestamps should be monotonic (second entry >= first)
        assert lines[1]["timestamp"] >= lines[0]["timestamp"]


# --------------------------------------------------------------------------- #
# 3. test_log_session_event_with_nested_payload
# --------------------------------------------------------------------------- #

class TestLogSessionEventPayload:
    def log_session_event(self, subject_root: Path, event_type: str, payload: dict):
        from study.logging import log_session_event as _lse
        return _lse(subject_root, event_type, payload)

    def test_nested_dict_payload_preserved(self, tmp_workspace: Path) -> None:
        """Nested dictionary payloads are fully preserved in the JSON line."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        payload = {
            "version_hash": "abc123",
            "chapters": 5,
            "metadata": {"author": "study-harness", "format": "markdown"}
        }
        self.log_session_event(subject_root, "draft_generated", payload)

        log_file = subject_root / "session_logs" / "draft_generated.jsonl"
        entry = json.loads(log_file.read_text().strip())
        
        assert entry["payload"] == {
            "version_hash": "abc123",
            "chapters": 5,
            "metadata": {"author": "study-harness", "format": "markdown"}
        }

    def test_event_type_is_string_only(self, tmp_workspace: Path) -> None:
        """The event_type field is always a string."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "recall_session", {"score": 0.5})

        log_file = subject_root / "session_logs" / "recall_session.jsonl"
        entry = json.loads(log_file.read_text().strip())
        
        assert isinstance(entry["event_type"], str)
        assert entry["event_type"] == "recall_session"


# --------------------------------------------------------------------------- #
# 4. test_log_session_event_idempotent_with_different_ids
# --------------------------------------------------------------------------- #

class TestLogSessionEventIdempotency:
    def log_session_event(self, subject_root: Path, event_type: str, payload: dict):
        from study.logging import log_session_event as _lse
        return _lse(subject_root, event_type, payload)

    def test_each_call_generates_unique_uuid(self, tmp_workspace: Path) -> None:
        """Each call to log_session_event generates a unique session_log_id."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})
        
        import uuid as _uuid
        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        entry = json.loads(log_file.read_text().strip())
        _uuid.UUID(entry["session_log_id"])  # should parse without error

    def test_same_event_type_appends_not_overwrites(self, tmp_workspace: Path) -> None:
        """Logging the same event type twice results in two entries (not one)."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})
        self.log_session_event(subject_root, "subject_created", {"topic": "Physics"})

        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        lines = [json.loads(l) for l in log_file.read_text().strip().split("\n")]
        
        assert len(lines) == 2
        topics = {entry["payload"]["topic"] for entry in lines}
        assert topics == {"Math", "Physics"}


# --------------------------------------------------------------------------- #
# 5. test_log_session_event_timestamp_format
# --------------------------------------------------------------------------- #

class TestLogSessionEventTimestamp:
    def log_session_event(self, subject_root: Path, event_type: str, payload: dict):
        from study.logging import log_session_event as _lse
        return _lse(subject_root, event_type, payload)

    def test_timestamp_is_iso8601(self, tmp_workspace: Path) -> None:
        """The timestamp field is a valid ISO-8601 string."""
        from datetime import datetime
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})

        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        entry = json.loads(log_file.read_text().strip())
        
        # Should parse as ISO-8601 with timezone
        ts = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
        assert ts.tzinfo is not None, "Timestamp should include timezone info"


# --------------------------------------------------------------------------- #
# 6. test_log_session_event_creates_dir_if_missing
# --------------------------------------------------------------------------- #

class TestLogSessionEventDirCreation:
    def log_session_event(self, subject_root: Path, event_type: str, payload: dict):
        from study.logging import log_session_event as _lse
        return _lse(subject_root, event_type, payload)

    def test_creates_session_logs_directory_if_not_exists(self, tmp_workspace: Path) -> None:
        """If session_logs/ does not exist, log_session_event creates it."""
        subject_root = tmp_workspace / "subjects" / "math-101"
        subject_root.mkdir(parents=True, exist_ok=True)
        
        # Explicitly do NOT create session_logs dir
        assert not (subject_root / "session_logs").exists()

        self.log_session_event(subject_root, "subject_created", {"topic": "Math"})

        log_file = subject_root / "session_logs" / "subject_created.jsonl"
        assert log_file.exists()
