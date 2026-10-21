"""The dependency edges of the inventory (decision W15-8): read from ``edges.json``, checked against the downstream package, expanded to entries.

An edge is written between cases. ``expand`` turns it into entry edges: the upstream is the reference entry of the upstream case (the entry that holds the
manifest's default variant, else the first fit by key), the downstream is every entry of the downstream case, because every fit runs the same code and
reads the same documents. ``verify_edge`` is the check behind the edge test: a document edge fails when the downstream file stops naming the upstream
document, a code edge when the import line goes away. A related link (a page statement, a shared method, a shared source, a measurement, a conceptual
link) is never an edge.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .readers import BakeError, Reader

EDGES_REL = "data-pipeline/pipeline/governance/edges.json"
KINDS = ("document", "code")
RELATED_KINDS = ("page-statement", "method", "source", "measures", "conceptual")


def load_edges(reader: Reader) -> dict[str, Any]:
    """The edge table, validated: every edge has a kind, a stated source and at least one line to check."""
    table = reader.json(EDGES_REL)
    ids = [e["id"] for e in table["edges"]]
    if len(set(ids)) != len(ids):
        raise BakeError(f"{EDGES_REL}: the edge ids repeat")
    for e in table["edges"]:
        if e["kind"] not in KINDS:
            raise BakeError(f"{EDGES_REL}: edge {e['id']} has the kind {e['kind']!r}, expected one of {KINDS}")
        if not e["stated_source"].strip() or not e["verify"]:
            raise BakeError(f"{EDGES_REL}: edge {e['id']} has no stated source or nothing to verify")
        if e["upstream_case"] == e["downstream_case"]:
            raise BakeError(f"{EDGES_REL}: edge {e['id']} joins a case to itself")
    dep = {(e["upstream_case"], e["downstream_case"]) for e in table["edges"]}
    for r in table["related"]:
        if r["kind"] not in RELATED_KINDS:
            raise BakeError(f"{EDGES_REL}: a related link has the kind {r['kind']!r}, expected one of {RELATED_KINDS}")
        if (r["a_case"], r["b_case"]) in dep:
            raise BakeError(f"{EDGES_REL}: the related link {r['a_case']} to {r['b_case']} is also a dependency edge in the same direction: a related link is never one")
    return table


def verify_edge(edge: dict[str, Any], root: Path | str) -> list[str]:
    """The problems of one edge against the downstream package under ``root`` (empty when the edge still holds)."""
    problems = []
    for v in edge["verify"]:
        path = Path(root) / v["file"]
        if not path.is_file():
            problems.append(f"{edge['id']}: {v['file']} is absent, so {edge['upstream_case']} to {edge['downstream_case']} ({edge['kind']}) is not stated")
        elif not any(v["needle"] in line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")):
            problems.append(f"{edge['id']}: {v['file']} no longer contains {v['needle']!r} outside a comment, so {edge['upstream_case']} to {edge['downstream_case']} "
                            f"({edge['kind']}) is not stated")
    return problems


def reference_entry(case_id: str, entries_of_case: list[dict[str, Any]], default_variant: str) -> str:
    """The key of the entry that stands for the case as an upstream: the one that holds the manifest's default variant, else the first by key."""
    for e in sorted(entries_of_case, key=lambda x: x["key"]):
        if default_variant in [v["variant_id"] for v in e["variants"]]:
            return e["key"]
    return sorted(entries_of_case, key=lambda x: x["key"])[0]["key"]


def expand(table: dict[str, Any], entries: list[dict[str, Any]], defaults: dict[str, str]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """(the entry edges, the entry related links). A case with no entry contributes no edge (its documents are not in the inventory)."""
    by_case: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        by_case.setdefault(e["case_id"], []).append(e)
    edges = []
    for ed in table["edges"]:
        up_entries = by_case.get(ed["upstream_case"])
        if not up_entries:
            continue
        up = reference_entry(ed["upstream_case"], up_entries, defaults[ed["upstream_case"]])
        for d in sorted(by_case.get(ed["downstream_case"], []), key=lambda x: x["key"]):
            edges.append({"upstream": up, "downstream": d["key"], "kind": ed["kind"], "stated_source": ed["stated_source"]})
    related = []
    for r in table["related"]:
        if r["a_case"] in by_case and r["b_case"] in by_case:
            related.append({"a": reference_entry(r["a_case"], by_case[r["a_case"]], defaults[r["a_case"]]),
                            "b": reference_entry(r["b_case"], by_case[r["b_case"]], defaults[r["b_case"]]), "kind": r["kind"], "source": r["source"]})
    edges.sort(key=lambda x: (x["upstream"], x["downstream"], x["kind"]))
    related.sort(key=lambda x: (x["a"], x["b"], x["kind"]))
    return edges, related
