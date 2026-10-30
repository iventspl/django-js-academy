from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dojo.models import Learner

from .content import load_bundles
from .projects import PROJECTS
from .models import (
    JsChallenge,
    JsChallengeCompletion,
    JsComponent,
    JsFact,
    JsInterviewQuestion,
    JsTerm,
    JsAttempt,
    JsFlashcard,
    JsFlashcardReview,
    JsLesson,
    JsLessonNote,
    JsLessonProgress,
    JsModule,
    JsProjectStepProgress,
    JsQuestion,
)


class SeededJsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_js", verbosity=0)


class JsContentTests(SeededJsTestCase):
    def test_content_counts(self):
        self.assertEqual(len(load_bundles()), 22)
        self.assertEqual(JsModule.objects.count(), 22)
        self.assertEqual(JsLesson.objects.count(), 116)
        self.assertEqual(JsQuestion.objects.count(), 152)
        self.assertEqual(JsFlashcard.objects.count(), 140)
        self.assertEqual(JsComponent.objects.count(), 13)

    def test_every_module_has_expected_lessons_questions_and_cards(self):
        for module in JsModule.objects.prefetch_related(
            "lessons", "questions", "flashcards"
        ):
            if module.slug == "fundamenty-js":
                expected_lessons = 7
            elif module.slug == "mvc-w-js":
                expected_lessons = 6
            elif module.slug == "przyklady-z-zycia":
                expected_lessons = 8
            else:
                expected_lessons = 5
            self.assertEqual(module.lessons.count(), expected_lessons, module.slug)
            if module.slug == "mistrzostwo-js":
                self.assertEqual(module.questions.count(), 15, module.slug)
                self.assertEqual(module.flashcards.count(), 25, module.slug)
            elif module.slug == "przyklady-z-zycia":
                self.assertEqual(module.questions.count(), 8, module.slug)
                self.assertEqual(module.flashcards.count(), 8, module.slug)
            elif module.slug == "fundamenty-js":
                self.assertEqual(module.questions.count(), 13, module.slug)
                self.assertEqual(module.flashcards.count(), 11, module.slug)
            elif module.slug == "mvc-w-js":
                self.assertEqual(module.questions.count(), 8, module.slug)
                self.assertEqual(module.flashcards.count(), 6, module.slug)
            else:
                self.assertEqual(module.questions.count(), 6, module.slug)
                self.assertEqual(module.flashcards.count(), 5, module.slug)
            for question in module.questions.prefetch_related("choices"):
                self.assertEqual(question.choices.count(), 4)
                self.assertEqual(
                    sum(1 for choice in question.choices.all() if choice.is_correct),
                    1,
                )
                self.assertTrue(question.explanation)

    def test_live_demos_are_attached_and_sandboxed(self):
        demo_lessons = JsLesson.objects.exclude(live_demo_html="")
        self.assertEqual(demo_lessons.count(), 13)
        for lesson in demo_lessons:
            self.assertTrue(lesson.demo_title)
            self.assertTrue(lesson.demo_description)
        lesson = demo_lessons.first()
        response = self.client.get(lesson.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Demo na żywo")
        self.assertContains(response, 'sandbox="allow-scripts"')
        self.assertContains(response, lesson.demo_title)

    def test_seed_is_idempotent(self):
        lesson = JsLesson.objects.first()
        call_command("seed_js", verbosity=0)
        self.assertEqual(JsModule.objects.count(), 22)
        self.assertEqual(JsLesson.objects.count(), 116)
        self.assertEqual(JsLesson.objects.get(pk=lesson.pk).title, lesson.title)

    def test_lessons_are_in_curriculum_order(self):
        modules = list(JsModule.objects.all())
        self.assertEqual(
            [module.slug for module in modules],
            [
                "fundamenty-js",
                "nowoczesny-js",
                "dom-przegladarka",
                "typescript",
                "react-podstawy",
                "react-architektura",
                "react-native",
                "testy-publikacja",
                "wzorce-frontendu",
                "struktury-danych",
                "node-narzedzia",
                "react-projekt",
                "react-native-produkcja",
                "javascript-ai",
                "bezpieczenstwo-wydajnosc",
                "mistrzostwo-js",
                "ai-praca",
                "mvc-w-js",
                "wzorce-projektowe",
                "web-api",
                "debugging",
                "przyklady-z-zycia",
            ],
        )


class JsPageTests(SeededJsTestCase):
    def test_home_and_tab_switcher_are_polish(self):
        response = self.client.get(reverse("js_academy:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="pl"')
        self.assertContains(response, "JS Akademia")
        self.assertContains(response, "JavaScript")
        self.assertContains(response, "Kontynuuj")
        self.assertContains(response, reverse("dojo:home"))

    def test_path_page(self):
        response = self.client.get(reverse("js_academy:path"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ścieżka")
        self.assertContains(response, "React Native")
        self.assertContains(response, "Fundamenty JavaScript")

    def test_module_and_lesson_pages(self):
        module = JsModule.objects.get(slug="fundamenty-js")
        lesson = module.lessons.first()
        response = self.client.get(module.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, module.project_title)
        response = self.client.get(lesson.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ukończ lekcję")

    def test_flashcards_and_progress_pages(self):
        for url in (
            reverse("js_academy:flashcards_index"),
            reverse("js_academy:flashcards_review"),
            reverse("js_academy:progress"),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_practical_module_and_plain_glossary(self):
        response = self.client.get(
            reverse("js_academy:module", args=["przyklady-z-zycia"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Koszyk zakupowy bez błędów")
        self.assertContains(response, "Aplikacja nawyków")
        lesson = self.client.get(
            reverse(
                "js_academy:lesson",
                args=["przyklady-z-zycia", "koszyk-zakupowy"],
            )
        )
        self.assertContains(lesson, "addToCart")
        response = self.client.get(reverse("js_academy:glossary"))
        self.assertContains(response, "localStorage")
        self.assertContains(response, "Mała pamięć w przeglądarce")

    def test_unknown_module_returns_404(self):
        response = self.client.get("/js/nie-ma-takiego-modulu/")
        self.assertEqual(response.status_code, 404)


class JsLessonProgressTests(SeededJsTestCase):
    def test_complete_lesson_is_idempotent_and_redirects_to_next(self):
        module = JsModule.objects.get(slug="fundamenty-js")
        lesson = module.lessons.first()
        url = reverse(
            "js_academy:complete_lesson",
            args=[module.slug, lesson.slug],
        )
        response = self.client.post(url, {"next": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JsLessonProgress.objects.count(), 1)
        response = self.client.post(url, {"next": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JsLessonProgress.objects.count(), 1)

    def test_progress_makes_next_lesson_skip_completed(self):
        module = JsModule.objects.get(slug="fundamenty-js")
        first = module.lessons.first()
        self.client.post(
            reverse("js_academy:complete_lesson", args=[module.slug, first.slug])
        )
        response = self.client.get(reverse("js_academy:home"))
        self.assertContains(response, module.lessons.all()[1].title)


class JsQuizTests(SeededJsTestCase):
    def _start(self):
        module = JsModule.objects.get(slug="fundamenty-js")
        response = self.client.post(reverse("js_academy:quiz_start", args=[module.slug]))
        self.assertEqual(response.status_code, 302)
        return JsAttempt.objects.latest("id")

    def test_start_creates_attempt_for_all_module_questions(self):
        attempt = self._start()
        self.assertEqual(attempt.length, attempt.module.questions.count())
        self.assertEqual(attempt.attempt_questions.count(), attempt.length)

    def test_complete_quiz_and_results(self):
        attempt = self._start()
        url = attempt.get_absolute_url()
        for index in range(attempt.length):
            attempt.refresh_from_db()
            aq = attempt.current_attempt_question()
            correct = aq.question.choices.get(is_correct=True)
            self.client.post(url, {"action": "answer", "choice": correct.pk})
            response = self.client.post(url, {"action": "next"})
            if index < attempt.length - 1:
                self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertIsNotNone(attempt.completed_at)
        self.assertEqual(attempt.score_percent, 100)
        response = self.client.get(
            reverse("js_academy:quiz_results", args=[attempt.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "100")
        self.assertContains(response, "Każde pytanie")

    def test_wrong_answer_shows_explanation(self):
        attempt = self._start()
        aq = attempt.current_attempt_question()
        wrong = aq.question.choices.filter(is_correct=False).first()
        response = self.client.post(
            attempt.get_absolute_url(),
            {"action": "answer", "choice": wrong.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jeszcze nie.")
        self.assertContains(response, "Dlaczego")

    def test_attempt_is_scoped_to_learner(self):
        attempt = self._start()
        other = Learner.objects.create(pk=2, name="Inny")
        attempt.learner = other
        attempt.save(update_fields=["learner"])
        response = self.client.get(attempt.get_absolute_url())
        self.assertEqual(response.status_code, 404)


class JsFlashcardTests(SeededJsTestCase):
    def test_rate_schedules_card(self):
        card = JsFlashcard.objects.first()
        response = self.client.post(
            reverse(
                "js_academy:flashcards_rate",
                args=[card.module.slug, card.pk],
            ),
            {"rating": "good"},
        )
        self.assertEqual(response.status_code, 302)
        review = JsFlashcardReview.objects.get(flashcard=card)
        self.assertEqual(review.interval_days, 3)
        self.assertEqual(review.due_date, timezone.localdate() + timedelta(days=3))

    def test_review_today_removes_card_from_all_queue(self):
        card = JsFlashcard.objects.first()
        card_review = JsFlashcardReview.objects.create(
            learner=Learner.local(),
            flashcard=card,
        )
        card_review.review("again")
        response = self.client.get(reverse("js_academy:flashcards_review"))
        self.assertEqual(response.status_code, 200)

    def test_rating_submit_keeps_submit_button_enabled(self):
        """A disabled submitter would omit the rating from POST data."""
        from django.conf import settings

        js = (settings.BASE_DIR / "dojo" / "static" / "dojo" / "app.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("button.disabled = true", js)
        self.assertIn('form.dataset.submitting = "true"', js)


class JsChallengeTests(SeededJsTestCase):
    def test_challenge_index_and_detail(self):
        self.assertEqual(JsChallenge.objects.count(), 31)
        response = self.client.get(reverse("js_academy:challenges"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "31")
        challenge = JsChallenge.objects.get(slug="sum-array")
        response = self.client.get(challenge.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sandbox="allow-scripts"')
        self.assertContains(response, "Uruchom testy")
        self.assertContains(response, "sumuje dodatnie")

    def test_challenge_filter(self):
        response = self.client.get(reverse("js_academy:challenges"), {"difficulty": "advanced"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Two Sum")
        self.assertNotContains(response, "FizzBuzz")

    def test_challenge_completion_is_idempotent(self):
        challenge = JsChallenge.objects.get(slug="sum-array")
        response = self.client.post(
            reverse("js_academy:challenge_complete", args=[challenge.slug])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JsChallengeCompletion.objects.count(), 1)
        response = self.client.post(
            reverse("js_academy:challenge_complete", args=[challenge.slug])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JsChallengeCompletion.objects.count(), 1)


class JsKnowledgeTests(SeededJsTestCase):
    def test_knowledge_counts_and_pages(self):
        self.assertEqual(JsFact.objects.count(), 36)
        self.assertEqual(JsTerm.objects.count(), 64)
        self.assertEqual(JsInterviewQuestion.objects.count(), 30)
        for url in (
            reverse("js_academy:knowledge"),
            reverse("js_academy:facts"),
            reverse("js_academy:glossary"),
            reverse("js_academy:interview"),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_glossary_search_and_interview_filter(self):
        response = self.client.get(reverse("js_academy:glossary"), {"q": "domk"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Domknięcie")
        response = self.client.get(
            reverse("js_academy:interview"), {"difficulty": "advanced"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zaawansowany")


class JsGamificationTests(SeededJsTestCase):
    def test_xp_and_streak_count_real_activity(self):
        from .services import gamification

        learner = Learner.local()
        empty = gamification(learner)
        self.assertEqual(empty["xp"], 0)
        self.assertEqual(empty["level_name"], "Nowicjusz")
        lesson = JsLesson.objects.first()
        JsLessonProgress.objects.create(learner=learner, lesson=lesson)
        challenge = JsChallenge.objects.get(slug="sum-array")
        JsChallengeCompletion.objects.create(learner=learner, challenge=challenge)
        result = gamification(learner)
        self.assertEqual(result["xp"], 30)
        self.assertEqual(result["challenge_count"], 1)
        self.assertEqual(result["streak"], 1)


class JsPlaygroundTests(SeededJsTestCase):
    def test_playground_is_sandboxed(self):
        response = self.client.get(reverse("js_academy:playground"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sandbox="allow-scripts"')
        self.assertContains(response, "Piaskownica")
        self.assertContains(response, "Uruchom")

    def test_async_challenge_is_available(self):
        response = self.client.get(
            reverse("js_academy:challenge", args=["retry-task"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "succeedAt")
        self.assertContains(response, "await solve")


class JsSearchAndAchievementTests(SeededJsTestCase):
    def test_search_finds_mvc_and_promises(self):
        response = self.client.get(reverse("js_academy:search"), {"q": "currentView"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "MVC w JavaScript")
        response = self.client.get(reverse("js_academy:search"), {"q": "promise"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Promise")
        self.assertContains(response, "wyników")

    def test_search_empty_state(self):
        response = self.client.get(reverse("js_academy:search"), {"q": "xyz-nie-ma"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Brak wyników")

    def test_achievements_track_first_lesson(self):
        from .services import achievements

        learner = Learner.local()
        lesson = JsLesson.objects.first()
        JsLessonProgress.objects.create(learner=learner, lesson=lesson)
        items = achievements(learner)
        earned = {item["key"] for item in items if item["earned"]}
        self.assertIn("first-step", earned)
        self.assertNotIn("ten-lessons", earned)
        self.assertEqual(len(items), 8)


class JsMvcTests(SeededJsTestCase):
    def test_mvc_guide_has_state_and_selector_concepts(self):
        response = self.client.get(reverse("js_academy:mvc_guide"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "currentView")
        self.assertContains(response, "currentSort")
        self.assertContains(response, "currentQuery")
        self.assertContains(response, "selectProducts")
        self.assertContains(response, "Parameter explosion")

    def test_mvc_module_and_component_are_linked(self):
        response = self.client.get(reverse("js_academy:module", args=["mvc-w-js"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "currentView")
        response = self.client.get(
            reverse("js_academy:component", args=["mvc-product-browser"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "currentSort")
        self.assertContains(response, 'sandbox="allow-scripts"')


class JsComponentTests(SeededJsTestCase):
    def test_component_index_and_detail(self):
        self.assertEqual(JsComponent.objects.count(), 13)
        response = self.client.get(reverse("js_academy:components"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "13")
        component = JsComponent.objects.get(key="product-cart")
        response = self.client.get(component.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sandbox="allow-scripts"')
        self.assertContains(response, "HTML")
        self.assertContains(response, "CSS")
        self.assertContains(response, "JavaScript")
        self.assertContains(response, "Intl.NumberFormat")

    def test_component_category_filter(self):
        response = self.client.get(
            reverse("js_academy:components"), {"category": "Dostępność"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dostępne zakładki")
        self.assertNotContains(response, "Filtr produktów i koszyk")

    def test_preview_is_complete_document(self):
        from .components import build_component_preview

        component = JsComponent.objects.get(key="drag-drop-list")
        preview = build_component_preview(component)
        self.assertTrue(preview.startswith("<!doctype html>"))
        self.assertIn("dragstart", preview)
        self.assertIn("</html>", preview)


class JsAiCareerTests(SeededJsTestCase):
    def test_ai_career_page_has_facts_and_sources(self):
        response = self.client.get(reverse("js_academy:ai_career"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "29%")
        self.assertContains(response, "66%")
        self.assertContains(response, "Veracode")
        self.assertContains(response, "BLS")
        self.assertContains(response, "Źródła")
        self.assertContains(response, "Dane sprawdzone")

    def test_ai_module_links_to_career_section(self):
        response = self.client.get(reverse("js_academy:module", args=["ai-praca"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fakty, liczby i źródła")

    def test_every_career_fact_has_https_source(self):
        from .career import FACTS, SOURCES

        self.assertGreaterEqual(len(FACTS), 8)
        for fact in FACTS:
            self.assertTrue(fact["url"].startswith("https://"), fact["label"])
        for source in SOURCES:
            self.assertTrue(source["url"].startswith("https://"), source["label"])


class JsProjectWalkthroughTests(SeededJsTestCase):
    def test_two_projects_have_eight_steps_with_hints_and_answers(self):
        self.assertEqual(len(PROJECTS), 2)
        for project in PROJECTS:
            self.assertGreaterEqual(len(project["steps"]), 8)
            self.assertGreaterEqual(len(project["files"]), 8)
            self.assertIn("data-app", project["shell"])
            self.assertTrue(project["preview"].endswith(".png"))
            for step in project["steps"]:
                self.assertGreaterEqual(len(step["hints"]), 2)
                self.assertTrue(step["answer"].strip())
                self.assertTrue(step["filename"])
                self.assertIn("//", step["answer"])

    def test_project_index_and_detail_render_hidden_hints_and_answers(self):
        response = self.client.get(reverse("js_academy:projects"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sklep internetowy")
        self.assertContains(response, "Movie HUB")
        response = self.client.get(
            reverse("js_academy:project", args=["sklep-internetowy"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Podpowiedź 1")
        self.assertContains(response, "Pełne rozwiązanie tego kroku")
        self.assertContains(response, "js-project-answer")
        self.assertContains(response, "Tak będzie wyglądać aplikacja")
        self.assertContains(response, "shop-preview.png")
        self.assertNotContains(response, "innerHTML =")

    def test_project_step_completion_toggles(self):
        url = reverse(
            "js_academy:project_step_complete",
            args=["movie-hub", "model-filmu"],
        )
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            JsProjectStepProgress.objects.filter(
                project_slug="movie-hub", step_slug="model-filmu"
            ).exists()
        )
        self.client.post(url)
        self.assertFalse(
            JsProjectStepProgress.objects.filter(
                project_slug="movie-hub", step_slug="model-filmu"
            ).exists()
        )

    def test_project_is_searchable(self):
        response = self.client.get(reverse("js_academy:search"), {"q": "Movie HUB"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Projekty")
        self.assertContains(response, "Movie HUB")


class JsLearnerToolsTests(SeededJsTestCase):
    def test_save_and_clear_note(self):
        lesson = JsLesson.objects.first()
        url = reverse("js_academy:save_note", args=[lesson.module.slug, lesson.slug])
        response = self.client.post(url, {"note": "Moja notatka", "bookmarked": "on"})
        self.assertEqual(response.status_code, 302)
        note = JsLessonNote.objects.get(lesson=lesson)
        self.assertEqual(note.body, "Moja notatka")
        self.assertTrue(note.is_bookmarked)
        response = self.client.get(reverse("js_academy:notes"))
        self.assertContains(response, "Moja notatka")
        self.client.post(url, {"note": ""})
        self.assertFalse(JsLessonNote.objects.filter(lesson=lesson).exists())

    def test_progress_export_is_downloadable(self):
        response = self.client.get(reverse("js_academy:progress_export"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/markdown; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_retry_missed_creates_smaller_attempt(self):
        module = JsModule.objects.get(slug="fundamenty-js")
        self.client.post(reverse("js_academy:quiz_start", args=[module.slug]))
        attempt = JsAttempt.objects.latest("id")
        for position in range(attempt.length):
            attempt.refresh_from_db()
            aq = attempt.current_attempt_question()
            choice = (
                aq.question.choices.get(is_correct=True)
                if position != 0
                else aq.question.choices.filter(is_correct=False).first()
            )
            self.client.post(attempt.get_absolute_url(), {"action": "answer", "choice": choice.pk})
            self.client.post(attempt.get_absolute_url(), {"action": "next"})
        attempt.refresh_from_db()
        response = self.client.post(reverse("js_academy:retry_missed", args=[attempt.pk]))
        self.assertEqual(response.status_code, 302)
        retry = JsAttempt.objects.latest("id")
        self.assertEqual(retry.length, 1)
        response = self.client.post(reverse("js_academy:weak_spots"))
        self.assertEqual(response.status_code, 302)
        weak = JsAttempt.objects.latest("id")
        self.assertEqual(weak.length, 1)

    def test_progress_reset_clears_learning_progress(self):
        module = JsModule.objects.get(slug="fundamenty-js")
        self.client.post(reverse("js_academy:quiz_start", args=[module.slug]))
        JsProjectStepProgress.objects.create(
            learner=Learner.local(), project_slug="movie-hub", step_slug="model-filmu"
        )
        self.client.post(reverse("js_academy:progress_reset"))
        self.assertEqual(JsAttempt.objects.count(), 0)
        self.assertEqual(JsLessonProgress.objects.count(), 0)
        self.assertEqual(JsProjectStepProgress.objects.count(), 0)


class JsAdminAndCommandsTests(SeededJsTestCase):
    def test_seed_if_changed_skips(self):
        from io import StringIO

        out = StringIO()
        call_command("seed_js", "--if-changed", stdout=out)
        self.assertIn("bez zmian", out.getvalue())
