"""Test the SESSION RECEIPT parser in browser_mode."""

import pytest

from oracle_plus.browser_mode import (
    OracleSessionReceiptError,
    SessionReceipt,
    parse_session_receipt,
)


def test_parse_terminal_session_receipt_fields():
    output = """Oracle analysis here.

<<<SESSION_RECEIPT
receipt_status: complete
receipt_outcome: success
receipt_summary: reviewed plan and found no blockers
receipt_next_action: none
>>>"""

    receipt = parse_session_receipt(output)

    assert receipt.receipt_status == "complete"
    assert receipt.receipt_outcome == "success"
    assert receipt.receipt_summary == "reviewed plan and found no blockers"
    assert receipt.receipt_next_action == "none"


def test_missing_receipt_defaults_warning_incomplete():
    receipt = parse_session_receipt("Oracle output without receipt.")

    assert receipt.receipt_status == "incomplete"
    assert receipt.receipt_outcome == "unknown"


def test_strict_failure_opt_in_marks_incomplete_receipt_as_strict():
    receipt = parse_session_receipt(
        "Oracle output without receipt.",
        strict_failure_opt_in=True,
    )

    assert receipt.receipt_status == "incomplete"
    assert receipt.strict_failure_opt_in is True
