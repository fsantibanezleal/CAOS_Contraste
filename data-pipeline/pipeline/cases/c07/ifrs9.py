"""The IFRS 9 regime on the book: the probability-weighted ECL, staged, with overlays as separate lines.

Every number is returned by ``riskvalidation.provisions`` (``term_structure``, ``staging``, ``ecl``, ``overlays``,
``reconciliation``) and ``riskvalidation.validation.ifrs9``; the product assembles inputs and sums (ADR-0069). The ECL of a
variant is the weighted ECL over the weighting scenarios of ``scenarios.WEIGHTING`` (IFRS 9 5.5.17(a), B5.5.42), each run at
the factor ``z_offset + z_shift`` with staging frozen at the weighted conditions; a single-scenario figure is only a
component. Convention: quarterly periods, the annual PIT PD of the one-factor model becomes a constant quarterly hazard, the
factor shock of the first year decays with a half-life of one year after it (assumption of the case).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from riskvalidation.provisions import ecl as ecl_mod
from riskvalidation.provisions import overlays as ov
from riskvalidation.provisions import reconciliation as rc
from riskvalidation.provisions import staging as stg
from riskvalidation.provisions import term_structure as ts
from riskvalidation.validation import ifrs9 as battery

from . import b1
from . import book as bk
from . import scenarios as sc
from .book import PARAMS, Book, State

CONVENTION = "mid-period"
PD_LADDER_RUNG = "L0-ttc-one-factor-constant-hazard"
STAGING_POLICY = {
    "dpd_backstop": 30, "default_dpd": 90, "threefold_ratio": 3.0, "absolute_floor": 0.005, "probation_months": 6,
    "low_credit_risk_pd": None,
    "multiplier_schedule": [{"pd_origination_upper": 0.01, "multiplier": 4.0}, {"pd_origination_upper": 0.05, "multiplier": 2.5},
                            {"pd_origination_upper": 0.99, "multiplier": 1.5}],
    "source": "Contraste policy parameters of the case (dossier 02 B.5 form: relative multiplier by origination PD, absolute floor, "
              "threefold backstop, 30 and 90 days past due); not IFRS 9 requirements",
}
STAGE_KEYS = ("stage1", "stage2", "stage3", "poci")
HALF_LIFE_QUARTERS = 4.0


def policy() -> stg.StagingPolicy:
    p = STAGING_POLICY
    return stg.StagingPolicy(
        multiplier_schedule=tuple((s["pd_origination_upper"], s["multiplier"]) for s in p["multiplier_schedule"]),
        absolute_floor=p["absolute_floor"], threefold_ratio=p["threefold_ratio"], dpd_backstop=p["dpd_backstop"],
        default_dpd=p["default_dpd"], probation_months=p["probation_months"], low_credit_risk_pd=p["low_credit_risk_pd"])


@dataclass
class Ifrs9Result:
    stage: np.ndarray                         # (A,) int8
    trigger: np.ndarray
    weights: np.ndarray
    z: np.ndarray                             # factor of each weighting scenario (offset plus shift)
    e12: np.ndarray                           # (S, A) discounted 12-month ECL by weighting scenario
    life: np.ndarray                          # (S, A) discounted lifetime ECL
    s3: np.ndarray                            # (A,) stage 3 ECL, discounted at the EIR
    e12_u: np.ndarray                         # undiscounted
    life_u: np.ndarray
    s3_u: np.ndarray
    e12_mean: np.ndarray                      # at the weighted mean factor (A,)
    life_mean: np.ndarray
    lgd: np.ndarray
    ead_first_year: np.ndarray
    pd_cur: np.ndarray
    pd_orig: np.ndarray
    extras: dict[str, Any] = field(default_factory=dict)


def _z_path(n: int, z0: float) -> np.ndarray:
    t = np.arange(1, n + 1, dtype=float)
    return np.where(t <= 4.0, z0, z0 * 0.5 ** ((t - 4.0) / HALF_LIFE_QUARTERS))


def _ead(e: np.ndarray, rem: np.ndarray, amortising: np.ndarray, months: np.ndarray) -> np.ndarray:
    mid = (months - 1.5)[None, :]
    inside = mid < rem[:, None]
    lin = np.clip(1.0 - mid / rem[:, None], 0.0, 1.0)
    return e[:, None] * np.where(amortising[:, None], lin, 1.0) * inside


def staged(book: Book, state: State, weighted_z: np.ndarray, weights: np.ndarray) -> stg.StageResult:
    """Staging at the weighted conditions: origination PD against the current PD, both weighted over the same scenarios."""
    pit_orig = np.zeros(book.n)
    pit_cur = np.zeros(book.n)
    for k, rho in enumerate(np.unique(book.rho)):
        m = book.rho == rho
        for w, zo in zip(weights, [s["z_offset"] for s in sc.WEIGHTING], strict=True):
            pit_orig[m] += w * ts.ttc_to_pit(book.pd_orig[m], float(rho), np.full(int(m.sum()), zo))
            pit_cur[m] += w * ts.ttc_to_pit(book.pd_now[m], float(rho), np.full(int(m.sum()), zo + state.z_shift))
    res = stg.allocate_stages(pit_orig, pit_cur, state.dpd.astype(np.int64), book.forborne, state.watch, state.default, policy())
    return res, pit_orig, pit_cur  # type: ignore[return-value]


def run(book: Book, state: State) -> Ifrs9Result:
    """The staged ECL by weighting scenario, discounted and undiscounted, 12-month and lifetime, for every account."""
    weights = np.array([s["weight"] for s in sc.WEIGHTING])
    offsets = np.array([s["z_offset"] for s in sc.WEIGHTING])
    z = offsets + state.z_shift
    z_mean = float(np.dot(weights, offsets) + state.z_shift)
    stage_res, pit_orig, pit_cur = staged(book, state, z, weights)
    r = b1.recovery(book, state.hpi)
    lgd = 1.0 - r
    n_s = len(weights)
    e12 = np.zeros((n_s, book.n))
    life, e12_u, life_u = np.zeros_like(e12), np.zeros_like(e12), np.zeros_like(e12)
    e12_mean, life_mean = np.zeros(book.n), np.zeros(book.n)
    zero_eir = np.zeros(book.n)
    for sid in range(len(bk.SEGMENTS)):
        idx = np.flatnonzero(book.seg == sid)
        if idx.size == 0:
            continue
        tmax = int(book.rem[idx].max())
        months = np.arange(3, tmax + 1, 3, dtype=np.int64)
        ead = _ead(book.e[idx], book.rem[idx].astype(float), book.amortising[idx], months)
        rho = float(book.rho[idx][0])
        eir = book.eir[idx]
        for s_i, zs in enumerate(list(z) + [z_mean]):
            zp = _z_path(months.size, float(zs))
            pit = ts.ttc_to_pit(book.pd_now[idx][:, None], rho, zp[None, :])
            haz = 1.0 - (1.0 - pit) ** 0.25
            q = ts.from_hazard(haz, months).marginal
            if s_i < n_s:
                e12[s_i, idx] = ecl_mod.ecl_scenario(q, lgd[idx], ead, eir, months, 12, CONVENTION)
                life[s_i, idx] = ecl_mod.ecl_scenario(q, lgd[idx], ead, eir, months, int(months[-1]), CONVENTION)
                e12_u[s_i, idx] = ecl_mod.ecl_scenario(q, lgd[idx], ead, zero_eir[idx], months, 12, CONVENTION)
                life_u[s_i, idx] = ecl_mod.ecl_scenario(q, lgd[idx], ead, zero_eir[idx], months, int(months[-1]), CONVENTION)
            else:
                e12_mean[idx] = ecl_mod.ecl_scenario(q, lgd[idx], ead, eir, months, 12, CONVENTION)
                life_mean[idx] = ecl_mod.ecl_scenario(q, lgd[idx], ead, eir, months, int(months[-1]), CONVENTION)
    k1, k2 = PARAMS["recovery_months"]
    cf = np.stack([0.5 * r * book.e, 0.5 * r * book.e], axis=1)
    mo = np.tile(np.array([[k1, k2]], dtype=float), (book.n, 1))
    s3 = ecl_mod.stage3_ecl(book.e, cf, mo, book.eir)
    s3_u = ecl_mod.stage3_ecl(book.e, cf, mo, np.zeros(book.n))
    return Ifrs9Result(stage_res.stage.astype(np.int64), stage_res.trigger, weights, z, e12, life, s3, e12_u, life_u, s3_u,
                       e12_mean, life_mean, lgd, np.zeros(0), pit_cur, pit_orig, {"z_mean": z_mean})


def pick(res: Ifrs9Result, k: int | None = None, mean: bool = False, undiscounted: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The (12-month, lifetime, stage 3) arrays of one weighting scenario, of the weighted measure (k None) or the mean path."""
    if mean:
        return res.e12_mean, res.life_mean, res.s3
    e12, life, s3 = (res.e12_u, res.life_u, res.s3_u) if undiscounted else (res.e12, res.life, res.s3)
    if k is None:
        return (ecl_mod.probability_weighted_ecl(e12, res.weights), ecl_mod.probability_weighted_ecl(life, res.weights), s3)
    return e12[k], life[k], s3


