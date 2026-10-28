import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import District, NightlightMonth, SatelliteSnapshot


class Command(BaseCommand):
    help = "Replace satellite indicators with data/processed/satellite_*.csv (run after load_indicators)"

    @transaction.atomic
    def handle(self, *args, **opts):
        districts = {d.name: d for d in District.objects.all()}
        processed = settings.BASE_DIR / "data" / "processed"

        snap = pd.read_csv(processed / "satellite_districts.csv")
        SatelliteSnapshot.objects.all().delete()
        SatelliteSnapshot.objects.bulk_create(SatelliteSnapshot(
            district=districts[r.district], period=r.period, population=r.population_worldpop, ntl_mean=r.ntl_mean,
            ntl_pop_weighted=r.ntl_pop_weighted, lit_population_share=r.lit_population_share, retrieved=r.retrieved,
        ) for r in snap.itertuples())

        monthly = pd.read_csv(processed / "satellite_monthly.csv")
        NightlightMonth.objects.all().delete()
        NightlightMonth.objects.bulk_create(NightlightMonth(
            district=districts[r.district], month=r.month, ntl_mean=None if pd.isna(r.ntl_mean) else r.ntl_mean,
            valid_share=0 if pd.isna(r.valid_share) else r.valid_share, reliable=bool(r.reliable), retrieved=r.retrieved,
        ) for r in monthly.itertuples())

        self.stdout.write(self.style.SUCCESS(f"Loaded satellite data: {len(snap)} districts, {len(monthly)} district-months"))
