"""Compute district targeting indicators from prepared household files.

Reads  <source>/households_<ROUND>.csv  (canonical schema, see features.py)
Writes data/processed/indicators.csv    (aggregates only - safe to publish)

Definitions (household level unless stated):
  poverty_rate     share of PEOPLE below the poverty line (person-weighted, as NISR reports it)
  coverage_poor    share of poor households receiving any social protection
  exclusion_error  share of poor households receiving nothing (= 1 - coverage_poor)
  inclusion_error  share of recipient households that are not poor
  excluded_poor    estimated number of poor households receiving nothing

Usage:
  python -m pipeline.build_indicators --source data/interim        # real EICV
  python -m pipeline.build_indicators --source data/demo --demo    # synthetic
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from pipeline import survey
from pipeline.features import DESIGN_COLUMNS, OUTCOME_COLUMNS, PROFILE_GROUPS, PROGRAMME_COLUMNS
from pipeline.geo import DISTRICT_TO_PROVINCE, DISTRICTS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed" / "indicators.csv"

# Below this many sampled poor households, district targeting estimates are flagged as unreliable.
MIN_POOR_SAMPLE = 30


def add_derived(df):
    df = df.copy()
    df["pop_weight"] = df["hh_weight"] * df["hh_size"]
    df["excluded"] = ((df["poor"] == 1) & (df["receives_sp"] == 0)).astype(int)
    df["not_poor"] = 1 - df["poor"]
    df["elderly_head"] = (df["head_age"] >= 65).astype(int) if "head_age" in df else 0
    df["large_household"] = (df["hh_size"] >= 7).astype(int)
    return df


def _share(v):
    """Round for JSON; an undefined share (empty group) becomes null rather than NaN."""
    return None if pd.isna(v) else round(v, 4)


def district_indicators(df, district):
    in_d = (df["district"] == district).astype(int)
    poor_in_d = in_d * df["poor"]
    sp_in_d = in_d * df["receives_sp"]
    excluded_in_d = in_d * df["excluded"]

    pov = survey.ratio(df, "poor", pd.Series(1, index=df.index), weight="pop_weight", domain=in_d)
    cov = survey.ratio(df, df["receives_sp"] * df["poor"], "poor", domain=in_d)
    inc = survey.ratio(df, df["not_poor"] * df["receives_sp"], "receives_sp", domain=in_d)

    profile = {}
    for col, label in PROFILE_GROUPS.items():
        if col in df:
            r = survey.ratio(df, df[col] * df["excluded"], "excluded", domain=in_d)
            profile[label] = _share(r["estimate"])

    programmes = {}
    for col in PROGRAMME_COLUMNS:
        if col in df:
            programmes[col] = _share(survey.ratio(df, df[col] * df["poor"], "poor", domain=in_d)["estimate"])

    return {
        "district": district,
        "province": DISTRICT_TO_PROVINCE[district],
        "households": round(survey.total(df, in_d)),
        "poor_households": round(survey.total(df, poor_in_d)),
        "beneficiaries": round(survey.total(df, sp_in_d)),
        "excluded_poor": round(survey.total(df, excluded_in_d)),
        "poverty_rate": pov["estimate"], "poverty_ci_low": pov["ci_low"], "poverty_ci_high": pov["ci_high"],
        "coverage_poor": cov["estimate"],
        "exclusion_error": 1 - cov["estimate"],
        "exclusion_ci_low": 1 - cov["ci_high"], "exclusion_ci_high": 1 - cov["ci_low"],
        "inclusion_error": inc["estimate"],
        "n_households": int(in_d.sum()), "n_poor": cov["n"],
        "reliable": cov["n"] >= MIN_POOR_SAMPLE,
        "excluded_profile": json.dumps(profile),
        "programme_coverage": json.dumps(programmes),
    }


def build(source, demo):
    files = sorted(Path(source).glob("households_*.csv"))
    if not files:
        raise SystemExit(f"No households_<ROUND>.csv files in {source}")
    rows = []
    for path in files:
        rnd = path.stem.replace("households_", "")
        df = pd.read_csv(path)
        missing = [c for c in DESIGN_COLUMNS + OUTCOME_COLUMNS if c not in df]
        if missing:
            raise SystemExit(f"{path.name} is missing required columns: {missing}")
        df = add_derived(df)
        for d in DISTRICTS:
            row = district_indicators(df, d)
            row.update(survey_round=rnd, is_demo=demo)
            rows.append(row)
        print(f"{rnd}: {len(df)} households, {df['district'].nunique()} districts")
    out = pd.DataFrame(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"Wrote {len(out)} district-round rows -> {OUT.relative_to(ROOT)}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(ROOT / "data" / "interim"))
    ap.add_argument("--demo", action="store_true", help="mark outputs as synthetic demo data")
    args = ap.parse_args()
    build(args.source, args.demo)
