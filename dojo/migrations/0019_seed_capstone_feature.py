from django.db import migrations


def add_capstone_feature(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    Feature.objects.update_or_create(
        slug="capstone",
        defaults={
            "title": "Django Capstone",
            "summary": "One end-to-end deployable project with six phases, deployment checklist and portfolio evidence.",
            "category": "Labs",
            "url": "/handbook/capstone/",
            "glyph": "★",
            "order": 180,
            "is_new": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0018_djangocapstoneprogress"),
    ]

    operations = [
        migrations.RunPython(add_capstone_feature, migrations.RunPython.noop),
    ]
