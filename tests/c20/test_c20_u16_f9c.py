"""U16-F9c (fix round 3, R2b c20): a C20 finding title names its test in words, never the engine's id ("ml.overfit: 1 red and
0 amber rows"); the evidence keeps the ids."""
from __future__ import annotations

from pipeline.cases.c20 import ops

IDS = ["fair.auc_by_group", "fair.calibration_within_groups", "fair.equal_opportunity", "fair.equalized_odds", "ml.additivity",
       "ml.cbpe_estimate", "ml.conformal_coverage", "ml.data_quality", "ml.effect_agreement", "ml.leakage_screen", "ml.overfit",
       "ml.reason_code_stability", "ml.robustness", "ml.seed_stability", "ml.shift_resilience", "ml.weak_spot", "stability.chi2",
       "stability.csi", "stability.ks", "stability.psi"]


def _row(test_id: str, light: str) -> dict:
    return {"test_id": test_id, "light": light, "model_id": "P4-lightgbm", "segment": None}


def test_every_finding_title_names_its_test_in_words() -> None:
    out = ops.findings([_row(t, "red") for t in IDS], limits=[], prefix="sgcd-seen")
    assert len(out) == len(IDS)
    for f in out:
        for lang in ("en", "es"):
            assert not any(t in f["title"][lang] for t in IDS), f["title"]
    titles = {f["id"]: f["title"] for f in out}
    assert titles["sgcd-seen-ml.overfit"]["en"].startswith("Overfit gap: 1 red and 0 amber rows")
    assert titles["sgcd-seen-ml.overfit"]["es"].startswith("Brecha de sobreajuste: 1 fila roja y 0 ámbar")
    assert titles["sgcd-seen-stability.chi2"]["es"].startswith("Prueba chi-cuadrado de homogeneidad:")


def test_an_unknown_test_still_raises_its_finding() -> None:
    out = ops.findings([_row("ml.some_new_test", "amber")], limits=[], prefix="v")
    assert out[0]["title"]["en"].startswith("ml.some_new_test: 0 red and 1 amber rows")
