"""CT-2106 to CT-2110: the estimates of a pair are engine calls, checked against independent references on planted files."""
from __future__ import annotations

from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from c21_support import API_HEADER, SEED, make_year, semantics
from riskvalidation.fairness import metrics as rv_metrics
from riskvalidation.fairness import situation as rv_situation
from scipy import stats

from pipeline.cases.c21 import estimates as est
from pipeline.cases.c21 import legal

PAIR = "pair-2018-19"
Z95 = float(stats.norm.ppf(0.975))
DTI_INDEX = {"<20%": 0, "20%-<30%": 1, "30%-<36%": 2, "50%-60%": 4, ">60%": 5}


def attribute(doc: dict, field: str) -> dict:
    return next(a for a in doc["outputs"]["attributes"] if a["field"] == field)


def contrast(doc: dict, field: str, group: str) -> dict:
    return next(c for c in attribute(doc, field)["contrasts"] if c["group"] == group)


def reference_frame(year: int) -> pd.DataFrame:
    """The planted file of a year read and coded independently of the reader and of the design under test."""
    df = pd.DataFrame(make_year(year, 2600, SEED), columns=API_HEADER)
    df = df[df.action_taken.isin(["1", "2", "3"])].copy()
    df["y"] = df.action_taken.isin(["1", "2"]).astype(int)
    df["code"] = df.action_taken.astype(int)
    df["bin"] = [np.nan if d == "NA" else DTI_INDEX.get(d, 3) for d in df.debt_to_income_ratio]
    for c in ("loan_amount", "loan_to_value_ratio", "property_value", "income"):
        df[c] = pd.to_numeric(df[c])
    df["rs"] = pd.to_numeric(df.rate_spread, errors="coerce")
    df["usable"] = df.bin.notna() & (df.loan_amount > 0) & (df.loan_to_value_ratio > 0) & (df.property_value > 0) & (df.income > 0)
    return df


def reference_controls(df: pd.DataFrame) -> pd.DataFrame:
    x = pd.DataFrame(index=df.index)
    for b in (0, 1, 2, 4, 5):
        x[f"dti{b}"] = (df.bin == b).astype(float)
    for c in ("loan_to_value_ratio", "income", "loan_amount", "property_value"):
        x[f"ln_{c}"] = np.log(df[c].where(df.usable, 1.0))
    for c, levels in (("loan_type", (2, 3, 4)), ("loan_purpose", (2, 31, 32, 4, 5)), ("lien_status", (2,)), ("occupancy_type", (2, 3))):
        for lv in levels:
            x[f"{c}{lv}"] = (df[c].astype(int) == lv).astype(float)
    return x


def reference_fit(df: pd.DataFrame, group: str, kind: str, field: str = "derived_race", reference: str = "White"):
    sel = df[field].isin([group, reference]) & df.usable
    if kind == "ols":
        sel &= df.code.isin([1, 2]) & df.rs.notna()
    d = df[sel]
    x = reference_controls(d)
    x = x.loc[:, x.std() > 0]
    x.insert(0, "protected", (d[field] == group).astype(float))
    exog = sm.add_constant(x.to_numpy(), prepend=True)
    res = sm.Logit(d.y.to_numpy(), exog).fit(disp=0, maxiter=200, tol=1e-12) if kind == "logit" else sm.OLS(d.rs.to_numpy(), exog).fit()
    return res.params[1], res.bse[1], len(d)


