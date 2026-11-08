"""The shared core of the experiments of the manuscript on the Unidad de Fomento as its own currency.

A *treatment* is five switches that say how the UF (UR) leg of a bank is measured: on its own curve or on the peso curve,
with its own shock sizes or the peso sizes, with its own floor (-2 percent) or the peso floor (0), with the 50 percent
CLP/CLF pair rule or with a plain sum of the two legs, and with the indexation charge or without it. All switches on is
the RAN 21-13 Annex 1 measure that the product bakes for case C15; all off is the single-currency treatment of the same
flows. Every number comes from a ``riskvalidation`` call on the flows of a Banco Andino book that the case's own generator
(``pipeline.cases.c15.book``) builds and on the curves that the case's own code (``pipeline.cases.c15.curves``) fits from
the raw Banco Central de Chile F022 files; this module builds no flow and no curve of its own.

The raw files are read from ``CONTRASTE_DATA`` (``<root>/raw/bcch-f022``) or from the ``--data`` argument of the script.
"""
from __future__ import annotations

import dataclasses
import itertools
import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "data-pipeline"))
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))

from pipeline.cases.c15 import assumptions as asm  # noqa: E402
from pipeline.cases.c15 import book as bk  # noqa: E402
from pipeline.cases.c15 import curves as cv  # noqa: E402
from pipeline.cases.c15 import variant as vt  # noqa: E402
from riskvalidation.irrbb import eve_nii, shocks  # noqa: E402

import figkit  # noqa: E402

MID = bk.MID
SHOCKS = shocks.SHOCKS
MONTH = "2026-09"
CASE_SEED = 42
SWITCHES = ("curve", "sizes", "floor", "pair", "charge")
NII_BP = vt.NII_BP


@dataclass(frozen=True)
class Treatment:
    """Which parts of the separate UF treatment are on (True) or replaced by the single-currency choice (False)."""

    curve: bool = True
    sizes: bool = True
    floor: bool = True
    pair: bool = True
    charge: bool = True

    def on(self) -> tuple[str, ...]:
        return tuple(s for s in SWITCHES if getattr(self, s))


ANNEX1 = Treatment()
SINGLE = Treatment(False, False, False, False, False)


def treatment_from(on: set[str]) -> Treatment:
    return Treatment(**{s: (s in on) for s in SWITCHES})


@dataclass
class Context:
    """The curves, the UF value and the valuation date of one run."""

    sel: cv.Selection
    fits: dict[str, cv.CurveFit]
    uf: float
    uf_source: str

    @property
    def date(self) -> str:
        return self.sel.valuation_date


def data_root(arg: str | None = None) -> pathlib.Path:
    root = arg or os.environ.get("CONTRASTE_DATA")
    if not root:
        raise SystemExit("pass --data or set CONTRASTE_DATA to the device data root that holds raw/bcch-f022")
    return pathlib.Path(root)


def load_raw(arg: str | None = None) -> cv.RawSet:
    return cv.load_raw(data_root(arg))


def context(raw: cv.RawSet, day: str | None = None, month: str = MONTH, level_shift_bp: float = 0.0) -> Context:
    """The case's selection of the month (its last common day) or of another business day of the month, and its fitted curves.

    ``level_shift_bp`` translates the UR curve by that many basis points (a what-if on the level of the real curve, used only by
    the floor experiment); 0 leaves the fit as the case's code made it.
    """
    sel = cv.select(raw.series, raw.infos, month)
    if day is not None and day != sel.valuation_date:
        sel = dataclasses.replace(sel, valuation_date=day)
    fits = {n: cv.fit_curve(sel, raw.series, n) for n in ("CLP", "UR")}
    uf, source = cv.uf_value(sel, raw.series)
    if level_shift_bp:
        shifted = fits["UR"].rates + level_shift_bp / 1e4
        fits["UR"] = dataclasses.replace(fits["UR"], rates=shifted)
    return Context(sel, fits, uf, source)


def common_days(raw: cv.RawSet, month: str = MONTH) -> list[str]:
    """The days of the month on which every chosen series and the UF value have an observation."""
    sel = cv.select(raw.series, raw.infos, month)
    codes = [c.code for c in sel.chosen] + [cv.UF_CODE]
    sets = [set(d for d in raw.series[c].values() if sel.first <= d <= sel.last) for c in codes]
    return sorted(set.intersection(*sets))


# ------------------------------------------------------------------------------------------------ the measures


def _prepare(book: bk.Book, ctx: Context) -> dict[str, Any]:
    conv = {"CLP": 1.0, "UR": ctx.uf}
    items = {n: book.legs[n].items for n in ("CLP", "UR")}
    base = {n: sum(it.flows * conv[n] for it in items[n]) for n in items}
    return {"conv": conv, "items": items, "base": base, "pn_ur": book.net_uf_position * ctx.uf, "tier1": book.tier1}


