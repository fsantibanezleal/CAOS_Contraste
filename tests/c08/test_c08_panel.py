"""CT-901 to CT-903: the cleaning, the LGD proxy and the values outside [0, 1], on the committed sample."""
from __future__ import annotations

import numpy as np
import pandas as pd
from c08_helpers import clipping_findings, proxy_findings

from pipeline.cases.c08 import build as bd
from pipeline.cases.c08 import panel
from pipeline.cases.c08.ladder import fit_ladder
from pipeline.io import sba as readers


def test_cleaning_counts_every_exclusion_under_its_reason(tables):
    counts = tables["counts"]
    reasons = {k: v for k, v in counts.items() if k not in ("charge-offs-read", "defaults-kept")}
    assert counts["charge-offs-read"] == counts["defaults-kept"] + sum(reasons.values()), "nothing is dropped silently"
    assert set(reasons) == {"no-chargeoff-date", "no-approval-date", "term-missing-or-implausible", "approval-amount-missing-or-not-positive",
                            "chargeoff-amount-missing-or-negative", "guarantee-missing-or-outside-the-approval", "chargeoff-before-approval",
                            "proxy-ratio-above-ten", "chargeoff-after-the-last-cohort"}
    assert counts["defaults-kept"] == tables["defaults"].n > 1000
    forbidden = {"BorrName", "BorrStreet", "BorrCity", "BorrZip", "LocationID", "BankName"}
    assert forbidden.isdisjoint(readers.SBA_COLUMNS), "the reader never reads a name, address or identifier"
    assert forbidden.isdisjoint(panel.Defaults.__dataclass_fields__)


def test_adversarial_a_planted_bad_row_is_counted_under_its_reason(tables):
    df = tables["frame"]
    co = df[df["status"] == "CHGOFF"].iloc[:6].copy().reset_index(drop=True)
    clean, base = panel.prepare(co)
    bad = co.copy()
    bad.loc[0, "term_months"] = 0.0                                     # an impossible term
    bad.loc[1, "chargeoff_date"] = pd.NaT                               # a charge-off with no date
    bad.loc[2, "chargeoff_date"] = bad.loc[2, "approval_date"] - pd.Timedelta(days=30)   # charged off before approved
    bad.loc[3, "chargeoff_amount"] = bad.loc[3, "gross_approval"] * 50.0               # a unit error of the approved amount
    out, counts = panel.prepare(bad)
    assert counts["term-missing-or-implausible"] - base["term-missing-or-implausible"] == 1
    assert counts["no-chargeoff-date"] - base["no-chargeoff-date"] == 1
    assert counts["chargeoff-before-approval"] - base["chargeoff-before-approval"] == 1
    assert counts["proxy-ratio-above-ten"] - base["proxy-ratio-above-ten"] == 1
    assert counts["charge-offs-read"] == counts["defaults-kept"] + sum(v for k, v in counts.items() if k not in ("charge-offs-read", "defaults-kept"))
    assert out.n == clean.n - 4


def test_the_proxy_is_the_gross_charge_off_over_the_gross_approval(tables, docs):
    d = tables["defaults"]
    assert np.array_equal(d.y, d.chargeoff_amount / d.gross_approval)
    assert np.array_equal(panel.lgd_proxy(np.array([30.0, 5.0]), np.array([100.0, 4.0])), np.array([0.3, 1.25]))
    blk = bd.lgd_proxy_block()
    assert (blk["formula"], blk["source_field"], blk["exposure_field"], blk["bias_direction"]) == (
        "GrossChargeOffAmount / GrossApproval", "GrossChargeOffAmount", "GrossApproval", "downward")
    assert blk["recovery_cash_flows_available"] is False and "denominator" in blk["bias_statement"]["en"]
    for vid, doc in docs["variants"].items():
        o = doc["outputs"]
        lo, hi = o["cohort"]["first_year"], o["cohort"]["last_year"]
        k = (d.year >= lo) & (d.year <= hi)
        assert o["lgd_proxy"] == blk, vid
        assert proxy_findings(o, d.y[k], d.chargeoff_amount[k], d.gross_approval[k]) == [], vid
        assert docs["models"][f"models-{vid}"]["fit"]["lgd_proxy"] == blk


def test_adversarial_a_proxy_with_another_denominator_is_found(tables, docs):
    d = tables["defaults"]
    o = docs["variants"]["dc-2009-10"]["outputs"]
    k = (d.year >= 2009) & (d.year <= 2010)
    assert proxy_findings(o, d.y[k], d.chargeoff_amount[k], d.gross_approval[k]) == []
    guaranteed = d.gross_approval * d.guaranteed_share      # the guaranteed share of the approval, not the approval
    assert proxy_findings(o, d.y[k], d.chargeoff_amount[k], guaranteed[k]) == ["approval total (another denominator)"]
    # a document built on the guaranteed amount is no better: its denominator no longer matches the cohort's approvals
    other = {**o, "exposure": {**o["exposure"], "gross_approval_total": float(guaranteed[k].sum())}}
    assert proxy_findings(other, d.y[k], d.chargeoff_amount[k], d.gross_approval[k]) == ["approval total (another denominator)"]
    assert proxy_findings({**o, "lgd_proxy": {**o["lgd_proxy"], "exposure_field": "SBAGuaranteedApproval"}}, d.y[k],
                          d.chargeoff_amount[k], d.gross_approval[k]) == ["proxy statement"]


def test_an_lgd_outside_zero_one_is_flagged_and_never_clipped(tables, docs):
    d = tables["defaults"]
    assert (d.y > 1).any(), "the sample carries charge-offs above the approval"
    for vid, doc in docs["variants"].items():
        o = doc["outputs"]
        k = (d.year >= o["cohort"]["first_year"]) & (d.year <= o["cohort"]["last_year"])
        dist = o["lgd_distribution"]
        assert clipping_findings(dist, d.y[k]) == [], vid
        assert dist["treatment"] == "flagged-not-clipped"
        assert dist["n"] == int(k.sum()) == sum(b["n"] for b in dist["bins"]) + dist["n_below_zero"] + dist["n_above_one"]
        if dist["n_above_one"]:
            assert dist["highest"]["flag"] == "above-one" and dist["highest"]["value"] > 1.0
    # a training default above one is left out by a counted exclusion, and never clipped into the fit
    rng = np.random.default_rng(3)
    x = rng.normal(size=(400, 17))
    y = np.clip(rng.beta(2, 1, 400), 0.0, 1.0)
    y2 = y.copy()
    y2[0], y2[1] = 1.4, -0.1
    lad = fit_ladder(x, y2, "2008-12-31", 1)
    assert lad.n_out_of_range == 2 and lad.n_fitted == 398


def test_adversarial_a_clipped_lgd_is_found(tables):
    d = tables["defaults"]
    k = (d.year >= 2009) & (d.year <= 2010)
    y = d.y[k]
    assert (y > 1).any()
    from riskvalidation.lgd_ead.workout import lgd_distribution

    def block(values):
        dist = lgd_distribution(values, np.linspace(0.0, 1.0, 11))
        return {"n_above_one": dist.n_above_one, "n_below_zero": dist.n_below_zero, "highest": {"value": float(values.max())}}

    assert clipping_findings(block(y), y) == []
    assert clipping_findings(block(np.minimum(y, 1.0)), y) == ["count above one", "highest value"]
