"""C05, low-default portfolios and PD calibration (U2).

The design is docs/design/features/c05-ldp-calibration/design.md; requirements CT-201 to CT-211 hold it. Inputs: the
arXiv PDFs of Tasche (2013) and Pluto and Tasche (2005), both derived-only, read from the device data root by
``pipeline.io.papers``; a seeded Vasicek generator for the known-truth variants. Every computation is
``riskvalidation`` 0.2.0 (``engines.pd_curve``, ``engines.low_default``, ``regulatory.irb``, the calibration tests).
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats
from scipy.special import ndtr, ndtri

from riskvalidation.engines import low_default as ldp
from riskvalidation.engines import pd_curve as pc
from riskvalidation.regulatory import capital_requirement
from riskvalidation.validation.calibration import (
    default_count_sf,
    pd_binomial,
    pd_binomial_vasicek,
    pd_chi2_grades,
    pd_default_profile,
    pd_jeffreys_grades,
)

from .. import __version__
from ..core import expect as expectations
from ..core import lineage as lin
from ..core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ..io import papers
from ..io.formats import write_json
from ..stages.export import write_artifact
from .c01_ladder import _t, _v

CASE_ID = "C05"
SOURCES = ("tasche-2013", "pluto-tasche-2005")
GENERATOR = "vasicek-ldp"
TASCHE_PDF = "tasche-2013-arxiv-1212.3716v6.pdf"
PLUTO_PDF = "pluto-tasche-arxiv-cond-mat-0411699v3.pdf"
ENGINES = {"numpy", "scipy", "riskvalidation", "pypdf"}
#: the bake of a variant (Monte Carlo default-profile tests, 20,000 generated years) runs seconds, above the
#: interaction budget: the artifacts are replayed; the web recomputes the calculators from committed inputs
RUN_MS = 30_000.0

#: the capital the impact computes: Basel III final, corporate, F-IRB senior unsecured LGD for financial
#: institutions (CRE32.6; the S&P universe includes them), the F-IRB maturity
REGIME, ASSET, LGD, MATURITY = "basel3", "corporate", 0.45, 2.5
N_SIM_PROFILE, SEED_PROFILE = 100_000, 2013

LDP_GRADES = ("A", "B", "C")
LDP_N = (100, 400, 300)                 # Pluto and Tasche (2005), example (2.3)
LDP_PUBLISHED_D = (0, 2, 1)             # their few-defaults example (section 3)
EXPERT_PD = (0.0003, 0.0005, 0.0010)    # a hypothetical expert model, below the generator's truth
TRUE_PD = (0.0005, 0.0010, 0.0020)      # the generator's truth
RHO = 0.12                              # the Basel minimum corporate correlation the paper uses
GAMMAS = (0.50, 0.75, 0.90, 0.95, 0.99, 0.999)
N_YEARS, SEED_YEARS = 20_000, 2005
MULTI = {"rho": 0.12, "theta": 0.3, "years": 5, "n_sim": 100_000, "seed": 5}

APPROACHES: tuple[dict[str, Any], ...] = (
    {"id": "A1-idp", "case": 1, "eq": "4.2", "title": _t("Invariant default profile", "Perfil de incumplimiento invariante"),
     "short": _t("Default profile", "Perfil de incumpl.")},
    {"id": "A2-iar", "case": 1, "eq": "4.3", "title": _t("Invariant accuracy ratio", "Razón de precisión invariante"),
     "short": _t("Accuracy ratio", "Razón de precisión")},
    {"id": "A3-spd", "case": 1, "eq": "4.4", "title": _t("Scaled PDs", "PD escaladas"), "short": _t("Scaled PDs", "PD escaladas")},
    {"id": "A4-slr", "case": 1, "eq": "4.5", "title": _t("Scaled likelihood ratio", "Razón de verosimilitud escalada"),
     "short": _t("Scaled LR", "RV escalada")},
    {"id": "B1-ilr", "case": 2, "eq": "4.11", "title": _t("Invariant likelihood ratio (PD known)", "Razón de verosimilitud invariante (PD conocida)"),
     "short": _t("Invariant LR", "RV invariante")},
    {"id": "C1-ipc", "case": 3, "eq": "4.12", "title": _t("Invariant PD curve (the 2009 curve unchanged)", "Curva de PD invariante (la curva de 2009 sin cambios)"),
     "short": _t("2009 curve", "Curva 2009")},
    {"id": "C2-ls", "case": 3, "eq": "4.14b", "title": _t("Invariant conditional profiles, least squares", "Perfiles condicionales invariantes, mínimos cuadrados"),
     "short": _t("Least squares", "Mín. cuadrados")},
    {"id": "C3-chi2", "case": 3, "eq": "4.9", "title": _t("Invariant conditional profiles, least chi-square", "Perfiles condicionales invariantes, mínimo chi-cuadrado"),
     "short": _t("Least chi-square", "Mín. chi-cuadrado")},
    {"id": "C4-ilr", "case": 3, "eq": "4.10", "title": _t("Invariant likelihood ratio (profile known)", "Razón de verosimilitud invariante (perfil conocido)"),
     "short": _t("LR, profile", "RV, perfil")},
)
CASE1 = tuple(a["id"] for a in APPROACHES if a["case"] == 1)

VARIANTS: tuple[dict[str, Any], ...] = (
    {"id": "sp-2010", "kind": "sp", "year": 2010, "truth": "published-answer",
     "title": _t("S&P corporates, 2009 curve to 2010", "Corporativos S&P, curva 2009 a 2010"), "short": _t("S&P 2010", "S&P 2010"),
     "regime": _t("The 2009 rating system smoothed by QMM, calibrated to the 2010 profile and default rate by every approach of Tasche (2013).",
                  "El sistema de calificación de 2009 suavizado por QMM, calibrado al perfil y la tasa de incumplimiento de 2010 con cada enfoque de Tasche (2013).")},
    {"id": "sp-2011", "kind": "sp", "year": 2011, "truth": "published-answer",
     "title": _t("S&P corporates, 2009 curve to 2011", "Corporativos S&P, curva 2009 a 2011"), "short": _t("S&P 2011", "S&P 2011"),
     "regime": _t("The same calibration to 2011, a year with fewer defaults.", "La misma calibración a 2011, un año con menos incumplimientos.")},
    {"id": "ldp-published", "kind": "ldp", "defaults": LDP_PUBLISHED_D, "truth": "published-answer",
     "title": _t("Low-default example of Pluto and Tasche", "Ejemplo de bajo incumplimiento de Pluto y Tasche"), "short": _t("Published", "Publicado"),
     "regime": _t("100, 400 and 300 obligors with 0, 2 and 1 defaults; every published bound recomputed.",
                  "100, 400 y 300 deudores con 0, 2 y 1 incumplimientos; cada cota publicada recalculada.")},
    {"id": "ldp-sim-0", "kind": "ldp", "total": 0, "truth": "synthetic-known-truth",
     "title": _t("Generated year without defaults", "Año generado sin incumplimientos"), "short": _t("0 defaults", "0 incumpl."),
     "regime": _t("A year of the Vasicek generator (true PDs 0.05%, 0.10%, 0.20%; correlation 12%) with no default.",
                  "Un año del generador de Vasicek (PD verdaderas 0,05%, 0,10%, 0,20%; correlación 12%) sin incumplimientos.")},
    {"id": "ldp-sim-1", "kind": "ldp", "total": 1, "truth": "synthetic-known-truth",
     "title": _t("Generated year with one default", "Año generado con un incumplimiento"), "short": _t("1 default", "1 incumpl."),
     "regime": _t("A year of the same generator with one default.", "Un año del mismo generador con un incumplimiento.")},
    {"id": "ldp-sim-3", "kind": "ldp", "total": 3, "truth": "synthetic-known-truth",
     "title": _t("Generated year with three defaults", "Año generado con tres incumplimientos"), "short": _t("3 defaults", "3 incumpl."),
     "regime": _t("A year of the same generator with three defaults.", "Un año del mismo generador con tres incumplimientos.")},
)

#: what a reader should see, declared before the bake (CT-207); the bases are in the design page and the engine docs
EXPECT: dict[str, tuple[float, float]] = {
    "qmm_alpha_2009": (5.2047, 5.2049),                    # the exact QMM root on the 2009 counts
    "qmm_beta_2009": (2.1612, 2.1614),
    "c_pd_sp-2010": (0.2641, 0.2643),                      # Tasche Table 7 implies 0.2643 from rounded inputs
    "c_lr_sp-2010": (1.4080, 1.4082),
    "p_profile_A3-spd_sp-2010": (0.030, 0.055),            # Table 7 prints 4.0%; Monte Carlo error at 100,000 draws
    "p_profile_A4-slr_sp-2010": (0.095, 0.130),            # Table 7 prints 11.3%
    "p_profile_A2-iar_sp-2011": (0.87, 0.91),              # Table 7 prints 89.4%
    "forecast_pd_C2-ls_sp-2010": (0.0479, 0.0481),         # Table 8 prints 4.80%
    "forecast_pd_C4-ilr_sp-2011": (0.0279, 0.0280),        # Table 8 prints 2.79%
    "golden_max_gap_table7_pct": (0.0, 0.00011),           # beyond 0.01% of the value: one unit of the fourth decimal
    "bound_A_independent_50_ldp-published": (0.0045, 0.0047),  # Table 4: 0.46%
    "bound_A_correlated_50_ldp-published": (0.0071, 0.0072),   # exact 0.7106% (Table 8 prints 0.72%)
    # at these sizes the zero-default bound already exceeds the truth (grade C at 90%: 1 - 0.1^(1/300) = 0.77% against
    # 0.20%), so every one-year bound covers in every year; its median multiple of the truth is at least 0.77 / 0.20
    "coverage_independent_C_90": (0.9999, 1.0),
    "coverage_correlated_C_90": (0.9999, 1.0),
    "ratio_independent_C_90_median": (3.8, 10.0),
    # scaled to the portfolio bound at 50%, a zero-default year (about 40% of the years) gives grade C 0.14%, below
    # its true 0.20%, so the scaled estimate cannot cover in those years
    "coverage_scaled_C_50": (0.2, 0.7),
    "power_jeffreys_portfolio_expert": (0.0, 0.5),         # the battery has little power against a model at half the truth
    "true_pd_recovered_C": (0.0018, 0.0022),               # the generator recovers its truth (CT-204)
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C05 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def _es(x: float, decimals: int) -> str:
    """A number as the Spanish texts write it: a decimal comma."""
    return f"{x:.{decimals}f}".replace(".", ",")


def _irb_rw(pd: float) -> float:
    """The risk weight (share of EAD) the impact uses, with its PD floor."""
    return capital_requirement(ASSET, float(pd), LGD, maturity=MATURITY, regime=REGIME).risk_weight


IRB_ASSUMPTIONS = {"regime": REGIME, "asset_class": ASSET, "lgd": LGD, "maturity": MATURITY, "pd_floor": 0.0005,
                   "references": {"risk_weight": "CRE31.5", "lgd": "CRE32.6 (F-IRB senior unsecured, financial institutions)",
                                  "maturity": "CRE32.44 (F-IRB effective maturity)", "pd_floor": "CRE32.4"}}


def _strip_counts(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """CT-208: a grade-level row of a derived-only source carries its rate and its result, not its counts."""
    out = []
    for r in rows:
        if r.get("segment") not in (None, "portfolio"):
            r = {**r, "n": None, "n_events": None,
                 "notes": (r.get("notes") or "") + ("; " if r.get("notes") else "") +
                 "grade counts of a derived-only source are not published (CT-208)"}
        out.append(r)
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the S&P variants


@dataclass
class Sp:
    table2: dict[str, Any]
    results: dict[str, Any]
    m0: dict[str, Any]
    q0: dict[str, Any]


def _load_sp(data_root: Path) -> Sp:
    pdf = Path(data_root) / "raw" / "tasche-2013" / TASCHE_PDF
    table2 = papers.read_tasche_table2(pdf)
    results = papers.read_tasche_results(pdf, table2)
    y09 = table2["years"][2009]
    m0 = pc.model_from_counts(y09["rated"], y09["defaults"])
    q0 = pc.qmm(m0["profile"], m0["pd"], m0["accuracy_ratio"], survival_profile=m0["survival_profile"])
    return Sp(table2, results, m0, q0)


def _approaches(sp: Sp, m1: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Every approach's forecast curve and constants for the forecast year's profile and (case 1, 2) its PD."""
    m0, q0 = sp.m0, sp.q0
    c0, p0 = q0["pd_curve"], q0["pd"]
    pi1, p1 = m1["profile"], m1["pd"]
    dp_s, sp_s = pc.implied_default_profile(c0, m0["profile"]), pc.implied_survival_profile(c0, m0["profile"])
    out: dict[str, dict[str, Any]] = {}
    r = pc.invariant_default_profile(m0["default_profile"], pi1, p1)
    out["A1-idp"] = {"curve": r["pd_curve"], "constants": {"alpha": r["alpha"], "beta": r["beta"],
                                                          "accuracy_ratio_target": r["accuracy_ratio_target"]}}
    r = pc.invariant_accuracy_ratio(pi1, p1, m0["accuracy_ratio"])
    out["A2-iar"] = {"curve": r["pd_curve"], "constants": {"alpha": r["alpha"], "beta": r["beta"]}}
    r = pc.scaled_pds(c0, pi1, p1)
    out["A3-spd"] = {"curve": r["pd_curve"], "constants": {"c_pd": r["c_pd"]}}
    r = pc.scaled_likelihood_ratio(c0, p0, pi1, p1)
    out["A4-slr"] = {"curve": r["pd_curve"], "constants": {"c_lr": r["c_lr"], "bracket_low": r["bracket"][0],
                                                          "bracket_high": r["bracket"][1]}}
    r = pc.invariant_likelihood_ratio(c0, p0, pd_1=p1)
    out["B1-ilr"] = {"curve": r["pd_curve"], "constants": {}}
    r = pc.invariant_pd_curve(c0, pi1)
    out["C1-ipc"] = {"curve": r["pd_curve"], "constants": {}}
    for aid, fit in (("C2-ls", "least_squares"), ("C3-chi2", "least_chi2")):
        r = pc.invariant_conditional_profiles(dp_s, sp_s, pi1, fit=fit)
        out[aid] = {"curve": r["pd_curve"], "constants": {}, "pd": r["pd"], "implied_profile": r["profile"]}
    r = pc.invariant_likelihood_ratio(c0, p0, profile_1=pi1)
    out["C4-ilr"] = {"curve": r["pd_curve"], "constants": {}, "pd": r["pd"]}
    for a in out.values():
        # the approach's own forecast of the PD (Tasche Table 8 for case 3; the given PD for cases 1 and 2), and the
        # PD its curve implies under the observed forecast profile (equal to it except for invariant conditional
        # profiles, whose curve (4.16) belongs to the implied profile 4.15)
        a["pd_under_profile1"] = pc.unconditional_pd(a["curve"], pi1)
        a.setdefault("pd", a["pd_under_profile1"])
        a["accuracy_ratio"] = pc.accuracy_ratio_from_curve(a["curve"], pi1)
    return out


