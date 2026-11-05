"""U16-F10b (fix round 4, the R3 capture review of C04, batch c05 minors), on the producer's functions: the F-HOMOG title groups its
statistic and degrees of freedom as the tests table does (m7), and the family source names no engine module (m10). The committed
documents are re-baked by the integrator."""
from __future__ import annotations

from pipeline.cases import c04_families, c04_transitions


def test_m7_the_homogeneity_title_groups_its_numbers_in_both_languages() -> None:
    t = c04_transitions.homog_title("S&P", {"statistic": 12028.4, "dof": 1075, "p_value": 0.0})
    assert "(chi-square 12,028 on 1,075 degrees of freedom, p < 1e-300)" in t["en"]
    assert "(chi-cuadrado 12.028 con 1.075 grados de libertad, p < 1e-300)" in t["es"]
    assert t["en"].startswith("S&P: the one-year matrix is not the same every year")


def test_m10_the_family_source_names_no_engine_module() -> None:
    assert "riskvalidation.transitions" not in c04_families.SOURCE
    assert c04_families.SOURCE.startswith("EM generator of riskvalidation")
