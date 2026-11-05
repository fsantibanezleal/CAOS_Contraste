"""U16-F12b (fix round 5, the R4 capture review of C04, batch c05 minors n3 and n4), on the producer's function over the committed
outputs: the Markov finding names CEREP's model as the page translates it ("modelo de concepto de saldo", never "modelo de stock"),
and the momentum title prints its rates with the one decimal its evidence lines carry (8.5 %, not "8%"). The committed documents are
re-baked by the integrator."""
from __future__ import annotations

import json
from pathlib import Path

from pipeline.cases import c04_transitions

DERIVED = Path(__file__).resolve().parents[1] / "data" / "derived" / "C04"


def _titles(fid: str) -> dict[str, dict[str, str]]:
    out = json.loads((DERIVED / f"{fid}.json").read_text(encoding="utf-8"))["outputs"]
    return {f["id"]: f["title"] for f in c04_transitions.family_findings({"id": fid}, out)}


def test_n3_the_spanish_names_cereps_model_as_the_page_does() -> None:
    es = _titles("markov")["F-EM-RARE"]["es"]
    assert "modelo de stock" not in es
    assert "el modelo de concepto de saldo de CEREP" in es
    assert "CEREP's stock model" in _titles("markov")["F-EM-RARE"]["en"]


def test_n4_the_momentum_title_keeps_one_decimal_as_its_evidence_does() -> None:
    out = json.loads((DERIVED / "momentum.json").read_text(encoding="utf-8"))["outputs"]
    rate = next(s for s in out["simulations"] if s["key"] == "rating.time_homogeneity@alpha0.125")["rates"]["p<0.05"]["rate"]
    t = _titles("momentum")["F-MOMENTUM-TESTS"]
    assert f"by time homogeneity in {100 * rate:.1f}%" in t["en"], t["en"]
    assert f"la homogeneidad temporal en {100 * rate:.1f}".replace(".", ",") + " %" in t["es"], t["es"]
