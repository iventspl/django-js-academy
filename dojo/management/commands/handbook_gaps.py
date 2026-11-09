"""Report local handbook searches that returned no results."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from dojo.models import HandbookSearchLog


class Command(BaseCommand):
    help = "Show zero-result handbook searches so content gaps are measurable."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete the logged gaps after printing them.",
        )

    def handle(self, *args, **options):
        queryset = HandbookSearchLog.objects.order_by("-count", "-last_seen")
        rows = list(queryset[: options["limit"]])
        if not rows:
            self.stdout.write("No zero-result searches recorded yet.")
            return

        self.stdout.write(f"{'count':>5}  {'last seen':<16}  query")
        for row in rows:
            seen = row.last_seen.strftime("%Y-%m-%d %H:%M")
            self.stdout.write(f"{row.count:>5}  {seen:<16}  {row.query}")

        if options["clear"]:
            deleted = HandbookSearchLog.objects.all().delete()[0]
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} logged gap(s)."))