def _sp_tests(appr: dict[str, dict[str, Any]], n1: list[int], d1: list[int]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for a in APPROACHES:
        cur = appr[a["id"]]["curve"]
        rows.append(pd_default_profile(n1, d1, cur, n_sim=N_SIM_PROFILE, seed=SEED_PROFILE, model_id=a["id"]).to_dict())
        rows.append(pd_chi2_grades(n1, d1, cur, model_id=a["id"], segment="portfolio").to_dict())
        rows += [r.to_dict() for r in pd_jeffreys_grades(n1, d1, cur, grades=list(papers.SP_GRADES), model_id=a["id"])]
    return _strip_counts(rows)


def _sp_golden(sp: Sp, year: int, appr: dict[str, dict[str, Any]], tests: list[dict[str, Any]]) -> dict[str, Any]:
    """CT-203: every printed cell of Tasche's Tables 5 to 9 that concerns this variant, with the recomputed value and
    the gap, against the engine's documented tolerances (riskvalidation docs/engines/03_pd-curve-calibration.md)."""
    res = sp.results
    curve09 = sp.q0["pd_curve"]
    t5 = [{"grade": g, "printed": p, "ours": round(100 * c, 3), "gap": round(round(100 * c, 3) - p, 4)}
          for g, p, c in zip(papers.SP_GRADES, res["table5"]["smoothed_pd_pct"], curve09, strict=True)]
    implied = pc.implied_default_profile(curve09, sp.m0["profile"])
    t6 = [{"grade": g, "printed": p, "ours": round(100 * v, 4), "gap": round(round(100 * v, 4) - p, 4)}
          for g, p, v in zip(papers.SP_GRADES, res["table6"]["implied_pct"], implied, strict=True)]
    names = {"invariant_default_profile": "A1-idp", "invariant_accuracy_ratio": "A2-iar", "scaled_pds": "A3-spd",
             "scaled_likelihood_ratio": "A4-slr"}
    t7 = {}
    for key, aid in names.items():
        printed = res["table7"][year]["forecast_pct"][key]
        t7[aid] = [{"grade": g, "printed": p, "ours": round(100 * c, 4), "gap": round(round(100 * c, 4) - p, 4)}
                   for g, p, c in zip(papers.SP_GRADES, printed, appr[aid]["curve"], strict=True)]
    p_ours = {r["model_id"]: r for r in tests if r["test_id"] == "pd.default_profile"}
    t7p = [{"approach": aid, "printed_pct": res["table7"][year]["p_value_pct"][key],
            "ours_pct": round(100 * p_ours[aid]["p_value"], 2),
            "mc_se_pct": round(100 * p_ours[aid]["extras"]["mc_standard_error"], 3)} for key, aid in names.items()]
    t8_names = {"invariant_pd_curve": "C1-ipc", "least_squares": "C2-ls", "least_chi2": "C3-chi2",
                "invariant_likelihood_ratio": "C4-ilr"}
    t8 = [{"approach": aid, "printed_pct": res["table8"][key][year]["forecast_pct"],
           "ours_pct": round(100 * appr[aid]["pd"], 3), "printed_p_value": res["table8"][key][year]["p_value"]}
          for key, aid in t8_names.items()]
    lam09 = pc.likelihood_ratio(curve09, sp.q0["pd"])
    t9 = [{"grade": g, "printed": p, "ours": round(v, 2)} for g, p, v in zip(papers.SP_GRADES, res["table9"][2009], lam09, strict=True)]
    gap7 = max(abs(c["gap"]) - 1e-4 * abs(c["printed"]) for cells in t7.values() for c in cells)
    return {"table5": t5, "table6": t6, "table7": t7, "table7_p_values": t7p, "table8": t8, "table9_2009": t9,
            "max_gap_table7_pct_beyond_relative": max(gap7, 0.0),
            "tolerances": {"table5": "one unit of the third decimal", "table6": "one unit of the fourth decimal plus 0.01% of the value",
                           "table7": "one unit of the fourth decimal plus 0.01% of the value",
                           "table7_p_values": "three Monte Carlo standard errors of a 2,000-sample run plus three of this run",
                           "table8": "one unit of the printed precision", "table9": "0.2% (the paper's QMM solver offset)"}}


def _parity_sp(sp: Sp, m1: dict[str, Any]) -> dict[str, Any]:
    """CT-209: the case 1 approaches at a grid of forecast PDs, for the live port to reproduce exactly."""
    grid = [0.002, 0.005, 0.01, round(m1["pd"], 6), 0.02, 0.04]
    out: dict[str, Any] = {"pd_grid": grid, "curves": {}}
    m0, q0 = sp.m0, sp.q0
    for p1 in grid:
        key = f"{p1:.6f}"
        out["curves"][key] = {
            "A1-idp": pc.invariant_default_profile(m0["default_profile"], m1["profile"], p1)["pd_curve"],
            "A2-iar": pc.invariant_accuracy_ratio(m1["profile"], p1, m0["accuracy_ratio"])["pd_curve"],
            "A3-spd": pc.scaled_pds(q0["pd_curve"], m1["profile"], p1)["pd_curve"],
            "A4-slr": pc.scaled_likelihood_ratio(q0["pd_curve"], q0["pd"], m1["profile"], p1)["pd_curve"],
        }
    return out


def _irb_parity() -> list[dict[str, Any]]:
    """CT-209: the IRB risk weight at a grid of PDs, LGDs, maturities and regimes, for the live port."""
    pts = []
    for regime in ("basel3", "crr3", "basel2"):
        for pd in (0.0001, 0.0005, 0.002, 0.01, 0.05, 0.2):
            for lgd, m in ((0.45, 2.5), (0.25, 1.0), (0.75, 5.0)):
                pts.append({"regime": regime, "asset_class": "corporate", "pd": pd, "lgd": lgd, "maturity": m,
                            "risk_weight": capital_requirement("corporate", pd, lgd, maturity=m, regime=regime).risk_weight})
    return pts


def _sp_impact(appr: dict[str, dict[str, Any]], profile1: list[float]) -> dict[str, Any]:
    """CT-206: the average IRB risk weight of the forecast portfolio (one unit of EAD per obligor) under each curve."""
    pi = np.asarray(profile1)
    rw = {aid: float(np.sum(pi * np.array([_irb_rw(p) for p in a["curve"]]))) for aid, a in appr.items()}
    out: dict[str, Any] = {}
    for a in APPROACHES:
        out[f"rw_{a['id']}"] = {"value": rw[a["id"]], "unit": "share of EAD",
                                "label": _t(f"Average risk weight, {a['title']['en']}", f"Ponderador medio, {a['title']['es']}")}
    ref = rw["A4-slr"]
    out["rw_spread_case1"] = {"value": max(rw[a] for a in CASE1) / min(rw[a] for a in CASE1) - 1.0, "unit": "ratio",
                              "label": _t("Spread of the case 1 risk weights (highest over lowest, less one)",
                                          "Dispersión de los ponderadores del caso 1 (mayor sobre menor, menos uno)")}
    out["rw_stale_vs_slr"] = {"value": rw["C1-ipc"] / ref - 1.0, "unit": "ratio",
                              "label": _t("The 2009 curve unchanged against the scaled likelihood ratio",
                                          "La curva de 2009 sin cambios frente a la razón de verosimilitud escalada")}
    return out


def _sp_findings(year: int, tests: list[dict[str, Any]], appr: dict[str, dict[str, Any]], p1: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    byid = {a["id"]: a for a in APPROACHES}
    for aid in CASE1:
        r = next(t for t in tests if t["test_id"] == "pd.default_profile" and t["model_id"] == aid)
        if r["light"] in ("amber", "red"):
            out.append({"id": f"F-PROFILE-{aid}", "severity": "S3" if r["light"] == "amber" else "S2", "status": "open",
                        "evidence": [f"pd.default_profile@{aid}"],
                        "title": _t(f"{byid[aid]['title']['en']}: the {year} defaults fall on the grades unlike the calibrated curve implies (p = {r['p_value']:.3f})",
                                    f"{byid[aid]['title']['es']}: los incumplimientos de {year} se reparten en los grados distinto de lo que implica la curva calibrada (p = {_es(r['p_value'], 3)})")})
    worst = papers.SP_GRADES[-1]
    flagged = [aid for aid in CASE1 if any(t["test_id"] == "pd.jeffreys" and t["model_id"] == aid and t["segment"] == worst
                                           and t["light"] == "red" for t in tests)]
    if flagged:
        out.append({"id": f"F-JEFF-{worst}", "severity": "S2", "status": "open",
                    "evidence": [f"pd.jeffreys@{aid}@{worst}" for aid in flagged],
                    "title": _t(f"{len(flagged)} of the 4 case 1 curves underestimate {worst} in {year} (Jeffreys, red)",
                                f"{len(flagged)} de las 4 curvas del caso 1 subestiman {worst} en {year} (Jeffreys, rojo)")})
    # every case 3 forecast of Table 8, the 2009 curve unchanged included
    c3 = [appr[a]["pd"] / p1 for a in ("C1-ipc", "C2-ls", "C3-chi2", "C4-ilr")]
    out.append({"id": "F-CASE3", "severity": "S2", "status": "open", "evidence": ["design:tasche-2013-table-8"],
                "title": _t(f"Without the {year} default rate, the case 3 approaches forecast {min(c3):.1f} to {max(c3):.1f} times the observed PD: the invariances fail on these data",
                            f"Sin la tasa de {year}, los enfoques del caso 3 pronostican {_es(min(c3), 1)} a {_es(max(c3), 1)} veces la PD observada: las invarianzas no se cumplen en estos datos")})
    out.append({"id": "F-PROPHETIC", "severity": "S4", "status": "accepted", "evidence": ["design:prophetic-pd"],
                "title": _t("Case 1 uses the observed default rate of the forecast year, as the paper does, to compare the approaches fairly; in use the PD is a forecast",
                            "El caso 1 usa la tasa observada del año pronosticado, como el artículo, para comparar los enfoques en igualdad; en uso la PD es un pronóstico")})
    out.append({"id": "F-IAR-PROFILE", "severity": "S4", "status": "accepted", "evidence": ["design:tasche-2013-section-4.2.2"],
                "title": _t("The invariant accuracy ratio approximates the survivor profile by the forecast profile (section 4.2.2), poor when the PD is high",
                            "La razón de precisión invariante aproxima el perfil de sobrevivientes con el perfil pronosticado (sección 4.2.2), pobre cuando la PD es alta")})
    return out


def _sp_variant(sp: Sp, v: dict[str, Any], seed: int, rv: str, paths: Any) -> tuple[dict[str, Any], dict[str, float]]:
    year = v["year"]
    y1 = sp.table2["years"][year]
    m1 = pc.model_from_counts(y1["rated"], y1["defaults"])
    appr = _approaches(sp, m1)
    tests = _sp_tests(appr, y1["rated"], y1["defaults"])
    golden = _sp_golden(sp, year, appr, tests)
    case3_profile = {aid: pc.profile_chi2(y1["rated"], appr[aid]["implied_profile"]) for aid in ("C2-ls", "C3-chi2")}
    models = []
    for a in APPROACHES:
        params = {"forecast_pd": {"value": appr[a["id"]]["pd"], "unit": "probability"}}
        params.update({k: {"value": float(val), "unit": "unitless"} for k, val in appr[a["id"]]["constants"].items()})
        models.append({"id": a["id"], "family": "pd-curve-calibration", "rung": f"case-{a['case']}", "title": a["title"],
                       "short_title": a["short"], "engine": "riskvalidation.engines.pd_curve", "engine_version": rv,
                       "licence": "MIT", "checkpoint_sha256": None, "calibration": None, "parameters": params})
    outputs = {
        "kind": "sp-calibration", "year": year, "grades": list(papers.SP_GRADES),
        "profile0": sp.m0["profile"], "profile1": m1["profile"],
        "default_rate0": sp.m0["default_rate"], "default_rate1": m1["default_rate"],
        "default_profile0": sp.m0["default_profile"], "pd0": sp.m0["pd"], "pd1": m1["pd"],
        "ar0": sp.m0["accuracy_ratio"], "ar1": m1["accuracy_ratio"],
        "qmm0": {"curve": sp.q0["pd_curve"], "alpha": sp.q0["alpha"], "beta": sp.q0["beta"], "scores": sp.q0["scores"],
                 "start": sp.q0["start"], "pd": sp.q0["pd"]},
        "approaches": {aid: {"curve": a["curve"], "pd": a["pd"], "pd_under_profile1": a["pd_under_profile1"],
                             "accuracy_ratio": a["accuracy_ratio"], "constants": a["constants"]} for aid, a in appr.items()},
        "case3_profile_tests": {aid: {"statistic": t["statistic"], "dof": t["dof"], "p_value": t["p_value"]} for aid, t in case3_profile.items()},
        "golden": golden,
        "parity": {"calibration": _parity_sp(sp, m1), "irb": _irb_parity()},
        "irb": IRB_ASSUMPTIONS,
        "n_obligors": int(sum(y1["rated"])), "n_defaults": int(sum(y1["defaults"])),
    }
    lineage = lin.build(CASE_ID, sources=["tasche-2013"], truth_status=v["truth"], seed=seed, code_version=__version__,
                        riskvalidation_version=rv)
    art = build_artifact(case_id=CASE_ID, variant_id=v["id"], model=models, outputs=outputs, tests=tests,
                         impact=_sp_impact(appr, m1["profile"]), findings=_sp_findings(year, tests, appr, m1["pd"]),
                         lineage=lineage, lane={"lane": "precompute", "reasons": []})
    values = {f"c_pd_{v['id']}": appr["A3-spd"]["constants"]["c_pd"], f"c_lr_{v['id']}": appr["A4-slr"]["constants"]["c_lr"]}
    for t in tests:
        if t["test_id"] == "pd.default_profile":
            values[f"p_profile_{t['model_id']}_{v['id']}"] = t["p_value"]
    for aid in ("C2-ls", "C4-ilr"):
        values[f"forecast_pd_{aid}_{v['id']}"] = appr[aid]["pd"]
    if year == 2010:
        values["golden_max_gap_table7_pct"] = golden["max_gap_table7_pct_beyond_relative"]
    return art, values


# ---------------------------------------------------------------------------------------------------------------------
# the low-default variants


def _bounds_table(n: tuple[int, ...], d: tuple[int, ...]) -> dict[str, Any]:
    """The bounds of one observation at the six levels: independent, correlated, scaled (both targets)."""
    out: dict[str, Any] = {"independent": [], "correlated": [], "scaled_upper_bound": [], "scaled_upper_bound_correlated": [],
                           "scaled_central_tendency": []}
    for g in GAMMAS:
        out["independent"].append(ldp.most_prudent_pd(n, d, g)["pd"])
        out["correlated"].append(ldp.most_prudent_pd(n, d, g, RHO)["pd"])
        s = ldp.most_prudent_pd_scaled(n, d, g, target="upper_bound")
        out["scaled_upper_bound"].append({"pd": s["pd"], "k": s["k"], "target": s["target"]})
        s = ldp.most_prudent_pd_scaled(n, d, g, RHO, target="upper_bound")
        out["scaled_upper_bound_correlated"].append({"pd": s["pd"], "k": s["k"], "target": s["target"]})
        if sum(d) > 0:
            s = ldp.most_prudent_pd_scaled(n, d, g, target="central_tendency")
            out["scaled_central_tendency"].append({"pd": s["pd"], "k": s["k"], "target": s["target"]})
    return out


def _generator(seed: int) -> dict[str, Any]:
    """The Vasicek generator: N_YEARS independent years, one systematic factor each, the true PDs and correlation."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(N_YEARS)
    n = np.array(LDP_N)
    cond = ndtr((ndtri(np.array(TRUE_PD))[None, :] - np.sqrt(RHO) * z[:, None]) / np.sqrt(1.0 - RHO))
    defaults = rng.binomial(n[None, :], cond)
    return {"z": z, "defaults": defaults}


def _variance_of_total(rho: float) -> float:
    """The variance of a year's number of defaults in the one-factor model: binomial terms plus the covariance of
    every pair of obligors, E[p_g(Z) p_h(Z)] - p_g p_h, by 256-node Gauss-Hermite quadrature over the factor."""
    nodes, weights = np.polynomial.hermite_e.hermegauss(256)
    weights = weights / np.sqrt(2.0 * np.pi)
    n = np.array(LDP_N, dtype=float)
    p = np.array(TRUE_PD)
    cond = ndtr((ndtri(p)[:, None] - np.sqrt(rho) * nodes[None, :]) / np.sqrt(1.0 - rho))  # grades x nodes
    joint = (cond[:, None, :] * cond[None, :, :]) @ weights                                  # E[p_g p_h]
    cov = joint - np.outer(p, p)
    pairs = np.outer(n, n) - np.diag(n)                                                      # g = h: n (n - 1) pairs
    return float(np.sum(n * p * (1.0 - p)) + np.sum(pairs * cov))


def _coverage_power(gen: dict[str, Any]) -> dict[str, Any]:
    """CT-205: coverage of each bound and power or size of each test over the generated years, by table lookup (the
    bounds and the p-values depend on a year only through its pooled counts)."""
    dmat = gen["defaults"]
    years = dmat.shape[0]
    pooled_d = np.cumsum(dmat[:, ::-1], axis=1)[:, ::-1]
    pooled_n = np.cumsum(np.array(LDP_N)[::-1])[::-1]
    dmax = int(pooled_d.max())
    se = lambda p: float(np.sqrt(p * (1 - p) / years))  # noqa: E731
    cov: dict[str, Any] = {}
    for method, rho in (("independent", 0.0), ("correlated", RHO)):
        cov[method] = {}
        for gi, g in enumerate(LDP_GRADES):
            cov[method][g] = []
            for gamma in GAMMAS[:5]:
                table = np.array([ldp.most_prudent_pd((int(pooled_n[gi]),), (k,), gamma, rho)["pd"][0] for k in range(dmax + 1)])
                b = table[pooled_d[:, gi]]
                hit = float(np.mean(b >= TRUE_PD[gi]))
                q = np.quantile(b / TRUE_PD[gi], [0.25, 0.5, 0.75])
                cov[method][g].append({"gamma": gamma, "coverage": hit, "se": se(hit), "ratio_q25": float(q[0]),
                                       "ratio_median": float(q[1]), "ratio_q75": float(q[2])})
    # the scaled bounds (section 5, to the portfolio bound) depend on all three pools at once: computed once per
    # distinct default pattern (the generated years repeat a small set of them)
    patterns, inverse = np.unique(dmat, axis=0, return_inverse=True)
    inverse = np.asarray(inverse).reshape(-1)
    for method, rho in (("scaled", 0.0), ("scaled_correlated", RHO)):
        cov[method] = {g: [] for g in LDP_GRADES}
        for gamma in GAMMAS[:5]:
            tab = np.array([ldp.most_prudent_pd_scaled(LDP_N, tuple(int(x) for x in pat), gamma, rho, target="upper_bound")["pd"]
                            for pat in patterns])
            b = tab[inverse]
            for gi, g in enumerate(LDP_GRADES):
                hit = float(np.mean(b[:, gi] >= TRUE_PD[gi]))
                q = np.quantile(b[:, gi] / TRUE_PD[gi], [0.25, 0.5, 0.75])
                cov[method][g].append({"gamma": gamma, "coverage": hit, "se": se(hit), "ratio_q25": float(q[0]),
                                       "ratio_median": float(q[1]), "ratio_q75": float(q[2])})
    # size (true PDs) and power (expert PDs) of the tests at 5% and 1%
    n = np.array(LDP_N)
    tot = dmat.sum(axis=1)
    tests: dict[str, Any] = {}
    for name, pds in (("true", TRUE_PD), ("expert", EXPERT_PD)):
        res: dict[str, Any] = {}
        for gi, g in enumerate(LDP_GRADES):
            pj = np.array([stats.beta.cdf(pds[gi], k + 0.5, n[gi] - k + 0.5) for k in range(int(dmat[:, gi].max()) + 1)])
            p = pj[dmat[:, gi]]
            res[f"jeffreys_{g}"] = {"reject_5": float(np.mean(p < 0.05)), "reject_1": float(np.mean(p < 0.01))}
        pd_port = float(np.dot(n, pds) / n.sum())
        pj = np.array([stats.beta.cdf(pd_port, k + 0.5, n.sum() - k + 0.5) for k in range(int(tot.max()) + 1)])[tot]
        res["jeffreys_portfolio"] = {"reject_5": float(np.mean(pj < 0.05)), "reject_1": float(np.mean(pj < 0.01))}
        pb = np.array([default_count_sf(k, int(n.sum()), pd_port, 0.0) for k in range(int(tot.max()) + 1)])[tot]
        res["binomial_portfolio"] = {"reject_5": float(np.mean(pb < 0.05)), "reject_1": float(np.mean(pb < 0.01))}
        pv = np.array([default_count_sf(k, int(n.sum()), pd_port, RHO) for k in range(int(tot.max()) + 1)])[tot]
        res["vasicek_portfolio"] = {"reject_5": float(np.mean(pv < 0.05)), "reject_1": float(np.mean(pv < 0.01))}
        tests[name] = res
    hist = np.bincount(tot, minlength=11)[:11]
    from scipy import optimize

    var_sim = float(np.var(tot, ddof=1))
    rho_hat = float(optimize.brentq(lambda r: _variance_of_total(r) - var_sim, 1e-6, 0.9, xtol=1e-10))
    return {"years": years, "coverage": cov, "tests": tests, "patterns": int(len(patterns)),
            "overdispersion": {"variance_simulated": var_sim, "variance_model": _variance_of_total(RHO),
                               "variance_independent": _variance_of_total(1e-12), "rho_moment_estimate": rho_hat},
            "total_defaults_histogram": [int(v) for v in hist],
            "total_defaults_tail": int(np.sum(tot > 10)), "share_of_defaults_by_grade": [float(v) for v in dmat.sum(axis=0) / (years * n)]}


def _ldp_tests(d: tuple[int, ...]) -> list[dict[str, Any]]:
    rows = [r.to_dict() for r in pd_jeffreys_grades(list(LDP_N), list(d), list(EXPERT_PD), grades=list(LDP_GRADES), model_id="E0-expert")]
    n = sum(LDP_N)
    pd_port = float(np.dot(LDP_N, EXPERT_PD) / n)
    rows.append(pd_binomial(n, sum(d), pd_port, model_id="E0-expert", segment="portfolio").to_dict())
    rows.append(pd_binomial_vasicek(n, sum(d), pd_port, RHO, model_id="E0-expert", segment="portfolio").to_dict())
    return rows


def _ldp_impact(bounds: dict[str, Any], truth: tuple[float, ...] | None) -> dict[str, Any]:
    n = np.asarray(LDP_N, dtype=float)
    k75 = GAMMAS.index(0.75)

    def avg(pds) -> float:
        return float(np.sum(n * np.array([_irb_rw(p) for p in pds])) / n.sum())

    out = {"rw_expert": {"value": avg(EXPERT_PD), "unit": "share of EAD", "label": _t("Average risk weight, expert PDs (floored at 0.05%)", "Ponderador medio, PD expertas (con piso 0,05%)")},
           "rw_independent_75": {"value": avg(bounds["independent"][k75]), "unit": "share of EAD", "label": _t("Average risk weight, most prudent at 75%", "Ponderador medio, más prudente al 75%")},
           "rw_correlated_75": {"value": avg(bounds["correlated"][k75]), "unit": "share of EAD", "label": _t("Average risk weight, most prudent at 75%, correlation 12%", "Ponderador medio, más prudente al 75%, correlación 12%")},
           "rw_scaled_75": {"value": avg(bounds["scaled_upper_bound"][k75]["pd"]), "unit": "share of EAD", "label": _t("Average risk weight, scaled to the portfolio bound at 75%", "Ponderador medio, escalado a la cota de la cartera al 75%")}}
    if truth is not None:
        out["rw_truth"] = {"value": avg(truth), "unit": "share of EAD", "label": _t("Average risk weight, the true PDs", "Ponderador medio, las PD verdaderas")}
    return out


def _ldp_findings(v: dict[str, Any], d: tuple[int, ...], tests: list[dict[str, Any]], bounds: dict[str, Any], cp: dict[str, Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in tests:
        if t["test_id"] == "pd.jeffreys" and t["light"] in ("amber", "red") and t["segment"] != "portfolio":
            out.append({"id": f"F-JEFF-{t['segment']}", "severity": "S3" if t["light"] == "amber" else "S2", "status": "open",
                        "evidence": [f"pd.jeffreys@E0-expert@{t['segment']}"],
                        "title": _t(f"Grade {t['segment']}: {t['n_events']} defaults of {t['n']} are unlikely at the expert PD (Jeffreys p = {t['p_value']:.3f})",
                                    f"Grado {t['segment']}: {t['n_events']} incumplimientos de {t['n']} son improbables con la PD experta (Jeffreys p = {_es(t['p_value'], 3)})")})
    k75 = GAMMAS.index(0.75)
    below = [g for g, e, b in zip(LDP_GRADES, EXPERT_PD, bounds["scaled_upper_bound"][k75]["pd"], strict=True) if e < b]
    out.append({"id": "F-BELOW-BOUND", "severity": "S3" if below else "S4", "status": "open",
                "evidence": ["design:pluto-tasche-section-5"],
                "title": _t(f"The expert PDs lie below the most prudent calibration (scaled to the portfolio bound at 75%) in grades {', '.join(below) or 'none'}",
                            f"Las PD expertas quedan bajo la calibración más prudente (escalada a la cota de la cartera al 75%) en los grados {', '.join(below) or 'ninguno'}")})
    if cp is not None:
        power = cp["tests"]["expert"]["vasicek_portfolio"]["reject_5"]
        size_j = cp["tests"]["true"]["jeffreys_portfolio"]["reject_5"]
        size_v = cp["tests"]["true"]["vasicek_portfolio"]["reject_5"]
        out.append({"id": "F-POWER", "severity": "S2", "status": "open", "evidence": ["design:known-truth-power"],
                    "title": _t(f"Against a model at half the truth, the test that keeps its size (Vasicek binomial, {100 * size_v:.1f}% under the truth) rejects in {100 * power:.1f}% of the years at 5%: the battery cannot see the underestimation",
                                f"Frente a un modelo a la mitad de la verdad, la prueba que mantiene su tamaño (binomial de Vasicek, {_es(100 * size_v, 1)}% bajo la verdad) rechaza en el {_es(100 * power, 1)}% de los años al 5%: la batería no ve la subestimación")})
        out.append({"id": "F-SIZE", "severity": "S3", "status": "open", "evidence": ["design:known-truth-size"],
                    "title": _t(f"With correlated defaults the Jeffreys portfolio test rejects the true PDs in {100 * size_j:.1f}% of the years at 5% (the BCBS WP14 warning on correlation)",
                                f"Con incumplimientos correlacionados la prueba de Jeffreys de la cartera rechaza las PD verdaderas en el {_es(100 * size_j, 1)}% de los años al 5% (la advertencia del WP14 de BCBS sobre la correlación)")})
        ratio = next(r for r in cp["coverage"]["independent"]["C"] if r["gamma"] == 0.75)["ratio_median"]
        sc = next(r for r in cp["coverage"]["scaled"]["C"] if r["gamma"] == 0.50)["coverage"]
        b50 = next(r for r in cp["coverage"]["independent"]["B"] if r["gamma"] == 0.50)["coverage"]
        out.append({"id": "F-CONSERVATISM", "severity": "S4", "status": "accepted", "evidence": ["design:known-truth-coverage"],
                    "title": _t(f"From 75% up the one-year bounds cover the truth in every generated year, far above it (grade C at 75%: {ratio:.1f} times the true PD in the median year); at 50% a year without defaults puts grade B's bound just under its truth (coverage {100 * b50:.0f}%)",
                                f"Desde el 75% las cotas de un año cubren la verdad en todos los años generados, muy por encima (grado C al 75%: {_es(ratio, 1)} veces la PD verdadera en el año mediano); al 50% un año sin incumplimientos deja la cota del grado B justo bajo su verdad (cobertura {_es(100 * b50, 0)}%)")})
        out.append({"id": "F-SCALED-COVERAGE", "severity": "S3", "status": "open", "evidence": ["design:known-truth-coverage"],
                    "title": _t(f"Scaled to the portfolio bound at a moderate 50% (the paper's proposal), grade C's estimate covers the truth in {100 * sc:.0f}% of the years",
                                f"Escalada a la cota de la cartera a un moderado 50% (la propuesta del artículo), la estimación del grado C cubre la verdad en el {_es(100 * sc, 0)}% de los años")})
    else:
        out.append({"id": "F-PAPER-DEVIATIONS", "severity": "S4", "status": "accepted", "evidence": ["design:pluto-tasche-deviations"],
                    "title": _t("The paper's Tables 4 (75%), 8, 12 and 13 to 14 deviate from their exact values; the golden table names each cell",
                                "Las tablas 4 (75%), 8, 12 y 13 a 14 del artículo se apartan de sus valores exactos; la tabla de referencia nombra cada celda")})
    return out


def _ldp_golden(pt: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """CT-203: Tables 1 to 14 of Pluto and Tasche recomputed, cell by cell, with the gaps (percent)."""
    cells: list[dict[str, Any]] = []
    zero, few = (0, 0, 0), LDP_PUBLISHED_D

    def add(table: int, row: str, gi: int, ours: float) -> None:
        printed = pt[table]["rows"][row][gi]
        scale = 1.0 if row == "k" else 100.0
        cells.append({"table": table, "row": row, "gamma": GAMMAS[gi], "printed": printed, "ours": round(scale * ours, 4),
                      "gap": round(round(scale * ours, 2) - printed, 4)})

    for gi, g in enumerate(GAMMAS):
        ind0, ind1 = ldp.most_prudent_pd(LDP_N, zero, g)["pd"], ldp.most_prudent_pd(LDP_N, few, g)["pd"]
        cor0, cor1 = ldp.most_prudent_pd(LDP_N, zero, g, RHO)["pd"], ldp.most_prudent_pd(LDP_N, few, g, RHO)["pd"]
        for t, j in ((1, 0), (2, 1), (3, 2)):
            add(t, ("pa", "pb", "pc")[j], gi, ind0[j])
        for t, j in ((4, 0), (5, 1), (6, 2)):
            add(t, ("pa", "pb", "pc")[j], gi, ind1[j])
        for j, row in enumerate(("pa", "pb", "pc")):
            add(7, row, gi, cor0[j])
            add(8, row, gi, cor1[j])
        for table, rho, target in ((9, 0.0, "central_tendency"), (10, RHO, "central_tendency"), (11, 0.0, "upper_bound"), (12, RHO, "upper_bound")):
            s = ldp.most_prudent_pd_scaled(LDP_N, few, g, rho, target=target)
            add(table, "k", gi, s["k"])
            for j, row in enumerate(("pa,scaled", "pb,scaled", "pc,scaled")):
                add(table, row, gi, s["pd"][j])
        for table, d in ((13, zero), (14, few)):
            m = ldp.most_prudent_pd_multiperiod(LDP_N, d, g, **MULTI)["pd"]
            for j, row in enumerate(("pa", "pb", "pc")):
                add(table, row, gi, m[j])
    return {"cells": cells, "notes": {
        "4": "75%: the paper's 0.65% is the bound at 76.3%; the exact one is 0.638%, and Table 11 scales with the 0.65%",
        "8": "every printed cell lies at or above the exact bound, within 0.0094 percentage points",
        "12": "B at 99.9%: printed 9.54%, exact 9.44%",
        "13-14": "Monte Carlo of the stated model, checked by a deterministic quadrature in riskvalidation; the print lies 1% to 5% above it at 99% and 99.9%"}}


def _ldp_parity() -> dict[str, Any]:
    """CT-209: the bounds at points the live port must reproduce exactly."""
    pts = []
    for d in ((0, 0, 0), (0, 2, 1), (1, 0, 2)):
        for g in (0.5, 0.75, 0.9, 0.99):
            for rho in (0.0, 0.12, 0.24):
                pts.append({"defaults": list(d), "gamma": g, "rho": rho, "pd": ldp.most_prudent_pd(LDP_N, d, g, rho)["pd"],
                            "scaled_upper_bound": ldp.most_prudent_pd_scaled(LDP_N, d, g, rho, target="upper_bound")["pd"]})
    return {"obligors": list(LDP_N), "points": pts}


def _ldp_variant(v: dict[str, Any], d: tuple[int, ...], seed: int, rv: str, cp: dict[str, Any] | None,
                 golden: dict[str, Any] | None, gen_year: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, float]]:
    bounds = _bounds_table(LDP_N, d)
    tests = _ldp_tests(d)
    models = [{"id": "E0-expert", "family": "pd-estimate", "rung": "expert", "title": _t("Expert PDs (hypothetical)", "PD expertas (hipotéticas)"),
               "short_title": _t("Expert", "Experta"), "engine": "none", "engine_version": "none", "licence": "MIT",
               "checkpoint_sha256": None, "calibration": None,
               "parameters": {f"pd_{g}": {"value": p, "unit": "probability"} for g, p in zip(LDP_GRADES, EXPERT_PD, strict=True)}}]
    for mid, title, short, params in (
        ("L1-independent", _t("Most prudent bound, independent", "Cota más prudente, independiente"), _t("Independent", "Independiente"), {}),
        ("L2-correlated", _t("Most prudent bound, correlation 12%", "Cota más prudente, correlación 12%"), _t("Correlated", "Correlacionada"),
         {"rho": {"value": RHO, "unit": "unitless"}}),
        ("L3-scaled", _t("Most prudent bound scaled to the portfolio bound", "Cota más prudente escalada a la cota de la cartera"), _t("Scaled", "Escalada"), {}),
    ):
        models.append({"id": mid, "family": "most-prudent-estimation", "rung": mid.split("-")[0], "title": title, "short_title": short,
                       "engine": "riskvalidation.engines.low_default", "engine_version": rv, "licence": "MIT",
                       "checkpoint_sha256": None, "calibration": None, "parameters": params})
    outputs: dict[str, Any] = {
        "kind": "ldp", "grades": list(LDP_GRADES), "obligors": list(LDP_N), "defaults": list(d), "gammas": list(GAMMAS),
        "expert_pd": list(EXPERT_PD), "true_pd": list(TRUE_PD) if cp is not None else None, "rho": RHO,
        "bounds": bounds, "irb": IRB_ASSUMPTIONS, "parity": {"bounds": _ldp_parity(), "irb": _irb_parity()},
        "known_truth": cp, "golden": golden, "generated_year": gen_year,
    }
    sources = ["pluto-tasche-2005"] if cp is None else []
    lineage = lin.build(CASE_ID, sources=sources, truth_status=v["truth"], seed=seed, code_version=__version__,
                        riskvalidation_version=rv, generators=(GENERATOR,) if cp is not None else ())
    art = build_artifact(case_id=CASE_ID, variant_id=v["id"], model=models, outputs=outputs, tests=tests,
                         impact=_ldp_impact(bounds, TRUE_PD if cp is not None else None),
                         findings=_ldp_findings(v, d, tests, bounds, cp), lineage=lineage,
                         lane={"lane": "precompute", "reasons": []})
    values: dict[str, float] = {}
    if v["id"] == "ldp-published":
        values["bound_A_independent_50_ldp-published"] = bounds["independent"][0][0]
        values["bound_A_correlated_50_ldp-published"] = bounds["correlated"][0][0]
    return art, values


# ---------------------------------------------------------------------------------------------------------------------


def _models_artifacts(sp: Sp, seed: int, rv: str, paths: Any) -> dict[str, dict[str, Any]]:
    entries = {}
    lineage = lin.build(CASE_ID, sources=["tasche-2013"], truth_status="published-answer", seed=seed, code_version=__version__,
                        riskvalidation_version=rv)
    records = [
        {"id": "M0-observed-2009", "family": "rating-system", "rung": "observed", "title": _t("2009 grade default rates", "Tasas de incumplimiento por grado, 2009"),
         "short_title": _t("Observed 2009", "Observada 2009"), "engine": "none", "engine_version": "none", "licence": "MIT",
         "checkpoint_sha256": None, "calibration": None,
         "parameters": {"pd": {"value": sp.m0["pd"], "unit": "probability"}, "accuracy_ratio": {"value": sp.m0["accuracy_ratio"], "unit": "unitless"}},
         "details": {"default_rate": sp.m0["default_rate"], "profile": sp.m0["profile"]}},
        {"id": "M1-qmm-2009", "family": "rating-system", "rung": "smoothed", "title": _t("2009 PD curve smoothed by quasi moment matching", "Curva de PD 2009 suavizada por cuasi ajuste de momentos"),
         "short_title": _t("QMM 2009", "QMM 2009"), "engine": "riskvalidation.engines.pd_curve", "engine_version": rv, "licence": "MIT",
         "checkpoint_sha256": None, "calibration": None,
         "parameters": {"alpha": {"value": sp.q0["alpha"], "unit": "unitless"}, "beta": {"value": sp.q0["beta"], "unit": "unitless"},
                        "pd_target": {"value": sp.m0["pd"], "unit": "probability"}, "ar_target": {"value": sp.m0["accuracy_ratio"], "unit": "unitless"}},
         "details": {"curve": sp.q0["pd_curve"], "scores": sp.q0["scores"], "start": sp.q0["start"],
                     "default_profile": sp.m0["default_profile"], "survival_profile": sp.m0["survival_profile"], "profile": sp.m0["profile"]}},
    ]
    doc = build_models_artifact(case_id=CASE_ID, fit_id="sp2009", model=records,
                                fit={"estimation_year": 2009, "targets": {"pd": sp.m0["pd"], "accuracy_ratio": sp.m0["accuracy_ratio"]}},
                                lineage=lineage, lane={"lane": "precompute", "reasons": []})
    rel = f"{CASE_ID}/models-sp2009.json"
    entries["sp"] = {"rel": rel, **write_artifact(paths.root, rel, doc, exact=frozenset({"details"}), engines=ENGINES, run_ms=RUN_MS)}
    nodes, weights = np.polynomial.hermite_e.hermegauss(256)
    lineage = lin.build(CASE_ID, sources=["pluto-tasche-2005"], truth_status="published-answer", seed=seed, code_version=__version__,
                        riskvalidation_version=rv)
    records = [{"id": "L0-methods", "family": "most-prudent-estimation", "rung": "methods",
                "title": _t("Most prudent estimation (Pluto and Tasche 2005)", "Estimación más prudente (Pluto y Tasche 2005)"),
                "short_title": _t("Most prudent", "Más prudente"), "engine": "riskvalidation.engines.low_default", "engine_version": rv,
                "licence": "MIT", "checkpoint_sha256": None, "calibration": None, "parameters": {"rho": {"value": RHO, "unit": "unitless"}},
                "details": {"quadrature": {"rule": "probabilists' Gauss-Hermite, 256 nodes", "nodes": [float(x) for x in nodes],
                                           "weights": [float(w / np.sqrt(2.0 * np.pi)) for w in weights]}}}]
    doc = build_models_artifact(case_id=CASE_ID, fit_id="ldp", model=records,
                                fit={"obligors": list(LDP_N), "expert_pd": list(EXPERT_PD)},
                                lineage=lineage, lane={"lane": "precompute", "reasons": []})
    rel = f"{CASE_ID}/models-ldp.json"
    entries["ldp"] = {"rel": rel, **write_artifact(paths.root, rel, doc, exact=frozenset({"details"}), engines=ENGINES, run_ms=RUN_MS)}
    return entries


class C05:
    id = CASE_ID
    slug = "ldp-calibration"
    title = _t("Low-default portfolios and PD calibration", "Carteras de bajo incumplimiento y calibración de PD")
    category_id = "ratings-calibration"
    kind = "real"  # the default variants read published S&P data; the generator variants are labelled synthetic
    question = _t("How should a PD curve be carried to a new year, and what can be said about PDs with almost no defaults?",
                  "¿Cómo llevar una curva de PD a un nuevo año, y qué se puede decir de PD con casi ningún incumplimiento?")
    sources = SOURCES

    def bake(self, seed: int, paths: Any, data_root: Path) -> dict[str, Any]:
        from ..io import sources as registry

        registry.assert_case_inputs(CASE_ID, list(SOURCES))
        rv = _v("riskvalidation")
        sp = _load_sp(data_root)
        pt = papers.read_pluto_tasche_tables(Path(data_root) / "raw" / "pluto-tasche-2005" / PLUTO_PDF)
        _log("papers read: Tasche Tables 2 and 5 to 9, Pluto-Tasche Tables 1 to 14")
        models = _models_artifacts(sp, seed, rv, paths)
        gen = _generator(SEED_YEARS)
        cp = _coverage_power(gen)
        _log(f"generator: {N_YEARS:,} years, coverage and power tables")
        values: dict[str, float] = {"qmm_alpha_2009": sp.q0["alpha"], "qmm_beta_2009": sp.q0["beta"],
                                    "true_pd_recovered_C": cp["share_of_defaults_by_grade"][2]}
        values["coverage_independent_C_90"] = next(r for r in cp["coverage"]["independent"]["C"] if r["gamma"] == 0.90)["coverage"]
        values["coverage_correlated_C_90"] = next(r for r in cp["coverage"]["correlated"]["C"] if r["gamma"] == 0.90)["coverage"]
        values["ratio_independent_C_90_median"] = next(r for r in cp["coverage"]["independent"]["C"] if r["gamma"] == 0.90)["ratio_median"]
        values["coverage_scaled_C_50"] = next(r for r in cp["coverage"]["scaled"]["C"] if r["gamma"] == 0.50)["coverage"]
        values["power_jeffreys_portfolio_expert"] = cp["tests"]["expert"]["jeffreys_portfolio"]["reject_5"]
        golden_ldp = _ldp_golden(pt)
        entries: list[dict[str, Any]] = []
        for key, e in models.items():
            entries.append({"role": "models", "variant_id": f"models-{'sp2009' if key == 'sp' else 'ldp'}", "truth_status": "published-answer",
                            "title": _t("2009 S&P rating system" if key == "sp" else "Most prudent estimation inputs",
                                        "Sistema de calificación S&P 2009" if key == "sp" else "Entradas de la estimación más prudente"),
                            "short_title": _t("Models " + key, "Modelos " + key),
                            "regime": _t("The estimation model and its constants" if key == "sp" else "The quadrature the live bounds use",
                                         "El modelo de estimación y sus constantes" if key == "sp" else "La cuadratura que usan las cotas en vivo"),
                            "path": e["rel"], "bytes": e["bytes"], "lane": e["lane"], "gate": e["gate"]})
        for v in VARIANTS:
            if v["kind"] == "sp":
                art, vals = _sp_variant(sp, v, seed, rv, paths)
                ref = models["sp"]["rel"]
            else:
                if v["id"] == "ldp-published":
                    d, cp_v, golden, year = LDP_PUBLISHED_D, None, golden_ldp, None
                else:
                    tot = gen["defaults"].sum(axis=1)
                    idx = int(np.flatnonzero(tot == v["total"])[0])
                    d = tuple(int(x) for x in gen["defaults"][idx])
                    cp_v, golden, year = cp, None, {"index": idx, "factor": float(gen["z"][idx])}
                art, vals = _ldp_variant(v, d, seed, rv, cp_v, golden, year)
                ref = models["ldp"]["rel"]
            values.update(vals)
            rel = f"{CASE_ID}/{v['id']}.json"
            entry = write_artifact(paths.root, rel, art, exact=frozenset({"parity", "qmm0", "curve", "profile1", "default_profile0",
                                                                           "obligors", "pd0", "pd1", "ar0"}),
                                   engines=ENGINES, run_ms=RUN_MS)
            _log(f"variant {v['id']}: {len(art['tests'])} test results, {entry['bytes']:,} bytes")
            entries.append({"role": "variant", "variant_id": v["id"], "title": v["title"], "short_title": v["short"], "regime": v["regime"],
                            "truth_status": v["truth"], "models_ref": ref, **entry})
        ranges = expectations.check(CASE_ID, EXPECT, values)
        manifest = build_case_manifest(
            case_id=CASE_ID, title=self.title, category={"en": "Ratings and calibration", "es": "Calificaciones y calibración"},
            question=self.question, sources=list(SOURCES), seed=seed, variants=entries, default_variant="sp-2010",
            # no contract-1 family: the inputs are paper tables, checked by pipeline.io.papers against their own
            # print (CT-201, CT-202); a reader that cannot satisfy them refuses the bake
            contract={},
            expect=ranges, riskvalidation_version=rv, source_details=_source_details(SOURCES))
        write_json(paths.manifests / f"{CASE_ID}.json", manifest)
        return manifest


def _source_details(ids) -> dict[str, dict[str, str]]:
    from ..io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing,
                "licence": reg[i].licence, "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


CASE = C05()
