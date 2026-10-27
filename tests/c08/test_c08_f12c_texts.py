"""U16-F12c (R4 batch c10 n3, C08): the downturn-coverage finding states the shortfall and the coverage test of each cohort it names,
so an open finding never reads as a test that failed when its test passed (p 0.17, green). Tested on the producer's function."""
from __future__ import annotations

from pipeline.cases.c08 import variant
from pipeline.core.text import NBSP


class _Down:
    def __init__(self, rows):
        self.rows = rows


def _cov(cohort, p, light):
    return {"test_id": "lgd_ead.downturn_coverage", "model_id": None, "segment": f"cohort-{cohort}", "p_value": p, "light": light}


def test_a_passed_coverage_test_is_named_beside_the_shortfall():
    down = _Down([{"cohort_id": "2009-10", "covered": False, "shortfall": 0.00143965865}])
    f = variant._findings({"light": "green", "metric": None}, "L1-ols", "all", down, [_cov("2009-10", 0.167148866, "green")])[0]
    assert f["title"]["en"] == ("The downturn LGD falls short of the realised loss of the cohort 2009-10 by 0.14 points, within the noise of its "
                                "coverage test (p 0.17, green)")
    assert f["title"]["es"] == ("La LGD de recesión queda bajo la pérdida realizada de la cohorte 2009-10 por 0,14 puntos, dentro del ruido de su "
                                "prueba de cobertura (p 0,17, verde)")


def test_a_rejected_coverage_test_says_it_rejects():
    down = _Down([{"cohort_id": "2007-08", "covered": False, "shortfall": 0.0312}])
    f = variant._findings({"light": "green", "metric": None}, "L1-ols", "all", down, [_cov("2007-08", 0.004, "red")])[0]
    assert "by 3.12 points, and its coverage test rejects the coverage (p 0.004, red)" in f["title"]["en"]
    assert "por 3,12 puntos, y su prueba de cobertura rechaza la cobertura (p 0,004, rojo)" in f["title"]["es"]
    assert NBSP not in f["title"]["en"]


def test_two_uncovered_cohorts_keep_the_plural_with_each_test():
    down = _Down([{"cohort_id": "2007-08", "covered": False, "shortfall": 0.01}, {"cohort_id": "2009-10", "covered": False, "shortfall": 0.002}])
    tests = [_cov("2007-08", 0.03, "amber"), _cov("2009-10", 0.2, "green")]
    f = variant._findings({"light": "green", "metric": None}, "L1-ols", "all", down, tests)[0]
    assert f["title"]["en"].startswith("The downturn LGD falls short of the realised loss of the cohorts 2007-08 and 2009-10")
    assert "2007-08 by 1.00 points (p 0.03, amber)" in f["title"]["en"]
    assert "2009-10 by 0.20 points (p 0.2, green)" in f["title"]["en"]
    assert "de las cohortes 2007-08 y 2009-10" in f["title"]["es"]
