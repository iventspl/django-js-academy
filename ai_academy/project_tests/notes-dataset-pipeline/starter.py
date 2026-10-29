"""Starter contract for the Notes-to-Dataset Pipeline project."""

from __future__ import annotations


def load_records(paths: list[str]) -> list[dict]:
    """Load JSON-array files into a single list of records.

    Each file contains a list of objects with at least ``text`` and ``label``.
    Raise a clear error for an unsupported extension or invalid JSON.
    """
    raise NotImplementedError("Implement JSON loading")


def clean_records(records: list[dict]) -> list[dict]:
    """Normalise text and labels, drop empty records, and deduplicate by text.

    Return new dictionaries; do not mutate the input records.
    """
    raise NotImplementedError("Implement cleaning and deduplication")


def split_records(
    records: list[dict], test_size: float = 0.2, seed: int = 42
) -> tuple[list[dict], list[dict]]:
    """Return a deterministic, label-stratified (train, validation) split."""
    raise NotImplementedError("Implement a reproducible split")


def summarize(records: list[dict]) -> dict:
    """Return rows, label_counts, missing_text and unique_texts."""
    raise NotImplementedError("Implement the dataset summary")
