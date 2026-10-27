"""The C11 documents: one window document per window (``c11-outputs``) and one models document (``c11-models``).

Every statistic is ``riskvalidation``: the exceedance tests, the Basel zone, the Acerbi-Szekely test, the dynamic quantile
test (``riskvalidation.validation.market``), the FZ0 and tick scores, the Diebold-Mariano comparison and the model confidence
set (``riskvalidation.market``). This module converts the engine's return convention into the document's positive losses
once (``to_loss_numbers``), rounds every array to the nine significant digits the writer keeps **before** any score is taken
(so each score recomputes from the committed arrays, which the producer checks do), arranges the results into the schema and
chooses nothing else: the champion is the lowest average FZ0 among the eligible models with an ES on every day, and a model
is eligible when none of Kupiec, conditional coverage and Acerbi-Szekely is red at either level.

The null of the Acerbi-Szekely test. The engine asks for ``simulate_null(rng)``, a loss path from the model's own predictive
distributions, which a historical, CAViaR or GAS model does not have. The same tail-consistent null is used for every rung: on
each day the loss exceeds the VaR with probability alpha, by an exponential excess whose mean is ``ES - VaR``, so the
simulated losses reproduce the model's own VaR and ES and the test asks only whether the ES level is right. The shape of the
excess is a stated assumption (exponential, the generalised Pareto with shape 0); a heavier real tail makes the critical values
too narrow. This is written in the case page and in the models document.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from riskvalidation.market import frtb as rv_frtb
from riskvalidation.market import scoring as rv_scoring
from riskvalidation.validation import market as rv_val
from riskvalidation.validation.market import _z_statistic

from ...core.text import percent
from . import portfolio as pf
from .constants import (BASEL_DAYS, LEVELS, MC_DRAWS, MCS_BLOCK, MCS_BOOTSTRAP, MCS_CONFIDENCE, MCS_STATISTIC, SIGNIFICANCE, SPAN,
                        WINDOWS, Z2_DRAWS)
from .forecast import CHALLENGER, LADDER, Hyper, ModelRun, Spec, look_back

GATES = ("market.kupiec_pof", "market.christoffersen_conditional_coverage", "market.acerbi_szekely")
US_MULTIPLIER = (3.0, 3.0, 3.0, 3.0, 3.0, 3.4, 3.5, 3.65, 3.75, 3.85, 4.0)   # 12 CFR 217.204 Table 1 (dossier 05 B.4)
REFIT_OF = {"garch": "garch_refit_every_days", "fhs": "garch_refit_every_days", "caviar": "caviar_refit_every_days",
            "caviar-es": "caviar_refit_every_days", "gas": "gas_refit_every_days"}
NO_ES = "the model forecasts no ES: FZ0 is not defined"


def t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def r9(x: float) -> float:
    """Nine significant digits, the precision the writer keeps; applied first so scores recompute from the stored arrays."""
    return float(f"{x:.9g}")


def sign_convention() -> dict:
    return {"engine_convention": "return-negative", "document_convention": "positive-loss",
            "definition": t("The engine stores VaR and ES in the return convention (negative numbers at the tail level alpha); this "
                            "document stores positive loss numbers, as decimals of the portfolio value.",
                            "El motor guarda VaR y ES en la convención de retornos (números negativos al nivel alfa); este "
                            "documento guarda pérdidas positivas, como decimales del valor de la cartera.")}


def refit_days(spec: Spec, hp: Hyper) -> int:
    name = REFIT_OF.get(spec.kind)
    return int(getattr(hp, name)) if name else 1


# ------------------------------------------------------------------------------------------------------------------- one window

def tail_null(var: np.ndarray, es: np.ndarray, alpha: float, zs: list[float]):
    """``simulate_null`` for the engine's Z2 test: the tail-consistent null of the module docstring. Every simulated path's Z2
    is appended to ``zs`` (the engine calls it once per draw), so the histogram is the engine's own null."""
    n = var.size
    excess = es - var

    def simulate(rng: np.random.Generator) -> np.ndarray:
        hit = rng.random(n) < alpha
        path = np.where(hit, var + rng.exponential(1.0, n) * excess, 0.0)
        zs.append(float(_z_statistic(path, var, es, alpha, "Z2")))
        return path

    return simulate


