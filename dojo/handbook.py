"""Load and search the plain-language Django handbook.

The handbook is deliberately file-backed: every chapter is a small JSON file
under ``dojo/content/handbook``. That keeps the prose reviewable in a diff and
means a learner can extend the manual without touching the database or writing
a migration.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.urls import reverse

HANDBOOK_DIR = Path(settings.BASE_DIR) / "dojo" / "content" / "handbook"

CATEGORY_ORDER = (
    "Start here",
    "Request path",
    "Data",
    "Forms",
    "Users & admin",
    "Quality",
    "Assets & runtime",
    "API & deploy",
    "Architecture",
    "Recipes",
    "Reference",
)

LEVELS = ("Core", "Advanced", "Reference", "Recipe")

REQUIRED_CHAPTER_FIELDS = (
    "slug",
    "title",
    "category",
    "summary",
    "quick_answer",
    "sections",
    "pitfalls",
    "checklist",
    "related",
    "official",
)


class HandbookError(ValueError):
    """Raised when a handbook file is missing or malformed."""


def _clean_text(value, field: str, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HandbookError(f"{context}: {field} must be a non-empty string")
    return value.strip()


def _clean_list(value, field: str, context: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise HandbookError(f"{context}: {field} must be a list of non-empty strings")
    if not allow_empty and not value:
        raise HandbookError(f"{context}: {field} must not be empty")
    return [item.strip() for item in value]


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9+#._]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _variant_set(query: str) -> set[str]:
    """Tiny, deliberately boring stemmer for the words learners actually type."""
    variants = {query}
    if len(query) > 3 and query.endswith("s"):
        variants.add(query[:-1])
    if len(query) > 2 and not query.endswith("s"):
        variants.add(query + "s")
    if query.endswith(".py"):
        variants.add(query[:-3])
    return {variant for variant in variants if len(variant) >= 2}


def _clean_table(value, context: str) -> dict | None:
    if not value:
        return None
    if not isinstance(value, dict):
        raise HandbookError(f"{context}: table must be an object")
    head = value.get("head")
    rows = value.get("rows")
    if not isinstance(head, list) or not head or any(not isinstance(cell, str) for cell in head):
        raise HandbookError(f"{context}: table.head must be a non-empty list of strings")
    if not isinstance(rows, list) or not rows:
        raise HandbookError(f"{context}: table.rows must be a non-empty list")
    cleaned_rows = []
    for index, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != len(head):
            raise HandbookError(f"{context}: table row {index + 1} must match the head length")
        if any(not isinstance(cell, str) for cell in row):
            raise HandbookError(f"{context}: table cells must be strings")
        cleaned_rows.append([cell.strip() for cell in row])
    return {"head": [cell.strip() for cell in head], "rows": cleaned_rows}


def _plain(value: str) -> str:
    """Strip the tiny markdown subset used by chapter prose."""
    value = re.sub(r"`([^`]+)`", r"\1", str(value))
    value = re.sub(r"\*\*([^*]+)\*\*", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", value)
    value = re.sub(r"^\s*[-*]\s+", "", value, flags=re.MULTILINE)
    value = re.sub(r"^\s*\d+\.\s+", "", value, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", value).strip()


def _snippet(text: str, query: str, limit: int = 168) -> str:
    plain = _plain(text)
    if len(plain) <= limit:
        return plain
    for variant in sorted(_variant_set(query), key=len, reverse=True):
        index = plain.casefold().find(variant)
        if index >= 0:
            start = max(0, index - 54)
            end = min(len(plain), start + limit)
            prefix = "…" if start else ""
            suffix = "…" if end < len(plain) else ""
            return f"{prefix}{plain[start:end].strip()}{suffix}"
    return plain[:limit].rstrip() + "…"


@lru_cache(maxsize=1)
def load_chapters() -> tuple[dict, ...]:
    """Read, validate and cache every chapter file."""
    if not HANDBOOK_DIR.exists():
        raise HandbookError(f"Handbook directory not found: {HANDBOOK_DIR}")
    paths = sorted(HANDBOOK_DIR.glob("*.json"))
    if not paths:
        raise HandbookError("No handbook chapters found")

    chapters: list[dict] = []
    seen_slugs: set[str] = set()
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HandbookError(f"{path.name}: invalid JSON: {exc}") from exc
        items = payload.get("chapters") if isinstance(payload, dict) else None
        if not isinstance(items, list) or not items:
            raise HandbookError(f"{path.name}: expected a non-empty 'chapters' list")

        for index, item in enumerate(items):
            context = f"{path.name} chapter #{index + 1}"
            if not isinstance(item, dict):
                raise HandbookError(f"{context}: expected an object")
            for field in REQUIRED_CHAPTER_FIELDS:
                if field not in item:
                    raise HandbookError(f"{context}: missing {field}")

            slug = _clean_text(item["slug"], "slug", context)
            if slug in seen_slugs:
                raise HandbookError(f"{context}: duplicate slug {slug!r}")
            seen_slugs.add(slug)
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
                raise HandbookError(f"{context}: slug must be lowercase kebab-case")
            if slug == "search":
                raise HandbookError(f"{context}: slug 'search' is reserved for the search endpoint")

            chapter = {
                "slug": slug,
                "title": _clean_text(item["title"], "title", context),
                "subtitle": str(item.get("subtitle", "")).strip(),
                "category": _clean_text(item["category"], "category", context),
                "summary": _clean_text(item["summary"], "summary", context),
                "aliases": _clean_list(item.get("aliases", []), "aliases", context),
                "level": str(item.get("level", "Core")).strip() or "Core",
                "tags": _clean_list(item.get("tags", []), "tags", context),
                "quick_answer": _clean_text(item["quick_answer"], "quick_answer", context),
                "sections": [],
                "pitfalls": _clean_list(item["pitfalls"], "pitfalls", context, allow_empty=False),
                "checklist": _clean_list(item["checklist"], "checklist", context),
                "errors": [],
                "related": _clean_list(item["related"], "related", context),
                "official": _clean_text(item["official"], "official", context),
                "order": int(item.get("order", index)),
            }
            if chapter["category"] not in CATEGORY_ORDER:
                raise HandbookError(f"{context}: unknown category {chapter['category']!r}")
            if chapter["level"] not in LEVELS:
                raise HandbookError(f"{context}: unknown level {chapter['level']!r}")
            if not chapter["official"].startswith(
                (
                    "https://docs.djangoproject.com/",
                    "https://www.django-rest-framework.org/",
                    "https://channels.readthedocs.io/",
                    "https://docs.celeryq.dev/",
                    "https://typish.github.io/django-stubs/",
                    "https://github.com/typeddjango/django-stubs",
                    "https://htmx.org/docs/",
                    "https://www.postgresql.org/docs/",
                    "https://docs.stripe.com/",
                    "https://docs.python.org/",
                )
            ):
                raise HandbookError(f"{context}: official must point at trusted documentation")

            raw_sections = item["sections"]
            if not isinstance(raw_sections, list) or len(raw_sections) < 2:
                raise HandbookError(f"{context}: sections must contain at least two entries")
            seen_anchors: set[str] = set()
            for section_index, raw in enumerate(raw_sections):
                section_context = f"{context} section #{section_index + 1}"
                if not isinstance(raw, dict):
                    raise HandbookError(f"{section_context}: expected an object")
                anchor = _clean_text(raw.get("id"), "id", section_context)
                if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", anchor):
                    raise HandbookError(f"{section_context}: id must be kebab-case")
                if anchor in seen_anchors:
                    raise HandbookError(f"{section_context}: duplicate id {anchor!r}")
                seen_anchors.add(anchor)
                code = raw.get("code", "")
                if not isinstance(code, str):
                    raise HandbookError(f"{section_context}: code must be a string")
                reference = str(raw.get("reference", "")).strip()
                if reference and not reference.startswith("https://"):
                    raise HandbookError(f"{section_context}: reference must be an HTTPS URL")
                chapter["sections"].append(
                    {
                        "id": anchor,
                        "title": _clean_text(raw.get("title"), "title", section_context),
                        "body": _clean_text(raw.get("body"), "body", section_context),
                        "code": code.rstrip(),
                        "language": str(raw.get("language", "python")).strip() or "python",
                        "note": str(raw.get("note", "")).strip(),
                        "table": _clean_table(raw.get("table"), section_context),
                        "reference": reference,
                    }
                )

            raw_errors = item.get("errors", [])
            if raw_errors:
                if not isinstance(raw_errors, list):
                    raise HandbookError(f"{context}: errors must be a list")
                for error_index, raw in enumerate(raw_errors):
                    error_context = f"{context} error #{error_index + 1}"
                    if not isinstance(raw, dict):
                        raise HandbookError(f"{error_context}: expected an object")
                    chapter["errors"].append(
                        {
                            "error": _clean_text(raw.get("error"), "error", error_context),
                            "cause": _clean_text(raw.get("cause"), "cause", error_context),
                            "fix": _clean_text(raw.get("fix"), "fix", error_context),
                        }
                    )

            words = len(_plain(chapter["summary"]).split())
            words += len(_plain(chapter["quick_answer"]).split())
            for section in chapter["sections"]:
                words += len(_plain(section["body"]).split())
                words += len(_plain(section["note"]).split())
                if section["table"]:
                    words += sum(len(_plain(cell).split()) for row in section["table"]["rows"] for cell in row)
            chapter["read_minutes"] = max(1, round(words / 210))
            chapter["word_count"] = words
            table_text = " ".join(
                " ".join(cell for row in section["table"]["rows"] for cell in row)
                for section in chapter["sections"]
                if section["table"]
            )
            chapter["search_text"] = _normalize(
                " ".join(
                    [
                        chapter["title"],
                        chapter["subtitle"],
                        chapter["summary"],
                        chapter["quick_answer"],
                        chapter["level"],
                        " ".join(chapter["tags"]),
                        " ".join(chapter["aliases"]),
                        " ".join(section["title"] + " " + section["body"] for section in chapter["sections"]),
                        " ".join(chapter["pitfalls"]),
                        table_text,
                    ]
                )
            )
            chapter["search_title"] = _normalize(chapter["title"])
            chapter["search_aliases"] = [_normalize(alias) for alias in chapter["aliases"] if alias]
            chapters.append(chapter)

    for chapter in chapters:
        for related in chapter["related"]:
            if related not in seen_slugs:
                raise HandbookError(f"{chapter['slug']}: related chapter {related!r} does not exist")

    category_rank = {name: index for index, name in enumerate(CATEGORY_ORDER)}
    chapters.sort(key=lambda chapter: (category_rank[chapter["category"]], chapter["order"], chapter["title"]))
    for index, chapter in enumerate(chapters, start=1):
        chapter["number"] = index
    return tuple(chapters)


def chapter_map() -> dict[str, dict]:
    return {chapter["slug"]: chapter for chapter in load_chapters()}


def categories(level: str | None = None) -> tuple[dict, ...]:
    grouped: dict[str, list[dict]] = {name: [] for name in CATEGORY_ORDER}
    for chapter in load_chapters():
        if level and chapter["level"] != level:
            continue
        grouped[chapter["category"]].append(chapter)
    return tuple(
        {"name": name, "chapters": grouped[name], "count": len(grouped[name])}
        for name in CATEGORY_ORDER
        if grouped[name]
    )


def level_summary() -> tuple[dict, ...]:
    counts = {level: 0 for level in LEVELS}
    for chapter in load_chapters():
        counts[chapter["level"]] += 1
    return tuple({"name": level, "count": counts[level]} for level in LEVELS if counts[level])


def _contains_word(haystack: str, needle: str) -> bool:
    """Match a complete word, so 'form' does not match 'information'."""
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def _chapter_score(chapter: dict, query: str) -> int:
    if query == chapter["search_title"]:
        return 240
    if query in chapter["search_aliases"]:
        return 190
    if chapter["search_title"].startswith(query):
        return 130
    if query in chapter["search_title"]:
        return 95
    alias_hits = [alias for alias in chapter["search_aliases"] if query in alias]
    if alias_hits:
        return 75 if any(alias.startswith(query) for alias in alias_hits) else 55
    if _contains_word(_normalize(chapter["summary"]), query):
        return 24
    return 0


def _section_score(section: dict, query: str) -> int:
    title = _normalize(section["title"])
    if title == query:
        return 185
    if title.startswith(query):
        return 120
    if query in title:
        return 85
    body = _normalize(section["body"] + " " + section["note"])
    if _contains_word(body, query):
        return 28
    return 0


def search_handbook(query: str, limit: int = 24) -> list[dict]:
    """Return chapter and section hits, best first.

    A hit contains a chapter reference, an optional section, a snippet and a
    score. The view turns those pieces into URLs.
    """
    query = _normalize(query)
    if len(query) < 2:
        return []
    variants = _variant_set(query)
    tokens = query.split()

    hits: list[dict] = []
    for chapter in load_chapters():
        search_text = chapter["search_text"]
        if not all(token in search_text for token in tokens):
            continue

        chapter_score = _chapter_score(chapter, query)
        section_hits: list[tuple[int, dict]] = []
        for section in chapter["sections"]:
            score = 0
            for variant in variants:
                score = max(score, _section_score(section, variant))
            # Body-only mentions are useful inside the matching chapter, but
            # they should not flood results from unrelated chapters.
            if score and (score >= 85 or chapter_score):
                section_hits.append((score, section))

        if chapter_score:
            hits.append(
                {
                    "kind": "chapter",
                    "chapter": chapter,
                    "section": None,
                    "title": chapter["title"],
                    "snippet": _snippet(chapter["summary"], query),
                    "score": chapter_score + min(18, len(section_hits) * 2),
                }
            )
        for score, section in sorted(section_hits, key=lambda pair: pair[0], reverse=True)[:5]:
            hits.append(
                {
                    "kind": "section",
                    "chapter": chapter,
                    "section": section,
                    "title": section["title"],
                    "snippet": _snippet(section["body"], query),
                    "score": score,
                }
            )

    hits.sort(key=lambda hit: (-hit["score"], hit["chapter"]["number"], hit["title"]))
    return hits[:limit]


def count_matches(query: str) -> int:
    return len(search_handbook(query, limit=200))


def chapter_hits(query: str, limit: int = 6) -> list[dict]:
    """Chapter-only results for the global search page."""
    query = _normalize(query)
    if len(query) < 2:
        return []
    variants = _variant_set(query)
    ranked: list[tuple[int, dict]] = []
    for chapter in load_chapters():
        score = _chapter_score(chapter, query)
        if not score:
            for variant in variants:
                if variant != query:
                    score = max(score, _chapter_score(chapter, variant))
        if score:
            ranked.append((score, chapter))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["number"]))
    return [
        {
            "chapter": chapter,
            "title": chapter["title"],
            "snippet": _snippet(chapter["summary"], query),
            "score": score,
        }
        for score, chapter in ranked[:limit]
    ]


def chapter_url(chapter: dict, section: dict | None = None) -> str:
    url = reverse("dojo:handbook_chapter", args=[chapter["slug"]])
    if section:
        url += f"#{section['id']}"
    return url


# ---------------------------------------------------------------------------
# A deliberately tiny renderer for the handbook's prose subset.
# ---------------------------------------------------------------------------

_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_BOLD = re.compile(r"\*\*([^*\n]+)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_STASH = re.compile(r"\x00(\d+)\x00")
_BULLET = re.compile(r"^\s*[-*]\s+")
_NUMBERED = re.compile(r"^\s*\d+\.\s+")


def render_inline(value: str) -> str:
    """Escape untrusted-ish text, then re-introduce a safe inline subset."""
    codes: list[str] = []

    def stash(match: re.Match) -> str:
        codes.append(match.group(1))
        return f"\x00{len(codes) - 1}\x00"

    text = _INLINE_CODE.sub(stash, str(value))
    text = html.escape(text)
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _LINK.sub(r'<a href="\2" rel="noreferrer">\1</a>', text)

    def restore(match: re.Match) -> str:
        return f"<code>{html.escape(codes[int(match.group(1))])}</code>"

    return _STASH.sub(restore, text)


def render_prose(value: str) -> str:
    """Render paragraphs, simple lists and inline code without a dependency."""
    blocks = re.split(r"\n\s*\n", str(value).strip())
    output: list[str] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if all(_BULLET.match(line) for line in lines):
            items = "".join(f"<li>{render_inline(_BULLET.sub('', line))}</li>" for line in lines)
            output.append(f"<ul>{items}</ul>")
        elif all(_NUMBERED.match(line) for line in lines):
            items = "".join(f"<li>{render_inline(_NUMBERED.sub('', line))}</li>" for line in lines)
            output.append(f"<ol>{items}</ol>")
        else:
            output.append("<p>" + "<br>".join(render_inline(line) for line in lines) + "</p>")
    return "".join(output)


def highlight(value: str, query: str) -> str:
    """Escape text and wrap the matching words in <mark>."""
    escaped = html.escape(str(value))
    query = _normalize(query)
    if len(query) < 2:
        return escaped
    variants = sorted(_variant_set(query), key=len, reverse=True)
    pattern = re.compile("(" + "|".join(re.escape(variant) for variant in variants) + ")", re.IGNORECASE)
    return pattern.sub(r"<mark>\1</mark>", escaped)
