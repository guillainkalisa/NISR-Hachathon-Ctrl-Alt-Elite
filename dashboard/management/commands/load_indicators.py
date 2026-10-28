import json
import math

import pandas as pd
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
        df = pd.read_csv(opts["csv"])
        Indicator.objects.all().delete()
        for row in df.to_dict("records"):
            district, _ = District.objects.update_or_create(
                slug=slugify(row["district"]), defaults={"name": row["district"], "province": row["province"]})
            Indicator.objects.create(
                district=district,
                survey_round=row["survey_round"],
                is_demo=bool(row["is_demo"]),
                reliable=bool(row["reliable"]),
                excluded_profile=json.loads(row["excluded_profile"]),
                programme_coverage=json.loads(row["programme_coverage"]),
                **{f: _float(row[f]) for f in FLOAT_FIELDS},
                **{f: int(row[f]) for f in INT_FIELDS},
            )
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(df)} indicators for {df['district'].nunique()} districts"))


def _float(v):
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)
