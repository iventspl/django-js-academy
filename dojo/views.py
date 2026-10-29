from __future__ import annotations

from datetime import date

import django
from django.contrib import messages
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .field_guide import load_releases
from .forms import QuizSetupForm
from .models import (
    AppBlueprint,
    ArchitectureCase,
    Attempt,
    Cheatsheet,
    DIFFICULTY_CHOICES,
    Flashcard,
    Learner,
    Question,
    ReleaseNote,
    ReleaseSeries,
    Topic,
)
from .services import (
    achievements,
    activities,
    award_flashcard,
    complete_attempt,
    create_attempt,
    create_retry_attempt,
    create_weak_spot_attempt,
    dashboard_stats,
    due_flashcards,
    flashcard_overview,
    flashcard_progress,
    flashcards_reviewed_today,
    next_flashcard,
    recent_activity,
    record_answer,
    reset_progress,
    topic_progress,
)


def home(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    stats = dashboard_stats(learner)
    context = {
        "learner": learner,
        "stats": stats,
        "activity": recent_activity(learner, 21),
        "next_card": next_flashcard(learner),
        "recent_attempts": Attempt.objects.filter(
            learner=learner, completed_at__isnull=False
        ).select_related("topic")[:3],
        "recipe_total": Cheatsheet.objects.count(),
        "blueprint_total": AppBlueprint.objects.count(),
        "architecture_case_total": ArchitectureCase.objects.count(),
        "latest_stable": ReleaseSeries.objects.filter(status="stable").first(),
        "latest_lts": ReleaseSeries.objects.filter(status="lts").first(),
        "active_nav": "home",
    }
    return render(request, "dojo/home.html", context)


@require_GET
def search(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    searched = len(query) >= 2
    topics = Topic.objects.none()
    questions = Question.objects.none()
    cards = Flashcard.objects.none()
    recipes = Cheatsheet.objects.none()
    blueprints = AppBlueprint.objects.none()
    cases = ArchitectureCase.objects.none()
    releases = ReleaseNote.objects.none()
    counts = {
        "topics": 0,
        "questions": 0,
        "cards": 0,
        "recipes": 0,
        "blueprints": 0,
        "cases": 0,
        "releases": 0,
    }

    if searched:
        topic_qs = Topic.objects.filter(
            Q(name__icontains=query)
            | Q(tagline__icontains=query)
            | Q(description__icontains=query)
        )
        question_qs = Question.objects.filter(
            Q(prompt__icontains=query) | Q(code__icontains=query),
            is_active=True,
        ).select_related("topic")
        card_qs = Flashcard.objects.filter(
            Q(front__icontains=query)
            | Q(back__icontains=query)
            | Q(hint__icontains=query)
        ).select_related("topic")
        recipe_qs = Cheatsheet.objects.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(when_to_use__icontains=query)
            | Q(code__icontains=query)
            | Q(category__icontains=query)
        ).select_related("topic")
        blueprint_qs = AppBlueprint.objects.filter(
            Q(name__icontains=query)
            | Q(tagline__icontains=query)
            | Q(problem__icontains=query)
            | Q(stack_notes__icontains=query)
        ).select_related("topic")
        case_qs = ArchitectureCase.objects.filter(
            Q(name__icontains=query)
            | Q(tagline__icontains=query)
            | Q(scenario__icontains=query)
            | Q(requirements__icontains=query)
        ).select_related("topic")
        release_qs = ReleaseNote.objects.filter(
            Q(version__icontains=query)
            | Q(headline__icontains=query)
            | Q(summary__icontains=query)
            | Q(why_it_matters__icontains=query)
        )

        counts = {
            "topics": topic_qs.count(),
            "questions": question_qs.count(),
            "cards": card_qs.count(),
            "recipes": recipe_qs.count(),
            "blueprints": blueprint_qs.count(),
            "cases": case_qs.count(),
            "releases": release_qs.count(),
        }
        topics = topic_qs[:8]
        questions = question_qs[:10]
        cards = card_qs[:8]
        recipes = recipe_qs[:8]
        blueprints = blueprint_qs[:8]
        cases = case_qs[:8]
        releases = release_qs[:8]

    return render(
        request,
        "dojo/search.html",
        {
            "query": query,
            "searched": searched,
            "topics": topics,
            "questions": questions,
            "cards": cards,
            "recipes": recipes,
            "blueprints": blueprints,
            "cases": cases,
            "releases": releases,
            "counts": counts,
            "total_count": sum(counts.values()),
            "topic_total": Topic.objects.count(),
            "active_nav": "search",
        },
    )


@require_http_methods(["GET", "POST"])
def quiz_setup(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    initial = {"length": 10}
    topic_slug = request.GET.get("topic")
    if topic_slug:
        topic = Topic.objects.filter(slug=topic_slug).first()
        if topic:
            initial["topic"] = topic.pk
    difficulty = request.GET.get("difficulty", "")
    if difficulty in dict(DIFFICULTY_CHOICES):
        initial["difficulty"] = difficulty
    try:
        initial["length"] = int(request.GET.get("length", 10))
    except (TypeError, ValueError):
        pass

    if request.method == "POST":
        form = QuizSetupForm(request.POST)
        if form.is_valid():
            try:
                attempt = create_attempt(
                    learner,
                    topic=form.cleaned_data["topic"],
                    difficulty=form.cleaned_data["difficulty"],
                    length=form.cleaned_data["length"],
                )
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                return redirect("dojo:quiz_question", attempt_id=attempt.pk)
    else:
        form = QuizSetupForm(initial=initial)

    topics = topic_progress(learner)
    return render(
        request,
        "dojo/quiz_setup.html",
        {
            "form": form,
            "learner": learner,
            "topics": topics,
            "active_nav": "quiz",
            "question_total": sum(row["question_total"] for row in topics),
        },
    )


@require_http_methods(["GET", "POST"])
def quiz_question(request: HttpRequest, attempt_id: int) -> HttpResponse:
    learner = Learner.local()
    attempt = get_object_or_404(
        Attempt.objects.select_related("topic", "learner"),
        pk=attempt_id,
        learner=learner,
    )
    if attempt.completed_at:
        return redirect("dojo:quiz_results", attempt_id=attempt.pk)

    attempt_question = attempt.current_attempt_question()
    if attempt_question is None:
        complete_attempt(attempt)
        return redirect("dojo:quiz_results", attempt_id=attempt.pk)
    question = attempt_question.question
    choices = list(question.choices.all())

    if request.method == "POST":
        action = request.POST.get("action", "answer")
        if action == "answer":
            raw_choice = request.POST.get("choice")
            try:
                choice_id = int(raw_choice)
            except (TypeError, ValueError):
                messages.error(request, "Pick an answer before checking it.")
            else:
                choice = next((c for c in choices if c.pk == choice_id), None)
                if choice is None:
                    messages.error(request, "That answer does not belong to this question.")
                else:
                    record_answer(attempt_question, choice)
                    return redirect(
                        f"{reverse('dojo:quiz_question', args=[attempt.pk])}?checked=1"
                    )
        elif action == "next":
            if attempt_question.selected_id is None:
                messages.error(request, "Choose an answer first.")
            elif attempt.current_index + 1 >= attempt.length:
                complete_attempt(attempt)
                return redirect("dojo:quiz_results", attempt_id=attempt.pk)
            else:
                attempt.current_index += 1
                attempt.save(update_fields=["current_index"])
                return redirect("dojo:quiz_question", attempt_id=attempt.pk)
        else:
            messages.error(request, "Unknown action.")
        # Re-fetch so the template always reflects persisted state.
        attempt_question.refresh_from_db()

    selected = next(
        (c for c in choices if attempt_question.selected_id == c.pk),
        None,
    )
    correct_choice = next((c for c in choices if c.is_correct), None)
    answered = attempt_question.selected_id is not None

    return render(
        request,
        "dojo/quiz_question.html",
        {
            "attempt": attempt,
            "attempt_question": attempt_question,
            "question": question,
            "choices": choices,
            "selected": selected,
            "correct_choice": correct_choice,
            "answered": answered,
            "is_correct": attempt_question.is_correct,
            "question_number": attempt.current_index + 1,
            "progress_percent": round(100 * (attempt.current_index + 1) / attempt.length),
            "active_nav": "quiz",
        },
    )


@require_GET
def quiz_results(request: HttpRequest, attempt_id: int) -> HttpResponse:
    learner = Learner.local()
    attempt = get_object_or_404(
        Attempt.objects.select_related("topic", "learner"),
        pk=attempt_id,
        learner=learner,
    )
    if not attempt.completed_at:
        if attempt.answered_count >= attempt.length:
            complete_attempt(attempt)
        else:
            return redirect("dojo:quiz_question", attempt_id=attempt.pk)

    attempt_questions = list(
        attempt.attempt_questions.select_related(
            "question", "question__topic", "selected"
        ).prefetch_related("question__choices")
    )
    by_difficulty = []
    for value, label in DIFFICULTY_CHOICES:
        rows = [row for row in attempt_questions if row.question.difficulty == value]
        correct = sum(1 for row in rows if row.is_correct)
        by_difficulty.append(
            {
                "label": label,
                "total": len(rows),
                "correct": correct,
                "percent": round(100 * correct / len(rows)) if rows else 0,
            }
        )
    if attempt.score_percent == 100:
        verdict = "Perfect run."
    elif attempt.score_percent >= 80:
        verdict = "Strong work."
    elif attempt.score_percent >= 50:
        verdict = "A solid start."
    else:
        verdict = "Every miss is a lesson."
    best_streak = 0
    running = 0
    for row in attempt_questions:
        if row.is_correct:
            running += 1
            best_streak = max(best_streak, running)
        else:
            running = 0
    missed_count = sum(1 for row in attempt_questions if not row.is_correct)
    return render(
        request,
        "dojo/quiz_results.html",
        {
            "attempt": attempt,
            "attempt_questions": attempt_questions,
            "by_difficulty": by_difficulty,
            "verdict": verdict,
            "best_streak": best_streak,
            "missed_count": missed_count,
            "active_nav": "quiz",
        },
    )


@require_POST
def retry_missed(request: HttpRequest, attempt_id: int) -> HttpResponse:
    learner = Learner.local()
    attempt = get_object_or_404(
        Attempt.objects.select_related("topic"),
        pk=attempt_id,
        learner=learner,
        completed_at__isnull=False,
    )
    try:
        retry = create_retry_attempt(learner, attempt)
    except ValueError as exc:
        messages.info(request, str(exc))
        return redirect("dojo:quiz_results", attempt_id=attempt.pk)
    return redirect("dojo:quiz_question", attempt_id=retry.pk)


@require_POST
def weak_spots_practice(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    try:
        attempt = create_weak_spot_attempt(learner)
    except ValueError as exc:
        messages.info(request, str(exc))
        return redirect("dojo:progress")
    return redirect("dojo:quiz_question", attempt_id=attempt.pk)


@require_GET
def flashcards_index(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    decks = flashcard_overview(learner)
    stats = dashboard_stats(learner)
    return render(
        request,
        "dojo/flashcards_index.html",
        {
            "learner": learner,
            "decks": decks,
            "stats": stats,
            "reviewed_today": flashcards_reviewed_today(learner),
            "active_nav": "flashcards",
        },
    )


def _study_context(request: HttpRequest, topic: Topic | None) -> dict:
    learner = Learner.local()
    queue = due_flashcards(learner, topic)
    progress_data = flashcard_progress(learner, topic)
    card = queue[0]["card"] if queue else None
    review = queue[0]["review"] if queue else None
    reveal = request.GET.get("reveal") == "1"
    return {
        "learner": learner,
        "topic": topic,
        "card": card,
        "review": review,
        "queue_remaining": len(queue),
        "progress": progress_data,
        "reveal": reveal,
        "reviewed_today": flashcards_reviewed_today(learner),
        "active_nav": "flashcards",
    }


@require_GET
def flashcards_study(request: HttpRequest, topic_slug: str) -> HttpResponse:
    topic = get_object_or_404(Topic, slug=topic_slug)
    return render(request, "dojo/flashcards_study.html", _study_context(request, topic))


@require_GET
def flashcards_review_all(request: HttpRequest) -> HttpResponse:
    return render(request, "dojo/flashcards_study.html", _study_context(request, None))


@require_POST
def flashcards_rate(
    request: HttpRequest, card_id: int, topic_slug: str | None = None
) -> HttpResponse:
    learner = Learner.local()
    topic = get_object_or_404(Topic, slug=topic_slug) if topic_slug else None
    card = get_object_or_404(Flashcard.objects.select_related("topic"), pk=card_id)
    if topic and card.topic_id != topic.pk:
        raise Http404("That card is not in this deck.")
    rating = request.POST.get("rating", "")
    if rating not in {"again", "hard", "good", "easy"}:
        messages.error(request, "Choose again, hard, good, or easy.")
        if topic:
            return redirect("dojo:flashcards_study", topic_slug=topic.slug)
        return redirect("dojo:flashcards_review_all")
    award_flashcard(learner, card, rating)
    if topic:
        return redirect("dojo:flashcards_study", topic_slug=topic.slug)
    return redirect("dojo:flashcards_review_all")


@require_GET
def architecture_studio(request: HttpRequest) -> HttpResponse:
    complexity = request.GET.get("complexity", "").strip()
    cases = ArchitectureCase.objects.select_related("topic")
    if complexity:
        cases = cases.filter(complexity=complexity)
    return render(
        request,
        "dojo/architecture_studio.html",
        {
            "cases": cases,
            "case_total": ArchitectureCase.objects.count(),
            "active_complexity": complexity,
            "complexity_choices": ArchitectureCase.COMPLEXITY_CHOICES,
            "recipe_total": Cheatsheet.objects.count(),
            "topic_total": Topic.objects.count(),
            "active_nav": "architecture",
        },
    )


@require_GET
def architecture_case(request: HttpRequest, key: str) -> HttpResponse:
    case = get_object_or_404(
        ArchitectureCase.objects.select_related("topic"), key=key
    )
    related_recipes = Cheatsheet.objects.none()
    if case.topic_id:
        related_recipes = Cheatsheet.objects.filter(topic_id=case.topic_id)[:4]
    return render(
        request,
        "dojo/architecture_case.html",
        {
            "case": case,
            "related_recipes": related_recipes,
            "active_nav": "architecture",
        },
    )


@require_GET
def field_guide(request: HttpRequest) -> HttpResponse:
    recipe_categories = (
        Cheatsheet.objects.values_list("category", flat=True).distinct().order_by("category")
    )
    meta = load_releases()
    reviewed_on = date.fromisoformat(meta["reviewed_on"])
    return render(
        request,
        "dojo/field_guide.html",
        {
            "recipe_total": Cheatsheet.objects.count(),
            "blueprint_total": AppBlueprint.objects.count(),
            "architecture_case_total": ArchitectureCase.objects.count(),
            "release_note_total": ReleaseNote.objects.count(),
            "recipes": Cheatsheet.objects.select_related("topic")[:5],
            "blueprints": AppBlueprint.objects.select_related("topic")[:3],
            "series": ReleaseSeries.objects.all(),
            "latest_notes": ReleaseNote.objects.all()[:3],
            "latest_stable": ReleaseSeries.objects.filter(status="stable").first(),
            "latest_lts": ReleaseSeries.objects.filter(status="lts").first(),
            "reviewed_on": reviewed_on,
            "active_nav": "guide",
        },
    )


@require_GET
def cheatsheets(request: HttpRequest) -> HttpResponse:
    search_query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    recipes = Cheatsheet.objects.select_related("topic")
    if search_query:
        recipes = recipes.filter(
            Q(title__icontains=search_query)
            | Q(summary__icontains=search_query)
            | Q(when_to_use__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(code__icontains=search_query)
        )
    if category:
        recipes = recipes.filter(category=category)
    categories = list(
        Cheatsheet.objects.values_list("category", flat=True).distinct().order_by("category")
    )
    return render(
        request,
        "dojo/cheatsheets.html",
        {
            "recipes": recipes,
            "categories": categories,
            "active_category": category,
            "search_query": search_query,
            "result_count": recipes.count(),
            "total_count": Cheatsheet.objects.count(),
            "active_nav": "guide",
        },
    )


@require_GET
def blueprints(request: HttpRequest) -> HttpResponse:
    complexity = request.GET.get("complexity", "").strip()
    items = AppBlueprint.objects.select_related("topic")
    if complexity:
        items = items.filter(complexity=complexity)
    return render(
        request,
        "dojo/blueprints.html",
        {
            "blueprints": items,
            "active_complexity": complexity,
            "complexity_choices": AppBlueprint.COMPLEXITY_CHOICES,
            "active_nav": "guide",
        },
    )


@require_GET
def blueprint_detail(request: HttpRequest, key: str) -> HttpResponse:
    blueprint = get_object_or_404(
        AppBlueprint.objects.select_related("topic"), key=key
    )
    related_recipes = Cheatsheet.objects.none()
    if blueprint.topic_id:
        related_recipes = Cheatsheet.objects.filter(topic_id=blueprint.topic_id)[:4]
    return render(
        request,
        "dojo/blueprint_detail.html",
        {
            "blueprint": blueprint,
            "related_recipes": related_recipes,
            "active_nav": "guide",
        },
    )


@require_GET
def release_radar(request: HttpRequest) -> HttpResponse:
    meta = load_releases()
    return render(
        request,
        "dojo/release_radar.html",
        {
            "series": ReleaseSeries.objects.all(),
            "notes": ReleaseNote.objects.all(),
            "reviewed_on": date.fromisoformat(meta["reviewed_on"]),
            "installed_version": django.get_version(),
            "active_nav": "guide",
        },
    )


@require_GET
def progress(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    stats = dashboard_stats(learner)
    return render(
        request,
        "dojo/progress.html",
        {
            "learner": learner,
            "stats": stats,
            "activity_days": recent_activity(learner, 28),
            "achievements": achievements(learner, stats),
            "activities": activities(learner),
            "recent_attempts": Attempt.objects.filter(
                learner=learner, completed_at__isnull=False
            ).select_related("topic")[:8],
            "active_nav": "progress",
        },
    )


@require_POST
def progress_reset(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    reset_progress(learner)
    messages.success(request, "Progress cleared. A clean notebook awaits.")
    return redirect("dojo:progress")
