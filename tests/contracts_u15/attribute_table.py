"""The JSON pointers the U15-S fixtures cite for the B.2 attributes of the four fixture entries (A D1 of the U15 research addendum).

One place, read by ``extract_sources.py`` (which resolves every pointer against the committed documents and stores the list it verified) and
by ``build_fixtures.py`` (which cites only verified pointers, so a basis never points at a field that is not there). A pointer is
``<repository path>#<JSON pointer>``. Standard library only.
"""
from __future__ import annotations

from typing import Any


def resolve(doc: Any, pointer: str) -> Any:
    """The value at a JSON pointer (``/a/0/b``); raises KeyError when it does not exist."""
    if pointer in ("", "#"):
        return doc
    node = doc
    for raw in pointer.lstrip("#").split("/")[1:]:
        key = raw.replace("~1", "/").replace("~0", "~")
        try:
            node = node[int(key)] if isinstance(node, list) else node[key]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise KeyError(pointer) from exc
    return node


def pointers(case: str, ex: dict) -> dict[str, list[str]]:
    """The pointers per attribute id for one case of the extract (``ex`` is ``extract["cases"][case]``)."""
    m = ex["models_document"]["path"]
    man = ex["manifest"]["path"]
    default = next(v for v in ex["variants"] if v["variant_id"] == ex["default_variant"])["path"]
    n = len(ex["models_document"]["models"])
    out: dict[str, list[str]] = {
        "A01": [f"{m}#/case_id", f"{m}#/fit_id"],
        "A02": [f"{man}#/title"],
        "A03": [f"{m}#/fit_id", f"{m}#/provenance/code_version", f"{m}#/provenance/riskvalidation_version"],
        "A04": [f"{man}#/question"],
        "A05": [f"{m}#/model/{i}/family" for i in range(n)],
        "A06": [f"{m}#/model/{i}/engine" for i in range(n)],
        "A08": [f"{man}#/question"],
        "A14": [f"{man}#/sources", f"{m}#/provenance/generators"],
        "A17": [f"{default}#/outputs", f"{default}#/impact"],
        "A18": [f"{m}#/model/{i}/rung" for i in range(n)],
        "A20": [f"{m}#/model/{i}/rung" for i in range(n)],
        "A34": [f"{m}#/provenance/code_version"],
        "A36": [f"{v['path']}#/tests" for v in ex["variants"]],
        "A37": [f"{v['path']}#/findings" for v in ex["variants"]],
    }
    if case == "C07":
        out["A09"] = [f"{m}#/fit/segments"]
        out["A26"] = [f"{default}#/outputs/ifrs9_detail/overlays_total"]
    if case == "C18":
        out["A09"] = [f"{m}#/fit/class_mapping"]
        out["A13"] = [f"{m}#/model/0/parameters/fit_end_year"]
        out["A16"] = [f"{m}#/fit/marginal_sources"]
        out["A19"] = [f"{m}#/fit/named_parameters"]
    if case == "C01":
        out["A13"] = [f"{m}#/fit/split", f"{m}#/fit/train_rows"]
    return out
