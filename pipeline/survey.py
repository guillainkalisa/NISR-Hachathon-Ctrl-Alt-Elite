"""Design-based survey estimators.

EICV is a stratified two-stage cluster sample, so plain means understate the
uncertainty. Ratios are estimated with their Taylor-linearised standard errors
(the same approach as Stata's `svy: mean`), treating PSUs as sampled with
replacement within strata.
"""

import numpy as np


def ratio(df, num, den, weight="hh_weight", strata="stratum", psu="psu", domain=None):
    """Weighted ratio sum(w*num) / sum(w*den) over an optional domain.

    For a share within a subgroup, pass num = indicator * subgroup flag.

    `num`, `den` and `domain` are column names or boolean/numeric Series aligned
    with `df`. Domain estimation keeps the full sample so the variance accounts
    for the domain's random sample size.

    Returns a dict with estimate, se, ci_low, ci_high and the unweighted n.
    """
    y = _col(df, num).astype(float)
    x = _col(df, den).astype(float)
    d = _col(df, domain).astype(float) if domain is not None else 1.0
    w = df[weight].astype(float)

    wy, wx = (w * y * d), (w * x * d)
    total_x = wx.sum()
    n = int(((x * d) > 0).sum())
    if total_x <= 0:
        return {"estimate": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan, "n": n}

    r = wy.sum() / total_x
    # Linearised score for each household, summed to PSU totals.
    z = (wy - r * wx) / total_x
    psu_totals = z.groupby([df[strata], df[psu]]).sum()

    var = 0.0
    for _, z_h in psu_totals.groupby(level=0):
        n_h = len(z_h)
        if n_h > 1:
            var += n_h / (n_h - 1) * ((z_h - z_h.mean()) ** 2).sum()
    se = float(np.sqrt(var))
    return {
        "estimate": float(r),
        "se": se,
        "ci_low": float(max(0.0, r - 1.96 * se)),
        "ci_high": float(min(1.0, r + 1.96 * se)) if 0 <= r <= 1 else float(r + 1.96 * se),
        "n": n,
    }


def total(df, value, weight="hh_weight", domain=None):
    """Weighted population total of `value` (column name or Series)."""
    v = _col(df, value).astype(float)
    d = _col(df, domain).astype(float) if domain is not None else 1.0
    return float((df[weight] * v * d).sum())


def _col(df, ref):
    return df[ref] if isinstance(ref, str) else ref
