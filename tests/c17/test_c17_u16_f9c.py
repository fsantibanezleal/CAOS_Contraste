"""U16-F9c (fix round 3, R2b c18 m-4): the C17 finding titles name the currency of the collection threshold, and the Spanish titles
write a percent with the no-break space before the sign (ADR-0017, the shell's es-CL form)."""
from __future__ import annotations

from types import SimpleNamespace

from pipeline.cases.c17.documents import _findings

NBSP = " "


def _cells() -> dict:
    splice = {"iqr_over_truth": 2.744, "ratio_to_truth": {"median": 0.909}}
    return {
        "y5-h10000": {"lda_splice": splice},
        "y10-h20000": {"lda_splice": {"iqr_over_truth": 1.983, "ratio_to_truth": {"median": 0.909}},
                       "lda_lognormal": {"ratio_to_truth": {"median": 0.0417}},
                       "lda_lognormal_truncated": {"ratio_to_truth": {"median": 0.2618}}},
    }


def _titles() -> dict[str, dict[str, str]]:
    v = SimpleNamespace(tail_index=0.8, infinite_mean=False)
    return {f["id"]: f["title"] for f in _findings(v, _cells(), 163_483_000.0, 142_003_392.0, [])}


def test_the_threshold_names_its_currency() -> None:
    t = _titles()
    for fid in ("F-1", "F-2"):
        assert "threshold EUR 20,000" in t[fid]["en"], t[fid]["en"]
        assert "umbral de EUR 20.000" in t[fid]["es"], t[fid]["es"]
        assert "threshold 20,000" not in t[fid]["en"]


def test_a_spanish_percent_has_its_no_break_space() -> None:
    t = _titles()
    assert f"274{NBSP}%" in t["F-1"]["es"] and f"198{NBSP}%" in t["F-1"]["es"]
    assert f"86,9{NBSP}%" in t["F-3"]["es"]
    assert "274%" in t["F-1"]["en"]
