"""Builds the four U8-S fixture documents (docs/contracts/fixtures/c11 and c13).

Run: ``python tests/contracts_u8/build_fixtures.py``. Deterministic, standard library only. The numbers are small and
synthetic on purpose; they satisfy the identities the engine contract promises (docs/contracts/engine/market-api.md,
recomputed by tests/contracts_u8 from market_math.py) but are fixtures, never results: every document is labelled
``fixture`` in its provenance and its ids, the series names are those a real bake will use, the values are not.
"""
from __future__ import annotations

import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import market_math as mm  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures"
NE = "fixture: the test did not run, no number stands in for it"


def r(x: float, n: int = 6) -> float:
    return round(x, n)


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def envelope_common(truth: str) -> dict:
    return {
        "provenance": {
            "truth_status": truth,
            "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
            "licence_classes": {"fixture-not-a-result": "fixture"},
            "generators": ["fixture:u8-s-contracts"],
            "seed": 0,
            "code_version": "fixture",
            "riskvalidation_version": None,
        },
        "lane": {"lane": "precompute", "reasons": ["fixture"]},
    }


def model_summary(mid: str, rung: str, title: str) -> dict:
    return {
        "id": mid, "family": "market-var-es", "rung": rung,
        "title": txt(f"Fixture model {title}", f"Modelo de ejemplo {title}"),
        "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture",
        "licence": "MIT", "calibration": None, "parameters": {}, "checkpoint_sha256": None,
    }


def model_record(mid: str, rung: str, title: str) -> dict:
    d = model_summary(mid, rung, title)
    d["details"] = {}
    return d


def row(test_id: str, model_id: str, alpha: float | None, statistic, p, metric, n, n_events, light: str, h0: str, alt: str,
        ref: str, notes: str = "fixture value", extras: dict | None = None, amber=0.10, red=0.05) -> dict:
    return {
        "test_id": test_id, "model_id": model_id, "segment": None if alpha is None else f"alpha={alpha}",
        "statistic": statistic, "p_value": p, "metric": metric, "h0": h0, "alternative": alt,
        "policy_version": "fixture-policy-0", "alpha_amber": amber, "alpha_red": red, "light": light,
        "n": n, "n_events": n_events, "inputs_hash": "0" * 64, "reference": ref, "notes": notes, "extras": extras or {},
    }


def not_evaluated(test_id: str, model_id: str, alpha: float, reason: str, h0: str, alt: str, ref: str) -> dict:
    d = row(test_id, model_id, alpha, None, None, None, None, None, "not_evaluated", h0, alt, ref, notes=reason)
    return d


def light_of(p: float, amber: float, red: float) -> str:
    return "red" if p < red else "amber" if p < amber else "green"


# ------------------------------------------------------------------------------------------------------- C11


def weekdays(start: date, n: int) -> list[date]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def shift_weekdays(d: date, back: int) -> date:
    while back > 0:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            back -= 1
    return d


def student_t(rng: random.Random, nu: int) -> float:
    g = rng.gauss(0, 1)
    chi2 = 2.0 * rng.gammavariate(nu / 2, 1.0)
    return g / math.sqrt(chi2 / nu) * math.sqrt((nu - 2) / nu)


MODELS = [
    # model_id, rung, title, lag, k, es_mult, es_state, undefined days
    ("hs-250", "R1", "historical simulation 250 days", 40, 0.80, 1.00, "forecast", []),
    ("ewma-094", "R4", "EWMA lambda 0.94", 1, 1.05, 1.02, "forecast", []),
    ("evt-mf", "R7", "conditional EVT (McNeil and Frey)", 1, 1.15, 1.08, "undefined-on-days", [120, 121]),
    ("caviar-sav", "R8", "CAViaR symmetric absolute value", 1, 1.00, 1.00, "not-forecast", []),
]
LEVELS = (0.01, 0.025)
ES_RATIO = {a: mm.ND.pdf(mm.ND.inv_cdf(a)) / a / -mm.ND.inv_cdf(a) for a in LEVELS}


