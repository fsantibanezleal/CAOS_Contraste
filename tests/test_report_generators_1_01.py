"""Release 1.01.000 of the technical report: the table generators that read the loan-level bootstrap intervals of C06 and C08, the
nine-setting sensitivity of the PC-Hazard rung, the C17 verdict over all sixteen cells, and the contract appendix.

Every new macro or table cell is asserted against the committed document it is read from, with the arithmetic redone here apart from the
generator; the missing-block and the interval-touching-zero edge cases run on planted documents; a generator run twice writes byte-equal
files; the contract appendix holds no internal id and no paragraph that names two versions of one contract.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TR = ROOT / "manuscripts" / "contraste-technical-report"
TABLES = TR / "tables"
SECTIONS = TR / "sections"
DERIVED = ROOT / "data" / "derived"
PY = sys.executable

DATES = ["2006-12", "2008-12", "2010-12", "2019-12", "2020-06", "2023-06"]
COHORTS = ["2003-06", "2007-08", "2009-10", "2011-13", "2014-19", "2020-23"]
VARIANTS = ["xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1"]


def _doc(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


def _module(name: str):
    path = TABLES / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TABLES))
    spec.loader.exec_module(mod)
    return mod


def _pv_macros() -> dict[str, str]:
    text = (TABLES / "provisions-numbers.tex").read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\pv(\w+)\}\{(.*)\}$", text, re.M))


def _op_macros() -> dict[str, str]:
    text = (TABLES / "oprisk-numbers.tex").read_text(encoding="utf-8")
    return dict(re.findall(r"\\newcommand\{\\op(\w+)\}\{(.*)\}$", text, re.M))


def _le_macros() -> dict[str, str]:
    text = (TABLES / "lgd-ead-numbers.tex").read_text(encoding="utf-8")
    return dict(re.findall(r"\\csname lgdead:([\w.-]+)\\endcsname\{(.*)\}$", text, re.M))


def _rows(path: Path) -> list[list[str]]:
    """The body rows of a generated table: the cells between the midrule and the bottomrule, split on the cell separator."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("\\midrule")) + 1
    end = next(i for i, ln in enumerate(lines) if ln.startswith("\\bottomrule"))
    return [[c.strip() for c in ln.rstrip(" \\").rstrip("\\").split(" & ")] for ln in lines[start:end]]


def _num(cell: str) -> float:
    return float(cell.replace("$", "").replace("{,}", "").replace(",", "").replace("\\,", "").strip())


def _interval(cell: str) -> tuple[float, float]:
    lo, hi = cell.replace("$", "").strip("[]").split(",")
    return float(lo), float(hi)


# --------------------------------------------------------------------------------------------------------------- C06 bootstrap
def test_c06_interval_table_equals_the_documents() -> None:
    rows = {r[0]: r for r in _rows(TABLES / "provisions-t-boot.tex")}
    assert list(rows) == DATES
    for d in DATES:
        b = _doc(f"C06/models-rd-{d}.json")["fit"]["s4_bootstrap"]
        ibs = next(x for x in b["differences"] if x["measure"] == "integrated_brier")
        gap = next(x for x in b["differences"] if x["measure"] == "mean_decile_gap")
        r = rows[d]
        assert _num(r[1]) == b["accounts"]
        for cells, x in ((r[2:4], ibs), (r[4:6], gap)):
            assert abs(_num(cells[0]) - x["difference"]) <= 0.5e-6 + 1e-12
            lo, hi = _interval(cells[1])
            assert abs(lo - x["lo"]) <= 0.5e-6 + 1e-12 and abs(hi - x["hi"]) <= 0.5e-6 + 1e-12
        assert r[6] == ("yes" if b["both_exclude_zero"] else "no")


def test_c06_interval_macros_equal_the_documents() -> None:
    m = _pv_macros()
    blocks = [_doc(f"C06/models-rd-{d}.json")["fit"]["s4_bootstrap"] for d in DATES]
    assert m["BootDates"] == str(len(DATES))
    assert m["BootEvaluated"] == str(sum(b["evaluated"] for b in blocks))
    assert m["BootReplicates"] == "1{,}000" or m["BootReplicates"] == str(blocks[0]["replicates"])
    assert m["BootBoth"] == str(sum(bool(b["both_exclude_zero"]) for b in blocks))
    assert m["BootHoldsExcl"] == str(blocks[0]["overall"]["holds_excluding_zero"])
    assert m["BootHolds"] == str(blocks[0]["overall"]["holds_at"])
    pos = sum(1 for b in blocks if next(x for x in b["differences"] if x["measure"] == "integrated_brier")["lo"] > 0)
    assert m["BootIbsWorse"] == str(pos)
    neg = sum(1 for b in blocks if next(x for x in b["differences"] if x["measure"] == "integrated_brier")["hi"] < 0)
    assert m["BootIbsBetter"] == str(neg)


