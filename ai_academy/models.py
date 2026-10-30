"""Models for AI Academy — a guided path from AI foundations to job-ready projects."""

from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.urls import reverse
from django.utils import timezone


DIFFICULTY_CHOICES = [
    ("beginner", "Beginner"),
    ("intermediate", "Intermediate"),
    ("advanced", "Advanced"),
]

STAGE_CHOICES = [
    ("foundation", "Foundation"),
    ("core", "Core ML"),
    ("llm", "LLM Engineering"),
    ("production", "Production & Career"),
]

RATING_CHOICES = [
    ("again", "Again"),
    ("hard", "Hard"),
    ("good", "Good"),
    ("easy", "Easy"),
]


def percent(part: int, whole: int) -> int:
    if not whole:
        return 0
    return min(100, max(0, round(100 * part / whole)))


class AiModule(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=160)
    subtitle = models.CharField(max_length=240)
    description = models.TextField()
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default="foundation")
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="beginner"
    )
    glyph = models.CharField(max_length=4, default="AI")
    accent = models.CharField(max_length=7, default="#8B5CF6")
    duration_weeks = models.PositiveSmallIntegerField(default=4)
    outcomes = models.TextField(help_text="One learning outcome per line.")
    skills = models.TextField(help_text="One job-relevant skill per line.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("ai_academy:module", args=[self.slug])

    @property
    def lesson_count(self) -> int:
        return self.lessons.count()

    @property
    def question_count(self) -> int:
        return self.questions.count()

    @property
    def card_count(self) -> int:
        return self.flashcards.count()

    @property
    def outcome_list(self) -> list[str]:
        return [line.strip() for line in self.outcomes.splitlines() if line.strip()]

    @property
    def skill_list(self) -> list[str]:
        return [line.strip() for line in self.skills.splitlines() if line.strip()]


class AiTerm(models.Model):
    key = models.SlugField(max_length=110, unique=True)
    term = models.CharField(max_length=120)
    category = models.CharField(max_length=40)
    definition = models.TextField()
    example = models.TextField(blank=True)
    module = models.ForeignKey(
        AiModule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="terms",
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "term"]

    def __str__(self) -> str:
        return self.term


class AiLesson(models.Model):
    module = models.ForeignKey(
        AiModule, on_delete=models.CASCADE, related_name="lessons"
    )
    slug = models.SlugField(max_length=110)
    title = models.CharField(max_length=200)
    summary = models.TextField()
    body_html = models.TextField(help_text="Trusted lesson HTML.")
    takeaways = models.TextField(
        blank=True, help_text="One key takeaway per line, shown after the lesson."
    )
    practice = models.TextField(
        blank=True, help_text="A small exercise the learner should do after reading."
    )
    minutes = models.PositiveSmallIntegerField(default=15)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["module__order", "order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "slug"], name="unique_ai_lesson_slug_per_module"
            )
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def takeaway_list(self) -> list[str]:
        return [line.strip() for line in self.takeaways.splitlines() if line.strip()]

    def get_absolute_url(self) -> str:
        return reverse("ai_academy:lesson", args=[self.module.slug, self.slug])


class AiQuestion(models.Model):
    module = models.ForeignKey(
        AiModule, on_delete=models.CASCADE, related_name="questions"
    )
    key = models.SlugField(max_length=110, unique=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    prompt = models.TextField()
    code = models.TextField(blank=True)
    explanation = models.TextField()
    explanation_code = models.TextField(blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self) -> str:
        return self.prompt[:80]

    @property
    def correct_choice(self) -> "AiChoice | None":
        return next((choice for choice in self.choices.all() if choice.is_correct), None)


class AiChoice(models.Model):
    question = models.ForeignKey(
        AiQuestion, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self) -> str:
        return self.text[:80]


class AiLessonProgress(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="ai_lesson_progress"
    )
    lesson = models.ForeignKey(
        AiLesson, on_delete=models.CASCADE, related_name="progress"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "lesson"], name="unique_ai_learner_lesson"
            )
        ]

    def __str__(self) -> str:
        return f"{self.learner_id}:{self.lesson_id}"


class AiLessonNote(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="ai_lesson_notes"
    )
    lesson = models.ForeignKey(
        AiLesson, on_delete=models.CASCADE, related_name="notes"
    )
    body = models.TextField(blank=True)
    is_bookmarked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "lesson"], name="unique_ai_note_learner_lesson"
            )
        ]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.learner_id}:{self.lesson_id}"


