"""Starter contract for the PII Redaction Pipeline project."""

from __future__ import annotations


def redact(text: str) -> tuple[str, dict]:
    """Return (redacted_text, counts).

    Replace emails with [EMAIL], phone numbers with [PHONE] and card-like
    13–16 digit numbers with [CARD]. Do not redact ordinary short numbers.
    """
    raise NotImplementedError("Implement the redaction pipeline")
