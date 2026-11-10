"""Load the Django interview question bank."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

INTERVIEW_PATH = Path(settings.BASE_DIR) / "dojo" / "content" / "interview.json"


class InterviewError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_interview_questions() -> tuple[dict, ...]:
    try:
        payload = json.loads(INTERVIEW_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InterviewError(f"Missing interview file: {INTERVIEW_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise InterviewError(f"{INTERVIEW_PATH.name}: invalid JSON: {exc}") from exc

    items = payload.get("questions")
    if not isinstance(items, list) or not items:
        raise InterviewError("interview.json must contain a non-empty questions list")
    seen: set[str] = set()
    loaded: list[dict] = []
    for index, item in enumerate(items):
        context = f"question #{index + 1}"
        if not isinstance(item, dict):
            raise InterviewError(f"{context}: expected an object")
        for field in ("slug", "question", "category", "difficulty", "answer"):
            if not item.get(field):
                raise InterviewError(f"{context}: missing {field}")
        slug = str(item["slug"]).strip()
        if slug in seen:
            raise InterviewError(f"{context}: duplicate slug {slug!r}")
        seen.add(slug)
        loaded.append(
            {
                "slug": slug,
                "question": str(item["question"]).strip(),
                "category": str(item["category"]).strip(),
                "difficulty": str(item["difficulty"]).strip(),
                "answer": str(item["answer"]).strip(),
                "follow_up": str(item.get("follow_up", "")).strip(),
            }
        )
    return tuple(loaded)


def interview_map() -> dict[str, dict]:
    return {item["slug"]: item for item in load_interview_questions()}
