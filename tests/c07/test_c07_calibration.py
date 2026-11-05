"""CT-701, CT-702: the calibration targets and the synthetic bank that reaches them."""
from __future__ import annotations

import pytest
from pipeline.cases.c07 import bake, sources


def test_every_target_names_its_source() -> None:
    sources.validate_targets()
    assert len(sources.TARGETS) >= 12
    for t in sources.TARGETS:
        pub = sources.PUBLICATIONS[t["publication"]]
        assert pub["url"].startswith("https://www.cmfchile.cl/") and len(pub["sha256"]) == 64 and pub["bytes"] > 0
        assert t["as_of"] == "2026-08-31" and t["status"] == "CMF primary" and t["where"]
        assert all(pub["url"] in text for text in sources.source_text(t).values())
    # the unit conversion value has its primary source too
    assert sources.PUBLICATIONS["sii-uf-2026"]["url"] == "https://www.sii.cl/valores_y_fechas/uf/uf2026.htm"
    assert sources.UF_VALUE == 40873.77 and sources.UF_DATE == "2026-08-31"


def test_the_targets_carry_the_published_figures() -> None:
    """The figures as the CMF report of August 2026 prints them (Cuadro N 1 and section 2.2)."""
    by = {t["metric"]: t["value"] for t in sources.TARGETS}
    assert by["provision index: consumer"] == 0.0821 and by["provision index: mortgage"] == 0.0062
    assert by["provision index: commercial"] == 0.0256 and by["provision index: total"] == 0.0251
    assert by["90-day delinquency: commercial"] == 0.0217 and by["90-day delinquency: total"] == 0.0234
    mix = sum(v for k, v in by.items() if k.startswith("loan mix"))
    assert mix == pytest.approx(1.0, abs=1e-12)
    assert by["loan mix: mortgage"] == pytest.approx(104610 / 302703, abs=1e-12)


def check(models_doc: dict) -> list[str]:
    """Targets whose achieved value is outside its relative tolerance."""
    bad = []
    for t in models_doc["fit"]["calibration_targets"]:
        tol = sources.TOLERANCE_TOTAL if t["metric"].endswith("total") else sources.TOLERANCE
        rel = abs(t["achieved"] - t["target"]) / t["target"]
        if rel > tol:
            bad.append(f"{t['metric']}: {t['achieved']:.5f} against {t['target']:.5f} ({rel:.2%})")
    return bad


@pytest.mark.parametrize("scale", [0.02, 0.1])
def test_generated_aggregates_match_their_targets_within_tolerance(scale: float, built) -> None:
    doc = built["models"] if scale == 0.02 else bake.build(7, scale)["models"]
    assert check(doc) == []
    got = {t["metric"] for t in doc["fit"]["calibration_targets"]}
    assert got == {t["metric"] for t in sources.TARGETS}
