"""Starter contract for the Study Buddy CLI project.

You may keep everything in this module or split it into packages, as long as
these public functions keep working. The tests run offline: no API key needed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuizQuestion:
    question: str
    answer: str


def generate_quiz(notes: str, count: int = 5) -> list[QuizQuestion]:
    """Turn notes into ``count`` questions using a deterministic offline fallback.

    The returned questions must have non-empty question and answer strings.
    Do not call a remote API from this function.
    """
    raise NotImplementedError("Implement the offline quiz generator")


def score_answers(questions: list[QuizQuestion], answers: list[str]) -> dict:
    """Compare user answers with the expected answers.

    Return: ``{"correct": int, "total": int, "percent": int}``.
    Missing answers count as incorrect. Comparison should ignore surrounding
    whitespace and letter case. An empty quiz must return 0 percent rather than
    dividing by zero.
    """
    raise NotImplementedError("Implement answer scoring")
