from starter import extract_actions


def test_named_owner_and_deadline_are_extracted():
    actions = extract_actions("Alice will send the report by Friday.")
    assert len(actions) == 1
    action = actions[0]
    assert action["owner"] == "Alice"
    assert "send the report" in action["task"]
    assert action["deadline"] == "Friday"
    assert action["source"] == "Alice will send the report by Friday."


def test_deadline_is_optional():
    actions = extract_actions("Bob to review the deck tomorrow.")
    assert len(actions) == 1
    assert actions[0]["owner"] == "Bob"
    assert "review the deck" in actions[0]["task"]
    assert actions[0]["deadline"] is None


def test_unowned_action_is_kept_separate():
    actions = extract_actions("We should improve onboarding.")
    assert len(actions) == 1
    assert actions[0]["owner"] == "unassigned"
    assert "improve onboarding" in actions[0]["task"]


def test_empty_notes_return_no_actions():
    assert extract_actions("  \n  ") == []