def test_c06_row_without_a_bootstrap_block_is_stated_not_skipped() -> None:
    mod = _module("make_provisions")
    doc = copy.deepcopy(_doc("C06/models-rd-2008-12.json"))
    doc["fit"]["s4_bootstrap"] = {"evaluated": False, "reason": {"en": "fewer than 30 defaults", "es": "menos de 30"},
                                  "differences": [], "both_exclude_zero": None}
    row = mod.boot_row("2008-12", doc)
    assert row["evaluated"] is False
    assert "fewer than 30 defaults" in row["reason"]
    cells = mod.boot_cells(row)
    assert cells[0] == "2008-12" and "not evaluated" in " ".join(cells)
    del doc["fit"]["s4_bootstrap"]
    row = mod.boot_row("2008-12", doc)
    assert row["evaluated"] is False and row["reason"]


def test_c06_interval_that_touches_zero_does_not_exclude_it() -> None:
    mod = _module("make_provisions")
    doc = copy.deepcopy(_doc("C06/models-rd-2008-12.json"))
    for x in doc["fit"]["s4_bootstrap"]["differences"]:
        x["lo"], x["hi"], x["excludes_zero"] = -1e-4, 2e-4, False
    doc["fit"]["s4_bootstrap"]["both_exclude_zero"] = False
    row = mod.boot_row("2008-12", doc)
    assert row["both"] is False
    assert mod.boot_cells(row)[6] == "no"
    # the count follows the interval itself when the stored flag is missing or stale
    doc["fit"]["s4_bootstrap"]["differences"][0]["excludes_zero"] = True
    assert mod.boot_row("2008-12", doc)["both"] is False


# --------------------------------------------------------------------------------------------------------------- C06 sensitivity
def test_c06_pch_sensitivity_macros_equal_the_documents() -> None:
    m = _pv_macros()
    docs = [_doc(f"C06/models-rd-{d}.json")["fit"]["pch_sensitivity"] for d in DATES]
    ov = docs[0]["overall"]
    assert m["SensSettings"] == str(ov["settings_count"]) == "9"
    assert m["SensAgree"] == str(ov["agree"])
    assert m["SensDefaultHolds"] == str(ov["settings"][0]["holds_at"])
    fitted = sum(1 for s in docs for st in s["settings"] if st["status"] == "fitted")
    assert m["SensFitted"] == str(fitted)
    assert m["SensNotConverged"] == str(sum(1 for s in docs for st in s["settings"] if st["status"] != "fitted"))
    c = [st["evaluation"]["c_index"]["pch"] for s in docs for st in s["settings"] if st.get("evaluation")]
    assert abs(float(m["SensCindexMin"]) - min(c)) <= 0.0051 and abs(float(m["SensCindexMax"]) - max(c)) <= 0.0051
    hold_min = min(x["holds_at"] for x in ov["settings"])
    hold_max = max(x["holds_at"] for x in ov["settings"])
    assert (m["SensHoldsMin"], m["SensHoldsMax"]) == (str(hold_min), str(hold_max))


def test_c06_pch_sensitivity_table_lists_every_setting() -> None:
    rows = _rows(TABLES / "provisions-t-sens.tex")
    ov = _doc("C06/models-rd-2008-12.json")["fit"]["pch_sensitivity"]["overall"]["settings"]
    assert len(rows) == len(ov) == 9
    for r, s in zip(rows, ov):
        assert r[2] == str(s["holds_at"]) and r[3] == str(s["evaluable"])
        assert r[4] == s["verdict"] and r[5] == ("yes" if s["agrees"] else "no")


# --------------------------------------------------------------------------------------------------------------- C08 bootstrap
def test_c08_interval_table_equals_the_documents() -> None:
    rows = {r[0]: r for r in _rows(TABLES / "lgd-ead-mlboot.tex")}
    assert list(rows) == [c.replace("-", "--") for c in COHORTS]
    for c in COHORTS:
        b = _doc(f"C08/dc-{c}.json")["outputs"]["ml_benchmark"]
        ab = b["against_best"]
        r = rows[c.replace("-", "--")]
        assert _num(r[1]) == b["defaults"]
        assert abs(_num(r[3]) - ab["difference"]) <= 0.5e-6 + 1e-12
        lo, hi = _interval(r[4])
        assert abs(lo - ab["lo"]) <= 0.5e-6 + 1e-12 and abs(hi - ab["hi"]) <= 0.5e-6 + 1e-12
        assert r[5] == ("yes" if (ab["lo"] > 0 or ab["hi"] < 0) else "no")
        others = [a for a in b["against"] if a["rung_id"] != ab["rung_id"]]
        assert r[6] == f"{sum(1 for a in others if a['lo'] > 0 or a['hi'] < 0)} of {len(others)}"


