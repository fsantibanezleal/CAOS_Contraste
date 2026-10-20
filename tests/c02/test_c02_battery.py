"""CT-0206 to CT-0210: the battery, the challenger table and the three exploratory blocks, all through `riskvalidation`.

The planted bake (small files, a known logistic rule) is the input; every expected value is recomputed here from the same arrays by
calling the engine directly, never by copying the producer's code path.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pytest
from c02_support import ROOT, SEED, semantics
from scipy.stats import norm

from pipeline.cases.c02 import blocks
from pipeline.cases.c02 import conventions as cv


def engine():
    from riskvalidation.ml import challenger, generalisation
    from riskvalidation.validation import calibration as cal
    from riskvalidation.validation import discrimination as disc
    from riskvalidation.validation import ml
    from riskvalidation.validation import stability as st

    return cal, disc, st, ml, challenger, generalisation


def rid_of(model_id: str, hid: str) -> str:
    return model_id.removeprefix(f"{hid}-")


def test_every_rung_statistic_is_the_engine_call_on_the_same_arrays(built) -> None:
    cal, disc, st, ml, _, gen = engine()
    for hid in ("h1", "h4", "pooled"):
        f, doc = built.fits[hid], built.variants[hid]
        y, ytr = f.yhold, f.ytr
        rungs = doc["outputs"]["rungs"]
        assert [rid_of(r["model_id"], hid) for r in rungs] == list(cv.BATTERY_RUNGS) and [m["id"] for m in doc["model"]] == [r["model_id"] for r in rungs]
        csi = [r for r in doc["tests"] if r["test_id"] == "stability.csi"]
        assert len(csi) == len(f.pp.columns) and all(r["model_id"] is None for r in csi)
        for r in rungs:
            rid = rid_of(r["model_id"], hid)
            p, ptr = f.rungs[rid].pd(f.Xhold), f.rungs[rid].pd(f.Xtr)
            auc = disc.disc_auc(p, y)
            d = r["discrimination"]
            assert d["auc"] == auc.metric and d["gini"] == auc.extras["gini"]
            assert (d["auc_ci"]["lo"], d["auc_ci"]["hi"]) == (auc.extras["ci95_low"], auc.extras["ci95_high"]) and d["auc_ci"]["method"] == "delong"
            assert d["ks"] == disc.disc_ks(p, y).metric
            c = r["calibration"]
            hl = cal.pd_hosmer_lemeshow(y, p, fitted=False)
            assert c["hosmer_lemeshow"] == {"statistic": hl.statistic, "df": hl.extras["dof"], "p_value": hl.p_value}
            assert c["brier"] == cal.pd_brier(y, p).metric and c["ece"] == cal.pd_ece(y, p).metric
            # the overfit gap is the engine's: train AUC minus holdout AUC, rounded as the engine rounds it
            tr = disc.disc_auc(ptr, ytr).metric
            og = gen.overfit_gap(tr, auc.metric, cv.OVERFIT_TOLERANCE)
            assert r["overfit"] == {"train_auc": tr, "holdout_auc": auc.metric, "gap": og.gap, "tolerance": cv.OVERFIT_TOLERANCE, "flag": og.flag}
            edges = np.unique(st.quantile_edges(ptr, 10))
            psi = st.stability_psi(st.bin_counts(ptr, edges), st.bin_counts(p, edges))
            assert r["stability"]["psi"] == (psi.metric if psi.metric is not None else psi.statistic)
            assert r["stability"]["csi_max"] == max((x["metric"] if x["metric"] is not None else x["statistic"]) for x in csi)
            rows = {(x["test_id"]): x for x in doc["tests"] if x["model_id"] == r["model_id"]}
            assert rows["pd.hosmer_lemeshow"]["statistic"] == hl.statistic and rows["pd.hosmer_lemeshow"]["light"] == hl.light.value
            jf = cal.pd_jeffreys(len(y), int(y.sum()), float(p.mean()))
            assert rows["pd.jeffreys"]["p_value"] == jf.p_value
            assert rows["pd.binomial"]["p_value"] == cal.pd_binomial(len(y), int(y.sum()), float(p.mean())).p_value
            assert rows["stability.psi"]["light"] == psi.light.value
            ov = ml.overfit(r["model_id"], og)
            assert rows["ml.overfit"]["light"] == ov.light.value and rows["ml.overfit"]["statistic"] == ov.statistic
            # reliability: the engine's ECE bins, ties merged, with the Wilson interval of the engine harness
            n_bins = sum(b["n"] for b in r["reliability"])
            assert n_bins == len(y) and 1 <= len(r["reliability"]) <= 10
        # the descriptive rows are the figures of the rungs, not test rows: no row is `not_evaluated` with a number
        for row in doc["tests"]:
            if row["light"] == "not_evaluated":
                assert row["statistic"] is None and row["p_value"] is None and row["metric"] is None and row["notes"]
        assert not [x for x in doc["tests"] if x["test_id"] in ("disc.auc", "disc.ks", "pd.brier", "pd.ece")]
    # the product re-implements no statistic the engine provides: no metric or test of scikit-learn or SciPy is imported
    banned = re.compile(r"roc_auc_score|brier_score_loss|ks_2samp|kstest|chi2_contingency|chisquare|binomtest|mannwhitneyu|"
                        r"calibration_curve|average_precision_score|from sklearn\.metrics import(?!.*roc_curve\b)|from scipy\.stats import(?!\s+norm\b)")
    for path in sorted((ROOT / "data-pipeline" / "pipeline" / "cases" / "c02").glob("*.py")):
        assert not banned.search(path.read_text(encoding="utf-8")), path.name


def test_the_challenger_table_is_the_engine_delong_and_paired_brier_bootstrap(built) -> None:
    _, disc, _, ml, ch, _ = engine()
    from pipeline.core.calibration import MASTER_SCALE_UPPER

    for hid in ("h2", "pooled"):
        f, doc = built.fits[hid], built.variants[hid]
        y = f.yhold
        champ = f.rungs[cv.CHAMPION].pd(f.Xhold)
        table = doc["outputs"]["challenger"]
        assert [rid_of(c["challenger"], hid) for c in table] == list(cv.CHALLENGERS) and {c["champion"] for c in table} == {f"{hid}-{cv.CHAMPION}"}
        z = float(norm.ppf(0.975))
        for c in table:
            rid = rid_of(c["challenger"], hid)
            p = f.rungs[rid].pd(f.Xhold)
            dl = disc.disc_delong(p, champ, y)
            half = z * math.sqrt(dl.extras["variance"])
            assert c["auc_diff"] == dl.extras["difference"] and c["delong_p_value"] == dl.p_value
            assert math.isclose(c["auc_diff_ci"]["lo"], dl.extras["difference"] - half, rel_tol=1e-12, abs_tol=1e-15)
            assert math.isclose(c["auc_diff_ci"]["hi"], dl.extras["difference"] + half, rel_tol=1e-12, abs_tol=1e-15)
            pb = ch.paired_brier_bootstrap(champ, p, y, cv.N_BOOT, SEED + cv.BOOT_SEED_OFFSET)
            assert (c["brier_diff"], c["brier_diff_ci"]["lo"], c["brier_diff_ci"]["hi"]) == (pb.diff, pb.lo, pb.hi)
            assert c["grade_disagreement_share"] == ch.grade_disagreement(champ, p, np.array(MASTER_SCALE_UPPER[:-1]), cv.GRADE_NOTCHES)
            rows = {r["test_id"]: r for r in doc["tests"] if r["model_id"] == c["challenger"]}
            assert rows["disc.delong"]["p_value"] == dl.p_value and rows["ml.challenger_brier"]["light"] == ml.challenger_brier(c["challenger"], pb).light.value
    assert semantics().check_c02(built.variants["h2"]) == []


def test_the_transfer_block_is_exploratory_and_its_diagonal_is_the_within_file_auc(built) -> None:
    _, disc, *_ = engine()
    pooled = built.variants["pooled"]["outputs"]["transfer"]
    assert pooled["label"] == "exploratory" and pooled["cells"] == [] and "firm overlap" in pooled["reason"]["en"]
    for k in (2, 5):
        hid = f"h{k}"
        f, doc = built.fits[hid], built.variants[hid]
        t = doc["outputs"]["transfer"]
        assert t["label"] == "exploratory" and "overlap" in t["reason"]["en"] and "inflated" in t["reason"]["en"]
        assert len(t["cells"]) == len(cv.TRANSFER_RUNGS) * 5 and {c["fitted_on_years"] for c in t["cells"]} == {k}
        by = {(c["rung"], c["scored_on_years"]): c for c in t["cells"]}
        codes = [cv.RUNG_CODE[r] for r in cv.TRANSFER_RUNGS]
        assert len(by) == len(t["cells"]) and set(r for r, _ in by) == set(codes)
        for rid in cv.TRANSFER_RUNGS:
            code = cv.RUNG_CODE[rid]
            for j in range(1, 6):
                g = built.fits[f"h{j}"]
                Xj = f.pp.transform(g.X.iloc[g.sp.holdout][list(cv.ATTRIBUTES)])
                p = f.rungs[rid].pd(Xj)
                cell = by[(code, j)]
                assert cell["auc"] == disc.disc_auc(p, g.yhold).metric and cell["n"] == len(g.yhold) and cell["events"] == int(g.yhold.sum())
            own = next(r for r in doc["outputs"]["rungs"] if r["model_id"] == f"{hid}-{rid}")
            assert by[(code, k)]["auc"] == own["discrimination"]["auc"]                             # the diagonal is the within-file holdout AUC


def test_the_term_structure_block_is_exploratory_and_comes_from_the_engine() -> None:
    from riskvalidation.provisions import term_structure as ts

    rows = {1: 7027, 2: 10173, 3: 10503, 4: 9792, 5: 5910}
    events = {1: 271, 2: 400, 3: 495, 4: 515, 5: 410}
    b = blocks.term_structure_block(rows, events)
    cum = np.array([events[k] / rows[k] for k in range(1, 6)])
    eng = ts.from_cumulative(cum, np.array([12, 24, 36, 48, 60]))
    assert b["label"] == "exploratory" and b["source"] == cv.TERM_SOURCE and b["cumulative_nondecreasing"] is True
    assert [p["years"] for p in b["points"]] == [1, 2, 3, 4, 5]
    assert [p["cumulative_pd"] for p in b["points"]] == list(cum) and [p["hazard"] for p in b["points"]] == list(eng.hazard)
    survive = 1.0
    for p in b["points"]:
        survive *= 1 - p["hazard"]
        assert abs((1 - survive) - p["cumulative_pd"]) < 1e-12
    # the rates must be strictly increasing for a term structure: otherwise C02 refuses to write the block, naming the rates
    with pytest.raises(blocks.TermStructureError, match="strictly increasing"):
        blocks.term_structure_block(rows, {**events, 2: 300})
    # the back-test row is the engine's, with the champion's horizon PDs against the holdout event rates
    from riskvalidation.validation import ifrs9

    pred = np.array([0.04, 0.045, 0.05, 0.055, 0.07])
    n = np.array([2108, 3052, 3151, 2938, 1773])
    d = np.array([85, 126, 148, 150, 124])
    row = blocks.backtest_row(pred, n, d)
    eng_row = ifrs9.lifetime_pd_backtest(np.array([12, 24, 36, 48, 60]), pred, d / n, n, d, model_id=None, segment=blocks.BACKTEST_SEGMENT)
    assert row["test_id"] == "ifrs9.lifetime_pd_backtest" and row["metric"] == eng_row.metric and row["light"] == eng_row.light.value


def test_the_impact_block_is_exploratory_and_comes_from_the_provisions_engine() -> None:
    pds = np.array([0.03, 0.04, 0.05, 0.06, 0.08])
    detail, impact = blocks.impact_block(pds, "P1 scorecard horizon PDs, test")
    assert detail["label"] == "exploratory" and detail["source"] == "engine-provisions-api" and detail["lgd"] == {"value": cv.LGD, "label": "assumption"}
    assert math.isclose(detail["ecl_12m_effect"], 0.03 * cv.LGD, rel_tol=1e-12)                    # q(1) * LGD * EAD, undiscounted
    assert math.isclose(detail["ecl_lifetime_effect"], 0.08 * cv.LGD, rel_tol=1e-12)               # cumulative(5) * LGD * EAD
    assert detail["reason_if_null"] is None and set(impact) == {"ecl_12m_effect", "ecl_lifetime_effect"}
    assert impact["ecl_12m_effect"]["value"] == detail["ecl_12m_effect"] and "exploratory" in impact["ecl_lifetime_effect"]["label"]["en"]
    # the horizon PDs cannot form a term structure (not strictly increasing): a null with its reason, never a number
    d2, i2 = blocks.impact_block(np.array([0.03, 0.04, 0.04, 0.06, 0.08]), "P1 scorecard horizon PDs, test")
    assert d2["ecl_12m_effect"] is None and d2["ecl_lifetime_effect"] is None and "strictly increasing" in d2["reason_if_null"]
    assert i2["ecl_12m_effect"]["value"] is None
    assert Path(blocks.__file__).name == "blocks.py"


def test_reliability_bins_merge_the_bins_of_one_step_of_a_calibration_map() -> None:
    """Bins whose mean PDs differ only by rounding hold one step of the map and are merged, so the PDs strictly increase."""
    from pipeline.cases.c02 import battery

    bins = [{"n": 100, "mean_pd": 0.04, "default_rate": 0.03}, {"n": 100, "mean_pd": 0.04 + 3e-17, "default_rate": 0.05},
            {"n": 100, "mean_pd": 0.04000000000000001, "default_rate": 0.04}, {"n": 100, "mean_pd": 0.07, "default_rate": 0.09}]
    out = battery.reliability_bins({"extras": {"bins": bins}})
    assert [b["n"] for b in out] == [300, 100] and out[0]["dr"] == pytest.approx(0.04) and out[0]["pd"] < out[1]["pd"]
    assert all(b["lo"] <= b["dr"] <= b["hi"] for b in out)
