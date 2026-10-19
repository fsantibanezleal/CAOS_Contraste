"""The cross-field checks of the C02, C20 and C21 documents, as importable functions (as ``tests/contracts_u11/semantics.py`` for C16).

JSON Schema cannot hold these: they compare values across fields, recompute numbers from counts or compare sequences. The bakes
U14-P1, U14-P2 and U14-P3 call ``check_c02``, ``check_c20`` and ``check_c21`` on every document they write (a non-empty list is a
refusal to publish), and the producer tests run them over every committed document (the fixtures and the baked data). The formulas
come from the dossiers and the U14 sizing; this module imports no fixture builder and no test constant (the approved named
parameters are copied below and a test pins the copy to ``values.py``).

Each function returns a list of messages, empty when the document conforms. The four-fifths flag is decided on the counts in exact
arithmetic (``fractions.Fraction``), never on a float ratio: 60/100 over 75/100 is 0.7999999999999999 in floats and exactly 4/5.
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Any

# The named parameters the main session approved (decision V6, 2026-10-19): the bakes write exactly these values.
APPROVED_PARAMS: dict[str, Any] = {
    "perturbation_grid": [0.05, 0.1, 0.25, 0.5, 1.0], "perturbation_tolerance": 0.02, "n_seeds": 20, "n_bootstrap_refits": 100,
    "overfit_tolerance": 0.05, "weak_spot_multiple": 2.0, "shift_score": "resemblance-classifier-probability",
    "worst_subsample_share": 0.10, "decision_cutoff_reject_share": 0.20,
}


class Report(list):
    def need(self, ok: bool, message: str) -> None:
        if not ok:
            self.append(message)


def close(a: float, b: float, tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def four_fifths_flag(x_g: int, n_g: int, x_h: int, n_h: int) -> bool:
    """Group (x_g of n_g) against the highest-rate group (x_h of n_h): flagged when its rate is below four-fifths of the highest rate.

    Exact arithmetic on the counts: (x_g / n_g) < (4 / 5) * (x_h / n_h)  <=>  5 * x_g * n_h < 4 * x_h * n_g.
    """
    return 5 * x_g * n_h < 4 * x_h * n_g


def params_of(doc: dict) -> dict[str, Any]:
    return {p["name"]: p["value"] for p in doc.get("outputs", doc.get("fit", {})).get("parameters", [])}


def check_params(doc: dict, out: Report) -> None:
    for name, value in params_of(doc).items():
        out.need(name in APPROVED_PARAMS and APPROVED_PARAMS[name] == value, f"named parameter {name} = {value!r} is not the approved value")


def curve_ok(xs: list[float], ys: list[float], label: str, out: Report) -> None:
    out.need(len(xs) == len(ys), f"{label}: the two arrays have different lengths ({len(xs)} and {len(ys)})")
    for arr, nm in ((xs, "x"), (ys, "y")):
        out.need(all(b >= a for a, b in zip(arr, arr[1:])), f"{label}: the {nm} points decrease")
        out.need(bool(arr) and arr[0] == 0 and arr[-1] == 1, f"{label}: the {nm} points do not run from 0 to 1")


# ---------------------------------------------------------------------------------------------------------------- C02
def check_c02(doc: dict) -> Report:
    out = Report()
    o = doc["outputs"]
    c = o["counts"]
    out.need(c["events"] <= c["rows"], "counts: events above rows")
    out.need(close(c["event_rate"], c["events"] / c["rows"], 1e-5), "counts: event_rate is not events over rows")
    s = o["split"]
    out.need(s["train_rows"] + s["calibration_rows"] + s["holdout_rows"] == c["rows"], "split: the three slices do not add to the rows")
    out.need(s["holdout_events"] <= s["holdout_rows"] and s["holdout_events"] <= c["events"], "split: holdout events above holdout rows or events")
    if o["pooled"] is not None:
        files = o["pooled"]["files"]
        out.need(sorted(f["years"] for f in files) == [1, 2, 3, 4, 5], "pooled: the five files are not the 1 to 5 year files, once each")
        out.need(sum(f["rows"] for f in files) == c["rows"] and sum(f["events"] for f in files) == c["events"], "pooled: the files do not add to the counts")
    for r in o["rungs"]:
        m = r["model_id"]
        d = r["discrimination"]
        ci = d["auc_ci"]
        out.need(ci["lo"] <= d["auc"] <= ci["hi"], f"{m}: the AUC is outside its interval or the interval is reversed")
        out.need(close(d["gini"], 2 * d["auc"] - 1, 1e-6), f"{m}: gini is not 2 * auc - 1")
        ov = r["overfit"]
        out.need(close(ov["gap"], ov["train_auc"] - ov["holdout_auc"], 1e-9), f"{m}: overfit gap is not train minus holdout")
        out.need(ov["flag"] == (ov["gap"] > ov["tolerance"]), f"{m}: overfit flag disagrees with gap > tolerance")
        out.need(ov["tolerance"] == APPROVED_PARAMS["overfit_tolerance"], f"{m}: overfit tolerance is not the named parameter")
        curve_ok(r["roc"]["fpr"], r["roc"]["tpr"], f"{m} roc", out)
        curve_ok(r["cap"]["population"], r["cap"]["defaults"], f"{m} cap", out)
        out.need(all(b["lo"] <= b["dr"] <= b["hi"] for b in r["reliability"]), f"{m}: a reliability bin has its rate outside its interval")
        pds = [b["pd"] for b in r["reliability"]]
        out.need(all(b > a for a, b in zip(pds, pds[1:])), f"{m}: the reliability bins are not in increasing PD order")
    for ch in o["challenger"]:
        out.need(ch["auc_diff_ci"]["lo"] <= ch["auc_diff"] <= ch["auc_diff_ci"]["hi"], "challenger: the AUC difference is outside its interval")
        out.need(ch["brier_diff_ci"]["lo"] <= ch["brier_diff"] <= ch["brier_diff_ci"]["hi"], "challenger: the Brier difference is outside its interval")
    ts = o["term_structure"]
    pts = ts["points"]
    out.need([p["years"] for p in pts] == [1, 2, 3, 4, 5], "term structure: the points are not years 1 to 5 in order")
    cum = [p["cumulative_pd"] for p in pts]
    out.need(ts["cumulative_nondecreasing"] == all(b >= a for a, b in zip(cum, cum[1:])), "term structure: cumulative_nondecreasing disagrees with the points")
    survive = 1.0
    for p in pts:
        survive *= 1 - p["hazard"]
        out.need(abs((1 - survive) - p["cumulative_pd"]) < 1e-3, f"term structure: year {p['years']} cumulative is not 1 - product of (1 - hazard)")
    check_params(doc, out)
    return out


# ---------------------------------------------------------------------------------------------------------------- C20
def check_c20(doc: dict) -> Report:
    out = Report()
    o = doc["outputs"]
    check_params(doc, out)
    p = params_of(doc)
    out.need(o["impact_detail"]["cutoff"]["reject_share"] == p.get("decision_cutoff_reject_share"), "impact: the cut-off reject share is not the named parameter")
    kind = o["kind"]
    if kind == "shock":
        for block in ("shipped", "applied"):
            for row in o[block]["rows"]:
                out.need(row["n_reaching_structured_view"] <= row["n_records"], f"{block} {row['shock_id']}: more records reach the view than the batch holds")
                v = row["drift"]["variables"]
                out.need(close(row["drift"]["psi_max"], max(x["psi"] for x in v)), f"{block} {row['shock_id']}: psi_max is not the maximum of the variables")
                out.need(close(row["drift"]["csi_max"], max(x["csi"] for x in v)), f"{block} {row['shock_id']}: csi_max is not the maximum of the variables")
    elif kind == "shift":
        conf = o["synthetic_shift"]["label_free"]["conformal"]
        out.need(close(conf["target_coverage"], 1 - conf["alpha"], 1e-12), "conformal: target coverage is not 1 - alpha")
        w = conf["coverage_by_window"]
        n = sum(x["n"] for x in w)
        out.need(close(sum(x["n"] * x["coverage"] for x in w) / n, conf["coverage"], 1e-6), "conformal: the windows do not average to the overall coverage")
    elif kind == "seeds":
        for r in o["rows"]:
            a = r["auc"]
            out.need(a["min"] <= a["mean"] <= a["max"], f"{r['rung']}: the AUC mean is outside its minimum and maximum")
            out.need(r["n_seeds"] == p.get("n_seeds"), f"{r['rung']}: n_seeds is not the named parameter")
            out.need(r["reason_code_overlap"]["n_refits"] == p.get("n_bootstrap_refits"), f"{r['rung']}: n_refits is not the named parameter")
        for e in o["explainer_agreement"]:
            out.need((e["rank_correlation"] is None) == (e["reason_if_null"] is not None), f"{e['rung']}: rank_correlation and its reason disagree")
            out.need(e["n_features"] >= len(e["top_features"]), f"{e['rung']}: more top features than features")
            for f in e["top_features"]:
                edges = f["ale"]["edges"]
                out.need(len(f["ale"]["effect"]) == len(edges) - 1, f"{f['feature']}: ALE needs one effect per bin")
                out.need(all(b > a for a, b in zip(edges, edges[1:])), f"{f['feature']}: ALE edges do not increase")
    elif kind == "perturbation":
        by = {r["eps"]: r for r in o["rows"]}
        out.need(o["preset_eps"] in by, "perturbation: the preset scale is not on the grid")
        for r in o["rows"]:
            expected = -r["metric"]["auc_delta"] > p.get("perturbation_tolerance", 0.02) if r["eps"] == o["preset_eps"] else None
            out.need(expected is None or r["finding"] == expected, f"perturbation: finding at eps {r['eps']} disagrees with the tolerance")
    elif kind == "leakage":
        s = o["screen"]["single_feature_auc"]
        out.need(s["suspect"] == (s["max_auc"] > o["thresholds"]["single_feature_auc"]["value"]), "leakage: suspect disagrees with max_auc above the limit")
        out.need(o["caught"] == (s["suspect"] or o["screen"]["temporal_order"]["violations"] > 0 or o["screen"]["entity_overlap"]["share"] > 0
                                 or o["screen"]["resemblance_auc"] > o["thresholds"]["resemblance_auc"]["value"]),
                 "leakage: caught disagrees with the four screens")
    return out


# ---------------------------------------------------------------------------------------------------------------- C21
def two_proportion_z(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    pooled = (x1 + x2) / (n1 + n2)
    if pooled in (0.0, 1.0):
        return 0.0, 1.0
    z = (x1 / n1 - x2 / n2) / math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return z, math.erfc(abs(z) / math.sqrt(2))


def check_c21(doc: dict) -> Report:
    out = Report()
    o = doc["outputs"]
    for a in o["attributes"]:
        f = a["field"]
        counts: dict[str, tuple[int, int]] = {}
        for g in a["groups"]:
            counts[g["group"]] = (g["n_approved"], g["n"])
            out.need(g["n_approved"] + g["n_denied"] == g["n"], f"{f} {g['group']}: approved and denied do not add to n")
            out.need(close(g["selection_rate"], g["n_approved"] / g["n"], 1e-12), f"{f} {g['group']}: the selection rate is not approved over n")
        out.need(len(counts) == len(a["groups"]), f"{f}: a group is listed twice")
        out.need(a["reference_group"] in counts, f"{f}: the reference group is not among the groups")
        # the four-fifths line: each group against the highest-rate group, exact counts
        ff = a["four_fifths"]
        top = max(counts, key=lambda g: Fraction(counts[g][0], counts[g][1]))
        out.need(ff["highest_rate_group"] == top, f"{f} four-fifths: the highest-rate group is {top!r}, the document says {ff['highest_rate_group']!r}")
        out.need(sorted(r["group"] for r in ff["groups"]) == sorted(counts), f"{f} four-fifths: one row per group is required")
        xh, nh = counts[top]
        for r in ff["groups"]:
            if r["group"] not in counts:
                continue
            x, n = counts[r["group"]]
            expected_flag = four_fifths_flag(x, n, xh, nh)
            out.need(r["flag"] == expected_flag, f"{f} four-fifths: {r['group']} flag is {r['flag']} but the exact counts give {expected_flag}")
            ratio = None if xh == 0 else float(Fraction(x, n) / Fraction(xh, nh))
            same = (ratio is None and r["ratio_to_highest"] is None) or (ratio is not None and r["ratio_to_highest"] is not None
                                                                         and close(ratio, r["ratio_to_highest"], 1e-9))
            out.need(same, f"{f} four-fifths: {r['group']} ratio_to_highest is not its rate over the highest rate")
        for c in a["contrasts"]:
            g = c["group"]
            out.need(g in counts and c["reference_group"] == a["reference_group"], f"{f} {g}: a contrast must be a group against the attribute's reference group")
            if g not in counts or a["reference_group"] not in counts or g == a["reference_group"]:
                out.append(f"{f} {g}: a contrast of a group with itself or outside the groups")
                continue
            x1, n1 = counts[g]
            x2, n2 = counts[a["reference_group"]]
            out.need((c["n_group"], c["n_reference"]) == (n1, n2), f"{f} {g}: the contrast sizes are not the group sizes")
            out.need(close(c["selection_rate_group"], x1 / n1, 1e-12) and close(c["selection_rate_reference"], x2 / n2, 1e-12), f"{f} {g}: the contrast rates are not the counts over n")
            out.need(close(c["parity_gap"], x1 / n1 - x2 / n2, 1e-12), f"{f} {g}: parity gap is not the rate difference")
            ratio = None if x2 == 0 else (x1 / n1) / (x2 / n2)
            for nm, v in (("parity_ratio", c["parity_ratio"]), ("adverse impact ratio", c["adverse_impact_ratio"]["value"])):
                out.need((ratio is None and v is None) or (ratio is not None and v is not None and close(ratio, v, 1e-9)), f"{f} {g}: {nm} is not the rate over the reference rate")
            z, pz = two_proportion_z(x1, n1, x2, n2)
            out.need(close(c["z_test"]["statistic"], z, 1e-7) and close(c["z_test"]["p_value"], pz, 1e-7), f"{f} {g}: the z-test is not the pooled two-proportion test")
            odds = None if (n1 - x1) * x2 == 0 else (x1 * (n2 - x2)) / ((n1 - x1) * x2)
            fo = c["fisher_exact"]["odds_ratio"]
            out.need((odds is None and fo is None) or (odds is not None and fo is not None and close(odds, fo, 1e-9)), f"{f} {g}: Fisher odds ratio is not the sample odds ratio")
            for key in ("controlled", "rate_spread"):
                est = c[key]["estimate"]
                if est is not None:
                    out.need(est["ci"]["lo"] <= est["coefficient"] <= est["ci"]["hi"], f"{f} {g} {key}: the coefficient is outside its interval")
                    if key == "controlled":
                        out.need(close(est["odds_ratio"], math.exp(est["coefficient"]), 1e-9), f"{f} {g}: the odds ratio is not exp(coefficient)")
            conf = c["confirmation"]["estimate"]
            if conf is not None:
                out.need((conf["fit_year"], conf["confirm_year"]) == (o["fit_year"], o["confirm_year"]), f"{f} {g}: the confirmation years are not the pair's years")
                fc, cc = conf["fit_coefficient"], conf["confirm_coefficient"]
                out.need(conf["same_sign"] == ((fc > 0) == (cc > 0) and fc != 0 and cc != 0), f"{f} {g}: same_sign disagrees with the coefficients")
                expect = None if fc == 0 else cc / fc
                out.need((expect is None and conf["size_ratio"] is None) or (expect is not None and conf["size_ratio"] is not None and close(expect, conf["size_ratio"], 1e-9)),
                         f"{f} {g}: size_ratio is not confirm over fit")
    st = o["situation_testing"]
    out.need(st["n_significant"] <= st["n_cases"] <= st["n_complainants"], "situation testing: n_significant <= n_cases <= n_complainants fails")
    return out
