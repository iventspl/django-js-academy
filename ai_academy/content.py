"""Load, validate and seed the AI Academy curriculum."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import (
    DIFFICULTY_CHOICES,
    STAGE_CHOICES,
    AiChoice,
    AiContentSnapshot,
    AiFlashcard,
    AiLesson,
    AiModule,
    AiProject,
    AiQuestion,
    AiTerm,
)

CONTENT_DIR = Path(settings.BASE_DIR) / "ai_academy" / "content"
PROJECTS_FILE = CONTENT_DIR / "projects.json"
GLOSSARY_FILE = CONTENT_DIR / "glossary.json"


class ContentError(ValueError):
    pass


def bundle_paths() -> list[Path]:
    return sorted(
        path
        for path in CONTENT_DIR.glob("*.json")
        if path.name not in {PROJECTS_FILE.name, GLOSSARY_FILE.name}
    )


def load_bundles() -> list[dict]:
    bundles = []
    seen_modules: set[str] = set()
    seen_questions: set[str] = set()
    seen_cards: set[str] = set()

    for path in bundle_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContentError(f"{path.name}: invalid JSON: {exc}") from exc

        module = data.get("module", {})
        slug = module.get("slug")
        if not slug:
            raise ContentError(f"{path.name}: module.slug is required")
        if slug in seen_modules:
            raise ContentError(f"{path.name}: duplicate module {slug!r}")
        seen_modules.add(slug)

        for field in (
            "title",
            "subtitle",
            "description",
            "stage",
            "difficulty",
            "glyph",
            "accent",
            "outcomes",
            "skills",
        ):
            if not module.get(field):
                raise ContentError(f"{path.name}: module.{field} is required")
        if module["stage"] not in dict(STAGE_CHOICES):
            raise ContentError(f"{path.name}: invalid stage {module['stage']!r}")
        if module["difficulty"] not in dict(DIFFICULTY_CHOICES):
            raise ContentError(f"{path.name}: invalid difficulty")
        if "<script" in str(module).lower():
            raise ContentError(f"{path.name}: module content cannot contain <script>")

        lessons = data.get("lessons", [])
        questions = data.get("questions", [])
        cards = data.get("flashcards", [])
        if len(lessons) < 3:
            raise ContentError(f"{path.name}: at least 3 lessons are required")
        if len(questions) < 5:
            raise ContentError(f"{path.name}: at least 5 questions are required")
        if len(cards) < 4:
            raise ContentError(f"{path.name}: at least 4 flashcards are required")

        lesson_slugs: set[str] = set()
        for index, lesson in enumerate(lessons):
            for field in ("slug", "title", "summary", "body_html", "takeaways", "practice"):
                if not lesson.get(field):
                    raise ContentError(
                        f"{path.name}: lesson #{index + 1} is missing {field}"
                    )
            if lesson["slug"] in lesson_slugs:
                raise ContentError(f"{path.name}: duplicate lesson {lesson['slug']!r}")
            lesson_slugs.add(lesson["slug"])
            if "<script" in lesson["body_html"].lower():
                raise ContentError(f"{path.name}: lessons cannot contain <script>")

        for index, question in enumerate(questions):
            key = question.get("key")
            if not key:
                raise ContentError(f"{path.name}: question #{index + 1} has no key")
            if key in seen_questions:
                raise ContentError(f"{path.name}: duplicate question {key!r}")
            seen_questions.add(key)
            if question.get("difficulty") not in dict(DIFFICULTY_CHOICES):
                raise ContentError(f"{path.name}: {key} has invalid difficulty")
            if not question.get("prompt") or not question.get("explanation"):
                raise ContentError(f"{path.name}: {key} needs prompt and explanation")
            choices = question.get("choices", [])
            if len(choices) != 4 or len(set(choices)) != 4:
                raise ContentError(f"{path.name}: {key} needs 4 unique choices")
            answer = question.get("answer")
            if not isinstance(answer, int) or not 0 <= answer < 4:
                raise ContentError(f"{path.name}: {key} has invalid answer")

        for index, card in enumerate(cards):
            key = card.get("key")
            if not key:
                raise ContentError(f"{path.name}: card #{index + 1} has no key")
            if key in seen_cards:
                raise ContentError(f"{path.name}: duplicate card {key!r}")
            seen_cards.add(key)
            if card.get("difficulty") not in dict(DIFFICULTY_CHOICES):
                raise ContentError(f"{path.name}: {key} has invalid difficulty")
            if not card.get("front") or not card.get("back"):
                raise ContentError(f"{path.name}: {key} needs front and back")

        bundles.append(data)

    if not bundles:
        raise ContentError(f"No content found in {CONTENT_DIR}")
    return bundles


def load_projects() -> list[dict]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"projects.json: invalid JSON: {exc}") from exc
    projects = data.get("projects", [])
    seen: set[str] = set()
    module_slugs = {bundle["module"]["slug"] for bundle in load_bundles()}
    for index, item in enumerate(projects):
        context = f"project #{index + 1}"
        for field in (
            "slug",
            "module",
            "title",
            "tagline",
            "scenario",
            "build",
            "hints",
            "solution_html",
            "difficulty",
            "skills",
            "deliverables",
            "milestones",
            "rubric",
            "stretch",
        ):
            if not item.get(field):
                raise ContentError(f"{context}: missing {field}")
        if item["slug"] in seen:
            raise ContentError(f"{context}: duplicate slug {item['slug']!r}")
        seen.add(item["slug"])
        if item["module"] not in module_slugs:
            raise ContentError(f"{context}: unknown module {item['module']!r}")
        if item["difficulty"] not in dict(DIFFICULTY_CHOICES):
            raise ContentError(f"{context}: invalid difficulty")
    return projects


def load_glossary() -> list[dict]:
    if not GLOSSARY_FILE.exists():
        return []
    try:
        data = json.loads(GLOSSARY_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentError(f"glossary.json: invalid JSON: {exc}") from exc
    terms = data.get("terms", [])
    seen: set[str] = set()
    module_slugs = {bundle["module"]["slug"] for bundle in load_bundles()}
    for index, item in enumerate(terms):
        context = f"glossary term #{index + 1}"
        for field in ("key", "term", "category", "definition"):
            if not item.get(field):
                raise ContentError(f"{context}: missing {field}")
        if item["key"] in seen:
            raise ContentError(f"{context}: duplicate key {item['key']!r}")
        seen.add(item["key"])
        if item.get("module") and item["module"] not in module_slugs:
            raise ContentError(f"{context}: unknown module {item['module']!r}")
    return terms


def content_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in sorted(CONTENT_DIR.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def stored_fingerprint() -> str | None:
    row = AiContentSnapshot.objects.order_by("-seeded_at").first()
    return row.fingerprint if row else None


def record_fingerprint() -> str:
    fingerprint = content_fingerprint()
    AiContentSnapshot.objects.update_or_create(
        fingerprint=fingerprint,
        defaults={},
    )
    AiContentSnapshot.objects.exclude(fingerprint=fingerprint).delete()
    return fingerprint


def validate_content() -> dict:
    bundles = load_bundles()
    projects = load_projects()
    terms = load_glossary()
    return {
        "modules": len(bundles),
        "lessons": sum(len(bundle["lessons"]) for bundle in bundles),
        "questions": sum(len(bundle["questions"]) for bundle in bundles),
        "flashcards": sum(len(bundle["flashcards"]) for bundle in bundles),
        "projects": len(projects),
        "terms": len(terms),
    }


@transaction.atomic
def seed_content() -> dict:
    bundles = load_bundles()
    projects = load_projects()
    terms = load_glossary()
    created_modules = 0
    created_lessons = 0
    created_questions = 0
    created_cards = 0
    created_projects = 0

    module_map: dict[str, AiModule] = {}
    for module_order, bundle in enumerate(bundles):
        data = bundle["module"]
        module, created = AiModule.objects.update_or_create(
            slug=data["slug"],
            defaults={
                "title": data["title"],
                "subtitle": data["subtitle"],
                "description": data["description"],
                "stage": data["stage"],
                "difficulty": data["difficulty"],
                "glyph": data["glyph"],
                "accent": data["accent"],
                "duration_weeks": data.get("duration_weeks", 4),
                "outcomes": "\n".join(data["outcomes"]),
                "skills": "\n".join(data["skills"]),
                "order": module_order,
            },
        )
        module_map[module.slug] = module
        created_modules += int(created)

        for position, item in enumerate(bundle["lessons"]):
            _, created = AiLesson.objects.update_or_create(
                module=module,
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "summary": item["summary"],
                    "body_html": item["body_html"],
                    "takeaways": "\n".join(item["takeaways"]),
                    "practice": item["practice"],
                    "minutes": item.get("minutes", 15),
                    "order": position,
                },
            )
            created_lessons += int(created)

        for position, item in enumerate(bundle["questions"]):
            question, created = AiQuestion.objects.update_or_create(
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
                AiChoice.objects.update_or_create(
                    question=question,
                    position=choice_position,
                    defaults={
                        "text": text,
                        "is_correct": item["answer"] == choice_position,
                    },
                )
            question.choices.filter(position__gte=len(item["choices"])).delete()

        for position, item in enumerate(bundle["flashcards"]):
            _, created = AiFlashcard.objects.update_or_create(
                key=item["key"],
                defaults={
                    "module": module,
                    "difficulty": item["difficulty"],
                    "front": item["front"],
                    "back": item["back"],
                    "front_code": item.get("front_code", ""),
                    "back_code": item.get("back_code", ""),
                    "hint": item.get("hint", ""),
                    "position": position,
                },
            )
            created_cards += int(created)

    for position, item in enumerate(projects):
        module = module_map.get(item["module"])
        _, created = AiProject.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "module": module,
                "title": item["title"],
                "tagline": item["tagline"],
                "scenario": item["scenario"],
                "build": item["build"],
                "hints": "\n".join(item["hints"]),
                "solution_html": item["solution_html"],
                "difficulty": item["difficulty"],
                "duration_hours": item.get("duration_hours", 8),
                "skills": "\n".join(item["skills"]),
                "deliverables": "\n".join(item["deliverables"]),
                "milestones": "\n".join(item["milestones"]),
                "rubric": "\n".join(item["rubric"]),
                "stretch": "\n".join(item["stretch"]),
                "portfolio_note": item.get("portfolio_note", ""),
                "order": position,
            },
        )
        created_projects += int(created)

    created_terms = 0
    for position, item in enumerate(terms):
        _, created = AiTerm.objects.update_or_create(
            key=item["key"],
            defaults={
                "term": item["term"],
                "category": item["category"],
                "definition": item["definition"],
                "example": item.get("example", ""),
                "module": module_map.get(item.get("module", "")),
                "order": position,
            },
        )
        created_terms += int(created)

    return {
        "modules": len(bundles),
        "lessons": sum(len(bundle["lessons"]) for bundle in bundles),
        "questions": sum(len(bundle["questions"]) for bundle in bundles),
        "flashcards": sum(len(bundle["flashcards"]) for bundle in bundles),
        "projects": len(projects),
        "terms": len(terms),
        "created_modules": created_modules,
        "created_lessons": created_lessons,
        "created_questions": created_questions,
        "created_cards": created_cards,
        "created_projects": created_projects,
        "created_terms": created_terms,
    }
