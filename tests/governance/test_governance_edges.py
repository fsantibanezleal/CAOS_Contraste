"""U15-P: the dependency edges (decision W15-8): each edge is what a downstream manifest states in its depends_on (U16-P1b), and the entry graph is what the table says."""
from __future__ import annotations

import json

import gov_support as gs
import pytest


@pytest.fixture(scope="module")
def table():
    """The edge table as the bake reads it: the dependency edges of the manifests' depends_on (U16-P1b), the related links of edges.json."""
    from pipeline.governance import edge_table

    mans = {p.stem: gs.read(f"data/derived/manifests/{p.name}") for p in sorted((gs.DERIVED / "manifests").glob("C[0-9][0-9].json"))}
    return {"edges": edge_table.dependency_edges(mans), "related": json.loads(gs.EDGES.read_text(encoding="utf-8"))["related"], "manifests": mans}


def test_every_edge_is_stated_by_the_downstream_producer_in_its_manifest(table):
    """An edge exists only because the downstream manifest lists a document or a module of the upstream case, with the producer's reason."""
    assert table["edges"]
    for edge in table["edges"]:
        listed = [d for d in table["manifests"][edge["downstream_case"]]["depends_on"] if d["kind"] == edge["kind"]]
        assert listed and all(d["reason"]["en"] in edge["stated_source"] for d in listed if gs_case(d["ref"]) == edge["upstream_case"]), edge
        assert f"data/derived/manifests/{edge['downstream_case']}.json depends_on" in edge["stated_source"]


def gs_case(ref: str) -> str:
    from pipeline.core.manifest import dependency_case

    return dependency_case(ref)


def test_adversarial_a_manifest_without_depends_on_stops_the_edges_naming_it(table):
    from pipeline.governance import edge_table
    from pipeline.governance.readers import BakeError

    mans = {c: dict(m) for c, m in table["manifests"].items()}
    del mans["C18"]["depends_on"]
    with pytest.raises(BakeError, match=r"manifests/C18\.json.*depends_on"):
        edge_table.dependency_edges(mans)


def test_adversarial_a_dependency_of_a_case_on_itself_or_an_unknown_kind_is_refused(table):
    from pipeline.governance import edge_table
    from pipeline.governance.readers import BakeError

    reason = {"en": "x", "es": "y"}
    mans = {"C18": {"depends_on": [{"kind": "code", "ref": "pipeline.cases.c18.fed", "reason": reason}]}}
    with pytest.raises(BakeError, match="itself"):
        edge_table.dependency_edges(mans)
    mans = {"C18": {"depends_on": [{"kind": "page", "ref": "C07/base.json", "reason": reason}]}}
    with pytest.raises(BakeError, match="kind"):
        edge_table.dependency_edges(mans)


def test_adversarial_a_related_link_in_the_direction_of_a_dependency_is_refused(table, tmp_path):
    from pipeline.governance import edge_table
    from pipeline.governance.readers import BakeError, Reader

    bad = json.loads(gs.EDGES.read_text(encoding="utf-8"))
    bad["related"].append({"a_case": "C07", "b_case": "C18", "kind": "method", "source": "planted"})
    target = tmp_path / "data-pipeline/pipeline/governance/edges.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(BakeError, match="never one"):
        edge_table.load_edges(Reader(tmp_path), table["manifests"])
    bad2 = dict(bad, edges=[])
    target.write_text(json.dumps(bad2), encoding="utf-8")
    with pytest.raises(BakeError, match="only the related links"):
        edge_table.load_edges(Reader(tmp_path), table["manifests"])


