"""The reconciliations of C12: the Python exposure against ORE 1.8.17.0 (decision S2), and the engine's Hull-White closed forms
against QuantLib 1.44 (decision B4). Both are test rows and, for ORE, the ``ore_reconciliation`` block of the document.

ORE's profile is the discounted exposure (its ``EPE`` column and its cube, a price that does not depend on the measure the
paths are drawn in); the undiscounted profile of the document is that divided by ``P(0, t)``, the same transformation the Python
profile goes through (see ``exposure.measures``). The Monte Carlo error of ORE's profile is the standard error of its own cube
(the net cube holds the exposure after collateral); the initial-margin variant's cube holds the exposure before initial margin
and ORE keeps no per-path DIM in its outputs, so the error of its post-IM profile is the Python one scaled to ORE's number of
samples (same law), stated in the row.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from riskvalidation.ccr import cva as cv
from riskvalidation.ccr import exposure as ex
from riskvalidation.ccr import hw1f
from riskvalidation.validation import ccr as vc

from . import ore
from . import variant as vt

K_SE = 2.0
ORE_REFERENCE = "ORE 1.8.17.0 (OpenSourceRisk Engine), xva.tex and the exposure example inputs; addendum R2 and R3"


def _flag(diff: float, comb: float) -> bool:
    return bool(abs(diff) <= K_SE * comb + 1e-12)


def _scalar(py: float, ore_v: float, comb: float) -> dict[str, Any]:
    return {"python": float(py), "ore": float(ore_v), "difference": float(ore_v - py), "combined_se": float(comb),
            "within_two_se": _flag(ore_v - py, comb)}


def ore_result(root: Path, n_report: int, scaled_se: dict[str, np.ndarray] | None) -> dict[str, Any]:
    """ORE's discounted EE and its error from the files of one run. ``scaled_se`` (the initial-margin variant) carries the
    Python errors scaled to ORE's sample count in place of a per-sample cube."""
    prof = ore.read_exposures(root)
    epe = prof["EPE"][1:]
    dates, net = ore.read_cube(root, "netcube.csv")
    pos = np.maximum(net[:, 1:], 0.0)
    if epe.size != n_report or pos.shape[1] != n_report:
        raise ValueError(f"ORE wrote {epe.size} exposure points for a report grid of {n_report}")
    if scaled_se is None:
        if not np.allclose(pos.mean(axis=0), epe, rtol=1e-6, atol=0.02):
            raise ValueError("ORE's net cube does not reproduce its EPE column")
        return {"epe": epe, "se": pos.std(axis=0, ddof=1) / np.sqrt(pos.shape[0]), "pos": pos, "samples": pos.shape[0],
                "vm_epe": None, "vm_se": None}
    return {"epe": epe, "se": scaled_se["se"], "pos": None, "samples": pos.shape[0], "vm_epe": pos.mean(axis=0),
            "vm_se": pos.std(axis=0, ddof=1) / np.sqrt(pos.shape[0]), "vm_pos": pos}