def leg_deltas(book: bk.Book, ctx: Context, tr: Treatment, floor_override: dict[str, float | None] | None = None) -> dict[str, Any]:
    """The loss-positive delta EVE of each leg under the six shocks and the delta NII under the two 300 bp shocks.

    The CLP leg is always on its own curve, sizes and floor. The UR leg follows the treatment: the UR curve or the peso curve, the UR
    sizes (200/250/150 bp) or the peso sizes (300/400/200 bp), the floor of -2 percent or 0. The flows, including the term-deposit
    redemption that depends on the shock, are the case's (``variant._net_flows``). ``floor_override`` replaces the floor of a leg (None for
    no floor).
    """
    p = _prepare(book, ctx)
    r0 = {"CLP": ctx.fits["CLP"].rates, "UR": ctx.fits["UR" if tr.curve else "CLP"].rates}
    size = {"CLP": shocks.shock_size("CLP", "cmf-annex1"), "UR": shocks.shock_size("CLF" if tr.sizes else "CLP", "cmf-annex1")}
    floor: dict[str, float | None] = {"CLP": vt.OTHER_FLOOR, "UR": vt.UR_FLOOR if tr.floor else vt.OTHER_FLOOR}
    if floor_override:
        floor.update(floor_override)          # None removes the floor of that leg (used only by the floor experiment)
    tdrr0 = asm.TERM_DEPOSIT_REDEMPTION_RATE
    eve_d = {"CLP": [], "UR": []}
    for s in SHOCKS:
        for n in ("CLP", "UR"):
            z = size[n]
            shape = shocks.shock_curve(s, z.parallel_bp, z.short_bp, z.long_bp, MID)
            shocked = shocks.apply_floor(r0[n], shape, floor[n])
            net = vt._net_flows(p["items"][n], p["conv"][n], s, tdrr0)
            eve_d[n].append(float(eve_nii.delta_eve(p["base"][n], net, r0[n], shocked, MID, kao=0.0)))
    nii_d = {"CLP": [], "UR": []}
    for bp in (NII_BP, -NII_BP):
        for n in ("CLP", "UR"):
            shocked = shocks.apply_floor(r0[n], np.full(19, bp), floor[n])
            nii_d[n].append(float(eve_nii.delta_nii(p["base"][n], r0[n], shocked, MID)))
    return {"eve": {k: np.array(v) for k, v in eve_d.items()}, "nii": {k: np.array(v) for k, v in nii_d.items()},
            "pn_ur": p["pn_ur"], "tier1": p["tier1"]}


def aggregate(d: dict[str, Any], tr: Treatment) -> dict[str, float]:
    """The two measures from the leg deltas: the Annex 1 pair rule with its 50 percent offset or a plain sum of the legs."""
    pn = d["pn_ur"]
    charge = float(eve_nii.indexation_charge(pn)) if tr.charge else 0.0
    if tr.pair:
        a1 = eve_nii.annex1_delta_eve(d["eve"]["CLP"], d["eve"]["UR"], True)
        a2 = eve_nii.annex1_delta_nii(d["nii"]["CLP"], d["nii"]["UR"], pn if tr.charge else 0.0, True)
        return {"delta_eve": float(a1.delta_eve), "delta_nii": float(a2.delta_nii), "max_pair": float(a2.max_pair), "charge": float(a2.indexation_charge)}
    eve_sum = max(0.0, float(np.max(d["eve"]["CLP"] + d["eve"]["UR"])))
    nii_sum = max(0.0, float(np.max(d["nii"]["CLP"] + d["nii"]["UR"])))
    return {"delta_eve": eve_sum, "delta_nii": nii_sum + charge, "max_pair": nii_sum, "charge": charge}


def positive_parts(d: dict[str, Any]) -> dict[str, float]:
    """The aggregation of the Basel standard across currencies: the positive parts add and a gain in one currency never offsets a loss in
    another (``eve_risk_measure``; the NII form is the same maximum over the two shocks), with the case's curves, sizes and floors and
    no indexation charge."""
    m = np.column_stack([d["eve"]["CLP"], d["eve"]["UR"]])
    nii = np.column_stack([d["nii"]["CLP"], d["nii"]["UR"]])
    return {"delta_eve": float(eve_nii.eve_risk_measure(m)), "delta_nii": float(max(0.0, np.max(np.where(nii > 0.0, nii, 0.0).sum(axis=1))))}


def measures(book: bk.Book, ctx: Context, tr: Treatment) -> dict[str, float]:
    d = leg_deltas(book, ctx, tr)
    out = aggregate(d, tr)
    out["tier1"] = d["tier1"]
    out["pn_ur"] = d["pn_ur"]
    return out


