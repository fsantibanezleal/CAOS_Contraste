"""CT-1824: the labels of the capital start and the headline statements (decisions Z12 and Z14)."""
from __future__ import annotations

from c18_support import requires_raw

from pipeline.cases.c18 import params as P

pytestmark = requires_raw


def test_the_labels_of_the_capital_start_and_the_headline_are_stated(built) -> None:
    for vid in P.SCENARIOS.values():
        if vid not in built.variants:
            continue
        o = built.variants[vid]["outputs"]
        basis = o["capital_start"]["basis"]["en"]
        assert "UNVERIFIED" in basis and "T2" in basis and "Tier 1" in basis and "conservative" in basis
        assert "UNVERIFIED" in o["capital_start"]["basis"]["es"]
        reds = [t for t in built.variants[vid]["tests"] if t["test_id"] == "stress.satellite_backcast" and t["light"] == "red"]
        assert reds                                                                         # the back-cast fails for the satellites
        head = next(f for f in built.variants[vid]["findings"] if f["id"] == "headline-simple-sum")
        for text in (head["title"], o["headline_cet1"]["statement"]):
            assert "fail their own" in text["en"] and "back-cast" in text["en"]
            # the Spanish names the back-cast in Spanish (U16-R3 c19 B3, ruling of 2026-10-27: no English technical word in Spanish)
            assert "falla" in text["es"].lower() and "retroproyecci" in text["es"].lower() and "back-cast" not in text["es"].lower()
