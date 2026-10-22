"""The Spanish orthography guard (U16-P1a, BL-089): scripts/check_spanish.py finds an unaccented Spanish word or ending in the
Spanish texts of the producers, of the frontend and, with --documents, of the committed documents, and prints its path, line
and corrected form. Each test plants a text in a throwaway tree and runs the guard's own main(); one test runs it on the real
tree, so the tree stays corrected."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_spanish.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_spanish_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def guard():
    return _load()


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _run(guard, root: Path, capsys, *argv: str):
    code = guard.main(["--root", str(root), *argv])
    return code, capsys.readouterr().out


PY = "data-pipeline/pipeline/cases/x.py"
TSX = "frontend/src/pages/X.tsx"
DOC = "data/derived/C99/doc.json"


def test_unaccented_word_in_a_bilingual_dict_is_found_with_path_line_and_fix(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'DOC = {\n    "title": {"en": "Ten years", "es": "Diez anos"},\n}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert f"{PY}:2" in out
    assert "anos" in out and "años" in out


def test_unaccented_cion_ending_is_found_in_a_spanish_text(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"en": "The zzzzing of the data", "es": "La zzzzcion de los datos del banco"}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert "zzzzcion" in out and "zzzzción" in out


def test_unaccented_sion_ending_is_found_in_the_second_argument_of_a_helper(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'x = t("Revision", "Revision")\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert "Revisión" in out
    assert out.count("finding") >= 1


def test_a_word_inside_an_identifier_is_code_not_spanish_text(guard, tmp_path, capsys):
    """The engine's reason quotes the attribute spec(test_id).decision in its Spanish sentence; the word is code."""
    _write(tmp_path, DOC, '{"reason": {"en": "the kind is spec(test_id).decision where", '
                          '"es": "el tipo es spec(test_id).decision donde la prueba está registrada"}}')
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 0, out
    _write(tmp_path, DOC, '{"rows": [{"en": "the model hmda-logistic-decision is the champion", '
                          '"es": "el modelo hmda-logistic-decision es el campeón del caso"}]}')
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 0, out
    _write(tmp_path, DOC, '{"reason": {"en": "the decision of the bank", "es": "la decision del banco y su situacion"}}')
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 1 and "decisión" in out


def test_a_correct_spanish_text_passes(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"en": "Ten years", "es": "Diez años de exposición, según el método ¿cuánto?"}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_an_english_text_with_cion_and_sion_words_is_ignored(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"en": "The version and precision of the decision", "es": "La versión del modelo"}\n'
                        'U = "Coercion is not a Spanish text here, and the supervision is shown for the whole population."\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_an_es_slot_that_copies_the_english_on_purpose_is_not_a_finding(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"en": "The rule of the decision Q4", "es": "The rule of the decision Q4"}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_an_f_string_is_checked_on_its_literal_parts_and_keeps_its_placeholders(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'n = 10\nT = {"en": f"A swap of {n} years", "es": f"Un swap a {n} anos y {n:,.2f} puntos"}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert "anos" in out and "años" in out
    assert "{n" not in out