def build_c11_variant() -> tuple[dict, dict]:
    rng = random.Random(20221)
    days = weekdays(date(2022, 1, 3), 260)
    missing = [date(2022, 1, 17), date(2022, 2, 21), date(2022, 5, 30), date(2022, 7, 4), date(2022, 9, 5)]
    grid = [x for x in days if x not in missing]
    n = len(grid)
    est_end = [date(2021, 12, 31)] + grid[:-1]
    est_start = [shift_weekdays(e, 1000) for e in est_end]
    sigma = [0.0045 * (1 + 0.55 * math.sin(2 * math.pi * i / 110) + 0.25 * math.sin(2 * math.pi * i / 37)) for i in range(n)]
    loss = [r(sigma[i] * student_t(rng, 5)) for i in range(n)]

    results: dict[str, dict[float, dict]] = {}
    for mid, rung, title, lag, k, esm, state, undef in MODELS:
        results[mid] = {}
        for a in LEVELS:
            z = -mm.ND.inv_cdf(a)
            var, es = [], []
            for i in range(n):
                s_hat = sigma[max(0, i - lag)]
                v = r(k * s_hat * z)
                var.append(v)
                es.append(r(max(v * (1.0 + 1e-6), v * ES_RATIO[a] * esm)) if state != "not-forecast" else None)
            for i in undef:
                es[i] = None
            exc = [i for i in range(n) if loss[i] > var[i]]
            fz = [mm.fz0_loss(loss[i], var[i], es[i], a) for i in range(n) if es[i] is not None]
            tick = sum(mm.tick_loss(loss[i], var[i], a) for i in range(n)) / n
            results[mid][a] = dict(var=var, es=es, exc=exc, fz=fz, tick=tick, state=state, undef=undef)

    tests: list[dict] = []
    zscore: dict[tuple[str, float], dict] = {}
    for mid, rung, *_ in MODELS:
        for a in LEVELS:
            res = results[mid][a]
            flags = [1 if i in set(res["exc"]) else 0 for i in range(n)]
            x = sum(flags)
            ids = []
            lr = mm.kupiec_lr(n, x, a)
            p = mm.chi2_sf(lr, 1)
            tests.append(row("market.kupiec_pof", mid, a, r(lr), r(p), r(mm.kupiec_exact_p(n, x, a)), n, x, light_of(p, 0.10, 0.05),
                             "the exceedance probability equals alpha", "the exceedance probability differs from alpha",
                             "Kupiec 1995; dossier 05 B.1",
                             extras={"p_value_exact_basis": "binomial-minlike", "expected_events": r(a * n)}))
            ids.append("market.kupiec_pof")
            li = mm.christoffersen_ind_lr(flags)
            pi_ = mm.chi2_sf(li, 1)
            tests.append(row("market.christoffersen_independence", mid, a, r(li), r(pi_), None, n, x, light_of(pi_, 0.10, 0.05),
                             "exceedances are independent", "exceedances cluster", "Christoffersen 1998; dossier 05 B.2"))
            ids.append("market.christoffersen_independence")
            lcc = lr + li
            pcc = mm.chi2_sf(lcc, 2)
            tests.append(row("market.christoffersen_conditional_coverage", mid, a, r(lcc), r(pcc), None, n, x, light_of(pcc, 0.10, 0.05),
                             "correct unconditional coverage and independence", "coverage is wrong or exceedances cluster",
                             "Christoffersen 1998; dossier 05 B.2"))
            ids.append("market.christoffersen_conditional_coverage")
            if a == 0.01:
                if x >= 2:
                    tests.append(row("market.duration_test", mid, a, 1.2, 0.27, None, n, x, "green",
                                     "no-hit durations are memoryless (Weibull b = 1)", "durations are not memoryless",
                                     "Christoffersen and Pelletier 2004; dossier 05 B.3",
                                     notes="fixture value, not recomputed here; Weibull form UNVERIFIED in the dossier"))
                else:
                    tests.append(not_evaluated("market.duration_test", mid, a, "fewer than two exceedances: no completed no-hit duration",
                                               "no-hit durations are memoryless (Weibull b = 1)", "durations are not memoryless",
                                               "Christoffersen and Pelletier 2004; dossier 05 B.3"))
                ids.append("market.duration_test")
            if a == 0.025:
                zr = ("Acerbi and Szekely 2014; dossier 05 B.5")
                if res["state"] == "forecast":
                    z2 = mm.z2(loss, res["var"], res["es"], a)
                    sig = [v / -mm.ND.inv_cdf(a) for v in res["var"]]
                    srng = random.Random(77 + len(zscore))
                    draws = []
                    for _ in range(10000):
                        zsum = 0.0
                        for i in range(n):
                            l_ = sig[i] * srng.gauss(0, 1)
                            if l_ > res["var"][i]:
                                zsum += (-l_) / (n * a * res["es"][i])
                        draws.append(zsum + 1.0)
                    draws.sort()
                    c5, c001 = draws[int(0.05 * len(draws))], draws[int(0.0001 * len(draws))]
                    pz = (sum(1 for q in draws if q <= z2) + 1) / (len(draws) + 1)
                    lo, hi = draws[0], draws[-1] + 1e-9
                    edges = [lo + (hi - lo) * j / 20 for j in range(21)]
                    counts = [0] * 20
                    for q in draws:
                        counts[min(19, int((q - lo) / (hi - lo) * 20))] += 1
                    zscore[(mid, a)] = dict(model_id=mid, alpha=a, statistic="Z2", realised=r(z2), critical_5pct=r(c5),
                                            critical_0_01pct=r(c001), n_draws=len(draws), p_value=r(pz, 9),
                                            histogram={"edges": [r(e) for e in edges], "counts": counts})
                    light = light_of(pz, 0.05, 0.0001)
                    tests.append(row("market.acerbi_szekely", mid, a, r(z2), r(pz, 9), None, n, len(res["exc"]), light,
                                     "the ES forecast is correct", "the ES is underestimated", zr, amber=0.05, red=0.0001,
                                     extras={"statistic_name": "Z2", "n_draws": len(draws), "critical_5pct": r(c5), "critical_0_01pct": r(c001), "reference": {"yellow": -0.70, "red": -1.8}}))
                else:
                    why = ("the ES is undefined on days where xi is at or above 1" if res["state"] == "undefined-on-days"
                           else "the model forecasts no ES")
                    tests.append(not_evaluated("market.acerbi_szekely", mid, a, why, "the ES forecast is correct",
                                               "the ES is underestimated", zr))
                ids.append("market.acerbi_szekely")
            res["test_ids"] = ids

    gates = ("market.kupiec_pof", "market.christoffersen_conditional_coverage", "market.acerbi_szekely")
    eligible: dict[str, list[str]] = {}
    for mid, *_ in MODELS:
        eligible[mid] = sorted({t["test_id"] for t in tests if t["model_id"] == mid and t["test_id"] in gates and t["light"] == "red"})

    def fz_mean(mid: str, a: float):
        f = results[mid][a]["fz"]
        return (sum(f) / len(f)) if f else None

    champions, dm_rows, mcs = [], [], []
    for a in LEVELS:
        cands = [(fz_mean(mid, a), mid) for mid, *_ in MODELS if not eligible[mid] and fz_mean(mid, a) is not None]
        champ = min(cands)[1] if cands else None
        champions.append({"alpha": a, "model_id": champ, "reason": None if champ else "no eligible model has an FZ0 score"})
        for mid, *_ in MODELS:
            if mid == champ:
                continue
            for lk in ("fz0", "tick"):
                if lk == "fz0" and results[mid][a]["state"] == "not-forecast":
                    dm_rows.append({"model_id": mid, "versus": champ, "alpha": a, "loss": lk, "mean_diff": None, "dm_statistic": None,
                                    "p_value": None, "hac_lags": 0, "n_common": None, "direction": "not-evaluated",
                                    "not_evaluated_reason": "the model forecasts no ES: FZ0 is not defined"})
                    continue
                idx = list(range(n))
                if lk == "fz0":
                    idx = [i for i in idx if results[mid][a]["es"][i] is not None and results[champ][a]["es"][i] is not None]

                def lossf(m: str, i: int) -> float:
                    res = results[m][a]
                    return mm.fz0_loss(loss[i], res["var"][i], res["es"][i], a) if lk == "fz0" else mm.tick_loss(loss[i], res["var"][i], a)

                diff = [lossf(mid, i) - lossf(champ, i) for i in idx]
                z = mm.dm_statistic(diff, 0)
                pv = mm.two_sided_p(z)
                md = sum(diff) / len(diff)
                direction = "indistinguishable" if pv >= 0.05 else ("better" if md < 0 else "worse")
                dm_rows.append({"model_id": mid, "versus": champ, "alpha": a, "loss": lk, "mean_diff": r(md, 9), "dm_statistic": r(z),
                                "p_value": r(pv), "hac_lags": 0, "n_common": len(idx), "direction": direction,
                                "not_evaluated_reason": None})
        scored = [(fz_mean(mid, a), mid) for mid, *_ in MODELS if fz_mean(mid, a) is not None]
        best = min(scored)[1]
        members = []
        for f, mid in scored:
            if mid == best:
                p = 1.0
            else:
                idx = [i for i in range(n) if results[mid][a]["es"][i] is not None and results[best][a]["es"][i] is not None]
                diff = [mm.fz0_loss(loss[i], results[mid][a]["var"][i], results[mid][a]["es"][i], a)
                        - mm.fz0_loss(loss[i], results[best][a]["var"][i], results[best][a]["es"][i], a) for i in idx]
                p = mm.two_sided_p(mm.dm_statistic(diff, 0))
            members.append({"model_id": mid, "in_set": p >= 0.10, "p_value": r(p)})
        mcs.append({"alpha": a, "loss": "fz0", "statistic": "TR", "confidence": 0.90, "n_bootstrap": 1000, "block_length": 10,
                    "members": members, "n_in_set": sum(1 for m in members if m["in_set"])})

    models_out = []
    for mid, rung, title, lag, k, esm, state, undef in MODELS:
        by_level = []
        for a in LEVELS:
            res = results[mid][a]
            flags = [1 if i in set(res["exc"]) else 0 for i in range(n)]
            counts = mm.rolling_counts(flags, 250)
            zs = [mm.traffic_zone(c) for c in counts]
            fm = fz_mean(mid, a)
            tl = None
            if a == 0.01:
                tl = {"window_days": 250, "n_windows": len(counts), "max_rolling_exceedances": max(counts),
                      "final_rolling_exceedances": counts[-1], "final_zone": mm.traffic_zone(counts[-1]),
                      "days_green": zs.count("green"), "days_amber": zs.count("amber"), "days_red": zs.count("red"), "reason": None}
            by_level.append({
                "alpha": a, "var": res["var"], "es": res["es"], "es_status": state, "es_undefined_days": undef,
                "exceedance_days": res["exc"], "n_scored": n, "n_exceedances": len(res["exc"]),
                "expected_exceedances": r(a * n, 9), "n_fz0": len(res["fz"]),
                "fz0_mean": None if fm is None else r(fm, 9),
                "fz0_reason": None if fm is not None else "the model forecasts no ES: FZ0 is not defined",
                "tick_loss_mean": r(res["tick"], 9), "traffic_light": tl, "test_ids": res["test_ids"]})
        models_out.append({"model_id": mid, "rung": rung, "eligible": not eligible[mid], "failed_gates": eligible[mid],
                           "by_level": by_level})

    outputs = {
        "kind": "window",
        "window": {"window_id": "rates-2022", "asset_class": "rates",
                   "title": txt("Rates 2022: the hiking cycle (fixture)", "Tasas 2022: el ciclo de alzas (ejemplo)"),
                   "start_date": grid[0].isoformat(), "end_date": grid[-1].isoformat(), "n_forecast_days": n},
        "sign_convention": sign_convention(),
        "levels": [{"alpha": a} for a in LEVELS],
        "portfolio": {
            "description": txt("A long position in the 10-year US Treasury par yield, loss = duration times the yield rise (fixture).",
                               "Posicion larga en el rendimiento par a 10 anos del Tesoro de EE. UU.; perdida = duracion por el alza del rendimiento (ejemplo)."),
            "value_unit": "decimal-of-portfolio-value", "currency": "USD", "weighting": "constant-weights-daily-rebalanced",
            "components": [{"series_id": "treasury-par", "label": txt("Treasury par curve, 10 years", "Curva par del Tesoro, 10 anos"),
                            "source_class": "mirror-allowed", "weight": 1.0,
                            "transform": "negative-modified-duration-times-yield-change"}]},
        "data_status": {"first_observation": est_start[0].isoformat(), "last_observation": grid[-1].isoformat(),
                        "n_observed_days": 1000 + n,
                        "missing_days": {"count": len(missing), "dates": [m.isoformat() for m in missing],
                                         "treatment": "skipped-not-filled"}},
        "grid": {"scheme": "rolling", "estimation_window_days": 1000, "dates": [x.isoformat() for x in grid],
                 "estimation_start": [x.isoformat() for x in est_start], "estimation_end": [x.isoformat() for x in est_end],
                 "realised_loss": {"status": "included", "loss": loss, "reason": None}},
        "hyperparameters": {"fixed_on": {"start": "1995-01-01", "end": "2003-12-31"}, "tuned_on_test_window": False,
                            "estimation_window_days": 1000, "ewma_lambda": 0.94, "age_weight_lambda": 0.98,
                            "evt_threshold_fraction": 0.10, "garch_refit_every_days": 1, "caviar_n_starts": 20, "gas_n_starts": 20, "seed": 0,
                            "others": [{"name": "hs_window", "value": 250, "unit": "days"}]},
        "models": models_out,
        "comparison": {"significance": 0.05, "hac_kernel": "bartlett", "hac_lags": 0, "champions": champions, "dm": dm_rows, "mcs": mcs},
        "es_backtests": [zscore[k] for k in sorted(zscore)],
    }
    doc = {
        "schema": "contraste.case/v1", "case_id": "C11", "variant_id": "fixture-rates-2022",
        "model": [model_summary(m[0], m[1], m[2]) for m in MODELS],
        "outputs": outputs, "tests": tests,
        "impact": {"champion_fz0_1pct": {"value": next((fz_mean(c["model_id"], 0.01) for c in champions if c["alpha"] == 0.01 and c["model_id"]), None),
                                         "unit": "fz0-loss", "label": txt("Champion average FZ0 at 1 percent", "FZ0 medio del campeon al 1 por ciento")}},
        "findings": [{"id": "f-fixture-1", "severity": "S2", "status": "open",
                      "evidence": ["market.kupiec_pof", "market.christoffersen_independence"],
                      "title": txt("Fixture: a stale-volatility rung fails the traditional back-tests",
                                   "Ejemplo: un modelo con volatilidad desactualizada falla los back-tests tradicionales")}],
        **envelope_common("real-outcomes"),
    }
    return doc, {"results": results, "eligible": eligible, "champions": champions, "n": n}


