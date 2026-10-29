"""Starter contract for the Support Email Triage project."""

from __future__ import annotations


def triage(text: str) -> dict:
    """Return category, urgency, needs_human and reason.

    Categories: billing, bug, account, other.
    Urgencies: low, normal, high.
    """
    raise NotImplementedError("Implement deterministic email triage")
