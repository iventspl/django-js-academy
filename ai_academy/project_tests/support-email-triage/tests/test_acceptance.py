from starter import triage


def test_billing_refund_is_high_and_human():
    result = triage("I was charged twice. Please refund me urgently.")
    assert result["category"] == "billing"
    assert result["urgency"] == "high"
    assert result["needs_human"] is True


def test_bug_report_is_high():
    result = triage("The production dashboard is down after the last deploy.")
    assert result["category"] == "bug"
    assert result["urgency"] == "high"


def test_account_issue_is_normal_and_not_forced_to_human():
    result = triage("I cannot log in with my email address.")
    assert result["category"] == "account"
    assert result["urgency"] == "normal"
    assert result["needs_human"] is False


def test_vague_message_routes_to_human():
    result = triage("Hello, I have a question.")
    assert result["category"] == "other"
    assert result["needs_human"] is True


def test_empty_message_is_safe():
    result = triage("   ")
    assert result["category"] == "other"
    assert result["urgency"] == "high"
    assert result["needs_human"] is True
