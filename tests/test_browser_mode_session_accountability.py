"""Test end-to-end session accountability wiring in browser-mode."""

import os
from pathlib import Path

import pytest

from oracle_plus.browser_mode import (
    OracleSessionReceiptError,
    SessionReceipt,
    inject_session_contract,
    parse_session_receipt,
)
from oracle_plus.run_state import record_session_receipt


def test_inject_then_parse_round_trip(tmp_path: Path):
    prompt = "Review the plan."
    injected = inject_session_contract(prompt)

    # Simulate captured output with receipt from Oracle session
    simulated_output = f"""{injected}

--- USER PROMPT ---

{prompt}

<<<SESSION_RECEIPT
receipt_status: complete
receipt_outcome: success
receipt_summary: plan reviewed, no blockers found
receipt_next_action: none
>>>
"""
    receipt = parse_session_receipt(simulated_output)
    assert receipt.receipt_status == "complete"
    assert receipt.receipt_outcome == "success"


def test_strict_failure_raises_after_meta_saved(tmp_path: Path):
    slug = "test-strict-fail"
    receipt = SessionReceipt(
        receipt_status="incomplete",
        receipt_outcome="unknown",
        receipt_summary="session failed to produce output",
        receipt_next_action="retry_or_followup",
        strict_failure_opt_in=True,
    )

    # Save meta first (this should succeed)
    record_session_receipt(slug, receipt, base_dir=tmp_path)

    # Now verify strict failure raises
    with pytest.raises(OracleSessionReceiptError):
        if receipt.should_fail_strictly:
            raise OracleSessionReceiptError(f"strict session failure: {receipt.receipt_summary}")


def test_non_strict_incomplete_does_not_raise(tmp_path: Path):
    slug = "test-non-strict"
    receipt = SessionReceipt(
        receipt_status="incomplete",
        receipt_outcome="failure",
        receipt_summary="partial output received",
        receipt_next_action="review_and_retry",
        strict_failure_opt_in=False,
    )

    record_session_receipt(slug, receipt, base_dir=tmp_path)
    assert not receipt.should_fail_strictly  # should NOT raise
