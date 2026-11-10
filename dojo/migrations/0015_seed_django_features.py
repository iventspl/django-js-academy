from django.db import migrations

FEATURES = [
    ("handbook", "90-chapter Django handbook", "A plain-language reference with 377 answers, 39 error fixes, 75 official links, 15 reference tables and 11 recipes.", "Handbook", "/handbook/", "¶", 10, False),
    ("search", "Ranked, code-aware search", "Search chapters, sections and code, with symbol lookup, typo suggestions, filters and keyboard navigation.", "Search & navigation", "/handbook/", "⌕", 20, False),
    ("traceback", "Traceback explainer", "Paste a Django traceback and get the exception, likely cause, fix and matching chapter.", "Search & navigation", "/handbook/traceback/", "!", 30, False),
    ("coverage", "Coverage report", "Chapters, answers, reference tables, review dates and known editorial gaps in one honest snapshot.", "Content health", "/handbook/coverage/", "▤", 40, False),
    ("versions", "Version matrix", "See which chapters apply to Django 5.2, 6.0 and 6.1 before copying a pattern.", "Versioning", "/handbook/versions/", "6", 50, True),
    ("upgrade", "Upgrade assistant", "Choose a source and target version, see incompatible chapters, release notes and an upgrade checklist.", "Versioning", "/handbook/upgrade/", "↗", 60, True),
    ("checkpoint", "Chapter checkpoint", "A three-question run tied to the chapter's quiz topic, separate from the full topic quiz.", "Practice", "/handbook/forms/#checkpoint", "?", 70, False),
    ("exercises", "Try-it exercises", "Selected chapters include a prompt, hint and hidden worked solution for active practice.", "Practice", "/handbook/messages/#exercises", "→", 80, False),
    ("notes", "Section notes and bookmarks", "Save a note under any section, bookmark without writing, review and export it as Markdown.", "Personal notes", "/handbook/notes/", "✎", 90, False),
    ("feedback", "Chapter feedback", "Mark a chapter helpful or needs-work and leave a local comment for your own review loop.", "Content health", "/handbook/forms/#feedback", "★", 100, False),
    ("gaps", "Search-gap dashboard", "See zero-result handbook queries and clear the log when you have addressed them.", "Content health", "/handbook/gaps/", "◌", 110, True),
    ("feedback-review", "Feedback review queue", "Group needs-work votes by chapter with the latest comment and stale-review flags.", "Content health", "/handbook/feedback/", "☷", 120, True),
    ("edit-next", "Edit-next queue", "One editorial priority list built from feedback, stale review dates and unmapped searches.", "Content health", "/handbook/edit-next/", "≡", 130, True),
    ("explain-back", "Explain it back", "Write a chapter explanation in your own words, self-rate it and compare with the short answer.", "Practice", "/handbook/forms/#explain", "✍", 140, True),
    ("teach-back", "Teach-back review", "Saved explanations sorted weakest-first, with previous attempts and spaced due dates.", "Practice", "/handbook/explanations/", "↻", 150, True),
    ("labs", "Django Labs", "Ten short build tasks with starter code, acceptance criteria, hints and reference implementations.", "Labs", "/handbook/labs/", "⚒", 160, True),
    ("lab-evidence", "Lab evidence journal", "Record what you built, one decision, one test and a repo link; export it as a portfolio.", "Labs", "/handbook/labs/contact-form/#evidence", "✓", 170, True),
    ("markdown", "Markdown export", "Every chapter exports as clean Markdown for offline reading or note-taking.", "Handbook", "/handbook/forms.md", "MD", 180, False),
    ("progress", "Progress and teaching analytics", "Streaks, mastery, weak spots, teach-back due count and recent attempts in one notebook.", "Practice", "/progress/", "↗", 190, False),
    ("themes", "Paper and high-contrast themes", "Switch between Dark, Paper and High contrast; the choice is stored locally.", "UI", "/features/", "◐", 200, True),
]


def seed_features(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    for slug, title, summary, category, url, glyph, order, is_new in FEATURES:
        Feature.objects.update_or_create(
            slug=slug,
            defaults={
                "title": title,
                "summary": summary,
                "category": category,
                "url": url,
                "glyph": glyph,
                "order": order,
                "is_new": is_new,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0014_djangofeature"),
    ]

    operations = [
        migrations.RunPython(seed_features, migrations.RunPython.noop),
    ]
