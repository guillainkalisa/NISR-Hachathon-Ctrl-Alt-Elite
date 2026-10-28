"""Rwanda's 30 districts and their provinces (administrative units since 2006)."""

PROVINCES = {
    "Kigali City": ["Gasabo", "Kicukiro", "Nyarugenge"],
    "Southern": ["Gisagara", "Huye", "Kamonyi", "Muhanga", "Nyamagabe", "Nyanza", "Nyaruguru", "Ruhango"],
    "Western": ["Karongi", "Ngororero", "Nyabihu", "Nyamasheke", "Rubavu", "Rusizi", "Rutsiro"],
    "Northern": ["Burera", "Gakenke", "Gicumbi", "Musanze", "Rulindo"],
    "Eastern": ["Bugesera", "Gatsibo", "Kayonza", "Kirehe", "Ngoma", "Nyagatare", "Rwamagana"],
}

DISTRICT_TO_PROVINCE = {d: p for p, ds in PROVINCES.items() for d in ds}
DISTRICTS = sorted(DISTRICT_TO_PROVINCE)


def normalise_district(name):
    """Map a raw district label (any case, stray spaces, 'Akarere ka ...') to the canonical name."""
    if name is None:
        return None
    key = str(name).strip().lower().replace("akarere ka ", "").replace(" district", "")
    for d in DISTRICTS:
        if d.lower() == key:
            return d
    return None
