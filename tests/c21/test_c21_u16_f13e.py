"""U16-F13e (fix round 6, the fifth capture review R5, batch c27 n2): the F-UNCONDITIONAL-GAP title counts the attributes by the test
that decides each count: the parity indicators above their tolerance in K of the attributes, and the red rows of the pairwise tests in
the M attributes they cover (2021-22 read "gaps in 2 of the 5 attributes, 20 red rows" while those rows covered 3). The producer's
function is run on the test rows of each committed pair document."""
from __future__ import annotations

from c21_support import VARIANTS, committed

from pipeline.cases.c21 import findings

UNCONDITIONAL = ("fair.two_proportion_z", "fair.fisher_exact")


def test_n2_the_gap_title_counts_each_attribute_by_its_own_test() -> None:
    for v in VARIANTS:
        tests = committed(v)["tests"]
        n = sum(1 for r in tests if r["test_id"] == "fair.demographic_parity")
        k = sum(1 for r in tests if r["test_id"] == "fair.demographic_parity" and r["light"] != "green")
        red = [r for r in tests if r["test_id"] in UNCONDITIONAL and r["light"] == "red"]
        m = len({r["segment"].split("|")[0] for r in red})
        title = {f["id"]: f for f in findings.build(tests)}["F-UNCONDITIONAL-GAP"]["title"]
        assert f"parity indicators above their tolerance in {k} of the {n} attributes" in title["en"], (v, title["en"])
        assert f"indicadores de paridad sobre su tolerancia en {k} de los {n} atributos" in title["es"], (v, title["es"])
        if red:
            word_en = "attribute" if m == 1 else "attributes"
            word_es = "atributo" if m == 1 else "atributos"
            assert f"{len(red)} red rows of the two-proportion z-test and the Fisher exact test in {m} {word_en}" in title["en"], (v, title["en"])
            assert f"{len(red)} filas rojas de la prueba z de dos proporciones y de la prueba exacta de Fisher en {m} {word_es}" in title["es"], (v, title["es"])
