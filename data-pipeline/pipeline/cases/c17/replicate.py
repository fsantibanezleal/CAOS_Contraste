"""One replication: a simulated loss history, as a bank records it, through the engine's ladder (CT-1705, CT-1709).

``estimate`` draws the history of a seed, removes the losses below the collection threshold, and returns the 99.9 percent capital of
each rung of the ladder (Poisson-lognormal LDA that ignores the threshold, the truncated lognormal LDA, the lognormal body and GPD
tail splice, the single loss approximation with and without the UNVERIFIED mean correction, and the scenario combination by
Bayesian credibility), the four rungs of S-3 of the method tiers plan (the GPD fitted by maximum likelihood, by minimum
Cramer-von Mises distance and by the optimally bias-robust estimator, each through the mean-adjusted single loss approximation, and
the lognormal fitted by Cramer-von Mises as the misspecified control), the tail-index profile, and the standardised approach (loss component, ILM, ORC) with the business
indicator of the synthetic bank. Every number is returned by ``riskvalidation``; a rung the engine refuses (a ValueError, a fit
that did not converge) is NaN with the reason counted, never a placeholder number.
"""
from __future__ import annotations

import functools
from typing import Any

import numpy as np
from riskvalidation.oprisk import aggregate as agg
from riskvalidation.oprisk import distributions as dist
from riskvalidation.oprisk import robust
from riskvalidation.oprisk import scenarios as scen
from riskvalidation.oprisk import sla, sma

from . import aggregation as ga
from . import params as P
from .generator import Recorded, Variant, draw_history, expected_count_above

NAN = float("nan")
RUNGS = ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla", "sla_mean_corrected", "scenario",
         "sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal")
MIN_LOSSES = 20  # fewer recorded losses than this and no rung is fitted: the replication is counted as failed
EXPECTED = (ValueError, FloatingPointError, OverflowError, ZeroDivisionError, np.linalg.LinAlgError)


def bank_business_indicator() -> dict[str, float]:
    """The business indicator of the synthetic bank from its stated three-year components, by the engine's OPE25 functions."""
    b = {k: np.array(v, dtype=float) for k, v in P.BANK.items()}
    ildc = sma.ildc(b["ii"], b["ie"], b["iea"], b["di"])
    sc = sma.service_component(b["ooi"], b["ooe"], b["fi"], b["fe"])
    fc = sma.financial_component(b["pl_tb"], b["pl_bb"])
    bi = sma.business_indicator(ildc, sc, fc)
    return {"ildc_eur": ildc, "sc_eur": sc, "fc_eur": fc, "bi_eur": bi, "bic_eur": sma.bic(bi), "bucket": sma.bic_bucket(bi)}


def scenario_points(v: Variant) -> list[scen.ScenarioPoint]:
    """The expert's scenario points: the true severity quantile of each exceedance frequency, rounded to two significant figures."""
    pts = []
    for s in P.SCENARIOS:
        q = 1.0 - s["frequency"] / v.lambda_per_year
        loss = float(dist.severity_ppf("gpd", v.sev_params, np.array([q]))[0])
        pts.append(scen.ScenarioPoint(s["scenario_id"], s["kind"], float(f"{loss:.2g}"), float(s["frequency"])))
    return pts


def expert_frequency_above_tail(v: Variant) -> float:
    """The expert's frequency of losses above the tail threshold: the true expected count, rounded to two significant figures."""
    return float(f"{expected_count_above(v, P.SPLICE_THRESHOLD_EUR):.2g}")


def scenario_prior(v: Variant, points: list[scen.ScenarioPoint], basis_years: int) -> tuple[scen.GammaPrior, int]:
    """See ``_scenario_prior``; memoised in the process (a pure function of its arguments)."""
    return _scenario_prior(v, tuple(points), int(basis_years))


@functools.lru_cache(maxsize=None)
def _scenario_prior(v: Variant, points: tuple[scen.ScenarioPoint, ...], basis_years: int) -> tuple[scen.GammaPrior, int]:
    """The Gamma prior on the Pareto shape from the scenario points (decisions D4 and D6), and the bootstrap seed used: the first of
    ``PRIOR_SEEDS`` whose refits all lie inside the search bounds of the engine (a refit on a bound is a stated failure, never a
    statistic). The prior is the expert's: it reads no loss of any history."""
    last: Exception | None = None
    for seed in range(P.PRIOR_SEEDS):
        try:
            return scen.gamma_prior_from_scenarios(list(points), P.SPLICE_THRESHOLD_EUR, expert_frequency_above_tail(v), float(basis_years),
                                                   n_bootstrap=P.N_BOOTSTRAP, seed=seed), seed
        except ValueError as exc:
            last = exc
    raise ValueError(f"no bootstrap seed below {P.PRIOR_SEEDS} gave a prior for tail index {v.tail_index}, {basis_years} years: {last}")