def test_an_identifier_like_string_is_not_a_text(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'KEYS = ["exposicion_total", "cmf-informe-desempeno-2026-08.pdf", "https://x.cl/estadisticas/a.pdf"]\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_a_docstring_is_not_a_text(guard, tmp_path, capsys):
    _write(tmp_path, PY, '"""Evaluacion de los anos, kept as the English module note says."""\n\n\ndef f():\n    """La simulacion historica."""\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_the_case_of_the_word_is_kept_in_the_fix(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'A = {"es": "Simulacion historica"}\nB = {"es": "ANOS"}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert "Simulación" in out and "histórica" in out and "AÑOS" in out


def test_a_frontend_object_with_an_es_field_and_a_t_call_are_found(guard, tmp_path, capsys):
    _write(tmp_path, TSX, "const a = { en: 'Years', es: 'Los anos' };\n"
                          "const b = t('Evaluation', 'Evaluacion');\n"
                          "const c = t('Evaluation', 'Evaluación');\n"
                          "const d = `Plan ${n} del ${a ? 'ano' : 'anos'}`;\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert f"{TSX}:1" in out and f"{TSX}:2" in out
    assert f"{TSX}:3" not in out
    assert "Evaluación" in out
    assert f"{TSX}:4" in out  # the word list applies inside a template expression too


def test_a_frontend_es_suffix_field_is_a_spanish_text(guard, tmp_path, capsys):
    _write(tmp_path, TSX, "const a = {\n  title: 'Architecture',\n  body_es:\n    'Zzzzcion',\n};\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert f"{TSX}:4" in out and "Zzzzción" in out


def test_jsx_text_is_checked(guard, tmp_path, capsys):
    _write(tmp_path, TSX, "export const A = () => (\n  <p>\n    La proyeccion de los datos.\n  </p>\n);\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert f"{TSX}:3" in out and "proyección" in out


def test_frontend_tests_and_generated_files_are_not_scanned(guard, tmp_path, capsys):
    _write(tmp_path, "frontend/src/pages/X.test.tsx", "const a = { en: 'Years', es: 'Los anos' };\n")
    _write(tmp_path, "frontend/src/lib/contract.gen.ts", "export const A = { es: 'Los anos' };\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out


def test_a_json_config_es_value_is_found(guard, tmp_path, capsys):
    _write(tmp_path, "data-pipeline/config/planned.json", json.dumps([{"title": {"en": "Years", "es": "Los anos"}}]))
    code, out = _run(guard, tmp_path, capsys)
    assert code == 1
    assert "planned.json" in out and "años" in out


def test_documents_are_read_only_with_the_flag_and_only_their_es_values(guard, tmp_path, capsys):
    _write(tmp_path, DOC, json.dumps({"title": {"en": "Years and anos", "es": "Los anos"}, "note": {"en": "Plain", "es": "Los años"}}))
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 1
    assert "doc.json" in out and "años" in out
    assert out.count("anos") >= 1
    # the English value holding the same word is not a finding: one finding only
    assert "1 finding" in out


def test_documents_mode_does_not_read_the_code(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"es": "Los anos"}\n')
    _write(tmp_path, DOC, json.dumps({"es": "Los años"}))
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 0, out


def test_an_allow_entry_silences_one_finding_and_an_unused_entry_fails(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"es": "Los anos"}\n')
    allow = tmp_path / "allow.txt"
    allow.write_text(f"{PY} :: anos  # quotes a source name as written there\n", encoding="utf-8")
    code, out = _run(guard, tmp_path, capsys, "--allow", str(allow))
    assert code == 0, out
    _write(tmp_path, PY, 'T = {"es": "Los años"}\n')
    code, out = _run(guard, tmp_path, capsys, "--allow", str(allow))
    assert code == 1
    assert "unused allow entry" in out


def test_an_allow_entry_of_a_document_is_not_judged_without_documents(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"es": "Los años"}\n')
    allow = tmp_path / "allow.txt"
    allow.write_text("data/derived/contract/x.json :: decision  # a field name\n", encoding="utf-8")
    code, out = _run(guard, tmp_path, capsys, "--allow", str(allow))
    assert code == 0, out


def test_explicit_paths_are_scanned_instead_of_the_tree(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"es": "Los anos"}\n')
    _write(tmp_path, "data-pipeline/pipeline/cases/y.py", 'T = {"es": "Los años"}\n')
    code, out = _run(guard, tmp_path, capsys, "data-pipeline/pipeline/cases/y.py")
    assert code == 0, out


def test_the_guard_does_not_evaluate_code(guard, tmp_path, capsys):
    marker = tmp_path / "evaluated.txt"
    _write(tmp_path, PY, f'open({str(marker)!r}, "w").write("x")\nT = {{"es": "Los años"}}\n')
    _write(tmp_path, TSX, f"const a = (() => {{ require('fs').writeFileSync({str(marker)!r}, 'x'); return 'Los años'; }})();\n")
    code, out = _run(guard, tmp_path, capsys)
    assert code == 0, out
    assert not marker.exists()


def test_the_word_list_has_only_unaccented_keys_with_an_accented_fix(guard):
    pairs = guard.load_words(ROOT / "scripts" / "check_spanish_words.txt")
    assert len(pairs) > 300
    for key, fix in pairs.items():
        assert key == key.lower() and key.isascii(), key
        assert fix != key and guard.strip_accents(fix) == key, (key, fix)


def test_the_real_tree_is_clean(guard, capsys):
    code = guard.main(["--root", str(ROOT)])
    out = capsys.readouterr().out
    assert code == 0, out


# --- U16-F1: a Spanish field that copies the English ------------------------------------------------------------------

COPY_DOC = "data/derived/C98/copy.json"


def test_documents_find_an_es_that_equals_the_en_when_the_en_has_three_words(guard, tmp_path, capsys):
    _write(tmp_path, COPY_DOC, json.dumps({"note": {"en": "The reason is stated here", "es": "The reason is stated here"}}))
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 1
    assert f"{COPY_DOC}:" in out and "copies the English" in out
    assert "The reason is stated here" in out


def test_documents_accept_an_es_that_differs_and_a_short_name_that_is_the_same(guard, tmp_path, capsys):
    _write(tmp_path, COPY_DOC, json.dumps({
        "a": {"en": "The reason is stated here", "es": "La razón se declara aquí"},
        "b": {"en": "Banco Andino", "es": "Banco Andino"},
        "c": {"en": "P4 LightGBM", "es": "P4 LightGBM"},
    }))
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 0, out


def test_documents_accept_an_identifier_that_is_the_same_in_both_languages(guard, tmp_path, capsys):
    _write(tmp_path, COPY_DOC, json.dumps({
        "a": {"en": "lda-lognormal-truncated", "es": "lda-lognormal-truncated"},
        "b": {"en": "port-1000-1pct-rho12", "es": "port-1000-1pct-rho12"},
        "c": {"en": "<test_id>-null", "es": "<test_id>-null"},
        "e": {"en": "market.dynamic_quantile_test#2-alternative", "es": "market.dynamic_quantile_test#2-alternative"},
        "d": {"en": "The rule of the floor", "es": "The rule of the floor"},
    }))
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 1
    assert "The rule of the floor" in out
    assert "lda-lognormal" not in out and "port-1000" not in out and "test_id" not in out and "dynamic_quantile" not in out


def test_documents_accept_a_reviewed_reference_kept_as_published_but_not_the_same_text_elsewhere(guard, tmp_path, capsys):
    cite = "Kupiec (1995), J. Derivatives 3(2):73-84, doi:10.3905/jod.1995.407942"
    _write(tmp_path, COPY_DOC, json.dumps({
        "tests": [{"extras": {"reference_text": {"en": cite, "es": cite}}}],
        "note": {"en": cite, "es": cite},
    }))
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 1
    assert out.count("copies the English") == 1, out


def test_documents_skip_the_words_of_a_reviewed_reference_but_not_of_an_es_text(guard, tmp_path, capsys):
    cite = "Tong, Mues, Brown and Thomas (2016), Exposure at default models with and without the credit conversion factor"
    _write(tmp_path, COPY_DOC, json.dumps({
        "tests": [{"extras": {"reference_text": {"en": cite, "es": cite}}}],
        "note": {"en": "The conversion factor", "es": "El factor de conversion"},
    }))
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 1
    assert out.count("conversion -> ") == 1, out


def test_the_copy_check_is_for_documents_only(guard, tmp_path, capsys):
    _write(tmp_path, PY, 'T = {"en": "The reason is stated here", "es": "The reason is stated here"}\n')
    code, out = _run(guard, tmp_path, capsys)
    assert "copies the English" not in out


def test_a_copy_allow_entry_with_a_reason_silences_one_text(guard, tmp_path, capsys):
    _write(tmp_path, COPY_DOC, json.dumps({"n": {"en": "Source: ESMA CEREP tables", "es": "Source: ESMA CEREP tables"}}))
    _write(tmp_path, "scripts/check_spanish_copies.txt", f"{COPY_DOC} :: Source: ESMA CEREP tables  # the source's own wording, kept verbatim\n")
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 0, out


def test_a_copy_allow_entry_without_a_reason_is_refused(guard, tmp_path, capsys):
    _write(tmp_path, COPY_DOC, json.dumps({"n": {"en": "Source: ESMA CEREP tables", "es": "Source: ESMA CEREP tables"}}))
    _write(tmp_path, "scripts/check_spanish_copies.txt", f"{COPY_DOC} :: Source: ESMA CEREP tables\n")
    code, out = _run(guard, tmp_path, capsys, "--documents")
    assert code == 1
    assert "reason" in out


def test_the_copy_list_of_the_real_tree_has_a_reason_on_every_line(guard):
    path = ROOT / "scripts" / "check_spanish_copies.txt"
    assert path.exists()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"):
            assert "  # " in raw and raw.split("  # ", 1)[1].strip(), raw
