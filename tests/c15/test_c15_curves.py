"""CT-1502, CT-1504: the choice of the BCCh series, the valuation date, the dating rule and the fitted zero curves."""
from __future__ import annotations

import copy

import numpy as np
import pytest
from c15_support import STALE, data_root, make_series, requires_raw, world
from riskvalidation.irrbb import curves as rv
from riskvalidation.irrbb import slotting

from pipeline.cases.c15 import curves

MID = slotting.bucket_grid().midpoints


def test_the_series_are_chosen_from_the_search_and_the_stale_ones_are_left_out_with_their_reason() -> None:
    series, infos = world()
    sel = curves.select(series, infos, "2026-09")
    assert sel.month == "2026-09" and (sel.first, sel.last) == ("2026-09-01", "2026-09-30")
    assert sel.valuation_date == "2026-09-02"
    clp = [c for c in sel.chosen if c.curve == "CLP"]
    ur = [c for c in sel.chosen if c.curve == "UR"]
    assert [(round(c.tenor_years, 6), c.kind) for c in clp] == [(round(1 / 360, 6), "anchor"), (2.0, "yield"), (5.0, "yield"), (10.0, "yield")]
    assert [(c.tenor_years, c.kind) for c in ur] == [(2.0, "yield"), (5.0, "yield"), (10.0, "yield"), (30.0, "yield")]
    assert {e.code: e.reason for e in sel.excluded}.keys() == set(STALE)
    for e in sel.excluded:
        assert "no observation in 2026-09" in e.reason and STALE[e.code] in e.reason
    # the anchor is a Central Bank policy rate, not a secondary-market yield, and says so
    anchor = [c for c in clp if c.kind == "anchor"][0]
    assert anchor.code == "F022.TPM.TIN.D001.NO.Z.D" and "policy rate" in anchor.note.lower()


def test_the_anchor_is_used_only_where_the_engine_fit_needs_a_fourth_point() -> None:
    series, infos = world(extra_clp_tenor=True)
    sel = curves.select(series, infos, "2026-09")
    assert [c.kind for c in sel.chosen if c.curve == "CLP"] == ["yield"] * 4
    fit = curves.fit_curve(sel, series, "CLP")
    assert "F022.TPM.TIN.D001.NO.Z.D" not in fit.block["series_codes"] and len(fit.block["points"]) == 4


def test_a_currency_with_fewer_than_three_tenors_is_blocked_and_never_filled() -> None:
    series, infos = world()
    dropped = copy.copy(series)
    del dropped["F022.BCLP.TIS.AN10.NO.Z.D"]
    with pytest.raises(curves.BlockedCurve, match="CLP.*fewer than 3"):
        curves.select(dropped, [i for i in infos if "BCLP.TIS.AN10" not in i.series_id], "2026-09")
    series2 = dict(series)
    del series2["F022.TPM.TIN.D001.NO.Z.D"]
    with pytest.raises(curves.BlockedCurve, match="anchor"):                       # three tenors and no anchor: the engine cannot fit
        curves.select(series2, infos, "2026-09")


def test_no_observation_after_the_valuation_date_enters_a_fit() -> None:
    series, infos = world()
    sel = curves.select(series, infos, "2026-09")
    assert sel.valuation_date == "2026-09-02"
    base = {c: curves.fit_curve(sel, series, c) for c in ("CLP", "UR")}
    planted = {code: make_series(code, {**{d: v for d, v in s.values().items()}, "2026-09-03": 99.0, "2026-09-04": 99.0, "2026-09-07": 99.0})
               for code, s in series.items()}
    for c in ("CLP", "UR"):
        again = curves.fit_curve(sel, planted, c)
        assert again.block == base[c].block and np.array_equal(again.rates, base[c].rates)
        assert all(p["observed_yield"] < 0.2 for p in again.block["points"])
    # not vacuous: a selection dated later does read them
    later = copy.copy(sel)
    object.__setattr__(later, "valuation_date", "2026-09-04")
    assert curves.fit_curve(later, planted, "UR").block != base["UR"].block
    # the UF value is the one of the valuation date, never a later one
    value, source = curves.uf_value(sel, series)
    assert value == 40871.0 and "F073.UFF.PRE.Z.D" in source and "2026-09-02" in source