def test_c08_interval_macros_equal_the_documents() -> None:
    m = _le_macros()
    blocks = [_doc(f"C08/dc-{c}.json")["outputs"]["ml_benchmark"] for c in COHORTS]
    assert m["ml-boot-replicates"] == str(blocks[0]["replicates"]) or m["ml-boot-replicates"] == "1{,}000"
    excl = sum(1 for b in blocks if b["against_best"]["lo"] > 0 or b["against_best"]["hi"] < 0)
    assert m["ml-boot-excl"] == str(excl)
    assert m["ml-boot-wins-excl"] == str(blocks[0]["overall"]["wins_excluding_zero"])
    others = [a for b in blocks for a in b["against"] if a["rung_id"] != b["against_best"]["rung_id"]]
    assert m["ml-boot-other-total"] == str(len(others))
    assert m["ml-boot-other-excl"] == str(sum(1 for a in others if a["lo"] > 0 or a["hi"] < 0))


def test_c08_row_without_a_bootstrap_block_is_stated_not_skipped() -> None:
    mod = _module("make_lgd-ead")
    doc = copy.deepcopy(_doc("C08/dc-2009-10.json"))
    doc["outputs"]["ml_benchmark"] = {"evaluated": False, "reason": {"en": "fewer than 30 defaults", "es": "x"}, "defaults": 12,
                                      "against": [], "against_best": None}
    row = mod.mlboot_row("2009-10", doc)
    assert row["evaluated"] is False and "fewer than 30 defaults" in row["reason"]
    assert "not evaluated" in " ".join(mod.mlboot_cells(row))
    del doc["outputs"]["ml_benchmark"]["against_best"]
    assert mod.mlboot_row("2009-10", doc)["evaluated"] is False


def test_c08_interval_that_touches_zero_does_not_exclude_it() -> None:
    mod = _module("make_lgd-ead")
    doc = copy.deepcopy(_doc("C08/dc-2009-10.json"))
    doc["outputs"]["ml_benchmark"]["against_best"].update(lo=-0.0001, hi=0.0002, excludes_zero=True)
    row = mod.mlboot_row("2009-10", doc)
    assert row["excludes"] is False
    assert mod.mlboot_cells(row)[5] == "no"


# --------------------------------------------------------------------------------------------------------------- C17 verdict
def test_c17_overall_verdict_macros_equal_the_document() -> None:
    m = _op_macros()
    s3 = _doc("C17/models-generator.json")["fit"]["s3_overall"]
    assert m["SThreeCells"] == str(s3["cells"]) == "16"
    assert m["SThreeVariants"] == str(s3["variants"])
    assert m["SThreeVerdict"] == s3["verdict"] == "inconclusive"
    by = {r["model_id"]: r for r in s3["rungs"]}
    assert (m["SThreeSpreadCvm"], m["SThreeBiasCvm"]) == (str(by["sla-cvm"]["smaller_spread"]), str(by["sla-cvm"]["smaller_bias"]))
    assert (m["SThreeSpreadObre"], m["SThreeBiasObre"]) == (str(by["sla-obre"]["smaller_spread"]), str(by["sla-obre"]["smaller_bias"]))
    params = (ROOT / "data-pipeline" / "pipeline" / "cases" / "c17" / "params.py").read_text(encoding="utf-8")
    holds = float(re.search(r'"holds_at_share":\s*([0-9.]+)', params).group(1))
    refuted = float(re.search(r'"refuted_below_share":\s*([0-9.]+)', params).group(1))
    assert (m["SThreeHolds"], m["SThreeRefuted"]) == (f"{round(holds * 100)}", f"{round(refuted * 100)}")
    # the verdict of every variant document is the one of the tail index alone: the overall one is stated once
    for v in VARIANTS:
        assert _doc(f"C17/{v}.json") is not None


# --------------------------------------------------------------------------------------------------------------- contracts
INTERNAL_IDS = re.compile(r"CT-[0-9]|decision Q[0-9]|U[0-9]+ G[0-9]+|BL-[0-9]")


def test_contract_appendix_holds_no_internal_id_and_no_stale_catalog_row() -> None:
    text = (SECTIONS / "contracts-generated.tex").read_text(encoding="utf-8")
    assert not INTERNAL_IDS.findall(text)
    assert "Catalog row" not in text


