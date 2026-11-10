from django.db import migrations


def add_interview_feature(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    Feature.objects.update_or_create(
        slug="interview",
        defaults={
            "title": "Django Interview Simulator",
            "summary": "Twenty Django interview questions with answer-first practice, model answers, spaced self-ratings and readiness export.",
            "category": "Practice",
            "url": "/interview/",
            "glyph": "?",
            "order": 155,
            "is_new": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0022_djangointerviewpractice"),
    ]

    operations = [
        migrations.RunPython(add_interview_feature, migrations.RunPython.noop),
    ]
