from django.db import models


class District(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(unique=True)
    province = models.CharField(max_length=40)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Indicator(models.Model):
    """Targeting indicators for one district in one survey round (from pipeline/build_indicators.py)."""

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="indicators")
    survey_round = models.CharField(max_length=10)
    is_demo = models.BooleanField(default=False)

    households = models.PositiveIntegerField()
    poor_households = models.PositiveIntegerField()
    beneficiaries = models.PositiveIntegerField()
    excluded_poor = models.PositiveIntegerField()

    poverty_rate = models.FloatField()
    poverty_ci_low = models.FloatField()
    poverty_ci_high = models.FloatField()
    coverage_poor = models.FloatField(null=True)
    exclusion_error = models.FloatField(null=True)
    exclusion_ci_low = models.FloatField(null=True)
    exclusion_ci_high = models.FloatField(null=True)
    inclusion_error = models.FloatField(null=True)

    n_households = models.PositiveIntegerField()
    n_poor = models.PositiveIntegerField()
    reliable = models.BooleanField(default=True)
    excluded_profile = models.JSONField(default=dict)
    programme_coverage = models.JSONField(default=dict)

    class Meta:
        ordering = ["district__name", "survey_round"]
        constraints = [models.UniqueConstraint(fields=["district", "survey_round"], name="one_indicator_per_round")]

    def __str__(self):
        return f"{self.district} {self.survey_round}"


class SatelliteSnapshot(models.Model):
    """Night-time lights and population over the EICV7 fieldwork period (pipeline/satellite.py snapshot)."""

    district = models.OneToOneField(District, on_delete=models.CASCADE, related_name="satellite")
    period = models.CharField(max_length=30)
    population = models.FloatField()
    ntl_mean = models.FloatField()
    ntl_pop_weighted = models.FloatField()
    lit_population_share = models.FloatField()
    retrieved = models.DateField()


class NightlightMonth(models.Model):
    """Monthly cloud-screened night-time lights (pipeline/satellite.py monthly)."""

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="nightlights")
    month = models.CharField(max_length=7)
    ntl_mean = models.FloatField(null=True)
    valid_share = models.FloatField()
    reliable = models.BooleanField()
    retrieved = models.DateField()

    class Meta:
        ordering = ["district__name", "month"]
        constraints = [models.UniqueConstraint(fields=["district", "month"], name="one_nightlight_per_month")]
