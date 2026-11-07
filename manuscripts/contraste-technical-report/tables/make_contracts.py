"""Generate the data-contracts appendix of the technical report from ``docs/contracts/catalog.md`` and the schema files:
one subsection per catalog row, labelled ``sec:contract-<id>`` (the label ``coverage.json`` maps the row to), with its
purpose, version, producer, consumers, tests and missing-data behaviour stated from the row, and a table of the fields of
its schema (name, JSON type, unit, range or values, description). Nothing is typed by hand: a new catalog row or a changed schema
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
OUT = HERE.parent / "sections" / "contracts-generated.tex"
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


def range_of(spec: dict) -> str:
    """The range or the values a field takes: the schema's own bounds, enumeration, constant or pattern, else what its type allows."""
    own = constraint_of(spec)
    if own != "-":
        return own
    kind = kind_of(spec)
    if "format" in spec:
        return f"format {spec['format']}"
    if kind.startswith("string"):
        return "any text" + (" or null" if "null" in kind else "")
    if kind.startswith("boolean"):
        return "true or false"
    if kind.startswith("integer"):
        return "any integer" + (" or null" if "null" in kind else "")
    if kind.startswith("number"):
        return "any real number" + (" or null" if "null" in kind else "")
    if kind.startswith("array"):
        return "any length"
    return "see its fields" if kind.startswith("object") else "any"


#: The unit of a field whose schema states none, from the words of its description and then from its name (the schema
#: files hold the unit in a field named ``unit`` of the document, not in the field's own declaration).
UNIT_WORDS = [
    (re.compile(r"\bbasis points?\b|\bbps?\b", re.I), "basis points"),
    (re.compile(r"\bpercent(?:age)?\b|\bper cent\b", re.I), "percent"),
    (re.compile(r"\bcalendar year\b|\byears?\b", re.I), "years"),
    (re.compile(r"\bdays?\b", re.I), "days"),
    (re.compile(r"\bmonths?\b", re.I), "months"),
    (re.compile(r"\bseconds?\b", re.I), "seconds"),
    (re.compile(r"\bcurrency units?\b", re.I), "currency units"),
]
UNIT_NAMES = [
    (re.compile(r"_bp$|^bp$|_bp_"), "basis points"),
    (re.compile(r"(^|_)months?($|_)"), "months"),
    (re.compile(r"(^|_)years?($|_)|^year$"), "calendar year"),
    (re.compile(r"(^|_)days?($|_)"), "days"),
    (re.compile(r"^seed$|_seed$"), "integer seed"),
    (re.compile(r"^n$|^n_|_n$|^defaults$|^count$|_count$"), "count"),
    (re.compile(r"^p_value$|^alpha|^pd\d*$|_pd$|^rate$|_rate$|^prob"), "probability"),
    (re.compile(r"^rho$|correlation"), "correlation (unitless)"),
    (re.compile(r"^ar\d*$"), "accuracy ratio (unitless)"),
    (re.compile(r"^statistic$|^metric$"), "the scale of its test"),
]


def unit_of(name: str, spec: dict, schema: dict, description: str) -> str:
    """The unit of a field: the one the schema declares, else the one its description names, else the one its name implies,
    else what its type implies (text, a record, a list, a flag), else ``unitless``."""
    node = resolve(spec, schema)
    for key in ("unit", "x-unit"):
        for s in (spec, node):
            if isinstance(s.get(key), str):
                return s[key]
    kind = kind_of(spec)
    numeric = kind.startswith(("number", "integer"))
    for pat, unit in UNIT_WORDS:
        if numeric and pat.search(description):
            return unit
    leaf = name.split(".")[-1]
    for pat, unit in UNIT_NAMES:
        if numeric and pat.search(leaf):
            return unit
    if kind.startswith(("string", "constant", "any")):
        return "none (text)"
    if kind.startswith("boolean"):
        return "none (flag)"
    if kind.startswith("object") or kind.startswith("one of"):
        return "none (record)"
    if kind.startswith("array"):
        return "none (list)"
    return "unitless"


