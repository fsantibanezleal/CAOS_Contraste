"""U6-S engine review amendments (review-u6-engine-2026-10-13.md, D4): the contract text states what the implementation does.

Each amended clause carries a dated "Amended 2026-10-13" note, as provisions-api.md does; no signature and no golden value changes.
"""
from __future__ import annotations

import re

from test_u6_contracts import API

TEXT = API.read_text(encoding="utf-8")


def section(title: str) -> str:
    i = TEXT.index(title)
    j = TEXT.find("\n### ", i + 5)
    return TEXT[i: j if j > 0 else len(TEXT)]


def amended(block: str) -> str:
    notes = [ln for ln in block.splitlines() if "Amended 2026-10-13" in ln]
    assert notes, "no dated amendment note"
    return " ".join(notes)


def test_every_amendment_note_is_dated_and_each_clause_has_one() -> None:
    notes = re.findall(r"^- Amended 2026-10-13 \(engine review[^)]*\)", TEXT, flags=re.M)
    assert len(notes) >= 8, len(notes)


def test_dev1_fit_direct_ead_needs_a_positive_limit_and_a_finite_ead() -> None:
    s = section("### `riskvalidation.lgd_ead.ccf.fit_direct_ead`")
    assert "`ead` (N,) finite" in s and "`limit` (N,) strictly positive" in s
    assert "ead` strictly positive" not in s and "`ead` and `limit` (strictly positive)" not in s
    assert "`n_clipped_below`" in amended(s)


def test_dev2_the_hurdle_severity_columns_are_columns_of_x() -> None:
    s = section("### `riskvalidation.lgd_ead.lgd_models.fit_hurdle`")
    assert "columns of `X`" in s and 'extras["severity_columns"]' in s and "`ValueError`" in s
    assert 'severity_columns' in amended(s)
    assert 'severity_columns' in section("### `riskvalidation.lgd_ead.lgd_models.LgdFit`")


def test_dev3_to_us_terms_is_nan_when_the_limit_does_not_exceed_the_drawn() -> None:
    s = section("### `riskvalidation.lgd_ead.ccf.to_us_terms`")
    assert "`limit <= drawn`" in s and "`drawn == 0`" in s
    amended(s)


def test_dev4_a_reference_must_precede_the_default() -> None:
    s = section("### `riskvalidation.lgd_ead.ccf.reference_indices`")
    assert "before `default_index`" in s and "`cohort_start_index == default_index`" in s
    amended(s)


def test_dev5_a_backtest_with_no_realised_ead_anywhere_is_not_evaluated() -> None:
    s = section("### `riskvalidation.validation.lgd_ead.ead_backtest_by_band`")
    assert "no realised EAD in any band" in s
    amended(s)


def test_dev6_zero_spread_has_a_stated_scale_aware_tolerance() -> None:
    conv = TEXT[TEXT.index("## Conventions"): TEXT.index("## Module `riskvalidation/lgd_ead/workout.py`")]
    assert "1e-12" in conv and "max(1, " in conv and "zero spread" in conv.lower()
    amended(conv)


def test_dev9_the_hurdle_raises_when_every_y_is_positive() -> None:
    s = section("### `riskvalidation.lgd_ead.lgd_models.fit_hurdle`")
    assert "every `y` is positive" in s


def test_f3_rows_are_serialised_by_to_dict_not_asdict() -> None:
    assert "serialised by `dataclasses.asdict`" not in TEXT
    assert "`TestResult.to_dict()`" in TEXT
    conv = TEXT[TEXT.index("## Conventions"): TEXT.index("## Module `riskvalidation/lgd_ead/workout.py`")]
    assert "Amended 2026-10-13" in conv.split("to_dict()")[1][:900]
