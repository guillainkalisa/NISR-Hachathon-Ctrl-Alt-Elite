from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render

from .forms import HouseholdForm
from .models import District, Indicator, SatelliteSnapshot
from .services import pmt, simulator

# Metrics a user can colour the map by: key -> (label, higher is worse?, unit, source)
MAP_METRICS = {
    "exclusion_error": ("Poor households receiving no support", True, "pct", "survey"),
    "excluded_poor": ("Number of poor households missed", True, "count", "survey"),
    "poverty_rate": ("Poverty rate (people)", True, "pct", "survey"),
    "coverage_poor": ("Support coverage of the poor", False, "pct", "survey"),
    "inclusion_error": ("Recipients who are not poor", True, "pct", "survey"),
    "lit_population_share": ("People living under night-time light", False, "pct", "satellite"),
    "ntl_pop_weighted": ("Night-time light where people live", False, "radiance", "satellite"),
}
SATELLITE_FIELDS = ["lit_population_share", "ntl_pop_weighted"]

INDICATOR_FIELDS = ["survey_round", "households", "poor_households", "beneficiaries", "excluded_poor",
                    "poverty_rate", "coverage_poor", "exclusion_error", "inclusion_error", "reliable", "n_poor"]


def _rounds():
    return sorted(Indicator.objects.values_list("survey_round", flat=True).distinct())


def _is_demo():
    return Indicator.objects.filter(is_demo=True).exists()


def map_view(request):
    rounds = _rounds()
    data = {}
    satellite = {s.district_id: s for s in SatelliteSnapshot.objects.all()}
    for ind in Indicator.objects.select_related("district"):
        row = {f: getattr(ind, f) for f in INDICATOR_FIELDS}
        row["slug"] = ind.district.slug
        sat = satellite.get(ind.district_id)
        # Satellite values are a single 2023/24 snapshot, shown alongside every survey round.
        row.update({f: getattr(sat, f) if sat else None for f in SATELLITE_FIELDS})
        data.setdefault(ind.district.name, {})[ind.survey_round] = row

    latest = rounds[-1] if rounds else None
    national = None
    if latest:
        latest_rows = Indicator.objects.filter(survey_round=latest)
        poor = sum(i.poor_households for i in latest_rows)
        excluded = sum(i.excluded_poor for i in latest_rows)
        national = {"round": latest, "poor": poor, "excluded": excluded,
                    "exclusion_rate": excluded / poor if poor else None,
                    "beneficiaries": sum(i.beneficiaries for i in latest_rows)}

    return render(request, "dashboard/map.html", {
        "rounds": rounds, "indicators": data, "national": national, "is_demo": _is_demo(),
        "metrics": {k: {"label": v[0], "higher_is_worse": v[1], "unit": v[2], "source": v[3]} for k, v in MAP_METRICS.items()},
    })


def districts_geojson(request):
    return FileResponse(open(settings.DISTRICTS_GEOJSON, "rb"), content_type="application/geo+json")


def district_detail(request, slug):
    district = get_object_or_404(District, slug=slug)
    rows = list(district.indicators.order_by("survey_round"))
    if not rows:
        raise Http404("No indicators for this district")
    latest = rows[-1]
    trend = [{"round": r.survey_round, "poverty_rate": r.poverty_rate, "coverage_poor": r.coverage_poor,
              "exclusion_error": r.exclusion_error} for r in rows]
    profile = sorted(latest.excluded_profile.items(), key=lambda kv: -(kv[1] or 0))
    rank = sorted(Indicator.objects.filter(survey_round=latest.survey_round), key=lambda i: -i.excluded_poor)
    satellite = getattr(district, "satellite", None)
    light_rank = None
    if satellite:
        lights = sorted(SatelliteSnapshot.objects.all(), key=lambda s: s.lit_population_share)
        light_rank = next(n for n, s in enumerate(lights, 1) if s.district_id == district.id)
    nightlights = [{"month": m.month, "ntl": m.ntl_mean if m.reliable else None} for m in district.nightlights.all()]
    return render(request, "dashboard/district.html", {
        "satellite": satellite, "light_rank": light_rank, "nightlights": nightlights,
        "district": district, "latest": latest, "trend": trend, "profile": profile,
        "rank": next(n for n, i in enumerate(rank, 1) if i.district_id == district.id), "n_districts": len(rank),
        "is_demo": _is_demo(),
    })


def checker(request):
    form = HouseholdForm(request.POST or None)
    result = None
    if request.method == "POST" and form.is_valid():
        result = pmt.score(form.model_values())
    return render(request, "dashboard/checker.html", {
        "form": form, "result": result, "metrics": pmt.load_metrics(), "model_ready": pmt.load_model() is not None,
        "is_demo": _is_demo(),
    })


def simulator_view(request):
    rounds = _rounds()
    if not rounds:
        return render(request, "dashboard/simulator.html", {"result": None, "is_demo": False})
    latest = rounds[-1]
    indicators = list(Indicator.objects.filter(survey_round=latest).select_related("district"))
    current_total = sum(i.beneficiaries for i in indicators)
    try:
        pct = max(1, min(100, int(request.GET.get("pct", 10))))
    except ValueError:
        pct = 10
    extra = current_total * pct / 100
    result = simulator.simulate(indicators, extra)
    gain = result["need_total"] - result["proportional_total"]
    return render(request, "dashboard/simulator.html", {
        "round": latest, "pct": pct, "extra": extra, "result": result, "gain": gain, "is_demo": _is_demo(),
    })


def about(request):
    return render(request, "dashboard/about.html", {"is_demo": _is_demo(), "metrics": pmt.load_metrics()})
