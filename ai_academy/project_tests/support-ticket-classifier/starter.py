"""Starter contract for the Support Ticket Classifier project."""

from __future__ import annotations


def train_baseline(texts: list[str], labels: list[str]):
    """Train a TF-IDF + linear classifier and return the fitted model."""
    raise NotImplementedError("Train the TF-IDF baseline")


def predict_with_confidence(model, texts: list[str]) -> list[tuple[str, float]]:
    """Return (label, confidence) pairs, one per text.

    Confidence is the model's probability for the selected label.
    """
    raise NotImplementedError("Return labels with confidence")


def route_low_confidence(
    predictions: list[tuple[str, float]], threshold: float = 0.6
) -> list[str]:
    """Replace predictions below the threshold with ``"human"``.

    Predictions at or above the threshold keep their label.
    """
    raise NotImplementedError("Implement uncertainty routing")
