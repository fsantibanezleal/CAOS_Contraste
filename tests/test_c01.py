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
    assert manifest["expect"], "the case declares its expected ranges"
    for name, (lo, hi) in manifest["expect"].items():
        assert name in values, name
        assert lo <= values[name] <= hi, (name, values[name], lo, hi)
