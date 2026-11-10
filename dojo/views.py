from __future__ import annotations

from datetime import date, timedelta

import django
from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .field_guide import load_releases
from .forms import QuizSetupForm
from .handbook import (
    LEVELS,
    SEARCH_KINDS,
    COVERAGE_GAPS,
    categories as handbook_categories,
    chapter_hits,
    chapter_map,
    chapter_markdown,
    filter_hits,
    level_summary,
    load_chapters,
    search_handbook,
    suggest_terms,
    traceback_hits,
)
from .capstone import load_capstone
from .labs import lab_for_chapter, lab_map, load_labs
from .tracks import load_tracks, track_map
from .models import (
    AppBlueprint,
    ArchitectureCase,
    Attempt,
    Cheatsheet,
    DIFFICULTY_CHOICES,
    Flashcard,
    HandbookProgress,
    HandbookNote,
    HandbookExplanation,
    HandbookFeedback,
    HandbookLabProgress,
    HandbookSearchLog,
    DjangoCapstoneProgress,
    DjangoFeature,
    DjangoTrackProgress,
    Learner,
    Question,
    ReleaseNote,
    ReleaseSeries,
    StudyNote,
    Topic,
)
from .services import (
    achievements,
    activities,
    award_flashcard,
    complete_attempt,
    create_attempt,
    create_attempt_from_questions,
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
    handbook_matches: list[dict] = []
    counts = {
        "topics": 0,
        "questions": 0,
        "cards": 0,
        "recipes": 0,
        "blueprints": 0,
        "cases": 0,
        "releases": 0,
        "handbook": 0,
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
        all_handbook_matches = chapter_hits(query, limit=200)

        counts = {
            "topics": topic_qs.count(),
            "questions": question_qs.count(),
            "cards": card_qs.count(),
            "recipes": recipe_qs.count(),
            "blueprints": blueprint_qs.count(),
            "cases": case_qs.count(),
            "releases": release_qs.count(),
            "handbook": len(all_handbook_matches),
        }
        topics = topic_qs[:8]
        questions = question_qs[:10]
        cards = card_qs[:8]
        recipes = recipe_qs[:8]
        blueprints = blueprint_qs[:8]
        cases = case_qs[:8]
        releases = release_qs[:8]
        handbook_matches = all_handbook_matches[:6]

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
            "handbook_matches": handbook_matches,
            "counts": counts,
            "total_count": sum(counts.values()),
            "topic_total": Topic.objects.count(),
            "active_nav": "search",
        },
    )


