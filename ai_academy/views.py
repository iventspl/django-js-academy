from __future__ import annotations

import random
import re
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib import messages
from django.db.models import Q
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from dojo.models import Learner

from .career import INTERVIEW_TOPICS, ROLE_PATHS, TWELVE_MONTH_PLAN
from .models import (
    AiAttempt,
    AiAttemptQuestion,
    AiFlashcard,
    AiLesson,
    AiLessonProgress,
    AiModule,
    AiProject,
    AiProjectCompletion,
    AiTerm,
    STAGE_CHOICES,
)
from .services import (
    award_flashcard,
    due_cards,
    flashcard_decks,
    flashcard_progress,
    module_progress,
    next_lesson,
    overall_stats,
    project_list,
    project_progress,
)

PROJECT_TEST_DIR = Path(__file__).resolve().parent / "project_tests"


def _learner() -> Learner:
    return Learner.local()


def _matches_query(query: str, *values: str) -> bool:
    """Word-start match so a search for RAG does not match 'average'."""
    pattern = re.compile(rf"(?<!\w){re.escape(query)}", re.IGNORECASE)
    return any(pattern.search(value or "") for value in values)


def _module_rows(learner: Learner) -> list[dict]:
    return [module_progress(learner, module) for module in AiModule.objects.all()]


def _stage_groups(rows: list[dict]) -> list[dict]:
    groups = []
    for value, label in STAGE_CHOICES:
        stage_rows = [row for row in rows if row["module"].stage == value]
        if not stage_rows:
            continue
        groups.append(
            {
                "key": value,
                "label": label,
                "rows": stage_rows,
                "lesson_total": sum(row["lesson_total"] for row in stage_rows),
                "completed": sum(row["completed_lessons"] for row in stage_rows),
                "weeks": sum(row["module"].duration_weeks for row in stage_rows),
            }
        )
    return groups


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    stats = overall_stats(learner)
    rows = stats["module_rows"]
    stages = _stage_groups(rows)
    projects = project_list(learner)[:3]
    return render(
        request,
        "ai_academy/home.html",
        {
            "stats": stats,
            "stages": stages,
            "next": next_lesson(learner),
            "featured_projects": projects,
            "recent_attempts": AiAttempt.objects.filter(
                learner=learner, completed_at__isnull=False
            ).select_related("module")[:3],
            "role_paths": ROLE_PATHS,
            "active_nav": "ai_home",
            "page_title": "AI Academy",
        },
    )


