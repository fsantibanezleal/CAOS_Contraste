"""Experiment 5 (ablation): what each verification layer contributes, measured by planting defects in the engine.

Five layers are run on the engine as released (no layer may fail: the false-alarm check) and on each of twelve mutants, defects
planted by replacing one engine function at run time with a wrapped version that is wrong in a stated way.  A layer detects a
mutant when at least one of its checks fails.  Layers: A analytic anchors, B published vectors and the ECB specification
transcription, C regeneration of the committed seeded rung, D the estimator against a simulator with a known truth, E
cross-implementation (independent Monte Carlo, independent Panjer recursion, QuantLib present value, independent shock shapes).

    python manuscripts/engines-and-test-catalogues/experiments/run_ablation.py
"""
from __future__ import annotations

import dataclasses
import gc
import json
import math
import pathlib
import argparse
import sys
import time

import numpy as np
from scipy import integrate, stats

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import run_ecb as ecb  # noqa: E402
import run_irrbb as irr  # noqa: E402
import run_portfolio as prt  # noqa: E402
import runstats  # noqa: E402

from riskvalidation.engines import vasicek
from riskvalidation.irrbb import eve_nii, shocks, slotting
from riskvalidation.portfolio import asrf_fit, copula, creditrisk_plus as cr, granularity as gr
from riskvalidation.portfolio import portfolio as pf
from riskvalidation.regulatory.irb import capital_requirement
from riskvalidation.validation import calibration as rv_cal
from riskvalidation.validation import rating_system as rv_rs

SEED = 20261107
CI = prt.read("C10", "commercial-industrial")
CARDS = prt.read("C10", "credit-cards")
BOOK = CI["outputs"]["portfolio"]
RUNGS = {r["id"]: r for r in CI["outputs"]["rungs"]}
ONE = pf.portfolio_from_groups(BOOK["groups"], BOOK["currency"], BOOK["lgd_gamma"], one_factor=True)
FIT = CI["outputs"]["fit"]["maximum_likelihood"]
PD_HAT, RHO_HAT = FIT["pd"]["estimate"], FIT["rho"]["estimate"]


def crp_input():
    crp = RUNGS["c4-creditrisk-plus"]
    sigma2 = next(p["value"] for p in crp["parameters"] if p["name"] == "sigma2")
    unit = next(p["value"] for p in crp["parameters"] if p["name"] == "loss_unit")
    n_max = int(next(d["value"] for d in crp["diagnostics"] if d["name"] == "n_max"))
    ead = np.concatenate([np.full(g["n_names"], g["ead_each"]) for g in BOOK["groups"]])
    pds = np.concatenate([np.full(g["n_names"], g["pd"]) for g in BOOK["groups"]])
    units = np.rint(ead * BOOK["lgd_mean"] / unit).astype(int)
    inp = cr.CreditRiskPlusInput(nu=units, pd=pds, w0=np.zeros(ead.size), weights=np.ones((ead.size, 1)),
                                 sigma2=np.array([sigma2]), loss_unit=unit, currency=BOOK["currency"])
    return inp, units, pds, sigma2, n_max


