"""Generate the data-contracts chapter of the technical report from ``docs/contracts/catalog.md`` and the schema files:
one subsection per catalog row, labelled ``sec:contract-<id>`` (the label ``coverage.json`` maps the row to), with its
purpose, version, producer, consumers, tests and missing-data behaviour stated from the row, and a table of the fields of
its schema (name, JSON type, constraint, description). Nothing is typed by hand: a new catalog row or a changed schema
changes the chapter at the next run.

    python manuscripts/contraste-technical-report/tables/make_contracts.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

ROOT = figkit.ROOT
CATALOG = ROOT / "docs" / "contracts" / "catalog.md"
SCHEMAS = ROOT / "docs" / "contracts" / "schemas"
OUT = HERE.parent / "chapters" / "contracts-generated.tex"
COLUMNS = ("id", "version", "owner", "schema file", "example", "documents", "producer test", "consumer test",
           "missing-data behavior", "provider", "model io", "swap test", "status")

GROUPS = [
    ("common", "Shared documents: the inventory, the manifests, the readiness and the envelopes"),
    ("contract", "Ingestion contracts: the eight input families"),
    ("api", "The API document"),
]


def catalog_rows() -> list[dict[str, str]]:
    """The rows of the table under ``## Contracts`` (the history tables further down are not contracts)."""
    text = CATALOG.read_text(encoding="utf-8")
    start = text.index("## Contracts")
    end = text.find("\n## ", start + 1)
    body = text[start:end if end != -1 else len(text)]
    rows = []
    for line in body.splitlines():
        if not line.startswith("| ") or line.startswith("| id "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS) or set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def load_schema(rel: str) -> dict | None:
    path = ROOT / rel
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def collect(schema: dict, base: pathlib.Path, seen: set[str] | None = None) -> dict[str, dict]:
    """The top-level properties of a schema, those of the files its ``allOf`` references included."""
    seen = seen or set()
    props: dict[str, dict] = dict(schema.get("properties", {}))
    for part in schema.get("allOf", []):
        ref = part.get("$ref")
        if ref and not ref.startswith("#"):
            target = ref.split("#")[0]
            name = target.rsplit("/", 1)[-1]
            hits = list(SCHEMAS.rglob(name))
            if hits and str(hits[0]) not in seen:
                seen.add(str(hits[0]))
                inner = json.loads(hits[0].read_text(encoding="utf-8"))
                for k, v in collect(inner, hits[0].parent, seen).items():
                    props.setdefault(k, v)
        for k, v in part.get("properties", {}).items():
            # the case's own part narrows what the envelope declares (its outputs point at the case's $defs)
            props[k] = {**props.get(k, {}), **v} if isinstance(v, dict) else v
    return props


def resolve(spec: dict, schema: dict) -> dict:
    """Follow a local ``#/$defs/...`` reference (and one level of ``allOf``) to the object it names."""
    ref = spec.get("$ref", "")
    if ref.startswith("#/"):
        node: object = schema
        for part in ref[2:].split("/"):
            node = node.get(part, {}) if isinstance(node, dict) else {}
        return node if isinstance(node, dict) else spec
    for part in spec.get("allOf", []):
        if "properties" in part:
            return part
    return spec


def expand(props: dict[str, dict], schema: dict) -> list[tuple[str, dict]]:
    """The top-level fields, and under ``outputs`` its own fields, which carry what the document means."""
    rows: list[tuple[str, dict]] = []
    for name, spec in props.items():
        if not isinstance(spec, dict):
            continue
        rows.append((name, spec))
        if name == "outputs":
            inner = resolve(spec, schema)
            for sub, sspec in list(inner.get("properties", {}).items())[:40]:
                if isinstance(sspec, dict):
                    rows.append((f"outputs.{sub}", sspec))
    return rows


def kind_of(spec: dict) -> str:
    if "$ref" in spec:
        return "object (" + spec["$ref"].rsplit("/", 1)[-1].replace(".schema.json", "") + ")"
    t = spec.get("type")
    if isinstance(t, list):
        t = " or ".join(t)
    if t == "array":
        items = spec.get("items", {}) if isinstance(spec.get("items"), dict) else {}
        inner = items.get("type") or (items.get("$ref", "").rsplit("/", 1)[-1] or "item")
        return f"array of {inner}"
    if t is None and "const" in spec:
        return "constant"
    if t is None and ("oneOf" in spec or "anyOf" in spec):
        return "one of " + str(len(spec.get("oneOf", spec.get("anyOf", []))))
    return t or "any"


def constraint_of(spec: dict) -> str:
    bits = []
    if "const" in spec:
        bits.append(f"= {spec['const']}")
    if "enum" in spec:
        e = spec["enum"]
        bits.append("one of " + ", ".join(map(str, e[:6])) + (" ..." if len(e) > 6 else ""))
    lo = spec.get("minimum", spec.get("exclusiveMinimum"))
    hi = spec.get("maximum", spec.get("exclusiveMaximum"))
    if lo is not None or hi is not None:
        left = "(" if "exclusiveMinimum" in spec else "["
        right = ")" if "exclusiveMaximum" in spec else "]"
        bits.append(f"{left}{'' if lo is None else lo}, {'' if hi is None else hi}{right}")
    if "pattern" in spec:
        bits.append("pattern")
    if "minItems" in spec:
        bits.append(f"at least {spec['minItems']} items")
    return "; ".join(bits) or "-"


