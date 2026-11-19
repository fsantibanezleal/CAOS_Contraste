"""The methods compared, question by question, for the Results chapter of the technical report (``sections/19-results.tex``,
subsection ``sec:results-methods-compared``), written from the committed document ``data/derived/benchmark/methods-compared.json``
(contract ``benchmark-methods`` 1.0.0). Nothing is typed by hand and nothing is recomputed: every value, every standing, every
reading, every reason for a null cell and every protocol is the document's own text or number, rounded for print by one rule.

    E:/_venvs/contraste/.venv-pipeline/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_methods-compared.py

Writes, into ``tables/``:

* ``methods-compared-numbers.tex``: ``\\newcommand`` macros ``\\bm...`` (questions, cells, null cells, methods left out);
* ``methods-compared-q1.tex`` to ``methods-compared-q12.tex``: one subsubsection per question (``sec:results-methods-compared-q<n>``)
  with its protocol, a table of its methods (standing, source, section of this report), one ``longtable`` of values per metric
  group (the best cell of each column in bold by the document's declared rule), the reasons of its null cells and the document's
  reading, the methods it leaves out and the manuscript that reports a negative or partial result;
* ``methods-compared-notes.tex``: the ladder methods left out of every question and the questions the document does not build.

The standing of a method is read by the document from the method ladder of the design document and printed with the labels
"Long-established", "Recent published", "Proposed in this work" and "Reference" (a method with no ladder row). The ladder id of a
row is used only to look up the section of this report that describes the method (``coverage.json``); it is never printed.
``render(doc)`` returns the files as text (the tests call it on altered documents); ``main`` writes them, byte-equal on every run.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
sys.path.insert(0, str(HERE))
import figkit  # noqa: E402
from _halfup import fixed, sci  # noqa: E402

ROOT = figkit.ROOT
REPORT = HERE.parent
DOC = ROOT / "data" / "derived" / "benchmark" / "methods-compared.json"
COVERAGE = REPORT / "coverage.json"
BS = chr(92)

STANDING = {"established": "Long-established", "recent": "Recent published", "proposed": "Proposed in this work",
            "reference": "Reference"}
STANDING_ORDER = ["established", "recent", "proposed", "reference"]
INTEGER_UNITS = {"days", "months", "histories"}
MAX_COLUMNS = 8  # a table with more value columns is turned: its columns become its rows


# ----------------------------------------------------------------------------------------------------------------------
# text

def esc(text: str) -> str:
    return figkit.tex_escape(text)


#: The plan's backlog and computation ids are process vocabulary, not content: the sentence keeps its meaning without them.
SCRUB = [
    (re.compile(r"\s*\(backlog BL-\d+, K-\d+\)"), ""),
    (re.compile(r";? backlog BL-\d+ \(K-\d+\) adds the treatment"), "; a later computation adds the treatment"),
    (re.compile(r"the other rules wait for backlog BL-\d+ \(K-\d+\)"), "the other rules carry no value in the committed documents"),
    (re.compile(r"the verdict block of the same document"), "the block of the same document that holds the outcome of the rule"),
    (re.compile(r"\b(?:Document verdict|Verdict of the document)\b"), "Outcome of the rule"),
    (re.compile(r"\bVerdict clause\b"), "Clause of the rule"),
    (re.compile(r"\bThe committed verdict\b"), "The committed outcome of the rule"),
    (re.compile(r"^verdict$"), "outcome"),
    (re.compile(r"\bWithdrawn ratings followed\b"), "Ratings that left the cohort, followed"),
    (re.compile(r"\bthe withdrawn ratings\b"), "the ratings that left the cohort"),
    (re.compile(r"\bevery withdrawn name\b"), "every name that left the cohort"),
    (re.compile(r"\s*\(backlog BL-\d+\)"), ""),
    (re.compile(r"\(question \d+ is not built\)"), "(the comparison is not built)"),
]
LEFTOVER = re.compile(r"\bBL-\d+|\bK-\d+|\b(?:BS|M)-\d+|\bQ\d+\b|(?i:\bbacklog\b|\bverdicts?\b|\bwithdrawn\b|\bthis (?:release|version)\b)")


def reader_text(text: str) -> str:
    """A text of the document as a reader of the report sees it (not yet escaped); an id no rule knows stops the script."""
    out = text
    for pat, rep in SCRUB:
        out = pat.sub(rep, out)
    out = re.sub(r"\s+([,;.])", r"\1", out)
    left = LEFTOVER.search(out)
    if left:
        raise ValueError(f"an internal id reaches the report: {left.group(0)!r} in {text!r}")
    return out.strip()


def txt(node: dict) -> str:
    """The escaped English text of a ``{en, es}`` pair."""
    return esc(reader_text(node["en"]))


def sentence(text: str) -> str:
    """Escaped text ending in a full stop."""
    t = text.strip()
    return t if t.endswith((".", "?", "!")) else t + "."


def join_and(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
               11: "eleven", 12: "twelve"}


def word(n: int) -> str:
    return COUNT_WORDS.get(n, str(n))


# ----------------------------------------------------------------------------------------------------------------------
# the bibliography: a source of the document is cited when exactly one entry matches its first author and year

def load_bib() -> dict[str, dict[str, str]]:
    bib: dict[str, dict[str, str]] = {}
    for path in sorted(REPORT.glob("references*.bib")):
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"@\w+\{([^,\s]+),(.*?)(?=\n@|\Z)", text, re.S):
            key, body = m.groups()
            bib[key] = {f: bib_field(body, f) for f in ("author", "title", "year", "doi")}
    return bib


def bib_field(body: str, name: str) -> str:
    """The value of a BibTeX field (braced with balanced braces, quoted or bare), braces removed; empty when absent."""
    m = re.search(rf"(?:^|[\s,]){name}\s*=\s*", body, re.I)
    if not m:
        return ""
    i = m.end()
    if body[i:i + 1] == "{":
        depth, j = 0, i
        while j < len(body):
            depth += {"{": 1, "}": -1}.get(body[j], 0)
            j += 1
            if depth == 0:
                break
        value = body[i + 1:j - 1]
    elif body[i:i + 1] == '"':
        j = body.index('"', i + 1)
        value = body[i + 1:j]
    else:
        value = re.match(r"[^,\s}]*", body[i:]).group(0)
    return re.sub(r"[{}]", "", value).strip()


BIB = load_bib()


def cite_key(source: str) -> str | None:
    """The bibliography key of ``Author, Author and Author (year)`` (or a titled report), or None when no single entry matches."""
    ym = re.search(r"\((\d{4})\)", source)
    if not ym:
        return None
    year = ym.group(1)
    head = source[: ym.start()].strip()
    surname = re.split(r",| and ", head)[0].strip().split()[-1].lower() if head else ""
    hits = [k for k, f in BIB.items() if f["year"] == year and f["author"].lower().startswith(surname) and surname]
    if len(hits) == 1:
        return hits[0]
    titled = [k for k, f in BIB.items() if f["year"] == year and head and head.lower() in f["title"].lower()]
    if len(titled) == 1:
        return titled[0]
    hits = [k for k in hits if head.split()[-1].lower() in f"{BIB[k]['author']} {BIB[k]['title']}".lower()]
    return hits[0] if len(hits) == 1 else None


def manuscript_key(path: str) -> str:
    """The bibliography entry of a manuscript of the product: the one that holds the concept DOI its ``main.tex`` declares."""
    main = ROOT / path
    m = re.search(r"\\newcommand\{\\conceptdoi\}\{([^}]*)\}", main.read_text(encoding="utf-8"))
    if not m:
        raise ValueError(f"{path} declares no concept DOI")
    hits = [k for k, f in BIB.items() if f["doi"] == m.group(1)]
    if len(hits) != 1:
        raise ValueError(f"the bibliography holds {len(hits)} entries for the concept DOI {m.group(1)} of {path}")
    return hits[0]


def cite(key: str | None) -> str:
    return f"~\\citep{{{key}}}" if key else ""


# ----------------------------------------------------------------------------------------------------------------------
# numbers

def value_text(value, unit: str) -> str:
    """One document value as a table cell: a word for a string, yes or no for a flag, else a number rounded half up."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return esc(value.replace("_", " "))
    if isinstance(value, int) or (float(value).is_integer() and unit in INTEGER_UNITS):
        return str(int(value))
    x = float(value)
    if x == 0:
        return "0.000"
    a = abs(x)
    if a < 0.001:
        return sci(x, 1)
    digits = 1 if a >= 100 else 2 if a >= 10 else 3 if a >= 0.01 else 4
    out = fixed(x, digits)
    return out.replace("-", "$-$") if out.startswith("-") else out


