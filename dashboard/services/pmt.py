"""Load the trained proxy-means-test model and score one household.

The model is read from models/pmt.npz (written by pipeline/export_trees.py) and its trees are walked with numpy,
so the website needs neither scikit-learn nor scipy.
"""

import json
from functools import lru_cache

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
    with np.load(settings.PMT_MODEL_PATH) as z:
        bundle = {k: z[k] for k in z.files}
    bundle.update(json.loads(str(bundle.pop("meta"))))
    return bundle


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
    X = _encode(bundle, np.array([[r[f] for f in bundle["features"]] for r in rows], dtype=float))
    raw = np.full(len(X), float(bundle["baseline"]))
    for tree, bits in zip(bundle["tree_offsets"], bundle["bitset_offsets"]):
        raw += _walk(bundle, X, int(tree), int(bits))
    return (1 / (1 + np.exp(-raw))).tolist()


def _encode(b, X):
    """Same input transform as scikit-learn: category columns first, each category replaced by its index."""
    X = X[:, b["column_order"]]
    offsets = b["cat_offsets"]
    for j, (start, end) in enumerate(zip(offsets[:-1], offsets[1:])):
        cats = b["cat_values"][start:end]
        match = X[:, j, None] == cats
        X[:, j] = np.where(match.any(axis=1), match.argmax(axis=1), np.nan)
    return X


def _walk(b, X, tree, bits):
    """Leaf values for every row of X in one tree, following scikit-learn's HistGradientBoosting split rules."""
    node = np.full(len(X), tree)
    rows = np.arange(len(X))
    while True:
        inner = ~b["node_is_leaf"][node].astype(bool)
        if not inner.any():
            return b["node_value"][node]
        n, r = node[inner], rows[inner]
        x = X[r, b["node_feature_idx"][n]]
        left = x <= b["node_num_threshold"][n]
        cat = b["node_is_categorical"][n].astype(bool)
        if cat.any():
            feat = b["node_feature_idx"][n][cat]
            v = x[cat]
            ok = (v >= 0) & (v < 256) & (v == np.floor(v))
            vi = np.where(ok, v, 0).astype(int)
            known = ok & _in_bitset(b["known_cat_bitsets"][b["f_idx_map"][feat]], vi)
            goes_left = _in_bitset(b["left_cat_bitsets"][bits + b["node_bitset_idx"][n][cat]], vi)
            # Unknown categories are treated like missing values.
            left[cat] = np.where(known, goes_left, b["node_missing_go_to_left"][n][cat].astype(bool))
        missing = np.isnan(x)
        left[missing] = b["node_missing_go_to_left"][n][missing].astype(bool)
        node[inner] = tree + np.where(left, b["node_left"][n], b["node_right"][n])


def _in_bitset(bitsets, values):
    return ((bitsets[np.arange(len(values)), values // 32] >> (values % 32).astype(np.uint32)) & 1).astype(bool)


def _show(feature, value):
    kind = KINDS[feature]
    if kind == "bool":
        return "Yes" if value >= 0.5 else "No"
    if kind == "choice":
        return CHOICES[feature].get(int(round(value)), str(value))
    if kind == "int":
        return str(int(round(value)))
    return f"{value:.1f}"
