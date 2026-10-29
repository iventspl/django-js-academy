"""Modele polskiej akademii JavaScript → React → React Native."""

from __future__ import annotations

from datetime import timedelta
from math import ceil

from django.db import models
from django.urls import reverse
from django.utils import timezone

DIFFICULTY_CHOICES = [
    ("beginner", "Podstawy"),
    ("intermediate", "Średni"),
    ("advanced", "Zaawansowany"),
]

LEVEL_CHOICES = [
    ("start", "Start"),
    ("core", "Rdzeń"),
    ("advanced", "Zaawansowany"),
]

RATING_CHOICES = [
    ("again", "Jeszcze raz"),
    ("hard", "Trudne"),
    ("good", "Dobre"),
    ("easy", "Łatwe"),
]


class JsModule(models.Model):
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=140)
    subtitle = models.CharField(max_length=220)
    description = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="core")
    glyph = models.CharField(max_length=4, default="JS")
    accent = models.CharField(max_length=7, default="#F7DF1E")
    duration_minutes = models.PositiveSmallIntegerField(default=45)
    outcomes = models.TextField(help_text="Jeden efekt nauki w linii.")
    project_title = models.CharField(max_length=180)
    project_brief = models.TextField()
    project_steps = models.TextField(help_text="Jeden krok projektu w linii.")
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("js_academy:module", args=[self.slug])

    @property
    def lesson_count(self) -> int:
        return self.lessons.count()

    @property
    def question_count(self) -> int:
        return self.questions.count()

    @property
    def card_count(self) -> int:
        return self.flashcards.count()


class JsLesson(models.Model):
    module = models.ForeignKey(JsModule, on_delete=models.CASCADE, related_name="lessons")
    slug = models.SlugField(max_length=100)
    title = models.CharField(max_length=180)
    summary = models.TextField()
    body_html = models.TextField(help_text="Zaufana treść lekcji w HTML.")
    live_demo_html = models.TextField(
        blank=True,
        help_text="Samodzielny HTML demo uruchamiany w iframe z sandboxem.",
    )
    demo_title = models.CharField(max_length=180, blank=True)
    demo_description = models.TextField(blank=True)
    minutes = models.PositiveSmallIntegerField(default=10)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["module__order", "order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["module", "slug"], name="unique_js_lesson_slug_per_module"
            )
        ]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse(
            "js_academy:lesson",
            args=[self.module.slug, self.slug],
        )


class JsQuestion(models.Model):
    module = models.ForeignKey(JsModule, on_delete=models.CASCADE, related_name="questions")
    key = models.SlugField(max_length=100, unique=True)
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
    def correct_choice(self) -> "JsChoice | None":
        return next((choice for choice in self.choices.all() if choice.is_correct), None)


class JsChoice(models.Model):
    question = models.ForeignKey(
        JsQuestion, on_delete=models.CASCADE, related_name="choices"
    )
    text = models.TextField()
    is_correct = models.BooleanField(default=False)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "pk"]

    def __str__(self) -> str:
        return self.text[:80]


class JsAttempt(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="js_attempts"
    )
    module = models.ForeignKey(
        JsModule, on_delete=models.CASCADE, related_name="attempts"
    )
    length = models.PositiveSmallIntegerField(default=6)
    current_index = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"JS attempt #{self.pk} · {self.module.title}"

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

    def current_attempt_question(self) -> "JsAttemptQuestion | None":
        return (
            self.attempt_questions.select_related("question")
            .filter(position=self.current_index)
            .first()
        )

    def get_absolute_url(self) -> str:
        return reverse("js_academy:quiz", args=[self.pk])


class JsAttemptQuestion(models.Model):
    attempt = models.ForeignKey(
        JsAttempt, on_delete=models.CASCADE, related_name="attempt_questions"
    )
    question = models.ForeignKey(JsQuestion, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField()
    selected = models.ForeignKey(
        JsChoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_correct = models.BooleanField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "position"],
                name="unique_js_attempt_question_position",
            )
        ]

    def __str__(self) -> str:
        return f"{self.attempt_id}:{self.position}"


