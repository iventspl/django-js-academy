from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .capstone import load_capstone
from .content import load_bundles
from .handbook import chapter_map, load_chapters, render_prose, search_handbook, suggest_terms
from .labs import load_labs
from .tracks import load_tracks
from .models import (
    AppBlueprint,
    ArchitectureCase,
    Attempt,
    Cheatsheet,
    Flashcard,
    FlashcardReview,
    HandbookProgress,
    HandbookNote,
    DjangoCapstoneProgress,
    DjangoFeature,
    DjangoTrackProgress,
    HandbookExplanation,
    HandbookFeedback,
    HandbookLabProgress,
    HandbookSearchLog,
    Learner,
    Question,
    ReleaseNote,
    ReleaseSeries,
    StudyEvent,
    StudyNote,
    Topic,
    level_from_xp,
    streak_for,
)
from .services import (
    complete_attempt,
    create_attempt,
    create_attempt_from_questions,
    create_retry_attempt,
    create_weak_spot_attempt,
    dashboard_stats,
    due_flashcards,
    flashcard_progress,
    record_answer,
    weak_spots,
)


class SeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_content", verbosity=0)


class ContentTests(SeededTestCase):
    def test_bundle_counts_and_shape(self):
        bundles = load_bundles()
        self.assertEqual(len(bundles), 24)
        self.assertEqual(Topic.objects.count(), 24)
        self.assertEqual(Question.objects.count(), 360)
        self.assertEqual(Flashcard.objects.count(), 168)
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
        self.assertEqual(Topic.objects.count(), 24)
        self.assertEqual(Question.objects.count(), 360)
        self.assertEqual(Flashcard.objects.count(), 168)
        self.assertEqual(Question.objects.first().choices.first().pk, old_pk)


class HomeAndSetupTests(SeededTestCase):
    def test_home_renders(self):
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "From first")
        self.assertContains(response, "The study map")
        self.assertContains(response, "JS Akademia")

    def test_mobile_navigation_and_styles_are_loaded(self):
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mobile-nav-toggle")
        self.assertContains(response, "dojo/mobile.css")

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
        self.assertEqual(Question.objects.count(), 360)
        self.assertEqual(Flashcard.objects.count(), 168)

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
        self.assertEqual(Cheatsheet.objects.count(), 34)
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



