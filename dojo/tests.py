from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .content import load_bundles
from .models import (
    AppBlueprint,
    ArchitectureCase,
    Attempt,
    Cheatsheet,
    Flashcard,
    FlashcardReview,
    Learner,
    Question,
    ReleaseNote,
    ReleaseSeries,
    StudyEvent,
    Topic,
    level_from_xp,
    streak_for,
)
from .services import (
    complete_attempt,
    create_attempt,
    dashboard_stats,
    due_flashcards,
    flashcard_progress,
    record_answer,
)


class SeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)


class ContentTests(SeededTestCase):
    def test_bundle_counts_and_shape(self):
        bundles = load_bundles()
        self.assertEqual(len(bundles), 22)
        self.assertEqual(Topic.objects.count(), 22)
        self.assertEqual(Question.objects.count(), 330)
        self.assertEqual(Flashcard.objects.count(), 154)
        for topic in Topic.objects.all():
            self.assertEqual(topic.questions.count(), 15)
            self.assertEqual(topic.flashcards.count(), 7)
            for difficulty in ("beginner", "intermediate", "advanced"):
                self.assertEqual(topic.questions.filter(difficulty=difficulty).count(), 5)

    def test_every_question_has_exactly_one_correct_choice(self):
        for question in Question.objects.prefetch_related("choices"):
            self.assertEqual(question.choices.count(), 4)
            self.assertEqual(
                sum(1 for choice in question.choices.all() if choice.is_correct),
                1,
                msg=question.key,
            )
            self.assertTrue(question.explanation)
            self.assertTrue(question.prompt)

    def test_content_can_be_seeded_twice_without_duplicating_or_resetting_choices(self):
        choice = Question.objects.first().choices.first()
        old_pk = choice.pk
        call_command("seed_content", verbosity=0)
        self.assertEqual(Topic.objects.count(), 22)
        self.assertEqual(Question.objects.count(), 330)
        self.assertEqual(Flashcard.objects.count(), 154)
        self.assertEqual(Question.objects.first().choices.first().pk, old_pk)


