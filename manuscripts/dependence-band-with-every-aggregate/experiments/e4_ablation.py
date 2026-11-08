"""E4. What each component of the protocol contributes (predictions H6 and H7, and the ablation table).

* The common horizon and level: the market marginal read at 99 percent in place of 99.9 percent, through the engine's consistency
  test and through the engine's refusal of an ``ec`` that does not match the marginal.
* The tests that need each row: every test of the aggregation battery is called with the inputs that exist when a row family is
  removed; a test is runnable when it returns a light.
* The Euler allocation: 20 repetitions of the allocation of the Gaussian aggregate's expected shortfall, against the allocation by
  stand-alone expected shortfall that does not add up.
* The rows of the band as interval estimators of the planted capital: coverage and width when a row family is removed (reads
  ``e3_planted_truth.json``).

Calls ``riskvalidation.validation.aggregation``, ``portfolio.euler``, ``aggregation.band``. Writes ``e4_ablation.json``. Run time: under a minute.

    python manuscripts/dependence-band-with-every-aggregate/experiments/e4_ablation.py
"""
from __future__ import annotations

import json
import time

import numpy as np

import bandkit as bk
from riskvalidation.portfolio import euler as rv_euler
from riskvalidation.portfolio import portfolio as rv_port
from riskvalidation.validation import aggregation as rv_va
from riskvalidation.validation import portfolio as rv_vp

INTERIOR = ["variance-covariance", "gaussian-copula", "t-copula-nu4", "t-copula-nu8", "t-copula-nu30"]
EULER_SEEDS = list(range(4001, 4021))


def attempt(fn):
    """A test is runnable when it returns a result with a light; an exception or a not-evaluated light means it is not."""
    try:
        r = fn()
    except Exception as exc:  # noqa: BLE001 - the type is recorded
        return {"runnable": False, "reason": f"{type(exc).__name__}: {str(exc)[:110]}"}
    light = r.light.value
    return {"runnable": light in ("green", "amber", "red"), "light": light, "reason": "" if light != "not_evaluated" else "not evaluated"}


