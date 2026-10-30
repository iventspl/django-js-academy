"""Progress, scheduling and readiness helpers for AI Academy."""

from __future__ import annotations

from datetime import timedelta
import random

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from dojo.models import Learner

from .models import (
    AiAttempt,
    AiAttemptQuestion,
    AiFlashcard,
    AiFlashcardReview,
    AiLesson,
    AiLessonNote,
    AiLessonProgress,
    AiModule,
    AiProject,
    AiProjectCompletion,
    AiQuestion,
    percent,
)

LEVELS = [
    (0, "Explorer"),
    (200, "Builder"),
    (450, "Practitioner"),
    (800, "AI Engineer"),
    (1300, "Applied AI Engineer"),
]


def module_progress(learner: Learner, module: AiModule) -> dict:
    lessons = list(module.lessons.all())
    completed = set(
        AiLessonProgress.objects.filter(
            learner=learner, lesson__module=module
        ).values_list("lesson_id", flat=True)
    )
    next_lesson = next((lesson for lesson in lessons if lesson.id not in completed), None)
    attempts = list(
        AiAttempt.objects.filter(
            learner=learner, module=module, completed_at__isnull=False
        ).order_by("-started_at")
    )
    best_score = max((attempt.score_percent for attempt in attempts), default=0)
    reviews = AiFlashcardReview.objects.filter(
        learner=learner, flashcard__module=module
    ).count()
    return {
        "module": module,
        "lessons": lessons,
        "completed_ids": completed,
        "completed_lessons": len(completed),
        "lesson_total": len(lessons),
        "lesson_percent": percent(len(completed), len(lessons)),
        "next_lesson": next_lesson,
        "best_score": best_score,
        "attempt_count": len(attempts),
        "last_attempt": attempts[0] if attempts else None,
        "card_total": module.flashcards.count(),
        "reviewed_cards": reviews,
        "card_percent": percent(reviews, module.flashcards.count()),
        "is_complete": bool(lessons) and len(completed) == len(lessons),
    }


def next_lesson(learner: Learner) -> dict | None:
    modules = list(AiModule.objects.prefetch_related("lessons"))
    for module in modules:
        completed = set(
            AiLessonProgress.objects.filter(
                learner=learner, lesson__module=module
            ).values_list("lesson_id", flat=True)
        )
        for lesson in module.lessons.all():
            if lesson.id not in completed:
                return {"module": module, "lesson": lesson}
    if modules:
        lesson = modules[-1].lessons.order_by("-order").first()
        if lesson:
            return {"module": modules[-1], "lesson": lesson}
    return None


def project_list(learner: Learner) -> list[dict]:
    completions = {
        completion.project_id: completion
        for completion in AiProjectCompletion.objects.filter(learner=learner)
    }
    rows = []
    for project in AiProject.objects.select_related("module"):
        rows.append(
            {
                "project": project,
                "completed": project.id in completions,
                "completion": completions.get(project.id),
            }
        )
    return rows


def project_progress(learner: Learner, project: AiProject) -> dict:
    completion = AiProjectCompletion.objects.filter(
        learner=learner, project=project
    ).first()
    return {"project": project, "completed": completion is not None, "completion": completion}


def _activity_dates(learner: Learner) -> set:
    dates: set = set()
    for completed_at in AiLessonProgress.objects.filter(learner=learner).values_list(
        "completed_at", flat=True
    ):
        if completed_at:
            dates.add(timezone.localtime(completed_at).date())
    for completed_at in AiAttempt.objects.filter(
        learner=learner, completed_at__isnull=False
    ).values_list("completed_at", flat=True):
        if completed_at:
            dates.add(timezone.localtime(completed_at).date())
    for reviewed_at in AiFlashcardReview.objects.filter(learner=learner).values_list(
        "last_reviewed", flat=True
    ):
        if reviewed_at:
            dates.add(timezone.localtime(reviewed_at).date())
    for completed_at in AiProjectCompletion.objects.filter(learner=learner).values_list(
        "completed_at", flat=True
    ):
        if completed_at:
            dates.add(timezone.localtime(completed_at).date())
    return dates


