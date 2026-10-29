from io import BytesIO
from zipfile import ZipFile

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from dojo.models import Learner

from .content import load_bundles
from .models import (
    AiAttempt,
    AiFlashcard,
    AiFlashcardReview,
    AiLesson,
    AiLessonProgress,
    AiModule,
    AiProject,
    AiProjectCompletion,
    AiQuestion,
    AiTerm,
)
from .services import overall_stats, project_list


class AiSeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_ai", verbosity=0)


class AiContentTests(AiSeededTestCase):
    def test_content_counts_and_shape(self):
        self.assertEqual(len(load_bundles()), 8)
        self.assertEqual(AiModule.objects.count(), 8)
        self.assertEqual(AiLesson.objects.count(), 26)
        self.assertEqual(AiQuestion.objects.count(), 48)
        self.assertEqual(AiFlashcard.objects.count(), 40)
        self.assertEqual(AiProject.objects.count(), 8)
        self.assertEqual(AiTerm.objects.count(), 55)
        for module in AiModule.objects.prefetch_related("lessons", "questions", "flashcards"):
            expected_lessons = 5 if module.slug == "python-for-ai" else 3
            self.assertEqual(module.lessons.count(), expected_lessons, module.slug)
            self.assertEqual(module.questions.count(), 6, module.slug)
            self.assertEqual(module.flashcards.count(), 5, module.slug)
            for lesson in module.lessons.all():
                self.assertTrue(lesson.takeaway_list, lesson.slug)
                self.assertTrue(lesson.practice, lesson.slug)
            for difficulty in ("beginner", "intermediate", "advanced"):
                self.assertEqual(
                    module.questions.filter(difficulty=difficulty).count(), 2, module.slug
                )
            for question in module.questions.all():
                self.assertEqual(question.choices.count(), 4)
                self.assertEqual(
                    sum(1 for choice in question.choices.all() if choice.is_correct), 1
                )
                self.assertTrue(question.explanation)

    def test_seed_is_idempotent(self):
        lesson = AiLesson.objects.first()
        call_command("seed_ai", verbosity=0)
        self.assertEqual(AiModule.objects.count(), 8)
        self.assertEqual(AiLesson.objects.count(), 26)
        self.assertEqual(AiTerm.objects.count(), 55)
        self.assertEqual(AiLesson.objects.get(pk=lesson.pk).title, lesson.title)

    def test_every_project_links_to_a_module(self):
        for project in AiProject.objects.select_related("module"):
            self.assertIsNotNone(project.module)
            self.assertTrue(project.deliverable_list)
            self.assertTrue(project.milestone_list)
            self.assertTrue(project.rubric_list)


