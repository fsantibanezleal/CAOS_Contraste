"""The dependency edges of the inventory (decision W15-8): built from the ``depends_on`` list of every case manifest, checked, expanded to entries.

A case producer states what it reads of other cases in its manifest (``core.manifest.derive_depends_on``, BL-086): the committed documents it opens (kind
``document``) and the product modules it imports (kind ``code``). The bake groups a manifest's list by upstream case and kind into an edge between cases.
``expand`` turns it into entry edges: the upstream is the reference entry of the upstream case (the entry that holds the manifest's default variant, else
the first fit by key), the downstream is every entry of the downstream case, because every fit runs the same code and reads the same documents. Every entry
also depends on the engine (implicit, W15-8), and a manifest without ``depends_on`` stops the bake naming it.

``edges.json`` keeps only what no producer can state: the related links (a page statement, a shared method, a shared source, a measurement, a conceptual
link). A related link is never an edge.
"""
from __future__ import annotations

from typing import Any

from ..core.manifest import DEPENDENCY_KINDS, dependency_case
from .readers import BakeError, Reader

EDGES_REL = "data-pipeline/pipeline/governance/edges.json"
KINDS = DEPENDENCY_KINDS
RELATED_KINDS = ("page-statement", "method", "source", "measures", "conceptual")


def dependency_edges(manifests: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    """The edges between cases, from the ``depends_on`` of each manifest: ``{upstream_case, downstream_case, kind, stated_source}``, sorted.

    ``stated_source`` is what the downstream producer states: the manifest that holds the list, then each reference with its reason.
    """
    edges = []
    for cid in sorted(manifests):
        rel = f"data/derived/manifests/{cid}.json"
        if "depends_on" not in manifests[cid]:
            raise BakeError(f"{rel}: the manifest states no depends_on (case-manifest 2.0.0 requires it, empty when the case reads nothing of another case)")
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for d in manifests[cid]["depends_on"]:
            if d["kind"] not in KINDS:
                raise BakeError(f"{rel}: depends_on {d['ref']!r} has the kind {d['kind']!r}, expected one of {KINDS}")
            try:
                up = dependency_case(d["ref"])
            except ValueError as exc:
                raise BakeError(f"{rel}: {exc}") from exc
            if up == cid:
                raise BakeError(f"{rel}: depends_on {d['ref']!r} joins the case to itself")
            grouped.setdefault((up, d["kind"]), []).append(d)
        for (up, kind), items in sorted(grouped.items()):
            said = "; ".join(f"{d['ref']}: {d['reason']['en']}" for d in sorted(items, key=lambda x: x["ref"]))
            edges.append({"upstream_case": up, "downstream_case": cid, "kind": kind, "stated_source": f"{rel} depends_on (stated by the {cid} producer): {said}"})
    return edges


def load_edges(reader: Reader, manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The edge table: the dependency edges of the manifests and the related links of ``edges.json``, validated."""
    table = reader.json(EDGES_REL)
    if set(table) != {"schema", "description", "tag", "related"}:
        raise BakeError(f"{EDGES_REL}: holds {sorted(table)}; only the related links stay here, the dependencies are the manifests' depends_on")
    edges = dependency_edges(manifests)
    dep = {(e["upstream_case"], e["downstream_case"]) for e in edges}
    for r in table["related"]:
        if r["kind"] not in RELATED_KINDS:
            raise BakeError(f"{EDGES_REL}: a related link has the kind {r['kind']!r}, expected one of {RELATED_KINDS}")
        if (r["a_case"], r["b_case"]) in dep:
            raise BakeError(f"{EDGES_REL}: the related link {r['a_case']} to {r['b_case']} is also a dependency edge in the same direction: a related link is never one")
    return {"edges": edges, "related": table["related"]}


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
