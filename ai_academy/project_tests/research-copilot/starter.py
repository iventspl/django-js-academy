"""Starter contract for the Research Copilot project.

The tests use a deterministic planner instead of a real LLM, so the agent loop
can be tested offline.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    fn: Callable
    write: bool = False


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def call(self, name: str, arguments: dict) -> dict:
        """Execute a tool and return a result dict."""
        raise NotImplementedError("Implement tool execution")


def run_agent(
    question: str,
    registry: ToolRegistry,
    planner,
    *,
    max_steps: int = 5,
    approve_write: bool = False,
) -> dict:
    """Run a bounded tool loop.

    ``planner(state)`` returns either:
      {"final": "answer"}
      {"tool": "name", "arguments": {...}}

    Return ``{"answer": str, "trace": list[dict], "status": "ok"|"blocked"|"max_steps"}``.
    A write tool must not execute unless ``approve_write`` is true. The trace
    must include every proposed tool call and its outcome.
    """
    raise NotImplementedError("Implement the bounded agent loop")