def _levels_for(spec: Spec, run: ModelRun, loss: np.ndarray, hp: Hyper) -> dict[float, dict[str, Any]]:
    """The rounded positive-loss arrays and the engine's scores of one model at each level."""
    out: dict[float, dict[str, Any]] = {}
    for a in LEVELS:
        var = np.array([r9(-v) for v in run.var[a]])
        es_raw = run.es[a]
        es = np.array([r9(-e) if np.isfinite(e) else np.nan for e in es_raw])
        if not np.all(var > 0.0):
            raise ValueError(f"{spec.model_id}@{a}: a VaR is not a positive loss (min {var.min():.3g})")
        if np.any(es[np.isfinite(es)] < var[np.isfinite(es)]):
            raise ValueError(f"{spec.model_id}@{a}: an ES is below its VaR")
        out[a] = {"var": var, "es": es}
    return out


def _flags(loss: np.ndarray, var: np.ndarray) -> np.ndarray:
    return (loss > var).astype(int)


def _test_row(res) -> dict:
    return res.to_dict()


def window_tests(spec: Spec, a: float, loss: np.ndarray, var: np.ndarray, es: np.ndarray, hp: Hyper, mc: int = MC_DRAWS,
                 z2: int = Z2_DRAWS) -> tuple[list[dict], dict | None]:
    """The rows of one model at one level and, when the ES test ran, its simulated null (histogram and the engine's numbers)."""
    mid, flags = spec.model_id, _flags(loss, var)
    rows = [rv_val.kupiec_pof(flags, a, mid), rv_val.christoffersen_independence(flags, a, mid),
            rv_val.christoffersen_conditional_coverage(flags, a, mid),
            rv_val.duration_test(flags, a, mid, n_mc=mc, seed=hp.seed),
            rv_val.dynamic_quantile_test(flags, -var, a, 4, mid, n_mc=mc, seed=hp.seed)]
    zs: list[float] = []
    if np.all(np.isfinite(es)):
        az = rv_val.acerbi_szekely(loss, var, es, a, tail_null(var, es, a, zs), mid, "Z2", z2, hp.seed)
    else:
        az = rv_val.acerbi_szekely(loss, var, es, a, lambda rng: loss, mid, "Z2", 1, hp.seed)   # not evaluated: an ES is undefined
    rows.append(az)
    null = None
    if zs and az.light.value != "not_evaluated":
        lo, hi = float(min(zs)), float(max(zs))
        counts, edges = np.histogram(zs, bins=20, range=(lo, hi if hi > lo else lo + 1e-9))
        null = {"model_id": mid, "alpha": a, "statistic": "Z2", "realised": az.statistic,
                "critical_5pct": az.extras["critical_5pct"], "critical_0_01pct": az.extras["critical_0_01pct"],
                "n_draws": z2, "p_value": az.p_value, "histogram": {"edges": [float(e) for e in edges], "counts": [int(c) for c in counts]}}
    return [_test_row(r) for r in rows], null


def traffic_light(flags: np.ndarray, n: int) -> dict:
    if n < BASEL_DAYS:
        return {"window_days": BASEL_DAYS, "n_windows": 0, "max_rolling_exceedances": None, "final_rolling_exceedances": None,
                "final_zone": "not_evaluated", "days_green": None, "days_amber": None, "days_red": None,
                "reason": f"fewer than {BASEL_DAYS} forecast days ({n}): the Basel traffic light of MAR32.9 is defined on {BASEL_DAYS} "
                          "observations and the window has no lead-in"}
    c = np.concatenate([[0], np.cumsum(flags)])
    counts = (c[BASEL_DAYS:] - c[:-BASEL_DAYS]).astype(int)
    zones = [rv_frtb.traffic_light_zone(int(k)) for k in counts]
    return {"window_days": BASEL_DAYS, "n_windows": int(counts.size), "max_rolling_exceedances": int(counts.max()),
            "final_rolling_exceedances": int(counts[-1]), "final_zone": zones[-1], "days_green": zones.count("green"),
            "days_amber": zones.count("amber"), "days_red": zones.count("red"), "reason": None}


