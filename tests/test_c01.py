"""C01 on its committed artifacts: CT-108 to CT-111. The shipped evidence is what these read; nothing is re-baked."""
from __future__ import annotations

import bisect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
BATTERY = ("disc.auc", "pd.jeffreys", "pd.binomial", "pd.binomial_vasicek", "pd.spiegelhalter", "pd.brier", "pd.ece",
           "rating.hhi")
# a constant PD ranks nobody and puts everyone in one grade: these are undefined for it, by design
NOT_FOR_CONSTANT = ("disc.ks", "stability.psi", "disc.auc_vs_initial", "pd.hosmer_lemeshow", "pd.chi2_grades")


def _read(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _read("manifests/C01.json")


def _variants(manifest: dict) -> list[tuple[dict, dict, dict]]:
    out = []
    for a in manifest["artifacts"]:
        if a["role"] == "variant":
            out.append((a, _read(a["path"]), _read(a["models_ref"])))
    return out


def _table_points(sc: dict, feature: str, value) -> int:
    """The points of the row a value falls in, from the committed points table and bins alone."""
    rows = [r for r in sc["points_table"] if r["feature"] == feature]
    spec = sc["bins"][feature]
    if value is None:
        return rows[-1]["points"]
    if spec["kind"] == "numerical":
        k = bisect.bisect_right(spec["splits"], float(value))
    else:
        k = next((i for i, cats in enumerate(spec["categories"]) if str(value) in cats), len(rows) - 1)
    return rows[k]["points"]


def test_points_table_recomputes_scores(manifest):
    checked = 0
    for a, v, models in _variants(manifest):
        sample = v["outputs"]["sample"]
        if sample is None:
            continue
        sc = next(m for m in models["model"] if m["id"] == "P1-scorecard")["details"]
        for i in range(len(sample["ids"])):
            points = [_table_points(sc, f, sample["inputs"][f][i]) for f in sc["features"]]
            assert points == sample["scorecard_points"][i], (a["variant_id"], sample["ids"][i])
            assert sum(points) == sample["scorecard_score"][i]
            checked += 1
    assert checked >= 100  # the holdout and the German twin, 50 applicants each


def test_every_rung_reports_the_battery(manifest):
    for a, v, _ in _variants(manifest):
        tests = {(t["test_id"], t["model_id"]) for t in v["tests"] if t["segment"] == "portfolio"}
        for m in v["model"]:
            for tid in BATTERY:
                assert (tid, m["id"]) in tests, (a["variant_id"], m["id"], tid)
            if m["id"] != "P0-constant":
                for tid in NOT_FOR_CONSTANT:
                    assert (tid, m["id"]) in tests, (a["variant_id"], m["id"], tid)
            if m["id"] not in ("P0-constant", "P1-scorecard"):
                assert ("disc.delong", m["id"]) in tests, (a["variant_id"], m["id"])
            auc = next(t for t in v["tests"] if t["test_id"] == "disc.auc" and t["model_id"] == m["id"])
            if m["id"] != "P0-constant":
                assert auc["extras"]["ci95_low"] < auc["metric"] < auc["extras"]["ci95_high"]
            grades = [t for t in v["tests"] if t["test_id"] == "pd.jeffreys" and t["model_id"] == m["id"]
                      and t["segment"] != "portfolio"]
            assert grades, (a["variant_id"], m["id"])  # calibration by grade is reported


def test_gbm_monotone_on_pdp_grid(manifest):
    for a in manifest["artifacts"]:
        if a["role"] != "models":
            continue
        models = _read(a["path"])
        for m in models["model"]:
            if m["rung"] != "P4":
                continue
            mono = m["details"]["monotonicity"]
            assert mono["monotone"], (a["variant_id"], m["id"])
            for f, spec in mono["features"].items():
                pdp = np.asarray(spec["pdp"])
                assert np.all(np.diff(pdp) * spec["direction"] >= -1e-12), (m["id"], f)
                assert spec["max_violation"] <= 1e-12, (m["id"], f)


def test_monotonicity_check_catches_a_violation():
    """The check is not vacuous: an unconstrained model of a U-shaped effect is caught."""
    from pipeline.model import gbm

    rng = np.random.default_rng(0)
    x = rng.normal(size=3000)
    y = (rng.random(3000) < 1 / (1 + np.exp(-(x**2 - 1)))).astype(int)
    X = pd.DataFrame({"x": x, "z": rng.normal(size=3000)})
    free = gbm.fit_lightgbm(X, y, (), features=["x", "z"], categorical=(), monotone={"x": 0, "z": 0}, seed=1,
                            rounds=60)
    free.constraints = [1, 0]  # declare a direction the model was never held to
    assert not gbm.monotonicity(free, X, seed=1)["monotone"]


def test_expected_ranges_hold(manifest):
    values: dict[str, float] = {}
    for a, v, _ in _variants(manifest):
        for t in v["tests"]:
            if t["segment"] != "portfolio":
                continue
            key = f"{t['model_id']}_{a['variant_id']}"
            if t["test_id"] == "disc.auc":
                values[f"auc_{key}"] = t["metric"]
            elif t["test_id"] == "stability.psi":
                values[f"psi_{key}"] = t["metric"] if t["metric"] is not None else t["statistic"]
            elif t["test_id"] == "pd.jeffreys":
                values[f"jeffreys_p_{key}"] = t["p_value"]
        if a["variant_id"] == "holdout":
            values["holdout_default_rate"] = v["outputs"]["defaults"] / v["outputs"]["n"]
            cut = v["outputs"]["rungs"]["P1-scorecard"]["cutoff"]
            rev, trn = cut["capital_per_lgd"]["basel3"][-1], cut["capital_per_lgd_transactors"]["basel3"][-1]
            values["capital_share_P1-scorecard_holdout"] = 0.5 * rev / cut["ead"][-1]
            values["transactor_effect_P1-scorecard_holdout"] = (rev - trn) / rev
    assert manifest["expect"], "the case declares its expected ranges"
    for name, (lo, hi) in manifest["expect"].items():
        assert name in values, name
        assert lo <= values[name] <= hi, (name, values[name], lo, hi)


def test_irb_capital_states_its_assumptions(manifest):
    """CT-212: every rung of every variant carries the capital at unit LGD along its cut-offs under the three regimes,
    and the variant states the class, the floors, the scaling, the EAD convention and the references it used."""
    for a, v, _ in _variants(manifest):
        irb = v["outputs"]["irb"]
        cards = a["variant_id"] != "german-twin"
        assert irb["asset_class"] == ("qrre" if cards else "other_retail")
        assert irb["regimes"] == ["basel3", "crr3", "basel2"]
        for regime in irb["regimes"]:
            facts = irb["by_regime"][regime]
            assert facts["name"] and facts["references"]["pd_floor"] and facts["references"]["scaling"]
            assert facts["scaling"] == (1.06 if regime == "basel2" else 1.0)
            assert facts["pd_floor"] == (0.0003 if regime == "basel2" else 0.0005)
            if cards:
                assert facts["pd_floor_revolver"] == (0.0003 if regime == "basel2" else 0.001)
        assert irb["lgd_floor_basel3"] == (0.5 if cards else 0.3) and "d424" in irb["lgd_floor_source"]
        assert irb["ead"]["en"] and irb["ead"]["es"]
        for rid, rung in v["outputs"]["rungs"].items():
            cut = rung["cutoff"]
            for regime in irb["regimes"]:
                curve = cut["capital_per_lgd"][regime]
                assert len(curve) == len(cut["approval_rate"]), (a["variant_id"], rid, regime)
                assert all(y >= x for x, y in zip(curve, curve[1:])), "approving more never lowers the capital"
                assert 0.0 < curve[-1] <= cut["ead"][-1], "capital at unit LGD is a fraction of the EAD"
        for key in ("capital_champion", "capital_challenger"):
            assert v["impact"][key]["value"] > 0 and "Basel III" in v["impact"][key]["label"]["en"]


def test_transactor_sensitivity_reported(manifest):
    """CT-214: the cards are all revolvers, the six-month full payers are counted, and their capital as transactors
    is reported, never above the revolvers' (the transactor's PD floor is the lower one)."""
    for a, v, _ in _variants(manifest):
        irb = v["outputs"]["irb"]
        if a["variant_id"] == "german-twin":
            assert irb["six_month_full_payers"] is None and not irb["revolvers_only"]
            assert all(r["cutoff"]["capital_per_lgd_transactors"] is None for r in v["outputs"]["rungs"].values())
            continue
        assert irb["revolvers_only"] is True
        assert 0 < irb["six_month_full_payers"] < v["outputs"]["n"]
        assert "d424" in irb["transactor_source"] and "152" in irb["transactor_source"]
        for rung in v["outputs"]["rungs"].values():
            cut = rung["cutoff"]
            for regime in irb["regimes"]:
                for rev, trn in zip(cut["capital_per_lgd"][regime], cut["capital_per_lgd_transactors"][regime], strict=True):
                    assert trn <= rev * (1 + 1e-12)


def test_hosmer_lemeshow_uses_g_on_the_holdout(manifest):
    """CT-312: the PDs were fitted on other data, so Hosmer-Lemeshow uses as many degrees of freedom as groups."""
    n = 0
    for _, v, _ in _variants(manifest):
        for t in v["tests"]:
            if t["test_id"] == "pd.hosmer_lemeshow":
                assert t["extras"]["dof"] == t["extras"]["groups"] and t["extras"]["fitted"] is False, t["model_id"]
                n += 1
    assert n > 0


def test_auc_vs_initial_carries_the_development_variance(manifest):
    """CT-313: the calibration slice's AUC is an estimate on rows disjoint from the evaluation set: its variance is
    added to the ECB statistic, and the result says so."""
    n = 0
    for _, v, _ in _variants(manifest):
        for t in v["tests"]:
            if t["test_id"] == "disc.auc_vs_initial" and t["p_value"] is not None:
                assert t["extras"]["auc_initial_variance"] > 0 and "extension" in t["notes"], t["model_id"]
                assert t["extras"]["s2_total"] == pytest.approx(t["extras"]["s2"] + t["extras"]["auc_initial_variance"])
                n += 1
    assert n > 0
