"""Load and seed the practical field guide: recipes, blueprints and releases."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import (
    AppBlueprint,
    ArchitectureCase,
    Cheatsheet,
    ReleaseNote,
    ReleaseSeries,
    Topic,
)

GUIDE_DIR = Path(settings.BASE_DIR) / "dojo" / "content" / "field_guide"

BLUEPRINT_COMPLEXITIES = {"starter", "production", "ambitious"}
CASE_COMPLEXITIES = {"production", "ambitious", "expert"}
RELEASE_KINDS = {"security", "patch", "feature", "lts"}
SERIES_STATUSES = {"lts", "stable", "extended", "unsupported"}


class GuideError(ValueError):
    pass


def _read(name: str) -> dict:
    path = GUIDE_DIR / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuideError(f"Missing field guide file: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise GuideError(f"{path.name}: invalid JSON: {exc}") from exc


def _require(item: dict, fields: tuple[str, ...], context: str) -> None:
    for field in fields:
        if not item.get(field):
            raise GuideError(f"{context}: missing {field}")


def load_cheatsheets() -> list[dict]:
    data = _read("cheatsheets.json")
    items = data.get("cheatsheets", [])
    seen = set()
    for index, item in enumerate(items):
        context = f"cheatsheet #{index + 1}"
        _require(item, ("key", "title", "category", "summary", "when_to_use", "code"), context)
        if item["key"] in seen:
            raise GuideError(f"{context}: duplicate key {item['key']!r}")
        seen.add(item["key"])
        if len(item["title"]) > 160:
            raise GuideError(f"{context}: title is too long for the database field")
    if not items:
        raise GuideError("cheatsheets.json must contain at least one recipe")
    return items


def load_blueprints() -> list[dict]:
    data = _read("blueprints.json")
    items = data.get("blueprints", [])
    seen = set()
    for index, item in enumerate(items):
        context = f"blueprint #{index + 1}"
        _require(
            item,
            (
                "key",
                "name",
                "tagline",
                "problem",
                "complexity",
                "stack_notes",
                "screens",
                "structure",
                "models_code",
                "starter_code",
                "checklist",
                "pitfalls",
            ),
            context,
        )
        if item["key"] in seen:
            raise GuideError(f"{context}: duplicate key {item['key']!r}")
        seen.add(item["key"])
        if item["complexity"] not in BLUEPRINT_COMPLEXITIES:
            raise GuideError(f"{context}: invalid complexity {item['complexity']!r}")
    if not items:
        raise GuideError("blueprints.json must contain at least one blueprint")
    return items


def load_cases() -> list[dict]:
    data = _read("architecture_cases.json")
    items = data.get("cases", [])
    seen = set()
    for index, item in enumerate(items):
        context = f"architecture case #{index + 1}"
        _require(
            item,
            (
                "key",
                "name",
                "tagline",
                "scenario",
                "scale",
                "complexity",
                "requirements",
                "constraints",
                "stack",
                "components",
                "data_flow",
                "decisions",
                "data_model_code",
                "starter_code",
                "failure_modes",
                "tradeoffs",
                "evolution",
            ),
            context,
        )
        if item["key"] in seen:
            raise GuideError(f"{context}: duplicate key {item['key']!r}")
        seen.add(item["key"])
        if item["complexity"] not in CASE_COMPLEXITIES:
            raise GuideError(f"{context}: invalid complexity {item['complexity']!r}")
    if not items:
        raise GuideError("architecture_cases.json must contain at least one case")
    return items


def load_releases() -> dict:
    data = _read("releases.json")
    try:
        date.fromisoformat(data["reviewed_on"])
    except (KeyError, ValueError) as exc:
        raise GuideError("releases.json: reviewed_on must be an ISO date") from exc
    series = data.get("series", [])
    notes = data.get("notes", [])
    seen_series = set()
    for index, item in enumerate(series):
        context = f"release series #{index + 1}"
        _require(item, ("series", "latest_version", "status"), context)
        if item["series"] in seen_series:
            raise GuideError(f"{context}: duplicate series {item['series']!r}")
        seen_series.add(item["series"])
        if item["status"] not in SERIES_STATUSES:
            raise GuideError(f"{context}: invalid status {item['status']!r}")
        for field in ("mainstream_ends", "extended_ends"):
            if item.get(field):
                try:
                    date.fromisoformat(item[field])
                except ValueError as exc:
                    raise GuideError(f"{context}: invalid {field} date") from exc

    seen_versions = set()
    for index, item in enumerate(notes):
        context = f"release note #{index + 1}"
        _require(
            item,
            (
                "version",
                "kind",
                "released_on",
                "headline",
                "summary",
                "why_it_matters",
                "action",
                "source_url",
            ),
            context,
        )
        if item["kind"] not in RELEASE_KINDS:
            raise GuideError(f"{context}: invalid kind {item['kind']!r}")
        if item["version"] in seen_versions:
            raise GuideError(f"{context}: duplicate version {item['version']!r}")
        seen_versions.add(item["version"])
        try:
            date.fromisoformat(item["released_on"])
        except ValueError as exc:
            raise GuideError(f"{context}: invalid released_on date") from exc
        if not str(item["source_url"]).startswith("https://"):
            raise GuideError(f"{context}: source_url must use https")

    if not series or not notes:
        raise GuideError("releases.json needs both series and notes")
    return data


def guide_fingerprint() -> str:
    import hashlib

    digest = hashlib.sha256()
    for path in sorted(GUIDE_DIR.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_guide() -> dict:
    cheatsheets = load_cheatsheets()
    blueprints = load_blueprints()
    cases = load_cases()
    releases = load_releases()
    return {
        "cheatsheets": len(cheatsheets),
        "blueprints": len(blueprints),
        "architecture_cases": len(cases),
        "release_notes": len(releases["notes"]),
        "release_series": len(releases["series"]),
    }


@transaction.atomic
def seed_guide() -> dict:
    cheatsheets = load_cheatsheets()
    blueprints = load_blueprints()
    cases = load_cases()
    releases = load_releases()
    topics = {topic.slug: topic for topic in Topic.objects.all()}

    created_recipes = 0
    for position, item in enumerate(cheatsheets):
        topic = topics.get(item.get("topic", ""))
        _, created = Cheatsheet.objects.update_or_create(
            key=item["key"],
            defaults={
                "title": item["title"],
                "category": item["category"],
                "summary": item["summary"],
                "when_to_use": item["when_to_use"],
                "code": item["code"],
                "language": item.get("language", "python"),
                "pitfalls": item.get("pitfalls", ""),
                "topic": topic,
                "order": position,
            },
        )
        created_recipes += int(created)

    created_blueprints = 0
    for position, item in enumerate(blueprints):
        topic = topics.get(item.get("topic", ""))
        _, created = AppBlueprint.objects.update_or_create(
            key=item["key"],
            defaults={
                "name": item["name"],
                "tagline": item["tagline"],
                "problem": item["problem"],
                "complexity": item["complexity"],
                "stack_notes": item["stack_notes"],
                "screens": item["screens"],
                "structure": item["structure"],
                "models_code": item["models_code"],
                "starter_code": item["starter_code"],
                "checklist": item["checklist"],
                "pitfalls": item["pitfalls"],
                "topic": topic,
                "order": position,
            },
        )
        created_blueprints += int(created)

    created_cases = 0
    for position, item in enumerate(cases):
        topic = topics.get(item.get("topic", ""))
        _, created = ArchitectureCase.objects.update_or_create(
            key=item["key"],
            defaults={
                "name": item["name"],
                "tagline": item["tagline"],
                "scenario": item["scenario"],
                "scale": item["scale"],
                "complexity": item["complexity"],
                "requirements": item["requirements"],
                "constraints": item["constraints"],
                "stack": item["stack"],
                "components": item["components"],
                "data_flow": item["data_flow"],
                "decisions": item["decisions"],
                "data_model_code": item["data_model_code"],
                "starter_code": item["starter_code"],
                "failure_modes": item["failure_modes"],
                "tradeoffs": item["tradeoffs"],
                "evolution": item["evolution"],
                "topic": topic,
                "order": position,
            },
        )
        created_cases += int(created)

    created_series = 0
    for position, item in enumerate(releases["series"]):
        _, created = ReleaseSeries.objects.update_or_create(
            series=item["series"],
            defaults={
                "latest_version": item["latest_version"],
                "status": item["status"],
                "mainstream_ends": item.get("mainstream_ends") or None,
                "extended_ends": item.get("extended_ends") or None,
                "order": position,
            },
        )
        created_series += int(created)

    created_notes = 0
    for position, item in enumerate(releases["notes"]):
        _, created = ReleaseNote.objects.update_or_create(
            version=item["version"],
            defaults={
                "kind": item["kind"],
                "released_on": item["released_on"],
                "headline": item["headline"],
                "summary": item["summary"],
                "why_it_matters": item["why_it_matters"],
                "action": item["action"],
                "source_url": item["source_url"],
                "order": position,
            },
        )
        created_notes += int(created)

    return {
        "cheatsheets": len(cheatsheets),
        "blueprints": len(blueprints),
        "architecture_cases": len(cases),
        "release_notes": len(releases["notes"]),
        "release_series": len(releases["series"]),
        "created_cheatsheets": created_recipes,
        "created_blueprints": created_blueprints,
        "created_architecture_cases": created_cases,
        "created_release_notes": created_notes,
        "created_release_series": created_series,
    }
