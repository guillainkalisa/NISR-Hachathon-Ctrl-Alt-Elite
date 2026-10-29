"""Load the trained proxy-means-test model and score one household."""

import json
import warnings
from functools import lru_cache

import joblib
import numpy as np
from django.conf import settings

from pipeline.features import PMT_FEATURES

# Probability bands shown to the user; a screening aid, not an eligibility decision.
BANDS = [(0.6, "high", "Likely poor - prioritise for verification"),
         (0.35, "medium", "Possibly poor - verify on a home visit"),
         (0.0, "low", "Unlikely to be poor")]

N_REASONS = 4
LABELS = {f["name"]: f["label"] for f in PMT_FEATURES}
CHOICES = {f["name"]: dict(f["choices"]) for f in PMT_FEATURES if f["kind"] == "choice"}
KINDS = {f["name"]: f["kind"] for f in PMT_FEATURES}


@lru_cache(maxsize=1)
def load_model():
    if not settings.PMT_MODEL_PATH.exists():
        return None
    return joblib.load(settings.PMT_MODEL_PATH)


@lru_cache(maxsize=1)
def load_metrics():
    if not settings.PMT_METRICS_PATH.exists():
        return None
    return json.loads(settings.PMT_METRICS_PATH.read_text())


def score(values):
    bundle = load_model()
    if bundle is None:
        return None
    features = bundle["features"]
    row = {f: float(values[f]) for f in features}
    prob = _predict(bundle, [row])[0]
    level, message = next((lvl, msg) for cut, lvl, msg in BANDS if prob >= cut)
    return {"probability": prob, "level": level, "message": message, "is_demo": bundle["is_demo"],
            "reasons": explain(bundle, row, prob)}


def explain(bundle, row, prob):
    """Top features by how much the probability changes when each is set to the typical household's value.

    Each `effect` is in percentage points: positive means this trait makes the household look poorer
    than a typical household would.
    """
    reference = bundle.get("reference")
    if not reference:
        return []
    swapped = []
    for f in bundle["features"]:
        alt = dict(row)
        alt[f] = reference[f]
        swapped.append(alt)
    probs = _predict(bundle, swapped)
    reasons = []
    for f, p_ref in zip(bundle["features"], probs):
        effect = (prob - p_ref) * 100
        if abs(effect) >= 0.5:
            reasons.append({"feature": LABELS[f], "value": _show(f, row[f]), "typical": _show(f, reference[f]),
                            "effect": effect})
    return sorted(reasons, key=lambda r: -abs(r["effect"]))[:N_REASONS]


def _predict(bundle, rows):
    # A plain array in the model's feature order keeps pandas off the web server; sklearn only warns
    # that the column names are missing.
    X = np.array([[r[f] for f in bundle["features"]] for r in rows], dtype=float)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="X does not have valid feature names")
        return bundle["model"].predict_proba(X)[:, 1].tolist()


def _show(feature, value):
    kind = KINDS[feature]
    if kind == "bool":
        return "Yes" if value >= 0.5 else "No"
    if kind == "choice":
        return CHOICES[feature].get(int(round(value)), str(value))
    if kind == "int":
        return str(int(round(value)))
    return f"{value:.1f}"
