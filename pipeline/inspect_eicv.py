"""List every variable (name + label) in a folder of EICV Stata/SPSS files.

Use it to check variable names when writing pipeline/rounds/<round>.py. Writes a searchable CSV too.

Usage:  python -m pipeline.inspect_eicv data/raw/EICV7
        python -m pipeline.inspect_eicv data/raw/EICV7 --grep vup
"""

import argparse
from pathlib import Path

import pandas as pd
import pyreadstat

READERS = {".dta": pyreadstat.read_dta, ".sav": pyreadstat.read_sav}


def inspect(folder, grep=None):
    rows = []
    for path in sorted(Path(folder).rglob("*")):
        reader = READERS.get(path.suffix.lower())
        if not reader:
            continue
        _, meta = reader(str(path), metadataonly=True)
        print(f"\n== {path.relative_to(folder)}  ({meta.number_rows} rows, {meta.number_columns} vars)")
        for name, label in zip(meta.column_names, meta.column_labels):
            rows.append({"file": str(path.relative_to(folder)), "variable": name, "label": label or ""})
            if not grep or grep.lower() in f"{name} {label}".lower():
                print(f"   {name:<20} {label or ''}")
    out = Path(folder) / "_variables.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nFull variable list -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--grep", help="only print variables whose name/label contains this text")
    args = ap.parse_args()
    inspect(args.folder, args.grep)
