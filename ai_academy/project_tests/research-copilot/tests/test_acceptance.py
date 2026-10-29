from starter import Tool, ToolRegistry, run_agent


def _registry(calls):
    registry = ToolRegistry()

    def read_notes(arguments):
        calls.append(("read_notes", arguments))
        return {"notes": "The launch is in May."}

    def save_note(arguments):
        calls.append(("save_note", arguments))
        return {"saved": True}

    registry.register(Tool("read_notes", read_notes, write=False))
    registry.register(Tool("save_note", save_note, write=True))
    return registry


def test_read_tool_executes_and_trace_is_recorded():
    calls = []
    registry = _registry(calls)
    steps = [{"tool": "read_notes", "arguments": {}}, {"final": "May"}]
    result = run_agent("When is launch?", registry, lambda state: steps.pop(0))
    assert result["answer"] == "May"
    assert result["status"] == "ok"
    assert calls == [("read_notes", {})]
    assert any(entry.get("tool") == "read_notes" for entry in result["trace"])


def test_write_tool_requires_approval():
    calls = []
    registry = _registry(calls)
    steps = [
        {"tool": "save_note", "arguments": {"text": "May"}},
        {"final": "Done"},
    ]
    result = run_agent(
        "Save the launch month", registry, lambda state: steps.pop(0), approve_write=False
    )
    assert result["status"] == "blocked"
    assert calls == []
    assert any(entry.get("status") == "approval_required" for entry in result["trace"])


def test_write_tool_executes_with_approval():
    calls = []
    registry = _registry(calls)
    steps = [
        {"tool": "save_note", "arguments": {"text": "May"}},
        {"final": "Done"},
    ]
    result = run_agent(
        "Save the launch month", registry, lambda state: steps.pop(0), approve_write=True
    )
    assert result["status"] == "ok"
    assert calls == [("save_note", {"text": "May"})]


def test_max_steps_is_enforced():
    calls = []
    registry = _registry(calls)
    planner = lambda state: {"tool": "read_notes", "arguments": {}}
    result = run_agent("Loop", registry, planner, max_steps=3)
    assert result["status"] == "max_steps"
    assert len([entry for entry in result["trace"] if entry.get("tool") == "read_notes"]) == 3