def level_result(spec: Spec, a: float, loss: np.ndarray, var: np.ndarray, es: np.ndarray, test_ids: list[str]) -> dict:
    n = loss.size
    flags = _flags(loss, var)
    exc = [int(i) for i in np.flatnonzero(flags)]
    ok = np.isfinite(es)
    y, v = -loss, -var
    e = np.where(ok, -es, np.nan)
    sc = rv_scoring.mean_scores(y, v, e, a)
    undef = [int(i) for i in np.flatnonzero(~ok)]
    status = "forecast" if not undef else ("not-forecast" if len(undef) == n else "undefined-on-days")
    reason = None
    if sc.fz0_mean is None:
        reason = NO_ES if status == "not-forecast" and not spec.forecasts_es else "the ES is undefined on every day: FZ0 is not defined"
    return {"alpha": a, "var": [float(x) for x in var], "es": [float(x) if f else None for x, f in zip(es, ok, strict=True)],
            "es_status": status, "es_undefined_days": [] if status == "not-forecast" else undef,
            "exceedance_days": exc, "n_scored": n, "n_exceedances": len(exc), "expected_exceedances": a * n,
            "n_fz0": sc.n_fz0, "fz0_mean": sc.fz0_mean, "fz0_reason": reason, "tick_loss_mean": sc.tick_mean,
            "traffic_light": traffic_light(flags, n) if a == 0.01 else None, "test_ids": test_ids}


def _fz0_series(loss: np.ndarray, var: np.ndarray, es: np.ndarray, a: float) -> np.ndarray:
    """Per-day FZ0 (NaN where the ES is undefined), the engine's loss on the return convention."""
    out = np.full(loss.size, np.nan)
    ok = np.isfinite(es)
    if ok.any():
        out[ok] = rv_scoring.fz0_loss(-loss[ok], -var[ok], -es[ok], a)
    return out


#: the rule that picks the champion, in both languages (a Spanish view prints it: "pruebas retrospectivas", R3 c12 m5)
SCORING_RULE = t(
    "Traditional back-tests (POF, conditional coverage, Z2) are eligibility gates; the champion is the lowest average FZ0 among the eligible models with an ES on every day; Diebold-Mariano and the model confidence set rank the ladder. The Z2 null is tail-consistent: an exponential excess over the VaR with mean ES minus VaR.",
    "Las pruebas retrospectivas tradicionales (proporción de fallas, cobertura condicional, Z2) son compuertas de elegibilidad; el campeón es el menor FZ0 medio entre los elegibles con ES todos los días; Diebold-Mariano y el conjunto de confianza de modelos ordenan la escalera. La nula de Z2 es consistente con la cola: un exceso exponencial sobre el VaR con media ES menos VaR.")


def no_champion_reason(n_eligible: int) -> str:
    """Why a level has no champion: no model is eligible at all, or none of the eligible ones has an ES on every day (R3 c12 m6)."""
    if n_eligible == 0:
        return "no model is eligible: every model fails at least one gate"
    return "no eligible model has an ES on every day, so none has an FZ0 score to rank"


