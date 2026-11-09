"""Validate the Django handbook content, review dates and official links."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

from django.core.management.base import BaseCommand, CommandError

from dojo.handbook import (
    HANDBOOK_DIR,
    STALE_AFTER_DAYS,
    HandbookError,
    load_chapters,
    symbol_index,
)


class Command(BaseCommand):
    help = "Validate handbook JSON, review dates, related links and optionally official URLs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--links",
            action="store_true",
            help="Also request every official/reference URL (network required).",
        )
        parser.add_argument(
            "--max-age",
            type=int,
            default=STALE_AFTER_DAYS,
            help="Warn when a chapter has not been reviewed for this many days.",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=8.0,
            help="Timeout in seconds for each link check.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Treat stale chapters and dead links as errors.",
        )

    def handle(self, *args, **options):
        try:
            chapters = load_chapters()
            symbols = symbol_index()
        except HandbookError as exc:
            raise CommandError(str(exc)) from exc

        warnings: list[str] = []
        errors: list[str] = []
        official_urls: set[str] = set()

        for chapter in chapters:
            if chapter["review_age_days"] > options["max_age"]:
                warnings.append(
                    f"{chapter['slug']}: last reviewed {chapter['reviewed_on']} "
                    f"({chapter['review_age_days']} days ago)"
                )
            official_urls.add(chapter["official"])
            for section in chapter["sections"]:
                if section["reference"]:
                    official_urls.add(section["reference"])
                if not section["code"] and not section["table"] and not section["body"]:
                    errors.append(f"{chapter['slug']}#{section['id']}: empty section")

        if options["links"]:
            for index, url in enumerate(sorted(official_urls)):
                if index:
                    time.sleep(0.15)
                if not _url_ok(url, options["timeout"]):
                    errors.append(f"dead link: {url}")

        section_count = sum(len(chapter["sections"]) for chapter in chapters)
        self.stdout.write(f"Handbook: {HANDBOOK_DIR}")
        self.stdout.write(
            f"Chapters: {len(chapters)} · sections: {section_count} · symbols: {len(symbols)} "
            f"· official URLs: {len(official_urls)}"
        )

        for warning in warnings:
            self.stdout.write(self.style.WARNING(f"warning: {warning}"))
        for error in errors:
            self.stdout.write(self.style.ERROR(f"error: {error}"))

        if errors or (options["strict"] and warnings):
            raise CommandError(
                f"Handbook validation failed ({len(errors)} errors, {len(warnings)} warnings)."
            )

        if warnings:
            self.stdout.write(self.style.WARNING("Handbook is valid with review warnings."))
        else:
            self.stdout.write(self.style.SUCCESS("Handbook is valid."))


def _url_ok(url: str, timeout: float) -> bool:
    """HEAD with a GET fallback for servers that reject HEAD."""
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "Django-Quest-Handbook-Check/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status < 400
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            time.sleep(1.2)
        elif exc.code not in {403, 405}:
            return False
    except (urllib.error.URLError, TimeoutError, OSError):
        return False

    get_request = urllib.request.Request(
        url,
        headers={"User-Agent": "Django-Quest-Handbook-Check/1.0"},
    )
    try:
        with urllib.request.urlopen(get_request, timeout=timeout) as response:
            return response.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
