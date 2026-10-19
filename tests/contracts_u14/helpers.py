"""Schema-building helpers shared by build_schemas.py (copied in form from tests/contracts_u12/build_schemas.py)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
BASE = "https://contraste.fasl-work.com/contracts/"
TXT = {"$ref": "../common/text.schema.json"}


def Ob(props: dict, desc: str | None = None) -> dict:
    d: dict = {"type": "object", "additionalProperties": False, "required": list(props), "properties": props}
    if desc:
        d["description"] = desc
    return d


def A(items: dict, minimum: int | None = None, maximum: int | None = None, desc: str | None = None, unique: bool = False) -> dict:
    d: dict = {"type": "array", "items": items}
    if minimum is not None:
        d["minItems"] = minimum
    if maximum is not None:
        d["maxItems"] = maximum
    if unique:
        d["uniqueItems"] = True
    if desc:
        d["description"] = desc
    return d


def R(name: str) -> dict:
    return {"$ref": f"#/$defs/{name}"}


def nullable(x: dict, desc: str | None = None) -> dict:
    d: dict = {"anyOf": [x, {"type": "null"}]}
    if desc:
        d["description"] = desc
    return d


def S(desc: str | None = None, **kw) -> dict:
    d: dict = {"type": "string", "minLength": 1, **kw}
    if desc:
        d["description"] = desc
    return d


def Int(minimum: int | None = None, maximum: int | None = None, desc: str | None = None) -> dict:
    d: dict = {"type": "integer"}
    if minimum is not None:
        d["minimum"] = minimum
    if maximum is not None:
        d["maximum"] = maximum
    if desc:
        d["description"] = desc
    return d


def N(desc: str | None = None, **kw) -> dict:
    d: dict = {"type": "number", **kw}
    if desc:
        d["description"] = desc
    return d


def E(*values) -> dict:
    return {"enum": list(values)}


def C(value, desc: str | None = None) -> dict:
    d: dict = {"const": value}
    if desc:
        d["description"] = desc
    return d


B = {"type": "boolean"}
UNIT = N("A value in [0, 1].", minimum=0, maximum=1)
NONNEG = N(minimum=0)


def one_of(ob: dict, *alternatives: dict) -> dict:
    ob["oneOf"] = [{"properties": a} for a in alternatives]
    return ob


def reachable(root: str, defs: dict) -> dict:
    seen: dict = {}
    todo = [root]

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str) and v.startswith("#/$defs/"):
                    todo.append(v[len("#/$defs/"):])
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen[name] = defs[name]
        walk(defs[name])
    return {k: seen[k] for k in defs if k in seen}


def contains_each(arr: dict, key: str, values: list) -> dict:
    """The array holds each value of ``key`` exactly once (maxItems = number of values, one ``contains`` per value)."""
    arr["minItems"] = arr["maxItems"] = len(values)
    arr["allOf"] = [{"contains": {"properties": {key: {"const": v}}, "required": [key]}} for v in values]
    return arr


# A not_evaluated test row carries no number and states its reason (engine contract conventions).
NOT_EVALUATED_RULE = {
    "properties": {"tests": {"items": {
        "if": {"properties": {"light": {"const": "not_evaluated"}}, "required": ["light"]},
        "then": {"properties": {"statistic": {"type": "null"}, "p_value": {"type": "null"}, "metric": {"type": "null"},
                                "notes": {"type": "string", "minLength": 1}}},
    }}},
}


def write(case: str, name: str, doc: dict) -> None:
    path = SCHEMAS / case / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")


def variant_schema(case: str, ref: str, kind: str, title: str, desc: str, root: str, defs: dict, extra_rules: list[dict]) -> None:
    cid = case.upper()
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}{case}/{ref}.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/variant-envelope.schema.json"},
            {"properties": {"case_id": {"const": cid},
                            "outputs": {"$ref": f"#/$defs/{root}", "properties": {"kind": {"const": kind}}}},
             "required": ["case_id", "outputs"]},
            NOT_EVALUATED_RULE,
            *extra_rules,
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write(case, f"{ref}.schema.json", doc)


def models_schema(case: str, title: str, desc: str, root: str, defs: dict) -> None:
    cid = case.upper()
    doc = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{BASE}{case}/models.schema.json",
        "title": title,
        "description": desc,
        "allOf": [
            {"$ref": "../common/models-envelope.schema.json"},
            {"properties": {"case_id": {"const": cid}, "fit": {"$ref": f"#/$defs/{root}"}}, "required": ["case_id", "fit"]},
        ],
        "unevaluatedProperties": False,
        "$defs": reachable(root, defs),
    }
    write(case, "models.schema.json", doc)
