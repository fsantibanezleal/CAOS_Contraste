"""The technical report's methods-compared subsection (``manuscripts/contraste-technical-report/tables/make_methods-compared.py``).

The consumed contract is ``benchmark-methods`` 1.0.0 (``data/derived/benchmark/methods-compared.json``). This side of the boundary
tests that every number the generator prints equals the document's value at the same question, method and metric (read back from
the generated LaTeX by a parser apart from the generator), that a null cell prints a dash and its reason, that no tier word and no
internal id reaches the LaTeX, that the committed tables are what a fresh run writes, and the edge cases of the brief: a row whose
every cell is null, a table that passes a page (``longtable``), and the characters ``%``, ``_``, ``&`` and ``#`` in a method name.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "manuscripts" / "contraste-technical-report"
SCRIPT = REPORT / "tables" / "make_methods-compared.py"
DOC_PATH = ROOT / "data" / "derived" / "benchmark" / "methods-compared.json"
SECTION = REPORT / "sections" / "19-results.tex"
TIER_OR_ID = re.compile(
    r"classical|state[ -]of[ -]the[ -]art|\bsota\b|beyond|\btiers?\b|\bBS-\d|\bM-\d|\bBL-\d|\bK-\d|\bQ\d+\b|\bSDD\b|dossier|\bverdicts?\b|\bwithdrawn\b|this (?:release|version)"
    r"|cl[aá]sic[oa]|estado del arte",
    re.I,
)
EM_DASH = "\u2014"


def load_generator():
    assert SCRIPT.is_file(), f"the generator is absent: {SCRIPT}"
    spec = importlib.util.spec_from_file_location("make_methods_compared", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gen():
    return load_generator()


@pytest.fixture(scope="module")
def doc() -> dict:
    return json.loads(DOC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rendered(gen, doc) -> dict[str, str]:
    return gen.render(doc)


def _numeric(cell: str):
    """The number a generated cell prints and the decimals it prints, or None for a dash and a word; and whether it is bold."""
    text = cell.strip().replace("$-$", "-")
    bold = text.startswith("\\textbf{") and text.endswith("}")
    if bold:
        text = text[len("\\textbf{"):-1].strip()
    sci = re.fullmatch(r"\\ensuremath\{(-?[0-9.]+)\\times10\^\{(-?\d+)\}\}", text)
    if sci:
        mant, exp = sci.group(1), int(sci.group(2))
        dec = len(mant.split(".")[1]) if "." in mant else 0
        return float(mant) * 10 ** exp, dec - exp, bold
    plain = re.fullmatch(r"-?[0-9]+(\.[0-9]+)?", text)
    if plain:
        dec = len(text.split(".")[1]) if "." in text else 0
        return float(text), dec, bold
    return None, None, bold


def parse_tables(rendered: dict[str, str]):
    """Every value table of the generated files: ``(qid, [(rowkey, [cell, ...], name), ...], colkeys, orient)``."""
    out = []
    for name, text in rendered.items():
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            m = re.match(r"% bm-table (Q\d+) (normal|transposed) cols=(.*)$", lines[i])
            if not m:
                i += 1
                continue
            qid, orient, cols = m.group(1), m.group(2), m.group(3).split(";")
            rows = []
            i += 1
            while i < len(lines) and not lines[i].startswith("\\end{longtable}"):
                rm = re.match(r"(.*) \\\\ % bm-row (.*)$", lines[i])
                if rm:
                    cells = rm.group(1).split(" & ")
                    rows.append((rm.group(2), cells[1:], cells[0]))
                i += 1
            out.append((qid, rows, cols, orient))
        # every value table is a longtable (a table may pass a page)
        assert text.count("% bm-table") == text.count("\\begin{longtable}"), name
    return out


def _cells_by_key(doc):
    table = {}
    for q in doc["questions"]:
        for r in q["rows"]:
            for c in r["cells"]:
                table[(q["id"], r["id"], c["metric"], c["column"])] = c
    return table


def _resolve(orient, rowkey, colkey):
    rid, mc = (rowkey, colkey) if orient == "normal" else (colkey, rowkey)
    metric, column = mc.split("/", 1)
    return rid, metric, column


def test_the_generator_writes_a_file_per_question_a_numbers_file_and_the_notes(rendered, doc):
    for i in range(1, len(doc["questions"]) + 1):
        assert f"methods-compared-q{i}.tex" in rendered
    assert "methods-compared-numbers.tex" in rendered and "methods-compared-notes.tex" in rendered


def test_every_printed_number_equals_the_document_value_at_its_question_method_and_metric(rendered, doc):
    cells = _cells_by_key(doc)
    seen = 0
    for qid, rows, colkeys, orient in parse_tables(rendered):
        for rowkey, values, _name in rows:
            assert len(values) == len(colkeys), (qid, rowkey)
            for colkey, printed in zip(colkeys, values):
                rid, metric, column = _resolve(orient, rowkey, colkey)
                cell = cells.get((qid, rid, metric, column))
                number, decimals, _bold = _numeric(printed)
                if cell is None or cell["value"] is None:
                    assert printed.strip() == "--", (qid, rid, metric, column, printed)
                    continue
                value = cell["value"]
                if isinstance(value, bool):
                    assert printed.strip().replace("\\textbf{", "").rstrip("}") == ("yes" if value else "no")
                elif isinstance(value, str):
                    assert value.replace("_", " ") in printed
                else:
                    assert number is not None, (qid, rid, metric, column, printed)
                    assert abs(number - value) <= 0.5 * 10 ** (-decimals) + 1e-12, (qid, rid, metric, column, printed, value)
                    seen += 1
    n_values = sum(1 for c in cells.values() if isinstance(c["value"], (int, float)) and not isinstance(c["value"], bool))
    assert seen == n_values, "every numeric cell of the document is printed exactly once"


def test_a_null_cell_prints_a_dash_and_its_reason_is_stated_in_the_question(rendered, gen, doc):
    for q in doc["questions"]:
        text = rendered[f"methods-compared-q{q['id'][1:]}.tex"]
        flat = re.sub(r"\s+", " ", text.replace("\\allowbreak ", ""))
        for raw, plain in (("\\_", "_"), ("\\%", "%"), ("\\&", "&"), ("\\#", "#")):
            flat = flat.replace(raw, plain)
        for r in q["rows"]:
            for c in r["cells"]:
                if c["value"] is None:
                    assert gen.reader_text(c["null_reason"]["en"]) in flat, (q["id"], r["id"], c["metric"])


def test_the_bold_cells_are_exactly_the_best_of_the_document_standings(rendered, doc):
    expected = set()
    for q in doc["questions"]:
        for s in q["standings"]:
            for rid in s["best"]:
                expected.add((q["id"], rid, s["metric"], s["column"]))
    bold = set()
    for qid, rows, colkeys, orient in parse_tables(rendered):
        for rowkey, values, _n in rows:
            for colkey, printed in zip(colkeys, values):
                if printed.strip().startswith("\\textbf{"):
                    rid, metric, column = _resolve(orient, rowkey, colkey)
                    bold.add((qid, rid, metric, column))
    assert bold == expected


def test_every_question_prints_its_title_protocol_standings_and_a_label_and_every_table_is_referenced(rendered, doc):
    for q in doc["questions"]:
        text = rendered[f"methods-compared-q{q['id'][1:]}.tex"]
        assert q["title"]["en"] in text.replace("\\&", "&")
        assert f"\\label{{sec:results-methods-compared-q{q['id'][1:]}}}" in text
        for label in re.findall(r"\\label\{(tab:[^}]+)\}", text):
            assert re.search(r"\\(?:[Cc]ref|ref)\{[^}]*\b" + re.escape(label) + r"\b", text), label
    joined = "\n".join(rendered.values())
    for label in ("Long-established", "Recent published", "Proposed in this work", "Reference"):
        assert label in joined


def test_no_tier_word_and_no_internal_id_and_no_em_dash_reaches_the_latex(rendered):
    for name, text in rendered.items():
        body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))
        body = re.sub(r"\\(?:label|ref|cref|Cref|citep|input)\{[^}]*\}", "", body)
        assert not TIER_OR_ID.search(body), (name, TIER_OR_ID.search(body).group(0))
        assert EM_DASH not in text and "\u2192" not in text, name


def test_the_committed_tables_are_what_a_fresh_run_writes(rendered):
    for name, text in rendered.items():
        path = REPORT / "tables" / name
        assert path.is_file(), f"{name} is not committed: run the generator"
        assert path.read_text(encoding="utf-8") == text, f"{name} differs from a fresh run"


def test_the_section_reads_every_question_by_its_label_and_inputs_its_generated_file():
    text = SECTION.read_text(encoding="utf-8")
    assert "\\label{sec:results-methods-compared}" in text
    assert text.index("\\label{sec:results-proposed-summary}") < text.index("\\label{sec:results-methods-compared}")
    for i in range(1, 13):
        assert f"\\input{{tables/methods-compared-q{i}}}" in text, i


def test_adversarial_characters_of_latex_in_a_method_name_are_escaped(gen, doc):
    plant = copy.deepcopy(doc)
    plant["questions"][0]["rows"][0]["method"]["en"] = "Rule A&B_C 5% #1"
    text = gen.render(plant)["methods-compared-q1.tex"]
    assert "Rule A\\&B\\_C 5\\% \\#1" in text
    assert "Rule A&B" not in text


def test_adversarial_a_row_whose_every_cell_is_null_prints_dashes_and_the_reason(gen, doc):
    plant = copy.deepcopy(doc)
    q = plant["questions"][2]  # the desk question: no null cell today
    row = q["rows"][0]
    for c in row["cells"]:
        c["value"] = None
        c["null_reason"] = {"en": "the plant computes nothing here", "es": "la planta no calcula nada aqui"}
        c["cited"] = None
    q["standings"] = [s for s in q["standings"] if row["id"] not in s["best"]]
    out = gen.render(plant)["methods-compared-q3.tex"]
    assert "the plant computes nothing here" in out
    checked = 0
    for qid, rows, colkeys, orient in parse_tables({"q3": out}):
        for rowkey, values, _n in rows:
            if rowkey == row["id"] and orient == "normal":
                assert all(v.strip() == "--" for v in values)
                checked += 1
    assert checked >= 1


def test_adversarial_a_changed_document_value_changes_the_printed_table(gen, doc):
    plant = copy.deepcopy(doc)
    cell = plant["questions"][0]["rows"][0]["cells"][0]
    cell["value"] = cell["value"] + 0.5
    assert gen.render(plant)["methods-compared-q1.tex"] != gen.render(doc)["methods-compared-q1.tex"]


def test_the_generator_is_deterministic_two_runs_write_byte_equal_files(gen, doc):
    first, second = gen.render(doc), gen.render(copy.deepcopy(doc))
    assert first == second
    assert all(text.encode("utf-8") == second[name].encode("utf-8") for name, text in first.items())


def test_every_table_with_a_dash_states_a_reason_in_its_note_and_the_methods_table_cites_its_sources(rendered):
    for name, text in rendered.items():
        if not name.startswith("methods-compared-q"):
            continue
        for label in re.findall(r"\\label\{(tab:bm-q\d+-\d+)\}", text):
            block = text.split("\\label{" + label + "}")[1].split("\\end{longtable}")[0]
            if re.search(r"(?<![\w-])--(?![\w-])", block.split("\\endhead")[1]):
                assert ("A dash in Table~\\ref{" + label + "}" in text
                        or "the document holds no entry in some columns of Table~\\ref{" + label + "}" in text), label
    assert "\\citep{market:kupiec1995}" in rendered["methods-compared-q2.tex"]
    assert "\\citep{proposed:contraste-eprocess}" in rendered["methods-compared-q2.tex"]
    assert "\\citep{proposed:contraste-anchored}" in rendered["methods-compared-q4.tex"]