class AiAttempt(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="ai_attempts"
    )
    module = models.ForeignKey(
        AiModule, on_delete=models.CASCADE, related_name="attempts"
    )
    length = models.PositiveSmallIntegerField(default=6)
    current_index = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"AI attempt #{self.pk} · {self.module.title}"

    @property
    def answered_count(self) -> int:
        return self.attempt_questions.exclude(selected__isnull=True).count()

    @property
    def correct_count(self) -> int:
        return self.attempt_questions.filter(is_correct=True).count()

    @property
    def score_percent(self) -> int:
        return percent(self.correct_count, self.length)

    def current_attempt_question(self) -> "AiAttemptQuestion | None":
        return (
            self.attempt_questions.select_related("question", "question__module")
            .filter(position=self.current_index)
            .first()
        )

    def get_absolute_url(self) -> str:
        return reverse("ai_academy:quiz", args=[self.pk])


class AiAttemptQuestion(models.Model):
    attempt = models.ForeignKey(
        AiAttempt, on_delete=models.CASCADE, related_name="attempt_questions"
    )
    question = models.ForeignKey(AiQuestion, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    selected = models.ForeignKey(
        AiChoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_correct = models.BooleanField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "position"],
                name="unique_ai_attempt_question_position",
            )
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id}:{self.position}"


class AiFlashcard(models.Model):
    module = models.ForeignKey(
        AiModule, on_delete=models.CASCADE, related_name="flashcards"
    )
    key = models.SlugField(max_length=110, unique=True)
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="beginner"
    )
    front = models.TextField()
    back = models.TextField()
    front_code = models.TextField(blank=True)
    back_code = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["module__order", "position", "pk"]

    def __str__(self) -> str:
        return self.front[:80]

    def get_absolute_url(self) -> str:
        return reverse("ai_academy:flashcards", args=[self.module.slug])


class AiFlashcardReview(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="ai_flashcard_reviews"
    )
    flashcard = models.ForeignKey(
        AiFlashcard, on_delete=models.CASCADE, related_name="reviews"
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
                fields=["learner", "flashcard"], name="unique_ai_learner_flashcard"
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
            raise ValueError(f"Unknown rating: {rating!r}")
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
        else:
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


class AiProject(models.Model):
    module = models.ForeignKey(
        AiModule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    slug = models.SlugField(max_length=110, unique=True)
    title = models.CharField(max_length=200)
    tagline = models.CharField(max_length=260)
    scenario = models.TextField()
    build = models.TextField()
    hints = models.TextField(
        blank=True, help_text="One progressive hint per line, hidden on the page."
    )
    solution_html = models.TextField(
        blank=True, help_text="Trusted reference solution HTML, hidden by default."
    )
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default="beginner"
    )
    duration_hours = models.PositiveSmallIntegerField(default=8)
    skills = models.TextField(help_text="One skill per line.")
    deliverables = models.TextField(help_text="One deliverable per line.")
    milestones = models.TextField(help_text="One milestone per line.")
    rubric = models.TextField(help_text="One rubric criterion per line.")
    stretch = models.TextField(help_text="One stretch goal per line.")
    portfolio_note = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("ai_academy:project", args=[self.slug])

    def _lines(self, value: str) -> list[str]:
        return [line.strip() for line in value.splitlines() if line.strip()]

    @property
    def hint_list(self) -> list[str]:
        return self._lines(self.hints)

    @property
    def skill_list(self) -> list[str]:
        return self._lines(self.skills)

    @property
    def deliverable_list(self) -> list[str]:
        return self._lines(self.deliverables)

    @property
    def milestone_list(self) -> list[str]:
        return self._lines(self.milestones)

    @property
    def rubric_list(self) -> list[str]:
        return self._lines(self.rubric)

    @property
    def stretch_list(self) -> list[str]:
        return self._lines(self.stretch)


class AiProjectCompletion(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="ai_project_completions"
    )
    project = models.ForeignKey(
        AiProject, on_delete=models.CASCADE, related_name="completions"
    )
    repo_url = models.URLField(blank=True)
    demo_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "project"], name="unique_ai_learner_project"
            )
        ]

    def __str__(self) -> str:
        return f"{self.learner_id}:{self.project_id}"


class AiContentSnapshot(models.Model):
    fingerprint = models.CharField(max_length=64, unique=True)
    seeded_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.fingerprint[:12]