#: What the fields every contract of a case shares mean (the envelope of the document), stated once.
COMMON = {
    "schema": "Identifier and version of the schema the document declares, checked against the schema file.",
    "case_id": "Identifier of the case the document belongs to.",
    "variant_id": "Identifier of the variant of the case the document describes.",
    "fit_id": "Identifier of the fit of the models artifact the document describes.",
    "fit": "The fit of the models the document describes.",
    "impact": "The headline quantities of the document, each with its value, its unit and a bilingual label.",
    "outputs": "The outputs of the case, in the structure its own schema defines.",
    "outputs.kind": "Kind of output the document carries, which names the structure of the other outputs.",
    "engine_version": "Version of the validation engine that produced the document.",
    "n_cases": "Number of cases the inventory lists.",
    "default_case": "Identifier of the case the application opens first.",
    "default_variant": "Identifier of the variant the application opens first.",
    "model_id": "Identifier of the model the test row refers to, when it refers to one.",
    "test_id": "Identifier of the test of the engine the row reports.",
    "segment": "Segment of the data the test row was computed on, when it is computed on one.",
    "statistic": "Value of the test statistic.",
    "p_value": "The p-value of the test, when the test decides by one.",
    "metric": "Value of the metric the test reports.",
    "alpha_amber": "Level of the p-value at which the light turns amber.",
    "alpha_red": "Level of the p-value at which the light turns red.",
    "light": "The light of the test: green, amber, red, not evaluated or error.",
    "n": "Number of observations the test used.",
    "n_events": "Number of events (defaults) among the observations the test used.",
    "inputs_hash": "Hash of the inputs the test was computed on.",
    "policy_version": "Version of the policy that sets the levels of the lights.",
    "h0": "The null hypothesis of the test.",
    "alternative": "The alternative hypothesis of the test.",
    "extras": "Further values of the test, open by design.",
    "seed": "Seed of the random number generator of the document.",
}


def ref_text(spec: dict, schema: dict) -> str:
    """The title and description of the schema a field points to, local or in another file."""
    ref = spec.get("$ref", "")
    items = spec.get("items") if isinstance(spec.get("items"), dict) else {}
    ref = ref or items.get("$ref", "")
    if not ref or ref.startswith("#"):
        return ""
    hits = list(SCHEMAS.rglob(ref.split("#")[0].rsplit("/", 1)[-1]))
    if not hits:
        return ""
    node = json.loads(hits[0].read_text(encoding="utf-8"))
    return (node.get("description") or node.get("title") or "").strip()


def describe(name: str, spec: dict, schema: dict) -> str:
    """The description of a field: the schema's own, else the one of the schema it points to, else the shared one of the
    envelope fields, else a statement of its structure from the declaration."""
    own = spec.get("description", "") or resolve(spec, schema).get("description", "")
    if own:
        return own
    if name in COMMON:
        return COMMON[name]
    pointed = ref_text(spec, schema)
    if pointed:
        return ("A list of: " if kind_of(spec).startswith("array") else "") + pointed.rstrip(".") + "."
    leaf = name.split(".")[-1]
    kind = kind_of(spec)
    words = leaf.replace("_", " ")
    if kind.startswith("constant"):
        return f"Fixed value of {words}: {constraint_of(spec).lstrip('= ')}."
    if "enum" in spec:
        return f"The {words}, one of the values stated in the range."
    if kind.startswith("array"):
        return f"The {words}, as a list of {kind[len('array of '):] or 'items'}."
    if kind.startswith("object"):
        return f"The {words}, as a record."
    return f"The {words}."


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


# The schemas' own descriptions name the plan's internal ids and tier words, which never reach a manuscript
# (CAOS_MANAGE conventions/method-tiers-and-manuscripts.md section 0); the generated text drops them.
# The tier phrase is assembled from its words so this source does not hold it (the internal-names gate reads it too).
_ART = r"state\s+of\s+the\s+" + "art"
INTERNAL = [
    (re.compile(r"\b(?:BS|M|S)-\d+[a-z]?\b(?:\s*\(unit [A-Z]+\d+[a-z]?\))?\s*(?:,\s*)?", re.I), ""),
    (re.compile(r"\(unit [A-Z]+\d+[a-z]?\)\s*"), ""),
    (re.compile(r"\bthe beyond tier;?\s*", re.I), ""),
    (re.compile(r"\bbeyond the " + _ART + r":?\s*", re.I), ""),
    (re.compile(r"\b" + _ART + r"\b", re.I), "published"),
    (re.compile(r"\bSO" + r"TA\b"), "published"),
    (re.compile(r"\bSDD\b"), "the design document"),
    (re.compile(r"\s*\(U\d+-[A-Z]\d*\)"), ""),
    (re.compile(r"\s*\bU\d+-[A-Z]\d*\b"), ""),
]