def allowance(res: Ifrs9Result, overlays: tuple[ov.Overlay, ...] = (), k: int | None = None, mean: bool = False,
              undiscounted: bool = False) -> ecl_mod.AllowanceBreakdown:
    a, b, c = pick(res, k, mean, undiscounted)
    return ecl_mod.portfolio_allowance(res.stage, a, b, c, overlays=overlays)


def account_ecl(res: Ifrs9Result, k: int | None = None) -> np.ndarray:
    """The model ECL of each account under the weighted measure (or one component): by its stage."""
    a, b, c = pick(res, k)
    return np.where(res.stage == 1, a, np.where(res.stage == 2, b, c))


def overlays_for(base: Ifrs9Result, book: Book, currency: str) -> tuple[ov.Overlay, ...]:
    """Two expert overlays sized once on the base model ECL and fixed in CLP for every variant (management judgement at the
    reporting date, assumption of the case): house price outlook on high-LTV mortgages (Stage 2), card utilisation drift
    (Stage 1)."""
    ecl = account_ecl(base)
    gt80 = bk.SEG_IDS.index("mortgage-ltv-gt80")
    cards = bk.SEG_IDS.index("consumer-cards")
    a_house = 0.10 * float(ecl[(book.seg == gt80) & (base.stage == 2)].sum())
    a_cards = 0.08 * float(ecl[(book.seg == cards) & (base.stage == 1)].sum())
    return (
        ov.Overlay(id="OVL-HOUSING", rationale_en="House price outlook on high-LTV mortgages, not in the model (expert, "
                   "assumption of the case: 10 per cent of the base Stage 2 ECL of the segment)",
                   rationale_es="Perspectiva de precios de viviendas en hipotecarios de PVG alto, fuera del modelo (experto, "
                   "supuesto del caso: 10 % de la PCE de Etapa 2 del segmento en el base)",
                   method="expert", target="lgd", segment_id="mortgage-ltv-gt80", stage="stage2", amount=round(a_house, 0),
                   staging_effect="none", review_date="2026-08-31", currency=currency),
        ov.Overlay(id="OVL-CARDS", rationale_en="Card utilisation drift not in the model (expert, assumption of the case: "
                   "8 per cent of the base Stage 1 ECL of the segment)",
                   rationale_es="Deriva de uso de tarjetas fuera del modelo (experto, supuesto del caso: 8 % de la PCE de "
                   "Etapa 1 del segmento en el base)",
                   method="expert", target="ead", segment_id="consumer-cards", stage="stage1", amount=round(a_cards, 0),
                   staging_effect="none", review_date="2026-08-31", currency=currency),
    )


