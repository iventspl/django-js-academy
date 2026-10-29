"""Query and scheduling helpers shared by the views.

Keeping these in one module makes the views mostly about HTTP and templates,
and gives the progress calculations a single, testable home.
"""

from __future__ import annotations

import random
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q, Sum
from django.utils import timezone

from .models import (
    Attempt,
    AttemptQuestion,
    Flashcard,
    FlashcardReview,
    Learner,
    Question,
    StudyEvent,
    Topic,
    level_from_xp,
    percent,
    streak_for,
)

DAILY_XP_GOAL = 60
XP_PER_CORRECT = 10
XP_PER_WRONG = 2


def create_attempt(
    learner: Learner,
    *,
    topic: Topic | None,
    difficulty: str,
    length: int,
) -> Attempt:
    """Create an attempt with a stable, randomized question order."""
    questions = Question.objects.filter(is_active=True)
    if topic:
        questions = questions.filter(topic=topic)
    if difficulty:
        questions = questions.filter(difficulty=difficulty)

    ids = list(questions.values_list("id", flat=True))
    if len(ids) < length:
        raise ValueError(f"Requested {length} questions but only {len(ids)} are available.")
    selected_ids = random.sample(ids, length)

    with transaction.atomic():
        attempt = Attempt.objects.create(
            learner=learner,
            topic=topic,
            difficulty=difficulty,
            length=length,
        )
        AttemptQuestion.objects.bulk_create(
            [
                AttemptQuestion(attempt=attempt, question_id=question_id, position=index)
                for index, question_id in enumerate(selected_ids)
            ]
        )
    return attempt


def create_attempt_from_questions(
    learner: Learner,
    question_ids: list[int],
    *,
    topic: Topic | None = None,
    difficulty: str = "",
    limit: int | None = None,
) -> Attempt:
    """Create a run from an explicit set of questions, preserving order diversity."""
    ids = list(dict.fromkeys(int(question_id) for question_id in question_ids))
    if not ids:
        raise ValueError("There are no questions to practise yet.")
    random.shuffle(ids)
    if limit is not None:
        ids = ids[:limit]
    with transaction.atomic():
        attempt = Attempt.objects.create(
            learner=learner,
            topic=topic,
            difficulty=difficulty,
            length=len(ids),
        )
        AttemptQuestion.objects.bulk_create(
            [
                AttemptQuestion(attempt=attempt, question_id=question_id, position=index)
                for index, question_id in enumerate(ids)
            ]
        )
    return attempt


def create_retry_attempt(learner: Learner, attempt: Attempt) -> Attempt:
    """Create a new run containing only the questions missed in a finished run."""
    missed_ids = list(
        attempt.attempt_questions.filter(
            selected__isnull=False,
            is_correct=False,
        ).values_list("question_id", flat=True)
    )
    if not missed_ids:
        raise ValueError("This run has no missed questions to retry.")
    return create_attempt_from_questions(
        learner,
        missed_ids,
        topic=attempt.topic,
        difficulty=attempt.difficulty,
    )


def _weak_spot_ids(learner: Learner) -> list[int]:
    """Question ids the learner has answered but never answered correctly."""
    rows = (
        AttemptQuestion.objects.filter(
            attempt__learner=learner,
            selected__isnull=False,
            question__is_active=True,
        )
        .values("question_id")
        .annotate(
            attempts=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
            last_answered=Max("answered_at"),
        )
        .filter(correct=0)
        .order_by("last_answered", "question_id")
    )
    return [row["question_id"] for row in rows]


def weak_spots(learner: Learner, limit: int | None = None) -> list[Question]:
    """Questions with an attempt but no correct answer on record."""
    ids = _weak_spot_ids(learner)
    if limit is not None:
        ids = ids[:limit]
    if not ids:
        return []
    questions = {
        question.pk: question
        for question in Question.objects.filter(pk__in=ids).select_related("topic")
    }
    return [questions[question_id] for question_id in ids if question_id in questions]


def weak_spot_count(learner: Learner) -> int:
    return len(_weak_spot_ids(learner))