def sentence(text: str) -> str:
    """A catalog cell as prose: backticks become typewriter text, the rest is escaped."""
    parts = re.split(r"(`[^`]*`)", text)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append("\\texttt{" + figkit.tex_escape(p[1:-1]) + "}")
        else:
            out.append(figkit.tex_escape(p))
    return "".join(out).strip()


def tests_text(cell: str) -> str:
    if cell in ("", "-"):
        return "none named"
    return ", ".join("\\texttt{" + figkit.tex_escape(t.strip()) + "}" for t in cell.split(",") if t.strip())


def group_of(row: dict[str, str]) -> str:
    schema = row["schema file"]
    m = re.search(r"schemas/(c\d\d)/", schema)
    if m:
        return m.group(1)
    if "contract" in row["id"]:
        return "contract"
    if schema.endswith("openapi.json") or row["id"] == "api":
        return "api"
    return "common"


def subsection(row: dict[str, str]) -> str:
    cid = row["id"]
    schema = load_schema(row["schema file"]) if row["schema file"].endswith(".schema.json") else None
    title = schema.get("title") if schema else None
    desc = schema.get("description", "") if schema else ""
    lines = [f"\\subsection{{\\texttt{{{figkit.tex_escape(cid)}}}" + (f": {figkit.tex_escape(title)}" if title else "") + "}",
             f"\\label{{sec:contract-{cid}}}", ""]
    para = []
    if desc:
        para.append(sentence(desc.rstrip(".")) + ".")
    para.append(f"The contract is at version {figkit.tex_escape(row['version'])} and its status in the catalog is "
                f"\\emph{{{figkit.tex_escape(row['status'])}}}.")
    para.append(f"Its producer is \\texttt{{{figkit.tex_escape(row['owner'])}}}, and its schema file is "
                f"\\texttt{{{figkit.tex_escape(row['schema file'])}}}" +
                (f"; the committed documents it governs are {sentence(row['documents'])}." if row["documents"] not in ("", "-")
                 else "; it governs no committed document of its own and is composed by the schemas that reference it."))
    para.append(f"The producer side is tested by {tests_text(row['producer test'])}, and the consumer side, the web "
                f"application that reads the document, by {tests_text(row['consumer test'])}.")
    if row["model io"] not in ("", "-"):
        para.append(f"As a model input or output it is described as follows: {sentence(row['model io'])}.")
    para.append(f"When the data is missing or out of date the behaviour is fixed in advance: {sentence(row['missing-data behavior'])}.")
    if row["provider"] not in ("", "-"):
        para.append(f"Its provider, the document served before and besides the real one, is {sentence(row['provider'])}.")
    if row["swap test"] not in ("", "-"):
        para.append(f"The test that every document matches exactly one schema is {tests_text(row['swap test'])}.")
    lines.append(" ".join(para))
    lines.append("")
    if schema:
        props = collect(schema, (ROOT / row["schema file"]).parent)
        if props:
            lines += ["{\\small", "\\begin{longtable}{p{0.22\\textwidth}p{0.17\\textwidth}p{0.15\\textwidth}p{0.36\\textwidth}}",
                      f"\\caption{{The top-level fields of the contract \\texttt{{{figkit.tex_escape(cid)}}}: the name, the JSON "
                      f"type, the constraint the schema states and its description, as the schema file holds them.}}"
                      f"\\label{{tab:contract-{cid}}}\\\\",
                      "\\toprule Field & Type & Constraint & Description \\\\ \\midrule \\endfirsthead",
                      "\\toprule Field & Type & Constraint & Description \\\\ \\midrule \\endhead"]
            for name, spec in expand(props, schema):
                d = spec.get("description", "") or resolve(spec, schema).get("description", "")
                d = (d[:220] + " ...") if len(d) > 220 else d
                lines.append(f"\\texttt{{{figkit.tex_escape(name)}}} & {figkit.tex_escape(kind_of(spec))} & "
                             f"{figkit.tex_escape(constraint_of(spec))} & {sentence(d) or '-'} \\\\")
            lines += ["\\bottomrule", "\\end{longtable}", "}", ""]
    return "\n".join(lines)


def main() -> None:
    rows = catalog_rows()
    by_group: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        by_group.setdefault(group_of(r), []).append(r)
    out = ["% Generated by tables/make_contracts.py from docs/contracts/catalog.md and the schema files; do not edit.", ""]
    names = dict(GROUPS)
    order = [g for g, _ in GROUPS] + sorted(g for g in by_group if g not in names)
    for g in order:
        if g not in by_group:
            continue
        head = names.get(g, f"Case {g.upper()}")
        out += [f"\\section{{{head}}}", f"\\label{{sec:contracts-{g}}}", ""]
        out += [subsection(r) for r in by_group[g]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"{len(rows)} contracts -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