# ------------------------------------------------------------------------------------------------------------- layers
def layer_a() -> list[bool]:
    ok = []
    pts = np.array([0.002, 0.01, 0.035, 0.07])
    areas = [integrate.quad(lambda t: float(vasicek.lhp_pdf(t, PD_HAT, RHO_HAT)), 0, x, limit=200)[0] for x in pts]
    ok.append(max(abs(a - float(vasicek.lhp_cdf(x, PD_HAT, RHO_HAT))) for a, x in zip(areas, pts)) < 1e-9)
    pd_c = CARDS["outputs"]["fit"]["maximum_likelihood"]["pd"]["estimate"]
    corr = CARDS["outputs"]["irb_reference"]["irb_correlation"]
    thr = (stats.norm.ppf(pd_c) + math.sqrt(corr) * stats.norm.ppf(0.999)) / math.sqrt(1 - corr)
    k = 0.45 * (stats.norm.cdf(thr) - pd_c)
    ok.append(abs(float(capital_requirement("qrre", pd_c, 0.45, regime="basel3").k) - k) < 1e-12)
    ok.append(abs(pf.lhp_measures(1.0, 0.45, pd_c, corr, (0.999,))[0].ec - k) < 1e-12)
    inp, units, pds, s2, n_max = crp_input()
    pmf = cr.pmf_stable(inp, n_max)
    n = np.arange(pmf.size)
    mean = float((n * pmf).sum())
    var = float(((n - mean) ** 2 * pmf).sum())
    mean_c = float((units * pds).sum())
    var_c = float((units ** 2 * pds).sum() + s2 * mean_c ** 2)
    ok.append(abs(pmf[0] - (1 + s2 * pds.sum()) ** (-1 / s2)) < 1e-10 and abs(mean - mean_c) / mean_c < 1e-8
              and abs(var - var_c) / var_c < 1e-8)
    gran = CI["outputs"]["granularity"]
    kn = float(capital_requirement("corporate", PD_HAT, 0.45, regime="basel3", maturity=2.5).k)
    prods = []
    for nn in (10, 1000):
        o = np.ones(nn)
        prods.append(gr.granularity_adjustment(o / nn, kn * o, PD_HAT * o, 0.45 * o, gran["gamma"], gran["xi"], 0.999).ga * nn)
    ok.append((max(prods) - min(prods)) / max(prods) < 1e-9)
    return ok


def layer_b() -> list[bool]:
    ok = []
    ok.append(round(gr.delta(0.25, 0.999), 2) == 4.83)
    t = np.array([3.5])
    ok.append(abs(float(shocks.shock_scalars(t, 4.0)[0][0]) - 0.417) <= 5e-4)
    for sh, printed in (("short-up", 41.7), ("steepener", 25.4), ("flattener", -1.6)):
        ok.append(abs(float(shocks.shock_curve(sh, 100, 100, 100, t)[0]) - printed) <= 5e-2)
    rng = np.random.default_rng(SEED)
    d_j, d_h, d_m = [], [], []
    for _ in range(30):
        n = int(rng.integers(50, 5000))
        pd = float(rng.uniform(0.005, 0.2))
        d = int(rng.binomial(n, pd * 1.3))
        d_j.append(abs(rv_cal.pd_jeffreys(n, d, pd).p_value - ecb.spec_jeffreys(n, d, pd)))
        k = int(rng.integers(3, 10))
        cur, ini = rng.dirichlet(np.ones(k) * 2) * 1000, rng.dirichlet(np.ones(k) * 2) * 1000
        r = rv_rs.rating_hhi(cur, ini)
        d_h.append(abs(r.p_value - ecb.spec_hhi(cur.tolist(), ini.tolist())[1]))
    ok.append(max(d_j) < 1e-8)
    ok.append(max(d_h) < 1e-9)
    return ok


def layer_c() -> list[bool]:
    sim = RUNGS["c2-gaussian-1f"]["simulation"]
    sample = copula.simulate_gaussian(ONE, sim["n_scenarios"], sim["seed"], sim["chunk_size"])
    rerun = pf.measures_from_sample(sample.losses, (0.99, 0.999), pf.expected_loss(ONE))
    rel = []
    for m, c in zip(rerun, RUNGS["c2-gaussian-1f"]["measures"]):
        rel.extend(abs(a - b) / b for a, b in ((m.var, c["var"]), (m.es, c["es"]), (m.var_se, c["var_se"]), (m.es_se, c["es_se"])))
    return [max(rel) < 1e-8]