def sign_convention() -> dict:
    return {"engine_convention": "return-negative", "document_convention": "positive-loss",
            "definition": txt("The engine stores VaR and ES in the return convention (negative numbers at the tail level alpha); this "
                              "document stores positive loss numbers, as decimals of the portfolio value.",
                              "El motor guarda VaR y ES en la convencion de retornos (numeros negativos al nivel alfa); este "
                              "documento guarda perdidas positivas, como decimales del valor de la cartera.")}


WINDOW_PLAN = [  # decision D2 (dates) and decision D1 (the span)
    ("equity-2007-09", "equity", "2007-07-02", "2009-06-30", "1995-01-01", "2003-12-31"),
    ("equity-2020", "equity", "2020-02-03", "2020-06-30", "1995-01-01", "2003-12-31"),
    ("rates-2022", "rates", "2022-01-03", "2022-12-30", "1995-01-01", "2003-12-31"),
    ("fx-2008", "fx", "2008-07-01", "2009-06-30", "1995-01-01", "2003-12-31"),
    ("mixed-2023", "mixed", "2023-03-01", "2023-05-31", "1995-01-01", "2003-12-31"),
    ("calm-2004-06", "mixed", "2004-01-02", "2006-12-29", "1995-01-01", "2003-12-31"),
]


