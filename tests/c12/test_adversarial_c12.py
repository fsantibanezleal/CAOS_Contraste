"""The adversarial checks of C12 (docs/design/features/c12/validation.md): a defect is planted and a gate must refuse it."""
from __future__ import annotations

import json
from pathlib import Path

import c12_docs as d
import numpy as np
import pytest
from c12_support import semantics
from c12_support import data_root, requires_raw

from pipeline.cases.c12 import calibration, credit, data, fetch
from pipeline.io import treasury


def refused(doc: dict, fn, fragment: str) -> None:
    """The planted document is refused by the schema or by the contract's cross-field checks, naming ``fragment``."""
    bad = d.mutated(doc, fn)
    found = d.problems(bad)
    assert found and any(fragment in m for m in found), (fragment, found[:3])


def _netting() -> dict:
    return d.variant("netting-set")


def test_adversarial_a_changed_raw_file_is_refused_by_its_provenance_record(tmp_path: Path) -> None:
    f = tmp_path / "daily-treasury-par-2024.csv"
    f.write_text("Date,3 Mo\n01/02/2024,5.0\n", encoding="utf-8")
    rec = treasury.describe(f, "https://home.treasury.gov/x", "2026-10-20").to_json()
    (tmp_path / "provenance.json").write_text(json.dumps([rec]), encoding="utf-8")
    assert fetch._records(tmp_path, [f], {f.name: rec["url"]}, ("provenance.json",))[0]["sha256"] == rec["sha256"]
    f.write_text("Date,3 Mo\n01/02/2024,5.1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from its provenance record"):
        fetch._records(tmp_path, [f], {f.name: rec["url"]}, ("provenance.json",))
    with pytest.raises(treasury.DeclaredAbsence, match="https://home.treasury.gov"):
        treasury.need(tmp_path / "missing.xls", fetch.hqm_url("hqmeom_04_08.xls"))


def test_adversarial_a_month_whose_horizon_is_not_observed_is_not_a_backtest_date() -> None:
    days = ["2000-01-03", "2000-01-31", "2000-02-29", "2000-03-31", "2000-12-29", "2001-01-31", "2001-02-28"]
    curves = data.Curves({x: treasury.ParCurve(x, {"3 Mo": 0.05, "6 Mo": 0.05, "1 Yr": 0.05}) for x in days})
    got = curves.backtest_dates("2000-01", curves.last)
    assert got == ["2000-01-31", "2000-02-29"]                     # March has no curve for 2001-03-31, so it is not a date
    assert curves.as_of("2000-04-30").observation_date == "2000-03-31"      # a month end without a curve carries the earlier day


def test_adversarial_a_spread_below_the_treasury_curve_is_floored_and_counted() -> None:
    tenors, zeros = np.array([0.5, 1.0, 2.0]), np.full(3, 0.05)
    cur = credit.hqm_curve((tenors, np.array([0.01, 0.02, 0.2])), tenors, zeros, np.array([0.5, 1.0, 2.0]))
    assert cur.floored == 2 and (cur.spreads >= 0).all() and cur.spreads[3] > 0


def test_adversarial_a_parameter_without_the_convention_label_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"]["named_parameters"]["seed"].pop("label"), "schema")
    refused(_netting(), lambda x: x["outputs"]["named_parameters"]["seed"].update(label="measured"), "schema")


@requires_raw
def test_adversarial_a_calibration_window_that_reaches_its_date_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"]["calibration_used"].update(sample_end=x["outputs"]["calibration_used"]["backtest_date"]),
            "look-ahead")
    ser = calibration.series_of(data.read_curves(data_root()))
    with pytest.raises(ValueError):
        calibration.fit_at(ser, "1992-12-31")


def test_adversarial_a_cva_term_computed_elsewhere_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"]["cva_dva"]["buckets"][3].update(cva_term=x["outputs"]["cva_dva"]["buckets"][3]["cva_term"] + 1.0),
            "cva term")
    refused(_netting(), lambda x: x["outputs"]["exposure"]["eepe"].update(amount=x["outputs"]["exposure"]["eepe"]["amount"] * 1.01), "EEPE")


def test_adversarial_an_mpor_below_the_floor_or_a_collateral_balance_above_the_bound_is_refused() -> None:
    refused(d.variant("csa-mpor-10d"), lambda x: x["outputs"]["collateral"]["csa"].update(mpor_business_days=5), "schema")
    refused(d.variant("csa-mpor-10d"), lambda x: x["outputs"]["exposure"]["ee"]["values"].__setitem__(5, 1e12), "collateralised EE")


def test_adversarial_initial_margin_labelled_simm_or_with_a_wrong_alpha_is_refused() -> None:
    doc = d.variant("with-im")
    refused(doc, lambda x: x["outputs"]["initial_margin"].update(simm_used=True), "schema")
    refused(doc, lambda x: x["outputs"]["initial_margin"].update(labelled="ISDA SIMM"), "schema")
    refused(doc, lambda x: x["outputs"]["initial_margin"].update(alpha=2.33), "alpha")
    refused(doc, lambda x: x["outputs"]["initial_margin"].update(mpor_calendar_days=10), "calendar days")
    refused(doc, lambda x: x["outputs"]["initial_margin"]["dim"]["values"].__setitem__(0, 0.0), "below max")


def test_adversarial_a_nica_changed_without_its_replacement_cost_is_refused() -> None:
    refused(d.variant("csa-mpor-10d"), lambda x: x["outputs"]["sa_ccr"]["nica"].update(amount=5e4), "RC")