def layer_d() -> list[bool]:
    rng = np.random.default_rng(SEED + 1)
    cov, est = [], []
    for _ in range(150):
        x = np.asarray(vasicek.conditional_pd(0.02, 0.12, rng.standard_normal(22)))
        est.append(asrf_fit.fit_ml(x).rho)
        lo, hi = asrf_fit.profile_interval(x, 0.95)["rho"]
        cov.append(lo <= 0.12 <= hi)
    p = float(np.mean(cov))
    half = 1.96 * math.sqrt(0.95 * 0.05 / 150)
    return [abs(p - 0.95) <= half + 0.02 and abs(np.mean(est) - 0.12) / 0.12 < 0.25]


def layer_e() -> list[bool]:
    ok = []
    m = [], []
    for r in range(3):
        a = pf.var_from_sample(copula.simulate_gaussian(ONE, 40_000, 5000 + r, 16741).losses, 0.99)
        b = pf.var_from_sample(prt.independent_mc(BOOK, RUNGS["c2-gaussian-1f"]["parameters"][0]["value"], 40_000, 6000 + r), 0.99)
        m[0].append(a)
        m[1].append(b)
    se = math.sqrt(np.var(m[0], ddof=1) / 3 + np.var(m[1], ddof=1) / 3)
    ok.append(abs(np.mean(m[0]) - np.mean(m[1])) < 4 * se)
    inp, units, pds, s2, n_max = crp_input()
    mu_j = np.bincount(units, weights=pds)
    jmax = mu_j.size - 1
    c = 1 + s2 * pds.sum()
    g = np.zeros(400)
    g[0] = c ** (-1 / s2)
    js = np.arange(1, jmax + 1)
    for q in range(1, 400):
        top = min(q, jmax)
        jj = js[:top]
        g[q] = np.sum(mu_j[jj] * (s2 * (q - jj) + jj) * g[q - jj]) / (c * q)
    ok.append(float(np.abs(g - cr.pmf_stable(inp, 399)[:400]).max()) < 1e-9)
    doc = json.loads((ROOT / "data" / "derived" / "C15" / "long-uf.json").read_text(encoding="utf-8"))["outputs"]
    mid = slotting.bucket_grid().midpoints
    base = np.asarray(doc["curves"]["clp"]["zero_rates_at_midpoints"], float)
    rel, shp = [], []
    sz = doc["eve_shock_sizes"][0]
    for r in doc["eve"]["rows"]:
        d = r["clp"]
        rates = base + np.asarray(d["shape_bp"]) / 1e4
        q = irr.ql_eve(np.asarray(d["net_cash_flows"]), rates, mid)
        rel.append(abs(eve_nii.eve(np.asarray(d["net_cash_flows"]), rates, mid) - q) / max(abs(q), 1.0))
        spec = np.array([irr.spec_shape(r["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"], float(t)) for t in mid])
        shp.append(float(np.abs(shocks.shock_curve(r["shock"], sz["parallel_bp"], sz["short_bp"], sz["long_bp"], mid) - spec).max()))
    ok.append(max(rel) < 1e-9)
    ok.append(max(shp) < 1e-9)
    return ok


LAYERS = {"A": ("analytic anchors", layer_a), "B": ("published vectors and ECB transcription", layer_b),
          "C": ("regeneration of the committed rung", layer_c), "D": ("known-truth simulator", layer_d),
          "E": ("cross-implementation", layer_e)}


