"""CT-521 to CT-523: the hyper-parameter sensitivity of the PC-Hazard rung (S-4), reported beside the pre-registered verdict.

The rung is refitted under nine settings, one hyper-parameter moved at a time around the defaults, on the same training loans, hold-out
split and seed; each refit is judged by ``s4_evaluation`` on the same out-of-time accounts. The verdict of the case stays the default's.
The tests state the set of settings, the identity of the default entry with the committed S-4 numbers, the record of a failed or
unconverged fit, the verdict and its count, and the documents of the sample bake."""
from __future__ import annotations

import dataclasses
import inspect
import json

import numpy as np
import pytest

from pipeline.cases.c06 import backtest as bt
from pipeline.cases.c06 import neural, page
from pipeline.cases.c06 import pch_sensitivity as ps
from pipeline.cases.c06.neural import conditional_cumulative_pd, fit_pch
from pipeline.core.schemas import validate_document

# ---------------------------------------------------------------------------------------------------------------------
# the set of settings


def _moved(s: ps.Setting, d: ps.Setting) -> list[str]:
    """The hyper-parameters in which ``s`` differs from the default ``d`` (width and its interval count are one parameter)."""
    out = []
    if (s.interval_months, s.intervals) != (d.interval_months, d.intervals):
        out.append("interval_width")
    if s.hidden != d.hidden:
        out.append("hidden_layers")
    if s.weight_decay != d.weight_decay:
        out.append("weight_decay")
    if s.learning_rate != d.learning_rate:
        out.append("learning_rate")
    return out


def test_the_nine_settings_move_one_parameter_at_a_time_and_every_grid_covers_180_months() -> None:
    ids = [s.setting_id for s in ps.SETTINGS]
    assert len(ids) == 9 and len(set(ids)) == 9
    defaults = [s for s in ps.SETTINGS if s.is_default]
    assert len(defaults) == 1 and ps.SETTINGS[0] is defaults[0]
    d = defaults[0]
    assert (d.interval_months, d.intervals, d.hidden, d.learning_rate, d.weight_decay) == (
        neural.WIDTH, neural.N_INTERVALS, neural.HIDDEN, neural.LEARNING_RATE, neural.WEIGHT_DECAY)
    for s in ps.SETTINGS:
        assert s.interval_months * s.intervals == 180.0 == ps.COVERED_MONTHS, s
        if not s.is_default:
            assert _moved(s, d) == [s.parameter], s
    by: dict[str, set] = {}
    for s in ps.SETTINGS:
        if s.parameter != "default":
            by.setdefault(s.parameter, set()).add({"interval_width": s.interval_months, "hidden_layers": s.hidden, "weight_decay": s.weight_decay,
                                                   "learning_rate": s.learning_rate}[s.parameter])
    by = {k: sorted(v) for k, v in by.items()}
    assert by["interval_width"] == [1.5, 6.0] and by["hidden_layers"] == [(16, 16), (64, 64)]
    assert by["weight_decay"] == [1e-5, 1e-3] and by["learning_rate"] == [0.003, 0.03]
    assert {s.intervals for s in ps.SETTINGS if s.parameter in ("interval_width", "default")} == {120, 60, 30}


def test_adversarial_two_parameters_moved_at_once_or_a_grid_that_covers_other_months_is_found() -> None:
    d = ps.SETTINGS[0]
    two = dataclasses.replace(ps.SETTINGS[1], hidden=(16, 16), parameter="hidden_layers")
    assert len(_moved(two, d)) == 2
    assert ps.settings_findings((d, two)) != []
    wide = dataclasses.replace(ps.SETTINGS[1], interval_months=6.0, intervals=60)   # 360 months
    assert any("180" in f for f in ps.settings_findings((d, wide)))
    assert ps.settings_findings(ps.SETTINGS) == []


# ---------------------------------------------------------------------------------------------------------------------
# the rung under a setting: the grid follows the width, the default path is the one of the main fit


def test_the_curve_of_a_fitted_rung_follows_its_own_width(tables, variant) -> None:
    run = variant.run
    wide = fit_pch(tables["loans"], run.obs, reporting_date=run.reporting_date, width=6.0, n_intervals=30, max_epochs=40)
    assert wide.width == 6.0 and wide.rates.shape == (neural.N_STRATA if hasattr(neural, "N_STRATA") else wide.rates.shape[0], 30)
    stratum = np.array([0, 1, 2])
    age, h = np.array([3.0, 10.0, 40.0]), np.array([12.0, 36.0])
    got = wide.cumulative(stratum, age, h)
    assert np.allclose(got, conditional_cumulative_pd(wide.rates, stratum, age, h, 6.0), atol=1e-12, rtol=0)
    assert not np.allclose(got, conditional_cumulative_pd(wide.rates, stratum, age, h, neural.WIDTH))   # the 3-month reading would differ
    assert got.shape == (3, 2) and np.all((got > 0) & (got < 1))