def build_c11_models() -> dict:
    ladder = [
        ("hs-250", "R1", "Historical simulation, 250 days", "Historical simulation", "historical simulation (textbook; Pritsker 2001)",
         "empirical", 250, 1, True, "empirical tail mean of the window", []),
        ("ewma-094", "R4", "EWMA, lambda 0.94", "EWMA (RiskMetrics)", "RiskMetrics Technical Document 1996, section 5.3.2",
         "normal", 1000, 1, True, "normal ES from the EWMA volatility",
         [{"name": "lambda", "min": 0.94, "median": 0.94, "max": 0.94, "unit": "1"}]),
        ("evt-mf", "R7", "Conditional EVT (McNeil and Frey)", "Conditional EVT", "McNeil and Frey 2000, J. Empirical Finance 7(3-4)",
         "gpd-tail", 1000, 20, True, "GPD tail ES, undefined for xi at or above 1",
         [{"name": "xi", "min": 0.05, "median": 0.18, "max": 1.04, "unit": "1"},
          {"name": "beta", "min": 0.4, "median": 0.62, "max": 0.9, "unit": "1"}]),
        ("caviar-sav", "R8", "CAViaR, symmetric absolute value", "CAViaR SAV", "Engle and Manganelli 2004, JBES 22(4)",
         "none", 1000, 20, False, "none: CAViaR SAV forecasts the VaR only",
         [{"name": "beta_1", "min": -0.001, "median": 0.0002, "max": 0.001, "unit": "1"}]),
    ]
    rungs = []
    for mid, rung, title, short, src, innov, win, refit, es, es_m, params in ladder:
        rungs.append({"model_id": mid, "rung": rung, "title": txt(title, title), "family": "market-var-es", "source": src,
                      "status": "fitted", "not_run_reason": None, "innovation": innov, "estimation_window_days": win,
                      "refit_every_days": refit, "forecasts_es": es, "es_method": es_m,
                      "window_fits": [{"window_id": "rates-2022", "n_refits": 255 if refit == 1 else 13,
                                       "n_convergence_failures": 0, "parameters": params}]})
    rungs.append({"model_id": "nn-fz", "rung": "R10", "title": txt("Quantile network trained on FZ0 (challenger)", "Red de cuantiles entrenada con FZ0 (retador)"),
                  "family": "market-var-es", "source": "arXiv 2606.04576 (preprint; challenger only)", "status": "challenger-not-run",
                  "not_run_reason": "challenger only: it must enter the 90 percent MCS on FZ0 out of sample, and the published run does not train it",
                  "innovation": "none", "estimation_window_days": None, "refit_every_days": None, "forecasts_es": True,
                  "es_method": "network output", "window_fits": []})
    traffic = {"window_days": 250, "confidence": 0.99, "reference": "MAR32.9 Table 1 (dossier 01 D.4); 12 CFR 217.204 Table 1 (dossier 05 B.4)",
               "rows": [{"exceptions": k, "zone": mm.traffic_zone(k), "frtb_multiplier": mm.FRTB_MULTIPLIER[k],
                         "us_multiplier": mm.US_MULTIPLIER[k],
                         "cumulative_probability_pct": r(100 * mm.binom_cdf(k, 250, 0.01), 2)} for k in range(11)]}
    return {
        "schema": "contraste.models/v1", "case_id": "C11", "fit_id": "fixture-ladder",
        "model": [model_record(m[0], m[1], m[2]) for m in MODELS] + [model_record("nn-fz", "R10", "quantile network on FZ0")],
        "fit": {
            "sign_convention": sign_convention(),
            "levels": [{"alpha": a} for a in LEVELS],
            "windows": [{"window_id": w, "asset_class": ac, "start_date": s, "end_date": e, "fixed_on": {"start": fs, "end": fe}}
                        for w, ac, s, e, fs, fe in WINDOW_PLAN],
            "ladder": rungs,
            "traffic_light": traffic,
            "es_reference": {"statistic": "Z2", "n_days": 250, "alpha": 0.025, "yellow": -0.7, "red": -1.8,
                             "status": txt("A published reference point (Acerbi and Szekely), not a regulatory threshold; each model's own simulated critical values are in the outputs.",
                                           "Un punto de referencia publicado (Acerbi y Szekely), no un umbral regulatorio; los valores criticos simulados de cada modelo estan en los resultados.")},
            "scoring": {"fz0_formula": "-(1/(alpha*e))*1{y<=v}*(v-y) + v/e + log(-e) - 1", "tick_formula": "(alpha - 1{y<v})*(y - v)",
                        "hac_kernel": "bartlett", "mcs_confidence": 0.90, "mcs_statistic": "TR",
                        "selection_rule": txt("Traditional back-tests (POF, conditional coverage, Z2) are eligibility gates; the champion is the lowest average FZ0 among the eligible; Diebold-Mariano and the model confidence set rank the ladder.",
                                              "Los back-tests tradicionales (POF, cobertura condicional, Z2) son compuertas de elegibilidad; el campeon es el menor FZ0 medio entre los elegibles; Diebold-Mariano y el conjunto de confianza de modelos ordenan la escalera.")},
            "eligibility_gates": [
                {"test_id": "market.kupiec_pof", "rule": txt("Red at the 5 percent level in any window level: ineligible.", "Rojo al 5 por ciento en cualquier nivel: inelegible.")},
                {"test_id": "market.christoffersen_conditional_coverage", "rule": txt("Red at the 5 percent level: ineligible.", "Rojo al 5 por ciento: inelegible.")},
                {"test_id": "market.acerbi_szekely", "rule": txt("Red against the model's own simulated critical value: ineligible; not evaluated is not red.", "Rojo frente al valor critico simulado propio: inelegible; no evaluado no es rojo.")}],
            "data_sources": [
                {"series_id": "french-daily", "title": txt("Kenneth French data library, daily factor and industry returns", "Biblioteca de datos de Kenneth French, retornos diarios de factores e industrias"),
                 "source_class": "derived-only", "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
                 "licence_note": txt("Copyright Eugene F. Fama and Kenneth R. French; only derived results are committed (dossier 08 C.5).", "Copyright Eugene F. Fama y Kenneth R. French; solo se publican resultados derivados (dossier 08 C.5).")},
                {"series_id": "treasury-par", "title": txt("US Treasury daily par yield curve", "Curva de rendimientos par diaria del Tesoro de EE. UU."),
                 "source_class": "mirror-allowed", "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/",
                 "licence_note": txt("Work of US federal employees (17 U.S.C. 105; page statement UNVERIFIED, dossier 08 C.2).", "Obra de empleados federales de EE. UU. (17 U.S.C. 105; la declaracion de la pagina no esta verificada, dossier 08 C.2).")},
                {"series_id": "h10-fx", "title": txt("Federal Reserve H.10 foreign exchange rates", "Tipos de cambio H.10 de la Reserva Federal"),
                 "source_class": "mirror-allowed", "url": "https://www.federalreserve.gov/releases/h10/",
                 "licence_note": txt("Board publication under the Board's public-domain statement (dossier 08 C.8); start dates UNVERIFIED.", "Publicacion de la Junta bajo su declaracion de dominio publico (dossier 08 C.8); fechas de inicio no verificadas.")}],
        },
        **envelope_common("real-outcomes"),
    }