def _finite(x: float) -> float:
    return float(x) if np.isfinite(x) and x > 0 else NAN


def guard_rescale(lam: float, lam_full: float) -> float:
    """The rescaled frequency of a truncated fit; a non-finite one is no capital (the engine refuses the rest)."""
    if not np.isfinite(lam_full) or lam_full <= 0:
        raise ValueError(f"the rescaled frequency {lam_full} of the truncated fit is not a finite positive number")
    return lam_full


def _lognormal_truncated(rec: Recorded, lam: float) -> tuple[Any, float]:
    fit = dist.fit_severity("lognormal", rec.amounts, rec.threshold_eur, truncated=True)
    if not fit.converged:
        raise ValueError("the truncated lognormal fit did not converge")
    return fit, guard_rescale(lam, dist.rescale_frequency(lam, "lognormal", fit.params, rec.threshold_eur))


def mean_adjusted_capital(lam: float, law: str, params: tuple[float, ...]) -> float:
    """Rungs 7 to 10: the mean-adjusted single loss approximation of the engine at the case's level (an infinite mean is refused)."""
    return _finite(robust.sla_var_mean_adjusted(lam, law, params, P.LEVEL).var)


def robust_gpd_capital(rec: Recorded, lam: float, method: str) -> float:
    """The GPD above the collection threshold fitted by the engine's minimum Cramer-von Mises distance (``cvm``) or optimally bias-robust
    (``obre``, at ``P.OBRE_EFFICIENCY``) estimator on the recorded losses, then its mean-adjusted single loss approximation."""
    fit = (robust.fit_severity_cvm("gpd", rec.amounts, rec.threshold_eur) if method == "cvm"
           else robust.fit_severity_obre("gpd", rec.amounts, rec.threshold_eur, P.OBRE_EFFICIENCY))
    if not fit.converged:
        raise ValueError(f"the {method} fit did not converge")
    return mean_adjusted_capital(lam, "gpd", (fit.params[0], fit.params[1], rec.threshold_eur))


def robust_lognormal_capital(rec: Recorded, lam: float) -> float:
    """The control that does not match the generator: the lognormal fitted by minimum Cramer-von Mises distance above the threshold, the
    frequency rescaled by the engine, then the mean-adjusted single loss approximation."""
    fit = robust.fit_severity_cvm("lognormal", rec.amounts, rec.threshold_eur)
    if not fit.converged:
        raise ValueError("the lognormal Cramer-von Mises fit did not converge")
    lam_full = guard_rescale(lam, dist.rescale_frequency(lam, "lognormal", fit.params, rec.threshold_eur))
    return mean_adjusted_capital(lam_full, "lognormal", fit.params)


def scenario_capital(rec: Recorded, lam: float, splice: dist.SpliceFit, prior: scen.GammaPrior) -> float:
    """Rung 6: the splice whose GPD tail is replaced by the Bayesian credibility tail (the expert's Gamma prior on the Pareto shape
    updated with the Pareto data above the splice threshold), aggregated by the Panjer recursion."""
    u = splice.splice_threshold
    cred = scen.credibility_pareto(prior, rec.amounts[rec.amounts >= u], u)
    mu, sigma, _, _, _, w = splice.params
    par = (mu, sigma, u, cred.xi, cred.beta, w)
    lam_full = guard_rescale(lam, dist.rescale_frequency(lam, "lognormal-gpd-splice", par, rec.threshold_eur))
    return ga.grid_aggregate("panjer", lam_full, "lognormal-gpd-splice", par)[0]


def lognormal_truncated_capital(rec: Recorded, lam: float) -> tuple[float, float]:
    """Rung 2 by the Panjer recursion, and the relative difference to the Fourier aggregation of the same grid (NaN where the Fourier
    transform of that grid is refused: the Panjer capital stands)."""
    fit, lam_full = _lognormal_truncated(rec, lam)
    q_p = ga.grid_aggregate("panjer", lam_full, "lognormal", fit.params)[0]
    try:
        q_f = ga.grid_aggregate("fft", lam_full, "lognormal", fit.params)[0]
    except ValueError:
        return q_p, NAN
    return q_p, abs(q_p - q_f) / q_p


