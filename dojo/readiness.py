"""Compute a practical Django readiness report from local learning evidence."""

from __future__ import annotations

from django.utils import timezone

from .models import (
    DjangoCapstoneProgress,
    DjangoInterviewPractice,
    DjangoTrackProgress,
    HandbookExplanation,
    HandbookLabProgress,
    HandbookProgress,
    Learner,
)
from .services import topic_progress

RATING_SCORE = {"shaky": 25, "okay": 60, "solid": 100}

AREAS = (
    {
        "key": "orm",
        "name": "ORM & data",
        "topics": ("models-orm", "data-domain-modeling"),
        "labs": ("paginated-search", "transaction-stock"),
        "interview": ("ORM", "Migrations"),
        "chapters": (
            "models",
            "orm",
            "orm-expressions",
            "transactions-locking",
            "models-advanced",
            "data-domain-modeling",
        ),
    },
    {
        "key": "forms",
        "name": "Forms & views",
        "topics": ("views-forms-templates", "django-fundamentals"),
        "labs": ("contact-form", "modelform-crud", "template-tag"),
        "interview": ("Forms", "Views", "Templates"),
        "chapters": (
            "forms",
            "forms-advanced",
            "views",
            "views-advanced",
            "templates",
            "templates-advanced",
        ),
    },
    {
        "key": "auth",
        "name": "Auth & security",
        "topics": ("auth-security-testing", "security-architecture"),
        "labs": ("auth-permissions", "file-upload"),
        "interview": ("Auth", "Security"),
        "chapters": (
            "auth",
            "auth-advanced",
            "security",
            "security-hardening",
            "security-architecture",
        ),
    },
    {
        "key": "testing",
        "name": "Testing",
        "topics": ("auth-security-testing",),
        "labs": (),
        "interview": ("Testing",),
        "chapters": ("testing", "testing-advanced"),
    },
    {
        "key": "api",
        "name": "APIs & DRF",
        "topics": ("apis-drf",),
        "labs": ("drf-endpoint",),
        "interview": ("API", "DRF"),
        "chapters": ("drf", "drf-advanced"),
    },
    {
        "key": "deploy",
        "name": "Deployment & ops",
        "topics": (
            "performance-async-deploy",
            "platform-engineering",
            "distributed-reliability",
        ),
        "labs": ("cached-dashboard", "management-command"),
        "interview": ("Deployment", "Performance"),
        "chapters": (
            "deploy",
            "deploy-hardening",
            "performance",
            "caching-deep",
            "async-deep",
            "observability",
        ),
    },
    {
        "key": "architecture",
        "name": "Architecture",
        "topics": ("architecture-saas", "architecture-boundaries"),
        "labs": (),
        "interview": ("Architecture",),
        "chapters": ("architecture-patterns", "internals", "multi-tenancy"),
    },
)


def _average(values: list[int]) -> int | None:
    return round(sum(values) / len(values)) if values else None


def build_readiness(learner: Learner) -> dict:
    topic_rows = {row["topic"].slug: row for row in topic_progress(learner)}
    labs = set(
        HandbookLabProgress.objects.filter(
            learner=learner, completed_at__isnull=False
        ).values_list("lab_slug", flat=True)
    )
    explanations = {
        item.chapter_slug: item
        for item in HandbookExplanation.objects.filter(learner=learner)
    }
    interview = {
        item.question_slug: item
        for item in DjangoInterviewPractice.objects.filter(
            learner=learner, rating__isnull=False
        ).exclude(rating="")
    }
    interview_categories: dict[str, list[int]] = {}
    for question in _interview_questions():
        practice = interview.get(question["slug"])
        if practice:
            interview_categories.setdefault(question["category"], []).append(
                RATING_SCORE.get(practice.rating, 0)
            )

    areas = []
    for area in AREAS:
        components = {}

        quiz_values = [
            topic_rows[slug]["mastery"]
            for slug in area["topics"]
            if slug in topic_rows
        ]
        components["quiz"] = _average(quiz_values)

        if area["labs"]:
            components["labs"] = round(
                100 * sum(1 for slug in area["labs"] if slug in labs) / len(area["labs"])
            )
        else:
            components["labs"] = None

        ratings = [
            RATING_SCORE[explanations[slug].rating]
            for slug in area["chapters"]
            if slug in explanations and explanations[slug].rating in RATING_SCORE
        ]
        components["teach_back"] = _average(ratings)

        values = [
            score
            for values in [
                interview_categories.get(category, []) for category in area["interview"]
            ]
            for score in values
        ]
        components["interview"] = _average(values)

        available = [value for value in components.values() if value is not None]
        score = round(
            sum(
                value * weight
                for key, value, weight in (
                    ("quiz", components["quiz"], 0.35),
                    ("labs", components["labs"], 0.25),
                    ("teach_back", components["teach_back"], 0.25),
                    ("interview", components["interview"], 0.15),
                )
                if value is not None
            )
            / sum(
                weight
                for key, value, weight in (
                    ("quiz", components["quiz"], 0.35),
                    ("labs", components["labs"], 0.25),
                    ("teach_back", components["teach_back"], 0.25),
                    ("interview", components["interview"], 0.15),
                )
                if value is not None
            )
        ) if available else 0

        weakest = min(
            ((key, value) for key, value in components.items() if value is not None),
            key=lambda item: item[1],
            default=("quiz", 0),
        )
        action = {
            "quiz": "Run a quiz on this area.",
            "labs": "Complete a lab in this area.",
            "teach_back": "Explain a chapter from this area.",
            "interview": "Practise an interview question in this area.",
        }[weakest[0]]
        areas.append(
            {
                "key": area["key"],
                "name": area["name"],
                "score": score,
                "components": components,
                "weakest": weakest[0],
                "action": action,
                "evidence": any(value is not None for value in components.values()),
            }
        )

    active = [area["score"] for area in areas if area["evidence"]]
    overall = round(sum(active) / len(active)) if active else 0
    if overall >= 80:
        band = "Interview-ready"
    elif overall >= 60:
        band = "Solid foundation"
    elif overall >= 35:
        band = "Building"
    else:
        band = "Start with the basics"
    return {
        "areas": areas,
        "overall": overall,
        "band": band,
        "labs_completed": len(labs),
        "explanations": len(explanations),
        "interview_rated": len(interview),
        "capstone_phases": sum(
            len(row.completed_phases or [])
            for row in DjangoCapstoneProgress.objects.filter(learner=learner)
        ),
        "tracks_completed": DjangoTrackProgress.objects.filter(
            learner=learner, completed_at__isnull=False
        ).count(),
        "chapters_read": HandbookProgress.objects.filter(
            learner=learner, is_read=True
        ).count(),
        "generated_on": timezone.localdate(),
    }


def _interview_questions() -> tuple[dict, ...]:
    from .interview import load_interview_questions

    return load_interview_questions()
