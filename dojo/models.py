"""Domain models for Django Quest.

The app is intentionally single-learner: it runs locally and keeps one
persistent profile, so there is no sign-in wall between you and a quiz.
"""

from __future__ import annotations

from datetime import timedelta
from math import ceil

from django.db import models
from django.urls import reverse
from django.utils import timezone


DIFFICULTY_CHOICES = [
    ("beginner", "Beginner"),
    ("intermediate", "Intermediate"),
    ("advanced", "Advanced"),
]

RATING_CHOICES = [
    ("again", "Again"),
    ("hard", "Hard"),
    ("good", "Good"),
    ("easy", "Easy"),
]

EVENT_CHOICES = [
    ("quiz", "Quiz"),
    ("flashcard", "Flashcard"),
    ("bonus", "Bonus"),
]


class Learner(models.Model):
    """A local learner profile.

    A fresh profile is created on demand under a stable primary key. This keeps
    the experience frictionless for a personal learning app while still keeping
    every progress query scoped to a real database row.
    """

    name = models.CharField(max_length=60, default="Learner")
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def local(cls) -> "Learner":
        learner, _ = cls.objects.get_or_create(pk=1, defaults={"name": "Learner"})
        return learner

    @property
    def xp(self) -> int:
        return self.events.aggregate(total=models.Sum("xp"))["total"] or 0

    @property
    def level(self) -> dict:
        return level_from_xp(self.xp)

    def __str__(self) -> str:
        return self.name


class Topic(models.Model):
    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=80)
    tagline = models.CharField(max_length=160)
    description = models.TextField()
    glyph = models.CharField(max_length=4, help_text="Short typographic mark, e.g. { }")
    accent = models.CharField(max_length=7, default="#FFC857")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return f"{reverse('dojo:quiz_setup')}?topic={self.slug}"

    @property
    def question_count(self) -> int:
        return self.questions.filter(is_active=True).count()

    @property
    def flashcard_count(self) -> int:
        return self.flashcards.count()


class Question(models.Model):
    key = models.SlugField(max_length=100, unique=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    prompt = models.TextField()
    code = models.TextField(blank=True)
    explanation = models.TextField()
    explanation_code = models.TextField(blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["topic__order", "difficulty", "position", "pk"]
        indexes = [
            models.Index(fields=["topic", "difficulty", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"[{self.get_difficulty_display()}] {self.prompt[:70]}"

    @property
    def correct_choice(self) -> "Choice | None":
        return next((choice for choice in self.choices.all() if choice.is_correct), None)


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self) -> str:
        return self.text[:80]


class Attempt(models.Model):
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name="attempts")
    topic = models.ForeignKey(
        Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="attempts"
    )
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, blank=True)
    length = models.PositiveSmallIntegerField(default=10)
    current_index = models.PositiveSmallIntegerField(default=0)
    bonus_xp = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Attempt #{self.pk} · {self.scope_label}"

    @property
    def scope_label(self) -> str:
        return self.topic.name if self.topic else "All topics"

    @property
    def difficulty_label(self) -> str:
        if not self.difficulty:
            return "Mixed levels"
        return dict(DIFFICULTY_CHOICES).get(self.difficulty, self.difficulty.title())

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    @property
    def answered_count(self) -> int:
        return self.attempt_questions.exclude(selected__isnull=True).count()

    @property
    def correct_count(self) -> int:
        return self.attempt_questions.filter(is_correct=True).count()

    @property
    def score_percent(self) -> int:
        if not self.length:
            return 0
        return round(100 * self.correct_count / self.length)

    @property
    def progress_percent(self) -> int:
        if not self.length:
            return 0
        return min(100, round(100 * self.current_index / self.length))

    @property
    def xp_earned(self) -> int:
        return self.answered_count * 2 + self.correct_count * 8 + self.bonus_xp

    def current_attempt_question(self) -> "AttemptQuestion | None":
        return (
            self.attempt_questions.select_related("question", "question__topic")
            .filter(position=self.current_index)
            .first()
        )

    def get_absolute_url(self) -> str:
        return reverse("dojo:quiz_question", args=[self.pk])


class AttemptQuestion(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="attempt_questions")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    selected = models.ForeignKey(
        Choice, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_correct = models.BooleanField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "position"], name="unique_attempt_question_position"
            )
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id}:{self.position}"


