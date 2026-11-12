from django.db import migrations


def add_mental_models_feature(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    Feature.objects.update_or_create(
        slug="mental-models",
        defaults={
            "title": "Django Mental Models",
            "summary": "Eight durable explanations of the request pipeline, model descriptors, lazy querysets, forms, transactions, migrations, auth and async.",
            "category": "Handbook",
            "url": "/handbook/django-mental-models/",
            "glyph": "◉",
            "order": 15,
            "is_new": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0025_seed_model_health_feature"),
    ]

    operations = [
        migrations.RunPython(add_mental_models_feature, migrations.RunPython.noop),
    ]