class JsFlashcard(models.Model):
    module = models.ForeignKey(
        JsModule, on_delete=models.CASCADE, related_name="flashcards"
    )
    key = models.SlugField(max_length=100, unique=True)
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
        return reverse("js_academy:flashcards", args=[self.module.slug])


class JsFlashcardReview(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="js_flashcard_reviews"
    )
    flashcard = models.ForeignKey(
        JsFlashcard, on_delete=models.CASCADE, related_name="reviews"
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
                fields=["learner", "flashcard"],
                name="unique_js_learner_flashcard_review",
            )
        ]
        indexes = [models.Index(fields=["learner", "due_date"])]

    def __str__(self) -> str:
        return f"{self.flashcard_id} do {self.due_date}"

    @property
    def is_due(self) -> bool:
        return self.due_date <= timezone.localdate()

    def review(self, rating: str) -> None:
        if rating not in dict(RATING_CHOICES):
            raise ValueError(f"Nieznana ocena fiszki: {rating!r}")

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


class JsLessonProgress(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="js_lesson_progress"
    )
    lesson = models.ForeignKey(
        JsLesson, on_delete=models.CASCADE, related_name="progress"
    )
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "lesson"], name="unique_js_learner_lesson_progress"
            )
        ]

    def __str__(self) -> str:
        return f"{self.lesson} ukończona"


class JsContentSnapshot(models.Model):
    fingerprint = models.CharField(max_length=64, unique=True)
    seeded_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.fingerprint[:12]


class JsFact(models.Model):
    """Ciekawostka — krótka, zaskakująca lub praktyczna historia o JS."""

    key = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=60)
    title = models.CharField(max_length=180)
    body = models.TextField()
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return self.title


class JsTerm(models.Model):
    """Pojęcie ze słownika — polska definicja i krótki przykład."""

    key = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=60)
    term = models.CharField(max_length=120)
    definition = models.TextField()
    example = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "term"]

    def __str__(self) -> str:
        return self.term


class JsInterviewQuestion(models.Model):
    key = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=60)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    question = models.TextField()
    answer = models.TextField()
    follow_up = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "question"]

    def __str__(self) -> str:
        return self.question[:90]


class JsChallenge(models.Model):
    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=160)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    module = models.ForeignKey(
        JsModule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="challenges",
    )
    prompt = models.TextField()
    starter_code = models.TextField()
    solution_code = models.TextField()
    tests = models.JSONField(help_text="Lista testów: name, args, expected.")
    hints = models.TextField(help_text="Jedna podpowiedź w linii.")
    explanation = models.TextField()
    xp = models.PositiveSmallIntegerField(default=20)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("js_academy:challenge", args=[self.slug])


class JsChallengeCompletion(models.Model):
    learner = models.ForeignKey(
        "dojo.Learner", on_delete=models.CASCADE, related_name="js_challenge_completions"
    )
    challenge = models.ForeignKey(
        JsChallenge, on_delete=models.CASCADE, related_name="completions"
    )
    passed = models.BooleanField(default=True)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learner", "challenge"],
                name="unique_js_learner_challenge_completion",
            )
        ]

    def __str__(self) -> str:
        return f"{self.challenge} · {self.learner}"


class JsComponent(models.Model):
    """Gotowy komponent HTML/CSS/JS z podglądem i kodem do skopiowania."""

    key = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=180)
    category = models.CharField(max_length=60)
    description = models.TextField()
    functions = models.JSONField(default=list)
    html_code = models.TextField()
    css_code = models.TextField()
    js_code = models.TextField()
    notes = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self) -> str:
        return self.title

    def get_absolute_url(self) -> str:
        return reverse("js_academy:component", args=[self.key])


def percent(part: int, whole: int) -> int:
    if not whole:
        return 0
    return min(100, max(0, ceil(100 * part / whole)))
