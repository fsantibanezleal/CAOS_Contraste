"""E1. The structure of the band in each committed aggregate (prediction H1), the identity of the aggregates, the closed-form rows
recomputed with the engine, the six tests of the aggregation battery as committed, and the analytic checks of the theory section.

Reads ``data/derived/C18`` only; calls ``riskvalidation.aggregation.simple`` for the two closed-form rows. Writes
``e1_structure.json``. Run time: under 5 seconds.

    python manuscripts/dependence-band-with-every-aggregate/experiments/e1_structure.py
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

import bandkit as bk
from riskvalidation.aggregation import simple as rv_simple

EXPECTED = ["lower-bound", "simple-sum", "variance-covariance", "gaussian-copula", "t-copula", "t-copula", "t-copula", "worst-case"]


def main() -> None:
    crit = bk.hypotheses()["H1"]["criterion"]
    blocks = bk.committed_blocks()
    rows_out, digests = {}, {}
    for name, block in blocks.items():
        band = block["band"]
        methods = [r["method"] for r in band]
        headline = [r["method"] for r in band if r["status"] == "headline-capital"]
        info = [r for r in band if r["status"] == "information-not-capital"]
        ec = np.array([m["ec_clp_m"] for m in block["marginals"]])
        corr = np.array(block["correlation"]["matrix"])
        by = {(r["method"], r["nu"]): r["capital_clp_m"] for r in band}
        sum_ok = bool(np.isclose(rv_simple.simple_sum(ec), by[("simple-sum", None)], rtol=1e-12))
        vc_ok = bool(np.isclose(rv_simple.variance_covariance(ec, corr), by[("variance-covariance", None)], rtol=1e-12))
        ok = {
            "rows": len(band) == crit["rows"], "order": methods == EXPECTED, "headline_is_simple_sum": headline == ["simple-sum"],
            "information_rows": len(info) == crit["information_rows"],
            "one_horizon_and_level": {r["horizon_years"] for r in band} == {1} and {r["confidence_level"] for r in band} == {0.999},
            "euler_additive": block["euler"]["additivity"]["relative_error"] <= crit["euler_relative_error_max"],
            "model_risk_information": block["model_risk"]["status"] == "information-not-capital",
            "euler_information": block["euler"]["status"] == "information-not-capital",
        }
        digests[name] = hashlib.sha256(json.dumps(block, sort_keys=True).encode("utf-8")).hexdigest()
        rows_out[name] = {"checks": ok, "all_pass": all(ok.values()), "euler_relative_error": block["euler"]["additivity"]["relative_error"],
                          "simple_sum_recomputed": sum_ok, "variance_covariance_recomputed": vc_ok, "headline": block["headline"]["capital_clp_m"],
                          "sha256": digests[name]}
    base = digests["baseline"]
    identical = [n for n, d in digests.items() if d == base]
    t_doc = bk.read("t-copula-baseline.json")
    tests = [{"test_id": t["test_id"], "light": t["light"], "statistic": t["statistic"], "metric": t["metric"]} for t in t_doc["tests"]]
    # the findings of the document, by id
    findings = [{"id": f["id"], "severity": f["severity"]} for f in t_doc["findings"]]
    case = bk.Case()
    base_rows = {bk.Case.label(case, r["method"], r["nu"]): r["capital_clp_m"] for r in case.committed_band}
    stress_rows = {bk.Case.label(case, r["method"], r["nu"]): r["capital_clp_m"] for r in case.committed_stress_band}
    # the closed form of the market-credit stress on the square-root row: VC_s^2 - VC_b^2 = 2 (0.8 - 0.5) EC_credit EC_market
    ec = case.ec
    vc_b, vc_s = base_rows["variance-covariance"], stress_rows["variance-covariance"]
    closed = 2.0 * 0.3 * ec[0] * ec[1]
    # the analytic upper bound of the worst case: VaR(sum) <= ES(sum) <= sum of the ES (coherence of ES)
    sum_es = float(case.es.sum())
    worst_var = base_rows["worst-case"] + case.el_total
    lower_var = base_rows["lower-bound"] + case.el_total
    stress_gauss_move = stress_rows["gaussian-copula"] / base_rows["gaussian-copula"] - 1.0
    h5 = bk.hypotheses()["H5"]["criterion"]
    out = {
        "H1": {"criterion": crit, "aggregates": len(blocks), "all_pass": all(v["all_pass"] for v in rows_out.values()),
               "outcome": "held" if len(blocks) == crit["aggregates"] and all(v["all_pass"] for v in rows_out.values()) else "refuted",
               "per_aggregate": rows_out},
        "distinct_aggregates": len(set(digests.values())), "identical_to_baseline": identical,
        "tests_of_the_document": tests, "findings_of_the_document": findings,
        "closed_form": {"vc_base": vc_b, "vc_stress": vc_s, "square_difference": vc_s ** 2 - vc_b ** 2, "closed_form_difference": float(closed)},
        "analytic_bound": {"sum_of_es": sum_es, "worst_var": worst_var, "lower_var": lower_var, "el_total": case.el_total,
                           "slack": sum_es - worst_var, "worst_var_over_sum_of_es": worst_var / sum_es,
                           "sum_of_var": float(case.var.sum()), "comonotonic_var": float(case.var.sum())},
        "H5": {"criterion": h5,
               "lower_relative_difference": abs(stress_rows["lower-bound"] / base_rows["lower-bound"] - 1.0),
               "worst_relative_difference": abs(stress_rows["worst-case"] / base_rows["worst-case"] - 1.0),
               "gaussian_move": stress_gauss_move,
               "row_moves": {k: stress_rows[k] / base_rows[k] - 1.0 for k in base_rows},
               "outcome": "held" if (abs(stress_rows["lower-bound"] / base_rows["lower-bound"] - 1.0) <= h5["bound_relative_difference_max"]
                                     and abs(stress_rows["worst-case"] / base_rows["worst-case"] - 1.0) <= h5["bound_relative_difference_max"]
                                     and stress_gauss_move > h5["gaussian_move_min"]) else "refuted"},
        "base_rows": base_rows, "stress_rows": stress_rows, "headline": case.headline,
        "marginals": {m["risk"]: {"el": m["el_clp_m"], "var": m["var_clp_m"], "es": m["es_clp_m"], "ec": m["ec_clp_m"], "var_se": m["var_se_clp_m"]}
                      for m in case.marginals},
        "euler": bk.read("baseline.json")["outputs"]["aggregation"]["euler"],
        "model_risk": bk.read("baseline.json")["outputs"]["aggregation"]["model_risk"],
        "diversification": bk.read("baseline.json")["outputs"]["aggregation"]["diversification"],
        "rosenberg_schuermann": t_doc["outputs"]["rosenberg_schuermann"],
        "copula_sensitivity": t_doc["outputs"]["copula_sensitivity"],
    }
    # the sample's smallest value of each marginal: losses can be negative (a market gain)
    out["grid_minimum"] = {r: float(case.quantiles[r].min()) for r in bk.RISKS}
    out["grid_points"] = int(case.probs.size)
    path = bk.write_json("e1_structure.json", out)
    print("wrote", path.name, "H1:", out["H1"]["outcome"], "distinct aggregates", out["distinct_aggregates"], "H5:", out["H5"]["outcome"])


if __name__ == "__main__":
    main()
