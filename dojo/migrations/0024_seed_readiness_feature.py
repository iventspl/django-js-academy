from django.db import migrations


def add_readiness_feature(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    Feature.objects.update_or_create(
        slug="readiness",
        defaults={
            "title": "Django Readiness Dashboard",
            "summary": "A job-readiness score built from quiz mastery, labs, teach-back, interview answers and capstone progress.",
            "category": "Practice",
            "url": "/readiness/",
            "glyph": "◎",
            "order": 195,
            "is_new": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0023_seed_interview_feature"),
    ]

    operations = [
        migrations.RunPython(add_readiness_feature, migrations.RunPython.noop),
    ]