def estimate(v: Variant, seed: int, years: int, threshold: float, bi: float, prior: scen.GammaPrior | None, mc_years: int) -> dict[str, Any]:
    """The ladder of one replication; NaN where a rung is undefined, ``failed`` when too few losses were recorded to fit any."""
    hist = draw_history(v, seed, years)
    rec = hist.recorded(threshold)
    out: dict[str, Any] = {"failed": 0.0, "n_losses": float(rec.amounts.size), "lam_obs": NAN, "agree": NAN, "lc": NAN, "ilm": NAN, "orc": NAN,
                           "xi": np.full(len(P.STABILITY_MULTIPLES), NAN), "n_exceed": np.full(len(P.STABILITY_MULTIPLES), NAN), "errors": {}}
    for r in RUNGS:
        out[r] = NAN

    def run(name: str, fn):
        try:
            return fn()
        except EXPECTED as exc:
            out["errors"][name] = f"{type(exc).__name__}: {str(exc)[:80]}"
            return None

    res = sma.sma_capital(bi, rec.annual)  # the engine refuses fewer than 5 years; every cell has 5 or 10 (CT-1712)
    if res.basis != "bic-times-ilm":
        raise ValueError(f"cell of {years} years gave the {res.basis} basis: no ILM exists on this history")
    out["lc"], out["ilm"], out["orc"] = res.loss_component, res.ilm, res.orc
    if rec.amounts.size < MIN_LOSSES:
        out["failed"] = 1.0
        return out
    lam = dist.fit_frequency(rec.counts).params[0]
    out["lam_obs"] = lam
    amounts = rec.amounts

    def rung1() -> float:
        fit = dist.fit_severity("lognormal", amounts, threshold, truncated=False)
        sample = agg.simulate_annual_losses("poisson", (lam,), "lognormal", fit.params, mc_years, seed, chunk_years=P.MC_CHUNK_YEARS)
        return _finite(agg.mc_quantile(sample.losses, P.LEVEL)[0])

    q = run("lda_lognormal", rung1)
    out["lda_lognormal"] = NAN if q is None else q
    r2 = run("lda_lognormal_truncated", lambda: lognormal_truncated_capital(rec, lam))
    if r2 is not None:
        out["lda_lognormal_truncated"], out["agree"] = _finite(r2[0]), r2[1]
    splice = run("lda_splice", lambda: dist.fit_splice(amounts, threshold, P.SPLICE_THRESHOLD_EUR))
    if splice is not None:
        def rung3() -> float:
            if not splice.converged:
                raise ValueError("the splice fit did not converge")
            lam_full = guard_rescale(lam, dist.rescale_frequency(lam, "lognormal-gpd-splice", splice.params, threshold))
            return _finite(ga.grid_aggregate("fft", lam_full, "lognormal-gpd-splice", splice.params)[0])
        q = run("lda_splice", rung3)
        out["lda_splice"] = NAN if q is None else q

    def gpd_fit():
        f = dist.fit_severity("gpd", amounts, threshold, truncated=True)
        if not f.converged:
            raise ValueError("the GPD fit did not converge")
        return f

    g = run("sla", gpd_fit)
    if g is not None:
        par = (g.params[0], g.params[1], threshold)
        q = run("sla", lambda: _finite(sla.sla_var(lam, "gpd", par, P.LEVEL)))
        out["sla"] = NAN if q is None else q
        if not v.infinite_mean:  # a tail index of 1 or more: no mean correction is attempted (CT-1711)
            q = run("sla_mean_corrected", lambda: _finite(sla.sla_var_mean_corrected(lam, "gpd", par, P.LEVEL).var))
            out["sla_mean_corrected"] = NAN if q is None else q
        q = run("sla_mean_adjusted", lambda: mean_adjusted_capital(lam, "gpd", par))
        out["sla_mean_adjusted"] = NAN if q is None else q
    for name, method in (("sla_cvm", "cvm"), ("sla_obre", "obre")):
        q = run(name, lambda m=method: robust_gpd_capital(rec, lam, m))
        out[name] = NAN if q is None else q
    q = run("sla_cvm_lognormal", lambda: robust_lognormal_capital(rec, lam))
    out["sla_cvm_lognormal"] = NAN if q is None else q
    prof = run("tail_profile", lambda: dist.tail_index_profile(amounts, threshold * np.array(P.STABILITY_MULTIPLES), min_exceedances=10))
    if prof is not None:
        out["xi"], out["n_exceed"] = np.where(prof.converged, prof.xi, NAN), prof.n_exceedances.astype(float)
    if prior is not None and splice is not None:
        q = run("scenario", lambda: _finite(scenario_capital(rec, lam, splice, prior)))
        out["scenario"] = NAN if q is None else q
    return out