def test_rates_ratios_and_the_four_fifths_flag_are_the_engine_calls_on_exact_counts(built) -> None:
    sem = semantics()
    doc = built.variants[PAIR]
    df = reference_frame(2018)
    for field in legal.ATTRIBUTES:
        a = attribute(doc, field)
        col = df[field if field != "applicant_age" else "applicant_age"]
        counts = {g["group"]: (g["n_approved"], g["n"]) for g in a["groups"]}
        for g, (x, n) in counts.items():                           # the counts are the file's, group by group
            assert n == int((col == g).sum()) and x == int(((col == g) & (df.y == 1)).sum())
        assert {e["group"] for e in a["excluded_groups"]} == {g for g in set(col) if g in legal.NON_GROUPS[field]}
        ff = a["four_fifths"]
        top = max(counts, key=lambda g: Fraction(counts[g][0], counts[g][1]))
        assert ff["highest_rate_group"] == top and ff["label"] == "employment benchmark" and ff["is_credit_law_threshold"] is False
        xh, nh = counts[top]
        for r in ff["groups"]:
            x, n = counts[r["group"]]
            assert r["flag"] == (Fraction(x, n) < Fraction(4, 5) * Fraction(xh, nh)) == sem.four_fifths_flag(x, n, xh, nh)
        rates = {g: rv_metrics.SelectionRate(g, n, x, x / n) for g, (x, n) in counts.items()}
        engine = rv_metrics.four_fifths_flag(rates)
        assert engine.highest_rate_group == top and engine.flag == {r["group"]: r["flag"] for r in ff["groups"]}
        ref = a["reference_group"]
        for c in a["contrasts"]:
            xg, ng = counts[c["group"]]
            xr, nr = counts[ref]
            assert c["parity_gap"] == pytest.approx(xg / ng - xr / nr, abs=1e-12)
            assert c["parity_ratio"] == pytest.approx((xg / ng) / (xr / nr)) == pytest.approx(c["adverse_impact_ratio"]["value"])
    # the golden of the contract: 60 of 100 against 75 of 100 is exactly four-fifths and is not flagged; 5999 of 10000 is
    exact = rv_metrics.four_fifths_flag({"h": rv_metrics.SelectionRate("h", 100, 75, 0.75), "g": rv_metrics.SelectionRate("g", 100, 60, 0.6)})
    assert exact.flag == {"h": False, "g": False} and 60 / 100 / (75 / 100) != 0.8 and sem.four_fifths_flag(60, 100, 75, 100) is False
    below = rv_metrics.four_fifths_flag({"h": rv_metrics.SelectionRate("h", 10000, 7500, 0.75), "g": rv_metrics.SelectionRate("g", 10000, 5999, 0.5999)})
    assert below.flag["g"] is True


def test_z_and_fisher_equal_the_engine_scipy_and_statsmodels(built) -> None:
    from statsmodels.stats.proportion import proportions_ztest

    doc = built.variants[PAIR]
    n_checked = 0
    for a in doc["outputs"]["attributes"]:
        ref = next(g for g in a["groups"] if g["group"] == a["reference_group"])
        for c in a["contrasts"]:
            g = next(x for x in a["groups"] if x["group"] == c["group"])
            assert c["reference_group"] == a["reference_group"] and c["group"] != c["reference_group"]
            stat, p = proportions_ztest([g["n_approved"], ref["n_approved"]], [g["n"], ref["n"]])
            assert c["z_test"]["statistic"] == pytest.approx(stat, rel=1e-9, abs=1e-12) and c["z_test"]["p_value"] == pytest.approx(p, rel=1e-9, abs=1e-15)
            table = [[g["n_approved"], g["n_denied"]], [ref["n_approved"], ref["n_denied"]]]
            odds, pf = stats.fisher_exact(table)
            assert c["fisher_exact"]["p_value"] == pytest.approx(pf, rel=1e-9, abs=1e-15)
            assert c["fisher_exact"]["odds_ratio"] == pytest.approx(odds, rel=1e-9)
            n_checked += 1
    assert n_checked >= 12
    rows = {(r["test_id"], r["segment"]): r for r in doc["tests"]}
    c = contrast(doc, "derived_race", "Black or African American")
    z = rows[("fair.two_proportion_z", "derived_race|Black or African American vs White")]
    assert z["statistic"] == pytest.approx(c["z_test"]["statistic"]) and z["p_value"] == pytest.approx(c["z_test"]["p_value"])


def test_controlled_estimates_equal_statsmodels_and_name_the_missing_credit_score(built) -> None:
    for pair in ("pair-2018-19", "pair-2020-21"):
        doc = built.variants[pair]
        year = doc["outputs"]["fit_year"]
        df = reference_frame(year)
        for group, field, reference in (("Black or African American", "derived_race", "White"), ("Hispanic or Latino", "derived_ethnicity", "Not Hispanic or Latino"),
                                        ("Female", "derived_sex", "Male")):
            c = contrast(doc, field, group)
            for key, kind in (("controlled", "logit"), ("rate_spread", "ols")):
                est_ = c[key]["estimate"]
                beta, se, n = reference_fit(df, group, kind, field, reference)
                tol = 1e-6 if kind == "logit" else 1e-8
                assert est_["coefficient"] == pytest.approx(beta, abs=tol), (pair, group, kind)
                assert (est_["ci"]["hi"] - est_["ci"]["lo"]) / (2 * Z95) == pytest.approx(se, abs=tol)
                assert est_["n"] == n and est_["missing_controls"] == ["credit_score"] and est_["controls"] == list(legal.CONTROLS)
                assert est_["ci"]["level"] == 0.95 and est_["label"] == "approximation of comparative evidence"
    # every controlled and rate-spread estimate of every contrast of every document names the missing credit score
    for doc in (built.variants[v] for v in built.order):
        for a in doc["outputs"]["attributes"]:
            for c in a["contrasts"]:
                for key in ("controlled", "rate_spread"):
                    if c[key]["estimate"] is not None:
                        assert c[key]["estimate"]["missing_controls"] == ["credit_score"]
                    else:
                        assert c[key]["reason"]
    # the planted effect on the Black or African American group (-0.8 log-odds) is recovered
    for v in built.order:
        e = contrast(built.variants[v], "derived_race", "Black or African American")["controlled"]["estimate"]
        assert abs(e["coefficient"] + 0.8) < 0.35 and e["odds_ratio"] == pytest.approx(np.exp(e["coefficient"]))
    # the unconditional rate gap is large in the planted files, and the sex contrast has no planted effect
    f = contrast(built.variants[PAIR], "derived_sex", "Female")["controlled"]["estimate"]
    assert abs(f["coefficient"]) < 0.4


