"""CT-1505, CT-1506: the Banco Andino book, its calibration to the CMF aggregates, its assumptions and the NMD caps."""
from __future__ import annotations

import math

import numpy as np
import pytest
import semantics
from c15_support import SEED, VARIANT_IDS

from pipeline.cases.c07 import book as c07_book
from pipeline.cases.c15 import assumptions as asm
from pipeline.cases.c15 import book, targets

UF = 40877.73


def books(seed: int = SEED):
    return {vid: book.build_book(seed, book.SPECS[vid], UF) for vid in VARIANT_IDS}


def test_the_book_reconciles_and_reproduces_the_cmf_aggregates() -> None:
    assert tuple(book.SPECS) == VARIANT_IDS
    for vid, b in books().items():
        total_net = 0.0
        for name, leg in b.legs.items():
            conv = UF if name == "UR" else 1.0
            assets = sum(i.amount for i in leg.items if i.side == "asset")
            liabs = sum(i.amount for i in leg.items if i.side == "liability")
            assert leg.assets_total == pytest.approx(assets, rel=1e-12) and leg.liabilities_total == pytest.approx(liabs, rel=1e-12)
            for i in leg.items:
                sign = 1.0 if i.side == "asset" else -1.0
                assert i.flows.shape == (19,) and float(i.flows.sum()) == pytest.approx(sign * i.amount, rel=1e-9, abs=1e-6), (vid, i.item_id)
                assert i.amount > 0 and i.source and i.label["en"] and i.label["es"]
            total_net += (assets - liabs) * conv
        # the book is balanced up to the equity it funds: assets less liabilities (CLP million) is the Tier 1 of the document
        assert total_net == pytest.approx(b.tier1, rel=1e-9)
        assert b.net_uf_position == pytest.approx((b.legs["UR"].assets_total - b.legs["UR"].liabilities_total), rel=1e-12)
        loans = sum(i.amount * (UF if n == "UR" else 1.0) for n, leg in b.legs.items() for i in leg.items if i.category.startswith("loans"))
        assert 0.0 < loans
        # the three loan portfolios reproduce the C07 total (the calibration of U5-P2 is read, not changed)
        retail_commercial = sum(i.amount * (UF if n == "UR" else 1.0) for n, leg in b.legs.items() for i in leg.items
                                if i.item_id.startswith(("CLP-COM", "UR-COM", "CLP-CON", "CLP-MTG", "UR-MTG")))
        assert retail_commercial == pytest.approx(c07_book.PARAMS["total_exposure_clp"] / 1e6, rel=1e-9)
        rows = b.calibration_rows()
        assert {r["metric"] for r in rows} >= {"loan mix: commercial", "loan mix: consumer", "loan mix: mortgage", "securities over total assets",
                                                "deposits over total assets", "equity over total assets"}
        for r in rows:
            assert math.isclose(r["achieved"], r["target"], rel_tol=targets.TOLERANCE), (vid, r["metric"])
            assert r["source"] and r["as_of"] == "2026-08-31" and r["unit"]
        # the two legs carry both currencies: CLP and CLF (UR)
        assert b.legs["CLP"].currency == "CLP" and b.legs["UR"].currency == "CLF"


def test_the_variants_differ_in_the_net_uf_position_as_their_parameters_say() -> None:
    bs = books()
    share = {v: bs[v].net_uf_position * UF / bs[v].tier1 for v in VARIANT_IDS}
    assert share["long-uf"] > 0.2 and share["short-uf"] < -0.2 and share["cpi-surprise"] == pytest.approx(share["long-uf"])
    assert share["long-uf"] == pytest.approx(book.SPECS["long-uf"].params["net_uf_share_tier1"], rel=1e-9)
    assert share["short-uf"] == pytest.approx(book.SPECS["short-uf"].params["net_uf_share_tier1"], rel=1e-9)
    assert book.SPECS["cpi-surprise"].cpi_surprise_pp == 2.5 and all(book.SPECS[v].cpi_surprise_pp is None for v in VARIANT_IDS if v != "cpi-surprise")
    assert book.SPECS["offset-on-off"].offset_state == "compared" and all(book.SPECS[v].offset_state == "on" for v in VARIANT_IDS if v != "offset-on-off")


