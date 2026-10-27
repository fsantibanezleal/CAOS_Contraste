"""U16-F12d (fix round 5, R4 c18): the C15 floors finding cites the floor distances it reads, not the CMF golden-value test (n2);
the English calibration source writes "Cuadro N° 1" as the publication does (m3); and the floor-exposed variant is not called
"Floors active" when no floor binds in it (m13)."""
from __future__ import annotations

from pipeline.cases.c07 import sources as c07_src
from pipeline.cases.c15 import bake, book, targets, variant


def _findings(effects: list[dict]) -> list[dict]:
    th = {"prioritised": False, "tests": [{"id": "eve-tier1", "ratio": 0.11}, {"id": "nii-tier1", "ratio": 0.013}]}
    o = {"indexation_charge": {"charge": 6.0}, "nii": {"delta_nii": 11.0}}
    return variant._findings(o, th, 20.48, ("UR, EVE, parallel down", "UR, EVE, paralelo a la baja"), effects)


def test_n2_the_floors_finding_cites_the_floor_distances() -> None:
    for effects in ([], [{"leg": "ur", "measure": "eve", "shock": "parallel-down"}]):
        f3 = next(f for f in _findings(effects) if f["id"] == "F3")
        assert f3["evidence"] == ["design:floors.distances"], effects
        assert "irrbb.cmf_annex1_goldens" not in f3["evidence"]


def test_m3_the_english_calibration_source_writes_cuadro_n_degree_1() -> None:
    text = bake.calibration_source_text(c07_src.PUBLICATIONS[targets.PUBLICATION])
    assert "Cuadro N° 1 column Bancos" in text
    assert "Cuadro N 1" not in text


def test_m13_the_floor_exposed_variant_does_not_say_its_floors_are_active() -> None:
    s = book.SPECS["floors-active"]
    assert s.label["en"] == "Floor-exposed UF book" and s.label["es"] == "Libro en UF expuesto al piso"
    assert "Floors active" not in s.label["en"] and "Pisos activos" not in s.label["es"]
    assert s.description["en"].endswith("no floor binds on the curves of the valuation date.")
    assert s.description["es"].endswith("ningún piso actúa sobre las curvas de la fecha de valoración.")
