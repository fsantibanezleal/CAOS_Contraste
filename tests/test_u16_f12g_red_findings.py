"""U16-F12g (fix round 5, the R4 capture review, ruling 4): every red test row is cited by an open finding.

A case's own finding cites a red test where the case has one for it; otherwise the pipeline's generic step
(``pipeline.core.red_findings``, run by ``build_artifact`` before any document is validated or written) adds one open finding
per red test of a document that no open finding cites: a bilingual title that names the test, its red rows' models and their
count, the red rows' ids as its evidence (``test@model@segment``, ``test@-@segment`` for a row of no model), at the severity a
red light carries in the case. The step is tested on fixture documents and, in memory, on every committed document; the
committed documents are re-baked by the integrator.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from pipeline.core import manifest as m
from pipeline.core import red_findings as rf
from pipeline.core import lineage as lin
from pipeline.core.lineage import Lineage
from pipeline.core.schemas import validate_document

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"

KEYS = m.TEST_RESULT_KEYS


def row(test_id: str, model: str | None, segment: str | None, light: str, p: float | None = 0.001) -> dict:
    r = {k: None for k in KEYS}
    r.update(test_id=test_id, model_id=model, segment=segment, light=light, p_value=p, statistic=1.5, metric=None, h0="h0",
             alternative="", policy_version="riskvalidation-default 2026.10.1", n=100, n_events=10, inputs_hash="x",
             reference="ref", notes="", extras={})
    return r


MODELS = [
    {"id": "P1-scorecard", "short_title": {"en": "P1 Scorecard", "es": "P1 Tarjeta de puntuación"}},
    {"id": "P4-lightgbm", "short_title": {"en": "P4 LightGBM", "es": "P4 LightGBM"}},
]


def fixture_tests() -> list[dict]:
    return [
        row("pd.jeffreys", "P1-scorecard", "portfolio", "red"),             # cited by F-OWN (open)
        row("pd.jeffreys", "P4-lightgbm", "grade-3", "red"),                 # same test: the test is cited, no generic finding
        row("stability.csi", "P1-scorecard", "characteristic:age", "red"),  # uncited
        row("stability.csi", "P4-lightgbm", "characteristic:age", "red"),   # uncited
        row("stability.csi", "P4-lightgbm", "characteristic:income", "amber"),
        row("disc.auc_vs_initial", "P4-lightgbm", "portfolio", "red"),       # cited by an accepted finding only: uncited
        row("stability.chi2", None, "rating|typical vs higher", "red"),      # no model: test@-@segment
        row("disc.auc", "P1-scorecard", "portfolio", "green"),
    ]


def fixture_findings() -> list[dict]:
    return [
        {"id": "F-OWN", "severity": "S2", "status": "open", "evidence": ["pd.jeffreys@P1-scorecard"],
         "title": {"en": "P1 Scorecard: the level tests flag", "es": "P1 Tarjeta de puntuación: las pruebas de nivel alertan"}},
        {"id": "F-LIMIT", "severity": "S3", "status": "accepted", "evidence": ["disc.auc_vs_initial@P4-lightgbm"],
         "title": {"en": "A stated limit", "es": "Un límite declarado"}},
    ]


# --- the step on fixture documents -----------------------------------------------------------------------------------------


def test_one_finding_per_red_test_that_no_open_finding_cites():
    out = rf.red_findings("C01", fixture_tests(), fixture_findings(), MODELS)
    cited = {f["evidence"][0].split("@")[0] for f in out}
    assert cited == {"stability.csi", "disc.auc_vs_initial", "stability.chi2"}
    assert all(f["status"] == "open" for f in out)


def test_the_evidence_is_every_red_row_of_the_test_by_its_full_id():
    out = {f["evidence"][0].split("@")[0]: f for f in rf.red_findings("C01", fixture_tests(), fixture_findings(), MODELS)}
    assert out["stability.csi"]["evidence"] == ["stability.csi@P1-scorecard@characteristic:age",
                                                "stability.csi@P4-lightgbm@characteristic:age"]
    assert out["stability.chi2"]["evidence"] == ["stability.chi2@-@rating|typical vs higher"]
    assert out["disc.auc_vs_initial"]["evidence"] == ["disc.auc_vs_initial@P4-lightgbm@portfolio"]


def test_the_title_names_the_test_the_models_and_the_count_in_both_languages():
    out = {f["evidence"][0].split("@")[0]: f for f in rf.red_findings("C01", fixture_tests(), fixture_findings(), MODELS)}
    t = out["stability.csi"]["title"]
    assert t["en"].startswith("CSI of each input: red on 2 rows (P1 Scorecard; P4 LightGBM) that no other finding cites")
    assert t["es"].startswith("CSI de cada variable: en rojo en 2 filas (P1 Tarjeta de puntuación; P4 LightGBM) que ningún otro hallazgo cita")
    one = out["stability.chi2"]["title"]
    assert "red on 1 row that" in one["en"] and "en rojo en 1 fila que" in one["es"]
    # no test id, no model id in the reader text
    for f in out.values():
        for lang in ("en", "es"):
            assert "stability." not in f["title"][lang] and "P4-lightgbm" not in f["title"][lang]


def test_the_count_is_written_in_the_language_form():
    tests = [row("stability.csi", "P1-scorecard", f"characteristic:v{k}", "red") for k in range(1234)]
    (f,) = rf.red_findings("C01", tests, [], MODELS)
    assert "red on 1,234 rows" in f["title"]["en"]
    assert "en rojo en 1.234 filas" in f["title"]["es"]


def test_the_ids_are_numbered_and_never_clash_with_the_case_findings():
    findings = [*fixture_findings(), {"id": "F-RED-01", "severity": "S4", "status": "open", "evidence": ["pd.jeffreys"],
                                      "title": {"en": "x y z", "es": "x y z"}}]
    out = rf.red_findings("C01", fixture_tests(), findings, MODELS)
    ids = [f["id"] for f in out]
    assert len(set(ids)) == len(ids) == 3
    assert "F-RED-01" not in ids
    assert all(i.startswith("F-RED-") for i in ids)


def test_no_red_row_adds_nothing():
    tests = [row("pd.jeffreys", "P1-scorecard", "portfolio", "amber")]
    assert rf.red_findings("C01", tests, [], MODELS) == []


def test_an_unknown_test_name_is_an_error_and_an_unknown_model_is_never_printed():
    with pytest.raises(ValueError, match="no name"):
        rf.red_findings("C01", [row("pd.not_a_test", "P1-scorecard", "portfolio", "red")], [], MODELS)
    (f,) = rf.red_findings("C01", [row("pd.jeffreys", "P9-unknown", "portfolio", "red")], [], MODELS)
    assert "P9-unknown" not in f["title"]["en"] + f["title"]["es"]
    assert f["title"]["en"].startswith("Jeffreys: red on 1 row that")


# --- the severity a red light carries in the case --------------------------------------------------------------------------


def test_the_severity_is_the_one_the_case_gives_a_red_light():
    assert rf.red_severity("C01", "pd.jeffreys") == "S2"
    assert rf.red_severity("C01", "pd.hosmer_lemeshow") == "S3"
    assert rf.red_severity("C03", "pd.spiegelhalter") == "S3"
    assert rf.red_severity("C21", "fair.fisher_exact") == "S4"
    assert rf.red_severity("C11", "market.duration_test") == "S2"
    out = {f["evidence"][0].split("@")[0]: f for f in rf.red_findings("C21", [row("fair.fisher_exact", None, "a vs b", "red")], [], [])}
    assert out["fair.fisher_exact"]["severity"] == "S4"


def test_the_policy_agrees_with_the_case_severity_tables():
    """C01 and C03 state their red severity per test family; the step reads the same values."""
    from pipeline.cases import c01_retail_pd
    from pipeline.cases.c03 import variant as c03

    for _family, ids, on_red, _amber in c01_retail_pd.SEVERITY:
        for tid in ids:
            assert rf.red_severity("C01", tid) == on_red, tid
    for _family, _es, ids, on_red, _amber in c03.SEVERITY:
        for tid in ids:
            assert rf.red_severity("C03", tid) == on_red, tid


# --- the wiring: build_artifact runs the step before the document is checked and written -----------------------------------


def _lineage(case_id: str = "C99") -> Lineage:
    return lin.build(case_id, sources=[], generators=("fixture",), truth_status="synthetic-known-truth", seed=42,
                     code_version="test-build", riskvalidation_version="1.0.1")


def test_build_artifact_adds_the_generic_findings_and_they_pass_the_contract():
    lineage = _lineage()
    models = [{**mm, "family": "x", "rung": "x", "title": mm["short_title"], "engine": "x", "engine_version": "1", "licence": "MIT",
               "checkpoint_sha256": None, "calibration": None, "parameters": {}} for mm in MODELS]
    art = m.build_artifact(case_id="C99", variant_id="v", model=models, outputs={}, tests=fixture_tests(), impact={},
                           findings=fixture_findings(), lineage=lineage, lane={"lane": "precompute", "reasons": []})
    ids = [f["id"] for f in art["findings"]]
    assert ids[:2] == ["F-OWN", "F-LIMIT"] and len(ids) == 5
    m._check_findings(art["findings"], m._check_tests(art["tests"], "C99/v"), "C99/v")


# --- the committed documents (in memory) -----------------------------------------------------------------------------------


def _variants():
    for p in sorted(DERIVED.glob("C*/*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema") == m.ARTIFACT_SCHEMA:
            yield p, d


def test_every_committed_document_with_its_generic_findings_still_validates():
    n = 0
    for p, d in _variants():
        added = rf.red_findings(d["case_id"], d["tests"], d["findings"], d["model"])
        if not added:
            continue
        doc = {**d, "findings": [*d["findings"], *added]}
        validate_document(p.relative_to(ROOT).as_posix(), doc)
        m._check_findings(doc["findings"], m._check_tests(doc["tests"], p.name), p.name, m._rate_keys(doc["outputs"]))
        n += 1
    assert n > 0


def test_the_step_is_idempotent_on_its_own_output():
    for _p, d in _variants():
        added = rf.red_findings(d["case_id"], d["tests"], d["findings"], d["model"])
        assert rf.red_findings(d["case_id"], d["tests"], [*d["findings"], *added], d["model"]) == []


def count_on_committed() -> tuple[Counter, Counter]:
    rows, pairs = Counter(), Counter()
    for _p, d in _variants():
        for f in rf.red_findings(d["case_id"], d["tests"], d["findings"], d["model"]):
            rows[d["case_id"]] += len(f["evidence"])
            pairs[(d["case_id"], f["evidence"][0].split("@")[0])] += 1
    return rows, pairs


@pytest.mark.xfail(strict=True, reason="the committed documents predate U16-F12g (base a95c27d): the integrator's re-bake adds the generic "
                                       "findings, then this test passes and its mark is removed")
def test_every_red_row_of_every_committed_document_is_cited_by_an_open_finding():
    rows, _pairs = count_on_committed()
    assert sum(rows.values()) == 0, dict(rows)


def test_the_models_are_named_as_the_web_names_them_and_at_most_three_are_listed():
    """C11's model block carries the ids as its short titles; the title takes the names module's names instead."""
    ids = ["hs-250", "hs-500", "awhs", "ewma", "garch-t"]
    models = [{"id": i, "short_title": {"en": i, "es": i}} for i in ids]
    tests = [row("market.duration_test", i, "alpha=0.025", "red") for i in ids]
    (f,) = rf.red_findings("C11", tests, [], models)
    en, es = f["title"]["en"], f["title"]["es"]
    assert "Age-weighted historical simulation" in en and "Simulación histórica ponderada por edad" in es
    assert "and 2 more models)" in en and "y 2 modelos más)" in es
    for i in ids:
        assert f"({i}" not in en and f" {i}," not in en and i not in es.replace("garch", "")
    assert len(f["evidence"]) == 5


def test_a_model_whose_name_is_its_id_is_not_listed():
    """C22's configurations are named by their ids in models.gen.json; the title lists none of them."""
    models = [{"id": "port-5000-k1.5", "short_title": {"en": "port-5000-k1.5", "es": "port-5000-k1.5"}}]
    (f,) = rf.red_findings("C22", [row("pd.jeffreys", "port-5000-k1.5", None, "red")], [], models)
    assert "port-5000" not in f["title"]["en"] + f["title"]["es"]
    assert f["title"]["en"].startswith("Jeffreys: red on 1 row that no other finding cites")
    assert f["evidence"] == ["pd.jeffreys@port-5000-k1.5"]