class NotesAndExportTests(SeededTestCase):
    def test_create_note_and_bookmark(self):
        topic = Topic.objects.first()
        response = self.client.post(
            reverse("dojo:notes"),
            {"title": "Pamiętaj o select_related", "body": "Mniej zapytań.", "topic": topic.pk, "bookmarked": "on"},
        )
        self.assertEqual(response.status_code, 302)
        note = StudyNote.objects.get(title="Pamiętaj o select_related")
        self.assertTrue(note.is_bookmarked)
        self.assertEqual(note.topic, topic)
        response = self.client.get(reverse("dojo:notes"))
        self.assertContains(response, "Pamiętaj o select_related")
        response = self.client.post(reverse("dojo:delete_note", args=[note.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StudyNote.objects.filter(pk=note.pk).exists())

    def test_progress_export(self):
        response = self.client.get(reverse("dojo:progress_export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertContains(response, "Django Quest progress")


class SearchTests(SeededTestCase):
    def test_search_finds_topics_questions_and_recipes(self):
        response = self.client.get(reverse("dojo:search"), {"q": "htmx"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Server-Driven UI")
        self.assertContains(response, "Return a partial for HTMX")
        self.assertContains(response, "Questions")
        self.assertGreaterEqual(response.context["counts"]["recipes"], 3)

    def test_search_finds_tooling_recipe_and_card(self):
        response = self.client.get(reverse("dojo:search"), {"q": "mypy"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Type-check Django models")
        self.assertContains(response, "Python Typing")
        self.assertGreaterEqual(response.context["counts"]["cards"], 1)

    def test_search_finds_release_notes(self):
        response = self.client.get(reverse("dojo:search"), {"q": "CVE"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Release notes")
        self.assertGreaterEqual(response.context["counts"]["releases"], 1)

    def test_search_needs_two_characters_and_shows_idle_state(self):
        response = self.client.get(reverse("dojo:search"), {"q": "h"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])
        self.assertContains(response, "Search the")

    def test_search_empty_state(self):
        response = self.client.get(reverse("dojo:search"), {"q": "xyz-not-real"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 0)
        self.assertContains(response, "Nothing matched")

    def test_home_sidebar_exposes_search(self):
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("dojo:search"))

    def test_search_finds_handbook_chapters(self):
        response = self.client.get(reverse("dojo:search"), {"q": "forms"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django handbook")
        self.assertGreaterEqual(response.context["counts"]["handbook"], 1)
        self.assertContains(response, reverse("dojo:handbook_chapter", args=["forms"]))


class HandbookContentTests(TestCase):
    def test_every_chapter_is_complete(self):
        chapters = load_chapters()
        self.assertGreaterEqual(len(chapters), 80)
        self.assertGreaterEqual(sum(len(chapter["sections"]) for chapter in chapters), 330)
        levels = {chapter["level"] for chapter in chapters}
        self.assertEqual(levels, {"Core", "Advanced", "Reference", "Recipe"})
        for chapter in chapters:
            self.assertGreaterEqual(len(chapter["sections"]), 2, chapter["slug"])
            self.assertGreaterEqual(len(chapter["pitfalls"]), 3, chapter["slug"])
            self.assertGreaterEqual(len(chapter["checklist"]), 3, chapter["slug"])
            for section in chapter["sections"]:
                self.assertTrue(section["body"], f"{chapter['slug']}#{section['id']}")
                if section["table"]:
                    for row in section["table"]["rows"]:
                        self.assertEqual(len(row), len(section["table"]["head"]))
            self.assertTrue(chapter["official"].startswith("https://"))
        slugs = [chapter["slug"] for chapter in chapters]
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_reference_and_recipe_material_exists(self):
        chapters = load_chapters()
        self.assertGreaterEqual(sum(1 for chapter in chapters if chapter["level"] == "Reference"), 15)
        self.assertGreaterEqual(sum(1 for chapter in chapters if chapter["level"] == "Recipe"), 10)
        self.assertIn("queryset-reference", chapter_map())
        self.assertIn("recipe-auth", chapter_map())

    def test_forms_chapter_covers_the_working_parts(self):
        chapter = chapter_map()["forms"]
        anchors = {section["id"] for section in chapter["sections"]}
        self.assertGreaterEqual(len(chapter["sections"]), 8)
        self.assertGreaterEqual(len(chapter["errors"]), 6)
        self.assertTrue(
            {
                "plain-form-end-to-end",
                "field-cheatsheet",
                "validation-pipeline",
                "modelform",
                "initial-and-dynamic-fields",
                "formsets",
                "file-uploads",
            }
            <= anchors
        )

    def test_related_links_resolve(self):
        by_slug = chapter_map()
        for chapter in load_chapters():
            for related in chapter["related"]:
                self.assertIn(related, by_slug)

    def test_search_prioritises_forms(self):
        hits = search_handbook("forms")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["chapter"]["slug"], "forms")
        titles = " ".join(hit["title"] for hit in hits)
        self.assertIn("ModelForm", titles)
        self.assertIn("Formsets", titles)
        self.assertNotIn("settings.py", {hit["chapter"]["title"] for hit in hits})

    def test_search_finds_an_exception_name(self):
        hits = search_handbook("NoReverseMatch")
        self.assertTrue(hits)
        self.assertIn(hits[0]["chapter"]["slug"], {"errors", "urls", "exceptions-reference"})

    def test_search_finds_advanced_and_reference_topics(self):
        locking = search_handbook("select_for_update")
        self.assertTrue(locking)
        self.assertIn(locking[0]["chapter"]["slug"], {"transactions-locking", "database-reference"})
        search = search_handbook("SearchVector")
        self.assertTrue(search)
        self.assertIn(search[0]["chapter"]["slug"], {"search-postgres", "orm-expressions"})

    def test_search_indexes_code_and_reference_tables(self):
        field_hits = search_handbook("PositiveIntegerField")
        self.assertTrue(field_hits)
        self.assertEqual(field_hits[0]["kind"], "symbol")
        self.assertEqual(field_hits[0]["title"], "PositiveIntegerField")
        self.assertIn("Scalar fields", {hit["title"] for hit in field_hits})
        self.assertIn("model-fields-reference", {hit["chapter"]["slug"] for hit in field_hits})

        auto_hits = search_handbook("AutoField")
        self.assertTrue(auto_hits)
        self.assertIn("Scalar fields", {hit["title"] for hit in auto_hits})

        code_hits = search_handbook("Post.objects.filter")
        self.assertTrue(code_hits)
        self.assertIn("orm", {hit["chapter"]["slug"] for hit in code_hits})

    def test_search_suggests_a_corrected_identifier(self):
        suggestions = suggest_terms("PositveIntegerField")
        self.assertTrue(suggestions)
        self.assertIn("PositiveIntegerField", {suggestion["term"] for suggestion in suggestions})
        self.assertEqual(search_handbook("PositveIntegerField"), [])

    def test_search_needs_two_characters(self):
        self.assertEqual(search_handbook("f"), [])
        self.assertEqual(search_handbook(""), [])

    def test_prose_escapes_html_but_keeps_inline_markup(self):
        rendered = render_prose("<script>alert(1)</script> **bold** `x<y`")
        self.assertNotIn("<script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("<strong>bold</strong>", rendered)
        self.assertIn("<code>x&lt;y</code>", rendered)

    def test_prose_renders_bullet_lists(self):
        rendered = render_prose("- one\n- two")
        self.assertIn("<ul><li>one</li><li>two</li></ul>", rendered)

    def test_check_handbook_command_reports_a_valid_book(self):
        output = StringIO()
        call_command("check_handbook", stdout=output)
        text = output.getvalue()
        self.assertIn("Chapters: 90", text)
        self.assertIn("Handbook is valid", text)

    def test_coverage_chapters_have_exercises(self):
        chapter = chapter_map()["messages"]
        self.assertTrue(chapter["exercises"])
        response = self.client.get(reverse("dojo:handbook_chapter", args=["messages"]))
        self.assertContains(response, "Try it yourself")
        self.assertContains(response, "Show solution")

    def test_markdown_export_contains_the_chapter(self):
        response = self.client.get(reverse("dojo:handbook_markdown", args=["forms"]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/markdown", response["Content-Type"])
        body = response.content.decode()
        self.assertTrue(body.startswith("# Forms"))
        self.assertIn("## Short answer", body)
        self.assertIn("```python", body)


class HandbookViewTests(TestCase):
    def test_handbook_home_renders(self):
        response = self.client.get(reverse("dojo:handbook"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ask the handbook")
        self.assertContains(response, "forms.py")
        self.assertContains(response, "data-theme-select")
        self.assertContains(response, "Paper")
        self.assertContains(response, "High contrast")
        self.assertContains(response, "Django handbook")

    def test_handbook_search_renders_results(self):
        response = self.client.get(reverse("dojo:handbook"), {"q": "forms"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "answers for")
        self.assertContains(response, "#modelform")
        self.assertContains(response, "#formsets")

    def test_handbook_search_json(self):
        response = self.client.get(reverse("dojo:handbook_search"), {"q": "forms"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 4)
        self.assertEqual(payload["results"][0]["chapter"], "Forms")
        self.assertTrue(payload["results"][0]["url"].startswith("/handbook/forms/"))

    def test_handbook_search_json_finds_field_identifiers(self):
        response = self.client.get(
            reverse("dojo:handbook_search"), {"q": "PositiveIntegerField"}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["kind"], "symbol")
        chapters = {result["chapter"] for result in payload["results"]}
        self.assertIn("Model fields reference", chapters)
        self.assertTrue(
            any("PositiveIntegerField" in result["snippet"] for result in payload["results"])
        )

    def test_chapter_renders_sections_and_official_link(self):
        response = self.client.get(reverse("dojo:handbook_chapter", args=["forms"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Short answer")
        self.assertContains(response, "What is_valid() actually does")
        self.assertContains(response, "Error fixes")
        self.assertContains(response, "https://docs.djangoproject.com/en/stable/topics/forms/")
        self.assertContains(response, "Reviewed 9 Nov 2026")
        self.assertContains(response, "Django 5.2 – 6.1")

    def test_coverage_page_renders(self):
        response = self.client.get(reverse("dojo:handbook_coverage"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Coverage report")
        self.assertContains(response, "Known gaps")
        self.assertContains(response, "90")

    def test_version_matrix_renders(self):
        response = self.client.get(reverse("dojo:handbook_versions"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Version matrix")
        self.assertContains(response, "5.2")
        self.assertContains(response, "6.1")

    def test_unknown_chapter_is_404(self):
        response = self.client.get(reverse("dojo:handbook_chapter", args=["not-a-chapter"]))
        self.assertEqual(response.status_code, 404)

    def test_reference_chapter_renders_a_table(self):
        response = self.client.get(reverse("dojo:handbook_chapter", args=["queryset-reference"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Query methods")
        self.assertContains(response, 'class="hb-table"')
        self.assertContains(response, "select_related")

    def test_level_filter_narrows_the_index(self):
        response = self.client.get(reverse("dojo:handbook"), {"level": "Reference"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QuerySet reference")
        self.assertNotContains(response, "Start a project")

    def test_kind_filter_narrows_search_results(self):
        response = self.client.get(
            reverse("dojo:handbook"),
            {"q": "PositiveIntegerField", "kind": "symbol"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PositiveIntegerField")
        self.assertContains(response, "Symbol")
        self.assertNotContains(response, "Choose the narrowest field")

    def test_search_json_returns_suggestions_for_a_typo(self):
        response = self.client.get(
            reverse("dojo:handbook_search"), {"q": "PositveIntegerField"}
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 0)
        self.assertIn(
            "PositiveIntegerField",
            {suggestion["term"] for suggestion in payload["suggestions"]},
        )

    def test_zero_result_search_is_logged(self):
        self.client.get(reverse("dojo:handbook_search"), {"q": "xyz-not-real"})
        self.client.get(reverse("dojo:handbook_search"), {"q": "xyz-not-real"})
        row = HandbookSearchLog.objects.get(query="xyz-not-real")
        self.assertEqual(row.count, 2)

        output = StringIO()
        call_command("handbook_gaps", stdout=output)
        self.assertIn("xyz-not-real", output.getvalue())

    def test_recipe_chapter_renders(self):
        response = self.client.get(reverse("dojo:handbook_chapter", args=["recipe-auth"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Signup, login, logout and password reset")
        self.assertContains(response, "UserCreationForm")

    def test_traceback_explainer_finds_the_exception(self):
        get_response = self.client.get(reverse("dojo:handbook_traceback"))
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "Paste the traceback")

        response = self.client.post(
            reverse("dojo:handbook_traceback"),
            {
                "traceback": (
                    "Traceback (most recent call last):\n"
                    "  File \"views.py\", line 42, in post_detail\n"
                    "django.urls.exceptions.NoReverseMatch: Reverse for 'post-detail' not found."
                )
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NoReverseMatch")
        self.assertContains(response, "Likely answers")

    def test_traceback_explainer_handles_unstructured_text(self):
        response = self.client.post(
            reverse("dojo:handbook_traceback"), {"traceback": "something went wrong"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No exception name found")

    def test_handbook_is_in_sidebar(self):
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("dojo:handbook"))


class HandbookPracticeTests(SeededTestCase):
    def test_chapter_links_to_quiz_topic_and_flashcards(self):
        response = self.client.get(reverse("dojo:handbook_chapter", args=["forms"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Checkpoint")
        self.assertContains(response, reverse("dojo:handbook_checkpoint", args=["forms"]))
        self.assertContains(response, "/quiz/?topic=views-forms-templates")
        self.assertContains(response, "/flashcards/views-forms-templates/")

    def test_every_mapped_quiz_topic_exists(self):
        slugs = set(Topic.objects.values_list("slug", flat=True))
        mapped = {chapter["quiz_topic"] for chapter in load_chapters() if chapter["quiz_topic"]}
        self.assertEqual(mapped - slugs, set())


class HandbookProgressTests(SeededTestCase):
    def test_visiting_a_chapter_creates_progress_and_continue_link(self):
        self.client.get(reverse("dojo:handbook_chapter", args=["models"]))
        progress = HandbookProgress.objects.get(chapter_slug="models")
        self.assertFalse(progress.is_read)
        response = self.client.get(reverse("dojo:handbook"))
        self.assertContains(response, "Continue where you left off.")
        self.assertContains(response, "Continue reading")

    def test_mark_read_and_bookmark_toggle(self):
        self.client.get(reverse("dojo:handbook_chapter", args=["forms"]))
        response = self.client.post(reverse("dojo:handbook_read", args=["forms"]))
        self.assertRedirects(response, reverse("dojo:handbook_chapter", args=["forms"]))
        progress = HandbookProgress.objects.get(chapter_slug="forms")
        self.assertTrue(progress.is_read)
        self.assertIsNotNone(progress.read_at)

        self.client.post(reverse("dojo:handbook_bookmark", args=["forms"]))
        progress.refresh_from_db()
        self.assertTrue(progress.is_bookmarked)
        landing = self.client.get(reverse("dojo:handbook"))
        self.assertContains(landing, "Bookmarks")
        self.assertContains(landing, "1 saved chapter")

    def test_progress_endpoints_404_for_unknown_chapter(self):
        self.assertEqual(
            self.client.post(reverse("dojo:handbook_read", args=["not-real"])).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(reverse("dojo:handbook_bookmark", args=["not-real"])).status_code,
            404,
        )

    def test_chapter_checkpoint_creates_three_question_attempt(self):
        response = self.client.post(reverse("dojo:handbook_checkpoint", args=["forms"]))
        self.assertEqual(response.status_code, 302)
        attempt = Attempt.objects.latest("id")
        self.assertEqual(attempt.length, 3)
        self.assertEqual(attempt.attempt_questions.count(), 3)
        self.assertIsNotNone(attempt.topic)


class HandbookNoteTests(SeededTestCase):
    def test_save_note_and_bookmark_section(self):
        url = reverse(
            "dojo:handbook_note", args=["messages", "thirty-second-answer"]
        )
        response = self.client.post(
            url, {"body": "Messages are consumed once.", "bookmarked": "on"}
        )
        self.assertEqual(response.status_code, 302)
        note = HandbookNote.objects.get(
            chapter_slug="messages", section_id="thirty-second-answer"
        )
        self.assertIn("consumed once", note.body)
        self.assertTrue(note.is_bookmarked)

        chapter = self.client.get(
            reverse("dojo:handbook_chapter", args=["messages"])
        )
        self.assertContains(chapter, "Your note")
        self.assertContains(chapter, "Messages are consumed once.")

        notes = self.client.get(reverse("dojo:handbook_notes"))
        self.assertContains(notes, "Messages are consumed once.")
        export = self.client.get(reverse("dojo:handbook_notes_export"))
        self.assertIn("text/markdown", export["Content-Type"])
        self.assertIn(b"Messages are consumed once.", export.content)

    def test_clearing_note_deletes_it(self):
        HandbookNote.objects.create(
            learner=Learner.local(),
            chapter_slug="messages",
            section_id="thirty-second-answer",
            body="Temporary",
        )
        url = reverse(
            "dojo:handbook_note", args=["messages", "thirty-second-answer"]
        )
        self.client.post(url, {"body": ""})
        self.assertFalse(HandbookNote.objects.exists())

    def test_note_rejects_unknown_section(self):
        response = self.client.post(
            reverse("dojo:handbook_note", args=["messages", "not-a-section"]),
            {"body": "x"},
        )
        self.assertEqual(response.status_code, 404)


class HandbookExplanationTests(SeededTestCase):
    def test_save_explanation_and_rating(self):
        url = reverse("dojo:handbook_explanation", args=["forms"])
        response = self.client.post(
            url, {"body": "Forms validate input before the view uses it.", "rating": "okay"}
        )
        self.assertEqual(response.status_code, 302)
        explanation = HandbookExplanation.objects.get(chapter_slug="forms")
        self.assertIn("validate input", explanation.body)
        self.assertEqual(explanation.rating, "okay")
        self.assertEqual(explanation.interval_days, 3)
        self.assertEqual(explanation.repetitions, 1)
        self.assertEqual(explanation.due_on, timezone.localdate() + timedelta(days=3))

        chapter = self.client.get(reverse("dojo:handbook_chapter", args=["forms"]))
        self.assertContains(chapter, "Close the page. Explain it.")
        self.assertContains(chapter, "Forms validate input before the view uses it.")
        self.assertContains(chapter, "self-rating: Okay")

    def test_teach_back_review_keeps_previous_attempt(self):
        url = reverse("dojo:handbook_explanation", args=["forms"])
        self.client.post(url, {"body": "First explanation.", "rating": "shaky"})
        self.client.post(url, {"body": "Second explanation.", "rating": "solid"})
        explanation = HandbookExplanation.objects.get(chapter_slug="forms")
        self.assertEqual(explanation.body, "Second explanation.")
        self.assertEqual(explanation.previous_body, "First explanation.")
        self.assertEqual(explanation.due_on, timezone.localdate() + timedelta(days=14))
        self.assertEqual(explanation.repetitions, 2)

        response = self.client.get(reverse("dojo:handbook_explanations"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Teach-back review")
        self.assertContains(response, "Second explanation.")
        self.assertContains(response, "First explanation.")
        self.assertContains(response, "Shaky")

        filtered = self.client.get(
            reverse("dojo:handbook_explanations"), {"rating": "shaky"}
        )
        self.assertContains(filtered, "No explanations saved yet.")

    def test_empty_explanation_is_removed(self):
        HandbookExplanation.objects.create(
            learner=Learner.local(),
            chapter_slug="forms",
            body="Temporary",
            rating="solid",
        )
        self.client.post(
            reverse("dojo:handbook_explanation", args=["forms"]), {"body": ""}
        )
        self.assertFalse(HandbookExplanation.objects.exists())

    def test_explanation_rejects_unknown_chapter(self):
        response = self.client.post(
            reverse("dojo:handbook_explanation", args=["not-real"]), {"body": "x"}
        )
        self.assertEqual(response.status_code, 404)


class HandbookLabTests(SeededTestCase):
    def test_labs_are_valid_and_linked_to_chapters(self):
        labs = load_labs()
        self.assertEqual(len(labs), 10)
        chapters = chapter_map()
        for lab in labs:
            self.assertIn(lab["chapter_slug"], chapters, lab["slug"])

    def test_lab_index_and_detail_render(self):
        response = self.client.get(reverse("dojo:handbook_labs"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Labs")
        self.assertContains(response, "CSRF-protected contact form")

        response = self.client.get(
            reverse("dojo:handbook_lab", args=["contact-form"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acceptance criteria")
        self.assertContains(response, "Show reference implementation")

    def test_lab_completion_toggle(self):
        url = reverse("dojo:handbook_lab_complete", args=["contact-form"])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        row = HandbookLabProgress.objects.get(lab_slug="contact-form")
        self.assertIsNotNone(row.completed_at)
        self.client.post(url)
        row.refresh_from_db()
        self.assertIsNone(row.completed_at)

    def test_lab_evidence_survives_completion_toggle(self):
        evidence_url = reverse("dojo:handbook_lab_evidence", args=["contact-form"])
        self.client.post(
            evidence_url,
            {
                "evidence_what": "A working contact page.",
                "evidence_decision": "Used a plain Form.",
                "evidence_test": "Bad email is rejected.",
                "evidence_url": "https://example.com/repo",
            },
        )
        row = HandbookLabProgress.objects.get(lab_slug="contact-form")
        self.assertTrue(row.has_evidence)
        self.client.post(reverse("dojo:handbook_lab_complete", args=["contact-form"]))
        row.refresh_from_db()
        self.assertIsNotNone(row.completed_at)
        self.assertTrue(row.has_evidence)

        detail = self.client.get(reverse("dojo:handbook_lab", args=["contact-form"]))
        self.assertContains(detail, "A working contact page.")
        export = self.client.get(reverse("dojo:handbook_lab_evidence_export"))
        self.assertIn(b"A working contact page.", export.content)


class DjangoFeatureTests(SeededTestCase):
    def test_feature_model_is_seeded(self):
        features = list(DjangoFeature.objects.all())
        self.assertGreaterEqual(len(features), 20)
        self.assertTrue(all(feature.url for feature in features))
        self.assertTrue(any(feature.is_new for feature in features))

    def test_feature_page_renders(self):
        response = self.client.get(reverse("dojo:features"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Everything")
        self.assertContains(response, "Django Labs")
        self.assertContains(response, "90-chapter Django handbook")


class DjangoTrackTests(SeededTestCase):
    def test_tracks_reference_existing_labs(self):
        tracks = load_tracks()
        self.assertEqual(len(tracks), 4)
        lab_slugs = {lab["slug"] for lab in load_labs()}
        for track in tracks:
            self.assertTrue(set(track["lab_slugs"]).issubset(lab_slugs))

    def test_track_index_and_detail_render(self):
        response = self.client.get(reverse("dojo:handbook_tracks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Project Tracks")
        self.assertContains(response, "Content platform")

        response = self.client.get(
            reverse("dojo:handbook_track", args=["content-platform"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Milestones")
        self.assertContains(response, "Track evidence")

    def test_track_completion_requires_all_labs(self):
        track = load_tracks()[0]
        url = reverse("dojo:handbook_track_complete", args=[track["slug"]])
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Complete every lab")
        self.assertFalse(DjangoTrackProgress.objects.filter(completed_at__isnull=False).exists())

        for lab_slug in track["lab_slugs"]:
            HandbookLabProgress.objects.create(
                learner=Learner.local(), lab_slug=lab_slug, completed_at=timezone.now()
            )
        self.client.post(url)
        self.assertTrue(
            DjangoTrackProgress.objects.filter(
                track_slug=track["slug"], completed_at__isnull=False
            ).exists()
        )

    def test_track_evidence_export(self):
        self.client.post(
            reverse("dojo:handbook_track_evidence", args=["content-platform"]),
            {"evidence_what": "A private content platform.", "evidence_test": "404 test."},
        )
        response = self.client.get(reverse("dojo:handbook_track_evidence_export"))
        self.assertIn(b"A private content platform.", response.content)


class DjangoCapstoneTests(SeededTestCase):
    def test_capstone_content_and_page(self):
        capstone = load_capstone()
        self.assertEqual(len(capstone["phases"]), 6)
        response = self.client.get(reverse("dojo:handbook_capstone"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Field Notes")
        self.assertContains(response, "Deployment checklist")

    def test_capstone_completion_requires_all_phases(self):
        capstone = load_capstone()
        response = self.client.post(
            reverse("dojo:handbook_capstone_complete"), follow=True
        )
        self.assertContains(response, "Complete every capstone phase")
        self.assertFalse(
            DjangoCapstoneProgress.objects.filter(completed_at__isnull=False).exists()
        )

        for phase in capstone["phases"]:
            self.client.post(
                reverse("dojo:handbook_capstone_phase", args=[phase["slug"]])
            )
        self.client.post(reverse("dojo:handbook_capstone_complete"))
        self.assertTrue(
            DjangoCapstoneProgress.objects.filter(completed_at__isnull=False).exists()
        )

    def test_capstone_defense_saves_and_exports(self):
        response = self.client.post(
            reverse("dojo:handbook_capstone_defense"),
            {
                "question_slug": "authorization",
                "answer": "The queryset filters by the current user.",
                "rating": "solid",
            },
        )
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse("dojo:handbook_capstone_defense"))
        self.assertContains(page, "The queryset filters by the current user.")
        export = self.client.get(reverse("dojo:handbook_capstone_defense_export"))
        self.assertIn(b"The queryset filters by the current user.", export.content)

    def test_capstone_evidence_exports(self):
        self.client.post(
            reverse("dojo:handbook_capstone_evidence"),
            {
                "evidence_what": "A deployed team notebook.",
                "evidence_test": "Private notes return 404.",
            },
        )
        response = self.client.get(reverse("dojo:handbook_capstone_evidence_export"))
        self.assertIn(b"A deployed team notebook.", response.content)


class HandbookFeedbackTests(SeededTestCase):
    def test_feedback_saves_and_updates(self):
        url = reverse("dojo:handbook_feedback", args=["forms"])
        response = self.client.post(url, {"helpful": "no", "comment": "More formsets."})
        self.assertEqual(response.status_code, 302)
        feedback = HandbookFeedback.objects.get(chapter_slug="forms")
        self.assertFalse(feedback.helpful)
        self.assertIn("formsets", feedback.comment)

        self.client.post(url, {"helpful": "yes", "comment": "Now it clicks."})
        feedback.refresh_from_db()
        self.assertTrue(feedback.helpful)

        chapter = self.client.get(reverse("dojo:handbook_chapter", args=["forms"]))
        self.assertContains(chapter, "Last vote")
        self.assertContains(chapter, "Now it clicks.")

    def test_feedback_rejects_unknown_chapter(self):
        response = self.client.post(
            reverse("dojo:handbook_feedback", args=["not-real"]), {"helpful": "yes"}
        )
        self.assertEqual(response.status_code, 404)

    def test_feedback_review_groups_needs_work(self):
        HandbookFeedback.objects.create(
            learner=Learner.local(),
            chapter_slug="forms",
            helpful=False,
            comment="Explain formsets earlier.",
        )
        response = self.client.get(reverse("dojo:handbook_feedback_review"))
        self.assertContains(response, "Triage queue")
        self.assertContains(response, "Forms")
        self.assertContains(response, "Explain formsets earlier.")

        filtered = self.client.get(
            reverse("dojo:handbook_feedback_review"), {"filtr": "needs-work"}
        )
        self.assertContains(filtered, "Explain formsets earlier.")

    def test_edit_next_queue_combines_feedback_and_gaps(self):
        HandbookFeedback.objects.create(
            learner=Learner.local(),
            chapter_slug="forms",
            helpful=False,
            comment="Add a real FormSet example.",
        )
        HandbookSearchLog.objects.create(query="custom lookup that does not exist", count=2)
        response = self.client.get(reverse("dojo:handbook_edit_next"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editorial queue")
        self.assertContains(response, "Add a real FormSet example.")
        self.assertContains(response, "custom lookup that does not exist")

    def test_upgrade_assistant_uses_version_ranges(self):
        response = self.client.get(
            reverse("dojo:handbook_upgrade"), {"from": "5.2", "to": "6.1"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upgrade assistant")
        self.assertContains(response, "5.2")
        self.assertContains(response, "6.1")
        self.assertContains(response, "Upgrade checklist")

    def test_gap_dashboard_lists_and_clears_queries(self):
        HandbookSearchLog.objects.create(query="custom lookup", count=3)
        response = self.client.get(reverse("dojo:handbook_gaps_page"))
        self.assertContains(response, "custom lookup")
        self.assertContains(response, "Most missed")

        response = self.client.post(reverse("dojo:handbook_gaps_clear"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(HandbookSearchLog.objects.exists())

    def test_diagram_renders_for_a_core_chapter(self):
        response = self.client.get(reverse("dojo:handbook_chapter", args=["views"]))
        self.assertContains(response, "hb-diagram")
        self.assertContains(response, "URL resolver")


class AdaptivePracticeTests(SeededTestCase):
    def _wrong_question(self, question):
        learner = Learner.local()
        attempt = create_attempt_from_questions(learner, [question.pk])
        attempt_question = attempt.attempt_questions.get()
        wrong = question.choices.filter(is_correct=False).first()
        record_answer(attempt_question, wrong)
        return attempt, question

    def test_weak_spots_track_questions_never_answered_correctly(self):
        question = Question.objects.get(key="htmx-b1")
        self._wrong_question(question)
        learner = Learner.local()
        self.assertEqual([item.pk for item in weak_spots(learner)], [question.pk])
        self.assertEqual(dashboard_stats(learner)["weak_spot_count"], 1)

    def test_weak_spot_disappears_after_a_correct_answer(self):
        question = Question.objects.get(key="typing-b1")
        self._wrong_question(question)
        learner = Learner.local()
        retry = create_attempt_from_questions(learner, [question.pk])
        attempt_question = retry.attempt_questions.get()
        record_answer(attempt_question, question.choices.get(is_correct=True))
        self.assertNotIn(question.pk, [item.pk for item in weak_spots(learner)])

    def test_home_offers_the_weak_spot_run(self):
        question = Question.objects.get(key="htmx-b3")
        self._wrong_question(question)
        response = self.client.get(reverse("dojo:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Review 1 weak spot")
        self.assertContains(response, reverse("dojo:weak_spots"))

    def test_weak_spot_view_creates_a_focused_attempt(self):
        question = Question.objects.get(key="htmx-b2")
        self._wrong_question(question)
        response = self.client.post(reverse("dojo:weak_spots"))
        self.assertEqual(response.status_code, 302)
        attempt = Attempt.objects.latest("id")
        self.assertEqual(attempt.length, 1)
        self.assertEqual(
            list(attempt.attempt_questions.values_list("question_id", flat=True)),
            [question.pk],
        )

    def test_weak_spot_view_is_safe_when_nothing_is_open(self):
        response = self.client.post(reverse("dojo:weak_spots"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No open weak spots")
        self.assertEqual(Attempt.objects.count(), 0)

    def test_retry_missed_creates_only_the_missed_questions(self):
        learner = Learner.local()
        questions = list(
            Question.objects.filter(topic__slug="htmx-server-driven-ui")[:2]
        )
        attempt = create_attempt_from_questions(
            learner,
            [question.pk for question in questions],
            topic=questions[0].topic,
            difficulty="beginner",
        )
        missed_ids = []
        for index, attempt_question in enumerate(attempt.attempt_questions.all()):
            if index == 0:
                choice = attempt_question.question.choices.get(is_correct=True)
            else:
                choice = attempt_question.question.choices.filter(is_correct=False).first()
                missed_ids.append(attempt_question.question_id)
            record_answer(attempt_question, choice)
        complete_attempt(attempt)

        results = self.client.get(reverse("dojo:quiz_results", args=[attempt.pk]))
        self.assertContains(results, "Retry 1 missed")

        response = self.client.post(reverse("dojo:retry_missed", args=[attempt.pk]))
        self.assertEqual(response.status_code, 302)
        retry = Attempt.objects.latest("id")
        self.assertEqual(
            list(retry.attempt_questions.values_list("question_id", flat=True)),
            missed_ids,
        )
        self.assertEqual(retry.topic, questions[0].topic)

    def test_retry_missed_rejects_a_perfect_attempt(self):
        learner = Learner.local()
        question = Question.objects.get(key="typing-b2")
        attempt = create_attempt_from_questions(learner, [question.pk])
        attempt_question = attempt.attempt_questions.get()
        record_answer(attempt_question, question.choices.get(is_correct=True))
        complete_attempt(attempt)
        with self.assertRaises(ValueError):
            create_retry_attempt(learner, attempt)

    def test_retry_missed_view_reports_nothing_to_retry(self):
        learner = Learner.local()
        question = Question.objects.get(key="typing-b3")
        attempt = create_attempt_from_questions(learner, [question.pk])
        attempt_question = attempt.attempt_questions.get()
        record_answer(attempt_question, question.choices.get(is_correct=True))
        complete_attempt(attempt)
        response = self.client.post(
            reverse("dojo:retry_missed", args=[attempt.pk]), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no missed questions")
        self.assertEqual(Attempt.objects.count(), 1)

    def test_create_weak_spot_attempt_raises_without_candidates(self):
        with self.assertRaises(ValueError):
            create_weak_spot_attempt(Learner.local())