def stage_gca(res: Ifrs9Result, book: Book) -> dict[str, tuple[int, float]]:
    return {f"stage{s}": (int((res.stage == s).sum()), float(book.e[res.stage == s].sum())) for s in (1, 2, 3)}


# --- the base-to-variant allowance bridge (IFRS 7 35H and 35I form) -----------------------------------------------------


def rollforward(base: Ifrs9Result, var: Ifrs9Result, book: Book, overlays: tuple[ov.Overlay, ...]) -> dict[str, Any]:
    """Allowance (35H) and gross carrying amount (35I) roll-forwards from the base model to a variant, with the stage
    transfers carrying the base amount, a remeasurement line per stage and each overlay as its own line; every row and
    identity is the engine's."""
    ecl_b, ecl_v = account_ecl(base), account_ecl(var)
    moves_a: dict[str, dict[str, float]] = {k: {} for k in STAGE_KEYS}
    moves_g: dict[str, dict[str, float]] = {k: {} for k in STAGE_KEYS}
    chain = {(1, 2): [(1, 2)], (2, 3): [(2, 3)], (1, 3): [(1, 2), (2, 3)], (2, 1): [(2, 1)], (3, 2): [(3, 2)],
             (3, 1): [(3, 2), (2, 1)]}
    for (a, b), steps in chain.items():
        m = (base.stage == a) & (var.stage == b)
        if not np.any(m):
            continue
        amount, gca = float(ecl_b[m].sum()), float(book.e[m].sum())
        for (x, y) in steps:
            line = f"transfer-{x}-{y}"
            moves_a[f"stage{x}"][line] = moves_a[f"stage{x}"].get(line, 0.0) - amount
            moves_a[f"stage{y}"][line] = moves_a[f"stage{y}"].get(line, 0.0) + amount
            moves_g[f"stage{x}"][line] = moves_g[f"stage{x}"].get(line, 0.0) - gca
            moves_g[f"stage{y}"][line] = moves_g[f"stage{y}"].get(line, 0.0) + gca
    carried = rc.carried_by_stage(overlays)
    stage_ecl_v = {f"stage{s}": float(ecl_v[var.stage == s].sum()) for s in (1, 2, 3)} | {"poci": 0.0}
    stage_ecl_b = {f"stage{s}": float(ecl_b[base.stage == s].sum()) for s in (1, 2, 3)} | {"poci": 0.0}
    gca_b, gca_v = stage_gca(base, book), stage_gca(var, book)
    allowance_rows, gca_rows = [], []
    for k in STAGE_KEYS[:3]:
        opening = stage_ecl_b[k]
        for o in overlays:
            if o.carried_stage == k:
                moves_a[k][f"overlay-{o.id}"] = float(o.amount)
        mv = dict(moves_a[k])
        closing = stage_ecl_v[k] + carried[k]
        mv["remeasurement"] = closing - opening - sum(mv.values())
        allowance_rows.append(rc.allowance_rollforward(k, opening, mv, closing))
        g_open, g_close = gca_b[k][1], gca_v[k][1]
        mv_g = dict(moves_g[k])
        mv_g["other"] = g_close - g_open - sum(mv_g.values())
        gca_rows.append(rc.gca_rollforward(k, g_open, mv_g, g_close))
    lines: list[dict[str, Any]] = [{"id": "opening", "kind": "opening", "amount": sum(r.opening for r in allowance_rows), "stage": None}]
    ids: dict[str, float] = {}
    for r in allowance_rows:
        for lid, amt in r.movements:
            ids[lid] = ids.get(lid, 0.0) + amt
    for lid, amt in ids.items():
        kind = "overlay" if lid.startswith("overlay-") else "movement"
        stage = next((o.carried_stage for o in overlays if f"overlay-{o.id}" == lid), None)
        lines.append({"id": lid, "kind": kind, "amount": amt, "stage": stage})
    lines.append({"id": "closing", "kind": "closing", "amount": sum(r.closing for r in allowance_rows), "stage": None})
    return {"allowance": allowance_rows, "gca": gca_rows, "lines": lines, "stage_ecl": stage_ecl_v, "overlays": overlays}