def test_confirmation_refits_the_same_estimate_on_the_next_year_by_sign_and_size(built) -> None:
    doc = built.variants[PAIR]
    c = contrast(doc, "derived_race", "Black or African American")
    fit, confirm = c["controlled"]["estimate"]["coefficient"], c["confirmation"]["estimate"]
    beta, _, _ = reference_fit(reference_frame(2019), "Black or African American", "logit")
    assert confirm["fit_year"] == 2018 and confirm["confirm_year"] == 2019
    assert confirm["fit_coefficient"] == fit and confirm["confirm_coefficient"] == pytest.approx(beta, abs=1e-6)
    assert confirm["same_sign"] is True and confirm["size_ratio"] == pytest.approx(beta / fit, abs=1e-5)
    rows = {(r["test_id"], r["segment"]): r for r in doc["tests"]}
    rep = rows[("fair.replication", "derived_race|Black or African American vs White|controlled")]
    assert rep["metric"] == pytest.approx(confirm["size_ratio"]) and rep["light"] == "green"
    assert ("fair.replication", "derived_race|Black or African American vs White|rate_spread") in rows
    # an estimate that cannot be fitted has its reason and no number
    none = est.Fit(None, 0, "a group has no usable row", [])
    block, rep_none = est._confirmation(none, none, (2018, 2019))
    assert block["estimate"] is None and "cannot be confirmed" in block["reason"] and rep_none is None
    assert est._controlled(none) == {"estimate": None, "reason": "a group has no usable row"}


def test_situation_testing_is_ceteris_paribus_with_range_normalization_and_categorical_columns(built) -> None:
    doc = built.variants[PAIR]
    s = doc["outputs"]["situation_testing"]
    assert s["comparator"] == "ceteris-paribus" and s["distance_normalization"] == "range" and s["counterfactual_test"]["run"] is False
    assert s["attribute"] == "derived_sex" and s["k"] == 30 and s["alpha"] == 0.05 and s["tau"] == 0 and s["centers"] == "excluded"
    names = est.SITUATION_COLUMNS
    assert [n for n, c in zip(names, est.SITUATION_CATEGORICAL) if c] == ["loan_type", "loan_purpose", "lien_status", "occupancy_type"]
    assert "dti_bin" in names and not est.SITUATION_CATEGORICAL[names.index("dti_bin")]       # the binned ratio is ordinal: its bin index
    df = reference_frame(2018)
    d = df[df.derived_sex.isin(["Female", "Male"]) & df.usable]
    x = reference_controls(d)
    cols = [d.bin.to_numpy(float), *(x[f"ln_{c}"].to_numpy() for c in ("loan_to_value_ratio", "income", "loan_amount", "property_value")),
            *(d[c].astype(float).to_numpy() for c in ("loan_type", "loan_purpose", "lien_status", "occupancy_type"))]
    res = rv_situation.situation_test(np.column_stack(cols), (d.derived_sex == "Female").astype(int).to_numpy(), d.y.to_numpy(), 30, tau=0.0,
                                      alpha=0.05, comparator="ceteris-paribus", normalization="range", categorical=est.SITUATION_CATEGORICAL)
    assert (s["n_complainants"], s["n_cases"], s["n_significant"]) == (res.n_complainants, res.n_cases, res.n_significant)
    row = next(r for r in doc["tests"] if r["test_id"] == "fair.situation_testing")
    assert row["metric"] == pytest.approx(res.n_significant / res.n_complainants) and row["segment"] == "derived_sex"
    with pytest.raises(ValueError, match="counterfactual is required"):
        rv_situation.situation_test(np.column_stack(cols), (d.derived_sex == "Female").astype(int).to_numpy(), d.y.to_numpy(), 30,
                                    comparator="mutatis-mutandis")
