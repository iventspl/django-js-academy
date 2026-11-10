from django.db import migrations


def add_defense_feature(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    Feature.objects.update_or_create(
        slug="project-defense",
        defaults={
            "title": "Project Defense",
            "summary": "Eight capstone defense questions with written answers, self-ratings and model answers.",
            "category": "Labs",
            "url": "/handbook/capstone/defense/",
            "glyph": "⚖",
            "order": 185,
            "is_new": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0020_djangocapstoneprogress_defense_answers"),
    ]

    operations = [
        migrations.RunPython(add_defense_feature, migrations.RunPython.noop),
    ]