def streak_for(learner: Learner, today=None) -> int:
    today = today or timezone.localdate()
    dates = _activity_dates(learner)
    if not dates:
        return 0
    cursor = today if today in dates else today - timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def create_attempt_from_questions(
    learner: Learner,
    question_ids: list[int],
    *,
    module: AiModule,
    limit: int | None = None,
) -> AiAttempt:
    ids = list(dict.fromkeys(int(question_id) for question_id in question_ids))
    if not ids:
        raise ValueError("There are no questions to practise yet.")
    random.shuffle(ids)
    if limit is not None:
        ids = ids[:limit]
    with transaction.atomic():
        attempt = AiAttempt.objects.create(
            learner=learner, module=module, length=len(ids)
        )
        AiAttemptQuestion.objects.bulk_create(
            [
                AiAttemptQuestion(attempt=attempt, question_id=question_id, position=index)
                for index, question_id in enumerate(ids)
            ]
        )
    return attempt


def create_retry_attempt(learner: Learner, attempt: AiAttempt) -> AiAttempt:
    missed_ids = list(
        attempt.attempt_questions.filter(
            selected__isnull=False, is_correct=False
        ).values_list("question_id", flat=True)
    )
    if not missed_ids:
        raise ValueError("This run has no missed questions to retry.")
    return create_attempt_from_questions(
        learner, missed_ids, module=attempt.module
    )


def _weak_spot_ids(learner: Learner) -> list[int]:
    rows = AiAttemptQuestion.objects.filter(
        attempt__learner=learner, selected__isnull=False
    )
    missed = set(rows.filter(is_correct=False).values_list("question_id", flat=True))
    correct = set(rows.filter(is_correct=True).values_list("question_id", flat=True))
    return sorted(missed - correct)


def weak_spot_count(learner: Learner) -> int:
    return len(_weak_spot_ids(learner))


def create_weak_spot_attempt(learner: Learner, limit: int = 10) -> AiAttempt:
    ids = _weak_spot_ids(learner)[:limit]
    if not ids:
        raise ValueError("No open weak spots yet.")
    module = AiQuestion.objects.select_related("module").get(pk=ids[0]).module
    return create_attempt_from_questions(learner, ids, module=module)


def reset_progress(learner: Learner) -> None:
    AiAttempt.objects.filter(learner=learner).delete()
    AiFlashcardReview.objects.filter(learner=learner).delete()
    AiLessonProgress.objects.filter(learner=learner).delete()
    AiProjectCompletion.objects.filter(learner=learner).delete()


