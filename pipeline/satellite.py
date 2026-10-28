"""District satellite indicators from Google Earth Engine.

All raster processing runs on Earth Engine's servers; only per-district numbers
come back. Two outputs, kept separate on purpose:

  snapshot  data/processed/satellite_districts.csv
            Averages over the EICV7 fieldwork period (Oct 2023 - Oct 2024), so they
            line up with the survey for modelling.
  monthly   data/processed/satellite_monthly.csv
            Recent monthly night-time lights, for the "what has changed since the
            survey" alerts. Re-run monthly to refresh.

Datasets:
  NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG   VIIRS night-time lights, monthly, ~460 m (stray-light corrected)
  WorldPop/GP/100m/R2025A/v1/pop       WorldPop population, 100 m (2024, the EICV7 survey year)

Setup (once): earthengine authenticate, and EE_PROJECT=<cloud project id> in .env
Usage:  python -m pipeline.satellite snapshot
        python -m pipeline.satellite monthly --months 24
"""

import argparse
import json
import os
from datetime import date
from pathlib import Path

import ee
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "processed"
DISTRICTS_GEOJSON = ROOT / "data" / "geo" / "rwa_districts.geojson"

VIIRS = "NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG"
WORLDPOP = "WorldPop/GP/100m/R2025A/v1/pop"
POP_YEAR = 2024
SURVEY_PERIOD = ("2023-10-01", "2024-11-01")  # EICV7 fieldwork, end exclusive
LIT_THRESHOLD = 0.5  # nW/cm2/sr; below this a pixel is treated as unlit (removes background noise)
# Rwanda's rainy seasons leave many pixels with few cloud-free nights; those months read as false darkness.
MIN_CLEAR_NIGHTS = 2
MIN_VALID_SHARE = 0.5  # district-months with less usable area than this are flagged unreliable


def clear_radiance(img):
    """Radiance with cloud-contaminated pixels masked out."""
    return img.select("avg_rad").max(0).updateMask(img.select("cf_cvg").gte(MIN_CLEAR_NIGHTS))


def init():
    project = os.environ.get("EE_PROJECT") or _read_env().get("EE_PROJECT")
    if not project:
        raise SystemExit("Set EE_PROJECT in .env (your Google Cloud project registered for Earth Engine)")
    ee.Initialize(project=project)


def _read_env():
    path = ROOT / ".env"
    if not path.exists():
        return {}
    pairs = (line.split("=", 1) for line in path.read_text().splitlines() if "=" in line and not line.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def districts():
    geo = json.loads(DISTRICTS_GEOJSON.read_text())
    feats = [ee.Feature(f["geometry"], {"district": f["properties"]["shapeName"]}) for f in geo["features"]]
    return ee.FeatureCollection(feats)


def snapshot():
    """Survey-period nightlights and population per district."""
    fc = districts()
    ntl = ee.ImageCollection(VIIRS).filterDate(*SURVEY_PERIOD).map(clear_radiance).mean().unmask(0).rename("ntl")
    pop = (ee.ImageCollection(WORLDPOP).filter(ee.Filter.eq("country", "RWA"))
           .filter(ee.Filter.eq("year", POP_YEAR)).first().select("population").rename("pop"))

    # Population living under lit pixels, computed at WorldPop's 100 m resolution.
    lit_pop = pop.updateMask(ntl.gt(LIT_THRESHOLD)).rename("lit_pop")
    sums = ee.Image.cat([pop, lit_pop, ntl.multiply(pop).rename("ntl_x_pop")]).reduceRegions(
        collection=fc, reducer=ee.Reducer.sum(), scale=100, tileScale=4)
    means = ntl.reduceRegions(collection=fc, reducer=ee.Reducer.mean().setOutputs(["ntl_mean"]), scale=463)

    rows = {f["properties"]["district"]: f["properties"] for f in sums.getInfo()["features"]}
    for f in means.getInfo()["features"]:
        rows[f["properties"]["district"]]["ntl_mean"] = f["properties"]["ntl_mean"]

    df = pd.DataFrame([{
        "district": d,
        "population_worldpop": r["pop"],
        "ntl_mean": r["ntl_mean"],                         # average radiance across the district's area
        "ntl_pop_weighted": r["ntl_x_pop"] / r["pop"],     # radiance where people actually live
        "lit_population_share": r["lit_pop"] / r["pop"],   # share of people living under lit pixels
    } for d, r in sorted(rows.items())])
    df["period"] = f"{SURVEY_PERIOD[0]}:{SURVEY_PERIOD[1]}"
    df["retrieved"] = date.today().isoformat()
    _write(df, "satellite_districts.csv")


def monthly(months):
    """Monthly mean nightlights per district for the most recent `months` months available."""
    fc = districts()
    col = ee.ImageCollection(VIIRS).sort("system:time_start", False).limit(months)

    def per_month(img):
        bands = ee.Image.cat([clear_radiance(img).rename("ntl_mean"),
                              img.select("cf_cvg").gte(MIN_CLEAR_NIGHTS).rename("valid_share")])
        stats = bands.reduceRegions(collection=fc, reducer=ee.Reducer.mean(), scale=463)
        month = img.date().format("YYYY-MM")
        return stats.map(lambda f: f.set("month", month))

    feats = ee.FeatureCollection(col.map(per_month)).flatten().getInfo()["features"]
    df = pd.DataFrame([{k: f["properties"].get(k) for k in ("district", "month", "ntl_mean", "valid_share")} for f in feats])
    df["reliable"] = df["valid_share"].fillna(0) >= MIN_VALID_SHARE
    df = df.sort_values(["district", "month"])
    df["retrieved"] = date.today().isoformat()
    _write(df, "satellite_monthly.csv")
    print(f"  months covered: {df['month'].min()} to {df['month'].max()}; "
          f"{(~df['reliable']).sum()} of {len(df)} district-months flagged as too cloudy")


def _write(df, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / name, index=False)
    print(f"Wrote {len(df)} rows -> {(OUT_DIR / name).relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("snapshot")
    m = sub.add_parser("monthly")
    m.add_argument("--months", type=int, default=24)
    args = ap.parse_args()
    init()
    snapshot() if args.cmd == "snapshot" else monthly(args.months)
