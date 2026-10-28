from django.contrib import admin

from .models import District, Indicator


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ["name", "province"]
    list_filter = ["province"]


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ["district", "survey_round", "poverty_rate", "exclusion_error", "inclusion_error", "reliable", "is_demo"]
    list_filter = ["survey_round", "reliable", "is_demo"]
