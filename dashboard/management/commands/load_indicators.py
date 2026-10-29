import csv
import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from dashboard.models import District, Indicator

FLOAT_FIELDS = ["poverty_rate", "poverty_ci_low", "poverty_ci_high", "coverage_poor", "exclusion_error",
                "exclusion_ci_low", "exclusion_ci_high", "inclusion_error"]
INT_FIELDS = ["households", "poor_households", "beneficiaries", "excluded_poor", "n_households", "n_poor"]


class Command(BaseCommand):
    help = "Replace all indicators with the contents of data/processed/indicators.csv"

    def add_arguments(self, parser):
        parser.add_argument("--csv", default=str(settings.INDICATORS_CSV))

    @transaction.atomic
    def handle(self, *args, **opts):
        with open(opts["csv"], newline="") as f:
            rows = list(csv.DictReader(f))
        Indicator.objects.all().delete()
        for row in rows:
            district, _ = District.objects.update_or_create(
                slug=slugify(row["district"]), defaults={"name": row["district"], "province": row["province"]})
            Indicator.objects.create(
                district=district,
                survey_round=row["survey_round"],
                is_demo=row["is_demo"] == "True",
                reliable=row["reliable"] == "True",
                excluded_profile=json.loads(row["excluded_profile"]),
                programme_coverage=json.loads(row["programme_coverage"]),
                **{f: _float(row[f]) for f in FLOAT_FIELDS},
                **{f: int(float(row[f])) for f in INT_FIELDS},
            )
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(rows)} indicators for {len({r['district'] for r in rows})} districts"))


def _float(v):
    return float(v) if v not in ("", "nan", None) else None
