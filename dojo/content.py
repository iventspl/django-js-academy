"""Load, validate and seed the editable JSON content bundles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import DIFFICULTY_CHOICES, Choice, ContentSnapshot, Flashcard, Question, Topic

CONTENT_DIR = Path(settings.BASE_DIR) / "dojo" / "content"


class ContentError(ValueError):
    pass


def content_fingerprint() -> str:
    """Stable fingerprint of every JSON content file in the project."""
    digest = hashlib.sha256()
    for path in sorted(CONTENT_DIR.rglob("*.json")):
        digest.update(path.relative_to(CONTENT_DIR).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def stored_fingerprint() -> str | None:
    snapshot = ContentSnapshot.objects.order_by("-seeded_at").first()
    return snapshot.fingerprint if snapshot else None


def record_fingerprint() -> str:
    fingerprint = content_fingerprint()
    ContentSnapshot.objects.update_or_create(
        fingerprint=fingerprint,
        defaults={},
    )
    # Keep only the current snapshot.
    ContentSnapshot.objects.exclude(fingerprint=fingerprint).delete()
    return fingerprint



def bundle_paths() -> list[Path]:
    return sorted(CONTENT_DIR.glob("*.json"))


def load_bundles() -> list[dict]:
    bundles = []
    seen_topics: set[str] = set()
    seen_question_keys: set[str] = set()
    seen_card_keys: set[str] = set()
    for path in bundle_paths():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ContentError(f"{path.name}: invalid JSON: {exc}") from exc
        topic = data.get("topic", {})
        slug = topic.get("slug")
        if not slug:
            raise ContentError(f"{path.name}: topic.slug is required")
        if slug in seen_topics:
            raise ContentError(f"{path.name}: duplicate topic slug {slug!r}")
        seen_topics.add(slug)
        for field in ("name", "tagline", "description", "glyph", "accent"):
            if not topic.get(field):
                raise ContentError(f"{path.name}: topic.{field} is required")

        questions = data.get("questions", [])
        cards = data.get("flashcards", [])
        if not questions:
            raise ContentError(f"{path.name}: at least one question is required")
        if not cards:
            raise ContentError(f"{path.name}: at least one flashcard is required")

        for index, question in enumerate(questions):
            key = question.get("key")
            if not key:
                raise ContentError(f"{path.name}: question #{index + 1} is missing a key")
            if key in seen_question_keys:
                raise ContentError(f"{path.name}: duplicate question key {key!r}")
            seen_question_keys.add(key)
            if question.get("difficulty") not in dict(DIFFICULTY_CHOICES):
                raise ContentError(f"{path.name}: {key} has an invalid difficulty")
            if not question.get("prompt") or not question.get("explanation"):
                raise ContentError(f"{path.name}: {key} needs a prompt and explanation")
            choices = question.get("choices", [])
            if len(choices) != 4:
                raise ContentError(f"{path.name}: {key} must have exactly 4 choices")
            answer = question.get("answer")
            if not isinstance(answer, int) or not 0 <= answer < 4:
                raise ContentError(f"{path.name}: {key} has an invalid answer index")
            if len(set(choices)) != 4:
                raise ContentError(f"{path.name}: {key} has duplicate choices")

        for index, card in enumerate(cards):
            key = card.get("key")
            if not key:
                raise ContentError(f"{path.name}: flashcard #{index + 1} is missing a key")
            if key in seen_card_keys:
                raise ContentError(f"{path.name}: duplicate flashcard key {key!r}")
            seen_card_keys.add(key)
            if card.get("difficulty") not in dict(DIFFICULTY_CHOICES):
                raise ContentError(f"{path.name}: {key} has an invalid difficulty")
            if not card.get("front") or not card.get("back"):
                raise ContentError(f"{path.name}: {key} needs a front and back")
        bundles.append(data)
    if not bundles:
        raise ContentError(f"No content bundles found in {CONTENT_DIR}")
    return bundles


def validate_content() -> dict:
    bundles = load_bundles()
    questions = sum(len(bundle["questions"]) for bundle in bundles)
    cards = sum(len(bundle["flashcards"]) for bundle in bundles)
    return {"topics": len(bundles), "questions": questions, "flashcards": cards}


@transaction.atomic
def seed_content(verbosity: int = 1) -> dict:
    bundles = load_bundles()
    created_topics = 0
    created_questions = 0
    created_cards = 0
    for topic_order, bundle in enumerate(bundles):
        topic_data = bundle["topic"]
        topic, topic_created = Topic.objects.update_or_create(
            slug=topic_data["slug"],
            defaults={
                "name": topic_data["name"],
                "tagline": topic_data["tagline"],
                "description": topic_data["description"],
                "glyph": topic_data["glyph"],
                "accent": topic_data["accent"],
                "order": topic_order,
            },
        )
        created_topics += int(topic_created)

        for position, item in enumerate(bundle["questions"]):
            question, question_created = Question.objects.update_or_create(
                key=item["key"],
                defaults={
                    "topic": topic,
                    "difficulty": item["difficulty"],
                    "prompt": item["prompt"],
                    "code": item.get("code", ""),
                    "explanation": item["explanation"],
                    "explanation_code": item.get("explanation_code", ""),
                    "position": position,
                    "is_active": True,
                },
            )
            created_questions += int(question_created)
            for choice_position, text in enumerate(item["choices"]):
                Choice.objects.update_or_create(
                    question=question,
                    position=choice_position,
                    defaults={
                        "text": text,
                        "is_correct": item["answer"] == choice_position,
                    },
                )
            # Remove stale choices only if a bundle shrank.
            question.choices.filter(position__gte=len(item["choices"])).delete()

        for position, item in enumerate(bundle["flashcards"]):
            _, card_created = Flashcard.objects.update_or_create(
                key=item["key"],
                defaults={
                    "topic": topic,
                    "difficulty": item["difficulty"],
                    "front": item["front"],
                    "front_code": item.get("front_code", ""),
                    "back": item["back"],
                    "back_code": item.get("back_code", ""),
                    "hint": item.get("hint", ""),
                    "position": position,
                },
            )
            created_cards += int(card_created)

    summary = {
        "topics": len(bundles),
        "questions": sum(len(bundle["questions"]) for bundle in bundles),
        "flashcards": sum(len(bundle["flashcards"]) for bundle in bundles),
        "created_topics": created_topics,
        "created_questions": created_questions,
        "created_flashcards": created_cards,
    }
    return summary
