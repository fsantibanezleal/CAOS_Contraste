"""U12-S: the C17 case contracts (operational risk, LDA against SMA), their fixtures, the catalog rows and the engine
operational risk API contract.

The fixtures validate by discovery (tests/contracts/contract_schemas.py) against exactly one schema; the schemas are strict
both ways (a removed or an added key fails); a document without its true parameters or its true 99.9 percent annual loss
quantile fails; a mean-based quantity (the true mean, the mean-corrected single loss approximation) is null with its
reason when the tail index is 1 or more and the document says so with the infinite-mean flag; a money block without its
currency fails; the LDCE calibration targets carry their source and the derived-only label and cannot drift from the
transcribed dossier values; the SMA block names its discretion; a history shorter than 5 years is BIC-only. The engine
contract names every function of the modules table of plans/contraste/units/U12-sizing.md with a golden value or an
invariant, and its golden values recompute here from the formulas of dossiers 05 (section F) and 01 (section F). The
fixtures are labelled as fixtures and never published as results.
"""
from __future__ import annotations

import copy
import math
import re
from pathlib import Path
from typing import Any, Iterator

import pytest

import contract_schemas as cs

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures" / "c17"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
API = ROOT / "docs" / "contracts" / "engine" / "oprisk-api.md"
ROWS = ROOT / "docs" / "contracts" / "rows" / "U12.md"


def catalog_rows(ids):
    """The catalog rows of these contract ids, header first (the unit's rows fragment was merged by the integrator at 0.11.000)."""
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    lines = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0].splitlines()
    head = [ln for ln in lines if ln.startswith("| id | version")]
    return head + ["|---|"] + [ln for ln in lines if ln.startswith("| ") and ln.split("|")[1].strip() in ids]

VAR = "c17/variant-tail-index"
MOD = "c17/models"
FINITE = FIXTURES / "variant-tail-index-fixture.json"
INFINITE = FIXTURES / "variant-tail-index-infinite-mean-fixture.json"
MODELS = FIXTURES / "models-fixture.json"
DOCS = [(VAR, FINITE), (VAR, INFINITE), (MOD, MODELS)]
IDS = [p.stem for _, p in DOCS]


def load(path: Path) -> Any:
    return cs.load_json(path)


def out(path: Path = FINITE) -> dict:
    return load(path)["outputs"]


def fit() -> dict:
    return load(MODELS)["fit"]


def root_of(ref: str) -> str:
    return "outputs" if "variant" in ref else "fit"


# --- the fixtures -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_the_fixture_exists_and_is_discovered_by_exactly_one_schema(ref: str, path: Path) -> None:
    assert path.is_file(), path
    doc = cs.load_json(path)
    assert cs.schema_for_document(path, doc) == ref
    assert cs.errors(ref, doc) == []
    passing = [c.ref for c in cs.candidates() if cs.errors(c.ref, doc) == []]
    assert passing == [ref], f"{path.name}: validates against {passing}"


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_the_fixture_is_labelled_as_a_fixture(ref: str, path: Path) -> None:
    doc = load(path)
    assert doc["provenance"]["generators"] == ["fixture:u12-s-contracts"]
    assert any(i["source"] == "fixture-not-a-result" for i in doc["provenance"]["inputs"])
    assert doc["provenance"]["truth_status"] == "synthetic-known-truth"
    key = "variant_id" if "variant" in ref else "fit_id"
    assert str(doc[key]).startswith("fixture-")


def test_every_u12_schema_is_case_folder_conformant_and_case_prefixed() -> None:
    assert cs.case_folder_violations() == []
    files = sorted((SCHEMAS / "c17").glob("*.schema.json"))
    assert {p.relative_to(SCHEMAS).as_posix() for p in files} == {f"{VAR}.schema.json", f"{MOD}.schema.json"}
    for p in files:
        for name in cs.load_json(p).get("$defs", {}):
            assert name.startswith("c17"), f"{p.name}: $defs name {name!r} is not prefixed 'c17'"


def test_the_variant_schema_declares_its_outputs_kind_and_is_not_a_default() -> None:
    by_ref = {c.ref: c for c in cs.candidates()}
    assert by_ref[VAR].consts["outputs.kind"] == "tail-index"
    assert by_ref[VAR].consts["case_id"] == "C17" and by_ref[MOD].consts["case_id"] == "C17"
    assert cs.default_variants().get("C17") is None
    assert cs.default_violations() == []


def test_a_second_kind_less_variant_schema_fails() -> None:
    a = cs.Candidate.from_parts("c17/variant-planted", {"schema": "contraste.case/v1", "case_id": "C17"})
    b = cs.Candidate.from_parts("c17/variant-planted2", {"schema": "contraste.case/v1", "case_id": "C17"})
    assert cs.default_violations(cs.candidates() + (a, b)) != []


# --- strictness ---------------------------------------------------------------------------------------------------


