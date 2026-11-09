"""Load and match a small, curated catalog of JavaScript errors."""

from __future__ import annotations

import difflib
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from django.conf import settings

ERRORS_PATH = Path(settings.BASE_DIR) / "js_academy" / "content" / "errors.json"


class JsErrorCatalogError(ValueError):
    pass


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9+#._]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


@lru_cache(maxsize=1)
def load_js_errors() -> tuple[dict, ...]:
    try:
        payload = json.loads(ERRORS_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise JsErrorCatalogError(f"Missing JS error catalog: {ERRORS_PATH}") from exc
    except json.JSONDecodeError as exc:
        raise JsErrorCatalogError(f"{ERRORS_PATH.name}: invalid JSON: {exc}") from exc

    items = payload.get("errors")
    if not isinstance(items, list) or not items:
        raise JsErrorCatalogError("errors.json must contain a non-empty errors list")

    seen: set[str] = set()
    loaded: list[dict] = []
    for index, item in enumerate(items):
        context = f"error #{index + 1}"
        if not isinstance(item, dict):
            raise JsErrorCatalogError(f"{context}: expected an object")
        for field in ("slug", "title", "category", "summary", "cause", "fix", "code"):
            if not item.get(field):
                raise JsErrorCatalogError(f"{context}: missing {field}")
        slug = str(item["slug"]).strip()
        if slug in seen:
            raise JsErrorCatalogError(f"{context}: duplicate slug {slug!r}")
        seen.add(slug)
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list) or any(not isinstance(alias, str) for alias in aliases):
            raise JsErrorCatalogError(f"{context}: aliases must be a list of strings")
        loaded.append(
            {
                "slug": slug,
                "title": str(item["title"]).strip(),
                "category": str(item["category"]).strip(),
                "aliases": [alias.strip() for alias in aliases if alias.strip()],
                "summary": str(item["summary"]).strip(),
                "cause": str(item["cause"]).strip(),
                "fix": str(item["fix"]).strip(),
                "code": str(item["code"]).rstrip(),
                "module": str(item.get("module", "")).strip(),
                "search_text": _normalize(
                    " ".join(
                        [
                            str(item["title"]),
                            " ".join(aliases),
                            str(item["summary"]),
                            str(item["cause"]),
                            str(item["fix"]),
                            str(item["code"]),
                        ]
                    )
                ),
            }
        )
    return tuple(loaded)


def error_categories() -> tuple[str, ...]:
    return tuple(dict.fromkeys(item["category"] for item in load_js_errors()))


def analyze_error(traceback_text: str, limit: int = 5) -> tuple[list[str], list[dict]]:
    """Extract likely error names and rank catalog entries against a pasted trace."""
    raw = str(traceback_text).strip()
    if not raw:
        return [], []
    query = _normalize(raw)
    terms: list[str] = []
    for match in re.finditer(r"\b([A-Z][A-Za-z]+Error)\b", raw):
        term = match.group(1)
        if term not in terms:
            terms.append(term)
    if not terms:
        first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "")
        if ":" in first_line:
            terms.append(first_line.split(":", 1)[0].strip()[:80])

    ranked: list[tuple[int, dict]] = []
    for item in load_js_errors():
        score = 0
        if _normalize(item["title"]) in query:
            score = 220
        else:
            for alias in item["aliases"]:
                alias_norm = _normalize(alias)
                if len(alias_norm) >= 5 and alias_norm in query:
                    score = max(score, 140 + min(len(alias_norm), 40))
        if not score and len(query) >= 3 and query in item["search_text"]:
            score = 60
        if score:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: -pair[0])
    return terms, [item for _, item in ranked[:limit]]


def suggest_error_terms(query: str, limit: int = 5) -> list[str]:
    query = _normalize(query)
    if len(query) < 3:
        return []
    candidates: dict[str, str] = {}
    for item in load_js_errors():
        candidates.setdefault(_normalize(item["title"]), item["title"])
        for alias in item["aliases"]:
            candidates.setdefault(_normalize(alias), alias)
    return [
        candidates[match]
        for match in difflib.get_close_matches(query, candidates.keys(), n=limit, cutoff=0.72)
    ]
