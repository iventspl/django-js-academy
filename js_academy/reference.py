"""Load and search the Polish JS quick-reference library."""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from django.conf import settings

REFERENCE_PATH = Path(settings.BASE_DIR) / "js_academy" / "content" / "reference.json"


class ReferenceError(ValueError):
    pass


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9+#._]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=1)
def load_reference() -> tuple[dict, ...]:
    try:
        payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReferenceError(f"Missing JS reference file: {REFERENCE_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise ReferenceError(f"{REFERENCE_PATH.name}: invalid JSON: {exc}") from exc

    categories = payload.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ReferenceError("reference.json must contain a non-empty categories list")

    seen_categories: set[str] = set()
    seen_entries: set[str] = set()
    loaded: list[dict] = []
    for category_index, category in enumerate(categories):
        context = f"reference category #{category_index + 1}"
        if not isinstance(category, dict):
            raise ReferenceError(f"{context}: expected an object")
        for field in ("slug", "title", "intro", "entries"):
            if not category.get(field):
                raise ReferenceError(f"{context}: missing {field}")
        category_slug = str(category["slug"]).strip()
        if category_slug in seen_categories:
            raise ReferenceError(f"{context}: duplicate category {category_slug!r}")
        seen_categories.add(category_slug)
        entries = category["entries"]
        if not isinstance(entries, list) or not entries:
            raise ReferenceError(f"{context}: entries must be a non-empty list")

        for entry_index, entry in enumerate(entries):
            entry_context = f"{context} entry #{entry_index + 1}"
            if not isinstance(entry, dict):
                raise ReferenceError(f"{entry_context}: expected an object")
            for field in ("slug", "symbol", "summary", "code", "module"):
                if not entry.get(field):
                    raise ReferenceError(f"{entry_context}: missing {field}")
            slug = str(entry["slug"]).strip()
            if slug in seen_entries:
                raise ReferenceError(f"{entry_context}: duplicate entry {slug!r}")
            seen_entries.add(slug)
            aliases = entry.get("aliases", [])
            if not isinstance(aliases, list) or any(not isinstance(item, str) for item in aliases):
                raise ReferenceError(f"{entry_context}: aliases must be a list of strings")
            loaded.append(
                {
                    "slug": slug,
                    "symbol": str(entry["symbol"]).strip(),
                    "aliases": [alias.strip() for alias in aliases if alias.strip()],
                    "summary": str(entry["summary"]).strip(),
                    "code": str(entry["code"]).rstrip(),
                    "note": str(entry.get("note", "")).strip(),
                    "module": str(entry["module"]).strip(),
                    "category": str(category["title"]).strip(),
                    "category_slug": category_slug,
                    "glyph": str(category.get("glyph", "JS")).strip(),
                    "search_text": _normalize(
                        " ".join(
                            [
                                str(entry["symbol"]),
                                " ".join(aliases),
                                str(entry["summary"]),
                                str(entry["code"]),
                            ]
                        )
                    ),
                }
            )
    return tuple(loaded)


def reference_categories() -> tuple[dict, ...]:
    groups: dict[str, dict] = {}
    for entry in load_reference():
        group = groups.setdefault(
            entry["category_slug"],
            {
                "slug": entry["category_slug"],
                "title": entry["category"],
                "glyph": entry["glyph"],
                "entries": [],
            },
        )
        group["entries"].append(entry)
    return tuple(groups.values())


def reference_entry_map() -> dict[str, dict]:
    return {entry["slug"]: entry for entry in load_reference()}


def search_reference(query: str, limit: int = 40) -> list[dict]:
    query = _normalize(query)
    if len(query) < 2:
        return []
    tokens = query.split()
    hits: list[tuple[int, dict]] = []
    for entry in load_reference():
        if not all(token in entry["search_text"] for token in tokens):
            continue
        symbol = _normalize(entry["symbol"])
        aliases = [_normalize(alias) for alias in entry["aliases"]]
        score = 0
        if query == symbol or query in aliases:
            score = 150
        elif symbol.startswith(query) or any(alias.startswith(query) for alias in aliases):
            score = 100
        elif query in symbol or any(query in alias for alias in aliases):
            score = 70
        elif query in _normalize(entry["summary"]):
            score = 30
        elif query in _normalize(entry["code"]):
            score = 20
        if score:
            hits.append((score, entry))
    hits.sort(key=lambda pair: (-pair[0], pair[1]["symbol"]))
    return [entry for _, entry in hits[:limit]]


def suggest_reference_terms(query: str, limit: int = 5) -> list[str]:
    query = _normalize(query)
    if len(query) < 3:
        return []
    candidates: dict[str, str] = {}
    for entry in load_reference():
        candidates.setdefault(_normalize(entry["symbol"]), entry["symbol"])
        for alias in entry["aliases"]:
            candidates.setdefault(_normalize(alias), alias)
    return [candidates[match] for match in difflib.get_close_matches(
        query, candidates.keys(), n=limit, cutoff=0.72
    )]