class AiPageTests(AiSeededTestCase):
    def test_home_path_and_navigation(self):
        for url in (
            reverse("ai_academy:home"),
            reverse("ai_academy:path"),
            reverse("ai_academy:projects"),
            reverse("ai_academy:flashcards_index"),
            reverse("ai_academy:progress"),
            reverse("ai_academy:career"),
            reverse("ai_academy:glossary"),
            reverse("ai_academy:search"),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

        response = self.client.get(reverse("ai_academy:home"))
        self.assertContains(response, "AI Academy")
        self.assertContains(response, "From curious beginner")
        self.assertContains(response, "Applied AI Engineer")
        self.assertContains(response, reverse("dojo:home"))
        self.assertContains(response, reverse("js_academy:home"))

    def test_module_and_lesson_pages(self):
        module = AiModule.objects.get(slug="ai-foundations")
        response = self.client.get(module.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The AI map")
        self.assertContains(response, "Study Buddy CLI")

        lesson = module.lessons.first()
        response = self.client.get(lesson.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Complete lesson and continue")
        self.assertContains(response, "Four labels, one stack")
        self.assertContains(response, "Key takeaways")
        self.assertContains(response, "Do this now")

    def test_python_for_ai_is_the_first_module_and_has_four_lessons(self):
        module = AiModule.objects.get(slug="python-for-ai")
        self.assertEqual(module.order, 0)
        self.assertEqual(module.lessons.count(), 5)
        response = self.client.get(module.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for AI")
        self.assertContains(response, "The Python data toolkit for AI")
        self.assertContains(response, "Notes-to-Dataset Pipeline")

    def test_python_cheatsheet_and_module_link(self):
        response = self.client.get(reverse("ai_academy:python_cheatsheet"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python for AI")
        self.assertContains(response, "pandas")
        self.assertContains(response, "pytest")

        module = AiModule.objects.get(slug="python-for-ai")
        response = self.client.get(module.get_absolute_url())
        self.assertContains(response, "Python cheat sheet")

    def test_projects_index_and_detail(self):
        response = self.client.get(reverse("ai_academy:projects"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Docs Answer Engine")
        self.assertContains(response, "AI Product Capstone")

        project = AiProject.objects.get(slug="docs-answer-engine")
        response = self.client.get(project.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Definition of done")
        self.assertContains(response, "Mark as shipped")
        self.assertContains(response, "Download .zip")

    def test_every_project_offers_a_downloadable_test_pack(self):
        for project in AiProject.objects.all():
            response = self.client.get(
                reverse("ai_academy:project_test_pack", args=[project.slug])
            )
            self.assertEqual(response.status_code, 200, project.slug)
            self.assertEqual(response["Content-Type"], "application/zip")
            self.assertIn(
                f"{project.slug}-test-pack.zip",
                response["Content-Disposition"],
            )
            archive = ZipFile(BytesIO(response.content))
            names = set(archive.namelist())
            self.assertIn(f"{project.slug}-test-pack/starter.py", names)
            self.assertIn(
                f"{project.slug}-test-pack/tests/test_acceptance.py",
                names,
            )
            self.assertIn(f"{project.slug}-test-pack/README.md", names)
            self.assertIn(f"{project.slug}-test-pack/requirements.txt", names)
            self.assertIn(f"{project.slug}-test-pack/conftest.py", names)

    def test_career_page_contains_roles_and_interview_topics(self):
        response = self.client.get(reverse("ai_academy:career"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LLM / GenAI Engineer")
        self.assertContains(response, "Machine Learning Engineer")
        self.assertContains(response, "AI Automation / Solutions Engineer")
        self.assertContains(response, "Interview map")


class AiProgressTests(AiSeededTestCase):
    def test_completing_a_lesson_updates_readiness(self):
        lesson = AiLesson.objects.first()
        before = overall_stats(Learner.local())["completed_lessons"]
        response = self.client.post(
            reverse(
                "ai_academy:complete_lesson",
                args=[lesson.module.slug, lesson.slug],
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AiLessonProgress.objects.count(), 1)
        after = overall_stats(Learner.local())["completed_lessons"]
        self.assertEqual(after, before + 1)

    def test_completion_is_idempotent(self):
        lesson = AiLesson.objects.first()
        url = reverse(
            "ai_academy:complete_lesson", args=[lesson.module.slug, lesson.slug]
        )
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(AiLessonProgress.objects.count(), 1)

    def test_project_completion_and_update(self):
        project = AiProject.objects.get(slug="study-buddy-cli")
        response = self.client.post(
            reverse("ai_academy:project_complete", args=[project.slug]),
            {
                "repo_url": "https://github.com/example/study-buddy",
                "demo_url": "https://example.com/demo",
                "notes": "The offline fallback was the hardest part.",
            },
        )
        self.assertEqual(response.status_code, 302)
        completion = AiProjectCompletion.objects.get(project=project)
        self.assertEqual(completion.repo_url, "https://github.com/example/study-buddy")
        self.assertIn(
            project,
            [row["project"] for row in project_list(Learner.local()) if row["completed"]],
        )

        self.client.post(
            reverse("ai_academy:project_complete", args=[project.slug]),
            {"notes": "Updated notes."},
        )
        completion.refresh_from_db()
        self.assertEqual(completion.notes, "Updated notes.")
        self.assertEqual(AiProjectCompletion.objects.count(), 1)


class AiQuizTests(AiSeededTestCase):
    def _start(self):
        module = AiModule.objects.get(slug="ai-foundations")
        response = self.client.post(reverse("ai_academy:quiz_start", args=[module.slug]))
        self.assertEqual(response.status_code, 302)
        return AiAttempt.objects.latest("id")

    def test_quiz_has_all_module_questions(self):
        attempt = self._start()
        self.assertEqual(attempt.length, 6)
        self.assertEqual(attempt.attempt_questions.count(), 6)

    def test_complete_quiz_and_results(self):
        attempt = self._start()
        url = reverse("ai_academy:quiz", args=[attempt.pk])
        for index in range(attempt.length):
            attempt.refresh_from_db()
            attempt_question = attempt.current_attempt_question()
            correct = attempt_question.question.choices.get(is_correct=True)
            self.client.post(url, {"action": "answer", "choice": correct.pk})
            response = self.client.post(url, {"action": "next"})
            if index < attempt.length - 1:
                self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertIsNotNone(attempt.completed_at)
        self.assertEqual(attempt.score_percent, 100)
        response = self.client.get(reverse("ai_academy:quiz_results", args=[attempt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "100")
        self.assertContains(response, "Every answer, explained.")


class AiFlashcardTests(AiSeededTestCase):
    def test_index_and_study_page(self):
        response = self.client.get(reverse("ai_academy:flashcards_index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Concept cards")

        module = AiModule.objects.get(slug="ai-foundations")
        response = self.client.get(
            reverse("ai_academy:flashcards", args=[module.slug]) + "?reveal=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["reveal"])

    def test_rate_card_creates_review(self):
        module = AiModule.objects.get(slug="ai-foundations")
        card = module.flashcards.first()
        response = self.client.post(
            reverse("ai_academy:flashcards_rate", args=[module.slug, card.pk]),
            {"rating": "good"},
        )
        self.assertEqual(response.status_code, 302)
        review = AiFlashcardReview.objects.get(flashcard=card)
        self.assertEqual(review.interval_days, 3)

    def test_invalid_rating_does_not_create_review(self):
        module = AiModule.objects.get(slug="ai-foundations")
        card = module.flashcards.first()
        self.client.post(
            reverse("ai_academy:flashcards_rate", args=[module.slug, card.pk]),
            {"rating": "impossible"},
        )
        self.assertFalse(AiFlashcardReview.objects.exists())


class AiGlossarySearchTests(AiSeededTestCase):
    def test_glossary_lists_terms_and_categories(self):
        response = self.client.get(reverse("ai_academy:glossary"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Artificial intelligence")
        self.assertContains(response, "Prompt injection")
        self.assertContains(response, "All")
        self.assertEqual(response.context["result_count"], 55)

    def test_glossary_search_and_category_filter(self):
        response = self.client.get(reverse("ai_academy:glossary"), {"q": "retrieval"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RAG")
        self.assertContains(response, "retrieval")

        response = self.client.get(
            reverse("ai_academy:glossary"), {"category": "Safety"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prompt injection")
        self.assertNotContains(response, "Gradient descent")

    def test_search_finds_lessons_projects_and_terms(self):
        response = self.client.get(reverse("ai_academy:search"), {"q": "RAG"})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.context["counts"]["lessons"], 1)
        self.assertGreaterEqual(response.context["counts"]["terms"], 1)
        self.assertContains(response, "RAG that answers with evidence")
        self.assertContains(response, "Docs Answer Engine")
        self.assertNotContains(response, "Churn Dataset Audit")

    def test_search_empty_and_short_queries(self):
        response = self.client.get(reverse("ai_academy:search"), {"q": "zzzz-not-real"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_count"], 0)
        self.assertContains(response, "Nothing matched")

        response = self.client.get(reverse("ai_academy:search"), {"q": "a"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["searched"])
