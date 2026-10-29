from django.core.management.base import BaseCommand, CommandError

from ai_academy.content import (
    ContentError,
    content_fingerprint,
    record_fingerprint,
    seed_content,
    stored_fingerprint,
    validate_content,
)
from ai_academy.models import AiModule


class Command(BaseCommand):
    help = "Validate and seed the AI Academy curriculum (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--check", action="store_true", help="Validate only.")
        parser.add_argument(
            "--if-changed",
            action="store_true",
            help="Skip when the content fingerprint matches the last seed.",
        )

    def handle(self, *args, **options):
        try:
            if options["check"]:
                summary = validate_content()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"AI content OK: {summary['modules']} modules, "
                        f"{summary['lessons']} lessons, {summary['questions']} questions, "
                        f"{summary['flashcards']} flashcards, {summary['projects']} projects, "
                        f"{summary['terms']} glossary terms."
                    )
                )
                return

            if (
                options["if_changed"]
                and AiModule.objects.exists()
                and stored_fingerprint() == content_fingerprint()
            ):
                self.stdout.write("AI content unchanged; skipping seed.")
                return

            summary = seed_content()
            record_fingerprint()
        except ContentError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {summary['modules']} modules, {summary['lessons']} lessons, "
                f"{summary['questions']} questions, {summary['flashcards']} flashcards, "
                f"{summary['projects']} projects, {summary['terms']} glossary terms "
                f"({summary['created_lessons']} new lessons, "
                f"{summary['created_projects']} new projects, "
                f"{summary['created_terms']} new terms)."
            )
        )
