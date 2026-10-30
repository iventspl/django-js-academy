"""Logika postępu i fiszek JS Akademii."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Prefetch

from django.utils import timezone

from dojo.models import Learner

from .models import (
    JsAttempt,
    JsAttemptQuestion,
    JsChallenge,
    JsChallengeCompletion,
    JsFlashcard,
    JsFlashcardReview,
    JsLesson,
    JsLessonNote,
    JsLessonProgress,
    JsModule,
    JsQuestion,
    percent,
)

LEVELS = [
    (0, "Nowicjusz"),
    (100, "Odkrywca"),
    (250, "Builder"),
    (450, "Architekt"),
    (700, "Ekspert"),
    (1000, "Mistrz JS"),
]


def create_attempt_from_questions(learner: Learner, module: JsModule, question_ids: list[int]) -> JsAttempt:
    attempt = JsAttempt.objects.create(
        learner=learner, module=module, length=len(question_ids)
    )
    JsAttemptQuestion.objects.bulk_create(
        [
            JsAttemptQuestion(attempt=attempt, question_id=question_id, position=index)
            for index, question_id in enumerate(question_ids)
        ]
    )
    return attempt


def create_retry_attempt(learner: Learner, attempt: JsAttempt) -> JsAttempt:
    missed_ids = list(
        attempt.attempt_questions.filter(
            selected__isnull=False, is_correct=False
        ).values_list("question_id", flat=True)
    )
    if not missed_ids:
        raise ValueError("Ta próba nie ma błędnych odpowiedzi do powtórki.")
    return create_attempt_from_questions(learner, attempt.module, missed_ids)


def _weak_spot_ids(learner: Learner) -> list[int]:
    rows = JsAttemptQuestion.objects.filter(
        attempt__learner=learner, selected__isnull=False
    )
    missed = set(rows.filter(is_correct=False).values_list("question_id", flat=True))
    correct = set(rows.filter(is_correct=True).values_list("question_id", flat=True))
    return sorted(missed - correct)


def weak_spot_count(learner: Learner) -> int:
    return len(_weak_spot_ids(learner))


def create_weak_spot_attempt(learner: Learner, limit: int = 10) -> JsAttempt:
    ids = _weak_spot_ids(learner)[:limit]
    if not ids:
        raise ValueError("Brak otwartych słabych punktów.")
    module = JsQuestion.objects.select_related("module").get(pk=ids[0]).module
    return create_attempt_from_questions(learner, module, ids)


def reset_progress(learner: Learner) -> None:
    JsAttempt.objects.filter(learner=learner).delete()
    JsFlashcardReview.objects.filter(learner=learner).delete()
    JsLessonProgress.objects.filter(learner=learner).delete()
    JsChallengeCompletion.objects.filter(learner=learner).delete()


def module_progress(learner: Learner, module: JsModule) -> dict:
    lesson_ids = list(module.lessons.values_list("id", flat=True))
    completed = set(
        JsLessonProgress.objects.filter(
            learner=learner, lesson_id__in=lesson_ids
        ).values_list("lesson_id", flat=True)
    )
    lessons = list(module.lessons.all())
    next_lesson = next((lesson for lesson in lessons if lesson.id not in completed), None)
    attempts = list(
        JsAttempt.objects.filter(
            learner=learner, module=module, completed_at__isnull=False
        ).order_by("-started_at")
    )
    best_percent = max((attempt.score_percent for attempt in attempts), default=0)
    review_count = JsFlashcardReview.objects.filter(
        learner=learner, flashcard__module=module
    ).count()
    card_total = module.flashcards.count()
    due = due_cards(learner, module)
    return {
        "module": module,
        "lessons": lessons,
        "completed_ids": completed,
        "completed_lessons": len(completed),
        "lesson_total": len(lessons),
        "lesson_percent": percent(len(completed), len(lessons)),
        "next_lesson": next_lesson,
        "best_score": best_percent,
        "attempt_count": len(attempts),
        "last_attempt": attempts[0] if attempts else None,
        "card_total": card_total,
        "reviewed_cards": review_count,
        "card_percent": percent(review_count, card_total),
        "due_cards": len(due),
        "is_complete": len(completed) == len(lessons) and len(lessons) > 0,
    }


def next_lesson(learner: Learner) -> dict | None:
    modules = list(JsModule.objects.prefetch_related("lessons"))
    for module in modules:
        completed = set(
            JsLessonProgress.objects.filter(
                learner=learner, lesson__module=module
            ).values_list("lesson_id", flat=True)
        )
        for lesson in module.lessons.all():
            if lesson.id not in completed:
                return {"module": module, "lesson": lesson}
    if modules:
        last_module = modules[-1]
        lesson = last_module.lessons.order_by("-order").first()
        if lesson:
            return {"module": last_module, "lesson": lesson}
    return None


def gamification(learner: Learner) -> dict:
    """XP, poziom i seria dni na podstawie rzeczywistych ukończeń."""
    dates: set = set()
    completed_lessons = JsLessonProgress.objects.filter(learner=learner)
    for completed_at in completed_lessons.values_list("completed_at", flat=True):
        if completed_at:
            dates.add(timezone.localtime(completed_at).date())

    attempts = JsAttempt.objects.filter(learner=learner, completed_at__isnull=False)
    for completed_at in attempts.values_list("completed_at", flat=True):
        if completed_at:
            dates.add(timezone.localtime(completed_at).date())

    reviews = JsFlashcardReview.objects.filter(learner=learner)
    for reviewed_at in reviews.values_list("last_reviewed", flat=True):
        if reviewed_at:
            dates.add(timezone.localtime(reviewed_at).date())

    completions = JsChallengeCompletion.objects.filter(
        learner=learner, passed=True
    ).select_related("challenge")
    for completed_at in completions.values_list("completed_at", flat=True):
        if completed_at:
            dates.add(timezone.localtime(completed_at).date())

    best_by_module: dict[int, int] = {}
    for attempt in attempts:
        best_by_module[attempt.module_id] = max(
            best_by_module.get(attempt.module_id, 0), attempt.score_percent
        )

    lesson_xp = completed_lessons.count() * 10
    card_xp = reviews.count() * 2
    quiz_xp = sum(10 + max(score, 0) // 10 * 2 for score in best_by_module.values())
    challenge_xp = sum(completion.challenge.xp for completion in completions)
    xp = lesson_xp + card_xp + quiz_xp + challenge_xp

    level_index = 0
    for index, (threshold, _) in enumerate(LEVELS):
        if xp >= threshold:
            level_index = index
    level_name = LEVELS[level_index][1]
    next_threshold = (
        LEVELS[level_index + 1][0] if level_index + 1 < len(LEVELS) else None
    )
    current_threshold = LEVELS[level_index][0]
    level_percent = (
        percent(xp - current_threshold, next_threshold - current_threshold)
        if next_threshold
        else 100
    )

    today = timezone.localdate()
    streak = 0
    cursor = today if today in dates else today - timedelta(days=1)
    if today not in dates and cursor not in dates:
        cursor = None
    while cursor is not None and cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "xp": xp,
        "lesson_xp": lesson_xp,
        "card_xp": card_xp,
        "quiz_xp": quiz_xp,
        "challenge_xp": challenge_xp,
        "level_index": level_index,
        "level_name": level_name,
        "next_level_xp": next_threshold,
        "level_percent": level_percent,
        "streak": streak,
        "active_days": len(dates),
        "challenge_count": completions.count(),
    }


def overall_stats(learner: Learner) -> dict:
    modules = list(JsModule.objects.all())
    lesson_total = JsLesson.objects.count()
    completed_lessons = JsLessonProgress.objects.filter(learner=learner).count()
    card_total = JsFlashcard.objects.count()
    reviewed_cards = JsFlashcardReview.objects.filter(learner=learner).count()
    attempts = JsAttempt.objects.filter(learner=learner, completed_at__isnull=False)
    best_scores = [attempt.score_percent for attempt in attempts]
    due = due_cards(learner)
    completed_modules = 0
    for module in modules:
        progress = module_progress(learner, module)
        if progress["lesson_percent"] == 100:
            completed_modules += 1
    game = gamification(learner)
    return {
        "module_total": len(modules),
        "lesson_total": lesson_total,
        "demo_total": JsLesson.objects.exclude(live_demo_html="").count(),
        "challenge_total": JsChallenge.objects.count(),
        "note_count": JsLessonNote.objects.filter(learner=learner).exclude(body="").count(),
        "bookmark_count": JsLessonNote.objects.filter(learner=learner, is_bookmarked=True).count(),
        "completed_lessons": completed_lessons,
        "lesson_percent": percent(completed_lessons, lesson_total),
        "card_total": card_total,
        "reviewed_cards": reviewed_cards,
        "card_percent": percent(reviewed_cards, card_total),
        "due_cards": len(due),
        "quiz_attempts": attempts.count(),
        "best_score": max(best_scores, default=0),
        "completed_modules": completed_modules,
        "xp": game["xp"],
        "level_name": game["level_name"],
        "next_level_xp": game["next_level_xp"],
        "level_percent": game["level_percent"],
        "streak": game["streak"],
        "active_days": game["active_days"],
        "challenge_count": game["challenge_count"],
    }


def achievements(learner: Learner) -> list[dict]:
    completed_lessons = JsLessonProgress.objects.filter(learner=learner).count()
    completed_quizzes = JsAttempt.objects.filter(
        learner=learner, completed_at__isnull=False
    )
    best_quiz = max(
        (attempt.score_percent for attempt in completed_quizzes), default=0
    )
    reviewed_cards = JsFlashcardReview.objects.filter(learner=learner).count()
    passed_challenges = JsChallengeCompletion.objects.filter(
        learner=learner, passed=True
    ).count()
    streak = gamification(learner)["streak"]
    items = [
        {
            "key": "first-step",
            "icon": "01",
            "title": "Pierwszy krok",
            "description": "Ukończ pierwszą lekcję.",
            "earned": completed_lessons >= 1,
            "progress": min(completed_lessons, 1),
            "target": 1,
        },
        {
            "key": "ten-lessons",
            "icon": "10",
            "title": "Dziesiątka",
            "description": "Ukończ 10 lekcji.",
            "earned": completed_lessons >= 10,
            "progress": min(completed_lessons, 10),
            "target": 10,
        },
        {
            "key": "first-quiz",
            "icon": "?",
            "title": "Pierwszy quiz",
            "description": "Ukończ dowolny quiz modułu.",
            "earned": completed_quizzes.exists(),
            "progress": min(completed_quizzes.count(), 1),
            "target": 1,
        },
        {
            "key": "quiz-80",
            "icon": "80",
            "title": "Pewna ręka",
            "description": "Zdobądź co najmniej 80% w quizie.",
            "earned": best_quiz >= 80,
            "progress": min(best_quiz, 80),
            "target": 80,
        },
        {
            "key": "cards-25",
            "icon": "▣",
            "title": "Fiszki w ruchu",
            "description": "Powtórz 25 fiszek.",
            "earned": reviewed_cards >= 25,
            "progress": min(reviewed_cards, 25),
            "target": 25,
        },
        {
            "key": "first-challenge",
            "icon": "⌘",
            "title": "Kod działa",
            "description": "Ukończ pierwsze wyzwanie.",
            "earned": passed_challenges >= 1,
            "progress": min(passed_challenges, 1),
            "target": 1,
        },
        {
            "key": "five-challenges",
            "icon": "5",
            "title": "Debugger",
            "description": "Ukończ 5 wyzwań.",
            "earned": passed_challenges >= 5,
            "progress": min(passed_challenges, 5),
            "target": 5,
        },
        {
            "key": "streak-7",
            "icon": "7",
            "title": "Tydzień rytmu",
            "description": "Utrzymaj serię przez 7 dni.",
            "earned": streak >= 7,
            "progress": min(streak, 7),
            "target": 7,
        },
    ]
    for item in items:
        item["percent"] = percent(item["progress"], item["target"])
    return items


def _cards_with_reviews(learner: Learner, module: JsModule | None = None) -> list[tuple]:
    cards = JsFlashcard.objects.select_related("module").prefetch_related(
        Prefetch(
            "reviews",
            queryset=JsFlashcardReview.objects.filter(learner=learner),
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


def due_cards(learner: Learner, module: JsModule | None = None) -> list[dict]:
    today = timezone.localdate()
    ready = []
    for card, review in _cards_with_reviews(learner, module):
        if review is None or review.due_date <= today:
            ready.append((card, review))
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


def flashcard_progress(learner: Learner, module: JsModule | None = None) -> dict:
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
    decks = []
    for module in JsModule.objects.all():
        progress = flashcard_progress(learner, module)
        decks.append(
            {
                "module": module,
                "total": progress["total"],
                "due": progress["due"],
                "reviewed": progress["reviewed"],
                "percent": progress["percent"],
                "next_due": progress["next_due"],
            }
        )
    return decks