# --- the battery -------------------------------------------------------------------------------------------------------


def battery_rows(res: Ifrs9Result, book: Book, state: State, overlays: tuple[ov.Overlay, ...], roll: dict[str, Any],
                 model_id: str) -> list[dict[str, Any]]:
    """The IFRS 9 battery rows computable on one reporting date, each the engine's ``TestResult``; the lifetime PD backtest,
    the stage migration backtest and the SICR threshold stability need a history the synthetic book does not have and are
    not run (stated in the case page). The SICR and backtest rows compare the model with the generator's own realised
    12-month outcomes (known truth), a self-consistency check, never evidence about a real bank."""
    rows: list[dict[str, Any]] = []
    totals = np.array([float(account_ecl(res, k).sum()) for k in range(len(res.weights))])
    mean_total = float(np.where(res.stage == 1, res.e12_mean, np.where(res.stage == 2, res.life_mean, res.s3)).sum())
    rows.append(battery.scenario_sensitivity(totals, res.weights, mean_total, model_id=model_id).to_dict())
    for seg in bk.SEGMENTS:
        sid = bk.SEG_IDS.index(seg["id"])
        pd_ttc = float(np.average(book.pd_now[book.seg == sid], weights=book.e[book.seg == sid]))
        row = battery.nonlinearity_test(min(max(pd_ttc, 1e-4), 0.5), seg["rho"], res.z, res.weights, model_id=model_id,
                                        ).to_dict()
        row["segment"] = seg["id"]
        rows.append(row)
    ecl_acc = account_ecl(res)
    by_stage = {s: float(ecl_acc[res.stage == int(s[-1])].sum()) for s in ("stage1", "stage2", "stage3")} | {"poci": 0.0}
    direction = -1 if state.z_shift > 0 else (1 if state.z_shift < 0 else 0)
    rows.append(battery.overlay_diagnostics(overlays, by_stage, direction, model_id=model_id).to_dict())
    live = ~state.default
    pit12 = np.zeros(book.n)
    for rho in np.unique(book.rho):
        m = book.rho == rho
        pit12[m] = ts.ttc_to_pit(book.pd_now[m], float(rho), np.full(int(m.sum()), state.z_shift))
    defaulted = live & (book.u_real < pit12)
    stage12 = res.stage[live]
    rows.append(battery.sicr_effectiveness(
        stage12, defaulted[live], 12, np.zeros(int(live.sum())), defaulted[live] & (stage12 == 1),
        (stage12 == 2) & (res.trigger[live] == "dpd-backstop"), model_id=model_id).to_dict())
    realised = np.where(defaulted, res.lgd * book.e * (1.0 + book.eir) ** -0.5, 0.0)
    ecl12 = np.where(res.stage == 3, 0.0, pick(res)[0])
    rows.append(battery.ecl_backtest(realised[live], ecl12[live], 12, model_id=model_id).to_dict())
    rows.append(battery.reconciliation_identities(roll["allowance"], roll["gca"], roll["lines"], roll["stage_ecl"],
                                                  model_id=model_id).to_dict())
    return rows
