"""U16-F13d (fix round 6, R5 c19): the two C14 tests that read the wholesale fit name that segment, as C15 does (M1, R5 ruling 2:
a row with no segment names its scope; these two have one); the retail-share threshold is a number in each language's form, never
"250 000 USD", which split at its space at 390 (n2); and the Spanish quarter of a variant title is "2022-T4", not the English
"2022-Q4" (n3)."""
from __future__ import annotations

from c14_sample import report

from pipeline.cases.c14 import assumptions, slotting, variant


def test_m1_the_wholesale_fit_tests_name_their_segment() -> None:
    rows = [{"test_id": i, "segment": None} for i in ("irrbb.srp31_92_goldens", "irrbb.eve_sum_of_parts", "irrbb.eve_with_without_behavioural",
                                                       "irrbb.nmd_parameter_stability", "irrbb.behavioural_change_at_breach",
                                                       "irrbb.nii_out_of_sample")]
    out = variant.test_segments(rows)
    assert [r["segment"] for r in out] == [None, None, None, "wholesale", "wholesale", None]


def test_n2_the_retail_threshold_is_grouped_in_each_language() -> None:
    texts = [x for i in slotting.build_items(report(), assumptions.REQUESTS) for x in (i.slotting_assumption, i.reason_missing) if x]
    split = [x for x in texts if "customer-type split" in x["en"]]
    assert split, "the deposit items carry the split text"
    for x in split:
        assert "250 000" not in x["en"] and "250 000" not in x["es"]
        assert "250,000 USD" in x["en"]
        assert "250.000 USD" in x["es"]
    assert "250 000" not in assumptions.REGISTRY["retail_share"].source
    assert "250,000 USD" in assumptions.REGISTRY["retail_share"].source


def test_n3_the_spanish_quarter_is_trimestre() -> None:
    assert variant.quarter_of("2022-12-31") == "2022-Q4"
    assert variant.quarter_text("2022-12-31") == {"en": "2022-Q4", "es": "2022-T4"}
    assert variant.quarter_text("2021-06-30") == {"en": "2021-Q2", "es": "2021-T2"}
    title = variant.variant_title("2022-12-31")
    assert title == {"en": "Valuation date 2022-12-31 (2022-Q4)", "es": "Fecha de valoración 2022-12-31 (2022-T4)"}
