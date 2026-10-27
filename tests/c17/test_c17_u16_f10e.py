"""U16-F10e (fix round 4, R3 c18 minors m6, m8, m9): the C17 finding titles write a ratio near zero with two significant digits
instead of "0.00 times the truth", the S2 title names the threshold of the cell its percent belongs to, and the generator notice
glosses the English acronym LDCE once in Spanish. Numbers through ``pipeline.core.text`` (the shell's forms)."""
from __future__ import annotations

from types import SimpleNamespace

from pipeline.cases.c17 import documents as D
from pipeline.cases.c17.documents import _findings

NBSP = " "


def _cells(lognormal: float = 0.00438) -> dict:
    return {
        "y5-h10000": {"lda_splice": {"iqr_over_truth": 3.30, "ratio_to_truth": {"median": 0.7}}},
        "y10-h20000": {"lda_splice": {"iqr_over_truth": 2.32, "ratio_to_truth": {"median": 0.725}},
                       "lda_lognormal": {"ratio_to_truth": {"median": lognormal}},
                       "lda_lognormal_truncated": {"ratio_to_truth": {"median": 0.0912}}},
    }


def _titles(lognormal: float = 0.00438) -> dict[str, dict[str, str]]:
    v = SimpleNamespace(tail_index=1.1, infinite_mean=True)
    return {f["id"]: f["title"] for f in _findings(v, _cells(lognormal), 2_148_602_460.0, 165_000_000.0, [])}


def test_m6_a_ratio_near_zero_keeps_two_significant_digits() -> None:
    t = _titles()["F-2"]
    assert "0.00 times" not in t["en"] and "0,00 veces" not in t["es"]
    assert "0.0044 times the truth" in t["en"], t["en"]
    assert "0,0044 veces la verdad" in t["es"], t["es"]
    # a ratio of ordinary size keeps its two decimals, as before
    t2 = _titles(0.0417)["F-2"]
    assert "0.042 times" in t2["en"] and "0,042 veces" in t2["es"]
    assert "0.091" in t2["en"] and "0,091" in t2["es"]


def test_m9_the_s2_title_names_the_threshold_of_its_cell() -> None:
    t = _titles()["F-1"]
    assert "with 5 years of data and threshold EUR 10,000" in t["en"], t["en"]
    assert "5 años de datos y umbral de EUR 10.000" in t["es"], t["es"]
    assert f"330{NBSP}%" in t["es"] and "330%" in t["en"]


def test_m8_the_generator_notice_glosses_the_acronym_in_spanish() -> None:
    assert "LDCE, por su sigla en inglés" in D.GENERATOR_NOTICE["es"]
    assert D.GENERATOR_NOTICE["en"].startswith("Synthetic data: a bank invented for the case")