def direction(metric: dict, metrics: dict[str, dict]) -> str:
    rule = metric["better"]
    if rule == "lower":
        return "lower is better"
    if rule == "higher":
        return "higher is better"
    if rule == "none":
        return "context, not ranked"
    if rule.startswith("nearer-metric:"):
        return f"nearer the {reader_text(metrics[rule.split(':', 1)[1]]['label']['en']).lower()} is better"
    if rule.startswith("nearer:"):
        return f"nearer {rule.split(':', 1)[1]} is better"
    if rule.startswith("order:"):
        order = rule.split(":", 1)[1].split(",")
        return f"{order[0]} is best, then {', then '.join(order[1:])}"
    raise ValueError(f"unknown rule {rule}")


# ----------------------------------------------------------------------------------------------------------------------
# tables

def column_label(run: dict, column: str) -> str:
    for c in run["columns"]:
        if c["id"] == column:
            return txt(c["label"])
    raise KeyError(column)


def table_plan(q: dict) -> list[dict]:
    """The value tables of a question: per run, one table for each metric with several columns and one for the metrics with one."""
    plans = []
    runs = {r["id"]: r for r in q["runs"]}
    for run in q["runs"]:
        metrics = [m for m in q["metrics"] if m["run_id"] == run["id"]]
        single = [m for m in metrics if len(m["columns"]) == 1]
        emitted = False
        for m in metrics:  # the order of the document's metrics; the one-column metrics of a run share the table of the first
            if len(m["columns"]) > 1:
                plans.append({"run": run, "metrics": [m], "keys": [(m["id"], c) for c in m["columns"]], "by": "column"})
            elif not emitted:
                emitted = True
                plans.append({"run": run, "metrics": single, "keys": [(x["id"], x["columns"][0]) for x in single],
                              "by": "metric" if len(single) > 1 else "column"})
    assert all(p["run"]["id"] in runs for p in plans)
    return plans


