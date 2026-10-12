"""Model slot c01-pd-rung: a feature matrix in, a PD in (0, 1) out. The baseline (P0, model/benchmark.py) answers in
place of any rung; the C01 evaluate path (the riskvalidation battery) runs unchanged on either and yields rows that
validate against ``common/test-result``."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "contracts"))

from contract_schemas import errors  # noqa: E402
from pipeline.cases import c01_ladder  # noqa: E402
from pipeline.model import benchmark, scorecard  # noqa: E402
from pipeline.stages import evaluate  # noqa: E402

FEATURES = ("limit", "age", "late")


def sample(n: int, seed: int) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = pd.DataFrame({"limit": rng.gamma(3.0, 30000.0, n), "age": rng.integers(21, 70, n).astype(float),
                      "late": rng.integers(0, 4, n).astype(float)})
    p = 1 / (1 + np.exp(-(-2.2 + 0.9 * X["late"] - 0.000008 * X["limit"] + 0.01 * (X["age"] - 40))))
    return X, (rng.random(n) < p).astype(int)


@pytest.fixture(scope="module")
def fitted() -> dict:
    X, y = sample(4000, 1)
    Xtr, ytr, Xcal, ycal = X.iloc[:2500], y[:2500], X.iloc[2500:3200], y[2500:3200]
    sc = scorecard.fit_scorecard(Xtr, ytr, features=list(FEATURES), categorical=(), monotone={})
    rung = c01_ladder.Rung("P1-scorecard", "P1", {"en": "WoE logistic scorecard", "es": "Scorecard logística WoE"},
                           "optbinning + statsmodels Logit", "test", "Apache-2.0", sc)
    return {"rung": rung, "baseline": benchmark.baseline_rung(ytr), "Xtr": Xtr, "Xcal": Xcal, "ycal": ycal}


def test_swap_baseline_and_fitted_rungs(fitted, monkeypatch):
    calls: list[str] = []
    real = evaluate.battery

    def spy(rung, *a, **k):
        calls.append(rung)
        return real(rung, *a, **k)

    monkeypatch.setattr(evaluate, "battery", spy)
    for rung in (fitted["rung"], fitted["baseline"]):
        Xev, yev = sample(1500, 7)
        pd_ev = rung.pd(Xev)
        assert pd_ev.shape == (len(Xev),) and np.all((pd_ev > 0) & (pd_ev < 1))
        rows = evaluate.battery(rung.id, pd_ev, yev, pd_train=rung.pd(fitted["Xtr"]), pd_cal=rung.pd(fitted["Xcal"]),
                                y_cal=fitted["ycal"], champion_pd=None)
        assert rows, rung.id
        assert {r["model_id"] for r in rows if r["model_id"]} == {rung.id}
        for r in rows:
            assert errors("common/test-result", r) == [], (rung.id, r["test_id"])
        assert any(r["test_id"] == "pd.binomial" for r in rows)
    assert calls == ["P1-scorecard", "P0-constant"], "the evaluate path ran once per implementation"


def test_the_baseline_has_the_rungs_interface(fitted):
    b = fitted["baseline"]
    for name in ("pd", "raw_pd", "record", "id", "rung", "title"):
        assert hasattr(b, name), name
    assert b.rung == "P0" and b.calibration is None
    assert b.record()["family"] == "pd-scoring"


def test_the_slot_resolves_a_missing_rung_to_the_baseline(fitted):
    rungs = {"P1-scorecard": fitted["rung"]}
    got, provenance = benchmark.resolve_rung(rungs, "P1-scorecard", fitted["baseline"])
    assert got is fitted["rung"] and provenance == "real"
    got, provenance = benchmark.resolve_rung(rungs, "P3-ebm", fitted["baseline"])
    assert got is fitted["baseline"] and provenance == "baseline"
