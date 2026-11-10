"""Load Django Project Tracks built from the existing labs."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings

from .labs import lab_map

TRACKS_PATH = Path(settings.BASE_DIR) / "dojo" / "content" / "tracks.json"


class TrackError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_tracks() -> tuple[dict, ...]:
    try:
        payload = json.loads(TRACKS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TrackError(f"Missing tracks file: {TRACKS_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise TrackError(f"{TRACKS_PATH.name}: invalid JSON: {exc}") from exc

    items = payload.get("tracks")
    if not isinstance(items, list) or not items:
        raise TrackError("tracks.json must contain a non-empty tracks list")

    known_labs = lab_map()
    seen: set[str] = set()
    loaded: list[dict] = []
    for index, item in enumerate(items):
        context = f"track #{index + 1}"
        if not isinstance(item, dict):
            raise TrackError(f"{context}: expected an object")
        for field in (
            "slug",
            "title",
            "subtitle",
            "goal",
            "level",
            "minutes",
            "lab_slugs",
            "milestones",
            "proof",
            "explain",
        ):
            if field not in item or item[field] in ("", [], None):
                raise TrackError(f"{context}: missing {field}")
        slug = str(item["slug"]).strip()
        if slug in seen:
            raise TrackError(f"{context}: duplicate slug {slug!r}")
        seen.add(slug)
        lab_slugs = item["lab_slugs"]
        if not isinstance(lab_slugs, list) or len(lab_slugs) < 2:
            raise TrackError(f"{context}: lab_slugs must contain at least two labs")
        for lab_slug in lab_slugs:
            if lab_slug not in known_labs:
                raise TrackError(f"{context}: unknown lab {lab_slug!r}")
        milestones = item["milestones"]
        if not isinstance(milestones, list) or any(
            not isinstance(entry, str) for entry in milestones
        ):
            raise TrackError(f"{context}: milestones must be a list of strings")
        loaded.append(
            {
                "slug": slug,
                "title": str(item["title"]).strip(),
                "subtitle": str(item["subtitle"]).strip(),
                "goal": str(item["goal"]).strip(),
                "level": str(item["level"]).strip(),
                "minutes": int(item["minutes"]),
                "lab_slugs": [str(lab_slug).strip() for lab_slug in lab_slugs],
                "labs": [known_labs[lab_slug] for lab_slug in lab_slugs],
                "milestones": [entry.strip() for entry in milestones],
                "proof": str(item["proof"]).strip(),
                "explain": str(item["explain"]).strip(),
            }
        )
    return tuple(loaded)


def track_map() -> dict[str, dict]:
    return {track["slug"]: track for track in load_tracks()}
