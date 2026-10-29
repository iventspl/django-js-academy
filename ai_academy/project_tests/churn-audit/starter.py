"""Starter contract for the Churn Dataset Audit project."""

from __future__ import annotations

import pandas as pd


def temporal_split(df: pd.DataFrame, date_column: str, cutoff: str):
    """Split into (train, validation) by date.

    Rows before ``cutoff`` belong to train; rows on or after it belong to
    validation. Return two DataFrames and preserve the original dtypes.
    """
    raise NotImplementedError("Implement a leakage-safe temporal split")


def audit_data(df: pd.DataFrame, target_column: str) -> dict:
    """Return a compact audit dictionary with at least:

    rows, target_rate, missing (dict column -> fraction), duplicate_rows,
    leakage_risks (list of strings).
    """
    raise NotImplementedError("Implement the dataset audit")


def classification_metrics(y_true, y_pred) -> dict:
    """Return accuracy, precision, recall and f1 as floats.

    Handle the case where a denominator is zero without crashing.
    """
    raise NotImplementedError("Implement the classification metrics")
