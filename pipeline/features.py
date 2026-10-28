"""Canonical household schema shared by the pipeline, the model and the Django app.

Every EICV round is mapped onto these column names by `prepare_eicv.py`, so the
rest of the code never depends on raw survey variable names.
"""

# Survey design and outcome columns (required in every prepared household file).
DESIGN_COLUMNS = ["hhid", "district", "urban", "stratum", "psu", "hh_weight", "hh_size"]
OUTCOME_COLUMNS = ["poor", "extreme_poor", "receives_sp"]

# Optional programme-level flags; used for the "which programme" breakdown when present.
# VUP any component, then VUP direct support / classic public works / expanded public works, and NSDS.
PROGRAMME_COLUMNS = ["sp_vup", "sp_vup_ds", "sp_vup_cpw", "sp_vup_epw", "sp_nsds"]

# Groups used to describe who the excluded poor are.
PROFILE_GROUPS = {
    "female_head": "Female-headed",
    "elderly_head": "Head aged 65+",
    "head_disabled": "Head with disability",
    "urban": "Urban",
    "large_household": "7+ members",
}

# Proxy-means-test features: things a field officer can observe or ask in minutes.
# kind: "int" / "float" / "bool" / "choice". Choices are (code, label) pairs.
PMT_FEATURES = [
    {"name": "hh_size", "label": "Household members", "kind": "int", "min": 1, "max": 20},
    {"name": "head_age", "label": "Age of household head", "kind": "int", "min": 15, "max": 100},
    {"name": "female_head", "label": "Head is female", "kind": "bool"},
    {"name": "head_disabled", "label": "Head has a disability", "kind": "bool"},
    {"name": "head_educ", "label": "Head's education", "kind": "choice",
     "choices": [(0, "None"), (1, "Primary"), (2, "Secondary"), (3, "Post-secondary")]},
    {"name": "urban", "label": "Lives in an urban area", "kind": "bool"},
    {"name": "roof_material", "label": "Main roof material", "kind": "choice",
     "choices": [(0, "Plastic / impermanent"), (1, "Local clay tiles"), (2, "Iron sheets"), (3, "Concrete / industrial tiles")]},
    {"name": "floor_cement", "label": "Floor is cement, tiles or better", "kind": "bool"},
    {"name": "n_rooms", "label": "Rooms used for sleeping", "kind": "int", "min": 1, "max": 15},
    {"name": "has_electricity", "label": "Electricity (grid or solar)", "kind": "bool"},
    {"name": "improved_water", "label": "Improved drinking-water source", "kind": "bool"},
    {"name": "livestock_tlu", "label": "Livestock (tropical livestock units)", "kind": "float", "min": 0, "max": 50},
    {"name": "owns_phone", "label": "Owns a mobile phone", "kind": "bool"},
    {"name": "n_children_u5", "label": "Children under 5", "kind": "int", "min": 0, "max": 10},
]

PMT_FEATURE_NAMES = [f["name"] for f in PMT_FEATURES]
