"""The c17-outputs (one per tail index) and c17-models documents of C17 from the replications and the engine's validation tests.

The percentiles of a rung's capital across the replications, the ratio to the true quantile, the share underestimating and the
dispersion come from ``validation.oprisk.capital_stability``; the SMA columns are percentiles of the engine's per-replication loss
component, ILM and ORC. The product orders, names and writes the bilingual text; it computes no capital (CT-1709).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import math

import numpy as np
from riskvalidation.validation import oprisk as val

from ...core import text as tx

from . import params as P
from .generator import Variant
from .truth import Truth

KEYS = ("p05", "p25", "median", "p75", "p95")
PCT = (5, 25, 50, 75, 95)


def T(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def es_num(x: float, spec: str) -> str:
    """A number in a Spanish sentence: the decimal comma (the gate's G11 and the Spanish UI write 0,96, not 0.96), and a percent with
    the no-break space before its sign (86,9\u00a0%, the shell's es-CL form; U16-F9c)."""
    out = format(x, spec).replace(".", ",")
    return out[:-1] + "\u00a0%" if out.endswith("%") else out


def sig2(x: float, lang: str) -> str:
    """A ratio with two significant digits and at least two decimals, in the language's form: 0.0044 (not "0.00 times the truth",
    U16-R3 c18 m6), 0.042, 0.26, 1.50."""
    decimals = 2 if x == 0 else max(2, 1 - math.floor(math.log10(abs(x))))
    return tx.number(x, decimals, lang=lang)


#: the generator's notice: the English acronym of the Loss Data Collection Exercise is glossed once in Spanish (U16-R3 c18 m8)
GENERATOR_NOTICE = T("Synthetic data: a bank invented for the case whose annual loss distribution is known by construction; the LDCE medians "
                     "shape it and it describes no real bank.",
                     "Datos sintéticos: un banco inventado para el caso cuya distribución de pérdida anual se conoce por construcción; "
                     "las medianas del Ejercicio de Recolección de Datos de Pérdidas (LDCE, por su sigla en inglés) lo moldean y no "
                     "describe a ningún banco real.")


def rv_version() -> str:
    from importlib.metadata import version

    return version("riskvalidation")


def cell_id(years: int, threshold: float) -> str:
    return f"y{years}-h{int(threshold)}"


@dataclass
class CellResult:
    """The replications of one cell as arrays, one entry per replication."""
    years: int
    threshold: float
    seed_first: int
    arrays: dict[str, np.ndarray]
    errors: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return cell_id(self.years, self.threshold)

    @property
    def n(self) -> int:
        return int(self.arrays["failed"].size)


def _q(x: np.ndarray, method: str = "linear") -> dict[str, float]:
    return {k: float(v) for k, v in zip(KEYS, np.percentile(x, PCT, method=method))}


#: the rungs of S-3 of the method tiers plan: the key of the replication arrays and the model id of the capital_stability row
S3_RUNGS: tuple[tuple[str, str], ...] = (("sla_mean_adjusted", "sla-mean-adjusted"), ("sla_cvm", "sla-cvm"), ("sla_obre", "sla-obre"),
                                         ("sla_cvm_lognormal", "sla-cvm-lognormal"))
S3_NAME = {"sla-cvm": T("Cramer-von Mises GPD", "GPD de Cramér-von Mises"), "sla-obre": T("optimally bias-robust GPD", "GPD óptimamente robusta al sesgo")}


def s3_counts(capitals: list[dict[str, Any]], rung_key: str) -> tuple[int, int, int]:
    """``(cells, smaller spread, smaller bias)`` of a robust rung against the splice LDA over the cells where both have a capital: spread is the
    interquartile range of capital over the truth, bias the absolute log of the median ratio to the truth (``params.S3_HYPOTHESIS``)."""
    n = spread = bias = 0
    for cap in capitals:
        r, sp = cap[rung_key], cap["lda_splice"]
        if r is None or sp is None:
            continue
        n += 1
        spread += r["iqr_over_truth"] < sp["iqr_over_truth"]
        bias += abs(math.log(r["ratio_to_truth"]["median"])) < abs(math.log(sp["ratio_to_truth"]["median"]))
    return n, spread, bias


def s3_verdict(n: int, spread: int, bias: int) -> str:
    """``holds``, ``refuted`` or ``inconclusive`` by the shares of ``params.S3_HYPOTHESIS`` (no cell with both rungs: inconclusive)."""
    if n == 0:
        return "inconclusive"
    h = P.S3_HYPOTHESIS
    if min(spread, bias) / n < h["refuted_below_share"]:
        return "refuted"
    return "holds" if min(spread, bias) / n >= h["holds_at_share"] else "inconclusive"


def _row(res: Any, segment: str | None = None) -> dict[str, Any]:
    d = res.to_dict()
    if segment is not None:
        d["segment"] = segment
    return d


def capital_summary(caps: np.ndarray, truth: float, model_id: str, segment: str, aggregation: str, status: str = "verified",
                    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The summary of the defined capitals of a rung against the truth and the engine's capital_stability row; ``None, None`` when
    fewer than four histories gave a capital (the engine's own floor)."""
    c = caps[np.isfinite(caps)]
    if c.size < 4:
        return None, None
    res = val.capital_stability(c, truth, model_id=model_id)
    ex = res.extras
    summary = {
        "aggregation": aggregation, "status": status, "n_defined": int(c.size), "capital_eur": _q(c),
        "ratio_to_truth": {k: float(ex[f"ratio_{k}"]) for k in KEYS}, "share_underestimating": float(ex["share_underestimating"]),
        "iqr_over_truth": float(res.metric), "log_sd": float(np.std(np.log(c), ddof=1)),
    }
    return summary, _row(res, segment)


def _sma_block(cell: CellResult, bank: dict[str, Any], truth: float) -> dict[str, Any]:
    a = cell.arrays
    lc, ilm, orc = (_q(a[k], "inverted_cdf") for k in ("lc", "ilm", "orc"))  # a monotone transform of a percentile is the percentile
    return {
        "currency": P.CURRENCY, "bucket": bank["bucket"], "bic_eur": bank["bic_eur"], "basis": "bic-times-ilm", "discretion_applied": "none",
        "lc_eur": lc, "ilm": ilm, "orc_eur": orc, "orc_over_true_quantile": {k: v / truth for k, v in orc.items()},
        "note": T("The SMA is not calibrated to the 99.9 percent quantile of any bank; the ratio is a comparison, not a claim of equivalence.",
                  "El SMA no está calibrado al cuantil 99,9 por ciento de ningún banco; la razón es una comparación, no una equivalencia."),
    }


def _stability(cell: CellResult, truth_row_model: str = "lda-splice") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    a = cell.arrays
    thr = cell.threshold * np.array(P.STABILITY_MULTIPLES)
    rows: list[dict[str, Any]] = []
    med_xi = np.full(thr.size, np.nan)
    for j, t in enumerate(thr):
        xi = a["xi"][:, j]
        fin = xi[np.isfinite(xi)]
        if fin.size < 2:
            continue
        p05, med, p95 = np.percentile(fin, [5, 50, 95])
        med_xi[j] = med
        rows.append({"threshold_eur": float(t), "n_exceedances_median": float(np.nanmedian(a["n_exceed"][:, j])), "n_fits": int(fin.size),
                     "tail_index": {"p05": float(p05), "median": float(med), "p95": float(p95)},
                     "share_at_least_one": float(np.mean(fin >= 1.0))})
    keep = np.isfinite(med_xi)
    res = val.threshold_stability(thr[keep], med_xi[keep], model_id=truth_row_model)
    return rows, _row(res, cell.id)


def model_summaries(rv: str) -> list[dict[str, Any]]:
    def m(mid: str, short: str, title: dict[str, str], params: dict[str, Any]) -> dict[str, Any]:
        return {"id": mid, "family": "oprisk", "rung": mid, "title": title, "short_title": T(short, short), "engine": "riskvalidation",
                "engine_version": rv, "licence": "MIT", "calibration": None, "parameters": params, "checkpoint_sha256": None}

    lvl = {"level": {"value": P.LEVEL, "unit": "probability"}}
    by_id = {r["rung_id"]: r for r in P.LADDER}
    out = []
    for rid in ("lda-lognormal", "lda-lognormal-truncated", "lda-splice", "sla", "sla-mean-corrected", "scenario", "sla-mean-adjusted", "sla-cvm",
                "sla-obre", "sla-cvm-lognormal"):
        extra = dict(lvl)
        if rid in ("lda-splice", "scenario"):
            extra["splice_threshold_eur"] = {"value": P.SPLICE_THRESHOLD_EUR, "unit": "EUR"}
        out.append(m(rid, rid, by_id[rid]["label"], extra))
    out.append(m("sma", "sma", T("Standardised approach of OPE25 (BIC x ILM)", "Enfoque estandarizado de OPE25 (BIC x ILM)"),
                 {"loss_multiple": {"value": 15, "unit": "multiple"}, "ilm_exponent": {"value": 0.8, "unit": "exponent"}}))
    return out


def bank_block(bank: dict[str, Any]) -> dict[str, Any]:
    return {
        "currency": P.CURRENCY, "synthetic": True,
        "label": T(f"Synthetic bank of EUR {P.ASSETS_EUR_BN:g} billion in assets", f"Banco sintético de EUR {P.ASSETS_EUR_BN:g} mil millones en activos"),
        "assets_eur": P.ASSETS_EUR_BN * 1e9,
        "business_indicator": {k: bank[k] for k in ("ildc_eur", "sc_eur", "fc_eur", "bi_eur")},
        "bic_eur": bank["bic_eur"], "bucket": bank["bucket"],
        "notice": T("Synthetic data: the business indicator is stated by the case from three years of invented components, and describes no real bank.",
                    "Datos sintéticos: el indicador de negocio lo declara el caso a partir de tres años de componentes inventados y no describe a un banco real."),
    }


def _findings(v: Variant, cells: dict[str, dict[str, Any]], truth: float, orc_median: float, tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    have = {(t["test_id"], t["model_id"], t["segment"]) for t in tests}

    def ev(model: str, seg: str) -> list[str]:
        return [f"oprisk.capital_stability@{model}@{seg}"] if ("oprisk.capital_stability", model, seg) in have else []

    out: list[dict[str, Any]] = []
    s5, s10 = cells["y5-h10000"]["lda_splice"], cells["y10-h20000"]["lda_splice"]
    out.append({"id": "F-1", "severity": "S2", "status": "open", "evidence": ev("lda-splice", "y5-h10000") or ["design:replications"],
                "title": T(f"At tail index {v.tail_index:g} with 5 years of data and threshold EUR 10,000 the splice LDA capital has an interquartile range of "
                           f"{s5['iqr_over_truth']:.0%} of the true 99.9 percent quantile (10 years, threshold EUR 20,000: {s10['iqr_over_truth']:.0%}).",
                           f"Con índice de cola {es_num(v.tail_index, 'g')}, 5 años de datos y umbral de EUR 10.000 el capital LDA con empalme tiene un rango intercuartil de "
                           f"{tx.percent(s5['iqr_over_truth'], 0, lang='es')} del cuantil 99,9 por ciento verdadero (10 años, umbral de EUR 20.000: "
                           f"{tx.percent(s10['iqr_over_truth'], 0, lang='es')}).")})
    a, b = cells["y10-h20000"]["lda_lognormal"], cells["y10-h20000"]["lda_lognormal_truncated"]
    out.append({"id": "F-2", "severity": "S3", "status": "open",
                "evidence": ev("lda-lognormal", "y10-h20000") + ev("lda-lognormal-truncated", "y10-h20000") or ["design:replications"],
                "title": T(f"Ignoring the collection threshold gives a median capital of {sig2(a['ratio_to_truth']['median'], 'en')} times the truth; "
                           f"modelling the truncation gives {sig2(b['ratio_to_truth']['median'], 'en')} (10 years, threshold EUR 20,000).",
                           f"Ignorar el umbral de recolección da un capital mediano de {sig2(a['ratio_to_truth']['median'], 'es')} veces la verdad; "
                           f"modelar el truncamiento da {sig2(b['ratio_to_truth']['median'], 'es')} (10 años, umbral de EUR 20.000).")})
    out.append({"id": "F-3", "severity": "S3", "status": "open", "evidence": ["design:sma-not-calibrated-to-the-999-quantile"],
                "title": T(f"The SMA operational risk capital is {orc_median / truth:.1%} of the true 99.9 percent quantile at tail index {v.tail_index:g}; "
                           "it depends on the losses only through the 10-year average and the BIC.",
                           f"El capital por riesgo operacional del SMA es {es_num(orc_median / truth, '.1%')} del cuantil 99,9 por ciento verdadero con índice de cola "
                           f"{es_num(v.tail_index, 'g')}; depende de las pérdidas solo por el promedio de 10 años y el BIC.")})
    caps = [{"lda_splice": c["lda_splice"], **{k: c[k]["summary"] for k, _ in S3_RUNGS}} for c in cells.values()]
    es_word = {"holds": "se sostiene", "refuted": "se refuta", "inconclusive": "no es concluyente"}
    lines_en, lines_es, refs = [], [], []
    for key, mid in S3_RUNGS[1:3]:
        n, sp, bi = s3_counts(caps, key)
        verdict = s3_verdict(n, sp, bi)
        lines_en.append(f"the {S3_NAME[mid]['en']} has the smaller spread in {sp} of {n} cells and the smaller bias in {bi} (hypothesis {verdict})")
        lines_es.append(f"la {S3_NAME[mid]['es']} tiene el menor rango en {sp} de {n} celdas y el menor sesgo en {bi} (hipótesis: {es_word[verdict]})")
        refs += ev(mid, "y10-h20000")
    out.append({"id": "F-5", "severity": "S3", "status": "open", "evidence": refs + ev("lda-splice", "y10-h20000") or ["design:replications"],
                "title": T(f"Robust severity, tail index {v.tail_index:g}: against the splice LDA, " + "; ".join(lines_en) + ".",
                           f"Severidad robusta, índice de cola {es_num(v.tail_index, 'g')}: frente al LDA con empalme, " + "; ".join(lines_es) + ".")})
    if v.infinite_mean:
        out.append({"id": "F-4", "severity": "S2", "status": "open", "evidence": ["design:infinite-mean"],
                    "title": T("The severity has an infinite mean: no true mean, no expected shortfall and no mean-corrected single loss approximation exist.",
                               "La severidad tiene media infinita: no existen media verdadera, pérdida esperada de cola ni aproximación de una pérdida con corrección por media.")})
    return out


def variant_document(v: Variant, truth: Truth, bank: dict[str, Any], cells: list[CellResult], response: dict[str, Any],
                     scenario: dict[str, Any], bench_row: dict[str, Any], rv: str) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    """``(outputs, tests, impact, findings)`` of one variant; the caller wraps them with ``build_artifact``."""
    tq = truth.quantile_eur
    out_cells: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = [bench_row]
    for c in cells:
        a = c.arrays
        cid = c.id
        cap: dict[str, Any] = {}
        specs = (("lda_lognormal", "lda-lognormal", "monte-carlo"), ("lda_lognormal_truncated", "lda-lognormal-truncated", "panjer"),
                 ("lda_splice", "lda-splice", "fft"), ("sla", "sla", "closed-form"))
        for key, mid, how in specs:
            s, row = capital_summary(a[key], tq, mid, cid, how)
            if s is None:
                raise ValueError(f"C17 {v.variant_id} {cid}: fewer than four histories gave a {mid} capital")
            cap[key] = s
            tests.append(row)
        if v.infinite_mean:
            cap["sla_mean_corrected"] = {"summary": None, "reason": "the tail index is 1 or more: the severity has an infinite mean and the mean "
                                                                   "correction lambda x E[X] does not exist"}
        else:
            s, row = capital_summary(a["sla_mean_corrected"], tq, "sla-mean-corrected", cid, "closed-form", "UNVERIFIED")
            cap["sla_mean_corrected"] = ({"summary": s, "reason": None} if s is not None
                                         else {"summary": None, "reason": "fewer than four histories gave a defined mean-corrected single loss approximation"})
            if row is not None:
                tests.append(row)
        s, row = capital_summary(a["scenario"], tq, "scenario", cid, "panjer")
        cap["scenario"] = ({"summary": s, "reason": None} if s is not None
                           else {"summary": None, "reason": "fewer than four histories gave a scenario combination (the prior or the fit was refused by the engine)"})
        if row is not None:
            tests.append(row)
        for key, mid in S3_RUNGS:
            s, row = capital_summary(a[key], tq, mid, cid, "closed-form", "SECONDARY_SOURCE")
            cap[key] = ({"summary": s, "reason": None} if s is not None
                        else {"summary": None, "reason": "fewer than four histories gave a capital: the fitted severity has no mean (a tail index of 1 or more) "
                                                         "or the engine refused the fit"})
            if row is not None:
                tests.append(row)
        stab, stab_row = _stability(c)
        tests.append(stab_row)
        ok = np.isfinite(a["agree"])
        out_cells.append({
            "id": cid, "years": c.years, "collection_threshold_eur": int(c.threshold), "currency": P.CURRENCY,
            "replications": {"seed_first": c.seed_first, "n_replications": c.n, "n_failed": int(a["failed"].sum()),
                             "n_losses_median": float(np.median(a["n_losses"]))},
            "capital": cap,
            "aggregation_agreement": {"max_rel_diff_panjer_fft": float(np.max(a["agree"][ok])), "n_compared": int(ok.sum())},
            "threshold_stability": stab, "sma": _sma_block(c, bank, tq),
        })
    tests.extend([response["test"], scenario["test"]])
    sma_med = out_cells[-1]["sma"]["orc_eur"]["median"]
    impact = {
        "lda_capital_999": {"value": out_cells[-1]["capital"]["lda_splice"]["capital_eur"]["median"], "unit": "EUR",
                            "label": T("LDA 99.9 percent capital, splice (median over histories, 10 years)",
                                       "Capital LDA al 99,9 por ciento, empalme (mediana, 10 años)")},
        "sma_orc": {"value": sma_med, "unit": "EUR", "label": T("SMA operational risk capital (median, 10 years)", "Capital por riesgo operacional SMA (mediana, 10 años)")},
    }
    findings = _findings(v, {c["id"]: c["capital"] for c in out_cells}, tq, sma_med, tests)
    outputs = {
        "kind": "tail-index", "currency": P.CURRENCY, "tail_index": v.tail_index, "infinite_mean": v.infinite_mean, "truth": truth.truth_block,
        "calibration": {"targets": P.LDCE_TARGETS,
                        "fit": {"tail_index": v.tail_index, "scale_eur": v.scale_eur, "fitted_quantiles_eur": list(v.fitted_quantiles_eur),
                                "max_abs_log_error": v.max_abs_log_error,
                                "method": "least squares on the log excess quantiles over EUR 20,000, scale only (the tail index is the variant's)"}},
        "bank": bank_block(bank), "cells": out_cells, "exceedance": truth.exceedance_block, "sma_response": response["block"],
        "scenario_influence": scenario["block"],
    }
    return outputs, tests, impact, findings


def models_document(vs: list[Variant], truths: dict[float, Truth], seed_base: int, n_rep: int, mc_years_truth: int, mc_years_rep: int, rv: str) -> dict[str, Any]:
    from .truth import PANJER_POINTS, TRUTH_POINTS

    fit = {
        "currency": P.CURRENCY,
        "generator": {"name": P.GENERATOR, "shaped_on": "bcbs160-ldce-2008", "assets_eur_bn": P.ASSETS_EUR_BN, "frequency_law": "poisson",
                      "severity_law": "gpd", "generator_floor_eur": P.FLOOR_EUR,
                      "notice": GENERATOR_NOTICE},
        "calibration": P.LDCE_TARGETS,
        "variants": [{"variant_id": v.variant_id, "tail_index": v.tail_index, "infinite_mean": v.infinite_mean, "lambda_per_year": v.lambda_per_year,
                      "location_eur": P.FLOOR_EUR, "scale_eur": v.scale_eur, "true_quantile_999_eur": truths[v.tail_index].quantile_eur,
                      "true_mean_eur": truths[v.tail_index].mean_eur,
                      "true_mean_reason": None if truths[v.tail_index].mean_eur is not None else
                      "the tail index is 1 or more: the severity has an infinite mean, so the annual loss has no mean"} for v in vs],
        "grid": {"years": list(P.YEARS), "collection_thresholds_eur": list(P.THRESHOLDS_EUR), "n_replications_per_cell": n_rep,
                 "seed_base": seed_base, "seed_stride": P.SEED_STRIDE},
        "ladder": P.LADDER,
        "aggregation": {"level": P.LEVEL, "panjer_step_eur": P.PANJER_STEP_EUR, "panjer_points": PANJER_POINTS, "fft_points": TRUTH_POINTS,
                        "fft_padding_factor": 4, "fft_tilt": 0.0, "mc_years_truth": mc_years_truth,
                        "mc_years_replication": mc_years_rep},
        "sma": P.SMA_SPEC,
        "scenarios": P.SCENARIO_SPEC,
    }
    return {"fit_id": "generator", "model": [{**m, "details": {}} for m in model_summaries(rv)], "fit": fit}
