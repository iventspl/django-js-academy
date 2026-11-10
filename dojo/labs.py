"""Load and validate the Django Labs build tasks."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

LABS_PATH = Path(settings.BASE_DIR) / "dojo" / "content" / "labs.json"


class LabError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_labs() -> tuple[dict, ...]:
    try:
        payload = json.loads(LABS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LabError(f"Missing labs file: {LABS_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise LabError(f"{LABS_PATH.name}: invalid JSON: {exc}") from exc

    items = payload.get("labs")
    if not isinstance(items, list) or not items:
        raise LabError("labs.json must contain a non-empty labs list")

    seen: set[str] = set()
    loaded: list[dict] = []
    for index, item in enumerate(items):
        context = f"lab #{index + 1}"
        if not isinstance(item, dict):
            raise LabError(f"{context}: expected an object")
        for field in (
            "slug",
            "title",
            "subtitle",
            "chapter_slug",
            "level",
            "minutes",
            "goal",
            "scenario",
            "starter_code",
            "tasks",
            "acceptance",
            "solution",
            "explain",
        ):
            if field not in item or item[field] in ("", [], None):
                raise LabError(f"{context}: missing {field}")
        slug = str(item["slug"]).strip()
        if slug in seen:
            raise LabError(f"{context}: duplicate slug {slug!r}")
        seen.add(slug)
        for list_field in ("tasks", "acceptance", "hints"):
            value = item.get(list_field, [])
            if not isinstance(value, list) or any(not isinstance(entry, str) for entry in value):
                raise LabError(f"{context}: {list_field} must be a list of strings")
        loaded.append(
            {
                "slug": slug,
                "title": str(item["title"]).strip(),
                "subtitle": str(item["subtitle"]).strip(),
                "chapter_slug": str(item["chapter_slug"]).strip(),
                "level": str(item["level"]).strip(),
                "minutes": int(item["minutes"]),
                "goal": str(item["goal"]).strip(),
                "scenario": str(item["scenario"]).strip(),
                "starter_code": str(item["starter_code"]).rstrip(),
                "language": str(item.get("language", "python")).strip() or "python",
                "tasks": [entry.strip() for entry in item["tasks"]],
                "acceptance": [entry.strip() for entry in item["acceptance"]],
                "hints": [entry.strip() for entry in item.get("hints", [])],
                "solution": str(item["solution"]).rstrip(),
                "language_solution": str(
                    item.get("language_solution", item.get("language", "python"))
                ).strip()
                or "python",
                "explain": str(item["explain"]).strip(),
            }
        )
    return tuple(loaded)


def lab_map() -> dict[str, dict]:
    return {lab["slug"]: lab for lab in load_labs()}


def lab_for_chapter(chapter_slug: str) -> dict | None:
    return next(
        (lab for lab in load_labs() if lab["chapter_slug"] == chapter_slug),
        None,
    )