def colspec(n_values: int) -> str:
    share = min(0.14, round(0.63 / max(n_values, 1), 3))
    return (">{\\raggedright\\arraybackslash}p{0.25\\textwidth}"
            + ("".join([f">{{\\raggedleft\\arraybackslash}}p{{{share}\\textwidth}}"] * n_values)))


def value_table(q: dict, plan: dict, label: str) -> tuple[str, list[str]]:
    """``(latex, notes)``: the longtable of one plan and the sentences that state the reason of its null cells."""
    metrics = {m["id"]: m for m in q["metrics"]}
    cells = {(r["id"], c["metric"], c["column"]): c for r in q["rows"] for c in r["cells"]}
    best = {(s["metric"], s["column"]): set(s["best"]) for s in q["standings"]}
    keys = plan["keys"]
    rows = [r for r in q["rows"] if any((r["id"], m, c) in cells for m, c in keys)]
    run = plan["run"]

    def header_of(key):
        m, c = key
        return column_label(run, c) if plan["by"] == "column" else txt(metrics[m]["label"])

    def cell_text(r, key):
        c = cells.get((r["id"], key[0], key[1]))
        if c is None or c["value"] is None:
            return "--"
        t = value_text(c["value"], metrics[key[0]]["unit"]["en"])
        return f"\\textbf{{{t}}}" if r["id"] in best.get(key, set()) else t

    units = []
    for m in plan["metrics"]:
        units.append(f"{reader_text(m['label']['en'])} ({reader_text(m['unit']['en'])}; {direction(m, metrics)})")
    caption = (f"{esc(q['title']['en'])}: " + esc("; ".join(units)) + f", for each method, on the run {esc(reader_text(run['label']['en']))}. "
               "The best value of a column by the declared rule is in bold, ties all in bold; a dash marks a cell without a "
               "value, and the notes below the table state why.")
    transposed = len(keys) > MAX_COLUMNS
    if transposed and len(rows) > MAX_COLUMNS:
        raise ValueError(f"table {label} has {len(keys)} columns and {len(rows)} rows: no layout fits")
    lines = ["{\\footnotesize\\setlength{\\tabcolsep}{3pt}"]
    if not transposed:
        lines.append(f"% bm-table {q['id']} normal cols=" + ";".join(f"{m}/{c}" for m, c in keys))
        lines.append(f"\\begin{{longtable}}{{{colspec(len(keys))}}}")
        head = "Method & " + " & ".join(header_of(k) for k in keys) + " \\\\"
        lines += [f"\\caption{{{caption}}}\\label{{{label}}}\\\\", f"\\toprule {head} \\midrule \\endfirsthead",
                  f"\\toprule {head} \\midrule \\endhead"]
        last = None
        for r in rows:
            if r["standing"] != last:
                lines.append(f"\\multicolumn{{{len(keys) + 1}}}{{l}}{{\\emph{{{STANDING[r['standing']]}}}}} \\\\")
                last = r["standing"]
            lines.append(esc(reader_text(r["method"]["en"])) + " & " + " & ".join(cell_text(r, k) for k in keys)
                         + f" \\\\ % bm-row {r['id']}")
    else:
        lines.append(f"% bm-table {q['id']} transposed cols=" + ";".join(r["id"] for r in rows))
        lines.append(f"\\begin{{longtable}}{{{colspec(len(rows))}}}")
        head = (("Column" if plan["by"] == "column" else "Metric") + " & "
                + " & ".join(esc(reader_text(r["method"]["en"])) for r in rows) + " \\\\")
        lines += [f"\\caption{{{caption}}}\\label{{{label}}}\\\\", f"\\toprule {head} \\midrule \\endfirsthead",
                  f"\\toprule {head} \\midrule \\endhead"]
        for k in keys:
            lines.append(header_of(k) + " & " + " & ".join(cell_text(r, k) for r in rows) + f" \\\\ % bm-row {k[0]}/{k[1]}")
    lines += ["\\bottomrule", "\\end{longtable}", "}", ""]

    # the reasons of the null cells, grouped by their text, and the methods the document holds no entry for
    reasons: dict[str, list[str]] = {}
    missing: list[str] = []
    for r in rows:
        held = [cells.get((r["id"], m, c)) for m, c in keys]
        name = esc(reader_text(r["method"]["en"]))
        for c in held:
            if c is not None and c["value"] is None:
                reason = txt(c["null_reason"])
                if name not in reasons.setdefault(reason, []):
                    reasons[reason].append(name)
        if any(c is None for c in held) and name not in missing:
            missing.append(name)
    notes = []
    if reasons:
        parts = []
        for reason, names in reasons.items():
            who = join_and(names) if len(names) <= 6 else f"{word(len(names))} methods"
            parts.append(f"{reason.rstrip('.')} ({who})")
        notes.append(f"A dash in Table~\\ref{{{label}}} is a cell the product does not compute, for the stated reason: "
                     + "; ".join(parts) + ".")
    if missing:
        who = join_and(missing) if len(missing) <= 6 else f"{word(len(missing))} methods"
        notes.append(f"For {who} the document holds no entry in some columns of Table~\\ref{{{label}}}; that is an entry the "
                     "document does not hold, not a value of zero, and nothing is claimed for it.")
    return "\n".join(lines), notes


