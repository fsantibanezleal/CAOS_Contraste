"""One variant of C12 as a document: the exposure measures of the book, CVA and DVA, the regulatory measures and the tests.

Every number is a call into ``riskvalidation`` (``exposure.py``, ``credit.py``, ``regulatory.py``, ``backtest.py``); this module
sequences them for one variant, picks the fields of the c12-outputs schema and builds the engine's test rows. The six variants
share one simulation, one curve and one calibration; they differ in the members of the netting set and in how the values become
an exposure.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import re

import numpy as np
from riskvalidation.ccr import cva as cv
from riskvalidation.ccr import exposure as ex
from riskvalidation.ccr import hw1f
from riskvalidation.ccr import swaps as sw
from riskvalidation.validation import ccr as vc
from scipy.stats import norm

from ...core.text import number
from . import book, credit
from . import exposure as xp
from . import regulatory as rg

MODEL_ID = "hw1f-exposure"
POLICY = "contraste-c12-1.0.0"
GIRR_SINGLE = ("SW-1",)


class BakeError(ValueError):
    """A document cannot be written: a measure the schema requires is undefined, with the reason."""


@dataclass(frozen=True)
class Spec:
    variant: str
    members: tuple[int, ...]
    mpor: int | None
    im: bool = False
    wwr: bool = False

    @property
    def basis(self) -> str:
        return "collateralised-vm-im" if self.im else "collateralised-vm" if self.mpor else "uncollateralised"

    @property
    def book_key(self) -> str:
        return "single" if len(self.members) == 1 else "netting"


ALL = (0, 1, 2, 3)
SPECS = (Spec("single-swap", (0,), None), Spec("netting-set", ALL, None), Spec("csa-mpor-10d", ALL, 10),
         Spec("csa-mpor-20d", ALL, 20), Spec("with-im", ALL, 10, im=True), Spec("wrong-way-risk", ALL, None, wwr=True))
IM = {"quantile": book.IM_QUANTILE, "horizon_cd": 14, "mpor_cd": 14, "order": 2}


def text(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def profile(values: np.ndarray, se: np.ndarray) -> dict[str, Any]:
    return {"currency": book.CURRENCY, "values": [float(v) for v in values], "mc_se": [float(s) for s in se]}


def money_se(amount: float, se: float) -> dict[str, Any]:
    return {"amount": float(amount), "currency": book.CURRENCY, "mc_se": float(se)}


def exposures_of(sim: xp.Sim, spec: Spec, mta: float | None = None) -> xp.Exposures:
    members = list(spec.members)
    if spec.mpor is None:
        return xp.uncollateralised(sim, members)
    vm = xp.variation_margin(sim, members, spec.mpor, mta)
    if not spec.im:
        return vm
    return xp.initial_margin(sim, members, vm, spec.mpor, IM["quantile"], IM["horizon_cd"], IM["mpor_cd"], IM["order"])


@dataclass
class Core:
    sim: xp.Sim
    spec: Spec
    e: xp.Exposures
    mx: dict[str, Any]
    my: dict[str, Any]
    mvm: dict[str, Any] | None
    x_d: np.ndarray          # (P, K) discounted exposure paths
    y_d: np.ndarray
    p0r: np.ndarray
    num: np.ndarray


def core(sim: xp.Sim, spec: Spec, seed: int, pfe_q: float | None = book.PFE_QUANTILE, mta: float | None = None,
         light: bool = False) -> Core:
    report = sim.report
    num = sim.numeraire[:, sim.index(report)]
    p0r = np.asarray(sim.p0(report), dtype=float)
    e = exposures_of(sim, spec, mta)
    boot = 20 if light else 50
    mx = xp.measures(e.x, num, p0r, report, pfe_q, seed, boot)
    my = xp.measures(e.y, num, p0r, report, None, seed)
    mvm = xp.measures(e.x_vm, num, p0r, report, None, seed) if e.x_vm is not None else None
    return Core(sim, spec, e, mx, my, mvm, e.x / num, e.y / num, p0r, num)


def effective_se(ee: np.ndarray, se: np.ndarray) -> np.ndarray:
    """The error of the effective EE at each point: that of the point that set the running maximum."""
    best, out = 0, []
    for k, v in enumerate(ee):
        if v >= ee[best]:
            best = k
        out.append(se[best])
    return np.array(out)


def sensitivity_case(name: str, a: float, sigma: float, mx: dict[str, Any]) -> dict[str, Any]:
    return {"case": name, "a": float(a), "sigma": float(sigma), "eepe": rg.money(mx["eepe"]),
            "pfe_peak": rg.money(float(np.max(mx["pfe"]))), "ee": profile(mx["ee"], mx["ee_se"]), "pfe": profile(mx["pfe"], mx["pfe_se"])}


# ---------------------------------------------------------------------------------------------------------- tests


def tr(result: Any, **overrides: Any) -> dict[str, Any]:
    """An engine TestResult as a document row: the model id set, optional fields overridden."""
    d = result.to_dict()
    d["model_id"] = MODEL_ID
    d.update(overrides)
    return d


def custom_row(test_id: str, light: str, statistic: float | None, metric: float | None, h0: str, alternative: str, reference: str,
               notes: str, extras: dict[str, Any], n: int | None = None) -> dict[str, Any]:
    from riskvalidation.core.result import Light, TestResult

    res = TestResult(test_id=test_id, h0=h0, alternative=alternative, reference=reference, policy_version=POLICY, light=Light(light),
                     statistic=statistic, metric=metric, n=n, notes=notes, extras=extras)
    return tr(res)


def engine_rows(c: Core, curve: credit.Curve, lgd: float, k_se: float, pfe_q: float) -> list[dict[str, Any]]:
    """The CCR validation tests of the engine on this variant's own arrays."""
    sim, spec, mx = c.sim, c.spec, c.mx
    report = sim.report
    rows: list[dict[str, Any]] = []
    ki = sim.index(report)
    if spec.mpor is None and len(spec.members) == 1:
        swap = sim.swaps[spec.members[0]]
        reset = sw.reset_times(swap)
        pick = [k for k, t in enumerate(report) if np.min(np.abs(reset - t)) < 1e-9]
        analytic = ex.analytic_ee_single_swap(swap, report[pick], sim.a, sim.sigma, sim.p0, sim.forward)
        rows.append(tr(vc.ee_analytic_vs_simulated(analytic * c.p0r[pick], mx["ee_d"][pick], mx["ee_d_se"][pick], k_se)))
    top = 10.0
    keep = report <= top + 1e-9
    means, ses = [], []
    for k in np.where(keep)[0]:
        i = ki[k]
        b = hw1f.bond_price(sim.r[:, i], float(sim.grid[i]), top, sim.a, sim.sigma, sim.p0, sim.forward) / sim.numeraire[:, i]
        means.append(b.mean())
        ses.append(b.std(ddof=1) / np.sqrt(b.size))
    p_top = float(sim.p0(np.array(top)))
    rows.append(tr(vc.martingale_discounted_bonds(np.array(means), np.full(len(means), p_top), np.array(ses), k_se)))
    rows.append(tr(vc.eepe_recomputed(report, mx["ee"], mx["eepe"])))
    s_cp = credit.survival(curve, report, lgd)
    pd = cv.default_probabilities(s_cp)
    cva_val, _ = cv.cva(mx["ee_d"], pd, lgd)
    rows.append(tr(vc.cva_recomputed(mx["ee_d"], pd, lgd, cva_val)))
    n = c.x_d.shape[0]
    half = n // 2
    ee_by, cva_by, ee_se_by, cva_se_by = {}, {}, {}, {}
    dt = np.diff(np.concatenate([[0.0], report]))
    for m in (n // 4, n // 2, n):
        idx = np.concatenate([np.arange(m // 2), half + np.arange(m // 2)])
        e_d, e_se = ex.expected_exposure(c.e.x[idx], c.num[idx])
        ee_by[m], ee_se_by[m] = e_d / c.p0r, e_se / c.p0r
        v, se = cv.wwr_cva(np.zeros_like(c.x_d[idx]), c.x_d[idx], s_cp[1:], dt, lgd, 0.0)
        cva_by[m], cva_se_by[m] = v, se
    rows.append(tr(vc.path_convergence(ee_by, cva_by, ee_se_by_path_count=ee_se_by, cva_se_by_path_count=cva_se_by, k_se=k_se)))
    return rows


# --------------------------------------------------------------------------------------------------------- document

MEASURE_NOTE = text(
    "EE and ENE are undiscounted (Basel style) in the t-forward measure: the discounted EE of the engine divided by P(0, t), the "
    "quantity the analytic swaption identity gives and the one ORE's own profile reproduces; the expectation in the simulation's "
    "own measure differs by the convexity gap. The discounted profiles feed the CVA. The PFE is the quantile of the simulated "
    "exposure in the simulation measure. Effective EE starts from zero: the current exposure is the replacement cost of the "
    "sa_ccr block. EPE and EEPE are averages over the first year; their errors are batch errors of 20 antithetic batches.",
    "EE y ENE no están descontados (estilo Basilea) en la medida t-forward: el EE descontado del motor dividido por P(0, t), la "
    "cantidad que da la identidad analítica de la swaption y la que reproduce el perfil de ORE; la esperanza en la medida propia de "
    "la simulación difiere por la brecha de convexidad. Los perfiles descontados alimentan el CVA. El PFE es el cuantil de la "
    "exposición simulada en la medida de la simulación. El EE efectivo parte de cero: la exposición actual es el costo de "
    "reemplazo del bloque sa_ccr. EPE y EEPE son promedios del primer año; sus errores son errores de 20 lotes antitéticos.")

CSA_LIMIT = text("The Andersen, Pykhtin and Sokol timelines are not modelled. The minimum transfer amount acts on the balance of the "
                 "report grid; ORE margins on its own call schedule, so its effect is larger there (see the ORE rows).",
                 "No se modelan las cronologías de Andersen, Pykhtin y Sokol. El monto mínimo de transferencia actúa sobre el saldo de "
                 "la grilla del informe; ORE margina con su propio calendario de llamadas, por lo que su efecto es mayor allí (véase "
                 "las filas de ORE).")

IM_LIMIT = text(
    "A regression proxy, never SIMM. The DIM reduces the exposure path by path, E[max(X - DIM, 0)] (ORE's method, decision B2): "
    "the expected exposure after margin lies between max(ee_vm_only - dim, 0) and ee_vm_only, and `dim` is the mean regression DIM.",
    "Un proxy de regresión, nunca SIMM. El DIM reduce la exposición camino por camino, E[max(X - DIM, 0)] (método de ORE, decisión "
    "B2): la exposición esperada tras el margen está entre max(ee_vm_only - dim, 0) y ee_vm_only, y `dim` es el DIM de regresión medio.")


def outputs(c: Core, ctx: dict[str, Any], stress_eepe: float, sens: list[dict[str, Any]], ore_block: dict[str, Any],
            backtest_block: dict[str, Any], seed: int) -> dict[str, Any]:
    """The ``outputs`` object of one variant (the c12-outputs schema)."""
    spec, sim, mx, my, e = c.spec, c.sim, c.mx, c.my, c.e
    report = sim.report
    members = list(spec.members)
    trades = [ctx["trades"][i] for i in members]
    grid = [float(t) for t in report]
    nb = xp.netting_profiles(sim, members, c.p0r)
    q = book.PFE_QUANTILE
    curve: credit.Curve = ctx["credit_curve"]

    exposure = {
        "basis": spec.basis, "time_grid_years": grid, "ee": profile(mx["ee"], mx["ee_se"]),
        "ee_discounted": profile(mx["ee_d"], mx["ee_d_se"]), "ene": profile(my["ee"], my["ee_se"]),
        "ene_discounted": profile(my["ee_d"], my["ee_d_se"]), "pfe_quantile": q, "pfe": profile(mx["pfe"], mx["pfe_se"]),
        "effective_ee": profile(mx["eff"], effective_se(mx["ee"], mx["ee_se"])), "epe": money_se(mx["epe"], mx["epe_se"]),
        "eepe": money_se(mx["eepe"], mx["eepe_se"]), "eepe_horizon_years": 1.0, "measure_note": MEASURE_NOTE}
    netting_benefit = {
        "per_trade_ee": [{"trade_id": t.trade_id, "ee": profile(nb["per_trade"][k], nb["per_trade_se"][k])} for k, t in enumerate(trades)],
        "sum_of_single_trade_ee": profile(nb["sum"], nb["sum_se"]), "netted_ee": profile(nb["net"], nb["net_se"]),
        "benefit": profile(np.maximum(nb["benefit"], 0.0), nb["benefit_se"])}
    if np.min(nb["benefit"]) < -1e-6:
        raise BakeError(f"{spec.variant}: the netting benefit is negative ({np.min(nb['benefit'])}): the netted EE exceeds the sum")

    collateral = None
    if spec.mpor is not None:
        bal = e.balance
        collateral = {
            "csa": {"threshold": rg.money(book.CSA["threshold"]), "minimum_transfer_amount": rg.money(book.CSA["mta"]),
                    "independent_amount": rg.money(book.CSA["independent_amount"]), "mpor_business_days": spec.mpor,
                    "remargining_days": book.CSA["remargining_days"], "closeout": "sticky-date close-out grid (ORE, R3)",
                    "floor_reference": "CRE53.24: 10 business days floor, 20 for illiquid or large netting sets"},
            "uncollateralised_ee": profile(nb["net"], nb["net_se"]),
            "collateral_balance": profile(bal.mean(axis=0), bal.std(axis=0, ddof=1) / np.sqrt(bal.shape[0])), "limit": CSA_LIMIT}

    initial_margin = None
    if spec.im:
        vm = c.mvm
        mean_dim = e.dim[:, 1:]
        dim, dim_se = mean_dim.mean(axis=0), mean_dim.std(axis=0, ddof=1) / np.sqrt(mean_dim.shape[0])
        initial_margin = {
            "method": "ORE dynamic initial margin by regression (R2)", "labelled": "regression proxy, not SIMM", "simm_used": False,
            "quantile": IM["quantile"], "alpha": float(norm.ppf(IM["quantile"])), "horizon_calendar_days": IM["horizon_cd"],
            "mpor_calendar_days": IM["mpor_cd"], "regression_order": IM["order"], "dim": profile(dim, dim_se),
            "ee_vm_only": profile(vm["ee"], vm["ee_se"]), "limit": IM_LIMIT}

    lgd, bank_lgd = 0.6, 0.6
    cva_blk = credit.cva_block(mx["ee_d"], my["ee_d"], c.x_d, c.y_d, report, curve, lgd, 0.008, bank_lgd)
    wwr = None
    if spec.wwr:
        wwr = credit.wrong_way_block(e.values[:, 1:] / 1e6, c.x_d, report, curve, lgd, cva_blk, list(book.WWR_B_GRID))

    margined = spec.mpor is not None
    nica = float(e.dim[0, 0]) if e.dim is not None else 0.0
    sa = rg.sa_ccr_block(trades, e.v0, e.c0 if margined else 0.0, margined, book.CSA["threshold"] if margined else 0.0,
                         book.CSA["mta"] if margined else 0.0, nica, spec.mpor)
    ba = rg.ba_cva_block(trades, sa["ead"]["amount"])
    try:
        m_eff = ex.effective_maturity(report, mx["ee"], mx["eff"], c.p0r, cap=5.0)
    except ValueError as exc:
        raise BakeError(f"{spec.variant}: the effective maturity M is undefined ({exc}); the schema requires a number, so no "
                        "document is written for this variant") from exc
    alpha_eepe = 1.4 * mx["eepe"]
    st = ctx["stress"]
    regulatory = {
        "alpha": 1.4, "alpha_paragraph": "CRE53.14", "effective_maturity_years": float(m_eff), "alpha_times_eepe": rg.money(alpha_eepe),
        "sa_ccr_ead": rg.money(sa["ead"]["amount"]), "sa_ccr_over_alpha_eepe": float(sa["ead"]["amount"] / alpha_eepe),
        "stressed": {"window_start": st["start"], "window_end": st["end"], "label": "convention", "effective_epe": rg.money(stress_eepe),
                     "hqm_spread_start": st["spread_start"], "hqm_spread_peak": st["spread_peak"],
                     "spread_rose": bool(st["spread_peak"] > st["spread_start"]), "paragraph": "CRE53.7 and CRE53.51"}}
    girr = rg.girr_block(trades, ctx["tenors"], ctx["zeros"])
    return {
        "kind": "swap-exposure", "variant": spec.variant,
        "sign_convention": {"ee": "positive-exposure-to-the-counterparty", "ene": "bank-own-exposure-reported-positive",
                            "cva": "positive-is-cost", "dva": "positive-is-benefit",
                            "statement": text("EE is the positive exposure to the counterparty, ENE the bank's own, CVA a positive cost "
                                              "and DVA a positive benefit.",
                                              "EE es la exposición positiva a la contraparte, ENE la propia del banco, CVA un costo "
                                              "positivo y DVA un beneficio positivo.")},
        "units": {"money": "amount with its ISO 4217 currency code, USD in this case", "rate": "decimal", "compounding": "continuous",
                  "time": "years-from-the-valuation-date", "mpor": "business-days", "dates": "ISO-8601"},
        "named_parameters": ctx["named"], "book": book.book_document(trades, "NS-SW1" if len(trades) == 1 else "NS-1"),
        "curve": ctx["curve_block"], "calibration_used": ctx["calibration_used"], "exposure": exposure,
        "netting_benefit": netting_benefit, "collateral": collateral, "initial_margin": initial_margin, "cva_dva": cva_blk,
        "wrong_way_risk": wwr, "sa_ccr": sa, "ba_cva": ba, "regulatory_comparison": regulatory, "girr": girr,
        "backtest": backtest_block, "calibration_sensitivity": sens, "ore_reconciliation": ore_block}


def not_applicable_ore() -> dict[str, Any]:
    reason = text("ORE's wrong-way example is a different model (a correlated credit LGM), not the Hull and White (2012) hazard on the "
                  "portfolio value, so this variant has no ORE reconciliation.",
                  "El ejemplo de riesgo de dirección equivocada de ORE es otro modelo (un LGM de crédito correlacionado), no el "
                  "hazard de Hull y White (2012) sobre el valor del portafolio, por lo que esta variante no tiene conciliación con ORE.")
    return {"status": "not-applicable", "ore_version": None, "platform": None, "run_seconds": None, "ore_ee": None,
            "ore_ee_discounted": None, "ore_eepe": None, "ore_cva": None, "ore_dim": None, "agreement": None, "eepe_agreement": None,
            "cva_agreement": None, "dim_agreement": None, "all_within_two_se": None, "reason": reason}


# ---------------------------------------------------------------------------------------------------------- findings

WHAT = {
    "ccr.pit_exposure_backtest": ("the simulated distributions against the realised curves (PIT, Anderson-Darling)",
                                  "las distribuciones simuladas frente a las curvas realizadas (PIT, Anderson-Darling)"),
    "ccr.pfe_exceedance_backtest": ("the exceedances of the PFE forecast, a secondary row (BCBS 185 paragraph 27)",
                                    "las excedencias del pronóstico de PFE, una fila secundaria (BCBS 185 párrafo 27)"),
    "ccr.reconcile_ee_profile": ("the EE profile against ORE 1.8.17.0", "el perfil de EE frente a ORE 1.8.17.0"),
    "ccr.ore_eepe_agreement": ("the EEPE against ORE 1.8.17.0", "el EEPE frente a ORE 1.8.17.0"),
    "ccr.ore_cva_agreement": ("the CVA against ORE 1.8.17.0", "el CVA frente a ORE 1.8.17.0"),
    "ccr.ore_dim_agreement": ("the mean initial margin against ORE's dim_cube", "el margen inicial medio frente al dim_cube de ORE"),
}
#: the measures of a finding ("book", "risk factor", a reconciliation case) in Spanish (U16-R2 b06 B2: "(book)" in a Spanish title)
MEASURE_ES = {"book": "cartera", "risk factor": "factor de riesgo", "risk-factor": "factor de riesgo",
              "minimum-transfer-amount-0": "monto mínimo de transferencia 0"}
#: the light of a finding as a feminine adjective of "fila", singular and plural
ROW_LIGHT_ES = {"red": ("roja", "rojas"), "amber": ("ámbar", "ámbar")}
_SEG = re.compile(r"-(10bd|20bd|1m|3m|6m|12m)(-q\d+)?$")
SEVERITY = {"red": "S2", "amber": "S3"}


def findings_of(tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One finding per kind of non-green row (test, light, measure), not one per row. A red level test is S2 and an amber one S3
    (the product's severity policy, FindingsView); the status is open: every effect here is a result to read, and the causes the
    case page marks UNVERIFIED stay open."""
    groups: dict[tuple[str, str, str], list[str]] = {}
    for r in tests:
        if r["light"] not in SEVERITY:
            continue
        seg = r.get("segment") or ""
        key = (r["test_id"], r["light"], _SEG.sub("", seg))
        ident = f"{r['test_id']}@{r['model_id']}" + (f"@{seg}" if seg else "")
        groups.setdefault(key, []).append(ident)
    out = []
    for n, ((tid, light, measure), ids) in enumerate(sorted(groups.items()), start=1):
        en, es = WHAT.get(tid, (tid, tid))
        tag = f" ({measure})" if measure else ""
        tag_es = f" ({MEASURE_ES.get(measure, measure)})" if measure else ""
        n_rows = len(ids)
        row_es = "fila" if n_rows == 1 else "filas"
        light_es = ROW_LIGHT_ES[light][0 if n_rows == 1 else 1]
        out.append({"id": f"C12-F{n:02d}", "severity": SEVERITY[light], "status": "open", "evidence": ids,
                    "title": text(f"{len(ids)} {light} row(s) on {en}{tag}", f"{number(n_rows, 0, lang='es')} {row_es} {light_es} sobre {es}{tag_es}")})
    return out