def test_the_curves_are_the_engine_fits_and_labelled_as_an_adaptation() -> None:
    series, infos = world()
    sel = curves.select(series, infos, "2026-09")
    for name in ("CLP", "UR"):
        fit = curves.fit_curve(sel, series, name)
        b = fit.block
        ten = np.array([p["tenor_years"] for p in b["points"]])
        par = np.array([p["observed_yield"] for p in b["points"]])
        zero = rv.bootstrap_zero_curve(ten, par, 2)
        assert np.allclose(zero, [p["zero_rate"] for p in b["points"]], rtol=0, atol=1e-12)
        ns = rv.fit_nelson_siegel(ten, zero)
        got = {p["name"]: p["value"] for p in b["fit"]["parameters"]}
        assert got == pytest.approx({"beta0": ns.beta0, "beta1": ns.beta1, "beta2": ns.beta2, "tau": ns.tau}, rel=1e-12, abs=1e-15)
        assert b["fit"]["model"] == "nelson-siegel" and b["fit"]["rmse_bp"] == pytest.approx(ns.rmse * 1e4)
        want = rv.nelson_siegel_yield(MID, ns.beta0, ns.beta1, ns.beta2, ns.tau)
        assert np.allclose(b["zero_rates_at_midpoints"], want, rtol=0, atol=1e-12) and np.allclose(fit.rates, want, rtol=0, atol=1e-12)
        assert b["date"] == "2026-09-02" and b["month"] == "2026-09" and b["curve"] == name
        assert b["compounding"] == "continuous" and b["observed_kind"] == "secondary-market-yield"
        # the BCCh terms: the owner is named, the fitted curve is Contraste's adaptation and its sole responsibility
        att = b["attribution"].lower()
        assert "banco central de chile" in att and "adaptation" in att and "contraste" in att and "sole responsibility" in att
        for code in b["series_codes"]:
            assert code in b["attribution"]
        for word in ("bootstrap_zero_curve", "fit_nelson_siegel", "tau"):
            assert word in b["source"]
    ur = curves.fit_curve(sel, series, "UR").block
    assert ur["series_codes"] == sorted(ur["series_codes"]) and len(ur["points"]) == 4 and ur["fit"]["rmse_bp"] < 5.0
    clp = curves.fit_curve(sel, series, "CLP").block
    assert clp["points"][0]["tenor_years"] == pytest.approx(1 / 360) and clp["points"][0]["observed_yield"] == pytest.approx(0.045)
    assert "policy rate" in clp["source"].lower()


@requires_raw
def test_the_real_month_gives_the_expected_selection_and_the_dating_rule_holds_on_it() -> None:
    raw = curves.load_raw(data_root())
    sel = curves.select(raw.series, raw.infos, "2026-09")
    assert sel.valuation_date == "2026-09-03"
    assert {c.code for c in sel.chosen} == {
        "F022.BCLP.TIS.AN02.NO.Z.D", "F022.BCLP.TIS.AN05.NO.Z.D", "F022.BCLP.TIS.AN10.NO.Z.D", "F022.TPM.TIN.D001.NO.Z.D",
        "F022.BUF.TIS.AN02.UF.Z.D", "F022.BUF.TIS.AN05.UF.Z.D", "F022.BUF.TIS.AN10.UF.Z.D", "F022.BUF.TIS.AN30.UF.Z.D"}
    assert {e.code for e in sel.excluded} == {"F022.BCLP.TIS.AN01.NO.Z.D", "F022.BUF.TIS.AN01.UF.Z.D", "F022.BUF.TIS.AN20.UF.Z.D"}
    # observations after the valuation date exist in the raw files (the whole month is kept) and change no fit
    assert any(d > sel.valuation_date for s in raw.series.values() for d in s.values())
    cut = {code: make_series(code, {d: v for d, v in s.values().items() if d <= sel.valuation_date}) for code, s in raw.series.items()}
    for c in ("CLP", "UR"):
        assert curves.fit_curve(sel, cut, c).block == curves.fit_curve(sel, raw.series, c).block
    # the figures the case page quotes about the month
    uf10, clp10 = raw.series["F022.BUF.TIS.AN10.UF.Z.D"].values(), raw.series["F022.BCLP.TIS.AN10.NO.Z.D"].values()
    assert (uf10["2026-09-01"], uf10["2026-09-30"], clp10["2026-09-01"], clp10["2026-09-30"]) == (2.54, 2.82, 5.71, 6.25)
    assert len(raw.series["F022.BUF.TIS.AN30.UF.Z.D"].values()) == 7
    last = {i.series_id: i.last_observation for i in raw.infos}
    assert (last["F022.BCLP.TIS.AN01.NO.Z.D"], last["F022.BUF.TIS.AN01.UF.Z.D"], last["F022.BUF.TIS.AN20.UF.Z.D"]) == ("2025-12-24", "2025-12-26", "2026-08-18")
