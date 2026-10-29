"""Ładowanie i walidacja polskich treści akademii JavaScript."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import (
    DIFFICULTY_CHOICES,
    LEVEL_CHOICES,
    JsChallenge,
    JsChoice,
    JsComponent,
    JsContentSnapshot,
    JsFact,
    JsFlashcard,
    JsInterviewQuestion,
    JsLesson,
    JsModule,
    JsQuestion,
    JsTerm,
)

CONTENT_DIR = Path(settings.BASE_DIR) / "js_academy" / "content"
DEMOS_FILE = CONTENT_DIR / "demos.json"
KNOWLEDGE_FILE = CONTENT_DIR / "knowledge.json"
CHALLENGES_FILE = CONTENT_DIR / "challenges.json"
COMPONENTS_FILE = CONTENT_DIR / "components.json"


class ContentError(ValueError):
    pass


def bundle_paths() -> list[Path]:
    auxiliary = {"demos.json", "knowledge.json", "challenges.json", "components.json"}
    return [path for path in sorted(CONTENT_DIR.glob("*.json")) if path.name not in auxiliary]


def load_bundles() -> list[dict]:
    bundles = []
    seen_modules: set[str] = set()
    seen_questions: set[str] = set()
    seen_cards: set[str] = set()

    for path in bundle_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContentError(f"{path.name}: niepoprawny JSON: {exc}") from exc

        module = data.get("module", {})
        slug = module.get("slug")
        if not slug:
            raise ContentError(f"{path.name}: brak module.slug")
        if slug in seen_modules:
            raise ContentError(f"{path.name}: duplikat modułu {slug!r}")
        seen_modules.add(slug)
        for field in (
            "title",
            "subtitle",
            "description",
            "level",
            "glyph",
            "accent",
            "outcomes",
            "project_title",
            "project_brief",
            "project_steps",
        ):
            if not module.get(field):
                raise ContentError(f"{path.name}: brak module.{field}")
        if module["level"] not in dict(LEVEL_CHOICES):
            raise ContentError(f"{path.name}: nieznany poziom modułu")
        if "<script" in str(module).lower():
            raise ContentError(f"{path.name}: treść modułu nie może zawierać <script>")

        lessons = data.get("lessons", [])
        questions = data.get("questions", [])
        cards = data.get("flashcards", [])
        if len(lessons) < 3:
            raise ContentError(f"{path.name}: moduł potrzebuje min. 3 lekcji")
        if len(questions) < 6:
            raise ContentError(f"{path.name}: moduł potrzebuje min. 6 pytań")
        if len(cards) < 5:
            raise ContentError(f"{path.name}: moduł potrzebuje min. 5 fiszek")

        lesson_slugs: set[str] = set()
        for index, lesson in enumerate(lessons):
            for field in ("slug", "title", "summary", "body_html"):
                if not lesson.get(field):
                    raise ContentError(
                        f"{path.name}: lekcja #{index + 1} nie ma pola {field}"
                    )
            if lesson["slug"] in lesson_slugs:
                raise ContentError(f"{path.name}: duplikat lekcji {lesson['slug']!r}")
            lesson_slugs.add(lesson["slug"])
            if "<script" in lesson["body_html"].lower():
                raise ContentError(f"{path.name}: lekcja nie może zawierać <script>")

        for index, question in enumerate(questions):
            key = question.get("key")
            if not key:
                raise ContentError(f"{path.name}: pytanie #{index + 1} bez key")
            if key in seen_questions:
                raise ContentError(f"{path.name}: duplikat pytania {key!r}")
            seen_questions.add(key)
            if question.get("difficulty") not in dict(DIFFICULTY_CHOICES):
                raise ContentError(f"{path.name}: {key} ma zły difficulty")
            if not question.get("prompt") or not question.get("explanation"):
                raise ContentError(f"{path.name}: {key} wymaga prompt i explanation")
            choices = question.get("choices", [])
            if len(choices) != 4 or len(set(choices)) != 4:
                raise ContentError(f"{path.name}: {key} wymaga 4 unikalnych odpowiedzi")
            answer = question.get("answer")
            if not isinstance(answer, int) or not 0 <= answer < 4:
                raise ContentError(f"{path.name}: {key} ma zły answer")

        for index, card in enumerate(cards):
            key = card.get("key")
            if not key:
                raise ContentError(f"{path.name}: fiszka #{index + 1} bez key")
            if key in seen_cards:
                raise ContentError(f"{path.name}: duplikat fiszki {key!r}")
            seen_cards.add(key)
            if not card.get("front") or not card.get("back"):
                raise ContentError(f"{path.name}: {key} wymaga front i back")
        bundles.append(data)

    if len(bundles) < 1:
        raise ContentError(f"Brak treści w {CONTENT_DIR}")
    return bundles


def content_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(CONTENT_DIR.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def stored_fingerprint() -> str | None:
    row = JsContentSnapshot.objects.order_by("-seeded_at").first()
    return row.fingerprint if row else None


def record_fingerprint() -> str:
    fingerprint = content_fingerprint()
    JsContentSnapshot.objects.update_or_create(
        fingerprint=fingerprint,
        defaults={},
    )
    JsContentSnapshot.objects.exclude(fingerprint=fingerprint).delete()
    return fingerprint


def load_demos() -> list[dict]:
    if not DEMOS_FILE.exists():
        return []
    try:
        data = json.loads(DEMOS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"demos.json: niepoprawny JSON: {exc}") from exc
    demos = data.get("demos", [])
    seen = set()
    for index, demo in enumerate(demos):
        context = f"demo #{index + 1}"
        for field in ("module", "lesson", "title", "description", "html"):
            if not demo.get(field):
                raise ContentError(f"{context}: brak pola {field}")
        key = (demo["module"], demo["lesson"])
        if key in seen:
            raise ContentError(f"{context}: duplikat demo dla {key}")
        seen.add(key)
        html = demo["html"].lower()
        if "</iframe" in html or "<script src=" in html:
            raise ContentError(f"{context}: demo nie może zawierać iframe ani zewnętrznych skryptów")
    return demos


def load_knowledge() -> dict:
    if not KNOWLEDGE_FILE.exists():
        return {"facts": [], "terms": [], "interview": []}
    try:
        data = json.loads(KNOWLEDGE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"knowledge.json: niepoprawny JSON: {exc}") from exc

    seen: set[str] = set()
    facts = data.get("facts", [])
    terms = data.get("terms", [])
    interview = data.get("interview", [])
    for label, items, fields in (
        ("fact", facts, ("key", "category", "title", "body")),
        ("term", terms, ("key", "category", "term", "definition")),
        ("interview", interview, ("key", "category", "difficulty", "question", "answer")),
    ):
        for index, item in enumerate(items):
            for field in fields:
                if not item.get(field):
                    raise ContentError(f"knowledge.json: {label} #{index + 1} brak {field}")
            if item["key"] in seen:
                raise ContentError(f"knowledge.json: duplikat key {item['key']!r}")
            seen.add(item["key"])
            if label == "interview" and item["difficulty"] not in dict(DIFFICULTY_CHOICES):
                raise ContentError(f"knowledge.json: zły difficulty w {item['key']}")
    return {"facts": facts, "terms": terms, "interview": interview}


def load_challenges() -> list[dict]:
    if not CHALLENGES_FILE.exists():
        return []
    try:
        data = json.loads(CHALLENGES_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"challenges.json: niepoprawny JSON: {exc}") from exc
    challenges = data.get("challenges", [])
    seen: set[str] = set()
    for index, item in enumerate(challenges):
        for field in (
            "slug",
            "title",
            "difficulty",
            "prompt",
            "starter_code",
            "solution_code",
            "tests",
            "hints",
            "explanation",
        ):
            if not item.get(field):
                raise ContentError(f"challenges.json: wyzwanie #{index + 1} brak {field}")
        if item["slug"] in seen:
            raise ContentError(f"challenges.json: duplikat slug {item['slug']!r}")
        seen.add(item["slug"])
        if item["difficulty"] not in dict(DIFFICULTY_CHOICES):
            raise ContentError(f"challenges.json: zły difficulty w {item['slug']}")
        tests = item["tests"]
        if not isinstance(tests, list) or not tests:
            raise ContentError(f"challenges.json: {item['slug']} potrzebuje testów")
        for test in tests:
            if not test.get("name") or not isinstance(test.get("args"), list):
                raise ContentError(f"challenges.json: zły test w {item['slug']}")
    return challenges


def load_components() -> list[dict]:
    if not COMPONENTS_FILE.exists():
        return []
    try:
        data = json.loads(COMPONENTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"components.json: niepoprawny JSON: {exc}") from exc
    items = data.get("components", [])
    seen: set[str] = set()
    for index, item in enumerate(items):
        for field in (
            "key",
            "title",
            "category",
            "description",
            "functions",
            "html_code",
            "css_code",
            "js_code",
            "difficulty",
        ):
            if not item.get(field):
                raise ContentError(f"components.json: komponent #{index + 1} brak {field}")
        if item["key"] in seen:
            raise ContentError(f"components.json: duplikat key {item['key']!r}")
        seen.add(item["key"])
        if item["difficulty"] not in dict(DIFFICULTY_CHOICES):
            raise ContentError(f"components.json: zły difficulty w {item['key']}")
        if not isinstance(item["functions"], list) or not item["functions"]:
            raise ContentError(f"components.json: {item['key']} potrzebuje funkcji")
        for code in (item["html_code"], item["js_code"]):
            if "<script src=" in code.lower():
                raise ContentError(f"components.json: zewnętrzny skrypt w {item['key']}")
    return items


def validate_content() -> dict:
    bundles = load_bundles()
    demos = load_demos()
    knowledge = load_knowledge()
    challenges = load_challenges()
    components = load_components()
    return {
        "modules": len(bundles),
        "lessons": sum(len(b["lessons"]) for b in bundles),
        "questions": sum(len(b["questions"]) for b in bundles),
        "flashcards": sum(len(b["flashcards"]) for b in bundles),
        "demos": len(demos),
        "facts": len(knowledge["facts"]),
        "terms": len(knowledge["terms"]),
        "interview": len(knowledge["interview"]),
        "challenges": len(challenges),
        "components": len(components),
    }


@transaction.atomic
def seed_content() -> dict:
    bundles = load_bundles()
    demos = {(demo["module"], demo["lesson"]): demo for demo in load_demos()}
    knowledge = load_knowledge()
    challenges = load_challenges()
    components = load_components()
    demo_keys_used: set[tuple[str, str]] = set()
    created_modules = 0
    created_lessons = 0
    created_questions = 0
    created_cards = 0

    for module_order, bundle in enumerate(bundles):
        data = bundle["module"]
        module, created = JsModule.objects.update_or_create(
            slug=data["slug"],
            defaults={
                "title": data["title"],
                "subtitle": data["subtitle"],
                "description": data["description"],
                "level": data["level"],
                "glyph": data["glyph"],
                "accent": data["accent"],
                "duration_minutes": data.get("duration_minutes", 45),
                "outcomes": "\n".join(data["outcomes"]),
                "project_title": data["project_title"],
                "project_brief": data["project_brief"],
                "project_steps": "\n".join(data["project_steps"]),
                "order": module_order,
            },
        )
        created_modules += int(created)

        for position, item in enumerate(bundle["lessons"]):
            demo = demos.get((module.slug, item["slug"]))
            if demo:
                demo_keys_used.add((module.slug, item["slug"]))
            _, created = JsLesson.objects.update_or_create(
                module=module,
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "summary": item["summary"],
                    "body_html": item["body_html"],
                    "live_demo_html": demo["html"] if demo else "",
                    "demo_title": demo["title"] if demo else "",
                    "demo_description": demo["description"] if demo else "",
                    "minutes": item.get("minutes", 10),
                    "order": position,
                },
            )
            created_lessons += int(created)

        for position, item in enumerate(bundle["questions"]):
            question, created = JsQuestion.objects.update_or_create(
                key=item["key"],
                defaults={
                    "module": module,
                    "difficulty": item["difficulty"],
                    "prompt": item["prompt"],
                    "code": item.get("code", ""),
                    "explanation": item["explanation"],
                    "explanation_code": item.get("explanation_code", ""),
                    "position": position,
                },
            )
            created_questions += int(created)
            for choice_position, text in enumerate(item["choices"]):
                JsChoice.objects.update_or_create(
                    question=question,
                    position=choice_position,
                    defaults={
                        "text": text,
                        "is_correct": item["answer"] == choice_position,
                    },
                )
            question.choices.filter(position__gte=len(item["choices"])).delete()

        for position, item in enumerate(bundle["flashcards"]):
            _, created = JsFlashcard.objects.update_or_create(
                key=item["key"],
                defaults={
                    "module": module,
                    "front": item["front"],
                    "back": item["back"],
                    "front_code": item.get("front_code", ""),
                    "back_code": item.get("back_code", ""),
                    "hint": item.get("hint", ""),
                    "position": position,
                },
            )
            created_cards += int(created)

    created_components = 0
    for position, item in enumerate(components):
        _, created = JsComponent.objects.update_or_create(
            key=item["key"],
            defaults={
                "title": item["title"],
                "category": item["category"],
                "description": item["description"],
                "functions": item["functions"],
                "html_code": item["html_code"],
                "css_code": item["css_code"],
                "js_code": item["js_code"],
                "notes": item.get("notes", ""),
                "difficulty": item["difficulty"],
                "order": position,
            },
        )
        created_components += int(created)

    modules_by_slug = {module.slug: module for module in JsModule.objects.all()}
    created_facts = 0
    for position, item in enumerate(knowledge["facts"]):
        _, created = JsFact.objects.update_or_create(
            key=item["key"],
            defaults={
                "category": item["category"],
                "title": item["title"],
                "body": item["body"],
                "order": position,
            },
        )
        created_facts += int(created)

    created_terms = 0
    for position, item in enumerate(knowledge["terms"]):
        _, created = JsTerm.objects.update_or_create(
            key=item["key"],
            defaults={
                "category": item["category"],
                "term": item["term"],
                "definition": item["definition"],
                "example": item.get("example", ""),
                "order": position,
            },
        )
        created_terms += int(created)

    created_interview = 0
    for position, item in enumerate(knowledge["interview"]):
        _, created = JsInterviewQuestion.objects.update_or_create(
            key=item["key"],
            defaults={
                "category": item["category"],
                "difficulty": item["difficulty"],
                "question": item["question"],
                "answer": item["answer"],
                "follow_up": item.get("follow_up", ""),
                "order": position,
            },
        )
        created_interview += int(created)

    created_challenges = 0
    for position, item in enumerate(challenges):
        module = modules_by_slug.get(item.get("module", ""))
        _, created = JsChallenge.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "title": item["title"],
                "difficulty": item["difficulty"],
                "module": module,
                "prompt": item["prompt"],
                "starter_code": item["starter_code"],
                "solution_code": item["solution_code"],
                "tests": item["tests"],
                "hints": item["hints"],
                "explanation": item["explanation"],
                "xp": item.get("xp", 20),
                "order": position,
            },
        )
        created_challenges += int(created)

    missing = set(demos) - demo_keys_used
    if missing:
        raise ContentError(f"Demo wskazuje na nieistniejącą lekcję: {sorted(missing)[0]}")

    return {
        "modules": len(bundles),
        "lessons": sum(len(b["lessons"]) for b in bundles),
        "questions": sum(len(b["questions"]) for b in bundles),
        "flashcards": sum(len(b["flashcards"]) for b in bundles),
        "demos": len(demos),
        "facts": len(knowledge["facts"]),
        "terms": len(knowledge["terms"]),
        "interview": len(knowledge["interview"]),
        "challenges": len(challenges),
        "components": len(components),
        "created_modules": created_modules,
        "created_lessons": created_lessons,
        "created_questions": created_questions,
        "created_flashcards": created_cards,
        "created_facts": created_facts,
        "created_terms": created_terms,
        "created_interview": created_interview,
        "created_challenges": created_challenges,
        "created_components": created_components,
    }
