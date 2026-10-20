"""CT-1813 and CT-1814: the capital plan, the 4 percent cap, the Annex 3 rows and the P2G proxy."""
from __future__ import annotations

import pytest
from c18_support import requires_raw, semantics
from riskvalidation.stress import capital as rv_cap

from pipeline.cases.c18 import params as P

pytestmark = requires_raw


def test_loss_only_headline_ppnr_row_oi_and_the_cap_on_p2r(built) -> None:
    for vid in P.SCENARIOS.values():
        if vid not in built.variants:
            continue
        o = built.variants[vid]["outputs"]
        cs = o["capital_start"]
        h = o["headline_cet1"]
        assert h["method"] == "loss-only-depletion" and h["ppnr"]["label"] == "ppnr-labelled-row"
        cum = 0.0
        for row, loss in zip(h["rows"], o["losses"]["scenario_losses"], strict=True):
            cum += loss["total"]
            assert row["cet1_clp_m"] == pytest.approx(cs["cet1_clp_m"] - cum)               # no revenue is invented
        pp = h["ppnr"]
        assert pp["fee_ratio"]["value"] == 0.25 and pp["cost_ratio"]["value"] == 0.55 and pp["fee_ratio"]["label"] == "case assumption"
        for r in pp["rows"]:
            assert r["ppnr_clp_m"] == pytest.approx(r["nii_clp_m"] + r["fee_income_clp_m"] - r["operating_cost_clp_m"])
        oi = o["internal_capital_target"]
        assert oi["oi"] == pytest.approx(oi["min_pe"] + oi["c_dsib"] + oi["c_p2"]["value"] + oi["c_ccob"] + oi["c_ccyb"] + oi["c_d"]["value"])
        rows = {r["row_id"]: r for r in o["annex3"]["rows"]}
        assert rows["7.2"]["a"]["value"] == pytest.approx(0.00125) and rows["7.2"]["a"]["value"] != oi["c_p2"]["value"]        # p2r, never c_p2
    # the 4 percent cap binds the requirement p2r and not the bank's own estimate c_p2 (engine rule, decision W3)
    t = rv_cap.internal_capital_target(0.015, 0.05, 0.025, 0.005, 0.01, 0.00125)
    assert t.c_p2 == 0.05 and t.oi == pytest.approx(0.08 + 0.015 + 0.05 + 0.025 + 0.005 + 0.01)       # a c_p2 above 4 percent is allowed
    with pytest.raises(ValueError):
        rv_cap.internal_capital_target(0.015, 0.05, 0.025, 0.005, 0.01, 0.05)                           # a p2r above the cap is refused


def test_annex3_rows_and_the_p2g_proxy_label(built) -> None:
    sem = semantics()
    o = built.variants[P.SCENARIOS["fed"]]["outputs"]
    rows = o["annex3"]["rows"]
    assert len(rows) == 34 and [(r["row_id"], r["label_cmf"]) for r in rows] == sem.ANNEX3_ROWS
    by = {r["row_id"]: r for r in rows}
    assert by["10.2"]["a"]["status"] == "not-applicable" and by["12"]["a"]["value"] == pytest.approx(by["1.1"]["a"]["value"] - by["5"]["a"]["value"])
    assert by["7"]["a"]["value"] == pytest.approx(0.08 + by["7.1"]["a"]["value"] + by["7.2"]["a"]["value"])
    p = o["p2g_proxy"]
    assert p["label"] == "contraste-approximation" and p["cmf_calibration_public"] is False
    assert p["value"] == pytest.approx(max(0.0, p["peak_depletion"] - p["usable_buffers_and_mitigation"]))
    assert o["capital_plan"]["mitigation"]["applies"] is False
