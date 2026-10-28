"""U16-F12g (fix round 5, the R4 capture review, ruling 10): the Spanish guard's defects are majors of the tooling.

scripts/check_spanish.py now (1) lists the English words of ruling 6 (swap, swaption, spread, spot, forward, commodities, bucket,
prior, test, tick, hash, port, shell, benchmark, offset, points, full, allocation) with their Spanish, and refuses an English
table or figure locator ("Table 8"); (2) reads a word joined to
another by "_" (``α_amber``, ``Score_ref``, ``odds_ref``, ``K_reduced``) and the text of a ``<sub>`` in a Spanish line, against the
English subscripts the words file lists after a ``_``; (3) reads, without --documents, the ``es`` values of the documents a view
loads at run time (the regulatory calculators, the governance documents). Each test plants a text in a throwaway tree and runs
the guard's main(), as tests/test_check_spanish.py does.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_spanish.py"
PY = "data-pipeline/pipeline/cases/x.py"
TSX = "frontend/src/pages/X.tsx"
CALC = "data/derived/regulatory/calculators.json"
GOV = "data/derived/governance/findings.json"
CASE_DOC = "data/derived/C99/doc.json"


@pytest.fixture(scope="module")
def guard():
    spec = importlib.util.spec_from_file_location("check_spanish_f12g", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _run(guard, root: Path, capsys, *argv: str):
    code = guard.main(["--root", str(root), *argv])
    return code, capsys.readouterr().out


RULING_6 = {"swap": "permuta", "swaption": "opción sobre permuta", "spread": "diferencial", "spot": "contado",
            "forward": "a plazo", "commodities": "materias primas", "bucket": "tramo", "prior": "a priori", "test": "prueba",
            "tick": "pérdida cuantílica", "hash": "huella", "port": "puerto", "shell": "intérprete de órdenes",
            "benchmark": "referencia comparativa"}


def test_the_words_of_ruling_6_are_listed_with_the_spanish_the_documentation_writes(guard):
    terms = guard.load_english(ROOT / "scripts" / "check_spanish_words.txt")
    for word, fix in RULING_6.items():
        assert word in terms, word
        assert fix in terms[word], (word, terms[word])
    assert {"offset", "points", "full", "allocation", "commodity"} <= set(terms)


@pytest.mark.parametrize("text, word", [
    ("parámetros y hash en el registro del modelo", "hash"),
    ("Correlación entre buckets, gamma", "buckets"),
    ("Spread de crédito, soberano, grado de inversión", "Spread"),
    ("CRE99 conjunto 1: swaps de tasa y una swaption, sin margen", "swaps"),
    ("conjunto 3: forwards y swaps de commodities", "commodities"),
    ("los puertos en vivo y el shell de la máquina", "shell"),
    ("el benchmark de la referencia", "benchmark"),
    ("la pérdida tick del cuantil", "tick"),
    ("el test de razón de verosimilitud", "test"),
    ("la distribución prior de la tasa", "prior"),
    ("la Table 8 del documento de la EBA", "Table"),
])
def test_an_english_word_of_ruling_6_in_a_spanish_text_is_found(guard, tmp_path, capsys, text, word):
    _write(tmp_path, PY, f'T = {{"en": "x", "es": {json.dumps(text, ensure_ascii=False)}}}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1, out
    assert f"{PY}:1: {word} ->" in out


def test_the_same_words_are_free_in_english_and_in_a_spanish_word_that_contains_them(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"en": "The swap spread of the test", "es": "La permuta y su diferencial, a priori, en la prueba del importe"}\n'
                         'K = {"es": "el campo test_id de la fila y spot_rate en el código"}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


@pytest.mark.parametrize("text, word", [
    ("Puntaje_ref = 600 con odds_ref = 50", "odds_ref"),
    ("Score_ref = 600 con razón_ref = 50", "Score_ref"),
    ("con α_rojo no mayor que α_amber los umbrales de la política", "α_amber"),
    ("la base K_reduced con rho igual a uno", "K_reduced"),
    ("λ_full la tasa de todas las pérdidas", "λ_full"),
    ("RWA_nominated los activos calculados con los enfoques", "RWA_nominated"),
    ("MWB_lower el límite de la banda", "MWB_lower"),
])
def test_an_english_word_joined_by_an_underscore_in_a_spanish_text_is_found(guard, tmp_path, capsys, text, word):
    _write(tmp_path, TSX, f"const a = {{ en: 'x', es: {json.dumps(text, ensure_ascii=False)} }};\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1, out
    assert f"{TSX}:1: {word} ->" in out


def test_a_spanish_subscript_passes(guard, tmp_path, capsys):
    _write(tmp_path, TSX, "const a = { en: 'x', es: 'Puntaje_ref = 600 con razón_ref = 50; α_rojo y α_ámbar los umbrales; K_reducido y K_cubierto' };\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_the_text_of_a_sub_in_a_spanish_line_is_read(guard, tmp_path, capsys):
    _write(tmp_path, TSX, "export const X = () => (\n  <T\n    en={<>p its p-value, α<sub>red</sub> the threshold of the policy</>}\n"
                          "    es={<>p su valor p, α<sub>red</sub> y α<sub>rojo</sub> los umbrales de la política</>}\n  />\n);\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1, out
    assert f"{TSX}:4: red ->" in out
    assert f"{TSX}:3:" not in out


def test_without_documents_the_run_time_documents_of_a_view_are_read(guard, tmp_path, capsys):
    _write(tmp_path, CALC, json.dumps({"official_examples": [{"title": {"en": "Set 1: interest rate swaps", "es": "Conjunto 1: swaps de tasa"}}]},
                                      ensure_ascii=False))
    _write(tmp_path, GOV, json.dumps({"rows": [{"note": {"en": "the hash of the file", "es": "el hash del archivo de la entrada"}}]},
                                     ensure_ascii=False))
    _write(tmp_path, CASE_DOC, json.dumps({"note": {"en": "a swap", "es": "una swap de la cartera"}}, ensure_ascii=False))
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1, out
    assert f"{CALC}:1: swaps ->" in out
    assert f"{GOV}:1: hash ->" in out
    assert CASE_DOC not in out  # a case document is judged with --documents, after the re-bake


def test_the_run_time_documents_are_read_on_their_es_values_only(guard, tmp_path, capsys):
    _write(tmp_path, CALC, json.dumps({"label": {"en": "the swap and the spread of the bucket", "es": "la permuta y el diferencial del tramo"}},
                                      ensure_ascii=False))
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_an_allow_entry_of_a_run_time_document_is_judged_without_documents(guard, tmp_path, capsys):
    _write(tmp_path, CALC, json.dumps({"t": {"en": "x", "es": "la permuta de la cartera"}}, ensure_ascii=False))
    _write(tmp_path, "scripts/check_spanish_allow.txt", f"{CALC} :: swaps  # owned by another unit\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert "unused allow entry" in out


def test_a_sub_on_a_line_that_holds_both_languages_is_read_in_its_spanish_part(guard, tmp_path, capsys):
    _write(tmp_path, TSX, "const c = <T en={<>p, α<sub>red</sub> and α<sub>amber</sub> the thresholds of the policy</>} "
                          "es={<>p, α<sub>red</sub> y α<sub>ámbar</sub> los umbrales de la política</>} />;\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1, out
    assert f"{TSX}:1: red ->" in out
    assert "amber" not in out


def test_an_english_author_pair_in_a_spanish_text_is_refused_and_a_title_keeps_its_words(guard) -> None:
    """R5 c15 M1 (ruling 5): "Christoffersen and Pelletier (2004)" in a Spanish reference is English body text."""
    cs, words = guard, {}
    found = cs.check_text("Prueba de duración de Christoffersen and Pelletier (2004), sección 3", True, words)
    assert ("Christoffersen and Pelletier", "Christoffersen y Pelletier") in found
    assert ("Engle and Manganelli", "Engle y Manganelli") in cs.check_text("Según Engle and Manganelli, 2004, la regresión", True, words)
    assert not [f for f in cs.check_text("El libro Theory and Practice of Risk de la sección", True, words) if " and " in f[0]]
    assert ("Angelopoulos and Bates", "Angelopoulos y Bates") in cs.check_text("predicción conforme de Angelopoulos and Bates, arXiv 2107.07511", True, words)
    assert not [f for f in cs.check_text("Christoffersen and Pelletier (2004)", False, words) if " and " in f[0]]
