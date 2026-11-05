"""Fix round 5, unit U16-F12a, the C01 producer (the fourth capture review, R4, batch c28 B8 named by U16-F12p).

- c28 B8 (ruling 6): the Spanish titles of the C01 variants carry no English word; "prior" reads "a priori" (the term the
  documentation pages write), so the Spanish Experiments and Variants views print "Cambio de la probabilidad a priori x1,5".
Checked on the producer's own table of variants, never by re-baking.
"""
from __future__ import annotations

import re

from pipeline.cases import c01_retail_pd

ENGLISH = re.compile(r"(?<![A-Za-zÀ-ÿ])(?:prior|test|shift|drift|holdout|noise)(?![A-Za-zÀ-ÿ])", re.I)


def test_the_spanish_variant_texts_carry_no_english_word() -> None:
    for v in c01_retail_pd.VARIANTS:
        for key in ("title", "short", "regime"):
            es = v[key]["es"]
            assert not ENGLISH.search(es), (v["id"], key, es)


def test_the_prior_shift_reads_a_priori() -> None:
    v = next(x for x in c01_retail_pd.VARIANTS if x["id"] == "prior-shift")
    assert v["title"]["es"] == "Cambio de la probabilidad a priori x1,5"
    assert v["short"]["es"] == "A priori x1,5"
    # the English keeps its wording
    assert v["title"]["en"] == "Prior shift x1.5"
    assert v["short"]["en"] == "Prior x1.5"