def test_a_refit_with_the_default_parameters_reproduces_the_main_fit(tables, variant) -> None:
    run = variant.run
    d = ps.SETTINGS[0]
    again = fit_pch(tables["loans"], run.obs, reporting_date=run.reporting_date, **ps.fit_arguments(d))
    assert again.weights_sha256 == run.ladder.pch.weights_sha256
    assert np.array_equal(again.rates, run.ladder.pch.rates) and again.seed == run.ladder.pch.seed


def test_a_restricted_lifetime_evaluation_gives_the_two_rungs_the_full_one_gives(tables, variant) -> None:
    run = variant.run
    follow = bt.follow_up(tables["loans"], run)
    full = bt.lifetime_results(tables["loans"], run, follow)
    part = bt.lifetime_results(tables["loans"], run, follow, rungs=("L2-cox", "L3-pch"), pooled_only=True)
    want = {r["rung_id"]: r for r in full.rung_comparison if r["rung_id"] in ("L2-cox", "L3-pch")}
    got = {r["rung_id"]: r for r in part.rung_comparison}
    assert set(got) == set(want) and all(got[k] == want[k] for k in want)
    a, b = bt.s4_evaluation(run, follow, full), bt.s4_evaluation(run, follow, part)
    assert a.summary == b.summary and a.deciles == b.deciles


# ---------------------------------------------------------------------------------------------------------------------
# the block of a date


@pytest.fixture(scope="module")
def context(tables, variant):
    run = variant.run
    follow = bt.follow_up(tables["loans"], run)
    life = bt.lifetime_results(tables["loans"], run, follow)
    ev = bt.s4_evaluation(run, follow, life)
    assert ev is not None
    return run, follow, ev


@pytest.fixture(scope="module")
def block(tables, context):
    run, follow, ev = context
    return ps.sensitivity(tables["loans"], run, follow, ev)


def test_the_default_entry_equals_the_committed_s4_numbers_and_every_setting_is_reported(block, context) -> None:
    run, follow, ev = context
    assert block["evaluated"] is True and block["reason"] is None
    assert [s["setting_id"] for s in block["settings"]] == [s.setting_id for s in ps.SETTINGS]
    assert len(block["settings"]) == 9
    d = block["settings"][0]
    s = ev.summary
    assert d["is_default"] is True and d["status"] == "fitted" and d["reason"] is None
    e = d["evaluation"]
    assert e["integrated_brier"] == s["integrated_brier"] and e["c_index"] == s["c_index"]
    assert e["mean_decile_gap"] == {"pch": s["mean_abs_decile_gap_aalen_johansen"]["pch_mean"], "cox": s["mean_abs_decile_gap_aalen_johansen"]["cox_mean"]}
    assert e["criteria"] == s["criteria"] and e["holds_at_date"] == s["holds_at_date"]
    for entry in block["settings"]:
        assert entry["status"] in ("fitted", "not_converged", "failed")
        if entry["status"] != "failed":
            e = entry["evaluation"]
            assert set(e) == {"c_index", "integrated_brier", "mean_decile_gap", "criteria", "holds_at_date"}
            assert e["integrated_brier"]["cox"] == s["integrated_brier"]["cox"]       # the Cox side does not move with the PC-Hazard settings
    assert block["same_training"] is True and block["seed"] == run.ladder.pch.seed
    assert block["covers_months"] == 180 and block["selected_setting"] is None
    assert block["method"]["en"] and block["method"]["es"]


def test_a_refit_setting_differs_from_the_default_only_where_its_parameter_acts(block) -> None:
    by = {s["setting_id"]: s for s in block["settings"]}
    d = by["default"]
    for sid in ("hidden-16", "hidden-64", "weight-decay-1e-5", "weight-decay-1e-3", "learning-rate-0.003", "learning-rate-0.03", "width-1.5", "width-6"):
        e = by[sid]
        assert e["parameters"]["interval_months"] * e["parameters"]["intervals"] == 180.0
        assert e["parameters"] != d["parameters"]
        assert e["weights_sha256"] != d["weights_sha256"]
    assert by["width-6"]["parameters"]["intervals"] == 30 and by["width-1.5"]["parameters"]["intervals"] == 120


def test_the_block_is_reproducible(tables, context, block) -> None:
    run, follow, ev = context
    assert ps.sensitivity(tables["loans"], run, follow, ev) == block


