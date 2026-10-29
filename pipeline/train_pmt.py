"""Train the proxy-means-test (PMT) poverty model.

The model predicts whether a household is poor from traits a field officer can
observe in a short visit (features.PMT_FEATURES). Its key evaluation is the
policy question: *with the same number of beneficiaries as today, how many more
poor households would be reached if they were ranked by the model?*

Writes models/pmt.joblib and models/pmt_metrics.json.

Usage:
  python -m pipeline.train_pmt --source data/interim --round EICV7
  python -m pipeline.train_pmt --source data/demo --round EICV7 --demo
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from pipeline import export_trees
from pipeline.features import PMT_FEATURES, PMT_FEATURE_NAMES

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = ROOT / "models"


def targeting_comparison(test, prob):
    """Compare current programme receipt with model ranking at equal budget (weighted)."""
    w = test["hh_weight"].to_numpy()
    poor = test["poor"].to_numpy()
    current = test["receives_sp"].to_numpy()
    n_slots = (w * current).sum()

    # Fill the same weighted number of slots, highest predicted poverty first.
    order = np.argsort(-prob)
    filled = np.cumsum(w[order]) <= n_slots
    model_pick = np.zeros_like(current)
    model_pick[order[filled]] = 1

    total_poor = (w * poor).sum()

    def stats(pick):
        reached = (w * poor * pick).sum()
        return {"poor_reached_share": reached / total_poor, "inclusion_error": 1 - reached / max((w * pick).sum(), 1)}

    return {"current": stats(current), "model": stats(model_pick), "slots": float(n_slots)}


def _weighted_median(values, weights):
    ok = values.notna()
    v, w = values[ok].to_numpy(), weights[ok].to_numpy()
    order = np.argsort(v)
    cum = np.cumsum(w[order])
    return float(v[order][np.searchsorted(cum, cum[-1] / 2)])


def train(source, rnd, demo):
    df = pd.read_csv(Path(source) / f"households_{rnd}.csv")
    missing = [c for c in PMT_FEATURE_NAMES if c not in df]
    if missing:
        raise SystemExit(f"Missing PMT features: {missing}")
    X, y, w = df[PMT_FEATURE_NAMES], df["poor"], df["hh_weight"]

    # Split by PSU so neighbouring households never sit on both sides of the split.
    train_idx, test_idx = next(GroupShuffleSplit(test_size=0.25, random_state=7).split(X, y, groups=df["psu"]))
    categorical = [f["kind"] == "choice" for f in PMT_FEATURES]
    model = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                           categorical_features=categorical, random_state=7)
    model.fit(X.iloc[train_idx], y.iloc[train_idx], sample_weight=w.iloc[train_idx])

    test = df.iloc[test_idx]
    prob = model.predict_proba(X.iloc[test_idx])[:, 1]
    auc = roc_auc_score(y.iloc[test_idx], prob, sample_weight=w.iloc[test_idx])
    imp = permutation_importance(model, X.iloc[test_idx], y.iloc[test_idx], scoring="roc_auc",
                                 n_repeats=10, random_state=7)
    labels = {f["name"]: f["label"] for f in PMT_FEATURES}
    importance = sorted(({"feature": labels[n], "importance": float(v)}
                         for n, v in zip(PMT_FEATURE_NAMES, imp.importances_mean)),
                        key=lambda r: -r["importance"])

    MODEL_DIR.mkdir(exist_ok=True)
    # A "typical household" (weighted median of each feature) that explanations are measured against.
    train = df.iloc[train_idx]
    reference = {f: _weighted_median(train[f], train["hh_weight"]) for f in PMT_FEATURE_NAMES}
    bundle = {"model": model, "features": PMT_FEATURE_NAMES, "reference": reference, "round": rnd, "is_demo": demo}
    joblib.dump(bundle, MODEL_DIR / "pmt.joblib")
    export_trees.export(bundle, MODEL_DIR / "pmt.npz")  # what the website loads
    metrics = {"round": rnd, "is_demo": demo, "auc": float(auc), "n_train": len(train_idx), "n_test": len(test_idx),
               "importance": importance, "targeting": targeting_comparison(test, prob)}
    (MODEL_DIR / "pmt_metrics.json").write_text(json.dumps(metrics, indent=2))

    t = metrics["targeting"]
    print(f"AUC {auc:.3f} | poor reached at equal budget: current {t['current']['poor_reached_share']:.1%}"
          f" vs model {t['model']['poor_reached_share']:.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(ROOT / "data" / "interim"))
    ap.add_argument("--round", default="EICV7")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    train(args.source, args.round, args.demo)
