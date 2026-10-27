"""U16-F12e (fix round 5, R4 c25): every red row of the unconditional two-proportion z-test and Fisher exact test of a C21 pair is cited
by F-UNCONDITIONAL-GAP, at its S4 "indicator only" (ruling 4 of the R4 triage: a red test row is cited by an open finding; the Interagency
procedures make the gross gap an indicator), and the counterfactual reason ends as a sentence (n4). The producer's function is run on the
test rows of each committed pair document."""
from __future__ import annotations

from c21_support import VARIANTS, committed

from pipeline.cases.c21 import estimates, findings

RATES = "hmda-selection-rates"
UNCONDITIONAL = ("fair.two_proportion_z", "fair.fisher_exact")


def test_m1_every_red_unconditional_row_is_cited_by_the_gap_finding() -> None:
    seen = 0
    for v in VARIANTS:
        tests = committed(v)["tests"]
        red = {f"{r['test_id']}@{r['model_id']}@{r['segment']}" for r in tests if r["test_id"] in UNCONDITIONAL and r["light"] == "red"}
        out = {f["id"]: f for f in findings.build(tests)}
        gap = out["F-UNCONDITIONAL-GAP"]
        assert (gap["severity"], gap["status"]) == ("S4", "open"), v
        assert red <= set(gap["evidence"]), (v, sorted(red - set(gap["evidence"]))[:3])
        assert len(gap["evidence"]) == len(set(gap["evidence"])), v
        assert all(e.split("@")[1] == RATES for e in gap["evidence"] if e.split("@")[0] in UNCONDITIONAL), v
        # the title counts the rows it cites, in both languages
        assert f"{len(red)} red rows of the two-proportion z-test and the Fisher exact test" in gap["title"]["en"], gap["title"]["en"]
        assert f"{len(red)} filas rojas de la prueba z de dos proporciones y de la prueba exacta de Fisher" in gap["title"]["es"], gap["title"]["es"]
        seen += len(red)
    assert seen == 116                       # 18 + 22 + 24 + 20 + 14 + 18 red rows over the six pairs (R4 c25 M1)


def test_n4_the_counterfactual_reason_ends_with_a_full_stop() -> None:
    reason = estimates.COUNTERFACTUAL_REASON
    assert reason["en"].endswith("is not run.") and reason["es"].endswith("no se ejecuta.")
