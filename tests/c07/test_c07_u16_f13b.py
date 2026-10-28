"""U16-F13b (fix round 6, the R5 capture review of C07, batch c10 n2; C06, batch c08 n6), on the producers' texts: the house-price
fall says that B-1 moves through the factor shift only, never that it does not move (the variant shows B-1 rising), and the C06
notice names Freddie Mac's missing account with the word its variant reason uses. The committed documents are re-baked by the
integrator."""
from __future__ import annotations

from pipeline.cases.c06 import build as c06_build
from pipeline.cases.c07 import scenarios


def _scenario(sid: str) -> dict:
    return next(s for s in scenarios.SCENARIOS if s["id"] == sid)


def test_c10_n2_house_price_fall_says_b1_moves_only_through_the_factor_shift() -> None:
    d = _scenario("house-price-fall")["description"]
    assert "do not move" not in d["en"], d["en"]
    assert "no se mueven" not in d["es"], d["es"]
    assert ("the B-1 matrices place a loan by its appraisal at origination, so the fall moves no account across a loan-to-value "
            "band; B-1 moves only through the systematic factor, which shifts by -0.4") in d["en"]
    assert ("las matrices de B-1 ubican cada préstamo por su tasación de origen, así que la caída no mueve ninguna cuenta de "
            "tramo de relación préstamo-garantía; B-1 se mueve solo por el factor sistemático, que se desplaza -0,4") in d["es"]
    # the scenario's numbers are unchanged
    s = _scenario("house-price-fall")
    assert (s["z_shift"], s["hpi"]) == (-0.4, -0.15)


def test_c08_n6_the_c06_notice_says_titular_as_the_variant_reason_does() -> None:
    es = c06_build.NOTICE["es"]
    assert "falta la cuenta del titular" in es
    assert "propietario" not in es
    from pipeline.cases.c06 import variant
    assert "falta la cuenta del titular" in variant.FREDDIE_REASON_ES
