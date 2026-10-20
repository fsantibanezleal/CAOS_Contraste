"""U9-P2 terms: the CRE52.61 terms, the MAR21.4(5)(b) flag and the CRE52.34 trade effective notionals are the engine's
(engine-regulatory-api 2.2.0), never derived in the bake (ADR-0069)."""
from __future__ import annotations

import json

import numpy as np
import pytest
from reg_support import BAKE, COMMITTED, by_id, out, terms_of

SIGN = {"protection-buyer": 1.0, "protection-seller": -1.0}


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


def test_the_bake_defines_no_fallback_and_computes_no_cre52_61_term() -> None:
    src = BAKE.read_text(encoding="utf-8")
    for token in ("_fallback", "_credit_terms", "radicand", "fill_diagonal(g, ", "(1.0 - r * r)", "zip(rhos, adds)", "zip(rhos"):
        assert token not in src, token
    for call in ("credit_addon_terms", "cross_bucket_charge_detail", "credit_trade_effective_notional",
                 "commodity_trade_effective_notional"):
        assert call in src, call


def _credit_entities(doc: dict):
    """The credit entities of each committed netting set, rebuilt from the document's own trades through the engine."""
    from riskvalidation.regulatory import sa_ccr

    for ex in doc["official_examples"]:
        mpor = {v["name"]: v["value"] for v in ex["inputs"]}.get("mpor_business_days")
        rows: dict = {}
        for tr in ex["trades"]:
            t = terms_of(tr)
            if t["asset_class"] != "credit":
                continue
            en = sa_ccr.credit_trade_effective_notional(SIGN[t["position"]], t["notional"], t["start_years"], t["end_years"],
                                                        None if mpor is None else int(mpor))
            row = rows.setdefault(t["entity"], [t["rating"], t["reference_kind"] == "index", 0.0])
            row[2] += en
        if rows:
            yield ex, [sa_ccr.CreditEntity(r, i, en) for r, i, en in rows.values()]


@pytest.mark.parametrize("which", ["built", "committed"])
def test_the_credit_terms_of_every_netting_set_equal_the_engines(which, request) -> None:
    from riskvalidation.regulatory import sa_ccr

    doc = request.getfixturevalue(which)
    seen = 0
    for ex, entities in _credit_entities(doc):
        want = sa_ccr.credit_addon_terms(entities)
        got = {v["name"]: v["value"] for v in ex["outputs"]}
        assert got["addon_credit"] == want.addon, ex["id"]
        if "term_1" in got:
            assert (got["term_1"], got["term_2"]) == (want.systematic, want.idiosyncratic), ex["id"]
        seen += 1
    assert seen >= 1


def test_the_credit_terms_are_read_from_the_engine_not_derived(monkeypatch) -> None:
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import sa_ccr

    real = sa_ccr.credit_addon_terms
    # keep the identity sqrt(systematic + idiosyncratic) = addon so only the source of the numbers is tested
    monkeypatch.setattr(sa_ccr, "credit_addon_terms", lambda entities: sa_ccr.AddonTerms(real(entities).systematic * 2.0,
                                                                                      real(entities).idiosyncratic * 2.0,
                                                                                      real(entities).addon * 2.0 ** 0.5))
    ex, want = by_id(bake.build())["cre99-netting-set-2"], real(next(e for x, e in _credit_entities(_doc()) if x["id"] == "cre99-netting-set-2"))
    assert out(ex, "term_1") == want.systematic * 2.0 and out(ex, "term_2") == want.idiosyncratic * 2.0


def _doc() -> dict:
    return json.loads(COMMITTED.read_text(encoding="utf-8"))


def test_an_engine_term_that_does_not_recompose_the_add_on_is_refused(monkeypatch) -> None:
    """The refusal the bake held stays: sqrt(systematic + idiosyncratic) is the engine's credit add-on (CRE52.61)."""
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import sa_ccr

    real = sa_ccr.credit_addon_terms
    monkeypatch.setattr(sa_ccr, "credit_addon_terms",
                        lambda entities: sa_ccr.AddonTerms(real(entities).systematic + 1.0, real(entities).idiosyncratic, real(entities).addon))
    with pytest.raises(ValueError, match="CRE52.61"):
        bake.build()