@require_GET
def path(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    stats = overall_stats(learner)
    rows = stats["module_rows"]
    return render(
        request,
        "ai_academy/path.html",
        {
            "stats": stats,
            "stages": _stage_groups(rows),
            "projects": project_list(learner),
            "plan": TWELVE_MONTH_PLAN,
            "active_nav": "ai_path",
            "page_title": "The 12-month path",
        },
    )


@require_GET
def module_detail(request: HttpRequest, module_slug: str) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(
        AiModule.objects.prefetch_related("lessons", "flashcards", "projects"),
        slug=module_slug,
    )
    return render(
        request,
        "ai_academy/module.html",
        {
            "module": module,
            "progress": module_progress(learner, module),
            "cards": flashcard_progress(learner, module),
            "projects": project_list(learner),
            "attempts": AiAttempt.objects.filter(
                learner=learner, module=module, completed_at__isnull=False
            ).order_by("-started_at")[:5],
            "active_nav": "ai_path",
            "page_title": module.title,
        },
    )


@require_GET
def lesson_detail(
    request: HttpRequest, module_slug: str, lesson_slug: str
) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(AiModule, slug=module_slug)
    lesson = get_object_or_404(
        AiLesson.objects.select_related("module"), module=module, slug=lesson_slug
    )
    lessons = list(module.lessons.all())
    index = lessons.index(lesson)
    completed = AiLessonProgress.objects.filter(
        learner=learner, lesson=lesson
    ).exists()
    completed_ids = set(
        AiLessonProgress.objects.filter(
            learner=learner, lesson__module=module
        ).values_list("lesson_id", flat=True)
    )
    return render(
        request,
        "ai_academy/lesson.html",
        {
            "module": module,
            "lesson": lesson,
            "lessons": lessons,
            "completed_ids": completed_ids,
            "completed": completed,
            "previous_lesson": lessons[index - 1] if index > 0 else None,
            "following_lesson": lessons[index + 1] if index + 1 < len(lessons) else None,
            "lesson_number": index + 1,
            "active_nav": "ai_path",
            "page_title": lesson.title,
        },
    )


@require_POST
def complete_lesson(
    request: HttpRequest, module_slug: str, lesson_slug: str
) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(AiModule, slug=module_slug)
    lesson = get_object_or_404(AiLesson, module=module, slug=lesson_slug)
    _, created = AiLessonProgress.objects.get_or_create(
        learner=learner, lesson=lesson
    )
    if created:
        messages.success(request, f"Lesson complete: {lesson.title}.")
    else:
        messages.info(request, "You already completed this lesson.")

    if request.POST.get("next") == "1":
        lessons = list(module.lessons.all())
        index = lessons.index(lesson)
        if index + 1 < len(lessons):
            return redirect(
                "ai_academy:lesson",
                module_slug=module.slug,
                lesson_slug=lessons[index + 1].slug,
            )
    return redirect("ai_academy:module", module_slug=module.slug)


@require_POST
def quiz_start(request: HttpRequest, module_slug: str) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(AiModule, slug=module_slug)
    question_ids = list(module.questions.values_list("id", flat=True))
    if not question_ids:
        messages.error(request, "This module has no questions yet.")
        return redirect("ai_academy:module", module_slug=module.slug)
    random.shuffle(question_ids)
    attempt = AiAttempt.objects.create(
        learner=learner, module=module, length=len(question_ids)
    )
    AiAttemptQuestion.objects.bulk_create(
        [
            AiAttemptQuestion(attempt=attempt, question_id=question_id, position=index)
            for index, question_id in enumerate(question_ids)
        ]
    )
    return redirect("ai_academy:quiz", attempt_id=attempt.pk)


@require_http_methods(["GET", "POST"])
def quiz(request: HttpRequest, attempt_id: int) -> HttpResponse:
    learner = _learner()
    attempt = get_object_or_404(
        AiAttempt.objects.select_related("module", "learner"),
        pk=attempt_id,
        learner=learner,
    )
    if attempt.completed_at:
        return redirect("ai_academy:quiz_results", attempt_id=attempt.pk)

    attempt_question = attempt.current_attempt_question()
    if attempt_question is None:
        attempt.completed_at = timezone.now()
        attempt.save(update_fields=["completed_at"])
        return redirect("ai_academy:quiz_results", attempt_id=attempt.pk)

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
                choice = next((item for item in choices if item.pk == choice_id), None)
                if choice is None:
                    messages.error(request, "That answer does not belong to this question.")
                else:
                    if attempt_question.selected_id is None:
                        attempt_question.selected = choice
                        attempt_question.is_correct = choice.is_correct
                        attempt_question.answered_at = timezone.now()
                        attempt_question.save(
                            update_fields=["selected", "is_correct", "answered_at"]
                        )
                    return redirect(
                        f"{attempt.get_absolute_url()}?checked=1"
                    )
        elif action == "next":
            if attempt_question.selected_id is None:
                messages.error(request, "Choose an answer first.")
            elif attempt.current_index + 1 >= attempt.length:
                attempt.completed_at = timezone.now()
                attempt.save(update_fields=["completed_at"])
                return redirect("ai_academy:quiz_results", attempt_id=attempt.pk)
            else:
                attempt.current_index += 1
                attempt.save(update_fields=["current_index"])
                return redirect("ai_academy:quiz", attempt_id=attempt.pk)
        else:
            messages.error(request, "Unknown action.")
        attempt_question.refresh_from_db()

    selected = next(
        (choice for choice in choices if attempt_question.selected_id == choice.pk),
        None,
    )
    correct_choice = next((choice for choice in choices if choice.is_correct), None)
    answered = attempt_question.selected_id is not None
    return render(
        request,
        "ai_academy/quiz.html",
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
            "progress_percent": round(
                100 * (attempt.current_index + 1) / attempt.length
            ),
            "active_nav": "ai_path",
            "page_title": f"Quiz · {attempt.module.title}",
        },
    )


