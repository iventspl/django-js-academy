"""Code-aware search across the JS Akademia content."""

from __future__ import annotations

import difflib
import html
import re
import unicodedata
from urllib.parse import quote

from django.urls import reverse

from .errors import load_js_errors
from .models import (
    JsChallenge,
    JsComponent,
    JsFact,
    JsInterviewQuestion,
    JsLesson,
    JsModule,
    JsTerm,
)
from .projects import PROJECTS
from .reference import load_reference

KIND_LABELS = {
    "module": "Moduł",
    "lesson": "Lekcja",
    "reference": "Ściągawka",
    "component": "Komponent",
    "challenge": "Wyzwanie",
    "term": "Słownik",
    "fact": "Ciekawostka",
    "interview": "Wywiad",
    "project": "Projekt",
    "error": "Błąd",
}
KIND_ORDER = tuple(KIND_LABELS)

_CODE_BLOCK = re.compile(r"<pre[^>]*>\s*<code[^>]*>(.*?)</code>\s*</pre>", re.IGNORECASE | re.DOTALL)
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value).casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9+#._]+", " ", value)
    return _SPACES.sub(" ", value).strip()


def _plain(value: str) -> str:
    value = html.unescape(_TAG.sub(" ", str(value)))
    return _SPACES.sub(" ", value).strip()


def _extract_code(value: str) -> str:
    blocks = _CODE_BLOCK.findall(str(value))
    if not blocks:
        return ""
    return "\n".join(html.unescape(_TAG.sub("", block)) for block in blocks).strip()


def _snippet(text: str, query: str, limit: int = 190) -> str:
    plain = _plain(text)
    if len(plain) <= limit:
        return plain
    for token in query.split():
        index = plain.casefold().find(token)
        if index >= 0:
            start = max(0, index - 55)
            end = min(len(plain), start + limit)
            return f"{'…' if start else ''}{plain[start:end].strip()}{'…' if end < len(plain) else ''}"
    return plain[:limit].rstrip() + "…"


def _score(query: str, title: str, aliases: tuple[str, ...], body: str, code: str) -> int:
    title_norm = _normalize(title)
    alias_norms = [_normalize(alias) for alias in aliases if alias]
    code_norm = _normalize(code)
    body_norm = _normalize(body)

    if query == title_norm:
        return 260
    if any(query == alias for alias in alias_norms):
        return 230
    if title_norm.startswith(query):
        return 190
    if any(alias.startswith(query) for alias in alias_norms):
        return 160
    if query in title_norm:
        return 130
    if any(query in alias for alias in alias_norms):
        return 110
    if _has_word(code_norm, query):
        return 150
    if query in code_norm:
        return 100
    if _has_word(body_norm, query):
        return 45
    if query in body_norm:
        return 25
    return 0


