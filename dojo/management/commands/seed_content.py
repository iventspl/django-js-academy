from django.core.management.base import BaseCommand, CommandError

from dojo.content import (
    ContentError,
    content_fingerprint,
    record_fingerprint,
    seed_content,
    stored_fingerprint,
    validate_content,
)
from dojo.field_guide import GuideError, seed_guide, validate_guide
from dojo.models import Cheatsheet, Question


class Command(BaseCommand):
    help = "Validate all JSON bundles and upsert them into the database (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Validate only; do not write to the database.",
        )
        parser.add_argument(
            "--if-changed",
            action="store_true",
            help="Skip when the JSON fingerprint matches the last successful seed.",
        )

    def handle(self, *args, **options):
        try:
            if options["check"]:
                content = validate_content()
                guide = validate_guide()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Content OK: {content['topics']} topics, "
                        f"{content['questions']} questions, "
                        f"{content['flashcards']} flashcards, "
                        f"{guide['cheatsheets']} recipes, "
                        f"{guide['blueprints']} blueprints, "
                        f"{guide['architecture_cases']} architecture cases, "
                        f"{guide['release_notes']} release notes."
                    )
                )
                return

            if (
                options["if_changed"]
                and Question.objects.exists()
                and Cheatsheet.objects.exists()
                and stored_fingerprint() == content_fingerprint()
            ):
                self.stdout.write("Content is unchanged; skipping seed.")
                return

            content = seed_content()
            guide = seed_guide()
            record_fingerprint()
        except (ContentError, GuideError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded "
                f"{content['topics']} topics, {content['questions']} questions, "
                f"{content['flashcards']} flashcards, "
                f"{guide['cheatsheets']} recipes, "
                f"{guide['blueprints']} blueprints, "
                f"{guide['architecture_cases']} architecture cases, "
                f"{guide['release_notes']} release notes "
                f"({content['created_questions']} new questions, "
                f"{content['created_flashcards']} new cards, "
                f"{guide['created_cheatsheets']} new recipes)."
            )
        )
