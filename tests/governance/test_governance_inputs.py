"""U15-P: the inputs of the bake (inputs.json, edges.json) carry their basis and tag; C02 and C20 are scored under W15-18 with a document pointer for
each input; the premises the scores state are true of the committed documents.
"""
from __future__ import annotations

import json
import re

import gov_support as gs
import pytest

BUILT = ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12", "C13", "C14", "C15", "C16", "C17", "C18", "C20", "C21", "C22"]
#: the exposure shares of A D2 3.2 (the U15-S tests hold the same table), 4 decimals
SHARES = {"C01": 0.0531, "C03": 0.2162, "C04": 0.3243, "C05": 0.3243, "C06": 1.0, "C07": 1.0, "C08": 0.2162, "C09": 0.0531, "C10": 0.7084,
          "C11": 0.1713, "C13": 0.1713, "C14": 1.0, "C15": 1.0, "C16": 1.0, "C17": 0.1203, "C18": 1.0, "C21": 0.3456}


@pytest.fixture(scope="module")
def inputs():
    return json.loads(gs.INPUTS.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def edges():
    return json.loads(gs.EDGES.read_text(encoding="utf-8"))


def manifest(case):
    return gs.read(f"data/derived/manifests/{case}.json")


def test_inputs_cover_every_built_case_with_a_basis_and_a_tag_for_each_input(inputs):
    assert sorted(inputs["cases"]) == BUILT
    for case, c in inputs["cases"].items():
        t = c["tier"]
        exp, reg, dec = t["exposure"], t["regulatory_use"], t["decision_criticality"]
        for name, block in (("exposure", exp), ("regulatory_use", reg), ("decision_criticality", dec)):
            assert block["tag"] in ("doc", "convention"), (case, name)
            assert block["basis"].strip(), (case, name)
        assert reg["graded"] <= reg["literal"], case
        assert [f["id"] for f in t["factors"]] == [f"F{i}" for i in range(1, 7)], case
        for f in t["factors"]:
            assert f["tag"] in ("doc", "convention") and f["basis"].strip() and f["pointer"], (case, f["id"])
            assert f["score"] in (1, 2, 3, 4), (case, f["id"])
        assert c["owner_role"].endswith("(synthetic role)"), case
    assert inputs["release"]["tag"] == "convention" and inputs["as_of"]["tag"] == "convention"
    assert inputs["as_of"]["basis"]["en"].strip() and inputs["as_of"]["basis"]["es"].strip()


def test_c02_and_c20_are_scored_by_the_same_rubric_with_a_document_pointer_for_each_input(inputs):
    """W15-18: each input gets its document pointer and its tag; an input with no committed basis would be missing with its reason, never guessed."""
    for case in ("C02", "C20"):
        t = inputs["cases"][case]["tier"]
        assert t["regulatory_use"]["pointer"] and t["decision_criticality"]["pointer"], case
        assert t["exposure"]["pointer"], case
        for f in t["factors"]:
            assert f["pointer"], (case, f["id"])
        for name in ("regulatory_use", "decision_criticality"):
            assert t[name]["tag"] in ("doc", "convention")


def _resolve(path: str, pointer: str | None, case: str):
    """A pointer is ``<file>#/json/pointer`` (resolved in the document), ``<file>#heading-slug`` (a heading of a page) or a file path."""
    path = path.replace("{manifest}", f"data/derived/manifests/{case}.json")
    return path, pointer


def test_every_input_pointer_resolves_in_the_committed_documents(inputs):
    from pipeline.governance.readers import resolve

    for case, c in inputs["cases"].items():
        man = manifest(case)
        models = sorted((gs.DERIVED / case).glob("models-*.json"))
        default = man["default_variant"]
        pointers = []
        t = c["tier"]
        pointers += [t["exposure"].get("pointer"), t["regulatory_use"]["pointer"], t["decision_criticality"]["pointer"]]
        pointers += [f["pointer"] for f in t["factors"]]
        for ptr in filter(None, pointers):
            for m in models:
                p = (ptr.replace("{manifest}", f"data/derived/manifests/{case}.json").replace("{models}", f"data/derived/{case}/{m.name}")
                     .replace("{default}", f"data/derived/{case}/{default}.json"))
                path, _, frag = p.partition("#")
                assert (gs.ROOT / path).is_file(), (case, p)
                if path.endswith(".json") and frag.startswith("/"):
                    resolve(gs.read(path), frag)
                elif frag:
                    text = (gs.ROOT / path).read_text(encoding="utf-8")
                    assert re.search(rf"(?mi)^#+\s+{re.escape(frag.replace('-', ' '))}\s*$", text), (case, p)
        assert (gs.ROOT / c["developer"]).exists(), (case, c["developer"])


def test_the_exposure_shares_are_the_documents_values(inputs, baked):
    for e in baked.inventory["entries"]:
        share = e["tier_block"]["materiality"]["exposure"]["share"]
        want = SHARES.get(e["case_id"])
        if e["case_id"] in ("C12", "C22"):
            assert share is None
        elif e["case_id"] in ("C02", "C20"):
            assert share == {"C02": 0.2162, "C20": 0.0531}[e["case_id"]]
        else:
            assert share == want, e["key"]


def test_the_scores_state_premises_that_the_documents_confirm(inputs):
    """F2 is 2 for a case that reads an outside source and 1 for generated data; F6 is 1 where seed, versions and file hashes are in every document."""
    for case, c in inputs["cases"].items():
        f = {x["id"]: x for x in c["tier"]["factors"]}
        sources = manifest(case)["sources"]
        if f["F2"]["score"] == 2:
            assert sources, case
        else:
            assert (not sources) or case == "C22", case
        for p in (gs.DERIVED / case).glob("*.json"):
            d = json.loads(p.read_text(encoding="utf-8"))
            prov = d.get("provenance")
            assert prov and prov["seed"] is not None and prov["code_version"] and prov["riskvalidation_version"], p.name
            for inp in prov["inputs"]:
                assert all(len(x["sha256"]) == 64 for x in inp["files"]), p.name


def test_f5_is_the_feeder_count_of_the_addendum_and_c18_equals_its_document_feeders(inputs, edges):
    """A D2 3.3: C18 reads four cases (document edges E01 to E04), C15 one (C07, whose edge E06 is a code import: the addendum counts it); the rest none."""
    feeders: dict[str, set[str]] = {}
    for e in edges["edges"]:
        if e["kind"] == "document":
            feeders.setdefault(e["downstream_case"], set()).add(e["upstream_case"])
    assert len(feeders["C18"]) == 4
    for case, c in inputs["cases"].items():
        want = {"C15": 2, "C18": 4}.get(case, 1)
        assert {x["id"]: x for x in c["tier"]["factors"]}["F5"]["score"] == want, case


def test_the_edge_table_lists_dependencies_and_keeps_the_related_links_apart(edges):
    kinds = {e["kind"] for e in edges["edges"]}
    assert kinds == {"document", "code"}
    assert len({e["id"] for e in edges["edges"]}) == len(edges["edges"])
    for e in edges["edges"]:
        assert e["stated_source"].strip() and e["verify"], e["id"]
        assert e["upstream_case"] != e["downstream_case"]
    assert {r["kind"] for r in edges["related"]} <= {"page-statement", "method", "source", "measures", "conceptual"}
    dep = {(e["upstream_case"], e["downstream_case"]) for e in edges["edges"]}
    for r in edges["related"]:
        assert (r["a_case"], r["b_case"]) not in dep, "a related link is never a dependency in its own direction"


def test_the_addendum_edges_are_all_in_the_table(edges):
    dep = {(e["upstream_case"], e["downstream_case"], e["kind"]) for e in edges["edges"]}
    for want in [("C07", "C18", "document"), ("C11", "C18", "document"), ("C15", "C18", "document"), ("C17", "C18", "document"),
                 ("C10", "C18", "code"), ("C07", "C15", "code"), ("C06", "C03", "code"), ("C06", "C08", "code"), ("C01", "C03", "code"),
                 ("C01", "C04", "code"), ("C01", "C05", "code"), ("C01", "C22", "code"), ("C05", "C04", "code")]:
        assert want in dep, want
    # the two edges the addendum could not state because the cases were planned (W15-18)
    assert ("C01", "C02", "code") in dep and ("C01", "C20", "code") in dep
    # the two edges the brief named that the record does not state are absent
    assert not any(u == "C15" and d == "C16" for u, d, _ in dep)