def create_weak_spot_attempt(learner: Learner, limit: int = 10) -> Attempt:
    questions = weak_spots(learner, limit=limit)
    if not questions:
        raise ValueError(
            "No open weak spots: every answered question has a correct answer on record."
        )
    return create_attempt_from_questions(
        learner,
        [question.pk for question in questions],
    )


def record_answer(attempt_question: AttemptQuestion, choice) -> bool:
    """Record an answer exactly once and award XP. Returns correctness."""
    if attempt_question.selected_id is not None:
        return bool(attempt_question.is_correct)
    if choice.question_id != attempt_question.question_id:
        raise ValueError("That choice does not belong to this question.")

    correct = choice.is_correct
    with transaction.atomic():
        attempt_question.selected = choice
        attempt_question.is_correct = correct
        attempt_question.answered_at = timezone.now()
        attempt_question.save(update_fields=["selected", "is_correct", "answered_at"])

        StudyEvent.objects.create(
            learner=attempt_question.attempt.learner,
            topic=attempt_question.question.topic,
            kind="quiz",
            xp=XP_PER_CORRECT if correct else XP_PER_WRONG,
        )
    return correct


def complete_attempt(attempt: Attempt) -> int:
    """Mark an attempt finished and award a completion bonus once."""
    if attempt.completed_at:
        return attempt.bonus_xp
    with transaction.atomic():
        score = attempt.score_percent
        bonus = 25 if score == 100 else 20 if score >= 80 else 0
        attempt.completed_at = timezone.now()
        attempt.bonus_xp = bonus
        attempt.save(update_fields=["completed_at", "bonus_xp"])
        if bonus:
            StudyEvent.objects.create(
                learner=attempt.learner,
                topic=attempt.topic,
                kind="bonus",
                xp=bonus,
            )
    return bonus


def _topic_maps(learner: Learner):
    """Build per-topic counters with a handful of aggregate queries."""
    answered_rows = (
        AttemptQuestion.objects.filter(
            attempt__learner=learner, selected__isnull=False
        )
        .values("question__topic_id")
        .annotate(
            answered=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
            seen=Count("question_id", distinct=True),
            mastered=Count("question_id", distinct=True, filter=Q(is_correct=True)),
        )
    )
    attempts = {
        row["question__topic_id"]: row for row in answered_rows
    }

    cards_total = {
        row["id"]: row["total"]
        for row in Topic.objects.annotate(total=Count("flashcards")).values("id", "total")
    }
    review_rows = (
        FlashcardReview.objects.filter(learner=learner)
        .values("flashcard__topic_id")
        .annotate(
            reviewed=Count("id"),
            due=Count("id", filter=Q(due_date__lte=timezone.localdate())),
            learned=Count("id", filter=Q(repetitions__gte=2)),
        )
    )
    reviews = {row["flashcard__topic_id"]: row for row in review_rows}
    return attempts, cards_total, reviews


def topic_progress(learner: Learner) -> list[dict]:
    """Return topic cards enriched with mastery and flashcard due counts."""
    attempts, cards_total, reviews = _topic_maps(learner)
    rows = []
    for topic in Topic.objects.all():
        question_total = topic.questions.filter(is_active=True).count()
        attempt = attempts.get(topic.id, {})
        seen = attempt.get("seen", 0) or 0
        mastered = attempt.get("mastered", 0) or 0
        answered = attempt.get("answered", 0) or 0
        correct = attempt.get("correct", 0) or 0
        card_total = cards_total.get(topic.id, 0) or 0
        review = reviews.get(topic.id, {})
        reviewed_cards = review.get("reviewed", 0) or 0
        due_cards = (review.get("due", 0) or 0) + max(0, card_total - reviewed_cards)
        learned_cards = review.get("learned", 0) or 0
        rows.append(
            {
                "topic": topic,
                "question_total": question_total,
                "flashcard_total": card_total,
                "seen": seen,
                "mastered": mastered,
                "answered": answered,
                "correct": correct,
                "accuracy": percent(correct, answered),
                "mastery": percent(mastered, question_total),
                "coverage": percent(seen, question_total),
                "reviewed_cards": reviewed_cards,
                "learned_cards": learned_cards,
                "card_progress": percent(reviewed_cards, card_total),
                "due_cards": due_cards,
            }
        )
    return rows


