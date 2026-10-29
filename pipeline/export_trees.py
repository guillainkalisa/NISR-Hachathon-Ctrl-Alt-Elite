"""Export the trained poverty model as plain numpy arrays, so the website can score households without scikit-learn.

    python -m pipeline.export_trees            # models/pmt.joblib -> models/pmt.npz

`train_pmt` calls this automatically. `dashboard/services/pmt.py` reads the .npz file and walks the trees itself,
which keeps scikit-learn and scipy (about 190 MB) off the web server.
"""

import json
from pathlib import Path

import joblib
import numpy as np

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
NODE_FIELDS = ["value", "feature_idx", "num_threshold", "missing_go_to_left", "left", "right", "is_leaf",
               "is_categorical", "bitset_idx"]


def export(bundle, path):
    model = bundle["model"]
    if model.n_trees_per_iteration_ != 1:
        raise SystemExit("Only binary classifiers are supported")
    trees = [it[0] for it in model._predictors]
    offsets = np.cumsum([0] + [len(t.nodes) for t in trees])
    nodes = np.concatenate([t.nodes for t in trees])
    # Category splits: one bitset per split node; offsets let every tree index its own block.
    bitsets = [t.raw_left_cat_bitsets for t in trees]
    bitset_offsets = np.cumsum([0] + [len(b) for b in bitsets])
    known, f_idx_map = model._bin_mapper.make_known_categories_bitsets()
    # With category features, scikit-learn first reorders the columns (category columns first) and replaces each
    # category by its position in the category list; the trees are indexed on that transformed input.
    order, categories = list(range(len(bundle["features"]))), []
    if getattr(model, "_preprocessor", None) is not None:
        (_, encoder, cat_mask), (_, _, num_mask) = model._preprocessor.transformers_[:2]
        order = list(np.flatnonzero(cat_mask)) + list(np.flatnonzero(num_mask))
        categories = encoder.categories_
    arrays = {f"node_{f}": nodes[f] for f in NODE_FIELDS}
    meta = {k: bundle[k] for k in ("features", "reference", "round", "is_demo")}
    meta["reference"] = {k: float(v) for k, v in meta["reference"].items()}
    np.savez_compressed(
        path, **arrays, tree_offsets=offsets[:-1], bitset_offsets=bitset_offsets[:-1],
        left_cat_bitsets=np.concatenate(bitsets) if sum(map(len, bitsets)) else np.zeros((0, 8), np.uint32),
        known_cat_bitsets=known, f_idx_map=f_idx_map, column_order=np.array(order, dtype=int),
        cat_values=np.concatenate(categories).astype(float) if categories else np.zeros(0),
        cat_offsets=np.cumsum([0] + [len(c) for c in categories]),
        baseline=np.float64(np.ravel(model._baseline_prediction)[0]), meta=np.array(json.dumps(meta)),
    )


if __name__ == "__main__":
    export(joblib.load(MODEL_DIR / "pmt.joblib"), MODEL_DIR / "pmt.npz")
    print(f"Wrote {MODEL_DIR / 'pmt.npz'}")
