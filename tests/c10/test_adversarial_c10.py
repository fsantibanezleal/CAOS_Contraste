"""Adversarial checks of C10 (docs/design/features/c10/validation.md): each plants a defect and asserts the clean input passes and
the planted one is found."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pytest
from c10_invariants import hash_findings, label_findings, schema_findings, violations
from c10_support import ONE_TYPE, SAMPLE, SCALE, SEED

from pipeline.cases.c10 import CASE_C10, bake, fed, ladder, page, portfolios
from pipeline.cases.c10 import documents as docs
from pipeline.cases.c10 import params as P
from pipeline.pipeline import PipelinePaths


def text() -> str:
    return SAMPLE.read_text(encoding="latin-1")


def write_page(tmp: Path, body: str, name: str = "page.htm") -> Path:
    p = tmp / name
    p.write_text(body, encoding="latin-1")
    return p


def loan(built, vid="credit-cards") -> dict:
    return copy.deepcopy(built["variants"][vid])


# --- CT-1101 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_page_the_reader_does_not_know_is_refused(tmp_path: Path, table) -> None:
    t = text()
    assert fed.read_table(write_page(tmp_path, t, "clean.htm")).quarters[0] == "1985Q1"
    with pytest.raises(fed.ReaderError, match="neither a rate nor n.a."):
        fed.read_table(write_page(tmp_path, t.replace(">1.28&nbsp;<", ">oops<", 1), "cell.htm"))
    with pytest.raises(fed.ReaderError, match="headed"):
        fed.read_table(write_page(tmp_path, t.replace("C&amp;I loans", "Corporate loans", 1), "head.htm"))
    row = re.search(r"<tr>\s*<th id=\"date\d+\">1990:3</th>.*?</tr>", t, re.S).group(0)
    with pytest.raises(fed.ReaderError, match="twice"):
        fed.read_table(write_page(tmp_path, t.replace(row, row + row, 1), "dup.htm"))
    # the same page with the cells of every row in the reverse order reads the same series: columns are named by header id
    def reverse(m: re.Match) -> str:
        cells = re.findall(r"<td.*?</td>", m.group(0), re.S)
        head = re.search(r"<th id=\"date\d+\">.*?</th>", m.group(0), re.S).group(0)
        return "<tr>" + head + "".join(reversed(cells)) + "</tr>"

    shuffled = re.sub(r"<tr>\s*<th id=\"date\d+\">.*?</tr>", reverse, t, flags=re.S)
    assert shuffled != t
    again = fed.read_table(write_page(tmp_path, shuffled, "shuffled.htm"))
    assert again.series == table.series and again.absent == table.absent


# --- CT-1102 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_an_interpolated_quarter_is_found(table, built) -> None:
    clean = fed.annual_rates(table, "residential", 1985, 1991)
    assert clean[0].rate is None and clean[0].n_quarters == 0

    def interpolating(tab: fed.Table) -> fed.Table:    # a planted reader that fills every n.a. with the next number
        out = {}
        for col, vals in tab.series.items():
            filled = list(vals)
            for i in range(len(filled) - 1, -1, -1):
                if filled[i] is None:
                    filled[i] = next((v for v in filled[i + 1:] if v is not None), None)
            out[col] = tuple(filled)
        return fed.Table(tab.quarters, out, tab.updated, frozenset())

    planted = fed.annual_rates(interpolating(table), "residential", 1985, 1991)
    assert planted[0].rate is not None and planted[0].rate != clean[0].rate
    # the document whose gap year carries a number is found by the schema (a year with a missing quarter is null)
    doc = loan(built, "residential")
    row = next(r for r in doc["outputs"]["annual_rates"] if r["year"] == 1985)
    assert row["loss_rate"] is None and row["n_quarters"] == 0
    assert schema_findings("data/derived/C10/residential.json", doc) == []
    row.update(loss_rate=planted[0].rate, reason=None)
    assert schema_findings("data/derived/C10/residential.json", doc), "a number in a year the table lacks must fail the schema"
    doc2 = loan(built, "residential")
    doc2["outputs"]["data_status"]["missing_quarters"].pop()
    assert any("missing_quarters" in v for v in violations(doc2))


# --- CT-1103 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_fit_that_sees_an_evaluation_year_is_found(table) -> None:
    rows = fed.annual_rates(table, "credit-cards", 1985, 2012)
    clean = docs.fit_window_rates(rows)
    assert clean.size == 22
    docs.check_fit_input(range(1985, 2007))
    leaking = np.array([np.nan if r.rate is None else r.rate for r in rows if r.year <= 2007])
    assert leaking.size == 23
    with pytest.raises(ValueError, match="evaluation"):
        docs.check_fit_input(range(1985, 2008))
    assert docs.fit_series(clean, 7, 100).ml.rho != docs.fit_series(leaking, 7, 100).ml.rho    # the leak would change the fit


# --- CT-1104 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_number_not_from_the_engine_is_found(built, monkeypatch) -> None:
    from riskvalidation.portfolio import portfolio as pf

    doc = loan(built)
    assert violations(doc) == []
    c1 = next(r for r in doc["outputs"]["rungs"] if r["id"] == "c1-lhp")
    c1["measures"][1]["var"] *= 1.02                                  # a hand-edited VaR no longer recomputes from the calibration
    assert any("c1-lhp" in v for v in violations(doc))
    # the ladder takes its C1 measures from the engine: what the engine's function returns is what the rung carries
    real, seen = pf.lhp_measures, []

    def spy(*args, **kw):
        out = real(*args, **kw)
        seen.append(out)
        return out

    monkeypatch.setattr(pf, "lhp_measures", spy)
    lt = next(x for x in P.LOAN_TYPES if x["id"] == "credit-cards")
    lad = ladder.run_ladder(lt, 0.04, 0.05, portfolios.groups("credit-cards", 0.04, 0.05, ladder.Run.scaled(SCALE).thin), ladder.Run.scaled(SCALE))
    assert len(seen) >= 1
    got = next(r for r in lad.rungs if r["id"] == "c1-lhp")["measures"]
    assert got == [ladder.measure(m) for m in seen[0]]


# --- CT-1105 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_an_unlabelled_portfolio_is_found(built) -> None:
    doc = loan(built)
    assert label_findings(doc) == [] and schema_findings("data/derived/C10/credit-cards.json", doc) == []
    bad = copy.deepcopy(doc)
    bad["outputs"]["portfolio"]["label"] = "bank"
    assert schema_findings("data/derived/C10/credit-cards.json", bad) and label_findings(bad)
    bad = copy.deepcopy(doc)
    bad["provenance"]["inputs"] = [i for i in bad["provenance"]["inputs"] if i["source"] != "illustrative-portfolio"]
    assert label_findings(bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["portfolio"]["notice"]["en"] = "The portfolio of the bank."
    assert label_findings(bad)


# --- CT-1106 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_broken_ladder_is_found(built, monkeypatch) -> None:
    from riskvalidation.portfolio import importance

    doc = loan(built)
    assert violations(doc) == []
    bad = copy.deepcopy(doc)
    m = next(r for r in bad["outputs"]["rungs"] if r["id"] == "c2-gaussian-1f")["measures"][1]
    m["es"] = m["var"] * 0.9
    assert any("ES below VaR" in v for v in violations(bad))
    bad = copy.deepcopy(doc)
    r = next(r for r in bad["outputs"]["rungs"] if r["id"] == "c6-is-student-t")
    r["measures"] = copy.deepcopy(doc["outputs"]["rungs"][1]["measures"])
    assert any("did not run" in v for v in violations(bad))
    assert schema_findings("data/derived/C10/credit-cards.json", bad)
    # an importance-sampling estimate a long way from the plain Monte Carlo stops the ladder
    real = importance.weighted_var_es
    monkeypatch.setattr(importance, "weighted_var_es", lambda res, q: tuple(x * 3 if i < 2 else x for i, x in enumerate(real(res, q))))
    lt = next(x for x in P.LOAN_TYPES if x["id"] == "credit-cards")
    with pytest.raises(ladder.LadderError, match="importance-sampling"):
        ladder.run_ladder(lt, 0.04, 0.05, portfolios.groups("credit-cards", 0.04, 0.05, ladder.Run.scaled(SCALE).thin), ladder.Run.scaled(SCALE))


# --- CT-1107 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_euler_rows_that_do_not_add_up_are_found(built) -> None:
    doc = loan(built)
    assert violations(doc) == []
    bad = copy.deepcopy(doc)
    bad["outputs"]["euler"][0]["levels"][1]["rows"][0]["rc_es"] *= 1.5
    assert any("rc_es" in v for v in violations(bad))
    bad = copy.deepcopy(doc)
    bad["outputs"]["euler"][0]["levels"][1]["anchor"]["rows"][0]["rc_var"] *= 1.2
    assert any("anchor" in v for v in violations(bad))
    bad = copy.deepcopy(doc)
    lv = next(x for x in bad["outputs"]["granularity"]["levels"] if x["q"] == 0.999)
    lv["delta"] = 1.0867
    assert any("delta" in v for v in violations(bad))


# --- CT-1108 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_grid_without_its_known_correlation_is_found(built) -> None:
    doc = copy.deepcopy(built["variants"]["grid-22"])
    assert violations(doc) == [] and schema_findings("data/derived/C10/grid-22.json", doc) == []
    bad = copy.deepcopy(doc)
    del bad["outputs"]["cells"][0]["known_rho"]
    assert schema_findings("data/derived/C10/grid-22.json", bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["cells"][0]["known_rho"] = 0.05
    assert violations(bad)
    bad = copy.deepcopy(doc)
    bad["outputs"]["generator"]["null_rho"] = 0.13
    assert any("null_rho" in v for v in violations(bad))


# --- CT-1109 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_different_seed_gives_different_bytes(table, raw) -> None:
    a = bake.build(42, 0.002, table, raw, only=ONE_TYPE, lengths=())
    b = bake.build(43, 0.002, table, raw, only=ONE_TYPE, lengths=())
    ja, jb = (json.dumps(x["variants"], sort_keys=True) for x in (a, b))
    assert ja != jb
    assert hashlib.sha256(ja.encode()).digest() != hashlib.sha256(jb.encode()).digest()


# --- CT-1110 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_document_failing_its_schema_or_its_hash_is_found(tmp_path: Path) -> None:
    CASE_C10.bake(SEED, PipelinePaths.from_output(tmp_path), None, 0.002, page=SAMPLE, only=ONE_TYPE, lengths=())
    assert hash_findings(tmp_path) == []
    doc = json.loads((tmp_path / "C10" / "credit-cards.json").read_text(encoding="utf-8"))
    del doc["outputs"]["backtest"]
    assert schema_findings("data/derived/C10/credit-cards.json", doc)
    path = tmp_path / "C10" / "credit-cards.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert any("credit-cards.json" in f for f in hash_findings(tmp_path))


# --- CT-1111 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_page_that_is_not_the_pinned_one_is_refused(tmp_path: Path, table, built) -> None:
    other = write_page(tmp_path, text() + "<!-- another per-request token -->", "token.htm")   # other bytes, same numbers
    t = fed.read_table(other)
    bake.check_raw(other, t, fed.raw_record(other))
    row = re.search(r"<tr>\s*<th id=\"date\d+\">2000:1</th>.*?</tr>", text(), re.S).group(0)
    revised = write_page(tmp_path, text().replace(row, re.sub(r">[0-9]+\.[0-9]{2}&nbsp;<", ">9.99&nbsp;<", row)), "revised.htm")
    with pytest.raises(bake.RawError, match="revised"):
        bake.check_raw(revised, fed.read_table(revised), fed.raw_record(revised))
    doc = loan(built, "residential")
    assert next(i for i in doc["provenance"]["inputs"] if i["source"] == "fed-chargeoff")["files"]
    doc["provenance"]["inputs"] = [i for i in doc["provenance"]["inputs"] if i["source"] != "fed-chargeoff"]
    assert not any(i["source"] == "fed-chargeoff" for i in doc["provenance"]["inputs"])


# --- CT-1112 ----------------------------------------------------------------------------------------------------------------


def test_adversarial_a_page_block_that_differs_from_the_documents_is_found() -> None:
    root = Path(__file__).resolve().parents[2]
    page_text = (root / "docs" / "cases" / "C10.md").read_text(encoding="utf-8")
    block = page_text.split(page.MARK_START, 1)[1].split(page.MARK_END, 1)[0].strip("\n")
    fresh = page.results_block(root / "data" / "derived").strip("\n")
    assert block == fresh
    assert block.replace("0.1", "0.2", 1) != fresh
    assert page.claim_findings(page_text) == []
    claim = page_text + "\nThe table shows a bank's real portfolio of loans.\n"
    assert any("bank's" in f for f in page.claim_findings(claim))
    assert page.claim_findings("A page about the Federal Reserve data only.")