def block(c: vt.Core, ore_out: dict[str, Any], seconds: float, platform: str, curve: Any, lgd: float,
          cva_python: float, cva_python_se: float) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """The ``ore_reconciliation`` block of a reconciled variant and its test rows."""
    report, p0r, mx = c.sim.report, c.p0r, c.mx
    n_ore = ore_out["samples"]
    py_ee, py_se = mx["ee"], mx["ee_se"]
    o_ee, o_se = ore_out["epe"] / p0r, ore_out["se"] / p0r
    eff = ex.effective_ee(o_ee)
    o_eepe = ex.effective_epe(report, eff)
    s_cp = cv.default_probabilities(np.exp(-curve.spreads * np.concatenate([[0.0], report]) / lgd))
    o_cva, _ = cv.cva(ore_out["epe"], s_cp, lgd)
    scale = np.sqrt(c.x_d.shape[0] / n_ore)
    if ore_out["pos"] is not None:
        pos = ore_out["pos"]
        half = n_ore // 2
        step = max(half // 20, 1)
        batches = [np.arange(b * step * 2, (b + 1) * step * 2) for b in range(20)]
        eepes = [ex.effective_epe(report, ex.effective_ee(pos[i].mean(axis=0) / p0r)) for i in batches]
        o_eepe_se = float(np.std(eepes, ddof=1) / np.sqrt(len(eepes)))
        o_cva_se = float((lgd * (pos @ s_cp)).std(ddof=1) / np.sqrt(n_ore))
    else:
        o_eepe_se = mx["eepe_se"] * scale
        o_cva_se = cva_python_se * scale
    agreement = []
    for k, t in enumerate(report):
        comb = float(np.hypot(py_se[k], o_se[k]))
        agreement.append({"t": float(t), "difference": float(o_ee[k] - py_ee[k]), "combined_se": comb,
                          "within_two_se": _flag(o_ee[k] - py_ee[k], comb)})
    eepe_ag = _scalar(mx["eepe"], o_eepe, np.hypot(mx["eepe_se"], o_eepe_se))
    cva_ag = _scalar(cva_python, o_cva, np.hypot(cva_python_se, o_cva_se))
    flags = [a["within_two_se"] for a in agreement] + [eepe_ag["within_two_se"], cva_ag["within_two_se"]]
    blk = {"status": "reconciled", "ore_version": ore.ORE_VERSION, "platform": f"{platform}; {n_ore} samples, antithetic",
           "run_seconds": float(seconds), "ore_ee": vt.profile(o_ee, o_se), "ore_ee_discounted": vt.profile(ore_out["epe"], ore_out["se"]),
           "ore_eepe": vt.rg.money(o_eepe), "ore_cva": vt.rg.money(o_cva), "ore_dim": None, "agreement": agreement,
           "eepe_agreement": eepe_ag, "cva_agreement": cva_ag, "dim_agreement": None, "all_within_two_se": None, "reason": None}
    rows = []
    r = vc.reconcile_ee_profile(py_ee, py_se, o_ee, o_se, K_SE)
    rows.append(vt.tr(r, reference=ORE_REFERENCE, notes=(r.notes + " " if r.notes else "") + f"ORE {n_ore} samples against Python "
                      f"{c.x_d.shape[0]} paths; the profile is the t-forward EE"))
    for name, ag, what in (("ccr.ore_eepe_agreement", eepe_ag, "EEPE"), ("ccr.ore_cva_agreement", cva_ag, "CVA")):
        z = abs(ag["difference"]) / ag["combined_se"] if ag["combined_se"] > 0 else 0.0
        rows.append(vt.custom_row(
            name, "green" if ag["within_two_se"] else "red", z, abs(ag["difference"]), f"the Python {what} agrees with ORE's within "
            "the combined Monte Carlo error", f"the Python {what} departs from ORE's", ORE_REFERENCE,
            "" if ag["within_two_se"] else f"{z:.2f} combined standard errors", {"agreement": ag, "thresholds": {"k_se": K_SE}}))
    return blk, rows, flags


def finish(blk: dict[str, Any], flags: list[bool]) -> None:
    blk["all_within_two_se"] = bool(all(flags))


def ore_mean_dim(run_dir: Path, n_report: int) -> tuple[np.ndarray, np.ndarray]:
    """ORE's mean dynamic initial margin per report date and its standard error, from its dim_cube."""
    sums: dict[str, list[float]] = {}
    with open(run_dir / "output" / "dim_cube.csv", encoding="utf-8") as fh:
        next(fh)
        for line in fh:
            p = line.split(",")
            sums.setdefault(p[3], []).append(float(p[4]))
    times = sorted(sums, key=float)[1:]
    arr = np.array([sums[t] for t in times])
    if arr.shape[0] != n_report:
        raise ValueError(f"ORE's dim_cube has {arr.shape[0]} dates for a report grid of {n_report}")
    return arr.mean(axis=1), arr.std(axis=1, ddof=1) / np.sqrt(arr.shape[1])


def im_block(blk: dict[str, Any], c: vt.Core, run_dir: Path, flags: list[bool]) -> list[dict[str, Any]]:
    """The initial-margin additions: ORE's mean regression DIM (its dim_cube) against the Python one, as the document's `dim`
    agreement and a test row. The two regressions differ in scale; the gap is reported as measured, cause UNVERIFIED."""
    o_mean, o_se = ore_mean_dim(run_dir, c.sim.report.size)
    dim = c.e.dim[:, 1:]
    p_mean, p_se = dim.mean(axis=0), dim.std(axis=0, ddof=1) / np.sqrt(dim.shape[0])
    blk["ore_dim"] = vt.profile(o_mean, o_se)
    ag = []
    for k, t in enumerate(c.sim.report):
        comb = float(np.hypot(p_se[k], o_se[k]))
        ag.append({"t": float(t), "difference": float(o_mean[k] - p_mean[k]), "combined_se": comb,
                   "within_two_se": _flag(o_mean[k] - p_mean[k], comb)})
    blk["dim_agreement"] = ag
    flags += [a["within_two_se"] for a in ag]
    z = max((abs(a["difference"]) / a["combined_se"] for a in ag if a["combined_se"] > 0), default=0.0)
    ok = all(a["within_two_se"] for a in ag)
    return [vt.custom_row("ccr.ore_dim_agreement", "green" if ok else "red", z, max(abs(a["difference"]) for a in ag),
                          "the mean regression DIM of the Python run agrees with ORE's dynamic initial margin within the combined Monte Carlo error",
                          "the two regressions differ", ORE_REFERENCE,
                          "" if ok else f"the largest gap is {z:.1f} combined standard errors; ORE's mean DIM is "
                          f"{float(np.mean(o_mean / p_mean)):.3f} of the Python one on average (cause UNVERIFIED: the expected "
                          "exposure after margin agrees, see the EE profile reconciled with ORE)", {"agreement": ag})]


# ------------------------------------------------------------------------------------------------------------ QuantLib


def quantlib_rows(tenors: np.ndarray, zeros: np.ndarray, a: float, sigma: float) -> list[dict[str, Any]]:
    """The engine's zero-coupon bond option and Jamshidian swaption against QuantLib 1.44 on the same curve and parameters
    (decision B4): green when the relative difference is within 1e-6 (QuantLib solves its root to 1e-8)."""
    import QuantLib as ql

    ref = ql.Date(1, 9, 2027)
    ql.Settings.instance().evaluationDate = ref
    dc = ql.Thirty360(ql.Thirty360.BondBasis)
    months = [int(round(t * 12)) for t in tenors]
    dates = [ref] + [ref + ql.Period(m, ql.Months) for m in months]
    curve = ql.ZeroCurve(dates, [float(zeros[0])] + [float(z) for z in zeros], dc, ql.NullCalendar(), ql.Linear(), ql.Continuous)
    curve.enableExtrapolation()
    handle = ql.YieldTermStructureHandle(curve)
    model = ql.HullWhite(handle, a, sigma)
    p0, forward = hw1f.curve_functions(zeros, tenors)
    rows = []
    strike, expiry, bond = 0.85, 2.0, 5.0
    q_call = model.discountBondOption(ql.Option.Call, strike, 2.0, 5.0)
    e_call = hw1f.bond_option(True, strike, expiry, bond, a, sigma, p0)
    q_put = model.discountBondOption(ql.Option.Put, 0.93, 2.0, 5.0)
    e_put = hw1f.bond_option(False, 0.93, expiry, bond, a, sigma, p0)
    for name, q, e_, what in (("ccr.quantlib_bond_call", q_call, e_call, "call"), ("ccr.quantlib_bond_put", q_put, e_put, "put")):
        rel = abs(e_ - q) / abs(q)
        rows.append(vt.custom_row(name, "green" if rel <= 1e-6 else "red", rel, abs(e_ - q), f"the engine's zero-coupon bond {what} option "
                                  "equals QuantLib 1.44's HullWhite.discountBondOption", "the engine's closed form departs from QuantLib's",
                                  "QuantLib 1.44 hullwhite.cpp discountBondOption (addendum R4); relative difference gate 1e-6",
                                  "" if rel <= 1e-6 else f"relative difference {rel:.3g}",
                                  {"engine": float(e_), "quantlib": float(q), "expiry": expiry, "bond_maturity": bond,
                                   "a": a, "sigma": sigma}))
    index = ql.IborIndex("C12", ql.Period(6, ql.Months), 0, ql.USDCurrency(), ql.NullCalendar(), ql.Unadjusted, False, dc, handle)
    start, end = ref + ql.Period(24, ql.Months), ref + ql.Period(60, ql.Months)
    fixed_rate, notional = 0.04, 1_000_000.0
    for payer, kind in ((True, "payer"), (False, "receiver")):
        sched = ql.Schedule(start, end, ql.Period(6, ql.Months), ql.NullCalendar(), ql.Unadjusted, ql.Unadjusted,
                            ql.DateGeneration.Forward, False)
        swap = ql.VanillaSwap(ql.VanillaSwap.Payer if payer else ql.VanillaSwap.Receiver, notional, sched, fixed_rate, dc, sched, index,
                              0.0, dc)
        swaption = ql.Swaption(swap, ql.EuropeanExercise(start))
        swaption.setPricingEngine(ql.JamshidianSwaptionEngine(model, handle))
        q = swaption.NPV()
        times = np.arange(1, 7) * 0.5 + 2.0
        amounts = np.full(6, notional * fixed_rate * 0.5)
        amounts[-1] += notional
        e_ = hw1f.swaption_jamshidian(payer, 2.0, times, amounts, a, sigma, p0, forward, nominal=notional)
        rel = abs(e_ - q) / abs(q)
        rows.append(vt.custom_row(f"ccr.quantlib_swaption_{kind}", "green" if rel <= 1e-6 else "red", rel, abs(e_ - q),
                                  f"the engine's Jamshidian {kind} swaption equals QuantLib 1.44's JamshidianSwaptionEngine",
                                  "the engine's closed form departs from QuantLib's",
                                  "QuantLib 1.44 jamshidianswaptionengine.cpp (addendum R4); relative difference gate 1e-6",
                                  "" if rel <= 1e-6 else f"relative difference {rel:.3g}",
                                  {"engine": float(e_), "quantlib": float(q), "expiry": 2.0, "fixed_rate": fixed_rate, "a": a,
                                   "sigma": sigma}))
    return rows


def mta0_row(c0: vt.Core, out0: dict[str, Any], seconds: float) -> dict[str, Any]:
    """The diagnostic row: the same CSA variant with a zero minimum transfer amount in both engines. It separates the margining
    dynamics (ORE calls on its own schedule, so its MTA acts between the report dates) from the exposure model itself."""
    p0r = c0.p0r
    r = vc.reconcile_ee_profile(c0.mx["ee"], c0.mx["ee_se"], out0["epe"] / p0r, out0["se"] / p0r, K_SE)
    return vt.tr(r, segment="minimum-transfer-amount-0", reference=ORE_REFERENCE,
                 notes=(r.notes + " " if r.notes else "") + "diagnostic: the minimum transfer amount is zero in both engines "
                 f"({out0['samples']} ORE samples)")  # the wall-clock time is in run_seconds only: a note is part of the deterministic document
