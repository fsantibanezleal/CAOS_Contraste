"""CT-1708 and CT-1709: the pinned engine reproduces the contract goldens and every capital comes from it."""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import numpy as np
from pipeline.cases.c17 import replicate
from riskvalidation.oprisk import aggregate as agg
from riskvalidation.oprisk import sla, sma
from engine_pin import engine_pin_findings

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "data-pipeline" / "pipeline" / "cases" / "c17"


def test_the_pinned_engine_reproduces_the_contract_goldens():
    pin = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    assert engine_pin_findings(pin, sdd) == [], "pin the engine by its release tag, or during a batch by the commit the SDD names"
    f = agg.discretise_severity("lognormal", (0.0, 2.0), 1.0, 6000)
    h = agg.panjer_recursion("poisson", (100.0,), f)
    assert agg.quantile_from_pmf(h, 1.0, 0.999) == 5849.0
    assert np.isclose(np.cumsum(h)[5849], 0.999000217026, atol=5e-10)
    assert sma.bic(35e9) == np.float64(5.37e9) or abs(sma.bic(35e9) - 5.37e9) < 1
    assert abs(sma.ilm(150.0, 150.0) - 1.0) < 1e-12
    assert abs(sla.sla_var_poisson_gpd(10.0, 0.5, 100.0, 0.99) - 6124.555320) < 1e-5
    assert sma.sma_capital(1.4e9, np.full(3, 1e7)).basis == "bic-only"
    bank = replicate.bank_business_indicator()
    assert abs(bank["bi_eur"] - 1.4e9) < 1 and abs(bank["bic_eur"] - 0.18e9) < 1 and bank["bucket"] == 2


def test_every_capital_comes_from_the_engine_and_the_product_holds_no_formula(variants_, monkeypatch):
    v = variants_[0.8]
    prior, _ = replicate.scenario_prior(v, replicate.scenario_points(v), 10)
    base = replicate.estimate(v, 3, 10, 20_000.0, 1.4e9, prior, 20_000)
    assert base["sla"] > 0
    monkeypatch.setattr(sla, "sla_var", lambda *a, **k: 123456789.0)
    assert replicate.estimate(v, 3, 10, 20_000.0, 1.4e9, prior, 20_000)["sla"] == 123456789.0
    monkeypatch.undo()
    real = sma.sma_capital
    monkeypatch.setattr(sma, "sma_capital", lambda bi, losses, **k: dataclasses.replace(real(bi, losses, **k), orc=2.0 * real(bi, losses, **k).orc))
    assert replicate.estimate(v, 3, 10, 20_000.0, 1.4e9, prior, 20_000)["orc"] == 2.0 * base["orc"]
    monkeypatch.undo()
    monkeypatch.setattr(agg, "quantile_from_pmf", lambda h, step, level: 5.0)
    out = replicate.estimate(v, 3, 10, 20_000.0, 1.4e9, prior, 20_000)
    assert out["lda_lognormal_truncated"] == 5.0 and out["lda_splice"] == 5.0 and out["scenario"] == 5.0
    monkeypatch.undo()
    forbidden = (r"0\.12\s*\*", r"0\.15\s*\*", r"\*\*\s*0\.8", r"np\.log\(\s*(math|np)\.e", r"math\.log\(\s*math\.e", r"1\s*-\s*\(1\s*-\s*level\)\s*/",
                 r"\bscipy\.stats\b", r"\bgenpareto\b", r"\blognorm\b")
    for f in PKG.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        for pat in forbidden:
            assert not re.search(pat, text), f"{f.name} holds a formula of the engine: {pat}"
