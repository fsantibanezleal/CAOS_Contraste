"""Fix round 4, unit U16-F10a, the C01 producer (the third capture review, R3, batches c01 and c02).

- c01 B1, c02 B1: the F-CODES finding title names the contract rules in words, never by their ids (C01-EDU-CODE, C01-PAY-CODE), and
  writes its counts as the shell does in each language (pipeline.core.text), with no list separator turned into a full stop.
- c01 B2, B4: the single-variable rung's title names its input as the dataset's codebook does (the German twin's checking_status,
  the Taiwan file's PAY_0), never by its column code.
- the ruling of 2026-10-27: the Spanish titles of the rungs carry no English technical word (scorecard, boosting).
Each is checked on the producer's own function, never by re-baking.
"""
from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

from pipeline.cases import c01_features as feat
from pipeline.cases import c01_ladder, c01_retail_pd

ROOT = Path(__file__).resolve().parents[1]
RULED = [line[1:].split(" ")[0] for line in (ROOT / "scripts" / "check_spanish_words.txt").read_text(encoding="utf-8").splitlines()
         if line.startswith("!")]
ENGLISH = re.compile(r"(?<![A-Za-z0-9_./-])(?:" + "|".join(re.escape(w) for w in RULED) + r")(?:s|es|ing)?(?![A-Za-z0-9_/-])", re.I)


def _codes_title() -> dict:
    fit = SimpleNamespace(contract={"by_rule": {"flagged": {"C01-EDU-CODE": 345, "C01-PAY-CODE": 25939}}}, rungs={})
    found = c01_retail_pd._findings([], "holdout", fit)
    return next(f for f in found if f["id"] == "F-CODES")


def test_the_codes_finding_names_the_rules_in_words():
    f = _codes_title()
    for lang in ("en", "es"):
        assert "C01-" not in f["title"][lang], f["title"][lang]
        assert "EDUCATION" not in f["title"][lang] and "PAY_0" not in f["title"][lang]
    assert f["evidence"] == ["contract:C01-EDU-CODE", "contract:C01-PAY-CODE"]
    assert "345 records" in f["title"]["en"] and "25,939" in f["title"]["en"]
    assert "education code outside 1 to 4" in f["title"]["en"]


def test_the_codes_finding_writes_spanish_counts_with_the_shell_form_and_keeps_its_separator():
    es = _codes_title()["title"]["es"]
    assert "25.939" in es and "345 registros" in es
    assert "; " in es, es  # the list separator is not turned into a full stop
    assert "código de educación fuera de 1 a 4" in es


def test_every_input_of_both_files_has_a_codebook_name():
    for f in (*feat.TAIWAN_FEATURES, *feat.GERMAN_FEATURES):
        name = feat.FEATURE_NAME[f]
        assert name["en"] and name["es"] and name["en"] != f, f


def test_the_single_variable_title_names_its_input():
    assert c01_ladder.single_title("PAY_0") == {"en": "Single variable (Repayment status, September 2005)",
                                                "es": "Una variable (Estado de pago, septiembre de 2005)"}
    assert c01_ladder.single_title("checking_status")["en"] == "Single variable (Status of the existing checking account)"
    # an input the codebooks of C01 do not hold (a ratio of another case) keeps its column name
    assert c01_ladder.single_title("Attr39") == {"en": "Single variable (Attr39)", "es": "Una variable (Attr39)"}


def test_the_spanish_titles_of_the_rungs_carry_no_english_technical_word():
    texts = [t["es"] for t in c01_ladder.SHORT_TITLES.values()] + [t["es"] for t in c01_ladder.TITLES.values()]
    assert [t for t in texts if ENGLISH.search(t)] == []
    assert c01_ladder.SHORT_TITLES["P1-scorecard"]["en"] == "P1 Scorecard"
