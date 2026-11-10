"""Load the single end-to-end Django capstone brief."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

CAPSTONE_PATH = Path(settings.BASE_DIR) / "dojo" / "content" / "capstone.json"


class CapstoneError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_capstone() -> dict:
    try:
        payload = json.loads(CAPSTONE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CapstoneError(f"Missing capstone file: {CAPSTONE_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise CapstoneError(f"{CAPSTONE_PATH.name}: invalid JSON: {exc}") from exc

    item = payload.get("capstone")
    if not isinstance(item, dict):
        raise CapstoneError("capstone.json must contain a capstone object")
    for field in (
        "slug",
        "title",
        "subtitle",
        "goal",
        "level",
        "weeks",
        "stack",
        "outcomes",
        "phases",
        "defense",
        "deployment",
        "portfolio",
    ):
        if field not in item or item[field] in ("", [], None):
            raise CapstoneError(f"capstone: missing {field}")

    phases = item["phases"]
    if not isinstance(phases, list) or len(phases) < 3:
        raise CapstoneError("capstone: phases must contain at least three entries")
    seen: set[str] = set()
    clean_phases = []
    for index, phase in enumerate(phases):
        context = f"phase #{index + 1}"
        if not isinstance(phase, dict):
            raise CapstoneError(f"{context}: expected an object")
        for field in ("slug", "title", "brief", "tasks", "acceptance"):
            if field not in phase or phase[field] in ("", [], None):
                raise CapstoneError(f"{context}: missing {field}")
        slug = str(phase["slug"]).strip()
        if slug in seen:
            raise CapstoneError(f"{context}: duplicate slug {slug!r}")
        seen.add(slug)
        for list_field in ("tasks", "acceptance"):
            if not isinstance(phase[list_field], list) or any(
                not isinstance(entry, str) for entry in phase[list_field]
            ):
                raise CapstoneError(f"{context}: {list_field} must be strings")
        clean_phases.append(
            {
                "slug": slug,
                "title": str(phase["title"]).strip(),
                "brief": str(phase["brief"]).strip(),
                "tasks": [entry.strip() for entry in phase["tasks"]],
                "acceptance": [entry.strip() for entry in phase["acceptance"]],
            }
        )

    defense = item["defense"]
    if not isinstance(defense, list) or len(defense) < 4:
        raise CapstoneError("capstone: defense must contain at least four questions")
    clean_defense = []
    defense_slugs: set[str] = set()
    for index, question in enumerate(defense):
        context = f"defense #{index + 1}"
        if not isinstance(question, dict):
            raise CapstoneError(f"{context}: expected an object")
        for field in ("slug", "question", "why", "model"):
            if not question.get(field):
                raise CapstoneError(f"{context}: missing {field}")
        slug = str(question["slug"]).strip()
        if slug in defense_slugs:
            raise CapstoneError(f"{context}: duplicate slug {slug!r}")
        defense_slugs.add(slug)
        clean_defense.append(
            {
                "slug": slug,
                "question": str(question["question"]).strip(),
                "why": str(question["why"]).strip(),
                "model": str(question["model"]).strip(),
            }
        )

    return {
        "slug": str(item["slug"]).strip(),
        "title": str(item["title"]).strip(),
        "subtitle": str(item["subtitle"]).strip(),
        "goal": str(item["goal"]).strip(),
        "level": str(item["level"]).strip(),
        "weeks": int(item["weeks"]),
        "stack": [str(entry).strip() for entry in item["stack"]],
        "outcomes": [str(entry).strip() for entry in item["outcomes"]],
        "phases": clean_phases,
        "defense": clean_defense,
        "deployment": [str(entry).strip() for entry in item["deployment"]],
        "portfolio": [str(entry).strip() for entry in item["portfolio"]],
    }