def objects(node: Any, path: tuple = ()) -> Iterator[tuple[tuple, dict]]:
    if isinstance(node, dict):
        yield path, node
        for k, v in node.items():
            yield from objects(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from objects(v, path + (i,))


def get(doc: Any, path: tuple) -> Any:
    for p in path:
        doc = doc[p]
    return doc


def closed_objects(ref: str, path: Path) -> list[tuple[tuple, dict]]:
    """Every object under outputs (or fit) of the fixture: all of them are closed by the schema."""
    doc = load(path)
    return list(objects(doc[root_of(ref)], (root_of(ref),)))


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_key_removed_from_any_object_fails(ref: str, path: Path) -> None:
    doc = load(path)
    checked = 0
    for p, obj in closed_objects(ref, path):
        for key in list(obj):
            bad = copy.deepcopy(doc)
            del get(bad, p)[key]
            assert cs.errors(ref, bad) != [], f"{path.name}: removing {'/'.join(map(str, p))}/{key} still validates"
            checked += 1
    assert checked > 80


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_key_added_to_any_object_fails(ref: str, path: Path) -> None:
    doc = load(path)
    for p, _ in closed_objects(ref, path):
        bad = copy.deepcopy(doc)
        get(bad, p)["unknown_key"] = 1
        assert cs.errors(ref, bad) != [], f"{path.name}: adding a key at {'/'.join(map(str, p))} still validates"


@pytest.mark.parametrize("path", [FINITE, INFINITE], ids=["finite", "infinite"])
def test_a_document_without_case_id_or_outputs_kind_does_not_pass(path: Path) -> None:
    doc = load(path)
    no_case = copy.deepcopy(doc)
    del no_case["case_id"]
    assert cs.errors(VAR, no_case) != []
    with pytest.raises(cs.SelectionError):
        cs.schema_for_document(path, no_case)
    no_kind = copy.deepcopy(doc)
    del no_kind["outputs"]["kind"]
    assert cs.errors(VAR, no_kind) != []
    chosen = None
    try:
        chosen = cs.schema_for_document(path, no_kind)
    except cs.SelectionError:
        pass
    assert chosen != VAR
    if chosen is not None:
        assert cs.errors(chosen, no_kind) != []


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_wrong_case_id_is_rejected(ref: str, path: Path) -> None:
    doc = load(path)
    doc["case_id"] = "C99"
    assert cs.errors(ref, doc) != []


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_fixture_of_one_case_does_not_validate_against_another_case(ref: str, path: Path) -> None:
    doc = load(path)
    others = [c.ref for c in cs.candidates() if c.ref != ref and c.ref.split("/")[0] in ("c03", "c08", "c09", "c17")]
    assert others
    for other in others:
        assert cs.errors(other, doc) != [], f"{path.name} validates against {other}"


def test_a_variant_fixture_does_not_validate_as_models_and_the_reverse() -> None:
    assert cs.errors(MOD, load(FINITE)) != []
    assert cs.errors(VAR, load(MODELS)) != []


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_the_truth_status_is_synthetic_known_truth_by_schema(ref: str, path: Path) -> None:
    doc = load(path)
    for status in ("real-outcomes", "synthetic-calibrated", "published-answer"):
        bad = copy.deepcopy(doc)
        bad["provenance"]["truth_status"] = status
        assert cs.errors(ref, bad) != [], f"{path.name}: truth_status {status} validates"


# --- the truth: true parameters and the true 99.9 percent annual loss quantile --------------------------------------


def test_a_document_without_its_true_parameters_or_true_quantile_fails() -> None:
    doc = load(FINITE)
    bad = copy.deepcopy(doc)
    del bad["outputs"]["truth"]
    assert cs.errors(VAR, bad) != []
    truth = doc["outputs"]["truth"]
    assert truth["label"] == "synthetic-known-truth"
    for key in truth:
        bad = copy.deepcopy(doc)
        del bad["outputs"]["truth"][key]
        assert cs.errors(VAR, bad) != [], f"truth without {key} validates"
    for block, keys in (("frequency", ("law", "lambda_per_year")), ("severity", ("law", "location_eur", "scale_eur", "tail_index")),
                        ("annual_loss_quantile", ("level", "value_eur", "method", "mc_check"))):
        for key in keys:
            bad = copy.deepcopy(doc)
            del bad["outputs"]["truth"][block][key]
            assert cs.errors(VAR, bad) != [], f"truth.{block} without {key} validates"
    bad = copy.deepcopy(doc)
    bad["outputs"]["truth"]["label"] = "synthetic-calibrated"
    assert cs.errors(VAR, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["truth"]["annual_loss_quantile"]["level"] = 0.99
    assert cs.errors(VAR, bad) != [], "the true quantile is the 99.9 percent one"
    bad = copy.deepcopy(doc)
    bad["outputs"]["truth"]["annual_loss_quantile"]["value_eur"] = 0
    assert cs.errors(VAR, bad) != []


def test_the_models_document_carries_the_true_parameters_and_quantile_of_every_variant() -> None:
    f = fit()
    assert len(f["variants"]) == 4
    assert [v["tail_index"] for v in f["variants"]] == [0.6, 0.8, 0.96, 1.1]
    doc = load(MODELS)
    for i, v in enumerate(f["variants"]):
        for key in ("lambda_per_year", "location_eur", "scale_eur", "tail_index", "true_quantile_999_eur", "true_mean_eur",
                    "true_mean_reason", "infinite_mean", "variant_id"):
            assert key in v
            bad = copy.deepcopy(doc)
            del bad["fit"]["variants"][i][key]
            assert cs.errors(MOD, bad) != [], f"variants[{i}] without {key} validates"
    bad = copy.deepcopy(doc)
    del bad["fit"]["variants"][0]
    assert cs.errors(MOD, bad) != [], "three variants validate"


def test_the_truth_is_consistent_inside_each_variant_fixture() -> None:
    for path in (FINITE, INFINITE):
        o = out(path)
        t = o["truth"]
        assert t["severity"]["tail_index"] == o["tail_index"] == o["calibration"]["fit"]["tail_index"]
        assert t["frequency"]["counted_above_eur"] == t["severity"]["location_eur"]
        assert t["frequency"]["lambda_per_year"] > 0 and t["severity"]["scale_eur"] > 0
        mc = t["annual_loss_quantile"]["mc_check"]
        assert mc["agrees"] == (abs(mc["value_eur"] - t["annual_loss_quantile"]["value_eur"]) <= 3 * mc["standard_error_eur"])
        assert o["calibration"]["fit"]["scale_eur"] == t["severity"]["scale_eur"]
        assert o["exceedance"]["quantile_999_eur"]["panjer"] == t["annual_loss_quantile"]["value_eur"] or \
            o["exceedance"]["quantile_999_eur"]["fft"] == t["annual_loss_quantile"]["value_eur"]


def test_the_models_variant_rows_match_the_variant_fixtures() -> None:
    by_xi = {v["tail_index"]: v for v in fit()["variants"]}
    for path in (FINITE, INFINITE):
        o = out(path)
        row = by_xi[o["tail_index"]]
        assert row["true_quantile_999_eur"] == o["truth"]["annual_loss_quantile"]["value_eur"]
        assert row["lambda_per_year"] == o["truth"]["frequency"]["lambda_per_year"]
        assert row["scale_eur"] == o["truth"]["severity"]["scale_eur"]
        assert row["infinite_mean"] == o["infinite_mean"]


# --- the infinite-mean rule: a tail index of 1 or more has no mean ---------------------------------------------------


def test_the_two_variant_fixtures_cover_both_sides_of_a_tail_index_of_one() -> None:
    assert out(FINITE)["tail_index"] < 1 and out(FINITE)["infinite_mean"] is False
    assert out(INFINITE)["tail_index"] >= 1 and out(INFINITE)["infinite_mean"] is True


def test_the_infinite_mean_flag_follows_the_tail_index_exactly() -> None:
    """The flag is true exactly when the tail index is 1 or more. The finite fixture (mean present) holds only on the finite
    side, the infinite fixture (mean null with its reason) only on the infinite side."""
    for xi in (0.6, 0.8, 0.96, 1.1):
        for flag in (False, True):
            for path, finite_side in ((FINITE, True), (INFINITE, False)):
                doc = load(path)
                doc["outputs"]["tail_index"] = xi
                doc["outputs"]["infinite_mean"] = flag
                valid = cs.errors(VAR, doc) == []
                assert valid == ((xi < 1) == finite_side and flag == (xi >= 1)), (path.name, xi, flag)


def test_a_true_mean_for_a_tail_index_of_one_or_more_fails() -> None:
    doc = load(INFINITE)
    assert doc["outputs"]["truth"]["annual_loss_mean"]["value_eur"] is None
    assert doc["outputs"]["truth"]["annual_loss_mean"]["reason"]
    bad = copy.deepcopy(doc)
    bad["outputs"]["truth"]["annual_loss_mean"]["value_eur"] = 1.0e7
    assert cs.errors(VAR, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["truth"]["annual_loss_mean"]["reason"] = None
    assert cs.errors(VAR, bad) != []
    # and the finite side must carry the number
    finite = load(FINITE)
    assert isinstance(finite["outputs"]["truth"]["annual_loss_mean"]["value_eur"], (int, float))
    bad = copy.deepcopy(finite)
    bad["outputs"]["truth"]["annual_loss_mean"].update({"value_eur": None, "reason": "no mean"})
    assert cs.errors(VAR, bad) != []


def test_a_mean_corrected_sla_for_a_tail_index_of_one_or_more_fails() -> None:
    doc = load(INFINITE)
    for i, cell in enumerate(doc["outputs"]["cells"]):
        mc = cell["capital"]["sla_mean_corrected"]
        assert mc["summary"] is None and "infinite" in mc["reason"].lower(), i
        bad = copy.deepcopy(doc)
        bad["outputs"]["cells"][i]["capital"]["sla_mean_corrected"] = {
            "summary": copy.deepcopy(cell["capital"]["sla"]) | {"status": "UNVERIFIED"}, "reason": None}
        assert cs.errors(VAR, bad) != [], f"cell {i}: a mean-corrected SLA at a tail index of {doc['outputs']['tail_index']} validates"
        # the same summary without the UNVERIFIED label fails for its own reason too
        worse = copy.deepcopy(bad)
        worse["outputs"]["cells"][i]["capital"]["sla_mean_corrected"]["summary"]["status"] = "verified"
        assert cs.errors(VAR, worse) != []


def test_the_mean_corrected_sla_is_labelled_unverified_wherever_it_has_a_value() -> None:
    doc = load(FINITE)
    seen = 0
    for i, cell in enumerate(doc["outputs"]["cells"]):
        s = cell["capital"]["sla_mean_corrected"]["summary"]
        if s is None:
            continue
        seen += 1
        assert s["status"] == "UNVERIFIED"
        bad = copy.deepcopy(doc)
        bad["outputs"]["cells"][i]["capital"]["sla_mean_corrected"]["summary"]["status"] = "verified"
        assert cs.errors(VAR, bad) != []
    assert seen >= 1
    for cell in doc["outputs"]["cells"]:
        assert cell["capital"]["sla"]["status"] == "verified"


def test_a_summary_and_its_reason_are_never_both_present_or_both_absent() -> None:
    doc = load(FINITE)
    for member in ("sla_mean_corrected", "scenario"):
        for i, cell in enumerate(doc["outputs"]["cells"]):
            w = cell["capital"][member]
            bad = copy.deepcopy(doc)
            bad["outputs"]["cells"][i]["capital"][member] = {"summary": w["summary"], "reason": "both" if w["summary"] else None}
            assert cs.errors(VAR, bad) != [], (member, i)


# --- the LDCE calibration targets: source, derived-only label, transcribed values ----------------------------------

LDCE_PERCENTILES = [(0.25, 27632), (0.5, 41916), (0.75, 82608), (0.95, 418400)]


@pytest.mark.parametrize("where", ["variant", "models"])
def test_the_calibration_targets_carry_their_source_the_derived_only_label_and_the_transcribed_values(where: str) -> None:
    path, ref = (FINITE, VAR) if where == "variant" else (MODELS, MOD)
    doc = load(path)
    root = doc["outputs"] if where == "variant" else doc["fit"]
    targets = root["calibration"]["targets"] if where == "variant" else root["calibration"]
    assert targets["label"] == "derived-only" and targets["licence_class"] == "derived-only"
    assert targets["source"]["id"] == "bcbs160" and targets["source"]["url"] == "https://www.bis.org/publ/bcbs160.htm"
    assert targets["source"]["date"] == "2009-07-28" and targets["currency"] == "EUR" and targets["threshold_eur"] == 20000
    assert targets["frequency"]["per_eur_bn_assets"] == 0.82
    assert [(r["p"], r["loss_eur"]) for r in targets["severity_percentiles"]] == LDCE_PERCENTILES
    base = ("outputs", "calibration", "targets") if where == "variant" else ("fit", "calibration")
    # each source field is required, a drifted label or value fails
    for key in targets["source"]:
        bad = copy.deepcopy(doc)
        del get(bad, base)["source"][key]
        assert cs.errors(ref, bad) != [], f"source without {key} validates"
    for key in ("label", "licence_class"):
        bad = copy.deepcopy(doc)
        get(bad, base)[key] = "mirror-allowed"
        assert cs.errors(ref, bad) != []
    bad = copy.deepcopy(doc)
    get(bad, base)["severity_percentiles"][3]["loss_eur"] = 418401
    assert cs.errors(ref, bad) != [], "a drifted LDCE percentile validates"
    bad = copy.deepcopy(doc)
    get(bad, base)["frequency"]["per_eur_bn_assets"] = 0.8
    assert cs.errors(ref, bad) != []
    bad = copy.deepcopy(doc)
    get(bad, base)["severity_percentiles"].pop()
    assert cs.errors(ref, bad) != []


def test_the_calibration_fit_reports_its_quantiles_against_the_targets() -> None:
    for path in (FINITE, INFINITE):
        c = out(path)["calibration"]
        targets = [r["loss_eur"] for r in c["targets"]["severity_percentiles"]]
        fq = c["fit"]["fitted_quantiles_eur"]
        assert len(fq) == 4 and fq == sorted(fq)
        worst = max(abs(math.log(a / b)) for a, b in zip(fq, targets))
        assert math.isclose(c["fit"]["max_abs_log_error"], worst, abs_tol=5e-4), (path.name, worst)


# --- money blocks carry their currency (EUR) ------------------------------------------------------------------------


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_a_money_block_without_its_currency_fails(ref: str, path: Path) -> None:
    doc = load(path)
    sites = [(p, o) for p, o in closed_objects(ref, path) if "currency" in o]
    assert sites, f"{path.name}: no object carries a currency"
    for p, _ in sites:
        bad = copy.deepcopy(doc)
        del get(bad, p)["currency"]
        assert cs.errors(ref, bad) != [], f"{path.name}: {p} without currency validates"
        for wrong in ("dollars", "USD", "eur"):
            worse = copy.deepcopy(doc)
            get(worse, p)["currency"] = wrong
            assert cs.errors(ref, worse) != [], f"{path.name}: {p} with currency {wrong} validates"


@pytest.mark.parametrize("ref,path", DOCS, ids=IDS)
def test_every_money_field_is_named_eur_and_sits_under_a_block_that_states_the_currency(ref: str, path: Path) -> None:
    doc = load(path)
    found = 0
    for p, obj in closed_objects(ref, path):
        for key in obj:
            if key.endswith("_eur"):
                found += 1
                assert any(get(doc, p[:n]).get("currency") == "EUR" for n in range(len(p), 0, -1)
                           if isinstance(get(doc, p[:n]), dict)), f"{path.name}: {'/'.join(map(str, p))}/{key} has no currency in any enclosing block"
    assert found > 10


# --- the SMA block: BI, BIC, LC and ILM with the discretion applied as a named field ---------------------------------


def bic(bi: float) -> float:
    """OPE25.7 Table 1 (dossier 01 section F), EUR: 12% to 1bn, 15% from 1bn to 30bn, 18% above."""
    bn = 1e9
    return 0.12 * min(bi, bn) + 0.15 * max(min(bi, 30 * bn) - bn, 0) + 0.18 * max(bi - 30 * bn, 0)


def ilm(lc: float, b: float) -> float:
    return math.log(math.e - 1 + (lc / b) ** 0.8)


def bucket_of(bi: float) -> int:
    return 1 if bi <= 1e9 else 2 if bi <= 30e9 else 3


def test_the_sma_block_names_bi_bic_lc_ilm_and_the_discretion_applied() -> None:
    o = out()
    bank = o["bank"]
    assert {"business_indicator", "bic_eur", "bucket"} <= set(bank)
    assert set(bank["business_indicator"]) == {"ildc_eur", "sc_eur", "fc_eur", "bi_eur"}
    for cell in o["cells"]:
        sma = cell["sma"]
        assert {"basis", "discretion_applied", "bucket", "bic_eur", "lc_eur", "ilm", "orc_eur"} <= set(sma)
        assert "reason" not in sma
        assert sma["discretion_applied"] in {"none", "bucket-1-ilm-one", "national-ilm-one"}
    doc = load(FINITE)
    for key in ("discretion_applied", "basis", "bic_eur", "lc_eur", "ilm", "orc_eur", "bucket"):
        bad = copy.deepcopy(doc)
        del bad["outputs"]["cells"][0]["sma"][key]
        assert cs.errors(VAR, bad) != [], f"sma without {key} validates"
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"][0]["sma"]["discretion_applied"] = "unknown"
    assert cs.errors(VAR, bad) != []


def test_the_bank_bi_bic_and_bucket_follow_ope25() -> None:
    for path in (FINITE, INFINITE):
        bank = out(path)["bank"]
        bi = bank["business_indicator"]
        assert math.isclose(bi["bi_eur"], bi["ildc_eur"] + bi["sc_eur"] + bi["fc_eur"], rel_tol=1e-12)  # OPE25.4
        assert math.isclose(bank["bic_eur"], bic(bi["bi_eur"]), rel_tol=1e-9)
        assert bank["bucket"] == bucket_of(bi["bi_eur"])
        assert bank["synthetic"] is True
        for cell in out(path)["cells"]:
            assert cell["sma"]["bic_eur"] == bank["bic_eur"] and cell["sma"]["bucket"] == bank["bucket"]


def test_the_ilm_and_orc_percentiles_follow_the_lc_percentiles_through_the_monotone_ope25_formulas() -> None:
    """ILM is increasing in LC and ORC = BIC x ILM is increasing in ILM, so each percentile of ILM and ORC is the transform
    of the same percentile of LC (nearest-rank percentiles commute with a monotone map)."""
    for path in (FINITE, INFINITE):
        for cell in out(path)["cells"]:
            sma = cell["sma"]
            if sma["basis"] != "bic-times-ilm":
                continue
            for key in ("p05", "p25", "median", "p75", "p95"):
                expected = 1.0 if sma["discretion_applied"] in ("bucket-1-ilm-one", "national-ilm-one") \
                    else ilm(sma["lc_eur"][key], sma["bic_eur"])
                assert math.isclose(sma["ilm"][key], expected, rel_tol=1e-6), (path.name, cell["id"], key)
                assert math.isclose(sma["orc_eur"][key], sma["bic_eur"] * sma["ilm"][key], rel_tol=1e-6)
                truth = out(path)["truth"]["annual_loss_quantile"]["value_eur"]
                assert math.isclose(sma["orc_over_true_quantile"][key], sma["orc_eur"][key] / truth, rel_tol=1e-6)


def test_the_sma_discretion_couples_with_the_bucket_and_sets_the_ilm_to_one() -> None:
    doc = load(FINITE)
    cell0 = doc["outputs"]["cells"][0]["sma"]
    assert cell0["basis"] == "bic-times-ilm" and cell0["discretion_applied"] == "none"
    # bucket-1 discretion is for bucket 1 only
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"][0]["sma"]["discretion_applied"] = "bucket-1-ilm-one"
    assert cs.errors(VAR, bad) != [], "bucket-1 discretion on a bucket-2 bank validates"
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"][0]["sma"]["basis"] = "bic-only"
    assert cs.errors(VAR, bad) != [], "a BIC-only basis is not reachable in a 5 or 10 year cell"
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"][0]["sma"]["lc_eur"] = None
    assert cs.errors(VAR, bad) != [], "a full ILM basis without LC validates"


def test_an_ilm_is_unreachable_on_fewer_than_five_years_in_any_c17_block() -> None:
    """OPE25.10 and OPE25.15 (dossier 01 section F): under 5 years of loss data capital is BIC only. The C17 grid is 5 or 10
    years, so a cell of any other length is refused whole; the BIC-only rule is the engine's (`sma_capital`)."""
    doc = load(FINITE)
    for years in (0, 1, 3, 4, 7, 9, 11):
        bad = copy.deepcopy(doc)
        bad["outputs"]["cells"][0]["years"] = years
        assert cs.errors(VAR, bad) != [], f"a cell of {years} years validates"
    assert "BIC only" in section("sma", "sma_capital") and "OPE25.15" in section("sma", "sma_capital")


def test_the_sma_response_curve_applies_the_ope25_formulas() -> None:
    for path in (FINITE, INFINITE):
        r = out(path)["sma_response"]
        assert r["bic_eur"] == out(path)["bank"]["bic_eur"]
        added = [x["added_loss_eur"] for x in r["rows"]]
        assert added == sorted(added) and added[0] == 0 and len(set(added)) == len(added)
        for x in r["rows"]:
            assert math.isclose(x["ilm"], ilm(x["lc_eur"], r["bic_eur"]), rel_tol=1e-6)
            assert math.isclose(x["orc_eur"], r["bic_eur"] * x["ilm"], rel_tol=1e-6)
        lc = [x["lc_eur"] for x in r["rows"]]
        assert lc == sorted(lc) and all(b > a for a, b in zip(lc, lc[1:]))
        # LC = 15 x the mean of 10 annual losses: one added loss L raises it by 15 L / 10
        for x in r["rows"]:
            assert math.isclose(x["lc_eur"] - lc[0], 1.5 * x["added_loss_eur"], rel_tol=1e-6)


# --- the replications: summaries, not histories; independent seeds --------------------------------------------------


def test_the_cells_are_the_cross_of_years_and_collection_thresholds_in_fixed_order() -> None:
    for path in (FINITE, INFINITE):
        cells = out(path)["cells"]
        assert [(c["years"], c["collection_threshold_eur"]) for c in cells] == [(5, 10000), (5, 20000), (10, 10000), (10, 20000)]
        assert len({c["id"] for c in cells}) == 4
    doc = load(FINITE)
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"].pop()
    assert cs.errors(VAR, bad) != []
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"].append(copy.deepcopy(bad["outputs"]["cells"][0]))
    assert cs.errors(VAR, bad) != []


def test_the_replication_seeds_are_disjoint_between_cells_and_variants() -> None:
    ranges = []
    for path in (FINITE, INFINITE):
        for c in out(path)["cells"]:
            r = c["replications"]
            assert r["n_failed"] < r["n_replications"] and r["n_replications"] >= 2
            ranges.append((r["seed_first"], r["seed_first"] + r["n_replications"] - 1, path.name, c["id"]))
    ranges.sort()
    for a, b in zip(ranges, ranges[1:]):
        assert a[1] < b[0], f"seed ranges overlap: {a} {b}"


def test_percentile_summaries_are_ordered_and_the_ratios_are_capital_over_the_true_quantile() -> None:
    for path in (FINITE, INFINITE):
        o = out(path)
        truth = o["truth"]["annual_loss_quantile"]["value_eur"]
        for cell in o["cells"]:
            for name, cap in cell["capital"].items():
                s = cap if name in ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla") else cap["summary"]
                if s is None:
                    continue
                keys = ("p05", "p25", "median", "p75", "p95")
                for block in ("capital_eur", "ratio_to_truth"):
                    vals = [s[block][k] for k in keys]
                    assert vals == sorted(vals), (path.name, cell["id"], name, block)
                for k in keys:
                    assert math.isclose(s["ratio_to_truth"][k], s["capital_eur"][k] / truth, rel_tol=1e-6), (cell["id"], name, k)
                assert math.isclose(s["iqr_over_truth"], (s["capital_eur"]["p75"] - s["capital_eur"]["p25"]) / truth, rel_tol=1e-6)
                assert 0 <= s["share_underestimating"] <= 1 and s["n_defined"] <= cell["replications"]["n_replications"]
                assert s["n_defined"] >= 2


def test_the_fitted_tail_index_profile_has_increasing_thresholds_starting_at_the_collection_threshold() -> None:
    for path in (FINITE, INFINITE):
        for cell in out(path)["cells"]:
            rows = cell["threshold_stability"]
            th = [r["threshold_eur"] for r in rows]
            assert th == sorted(th) and len(set(th)) == len(th) and th[0] == cell["collection_threshold_eur"]
            for r in rows:
                t = r["tail_index"]
                assert t["p05"] <= t["median"] <= t["p95"]
                assert 0 <= r["share_at_least_one"] <= 1 and r["n_fits"] <= cell["replications"]["n_replications"]
            ex = [r["n_exceedances_median"] for r in rows]
            assert ex == sorted(ex, reverse=True)


def test_the_aggregate_exceedance_curve_agrees_across_methods_and_ends_at_the_marked_quantiles() -> None:
    for path in (FINITE, INFINITE):
        o = out(path)
        e = o["exceedance"]
        grid = e["grid_eur"]
        assert grid == sorted(grid) and len(set(grid)) == len(grid) and grid[0] > 0
        for name in ("monte_carlo", "panjer", "fft"):
            curve = e[name]["exceedance"]
            assert len(curve) == len(grid), name
            assert all(0 <= x <= 1 for x in curve)
            assert all(b <= a + 1e-12 for a, b in zip(curve, curve[1:])), f"{name} exceedance is not nonincreasing"
        q = e["quantile_999_eur"]
        assert set(q) == {"monte_carlo", "panjer", "fft", "sla"}
        truth = o["truth"]["annual_loss_quantile"]
        assert truth["level"] == 0.999
        assert abs(q["panjer"] - q["fft"]) / q["panjer"] < 1e-3
        assert abs(q[truth["method"]] - truth["value_eur"]) < 1e-9 * truth["value_eur"] + 1e-6


# --- the other views' blocks ------------------------------------------------------------------------------------------


def test_the_scenario_influence_is_the_relative_change_of_capital_without_the_point() -> None:
    for path in (FINITE, INFINITE):
        si = out(path)["scenario_influence"]
        assert si["level"] == 0.999 and si["scenarios"]
        ids = [s["scenario_id"] for s in si["scenarios"]]
        assert len(set(ids)) == len(ids)
        for s in si["scenarios"]:
            assert math.isclose(s["influence"], (si["base_capital_eur"] - s["capital_without_eur"]) / si["base_capital_eur"], abs_tol=1e-6)
            assert s["loss_eur"] > 0 and s["exceedance_frequency_per_year"] > 0
        cells = {c["id"] for c in out(path)["cells"]}
        assert si["cell_id"] in cells and out(path)["sma_response"]["cell_id"] in cells


# --- the catalog rows -----------------------------------------------------------------------------------------------


def row_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


ROW_IDS = ["c17-outputs", "c17-models", "engine-oprisk-api"]


def test_the_rows_fragment_has_the_three_rows_in_the_catalog_columns() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    header = next(row_cells(ln) for ln in catalog.splitlines() if ln.startswith("| id | version"))
    lines = [ln for ln in catalog_rows(ROW_IDS) if ln.startswith("|")]
    rows = [row_cells(ln) for ln in lines]
    assert rows[0] == header
    data = [r for r in rows[1:] if not all(set(c) <= set(":- ") for c in r)]
    assert [r[0] for r in data] == ROW_IDS
    for r in data:
        assert len(r) == len(header), r[0]
        d = dict(zip(header, r))
        assert d["version"] == ("3.0.0" if d["id"] == "c17-outputs" else "1.0.0")  # c17-outputs 3.0.0: the nullable FFT exceedance (U16-R3 c18 B2), after 2.0.0 the Panjer one (U16-F4)
        assert d["status"] == "real"                         # the integrator set real when the bake landed (0.11.000)
        assert d["provider"].startswith("fixture:")
        assert (ROOT / d["schema file"]).is_file(), d["schema file"]
        assert (ROOT / d["example"]).is_file(), d["example"]
        assert (ROOT / d["provider"].removeprefix("fixture:")).is_file(), d["provider"]
        for cell in (d["producer test"], d["consumer test"]):
            for t in cell.split(","):
                path, _, name = t.strip().partition("::")
                assert (ROOT / path).is_file(), path
                if name:
                    assert f"def {name}(" in (ROOT / path).read_text(encoding="utf-8"), t
    contracts = catalog.split("## Contracts", 1)[1].split("\n## ", 1)[0]
    cat_ids = [row_cells(ln)[0] for ln in contracts.splitlines() if ln.startswith("| ")]
    assert all(cat_ids.count(i) == 1 for i in ROW_IDS), "the integrator merged these rows once each"


# --- the engine operational risk API contract -----------------------------------------------------------------------

MODULES = {
    "distributions": ["frequency_pmf", "severity_cdf", "severity_ppf", "severity_moment", "truncated_severity_cdf",
                      "rescale_frequency", "FrequencyFit", "fit_frequency", "SeverityFit", "fit_severity", "SpliceFit",
                      "fit_splice", "TailProfile", "tail_index_profile"],
    "aggregate": ["panjer_coefficients", "panjer_h0", "discretise_severity", "panjer_recursion", "fft_aggregate",
                  "AnnualLossSample", "simulate_annual_losses", "mc_quantile", "quantile_from_pmf", "es_from_pmf",
                  "exceedance_from_pmf", "CompoundMoments", "compound_poisson_moments"],
    "sla": ["sla_var", "sla_var_poisson_gpd", "SlaResult", "sla_var_mean_corrected"],
    "scenarios": ["ScenarioPoint", "scenario_pseudo_observations", "fit_tail_to_scenarios", "GammaPrior",
                  "gamma_prior_from_mean_interval", "gamma_prior_from_scenarios", "CredibilityFit", "credibility_pareto",
                  "scenario_influence"],
    "sma": ["ildc", "service_component", "financial_component", "business_indicator", "bic_bucket", "bic", "loss_component",
            "ilm", "SmaResult", "sma_capital"],
    "validation.oprisk": ["benchmark_reproduction", "threshold_stability", "capital_stability", "sma_ilm_response",
                          "scenario_influence"],
}
TEST_FUNCTIONS = MODULES["validation.oprisk"]
RESULT_TYPES = {"FrequencyFit", "SeverityFit", "SpliceFit", "TailProfile", "AnnualLossSample", "CompoundMoments", "SlaResult",
                "ScenarioPoint", "GammaPrior", "CredibilityFit", "SmaResult"}


def prefix_of(module: str) -> str:
    return "riskvalidation.validation.oprisk" if module == "validation.oprisk" else f"riskvalidation.oprisk.{module}"


def key_of(module: str, name: str) -> str:
    return f"{prefix_of(module)}.{name}"


def api_sections() -> dict[str, str]:
    text = API.read_text(encoding="utf-8")
    parts = re.split(r"^### `([^`]+)`\s*$", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def section(module: str, name: str) -> str:
    return api_sections()[key_of(module, name)]


def test_the_engine_contract_exists_with_its_version() -> None:
    text = API.read_text(encoding="utf-8")
    assert "engine-oprisk-api" in text and "1.0.0" in text
    assert "common/test-result" in text


def test_the_engine_contract_covers_every_module_of_the_sizing_table() -> None:
    text = API.read_text(encoding="utf-8")
    for module in ("oprisk/distributions.py", "oprisk/aggregate.py", "oprisk/sla.py", "oprisk/scenarios.py", "oprisk/sma.py",
                   "validation/oprisk.py"):
        assert f"`riskvalidation/{module}`" in text, module


@pytest.mark.parametrize("module", MODULES)
def test_every_function_has_a_signature_and_a_golden_value_or_an_invariant(module: str) -> None:
    for name in MODULES[module]:
        body = section(module, name)
        assert "```python" in body, name
        assert re.search(r"^- (Golden|Invariants):", body, flags=re.M), f"{name}: no golden value or invariant"
        assert re.search(r"^- Units:", body, flags=re.M), f"{name}: no units line"
        if name in RESULT_TYPES:
            assert "@dataclass(frozen=True)" in body, f"{name}: result types are frozen dataclasses"


def test_every_validation_function_has_a_light_rule_a_test_id_and_a_golden() -> None:
    for name in TEST_FUNCTIONS:
        body = section("validation.oprisk", name)
        assert "-> TestResult" in body, name
        assert re.search(r"^- Light:", body, flags=re.M), name
        assert re.search(r"^- Golden:", body, flags=re.M), name
        assert re.search(r'test_id = "oprisk\.[a-z_]+"', body), name


def test_the_engine_contract_has_no_function_outside_the_table() -> None:
    declared = {key_of(m, n) for m, names in MODULES.items() for n in names}
    assert set(api_sections()) == declared


def test_the_engine_contract_carries_the_dossier_goldens() -> None:
    text = API.read_text(encoding="utf-8")
    for golden in ("738.9056", "298095.7987", "40.3428", "0.998999329", "5849", "5850", "5.37", "OPE25.7", "OPE25.8", "OPE25.9",
                   "OPE25.15", "OPE25.10", "OPE25.11", "OPE25.5", "OPE25.4", "OPE25.2", "OPE25.18"):
        assert golden in text, golden
    for test_id in ("oprisk.benchmark_reproduction", "oprisk.threshold_stability", "oprisk.capital_stability",
                    "oprisk.sma_ilm_response", "oprisk.scenario_influence"):
        assert test_id in text, test_id
    for cite in ("Shevchenko", "Table 1", "eq. 36", "eq. 70", "Example 9.4", "Table 2"):
        assert cite in text, cite
    assert "UNVERIFIED" in text
    assert "infinite" in text.lower()


def test_the_unverified_items_are_stated_unverified_never_decided() -> None:
    text = API.read_text(encoding="utf-8")
    body = section("sla", "sla_var_mean_corrected")
    assert "UNVERIFIED" in body and "Bocker and Sprittulla" in body
    assert "ValueError" in body and "tail index" in body
    assert "UNVERIFIED" in section("sla", "SlaResult")
    assert "offset" not in text.lower(), "the Table 2 label offset was refuted by the review and is gone"


# --- the golden values of the engine contract recompute here from the formulas ---------------------------------------


def test_golden_compound_poisson_lognormal_moments_recompute() -> None:
    lam, mu, sigma = 100.0, 0.0, 2.0
    m = lambda k: math.exp(k * mu + k * k * sigma * sigma / 2)  # noqa: E731  (raw lognormal moment)
    mean, var = lam * m(1), lam * m(2)
    skew = lam * m(3) / var ** 1.5
    assert math.isclose(mean, 738.9056, abs_tol=5e-5)
    assert math.isclose(var, 298095.7987, abs_tol=5e-5)
    assert math.isclose(skew, 40.3428, abs_tol=1e-4)  # the dossier's 40.3428 is 40.342879 cut at four decimals


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def test_golden_panjer_benchmark_reproduces_h_of_dossier_05() -> None:
    """Shevchenko Example 9.4 / Table 2 as quoted in dossier 05 F.3: Poisson(100) with LN(0, 2), central-difference
    discretisation with step 1. The cumulative sum through the zero-based index 5847 is the table's 0.998999329 (the
    table labels it H_5849, an offset of two that the contract states as UNVERIFIED), and the smallest n with a cumulative
    sum of at least 0.999 is the zero-based 5849 (the dossier: the quantile is about 5849 to 5850)."""
    lam, n_max = 100.0, 5850
    cdf = lambda x: 0.0 if x <= 0 else _phi(math.log(x) / 2.0)  # noqa: E731
    f = [cdf(0.5)] + [cdf(j + 0.5) - cdf(j - 0.5) for j in range(1, n_max + 1)]
    h = [math.exp(lam * (f[0] - 1))]
    for n in range(1, n_max + 1):
        h.append(lam / n * sum(j * f[j] * h[n - j] for j in range(1, n + 1)))
    cum, running = [], 0.0
    for p in h:
        running += p
        cum.append(running)
    assert math.isclose(cum[5847], 0.998999329, abs_tol=5e-10)
    assert cum[5848] < 0.999 <= cum[5849]
    text = API.read_text(encoding="utf-8")
    assert "0.998999329" in text and "0.998999329180" in text
    assert "0.999000217" in text


def test_golden_panjer_h0_of_each_law_recomputes_from_shevchenko_table_1() -> None:
    f0 = 0.5
    assert math.isclose(math.exp(2.0 * (f0 - 1)), 0.367879, abs_tol=5e-7)                    # Poisson(2)
    r, q = 2.0, 0.5
    assert math.isclose((1 + (1 - f0) * (1 - q) / q) ** (-r), 0.444444, abs_tol=5e-7)          # NegBin(2, 0.5)
    assert (1 - q, (1 - q) * (r - 1)) == (0.5, 0.5)                                            # its (a, b)
    m = 2.0
    assert math.isclose((1 + q * (f0 - 1)) ** m, 0.5625, abs_tol=1e-12)                       # binomial(2, 0.5)
    assert (-q / (1 - q), q * (m + 1) / (1 - q)) == (-1.0, 3.0)                                # its (a, b)
    text = API.read_text(encoding="utf-8")
    for golden in ("0.367879", "0.444444", "0.5625"):
        assert golden in text, golden


def test_golden_bic_and_ilm_recompute() -> None:
    assert math.isclose(bic(35e9), 5.37e9, rel_tol=1e-12)                    # OPE25.7 footnote 2
    assert math.isclose(1 * 0.12 + 29 * 0.15 + 5 * 0.18, 5.37, abs_tol=1e-12)
    assert math.isclose(bic(0.5e9), 0.06e9, rel_tol=1e-12) and math.isclose(bic(1e9), 0.12e9, rel_tol=1e-12)
    assert math.isclose(bic(30e9), 4.47e9, rel_tol=1e-12)
    assert ilm(150.0, 150.0) == 1.0                                          # OPE25.9: ILM = 1 when LC = BIC
    assert ilm(300.0, 150.0) > 1 > ilm(75.0, 150.0)
    text = API.read_text(encoding="utf-8")
    for golden in ("5.37", "4.47", "0.06", "1.220648", "1.241090", "0.829700"):
        assert golden in text, golden
    assert math.isclose(ilm(285.0, 150.0), 1.220648, abs_tol=5e-7)
    assert math.isclose(ilm(300.0, 150.0), 1.241090, abs_tol=5e-7)
    assert math.isclose(ilm(75.0, 150.0), 0.829700, abs_tol=5e-7)


def test_golden_sla_closed_forms_recompute() -> None:
    xi, beta, lam, alpha = 0.5, 100.0, 10.0, 0.99
    closed = beta / xi * ((lam / (1 - alpha)) ** xi - 1)                     # dossier 05 F.4, Poisson-GPD
    assert math.isclose(closed, 6124.555320, abs_tol=5e-7)
    ppf = lambda p: beta / xi * ((1 - p) ** (-xi) - 1)                      # noqa: E731  (GPD, location 0)
    assert math.isclose(ppf(1 - (1 - alpha) / lam), closed, rel_tol=1e-12)    # eq. 70 agrees with the closed form
    corrected = closed + lam * beta / (1 - xi)                               # UNVERIFIED form of dossier 05 F.4
    assert math.isclose(corrected, 8124.555320, abs_tol=5e-7)
    text = API.read_text(encoding="utf-8")
    assert "6124.555320" in text and "8124.555320" in text


def test_the_dossier_sla_figure_of_647_million_is_reproduced_by_the_log_excess_least_squares_fit() -> None:
    """Dossier 05 F.6: a GPD for the excesses over EUR 20,000 fitted by least squares on the log of the excess quantiles to the four
    LDCE median percentiles gives xi 0.96378, beta 22,349.4 and an SLA of EUR 647.1 million at lambda 41 and level 0.999;
    rounding xi to 0.96 gives 624.1 million."""
    u, ps, tgt = 20000.0, (0.25, 0.5, 0.75, 0.95), (27632.0, 41916.0, 82608.0, 418400.0)

    def q(p: float, xi: float, b: float) -> float:
        return u + b / xi * ((1 - p) ** (-xi) - 1)

    def obj(xi: float, b: float) -> float:
        return sum((math.log(q(p, xi, b) - u) - math.log(t - u)) ** 2 for p, t in zip(ps, tgt))

    xi0, b0, sx, sb = 0.96, 22350.0, 0.2, 8000.0
    for _ in range(80):
        best = (1e18, xi0, b0)
        for i in range(-20, 21):
            for j in range(-20, 21):
                xi, b = xi0 + sx * i / 20, b0 + sb * j / 20
                if xi > 0.05 and b > 0 and obj(xi, b) < best[0]:
                    best = (obj(xi, b), xi, b)
        _, xi0, b0 = best
        sx, sb = sx * 0.6, sb * 0.6
    assert math.isclose(xi0, 0.96378, abs_tol=5e-5) and math.isclose(b0, 22349.4, abs_tol=0.5)
    assert [round(q(p, xi0, b0)) for p in ps] == [27409, 42039, 85025, 412906]
    sla = u + b0 / xi0 * ((41 / 0.001) ** xi0 - 1)
    assert math.isclose(sla, 647.1e6, rel_tol=1e-3)
    rounded = u + 22350.0 / 0.96 * ((41 / 0.001) ** 0.96 - 1)
    assert math.isclose(rounded, 624.1e6, rel_tol=1e-3)
    text = API.read_text(encoding="utf-8")
    for needle in ("647.1 million", "0.96378", "22349.4", "624.1 million", "27409"):
        assert needle in text, needle
    for gone in ("not reproduced", "which unrounded fit gives 647 million is UNVERIFIED"):
        assert gone not in text, gone


def test_golden_object_level_values_recompute() -> None:
    text = API.read_text(encoding="utf-8")
    # discretise_severity: LN(0, 2), step 1, central difference
    cdf = lambda x: 0.0 if x <= 0 else _phi(math.log(x) / 2.0)  # noqa: E731
    f = [cdf(0.5), cdf(1.5) - cdf(0.5), cdf(2.5) - cdf(1.5)]
    for g, t in zip(f, (0.364456, 0.215872, 0.096248)):
        assert math.isclose(g, t, abs_tol=5e-7) and f"{t:.6f}" in text
    assert math.isclose(math.exp(100 * (f[0] - 1)), 2.504194e-28, rel_tol=1e-6) and "2.504194e-28" in text
    # frequency_pmf, severity laws, moments
    assert [round(math.exp(-2) * 2 ** n / math.factorial(n), 6) for n in range(3)] == [0.135335, 0.270671, 0.270671]
    assert math.isclose(1 - 1.5 ** -2, 0.555556, abs_tol=5e-7) and 200 * (10 - 1) == 1800
    assert math.isclose(20000 / 0.375, 53333.333333, abs_tol=5e-7) and math.isclose(100 / 0.75, 133.333333, abs_tol=5e-7)
    assert math.isclose(math.gamma(1.5), 0.886227, abs_tol=5e-7) and math.isclose(1 - math.exp(-1), 0.632121, abs_tol=5e-7)
    assert math.isclose(10 / 1.5 ** -2, 22.5, abs_tol=1e-9)  # lambda_obs / (1 - F(H)) with 1 - F(H) = 1.5 ** -2
    # fits: the lognormal MLE of [1, e, e^2] and the Poisson MLE of [3, 5, 4]
    assert math.isclose(math.sqrt(2 / 3), 0.816497, abs_tol=5e-7) and math.isclose(math.sqrt(2 / 3) / math.sqrt(3), 0.471405, abs_tol=5e-7)
    assert math.isclose(math.sqrt(4 / 3), 1.154701, abs_tol=5e-7)
    # the splice weight from the observed tail share t and c = F_b(H) / F_b(u): w = (1 - t) / (1 - t c), so that (1 - w) / (1 - w c) = t
    t, c = 0.2, 0.5
    w = (1 - t) / (1 - t * c)
    assert math.isclose(w, 0.888889, abs_tol=5e-7) and math.isclose((1 - w) / (1 - w * c), t, abs_tol=1e-12)
    # mc_quantile: the order statistics of 1..1000
    assert (math.ceil(1000 * 0.5 + math.sqrt(1000 * 0.25)), math.floor(1000 * 0.5 - math.sqrt(1000 * 0.25))) == (516, 484)
    assert (math.ceil(1000 * 0.999 + math.sqrt(1000 * 0.999 * 0.001)), math.floor(1000 * 0.999 - math.sqrt(1000 * 0.999 * 0.001))) == (1000, 998)
    # quantile_from_pmf, es_from_pmf, exceedance_from_pmf on h = [0.5, 0.3, 0.2], step 10
    h, step, alpha = [0.5, 0.3, 0.2], 10.0, 0.75
    cum = [sum(h[: i + 1]) for i in range(3)]
    n_q = next(i for i, c_ in enumerate(cum) if c_ >= alpha - 1e-12)
    q = n_q * step
    es = (sum(i * step * p for i, p in enumerate(h) if i > n_q) + q * (cum[n_q] - alpha)) / (1 - alpha)
    assert (n_q, q) == (1, 10.0) and math.isclose(es, 18.0, abs_tol=1e-12)
    # scenario_influence (engine) on capital = sum of loss x frequency
    pts = [(100.0, 0.1), (1000.0, 0.01), (50.0, 1.0)]
    cap = sum(x * f_ for x, f_ in pts)
    infl = [round((cap - (cap - x * f_)) / cap, 6) for x, f_ in pts]
    assert cap == 70.0 and infl == [0.142857, 0.142857, 0.714286]
    # OPE25 components with the absolute values taken year by year (OPE25.5 footnote 1)
    assert min(8.0, 0.0225 * 100) + 1.0 == 3.25 and min(8.0, 0.0225 * 1000) + 1.0 == 9.0
    assert sum(abs(a - b) for a, b in zip([10, 2, 10], [2, 10, 2])) / 3 == 8.0 and abs(sum([10, 2, 10]) - sum([2, 10, 2])) / 3 < 8.0
    assert max(5, 3) + max(2, 4) == 9 and sum(map(abs, [10, -10, 10])) / 3 + sum(map(abs, [-3, 3, -3])) / 3 == 13.0
    assert 3.25 + 9 + 13 == 25.25 and 15 * (20 + 10 + 30 + 40 + 0) / 5 == 300.0
    assert math.isclose(ilm(0.0, 1.0), 0.541325, abs_tol=5e-7) and math.isclose(12.5 * 5.37e9, 67.125e9)
    for golden in ("0.541325", "67.125", "25.25", "3.25", "0.142857", "0.714286", "0.888889", "18.0", "0.471405", "1.154701",
                   "0.816497", "22.5", "53333.333333", "133.333333", "0.886227", "0.632121", "1800", "0.555556", "0.135335"):
        assert golden in text, golden


def test_golden_validation_statistics_recompute() -> None:
    # benchmark_reproduction: the panjer and fft quantiles are inside the step-1 range [5849, 5850] (deviation 0); the Monte Carlo
    # quantile is the continuous one, 5853.1 (Shevchenko Table 3 at step 0.0625 and Table 7), so its deviation is |q - 5853.1| / 5853.1
    dev = abs(5900.0 - 5853.1) / 5853.1
    assert math.isclose(dev, 0.008013, abs_tol=5e-7) and math.isclose(dev / 0.01, 0.801285, abs_tol=5e-7)
    # threshold_stability: the range of the fitted tail index over the profile, and the count of fits at or above 1
    xs = [0.90, 0.95, 1.00, 0.97]
    assert math.isclose(max(xs) - min(xs), 0.10, abs_tol=1e-12) and sum(x >= 1 for x in xs) == 1
    # capital_stability: linear-interpolation percentiles (numpy default)
    caps = [90.0, 100.0, 110.0, 120.0]

    def pct(x: list[float], p: float) -> float:
        k = (len(x) - 1) * p
        i = int(k)
        return x[i] + (x[min(i + 1, len(x) - 1)] - x[i]) * (k - i)

    assert (pct(caps, 0.25), pct(caps, 0.5), pct(caps, 0.75)) == (97.5, 105.0, 112.5)
    assert math.isclose((pct(caps, 0.75) - pct(caps, 0.25)) / 100.0, 0.15, abs_tol=1e-12)
    assert math.isclose(pct(caps, 0.5) / 100.0 - 1, 0.05, abs_tol=1e-12)
    # sma_ilm_response: ten annual losses of 10, BIC 150: LC = 150, ILM = 1; one added loss of 90 gives LC 285
    assert 15 * (10 * 10) / 10 == 150.0 and 15 * (100 + 90) / 10 == 285.0
    assert math.isclose(ilm(285.0, 150.0) - ilm(150.0, 150.0), 0.220648, abs_tol=5e-7)
    # scenario_influence: base 100, capital without each point [95, 100, 80]
    assert [round((100 - c) / 100, 12) for c in (95.0, 100.0, 80.0)] == [0.05, 0.0, 0.2]
    text = API.read_text(encoding="utf-8")
    for golden in ("0.008013", "0.801285", "0.220648", "97.5", "112.5", "0.15"):
        assert golden in text, golden