@require_GET
def quiz_results(request: HttpRequest, attempt_id: int) -> HttpResponse:
    learner = _learner()
    attempt = get_object_or_404(
        AiAttempt.objects.select_related("module", "learner"),
        pk=attempt_id,
        learner=learner,
    )
    if not attempt.completed_at:
        if attempt.answered_count >= attempt.length:
            attempt.completed_at = timezone.now()
            attempt.save(update_fields=["completed_at"])
        else:
            return redirect("ai_academy:quiz", attempt_id=attempt.pk)
    rows = list(
        attempt.attempt_questions.select_related(
            "question", "question__module", "selected"
        ).prefetch_related("question__choices")
    )
    missed = [row for row in rows if not row.is_correct]
    return render(
        request,
        "ai_academy/quiz_results.html",
        {
            "attempt": attempt,
            "rows": rows,
            "missed": missed,
            "active_nav": "ai_path",
            "page_title": f"Result · {attempt.module.title}",
        },
    )


@require_GET
def projects(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    return render(
        request,
        "ai_academy/projects.html",
        {
            "rows": project_list(learner),
            "stats": overall_stats(learner),
            "active_nav": "ai_projects",
            "page_title": "Projects",
        },
    )


@require_GET
def project_detail(request: HttpRequest, slug: str) -> HttpResponse:
    learner = _learner()
    project = get_object_or_404(
        AiProject.objects.select_related("module"), slug=slug
    )
    return render(
        request,
        "ai_academy/project.html",
        {
            "project": project,
            "progress": project_progress(learner, project),
            "active_nav": "ai_projects",
            "page_title": project.title,
        },
    )


@require_GET
def project_test_pack(request: HttpRequest, slug: str) -> HttpResponse:
    """Download a ready-to-run pytest acceptance pack for a project."""
    project = get_object_or_404(AiProject, slug=slug)
    root = PROJECT_TEST_DIR / project.slug
    if not root.is_dir():
        raise Http404("No test pack is available for this project.")

    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            archive.write(
                path,
                arcname=f"{project.slug}-test-pack/{path.relative_to(root).as_posix()}",
            )
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="{project.slug}-test-pack.zip"'
    )
    response["Content-Length"] = str(len(buffer.getvalue()))
    return response


@require_POST
def project_complete(request: HttpRequest, slug: str) -> HttpResponse:
    learner = _learner()
    project = get_object_or_404(AiProject, slug=slug)
    completion, created = AiProjectCompletion.objects.update_or_create(
        learner=learner,
        project=project,
        defaults={
            "repo_url": request.POST.get("repo_url", "").strip(),
            "demo_url": request.POST.get("demo_url", "").strip(),
            "notes": request.POST.get("notes", "").strip(),
        },
    )
    if created:
        messages.success(request, f"Project shipped: {project.title}.")
    else:
        messages.info(request, "Project details updated.")
    return redirect("ai_academy:project", slug=project.slug)