@pytest.mark.parametrize("which", ["built", "committed"])
def test_the_fallback_flag_and_cross_bucket_charge_of_every_sbm_case_equal_the_engines(which, request) -> None:
    from riskvalidation.regulatory import frtb

    doc = request.getfixturevalue(which)
    seen = 0
    for e in doc["invariant_cases"]:
        if not e["id"].startswith("sbm-") or e["id"] == "sbm-low-and-high-scenarios":
            continue
        ins = {v["name"]: v["value"] for v in e["inputs"]}
        ws = [np.array(ins[k], dtype=float) for k in sorted(ins) if k.startswith("ws_")]
        rho = [np.array(ins[f"rho_{b + 1}"], dtype=float).reshape(len(w), len(w)) for b, w in enumerate(ws)]
        gamma = np.full((len(ws), len(ws)), float(ins["gamma"]))
        np.fill_diagonal(gamma, 1.0)
        for sc in ("low", "medium", "high"):
            k_b = np.array([frtb.bucket_charge(w, r, sc) for w, r in zip(ws, rho)])
            d = frtb.cross_bucket_charge_detail(k_b, np.array([float(np.sum(w)) for w in ws]), gamma, sc)
            assert out(e, f"fallback_{sc}") == (1.0 if d.fallback_used else 0.0), (e["id"], sc)
            assert out(e, f"cross_bucket_{sc}") == d.charge, (e["id"], sc)
            seen += 1
    assert seen >= 6


def test_the_fallback_flag_is_read_from_the_engine_not_derived(monkeypatch) -> None:
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import frtb

    real = frtb.cross_bucket_charge_detail
    monkeypatch.setattr(frtb, "cross_bucket_charge_detail", lambda *a, **k: type(real(*a, **k))(5.0, True))
    ex = by_id(bake.build())["sbm-bucket-and-cross-bucket-aggregation"]
    assert all(out(ex, f"fallback_{sc}") == 1.0 and out(ex, f"cross_bucket_{sc}") == 5.0 for sc in ("low", "medium", "high"))


def test_the_trade_effective_notionals_are_the_engines_new_functions(monkeypatch) -> None:
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import sa_ccr

    baseline = by_id(bake.build())
    calls = {"credit": 0, "commodity": 0}
    real_c, real_m = sa_ccr.credit_trade_effective_notional, sa_ccr.commodity_trade_effective_notional

    def credit(*a, **k):
        calls["credit"] += 1
        return real_c(*a, **k)

    def commodity(*a, **k):
        calls["commodity"] += 1
        return real_m(*a, **k)

    monkeypatch.setattr(sa_ccr, "credit_trade_effective_notional", credit)
    monkeypatch.setattr(sa_ccr, "commodity_trade_effective_notional", commodity)
    assert by_id(bake.build()) == baseline and calls["credit"] >= 1 and calls["commodity"] >= 1
    monkeypatch.setattr(sa_ccr, "credit_trade_effective_notional", lambda *a, **k: 1.0)
    monkeypatch.setattr(sa_ccr, "commodity_trade_effective_notional", lambda *a, **k: 1.0)
    changed = by_id(bake.build())
    assert out(changed["cre99-netting-set-2"], "addon_credit") != out(baseline["cre99-netting-set-2"], "addon_credit")
    assert out(changed["cre99-netting-set-3"], "addon_energy") != out(baseline["cre99-netting-set-3"], "addon_energy")


def test_an_engine_refusal_of_a_trade_effective_notional_stops_the_bake_and_writes_nothing(tmp_path, monkeypatch) -> None:
    from pipeline.regulatory import bake
    from riskvalidation.regulatory import sa_ccr

    def refuse(*a, **k):
        raise ValueError("planted refusal (CRE52.34)")

    monkeypatch.setattr(sa_ccr, "credit_trade_effective_notional", refuse)
    with pytest.raises(ValueError, match="planted refusal"):
        bake.bake(tmp_path)
    assert not (tmp_path / "regulatory" / "calculators.json").exists()