def main() -> None:
    t0 = time.time()
    h = bk.hypotheses()
    case = bk.Case()
    base = {k: v["capital_clp_m"] for k, v in ((case.label(r["method"], r["nu"]), r) for r in case.committed_band)}
    stress = {case.label(r["method"], r["nu"]): r["capital_clp_m"] for r in case.committed_stress_band}
    # ---------------------------------------------------------------- H6: level mismatch
    c6 = h["H6"]["criterion"]
    j = bk.RISKS.index(c6["marginal"])
    wrong_ec = float(case.ppfs[j](np.array([c6["wrong_level"]]))[0]) - float(case.el[j])
    ec_wrong = case.ec.copy()
    ec_wrong[j] = wrong_ec
    levels = [bk.LEVEL] * 4
    levels[j] = c6["wrong_level"]
    consistency = rv_va.horizon_confidence_consistency([1.0] * 4, levels)
    horizon_bad = rv_va.horizon_confidence_consistency([1.0, 1.0, 10.0 / 250.0, 1.0], [bk.LEVEL] * 4)
    ok = rv_va.horizon_confidence_consistency([1.0] * 4, [bk.LEVEL] * 4)
    refusal = None
    try:
        case.band(seed=bk.COMMITTED_SEED, ec=ec_wrong, n_draws=20_000)
    except ValueError as exc:
        refusal = str(exc)
    change = float(ec_wrong.sum() / case.ec.sum() - 1.0)
    h6 = {"criterion": c6, "market_ec_at_99": wrong_ec, "market_ec_at_999": float(case.ec[j]), "market_ec_change": wrong_ec / float(case.ec[j]) - 1.0,
          "simple_sum_mismatched": float(ec_wrong.sum()), "simple_sum": float(case.ec.sum()), "headline_change": change,
          "consistency_light_mismatched_level": consistency.light.value, "consistency_light_mismatched_horizon": horizon_bad.light.value,
          "consistency_light_matched": ok.light.value, "engine_refusal": refusal,
          "outcome": "held" if (abs(change) >= c6["headline_change_min"] and consistency.light.value == "red") else "refuted"}
    print("H6", h6["outcome"], round(time.time() - t0), "s", flush=True)
    # ---------------------------------------------------------------- H7: the tests and the rows they need
    gauss, vc, headline = base["gaussian-copula"], base["variance-covariance"], base["simple-sum"]
    t_caps = [(nu, base[f"t-copula-nu{nu:g}"]) for nu in case.nu_set]
    factors_all = [base[k] / headline for k in INTERIOR]
    # the Euler additivity test needs the allocation, which exists once the Gaussian sample exists
    seed = bk.COMMITTED_SEED
    joint = bk.rv_cop.simulate_component_losses(case.ppfs, case.corr, "gaussian", None, bk.N_DRAWS, seed, bk.CHUNK)
    total = joint.sum(axis=1)
    es_total = rv_port.es_from_sample(total, bk.LEVEL)
    contrib = rv_euler.es_contributions(joint, total, bk.LEVEL)
    from scipy import stats

    sds = case.ec / float(stats.norm.ppf(bk.LEVEL))
    ppfs_n = [(lambda u, s=s: s * stats.norm.ppf(u)) for s in sds]
    agg_n = bk.rv_cop.copula_aggregate(ppfs_n, case.corr, "gaussian", None, 0.0, bk.LEVEL, bk.N_DRAWS, seed + 7, bk.CHUNK)
    tests = {
        "aggregation.simple_sum_and_variance_covariance": {
            "needs": ["Gaussian row", "marginal capitals", "correlation matrix"],
            "with_all_rows": attempt(lambda: rv_va.simple_sum_and_variance_covariance(case.ec, case.corr, gauss)),
            "with_gaussian_only": attempt(lambda: rv_va.simple_sum_and_variance_covariance(case.ec, case.corr, gauss))},
        "aggregation.copula_choice_sensitivity": {
            "needs": ["Gaussian row", "t rows"],
            "with_all_rows": attempt(lambda: rv_va.copula_choice_sensitivity(gauss, t_caps)),
            "without_t_rows": attempt(lambda: rv_va.copula_choice_sensitivity(gauss, []))},
        "aggregation.worst_case_bracket": {
            "needs": ["lower bound", "worst case", "interior rows"],
            "with_all_rows": attempt(lambda: rv_va.worst_case_bracket(base["lower-bound"], [base[k] for k in INTERIOR], base["worst-case"])),
            "without_bounds": {"runnable": False, "reason": "no lower bound and no worst case to bracket with"}},
        "aggregation.correlation_stress": {
            "needs": ["Gaussian row of the base matrix", "Gaussian row of the stressed matrix"],
            "with_all_rows": attempt(lambda: rv_va.correlation_stress(gauss, stress["gaussian-copula"])),
            "without_stressed_band": {"runnable": False, "reason": "no second matrix, so no second Gaussian row"}},
        "aggregation.diversification_sign": {
            "needs": ["the diversification factor of each interior row"],
            "with_all_rows": attempt(lambda: rv_va.diversification_sign(factors_all)),
            "with_gaussian_only": attempt(lambda: rv_va.diversification_sign([gauss / headline]))},
        "aggregation.horizon_confidence_consistency": {
            "needs": ["horizon and level of each marginal"],
            "with_all_rows": attempt(lambda: rv_va.horizon_confidence_consistency([1.0] * 4, [bk.LEVEL] * 4)),
            "with_gaussian_only": attempt(lambda: rv_va.horizon_confidence_consistency([1.0] * 4, [bk.LEVEL] * 4))},
        "portfolio.euler_additivity": {
            "needs": ["the Euler contributions and the aggregate expected shortfall"],
            "with_all_rows": attempt(lambda: rv_vp.euler_additivity(contrib, es_total, 1e-6)),
            "with_gaussian_only": attempt(lambda: rv_vp.euler_additivity(contrib, es_total, 1e-6))},
        "aggregation.elliptical_mc_agreement": {
            "needs": ["square-root row", "an elliptical simulation"],
            "with_all_rows": attempt(lambda: rv_va.elliptical_mc_agreement(agg_n.ec, agg_n.var_se, vc)),
            "with_gaussian_only": attempt(lambda: rv_va.elliptical_mc_agreement(agg_n.ec, agg_n.var_se, float(np.sqrt(case.ec @ case.corr @ case.ec))))},
        "aggregation.rosenberg_schuermann_reference": {
            "needs": ["simple sum", "Gaussian row"],
            "with_all_rows": attempt(lambda: rv_va.rosenberg_schuermann_reference(headline, gauss)),
            "with_gaussian_only": attempt(lambda: rv_va.rosenberg_schuermann_reference(float(case.ec.sum()), gauss))},
    }
    runnable_gauss_only = [k for k, v in tests.items() if v.get("with_gaussian_only", {}).get("runnable")]
    needs_more = [k for k in tests if k not in runnable_gauss_only]
    doc_lights = {t["test_id"]: t["light"] for t in bk.read("t-copula-baseline.json")["tests"]}
    for k, v in tests.items():
        v["light_in_committed_document"] = doc_lights.get(k)
    c7 = h["H7"]["criterion"]
    t_removed = tests["aggregation.copula_choice_sensitivity"]["without_t_rows"]["runnable"]
    share = len(runnable_gauss_only) / c7["tests_total"]
    h7 = {"criterion": c7, "tests": tests, "runnable_with_gaussian_only": runnable_gauss_only, "need_other_rows": needs_more,
          "runnable_with_gaussian_only_share": share,
          "clause_removing_rows_makes_tests_unrunnable": (not t_removed),
          "clause_gaussian_only_share_ok": share <= c7["runnable_with_gaussian_only_max_share"],
          "non_green_lights_in_document": {k: v for k, v in doc_lights.items() if v != "green"},
          "outcome": "held" if ((not t_removed) and share <= c7["runnable_with_gaussian_only_max_share"]) else "refuted"}
    print("H7", h7["outcome"], round(time.time() - t0), "s", flush=True)
    # ---------------------------------------------------------------- the Euler allocation: repetitions, and the stand-alone allocation
    shares, gaps, es_tot = [], [], []
    for s in EULER_SEEDS:
        jl = bk.rv_cop.simulate_component_losses(case.ppfs, case.corr, "gaussian", None, bk.N_DRAWS, s, bk.CHUNK)
        tt = jl.sum(axis=1)
        es_t = rv_port.es_from_sample(tt, bk.LEVEL)
        c = rv_euler.es_contributions(jl, tt, bk.LEVEL)
        shares.append((c / es_t).tolist())
        gaps.append(abs(float(c.sum()) - es_t) / es_t)
        es_tot.append(es_t)
    sh = np.array(shares)
    standalone_es = case.es
    euler = {"seeds": EULER_SEEDS, "risks": list(bk.RISKS), "share_mean": sh.mean(axis=0).tolist(), "share_sd": sh.std(axis=0, ddof=1).tolist(),
             "max_relative_gap": float(max(gaps)), "es_total_mean": float(np.mean(es_tot)), "es_total_sd": float(np.std(es_tot, ddof=1)),
             "standalone_es": standalone_es.tolist(), "standalone_share": (standalone_es / standalone_es.sum()).tolist(),
             "sum_of_standalone_es": float(standalone_es.sum()),
             "standalone_over_aggregate_es": float(standalone_es.sum() / np.mean(es_tot)),
             "euler_contribution_mean": (sh.mean(axis=0) * np.mean(es_tot)).tolist(),
             "benefit_by_risk_mean": (1.0 - sh.mean(axis=0) * np.mean(es_tot) / standalone_es).tolist()}
    print("Euler done", round(time.time() - t0), "s", flush=True)
    # ---------------------------------------------------------------- the rows as interval estimators of the planted capital
    e3 = json.loads((bk.HERE / "e3_planted_truth.json").read_text(encoding="utf-8"))
    rows = e3["structures"]
    base_e2 = e3["band_rows_used"]["base"]
    stress_e2 = e3["band_rows_used"]["stress"]
    lower, worst = base_e2["lower-bound"], base_e2["worst-case"]
    variants = []

    def interval(name, keys_base, keys_stress, with_bounds, rowsel):
        lo = min([base_e2[k] for k in keys_base] + [stress_e2[k] for k in keys_stress] + ([lower] if with_bounds else []))
        hi = max([base_e2[k] for k in keys_base] + [stress_e2[k] for k in keys_stress] + ([worst] if with_bounds else []))
        cov = [bool(lo - 3 * r["truth_se"] <= r["truth"] <= hi + 3 * r["truth_se"]) for r in rowsel]
        widths = [(hi - lo) / r["truth"] for r in rowsel]
        return {"variant": name, "kind": "interval", "low": lo, "high": hi, "covered": int(sum(cov)), "of": len(rowsel),
                "share": sum(cov) / len(rowsel), "median_width_over_truth": float(np.median(widths)),
                "missed": [r["id"] for r, c in zip(rowsel, cov) if not c]}

    variants.append(interval("full band (bounds and all interior rows, base and stressed matrix)", INTERIOR, INTERIOR, True, rows))
    variants.append(interval("without the sharp bounds (interior rows, base and stressed matrix)", INTERIOR, INTERIOR, False, rows))
    variants.append(interval("without the stressed matrix (interior rows of the base matrix)", INTERIOR, [], False, rows))
    variants.append(interval("without the t copula rows (square-root rule and Gaussian copula, base matrix)", ["variance-covariance", "gaussian-copula"], [], False, rows))

    def point(name, getter, tol=0.05):
        errs = [getter(r) / r["truth"] - 1.0 for r in rows]
        within = [abs(e) <= tol for e in errs]
        return {"variant": name, "kind": "point", "tolerance": tol, "covered": int(sum(within)), "of": len(rows), "share": sum(within) / len(rows),
                "median_abs_error": float(np.median(np.abs(errs))), "max_abs_error": float(np.max(np.abs(errs))),
                "mean_error": float(np.mean(errs)), "errors": {r["id"]: e for r, e in zip(rows, errs)}}

    variants.append(point("Gaussian copula row alone", lambda r: base_e2["gaussian-copula"]))
    variants.append(point("square-root row alone", lambda r: base_e2["variance-covariance"]))
    variants.append(point("simple sum alone (the headline)", lambda r: base_e2["simple-sum"]))
    variants.append(point("hybrid quantile with the correlation of the truth sample", lambda r: r["hybrid_calibrated"]))
    variants.append(point("Gaussian copula with the rank correlation of the truth sample", lambda r: r["gaussian_kendall_calibrated"]))
    variants.append(point("Gaussian copula alone, tolerance 10 percent", lambda r: base_e2["gaussian-copula"], 0.10))
    variants.append(interval("without the t copula rows, with the stressed matrix (square-root rule and Gaussian copula, both matrices)",
                             ["variance-covariance", "gaussian-copula"], ["variance-covariance", "gaussian-copula"], False, rows))
    variants.append(interval("t copula rows only (4, 8 and 30 degrees of freedom, both matrices)",
                             ["t-copula-nu4", "t-copula-nu8", "t-copula-nu30"], ["t-copula-nu4", "t-copula-nu8", "t-copula-nu30"], False, rows))
    out = {"H6": h6, "H7": h7, "euler": euler, "ablation_variants": variants, "seconds": round(time.time() - t0)}
    path = bk.write_json("e4_ablation.json", out)
    print("wrote", path.name, "H6", h6["outcome"], "H7", h7["outcome"], "seconds", out["seconds"], flush=True)


if __name__ == "__main__":
    main()
