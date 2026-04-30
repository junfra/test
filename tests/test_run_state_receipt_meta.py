"""Test run_state.meta persistence for session receipts."""

import os
from pathlib import Path

import pytest

from oracle_plus.run_state import (
    RECEIPT_META_FIELDS,
    record_session_receipt,
)


def test_receip_meta_fields_tuple_exists():
    assert isinstance(RECEIPT_META_FIELDS, tuple)
    assert "receipt_status" in RECEIPT_META_FIELDS
    assert "receipt_outcome" in RECEIPT_META_FIELDS
    assert "receipt_summary" in RECEIPT_META_FIELDS
    assert "receipt_next_action" in RECEIPT_META_FIELDS


def test_record_session_receipt_persists_fields(tmp_path: Path) -> None:
    from oracle_plus.browser_mode import SessionReceipt

    slug = "test-session-1"
    receipt = SessionReceipt(
        receipt_status="complete",
        receipt_outcome="success",
        receipt_summary="reviewed plan and found no blockers",
        receipt_next_action="none",
        strict_failure_opt_in=False,
    )
    record_session_receipt(slug, receipt, base_dir=tmp_path)

    meta = (tmp_path / "runs" / f"{slug}.meta").read_text(encoding="utf-8")
    assert "receipt_status: complete" in meta
    assert "receipt_outcome: success" in meta
    assert "receipt_summary: reviewed plan and found no blockers" in meta
    assert "receipt_next_action: none" in meta
    assert "strict_failure_opt_in: False" in meta


def test_record_session_receipt_defaults_strict_false(tmp_path: Path) -> None:
    from oracle_plus.browser_mode import SessionReceipt

    slug = "test-session-2"
    receipt = SessionReceipt(
        receipt_status="incomplete",
        receipt_outcome="unknown",
        receipt_summary="missing receipt block",
        receipt_next_action="review_output_and_decide_retry_or_followup",
    )
    record_session_receipt(slug, receipt, base_dir=tmp_path)

    meta = (tmp_path / "runs" / f"{slug}.meta").read_text(encoding="utf-8")
    assert "strict_failure_opt_in: False" in meta