class Flashcard(models.Model):
    key = models.SlugField(max_length=100, unique=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="flashcards")
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    front = models.TextField(help_text="The open question shown first.")
    front_code = models.TextField(blank=True)
    back = models.TextField(help_text="The answer revealed on the other side.")
    back_code = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["topic__order", "position", "pk"]
        indexes = [models.Index(fields=["topic", "difficulty"])]

    def __str__(self) -> str:
        return self.front[:70]

    def get_absolute_url(self) -> str:
        return reverse("dojo:flashcards_study", args=[self.topic.slug])


class FlashcardReview(models.Model):
    """Per-card spaced-repetition state.

    The scheduler is deliberately small and transparent: a rating sets the next
    due date using a gently modified SM-2-style interval. One review per card
    keeps the local SQLite database compact.
    """

    learner = models.ForeignKey(
        Learner, on_delete=models.CASCADE, related_name="flashcard_reviews"
    )
    flashcard = models.ForeignKey(
        Flashcard, on_delete=models.CASCADE, related_name="reviews"
    )
    repetitions = models.PositiveIntegerField(default=0)
    lapses = models.PositiveIntegerField(default=0)
    interval_days = models.PositiveIntegerField(default=0)
    ease = models.FloatField(default=2.5)
    due_date = models.DateField(default=timezone.localdate)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    last_rating = models.CharField(max_length=10, choices=RATING_CHOICES, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "flashcard"], name="unique_learner_flashcard_review"
            )
        ]
        indexes = [models.Index(fields=["learner", "due_date"])]

    def __str__(self) -> str:
        return f"{self.flashcard_id} due {self.due_date}"

    @property
    def is_due(self) -> bool:
        return self.due_date <= timezone.localdate()

    def review(self, rating: str) -> None:
        if rating not in dict(RATING_CHOICES):
            raise ValueError(f"Unknown flashcard rating: {rating!r}")

        today = timezone.localdate()
        interval = self.interval_days
        ease = self.ease

        if rating == "again":
            self.repetitions = 0
            self.lapses += 1
            interval = 1
            ease = max(1.3, ease - 0.2)
        elif rating == "hard":
            self.repetitions += 1
            interval = max(2, round(max(interval, 1) * 1.2))
            ease = max(1.3, ease - 0.15)
        elif rating == "good":
            self.repetitions += 1
            interval = 3 if self.repetitions == 1 else max(3, round(interval * ease))
        else:  # easy
            self.repetitions += 1
            interval = 7 if self.repetitions == 1 else max(7, round(interval * ease * 1.3))
            ease = min(3.2, ease + 0.15)

        self.ease = round(ease, 2)
        self.interval_days = int(interval)
        self.due_date = today + timedelta(days=self.interval_days)
        self.last_reviewed = timezone.now()
        self.last_rating = rating
        self.save(
            update_fields=[
                "repetitions",
                "lapses",
                "interval_days",
                "ease",
                "due_date",
                "last_reviewed",
                "last_rating",
            ]
        )


class StudyEvent(models.Model):
    """A tiny activity ledger used for XP, streaks and daily momentum."""

    learner = models.ForeignKey(Learner, on_delete=models.CASCADE, related_name="events")
    topic = models.ForeignKey(
        Topic, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    kind = models.CharField(max_length=20, choices=EVENT_CHOICES)
    xp = models.PositiveSmallIntegerField(default=0)
    occurred_on = models.DateField(default=timezone.localdate)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["learner", "occurred_on"])]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} +{self.xp} XP"


LEVELS = [
    (0, "Curious"),
    (150, "Apprentice"),
    (400, "Practitioner"),
    (800, "Craftsperson"),
    (1300, "Engineer"),
    (2000, "Architect"),
    (3000, "Djangoist"),
]


def level_from_xp(xp: int) -> dict:
    """Return level metadata without introducing a second source of truth."""
    xp = max(0, int(xp))
    index = 0
    for i, (threshold, _) in enumerate(LEVELS):
        if xp >= threshold:
            index = i
    current_threshold, title = LEVELS[index]
    next_threshold = LEVELS[index + 1][0] if index + 1 < len(LEVELS) else None
    if next_threshold is None:
        within = 100
    else:
        within = round(100 * (xp - current_threshold) / (next_threshold - current_threshold))
    return {
        "number": index + 1,
        "title": title,
        "xp": xp,
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "percent": min(100, max(0, within)),
        "to_next": max(0, (next_threshold or xp) - xp),
    }


