"""The roll-forward of C06 between two reporting dates (CT-510): the IFRS 7 35H allowance and 35I gross carrying amount
tables by stage, the waterfall that opens into them, and the stage flows.

Between the opening date R0 (twelve months before the reporting date) and the closing date R, every loan of either book
is in exactly one class, and each class moves the allowance and the gross carrying amount by a fixed rule:

* continuing (in both books): a transfer when its stage changed (out of the old stage at the amount held at R0 on the old
  basis, into the new stage at the amount R0 gives on the new basis, so the cliff is the difference), then the
  re-measurement to the closing amount, split into ``macro-update`` (the change of the gap between the weighted and the
  baseline-scenario ECL) and ``remeasurement`` (the rest: seasoning, the refitted model, the new data);
* left by repayment or maturity: ``derecognition`` of its allowance, ``repayments`` of its balance;
* left by charge-off: the SBA file shows no stage between the dates, so the loan passes Stage 1 to Stage 2 (when it was in
  Stage 1) to Stage 3 and is written off in the window: the Stage 3 allowance is the amount charged off (the engine's
  ``stage3_ecl`` with no recovery), then ``write-off`` removes it;
* new (approved in the window): ``originations`` at the closing amount in the closing stage.

Opening plus movements equals closing by construction; the engine (``reconciliation``) builds the rows and judges the
identities. Overlays are separate lines carried in their stage (stage 1 for a portfolio-level overlay); the model amounts
never include them.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.provisions import ecl as rv_ecl
from riskvalidation.provisions import overlays as rv_ov
from riskvalidation.provisions import reconciliation as rv_rc
from riskvalidation.provisions.overlays import Overlay
from riskvalidation.provisions.reconciliation import RollForwardRow

from .panel import EXIT_DEFAULT, EXIT_MATURED, EXIT_PAID, Loans
from .run import DateRun

STAGES = ("stage1", "stage2", "stage3")
ALLOWANCE_LINES = ("originations", "transfer-1-2", "transfer-2-3", "transfer-2-1", "remeasurement", "macro-update", "write-off",
                   "derecognition")
GCA_LINES = ("originations", "transfer-1-2", "transfer-2-3", "transfer-2-1", "repayments", "write-off")
LABELS = {
    "opening": ("Opening allowance", "Cobertura inicial"),
    "originations": ("Originations", "Originaciones"),
    "transfer-1-2": ("Transfer 1 to 2", "Traspaso 1 a 2"),
    "transfer-2-3": ("Transfer 2 to 3", "Traspaso 2 a 3"),
    "transfer-2-1": ("Transfer 2 to 1", "Traspaso 2 a 1"),
    "remeasurement": ("Re-measurement", "Remedición"),
    "macro-update": ("Macro update", "Actualización macro"),
    "write-off": ("Write-off", "Castigo"),
    "derecognition": ("Derecognition (repaid or matured)", "Baja (pagado o vencido)"),
    "closing": ("Closing allowance", "Cobertura final"),
}


@dataclass(frozen=True)
class RollForward:
    allowance: list[RollForwardRow]
    gca: list[RollForwardRow]
    waterfall: list[dict[str, Any]]
    flows: list[dict[str, Any]]
    stage_ecl: dict[str, float]
    n_new: int
    n_continuing: int
    n_repaid: int
    n_defaulted: int


def _text(key: str) -> dict[str, str]:
    en, es = LABELS[key]
    return {"en": en, "es": es}


def _basis(stage: np.ndarray, e12: np.ndarray, e_life: np.ndarray) -> np.ndarray:
    return np.where(stage == 1, e12, e_life)


def _put(rows: dict[str, dict[str, float]], stage: int, line: str, amount: float) -> None:
    rows[STAGES[stage - 1]][line] += float(amount)


def stage3_amount(loans: Loans, idx: np.ndarray, gca0: np.ndarray, eir: np.ndarray) -> np.ndarray:
    """The Stage 3 allowance of a loan charged off in the window: its charge-off amount (the file shows no recovery),
    through the engine's ``stage3_ecl`` with no expected recovery. A charge-off with no amount takes its modelled balance."""
    coa = loans.chargeoff_amount[idx]
    gross = np.where(np.isfinite(coa), coa, gca0)
    if gross.size == 0:
        return gross
    return rv_ecl.stage3_ecl(gross, np.zeros((gross.size, 1)), np.ones((gross.size, 1)), eir)