def test_every_behavioural_assumption_is_named_with_its_source_and_stated_synthetic() -> None:
    assert asm.check_registry(asm.REGISTRY) == []
    for name in ("nmd_core_share", "nmd_core_maturity_years", "prepayment_cpr", "term_deposit_redemption_rate", "deposit_beta",
                 "item_profiles", "currency_split", "deposit_split", "tier1_proxy", "reprice_months"):
        assert name in asm.REGISTRY, name
    for name, a in asm.REGISTRY.items():
        assert a.unit and a.source and a.source_kind in asm.SOURCE_KINDS
        if a.source_kind == "synthetic-stated":
            assert "synthetic" in a.source.lower(), name
    b = books()["long-uf"]
    doc = b.assumptions_doc()
    assert set(doc) == {"nmd_core_share", "nmd_core_maturity_years", "prepayment_cpr", "term_deposit_redemption_rate", "deposit_beta"}
    for a in doc.values():
        assert set(a) == {"value", "unit", "source_kind", "source"} and a["source_kind"] in asm.SOURCE_KINDS
    # an assumption that loses its stamp or its source is a finding
    bad = dict(asm.REGISTRY)
    bad["deposit_beta"] = asm.Assumption(0.4, "pass-through", "synthetic-stated", "stated by someone")
    assert any("deposit_beta" in f for f in asm.check_registry(bad))
    bad["prepayment_cpr"] = asm.Assumption(0.06, "", "synthetic-stated", "synthetic")
    assert any("prepayment_cpr" in f for f in asm.check_registry(bad))
    # every item that is not a CMF aggregate says what it is: a synthetic profile or a plug
    for leg in b.legs.values():
        for i in leg.items:
            assert "synthetic" in i.source.lower() or "CMF" in i.source, i.item_id


def test_nmd_requests_above_the_cap_are_cut_flagged_and_slotted_at_the_used_values() -> None:
    caps = {"retail-operational": (0.9, 5.0), "retail-non-operational": (0.7, 4.5), "wholesale": (0.5, 4.0)}
    for vid, b in books().items():
        segs = b.segments_doc()
        assert [s["category"] for s in segs] == ["retail-operational", "retail-non-operational", "wholesale"]
        for s in segs:
            cs_, cm = caps[s["category"]]
            assert (s["core_share_cap"], s["core_maturity_cap_years"]) == (cs_, cm)
            assert s["core_share_used"] == min(s["requested_core_share"], cs_) and s["core_maturity_used_years"] == min(s["requested_core_maturity_years"], cm)
            assert s["cap_applied"] == (s["requested_core_share"] > cs_ or s["requested_core_maturity_years"] > cm)
            assert s["source_kind"] == "synthetic-stated" and "synthetic" in s["source"].lower()
        assert [s["cap_applied"] for s in segs] == [True, False, True]       # the requests stand above two caps on purpose
        out = {"nmd_segments": segs, "assumptions": b.assumptions_doc()}
        items = [i for name in b.legs for i in b.items_doc(name)]
        rep = semantics.Report()
        semantics.check_nmd_segments(out, items, rep, "c15")
        assert list(rep) == [], vid
        used = sum(s["balance"] * s["core_share_used"] for s in segs) / sum(s["balance"] for s in segs)
        assert out["assumptions"]["nmd_core_share"]["value"] == pytest.approx(used, abs=1e-12)
        nmd = [i for i in items if i["behavioural_class"].startswith("nmd-")]
        assert len(nmd) == 3 and all(i["category"] == "deposits-nmd" and i["side"] == "liability" for i in nmd)
        assert sum(i["amount"] for i in nmd) == pytest.approx(sum(s["balance"] for s in segs))


def test_the_seed_changes_the_profiles_and_never_the_totals() -> None:
    a, c = books(SEED), books(SEED + 1)
    for vid in VARIANT_IDS:
        assert a[vid].tier1 == c[vid].tier1 and a[vid].net_uf_position == pytest.approx(c[vid].net_uf_position, rel=1e-12)
        fa = np.concatenate([i.flows for leg in a[vid].legs.values() for i in leg.items])
        fc = np.concatenate([i.flows for leg in c[vid].legs.values() for i in leg.items])
        assert not np.array_equal(fa, fc)
        assert a[vid].digest() == books(SEED)[vid].digest() != c[vid].digest()
