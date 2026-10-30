"""Builds the three U12-S fixture documents (docs/contracts/fixtures/c17).

Run: ``python tests/contracts_u12/build_fixtures.py``. Deterministic, standard library only. The numbers are round, small and
internally consistent (the identities the contract promises: ratios to the true quantile, the OPE25 BI, BIC and ILM formulas,
LC = 15 x the average annual loss, the exceedance curves) but they are fixtures, never results: every document is labelled
``fixture`` in its provenance and its ids, and no value comes from running the generator or the engine.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "docs" / "contracts" / "fixtures" / "c17"
Z = {"p05": -1.6449, "p25": -0.6745, "median": 0.0, "p75": 0.6745, "p95": 1.6449}
KEYS = tuple(Z)
LDCE = [(0.25, 27632), (0.5, 41916), (0.75, 82608), (0.95, 418400)]


def txt(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def sig(x: float, n: int = 6) -> float:
    return float(f"{x:.{n}g}")


def envelope_common() -> dict:
    return {
        "provenance": {
            "truth_status": "synthetic-known-truth",
            "inputs": [{"source": "fixture-not-a-result", "class": "fixture", "files": []}],
            "licence_classes": {"fixture-not-a-result": "fixture"},
            "generators": ["fixture:u12-s-contracts"],
            "seed": 0,
            "code_version": "fixture",
            "riskvalidation_version": None,
        },
        "lane": {"lane": "precompute", "reasons": ["fixture"]},
    }


NE = "fixture: the test did not run, no number stands in for it"


def test_row(test_id: str, model_id: str, reason: str) -> dict:
    return {
        "test_id": test_id, "model_id": model_id, "segment": None, "statistic": None, "p_value": None,
        "metric": None, "h0": "fixture row", "alternative": "fixture row", "policy_version": "fixture",
        "alpha_amber": None, "alpha_red": None, "light": "not_evaluated", "n": None, "n_events": None,
        "inputs_hash": "0" * 64, "reference": "fixture, not a result", "notes": reason, "extras": {},
    }


def model_summary(mid: str, rung: str) -> dict:
    return {
        "id": mid, "family": "oprisk", "rung": rung,
        "title": txt(f"Fixture model {mid}", f"Modelo de ejemplo {mid}"),
        "short_title": txt(mid, mid), "engine": "riskvalidation", "engine_version": "fixture",
        "licence": "MIT", "calibration": None, "parameters": {}, "checkpoint_sha256": None,
    }


def model_record(mid: str, rung: str) -> dict:
    d = model_summary(mid, rung)
    d["details"] = {}
    return d


# ------------------------------------------------------------------------------------------------ the generator's truth

ASSETS_BN = 50.0
BI = {"ildc_eur": 0.8e9, "sc_eur": 0.5e9, "fc_eur": 0.1e9}
BI["bi_eur"] = BI["ildc_eur"] + BI["sc_eur"] + BI["fc_eur"]


def bic(bi: float) -> float:
    return 0.12 * min(bi, 1e9) + 0.15 * max(min(bi, 30e9) - 1e9, 0) + 0.18 * max(bi - 30e9, 0)


def ilm(lc: float, b: float) -> float:
    return math.log(math.e - 1 + (lc / b) ** 0.8)


BIC = bic(BI["bi_eur"])  # EUR 0.18bn (bucket 2)

VARIANTS = [  # tail index, generator scale (EUR, at the floor), fixture true 99.9 percent quantile (EUR)
    (0.6, 12500.0, 6.0e7), (0.8, 19600.0, 1.76e8), (0.96, 24000.0, 5.9e8), (1.1, 7300.0, 1.65e9)]
FLOOR = 10000.0


def lam_for(xi: float, beta: float) -> float:
    """The frequency at the floor that gives the LDCE 0.82 x 50 = 41 losses a year above EUR 20,000."""
    return round(41.0 / (1 + xi * (20000.0 - FLOOR) / beta) ** (-1 / xi), 1)


def calib_quantiles(xi: float, beta: float) -> list[float]:
    """Severity quantiles at the LDCE percentiles of the loss distribution conditional on EUR 20,000 or more."""
    b2 = beta + xi * (20000.0 - FLOOR)
    return [round(20000.0 + b2 / xi * ((1 - p) ** (-xi) - 1)) for p, _ in LDCE]


def ldce() -> dict:
    return {
        "currency": "EUR", "label": "derived-only", "licence_class": "derived-only",
        "source": {"id": "bcbs160", "title": "Results from the 2008 Loss Data Collection Exercise for Operational Risk",
                   "url": "https://www.bis.org/publ/bcbs160.htm", "date": "2009-07-28", "table": "ILD7"},
        "threshold_eur": 20000,
        "frequency": {"per_eur_bn_assets": 0.82, "iqr_low": 0.36, "iqr_high": 1.66,
                      "statistic": "median across banks of the losses of EUR 20,000 or more per year per EUR billion of consolidated assets"},
        "severity_percentiles": [{"p": p, "loss_eur": v} for p, v in LDCE],
        "caveat": txt("Medians of per-bank percentiles are not the percentiles of any one bank; the statistics calibrate a synthetic "
                      "bank and describe no real one.",
                      "Las medianas de percentiles por banco no son los percentiles de ningun banco; las estadisticas calibran un banco "
                      "sintetico y no describen a uno real."),
    }


def truth_block(xi: float, beta: float, q999: float) -> dict:
    lam = lam_for(xi, beta)
    mean = None if xi >= 1 else round(lam * (FLOOR + beta / (1 - xi)))
    return {
        "label": "synthetic-known-truth", "currency": "EUR",
        "frequency": {"law": "poisson", "lambda_per_year": lam, "counted_above_eur": FLOOR},
        "severity": {"law": "gpd", "location_eur": FLOOR, "scale_eur": beta, "tail_index": xi},
        "annual_loss_quantile": {
            "level": 0.999, "value_eur": q999, "method": "panjer", "grid_step_eur": 1000.0,
            "mc_check": {"n_years": 10000000, "seed": 7, "value_eur": q999 * 0.997, "standard_error_eur": q999 * 0.004, "agrees": True}},
        "annual_loss_mean": {"value_eur": mean, "reason": None if mean is not None else
                             "the tail index is 1 or more: the severity has an infinite mean, so the annual loss has no mean"},
        "notice": txt("Fixture, not a result. The truth is the annual loss of every loss the generator draws at or above its floor, "
                      "whatever the collection threshold.",
                      "Ejemplo, no es un resultado. La verdad es la perdida anual de toda perdida que el generador simula sobre su piso, "
                      "cualquiera sea el umbral de recoleccion."),
    }


def calibration_block(xi: float, beta: float) -> dict:
    fq = calib_quantiles(xi, beta)
    worst = max(abs(math.log(a / b)) for a, (_, b) in zip(fq, LDCE))
    return {"targets": ldce(),
            "fit": {"tail_index": xi, "scale_eur": beta, "fitted_quantiles_eur": fq, "max_abs_log_error": round(worst, 6),
                    "method": "least squares on the log quantiles, scale only (fixture values)"}}


def bank_block() -> dict:
    return {"currency": "EUR", "synthetic": True,
            "label": txt("Synthetic bank of EUR 50 billion in assets", "Banco sintetico de EUR 50 mil millones en activos"),
            "assets_eur": ASSETS_BN * 1e9, "business_indicator": BI, "bic_eur": BIC, "bucket": 2,
            "notice": txt("Fixture, not a result. The business indicator is stated, synthetic and describes no real bank.",
                          "Ejemplo, no es un resultado. El indicador de negocio es declarado, sintetico y no describe a un banco real.")}


# ---------------------------------------------------------------------------------------------------------- the cells

GRID = [(5, 10000), (5, 20000), (10, 10000), (10, 20000)]
RUNG_MEDIAN = {"lda_lognormal": 0.55, "lda_lognormal_truncated": 0.80, "lda_splice": 0.97, "sla": 0.90, "sla_mean_corrected": 0.99,
               "scenario": 1.02, "sla_mean_adjusted": 0.88, "sla_cvm": 0.84, "sla_obre": 0.86, "sla_cvm_lognormal": 0.55}
S3 = ("sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal")
AGGREGATION = {"lda_lognormal": "monte-carlo", "lda_lognormal_truncated": "panjer", "lda_splice": "fft", "sla": "closed-form",
               "sla_mean_corrected": "closed-form", "scenario": "panjer", **{r: "closed-form" for r in S3}}


def capital_summary(rung: str, xi: float, years: int, thr: int, q999: float, n_rep: int, n_fail: int) -> dict:
    med = RUNG_MEDIAN[rung]
    if rung == "lda_lognormal" and thr == 20000:
        med *= 0.85  # ignoring a higher collection threshold biases further
    sd = (0.55 if years == 5 else 0.35) * (1 + max(xi - 0.6, 0)) * (1.1 if thr == 20000 else 1.0)
    ratios = {k: sig(med * math.exp(Z[k] * sd), 8) for k in KEYS}
    caps = {k: round(ratios[k] * q999) for k in KEYS}
    share = round(phi(-math.log(med) / sd), 4)
    n_defined = n_rep - n_fail - (130 if rung == "sla_mean_corrected" else 0)
    return {
        "aggregation": AGGREGATION[rung],
        "status": "UNVERIFIED" if rung == "sla_mean_corrected" else "SECONDARY_SOURCE" if rung in S3 else "verified",
        "n_defined": n_defined,
        "capital_eur": caps,
        "ratio_to_truth": {k: caps[k] / q999 for k in KEYS},
        "share_underestimating": share,
        "iqr_over_truth": (caps["p75"] - caps["p25"]) / q999,
        "log_sd": round(sd, 4),
    }


def sma_cell(xi: float, years: int, thr: int, q999: float) -> dict:
    # LC = 15 x the average annual recorded loss; the percentile spread is wider on 5 years and with the tail index
    lam_rec = 41.0 if thr == 20000 else lam_for(xi, VARIANT_SCALE[xi])
    mean_x = (20000.0 if thr == 20000 else FLOOR) + (VARIANT_SCALE[xi] + (xi * 10000.0 if thr == 20000 else 0.0)) / (1 - min(xi, 0.9))
    lc_mid = 15 * lam_rec * mean_x * (0.8 if xi < 1 else 0.5)
    sd = (0.60 if years == 5 else 0.40) * (1 + max(xi - 0.6, 0))
    lc = {k: round(lc_mid * math.exp(Z[k] * sd)) for k in KEYS}
    ilms = {k: sig(ilm(lc[k], BIC), 10) for k in KEYS}
    orc = {k: round(BIC * ilms[k]) for k in KEYS}
    return {"currency": "EUR", "bucket": 2, "bic_eur": BIC, "basis": "bic-times-ilm", "discretion_applied": "none",
            "lc_eur": lc, "ilm": ilms, "orc_eur": orc, "orc_over_true_quantile": {k: orc[k] / q999 for k in KEYS},
            "note": txt("The SMA is not calibrated to the 99.9 percent quantile of any bank; the ratio is a comparison, not a claim of equivalence.",
                        "El SMA no esta calibrado al cuantil 99,9 por ciento de ningun banco; la razon es una comparacion, no una equivalencia.")}


VARIANT_SCALE = {xi: beta for xi, beta, _ in VARIANTS}


def stability_rows(xi: float, years: int, thr: int, n_rep: int) -> list[dict]:
    lam_rec = 41.0 if thr == 20000 else lam_for(xi, VARIANT_SCALE[xi])
    beta2 = VARIANT_SCALE[xi] + (xi * 10000.0 if thr == 20000 else 0.0)
    rows = []
    for mult in (1, 2, 4, 8):
        u = thr * mult
        n_exc = lam_rec * years * (1 + xi * (u - thr) / beta2) ** (-1 / xi)
        se = (1 + xi) / math.sqrt(n_exc)
        med = xi + 0.04 / mult
        rows.append({"threshold_eur": float(u), "n_exceedances_median": round(n_exc, 1), "n_fits": n_rep - 12,
                     "tail_index": {"p05": round(med - 1.6449 * se, 4), "median": round(med, 4), "p95": round(med + 1.6449 * se, 4)},
                     "share_at_least_one": round(1 - phi((1 - med) / se), 4)})
    return rows


def cell_block(xi: float, vidx: int, k: int, years: int, thr: int, q999: float, with_scenario: bool) -> dict:
    n_rep, n_fail = 1000, 8 + 4 * k
    cap = {r: capital_summary(r, xi, years, thr, q999, n_rep, n_fail)
           for r in ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla")}
    if xi >= 1:
        cap["sla_mean_corrected"] = {"summary": None, "reason": "the tail index is 1 or more: the severity has an infinite mean and the "
                                                                 "mean correction lambda x E[X] does not exist"}
    else:
        cap["sla_mean_corrected"] = {"summary": capital_summary("sla_mean_corrected", xi, years, thr, q999, n_rep, n_fail), "reason": None}
    for r in S3:  # fixture: every fit defined on the finite-mean variants, the mean-adjusted form undefined for most fits at an infinite mean
        cap[r] = {"summary": capital_summary(r, xi, years, thr, q999, n_rep, n_fail), "reason": None}
    if with_scenario:
        cap["scenario"] = {"summary": capital_summary("scenario", xi, years, thr, q999, n_rep, n_fail), "reason": None}
    else:
        cap["scenario"] = {"summary": None, "reason": "fixture: the scenario combination is evaluated on the 10-year cells only"}
    return {
        "id": f"y{years}-h{thr}", "years": years, "collection_threshold_eur": thr, "currency": "EUR",
        "replications": {"seed_first": 1000 + (4 * vidx + k) * 1000, "n_replications": n_rep, "n_failed": n_fail,
                         "n_losses_median": round((41.0 if thr == 20000 else lam_for(xi, VARIANT_SCALE[xi])) * years)},
        "capital": cap,
        "aggregation_agreement": {"max_rel_diff_panjer_fft": 2.1e-6, "n_compared": n_rep - n_fail},
        "threshold_stability": stability_rows(xi, years, thr, n_rep),
        "sma": sma_cell(xi, years, thr, q999),
    }


# --------------------------------------------------------------------------------------------------- the other blocks


def exceedance_block(xi: float, beta: float, q999: float) -> dict:
    lam = lam_for(xi, beta)
    grid = [float(10 ** (4 + i / 2)) for i in range(0, 13)]
    grid = [float(f"{g:.6g}") for g in grid]

    def curve(scale: float) -> list[float]:
        out, prev = [], 1.0
        for x in grid:
            s = (1 + xi * max(x - FLOOR, 0) / beta) ** (-1 / xi)
            v = min(prev, round(min(1.0, (1 - math.exp(-lam * s)) * scale), 7))
            out.append(v)
            prev = v
        return out

    sla = FLOOR + beta / xi * ((lam / 0.001) ** xi - 1)
    return {"currency": "EUR", "grid_eur": grid,
            "monte_carlo": {"n_years": 10000000, "seed": 7, "exceedance": curve(1.003)},
            "panjer": {"step_eur": 1000.0, "exceedance": curve(1.0)},
            "fft": {"n_points": 1048576, "padding_factor": 2, "tilt": 0.0, "exceedance": curve(1.0)},
            "quantile_999_eur": {"monte_carlo": q999 * 0.997, "panjer": q999, "fft": q999 * 1.0001, "sla": round(sla)}}


def sma_response_block(cell_lc_mid: float, lda_base: float) -> dict:
    rows = []
    for added in (0.0, 1e7, 5e7, 2e8, 1e9):
        lc = cell_lc_mid + 1.5 * added  # one added loss in a 10-year window: LC = 15 x (sum + L) / 10
        i = sig(ilm(lc, BIC), 10)
        rows.append({"added_loss_eur": added, "lc_eur": lc, "ilm": i, "orc_eur": round(BIC * i),
                     "lda_capital_eur": round(lda_base + 0.05 * added)})
    return {"currency": "EUR", "cell_id": "y10-h20000", "seed": 1000, "bic_eur": BIC, "rows": rows}


def scenario_block(base: float) -> dict:
    spec = [("S1", "Cyber outage of the core platform", "Caida informatica de la plataforma central", "percentile", 8.0e7, 0.1, 0.12),
            ("S2", "Large external fraud", "Fraude externo grande", "individual", 2.5e7, 0.5, 0.05),
            ("S3", "Mis-selling litigation", "Litigio por venta indebida", "percentile", 1.5e8, 0.05, 0.0),
            ("S4", "Settlement error", "Error de liquidacion", "individual", 1.0e7, 1.0, -0.03)]
    scen = []
    for sid, en, es, kind, loss, freq, infl in spec:
        without = round(base * (1 - infl))
        scen.append({"scenario_id": sid, "label": txt(en, es), "kind": kind, "loss_eur": loss,
                     "exceedance_frequency_per_year": freq, "capital_without_eur": without,
                     "influence": round((base - without) / base, 9)})
    return {"prior_kind": "unrestricted-gamma-on-pareto-shape", "currency": "EUR", "cell_id": "y10-h20000", "seed": 1000, "level": 0.999,
            "method": "bayesian-credibility",
            "base_capital_eur": base, "scenarios": scen, "reference": "Shevchenko and Wuthrich (2006), J. Operational Risk 1(3):3-26"}


def variant_doc(vidx: int) -> dict:
    xi, beta, q999 = VARIANTS[vidx]
    cells = [cell_block(xi, vidx, k, y, t, q999, y == 10) for k, (y, t) in enumerate(GRID)]
    lc_mid = cells[3]["sma"]["lc_eur"]["median"]
    base = cells[3]["capital"]["scenario"]["summary"]["capital_eur"]["median"]
    out = {
        "kind": "tail-index", "currency": "EUR", "tail_index": xi, "infinite_mean": xi >= 1,
        "truth": truth_block(xi, beta, q999), "calibration": calibration_block(xi, beta), "bank": bank_block(),
        "cells": cells, "exceedance": exceedance_block(xi, beta, q999),
        "sma_response": sma_response_block(float(lc_mid), float(cells[3]["capital"]["lda_splice"]["capital_eur"]["median"])), "scenario_influence": scenario_block(float(base)),
    }
    tests = [test_row("oprisk.benchmark_reproduction", "lda-splice", NE),
             test_row("oprisk.threshold_stability", "lda-splice", NE),
             test_row("oprisk.capital_stability", "lda-splice", NE),
             test_row("oprisk.sma_ilm_response", "sma", NE),
             test_row("oprisk.scenario_influence", "scenario", NE)]
    return {
        "schema": "contraste.case/v1", "case_id": "C17", "variant_id": f"fixture-xi-{str(xi).replace('.', '-')}",
        "model": [model_summary("lda-splice", "lda-splice"), model_summary("sma", "sma")],
        "outputs": out, "tests": tests,
        "impact": {"lda_capital_999": {"value": float(cells[3]["capital"]["lda_splice"]["capital_eur"]["median"]), "unit": "EUR",
                                       "label": txt("LDA 99.9 percent capital (median over histories)", "Capital LDA al 99,9 por ciento (mediana)")},
                   "sma_orc": {"value": float(cells[3]["sma"]["orc_eur"]["median"]), "unit": "EUR",
                               "label": txt("SMA operational risk capital (median)", "Capital por riesgo operacional SMA (mediana)")}},
        "findings": [],
        **envelope_common(),
    }


def models_doc() -> dict:
    variants = []
    for xi, beta, q999 in VARIANTS:
        t = truth_block(xi, beta, q999)
        variants.append({"variant_id": f"fixture-xi-{str(xi).replace('.', '-')}", "tail_index": xi, "infinite_mean": xi >= 1,
                         "lambda_per_year": t["frequency"]["lambda_per_year"], "location_eur": FLOOR, "scale_eur": beta,
                         "true_quantile_999_eur": q999, "true_mean_eur": t["annual_loss_mean"]["value_eur"],
                         "true_mean_reason": t["annual_loss_mean"]["reason"]})
    ladder = [
        ("lda-lognormal", "Poisson-lognormal LDA ignoring the collection threshold", "El LDA Poisson-lognormal que ignora el umbral",
         "lognormal", False, "monte-carlo", "verified", "dossier 05 F.2, rung 1"),
        ("lda-lognormal-truncated", "Truncated lognormal above the threshold, frequency rescaled", "Lognormal truncada sobre el umbral",
         "lognormal-truncated", True, "panjer", "verified", "dossier 05 F.2, rung 2; Mignola and Ugoccioni (2007)"),
        ("lda-splice", "Lognormal body and GPD tail splice", "Empalme de cuerpo lognormal y cola GPD", "lognormal-gpd-splice", True,
         "fft", "verified", "dossier 05 F.2, rung 3"),
        ("sla", "Single loss approximation", "Aproximacion de una perdida", "gpd", True, "closed-form", "verified",
         "dossier 05 F.4, Shevchenko eq. 70"),
        ("sla-mean-corrected", "Single loss approximation with the mean correction", "Aproximacion de una perdida con correccion por media",
         "gpd", True, "closed-form", "UNVERIFIED", "dossier 05 F.4: the form is not checked against Bocker and Sprittulla (2006) or Degen (2010)"),
        ("scenario", "Scenario combination by Bayesian credibility", "Combinacion de escenarios por credibilidad bayesiana", "gpd", True,
         "panjer", "verified", "dossier 05 F.5, Shevchenko and Wuthrich (2006)"),
        ("sla-mean-adjusted", "Mean-adjusted single loss approximation, GPD by maximum likelihood",
         "Aproximacion de una perdida con ajuste por media, GPD por maxima verosimilitud", "gpd", True, "closed-form", "SECONDARY_SOURCE",
         "riskvalidation.oprisk.robust.sla_var_mean_adjusted"),
        ("sla-cvm", "Robust GPD by minimum Cramer-von Mises distance, mean-adjusted single loss approximation",
         "GPD robusta por distancia minima de Cramer-von Mises, aproximacion de una perdida con ajuste por media", "gpd", True, "closed-form",
         "SECONDARY_SOURCE", "Opdyke and Cavallo (2012)"),
        ("sla-obre", "Optimally bias-robust GPD at 95 percent efficiency, mean-adjusted single loss approximation",
         "GPD optimamente robusta al sesgo con eficiencia de 95 por ciento, aproximacion de una perdida con ajuste por media", "gpd", True,
         "closed-form", "SECONDARY_SOURCE", "Hampel et al. (1986) section 4.2"),
        ("sla-cvm-lognormal", "Robust lognormal by minimum Cramer-von Mises distance, mean-adjusted single loss approximation (control)",
         "Lognormal robusta por distancia minima de Cramer-von Mises, aproximacion de una perdida con ajuste por media (control)",
         "lognormal-truncated", True, "closed-form", "SECONDARY_SOURCE", "the control"),
    ]
    fit = {
        "currency": "EUR",
        "generator": {"name": "operational-loss-history-generator", "shaped_on": "bcbs160-ldce-2008", "assets_eur_bn": ASSETS_BN,
                      "frequency_law": "poisson", "severity_law": "gpd", "generator_floor_eur": FLOOR,
                      "notice": txt("Fixture, not a result. A synthetic bank whose annual loss distribution is known by construction.",
                                    "Ejemplo, no es un resultado. Un banco sintetico cuya distribucion de perdida anual se conoce por construccion.")},
        "calibration": ldce(), "variants": variants,
        "grid": {"years": [5, 10], "collection_thresholds_eur": [10000, 20000], "n_replications_per_cell": 1000, "seed_base": 1000,
                 "seed_stride": 1000},
        "ladder": [{"rung_id": r, "label": txt(en, es), "severity_law": sev, "truncated": tr, "aggregation": agg, "status": st,
                    "reference": ref} for r, en, es, sev, tr, agg, st, ref in ladder],
        "aggregation": {"level": 0.999, "panjer_step_eur": 1000.0, "panjer_points": 400000, "fft_points": 1048576, "fft_padding_factor": 2,
                        "fft_tilt": 0.0, "mc_years_truth": 10000000, "mc_years_replication": 1000000},
        "sma": {"currency": "EUR",
                "buckets": [{"bucket": 1, "upper_eur": 1e9, "coefficient": 0.12}, {"bucket": 2, "upper_eur": 30e9, "coefficient": 0.15},
                            {"bucket": 3, "upper_eur": None, "coefficient": 0.18}],
                "loss_multiple": 15, "loss_window_years": 10, "minimum_years": 5, "ilm_exponent": 0.8, "rwa_factor": 12.5,
                "discretions": [
                    {"id": "bucket-1-ilm-one", "description": txt("Bucket 1 banks have ILM = 1 unless national discretion includes their losses.",
                                                                  "Los bancos del tramo 1 tienen ILM = 1 salvo que la discrecion nacional incluya sus perdidas."),
                     "reference": "OPE25.11"},
                    {"id": "national-ilm-one", "description": txt("Supervisors may set ILM = 1 for every bank of the jurisdiction; disclosure stays.",
                                                                  "Los supervisores pueden fijar ILM = 1 para todos los bancos de la jurisdiccion; la divulgacion se mantiene."),
                     "reference": "OPE25.11"},
                    {"id": "transitional-bic-only", "description": txt("Under 5 years of loss data (10 are required, 5 are the transitional minimum) capital is the BIC only.",
                                                                       "Con menos de 5 anos de datos de perdida (se piden 10, 5 es el minimo transitorio) el capital es solo el BIC."),
                     "reference": "OPE25.10, OPE25.15"}],
                "golden": {"bi_eur": 35e9, "bic_eur": 5.37e9, "reference": "OPE25.7 footnote 2"},
                "reference": "dossier 01 section F (OPE25, in force 2023-01-01, published 2024-07-05)"},
        "scenarios": {"methods": ["pseudo-observations", "body-tail", "bayesian-credibility"],
                      "prior": {"kind": "unrestricted-gamma-on-pareto-shape", "restricted": False, "interval_level": 0.9,
                                "mapping": "GPD fitted to the scenario points by least squares on the log excess quantiles; alpha_s = 1 / xi_s is the "
                                           "prior mean and the parametric-bootstrap 90 percent interval of alpha_s the expert interval; the Gamma "
                                           "shape and rate solve the mean and the interval mass (decision D4)"},
                      "reference": "dossier 05 F.5; Shevchenko and Wuthrich (2006), J. Operational Risk 1(3):3-26"},
    }
    return {
        "schema": "contraste.models/v1", "case_id": "C17", "fit_id": "fixture-generator",
        "model": [model_record("lda-splice", "lda-splice"), model_record("sma", "sma")],
        "fit": fit, **envelope_common(),
    }


def dump(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    dump(FIX / "variant-tail-index-fixture.json", variant_doc(1))
    dump(FIX / "variant-tail-index-infinite-mean-fixture.json", variant_doc(3))
    dump(FIX / "models-fixture.json", models_doc())


if __name__ == "__main__":
    main()
