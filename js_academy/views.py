from __future__ import annotations

import random

from django.contrib import messages
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from dojo.models import Learner

from .career import FACTS as CAREER_FACTS, REVIEWED_ON, SOURCES as CAREER_SOURCES
from .components import build_component_preview
from .models import (
    JsAttempt,
    JsAttemptQuestion,
    JsChallenge,
    JsChallengeCompletion,
    JsComponent,
    JsFact,
    JsFlashcard,
    JsFlashcardReview,
    JsInterviewQuestion,
    JsLesson,
    JsLessonProgress,
    JsModule,
    JsTerm,
)
from .runner import build_challenge_runner
from .services import (
    achievements,
    due_cards,
    flashcard_decks,
    flashcard_progress,
    module_progress,
    next_lesson,
    overall_stats,
)


def _learner() -> Learner:
    return Learner.local()


def _modules_with_progress(learner: Learner) -> list[dict]:
    return [module_progress(learner, module) for module in JsModule.objects.all()]


def start_lesson(learner: Learner) -> dict | None:
    return next_lesson(learner)


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    facts = list(JsFact.objects.all())
    fact_of_day = facts[timezone.localdate().toordinal() % len(facts)] if facts else None
    challenges = list(JsChallenge.objects.all())
    challenge_of_day = (
        challenges[timezone.localdate().toordinal() % len(challenges)] if challenges else None
    )
    return render(
        request,
        "js_academy/home.html",
        {
            "modules": _modules_with_progress(learner),
            "stats": overall_stats(learner),
            "continue_item": start_lesson(learner),
            "recent_attempts": JsAttempt.objects.filter(
                learner=learner, completed_at__isnull=False
            ).select_related("module")[:3],
            "fact_of_day": fact_of_day,
            "challenge_of_day": challenge_of_day,
            "recent_facts": JsFact.objects.all()[:4],
            "active_nav": "js_start",
            "page_title": "JS Akademia",
        },
    )