def streak_for(learner: Learner, today=None) -> int:
    """Count consecutive active days, remaining alive until today ends."""
    today = today or timezone.localdate()
    dates = set(
        learner.events.filter(occurred_on__lte=today)
        .values_list("occurred_on", flat=True)
        .distinct()
    )
    if not dates:
        return 0
    cursor = today
    if cursor not in dates:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def days_until(target_date, today=None) -> int:
    today = today or timezone.localdate()
    return max(0, (target_date - today).days)


def percent(part: int, whole: int) -> int:
    if not whole:
        return 0
    return min(100, max(0, ceil(100 * part / whole)))


class Cheatsheet(models.Model):
    """A practical recipe for a recurring Django situation."""

    key = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=160)
    category = models.CharField(max_length=60)
    summary = models.TextField()
    when_to_use = models.TextField()
    code = models.TextField()
    language = models.CharField(max_length=20, default="python")
    pitfalls = models.TextField(blank=True)
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cheatsheets",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return f"{reverse('dojo:cheatsheets')}#recipe-{self.key}"


class AppBlueprint(models.Model):
    """A studied, real-world application shape — not a generated project."""

    COMPLEXITY_CHOICES = [
        ("starter", "Starter"),
        ("production", "Production"),
        ("ambitious", "Ambitious"),
    ]

    key = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=120)
    tagline = models.CharField(max_length=200)
    problem = models.TextField()
    complexity = models.CharField(
        max_length=20, choices=COMPLEXITY_CHOICES, default="production"
    )
    stack_notes = models.TextField()
    screens = models.TextField(help_text="One screen or flow per line.")
    structure = models.TextField(help_text="One app/module per line.")
    models_code = models.TextField()
    starter_code = models.TextField()
    checklist = models.TextField(help_text="One implementation step per line.")
    pitfalls = models.TextField(help_text="One production trap per line.")
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blueprints",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("dojo:blueprint_detail", args=[self.key])


class ReleaseSeries(models.Model):
    STATUS_CHOICES = [
        ("lts", "LTS"),
        ("stable", "Supported"),
        ("extended", "Extended support"),
        ("unsupported", "Unsupported"),
    ]

    series = models.CharField(max_length=20, unique=True)
    latest_version = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="stable")
    mainstream_ends = models.DateField(null=True, blank=True)
    extended_ends = models.DateField(null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "series"]

    def __str__(self) -> str:
        return f"Django {self.series}"


class ReleaseNote(models.Model):
    KIND_CHOICES = [
        ("security", "Security release"),
        ("patch", "Patch release"),
        ("feature", "Feature release"),
        ("lts", "LTS release"),
    ]

    version = models.CharField(max_length=80, unique=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    released_on = models.DateField()
    headline = models.CharField(max_length=200)
    summary = models.TextField()
    why_it_matters = models.TextField()
    action = models.TextField()
    source_url = models.URLField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "-released_on"]

    def __str__(self) -> str:
        return f"Django {self.version}"


class ArchitectureCase(models.Model):
    """A system-design lab: constraints first, reference architecture second."""

    COMPLEXITY_CHOICES = [
        ("production", "Production"),
        ("ambitious", "Ambitious"),
        ("expert", "Expert"),
    ]

    key = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=140)
    tagline = models.CharField(max_length=220)
    scenario = models.TextField()
    scale = models.CharField(max_length=120)
    complexity = models.CharField(
        max_length=20, choices=COMPLEXITY_CHOICES, default="production"
    )
    requirements = models.TextField(help_text="One requirement per line.")
    constraints = models.TextField(help_text="One constraint per line.")
    stack = models.TextField(help_text="One technology/role per line.")
    components = models.TextField(help_text="One component per line.")
    data_flow = models.TextField(help_text="One numbered flow step per line.")
    decisions = models.TextField(help_text="One important decision per line.")
    data_model_code = models.TextField()
    starter_code = models.TextField()
    failure_modes = models.TextField(help_text="One failure mode per line.")
    tradeoffs = models.TextField(help_text="One trade-off per line.")
    evolution = models.TextField(help_text="One evolution step per line.")
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="architecture_cases",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("dojo:architecture_case", args=[self.key])


class ContentSnapshot(models.Model):
    """Fingerprint of the JSON content used to seed this database."""

    fingerprint = models.CharField(max_length=64, unique=True)
    seeded_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.fingerprint[:12]