def gap_measures(book: bk.Book, ctx: Context) -> dict[str, float]:
    """The textbook gap measures of the whole book in pesos, run by the engine on the same flows: the earnings change of the repricing gap
    (``delta_nii_gap``) for the two 300 bp parallel shocks and the first-order change of equity of the duration gap (``duration_gap``)
    scaled to 300 bp, each the largest loss of the two directions. The UF flows are converted at the UF value and discounted on the peso
    curve, so the book is one currency."""
    p = _prepare(book, ctx)
    asset = np.zeros(19)
    liab = np.zeros(19)
    for n in ("CLP", "UR"):
        for it in p["items"][n]:
            v = it.flows * p["conv"][n]
            if it.side == "asset":
                asset += v
            else:
                liab += -v
    gap = eve_nii.repricing_gap(asset, liab)
    nii = max(0.0, max(eve_nii.delta_nii_gap(gap, MID, NII_BP), eve_nii.delta_nii_gap(gap, MID, -NII_BP)))
    dg = eve_nii.duration_gap(asset, liab, ctx.fits["CLP"].rates, MID)
    scale = NII_BP / 100.0
    eve = max(0.0, -dg.equity_change_100bp_up * scale, dg.equity_change_100bp_up * scale)
    return {"delta_nii_gap": float(nii), "delta_eve_duration": float(eve), "duration_gap_years": float(dg.duration_gap_years)}


def prioritised(book: bk.Book, ctx: Context, m: dict[str, float], margin_12m: float) -> dict[str, bool]:
    """The three prioritised-bank tests of Annex 1 for a pair of measures (engine: ``prioritised_bank``)."""
    pb = eve_nii.prioritised_bank(m["delta_nii"], m["delta_eve"], book.tier1, margin_12m)
    return {t["id"]: bool(t["breached"]) for t in pb.tests}


# ------------------------------------------------------------------------------------------------ the decomposition


def factorial(book: bk.Book, ctx: Context) -> dict[tuple[str, ...], dict[str, float]]:
    """The 32 treatments, keyed by the sorted tuple of the switches that are on."""
    out = {}
    for bits in itertools.product((False, True), repeat=len(SWITCHES)):
        tr = Treatment(*bits)
        out[tuple(sorted(tr.on()))] = measures(book, ctx, tr)
    return out


def shapley(values: dict[tuple[str, ...], dict[str, float]], key: str) -> dict[str, float]:
    """The exact Shapley value of each switch for the measure ``key``: the average over the orderings of the five switches of the change
    the switch makes when it is turned on after the switches before it. The values add up to measure(Annex 1) - measure(single currency)."""
    n = len(SWITCHES)
    out = {}
    for j in SWITCHES:
        others = [s for s in SWITCHES if s != j]
        total = 0.0
        for r in range(n):
            for sub in itertools.combinations(others, r):
                w = _fact(r) * _fact(n - r - 1) / _fact(n)
                a = values[tuple(sorted(sub))][key]
                b = values[tuple(sorted(sub + (j,)))][key]
                total += w * (b - a)
        out[j] = total
    return out


def _fact(k: int) -> float:
    return float(np.prod(np.arange(1, k + 1))) if k > 0 else 1.0


def mean_ci(x: np.ndarray, level: float = 0.95) -> tuple[float, float, float]:
    """The mean and the half-width of its t interval over the repetitions (the standard error times the Student quantile)."""
    from scipy import stats

    x = np.asarray(x, dtype=float)
    n = x.size
    if n < 2:
        return float(x.mean()), float("nan"), float("nan")
    se = float(x.std(ddof=1) / np.sqrt(n))
    q = float(stats.t.ppf(0.5 + level / 2.0, n - 1))
    return float(x.mean()), q * se, float(x.std(ddof=1))


def committed(variant_id: str) -> dict[str, Any]:
    return figkit.doc(f"C15/{variant_id}.json")["outputs"]


def book_of(vid: str, seed: int, ctx: Context) -> bk.Book:
    return bk.build_book(seed, bk.SPECS[vid], ctx.uf)


def margin_12m(book: bk.Book, ctx: Context) -> float:
    """The 12-month net interest and indexation margin of the case: the base total of the dynamic NII of the two legs (engine: ``simulate_nii``),
    built with the case's own item rules (``variant._dyn_items``)."""
    from riskvalidation.irrbb import simulation

    p = _prepare(book, ctx)
    total = 0.0
    for n in ("CLP", "UR"):
        its = vt._dyn_items(p["items"][n], p["conv"][n], ctx.fits[n].rates)
        arrs = vt._arrays(its)
        r_short = float(ctx.fits[n].rates[1])
        rate = float(shocks.apply_floor(np.array([r_short]), np.array([0.0]), vt.UR_FLOOR if n == "UR" else vt.OTHER_FLOOR)[0])
        path = np.full(asm.HORIZON_MONTHS, rate)
        total += float(simulation.simulate_nii(*arrs, path, 0.0).total)
    return total
