"""Generate SYNTHETIC household data in the canonical schema.

This exists only so the pipeline and the app can be developed and demoed before
the real EICV files are prepared. Nothing produced here is an NISR statistic,
and every output is flagged `is_demo` so the app shows a warning banner.

Usage:  python -m pipeline.demo_data
"""

from pathlib import Path

import numpy as np
import pandas as pd

from pipeline.geo import DISTRICTS

ROUNDS = ["EICV5", "EICV6", "EICV7"]
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"


def simulate_round(rng, round_idx, households_per_district=240, cluster_size=12):
    rows = []
    district_wealth = {d: rng.normal(0, 0.6) for d in DISTRICTS}
    for d in ["Gasabo", "Kicukiro", "Nyarugenge"]:
        district_wealth[d] += 1.2
    district_targeting = {d: rng.uniform(0.3, 1.2) for d in DISTRICTS}

    for d in DISTRICTS:
        n_clusters = households_per_district // cluster_size
        for c in range(n_clusters):
            urban = int(rng.random() < (0.8 if district_wealth[d] > 1 else 0.15))
            cluster_effect = rng.normal(0, 0.4)
            for i in range(cluster_size):
                rows.append(_household(rng, d, c, i, urban, district_wealth[d] + cluster_effect + 0.15 * round_idx,
                                       district_targeting[d] + 0.1 * round_idx))
    df = pd.DataFrame(rows)
    df["stratum"] = df["district"] + "_" + df["urban"].map({0: "R", 1: "U"})
    df["psu"] = df["district"] + "_" + df["cluster"].astype(str)
    return df.drop(columns="cluster")


def _household(rng, district, cluster, i, urban, wealth_shift, targeting_skill):
    hh_size = int(np.clip(rng.poisson(4.3) + 1, 1, 14))
    head_age = int(np.clip(rng.normal(45, 14), 18, 95))
    female_head = int(rng.random() < 0.27)
    head_disabled = int(rng.random() < 0.07)
    head_educ = int(rng.choice(4, p=[0.2, 0.55, 0.18, 0.07]) if not urban else rng.choice(4, p=[0.08, 0.4, 0.32, 0.2]))
    n_children_u5 = int(min(rng.poisson(0.8), hh_size - 1))

    latent = (wealth_shift + 0.9 * urban + 0.45 * head_educ - 0.12 * hh_size - 0.3 * female_head
              - 0.35 * head_disabled + rng.normal(0, 0.8))
    roof_material = int(np.clip(round(1.5 + 0.7 * latent + rng.normal(0, 0.6)), 0, 3))
    floor_cement = int(rng.random() < _sigmoid(latent - 0.3))
    n_rooms = int(np.clip(round(2 + 0.6 * latent + rng.normal(0, 0.8)), 1, 10))
    has_electricity = int(rng.random() < _sigmoid(latent + 0.4 + urban))
    improved_water = int(rng.random() < _sigmoid(latent + 1.0))
    livestock_tlu = float(max(0, rng.gamma(1.0, 0.4 + 0.2 * max(latent, 0))))
    owns_phone = int(rng.random() < _sigmoid(latent + 1.2))

    consumption = latent + 0.3 * livestock_tlu + rng.normal(0, 0.5)
    poor = int(consumption < -0.4)
    extreme_poor = int(consumption < -1.2)

    # Programmes see some of the true need, plus noise: this creates both error types.
    p_receive = _sigmoid(-2.2 + targeting_skill * (poor * 1.6 + extreme_poor * 0.8 + head_disabled + 0.5 * (head_age >= 65))
                         + rng.normal(0, 0.7))
    receives_sp = int(rng.random() < p_receive)
    sp_nsds = int(receives_sp and n_children_u5 > 0 and rng.random() < 0.3)
    sp_vup_ds = int(receives_sp and not sp_nsds and rng.random() < 0.5)
    sp_vup_cpw = int(receives_sp and not (sp_nsds or sp_vup_ds) and rng.random() < 0.6)
    sp_vup_epw = int(receives_sp and not (sp_nsds or sp_vup_ds or sp_vup_cpw))

    return {
        "hhid": f"{district[:3].upper()}-{cluster:02d}-{i:02d}",
        "district": district, "urban": urban, "cluster": cluster,
        "hh_weight": float(rng.uniform(80, 160)), "hh_size": hh_size,
        "poor": poor, "extreme_poor": extreme_poor, "receives_sp": receives_sp,
        "sp_vup": receives_sp, "sp_vup_ds": sp_vup_ds, "sp_vup_cpw": sp_vup_cpw, "sp_vup_epw": sp_vup_epw,
        "sp_nsds": sp_nsds,
        "head_age": head_age, "female_head": female_head, "head_disabled": head_disabled, "head_educ": head_educ,
        "roof_material": roof_material, "floor_cement": floor_cement, "n_rooms": n_rooms,
        "has_electricity": has_electricity, "improved_water": improved_water,
        "livestock_tlu": round(livestock_tlu, 2), "owns_phone": owns_phone, "n_children_u5": n_children_u5,
    }


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def main():
    rng = np.random.default_rng(2026)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for idx, rnd in enumerate(ROUNDS):
        df = simulate_round(rng, idx)
        path = OUT_DIR / f"households_{rnd}.csv"
        df.to_csv(path, index=False)
        print(f"{rnd}: {len(df)} synthetic households -> {path}")


if __name__ == "__main__":
    main()
