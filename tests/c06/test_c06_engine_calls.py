"""CT-507 and CT-515: the engine contract's golden values through the pinned `riskvalidation`, and no engine logic in the product.

The goldens are transcribed from `docs/contracts/engine/provisions-api.md` (engine-provisions-api 1.0.0), which takes them from
dossier 02 B.2 to B.5 and C.1. A drift of the pin from the released engine fails here."""
from __future__ import annotations

import importlib.metadata as md
import json
from pathlib import Path

import numpy as np
import pytest
from riskvalidation.provisions import ecl as E
from riskvalidation.provisions import overlays as O
from riskvalidation.provisions import reconciliation as RC
from riskvalidation.provisions import staging as S
from riskvalidation.provisions import term_structure as T
from riskvalidation.validation import ifrs9 as V

from c06_helpers import engine_logic_findings

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "data-pipeline" / "pipeline" / "cases" / "c06"
FIXTURE = ROOT / "docs" / "contracts" / "fixtures" / "c06" / "variant-reporting-date-fixture.json"

def test_the_pin_is_the_released_engine():
    assert md.version("riskvalidation") == "0.5.0"
    req = (ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    assert "CAOS_RiskValidation@v0.05.000" in req


def test_the_engine_golden_values_reproduce_through_the_pin():
    m = np.array([3, 6])
    ts = T.from_hazard(np.array([0.01, 0.01]), m)
    assert np.allclose(ts.survival, [0.99, 0.9801], atol=1e-12) and np.allclose(ts.marginal, [0.01, 0.0099], atol=1e-12)
    assert np.allclose(ts.cumulative, [0.01, 0.0199], atol=1e-12)
    assert np.allclose(T.from_marginal(np.array([0.01, 0.0099]), m).hazard, [0.01, 0.01], atol=1e-12)
    assert np.allclose(T.from_cumulative(np.array([0.01, 0.0199]), m).hazard, [0.01, 0.01], atol=1e-12)
    assert abs(float(T.annualise_pd(np.array([0.19]), 2.0)[0]) - 0.1) < 1e-12
    z = np.array([1.0, 0.0, -2.0])
    pit = T.ttc_to_pit(np.full(3, 0.02), 0.12, z)
    assert np.allclose(pit, [0.005255059, 0.014287387, 0.073424082], atol=1e-8)
    w = np.array([0.25, 0.5, 0.25])
    assert abs(T.weighted_pit_pd(0.02, 0.12, z, w) - 0.026813479) < 1e-8
    assert abs(float(T.ttc_to_pit(np.array([0.02]), 0.12, np.array([-0.25]))[0]) - 0.017997448) < 1e-8
    assert abs(E.non_linearity_index(0.026813479, 0.017997448) - 0.4898489) < 1e-6
    assert abs(float(E.probability_weighted_ecl(0.4 * pit, w)) - 0.010725392) < 1e-8
    assert abs(float(T.implied_z(np.array([0.014287387]), 0.02, 0.12)[0])) < 1e-6
    q = np.array([[0.01, 0.01]])
    assert abs(float(E.ecl_scenario(q, 0.4, 100000.0, np.array([0.0]), np.array([6, 12]), 12)[0]) - 800.0) < 1e-9
    assert abs(float(E.ecl_scenario(q, 0.4, 100000.0, np.array([0.0]), np.array([6, 12]), 6)[0]) - 400.0) < 1e-9
    df = E.discount_factors(np.array([0.06]), np.array([3, 6]))
    assert np.allclose(df[0], [0.992742848, 0.978386160], atol=1e-9)
    ov = O.Overlay("OVL-A", "a", "a", "expert", "pd", None, "stage1", 5.0, "none", "2026-12-31", "USD")
    br = E.portfolio_allowance(np.array([1, 2, 3]), np.array([10.0, 20, 30]), np.array([15.0, 40, 45]), np.array([0.0, 0, 25]), overlays=[ov])
    assert br.by_stage == {"stage1": 10.0, "stage2": 40.0, "stage3": 25.0, "poci": 0.0} and br.model_total == 75.0 and br.total == 80.0
    assert abs(O.overlay_share(5.0, 80.0) - 0.0625) < 1e-12


def test_the_staging_goldens_and_the_amended_cure_signature():
    pol = S.StagingPolicy(multiplier_schedule=((0.01, 4.0), (0.05, 2.5), (0.5, 1.5)), absolute_floor=0.005, threefold_ratio=3.0,
                          probation_months=6)
    assert S.sicr_quantitative(np.array([0.02, 0.02, 0.001]), np.array([0.05, 0.049, 0.003]), pol).tolist() == [True, False, True]
    one = lambda v: np.array([v])  # noqa: E731
    f = np.zeros(1, dtype=bool)
    r = S.allocate_stages(one(0.02), one(0.021), np.array([31]), f, f, f, pol)
    assert r.stage[0] == 2 and r.trigger[0] == "dpd-backstop"
    assert S.allocate_stages(one(0.02), one(0.021), np.array([30]), f, f, f, pol).stage[0] == 1
    assert S.allocate_stages(one(0.02), one(0.021), np.array([90]), f, f, f, pol).trigger[0] == "default"
    now = S.StageResult(stage=np.array([1, 1], dtype=np.int8), trigger=np.array(["none", "none"]), lcr_exempt=np.zeros(2, dtype=bool))
    out = S.apply_cure_probation(np.array([1, 1]), np.array([2, 2]), np.array([3, 6]), pol, now=now)
    assert out.stage.tolist() == [2, 1] and out.trigger[0] == "cure-probation"
    with pytest.raises(TypeError):
        S.apply_cure_probation(np.array([1]), np.array([2]), np.array([3]), pol)  # `now` is required (contract amendment)
    assert abs(float(E.stage3_ecl(np.array([50000.0]), np.array([[30000.0]]), np.array([[12]]), np.array([0.08]))[0]) - 22222.2222) < 1e-3


def _rows(block):
    return [RC.RollForwardRow(r["stage"], r["opening"], tuple((m["line_id"], m["amount"]) for m in r["movements"]), r["closing"], r["residual"])
            for r in block]


def test_the_contract_fixture_reconciliation_closes_through_the_pin():
    o = json.loads(FIXTURE.read_text(encoding="utf-8"))["outputs"]
    allow, gca = _rows(o["reconciliation"]["allowance"]), _rows(o["reconciliation"]["gross_carrying_amount"])
    stage_ecl = {r["stage"]: r["ecl"] for r in o["stage_summary"]["rows"]}
    stage_ecl["poci"] = 0.0
    assert RC.check_identities(allow, gca, o["waterfall"]["lines"], stage_ecl, []) == []
    res = V.reconciliation_identities(allow, gca, o["waterfall"]["lines"], stage_ecl)
    assert res.light.value == "green" and res.metric < 1e-6
    assert "stage_ecl_gap_max" in res.extras  # the contract amendment: the gap to the stage ECL is its own extra


def test_the_battery_goldens_reproduce_through_the_pin():
    obs = np.array([0.02, 0.04])
    res = V.lifetime_pd_backtest(np.array([12, 24]), obs, obs, np.array([1000.0, 1000.0]), np.array([20.0, 40.0]))
    assert res.metric == 0.0 and res.light.value == "green"
    s = V.sicr_effectiveness(np.array([1.0] * 1000 + [2.0] * 100), np.array([True] * 10 + [False] * 990 + [True] * 30 + [False] * 70), 12,
                             np.zeros(1100), np.zeros(1100, dtype=bool), np.zeros(1100, dtype=bool))
    assert abs(s.metric - 30.0) < 1e-9 and s.light.value == "green"
    assert V.ecl_backtest(np.array([90.0]), np.array([100.0]), 12).metric == pytest.approx(0.9)
    sens = V.scenario_sensitivity(0.4 * np.array([0.005255059, 0.014287387, 0.073424082]), np.array([0.25, 0.5, 0.25]), 0.4 * 0.017997448)
    assert abs(sens.metric - 0.4898489) < 1e-6
    assert V.overlay_diagnostics([O.Overlay("X", "a", "a", "expert", "pd", None, "stage1", 5.0, "none", "2026-12-31", "USD")],
                                 {"stage1": 75.0, "stage2": 0.0, "stage3": 0.0, "poci": 0.0}, 0).metric == pytest.approx(0.0625)


def test_each_term_structure_of_a_document_satisfies_the_survival_identities(variant):
    rows = variant.document["outputs"]["term_structures"]
    assert rows
    for r in rows:
        h, q, f = (np.array(r[k]) for k in ("hazard", "marginal_pd", "cumulative_pd"))
        s = 1.0 - f
        s_prev = np.concatenate([[1.0], s[:-1]])
        assert np.allclose(q, s_prev * h, atol=1e-9) and np.allclose(np.cumsum(q), f, atol=1e-9) and (np.diff(f) > 0).all()
        assert ((f > 0) & (f < 1)).all()


def test_the_product_defines_no_engine_function():
    sources = {p.name: p.read_text(encoding="utf-8") for p in PACKAGE.glob("*.py")}
    assert sources and engine_logic_findings(sources) == []
    used = {"allocate_stages", "ecl_scenario", "from_hazard", "portfolio_allowance", "probability_weighted_ecl", "ttc_to_pit", "implied_z",
            "annualise_pd", "forward_pd", "check_identities", "allowance_rollforward", "gca_rollforward", "stage3_ecl", "lifetime_pd_backtest"}
    text = "\n".join(sources.values())
    for fn in used:
        assert fn in text, f"{fn} is not called by the C06 package"
    assert "from riskvalidation" in text


def test_adversarial_an_engine_formula_copied_into_the_product_is_found():
    planted = {"run.py": "from riskvalidation.provisions import ecl\n\ndef ecl_scenario(q, lgd, ead):\n    return (q * lgd * ead).sum()\n"}
    assert engine_logic_findings(planted) == ["run.py: defines ecl_scenario, an engine function"]
    assert engine_logic_findings({"run.py": "def f():\n    pass\n"}) == ["no import from riskvalidation"]


def test_adversarial_a_drifted_golden_value_is_found():
    z = np.array([1.0, 0.0, -2.0])
    good = T.ttc_to_pit(np.full(3, 0.02), 0.12, z)
    drifted = T.ttc_to_pit(np.full(3, 0.02), 0.13, z)  # an engine whose rho constant drifted
    golden = np.array([0.005255059, 0.014287387, 0.073424082])
    assert np.allclose(good, golden, atol=1e-8) and not np.allclose(drifted, golden, atol=1e-8)
