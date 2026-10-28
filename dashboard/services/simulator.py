"""Budget simulator: where should extra social-protection slots go?

Assumption (stated in the UI): new slots in a district reach still-excluded poor
households at that district's current targeting precision (1 - inclusion
error), with diminishing returns as the excluded pool shrinks:

    poor reached in d from x new slots = E_d * (1 - exp(-p_d * x / E_d))

where E_d is the number of excluded poor households and p_d the precision.
Two allocation rules are compared for the same total:
  * "proportional" - split slots in proportion to current beneficiaries (business as usual)
  * "need-based"   - give each chunk of slots to the district where it reaches the most poor
"""

import heapq
import math

CHUNKS = 400


def reached(excluded, precision, slots):
    if excluded <= 0 or slots <= 0:
        return 0.0
    return excluded * (1 - math.exp(-precision * slots / excluded))


def simulate(indicators, extra_slots):
    """`indicators`: iterable of Indicator rows for one round. Returns per-district rows and totals."""
    rows = [{
        "district": ind.district.name,
        "slug": ind.district.slug,
        "excluded": ind.excluded_poor,
        "precision": 1 - (ind.inclusion_error if ind.inclusion_error is not None else 1),
        "beneficiaries": ind.beneficiaries,
    } for ind in indicators]
    if not rows or extra_slots <= 0:
        return {"rows": rows, "proportional_total": 0, "need_total": 0}

    total_benef = sum(r["beneficiaries"] for r in rows) or 1
    for r in rows:
        r["prop_slots"] = extra_slots * r["beneficiaries"] / total_benef
        r["prop_reached"] = reached(r["excluded"], r["precision"], r["prop_slots"])
        r["need_slots"] = 0.0

    # Greedy marginal-gain allocation; the gain curve is concave so this is optimal up to chunk size.
    chunk = extra_slots / CHUNKS
    heap = [(-_gain(r, chunk), i) for i, r in enumerate(rows)]
    heapq.heapify(heap)
    for _ in range(CHUNKS):
        _, i = heapq.heappop(heap)
        rows[i]["need_slots"] += chunk
        heapq.heappush(heap, (-_gain(rows[i], chunk), i))
    for r in rows:
        r["need_reached"] = reached(r["excluded"], r["precision"], r["need_slots"])

    rows.sort(key=lambda r: -r["need_slots"])
    return {
        "rows": rows,
        "proportional_total": sum(r["prop_reached"] for r in rows),
        "need_total": sum(r["need_reached"] for r in rows),
    }


def _gain(r, chunk):
    return reached(r["excluded"], r["precision"], r["need_slots"] + chunk) - reached(r["excluded"], r["precision"], r["need_slots"])
