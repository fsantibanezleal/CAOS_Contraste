"""Every red test row is cited by an open finding (U16-R4 ruling 4, unit U16-F12g).

A case raises its findings from the tests its policy rates; a red light on any other test reached no finding, so the Findings
view answered "what the validation found" without it (R4 c07 N-M1, c08 N1, c10 Q1, c25 M1: 433 red rows of 24 (case, test) pairs
at 9a958d9). This step adds, to the findings of a document, one open finding per red test that no open finding cites:

- a test is cited when an open finding's evidence names it, alone or with a model and a segment (``test``, ``test@model``,
  ``test@model@segment``, ``test@-@segment``), so a case's own finding for that test always wins;
- the finding's evidence is every red row of the test by its full id (``test@model@segment``, ``test@model`` for a row of no
  segment, ``test@-@segment`` for a row of no model, the bare test id for a row of neither), rows with a model first;
- its title names the test and the models of its red rows as the web's names module does (``frontend/src/workbench/names/tests.ts``
  and ``models.gen.json``, so the product says one name per test and per model; at most three models, the others counted) and
  the count of its red rows, in both languages with the shell's number form; a test with no name is an error and a model with
  none is left to its evidence line, never a raw id on screen;
- its severity is the one a red light of that test carries in the case (``red_severity``).

``build_artifact`` runs it, so every case's bake adds the findings before its documents are validated and written.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

from .text import number

#: data-pipeline/pipeline/core/red_findings.py -> parents[3] = the repository root
NAMES_DIR = Path(__file__).resolve().parents[3] / "frontend" / "src" / "workbench" / "names"
NAMES_FILE = NAMES_DIR / "tests.ts"
MODELS_FILE = NAMES_DIR / "models.gen.json"
#: the models a title lists by name; the others are counted ("and 3 more models"), the evidence lines name every one
MAX_MODELS = 3
ID_PREFIX = "F-RED-"

#: the severity a red light carries where a case states no other: S2, as C06, C08, C10, C12, C14 and C20 rate a red test
DEFAULT_RED = "S2"
#: the cases' own policies, per test: C01 and C03 rate a red fit test (chi-square over grades, Hosmer-Lemeshow, Spiegelhalter) S3,
#: because on a large book it rejects deviations too small to matter (c01_retail_pd.SEVERITY, c03/variant.py SEVERITY); a red
#: paired DeLong test says a challenger ranks better, which C02 rates S3 (c02/findings.py F-CHALLENGER-GAP); C21's unconditional
#: z and Fisher tests of a gross disparity are an indicator only under the Interagency procedures, S4 (R4 ruling 4)
_FIT = ("pd.chi2_grades", "pd.hosmer_lemeshow", "pd.spiegelhalter")
RED_SEVERITY: dict[str, dict[str, str]] = {
    "C01": {**dict.fromkeys(_FIT, "S3"), "disc.delong": "S3"},
    "C02": {"disc.delong": "S3"},
    "C03": {**dict.fromkeys(_FIT, "S3"), "disc.delong": "S3"},
    "C21": {"fair.two_proportion_z": "S4", "fair.fisher_exact": "S4"},
}

_ENTRY = re.compile(r"^\s*'(?P<id>[^']+)':\s*\{\s*en:\s*'(?P<en>(?:[^'\\]|\\.)*)',\s*es:\s*'(?P<es>(?:[^'\\]|\\.)*)'\s*\},?\s*$")


def _unquote(s: str) -> str:
    return re.sub(r"\\(.)", r"\1", s)


@lru_cache(maxsize=1)
def catalog_names() -> dict[str, dict[str, str]]:
    """The bilingual name of every test the web names (``TEST_NAMES`` of the names module), read from its source."""
    out: dict[str, dict[str, str]] = {}
    for line in NAMES_FILE.read_text(encoding="utf-8").splitlines():
        m = _ENTRY.match(line)
        if m:
            out[m["id"]] = {"en": _unquote(m["en"]), "es": _unquote(m["es"])}
    if not out:
        raise ValueError(f"{NAMES_FILE}: no test name read")
    return out


@lru_cache(maxsize=1)
def model_names() -> dict[str, dict[str, dict[str, str]]]:
    """The web's name of every model of every case (``models`` of the names module's ``models.gen.json``)."""
    return json.loads(MODELS_FILE.read_text(encoding="utf-8"))["models"]


def model_name(case_id: str, model: Mapping[str, Any]) -> dict[str, str] | None:
    """A model by the web's name, else by the document's short title, when that is a name and not the id; None when neither."""
    for name in (model_names().get(case_id, {}).get(model["id"]), model.get("short_title")):
        if name and name.get("en") and name.get("es") and model["id"] not in (name["en"], name["es"]):
            return name
    return None  # an id written as its own name (C22's configurations, C11's rungs in the model block) is not a name


def red_severity(case_id: str, test_id: str) -> str:
    """The severity of a red light of ``test_id`` in ``case_id``."""
    return RED_SEVERITY.get(case_id, {}).get(test_id, DEFAULT_RED)


def row_id(row: Mapping[str, Any]) -> str:
    """The full evidence id of one test row, as ``manifest._check_tests`` registers it."""
    tid, model, seg = row["test_id"], row.get("model_id"), row.get("segment")
    if model is not None:
        return f"{tid}@{model}@{seg}" if seg is not None else f"{tid}@{model}"
    return f"{tid}@-@{seg}" if seg is not None else tid


def cited_rows(findings: Sequence[Mapping[str, Any]], tests: Sequence[Mapping[str, Any]]) -> set[str]:
    """The full ids of the test rows the open findings cite (R5: every red ROW is cited, not every test). An evidence id cites the
    rows it resolves to: ``test@model@segment`` and ``test@-@segment`` that row; ``test@model`` the model's portfolio row, else its
    row of no segment; a bare ``test`` its only row, else its row of no model and no segment. ``design:``, ``contract:`` and
    ``rate:`` evidence cites no test row."""
    by_test: dict[str, list[Mapping[str, Any]]] = {}
    for r in tests:
        by_test.setdefault(r["test_id"], []).append(r)
    out: set[str] = set()
    for f in findings:
        if f.get("status") != "open":
            continue
        for e in f.get("evidence") or []:
            if e.startswith(("design:", "contract:", "rate:")):
                continue
            parts = e.split("@")
            rows = by_test.get(parts[0], [])
            if len(parts) == 3:
                model = None if parts[1] == "-" else parts[1]
                hit = [r for r in rows if r.get("model_id") == model and r.get("segment") == parts[2]]
            elif len(parts) == 2:
                mine = [r for r in rows if r.get("model_id") == parts[1]]
                hit = [r for r in mine if r.get("segment") == "portfolio"] or [r for r in mine if r.get("segment") is None]
            else:
                hit = rows if len(rows) == 1 else [r for r in rows if r.get("model_id") is None and r.get("segment") is None]
            out.update(row_id(r) for r in hit)
    return out


def _title(name: Mapping[str, str], n: int, models: list[Mapping[str, str]]) -> dict[str, str]:
    out = {}
    shown, more = models[:MAX_MODELS], len(models) - MAX_MODELS
    for lang in ("en", "es"):
        count = number(n, lang=lang)
        listed = "; ".join(m[lang] for m in shown)  # a model name may hold a comma ("CAViaR, asymmetric slope")
        if more > 0:
            listed += (f" and {number(more, lang=lang)} more model{'s' if more > 1 else ''}" if lang == "en"
                       else f" y {number(more, lang=lang)} modelo{'s' if more > 1 else ''} más")
        who = f" ({listed})" if shown else ""
        if lang == "en":
            rows = "row" if n == 1 else "rows"
            out[lang] = f"{name[lang]}: red on {count} {rows}{who} that no other finding cites"
        else:
            rows = "fila" if n == 1 else "filas"
            out[lang] = f"{name[lang]}: en rojo en {count} {rows}{who} que ningún otro hallazgo cita"
    return out


def red_findings(case_id: str, tests: Sequence[Mapping[str, Any]], findings: Sequence[Mapping[str, Any]],
                 models: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The findings to add: one per test with red rows no open finding cites, citing those rows, in test-id order (none when every red row is cited)."""
    cited = cited_rows(findings, tests)
    red: dict[str, list[Mapping[str, Any]]] = {}
    for r in tests:
        if r.get("light") == "red" and row_id(r) not in cited:
            red.setdefault(r["test_id"], []).append(r)
    if not red:
        return []
    names = catalog_names()
    named = {m["id"]: model_name(case_id, m) for m in models}
    taken = {f.get("id") for f in findings}
    out, k = [], 0
    for tid in sorted(red):
        if tid not in names:
            raise ValueError(f"{case_id}: the red test {tid!r} has no name in {NAMES_FILE.name}: add it there, never print the id")
        rows = sorted(red[tid], key=lambda r: (r.get("model_id") is None, row_id(r)))
        # the models by their names; a row whose model has no name here (not in the document's model block) is named by its
        # evidence line, never by its id in the title
        model_ids = [m for m in dict.fromkeys(r.get("model_id") for r in rows) if m is not None and named.get(m)]
        k += 1
        while f"{ID_PREFIX}{k:02d}" in taken:
            k += 1
        out.append({"id": f"{ID_PREFIX}{k:02d}", "severity": red_severity(case_id, tid), "status": "open",
                    "evidence": list(dict.fromkeys(row_id(r) for r in rows)),
                    "title": _title(names[tid], len(rows), [named[m] for m in model_ids])})
    return out