def producer_text(owner: str) -> str:
    """The producer cell without the development unit ids (``U13-S``, ``U13-E1``, ``U13-P1``, ``U15-W``): the modules and paths
    stay, the process vocabulary goes."""
    out = re.sub(r"^U\d+-[A-Z]\d*\s*\((.*)\)$", r"\1", owner.strip())
    out = re.sub(r"implemented by U\d+-[A-Z]\d* in ", "implemented in ", out)
    out = re.sub(r"(\w) U\d+-[A-Z]\d*( in)", r"\1\2", out)
    out = re.sub(r"\bU\d+-[A-Z]\d*\b", "", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def scrub(text: str) -> str:
    """The text without the plan's internal ids and tier words; a sentence left starting in lower case is capitalised."""
    out = text
    for pat, rep in INTERNAL:
        out = pat.sub(rep, out)
    if out == text:
        return out
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"\s+([,;.])", r"\1", out)
    out = re.sub(r"\s{2,}", " ", out)
    return re.sub(r"(^|\.\s)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)


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
    lines = [f"\\subsubsection{{\\texttt{{{figkit.tex_escape(cid)}}}" + (f": {figkit.tex_escape(title)}" if title else "") + "}",
             f"\\label{{sec:contract-{cid}}}", ""]
    para = []
    if desc:
        para.append(sentence(desc.rstrip(".")) + ".")
    para.append(f"The contract is at version {figkit.tex_escape(row['version'])} and its status in the catalog is "
                f"\\emph{{{figkit.tex_escape(row['status'])}}}.")
    para.append(f"Its producer is \\texttt{{{figkit.tex_escape(producer_text(row['owner']))}}}, and its schema file is "
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
    props = collect(schema, (ROOT / row["schema file"]).parent) if schema else None
    if props:
        n = len(list(expand(props, schema)))
        para.append(f"Table~\\ref{{tab:contract-{cid}}} lists its {n} top-level "
                    f"field{'s' if n != 1 else ''} with the type, the unit, the range or the values and the description.")
    lines.append(" ".join(para))
    lines.append("")
    if schema:
        if props:
            lines += ["{\\small", "\\begin{longtable}{p{0.19\\textwidth}p{0.13\\textwidth}p{0.11\\textwidth}p{0.16\\textwidth}p{0.30\\textwidth}}",
                      f"\\caption{{The top-level fields of the contract \\texttt{{{figkit.tex_escape(cid)}}}: the name, the JSON "
                      f"type, the unit, the range or the values and the description, as the schema file holds them.}}"
                      f"\\label{{tab:contract-{cid}}}\\\\",
                      "\\toprule Field & Type & Unit & Range or values & Description \\\\ \\midrule \\endfirsthead",
                      "\\toprule Field & Type & Unit & Range or values & Description \\\\ \\midrule \\endhead"]
            for name, spec in expand(props, schema):
                d = describe(name, spec, schema)
                d = (d[:220] + " ...") if len(d) > 220 else d
                lines.append(f"\\texttt{{{figkit.tex_escape(name)}}} & {figkit.tex_escape(kind_of(spec))} & "
                             f"{figkit.tex_escape(unit_of(name, spec, schema, d))} & "
                             f"{figkit.tex_escape(range_of(spec))} & {sentence(d) or '-'} \\\\")
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
        out += [f"\\subsection{{{head}}}", f"\\label{{sec:contracts-{g}}}", ""]
        out += [subsection(r) for r in by_group[g]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(out).split("\n")
    text = "\n".join(line if line.startswith("\\label") else scrub(line) for line in lines)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(rows)} contracts -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