def test_adversarial_a_failed_or_unconverged_fit_is_recorded_and_never_dropped(tables, context, monkeypatch) -> None:
    run, follow, ev = context
    real = ps.fit_pch

    def flaky(loans, obs, **k):
        if k.get("width") == 6.0:
            raise ValueError("planted failure of the width-6 fit")
        m = real(loans, obs, **k)
        if k.get("hidden") == (16, 16):
            return dataclasses.replace(m, epochs=neural.MAX_EPOCHS)
        return m

    monkeypatch.setattr(ps, "fit_pch", flaky)
    out = ps.sensitivity(tables["loans"], run, follow, ev)
    assert len(out["settings"]) == 9
    by = {s["setting_id"]: s for s in out["settings"]}
    assert by["width-6"]["status"] == "failed" and "planted failure" in by["width-6"]["reason"]["en"] and by["width-6"]["reason"]["es"]
    assert by["width-6"]["evaluation"] is None
    assert by["hidden-16"]["status"] == "not_converged" and by["hidden-16"]["reason"]["en"] and by["hidden-16"]["evaluation"] is not None
    assert by["default"]["status"] == "fitted"
    schema_doc = {"settings": out["settings"]}
    assert [s["status"] for s in schema_doc["settings"]].count("failed") == 1


def test_fit_status_names_a_run_to_the_cap_and_non_finite_rates() -> None:
    ok = neural.PchModel(status=None, rates=np.ones((2, 3)), epochs=200, best_epoch=140)       # type: ignore[arg-type]
    assert ps.fit_status(ok) == ("fitted", None)
    capped = dataclasses.replace(ok, epochs=neural.MAX_EPOCHS, best_epoch=neural.MAX_EPOCHS)
    st, why = ps.fit_status(capped)
    assert st == "not_converged" and f"{neural.MAX_EPOCHS:,}" in why["en"] and why["es"]
    bad = dataclasses.replace(ok, rates=np.array([[1.0, np.nan]]))
    st, why = ps.fit_status(bad)
    assert st == "failed" and why["en"] and why["es"]


def test_an_unfitted_rung_gives_a_block_that_says_so_and_writes_no_setting(tables, context) -> None:
    run, follow, _ = context
    out = ps.sensitivity(tables["loans"], run, follow, None)
    assert out["evaluated"] is False and out["settings"] == [] and out["reason"]["en"] and out["reason"]["es"] and "PC-Hazard" in out["reason"]["en"]


# ---------------------------------------------------------------------------------------------------------------------
# the verdict over the dates and its count


def _holds(default, others=None):
    out = {s.setting_id: list(default) for s in ps.SETTINGS}
    out.update(others or {})
    return out


def test_the_case_verdict_stays_the_default_s_and_the_agreement_is_counted() -> None:
    default = [True, True, False, True, False, None]
    holds = _holds(default, {"width-6": [False, False, False, True, False, None], "hidden-64": [True, True, True, True, False, None]})
    o = ps.overall(holds)
    v = bt.s4_verdict(default)
    assert o["case_setting"] == "default" and o["case_verdict"] == v["verdict"] == "holds"
    assert o["dates"] == 6 and o["settings_count"] == 9
    by = {s["setting_id"]: s for s in o["settings"]}
    assert by["width-6"]["verdict"] == "refuted" and by["width-6"]["agrees"] is False
    assert by["hidden-64"]["verdict"] == "holds" and by["hidden-64"]["agrees"] is True
    for s in o["settings"]:
        want = bt.s4_verdict(holds[s["setting_id"]])
        assert (s["dates"], s["evaluable"], s["holds_at"], s["verdict"]) == (want["dates"], want["evaluable"], want["holds_at"], want["verdict"])
    assert o["agree"] == sum(1 for s in o["settings"] if s["agrees"]) == 8
    assert ps.overall_findings(o, holds) == []


def test_the_case_verdict_does_not_depend_on_the_other_settings() -> None:
    default = [True, False, False, False, True, None]            # 2 of 5: refuted
    base = ps.overall(_holds(default))
    flipped = ps.overall(_holds(default, {s.setting_id: [True] * 6 for s in ps.SETTINGS[1:]}))
    assert base["case_verdict"] == flipped["case_verdict"] == "refuted"
    assert base["agree"] == 9 and flipped["agree"] == 1
    none = ps.overall(_holds([None] * 6))
    assert none["case_verdict"] is None and none["agree"] == 0 and all(s["agrees"] is False for s in none["settings"])


