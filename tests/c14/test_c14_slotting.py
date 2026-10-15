"""CT-1404, CT-1405: the slotting reconciles to the call report, spreads the bands over the buckets they overlap, and every behavioural
assumption is a named field with its source."""
from __future__ import annotations

import numpy as np
import pytest
from c14_sample import report

from pipeline.cases.c14 import assumptions, bands, slotting


def test_a_band_spreads_over_the_buckets_it_overlaps() -> None:
    w = bands.slot_band(0.0, 3.0)
    assert w.shape == (19,) and abs(w.sum() - 1.0) < 1e-12
    assert w[:9].sum() == pytest.approx(1.0) and w[9:].sum() == 0.0          # up to 3 years is buckets 1 to 9
    assert w[8] == pytest.approx(1.0 / 3.0)                                  # 2Y to 3Y is one third of 0..3 years
    w = bands.slot_band(5.0, 15.0)                                           # buckets 12..16 (1 year each) and 17 (10Y to 15Y)
    assert w[11:16] == pytest.approx([0.1] * 5) and w[16] == pytest.approx(0.5)
    w = bands.slot_band(15.0, 30.0)
    assert w[17] == pytest.approx(1 / 3) and w[18] == pytest.approx(2 / 3)
    with pytest.raises(ValueError):
        bands.slot_band(3.0, 3.0)


def test_every_item_slots_its_reported_amount_and_the_sheet_reconciles_to_the_report() -> None:
    r = report()
    items = slotting.build_items(r, assumptions.REQUESTS)
    assets = [i for i in items if i.side == "asset"]
    liabs = [i for i in items if i.side == "liability"]
    assert sum(i.amount for i in assets) == pytest.approx(r.get("ASSET"))
    assert sum(i.amount for i in liabs) == pytest.approx(r.get("LIAB"))
    for i in items:
        sign = 1.0 if i.side == "asset" else -1.0
        for flows in (i.behavioural, i.contractual):
            assert flows.shape == (19,) and flows.sum() == pytest.approx(sign * i.amount)
        assert i.slotting_assumption and i.source_field
        if i.reported_amount is None:
            assert i.reason_missing is not None                                  # a plug says why it has no reported amount
        else:
            assert i.reported_amount == pytest.approx(i.amount) and i.reason_missing is None
    plugs = {i.item_id for i in items if i.reported_amount is None}
    # the two plugs, and the four NMD items the report cannot split by customer (reported total times a synthetic share)
    assert plugs == {"A8", "L9", "L1", "L2", "L3", "L4"}
    nmd = [i for i in liabs if i.behavioural_class.startswith("nmd")]
    assert sum(i.amount for i in nmd) == pytest.approx(r.get("DEP") - r.get("NTRTIME"))
    assert {i.category for i in items} <= set(slotting.CATEGORIES)
    td = next(i for i in liabs if i.behavioural_class == "term-deposit")
    assert td.amount == pytest.approx(r.get("NTRTIME"))
    # the contractual treatment puts every non-maturity deposit overnight
    for i in nmd:
        assert i.contractual[0] == pytest.approx(-i.amount)
    pre = next(i for i in assets if i.behavioural_class == "prepayable-loan")
    assert pre.behavioural[:9].sum() > pre.contractual[:9].sum()                   # prepayment brings repricing flows forward
    assert pre.behavioural.sum() == pytest.approx(pre.contractual.sum())


def test_every_behavioural_assumption_is_named_with_its_source_and_stated_synthetic() -> None:
    reg = assumptions.REGISTRY
    for name in ("nmd_core_share", "nmd_core_maturity_years", "prepayment_cpr", "term_deposit_redemption_rate", "deposit_beta",
                 "open_band_edges", "hw1f_a", "retail_share", "reprice_months"):
        a = reg[name]
        assert a.unit and a.source and a.source_kind in ("regulatory-cap", "fitted", "synthetic-stated"), name
    for name in ("prepayment_cpr", "term_deposit_redemption_rate", "open_band_edges", "hw1f_a", "retail_share", "reprice_months"):
        assert reg[name].source_kind == "synthetic-stated" and "synthetic" in reg[name].source.lower(), name
    assert assumptions.check_registry(reg) == []
    for cat, req in assumptions.REQUESTS.items():
        cap_share, cap_mat = assumptions.CAPS[cat]
        assert req.share > cap_share and req.maturity > cap_mat, "the requests stand above the caps so the cut is shown"
    assert np.isclose(sum(assumptions.CAPS[c][0] for c in assumptions.CAPS), 0.9 + 0.7 + 0.5)