class HomeAndSetupTests(SeededTestCase):
    def test_home_renders(self):
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "From first")
        self.assertContains(response, "The study map")
        self.assertContains(response, "JS Akademia")

    def test_quiz_setup_renders(self):
        response = self.client.get(reverse("dojo:quiz_setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Build a run")

    def test_setup_prefills_topic_from_query_string(self):
        topic = Topic.objects.get(slug="python-core")
        response = self.client.get(reverse("dojo:quiz_setup") + "?topic=python-core")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["topic"], topic.pk)

    def test_create_filtered_attempt(self):
        topic = Topic.objects.get(slug="python-core")
        response = self.client.post(
            reverse("dojo:quiz_setup"),
            {"topic": topic.pk, "difficulty": "advanced", "length": 5},
        )
        self.assertEqual(response.status_code, 302)
        attempt = Attempt.objects.get()
        self.assertEqual(attempt.topic, topic)
        self.assertEqual(attempt.difficulty, "advanced")
        self.assertEqual(attempt.length, 5)
        self.assertEqual(attempt.attempt_questions.count(), 5)
        for attempt_question in attempt.attempt_questions.select_related("question"):
            self.assertEqual(attempt_question.question.topic, topic)
            self.assertEqual(attempt_question.question.difficulty, "advanced")

    def test_setup_rejects_more_questions_than_available(self):
        topic = Topic.objects.get(slug="python-core")
        response = self.client.post(
            reverse("dojo:quiz_setup"),
            {"topic": topic.pk, "difficulty": "advanced", "length": 20},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only 5 questions are available")
        self.assertEqual(Attempt.objects.count(), 0)


class QuizFlowTests(SeededTestCase):
    def _start_attempt(self, length=5):
        topic = Topic.objects.get(slug="python-core")
        return create_attempt(
            Learner.local(), topic=topic, difficulty="beginner", length=length
        )

    def test_question_page_renders(self):
        attempt = self._start_attempt()
        response = self.client.get(reverse("dojo:quiz_question", args=[attempt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lock in answer")
        self.assertEqual(response.context["question_number"], 1)

    def test_answer_records_choice_and_awards_once(self):
        attempt = self._start_attempt()
        aq = attempt.current_attempt_question()
        correct = aq.question.choices.get(is_correct=True)
        response = self.client.post(
            reverse("dojo:quiz_question", args=[attempt.pk]),
            {"action": "answer", "choice": correct.pk},
        )
        self.assertEqual(response.status_code, 302)
        aq.refresh_from_db()
        self.assertEqual(aq.selected, correct)
        self.assertTrue(aq.is_correct)
        self.assertEqual(StudyEvent.objects.filter(kind="quiz").count(), 1)
        self.assertEqual(StudyEvent.objects.get(kind="quiz").xp, 10)

        response = self.client.post(
            reverse("dojo:quiz_question", args=[attempt.pk]),
            {"action": "answer", "choice": correct.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StudyEvent.objects.filter(kind="quiz").count(), 1)

    def test_wrong_answer_awards_effort_xp_and_reveals_explanation(self):
        attempt = self._start_attempt()
        aq = attempt.current_attempt_question()
        wrong = aq.question.choices.filter(is_correct=False).first()
        response = self.client.post(
            reverse("dojo:quiz_question", args=[attempt.pk]),
            {"action": "answer", "choice": wrong.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Not quite.")
        self.assertContains(response, "Why")
        self.assertEqual(StudyEvent.objects.get(kind="quiz").xp, 2)

    def test_cannot_answer_with_choice_from_another_question(self):
        attempt = self._start_attempt()
        aq = attempt.current_attempt_question()
        other = Question.objects.exclude(pk=aq.question_id).first()
        response = self.client.post(
            reverse("dojo:quiz_question", args=[attempt.pk]),
            {"action": "answer", "choice": other.choices.first().pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not belong")
        aq.refresh_from_db()
        self.assertIsNone(aq.selected)

    def test_next_requires_an_answer(self):
        attempt = self._start_attempt()
        response = self.client.post(
            reverse("dojo:quiz_question", args=[attempt.pk]), {"action": "next"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Choose an answer first")
        attempt.refresh_from_db()
        self.assertEqual(attempt.current_index, 0)

    def test_complete_run_awards_perfect_bonus_and_shows_results(self):
        attempt = self._start_attempt(length=5)
        url = reverse("dojo:quiz_question", args=[attempt.pk])
        for index in range(5):
            attempt.refresh_from_db()
            aq = attempt.current_attempt_question()
            correct = aq.question.choices.get(is_correct=True)
            self.client.post(url, {"action": "answer", "choice": correct.pk})
            response = self.client.post(url, {"action": "next"})
            if index < 4:
                self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertIsNotNone(attempt.completed_at)
        self.assertEqual(attempt.correct_count, 5)
        self.assertEqual(attempt.bonus_xp, 25)
        self.assertEqual(attempt.xp_earned, 75)
        response = self.client.get(reverse("dojo:quiz_results", args=[attempt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Perfect run.")
        self.assertContains(response, "Every answer, explained.")

    def test_results_redirect_to_unfinished_quiz(self):
        attempt = self._start_attempt()
        response = self.client.get(reverse("dojo:quiz_results", args=[attempt.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dojo:quiz_question", args=[attempt.pk]))

    def test_attempts_are_scoped_to_the_local_learner(self):
        other = Learner.objects.create(pk=2, name="Other")
        attempt = Attempt.objects.create(learner=other, length=5)
        response = self.client.get(reverse("dojo:quiz_question", args=[attempt.pk]))
        self.assertEqual(response.status_code, 404)

    def test_completion_is_idempotent(self):
        attempt = self._start_attempt(length=1)
        aq = attempt.current_attempt_question()
        record_answer(aq, aq.question.choices.get(is_correct=True))
        first = complete_attempt(attempt)
        second = complete_attempt(attempt)
        self.assertEqual(first, 25)
        self.assertEqual(second, 25)
        self.assertEqual(StudyEvent.objects.filter(kind="bonus").count(), 1)


class FlashcardTests(SeededTestCase):
    def test_flashcards_index_renders(self):
        response = self.client.get(reverse("dojo:flashcards"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open question.")

    def test_study_reveals_answer(self):
        topic = Topic.objects.get(slug="python-core")
        card = topic.flashcards.first()
        response = self.client.get(
            reverse("dojo:flashcards_study", args=[topic.slug]) + "?reveal=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["reveal"])
        self.assertContains(response, card.back[:30])

    def test_rate_schedules_review_and_awards_xp(self):
        topic = Topic.objects.get(slug="python-core")
        card = topic.flashcards.first()
        response = self.client.post(
            reverse("dojo:flashcards_rate", args=[topic.slug, card.pk]),
            {"rating": "good"},
        )
        self.assertEqual(response.status_code, 302)
        review = FlashcardReview.objects.get(flashcard=card)
        self.assertEqual(review.interval_days, 3)
        self.assertEqual(review.due_date, timezone.localdate() + timedelta(days=3))
        self.assertEqual(StudyEvent.objects.get(kind="flashcard").xp, 4)
        self.assertNotIn(
            card.pk,
            [item["card"].pk for item in due_flashcards(Learner.local(), topic)],
        )

    def test_again_resets_and_records_lapse(self):
        topic = Topic.objects.get(slug="python-core")
        card = topic.flashcards.first()
        self.client.post(
            reverse("dojo:flashcards_rate", args=[topic.slug, card.pk]),
            {"rating": "good"},
        )
        review = FlashcardReview.objects.get(flashcard=card)
        review.interval_days = 9
        review.repetitions = 4
        review.save()
        self.client.post(
            reverse("dojo:flashcards_rate", args=[topic.slug, card.pk]),
            {"rating": "again"},
        )
        review.refresh_from_db()
        self.assertEqual(review.interval_days, 1)
        self.assertEqual(review.repetitions, 0)
        self.assertEqual(review.lapses, 1)

    def test_invalid_rating_does_not_create_review(self):
        topic = Topic.objects.get(slug="python-core")
        card = topic.flashcards.first()
        response = self.client.post(
            reverse("dojo:flashcards_rate", args=[topic.slug, card.pk]),
            {"rating": "impossible"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(FlashcardReview.objects.exists())

    def test_card_from_other_deck_is_rejected(self):
        topic = Topic.objects.get(slug="python-core")
        card = Flashcard.objects.exclude(topic=topic).first()
        response = self.client.post(
            reverse("dojo:flashcards_rate", args=[topic.slug, card.pk]),
            {"rating": "good"},
        )
        self.assertEqual(response.status_code, 404)

    def test_progress_counts_new_and_due_cards(self):
        learner = Learner.local()
        topic = Topic.objects.get(slug="python-core")
        progress = flashcard_progress(learner, topic)
        self.assertEqual(progress["total"], 7)
        self.assertEqual(progress["due"], 7)
        self.assertEqual(progress["reviewed"], 0)
        card = topic.flashcards.first()
        self.client.post(
            reverse("dojo:flashcards_rate", args=[topic.slug, card.pk]),
            {"rating": "easy"},
        )
        progress = flashcard_progress(learner, topic)
        self.assertEqual(progress["due"], 6)
        self.assertEqual(progress["reviewed"], 1)

    def test_all_due_review_route(self):
        response = self.client.get(reverse("dojo:flashcards_review_all"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "All due cards")


class ProgressAndModelTests(SeededTestCase):
    def test_progress_page_renders_achievements_and_heatmap(self):
        response = self.client.get(reverse("dojo:progress"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mastery map")
        self.assertContains(response, "First contact")
        self.assertEqual(len(response.context["activity_days"]), 28)

    def test_reset_clears_progress_but_not_content(self):
        attempt = create_attempt(
            Learner.local(), topic=None, difficulty="beginner", length=5
        )
        aq = attempt.current_attempt_question()
        record_answer(aq, aq.question.choices.get(is_correct=True))
        card = Flashcard.objects.first()
        self.client.post(
            reverse("dojo:flashcards_rate_all", args=[card.pk]), {"rating": "good"}
        )
        response = self.client.post(reverse("dojo:progress_reset"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Attempt.objects.count(), 0)
        self.assertEqual(StudyEvent.objects.count(), 0)
        self.assertEqual(FlashcardReview.objects.count(), 0)
        self.assertEqual(Question.objects.count(), 330)
        self.assertEqual(Flashcard.objects.count(), 154)

    def test_streak_counts_consecutive_days(self):
        learner = Learner.local()
        today = timezone.localdate()
        for offset in (0, 1, 2):
            StudyEvent.objects.create(
                learner=learner,
                kind="quiz",
                xp=10,
                occurred_on=today - timedelta(days=offset),
            )
        self.assertEqual(streak_for(learner, today), 3)
        StudyEvent.objects.filter(occurred_on=today - timedelta(days=1)).delete()
        self.assertEqual(streak_for(learner, today), 1)

    def test_streak_remains_alive_from_yesterday(self):
        learner = Learner.local()
        today = timezone.localdate()
        StudyEvent.objects.create(
            learner=learner,
            kind="quiz",
            xp=10,
            occurred_on=today - timedelta(days=1),
        )
        self.assertEqual(streak_for(learner, today), 1)

    def test_level_boundaries(self):
        self.assertEqual(level_from_xp(0)["title"], "Curious")
        self.assertEqual(level_from_xp(149)["number"], 1)
        self.assertEqual(level_from_xp(150)["title"], "Apprentice")
        self.assertEqual(level_from_xp(3000)["number"], 7)

    def test_dashboard_mastery_tracks_distinct_correct_questions(self):
        learner = Learner.local()
        attempt = create_attempt(
            learner,
            topic=Topic.objects.get(slug="python-core"),
            difficulty="beginner",
            length=5,
        )
        for _ in range(5):
            aq = attempt.current_attempt_question()
            record_answer(aq, aq.question.choices.get(is_correct=True))
            if attempt.current_index + 1 < attempt.length:
                attempt.current_index += 1
                attempt.save(update_fields=["current_index"])
        stats = dashboard_stats(learner)
        row = next(row for row in stats["topics"] if row["topic"].slug == "python-core")
        self.assertEqual(row["mastered"], 5)
        self.assertGreaterEqual(row["mastery"], 33)


class FieldGuideTests(SeededTestCase):
    def test_guide_content_counts(self):
        self.assertEqual(Cheatsheet.objects.count(), 28)
        self.assertEqual(AppBlueprint.objects.count(), 6)
        self.assertEqual(ArchitectureCase.objects.count(), 8)
        self.assertEqual(ReleaseNote.objects.count(), 6)
        self.assertEqual(ReleaseSeries.objects.count(), 4)

    def test_field_guide_landing_renders(self):
        response = self.client.get(reverse("dojo:field_guide"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The field guide")
        self.assertContains(response, "Latest stable")
        self.assertContains(response, "6.1.2")

    def test_cheatsheets_search_and_category_filter(self):
        response = self.client.get(reverse("dojo:cheatsheets") + "?q=webhook")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Receive a signed webhook")

        response = self.client.get(reverse("dojo:cheatsheets") + "?category=Security")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rate-limit login and API abuse sensibly")
        self.assertNotContains(response, "Validate an uploaded file")

    def test_cheatsheet_anchor_and_code_are_rendered(self):
        recipe = Cheatsheet.objects.get(key="idempotent-webhook")
        response = self.client.get(reverse("dojo:cheatsheets"))
        self.assertContains(response, f'id="recipe-{recipe.key}"')
        self.assertContains(response, "hmac.compare_digest")

    def test_blueprints_index_and_detail(self):
        response = self.client.get(reverse("dojo:blueprints"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SaaS subscription workspace")

        blueprint = AppBlueprint.objects.get(key="saas-subscriptions")
        response = self.client.get(reverse("dojo:blueprint_detail", args=[blueprint.key]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The data shape")
        self.assertContains(response, "unique_workspace_member")

    def test_release_radar_contains_security_and_support_information(self):
        response = self.client.get(reverse("dojo:release_radar"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CVE-2026-84429")
        self.assertContains(response, "CVE-2026-87975")
        self.assertContains(response, "5.2.18")
        self.assertContains(response, "Official release notes")

    def test_unknown_blueprint_returns_404(self):
        response = self.client.get(
            reverse("dojo:blueprint_detail", args=["does-not-exist"])
        )
        self.assertEqual(response.status_code, 404)

    def test_seed_content_if_changed_skips_second_run(self):
        from io import StringIO

        out = StringIO()
        call_command("seed_content", "--if-changed", stdout=out)
        self.assertIn("skipping seed", out.getvalue())

    def test_architecture_studio_and_case_pages(self):
        response = self.client.get(reverse("dojo:architecture_studio"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI writes code")
        self.assertContains(response, "AI document assistant with citations")

        case = ArchitectureCase.objects.get(key="rag-document-assistant")
        response = self.client.get(reverse("dojo:architecture_case", args=[case.key]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reference architecture")
        self.assertContains(response, "Data flow")
        self.assertContains(response, "Cross-tenant retrieval")

    def test_architecture_complexity_filter(self):
        response = self.client.get(
            reverse("dojo:architecture_studio") + "?complexity=expert"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tool-using operations agent")
        self.assertNotContains(response, "AI document assistant with citations")

    def test_unknown_architecture_case_returns_404(self):
        response = self.client.get(
            reverse("dojo:architecture_case", args=["not-real"])
        )
        self.assertEqual(response.status_code, 404)

    def test_home_links_to_architecture_studio(self):
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI writes code")
        self.assertContains(response, reverse("dojo:architecture_studio"))

    def test_home_links_to_the_field_guide(self):
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Real-world app blueprints")
        self.assertContains(response, reverse("dojo:cheatsheets"))

