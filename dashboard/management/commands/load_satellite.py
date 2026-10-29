import csv

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import District, NightlightMonth, SatelliteSnapshot


def _read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _float(v, missing=None):
    return float(v) if v not in ("", "nan") else missing


class Command(BaseCommand):
    help = "Replace satellite indicators with data/processed/satellite_*.csv (run after load_indicators)"

    @transaction.atomic
    def handle(self, *args, **opts):
        districts = {d.name: d for d in District.objects.all()}
        processed = settings.BASE_DIR / "data" / "processed"

        snap = _read(processed / "satellite_districts.csv")
        SatelliteSnapshot.objects.all().delete()
        SatelliteSnapshot.objects.bulk_create(SatelliteSnapshot(
            district=districts[r["district"]], period=r["period"], population=_float(r["population_worldpop"]),
            ntl_mean=_float(r["ntl_mean"]), ntl_pop_weighted=_float(r["ntl_pop_weighted"]),
            lit_population_share=_float(r["lit_population_share"]), retrieved=r["retrieved"],
        ) for r in snap)

        monthly = _read(processed / "satellite_monthly.csv")
        NightlightMonth.objects.all().delete()
        NightlightMonth.objects.bulk_create(NightlightMonth(
            district=districts[r["district"]], month=r["month"], ntl_mean=_float(r["ntl_mean"]),
            valid_share=_float(r["valid_share"], 0), reliable=r["reliable"] == "True", retrieved=r["retrieved"],
        ) for r in monthly)

        self.stdout.write(self.style.SUCCESS(f"Loaded satellite data: {len(snap)} districts, {len(monthly)} district-months"))
