"""Turn raw EICV microdata into one canonical household table per round.

Round-specific knowledge (file names, variable names, codes) lives in
pipeline/rounds/<round>.py, each exposing load(folder) -> DataFrame.

Writes data/interim/households_<ROUND>.csv - household microdata, which stays
local: data/interim is git-ignored and must never be committed or deployed.

Usage:  python -m pipeline.prepare_eicv --round EICV7
"""

import argparse
import importlib
from pathlib import Path

from pipeline.features import DESIGN_COLUMNS, OUTCOME_COLUMNS, PMT_FEATURE_NAMES

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", required=True, help="e.g. EICV7 (needs pipeline/rounds/eicv7.py)")
    ap.add_argument("--folder", help="raw files folder (default data/raw/<ROUND>)")
    args = ap.parse_args()

    module = importlib.import_module(f"pipeline.rounds.{args.round.lower()}")
    folder = Path(args.folder) if args.folder else ROOT / "data" / "raw" / args.round
    missing_files = [f for f in module.FILES.values() if not (folder / f).exists()]
    if missing_files:
        raise SystemExit(f"Missing in {folder}: {missing_files}")

    print(f"Preparing {args.round} from {folder}")
    df = module.load(folder)

    missing = [c for c in DESIGN_COLUMNS + OUTCOME_COLUMNS + PMT_FEATURE_NAMES if c not in df]
    if missing:
        raise SystemExit(f"{args.round} loader does not produce: {missing}")
    if df["district"].isna().any():
        raise SystemExit(f"{df['district'].isna().sum()} households have an unknown district code")
    nulls = df[PMT_FEATURE_NAMES].isna().sum()
    if nulls.any():
        print(f"  note: missing feature values (model handles them natively):\n{nulls[nulls > 0].to_string()}")

    out = ROOT / "data" / "interim" / f"households_{args.round}.csv"
    df.to_csv(out, index=False)
    pop = df.hh_weight * df.hh_size
    print(f"  -> {out.relative_to(ROOT)}: {len(df)} households")
    print(f"  check against the published report: poverty {(df.poor * pop).sum() / pop.sum():.1%}, "
          f"extreme poverty {(df.extreme_poor * pop).sum() / pop.sum():.1%}, "
          f"households in VUP {(df.sp_vup * df.hh_weight).sum() / df.hh_weight.sum():.1%}")


if __name__ == "__main__":
    main()
