"""What the experiments of the dependence-band manuscript share: the committed C18 documents, the four marginals rebuilt from the
committed quantile grids, the engine's band on them, and the generators of the planted dependence structures.

Everything numeric is a call of ``riskvalidation`` 1.1.0 (the band, the copula aggregate, the bounds, the Euler contributions, the
consistency tests) or a read of a committed document under ``data/derived/C18``. The only code of this file that is not an engine
call is the sampling of the planted structures that the engine does not sample (the Clayton and the Gumbel copula by the
Marshall-Olkin construction, and the mixture of two regimes), each checked against its closed-form Kendall rank correlation.

Run any experiment from the repository root with ``python``, in the environment of the pipeline requirements.
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from functools import partial
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived" / "C18"
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))

from riskvalidation.aggregation import band as rv_band  # noqa: E402
from riskvalidation.aggregation import bounds as rv_bounds  # noqa: E402
from riskvalidation.aggregation import copulas as rv_cop  # noqa: E402
from riskvalidation.portfolio import portfolio as rv_port  # noqa: E402

LEVEL = 0.999
HORIZON = 1
COMMITTED_SEED = 42           # the seed of the committed bake (models-banco-andino.json, fit.aggregation.seed)
N_DRAWS = 1_000_000
CHUNK = 100_000
BOUNDS_N = 100_000
BOUNDS_EPS = 1e-3
EC_TOL = 0.01
RISKS = ("credit", "market", "irrbb", "operational")

SCENARIO_FILES = ("baseline", "eba-2025-adverse", "fed-2026-severely-adverse", "ngfs-delayed-transition")


def read(rel: str) -> Any:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


def write_json(name: str, obj: Any) -> pathlib.Path:
    path = HERE / name
    path.write_text(json.dumps(obj, indent=1, sort_keys=False, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path


def hypotheses() -> dict[str, Any]:
    return json.loads((HERE / "hypotheses.json").read_text(encoding="utf-8"))


def committed_blocks() -> dict[str, dict[str, Any]]:
    """The six committed aggregation blocks by name: four scenario documents, the t-copula document and its stressed block."""
    blocks = {name: read(f"{name}.json")["outputs"]["aggregation"] for name in SCENARIO_FILES}
    second = read("t-copula-baseline.json")["outputs"]
    blocks["t-copula-baseline"] = second["aggregation"]
    blocks["t-copula-baseline, market-credit 0.8"] = second["correlation_stress"]["aggregation"]
    return blocks


class Case:
    """The marginals of Banco Andino rebuilt from the committed grids, with the capital, expected loss, correlation and nu set."""

    def __init__(self) -> None:
        grid = read("models-banco-andino.json")["fit"]["aggregation"]["quantile_grid"]
        agg = read("baseline.json")["outputs"]["aggregation"]
        stress = read("t-copula-baseline.json")["outputs"]["correlation_stress"]
        self.probs = np.array(grid["probabilities"])
        self.quantiles = {q["risk"]: np.array(q["quantiles"]) for q in grid["marginals"]}
        self.ppfs = [partial(np.interp, xp=self.probs, fp=self.quantiles[r]) for r in RISKS]
        by_risk = {m["risk"]: m for m in agg["marginals"]}
        self.marginals = [by_risk[r] for r in RISKS]
        self.ec = np.array([m["ec_clp_m"] for m in self.marginals])
        self.el = np.array([m["el_clp_m"] for m in self.marginals])
        self.var = np.array([m["var_clp_m"] for m in self.marginals])
        self.es = np.array([m["es_clp_m"] for m in self.marginals])
        self.corr = np.array(agg["correlation"]["matrix"])
        self.corr_stress = np.array(stress["aggregation"]["correlation"]["matrix"])
        self.nu_set = [float(v) for v in agg["nu_set"]["values"]]
        self.el_total = float(self.el.sum())
        self.committed_band = agg["band"]
        self.committed_stress_band = stress["aggregation"]["band"]
        self.headline = float(agg["headline"]["capital_clp_m"])

    def band(self, seed: int = COMMITTED_SEED, corr: np.ndarray | None = None, n_draws: int = N_DRAWS,
             ec: np.ndarray | None = None, el: np.ndarray | None = None) -> rv_band.Band:
        return rv_band.dependence_band(
            self.ppfs, self.ec if ec is None else ec, self.el if el is None else el, self.corr if corr is None else corr,
            self.nu_set, level=LEVEL, horizon_years=HORIZON, n_draws=n_draws, seed=seed, chunk_size=min(CHUNK, n_draws),
            bounds_n=min(BOUNDS_N, n_draws), bounds_epsilon=BOUNDS_EPS, ec_consistency_tolerance=EC_TOL)

    def label(self, method: str, nu: float | None) -> str:
        return method if nu is None else f"{method}-nu{nu:g}"


def band_dict(band: rv_band.Band) -> dict[str, dict[str, Any]]:
    return {("t-copula-nu%g" % r.nu if r.nu else r.method): {"capital": r.capital, "df": r.diversification_factor, "se": r.mc_se,
                                                              "status": r.status} for r in band.rows}


# ------------------------------------------------------------------------------------------------ planted structures


def kendall_from_corr(rho: float) -> float:
    return 2.0 / math.pi * math.asin(rho)


def stable_positive(alpha: float, size: int, rng: np.random.Generator) -> np.ndarray:
    """Positive stable variates V with Laplace transform exp(-t^alpha), alpha in (0, 1) (Kanter's representation)."""
    theta = rng.uniform(0.0, math.pi, size)
    w = rng.exponential(1.0, size)
    a = np.sin(alpha * theta) / np.sin(theta) ** (1.0 / alpha)
    b = (np.sin((1.0 - alpha) * theta) / w) ** ((1.0 - alpha) / alpha)
    return a * b


def clayton_survival_uniforms(theta: float, n: int, k: int, seed: int) -> np.ndarray:
    """Exchangeable Clayton copula of parameter theta, reflected (survival copula): upper tail dependence, as a loss tail needs."""
    rng = np.random.Generator(np.random.PCG64(seed))
    v = rng.gamma(1.0 / theta, 1.0, n)
    e = rng.exponential(1.0, (n, k))
    u = (1.0 + e / v[:, None]) ** (-1.0 / theta)
    return np.clip(1.0 - u, 1e-12, 1.0 - 1e-12)


def gumbel_uniforms(theta: float, n: int, k: int, seed: int) -> np.ndarray:
    """Exchangeable Gumbel copula of parameter theta >= 1 (upper tail dependence)."""
    rng = np.random.Generator(np.random.PCG64(seed))
    alpha = 1.0 / theta
    v = stable_positive(alpha, n, rng) if alpha < 1.0 else np.ones(n)
    e = rng.exponential(1.0, (n, k))
    u = np.exp(-((e / v[:, None]) ** alpha))
    return np.clip(u, 1e-12, 1.0 - 1e-12)


def crisis_corr() -> np.ndarray:
    """All three financial risks at 0.8 with each other and 0.4 with operational risk: a matrix beyond the market-credit stress."""
    r = np.full((4, 4), 0.8)
    r[3, :] = r[:, 3] = 0.4
    np.fill_diagonal(r, 1.0)
    return r


def sample_total(case: Case, structure: dict[str, Any], seed: int, n: int) -> np.ndarray:
    """(n, 4) losses under a planted dependence structure with the marginals of the case."""
    kind = structure["kind"]
    if kind in ("gaussian", "t"):
        return rv_cop.simulate_component_losses(case.ppfs, np.array(structure["corr"]), kind, structure.get("nu"), n, seed, min(CHUNK, n))
    if kind == "mixture":
        base = rv_cop.simulate_copula_uniforms(np.array(structure["corr"]), "gaussian", None, n, seed)
        crisis = rv_cop.simulate_copula_uniforms(np.array(structure["corr_crisis"]), "gaussian", None, n, seed + 7919)
        pick = np.random.Generator(np.random.PCG64(seed + 104729)).random(n) < structure["share"]
        u = np.where(pick[:, None], crisis, base)
    elif kind == "clayton-survival":
        u = clayton_survival_uniforms(structure["theta"], n, 4, seed)
    elif kind == "gumbel":
        u = gumbel_uniforms(structure["theta"], n, 4, seed)
    else:
        raise ValueError(kind)
    return np.column_stack([case.ppfs[j](u[:, j]) for j in range(4)])


def structures(case: Case) -> list[dict[str, Any]]:
    """The ten planted structures, in the order of the manuscript table."""
    tau_bar = float(np.mean([kendall_from_corr(case.corr[i, j]) for i in range(4) for j in range(i + 1, 4)]))
    return [
        {"id": "gaussian-base", "kind": "gaussian", "corr": case.corr.tolist(), "family": "in the band", "label": "Gaussian, base matrix"},
        {"id": "gaussian-stress", "kind": "gaussian", "corr": case.corr_stress.tolist(), "family": "in the band", "label": "Gaussian, market-credit 0.8"},
        {"id": "gaussian-crisis", "kind": "gaussian", "corr": crisis_corr().tolist(), "family": "matrix outside the band", "label": "Gaussian, crisis matrix"},
        {"id": "gaussian-independent", "kind": "gaussian", "corr": np.eye(4).tolist(), "family": "matrix outside the band", "label": "Gaussian, independent risks"},
        {"id": "t3-base", "kind": "t", "nu": 3.0, "corr": case.corr.tolist(), "family": "degrees outside the set", "label": "t copula, 3 degrees, base matrix"},
        {"id": "t25-base", "kind": "t", "nu": 2.5, "corr": case.corr.tolist(), "family": "degrees outside the set", "label": "t copula, 2.5 degrees, base matrix"},
        {"id": "t3-crisis", "kind": "t", "nu": 3.0, "corr": crisis_corr().tolist(), "family": "degrees and matrix outside", "label": "t copula, 3 degrees, crisis matrix"},
        {"id": "regime-mixture", "kind": "mixture", "corr": case.corr.tolist(), "corr_crisis": crisis_corr().tolist(), "share": 0.05,
         "family": "family outside the band", "label": "Gaussian regimes, 5 percent crisis"},
        {"id": "clayton-survival", "kind": "clayton-survival", "theta": 2.0 * tau_bar / (1.0 - tau_bar), "family": "family outside the band",
         "label": "Clayton, reflected, same mean tau"},
        {"id": "gumbel", "kind": "gumbel", "theta": 1.0 / (1.0 - tau_bar), "family": "family outside the band", "label": "Gumbel, same mean tau"},
    ]


def capital_of_total(total: np.ndarray, el_total: float) -> tuple[float, float, float]:
    """EC = VaR - EL, its batch-means standard error and the expected shortfall of a loss sample through the engine."""
    m = rv_port.measures_from_sample(total, [LEVEL], el_total)[0]
    return float(m.ec), float(m.var_se) if m.var_se is not None else float("nan"), float(m.es)


def self_checks() -> dict[str, Any]:
    """The generators not in the engine, against their closed forms: Laplace transform of the stable law, Kendall's tau of both copulas."""
    from scipy import stats

    rng = np.random.Generator(np.random.PCG64(5))
    alpha = 0.6
    v = stable_positive(alpha, 400_000, rng)
    lap = {t: (float(np.mean(np.exp(-t * v))), math.exp(-(t ** alpha))) for t in (0.5, 1.0, 2.0)}
    theta_c, theta_g = 2.0, 1.0 / (1.0 - 0.4)
    uc = clayton_survival_uniforms(theta_c, 200_000, 2, 11)
    ug = gumbel_uniforms(theta_g, 200_000, 2, 12)
    tau_c = float(stats.kendalltau(uc[:50_000, 0], uc[:50_000, 1]).statistic)
    tau_g = float(stats.kendalltau(ug[:50_000, 0], ug[:50_000, 1]).statistic)
    return {"stable_laplace": {str(t): {"simulated": a, "closed_form": b} for t, (a, b) in lap.items()},
            "clayton": {"theta": theta_c, "tau_simulated": tau_c, "tau_closed_form": theta_c / (theta_c + 2.0)},
            "gumbel": {"theta": theta_g, "tau_simulated": tau_g, "tau_closed_form": 1.0 - 1.0 / theta_g}}


__all__ = ["Case", "rv_band", "rv_bounds", "rv_cop", "rv_port"]
