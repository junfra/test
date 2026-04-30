"""Test that SESSION_CONTRACT is injected into browser-mode prompts."""

from oracle_plus.browser_mode import SESSION_CONTRACT, inject_session_contract


def test_injects_fixed_session_contract_into_browser_prompt():
    prompt = "Review the attached plan."
    injected = inject_session_contract(prompt)

    assert injected.startswith("SESSION CONTRACT")
    assert SESSION_CONTRACT in injected
    assert "--- USER PROMPT ---" in injected
    assert injected.endswith(prompt)


def test_session_contract_requires_terminal_session_receipt_block():
    assert "<<<SESSION_RECEIPT" in SESSION_CONTRACT
    assert ">>>" in SESSION_CONTRACT
    assert "receipt_status" in SESSION_CONTRACT
    assert "receipt_outcome" in SESSION_CONTRACT
    assert "receipt_summary" in SESSION_CONTRACT
    assert "receipt_next_action" in SESSION_CONTRACT