def comparison(specs: list[Spec], loss: np.ndarray, arrays: dict[str, dict[float, dict]], eligible: dict[str, bool], hp: Hyper) -> dict:
    n = loss.size
    champions, dm_rows, mcs = [], [], []
    for a in LEVELS:
        fz = {s.model_id: _fz0_series(loss, arrays[s.model_id][a]["var"], arrays[s.model_id][a]["es"], a) for s in specs}
        tick = {s.model_id: rv_scoring.tick_loss(-loss, -arrays[s.model_id][a]["var"], a) for s in specs}
        full = [m for m, f in fz.items() if np.isfinite(f).all()]
        cands = [(float(np.mean(fz[m])), m) for m in full if eligible[m]]
        champ = min(cands)[1] if cands else None
        champions.append({"alpha": a, "model_id": champ, "reason": None if champ else no_champion_reason(sum(eligible.values()))})
        for s in specs:
            m = s.model_id
            if champ is None or m == champ:
                continue
            for lk in ("fz0", "tick"):
                row = {"model_id": m, "versus": champ, "alpha": a, "loss": lk, "mean_diff": None, "dm_statistic": None,
                       "p_value": None, "hac_lags": 0, "n_common": None, "direction": "not-evaluated", "not_evaluated_reason": None}
                if lk == "fz0":
                    common = np.isfinite(fz[m]) & np.isfinite(fz[champ])
                    la, lb = fz[m][common], fz[champ][common]
                    if not np.isfinite(fz[m]).any():
                        row["not_evaluated_reason"] = NO_ES
                        dm_rows.append(row)
                        continue
                else:
                    la, lb = tick[m], tick[champ]
                try:
                    dm = rv_scoring.diebold_mariano(la, lb, 0)
                except ValueError as exc:
                    row["not_evaluated_reason"] = str(exc)
                    dm_rows.append(row)
                    continue
                direction = "indistinguishable" if dm.p_value >= SIGNIFICANCE else ("better" if dm.mean_diff < 0 else "worse")
                row.update(mean_diff=dm.mean_diff, dm_statistic=dm.statistic, p_value=dm.p_value, n_common=dm.n, direction=direction)
                dm_rows.append(row)
        if len(full) >= 1:
            losses = np.column_stack([fz[m] for m in full])
            res = rv_scoring.model_confidence_set(losses, MCS_CONFIDENCE, MCS_STATISTIC, MCS_BOOTSTRAP, min(MCS_BLOCK, max(1, n // 4)), hp.seed)
            members = [{"model_id": m, "in_set": i in res.members, "p_value": float(res.p_values[i])} for i, m in enumerate(full)]
            mcs.append({"alpha": a, "loss": "fz0", "statistic": MCS_STATISTIC, "confidence": MCS_CONFIDENCE, "n_bootstrap": MCS_BOOTSTRAP,
                        "block_length": min(MCS_BLOCK, max(1, n // 4)), "members": members, "n_in_set": len(res.members)})
    return {"significance": SIGNIFICANCE, "hac_kernel": "bartlett", "hac_lags": 0, "champions": champions, "dm": dm_rows, "mcs": mcs}


def model_summary(spec: Spec, hp: Hyper, engine_version: str) -> dict:
    params = {"window_days": {"value": float(look_back(spec, hp)), "unit": "days"},
              "refit_every_days": {"value": float(refit_days(spec, hp)), "unit": "days"}}
    if spec.kind == "ewma":
        params["lambda"] = {"value": hp.ewma_lambda, "unit": "1"}
    if spec.kind == "awhs":
        params["lambda"] = {"value": hp.age_weight_lambda, "unit": "1"}
    if spec.kind == "evt":
        params["threshold_fraction"] = {"value": hp.evt_threshold_fraction, "unit": "1"}
    return {"id": spec.model_id, "family": "market-var-es", "rung": spec.rung, "title": t(spec.en, spec.es), "short_title": t(spec.model_id, spec.model_id),
            "engine": "riskvalidation", "engine_version": engine_version, "licence": "MIT", "calibration": None, "parameters": params,
            "checkpoint_sha256": None}


def hyper_block(hp: Hyper, mc: int = MC_DRAWS, z2: int = Z2_DRAWS) -> dict:
    return {"fixed_on": {"start": SPAN[0], "end": SPAN[1]}, "tuned_on_test_window": False,
            "estimation_window_days": hp.estimation_window_days, "ewma_lambda": hp.ewma_lambda, "age_weight_lambda": hp.age_weight_lambda,
            "evt_threshold_fraction": hp.evt_threshold_fraction, "garch_refit_every_days": hp.garch_refit_every_days,
            "caviar_n_starts": hp.caviar_n_starts, "gas_n_starts": hp.gas_n_starts, "seed": hp.seed,
            "others": [{"name": "caviar_refit_every_days", "value": hp.caviar_refit_every_days, "unit": "days"},
                       {"name": "gas_refit_every_days", "value": hp.gas_refit_every_days, "unit": "days"},
                       {"name": "hs_short_window", "value": 250, "unit": "days"}, {"name": "hs_long_window", "value": 500, "unit": "days"},
                       {"name": "evt_refit_every_days", "value": 1, "unit": "days"},
                       {"name": "z2_draws", "value": z2, "unit": "draws"}, {"name": "mc_draws", "value": mc, "unit": "draws"}]}


def portfolio_block(p: pf.Portfolio) -> dict:
    w = p.window
    comps = []
    for s in p.components:
        klass, transform, (en, es) = pf.COMPONENT_META[s.series_id]
        comps.append({"series_id": s.series_id, "label": t(en, es), "source_class": klass, "weight": p.weights[s.series_id], "transform": transform})
    names = {"equity": ("A long position in the US equity market, the daily return of the Fama-French market factor plus the risk-free rate.",
                        "Posición larga en el mercado accionario de EE. UU.: el retorno diario del factor de mercado de Fama-French más la tasa libre de riesgo."),
             "rates": ("A long position in the 10-year US Treasury par bond: the daily return is minus the modified duration times the yield change.",
                       "Posición larga en el bono par del Tesoro de EE. UU. a 10 años: el retorno diario es menos la duración modificada por el cambio del rendimiento."),
             "fx": ("A long position in the euro against the US dollar: the simple daily return of US dollars per euro (H.10).",
                    "Posición larga en el euro frente al dólar: el retorno simple diario de dólares por euro (H.10)."),
             "mixed": ("A mixed book of 50 percent US equity, 30 percent 10-year Treasury par bond and 20 percent euro, rebalanced daily to constant weights.",
                       "Una cartera mixta de 50 por ciento renta variable de EE. UU., 30 por ciento bono par a 10 años y 20 por ciento euro, reequilibrada a diario a pesos constantes.")}
    en, es = names[w.asset_class]
    return {"description": t(en, es), "value_unit": "decimal-of-portfolio-value", "currency": "USD",
            "weighting": "constant-weights-daily-rebalanced", "components": comps}


def provenance_block(p: pf.Portfolio, seed: int, code_version: str, engine_version: str) -> dict:
    src = {"french-daily": ("french-data-library", "derived-only"), "treasury-par": ("treasury-par-curve", "mirror-allowed"),
           "h10-fx": ("fred-public-domain", "mirror-allowed")}
    inputs = [{"source": src[s.series_id][0], "class": src[s.series_id][1],
               "files": [{"name": f.name, "sha256": f.sha256} for f in s.files]} for s in p.components]
    return {"truth_status": "real-outcomes", "inputs": inputs, "licence_classes": {i["source"]: i["class"] for i in inputs},
            "generators": ["contraste:c11-bake"], "seed": seed, "code_version": code_version, "riskvalidation_version": engine_version}


def build_window(p: pf.Portfolio, runs: dict[str, ModelRun], hp: Hyper, *, code_version: str, engine_version: str,
                 model_ids: tuple[str, ...] | None = None, mc_draws: int = MC_DRAWS, z2_draws: int = Z2_DRAWS,
                 limit: int | None = None) -> dict:
    """The ``c11-outputs`` document of one window from its portfolio and the forecasts of every model.

    ``mc_draws``, ``z2_draws`` and ``limit`` (the first days of the window) are for tests of a small size; the bake uses the defaults."""
    w = p.window
    pos = pf.forecast_positions(p, limit)
    n = pos.size
    loss = np.array([r9(-x) for x in p.returns[pos]])
    specs = [s for s in LADDER if (model_ids is None or s.model_id in model_ids)]
    arrays: dict[str, dict[float, dict]] = {}
    tests: list[dict] = []
    nulls: list[dict] = []
    models, eligible = [], {}
    by_level_all: dict[str, list[dict]] = {}
    for s in specs:
        arrays[s.model_id] = _levels_for(s, runs[s.model_id], loss, hp)
        by_level, failed = [], set()
        for a in LEVELS:
            ar = arrays[s.model_id][a]
            rows, null = window_tests(s, a, loss, ar["var"], ar["es"], hp, mc_draws, z2_draws)
            tests += rows
            if null:
                nulls.append(null)
            failed |= {r["test_id"] for r in rows if r["test_id"] in GATES and r["light"] == "red"}
            by_level.append(level_result(s, a, loss, ar["var"], ar["es"], [r["test_id"] for r in rows]))
        eligible[s.model_id] = not failed
        models.append({"model_id": s.model_id, "rung": s.rung, "eligible": not failed, "failed_gates": sorted(failed), "by_level": by_level})
        by_level_all[s.model_id] = by_level
    cmp = comparison(specs, loss, arrays, eligible, hp)
    dates = p.dates[pos]
    lookback = hp.estimation_window_days
    est_end = [str(p.dates[i - 1]) for i in pos]
    est_start = [str(p.dates[i - min(lookback, int(i))]) for i in pos]
    first_obs = est_start[0]
    in_range = [d for d in p.missing if first_obs <= d <= str(dates[-1])]
    n_obs = int(np.sum((p.dates >= np.datetime64(first_obs)) & (p.dates <= dates[-1])))
    derived = p.derived_only
    rl = {"status": "withheld-derived-only", "loss": None,
          "reason": "A component of this portfolio is the Kenneth French equity return, a derived-only source (dossier 08 C.5): only "
                    "model outputs are committed, so the realised loss series is withheld; the exceedance days and the scores stand."} \
        if derived else {"status": "included", "loss": [float(x) for x in loss], "reason": None}
    champ = {c["alpha"]: c["model_id"] for c in cmp["champions"]}
    fz_of = {(m["model_id"], lv["alpha"]): lv["fz0_mean"] for m in models for lv in m["by_level"]}
    impact = {
        "champion_fz0_1pct": {"value": fz_of.get((champ[0.01], 0.01)) if champ[0.01] else None, "unit": "fz0-loss",
                              "label": t("Champion average FZ0 at 1 percent", "FZ0 medio del campeón al 1 por ciento")},
        "champion_fz0_2_5pct": {"value": fz_of.get((champ[0.025], 0.025)) if champ[0.025] else None, "unit": "fz0-loss",
                                "label": t("Champion average FZ0 at 2.5 percent", "FZ0 medio del campeón al 2,5 por ciento")},
        "eligible_models": {"value": float(sum(eligible.values())), "unit": "models", "label": dict(ELIGIBLE_LABEL)}}
    outputs = {
        "kind": "window",
        "window": {"window_id": w.window_id, "asset_class": w.asset_class, "title": t(w.en, w.es), "start_date": w.start, "end_date": w.end,
                   "n_forecast_days": n},
        "sign_convention": sign_convention(), "levels": [{"alpha": a} for a in LEVELS], "portfolio": portfolio_block(p),
        "data_status": {"first_observation": first_obs, "last_observation": str(dates[-1]), "n_observed_days": n_obs,
                        "missing_days": {"count": len(in_range), "dates": in_range, "treatment": "skipped-not-filled"}},
        "grid": {"scheme": "rolling", "estimation_window_days": lookback, "dates": [str(d) for d in dates],
                 "estimation_start": est_start, "estimation_end": est_end, "realised_loss": rl},
        "hyperparameters": hyper_block(hp, mc_draws, z2_draws), "models": models, "comparison": cmp,
        "es_backtests": sorted(nulls, key=lambda x: (x["model_id"], x["alpha"])),
    }
    return {"schema": "contraste.case/v1", "case_id": "C11", "variant_id": w.window_id,
            "model": [model_summary(s, hp, engine_version) for s in specs], "outputs": outputs, "tests": tests, "impact": impact,
            "findings": findings(models, tests), "provenance": provenance_block(p, hp.seed, code_version, engine_version),
            "lane": {"lane": "precompute", "reasons": []}}


#: what the eligible count is: the models no gate rejects; a gate that did not run (no exceedance) rejects nothing, so the count is not
#: "the models that pass every gate" (R4 c14 NB1)
ELIGIBLE_LABEL = t("Models no eligibility gate rejects", "Modelos que ninguna compuerta de elegibilidad rechaza")

#: the gate tests in words, in the order of GATES
GATE_TEXT = {"market.kupiec_pof": t("the coverage test", "la prueba de cobertura"),
             "market.christoffersen_conditional_coverage": t("the conditional coverage test", "la prueba de cobertura condicional"),
             "market.acerbi_szekely": t("the ES test", "la prueba de ES")}


def _tail(alpha: float, lang: str) -> str:
    return percent(alpha, 0 if round(alpha * 100) == alpha * 100 else 1, lang=lang)


def _not_run(n: int, tests: list[dict]) -> dict[str, str] | None:
    """The gates that did not run, with their counts by tail level, in both languages; None when every gate ran for every model."""
    parts_en, parts_es = [], []
    for g in GATES:
        counts = []
        for a in LEVELS:
            k = sum(1 for r in tests if r["test_id"] == g and r["segment"] == f"alpha={a}" and r["light"] == "not_evaluated")
            if k:
                counts.append((a, k))
        if not counts:
            continue
        name = GATE_TEXT[g]
        if len(counts) == len(LEVELS) and len({k for _, k in counts}) == 1:
            parts_en.append(f"{name['en']} for {counts[0][1]} of {n} at each tail")
            parts_es.append(f"{name['es']}, para {counts[0][1]} de {n} en cada cola")
            continue
        en = [f"{k} of {n} models at the {_tail(a, 'en')} tail" if i == 0 else f"{k} of {n} at the {_tail(a, 'en')} tail"
              for i, (a, k) in enumerate(counts)]
        es = [f"{k} de {n} modelos en la cola de {_tail(a, 'es')}" if i == 0 else f"{k} de {n} en la de {_tail(a, 'es')}"
              for i, (a, k) in enumerate(counts)]
        parts_en.append(f"{name['en']} was not evaluated for {' and '.join(en)}")
        parts_es.append(f"{name['es']} no se evaluó para {' y para '.join(es)}")
    if not parts_en:
        return None
    return {"en": ", ".join(parts_en), "es": "; ".join(parts_es)}


def findings(models: list[dict], tests: list[dict]) -> list[dict]:
    n = len(models)
    failing = [m["model_id"] for m in models if not m["eligible"]]
    clustered = sorted({r["model_id"] for r in tests if r["test_id"] == "market.christoffersen_independence" and r["light"] == "red"})
    out = []
    if failing:
        out.append({"id": "c11-gates", "severity": "S2", "status": "open", "evidence": list(GATES),
                    "title": t(f"{len(failing)} of {n} models fail at least one eligibility gate (coverage, conditional coverage or the ES test).",
                               f"{len(failing)} de {n} modelos fallan al menos una compuerta de elegibilidad (cobertura, cobertura condicional o la prueba de ES).")})
    else:
        not_run = _not_run(n, tests)
        if not_run is None:
            # every gate ran and none is red: said so and accepted, never an open finding of "0 of 17 models fail" (R3 c12 m6)
            out.append({"id": "c11-gates", "severity": "S4", "status": "accepted", "evidence": list(GATES),
                        "title": t(f"All {n} models pass every eligibility gate (coverage, conditional coverage and the ES test).",
                                   f"Los {n} modelos pasan todas las compuertas de elegibilidad (cobertura, cobertura condicional y la prueba de ES).")})
        else:
            # no gate is red, but a gate that did not run passed nothing: the finding counts what did not run and stays open (R4 c14 NB1:
            # mixed-2023 said every model passed conditional coverage, which ran for none of them at the 1 % tail)
            out.append({"id": "c11-gates", "severity": "S4", "status": "open", "evidence": list(GATES),
                        "title": t(f"No model fails an eligibility gate, but not every gate ran: {not_run['en']}.",
                                   f"Ningún modelo falla una compuerta de elegibilidad, pero no todas corrieron: {not_run['es']}.")})
    if clustered:
        out.append({"id": "c11-clustering", "severity": "S3", "status": "open", "evidence": ["market.christoffersen_independence"],
                    "title": t(f"{len(clustered)} models show clustered exceedances (independence test red).",
                               f"{len(clustered)} modelos muestran excedencias agrupadas (prueba de independencia en rojo).")})
    return out


# ------------------------------------------------------------------------------------------------------------------- the models document

def _summ(values: list[float]) -> dict:
    a = np.array(values, dtype=float)
    return {"min": float(a.min()), "median": float(np.median(a)), "max": float(a.max())}


def build_models(portfolios: dict[str, pf.Portfolio], runs: dict[str, dict[str, ModelRun]], hp: Hyper, *, code_version: str,
                 engine_version: str, provenance: dict, model_ids: tuple[str, ...] | None = None) -> dict:
    specs = [s for s in LADDER if model_ids is None or s.model_id in model_ids]
    ladder = []
    for s in specs:
        fits = []
        for wd in WINDOWS:
            r = runs[wd.window_id][s.model_id]
            pars = [{"name": k, "unit": "1", **_summ(v)} for k, v in sorted(r.params.items()) if v]
            fits.append({"window_id": wd.window_id, "n_refits": r.n_refits, "n_convergence_failures": r.n_failures, "parameters": pars})
            if r.n_fallback_days:
                fits[-1]["parameters"].append({"name": "fallback_days", "unit": "days", "min": float(r.n_fallback_days),
                                               "median": float(r.n_fallback_days), "max": float(r.n_fallback_days)})
        ladder.append({"model_id": s.model_id, "rung": s.rung, "title": t(s.en, s.es), "family": "market-var-es", "source": s.source,
                       "status": "fitted", "not_run_reason": None, "innovation": s.innovation, "estimation_window_days": look_back(s, hp),
                       "refit_every_days": refit_days(s, hp), "forecasts_es": s.forecasts_es, "es_method": s.es_method, "window_fits": fits})
    c = CHALLENGER
    ladder.append({"model_id": c["model_id"], "rung": c["rung"], "title": t(c["en"], c["es"]), "family": "market-var-es", "source": c["source"],
                   "status": "challenger-not-run", "not_run_reason": c["reason"], "innovation": "none", "estimation_window_days": None,
                   "refit_every_days": None, "forecasts_es": True, "es_method": "network output", "window_fits": []})
    traffic = {"window_days": 250, "confidence": 0.99,
               "reference": "MAR32.9 Table 1 (dossier 01 D.4); 12 CFR 217.204 Table 1 (dossier 05 B.4)",
               "rows": [{"exceptions": k, "zone": rv_frtb.traffic_light_zone(k), "frtb_multiplier": rv_frtb.mar32_multiplier(k),
                         "us_multiplier": US_MULTIPLIER[k],
                         "cumulative_probability_pct": round(100 * rv_frtb.binomial_cumulative_probability(k, 250, 0.01), 2)}
                        for k in range(11)]}
    return {
        "schema": "contraste.models/v1", "case_id": "C11", "fit_id": "ladder",
        "model": [{**model_summary(s, hp, engine_version), "details": {"source": s.source, "es_method": s.es_method}} for s in specs]
                 + [{"id": c["model_id"], "family": "market-var-es", "rung": c["rung"], "title": t(c["en"], c["es"]),
                     "short_title": t(c["model_id"], c["model_id"]), "engine": "riskvalidation", "engine_version": engine_version,
                     "licence": "MIT", "calibration": None, "parameters": {}, "checkpoint_sha256": None, "details": {"not_run": c["reason"]}}],
        "fit": {
            "sign_convention": sign_convention(), "levels": [{"alpha": a} for a in LEVELS],
            "windows": [{"window_id": w.window_id, "asset_class": w.asset_class, "start_date": w.start, "end_date": w.end,
                         "fixed_on": {"start": SPAN[0], "end": SPAN[1]}} for w in WINDOWS],
            "ladder": ladder, "traffic_light": traffic,
            "es_reference": {"statistic": "Z2", "n_days": 250, "alpha": 0.025, "yellow": -0.7, "red": -1.8,
                             "status": t("A published reference point (Acerbi and Szekely), not a regulatory threshold; each model's own simulated critical values are in the outputs.",
                                         "Un punto de referencia publicado (Acerbi y Szekely), no un umbral regulatorio; los valores críticos simulados de cada modelo están en los resultados.")},
            "scoring": {"fz0_formula": "-(1/(alpha*e))*1{y<=v}*(v-y) + v/e + log(-e) - 1", "tick_formula": "(alpha - 1{y<v})*(y - v)",
                        "hac_kernel": "bartlett", "mcs_confidence": MCS_CONFIDENCE, "mcs_statistic": MCS_STATISTIC,
                        "selection_rule": dict(SCORING_RULE)},
            "eligibility_gates": [
                {"test_id": "market.kupiec_pof", "rule": t("Red at the 5 percent level at either tail level: ineligible.", "Rojo al 5 por ciento en cualquiera de los dos niveles: inelegible.")},
                {"test_id": "market.christoffersen_conditional_coverage", "rule": t("Red at the 5 percent level at either tail level: ineligible.", "Rojo al 5 por ciento en cualquiera de los dos niveles: inelegible.")},
                {"test_id": "market.acerbi_szekely", "rule": t("Red against the model's own simulated critical value: ineligible; not evaluated is not red.", "Rojo frente al valor crítico simulado propio: inelegible; no evaluado no es rojo.")}],
            "data_sources": [
                {"series_id": "french-daily", "title": t("Kenneth French data library, daily factor returns", "Biblioteca de datos de Kenneth French, retornos diarios de factores"),
                 "source_class": "derived-only", "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
                 "licence_note": t("Copyright Eugene F. Fama and Kenneth R. French; only derived results are committed (dossier 08 C.5).", "Copyright Eugene F. Fama y Kenneth R. French; solo se publican resultados derivados (dossier 08 C.5).")},
                {"series_id": "treasury-par", "title": t("US Treasury daily par yield curve", "Curva de rendimientos par diaria del Tesoro de EE. UU."),
                 "source_class": "mirror-allowed", "url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/",
                 "licence_note": t("Work of US federal employees (17 U.S.C. 105; page statement UNVERIFIED, dossier 08 C.2).", "Obra de empleados federales de EE. UU. (17 U.S.C. 105; la declaración de la página no está verificada, dossier 08 C.2).")},
                {"series_id": "h10-fx", "title": t("Federal Reserve H.10 foreign exchange rates, euro", "Tipos de cambio H.10 de la Reserva Federal, euro"),
                 "source_class": "mirror-allowed", "url": "https://www.federalreserve.gov/releases/h10/",
                 "licence_note": t("Board publication under the Board's public-domain statement (dossier 08 C.8); the euro series starts 2000-01-03.", "Publicación de la Junta bajo su declaración de dominio público (dossier 08 C.8); la serie del euro comienza el 2000-01-03.")}]},
        "provenance": provenance, "lane": {"lane": "precompute", "reasons": []}}


def finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)