# ------------------------------------------------------------------------------------------------------- C13


def c13_example(rng: random.Random) -> tuple[list[float], list[float]]:
    hpl, rtpl = [], []
    for _ in range(250):
        f1, f2 = rng.gauss(0, 1), rng.gauss(0, 1)
        basis = rng.gauss(0, 1)
        systematic = 0.006 * f1 + 0.004 * f2
        hpl.append(r(systematic + 0.0060 * basis))
        rtpl.append(r(systematic))
    return hpl, rtpl


def build_c13() -> tuple[dict, dict]:
    seed_base, idx = 13000, 7
    hpl, rtpl = c13_example(random.Random(seed_base + idx))
    rho, ks = mm.spearman(hpl, rtpl), mm.ks_statistic(hpl, rtpl)
    n = 1000
    zones = {"n": n, "overall": {"green": 80, "amber": 540, "red": 380},
             "spearman": {"green": 150, "amber": 640, "red": 210}, "ks": {"green": 250, "amber": 480, "red": 270}}
    det_n = zones["overall"]["amber"] + zones["overall"]["red"]
    share = det_n / n
    se = math.sqrt(share * (1 - share) / n)
    desk = []
    for a, limit, mean, qs, over in ((0.025, 30, 6.1, (2, 6, 11, 19), 3), (0.01, 12, 2.4, (0, 2, 6, 10), 2)):
        desk.append({"alpha": a, "basis": "HPL", "limit_exceptions": limit, "n_days": 250,
                     "exceptions": {"mean": mean, "sd": 3.0, "q05": float(qs[0]), "q50": float(qs[1]), "q95": float(qs[2]), "min": 0.0, "max": float(qs[3])},
                     "n_within_limit": n - over, "n_over_limit": over, "share_over_limit": over / n})
    outputs = {
        "kind": "deficiency",
        "known_deficiency": {
            "deficiency_id": "missing-basis", "planted": True,
            "mechanism": txt("The hypothetical P&L carries a basis between the traded instrument and the risk factor that the risk model leaves out.",
                             "El P&L hipotetico incluye una base entre el instrumento y el factor de riesgo que el modelo de riesgo omite."),
            "parameters": [{"name": "basis_sd_share", "value": 0.65, "unit": "share-of-hpl-sd"}],
            "intended_to_fail": "spearman"},
        "sign_convention": sign_convention(),
        "generator": {"name": "fixture desk generator", "n_risk_factors": 2, "pnl_unit": "decimal-of-desk-notional", "window_days": 250,
                      "n_replications": n, "seed_base": seed_base, "seed_rule": "seed_base+replication_index",
                      "notice": txt("Synthetic desk P&L with a planted deficiency; the truth is known. A fixture, not a result.",
                                    "P&L sintetico de mesa con una deficiencia plantada; la verdad es conocida. Un ejemplo, no un resultado.")},
        "pnl_summary": [
            {"series": "HPL", "mean": 0.00005, "sd": 0.0092, "skewness": 0.02, "excess_kurtosis": 0.1, "min": -0.029, "max": 0.030},
            {"series": "RTPL", "mean": 0.00004, "sd": 0.0072, "skewness": 0.01, "excess_kurtosis": 0.05, "min": -0.022, "max": 0.023}],
        "pla": {"thresholds": pla_thresholds(),
                "spearman": {"mean": 0.75, "sd": 0.045, "q05": 0.67, "q50": 0.75, "q95": 0.82, "min": 0.58, "max": 0.89},
                "ks": {"mean": 0.105, "sd": 0.03, "q05": 0.06, "q50": 0.10, "q95": 0.16, "min": 0.03, "max": 0.24},
                "zones": zones},
        "example": {"replication_index": idx, "seed": seed_base + idx, "hpl": hpl, "rtpl": rtpl,
                    "spearman": r(rho), "ks": r(ks), "zone": mm.pla_zone(rho, ks)},
        "desk_backtest": desk,
        "detection": {"role": "power", "rule": txt("Caught when the joint PLA zone is amber or red.", "Detectado cuando la zona PLA conjunta es ambar o roja."),
                      "n_replications": n, "n_amber_or_red": det_n, "n_red": zones["overall"]["red"],
                      "share_amber_or_red": share, "share_red": zones["overall"]["red"] / n, "mc_se": r(se, 9),
                      "ci_low": r(share - 1.96 * se, 9), "ci_high": r(share + 1.96 * se, 9),
                      "by_test": {"spearman_flagged": zones["spearman"]["amber"] + zones["spearman"]["red"],
                                  "ks_flagged": zones["ks"]["amber"] + zones["ks"]["red"], "desk_backtest_flagged": desk[1]["n_over_limit"]},
                      "intended_test_flagged": zones["spearman"]["amber"] + zones["spearman"]["red"]},
    }
    tests = [
        row("market.pla_test", "desk-risk-model", None, r(rho), None, r(ks), 250, None, outputs["example"]["zone"],
            "the risk-theoretical P&L tracks the hypothetical P&L", "the risk model fails the P&L attribution test",
            "MAR32.36 to MAR32.42; dossier 01 D.4", notes="fixture: one example replication; statistic is Spearman, metric is KS",
            extras={"zone": outputs["example"]["zone"], "thresholds": {"spearman_green": 0.8, "spearman_red": 0.7, "ks_green": 0.09, "ks_red": 0.12}},
            amber=None, red=None),
    ]
    for dk in desk:
        q50 = dk["exceptions"]["q50"]
        tests.append(row("market.desk_backtest", "desk-risk-model", dk["alpha"], q50, None, float(dk["limit_exceptions"]), 250, int(q50),
                         "green" if q50 <= dk["limit_exceptions"] else "red", "the desk stays within the exception limit",
                         "the desk exceeds the exception limit", "MAR32.18 to MAR32.19; dossier 01 D.4",
                         notes="fixture: the median count across replications",
                         extras={"aggregate": "median-across-replications", "n_replications": n}, amber=None, red=None))
    doc = {
        "schema": "contraste.case/v1", "case_id": "C13", "variant_id": "fixture-missing-basis",
        "model": [model_summary("desk-risk-model", "R0", "desk risk model with a planted missing basis")],
        "outputs": outputs, "tests": tests,
        "impact": {"share_caught": {"value": share, "unit": "share", "label": txt("Replications where the PLA is amber or red", "Replicaciones donde el PLA es ambar o rojo")}},
        "findings": [{"id": "f-fixture-1", "severity": "S3", "status": "open", "evidence": ["market.pla_test"],
                      "title": txt("Fixture: the planted missing basis is caught in most replications", "Ejemplo: la base omitida plantada se detecta en la mayoria de las replicaciones")}],
        **envelope_common("synthetic-known-truth"),
    }
    models = {
        "schema": "contraste.models/v1", "case_id": "C13", "fit_id": "fixture-generator",
        "model": [model_record("desk-risk-model", "R0", "desk risk model")],
        "fit": {
            "sign_convention": sign_convention(),
            "generator": {"name": "fixture desk generator",
                          "true_risk_model": txt("Two normal risk factors with loadings 0.006 and 0.004 and an instrument basis; the risk model is exact when nothing is planted.",
                                                 "Dos factores de riesgo normales con cargas 0.006 y 0.004 y una base del instrumento; el modelo de riesgo es exacto cuando no se planta nada."),
                          "parameters": [{"name": "loading_1", "value": 0.006, "unit": "decimal-per-sd"}, {"name": "loading_2", "value": 0.004, "unit": "decimal-per-sd"}],
                          "pnl_unit": "decimal-of-desk-notional", "window_days": 250, "seed_rule": "seed_base+replication_index",
                          "notice": txt("Synthetic: the truth is known. Fixture parameters, not results.", "Sintetico: la verdad es conocida. Parametros de ejemplo, no resultados.")},
            "deficiencies": [
                deficiency("none", False, "No deficiency: the risk model is exact (the size of the test).", "Sin deficiencia: el modelo de riesgo es exacto (el tamano del test).", [], "none"),
                deficiency("missing-basis", True, "The risk model omits the basis between instrument and factor.", "El modelo de riesgo omite la base entre instrumento y factor.", [("basis_sd_share", 0.65, "share-of-hpl-sd")], "spearman"),
                deficiency("stale-volatility", True, "The risk model uses a volatility that lags the true one.", "El modelo de riesgo usa una volatilidad rezagada respecto de la verdadera.", [("vol_lag_days", 20.0, "days")], "ks"),
                deficiency("wrong-correlation", True, "The risk model uses a wrong correlation between the factors.", "El modelo de riesgo usa una correlacion erronea entre los factores.", [("correlation_error", 0.3, "correlation-points")], "either"),
                deficiency("omitted-factor", True, "The risk model leaves out a risk factor the desk is exposed to.", "El modelo de riesgo omite un factor de riesgo al que la mesa esta expuesta.", [("omitted_loading_share", 0.3, "share-of-hpl-sd")], "spearman"),
                deficiency("time-misalignment", True, "The risk-theoretical P&L is dated one day off the hypothetical P&L.", "El P&L teorico por riesgo esta fechado un dia desfasado del P&L hipotetico.", [("lag_days", 1.0, "days")], "spearman")],
            "pla_thresholds": pla_thresholds(),
            "desk_limits": [{"alpha": 0.025, "limit_exceptions": 30, "reference": "MAR32.18 to MAR32.19"},
                            {"alpha": 0.01, "limit_exceptions": 12, "reference": "MAR32.18 to MAR32.19"}],
            "replication_plan": {"n_replications": n, "seed_base": seed_base, "seed_rule": "seed_base+replication_index"}},
        **envelope_common("synthetic-known-truth"),
    }
    return doc, models


