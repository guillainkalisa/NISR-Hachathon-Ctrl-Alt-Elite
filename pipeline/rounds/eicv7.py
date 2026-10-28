"""EICV7 (2023/24) -> canonical household table.

Variable names and codes are taken from the NISR data dictionary
(data/metadata/RWA-NISR-EICV7-2023-2024-v01.json, catalog 119).
"""

import numpy as np
import pandas as pd

FILES = {
    "poverty": "CS_EICV7_poverty_file.dta",
    "household": "CS_S01_S5_S7_Household.dta",
    "person": "CS_S0_S1_S2_S3_S4_S6A_S6B_S6C_Person.dta",
    "vup_ds": "CS_S9D1_Direct_Support.dta",
    "vup_cpw": "CS_S9D2_Classic_Public_Work.dta",
    "vup_epw": "CS_S9D3_Expanded_Public_Work.dta",
    "nsds": "CS_S9D4_NSDS.dta",
}

DISTRICT_CODES = {
    11: "Nyarugenge", 12: "Gasabo", 13: "Kicukiro",
    21: "Nyanza", 22: "Gisagara", 23: "Nyaruguru", 24: "Huye", 25: "Nyamagabe", 26: "Ruhango", 27: "Muhanga", 28: "Kamonyi",
    31: "Karongi", 32: "Rutsiro", 33: "Rubavu", 34: "Nyabihu", 35: "Ngororero", 36: "Rusizi", 37: "Nyamasheke",
    41: "Rulindo", 42: "Gakenke", 43: "Musanze", 44: "Burera", 45: "Gicumbi",
    51: "Rwamagana", 52: "Nyagatare", 53: "Gatsibo", 54: "Kayonza", 55: "Kirehe", 56: "Ngoma", 57: "Bugesera",
}

YES = 1

# s5dq2 roof -> features.PMT_FEATURES roof_material code
ROOF = {4: 0, 6: 0, 2: 1, 1: 2, 3: 3, 5: 3}
# s5dq3 floor: clay tiles, cement, bricks, carpet count as finished
FINISHED_FLOOR = {4, 5, 6, 7}
# s5cq3 drinking water: JMP improved sources
IMPROVED_WATER = {1, 2, 3, 4, 5, 6, 8, 10, 11, 14}
# s5cq14 grid and/or solar
ELECTRICITY = {1, 2, 3}
# s4aq2 highest class -> 0 none, 1 primary/vocational, 2 secondary, 3 tertiary
EDUCATION = {1: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 2, 7: 3}
# Tropical livestock units (FAO): cattle, goats, sheep, pigs, poultry
TLU = {"s7aq4a": 0.7, "s7aq4b": 0.1, "s7aq4c": 0.1, "s7aq4d": 0.2, "s7aq4e": 0.01}
# Washington Group disability: "a lot of difficulty" or "cannot do at all" in any domain
DISABILITY_ITEMS = ["s3q7", "s3q8", "s3q9", "s3q10", "s3q11", "s3q12"]


def load(folder):
    read = lambda key: pd.read_stata(folder / FILES[key], convert_categoricals=False)

    pov = read("poverty")
    out = pd.DataFrame({
        "hhid": pov["hhid"],
        "district": pov["district"].astype(int).map(DISTRICT_CODES),
        "urban": (pov["ur"] == 1).astype(int),
        "psu": pov["clust"],
        "hh_weight": pov["weight"],
        "hh_size": pov["member"],
        "poor": (pov["pov_jan"] == 100).astype(int),
        "extreme_poor": (pov["epov_jan"] == 100).astype(int),
    })

    hh = read("household").set_index("hhid")
    out = out.join(_household_features(hh), on="hhid")
    out = out.join(_person_features(read("person")), on="hhid")

    # Each S9D file repeats a column named s9d1q1 ("VUP, any component"), but within each file it only
    # screens that file's own component, so "any VUP" is built from the three components instead.
    programmes = {
        "sp_vup_ds": ("vup_ds", "s9d1q2"),
        "sp_vup_cpw": ("vup_cpw", "s9d2q1"),
        "sp_vup_epw": ("vup_epw", "s9d3q1"),
        "sp_nsds": ("nsds", "s9d4q1"),
    }
    for col, (key, var) in programmes.items():
        out = out.join(_household_flag(read(key), var).rename(col), on="hhid")
    flags = list(programmes)
    out[flags] = out[flags].fillna(0).astype(int)
    out["sp_vup"] = out[["sp_vup_ds", "sp_vup_cpw", "sp_vup_epw"]].max(axis=1)
    out["receives_sp"] = out[flags].max(axis=1)
    return out


def _household_features(hh):
    livestock = sum(hh[c].fillna(0).clip(lower=0) * w for c, w in TLU.items())
    return pd.DataFrame({
        "stratum": hh["strata_id"],
        "n_rooms": hh["s5aq3"].clip(lower=1),
        "roof_material": hh["s5dq2"].map(ROOF),
        "floor_cement": hh["s5dq3"].isin(FINISHED_FLOOR).astype(int),
        "improved_water": hh["s5cq3"].isin(IMPROVED_WATER).astype(int),
        "has_electricity": hh["s5cq14"].isin(ELECTRICITY).astype(int),
        "livestock_tlu": livestock.round(2),
    })


def _person_features(person):
    g = person.groupby("hhid")
    head = person[person["s1q2"] == 1].drop_duplicates("hhid").set_index("hhid")
    disabled = head[DISABILITY_ITEMS].ge(3).any(axis=1)
    never_school = head["s4aq1"] == 2
    return pd.DataFrame({
        "female_head": (head["s1q1"] == 2).astype(int),
        "head_age": head["s1q3y"],
        "head_disabled": disabled.astype(int),
        "head_educ": np.where(never_school, 0, head["s4aq2"].map(EDUCATION).fillna(0)).astype(int),
        "owns_phone": g["s4bq8"].apply(lambda s: int((s == YES).any())),
        "n_children_u5": g["s1q3y"].apply(lambda s: int((s < 5).sum())),
    })


def _household_flag(df, var):
    """1 if any row for the household answers Yes (some modules have one row per member)."""
    return df.assign(flag=(df[var] == YES).astype(int)).groupby("hhid")["flag"].max()
