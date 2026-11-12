import json

from django.core.management.base import BaseCommand, CommandError

from dojo.model_health import scan_models


class Command(BaseCommand):
    help = "Audit installed Django models for risky patterns."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print machine-readable JSON.",
        )
        parser.add_argument(
            "--fail-on",
            choices=["error", "warning"],
            help="Exit non-zero when findings at this severity exist.",
        )

    def handle(self, *args, **options):
        report = scan_models()
        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2, default=str))
        else:
            counts = report["counts"]
            self.stdout.write(
                f"Model health audit: {report['models_scanned']} models, "
                f"{counts['error']} errors, {counts['warning']} warnings, "
                f"{counts['info']} notes."
            )
            for finding in report["findings"]:
                self.stdout.write(
                    f"[{finding['severity']}] {finding['app']}.{finding['model']}"
                    f".{finding['field']}: {finding['message']}"
                )
                self.stdout.write(f"  fix: {finding['fix']}")

        threshold = options["fail_on"]
        if threshold == "error" and report["counts"]["error"]:
            raise CommandError("Model health audit found errors.")
        if threshold == "warning" and (
            report["counts"]["error"] or report["counts"]["warning"]
        ):
            raise CommandError("Model health audit found warnings or errors.")