# ------------------------------------------------------------------------------------------------------------ mutants
def mutants():
    orig = {"delta": gr.delta, "cdf": vasicek.lhp_cdf, "sim": copula.simulate_gaussian, "pmf": cr.pmf_stable,
            "jef": rv_cal.pd_jeffreys, "hhi": rv_rs.rating_hhi, "curve": shocks.shock_curve, "eve": eve_nii.eve,
            "fit": asrf_fit.fit_ml, "lhp": pf.lhp_measures, "ql": None}

    def scaled_loadings(p, f):
        return dataclasses.replace(p, loadings=p.loadings * f)

    def jeff_prior(n, d, pd, **kw):
        r = orig["jef"](n, d, pd, **kw)
        return dataclasses.replace(r, p_value=float(stats.beta.cdf(pd, d + 1.0, n - d + 1.0)))

    def hhi_k(cur, ini, **kw):
        r = orig["hhi"](cur, ini, **kw)
        k = len(cur)
        c, i0 = r.extras["cv_current"], r.extras["cv_initial"]
        s = math.sqrt(k) * (c - i0) / math.sqrt(c ** 2 * (0.5 + c ** 2))
        return dataclasses.replace(r, statistic=s, p_value=float(stats.norm.sf(s)))

    def curve_flat(shock, par, short, long_, mid, x=4.0):
        if shock == "flattener":
            a_s, a_l = shocks.shock_scalars(mid, x)
            return 0.8 * short * a_s - 0.65 * long_ * a_l
        return orig["curve"](shock, par, short, long_, mid, x)

    def pmf_shift(inp, n_max):
        p = orig["pmf"](inp, n_max)
        return np.concatenate([[0.0], p[:-1]])

    def lhp_scaled(*a, **k):
        res = orig["lhp"](*a, **k)
        return tuple(dataclasses.replace(r, ec=r.ec * 1.01) for r in res)

    def fit_low(x):
        f = orig["fit"](x)
        return dataclasses.replace(f, rho=f.rho * 0.7)

    def eve_discrete(cf, rates, mid):
        cf, rates, mid = (np.asarray(v, float) for v in (cf, rates, mid))
        return float(np.sum(cf * (1.0 + rates) ** (-mid)))

    # (id, description, equivalent, apply, restore)
    def patch(mod, name, fn):
        return lambda: setattr(mod, name, fn)

    def unpatch(mod, name, f):
        return lambda: setattr(mod, name, f)

    spec = [
        ("m01", "granularity delta scaled by 1.02", False, (gr, "delta", lambda xi, q: orig["delta"](xi, q) * 1.02), (gr, "delta", orig["delta"])),
        ("m02", "large-portfolio distribution function with the correlation scaled by 1.05", False,
         (vasicek, "lhp_cdf", lambda x, pd, rho: orig["cdf"](x, pd, rho * 1.05)), (vasicek, "lhp_cdf", orig["cdf"])),
        ("m03", "copula sampler drawn with the next seed (statistically equivalent)", True,
         (copula, "simulate_gaussian", lambda p, n, seed, chunk=100000, track_groups=False: orig["sim"](p, n, seed + 1, chunk, track_groups)),
         (copula, "simulate_gaussian", orig["sim"])),
        ("m04", "copula loadings scaled by 0.97 (correlation 6 percent low)", False,
         (copula, "simulate_gaussian", lambda p, n, seed, chunk=100000, track_groups=False: orig["sim"](scaled_loadings(p, 0.97), n, seed, chunk, track_groups)),
         (copula, "simulate_gaussian", orig["sim"])),
        ("m05", "CreditRisk+ recursion shifted by one loss unit", False, (cr, "pmf_stable", pmf_shift), (cr, "pmf_stable", orig["pmf"])),
        ("m06", "Jeffreys prior Beta(1, 1) in place of Beta(1/2, 1/2)", False, (rv_cal, "pd_jeffreys", jeff_prior), (rv_cal, "pd_jeffreys", orig["jef"])),
        ("m07", "concentration statistic with sqrt(K) in place of sqrt(K-1)", False, (rv_rs, "rating_hhi", hhi_k), (rv_rs, "rating_hhi", orig["hhi"])),
        ("m08", "flattener long coefficient 0.65 in place of 0.60", False, (shocks, "shock_curve", curve_flat), (shocks, "shock_curve", orig["curve"])),
        ("m09", "present value with annual compounding in place of continuous", False, (eve_nii, "eve", eve_discrete), (eve_nii, "eve", orig["eve"])),
        ("m10", "maximum-likelihood correlation scaled by 0.7", False, (asrf_fit, "fit_ml", fit_low), (asrf_fit, "fit_ml", orig["fit"])),
        ("m11", "large-portfolio capital scaled by 1.01", False, (pf, "lhp_measures", lhp_scaled), (pf, "lhp_measures", orig["lhp"])),
        ("m12", "copula sampler ignores the committed chunk size (statistically equivalent)", True,
         (copula, "simulate_gaussian", lambda p, n, seed, chunk=100000, track_groups=False: orig["sim"](p, n, seed, 12345, track_groups)),
         (copula, "simulate_gaussian", orig["sim"])),
    ]
    return spec