def test_adversarial_a_wrong_way_sweep_whose_zero_point_differs_from_the_independent_cva_is_refused() -> None:
    doc = d.variant("wrong-way-risk")
    refused(doc, lambda x: x["outputs"]["wrong_way_risk"]["sweep"][1]["cva"].update(amount=x["outputs"]["wrong_way_risk"]["sweep"][1]["cva"]["amount"] + 1e-6),
            "b = 0")
    refused(doc, lambda x: x["outputs"]["ore_reconciliation"].update(status="reconciled"), "schema")
    refused(d.variant("netting-set"), lambda x: x["outputs"]["ore_reconciliation"].update(status="not-applicable"), "schema")


def test_adversarial_an_ead_or_a_girr_charge_computed_elsewhere_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"]["sa_ccr"]["ead"].update(amount=x["outputs"]["sa_ccr"]["ead"]["amount"] + 1.0), "EAD")
    refused(_netting(), lambda x: x["outputs"]["girr"]["delta_charge"].update(amount=x["outputs"]["girr"]["delta_charge"]["amount"] * 1.1), "girr")


def test_adversarial_a_stress_window_whose_spread_flag_disagrees_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"]["regulatory_comparison"]["stressed"].update(spread_rose=False), "spread_rose")


def test_adversarial_a_pit_edited_or_a_decision_flipped_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"]["backtest"]["book_horizons"][2]["pits"].__setitem__(0, 0.5), "W^2")
    refused(_netting(), lambda x: x["outputs"]["backtest"]["book_horizons"][0].update(
        reject_at_5pct=not x["outputs"]["backtest"]["book_horizons"][0]["reject_at_5pct"]), "decision")
    refused(_netting(), lambda x: x["outputs"]["backtest"]["book_horizons"][0]["critical_iid"].update(p05=2.0), "schema")


def test_adversarial_a_sensitivity_that_does_not_move_a_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"]["calibration_sensitivity"][1].update(a=x["outputs"]["calibration_used"]["a"]), "standard error")


def test_adversarial_an_ore_flag_that_disagrees_with_its_difference_is_refused() -> None:
    def flip(x: dict) -> None:
        a = x["outputs"]["ore_reconciliation"]["agreement"][0]
        a["within_two_se"] = not a["within_two_se"]

    refused(d.variant("csa-mpor-20d"), flip, "within_two_se")
    refused(d.variant("csa-mpor-20d"), lambda x: x["outputs"]["ore_reconciliation"].update(
        all_within_two_se=not x["outputs"]["ore_reconciliation"]["all_within_two_se"]), "all_within_two_se")
    refused(d.variant("csa-mpor-20d"), lambda x: x["outputs"]["ore_reconciliation"].update(ore_version="1.8.16.0"), "schema")


def test_adversarial_an_engine_closed_form_that_departs_from_quantlib_turns_the_row_red(monkeypatch) -> None:
    from riskvalidation.ccr import hw1f

    from pipeline.cases.c12 import reconcile

    tenors, zeros = np.array([0.25, 1.0, 5.0, 10.0, 30.0]), np.array([0.03, 0.031, 0.033, 0.035, 0.036])
    assert all(r["light"] == "green" for r in reconcile.quantlib_rows(tenors, zeros, 0.1, 0.01))
    real = hw1f.bond_option
    monkeypatch.setattr(hw1f, "bond_option", lambda *a, **k: real(*a, **k) * 1.01)
    assert any(r["light"] == "red" for r in reconcile.quantlib_rows(tenors, zeros, 0.1, 0.01))


def test_adversarial_a_document_with_a_missing_block_or_a_changed_byte_is_refused() -> None:
    refused(_netting(), lambda x: x["outputs"].pop("backtest"), "schema")
    refused(_netting(), lambda x: x["outputs"]["exposure"]["ee"]["mc_se"].pop(), "mc_se")
    sums = (d.C12 / "SHA256SUMS.txt").read_text(encoding="utf-8")
    assert d.sha(d.C12 / "netting-set.json") in sums
    tampered = (d.C12 / "netting-set.json").read_bytes().replace(b'"netting-set"', b'"netting-Set"', 1)
    import hashlib

    assert hashlib.sha256(tampered).hexdigest() not in sums


def test_adversarial_a_different_seed_writes_different_documents(built) -> None:
    from c12_support import SEED, SMALL

    from pipeline.cases.c12 import bake

    other = bake.build(SEED + 1, data_root(), work_dir=built_work(built), **{**SMALL, "date_stride": 24, "ore_samples": 200})
    a, b = built.variants["netting-set"], other.variants["netting-set"]
    assert a["outputs"]["exposure"]["ee"]["values"] != b["outputs"]["exposure"]["ee"]["values"]


def built_work(built) -> Path:
    import tempfile

    return Path(tempfile.mkdtemp(prefix="c12-adv-"))


def test_adversarial_a_planted_generated_block_is_not_the_committed_one() -> None:
    from pipeline.cases.c12 import page

    docs = {v: d.variant(v) for v in d.VARIANTS}
    block = page.results_block(docs, d.models())
    docs["netting-set"] = d.mutated(docs["netting-set"], lambda x: x["outputs"]["sa_ccr"]["ead"].update(amount=1.0))
    assert page.results_block(docs, d.models()) != block


def test_adversarial_a_book_with_no_first_year_exposure_has_no_effective_maturity() -> None:
    from riskvalidation.ccr import exposure as ex

    grid = np.array([0.5, 1.0, 2.0])
    with pytest.raises(ValueError, match="undefined"):
        ex.effective_maturity(grid, np.zeros(3), np.zeros(3), np.ones(3))
    assert semantics is not None


def test_adversarial_a_red_row_without_a_finding_is_found() -> None:
    from test_c12_documents import uncited

    doc = d.variant("netting-set")
    assert uncited(doc) == []
    bad = d.mutated(doc, lambda x: x.update(findings=x["findings"][1:]))
    assert uncited(bad)
