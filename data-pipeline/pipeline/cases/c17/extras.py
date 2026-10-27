"""The single-history blocks of a variant document and the benchmark row, each from the engine's functions.

- ``benchmark_row``: Shevchenko's Poisson(100) / LN(0, 2) benchmark through the Monte Carlo, Panjer and Fourier aggregation
  (``validation.oprisk.benchmark_reproduction``); one engine check of the three aggregation methods, the same in every document.
- ``sma_response``: one large loss added to the latest year of a history, the loss component, ILM and ORC of the standardised
  approach and the single loss approximation capital of the same history (``validation.oprisk.sma_ilm_response``).
- ``scenario_influence``: the sensitivity of the scenario rung's capital to each scenario point (``scenarios.scenario_influence``,
  ``validation.oprisk.scenario_influence``).
"""
from __future__ import annotations

from typing import Any

import numpy as np
from riskvalidation.oprisk import aggregate as agg
from riskvalidation.oprisk import distributions as dist
from riskvalidation.oprisk import scenarios as scen
from riskvalidation.oprisk import sla, sma
from riskvalidation.validation import oprisk as val

from . import params as P
from .documents import _row, cell_id
from .generator import Variant, draw_history
from .replicate import EXPECTED, scenario_capital, scenario_prior

BENCH_YEARS = 1_000_000
BENCH_SEED = 2010
_BENCH: dict[str, Any] = {}


def benchmark_row() -> dict[str, Any]:
    """The reproduction of Shevchenko's benchmark by the three aggregation methods, as a test row (computed once per process)."""
    if "row" not in _BENCH:
        mom = agg.compound_poisson_moments(100.0, "lognormal", (0.0, 2.0))
        f = agg.discretise_severity("lognormal", (0.0, 2.0), 1.0, 6000)
        q_p = agg.quantile_from_pmf(agg.panjer_recursion("poisson", (100.0,), f), 1.0, P.LEVEL)
        q_f = agg.quantile_from_pmf(agg.fft_aggregate("poisson", (100.0,), f), 1.0, P.LEVEL)
        s = agg.simulate_annual_losses("poisson", (100.0,), "lognormal", (0.0, 2.0), BENCH_YEARS, BENCH_SEED, chunk_years=P.MC_CHUNK_YEARS)
        q_mc = agg.mc_quantile(s.losses, P.LEVEL)[0]
        _BENCH["row"] = _row(val.benchmark_reproduction((mom.mean, mom.variance, mom.skewness),
                                                        {"monte-carlo": q_mc, "panjer": q_p, "fft": q_f}, moment_rel_tol=1e-5))
    return dict(_BENCH["row"])


def _sla_capital(amounts: np.ndarray, counts: np.ndarray, threshold: float) -> float:
    """The single loss approximation capital of a history: the truncated GPD fit above the threshold and the recorded frequency."""
    lam = dist.fit_frequency(counts).params[0]
    fit = dist.fit_severity("gpd", amounts, threshold, truncated=True)
    if not fit.converged:
        raise ValueError("the GPD fit did not converge")
    return sla.sla_var(lam, "gpd", (fit.params[0], fit.params[1], threshold), P.LEVEL)


def sma_response(v: Variant, seed: int, years: int, threshold: float, bank: dict[str, Any]) -> dict[str, Any]:
    rec = draw_history(v, seed, years).recorded(threshold)
    bic, bi = bank["bic_eur"], bank["bi_eur"]
    rows = []
    for mult in P.RESPONSE_MULTIPLES:
        added = mult * bic
        annual = rec.annual.copy()
        annual[-1] += added
        r = sma.sma_capital(bi, annual)
        amounts, counts = rec.amounts, rec.counts.copy()
        if added > 0:
            amounts, counts[-1] = np.append(amounts, added), counts[-1] + 1
        rows.append({"added_loss_eur": added, "lc_eur": r.loss_component, "ilm": r.ilm, "orc_eur": r.orc,
                     "lda_capital_eur": _sla_capital(amounts, counts, threshold)})
    test = _row(val.sma_ilm_response(bic, rec.annual, 0.5 * bic, model_id="sma"), cell_id(years, threshold))
    return {"block": {"currency": P.CURRENCY, "cell_id": cell_id(years, threshold), "seed": int(seed), "bic_eur": bic, "rows": rows}, "test": test}


def scenario_influence(v: Variant, seed_first: int, years: int, threshold: float, points: list[scen.ScenarioPoint], tries: int = 25) -> dict[str, Any]:
    """The influence of each scenario point on the scenario rung's capital, on the first history of the cell where the rung is defined.

    The capital without a point re-derives the expert's prior from the remaining points (the prior is the expert's, so it moves with
    them) and updates it with the history's Pareto tail."""
    last: Exception | None = None
    for seed in range(seed_first, seed_first + tries):
        rec = draw_history(v, seed, years).recorded(threshold)
        cache: dict[tuple[str, ...], float] = {}
        try:
            lam = dist.fit_frequency(rec.counts).params[0]
            splice = dist.fit_splice(rec.amounts, threshold, P.SPLICE_THRESHOLD_EUR)

            def capital(pts):
                key = tuple(p.scenario_id for p in pts)
                if key not in cache:
                    cache[key] = scenario_capital(rec, lam, splice, scenario_prior(v, list(pts), years)[0])
                return cache[key]

            infl = scen.scenario_influence(points, capital)
        except EXPECTED as exc:
            last = exc
            continue
        ids = [p.scenario_id for p in points]
        base = cache[tuple(ids)]
        spec = {s["scenario_id"]: s for s in P.SCENARIOS}
        scenarios = [{"scenario_id": p.scenario_id, "label": spec[p.scenario_id]["label"], "kind": p.kind, "loss_eur": p.loss,
                      "exceedance_frequency_per_year": p.exceedance_frequency,
                      "capital_without_eur": cache[tuple(i for i in ids if i != p.scenario_id)], "influence": float(x)}
                     for p, x in zip(points, infl)]
        block = {"prior_kind": "unrestricted-gamma-on-pareto-shape", "currency": P.CURRENCY, "cell_id": cell_id(years, threshold), "seed": int(seed),
                 "level": P.LEVEL, "method": "bayesian-credibility", "base_capital_eur": base, "scenarios": scenarios,
                 "reference": "Shevchenko and Wüthrich (2006), J. Operational Risk 1(3):3-26"}
        return {"block": block, "test": _row(val.scenario_influence(np.asarray(infl), model_id="scenario"), cell_id(years, threshold))}
    raise ValueError(f"the scenario rung was undefined on {tries} histories of the cell: {last}")