def test_no_generic_title_on_the_committed_documents_prints_a_model_or_a_test_id():
    import re

    for p, d in _variants():
        ids = {mm["id"] for mm in d["model"]} | {t["test_id"] for t in d["tests"]}
        for f in rf.red_findings(d["case_id"], d["tests"], d["findings"], d["model"]):
            for lang in ("en", "es"):
                text = f["title"][lang]
                raw = [i for i in ids if not re.fullmatch(r"[A-Z][A-Za-z]+", i)
                       and re.search(r"(?<![\w-])" + re.escape(i) + r"(?![\w-])", text)]
                assert raw == [], (p.name, lang, raw, text)


def test_the_governance_register_reads_the_generic_findings_through_the_engine_anchor():
    """The governance bake anchors a finding on its first cited row (riskvalidation.governance.findings.anchor_from_test_row): every
    generic finding whose first row has a model gets its anchor; a row of no model (``test@-@segment``) gets the engine's stated
    reason, as the C20 findings of the same form do."""
    from riskvalidation.governance import findings as gov

    n = 0
    for p, d in _variants():
        for f in rf.red_findings(d["case_id"], d["tests"], d["findings"], d["model"]):
            anchor, why = gov.anchor_from_test_row(f["evidence"], d["tests"], document=p.name)
            if "@-@" in f["evidence"][0]:
                assert anchor is None and why
            else:
                assert anchor is not None and anchor["test_id"] == f["evidence"][0].split("@")[0], (p.name, f["id"], why)
                n += 1
    assert n > 0