def gamification(learner: Learner) -> dict:
    completed_lessons = AiLessonProgress.objects.filter(learner=learner).count()
    completed_attempts = AiAttempt.objects.filter(
        learner=learner, completed_at__isnull=False
    )
    best_by_module: dict[int, int] = {}
    for attempt in completed_attempts:
        best_by_module[attempt.module_id] = max(
            best_by_module.get(attempt.module_id, 0), attempt.score_percent
        )
    reviewed_cards = AiFlashcardReview.objects.filter(learner=learner).count()
    projects = AiProjectCompletion.objects.filter(learner=learner).count()

    xp = (
        completed_lessons * 20
        + sum(20 + score // 5 for score in best_by_module.values())
        + reviewed_cards * 2
        + projects * 150
    )
    level_index = 0
    for index, (threshold, _) in enumerate(LEVELS):
        if xp >= threshold:
            level_index = index
    current_threshold, level_name = LEVELS[level_index]
    next_threshold = (
        LEVELS[level_index + 1][0] if level_index + 1 < len(LEVELS) else None
    )
    return {
        "xp": xp,
        "level_index": level_index,
        "level_name": level_name,
        "next_level_xp": next_threshold,
        "level_percent": (
            percent(xp - current_threshold, next_threshold - current_threshold)
            if next_threshold
            else 100
        ),
        "streak": streak_for(learner),
        "active_days": len(_activity_dates(learner)),
    }


def overall_stats(learner: Learner) -> dict:
    modules = list(AiModule.objects.all())
    lesson_total = AiLesson.objects.count()
    completed_lessons = AiLessonProgress.objects.filter(learner=learner).count()
    card_total = AiFlashcard.objects.count()
    reviewed_cards = AiFlashcardReview.objects.filter(learner=learner).count()
    attempts = AiAttempt.objects.filter(learner=learner, completed_at__isnull=False)
    best_scores = [attempt.score_percent for attempt in attempts]
    project_total = AiProject.objects.count()
    projects_shipped = AiProjectCompletion.objects.filter(learner=learner).count()
    module_rows = [module_progress(learner, module) for module in modules]
    completed_modules = sum(1 for row in module_rows if row["is_complete"])
    quiz_average = round(sum(best_scores) / len(best_scores)) if best_scores else 0
    games = gamification(learner)

    lesson_percent = percent(completed_lessons, lesson_total)
    card_percent = percent(reviewed_cards, card_total)
    project_percent = percent(projects_shipped, project_total)
    readiness = round(
        lesson_percent * 0.30
        + quiz_average * 0.25
        + card_percent * 0.10
        + project_percent * 0.35
    )
    return {
        "module_total": len(modules),
        "lesson_total": lesson_total,
        "completed_lessons": completed_lessons,
        "lesson_percent": lesson_percent,
        "card_total": card_total,
        "reviewed_cards": reviewed_cards,
        "card_percent": card_percent,
        "due_cards": len(due_cards(learner)),
        "quiz_attempts": attempts.count(),
        "quiz_average": quiz_average,
        "best_score": max(best_scores, default=0),
        "project_total": project_total,
        "projects_shipped": projects_shipped,
        "project_percent": project_percent,
        "completed_modules": completed_modules,
        "readiness": readiness,
        "module_rows": module_rows,
        "xp": games["xp"],
        "level_name": games["level_name"],
        "next_level_xp": games["next_level_xp"],
        "level_percent": games["level_percent"],
        "streak": games["streak"],
        "active_days": games["active_days"],
        "note_count": AiLessonNote.objects.filter(learner=learner).exclude(
            body="", is_bookmarked=False
        ).count(),
        "bookmark_count": AiLessonNote.objects.filter(
            learner=learner, is_bookmarked=True
        ).count(),
    }


def _cards_with_reviews(learner: Learner, module: AiModule | None = None):
    cards = AiFlashcard.objects.select_related("module").prefetch_related(
        Prefetch(
            "reviews",
            queryset=AiFlashcardReview.objects.filter(learner=learner),
            to_attr="learner_reviews",
        )
    )
    if module:
        cards = cards.filter(module=module)
    result = []
    for card in cards:
        review = card.learner_reviews[0] if card.learner_reviews else None
        result.append((card, review))
    return result


def due_cards(learner: Learner, module: AiModule | None = None) -> list[dict]:
    today = timezone.localdate()
    ready = [
        (card, review)
        for card, review in _cards_with_reviews(learner, module)
        if review is None or review.due_date <= today
    ]
    ready.sort(
        key=lambda pair: (
            0 if pair[1] else 1,
            pair[1].due_date if pair[1] else today,
            pair[0].module.order,
            pair[0].position,
            pair[0].pk,
        )
    )
    return [{"card": card, "review": review} for card, review in ready]


def flashcard_progress(learner: Learner, module: AiModule | None = None) -> dict:
    pairs = _cards_with_reviews(learner, module)
    today = timezone.localdate()
    reviewed = sum(1 for _, review in pairs if review is not None)
    due = sum(1 for _, review in pairs if review is None or review.due_date <= today)
    learned = sum(
        1 for _, review in pairs if review is not None and review.repetitions >= 2
    )
    future = [
        review.due_date
        for _, review in pairs
        if review is not None and review.due_date > today
    ]
    return {
        "total": len(pairs),
        "reviewed": reviewed,
        "due": due,
        "learned": learned,
        "next_due": min(future) if future else None,
        "percent": percent(reviewed, len(pairs)),
    }


def flashcard_decks(learner: Learner) -> list[dict]:
    rows = []
    for module in AiModule.objects.all():
        progress = flashcard_progress(learner, module)
        rows.append({"module": module, **progress})
    return rows


def award_flashcard(learner: Learner, card: AiFlashcard, rating: str) -> AiFlashcardReview:
    review, _ = AiFlashcardReview.objects.get_or_create(
        learner=learner,
        flashcard=card,
        defaults={"due_date": timezone.localdate()},
    )
    review.review(rating)
    return review
