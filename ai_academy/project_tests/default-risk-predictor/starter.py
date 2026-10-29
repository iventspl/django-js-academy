"""Starter contract for the Default-Risk Predictor project."""

from __future__ import annotations

from sklearn.pipeline import Pipeline


def build_pipeline(numeric_features: list[str], categorical_features: list[str]) -> Pipeline:
    """Return a scikit-learn Pipeline that:

    - imputes missing numeric values and scales them,
    - imputes missing categorical values and one-hot encodes them,
    - ends with a binary classifier.

    The pipeline must accept a pandas DataFrame and predict without manual
    preprocessing outside the pipeline.
    """
    raise NotImplementedError("Build the preprocessing + classifier pipeline")


def choose_threshold(
    y_true,
    y_scores,
    cost_false_positive: float = 1.0,
    cost_false_negative: float = 5.0,
) -> float:
    """Choose the probability threshold that minimizes expected cost.

    Consider candidate thresholds from 0 to 1 (including the observed scores).
    Return a float threshold. The test uses a case where 0.5 is optimal.
    """
    raise NotImplementedError("Implement cost-sensitive threshold selection")