def deficiency(did: str, planted: bool, en: str, es: str, params: list, fails: str) -> dict:
    return {"deficiency_id": did, "planted": planted, "mechanism": txt(en, es),
            "parameters": [{"name": n_, "value": v, "unit": u} for n_, v, u in params], "intended_to_fail": fails}


def pla_thresholds() -> dict:
    return {"spearman_green": 0.8, "spearman_red": 0.7, "ks_green": 0.09, "ks_red": 0.12, "ecdf_step": 0.004, "window_days": 250,
            "reference": "MAR32.42"}


def write(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    c11, info = build_c11_variant()
    write(FIX / "c11" / "variant-window-fixture.json", c11)
    write(FIX / "c11" / "models-fixture.json", build_c11_models())
    c13, c13m = build_c13()
    write(FIX / "c13" / "variant-deficiency-fixture.json", c13)
    write(FIX / "c13" / "models-fixture.json", c13m)
    print("n =", info["n"], "eligible failed:", info["eligible"], "champions:", info["champions"])
    for m in c11["outputs"]["models"]:
        for lv in m["by_level"]:
            print(m["model_id"], lv["alpha"], "exc", lv["n_exceedances"], "fz0", lv["fz0_mean"], "tl", (lv["traffic_light"] or {}).get("final_zone"))
    print("c13 example", c13["outputs"]["example"]["spearman"], c13["outputs"]["example"]["ks"], c13["outputs"]["example"]["zone"])
