from django.db import migrations


def add_model_health_feature(apps, schema_editor):
    Feature = apps.get_model("dojo", "DjangoFeature")
    Feature.objects.update_or_create(
        slug="model-health",
        defaults={
            "title": "Model Health Audit",
            "summary": "A conservative scan of installed models for nullable strings, missing relations, risky deletes and missing constraints.",
            "category": "Content health",
            "url": "/handbook/model-health/",
            "glyph": "⚕",
            "order": 115,
            "is_new": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("dojo", "0024_seed_readiness_feature"),
    ]

    operations = [
        migrations.RunPython(add_model_health_feature, migrations.RunPython.noop),
    ]
