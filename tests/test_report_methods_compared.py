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


# --- BL-113 T2 correction after the reader review (F17, F19, F20 and the readings of Q1, Q2, Q8, Q10, Q12) ---------------------------------------


def _bold_texts_by_column(rendered):
    """``{(qid, orient, colkey): (set of bold texts, [(rowkey, text)] of the non-bold numeric cells)}``."""
    out = {}
    for qid, rows, colkeys, orient in parse_tables(rendered):
        for j, colkey in enumerate(colkeys):
            bold, other = set(), []
            for rowkey, values, _n in rows:
                printed = values[j].strip()
                number, _dec, is_bold = _numeric(printed)
                if number is None:
                    continue
                key = printed[len("\\textbf{"):-1] if is_bold else printed
                if is_bold:
                    bold.add(key)
                else:
                    other.append((rowkey, key))
            out[(qid, orient, colkey)] = (bold, other)
        if orient == "transposed":
            pass
    return out


def test_f17_a_rounded_tie_never_hides_the_order_no_plain_cell_prints_the_text_of_a_bold_one_in_its_column(rendered, doc):
    # a normal table has the columns of the metric; a transposed one has a method per column and a column per row: compare along each ranking unit
    seen = 0
    unranked = {(q["id"], r["id"]) for q in doc["questions"] for r in q["rows"] if not r["ranked"]}
    for qid, rows, colkeys, orient in parse_tables(rendered):
        units = []
        if orient == "normal":
            for j in range(len(colkeys)):
                units.append([(r[0], r[1][j]) for r in rows])
        else:
            for r in rows:
                units.append([(colkeys[j], r[1][j]) for j in range(len(colkeys))])
        for unit in units:
            bold = {t.strip()[len("\\textbf{"):-1] for _k, t in unit if t.strip().startswith("\\textbf{")}
            for k, t in unit:
                t = t.strip()
                if t.startswith("\\textbf{") or _numeric(t)[0] is None or (qid, k) in unranked:
                    continue
                assert t not in bold, (qid, k, t, "prints the same as a best cell but is not best")
                seen += 1
    assert seen > 500


def test_f17_the_two_cells_that_printed_alike_in_the_review_now_print_apart(rendered):
    q1 = rendered["methods-compared-q1.tex"]
    calm = [ln for ln in q1.splitlines() if "bm-row ewma" in ln or "bm-row gjr-t" in ln]
    assert calm, "the Q1 rows are in the table"
    assert not re.search(r"4\.659(?!\d)", "\n".join(calm)), "the rounded tie of the FZ0 loss in the calm window must show a further digit"


def test_adversarial_f17_two_values_that_round_alike_print_with_the_digits_that_separate_them(gen, doc):
    plant = copy.deepcopy(doc)
    q = plant["questions"][2]  # the desk question
    rows = [r for r in q["rows"] if r["ranked"]]
    metric = next(m for m in q["metrics"] if m["better"] == "higher")
    col = metric["columns"][0]
    vals = {}
    for r in rows[:2]:
        c = next(c for c in r["cells"] if c["metric"] == metric["id"] and c["column"] == col)
        vals[r["id"]] = c
    a, b = list(vals.values())
    a["value"], b["value"] = 0.50004, 0.50001
    for s in q["standings"]:
        if s["metric"] == metric["id"] and s["column"] == col:
            s["best"] = [list(vals)[0]]
            s["tie"] = False
    out = gen.render(plant)["methods-compared-q3.tex"]
    texts = {rid: None for rid in vals}
    for qid, prows, colkeys, orient in parse_tables({"q3": out}):
        for rowkey, values, _n in prows:
            for colkey, printed in zip(colkeys, values):
                if orient == "normal" and rowkey in texts and colkey == f"{metric['id']}/{col}":
                    texts[rowkey] = printed.strip()
    first, second = texts.values()
    assert first.startswith("\\textbf{") and not second.startswith("\\textbf{"), texts
    assert first[len("\\textbf{"):-1] != second, texts


def test_f19_no_generated_reading_runs_two_sentences_together(rendered):
    for name, text in rendered.items():
        flat = re.sub(r"\s+", " ", text)
        assert not re.search(r"[a-z0-9)] A null cell is never ranked", flat), name
    assert "the multiplier. A null cell is never ranked" in re.sub(r"\s+", " ", rendered["methods-compared-q10.tex"])


def _reading_paragraphs() -> dict[int, str]:
    """The ``What the tables show`` paragraph of each question, by number, from the section file (inside the methods-compared subsection)."""
    text = SECTION.read_text(encoding="utf-8")
    sub = text[text.index("\\label{sec:results-methods-compared}"):]
    out = {}
    for m in re.finditer(r"\\input\{tables/methods-compared-q(\d+)\}\s*\n\n\\paragraph\{What the tables show\.\}(.*?)(?=\n\n)", sub, re.S):
        out[int(m.group(1))] = m.group(2)
    return out


def test_f20_every_value_table_of_a_question_is_read_in_its_what_the_tables_show_paragraph(rendered):
    paras = _reading_paragraphs()
    assert sorted(paras) == list(range(1, 13))
    for i, para in paras.items():
        labels = re.findall(r"\\label\{(tab:bm-q" + str(i) + r"-\d+)\}", rendered[f"methods-compared-q{i}.tex"])
        refs = set()
        for m in re.finditer(r"\\[Cc]ref\{([^}]*)\}", para):
            refs.update(m.group(1).split(","))
        missing = [lab for lab in labels if lab not in refs]
        assert not missing, (i, missing)


def test_the_readings_state_what_the_review_found_wrong():
    paras = _reading_paragraphs()
    assert "wrapped rule or to the rule it wraps" not in paras[1] and "only those rules carry the two p-values" not in paras[1]
    assert re.search(r"p-values? .*evidence", paras[1]) and "never ranked" in paras[1]
    assert "no such claim is made" not in paras[2] and "tab:mk-ebacktest" in paras[2] and "sec:m39" in paras[2]
    assert "not in the comparison" not in paras[2]
    assert "is not a method of the ladder" not in paras[8]
    assert "mean signed bias" in paras[12] and "mean absolute bias" in paras[12]
    assert "multiplier" in paras[10] and "tab:bm-q10-2" in paras[10]
