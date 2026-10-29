"""One variant of C06: a reporting date, baked into its variant and models documents (CT-504 to CT-512)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from riskvalidation.provisions import overlays as rv_ov
from riskvalidation.provisions.overlays import Overlay
from riskvalidation.provisions.reconciliation import check_identities
from riskvalidation.validation import ifrs9 as rv_ifrs9

from . import backtest as bt
from . import build as bd
from . import macro as mc
from . import models as md
from .panel import Loans
from ...io.sba import FREDDIE_REASON, FedTables
from .rollforward import build_rollforward
from .run import LIFETIME_CAP_MONTHS, PERIOD_MONTHS, RHO, STAGE1_MONTHS, DateRun, run_date
from ...io import contract as c1

WINDOW_MONTHS = 12
#: the Spanish of ``io.sba.FREDDIE_REASON`` (the registry of the readers keeps the English; the name Freddie Mac stays)
FREDDIE_REASON_ES = "Freddie Mac: falta la cuenta del titular; se publica el gemelo de la SBA"


def opening_date(reporting_date: np.datetime64) -> np.datetime64:
    """The reporting date twelve months earlier (a quarter end)."""
    ts = pd.Timestamp(np.datetime64(reporting_date, "D")) - pd.DateOffset(months=WINDOW_MONTHS) + pd.offsets.MonthEnd(0)
    return np.datetime64(ts.date(), "D")


@dataclass
class VariantResult:
    variant_id: str
    reporting_date: np.datetime64
    document: dict[str, Any]          # the variant document without provenance and lane (the case adds them)
    models: dict[str, Any]            # the models document's `fit` and `model`
    values: dict[str, float]          # the scalars the expected ranges judge
    contract: dict[str, Any]          # contract-1 summaries of the readers' output
    run: DateRun | None = None


def loan_panel_records(loans: Loans, run: DateRun, every: int = 1) -> list[dict[str, Any]]:
    """The book as the ``loan_panel`` contract rows (one per account at the reporting date). ``account_id`` is the row
    position in the cleaned file, never an SBA identifier; ``balance`` is the modelled balance; ``dpd`` is 0 because the
    file has none; every row is open at the date (no default, prepayment or write-off flag set)."""
    rd = str(np.datetime64(run.reporting_date, "D"))
    sel = np.arange(0, run.a, every)
    idx = run.idx[sel]
    orig = loans.approval[idx].astype(str)
    out = []
    for k, i in enumerate(sel):
        rev = bool(loans.revolver[idx[k]])
        bal = float(run.gca[i])
        out.append({"account_id": f"SBA{int(idx[k]):07d}", "reporting_date": rd, "origination_date": str(orig[k]), "balance": bal,
                    "limit": float(loans.amount[idx[k]]) if rev else None, "revolving": 1 if rev else 0, "eir": float(run.eir[i]),
                    "dpd": 0, "default_flag": 0, "prepay_flag": 0, "writeoff_flag": 0})
    return out


def validate_inputs(loans: Loans, fed: FedTables, run: DateRun, panel_every: int) -> dict[str, Any]:
    """Run the two contract-1 families over what the readers produced for this date; the summaries go to the manifest."""
    rd = str(np.datetime64(run.reporting_date, "D"))
    panel = c1.validate("loan_panel", loan_panel_records(loans, run, panel_every))
    macro_rows = mc.macro_path_records(run.history, run.paths, run.reporting_date)
    mac = c1.validate("macro_path", macro_rows, params={"observation_date": rd})
    if not panel.ok or not mac.ok or panel.rejected or mac.rejected:
        raise ValueError(f"{rd}: contract 1 rejects the readers' output: loan_panel {panel.counts()}, macro_path {mac.counts()}")
    return {"loan_panel": panel.summary(), "macro_path": mac.summary()}


def bake_variant(loans: Loans, fed: FedTables, reporting_date: np.datetime64, seed: int, *, overlays: list[Overlay] | None = None,
                 min_quarter_at_risk: int = 1000, panel_every: int = 1,
                 cleaning: dict[str, int] | None = None) -> VariantResult:
    overlays = list(overlays or [])
    rd = np.datetime64(reporting_date, "D")
    run1 = run_date(loans, fed, rd, min_quarter_at_risk=min_quarter_at_risk)
    run0 = run_date(loans, fed, opening_date(rd), min_quarter_at_risk=min_quarter_at_risk)
    contract = validate_inputs(loans, fed, run1, panel_every)
    rf = build_rollforward(loans, run0, run1, overlays, bd.CURRENCY)
    follow = bt.follow_up(loans, run1)
    life = bt.lifetime_results(loans, run1, follow)
    s4 = bt.s4_evaluation(run1, follow, life)

    stage = run1.stage.astype(np.int64)
    ids = list(run1.scenario_ids)
    breakdown = bd._by_stage(stage, run1.weighted(run1.ecl12), run1.weighted(run1.ecl_life), overlays)
    by_stage = breakdown.by_stage
    scen_by_stage = {sid: bd._by_stage(stage, run1.ecl12[k], run1.ecl_life[k]) for k, sid in enumerate(ids)}
    scen_total = np.array([scen_by_stage[sid].model_total for sid in ids])
    mean_total = bd._by_stage(stage, run1.ecl12_mean, run1.ecl_life_mean).model_total
    model_total = breakdown.model_total
    gca_by = {s: float(run1.gca[stage == s].sum()) for s in (1, 2, 3)}
    n_by = {s: int((stage == s).sum()) for s in (1, 2, 3)}
    stage_rows = [{"stage": f"stage{s}", "accounts": n_by[s], "gross_carrying_amount": gca_by[s], "ecl": float(by_stage[f"stage{s}"]),
                   "coverage": float(by_stage[f"stage{s}"] / gca_by[s]) if gca_by[s] > 0 else 0.0} for s in (1, 2, 3)]
    stage_summary = {"currency": bd.CURRENCY, "rows": stage_rows}
    ecl_rows = [{"scenario_id": sid, "stage": f"stage{s}", "ecl": float(scen_by_stage[sid].by_stage[f"stage{s}"])}
                for sid in ids for s in (1, 2, 3)]
    recon, waterfall = bd.rollforward_blocks(rf, overlays)
    curves, points, _ = bd.account_curves(run1, seed)
    nl = bd.non_linearity_block(run1, model_total, mean_total)
    grid = bd.weight_grid(run1)

    # the battery, every row an engine TestResult
    tests = list(life.tests)
    tests.append(bt.run_sicr_effectiveness(run1, follow))
    tests.append(rv_ifrs9.sicr_threshold_stability(np.array([bd.implied_multiplier(run0), bd.implied_multiplier(run1)]),
                                                   np.array([run0.history.at(run0.history.last)[0], run1.history.at(run1.history.last)[0]]),
                                                   model_id="L1-dth").to_dict())
    tests.append(bt.stage_migration(run0, run1))
    ecl_bt = bt.run_ecl_backtest(run1, loans, follow, 12)
    tests.append(ecl_bt)
    tests.append(rv_ifrs9.scenario_sensitivity(scen_total, run1.weights, mean_total, model_id="L1-dth").to_dict())
    zm = bd.z_means(run1)
    tests.append(rv_ifrs9.nonlinearity_test(run1.pd_ttc, RHO, zm, run1.weights, model_id="L1-dth").to_dict())
    tests.append(rv_ifrs9.overlay_diagnostics(overlays, dict(by_stage), bd.scenario_direction(run1), model_id="L1-dth").to_dict())
    tests.append(rv_ifrs9.reconciliation_identities(rf.allowance, rf.gca, rf.waterfall, rf.stage_ecl, model_id="L1-dth").to_dict())
    failing = check_identities(rf.allowance, rf.gca, rf.waterfall, rf.stage_ecl, overlays)
    if failing:
        raise ValueError(f"{rd}: reconciliation identities fail: {failing}")

    stage2_share = gca_by[2] / max(sum(gca_by.values()), 1.0)
    ov_total = float(rv_ov.sum_amounts(overlays)) if overlays else 0.0
    realised = ecl_bt["metric"] if ecl_bt.get("metric") is not None else None
    finds = bd.findings(tests, run1, scen_total, stage_summary, life.left_out)
    impact = bd.impact_block(dict(by_stage), float(run1.gca.sum()), ov_total, nl["index"], stage2_share, realised)
    en_m, es_m, year, iso = bd.month_label(rd)
    outputs = {
        "kind": "reporting-date", "reporting_date": iso, "currency": bd.CURRENCY, "period_months": PERIOD_MONTHS,
        "horizon": {"stage1_months": STAGE1_MONTHS, "lifetime_cap_months": LIFETIME_CAP_MONTHS},
        "settings": bd.settings_block(),
        "data_status": {"primary_source": "sba-7a", "freddie_mac_available": False, "freddie_mac_reason": {"en": FREDDIE_REASON, "es": FREDDIE_REASON_ES},
                        "notice": bd.NOTICE},
        "scenarios": [{"id": sid, "label": bd.t(mc.SCENARIO_LABELS[sid]["en"], mc.SCENARIO_LABELS[sid]["es"]), "weight": float(run1.weights[k]),
                       "z_mean": float(zm[k])} for k, sid in enumerate(ids)],
        "term_structures": bd.term_structure_rows(run1), "account_curves": curves, "sicr_points": points,
        "stage_flows": {"from_date": str(run0.reporting_date), "to_date": iso, "currency": bd.CURRENCY, "flows": rf.flows},
        "stage_summary": stage_summary, "ecl_by_scenario": {"currency": bd.CURRENCY, "rows": ecl_rows}, "weight_grid": grid,
        "non_linearity": nl, "waterfall": waterfall, "overlays": bd.overlay_rows(overlays), "reconciliation": recon,
        "lifetime_backtest": {"rows": life.rows}, "rung_comparison": life.rung_comparison,
        "decile_calibration": {"rung_id": "L1-dth", "rows": life.deciles},
    }
    document = {"model": md.model_summaries(run1), "outputs": outputs, "tests": tests, "impact": impact, "findings": finds}
    fit = md.fit_block(run1)
    values = {
        f"coverage@{iso}": model_total / float(run1.gca.sum()), f"stage2_share@{iso}": stage2_share,
        f"pd12_mean@{iso}": float(run1.pd12.mean()), f"accounts@{iso}": float(run1.a),
    }
    return VariantResult(variant_id=bd.variant_id(rd), reporting_date=rd, document=document,
                         models={"fit": fit, "model": md.model_records(run1, cleaning, s4)}, values=values, contract=contract, run=run1)

