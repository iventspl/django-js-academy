"""Static model-health checks with links back to the handbook.

The audit is intentionally conservative: it flags patterns that are almost
always worth a second look, not every stylistic preference.
"""

from __future__ import annotations

from collections import Counter

from django.apps import apps
from django.db import models

STRING_FIELDS = (
    models.CharField,
    models.TextField,
    models.EmailField,
    models.SlugField,
    models.URLField,
)
NUMERIC_FIELDS = (
    models.DecimalField,
    models.IntegerField,
    models.FloatField,
)
INDEX_HINTS = {"slug", "email", "status"}
NON_NEGATIVE_HINTS = {
    "price",
    "amount",
    "quantity",
    "stock",
    "total",
    "balance",
    "discount",
}

LINKS = {
    "null-string": "/handbook/model-fields-reference/#field-options",
    "missing-str": "/handbook/models/#a-model-is-a-table",
    "related-name": "/handbook/models/#relationships",
    "do-nothing": "/handbook/deletion-constraints-reference/#on-delete",
    "db-constraint": "/handbook/deletion-constraints-reference/#protect-restrict",
    "missing-index": "/handbook/model-fields-reference/#field-options",
    "missing-constraint": "/handbook/deletion-constraints-reference/#constraints",
    "default-mismatch": "/handbook/models/#db-default",
}

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _field_label(field) -> str:
    return field.name


def _has_custom_str(model) -> bool:
    return model.__str__ is not models.Model.__str__


def _condition_mentions(model, field_name: str) -> bool:
    for constraint in model._meta.constraints:
        condition = getattr(constraint, "condition", None)
        if condition is not None and field_name in str(condition):
            return True
    return False


def _finding(
    *,
    severity: str,
    check: str,
    model,
    field: str,
    message: str,
    fix: str,
) -> dict:
    return {
        "severity": severity,
        "check": check,
        "model": model.__name__,
        "app": model._meta.app_label,
        "field": field,
        "message": message,
        "fix": fix,
        "link": LINKS[check],
    }


def scan_models() -> dict:
    findings: list[dict] = []
    scanned = 0
    for model in apps.get_models():
        if model._meta.abstract or model._meta.proxy:
            continue
        scanned += 1
        if not _has_custom_str(model):
            findings.append(
                _finding(
                    severity="warning",
                    check="missing-str",
                    model=model,
                    field="—",
                    message="No useful __str__; the admin, shell and logs will show a generic object.",
                    fix="Add `def __str__(self): return self.name` (or another stable label).",
                )
            )

        for field in model._meta.get_fields():
            if not getattr(field, "concrete", False):
                continue
            name = _field_label(field)

            if isinstance(field, STRING_FIELDS) and getattr(field, "null", False):
                findings.append(
                    _finding(
                        severity="warning",
                        check="null-string",
                        model=model,
                        field=name,
                        message="Nullable string creates two empty states: NULL and ''.",
                        fix="Use `blank=True` with a non-null string unless NULL has a distinct meaning.",
                    )
                )

            if getattr(field, "is_relation", False) and getattr(
                field, "related_name", None
            ) is None:
                findings.append(
                    _finding(
                        severity="info",
                        check="related-name",
                        model=model,
                        field=name,
                        message="No explicit related_name; the reverse accessor is inferred.",
                        fix="Set a clear `related_name` (or `related_name='+'` if the reverse is intentionally hidden).",
                    )
                )

            on_delete = getattr(getattr(field, "remote_field", None), "on_delete", None)
            if on_delete is models.DO_NOTHING:
                findings.append(
                    _finding(
                        severity="error",
                        check="do-nothing",
                        model=model,
                        field=name,
                        message="DO_NOTHING leaves referential integrity to the database or to chance.",
                        fix="Use CASCADE, PROTECT, RESTRICT, SET_NULL or SET(callable) unless a trigger owns this.",
                    )
                )

            if getattr(field, "db_constraint", True) is False:
                findings.append(
                    _finding(
                        severity="warning",
                        check="db-constraint",
                        model=model,
                        field=name,
                        message="db_constraint=False removes the foreign-key guarantee.",
                        fix="Keep the database constraint unless a documented legacy schema requires otherwise.",
                    )
                )

            if (
                name in INDEX_HINTS
                and not getattr(field, "unique", False)
                and not getattr(field, "db_index", False)
            ):
                findings.append(
                    _finding(
                        severity="info",
                        check="missing-index",
                        model=model,
                        field=name,
                        message="A commonly filtered field has no database index.",
                        fix="Add `db_index=True` or `Meta.indexes` after confirming the query pattern.",
                    )
                )

            if (
                name in NON_NEGATIVE_HINTS
                and isinstance(field, NUMERIC_FIELDS)
                and not _condition_mentions(model, name)
            ):
                findings.append(
                    _finding(
                        severity="info",
                        check="missing-constraint",
                        model=model,
                        field=name,
                        message="An obvious numeric invariant has no CheckConstraint.",
                        fix="Add a CheckConstraint such as `Q(price__gte=0)`, or document why negative values are valid.",
                    )
                )

            has_default = getattr(field, "has_default", lambda: False)()
            has_db_default = getattr(field, "has_db_default", lambda: False)()
            if has_default and has_db_default:
                default = getattr(field, "default", None)
                db_default = getattr(field, "db_default", None)
                if str(default) != str(db_default):
                    findings.append(
                        _finding(
                            severity="info",
                            check="default-mismatch",
                            model=model,
                            field=name,
                            message="`default` and `db_default` disagree; Python and the database can produce different values.",
                            fix="Make the values identical or remove one deliberately.",
                        )
                    )

    findings.sort(
        key=lambda item: (
            SEVERITY_ORDER[item["severity"]],
            item["app"],
            item["model"],
            item["field"],
        )
    )
    counts = Counter(item["severity"] for item in findings)
    return {
        "models_scanned": scanned,
        "findings": findings,
        "counts": {
            "error": counts.get("error", 0),
            "warning": counts.get("warning", 0),
            "info": counts.get("info", 0),
            "total": len(findings),
        },
    }