@require_GET
def flashcards_index(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    return render(
        request,
        "ai_academy/flashcards_index.html",
        {
            "decks": flashcard_decks(learner),
            "stats": overall_stats(learner),
            "active_nav": "ai_cards",
            "page_title": "Concept cards",
        },
    )


def _study_context(request: HttpRequest, module: AiModule | None) -> dict:
    learner = _learner()
    queue = due_cards(learner, module)
    progress = flashcard_progress(learner, module)
    return {
        "module": module,
        "card": queue[0]["card"] if queue else None,
        "review": queue[0]["review"] if queue else None,
        "queue_remaining": len(queue),
        "progress": progress,
        "reveal": request.GET.get("reveal") == "1",
        "active_nav": "ai_cards",
        "page_title": "Concept cards",
    }


@require_GET
def flashcards_study(request: HttpRequest, module_slug: str) -> HttpResponse:
    module = get_object_or_404(AiModule, slug=module_slug)
    return render(request, "ai_academy/flashcards_study.html", _study_context(request, module))


@require_GET
def flashcards_review(request: HttpRequest) -> HttpResponse:
    return render(request, "ai_academy/flashcards_study.html", _study_context(request, None))


@require_POST
def flashcards_rate(
    request: HttpRequest, card_id: int, module_slug: str | None = None
) -> HttpResponse:
    learner = _learner()
    module = get_object_or_404(AiModule, slug=module_slug) if module_slug else None
    card = get_object_or_404(AiFlashcard.objects.select_related("module"), pk=card_id)
    if module and card.module_id != module.pk:
        messages.error(request, "That card belongs to another deck.")
        return redirect("ai_academy:flashcards_index")
    rating = request.POST.get("rating", "")
    if rating not in {"again", "hard", "good", "easy"}:
        messages.error(request, "Choose again, hard, good, or easy.")
    else:
        award_flashcard(learner, card, rating)
    if module:
        return redirect("ai_academy:flashcards", module_slug=module.slug)
    return redirect("ai_academy:flashcards_review")


@require_GET
def progress(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    stats = overall_stats(learner)
    return render(
        request,
        "ai_academy/progress.html",
        {
            "stats": stats,
            "projects": project_list(learner),
            "recent_attempts": AiAttempt.objects.filter(
                learner=learner, completed_at__isnull=False
            ).select_related("module")[:10],
            "active_nav": "ai_progress",
            "page_title": "Your progress",
        },
    )


@require_GET
def glossary(request: HttpRequest) -> HttpResponse:
    learner = _learner()
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    terms = AiTerm.objects.select_related("module")
    if query:
        terms = terms.filter(
            Q(term__icontains=query)
            | Q(definition__icontains=query)
            | Q(example__icontains=query)
        )
    if category:
        terms = terms.filter(category=category)
    categories = list(
        AiTerm.objects.values_list("category", flat=True).distinct().order_by("category")
    )
    return render(
        request,
        "ai_academy/glossary.html",
        {
            "terms": terms,
            "categories": categories,
            "query": query,
            "active_category": category,
            "term_total": AiTerm.objects.count(),
            "result_count": terms.count(),
            "stats": overall_stats(learner),
            "active_nav": "ai_glossary",
            "page_title": "AI glossary",
        },
    )


@require_GET
def search(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    searched = len(query) >= 2
    modules = AiModule.objects.none()
    lessons = AiLesson.objects.none()
    projects = AiProject.objects.none()
    terms = AiTerm.objects.none()
    counts = {"modules": 0, "lessons": 0, "projects": 0, "terms": 0}
    if searched:
        module_qs = AiModule.objects.filter(
            Q(title__icontains=query)
            | Q(subtitle__icontains=query)
            | Q(description__icontains=query)
        )
        lesson_qs = AiLesson.objects.filter(
            Q(title__icontains=query) | Q(summary__icontains=query)
        ).select_related("module")
        project_qs = AiProject.objects.filter(
            Q(title__icontains=query)
            | Q(tagline__icontains=query)
            | Q(scenario__icontains=query)
            | Q(build__icontains=query)
        ).select_related("module")
        term_qs = AiTerm.objects.filter(
            Q(term__icontains=query)
            | Q(definition__icontains=query)
            | Q(example__icontains=query)
        ).select_related("module")
        module_rows = [
            item
            for item in module_qs
            if _matches_query(query, item.title, item.subtitle, item.description)
        ]
        lesson_rows = [
            item
            for item in lesson_qs
            if _matches_query(query, item.title, item.summary)
        ]
        project_rows = [
            item
            for item in project_qs
            if _matches_query(query, item.title, item.tagline, item.scenario, item.build)
        ]
        term_rows = [
            item
            for item in term_qs
            if _matches_query(query, item.term, item.definition, item.example)
        ]
        counts = {
            "modules": len(module_rows),
            "lessons": len(lesson_rows),
            "projects": len(project_rows),
            "terms": len(term_rows),
        }
        modules = module_rows[:8]
        lessons = lesson_rows[:10]
        projects = project_rows[:8]
        terms = term_rows[:10]
    return render(
        request,
        "ai_academy/search.html",
        {
            "query": query,
            "searched": searched,
            "modules": modules,
            "lessons": lessons,
            "projects": projects,
            "terms": terms,
            "counts": counts,
            "total_count": sum(counts.values()),
            "term_total": AiTerm.objects.count(),
            "active_nav": "ai_search",
            "page_title": "Search AI Academy",
        },
    )


@require_GET
def python_cheatsheet(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "ai_academy/python_cheatsheet.html",
        {
            "active_nav": "ai_path",
            "page_title": "Python for AI cheat sheet",
        },
    )


@require_GET
def career(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "ai_academy/career.html",
        {
            "roles": ROLE_PATHS,
            "plan": TWELVE_MONTH_PLAN,
            "interview_topics": INTERVIEW_TOPICS,
            "active_nav": "ai_career",
            "page_title": "AI careers",
        },
    )