def test_adversarial_a_verdict_taken_from_another_setting_or_a_wrong_count_is_found() -> None:
    default = [True, False, False, False, True, None]
    holds = _holds(default)
    holds["learning-rate-0.03"] = [True, True, True, True, True, None]
    o = ps.overall(holds)
    assert ps.overall_findings(o, holds) == []
    assert ps.overall_findings(dict(o, case_verdict="holds"), holds) != []                 # the verdict of the best setting
    assert ps.overall_findings(dict(o, agree=o["agree"] + 1), holds) != []
    assert ps.overall_findings(dict(o, case_setting="learning-rate-0.03"), holds) != []
    changed = dict(holds, **{"width-6": [True] * 6})
    assert ps.overall_findings(o, changed) != []


def test_the_module_never_hands_the_out_of_time_follow_up_to_a_fit() -> None:
    src = inspect.getsource(ps.sensitivity)
    calls = [c for c in src.split("fit_pch(")[1:]]
    assert calls, "the sweep refits through fit_pch"
    for c in calls:
        head = c.split(")")[0]
        assert "follow" not in head and "evaluation" not in head, head      # a fit sees the training loans and the date, nothing after it
    assert "run.obs" in src


# ---------------------------------------------------------------------------------------------------------------------
# the documents of the sample bake


def _fits(sample_bake, which="a"):
    root, manifest = sample_bake[which]
    out = {}
    for a in manifest["artifacts"]:
        if a["role"] == "models":
            out[a["variant_id"]] = json.loads((root / a["path"]).read_text(encoding="utf-8"))
    return out


def test_every_models_document_carries_the_sweep_and_validates(sample_bake) -> None:
    root, _ = sample_bake["a"]
    fits = _fits(sample_bake)
    assert fits
    for vid, doc in fits.items():
        blk = doc["fit"]["pch_sensitivity"]
        assert blk["covers_months"] == 180 and blk["selected_setting"] is None
        if blk["evaluated"]:
            assert [s["setting_id"] for s in blk["settings"]] == [s.setting_id for s in ps.SETTINGS], vid
        else:
            assert blk["settings"] == [] and blk["reason"]["en"]
        validate_document(f"data/derived/C06/{vid}.json", doc)


def test_the_sweep_default_is_the_committed_evaluation_of_the_document(sample_bake) -> None:
    for vid, doc in _fits(sample_bake).items():
        blk = doc["fit"]["pch_sensitivity"]
        ev = next(m for m in doc["model"] if m["id"] == "L3-pch")["details"].get("evaluation")
        if not blk["evaluated"]:
            assert ev is None
            continue
        e = blk["settings"][0]["evaluation"]
        assert e["holds_at_date"] == ev["holds_at_date"] and e["criteria"] == ev["criteria"]
        assert e["integrated_brier"]["pch"] == pytest.approx(ev["integrated_brier"]["pch"], rel=1e-8)
        assert e["integrated_brier"]["cox"] == pytest.approx(ev["integrated_brier"]["cox"], rel=1e-8)


def test_the_overall_of_every_document_is_the_one_the_dates_give_and_the_case_verdict_is_unchanged(sample_bake) -> None:
    fits = _fits(sample_bake)
    holds = {s.setting_id: [] for s in ps.SETTINGS}
    for doc in fits.values():
        blk = doc["fit"]["pch_sensitivity"]
        by = {s["setting_id"]: s for s in blk["settings"]}
        for sid in holds:
            e = by.get(sid, {}).get("evaluation")
            holds[sid].append(None if e is None else e["holds_at_date"])
    overall = next(iter(fits.values()))["fit"]["pch_sensitivity"]["overall"]
    assert overall == ps.overall(holds) and ps.overall_findings(overall, holds) == []
    assert all(d["fit"]["pch_sensitivity"]["overall"] == overall for d in fits.values())
    s4 = next(iter(fits.values()))["fit"]["s4_bootstrap"]["overall"]
    assert overall["case_verdict"] == s4["verdict"] and overall["case_setting"] == "default"


def test_the_sweep_is_reproducible_across_two_bakes(sample_bake) -> None:
    a, b = _fits(sample_bake, "a"), _fits(sample_bake, "b")
    for vid in a:
        assert a[vid]["fit"]["pch_sensitivity"] == b[vid]["fit"]["pch_sensitivity"]


def test_the_case_page_prints_the_sweep_and_the_agreement(sample_bake) -> None:
    root, _ = sample_bake["a"]
    text = page.pch_block(root)
    overall = next(iter(_fits(sample_bake).values()))["fit"]["pch_sensitivity"]["overall"]
    assert "Sensitivity to the hyper-parameters" in text
    assert f"in {overall['agree']} of {overall['settings_count']} settings" in text
    for s in ps.SETTINGS:
        assert s.setting_id in text or s.label["en"] in text