def recent_activity(learner: Learner, days: int = 28) -> list[dict]:
    """A compact calendar series for the progress heat strip."""
    today = timezone.localdate()
    start = today - timedelta(days=days - 1)
    totals = {
        row["occurred_on"]: row["total"] or 0
        for row in learner.events.filter(occurred_on__gte=start)
        .values("occurred_on")
        .annotate(total=Sum("xp"))
    }
    series = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        xp = totals.get(day, 0)
        if xp == 0:
            intensity = 0
        elif xp < 25:
            intensity = 1
        elif xp < 60:
            intensity = 2
        elif xp < 100:
            intensity = 3
        else:
            intensity = 4
        series.append(
            {
                "date": day,
                "label": day.strftime("%b %d"),
                "weekday": day.strftime("%a"),
                "xp": xp,
                "intensity": intensity,
                "is_today": day == today,
            }
        )
    return series


def dashboard_stats(learner: Learner) -> dict:
    today = timezone.localdate()
    topics = topic_progress(learner)
    total_questions = sum(row["question_total"] for row in topics)
    seen_questions = sum(row["seen"] for row in topics)
    mastered_questions = sum(row["mastered"] for row in topics)
    total_cards = sum(row["flashcard_total"] for row in topics)
    reviewed_cards = sum(row["reviewed_cards"] for row in topics)
    due_cards = sum(row["due_cards"] for row in topics)

    answered = AttemptQuestion.objects.filter(
        attempt__learner=learner, selected__isnull=False
    ).count()
    correct = AttemptQuestion.objects.filter(
        attempt__learner=learner, is_correct=True
    ).count()
    completed_attempts = Attempt.objects.filter(
        learner=learner, completed_at__isnull=False
    ).count()
    today_xp = (
        learner.events.filter(occurred_on=today).aggregate(total=Sum("xp"))["total"] or 0
    )
    xp = learner.xp
    return {
        "topics": topics,
        "total_questions": total_questions,
        "seen_questions": seen_questions,
        "mastered_questions": mastered_questions,
        "mastery_percent": percent(mastered_questions, total_questions),
        "total_cards": total_cards,
        "reviewed_cards": reviewed_cards,
        "card_progress": percent(reviewed_cards, total_cards),
        "due_cards": due_cards,
        "answered": answered,
        "correct": correct,
        "accuracy": percent(correct, answered),
        "completed_attempts": completed_attempts,
        "weak_spot_count": weak_spot_count(learner),
        "today_xp": today_xp,
        "daily_goal": DAILY_XP_GOAL,
        "daily_percent": percent(today_xp, DAILY_XP_GOAL),
        "daily_remaining": max(0, DAILY_XP_GOAL - today_xp),
        "xp": xp,
        "level": level_from_xp(xp),
        "streak": streak_for(learner),
        "continue_attempt": Attempt.objects.filter(
            learner=learner, completed_at__isnull=True
        )
        .select_related("topic")
        .first(),
    }


def _cards_with_reviews(learner: Learner, topic: Topic | None = None):
    cards = Flashcard.objects.select_related("topic").prefetch_related(
        Prefetch(
            "reviews",
            queryset=FlashcardReview.objects.filter(learner=learner),
            to_attr="learner_reviews",
        )
    )
    if topic:
        cards = cards.filter(topic=topic)
    payload = []
    for card in cards:
        review = card.learner_reviews[0] if card.learner_reviews else None
        payload.append((card, review))
    return payload


def due_flashcards(learner: Learner, topic: Topic | None = None) -> list[dict]:
    """Cards ready for review: overdue reviews first, then unseen cards."""
    today = timezone.localdate()
    ready = []
    for card, review in _cards_with_reviews(learner, topic):
        if review is None or review.due_date <= today:
            ready.append((card, review))
    ready.sort(
        key=lambda pair: (
            0 if pair[1] else 1,
            pair[1].due_date if pair[1] else today,
            pair[0].topic.order,
            pair[0].position,
            pair[0].pk,
        )
    )
    return [{"card": card, "review": review} for card, review in ready]