@require_GET
def handbook(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    level = request.GET.get("level", "").strip()
    if level not in LEVELS:
        level = ""
    kind = request.GET.get("kind", "").strip()
    if kind not in SEARCH_KINDS:
        kind = ""
    search_ready = len(query) >= 2
    raw_hits = search_handbook(query) if search_ready else []
    if search_ready and not raw_hits:
        _log_handbook_gap(query)
    hits = filter_hits(raw_hits, level=level, kind=kind)
    suggestions = suggest_terms(query) if search_ready and not raw_hits else []
    chapters = load_chapters()
    visible_chapters = [chapter for chapter in chapters if not level or chapter["level"] == level]
    learner = Learner.local()
    progress_rows = list(HandbookProgress.objects.filter(learner=learner))
    by_slug = chapter_map()
    read_slugs = {row.chapter_slug for row in progress_rows if row.is_read}
    bookmarked_chapters = [
        by_slug[row.chapter_slug]
        for row in progress_rows
        if row.is_bookmarked and row.chapter_slug in by_slug
    ]
    continue_chapter = None
    for row in progress_rows:
        if not row.is_read and row.chapter_slug in by_slug:
            continue_chapter = by_slug[row.chapter_slug]
            break
    return render(
        request,
        "dojo/handbook.html",
        {
            "query": query,
            "level": level,
            "kind": kind,
            "levels": level_summary(),
            "searched": bool(query),
            "too_short": 0 < len(query) < 2,
            "search_ready": search_ready,
            "hits": hits,
            "raw_hit_count": len(raw_hits),
            "filters_active": bool(level or kind),
            "suggestions": suggestions,
            "categories": handbook_categories(level or None),
            "visible_total": len(visible_chapters),
            "chapter_total": len(chapters),
            "section_total": sum(len(chapter["sections"]) for chapter in chapters),
            "error_total": sum(len(chapter["errors"]) for chapter in chapters),
            "read_count": len(read_slugs),
            "read_slugs": read_slugs,
            "bookmarked_chapters": bookmarked_chapters,
            "continue_chapter": continue_chapter,
            "active_nav": "handbook",
        },
    )


@require_GET
def handbook_coverage(request: HttpRequest) -> HttpResponse:
    chapters = load_chapters()
    rows = []
    for category in handbook_categories():
        category_chapters = category["chapters"]
        rows.append(
            {
                "name": category["name"],
                "chapters": len(category_chapters),
                "sections": sum(len(chapter["sections"]) for chapter in category_chapters),
                "tables": sum(
                    1
                    for chapter in category_chapters
                    for section in chapter["sections"]
                    if section["table"]
                ),
                "latest_review": max(chapter["reviewed_on"] for chapter in category_chapters),
            }
        )
    return render(
        request,
        "dojo/handbook_coverage.html",
        {
            "rows": rows,
            "levels": level_summary(),
            "chapter_total": len(chapters),
            "section_total": sum(len(chapter["sections"]) for chapter in chapters),
            "error_total": sum(len(chapter["errors"]) for chapter in chapters),
            "stale_chapters": [chapter for chapter in chapters if chapter["is_stale"]],
            "gaps": COVERAGE_GAPS,
            "active_nav": "handbook",
        },
    )


@require_GET
def handbook_versions(request: HttpRequest) -> HttpResponse:
    chapters = load_chapters()
    versions = ("5.2", "6.0", "6.1")
    rows = []
    for version in versions:
        version_tuple = tuple(int(part) for part in version.split("."))
        compatible = [
            chapter
            for chapter in chapters
            if chapter["django_min_tuple"] <= version_tuple <= chapter["django_max_tuple"]
        ]
        rows.append(
            {
                "version": version,
                "count": len(compatible),
                "chapters": compatible,
                "runtime": django.get_version().startswith(version + "."),
            }
        )
    return render(
        request,
        "dojo/handbook_versions.html",
        {
            "rows": rows,
            "chapter_total": len(chapters),
            "runtime_version": django.get_version(),
            "new_in_60": [
                chapter
                for chapter in chapters
                if chapter["django_min_tuple"] >= (6, 0)
            ],
            "not_in_61": [
                chapter
                for chapter in chapters
                if chapter["django_max_tuple"] < (6, 1)
            ],
            "active_nav": "handbook",
        },
    )


@require_GET
def handbook_upgrade(request: HttpRequest) -> HttpResponse:
    versions = ("5.2", "6.0", "6.1")
    source = request.GET.get("from", "5.2").strip()
    target = request.GET.get("to", "6.1").strip()
    if source not in versions:
        source = "5.2"
    if target not in versions:
        target = "6.1"
    source_tuple = tuple(int(part) for part in source.split("."))
    target_tuple = tuple(int(part) for part in target.split("."))
    chapters = load_chapters()
    not_compatible = [
        chapter
        for chapter in chapters
        if not (
            chapter["django_min_tuple"]
            <= target_tuple
            <= chapter["django_max_tuple"]
        )
    ]
    newer_than_target = [
        chapter
        for chapter in chapters
        if chapter["django_min_tuple"] > target_tuple
    ]
    ends_before_target = [
        chapter
        for chapter in chapters
        if chapter["django_max_tuple"] < target_tuple
    ]
    changed = [
        chapter
        for chapter in chapters
        if chapter["django_min_tuple"] > source_tuple
        or chapter["django_max_tuple"] < target_tuple
    ]
    return render(
        request,
        "dojo/handbook_upgrade.html",
        {
            "versions": versions,
            "source": source,
            "target": target,
            "source_tuple": source_tuple,
            "target_tuple": target_tuple,
            "not_compatible": not_compatible,
            "newer_than_target": newer_than_target,
            "ends_before_target": ends_before_target,
            "changed": changed,
            "release_notes": ReleaseNote.objects.filter(version=target),
            "stale_chapters": [chapter for chapter in chapters if chapter["is_stale"]],
            "chapter_total": len(chapters),
            "runtime_version": django.get_version(),
            "active_nav": "handbook",
            "page_title": "Upgrade assistant",
        },
    )


@require_GET
def handbook_capstone(request: HttpRequest) -> HttpResponse:
    capstone = load_capstone()
    progress = DjangoCapstoneProgress.objects.filter(
        learner=Learner.local(), capstone_slug=capstone["slug"]
    ).first()
    completed_phases = set(progress.completed_phases if progress else [])
    phases = [
        {**phase, "completed": phase["slug"] in completed_phases}
        for phase in capstone["phases"]
    ]
    done = sum(1 for phase in phases if phase["completed"])
    return render(
        request,
        "dojo/handbook_capstone.html",
        {
            "capstone": capstone,
            "phases": phases,
            "progress": progress,
            "done_count": done,
            "phase_count": len(phases),
            "ready": done == len(phases),
            "completed": bool(progress and progress.completed_at),
            "active_nav": "handbook",
            "page_title": capstone["title"],
        },
    )


@require_POST
def handbook_capstone_phase(request: HttpRequest, phase_slug: str) -> HttpResponse:
    capstone = load_capstone()
    phase = next(
        (item for item in capstone["phases"] if item["slug"] == phase_slug), None
    )
    if phase is None:
        raise Http404("Capstone phase not found")
    row, _ = DjangoCapstoneProgress.objects.get_or_create(
        learner=Learner.local(), capstone_slug=capstone["slug"]
    )
    completed = set(row.completed_phases or [])
    if phase_slug in completed:
        completed.remove(phase_slug)
        messages.info(request, "Phase marked unfinished.")
    else:
        completed.add(phase_slug)
        messages.success(request, "Phase complete.")
    row.completed_phases = sorted(completed)
    if len(completed) < len(capstone["phases"]):
        row.completed_at = None
    row.save(update_fields=["completed_phases", "completed_at", "updated_at"])
    return redirect(f"{reverse('dojo:handbook_capstone')}#phase-{phase_slug}")


@require_POST
def handbook_capstone_complete(request: HttpRequest) -> HttpResponse:
    capstone = load_capstone()
    row, _ = DjangoCapstoneProgress.objects.get_or_create(
        learner=Learner.local(), capstone_slug=capstone["slug"]
    )
    if set(row.completed_phases or []) != {phase["slug"] for phase in capstone["phases"]}:
        messages.error(request, "Complete every capstone phase first.")
        return redirect("dojo:handbook_capstone")
    if row.completed_at:
        row.completed_at = None
        messages.info(request, "Capstone marked unfinished.")
    else:
        row.completed_at = timezone.now()
        messages.success(request, "Capstone completed. That is a portfolio piece.")
    row.save(update_fields=["completed_at", "updated_at"])
    return redirect("dojo:handbook_capstone")


@require_POST
def handbook_capstone_evidence(request: HttpRequest) -> HttpResponse:
    capstone = load_capstone()
    row, _ = DjangoCapstoneProgress.objects.get_or_create(
        learner=Learner.local(), capstone_slug=capstone["slug"]
    )
    row.evidence_what = request.POST.get("evidence_what", "")[:4000].strip()
    row.evidence_decision = request.POST.get("evidence_decision", "")[:4000].strip()
    row.evidence_test = request.POST.get("evidence_test", "")[:4000].strip()
    row.evidence_url = request.POST.get("evidence_url", "")[:500].strip()
    row.save(
        update_fields=[
            "evidence_what",
            "evidence_decision",
            "evidence_test",
            "evidence_url",
            "updated_at",
        ]
    )
    messages.success(request, "Capstone portfolio evidence saved.")
    return redirect(f"{reverse('dojo:handbook_capstone')}#portfolio")


@require_GET
def handbook_capstone_evidence_export(request: HttpRequest) -> HttpResponse:
    capstone = load_capstone()
    row = DjangoCapstoneProgress.objects.filter(
        learner=Learner.local(), capstone_slug=capstone["slug"]
    ).first()
    lines = [f"# {capstone['title']} — capstone evidence", "", capstone["goal"], ""]
    if row:
        lines.extend(
            [
                f"Status: {'completed' if row.completed_at else 'in progress'}",
                f"Phases: {len(row.completed_phases or [])}/{len(capstone['phases'])}",
                "",
            ]
        )
        for label, value in (
            ("What I built", row.evidence_what),
            ("Hardest decision", row.evidence_decision),
            ("Test proven", row.evidence_test),
            ("Evidence URL", row.evidence_url),
        ):
            if value:
                lines.extend([f"**{label}:** {value}", ""])
    response = HttpResponse(
        "\n".join(lines).rstrip() + "\n", content_type="text/markdown; charset=utf-8"
    )
    response["Content-Disposition"] = 'attachment; filename="django-capstone-evidence.md"'
    return response


@require_GET
def handbook_tracks(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    done_labs = set(
        HandbookLabProgress.objects.filter(
            learner=learner, completed_at__isnull=False
        ).values_list("lab_slug", flat=True)
    )
    progress_rows = {
        row.track_slug: row
        for row in DjangoTrackProgress.objects.filter(learner=learner)
    }
    rows = []
    for track in load_tracks():
        labs = [
            {**lab, "completed": lab["slug"] in done_labs}
            for lab in track["labs"]
        ]
        done = sum(1 for lab in labs if lab["completed"])
        progress = progress_rows.get(track["slug"])
        rows.append(
            {
                **track,
                "labs": labs,
                "done_count": done,
                "lab_count": len(labs),
                "ready": done == len(labs),
                "progress": progress,
                "completed": bool(progress and progress.completed_at),
            }
        )
    return render(
        request,
        "dojo/handbook_tracks.html",
        {
            "rows": rows,
            "completed_count": sum(1 for row in rows if row["completed"]),
            "track_total": len(rows),
            "active_nav": "handbook",
            "page_title": "Django Project Tracks",
        },
    )


@require_GET
def handbook_track(request: HttpRequest, slug: str) -> HttpResponse:
    track = track_map().get(slug)
    if track is None:
        raise Http404("Track not found")
    learner = Learner.local()
    done_labs = set(
        HandbookLabProgress.objects.filter(
            learner=learner, completed_at__isnull=False
        ).values_list("lab_slug", flat=True)
    )
    progress = DjangoTrackProgress.objects.filter(
        learner=learner, track_slug=slug
    ).first()
    labs = [
        {**lab, "completed": lab["slug"] in done_labs}
        for lab in track["labs"]
    ]
    done = sum(1 for lab in labs if lab["completed"])
    return render(
        request,
        "dojo/handbook_track.html",
        {
            "track": track,
            "labs": labs,
            "done_count": done,
            "lab_count": len(labs),
            "ready": done == len(labs),
            "progress": progress,
            "completed": bool(progress and progress.completed_at),
            "active_nav": "handbook",
            "page_title": track["title"],
        },
    )


@require_POST
def handbook_track_complete(request: HttpRequest, slug: str) -> HttpResponse:
    track = track_map().get(slug)
    if track is None:
        raise Http404("Track not found")
    learner = Learner.local()
    done = set(
        HandbookLabProgress.objects.filter(
            learner=learner, completed_at__isnull=False
        ).values_list("lab_slug", flat=True)
    )
    if not all(lab_slug in done for lab_slug in track["lab_slugs"]):
        messages.error(request, "Complete every lab in this track first.")
        return redirect("dojo:handbook_track", slug=slug)
    row, _ = DjangoTrackProgress.objects.get_or_create(
        learner=learner, track_slug=slug
    )
    if row.completed_at:
        row.completed_at = None
        row.save(update_fields=["completed_at", "updated_at"])
        messages.info(request, "Track marked unfinished.")
    else:
        row.completed_at = timezone.now()
        row.save(update_fields=["completed_at", "updated_at"])
        messages.success(request, "Track completed. A project is stronger than a checklist.")
    return redirect("dojo:handbook_track", slug=slug)


@require_POST
def handbook_track_evidence(request: HttpRequest, slug: str) -> HttpResponse:
    if slug not in track_map():
        raise Http404("Track not found")
    learner = Learner.local()
    row, _ = DjangoTrackProgress.objects.get_or_create(
        learner=learner, track_slug=slug
    )
    row.evidence_what = request.POST.get("evidence_what", "")[:4000].strip()
    row.evidence_decision = request.POST.get("evidence_decision", "")[:4000].strip()
    row.evidence_test = request.POST.get("evidence_test", "")[:4000].strip()
    row.evidence_url = request.POST.get("evidence_url", "")[:500].strip()
    row.save(
        update_fields=[
            "evidence_what",
            "evidence_decision",
            "evidence_test",
            "evidence_url",
            "updated_at",
        ]
    )
    messages.success(request, "Track evidence saved.")
    return redirect(f"{reverse('dojo:handbook_track', args=[slug])}#track-evidence")


@require_GET
def handbook_track_evidence_export(request: HttpRequest) -> HttpResponse:
    rows = {
        row.track_slug: row
        for row in DjangoTrackProgress.objects.filter(learner=Learner.local())
    }
    lines = ["# Django Project Tracks — evidence", ""]
    for track in load_tracks():
        row = rows.get(track["slug"])
        if not row or not row.has_evidence:
            continue
        lines.extend(
            [
                f"## {track['title']}",
                "",
                f"Status: {'completed' if row.completed_at else 'in progress'}",
                "",
            ]
        )
        if row.evidence_what:
            lines.extend([f"**What I built:** {row.evidence_what}", ""])
        if row.evidence_decision:
            lines.extend([f"**Hard decision:** {row.evidence_decision}", ""])
        if row.evidence_test:
            lines.extend([f"**Test added:** {row.evidence_test}", ""])
        if row.evidence_url:
            lines.extend([f"**Evidence:** {row.evidence_url}", ""])
    response = HttpResponse(
        "\n".join(lines).rstrip() + "\n", content_type="text/markdown; charset=utf-8"
    )
    response["Content-Disposition"] = 'attachment; filename="django-tracks-evidence.md"'
    return response


@require_GET
def django_features(request: HttpRequest) -> HttpResponse:
    features = list(DjangoFeature.objects.all())
    return render(
        request,
        "dojo/features.html",
        {
            "features": features,
            "feature_count": len(features),
            "new_count": sum(1 for feature in features if feature.is_new),
            "categories": list(dict.fromkeys(feature.category for feature in features)),
            "chapter_total": len(load_chapters()),
            "lab_total": len(load_labs()),
            "active_nav": "features",
            "page_title": "Django module features",
        },
    )


@require_GET
def handbook_labs(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    rows = list(HandbookLabProgress.objects.filter(learner=learner))
    completed = {row.lab_slug for row in rows if row.completed_at}
    evidence_slugs = {row.lab_slug for row in rows if row.has_evidence}
    labs = []
    by_slug = chapter_map()
    for lab in load_labs():
        labs.append(
            {
                **lab,
                "completed": lab["slug"] in completed,
                "has_evidence": lab["slug"] in evidence_slugs,
                "chapter": by_slug.get(lab["chapter_slug"]),
            }
        )
    return render(
        request,
        "dojo/handbook_labs.html",
        {
            "labs": labs,
            "completed_count": len(completed),
            "evidence_count": len(evidence_slugs),
            "lab_total": len(labs),
            "active_nav": "handbook",
            "page_title": "Django Labs",
        },
    )


@require_GET
def handbook_lab(request: HttpRequest, slug: str) -> HttpResponse:
    lab = lab_map().get(slug)
    if lab is None:
        raise Http404("Lab not found")
    chapter = chapter_map().get(lab["chapter_slug"])
    progress = HandbookLabProgress.objects.filter(
        learner=Learner.local(), lab_slug=slug
    ).first()
    completed = bool(progress and progress.completed_at)
    return render(
        request,
        "dojo/handbook_lab.html",
        {
            "lab": lab,
            "chapter": chapter,
            "progress": progress,
            "completed": completed,
            "active_nav": "handbook",
            "page_title": lab["title"],
        },
    )


@require_POST
def handbook_lab_complete(request: HttpRequest, slug: str) -> HttpResponse:
    if slug not in lab_map():
        raise Http404("Lab not found")
    learner = Learner.local()
    row, _ = HandbookLabProgress.objects.get_or_create(
        learner=learner, lab_slug=slug
    )
    if row.completed_at:
        row.completed_at = None
        row.save(update_fields=["completed_at", "updated_at"])
        messages.info(request, "Lab marked unfinished.")
    else:
        row.completed_at = timezone.now()
        row.save(update_fields=["completed_at", "updated_at"])
        messages.success(request, "Lab completed. Evidence beats a percentage.")
    return redirect("dojo:handbook_lab", slug=slug)


@require_POST
def handbook_lab_evidence(request: HttpRequest, slug: str) -> HttpResponse:
    if slug not in lab_map():
        raise Http404("Lab not found")
    learner = Learner.local()
    row, _ = HandbookLabProgress.objects.get_or_create(
        learner=learner, lab_slug=slug
    )
    row.evidence_what = request.POST.get("evidence_what", "")[:4000].strip()
    row.evidence_decision = request.POST.get("evidence_decision", "")[:4000].strip()
    row.evidence_test = request.POST.get("evidence_test", "")[:4000].strip()
    row.evidence_url = request.POST.get("evidence_url", "")[:500].strip()
    row.save(
        update_fields=[
            "evidence_what",
            "evidence_decision",
            "evidence_test",
            "evidence_url",
            "updated_at",
        ]
    )
    messages.success(request, "Lab evidence saved.")
    return redirect(f"{reverse('dojo:handbook_lab', args=[slug])}#evidence")


@require_GET
def handbook_lab_evidence_export(request: HttpRequest) -> HttpResponse:
    rows = {
        row.lab_slug: row
        for row in HandbookLabProgress.objects.filter(learner=Learner.local())
    }
    lines = ["# Django Labs — evidence", ""]
    for lab in load_labs():
        row = rows.get(lab["slug"])
        if not row or not row.has_evidence:
            continue
        lines.extend(
            [
                f"## {lab['title']}",
                "",
                f"Status: {'completed' if row.completed_at else 'in progress'}",
                "",
            ]
        )
        if row.evidence_what:
            lines.extend([f"**What I built:** {row.evidence_what}", ""])
        if row.evidence_decision:
            lines.extend([f"**Hard decision:** {row.evidence_decision}", ""])
        if row.evidence_test:
            lines.extend([f"**Test added:** {row.evidence_test}", ""])
        if row.evidence_url:
            lines.extend([f"**Evidence:** {row.evidence_url}", ""])
    response = HttpResponse(
        "\n".join(lines).rstrip() + "\n", content_type="text/markdown; charset=utf-8"
    )
    response["Content-Disposition"] = 'attachment; filename="django-labs-evidence.md"'
    return response


def _handbook_url(hit_or_suggestion: dict) -> str:
    chapter = hit_or_suggestion["chapter"]
    section = hit_or_suggestion.get("section")
    url = reverse("dojo:handbook_chapter", args=[chapter["slug"]])
    if section:
        url = f"{url}#{section['id']}"
    return url


def _log_handbook_gap(query: str) -> None:
    """Record a local zero-result query, merging repeats."""
    query = query.strip()[:200]
    if len(query) < 2:
        return
    row = HandbookSearchLog.objects.filter(query__iexact=query).first()
    if row is None:
        HandbookSearchLog.objects.create(query=query)
        return
    row.count += 1
    row.hits = 0
    row.save(update_fields=["count", "hits", "last_seen"])


@require_GET
def handbook_search(request: HttpRequest) -> HttpResponse:
    query = request.GET.get("q", "").strip()
    level = request.GET.get("level", "").strip()
    if level not in LEVELS:
        level = ""
    kind = request.GET.get("kind", "").strip()
    if kind not in SEARCH_KINDS:
        kind = ""
    raw_hits = search_handbook(query) if len(query) >= 2 else []
    if len(query) >= 2 and not raw_hits:
        _log_handbook_gap(query)
    hits = filter_hits(raw_hits, level=level, kind=kind)
    suggestions = suggest_terms(query) if len(query) >= 2 and not raw_hits else []
    results = []
    for hit in hits:
        chapter = hit["chapter"]
        section = hit["section"]
        results.append(
            {
                "kind": hit["kind"],
                "title": hit["title"],
                "chapter": chapter["title"],
                "chapter_number": chapter["number"],
                "category": chapter["category"],
                "level": chapter["level"],
                "section": section["title"] if section else "",
                "snippet": hit["snippet"],
                "url": _handbook_url(hit),
            }
        )
    return JsonResponse(
        {
            "query": query,
            "count": len(results),
            "raw_count": len(raw_hits),
            "filtered": bool(raw_hits and not hits),
            "results": results,
            "suggestions": [
                {
                    "term": suggestion["term"],
                    "chapter": suggestion["chapter"]["title"],
                    "url": _handbook_url(suggestion),
                }
                for suggestion in suggestions
            ],
        }
    )


@require_http_methods(["GET", "POST"])
def handbook_traceback(request: HttpRequest) -> HttpResponse:
    raw = ""
    terms: list[str] = []
    hits: list[dict] = []
    suggestions: list[dict] = []
    if request.method == "POST":
        raw = request.POST.get("traceback", "")[:20000].strip()
        if raw:
            terms, hits = traceback_hits(raw)
            if not hits and terms:
                suggestions = suggest_terms(terms[0])
    return render(
        request,
        "dojo/handbook_traceback.html",
        {
            "raw": raw,
            "terms": terms,
            "hits": hits,
            "suggestions": suggestions,
            "submitted": request.method == "POST",
            "active_nav": "handbook",
        },
    )


@require_GET
def handbook_chapter(request: HttpRequest, slug: str) -> HttpResponse:
    chapters = load_chapters()
    chapter = next((item for item in chapters if item["slug"] == slug), None)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    index = chapters.index(chapter)
    by_slug = chapter_map()
    related = [
        by_slug[related_slug]
        for related_slug in chapter["related"]
        if related_slug in by_slug
    ]
    practice_topic = None
    if chapter["quiz_topic"]:
        practice_topic = Topic.objects.filter(slug=chapter["quiz_topic"]).first()
    learner = Learner.local()
    progress, _ = HandbookProgress.objects.get_or_create(
        learner=learner, chapter_slug=slug
    )
    progress.save(update_fields=["last_seen_at"])
    section_notes = {
        note.section_id: note
        for note in HandbookNote.objects.filter(learner=learner, chapter_slug=slug)
    }
    feedback = HandbookFeedback.objects.filter(
        learner=learner, chapter_slug=slug
    ).first()
    explanation = HandbookExplanation.objects.filter(
        learner=learner, chapter_slug=slug
    ).first()
    chapter_lab = lab_for_chapter(slug)
    runtime_version = django.get_version()
    runtime_tuple = tuple(int(part) for part in runtime_version.split(".")[:2])
    version_warning = not (
        chapter["django_min_tuple"] <= runtime_tuple <= chapter["django_max_tuple"]
    )
    return render(
        request,
        "dojo/handbook_chapter.html",
        {
            "chapter": chapter,
            "previous_chapter": chapters[index - 1] if index > 0 else None,
            "next_chapter": chapters[index + 1] if index + 1 < len(chapters) else None,
            "related_chapters": related,
            "practice_topic": practice_topic,
            "progress": progress,
            "section_notes": section_notes,
            "feedback": feedback,
            "explanation": explanation,
            "chapter_lab": chapter_lab,
            "runtime_version": runtime_version,
            "version_warning": version_warning,
            "active_nav": "handbook",
        },
    )


@require_GET
def handbook_markdown(request: HttpRequest, slug: str) -> HttpResponse:
    chapter = chapter_map().get(slug)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    response = HttpResponse(
        chapter_markdown(chapter),
        content_type="text/markdown; charset=utf-8",
    )
    response["Content-Disposition"] = f'inline; filename="{slug}.md"'
    return response


@require_POST
def handbook_read(request: HttpRequest, slug: str) -> HttpResponse:
    chapter = next((item for item in load_chapters() if item["slug"] == slug), None)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    progress, _ = HandbookProgress.objects.get_or_create(
        learner=Learner.local(), chapter_slug=slug
    )
    progress.is_read = not progress.is_read
    progress.read_at = timezone.now() if progress.is_read else None
    progress.save(update_fields=["is_read", "read_at", "last_seen_at"])
    return redirect("dojo:handbook_chapter", slug=slug)


@require_POST
def handbook_bookmark(request: HttpRequest, slug: str) -> HttpResponse:
    chapter = next((item for item in load_chapters() if item["slug"] == slug), None)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    progress, _ = HandbookProgress.objects.get_or_create(
        learner=Learner.local(), chapter_slug=slug
    )
    progress.is_bookmarked = not progress.is_bookmarked
    progress.save(update_fields=["is_bookmarked", "last_seen_at"])
    return redirect("dojo:handbook_chapter", slug=slug)


@require_POST
def handbook_note(request: HttpRequest, slug: str, section_id: str) -> HttpResponse:
    chapter = chapter_map().get(slug)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    section = next(
        (item for item in chapter["sections"] if item["id"] == section_id), None
    )
    if section is None:
        raise Http404("Handbook section not found")
    body = request.POST.get("body", "")[:20000].strip()
    is_bookmarked = request.POST.get("bookmarked") == "on"
    learner = Learner.local()
    note = HandbookNote.objects.filter(
        learner=learner, chapter_slug=slug, section_id=section_id
    ).first()
    if not body and not is_bookmarked:
        if note:
            note.delete()
        messages.info(request, "Notatka usunięta.")
    else:
        HandbookNote.objects.update_or_create(
            learner=learner,
            chapter_slug=slug,
            section_id=section_id,
            defaults={"body": body, "is_bookmarked": is_bookmarked},
        )
        messages.success(request, "Notatka zapisana.")
    return redirect(f"{reverse('dojo:handbook_chapter', args=[slug])}#{section_id}")


@require_GET
def handbook_notes(request: HttpRequest) -> HttpResponse:
    by_slug = chapter_map()
    rows = []
    for note in HandbookNote.objects.filter(learner=Learner.local()):
        chapter = by_slug.get(note.chapter_slug)
        if chapter is None:
            continue
        section = next(
            (item for item in chapter["sections"] if item["id"] == note.section_id),
            None,
        )
        if section is None:
            continue
        rows.append({"note": note, "chapter": chapter, "section": section})
    return render(
        request,
        "dojo/handbook_notes.html",
        {
            "rows": rows,
            "active_nav": "handbook",
            "page_title": "Handbook notes",
        },
    )


@require_GET
def handbook_notes_export(request: HttpRequest) -> HttpResponse:
    by_slug = chapter_map()
    lines = ["# Django handbook notes", ""]
    current = None
    for note in HandbookNote.objects.filter(learner=Learner.local()):
        chapter = by_slug.get(note.chapter_slug)
        if chapter is None:
            continue
        section = next(
            (item for item in chapter["sections"] if item["id"] == note.section_id),
            None,
        )
        if section is None:
            continue
        if chapter["slug"] != current:
            current = chapter["slug"]
            lines.extend([f"## {chapter['title']}", ""])
        marker = "★ " if note.is_bookmarked else ""
        lines.extend([f"### {marker}{section['title']}", ""])
        lines.extend([note.body or "_Bookmarked section._", ""])
    response = HttpResponse(
        "\n".join(lines).rstrip() + "\n",
        content_type="text/markdown; charset=utf-8",
    )
    response["Content-Disposition"] = 'attachment; filename="django-handbook-notes.md"'
    return response


@require_POST
def handbook_checkpoint(request: HttpRequest, slug: str) -> HttpResponse:
    chapter = chapter_map().get(slug)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    if not chapter["quiz_topic"]:
        messages.error(request, "This chapter has no checkpoint yet.")
        return redirect("dojo:handbook_chapter", slug=slug)
    topic = Topic.objects.filter(slug=chapter["quiz_topic"]).first()
    if topic is None:
        messages.error(request, "The checkpoint topic is not available.")
        return redirect("dojo:handbook_chapter", slug=slug)
    question_ids = list(
        Question.objects.filter(topic=topic).values_list("id", flat=True)
    )
    try:
        attempt = create_attempt_from_questions(
            Learner.local(), question_ids, topic=topic, limit=3
        )
    except ValueError:
        messages.error(request, "This checkpoint has no questions yet.")
        return redirect("dojo:handbook_chapter", slug=slug)
    return redirect("dojo:quiz_question", attempt_id=attempt.pk)


@require_POST
def handbook_feedback(request: HttpRequest, slug: str) -> HttpResponse:
    chapter = chapter_map().get(slug)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    helpful = request.POST.get("helpful") == "yes"
    comment = request.POST.get("comment", "")[:4000].strip()
    HandbookFeedback.objects.update_or_create(
        learner=Learner.local(),
        chapter_slug=slug,
        defaults={"helpful": helpful, "comment": comment},
    )
    messages.success(request, "Feedback saved locally.")
    return redirect(f"{reverse('dojo:handbook_chapter', args=[slug])}#feedback")


@require_GET
def handbook_gaps_page(request: HttpRequest) -> HttpResponse:
    rows = HandbookSearchLog.objects.all()[:100]
    return render(
        request,
        "dojo/handbook_gaps.html",
        {
            "rows": rows,
            "active_nav": "handbook",
            "page_title": "Search gaps",
        },
    )


@require_POST
def handbook_gaps_clear(request: HttpRequest) -> HttpResponse:
    deleted = HandbookSearchLog.objects.all().delete()[0]
    messages.success(request, f"Cleared {deleted} logged search gap(s).")
    return redirect("dojo:handbook_gaps_page")


@require_POST
def handbook_explanation(request: HttpRequest, slug: str) -> HttpResponse:
    chapter = chapter_map().get(slug)
    if chapter is None:
        raise Http404("Handbook chapter not found")
    body = request.POST.get("body", "")[:12000].strip()
    rating = request.POST.get("rating", "")
    if rating not in {"shaky", "okay", "solid"}:
        rating = ""
    learner = Learner.local()
    existing = HandbookExplanation.objects.filter(
        learner=learner, chapter_slug=slug
    ).first()
    if not body and not rating:
        if existing:
            existing.delete()
        messages.info(request, "Explanation removed.")
    else:
        explanation, _ = HandbookExplanation.objects.update_or_create(
            learner=learner,
            chapter_slug=slug,
            defaults={
                "body": body,
                "rating": rating,
                "previous_body": existing.body if existing else "",
                "previous_rating": existing.rating if existing else "",
            },
        )
        interval = {"shaky": 1, "okay": 3, "solid": 14}.get(rating, 1)
        explanation.interval_days = interval
        explanation.repetitions = (existing.repetitions if existing else 0) + 1
        explanation.due_on = timezone.localdate() + timedelta(days=interval)
        explanation.save(update_fields=["interval_days", "repetitions", "due_on"])
        messages.success(request, "Explanation saved.")
    return redirect(f"{reverse('dojo:handbook_chapter', args=[slug])}#explain")


@require_GET
def handbook_explanations(request: HttpRequest) -> HttpResponse:
    rating = request.GET.get("rating", "")
    due_only = request.GET.get("due") == "1"
    today = timezone.localdate()
    by_slug = chapter_map()
    explanations = list(
        HandbookExplanation.objects.filter(learner=Learner.local())
    )
    if rating in {"shaky", "okay", "solid"}:
        explanations = [item for item in explanations if item.rating == rating]
    due_count = sum(1 for item in explanations if item.due_on <= today)
    if due_only:
        explanations = [item for item in explanations if item.due_on <= today]
    rank = {"shaky": 0, "okay": 1, "solid": 2, "": 3}
    rows = []
    for item in explanations:
        chapter = by_slug.get(item.chapter_slug)
        if chapter is None:
            continue
        rows.append({"explanation": item, "chapter": chapter})
    rows.sort(
        key=lambda row: (
            row["explanation"].due_on,
            rank.get(row["explanation"].rating, 3),
            -row["explanation"].updated_at.timestamp(),
        )
    )
    return render(
        request,
        "dojo/handbook_explanations.html",
        {
            "rows": rows,
            "rating": rating,
            "due_only": due_only,
            "due_count": due_count,
            "today": today,
            "counts": {
                key: sum(1 for item in explanations if item.rating == key)
                for key in ("shaky", "okay", "solid", "")
            },
            "active_nav": "handbook",
            "page_title": "Teach-back review",
        },
    )


@require_GET
def handbook_feedback_review(request: HttpRequest) -> HttpResponse:
    only_needs_work = request.GET.get("filtr") == "needs-work"
    by_slug = chapter_map()
    aggregate = (
        HandbookFeedback.objects.values("chapter_slug")
        .annotate(
            total=Count("id"),
            needs_work=Count("id", filter=Q(helpful=False)),
            helpful=Count("id", filter=Q(helpful=True)),
        )
        .order_by("-needs_work", "-total", "chapter_slug")
    )
    rows = []
    for item in aggregate:
        chapter = by_slug.get(item["chapter_slug"])
        if chapter is None:
            continue
        if only_needs_work and not item["needs_work"]:
            continue
        comments = list(
            HandbookFeedback.objects.filter(chapter_slug=item["chapter_slug"])
            .exclude(comment="")
            .order_by("-updated_at")[:5]
        )
        rows.append({**item, "chapter": chapter, "comments": comments})
    return render(
        request,
        "dojo/handbook_feedback_review.html",
        {
            "rows": rows,
            "only_needs_work": only_needs_work,
            "needs_work_total": sum(row["needs_work"] for row in rows),
            "feedback_total": sum(row["total"] for row in rows),
            "active_nav": "handbook",
            "page_title": "Feedback review",
        },
    )


@require_GET
def handbook_edit_next(request: HttpRequest) -> HttpResponse:
    chapters = load_chapters()
    feedback = {
        row["chapter_slug"]: row
        for row in HandbookFeedback.objects.values("chapter_slug").annotate(
            total=Count("id"),
            needs_work=Count("id", filter=Q(helpful=False)),
        )
    }
    latest_comments = {}
    for note in HandbookFeedback.objects.exclude(comment="").order_by("-updated_at"):
        latest_comments.setdefault(note.chapter_slug, note.comment)
    queries = list(HandbookSearchLog.objects.all()[:40])
    rows = []
    for chapter in chapters:
        reasons = []
        score = 0
        feedback_row = feedback.get(chapter["slug"])
        if feedback_row and feedback_row["needs_work"]:
            score += feedback_row["needs_work"] * 10
            reasons.append(
                f"{feedback_row['needs_work']} needs-work vote(s)"
            )
        if chapter["is_stale"]:
            score += 5
            reasons.append(f"reviewed {chapter['reviewed_on'].isoformat()}")
        if reasons:
            rows.append(
                {
                    "chapter": chapter,
                    "score": score,
                    "reasons": reasons,
                    "comment": latest_comments.get(chapter["slug"], ""),
                }
            )
    rows.sort(key=lambda row: (-row["score"], row["chapter"]["title"]))
    normalized = {
        chapter["slug"]: " ".join(
            [chapter["title"], " ".join(chapter["aliases"]), chapter["summary"]]
        ).casefold()
        for chapter in chapters
    }
    unmapped = [
        query
        for query in queries
        if not any(query.query.casefold() in text for text in normalized.values())
    ]
    return render(
        request,
        "dojo/handbook_edit_next.html",
        {
            "rows": rows,
            "unmapped": unmapped,
            "active_nav": "handbook",
            "page_title": "Edit next",
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
            "teach_back_due": HandbookExplanation.objects.filter(
                learner=learner, due_on__lte=timezone.localdate()
            ).count(),
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


@require_http_methods(["GET", "POST"])
def notes(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        body = request.POST.get("body", "").strip()
        topic_id = request.POST.get("topic") or None
        bookmarked = request.POST.get("bookmarked") == "on"
        if not title:
            messages.error(request, "Give the note a title.")
        else:
            topic = Topic.objects.filter(pk=topic_id).first() if topic_id else None
            StudyNote.objects.update_or_create(
                learner=learner,
                title=title,
                defaults={"body": body, "topic": topic, "is_bookmarked": bookmarked},
            )
            messages.success(request, "Note saved locally.")
        return redirect("dojo:notes")
    bookmarked_only = request.GET.get("bookmarked") == "1"
    rows = StudyNote.objects.filter(learner=learner).select_related("topic")
    if bookmarked_only:
        rows = rows.filter(is_bookmarked=True)
    return render(
        request,
        "dojo/notes.html",
        {
            "notes": rows,
            "topics": Topic.objects.all(),
            "bookmarked_only": bookmarked_only,
            "active_nav": "notes",
            "page_title": "Notes",
        },
    )


@require_POST
def delete_note(request: HttpRequest, note_id: int) -> HttpResponse:
    note = get_object_or_404(StudyNote, pk=note_id, learner=Learner.local())
    note.delete()
    messages.info(request, "Note deleted.")
    return redirect("dojo:notes")


@require_GET
def progress_export(request: HttpRequest) -> HttpResponse:
    learner = Learner.local()
    stats = dashboard_stats(learner)
    lines = [
        "# Django Quest progress",
        "",
        f"Generated: {timezone.localdate().isoformat()}",
        f"XP: {stats['xp']} · Level {stats['level']['number']} ({stats['level']['title']})",
        f"Streak: {stats['streak']} days",
        f"Quizzes completed: {stats['completed_attempts']} · accuracy {stats['accuracy']}%",
        f"Cards reviewed: {stats['reviewed_cards']}/{stats['total_cards']}",
        "",
        "## Topics",
    ]
    for row in stats["topics"]:
        lines.append(
            f"- {row['topic'].name}: {row['seen']}/{row['question_total']} seen, {row['accuracy']}% accuracy"
        )
    lines.extend(["", "Generated locally by Django Quest."])
    response = HttpResponse(
        "\n".join(lines) + "\n", content_type="text/markdown; charset=utf-8"
    )
    response["Content-Disposition"] = 'attachment; filename="django-quest-progress.md"'
    return response
