"""CT-1305: the pinned engine reproduces the PLA and desk goldens of docs/contracts/engine/market-api.md (the consumer test), and
the C13 numbers come from it."""
from __future__ import annotations

import json
import math
import pathlib
import re
from importlib.metadata import distribution

import numpy as np
import pytest
from engine_pin import PYPI_PIN
from pipeline.cases.c13 import generator, measure
from riskvalidation.market import frtb
from riskvalidation.validation import market as val

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_the_pin_carries_the_market_extra() -> None:
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    # the PyPI release, with its market extra among the extras (market,ml,stress since the engine 1.0.1; tests/engine_pin.py reads the pin)
    if PYPI_PIN.search(req) and re.search(r"^riskvalidation\[(?:[a-z]+,)*market(?:,[a-z]+)*\]==", req, re.MULTILINE):
        return
    m = re.search(r"^riskvalidation\[market\] @ git\+https://github\.com/fsantibanezleal/CAOS_RiskValidation(?:\.git)?@([0-9a-f]{40}|v\d+\.\d+\.\d+)$",
                  req, re.MULTILINE)
    assert m is not None, "the engine is pinned with its market extra to its PyPI release, a commit or a tag"
    direct = distribution("riskvalidation").read_text("direct_url.json")
    if direct and not m.group(1).startswith("v"):                   # an editable or local install has no VCS record to compare
        info = json.loads(direct).get("vcs_info", {})
        assert info.get("commit_id", m.group(1)) == m.group(1)


def test_the_pinned_engine_reproduces_the_contract_goldens() -> None:
    h = np.arange(250, dtype=float)
    assert frtb.pla_spearman(h, h) == 1.0 and frtb.pla_spearman(h, h[::-1]) == -1.0
    swapped = h.copy()
    swapped[[0, 1]] = swapped[[1, 0]]
    assert math.isclose(frtb.pla_spearman(h, swapped), 1 - 6 * 2 / (250 * (250 ** 2 - 1)), abs_tol=1e-12)
    assert math.isclose(frtb.pla_ks(h, h + 0.5), 0.004, abs_tol=1e-12)
    assert frtb.pla_ks(h, h + 29.5) == 0.12 and frtb.pla_zone(1.0, frtb.pla_ks(h, h + 29.5)) == "amber"
    assert math.isclose(frtb.pla_ks(h, h + 30.5), 0.124, abs_tol=1e-12) and frtb.pla_zone(1.0, frtb.pla_ks(h, h + 30.5)) == "red"
    for s, k, zone in ((0.81, 0.08, "green"), (0.80, 0.05, "amber"), (0.85, 0.09, "amber"), (0.69, 0.05, "red"),
                       (0.70, 0.05, "amber"), (0.95, 0.121, "red"), (0.95, 0.12, "amber")):
        assert frtb.pla_zone(s, k) == zone, (s, k)
    assert (frtb.desk_exception_limit(0.01), frtb.desk_exception_limit(0.025)) == (12, 30)
    loss, var = np.array([0.01, 0.03, np.nan, 0.02]), np.full(4, 0.02)
    assert frtb.desk_exceptions(loss, var, missing_as_exception=False) == 1 and frtb.desk_exceptions(loss, var) == 2
    table = [round(100 * frtb.binomial_cumulative_probability(k, 250, 0.01), 2) for k in range(11)]
    assert table == [8.11, 28.58, 54.32, 75.81, 89.22, 95.88, 98.63, 99.60, 99.89, 99.97, 99.99]
    rng = np.random.default_rng(0)
    for alpha, limit in ((0.01, 12), (0.025, 30)):
        v = np.full(250, 1.0)
        for count, light in ((limit, "green"), (limit + 1, "red")):
            lossv = np.zeros(250)
            lossv[:count] = 2.0
            rng.shuffle(lossv)
            row = val.desk_backtest(lossv, v, alpha, model_id="desk", basis="HPL")
            assert (row.statistic, row.metric, row.light, row.n_events) == (count, limit, light, count)


def test_the_c13_statistics_are_the_engines_and_not_the_products(monkeypatch: pytest.MonkeyPatch) -> None:
    before = measure.measure("missing-basis", 13, 8)
    rep = generator.replicate("missing-basis", 0)
    assert before.spearman[0] == frtb.pla_spearman(rep.hpl, rep.rtpl) and before.ks[0] == frtb.pla_ks(rep.hpl, rep.rtpl)
    assert before.zone[0] == frtb.pla_zone(float(before.spearman[0]), float(before.ks[0]))
    assert before.exceptions[0.01][0] == frtb.desk_exceptions(rep.loss, rep.var[0.01])
    monkeypatch.setattr(frtb, "pla_spearman", lambda hpl, rtpl: 0.5)
    after = measure.measure("missing-basis", 13, 8)
    assert set(after.spearman) == {0.5}                              # the bake reads the engine function, whatever it returns