def methods_table(q: dict, label: str, coverage: dict[str, str]) -> str:
    lines = ["{\\footnotesize\\setlength{\\tabcolsep}{3pt}", f"% bm-table-methods {q['id']}",
             "\\begin{longtable}{>{\\raggedright\\arraybackslash}p{0.38\\textwidth}>{\\raggedright\\arraybackslash}p{0.17\\textwidth}"
             ">{\\raggedright\\arraybackslash}p{0.27\\textwidth}>{\\raggedright\\arraybackslash}p{0.10\\textwidth}}"]
    cap = (f"The methods compared on the question {q['title']['en'].rstrip('.')}: the standing of each method, the source and the "
           "year the document records for it, and the section of this report that describes it; a dash marks a method with no "
           "source recorded or with no section of its own.")
    head = "Method & Standing & Source & Section \\\\"
    lines += [f"\\caption{{{esc(cap)}}}\\label{{{label}}}\\\\", f"\\toprule {head} \\midrule \\endfirsthead",
              f"\\toprule {head} \\midrule \\endhead"]
    for r in q["rows"]:
        src = r["source"]
        source = (esc(src["text"]) + cite(cite_key(src["text"]))) if src else "--"
        section = f"\\ref{{{coverage[r['ladder_id']]}}}" if r["ladder_id"] in coverage else "--"
        lines.append(f"{esc(reader_text(r['method']['en']))} & {STANDING[r['standing']]} & {source} & {section} \\\\")
    lines += ["\\bottomrule", "\\end{longtable}", "}", ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------------------------------------------------------
# a question

def render_question(q: dict, n: int, coverage: dict[str, str]) -> str:
    qlabel = f"sec:results-methods-compared-q{n}"
    mlabel = f"tab:bm-q{n}-methods"
    counts = {s: sum(1 for r in q["rows"] if r["standing"] == s) for s in STANDING_ORDER}
    standing_text = join_and([f"{word(counts[s])} {STANDING[s].lower() if s != 'proposed' else 'proposed in this work'}"
                              for s in STANDING_ORDER if counts[s]])
    cases = join_and([c for c in q["case_ids"]])
    plans = table_plan(q)
    labels = [f"tab:bm-q{n}-{i + 1}" for i in range(len(plans))]
    lines = [f"\\subsubsection{{{esc(q['title']['en'])}}}", f"\\label{{{qlabel}}}", ""]
    para = [f"This question is answered on {'case' if len(q['case_ids']) == 1 else 'cases'} {cases}. "
            + sentence(txt(q["protocol"]))]
    for run in q["runs"]:
        seed = run["seed"]
        seed_text = (f"its random seed is {seed['value']}" if seed else "the document records no random seed for it")
        para.append(f"The run ``{esc(reader_text(run['label']['en']))}'' reads as follows: {esc(reader_text(run['protocol']['en']).rstrip('.'))}; {seed_text}.")
    para.append(f"Table~\\ref{{{mlabel}}} lists the {word(len(q['rows']))} methods the document compares, {standing_text}, with "
                "the section of this report that describes each. "
                + ("Table" if len(labels) == 1 else "Tables") + "~" + ", ".join(f"\\ref{{{l}}}" for l in labels)
                + " give the values, one table for each group of metrics that share a run and a layout.")
    lines += [" ".join(para), ""]
    notes_on_rows = [f"{esc(reader_text(r['method']['en']))}: {esc(reader_text(r['note']['en']).rstrip('.'))}" for r in q["rows"] if r["note"]]
    lines.append(methods_table(q, mlabel, coverage))
    if notes_on_rows:
        lines += ["The document adds a note on " + word(len(notes_on_rows)) + " of these methods. " + "; ".join(notes_on_rows) + ".", ""]
    for plan, label in zip(plans, labels):
        table, notes = value_table(q, plan, label)
        lines.append(table)
        if notes:
            lines += [" ".join(notes), ""]
    lines += ["The document reads the tables of this question by the declared rule of each metric. "
              + sentence(esc(reader_text(q["reading"]["en"]))), ""]
    for a in q["absent"]:
        key = cite_key(a["method"]["en"])
        lines += [f"The document leaves out of this question {esc(reader_text(a['method']['en']))}{cite(key)}: "
                  + sentence(esc(reader_text(a["reason"]["en"]))), ""]
    for neg in q["negative_results"]:
        key = manuscript_key(neg["manuscript"])
        lines += [f"{sentence(esc(reader_text(neg['text']['en'])))} The product's own manuscript on this method reports it{cite(key)}.", ""]
    return "\n".join(lines)


def render(doc: dict) -> dict[str, str]:
    coverage = json.loads(COVERAGE.read_text(encoding="utf-8"))["methods"]
    out: dict[str, str] = {}
    header = "% Generated by tables/make_methods-compared.py from data/derived/benchmark/methods-compared.json; do not edit.\n"
    cells = [c for q in doc["questions"] for r in q["rows"] for c in r["cells"]]
    nulls = sum(1 for c in cells if c["value"] is None)
    macros = {"bmNQuestions": word(len(doc["questions"])), "bmNCells": f"{len(cells):,}".replace(",", "\\,"),
              "bmNFilled": f"{len(cells) - nulls:,}".replace(",", "\\,"), "bmNNull": str(nulls),
              "bmNLeftOut": word(len(doc["left_out"])), "bmNNotBuilt": word(len(doc["not_built"])),
              "bmCodeVersion": esc(doc["provenance"]["code_version"]), "bmSchemaVersion": esc(doc["schema_version"])}
    out["methods-compared-numbers.tex"] = header + "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in macros.items())
    for i, q in enumerate(doc["questions"], start=1):
        out[f"methods-compared-q{i}.tex"] = header + render_question(q, i, coverage)
    notes = []
    if doc["left_out"]:
        items = [f"{esc(reader_text(x['method']['en']))}: {sentence(esc(reader_text(x['reason']['en'])))}" for x in doc["left_out"]]
        notes.append(f"The document leaves {word(len(doc['left_out']))} methods of the ladder out of every question. " + " ".join(items))
    if doc["not_built"]:
        items = [f"{esc(reader_text(x['title']['en']))}: {sentence(esc(reader_text(x['reason']['en'])))}" for x in doc["not_built"]]
        notes.append(f"The document builds no comparison for {word(len(doc['not_built']))} further questions. " + " ".join(items))
    out["methods-compared-notes.tex"] = header + "\n\n".join(notes) + "\n"
    return out


def main() -> None:
    doc = json.loads(DOC.read_text(encoding="utf-8"))
    files = render(doc)
    for name, text in files.items():
        (HERE / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"{len(files)} files -> {HERE}")


if __name__ == "__main__":
    main()
