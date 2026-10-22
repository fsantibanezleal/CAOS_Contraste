"""Cross-field rules of a C17 document that JSON Schema cannot state (review of U12-S, finding F6).

``semantic_findings(doc)`` returns one message per rule a C17 variant or models document breaks; an empty list means none. The U12-S
tests run it over the fixtures and plants; the C17 bake (U12-P) names it as its gate and runs it over every document it writes under
data/derived/C17/ (tests/contracts_u12/test_u12_review_fixes.py runs it over each committed document).
"""
from __future__ import annotations

import math
from typing import Any

KEYS = ("p05", "p25", "median", "p75", "p95")
GRID = [(5, 10000), (5, 20000), (10, 10000), (10, 20000)]


def _ilm(lc: float, bic: float) -> float:
    return math.log(math.e - 1 + (lc / bic) ** 0.8)


def _bic(bi: float) -> float:
    return 0.12 * min(bi, 1e9) + 0.15 * max(min(bi, 30e9) - 1e9, 0) + 0.18 * max(bi - 30e9, 0)


def _ordered(vals: list[float]) -> bool:
    return all(b >= a for a, b in zip(vals, vals[1:]))


def _close(a: float, b: float, rel: float = 1e-6) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-9)


def _variant(doc: dict) -> list[str]:
    o: dict[str, Any] = doc["outputs"]
    out: list[str] = []
    t, cal = o["truth"], o["calibration"]["fit"]
    if not (t["severity"]["tail_index"] == o["tail_index"] == cal["tail_index"]):
        out.append("tail index: truth.severity, outputs and calibration.fit differ")
    if t["severity"]["scale_eur"] != cal["scale_eur"]:
        out.append("scale: truth.severity and calibration.fit differ")
    if t["frequency"]["counted_above_eur"] != t["severity"]["location_eur"]:
        out.append("truth.frequency.counted_above_eur differs from truth.severity.location_eur")
    cells = o["cells"]
    if [(c["years"], c["collection_threshold_eur"]) for c in cells] != GRID:
        out.append("cells are not the cross (5, 10) x (10000, 20000) in the fixed order")
    for c in cells:
        if c["id"] != f"y{c['years']}-h{c['collection_threshold_eur']}":
            out.append(f"cell id {c['id']} does not name its years and threshold")
        if t["severity"]["location_eur"] > c["collection_threshold_eur"]:
            out.append(f"truth floor above the collection threshold of cell {c['id']}")
    q = t["annual_loss_quantile"]
    mc = q["mc_check"]
    if mc["agrees"] != (abs(mc["value_eur"] - q["value_eur"]) <= 3 * mc["standard_error_eur"]):
        out.append("mc_check.agrees does not follow value and standard error")
    ex = o["exceedance"]
    grid = ex["grid_eur"]
    if not all(b > a for a, b in zip(grid, grid[1:])):
        out.append("exceedance grid is not strictly increasing")
    for name in ("monte_carlo", "panjer", "fft"):
        curve = ex[name]["exceedance"]
        if len(curve) != len(grid):
            out.append(f"exceedance.{name} has {len(curve)} points for a grid of {len(grid)}")
        # the Panjer curve is null past the end of its grid (c17-outputs 2.0.0): the nulls are a suffix, the rest is the curve
        real = [x for x in curve if x is not None]
        if curve[: len(real)] != real:
            out.append(f"exceedance.{name} has a null before a value: the nulls are only the part of the axis past the grid")
        if any(not 0 <= x <= 1 for x in real) or any(b > a + 1e-12 for a, b in zip(real, real[1:])):
            out.append(f"exceedance.{name} is not a nonincreasing curve in [0, 1]")
    qm = ex["quantile_999_eur"]
    if abs(qm["panjer"] - qm["fft"]) / qm["panjer"] >= 1e-3:
        out.append("panjer and fft 99.9 percent quantiles differ by 0.1 percent or more")
    if not _close(qm[q["method"]], q["value_eur"]):
        out.append("truth quantile differs from the quantile of its method in the exceedance block")
    bank = o["bank"]
    bi = bank["business_indicator"]
    if not _close(bi["bi_eur"], bi["ildc_eur"] + bi["sc_eur"] + bi["fc_eur"], 1e-12):
        out.append("bi_eur is not ILDC + SC + FC")
    if not _close(bank["bic_eur"], _bic(bi["bi_eur"]), 1e-9):
        out.append("bic_eur does not follow OPE25.7 from bi_eur")
    if bank["bucket"] != (1 if bi["bi_eur"] <= 1e9 else 2 if bi["bi_eur"] <= 30e9 else 3):
        out.append("bank bucket does not follow bi_eur")
    seeds = []
    for c in cells:
        r = c["replications"]
        seeds.append((r["seed_first"], r["seed_first"] + r["n_replications"] - 1, c["id"]))
        if r["n_failed"] >= r["n_replications"]:
            out.append(f"cell {c['id']}: every replication failed")
        truth = q["value_eur"]
        for name, cap in c["capital"].items():
            s = cap if name in ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla") else cap["summary"]
            if s is None:
                continue
            for block in ("capital_eur", "ratio_to_truth"):
                if not _ordered([s[block][k] for k in KEYS]):
                    out.append(f"cell {c['id']} {name}.{block}: percentiles are disordered")
            if any(not _close(s["ratio_to_truth"][k], s["capital_eur"][k] / truth) for k in KEYS):
                out.append(f"cell {c['id']} {name}: ratio_to_truth is not capital_eur over the true quantile")
            if not _close(s["iqr_over_truth"], (s["capital_eur"]["p75"] - s["capital_eur"]["p25"]) / truth):
                out.append(f"cell {c['id']} {name}: iqr_over_truth is inconsistent")
            if s["n_defined"] > r["n_replications"]:
                out.append(f"cell {c['id']} {name}: n_defined exceeds n_replications")
        rows = c["threshold_stability"]
        th = [x["threshold_eur"] for x in rows]
        if th != sorted(set(th)) or th[0] != c["collection_threshold_eur"]:
            out.append(f"cell {c['id']}: threshold_stability thresholds are not increasing from the collection threshold")
        for x in rows:
            b = x["tail_index"]
            if not b["p05"] <= b["median"] <= b["p95"] or x["n_fits"] > r["n_replications"]:
                out.append(f"cell {c['id']}: threshold_stability row at {x['threshold_eur']} is inconsistent")
        sma = c["sma"]
        if sma["bic_eur"] != bank["bic_eur"] or sma["bucket"] != bank["bucket"]:
            out.append(f"cell {c['id']}: sma bic or bucket differs from the bank")
        for block in ("lc_eur", "ilm", "orc_eur", "orc_over_true_quantile"):
            if not _ordered([sma[block][k] for k in KEYS]):
                out.append(f"cell {c['id']} sma.{block}: percentiles are disordered")
        for k in KEYS:
            want = 1.0 if sma["discretion_applied"] in ("bucket-1-ilm-one", "national-ilm-one") else _ilm(sma["lc_eur"][k], sma["bic_eur"])
            if not _close(sma["ilm"][k], want):
                out.append(f"cell {c['id']} sma.ilm.{k} does not follow OPE25.8 and the discretion")
            if not _close(sma["orc_eur"][k], sma["bic_eur"] * sma["ilm"][k]):
                out.append(f"cell {c['id']} sma.orc_eur.{k} is not BIC x ILM")
            if not _close(sma["orc_over_true_quantile"][k], sma["orc_eur"][k] / truth):
                out.append(f"cell {c['id']} sma.orc_over_true_quantile.{k} is inconsistent")
    seeds.sort()
    for a, b in zip(seeds, seeds[1:]):
        if a[1] >= b[0]:
            out.append(f"seed ranges of cells {a[2]} and {b[2]} overlap")
    by_id = {c["id"]: c for c in cells}
    resp = o["sma_response"]
    if resp["cell_id"] not in by_id:
        out.append("sma_response.cell_id names no cell")
    else:
        years = by_id[resp["cell_id"]]["years"]
        rows = resp["rows"]
        if resp["bic_eur"] != bank["bic_eur"]:
            out.append("sma_response.bic_eur differs from the bank")
        for x in rows:
            if not _close(x["lc_eur"] - rows[0]["lc_eur"], 15 * x["added_loss_eur"] / years):
                out.append("sma_response: lc_eur does not rise by 15 x added loss / years")
            if not _close(x["ilm"], _ilm(x["lc_eur"], resp["bic_eur"])) or not _close(x["orc_eur"], resp["bic_eur"] * x["ilm"]):
                out.append("sma_response: ilm or orc_eur does not follow OPE25.8")
        added = [x["added_loss_eur"] for x in rows]
        if added != sorted(set(added)) or added[0] != 0:
            out.append("sma_response: added losses are not increasing from 0")
        if not _ordered([x["lda_capital_eur"] for x in rows]):
            out.append("sma_response: the LDA capital falls as a loss is added")
    si = o["scenario_influence"]
    if si["cell_id"] not in by_id:
        out.append("scenario_influence.cell_id names no cell")
    ids = [s["scenario_id"] for s in si["scenarios"]]
    if len(set(ids)) != len(ids):
        out.append("scenario_influence: duplicate scenario ids")
    for s in si["scenarios"]:
        if not math.isclose(s["influence"], (si["base_capital_eur"] - s["capital_without_eur"]) / si["base_capital_eur"], abs_tol=1e-6):
            out.append(f"scenario {s['scenario_id']}: influence is not (base - without) / base")
    return out


def _models(doc: dict) -> list[str]:
    f = doc["fit"]
    out: list[str] = []
    v = f["variants"]
    xi = [x["tail_index"] for x in v]
    if xi != sorted(set(xi)):
        out.append("variants are not in strictly increasing tail index order")
    if not _ordered([x["true_quantile_999_eur"] for x in v]) or len({x["true_quantile_999_eur"] for x in v}) != len(v):
        out.append("the true 99.9 percent quantile does not increase with the tail index")
    for x in v:
        if x["location_eur"] != f["generator"]["generator_floor_eur"]:
            out.append(f"variant {x['variant_id']}: location differs from the generator floor")
    if len({x["variant_id"] for x in v}) != len(v):
        out.append("duplicate variant ids")
    return out


def semantic_findings(doc: dict) -> list[str]:
    """Findings for a C17 variant document (``outputs``) or models document (``fit``)."""
    return _variant(doc) if "outputs" in doc else _models(doc)