def build_rollforward(loans: Loans, run0: DateRun, run1: DateRun, overlays: Sequence[Overlay] = (),
                      currency: str = "USD") -> RollForward:
    """The 35H and 35I tables, the waterfall and the stage flows from ``run0`` to ``run1`` (see the module text)."""
    rv_ov.check_unique(overlays)
    stage0, stage1 = run0.stage.astype(np.int64), run1.stage.astype(np.int64)
    e12_w0, el_w0 = run0.weighted(run0.ecl12), run0.weighted(run0.ecl_life)
    e12_w1, el_w1 = run1.weighted(run1.ecl12), run1.weighted(run1.ecl_life)
    base = 0  # scenario 0 is the baseline
    in1 = np.isin(run0.idx, run1.idx, assume_unique=True)
    c0 = np.flatnonzero(in1)
    order = np.argsort(run1.idx)
    c1 = order[np.searchsorted(run1.idx[order], run0.idx[c0])]
    left = np.flatnonzero(~in1)
    new = np.setdiff1d(np.arange(run1.a), c1, assume_unique=True)

    allow = {s: {ln: 0.0 for ln in ALLOWANCE_LINES} for s in STAGES}
    gca = {s: {ln: 0.0 for ln in GCA_LINES} for s in STAGES}
    flows: dict[tuple[str, str], list[float]] = {}

    def flow(src: str, dst: str, n: int, amount: float) -> None:
        f = flows.setdefault((src, dst), [0, 0.0])
        f[0] += int(n)
        f[1] += amount

    open_a = np.zeros(3)
    open_g = np.zeros(3)
    close_a = np.zeros(3)
    close_g = np.zeros(3)
    for s in (1, 2):
        open_a[s - 1] = _basis(stage0, e12_w0, el_w0)[stage0 == s].sum()
        open_g[s - 1] = run0.gca[stage0 == s].sum()
        close_a[s - 1] = _basis(stage1, e12_w1, el_w1)[stage1 == s].sum()
        close_g[s - 1] = run1.gca[stage1 == s].sum()

    # continuing loans
    s0, s1 = stage0[c0], stage1[c1]
    old_amt = _basis(s0, e12_w0[c0], el_w0[c0])
    e0_new = _basis(s1, e12_w0[c0], el_w0[c0])
    e0b_new = _basis(s1, run0.ecl12[base][c0], run0.ecl_life[base][c0])
    e1 = _basis(s1, e12_w1[c1], el_w1[c1])
    e1b = _basis(s1, run1.ecl12[base][c1], run1.ecl_life[base][c1])
    macro_i = (e1 - e1b) - (e0_new - e0b_new)
    remeas_i = e1 - e0_new - macro_i
    g0, g1 = run0.gca[c0], run1.gca[c1]
    for s in (1, 2):
        m = s1 == s
        _put(allow, s, "remeasurement", remeas_i[m].sum())
        _put(allow, s, "macro-update", macro_i[m].sum())
        _put(gca, s, "repayments", (g1[m] - g0[m]).sum())
    for a_, b_, line in ((1, 2, "transfer-1-2"), (2, 1, "transfer-2-1")):
        m = (s0 == a_) & (s1 == b_)
        if m.any():
            _put(allow, a_, line, -old_amt[m].sum())
            _put(allow, b_, line, e0_new[m].sum())
            _put(gca, a_, line, -g0[m].sum())
            _put(gca, b_, line, g0[m].sum())
    for a_ in (1, 2):
        for b_ in (1, 2):
            m = (s0 == a_) & (s1 == b_)
            if m.any():
                flow(STAGES[a_ - 1], STAGES[b_ - 1], int(m.sum()), float(g1[m].sum()))

    # loans that left
    kinds = run1.obs.end_kind[run0.idx[left]]
    sl = stage0[left]
    old_l = _basis(sl, e12_w0[left], el_w0[left])
    gl = run0.gca[left]
    repaid = (kinds == EXIT_PAID) | (kinds == EXIT_MATURED)
    dflt = kinds == EXIT_DEFAULT
    for s in (1, 2):
        m = repaid & (sl == s)
        _put(allow, s, "derecognition", -old_l[m].sum())
        _put(gca, s, "repayments", -gl[m].sum())
        if m.any():
            flow(STAGES[s - 1], "derecognised", int(m.sum()), float(gl[m].sum()))
    e_d = np.zeros(left.size)
    if dflt.any():
        e_d[dflt] = stage3_amount(loans, run0.idx[left][dflt], gl[dflt], run0.eir[left][dflt])
    for s in (1, 2):
        m = dflt & (sl == s)
        if not m.any():
            continue
        if s == 1:
            _put(allow, 1, "transfer-1-2", -e12_w0[left][m].sum())
            _put(allow, 2, "transfer-1-2", el_w0[left][m].sum())
            _put(gca, 1, "transfer-1-2", -gl[m].sum())
            _put(gca, 2, "transfer-1-2", gl[m].sum())
        _put(allow, 2, "transfer-2-3", -el_w0[left][m].sum())
        _put(allow, 3, "transfer-2-3", e_d[m].sum())
        _put(allow, 3, "write-off", -e_d[m].sum())
        _put(gca, 2, "transfer-2-3", -gl[m].sum())
        _put(gca, 3, "transfer-2-3", gl[m].sum())
        _put(gca, 3, "write-off", -gl[m].sum())
        flow(STAGES[s - 1], "written-off", int(m.sum()), float(gl[m].sum()))

    # new loans
    sn = stage1[new]
    en = _basis(sn, e12_w1[new], el_w1[new])
    for s in (1, 2):
        m = sn == s
        _put(allow, s, "originations", en[m].sum())
        _put(gca, s, "originations", run1.gca[new][m].sum())
        if m.any():
            flow("new", STAGES[s - 1], int(m.sum()), float(run1.gca[new][m].sum()))

    # overlays: separate lines, carried in their stage (stage 1 for a portfolio-level overlay)
    ov_lines = rv_ov.overlay_lines(overlays)
    for o in overlays:
        st = o.stage or "stage1"
        k = STAGES.index(st) if st in STAGES else 0
        close_a[k] += o.amount
    for st in STAGES:
        for o in overlays:
            allow[st][f"overlay-{o.id}"] = 0.0
    for o in overlays:
        allow[o.stage or "stage1"][f"overlay-{o.id}"] = float(o.amount)

    allowance_rows, gca_rows = [], []
    for k, st in enumerate(STAGES):
        allowance_rows.append(rv_rc.allowance_rollforward(st, float(open_a[k]), allow[st], float(close_a[k])))
        gca_rows.append(rv_rc.gca_rollforward(st, float(open_g[k]), gca[st], float(close_g[k])))
    lines: list[dict[str, Any]] = [{"id": "opening", "kind": "opening", "label": _text("opening"), "amount": float(open_a.sum()),
                                    "stage": None, "overlay_id": None}]
    for ln in ALLOWANCE_LINES:
        if ln in ("write-off", "derecognition"):
            continue
        lines.append({"id": ln, "kind": ln, "label": _text(ln), "amount": float(sum(allow[s][ln] for s in STAGES)), "stage": None,
                      "overlay_id": None})
    ov_by_id = {o.id: o for o in overlays}
    for ol in ov_lines:
        o = ov_by_id[ol["overlay_id"]]
        lines.append({"id": ol["id"], "kind": "overlay", "label": {"en": o.rationale_en, "es": o.rationale_es},
                      "amount": float(ol["amount"]), "stage": ol["stage"], "overlay_id": ol["overlay_id"]})
    for ln in ("write-off", "derecognition"):
        lines.append({"id": ln, "kind": ln, "label": _text(ln), "amount": float(sum(allow[s][ln] for s in STAGES)), "stage": None,
                      "overlay_id": None})
    lines.append({"id": "closing", "kind": "closing", "label": _text("closing"), "amount": float(close_a.sum()), "stage": None,
                  "overlay_id": None})
    by_stage = rv_ecl.portfolio_allowance(stage1, e12_w1, el_w1, np.zeros(run1.a)).by_stage
    stage_ecl = {k: float(v) for k, v in by_stage.items()}
    flow_rows = [{"source": a_, "target": b_, "accounts": int(n_), "gross_carrying_amount": float(g_)}
                 for (a_, b_), (n_, g_) in sorted(flows.items())]
    return RollForward(allowance=allowance_rows, gca=gca_rows, waterfall=lines, flows=flow_rows, stage_ecl=stage_ecl,
                       n_new=int(new.size), n_continuing=int(c0.size), n_repaid=int(repaid.sum()), n_defaulted=int(dflt.sum()))