@require_GET
def path(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    return render(
        request,
        "js_academy/path.html",
        {
            "modules": _modules_with_progress(learner),
            "stats": overall_stats(learner),
            "active_nav": "js_path",
            "page_title": "Ścieżka nauki",
        },
    )


@require_GET
def module_detail(request: HttpRequest, module_slug: str) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(
        JsModule.objects.prefetch_related("lessons", "flashcards"), slug=module_slug
    )
    return render(
        request,
        "js_academy/module.html",
        {
            "module": module,
            "progress": module_progress(learner, module),
            "cards": flashcard_progress(learner, module),
            "attempts": JsAttempt.objects.filter(
                learner=learner, module=module, completed_at__isnull=False
            ).order_by("-started_at")[:5],
            "active_nav": "js_path",
            "page_title": module.title,
        },
    )


@require_GET
def lesson_detail(request: HttpRequest, module_slug: str, lesson_slug: str) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(JsModule, slug=module_slug)
    lesson = get_object_or_404(
        JsLesson.objects.select_related("module"), module=module, slug=lesson_slug
    )
    lessons = list(module.lessons.all())
    index = lessons.index(lesson)
    completed = JsLessonProgress.objects.filter(
        learner=learner, lesson=lesson
    ).exists()
    completed_ids = set(
        JsLessonProgress.objects.filter(
            learner=learner, lesson__module=module
        ).values_list("lesson_id", flat=True)
    )
    return render(
        request,
        "js_academy/lesson.html",
        {
            "module": module,
            "lesson": lesson,
            "lessons": lessons,
            "completed_ids": completed_ids,
            "completed": completed,
            "previous_lesson": lessons[index - 1] if index > 0 else None,
            "following_lesson": lessons[index + 1] if index + 1 < len(lessons) else None,
            "lesson_number": index + 1,
            "active_nav": "js_path",
            "page_title": lesson.title,
        },
    )


@require_POST
def complete_lesson(request: HttpRequest, module_slug: str, lesson_slug: str) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(JsModule, slug=module_slug)
    lesson = get_object_or_404(JsLesson, module=module, slug=lesson_slug)
    _, created = JsLessonProgress.objects.get_or_create(
        learner=learner, lesson=lesson
    )
    if created:
        messages.success(request, f"Ukończono lekcję: {lesson.title}.")
    else:
        messages.info(request, "Ta lekcja była już ukończona.")

    if request.POST.get("next") == "1":
        lessons = list(module.lessons.all())
        index = lessons.index(lesson)
        if index + 1 < len(lessons):
            return redirect(
                "js_academy:lesson",
                module_slug=module.slug,
                lesson_slug=lessons[index + 1].slug,
            )
    return redirect("js_academy:module", module_slug=module.slug)


@require_POST
def quiz_start(request: HttpRequest, module_slug: str) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(JsModule, slug=module_slug)
    question_ids = list(module.questions.values_list("id", flat=True))
    if not question_ids:
        messages.error(request, "Ten moduł nie ma jeszcze pytań.")
        return redirect("js_academy:module", module_slug=module.slug)
    random.shuffle(question_ids)
    attempt = JsAttempt.objects.create(
        learner=learner, module=module, length=len(question_ids)
    )
    JsAttemptQuestion.objects.bulk_create(
        [
            JsAttemptQuestion(attempt=attempt, question_id=question_id, position=index)
            for index, question_id in enumerate(question_ids)
        ]
    )
    return redirect("js_academy:quiz", attempt_id=attempt.pk)


@require_http_methods(["GET", "POST"])
def quiz(request: HttpRequest, attempt_id: int) -> HttpResponse:
    learner = _learner()
    attempt = get_object_or_404(
        JsAttempt.objects.select_related("module", "learner"),
        pk=attempt_id,
        learner=learner,
    )
    if attempt.completed_at:
        return redirect("js_academy:quiz_results", attempt_id=attempt.pk)

    aq = attempt.current_attempt_question()
    if aq is None:
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=["completed_at"])
        return redirect("js_academy:quiz_results", attempt_id=attempt.pk)

    question = aq.question
    choices = list(question.choices.all())

    if request.method == "POST":
        action = request.POST.get("action", "answer")
        if action == "answer":
            try:
                choice_id = int(request.POST.get("choice", ""))
            except (TypeError, ValueError):
                messages.error(request, "Wybierz odpowiedź.")
            else:
                choice = next((item for item in choices if item.pk == choice_id), None)
                if choice is None:
                    messages.error(request, "Ta odpowiedź nie należy do pytania.")
                elif aq.selected_id is None:
                    aq.selected = choice
                    aq.is_correct = choice.is_correct
                    aq.answered_at = timezone.now()
                    aq.save(update_fields=["selected", "is_correct", "answered_at"])
                    return redirect(
                        f"{reverse('js_academy:quiz', args=[attempt.pk])}?sprawdzone=1"
                    )
                else:
                    return redirect(
                        f"{reverse('js_academy:quiz', args=[attempt.pk])}?sprawdzone=1"
                    )
        elif action == "next":
            if aq.selected_id is None:
                messages.error(request, "Najpierw wybierz odpowiedź.")
            elif attempt.current_index + 1 >= attempt.length:
                attempt.completed_at = timezone.now()
                attempt.save(update_fields=["completed_at"])
                return redirect("js_academy:quiz_results", attempt_id=attempt.pk)
            else:
                attempt.current_index += 1
                attempt.save(update_fields=["current_index"])
                return redirect("js_academy:quiz", attempt_id=attempt.pk)

        aq.refresh_from_db()

    selected = next((item for item in choices if item.pk == aq.selected_id), None)
    correct = next((item for item in choices if item.is_correct), None)
    return render(
        request,
        "js_academy/quiz.html",
        {
            "attempt": attempt,
            "aq": aq,
            "question": question,
            "choices": choices,
            "selected": selected,
            "correct": correct,
            "answered": aq.selected_id is not None,
            "is_correct": aq.is_correct,
            "number": attempt.current_index + 1,
            "progress": round(100 * (attempt.current_index + 1) / attempt.length),
            "active_nav": "js_path",
            "page_title": f"Quiz · {attempt.module.title}",
        },
    )


