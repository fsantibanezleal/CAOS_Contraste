"""U15-P: the dependency edges (decision W15-8): each edge is checked against the downstream package, and the entry graph is what the table says."""
from __future__ import annotations

import json
import shutil

import gov_support as gs
import pytest


@pytest.fixture(scope="module")
def table():
    return json.loads(gs.EDGES.read_text(encoding="utf-8"))


def test_every_edge_is_still_stated_in_the_downstream_package(table):
    """A document edge fails when the downstream package stops naming the upstream document, a code edge when the import line goes away."""
    from pipeline.governance import edge_table

    for edge in table["edges"]:
        assert edge_table.verify_edge(edge, gs.ROOT) == [], edge["id"]


def test_adversarial_an_edge_whose_downstream_file_stops_naming_the_upstream_fails_the_check(table, tmp_path):
    from pipeline.governance import edge_table

    edge = next(e for e in table["edges"] if e["id"] == "E01")
    for v in edge["verify"]:
        target = tmp_path / v["file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(gs.ROOT / v["file"], target)
    assert edge_table.verify_edge(edge, tmp_path) == []
    f = tmp_path / edge["verify"][0]["file"]
    f.write_text(f.read_text(encoding="utf-8").replace(edge["verify"][0]["needle"], "removed"), encoding="utf-8")
    found = edge_table.verify_edge(edge, tmp_path)
    assert found and edge["verify"][0]["needle"] in found[0]
    f.unlink()
    assert "absent" in edge_table.verify_edge(edge, tmp_path)[0]


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
    assert inv["engine_node"]["key"] == "riskvalidation" and inv["engine_node"]["version"] == "0.9.0"
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
