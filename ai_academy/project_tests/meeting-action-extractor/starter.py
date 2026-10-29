"""Starter contract for the Meeting Notes → Action Items project."""

from __future__ import annotations


def extract_actions(text: str) -> list[dict]:
    """Return a list of {owner, task, deadline, source} dictionaries.

    Only extract named owners when the text clearly provides one. Put other
    action-like lines in the result with owner "unassigned".
    """
    raise NotImplementedError("Implement action extraction")