def flashcard_progress(learner: Learner, topic: Topic | None = None) -> dict:
    pairs = _cards_with_reviews(learner, topic)
    today = timezone.localdate()
    reviewed = sum(1 for _, review in pairs if review is not None)
    due = sum(1 for _, review in pairs if review is None or review.due_date <= today)
    learned = sum(
        1 for _, review in pairs if review is not None and review.repetitions >= 2
    )
    future_dates = [
        review.due_date for _, review in pairs if review is not None and review.due_date > today
    ]
    next_due = min(future_dates) if future_dates else None
    return {
        "total": len(pairs),
        "reviewed": reviewed,
        "due": due,
        "learned": learned,
        "next_due": next_due,
        "percent": percent(reviewed, len(pairs)),
    }


def flashcard_overview(learner: Learner) -> list[dict]:
    topics = {row["topic"].id: row for row in topic_progress(learner)}
    decks = []
    for topic in Topic.objects.all():
        progress = flashcard_progress(learner, topic)
        row = topics[topic.id]
        decks.append(
            {
                "topic": topic,
                "total": progress["total"],
                "due": progress["due"],
                "reviewed": progress["reviewed"],
                "learned": progress["learned"],
                "percent": progress["percent"],
                "next_due": progress["next_due"],
                "quiz_mastery": row["mastery"],
            }
        )
    return decks


def flashcards_reviewed_today(learner: Learner) -> int:
    return learner.events.filter(
        kind="flashcard", occurred_on=timezone.localdate()
    ).count()


def next_flashcard(learner: Learner, topic: Topic | None = None) -> dict | None:
    queue = due_flashcards(learner, topic)
    return queue[0] if queue else None


def award_flashcard(learner: Learner, card: Flashcard, rating: str) -> FlashcardReview:
    with transaction.atomic():
        review, _ = FlashcardReview.objects.get_or_create(
            learner=learner,
            flashcard=card,
            defaults={"due_date": timezone.localdate()},
        )
        review.review(rating)
        StudyEvent.objects.create(
            learner=learner,
            topic=card.topic,
            kind="flashcard",
            xp=4,
        )
    return review


def activities(learner: Learner, days: int = 14) -> list[dict]:
    """Recent study events grouped for a readable activity feed."""
    rows = (
        learner.events.filter(occurred_on__gte=timezone.localdate() - timedelta(days=days))
        .select_related("topic")
        .order_by("-created_at")[:30]
    )
    return [
        {
            "event": event,
            "topic": event.topic,
            "kind": event.get_kind_display(),
            "xp": event.xp,
            "when": event.created_at,
        }
        for event in rows
    ]


def achievements(learner: Learner, stats: dict) -> list[dict]:
    perfect = Attempt.objects.filter(
        learner=learner, completed_at__isnull=False, bonus_xp=25
    ).exists()
    topics_touched = sum(1 for row in stats["topics"] if row["seen"] > 0)
    return [
        {
            "name": "First contact",
            "description": "Finish your first quiz.",
            "earned": stats["completed_attempts"] >= 1,
            "glyph": "01",
        },
        {
            "name": "Card sharp",
            "description": "Review 10 flashcards.",
            "earned": stats["reviewed_cards"] >= 10,
            "glyph": "10",
        },
        {
            "name": "On a roll",
            "description": "Study three days in a row.",
            "earned": stats["streak"] >= 3,
            "glyph": "3d",
        },
        {
            "name": "Flawless",
            "description": "Score 100% on a quiz.",
            "earned": perfect,
            "glyph": "100",
        },
        {
            "name": "Generalist",
            "description": "Answer a question from every topic.",
            "earned": topics_touched == len(stats["topics"]) and topics_touched > 0,
            "glyph": "all",
        },
        {
            "name": "Deep water",
            "description": "Answer 20 advanced questions.",
            "earned": AttemptQuestion.objects.filter(
                attempt__learner=learner,
                is_correct=True,
                question__difficulty="advanced",
            ).count()
            >= 20,
            "glyph": "++",
        },
    ]


def reset_progress(learner: Learner) -> None:
    with transaction.atomic():
        Attempt.objects.filter(learner=learner).delete()
        FlashcardReview.objects.filter(learner=learner).delete()
        StudyEvent.objects.filter(learner=learner).delete()