@require_GET
def quiz_results(request: HttpRequest, attempt_id: int) -> HttpResponse:
    learner = _learner()
    attempt = get_object_or_404(
        JsAttempt.objects.select_related("module", "learner"),
        pk=attempt_id,
        learner=learner,
    )
    if not attempt.completed_at:
        if attempt.answered_count >= attempt.length:
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=["completed_at"])
        else:
            return redirect("js_academy:quiz", attempt_id=attempt.pk)
    rows = list(
        attempt.attempt_questions.select_related("question", "selected").prefetch_related(
            "question__choices"
        )
    )
    if attempt.score_percent >= 80:
        verdict = "Świetnie! Ten materiał masz opanowany."
    elif attempt.score_percent >= 50:
        verdict = "Dobry start. Przeczytaj wyjaśnienia i wróć do trudnych tematów."
    else:
        verdict = "Nie zgaduj — wróć do lekcji i przepisz przykłady własnymi słowami."
    return render(
        request,
        "js_academy/quiz_results.html",
        {
            "attempt": attempt,
            "rows": rows,
            "verdict": verdict,
            "wrong_count": attempt.length - attempt.correct_count,
            "active_nav": "js_path",
            "page_title": f"Wynik · {attempt.module.title}",
        },
    )


@require_GET
def flashcards_index(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    return render(
        request,
        "js_academy/flashcards_index.html",
        {
            "decks": flashcard_decks(learner),
            "stats": overall_stats(learner),
            "active_nav": "js_cards",
            "page_title": "Fiszki JavaScript",
        },
    )


def _study_context(request: HttpRequest, module: JsModule | None) -> dict:
    learner = _learner()
    queue = due_cards(learner, module)
    return {
        "module": module,
        "card": queue[0]["card"] if queue else None,
        "review": queue[0]["review"] if queue else None,
        "remaining": len(queue),
        "progress": flashcard_progress(learner, module),
        "reveal": request.GET.get("reveal") == "1",
        "active_nav": "js_cards",
        "page_title": f"Fiszki · {module.title}" if module else "Fiszki · powtórka",
    }


@require_GET
def flashcards_study(request: HttpRequest, module_slug: str) -> HttpResponse:
    module = get_object_or_404(JsModule, slug=module_slug)
    return render(request, "js_academy/flashcards_study.html", _study_context(request, module))


@require_GET
def flashcards_review(request: HttpRequest) -> HttpResponse:
    return render(request, "js_academy/flashcards_study.html", _study_context(request, None))


@require_POST
def flashcards_rate(
    request: HttpRequest, card_id: int, module_slug: str | None = None
) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(JsModule, slug=module_slug) if module_slug else None
    card = get_object_or_404(JsFlashcard.objects.select_related("module"), pk=card_id)
    if module and card.module_id != module.pk:
        messages.error(request, "Ta fiszka należy do innego modułu.")
        return redirect("js_academy:flashcards_review")
    rating = request.POST.get("rating", "")
    if rating not in {"again", "hard", "good", "easy"}:
        messages.error(request, "Wybierz jedną z czterech ocen.")
    else:
        review, _ = JsFlashcardReview.objects.get_or_create(
            learner=learner, flashcard=card
        )
        review.review(rating)
    if module:
        return redirect("js_academy:flashcards", module_slug=module.slug)
    return redirect("js_academy:flashcards_review")


@require_GET
def progress(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    achievement_list = achievements(learner)
    return render(
        request,
        "js_academy/progress.html",
        {
            "modules": _modules_with_progress(learner),
            "stats": overall_stats(learner),
            "achievements": achievement_list,
            "achievements_earned": sum(
                1 for item in achievement_list if item["earned"]
            ),
            "attempts": JsAttempt.objects.filter(
                learner=learner, completed_at__isnull=False
            ).select_related("module")[:10],
            "active_nav": "js_progress",
            "page_title": "Postępy",
        },
    )


@require_GET
def challenges(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    difficulty = request.GET.get("difficulty", "")
    items = JsChallenge.objects.select_related("module").all()
    if difficulty in {"beginner", "intermediate", "advanced"}:
        items = items.filter(difficulty=difficulty)
    solved_ids = set(
        JsChallengeCompletion.objects.filter(learner=learner, passed=True).values_list(
            "challenge_id", flat=True
        )
    )
    total = JsChallenge.objects.count()
    return render(
        request,
        "js_academy/challenges.html",
        {
            "challenges": items,
            "difficulty": difficulty,
            "solved_ids": solved_ids,
            "solved_count": len(solved_ids),
            "challenge_total": total,
            "active_nav": "js_challenges",
            "page_title": "Wyzwania kodowania",
        },
    )


@require_GET
def challenge_detail(request: HttpRequest, slug: str) -> HttpResponse:
    learner = _learner()
    challenge = get_object_or_404(
        JsChallenge.objects.select_related("module"), slug=slug
    )
    completion = JsChallengeCompletion.objects.filter(
        learner=learner, challenge=challenge
    ).first()
    return render(
        request,
        "js_academy/challenge.html",
        {
            "challenge": challenge,
            "completion": completion,
            "runner_html": build_challenge_runner(challenge),
            "challenge_total": JsChallenge.objects.count(),
            "active_nav": "js_challenges",
            "page_title": challenge.title,
        },
    )


@require_POST
def challenge_complete(request: HttpRequest, slug: str) -> HttpResponse:
    learner = _learner()
    challenge = get_object_or_404(JsChallenge, slug=slug)
    completion, created = JsChallengeCompletion.objects.get_or_create(
        learner=learner,
        challenge=challenge,
        defaults={"passed": True, "completed_at": timezone.now()},
    )
    if created:
        messages.success(
            request,
            f"Wyzwanie ukończone: {challenge.title}. +{challenge.xp} XP.",
        )
    else:
        messages.info(request, "To wyzwanie jest już oznaczone jako ukończone.")
    return redirect("js_academy:challenge", slug=challenge.slug)


@require_GET
def knowledge(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "js_academy/knowledge.html",
        {
            "fact_count": JsFact.objects.count(),
            "term_count": JsTerm.objects.count(),
            "interview_count": JsInterviewQuestion.objects.count(),
            "facts": JsFact.objects.all()[:5],
            "terms": JsTerm.objects.all()[:8],
            "questions": JsInterviewQuestion.objects.all()[:5],
            "active_nav": "js_knowledge",
            "page_title": "Wiedza JavaScript",
        },
    )


@require_GET
def facts(request: HttpRequest) -> HttpResponse:
    category = request.GET.get("category", "")
    items = JsFact.objects.all()
    if category:
        items = items.filter(category=category)
    return render(
        request,
        "js_academy/facts.html",
        {
            "facts": items,
            "category": category,
            "categories": JsFact.objects.order_by("category")
            .values_list("category", flat=True)
            .distinct(),
            "active_nav": "js_knowledge",
            "page_title": "Ciekawostki o JS",
        },
    )


@require_GET
def glossary(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    items = JsTerm.objects.all()
    if query:
        items = items.filter(
            Q(term__icontains=query)
            | Q(definition__icontains=query)
            | Q(example__icontains=query)
        )
    if category:
        items = items.filter(category=category)
    return render(
        request,
        "js_academy/glossary.html",
        {
            "terms": items,
            "query": query,
            "category": category,
            "categories": JsTerm.objects.order_by("category")
            .values_list("category", flat=True)
            .distinct(),
            "active_nav": "js_knowledge",
            "page_title": "Słownik JS",
        },
    )


@require_GET
def interview(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    difficulty = request.GET.get("difficulty", "")
    category = request.GET.get("category", "")
    items = JsInterviewQuestion.objects.all()
    if query:
        items = items.filter(Q(question__icontains=query) | Q(answer__icontains=query))
    if difficulty in {"beginner", "intermediate", "advanced"}:
        items = items.filter(difficulty=difficulty)
    if category:
        items = items.filter(category=category)
    return render(
        request,
        "js_academy/interview.html",
        {
            "questions": items,
            "query": query,
            "difficulty": difficulty,
            "category": category,
            "categories": JsInterviewQuestion.objects.order_by("category")
            .values_list("category", flat=True)
            .distinct(),
            "active_nav": "js_knowledge",
            "page_title": "Pytania rekrutacyjne",
        },
    )


@require_GET
def ai_career(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "js_academy/ai_career.html",
        {
            "facts": CAREER_FACTS,
            "sources": CAREER_SOURCES,
            "reviewed_on": REVIEWED_ON,
            "active_nav": "js_ai",
            "page_title": "AI a praca programisty",
        },
    )


@require_GET
def playground(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "js_academy/playground.html",
        {
            "active_nav": "js_challenges",
            "page_title": "Piaskownica JavaScript",
        },
    )


@require_GET
def components(request: HttpRequest) -> HttpResponse:
    category = request.GET.get("category", "")
    items = JsComponent.objects.all()
    if category:
        items = items.filter(category=category)
    return render(
        request,
        "js_academy/components.html",
        {
            "components": items,
            "category": category,
            "categories": JsComponent.objects.order_by("category")
            .values_list("category", flat=True)
            .distinct(),
            "component_total": JsComponent.objects.count(),
            "active_nav": "js_components",
            "page_title": "Komponenty JS",
        },
    )


@require_GET
def component_detail(request: HttpRequest, slug: str) -> HttpResponse:
    component = get_object_or_404(JsComponent, key=slug)
    return render(
        request,
        "js_academy/component.html",
        {
            "component": component,
            "preview_html": build_component_preview(component),
            "related": JsComponent.objects.filter(category=component.category).exclude(
                pk=component.pk
            )[:3],
            "active_nav": "js_components",
            "page_title": component.title,
        },
    )


@require_GET
def mvc_guide(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "js_academy/mvc.html",
        {
            "active_nav": "js_mvc",
            "page_title": "MVC w JavaScript",
        },
    )


@require_GET
def search(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    context = {
        "query": query,
        "active_nav": "js_search",
        "page_title": "Szukaj w JS Akademii",
        "groups": [],
    }
    if query:
        modules = JsModule.objects.filter(
            Q(title__icontains=query)
            | Q(subtitle__icontains=query)
            | Q(description__icontains=query)
        )[:8]
        lessons = JsLesson.objects.select_related("module").filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(body_html__icontains=query)
        )[:12]
        components = JsComponent.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:8]
        challenges = JsChallenge.objects.filter(
            Q(title__icontains=query) | Q(prompt__icontains=query)
        )[:8]
        terms = JsTerm.objects.filter(
            Q(term__icontains=query) | Q(definition__icontains=query)
        )[:10]
        facts = JsFact.objects.filter(
            Q(title__icontains=query) | Q(body__icontains=query)
        )[:8]
        interview = JsInterviewQuestion.objects.filter(
            Q(question__icontains=query) | Q(answer__icontains=query)
        )[:8]
        context["groups"] = [
            {"label": "Moduły", "kind": "module", "items": modules},
            {"label": "Lekcje", "kind": "lesson", "items": lessons},
            {"label": "Komponenty", "kind": "component", "items": components},
            {"label": "Wyzwania", "kind": "challenge", "items": challenges},
            {"label": "Słownik", "kind": "term", "items": terms},
            {"label": "Ciekawostki", "kind": "fact", "items": facts},
            {"label": "Pytania rekrutacyjne", "kind": "interview", "items": interview},
        ]
        context["total"] = sum(len(group["items"]) for group in context["groups"])
    return render(request, "js_academy/search.html", context)
