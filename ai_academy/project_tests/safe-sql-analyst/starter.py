"""Starter contract for the Safe Text-to-SQL Analyst project."""

from __future__ import annotations


def validate_sql(sql: str) -> bool:
    """Return True only for a single read-only SELECT statement.

    Reject writes, stacked statements, comments and empty input.
    """
    raise NotImplementedError("Implement the SQL validator")


def enforce_limit(sql: str, limit: int = 100) -> str:
    """Add a LIMIT when absent; do not duplicate an existing limit."""
    raise NotImplementedError("Implement the row-limit guard")
