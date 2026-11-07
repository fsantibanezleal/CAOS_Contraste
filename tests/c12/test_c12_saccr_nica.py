"""CRE52.10, CRE52.17 and CRE52.23: the net collateral C of a margined netting set includes the NICA, so the multiplier and the
EAD of the initial-margin variant are computed from V - (VM + NICA)."""
from __future__ import annotations

import math

import c12_docs as d
import pytest

FLOOR = 0.05


def _multiplier(v_minus_c: float, addon: float) -> float:
    """CRE52.23, written out here and not taken from the engine: min(1, floor + (1 - floor) exp((V - C) / (2 (1 - floor) AddOn)))."""
    if v_minus_c >= 0.0 or addon == 0.0:
        return 1.0
    return min(1.0, FLOOR + (1 - FLOOR) * math.exp(v_minus_c / (2 * (1 - FLOOR) * addon)))


def _sa(variant: str) -> dict:
    return d.variant(variant)["outputs"]["sa_ccr"]


def test_the_net_collateral_c_of_the_initial_margin_variant_is_the_variation_margin_plus_the_nica() -> None:
    sa = _sa("with-im")
    nica = sa["nica"]["amount"]
    assert nica > 0.0
    vm = sa["v"]["amount"]          # the threshold is 0: the variation margin held at the valuation date equals V
    assert sa["th"]["amount"] == 0.0
    assert sa["c"]["amount"] == pytest.approx(vm + nica, rel=1e-12)


def test_the_multiplier_and_the_ead_of_every_variant_follow_cre52_23_with_c_including_the_nica() -> None:
    for name in d.VARIANTS:
        sa = _sa(name)
        v, c, nica = sa["v"]["amount"], sa["c"]["amount"], sa["nica"]["amount"]
        addon = sa["addon_aggregate"]["amount"]
        if sa["margined"]:
            vm = v if sa["th"]["amount"] == 0.0 else c - nica
            assert c == pytest.approx(vm + nica, rel=1e-12), name
        mult = _multiplier(v - c, addon)
        assert sa["multiplier"] == pytest.approx(mult, rel=1e-12), name
        rc = max(v - c, sa["th"]["amount"] + sa["mta"]["amount"] - nica, 0.0) if sa["margined"] else max(v - c, 0.0)
        assert sa["rc"]["amount"] == pytest.approx(rc, abs=1e-9), name
        assert sa["ead"]["amount"] == pytest.approx(sa["alpha"] * (rc + mult * addon), rel=1e-12), name


def test_the_initial_margin_variant_multiplier_is_below_one_because_the_nica_lowers_the_pfe() -> None:
    sa = _sa("with-im")
    assert sa["multiplier"] < 1.0
    assert sa["multiplier"] == pytest.approx(_multiplier(sa["v"]["amount"] - sa["c"]["amount"], sa["addon_aggregate"]["amount"]), rel=1e-12)