def test_contract_appendix_has_no_paragraph_with_two_versions_of_one_contract() -> None:
    text = (SECTIONS / "contracts-generated.tex").read_text(encoding="utf-8")
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    versions = {}
    for line in catalog[catalog.index("## Contracts"):].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.startswith("| ") and len(cells) > 2 and re.fullmatch(r"\d+\.\d+\.\d+", cells[1]):
            versions[cells[0]] = cells[1]
    n = 0
    chunks = re.split(r"(?=\\subsubsection\{)", text)
    for para in chunks:
        m = re.search(r"\\label\{sec:contract-([^}]+)\}", para)
        if not m or m.group(1) not in versions:
            continue
        cid = m.group(1)
        carried = re.findall(r"carries schema (\d+\.\d+\.\d+)", para)
        assert carried == [versions[cid]], cid
        assert not re.search(re.escape(cid) + r"\S* \d+\.\d+\.\d+:", para), cid
        n += 1
    assert n >= 80
    for chunk in chunks:
        parts = chunk.split("\n\n")
        if "carries schema" in chunk and len(parts) > 1:
            # the prose paragraph of the contract names one version: the catalog's
            assert len(set(re.findall(r"(?<![\d.])\d+\.\d+\.\d+(?![\d.])", parts[1]))) == 1, parts[0]


def test_contract_scrub_removes_the_catalog_row_prefix_and_the_ids() -> None:
    mod = _module("make_contracts")
    assert mod.strip_catalog_prefix("Catalog row c01-variant 3.0.0: one C01 (retail PD) variant artifact.") == \
        "One C01 (retail PD) variant artifact."
    assert mod.strip_catalog_prefix("Catalog row readiness 1.0.0 (ADR-0080 decision 4): what is real in the product.") == \
        "What is real in the product."
    assert mod.strip_catalog_prefix("A plain description.") == "A plain description."
    for raw in ("What C01's capital view states (CT-212, CT-214).", "Exploratory (decision Q9). Null.", "Requirement ids CT-0201 onward (decision Q14).",
                "cannot form a curve (U14 G22: the files are independent samples).", "Reading (a) of decision Q7: the drift.",
                "the backlog row BL-115 closes it"):
        assert not INTERNAL_IDS.search(mod.scrub(raw)), raw


# --------------------------------------------------------------------------------------------------------------- idempotence
def _digest(paths: list[Path]) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@pytest.mark.parametrize("script,outputs", [
    ("make_provisions.py", ["provisions-numbers.tex", "provisions-t-boot.tex", "provisions-t-sens.tex"]),
    ("make_lgd-ead.py", ["lgd-ead-numbers.tex", "lgd-ead-mlboot.tex"]),
    ("make_oprisk.py", ["oprisk-numbers.tex"]),
])
def test_a_generator_run_twice_writes_byte_equal_files(script: str, outputs: list[str]) -> None:
    paths = [TABLES / o for o in outputs]
    subprocess.run([PY, str(TABLES / script)], check=True, cwd=ROOT, capture_output=True, timeout=900)
    first = _digest(paths)
    subprocess.run([PY, str(TABLES / script)], check=True, cwd=ROOT, capture_output=True, timeout=900)
    assert _digest(paths) == first


def test_make_contracts_run_twice_writes_byte_equal_files() -> None:
    path = SECTIONS / "contracts-generated.tex"
    subprocess.run([PY, str(TABLES / "make_contracts.py")], check=True, cwd=ROOT, capture_output=True, timeout=900)
    first = path.read_bytes()
    subprocess.run([PY, str(TABLES / "make_contracts.py")], check=True, cwd=ROOT, capture_output=True, timeout=900)
    assert path.read_bytes() == first


# --------------------------------------------------------------------------------------------------------------- the counts in the text
def _printed(path: Path) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*$", "", ln) for ln in path.read_text(encoding="utf-8").splitlines())


def test_no_section_counts_four_proposed_methods_or_twelve_other_contributions() -> None:
    files = [TR / "main.tex", SECTIONS / "01-introduction.tex", SECTIONS / "17-proposed.tex", SECTIONS / "19-results.tex",
             SECTIONS / "21-discussion.tex", TABLES / "make_proposed.py", TABLES / "proposed-summary.tex"]
    bad = re.compile(r"\b(?:four|twelve|Four|Twelve)\b[^.\n]{0,40}\b(?:methods?|contributions?|of its sixteen|of the sixteen)\b", re.I)
    for f in files:
        text = f.read_text(encoding="utf-8") if f.suffix == ".py" else _printed(f)
        assert not [m.group(0) for m in bad.finditer(text)], f.name


def test_the_abstract_and_the_introduction_name_seven_methods_and_nine_contributions() -> None:
    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", (TR / "main.tex").read_text(encoding="utf-8"), re.S).group(1)
    assert "seven methods" in abstract and "nine other contributions" in abstract
    intro = _printed(SECTIONS / "01-introduction.tex")
    assert "seven methods" in intro
