from django.core.management.base import BaseCommand, CommandError

from js_academy.content import (
    ContentError,
    content_fingerprint,
    record_fingerprint,
    seed_content,
    stored_fingerprint,
    validate_content,
)
from js_academy.models import JsModule


class Command(BaseCommand):
    help = "Waliduje i ładuje polskie treści JS Akademii (idempotentnie)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Tylko walidacja; bez zapisu do bazy.",
        )
        parser.add_argument(
            "--if-changed",
            action="store_true",
            help="Pomiń, jeśli fingerprint treści jest aktualny.",
        )

    def handle(self, *args, **options):
        try:
            if options["check"]:
                summary = validate_content()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Treści JS OK: {summary['modules']} modułów, "
                        f"{summary['lessons']} lekcji, "
                        f"{summary['questions']} pytań, "
                        f"{summary['flashcards']} fiszek, "
                        f"{summary['demos']} dem, "
                        f"{summary['facts']} ciekawostek, "
                        f"{summary['terms']} pojęć, "
                        f"{summary['interview']} pytań rekrutacyjnych, "
                        f"{summary['challenges']} wyzwań, {summary['components']} komponentów."
                    )
                )
                return

            if (
                options["if_changed"]
                and JsModule.objects.exists()
                and stored_fingerprint() == content_fingerprint()
            ):
                self.stdout.write("Treści JS bez zmian; pomijam seed.")
                return

            summary = seed_content()
            record_fingerprint()
        except ContentError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Załadowano {summary['modules']} modułów, "
                f"{summary['lessons']} lekcji, {summary['questions']} pytań, "
                f"{summary['flashcards']} fiszek, {summary['demos']} dem, "
                f"{summary['facts']} ciekawostek, {summary['terms']} pojęć, "
                f"{summary['interview']} pytań, {summary['challenges']} wyzwań, {summary['components']} komponentów "
                f"({summary['created_lessons']} nowych lekcji, "
                f"{summary['created_questions']} nowych pytań)."
            )
        )