def test_the_inventory_edges_are_the_table_expanded_to_entries(baked, table):
    inv = baked.inventory
    keys = {e["key"] for e in inv["entries"]}
    by_case: dict[str, list[str]] = {}
    for e in inv["entries"]:
        by_case.setdefault(e["case_id"], []).append(e["key"])
    assert inv["edges"]
    for ed in inv["edges"]:
        assert ed["upstream"] in keys and ed["downstream"] in keys and ed["kind"] in ("document", "code") and ed["stated_source"].strip()
    want = set()
    for e in table["edges"]:
        for d in by_case.get(e["downstream_case"], []):
            want.add((e["upstream_case"], d, e["kind"]))
    got = {(ed["upstream"].split("/")[0], ed["downstream"], ed["kind"]) for ed in inv["edges"]}
    assert got == want
    # the upstream of an expanded edge is the reference entry: the one that holds the manifest's default variant
    for ed in inv["edges"]:
        case = ed["upstream"].split("/")[0]
        man = gs.read(f"data/derived/manifests/{case}.json")
        ent = next(x for x in inv["entries"] if x["key"] == ed["upstream"])
        assert man["default_variant"] in [v["variant_id"] for v in ent["variants"]] or len(by_case[case]) == 1


def test_related_links_are_listed_apart_and_never_drawn_as_dependencies(baked, table):
    inv = baked.inventory
    pairs = {(e["upstream"], e["downstream"]) for e in inv["edges"]}
    assert inv["related"]
    for r in inv["related"]:
        assert (r["a"], r["b"]) not in pairs, "a related link is never drawn as the dependency it relates"
        assert r["a"] in {e["key"] for e in inv["entries"]} and r["source"].strip()


def test_every_entry_depends_on_the_engine_node_and_the_graph_is_layered(baked):
    inv = baked.inventory
    assert inv["engine_node"]["key"] == "riskvalidation" and inv["engine_node"]["version"] == pinned_engine()
    assert all(e["key"] != "riskvalidation" for e in inv["entries"])
    pairs = [(e["upstream"], e["downstream"]) for e in inv["edges"]]
    for e in inv["entries"]:
        up = {u for u, d in pairs if d == e["key"]}
        if up:
            assert e["graph"]["depth"] == 1 + max(next(x for x in inv["entries"] if x["key"] == u)["graph"]["depth"] for u in up)
        else:
            assert e["graph"]["depth"] == 0
        assert e["map"]["generation"] == e["graph"]["depth"]
        assert -1.0 <= e["map"]["x"] <= 1.0 and -1.0 <= e["map"]["y"] <= 1.0


def test_adversarial_an_edge_to_a_case_with_no_inventory_entry_stops_the_bake_naming_the_edge():
    """m4 of the U16-P1 review: an upstream case with no entry (planned or excluded) was dropped without a word."""
    from pipeline.governance import edge_table
    from pipeline.governance.readers import BakeError

    entries = [{"key": "C18/a", "case_id": "C18", "variants": [{"variant_id": "v"}]}]
    tbl = {"edges": [{"upstream_case": "C99", "downstream_case": "C18", "kind": "document", "stated_source": "x"}], "related": []}
    with pytest.raises(BakeError, match=r"C99.*C18"):
        edge_table.expand(tbl, entries, {"C18": "v"})


def test_the_related_link_c14_c16_names_the_treasury_files_c16_shares_with_c14():
    link = [r for r in json.loads(gs.EDGES.read_text(encoding="utf-8"))["related"] if (r["a_case"], r["b_case"]) == ("C14", "C16")]
    assert len(link) == 1 and link[0]["kind"] == "source"
    assert "Treasury" in link[0]["source"] and "FDIC data fetched by C14" not in link[0]["source"]
    assert len(json.loads(gs.EDGES.read_text(encoding="utf-8"))["related"]) == 6


def test_no_dangling_edge_id_is_published_in_the_inputs_or_the_inventory():
    """m1: the edge ids E01 to E15 no longer exist (edges.json dropped them); a basis cites the downstream manifest instead."""
    import re

    for rel in (gs.INPUTS, gs.DERIVED / "governance" / "inventory.json"):
        assert not re.search(r"\(E\d\d\)", rel.read_text(encoding="utf-8")), rel

def pinned_engine() -> str:
    """The riskvalidation release data-pipeline/requirements.txt pins (tests/engine_pin.py reads the same line)."""
    from engine_pin import PYPI_PIN
    from pathlib import Path as _P
    req = (_P(__file__).resolve().parents[2] / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = PYPI_PIN.search(req)
    assert m is not None, "no PyPI pin of riskvalidation in data-pipeline/requirements.txt"
    return m.group("version")
