"""S-2 of the method tiers: the VAR conditional forecast and the growth-at-risk quantile satellite beside the OLS satellites.

Known truth on synthetic series first (the engine functions are exercised through the case's producer, on a train span only), then the
committed models document: its two model records are the producer's output on the case's data, they back-cast 2008-09 and 2020 on
prior data with the OLS satellite beside and report the coefficient-sign checks, and no number of the OLS back-cast moved.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from c18_support import C18, ROOT, data_root, requires_raw

from pipeline.cases.c18 import fed
from pipeline.cases.c18 import params as P
from pipeline.cases.c18 import satellites as sat
from pipeline.cases.c18 import stress_rungs as sr
from pipeline.core.schemas import validate_document

GFC, COVID = sr.WINDOWS
EM_DASH = chr(0x2014)


def quarters_from(first: str, last: str) -> list[str]:
    out, q = [first], first
    while q != last:
        q = P.next_quarters(q, 1)[0]
        out.append(q)
    return out


def synthetic_satellite(seed: int = 7) -> SimpleNamespace:
    """A residential-type series from a known VAR(1) of growth, unemployment and the loss rate (identity link), 1991 Q1 to 2025 Q4."""
    qs = quarters_from("1985-03-31", "2025-12-31")
    n = len(qs)
    rng = np.random.default_rng(seed)
    g, u, z = np.zeros(n), np.zeros(n), np.zeros(n)
    u[0], z[0] = 6.0, 0.01
    for t in range(1, n):
        g[t] = 1.0 + 0.5 * g[t - 1] + rng.normal(0, 0.8)
        u[t] = 1.5 + 0.8 * u[t - 1] - 0.15 * g[t - 1] + rng.normal(0, 0.1)
        z[t] = 0.002 + 0.7 * z[t - 1] - 0.0008 * g[t - 1] + 0.0012 * u[t - 1] + rng.normal(0, 0.0002)
    return SimpleNamespace(loan_type="residential", series_id="RERES", quarters=tuple(qs), rates=z, x=np.column_stack([g, u]))


def perturbed_after(s: SimpleNamespace, last_kept: str) -> SimpleNamespace:
    i = list(s.quarters).index(last_kept) + 1
    rates, x = s.rates.copy(), s.x.copy()
    rates[i:] += 0.05
    x[i:] += 3.0
    return SimpleNamespace(**{**vars(s), "rates": rates, "x": x})


def test_the_var_back_cast_recovers_a_known_var_and_names_its_signs() -> None:
    s = synthetic_satellite()
    r = sr.var_backcast(s, GFC)
    est = {c["name"]: c["estimate"] for c in r["coefficients"]}
    assert est["ar_1"] == pytest.approx(0.7, abs=0.08)
    assert est["real_gdp_growth_lag1"] == pytest.approx(-0.0008, abs=0.0004)
    assert est["unemployment_rate_lag1"] == pytest.approx(0.0012, abs=0.0005)
    assert [c["expected_sign"] for c in r["coefficients"]] == ["none", "positive", "negative", "positive"]
    assert r["sign_check"] == {"wrong_signs": 0, "offending": [], "light": "green"}
    assert [q["quarter_end"] for q in r["quarters"]][0] == "2008-03-31" and len(r["quarters"]) == 8
    assert r["fit_window"] == {"start": "1991-03-31", "end": "2007-12-31"} and r["n_obs"] == 68 - 1
    truth_rmse = r["metrics"]["var"]["rmse"]
    assert truth_rmse < 0.002          # the loss rate is about 0.01: a conditional forecast of a known process is close to the realised path
    assert r["conditioned_on"] == ["real_gdp_growth"]
    # given BOTH macro paths a VAR(1) conditional forecast is the OLS satellite's regression: the form adds no model, and the gap says so
    assert r["full_conditioning_gap_to_ols"] < 1e-9
    assert r["closer"] in ("var", "ols") and r["metrics"]["rmse_ratio_var_over_ols"] == pytest.approx(truth_rmse / r["metrics"]["ols"]["rmse"])


def test_given_one_scenario_variable_the_var_differs_from_the_satellite_and_the_unemployment_path_is_its_own() -> None:
    r = sr.var_backcast(synthetic_satellite(), COVID)
    var, ols = (np.array([q[k] for q in r["quarters"]]) for k in ("var", "ols"))
    assert float(np.max(np.abs(var - ols))) > 1e-5                        # the GDP-path conditioning is a different model from the satellite fed both paths
    assert any(q["unemployment_var"] != q["unemployment_realised"] for q in r["quarters"])


def test_a_wrong_sign_is_reported_not_hidden() -> None:
    s = synthetic_satellite()
    flipped = SimpleNamespace(**{**vars(s), "x": np.column_stack([-s.x[:, 0], s.x[:, 1]])})     # a rise in growth now raises the loss rate
    r = sr.var_backcast(flipped, GFC)
    assert r["sign_check"]["wrong_signs"] >= 1 and "real_gdp_growth_lag1" in r["sign_check"]["offending"] and r["sign_check"]["light"] == "red"


def test_the_train_span_ends_before_the_episode_and_the_future_never_enters_the_fit() -> None:
    s = synthetic_satellite()
    a = sr.var_backcast(s, GFC)
    b = sr.var_backcast(perturbed_after(s, "2007-12-31"), GFC)
    assert a["coefficients"] == b["coefficients"] and a["n_obs"] == b["n_obs"]              # the fit reads up to 2007 Q4 only
    assert [q["var"] for q in a["quarters"]] != [q["var"] for q in b["quarters"]]            # the episode's macro path does drive the forecast
    assert [q["ols"] for q in a["quarters"]] != [q["ols"] for q in b["quarters"]]
    with pytest.raises(ValueError, match="not before the episode"):
        sr.var_backcast(s, sr.Window("overlap", "2008-03-31", "2008-03-31", "2009-12-31", {"en": "x", "es": "x"}))
    with pytest.raises(ValueError, match="quarter after"):
        sr.var_backcast(s, sr.Window("gap", "2007-12-31", "2008-09-30", "2009-12-31", {"en": "x", "es": "x"}))


def synthetic_history(seed: int = 3) -> pd.DataFrame:
    qs = quarters_from("1976-03-31", "2025-12-31")
    n = len(qs)
    rng = np.random.default_rng(seed)
    spread = np.zeros(n)
    for t in range(1, n):
        spread[t] = 0.8 * spread[t - 1] + rng.normal(0, 0.5)
    g = np.zeros(n)
    for t in range(1, n):
        g[t] = 1.0 + 0.9 * spread[t - 1] + rng.normal(0, 1.0)
    return pd.DataFrame({"quarter_end": qs, "real_gdp_growth": g, "unemployment_rate": 6.0, "prime_rate": 8.0, "treasury_10y": 8.0 + spread})


def test_growth_at_risk_quantiles_are_ordered_signed_and_scored_beside_the_unconditional_ones() -> None:
    h = synthetic_history()
    g = sr.gar_window(h, GFC)
    taus = [c["tau"] for c in g["coefficients"]]
    assert taus == list(sr.GAR_TAUS)
    median = next(c for c in g["coefficients"] if c["tau"] == 0.5)
    spread_coef = next(t for t in median["terms"] if t["name"] == "term_spread")["estimate"]
    assert 0.4 < spread_coef < 1.0                                               # the generator carries 0.9 through persistence: truth is about 0.66
    assert median["sign_check"]["light"] in ("green", "red") and median["sign_check"]["wrong_signs"] == len(median["sign_check"]["offending"])
    for o in g["origins"]:
        assert o["quantiles"] == sorted(o["quantiles"])                           # rearranged, never crossing
    assert [o["origin"] for o in g["origins"]] == ["2007-12-31", "2008-03-31", "2008-06-30", "2008-09-30", "2008-12-31"]
    assert g["origins"][-1]["target_end"] == "2009-12-31"                            # the last scored target is the episode's last quarter
    assert g["train_origins"]["last"] == "2006-12-31"                                # the last train target ends at the fit end, 2007 Q4
    assert len(g["pinball"]) == len(sr.GAR_TAUS) and all(p["ratio"] > 0 for p in g["pinball"])
    # a conditional quantile fitted on a generator that depends on the spread beats the unconditional quantile out of the train span
    assert g["mean_pinball_ratio"] < 1.05
    assert g["coverage"][0]["n"] == 5 and 0 <= g["coverage"][0]["hits"] <= 5


def test_growth_at_risk_reads_the_train_span_only() -> None:
    h = synthetic_history()
    a = sr.gar_window(h, GFC)
    h2 = h.copy()
    i = list(h2["quarter_end"]).index("2007-12-31") + 1
    h2.loc[i:, "real_gdp_growth"] += 5.0
    h2.loc[i:, "treasury_10y"] += 2.0
    b = sr.gar_window(h2, GFC)
    assert a["coefficients"] == b["coefficients"] and a["unconditional_quantiles"] == b["unconditional_quantiles"]
    assert a["origins"][1]["quantiles"] != b["origins"][1]["quantiles"]
    with pytest.raises(ValueError, match="not before the episode"):
        sr.gar_window(h, sr.Window("overlap", "2008-03-31", "2008-03-31", "2009-12-31", {"en": "x", "es": "x"}))


# ------------------------------------------------------------------------------------------------ the committed documents


def committed() -> dict:
    return json.loads((C18 / "models-banco-andino.json").read_text(encoding="utf-8"))


def record(doc: dict, mid: str) -> dict:
    return next(m for m in doc["model"] if m["id"] == mid)


def test_the_models_document_carries_both_rungs_as_sota_models() -> None:
    doc = committed()
    v, g = record(doc, sr.VAR_MODEL_ID), record(doc, sr.GAR_MODEL_ID)
    for m in (v, g):
        assert m["family"] == "stress" and m["engine"] == "riskvalidation" and m["details"]["tier"] == "sota"
        assert m["title"]["en"] != m["title"]["es"] and EM_DASH not in json.dumps(m, ensure_ascii=False)
    assert v["rung"] == "var-conditional-forecast" and g["rung"] == "growth-at-risk-quantile"
    assert [w["window_id"] for w in v["details"]["var"]["windows"]] == ["gfc-2008-09", "pandemic-2020"]
    assert [w["window_id"] for w in g["details"]["growth_at_risk"]["windows"]] == ["gfc-2008-09", "pandemic-2020"]
    for w in v["details"]["var"]["windows"]:
        assert sorted(r["fed_loan_type"] for r in w["per_loan_type"]) == sorted(P.FED_TYPES)
        for r in w["per_loan_type"]:
            assert r["fit_window"]["end"] == w["fit_end"] < w["start"] and r["quarters"][0]["quarter_end"] == w["start"] and r["quarters"][-1]["quarter_end"] == w["end"]
            assert r["metrics"]["var"]["light"] != "error" and r["metrics"]["ols"]["light"] != "error"          # the engine's leakage light
            assert r["full_conditioning_gap_to_ols"] < 1e-9 and r["conditioned_on"] == ["real_gdp_growth"]
    for w in g["details"]["growth_at_risk"]["windows"]:
        assert [c["tau"] for c in w["coefficients"]] == list(sr.GAR_TAUS) and w["fit_end"] < w["origins"][1]["origin"]
    # the three existing model records are untouched
    assert [m["id"] for m in doc["model"]][:3] == [sat.MODEL_ID, "c18-aggregation-ladder", "c18-capital-engine"]


def test_the_ols_satellite_beside_the_var_is_the_existing_backcast_of_2020_and_none_of_its_numbers_moved() -> None:
    doc = committed()
    base = json.loads((C18 / "baseline.json").read_text(encoding="utf-8"))
    old = {b["fed_loan_type"]: b for b in base["outputs"]["backcast"]["per_loan_type"]}
    win = next(w for w in record(doc, sr.VAR_MODEL_ID)["details"]["var"]["windows"] if w["window_id"] == "pandemic-2020")
    for r in win["per_loan_type"]:
        o = old[r["fed_loan_type"]]
        assert [q["quarter_end"] for q in r["quarters"]] == [q["quarter_end"] for q in o["quarters"]]
        assert np.allclose([q["ols"] for q in r["quarters"]], [q["predicted"] for q in o["quarters"]], rtol=0, atol=1e-9)
        assert np.allclose([q["realised"] for q in r["quarters"]], [q["realised"] for q in o["quarters"]], rtol=0, atol=1e-9)
        assert r["metrics"]["ols"]["rmse"] == pytest.approx(o["metrics"]["rmse"], abs=1e-9)


def test_every_summary_number_is_recomputed_from_the_rows_it_summarises() -> None:
    v = record(committed(), sr.VAR_MODEL_ID)["details"]["var"]
    for w, s in zip(v["windows"], v["summary"], strict=True):
        assert s["window_id"] == w["window_id"] and s["loan_types"] == len(w["per_loan_type"])
        for r in w["per_loan_type"]:
            real = np.array([q["realised"] for q in r["quarters"]])
            for key in ("var", "ols"):
                pred = np.array([q[key] for q in r["quarters"]])
                assert r["metrics"][key]["rmse"] == pytest.approx(float(np.sqrt(np.mean((pred - real) ** 2))), rel=1e-7, abs=1e-9)
            ratio = r["metrics"]["var"]["rmse"] / r["metrics"]["ols"]["rmse"]
            assert r["metrics"]["rmse_ratio_var_over_ols"] == pytest.approx(ratio, rel=1e-7, abs=1e-9)
            assert r["closer"] == ("var" if ratio < 1.0 else "ols")
            assert r["sign_check"]["wrong_signs"] == len(r["sign_check"]["offending"])
        assert s["var_closer"] == sum(r["closer"] == "var" for r in w["per_loan_type"]) and s["var_closer"] + s["ols_closer"] == s["loan_types"]
    g = record(committed(), sr.GAR_MODEL_ID)["details"]["growth_at_risk"]
    for w, s in zip(g["windows"], g["summary"], strict=True):
        assert s["mean_pinball_ratio"] == pytest.approx(float(np.mean([p["ratio"] for p in w["pinball"]])), rel=1e-7, abs=1e-9)
        assert s["better_than_unconditional"] == (s["mean_pinball_ratio"] < 1.0) and s["origins"] == len(w["origins"])
        for c in w["coverage"]:
            k = sr.GAR_TAUS.index(c["tau"])
            assert c["hits"] == sum(o["realised"] < o["quantiles"][k] for o in w["origins"]) and c["n"] == len(w["origins"])


def test_the_acceptance_criterion_and_the_statement_are_the_measured_ones() -> None:
    d = record(committed(), sr.VAR_MODEL_ID)["details"]
    a = d["acceptance"]
    assert a["met"] is True and a["leak_free"] is True and a["complete"] is True and a["sign_checks_reported"] is True
    assert a["var_sign_checks"] == 10 and a["gar_sign_checks"] == 10
    want = sr.statement(record(committed(), sr.GAR_MODEL_ID)["details"] | {"var": d["var"]})
    assert d["statement"] == want and want["en"] != want["es"]
    for lang in ("en", "es"):
        assert EM_DASH not in want[lang] and "->" not in want[lang]


def test_the_stress_rung_blocks_validate_against_their_own_schema() -> None:
    schema = json.loads((ROOT / "tests" / "c18" / "stress_rungs.schema.json").read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator

    doc = committed()
    for mid in (sr.VAR_MODEL_ID, sr.GAR_MODEL_ID):
        errs = sorted(Draft202012Validator(schema).iter_errors(record(doc, mid)["details"]), key=lambda e: list(e.path))
        assert errs == [], [f"{list(e.path)}: {e.message}" for e in errs[:3]]
    bad = json.loads(json.dumps(record(doc, sr.VAR_MODEL_ID)["details"]))
    bad["var"]["windows"][0]["per_loan_type"][0]["closer"] = "maybe"
    assert list(Draft202012Validator(schema).iter_errors(bad))
    validate_document("data/derived/C18/models-banco-andino.json", doc)


def assert_close(a, b, where: str) -> None:
    """Equal structure, strings and integers; floats to 1e-9 relative (the writer keeps 11 significant digits)."""
    if isinstance(a, dict):
        assert isinstance(b, dict) and a.keys() == b.keys(), where
        for k in a:
            assert_close(a[k], b[k], f"{where}.{k}")
    elif isinstance(a, list):
        assert isinstance(b, list) and len(a) == len(b), where
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            assert_close(x, y, f"{where}[{i}]")
    elif isinstance(a, float) and isinstance(b, float):
        assert a == pytest.approx(b, rel=1e-7, abs=1e-9), where
    else:
        assert a == b, where


@requires_raw
def test_the_committed_details_are_what_the_producer_computes_on_the_case_data_and_it_is_deterministic() -> None:
    f = fed.read_inputs(data_root())
    sats = sat.fit_all(fed.read_chargeoffs(data_root()), f)
    a = sr.build(sats, f.history)
    b = sr.build(sats, f.history)
    assert a == b
    doc = committed()
    got = json.loads(json.dumps(a))
    for key in ("var", "acceptance", "tier"):
        assert_close(got[key], record(doc, sr.VAR_MODEL_ID)["details"][key], key)
    for key in ("growth_at_risk", "tier"):
        assert_close(got[key], record(doc, sr.GAR_MODEL_ID)["details"][key], key)