def _has_word(haystack: str, needle: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


def _add(
    results: list[dict],
    *,
    kind: str,
    title: str,
    url: str,
    body: str,
    code: str = "",
    aliases: tuple[str, ...] = (),
    meta: str = "",
    level: str = "",
) -> None:
    results.append(
        {
            "kind": kind,
            "kind_label": KIND_LABELS[kind],
            "title": title,
            "url": url,
            "body": body,
            "code": code,
            "aliases": aliases,
            "meta": meta,
            "level": level,
        }
    )


def search_js(query: str, kind: str = "", level: str = "") -> list[dict]:
    query = _normalize(query)
    if len(query) < 2:
        return []
    tokens = query.split()
    if kind and kind not in KIND_LABELS:
        kind = ""
    if level and level not in {"start", "core", "advanced"}:
        level = ""

    results: list[dict] = []

    for module in JsModule.objects.all():
        _add(
            results,
            kind="module",
            title=module.title,
            url=module.get_absolute_url(),
            body=" ".join([module.subtitle, module.description, module.project_brief]),
            aliases=(module.slug,),
            meta=f"{module.get_level_display()} · {module.lesson_count} lekcji",
            level=module.level,
        )

    for project in PROJECTS:
        _add(
            results,
            kind="project",
            title=project["title"],
            url=reverse("js_academy:project", args=[project["slug"]]),
            body=" ".join([project["subtitle"], project["summary"], *project["features"]]),
            aliases=(project["slug"],),
            meta=f"Projekt · {len(project['steps'])} kroków",
        )

    for lesson in JsLesson.objects.select_related("module"):
        code = _extract_code(lesson.body_html)
        _add(
            results,
            kind="lesson",
            title=lesson.title,
            url=lesson.get_absolute_url(),
            body=" ".join([lesson.summary, _plain(lesson.body_html)]),
            code=code,
            aliases=(lesson.slug,),
            meta=lesson.module.title,
            level=lesson.module.level,
        )

    for entry in load_reference():
        _add(
            results,
            kind="reference",
            title=entry["symbol"],
            url=f"{reverse('js_academy:reference')}#{entry['slug']}",
            body=entry["summary"],
            code=entry["code"],
            aliases=tuple(entry["aliases"]),
            meta=entry["category"],
        )

    for item in load_js_errors():
        _add(
            results,
            kind="error",
            title=item["title"],
            url=f"{reverse('js_academy:errors')}?q={quote(item['title'])}",
            body=" ".join([item["summary"], item["cause"], item["fix"]]),
            code=item["code"],
            aliases=tuple(item["aliases"]),
            meta=item["category"],
        )

    for component in JsComponent.objects.all():
        _add(
            results,
            kind="component",
            title=component.title,
            url=component.get_absolute_url(),
            body=" ".join([component.description, component.notes, " ".join(component.functions)]),
            code=component.js_code,
            aliases=(component.key,),
            meta=f"{component.category} · {component.get_difficulty_display()}",
        )

    for challenge in JsChallenge.objects.all():
        _add(
            results,
            kind="challenge",
            title=challenge.title,
            url=challenge.get_absolute_url(),
            body=" ".join([challenge.prompt, challenge.explanation]),
            code="\n".join([challenge.starter_code, challenge.solution_code]),
            aliases=(challenge.slug,),
            meta=challenge.get_difficulty_display(),
        )

    for term in JsTerm.objects.all():
        _add(
            results,
            kind="term",
            title=term.term,
            url=f"{reverse('js_academy:glossary')}?q={quote(term.term)}",
            body=term.definition,
            code=term.example,
            aliases=(term.key,),
            meta=term.category,
        )

    for fact in JsFact.objects.all():
        _add(
            results,
            kind="fact",
            title=fact.title,
            url=reverse("js_academy:facts"),
            body=fact.body,
            meta=fact.category,
        )

    for interview in JsInterviewQuestion.objects.all():
        _add(
            results,
            kind="interview",
            title=interview.question[:100],
            url=f"{reverse('js_academy:interview')}?q={quote(interview.question[:50])}",
            body=" ".join([interview.answer, interview.follow_up]),
            meta=interview.get_difficulty_display(),
        )

    scored: list[dict] = []
    for result in results:
        if kind and result["kind"] != kind:
            continue
        if level and result["level"] != level:
            continue
        searchable = " ".join(
            [result["title"], *result["aliases"], result["body"], result["code"]]
        )
        searchable_norm = _normalize(searchable)
        if not all(token in searchable_norm for token in tokens):
            continue
        score = _score(query, result["title"], result["aliases"], result["body"], result["code"])
        if not score:
            continue
        if result["code"] and _normalize(query) in _normalize(result["code"]):
            snippet = _snippet(result["code"], query)
        else:
            snippet = _snippet(result["body"], query)
        scored.append(
            {
                **result,
                "snippet": snippet,
                "score": score,
            }
        )

    scored.sort(key=lambda result: (-result["score"], KIND_ORDER.index(result["kind"]), result["title"]))
    return scored[:80]


def suggest_js_terms(query: str, limit: int = 5) -> list[str]:
    query = _normalize(query)
    if len(query) < 3:
        return []
    candidates: dict[str, str] = {}
    for module in JsModule.objects.all():
        candidates.setdefault(_normalize(module.title), module.title)
    for lesson in JsLesson.objects.all():
        candidates.setdefault(_normalize(lesson.title), lesson.title)
    for term in JsTerm.objects.all():
        candidates.setdefault(_normalize(term.term), term.term)
    for component in JsComponent.objects.all():
        candidates.setdefault(_normalize(component.title), component.title)
    for entry in load_reference():
        candidates.setdefault(_normalize(entry["symbol"]), entry["symbol"])
        for alias in entry["aliases"]:
            candidates.setdefault(_normalize(alias), alias)
    matches = difflib.get_close_matches(query, candidates.keys(), n=limit, cutoff=0.74)
    return [candidates[match] for match in matches]