class LayerRunError(RuntimeError):
    """A layer failed to run (an exception that is not a failed check), or the released engine was detected.  Never a detection."""


RETRIED: dict[str, str] = {}
"""The exception type of each layer that raised once and passed on its retry in the last ``run_layers`` call (reported, never counted)."""
RAISED: dict[str, str] = {}
"""The exception type of each layer whose run failed in the last ``run_layers`` call; non-empty only just before ``LayerRunError``."""
RETRY_LOG: list[dict] = []
"""Every retry of the whole run: the label of the engine state, the layer and the exception type; written to the results file."""


def run_layers(layers=None, retries: int = 2, pause: float = 5.0, label: str = "") -> dict[str, bool]:
    """Run every layer; a layer detects a defect only when its checks report it (``not all(checks)``).

    Any exception is a failed run, not a finding: the layer is retried ``retries`` times after ``pause`` seconds and a garbage
    collection (a ``MemoryError`` is a state of the machine, not a property of the planted defect); when it persists the run stops
    with ``LayerRunError`` and no result is written.
    """
    layers = LAYERS if layers is None else layers
    out = {}
    RAISED.clear()
    RETRIED.clear()
    for k, (_, fn) in layers.items():
        for attempt in range(retries + 1):
            try:
                out[k] = not all(fn())  # True: a check failed, the layer detects
                break
            except Exception as exc:  # not a detection: a failed run
                name = type(exc).__name__
                gc.collect()
                if attempt == retries:
                    RAISED[k] = name
                    raise LayerRunError(f"{label or 'engine'}: layer {k} raised {name} on {retries + 1} attempts: {exc}") from exc
                RETRIED[k] = name
                RETRY_LOG.append({"state": label, "layer": k, "exception": name})
                time.sleep(pause)
    return out


def require_clean(label: str, det: dict[str, bool]) -> None:
    """The released engine must be detected by no layer (the false-alarm check); a detection there is an error of the run."""
    if any(det.values()):
        raise LayerRunError(f"{label}: layers flagged the released engine: {det}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "results_ablation.json"), help="results file (default: the committed one)")
    out_path = pathlib.Path(ap.parse_args().out)
    t0 = time.time()
    base = run_layers(label="baseline")
    require_clean("baseline", base)
    print("baseline detections (must all be False):", base, f"{time.time() - t0:.0f}s")
    rows = []
    for mid, desc, equiv, (mod, name, fn), (rmod, rname, rfn) in mutants():
        setattr(mod, name, fn)
        try:
            det = run_layers(label=mid)
        finally:
            setattr(rmod, rname, rfn)
        rows.append({"id": mid, "defect": desc, "equivalent": equiv, "detected_by": det, "retried": dict(RETRIED)})
        print(mid, det, f"{time.time() - t0:.0f}s", flush=True)
    after = run_layers(label="after restore")
    require_clean("after restore", after)
    result = {"baseline_false_alarms": base, "after_restore": after, "layers": {k: v[0] for k, v in LAYERS.items()},
              "mutants": rows, "seed": SEED, "retries": RETRY_LOG, "run": runstats.stats(t0)}
    out_path.write_text(json.dumps(result, indent=1), encoding="utf-8", newline="\n")
    print("after restore:", after)


if __name__ == "__main__":
    main()
