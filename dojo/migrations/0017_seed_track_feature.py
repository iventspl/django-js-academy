from django.db import migrations


def add_track_feature(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    Feature.objects.update_or_create(
        slug="tracks",
        defaults={
            "title": "Django Project Tracks",
            "summary": "Four coherent project tracks combining labs, milestones, track evidence and portfolio export.",
            "category": "Labs",
            "url": "/handbook/tracks/",
            "glyph": "⧉",
            "order": 175,
            "is_new": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0016_djangotrackprogress"),
    ]

    operations = [
        migrations.RunPython(add_track_feature, migrations.RunPython.noop),
    ]
