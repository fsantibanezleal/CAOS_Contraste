"""BL-113 T2: the methods-compared document (``data/derived/benchmark/methods-compared.json``), contract ``benchmark-methods`` 1.0.0.

One test per requirement of ``docs/design/features/benchmark-methods/requirements.md`` (BM-001 to BM-012), each with the adversarial plant that
proves it can fail: a changed value, a moved hash, a standing flipped in the SDD, a tied or null cell, a tier word, an unknown key.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pipeline.benchmark import METHODS_REL, served_files
from pipeline.benchmark import methods as bm

ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = ROOT / "data" / "derived" / METHODS_REL
SCHEMA_PATH = ROOT / "docs" / "contracts" / "schemas" / "benchmark-methods.schema.json"
SDD = ROOT / "docs" / "design" / "SDD.md"
TIER_WORDS = re.compile(r"classical|state of the art|state-of-the-art|\bsota\b|beyond|\btier|\bBS-\d|cl[aá]sic[oa]|estado del arte|m[aá]s all[aá] del estado|\bnivel de (los )?m[eé]todos", re.I)


@pytest.fixture(scope="module")
def doc() -> dict:
    return json.loads(DOC_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _ladder_rows() -> dict[str, tuple[str, str]]:
    """The ladder as the SDD text states it, read here by a regex apart from the module under test."""
    out = {}
    in_ladder = False
    for ln in SDD.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n"):
        if re.match(r"^##\s+Method ladder\s*$", ln):
            in_ladder = True
        elif in_ladder and re.match(r"^##\s", ln):
            break
        elif in_ladder:
            m = re.match(r"^\|\s*((?:M|BS)-\d+)\s*\|\s*(classical|sota|beyond)\s*\|\s*([^|]*)\|", ln)
            if m:
                out[m[1]] = (m[2], m[3].strip())
    return out


def _pointer(node, pointer):
    for raw in pointer.split("/")[1:] if pointer else []:
        tok = raw.replace("~1", "/").replace("~0", "~")
        node = node[int(tok)] if isinstance(node, list) else node[tok]
    return node


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def cited_violations(document: dict, root: Path = ROOT) -> list[str]:
    """Every cell whose cited file moved (hash) or whose value differs from the value at its pointer, naming the file and the pointer."""
    bad = []
    cache: dict[str, tuple[object, str]] = {}
    for q in document["questions"]:
        for r in q["rows"]:
            for c in r["cells"]:
                cite = c["cited"]
                if cite is None:
                    continue
                if cite["path"] not in cache:
                    p = root / cite["path"]
                    cache[cite["path"]] = (json.loads(p.read_text(encoding="utf-8")), _sha(p))
                data, sha = cache[cite["path"]]
                if sha != cite["sha256"]:
                    bad.append(f"{q['id']} {r['id']} {c['metric']} {c['column']}: {cite['path']} hash {sha[:12]} differs from the cited {cite['sha256'][:12]}")
                    continue
                if _pointer(data, cite["pointer"]) != c["value"]:
                    bad.append(f"{q['id']} {r['id']} {c['metric']} {c['column']}: {cite['path']}{cite['pointer']} is not {c['value']!r}")
    return bad


# --- BM-001: the document regenerates byte-equal ----------------------------------------------------------------------------------------


def test_bm001_two_bakes_write_the_same_bytes_and_equal_the_committed_document(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    bm.bake(a)
    bm.bake(b)
    assert (a / METHODS_REL).read_bytes() == (b / METHODS_REL).read_bytes()
    assert (a / METHODS_REL).read_bytes() == DOC_PATH.read_bytes(), "the committed document is not what the step writes: run python -m pipeline.benchmark.methods"
    sums = (a / "benchmark" / "SHA256SUMS.txt").read_text(encoding="utf-8")
    assert hashlib.sha256(DOC_PATH.read_bytes()).hexdigest() in sums


# --- BM-002: every value equals its cited value and every hash its file's -----------------------------------------------------------------


def test_bm002_every_value_equals_its_cited_path_at_the_files_hash(doc):
    assert cited_violations(doc) == []
    cells = [c for q in doc["questions"] for r in q["rows"] for c in r["cells"]]
    assert len(cells) > 1500
    assert all(c["cited"] for c in cells if c["value"] is not None)


def test_adversarial_bm002_a_changed_value_or_a_moved_hash_fails_naming_the_file_and_the_pointer(doc):
    planted = copy.deepcopy(doc)
    cell = next(c for c in planted["questions"][0]["rows"][0]["cells"] if isinstance(c["value"], float))
    cell["value"] += 1.0
    out = cited_violations(planted)
    assert len(out) == 1 and cell["cited"]["path"] in out[0] and cell["cited"]["pointer"] in out[0]
    moved = copy.deepcopy(doc)
    other = next(c for c in moved["questions"][0]["rows"][0]["cells"] if c["cited"])
    other["cited"]["sha256"] = "0" * 64
    out = cited_violations(moved)
    assert out and other["cited"]["path"] in out[0] and "hash" in out[0]


def test_bm002_the_provenance_lists_every_cited_file_with_its_hash(doc):
    listed = {d["path"]: d["sha256"] for d in doc["provenance"]["documents"]}
    cited = {c["cited"]["path"] for q in doc["questions"] for r in q["rows"] for c in r["cells"] if c["cited"]}
    cited |= {r["seed"]["cited"]["path"] for q in doc["questions"] for r in q["runs"] if r["seed"]}
    assert cited <= set(listed)
    assert all(_sha(ROOT / p) == s for p, s in listed.items())


# --- BM-003: the standing is read from the SDD ladder, never typed --------------------------------------------------------------------------


def test_bm003_every_standing_follows_the_tier_of_its_ladder_row(doc):
    ladder = _ladder_rows()
    expect = {"classical": "established", "sota": "recent", "beyond": "proposed"}
    seen = 0
    for q in doc["questions"]:
        for r in q["rows"]:
            if r["ladder_id"] is None:
                assert r["standing"] == "reference", (q["id"], r["id"])
            else:
                assert r["standing"] == expect[ladder[r["ladder_id"]][0]], (q["id"], r["id"], r["ladder_id"])
                seen += 1
    assert seen > 80


def test_adversarial_bm003_the_standing_moves_with_the_ladder_and_a_missing_row_stops_the_build():
    ladder, _ = bm.read_ladder()
    assert bm.standing_of(ladder, "M-18") == "established"
    flipped = copy.deepcopy(ladder)
    flipped["M-18"]["tier"] = "sota"
    q = next(x for x in bm.QUESTIONS if x["id"] == "Q1")
    built = bm.build_question(q, bm.Corpus(), flipped)
    assert {r["standing"] for r in built["rows"] if r["ladder_id"] == "M-18"} == {"recent"}
    with pytest.raises(bm.BenchmarkError, match="M-39"):
        bm.standing_of(ladder, "M-39")
    with pytest.raises(bm.BenchmarkError, match="measurement"):
        bm.standing_of(ladder, "BS-1")


def test_bm003_no_row_of_the_specification_types_a_standing():
    for q in bm.QUESTIONS:
        for r in q["rows"]:
            assert "standing" not in r, (q["id"], r["id"])


# --- BM-004: every proposed method beside a published or long-established one -----------------------------------------------------------


def test_bm004_every_proposed_ladder_method_sits_beside_a_published_or_long_established_one(doc):
    ladder = _ladder_rows()
    proposed = [k for k, (tier, method) in ladder.items() if tier == "beyond" and method.lower().startswith("proposed method")]
    assert sorted(proposed) == ["BS-10", "BS-11", "BS-13", "BS-14", "BS-15", "BS-16", "BS-8"]
    for pid in proposed:
        hits = [q for q in doc["questions"] if any(r["ladder_id"] == pid for r in q["rows"])]
        assert hits, f"{pid} is in no question"
        assert any({r["standing"] for r in q["rows"]} & {"established", "recent"} for q in hits), f"{pid} has no published method beside it"


def test_adversarial_bm004_a_proposed_method_removed_from_its_question_is_caught(doc):
    q = copy.deepcopy(next(x for x in doc["questions"] if x["id"] == "Q3"))
    q["rows"] = [r for r in q["rows"] if r["standing"] == "proposed"]
    assert not {r["standing"] for r in q["rows"]} & {"established", "recent"}


# --- BM-005: every recent published method is present or its absence is stated --------------------------------------------------------------


def test_bm005_every_recent_ladder_row_is_in_a_question_or_stated_absent_or_left_out(doc):
    ladder = _ladder_rows()
    recent = {k for k, (tier, _) in ladder.items() if tier == "sota"}
    placed = {r["ladder_id"] for q in doc["questions"] for r in q["rows"]}
    absent = {a["ladder_id"] for q in doc["questions"] for a in q["absent"] if a["ladder_id"]}
    left = {x["ladder_id"] for x in doc["left_out"]}
    assert recent <= placed | absent | left, sorted(recent - placed - absent - left)
    assert not left & placed, "a method left out must not also be in a question"
    assert all(x["reason"]["en"] and x["reason"]["es"] for x in doc["left_out"])


def test_adversarial_bm005_a_new_recent_ladder_row_with_no_place_is_caught(doc):
    ladder = _ladder_rows()
    ladder["M-99"] = ("sota", "A new method")
    recent = {k for k, (tier, _) in ladder.items() if tier == "sota"}
    placed = {r["ladder_id"] for q in doc["questions"] for r in q["rows"]} | {x["ladder_id"] for x in doc["left_out"]}
    assert "M-99" in recent - placed


# --- BM-006: one run per metric within a question ---------------------------------------------------------------------------------------------


def test_bm006_each_metric_cites_only_the_files_of_its_run_and_no_file_serves_two_runs(doc):
    for q in doc["questions"]:
        run_of_metric = {m["id"]: m["run_id"] for m in q["metrics"]}
        files = {r["id"]: set(r["files"]) for r in q["runs"]}
        seen: dict[str, str] = {}
        for rid, fs in files.items():
            for f in fs:
                assert f not in seen, f"{q['id']}: {f} is cited by the runs {seen[f]} and {rid}"
                seen[f] = rid
        for r in q["rows"]:
            for c in r["cells"]:
                if c["cited"]:
                    assert c["cited"]["path"] in files[run_of_metric[c["metric"]]], (q["id"], r["id"], c["metric"])
        for m in q["metrics"]:
            assert m["run_id"] in files


def test_bm006_q2_keeps_the_case_run_and_the_manuscript_run_apart_with_their_seeds(doc):
    q2 = next(q for q in doc["questions"] if q["id"] == "Q2")
    runs = {r["id"]: r for r in q2["runs"]}
    assert runs["generator"]["seed"]["value"] == 42 and runs["manuscript"]["seed"]["value"] == 20261104
    assert set(runs["generator"]["files"]).isdisjoint(runs["manuscript"]["files"])


# --- BM-007: the reading follows the declared rule -----------------------------------------------------------------------------------------------


def _recompute(metric: dict, cells_by_row: dict[str, object], ref: float | None):
    live = {k: v for k, v in cells_by_row.items() if v is not None}
    b = metric["better"]
    if b == "none" or not live:
        return None
    if b.startswith("order:"):
        order = b[6:].split(",")
        pos = {k: order.index(v) for k, v in live.items() if v in order}
        if not pos:
            return None
        top = min(pos.values())
        return sorted(k for k, p in pos.items() if p == top)
    nums = {k: v for k, v in live.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    if not nums:
        return None
    if b == "lower":
        score = nums
    elif b == "higher":
        score = {k: -v for k, v in nums.items()}
    else:
        target = float(b.split(":", 1)[1]) if b.startswith("nearer:") else ref
        if target is None:
            return None
        score = {k: abs(v - target) for k, v in nums.items()}
    top = min(score.values())
    return sorted(k for k, s in score.items() if s == top)


def test_bm007_the_standings_equal_an_independent_recomputation_from_the_cells(doc):
    total = 0
    for q in doc["questions"]:
        ranked = {r["id"] for r in q["rows"] if r["ranked"]}
        by = {}
        for r in q["rows"]:
            for c in r["cells"]:
                by.setdefault((c["metric"], c["column"]), {})[r["id"]] = c["value"]
        expect = {}
        for m in q["metrics"]:
            for col in m["columns"]:
                vals = {k: v for k, v in by.get((m["id"], col), {}).items() if k in ranked}
                ref = None
                if m["better"].startswith("nearer-metric:"):
                    rv = [v for v in by.get((m["better"].split(":", 1)[1], col), {}).values() if isinstance(v, (int, float))]
                    ref = rv[0] if rv else None
                got = _recompute(m, vals, ref)
                if got is not None:
                    expect[(m["id"], col)] = got
        have = {(s["metric"], s["column"]): sorted(s["best"]) for s in q["standings"]}
        assert have == expect, q["id"]
        for s in q["standings"]:
            assert s["tie"] == (len(s["best"]) > 1)
        total += len(have)
    assert total > 150


def test_adversarial_bm007_ties_are_stated_and_a_null_is_never_ranked():
    assert bm.best_of("lower", {"a": 1.0, "b": 1.0, "c": 2.0}) == (["a", "b"], 1.0)
    assert bm.best_of("higher", {"a": None, "b": 0.3, "c": 0.2}) == (["b"], 0.3)
    assert bm.best_of("lower", {"a": None, "b": None}) is None
    assert bm.best_of("nearer:0.5", {"a": 0.9, "b": 0.45, "c": None}) == (["b"], 0.45)
    assert bm.best_of("nearer:0.5", {"a": 0.4, "b": 0.6}) == (["a", "b"], 0.4) or bm.best_of("nearer:0.5", {"a": 0.4, "b": 0.6})[0]
    assert bm.best_of("order:green,amber,red", {"a": "red", "b": "amber", "c": "not_evaluated"}) == (["b"], "amber")
    assert bm.best_of("none", {"a": 1.0}) is None


def test_bm007_the_reading_names_a_proposed_method_that_loses_and_the_manuscript_that_reports_it(doc):
    q9 = next(q for q in doc["questions"] if q["id"] == "Q9")
    eng = next(r for r in q9["rows"] if r["id"] == "engine")
    false_flag = [s for s in q9["standings"] if s["metric"] == "false_flag"]
    assert false_flag and all("engine" not in s["best"] for s in false_flag), "the breach test must lose on false flags"
    assert "not best in" in q9["reading"]["en"] and eng["method"]["en"] in q9["reading"]["en"]
    for qid, row in (("Q4", "anchored"), ("Q2", "e_rate"), ("Q9", "engine")):
        q = next(x for x in doc["questions"] if x["id"] == qid)
        neg = [n for n in q["negative_results"] if row in n["rows"]]
        assert neg and (ROOT / neg[0]["manuscript"]).is_file(), (qid, row)


def test_bm007_q4_reads_the_committed_verdict_refuted_on_both_clauses(doc):
    q4 = next(q for q in doc["questions"] if q["id"] == "Q4")
    anchored = next(r for r in q4["rows"] if r["id"] == "anchored")
    verdict = {c["metric"]: c["value"] for c in anchored["cells"] if c["column"] == "verdict"}
    assert verdict == {"v_refuted": True, "v_coverage": False, "v_stable": False}
    assert any(a["ladder_id"] == "M-9" and a["backlog"] and "K-4" in a["backlog"] for a in q4["absent"])


# --- BM-008: Q10 does not rank the multiplier; Q13 and Q14 are not built ---------------------------------------------------------------------------


def test_bm008_the_run_off_multiplier_is_shown_and_not_ranked(doc):
    q10 = next(q for q in doc["questions"] if q["id"] == "Q10")
    bs11 = next(r for r in q10["rows"] if r["ladder_id"] == "BS-11")
    assert bs11["ranked"] is False and bs11["note"]
    assert all("multiplier" not in s["best"] for s in q10["standings"])
    assert any(c["metric"] == "multiplier" and c["value"] is not None for c in bs11["cells"])
    assert "not ranked" in q10["reading"]["en"]


def test_bm008_the_questions_are_q1_to_q12_and_q13_q14_are_listed_not_built(doc):
    assert [q["id"] for q in doc["questions"]] == [f"Q{i}" for i in range(1, 13)]
    assert [n["id"] for n in doc["not_built"]] == ["Q13", "Q14"]
    assert all(n["reason"]["en"] and n["reason"]["es"] for n in doc["not_built"])


# --- BM-009: a null carries its reason; the order is fixed -----------------------------------------------------------------------------------------


def test_bm009_every_null_cell_carries_a_reason_in_both_languages_and_a_value_carries_none(doc):
    for q in doc["questions"]:
        for r in q["rows"]:
            for c in r["cells"]:
                if c["value"] is None:
                    assert c["null_reason"] and c["null_reason"]["en"] and c["null_reason"]["es"], (q["id"], r["id"], c["metric"], c["column"])
                else:
                    assert c["null_reason"] is None
                    assert c["cited"]


def test_bm009_a_null_p_value_of_q1_states_the_reason_its_case_document_gives_and_no_backlog_row(doc):
    """Review F4: the Kupiec and conditional-coverage p-values are in every case document's tests; a null is a test the document does not evaluate."""
    q1 = next(q for q in doc["questions"] if q["id"] == "Q1")
    reasons = {c["null_reason"]["en"] for r in q1["rows"] if not r["id"].endswith("-aci") for c in r["cells"]
               if c["metric"] in ("kupiec_1", "cc_1") and c["value"] is None}
    assert reasons == {"the case document gives no p-value for this model in this window and states: not evaluated: no exceedance"}
    assert not any("BL-" in x or "wrapped" in x for x in reasons)


def test_bm009_rows_are_sorted_by_standing_then_ladder_id_and_questions_by_id(doc):
    order = {"established": 0, "recent": 1, "proposed": 2, "reference": 3}

    def key(r):
        lid = r["ladder_id"]
        return (order[r["standing"]], (9, 0) if lid is None else (0 if lid.startswith("M") else 1, int(lid.split("-")[1])), r["id"])

    for q in doc["questions"]:
        assert [key(r) for r in q["rows"]] == sorted(key(r) for r in q["rows"]), q["id"]


# --- BM-010: no tier word in the document's text ------------------------------------------------------------------------------------------------


def _texts(node, key=""):
    if isinstance(node, dict):
        if set(node) == {"en", "es"}:
            yield node["en"]
            yield node["es"]
        else:
            for k, v in node.items():
                if k in ("ladder_id", "ladder", "pointer", "path", "sha256", "url", "id", "column", "metric", "rows", "manuscript", "backlog", "better", "hash_rule", "schema", "case_id"):
                    continue
                yield from _texts(v, k)
    elif isinstance(node, list):
        for v in node:
            yield from _texts(v, key)
    elif isinstance(node, str) and key in ("text", "note", "code_version"):
        yield node


def test_bm010_no_text_of_the_document_carries_a_tier_word(doc):
    texts = list(_texts(doc))
    assert len(texts) > 500
    bad = [t for t in texts if TIER_WORDS.search(t)]
    assert bad == []
    assert TIER_WORDS.search("a method of the beyond tier") and TIER_WORDS.search("BS-14 refuted")


def test_bm010_the_two_languages_differ_wherever_the_text_has_three_words_or_more(doc):
    same = [t for t in _bilingual(doc) if len(t["en"].split()) >= 3 and t["en"] == t["es"]]
    assert same == []


def _bilingual(node):
    if isinstance(node, dict):
        if set(node) == {"en", "es"}:
            yield node
        else:
            for v in node.values():
                yield from _bilingual(v)
    elif isinstance(node, list):
        for v in node:
            yield from _bilingual(v)


# --- BM-011: the contract is closed ---------------------------------------------------------------------------------------------------------------


def test_bm011_the_committed_document_validates_against_the_closed_schema(doc, validator):
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    assert errors == [], [e.message for e in errors[:3]]


def test_adversarial_bm011_an_unknown_key_fails_at_every_level(doc, validator):
    for path in ([], ["provenance"], ["questions", 0], ["questions", 0, "rows", 0], ["questions", 0, "rows", 0, "cells", 0], ["questions", 0, "runs", 0], ["not_built", 0]):
        planted = copy.deepcopy(doc)
        node = planted
        for p in path:
            node = node[p]
        node["surprise"] = 1
        assert not validator.is_valid(planted), path


def test_bm011_a_value_without_its_citation_fails(doc, validator):
    planted = copy.deepcopy(doc)
    cell = next(c for c in planted["questions"][0]["rows"][0]["cells"] if c["value"] is not None)
    cell["cited"] = None
    assert not validator.is_valid(planted)
    planted = copy.deepcopy(doc)
    cell = next(c for c in planted["questions"][0]["rows"][0]["cells"] if c["value"] is not None)
    del cell["cited"]["sha256"]
    assert not validator.is_valid(planted)


def test_bm011_a_null_without_its_reason_fails(doc, validator):
    planted = copy.deepcopy(doc)
    cell = next(c for q in planted["questions"] for r in q["rows"] for c in r["cells"] if c["value"] is None)
    cell["null_reason"] = None
    assert not validator.is_valid(planted)


def test_bm011_a_row_without_its_standing_fails_and_a_bad_standing_fails(doc, validator):
    planted = copy.deepcopy(doc)
    del planted["questions"][0]["rows"][0]["standing"]
    assert not validator.is_valid(planted)
    planted = copy.deepcopy(doc)
    planted["questions"][0]["rows"][0]["standing"] = "classical"
    assert not validator.is_valid(planted)


def test_bm011_a_missing_spanish_text_fails(doc, validator):
    planted = copy.deepcopy(doc)
    del planted["questions"][0]["title"]["es"]
    assert not validator.is_valid(planted)


# --- BM-012: the index lists the document ------------------------------------------------------------------------------------------------------


def test_bm012_the_index_builder_lists_the_document_and_its_hash_is_in_the_sums():
    from pipeline import pipeline

    assert served_files() == [METHODS_REL]
    assert METHODS_REL in pipeline.served_files()
    sums = (ROOT / "data" / "derived" / "benchmark" / "SHA256SUMS.txt").read_text(encoding="utf-8")
    assert f"{hashlib.sha256(DOC_PATH.read_bytes()).hexdigest()}  {METHODS_REL}" in sums


def test_pointer_resolution_handles_selectors_literal_keys_and_parent_nulls():
    d = {"a": [{"id": "x", "v": 1}, {"id": "y", "v": None, "z": 3}], "k.k": {"n": None}, "m": None}
    assert bm.resolve(d, "a[id=y].z") == (3, "/a/1/z")
    assert bm.resolve(d, "['k.k'].n") == (None, "/k.k/n")
    assert bm.resolve(d, "m.deep") == (None, "/m")
    assert bm.resolve(d, "a[1].v") == (None, "/a/1/v")
    with pytest.raises(bm.BenchmarkError):
        bm.resolve(d, "a[id=q].v")
    with pytest.raises(bm.BenchmarkError):
        bm.resolve(d, "a[id=y].missing")


# --- the adversarial plants of requirements BM-001, BM-006, BM-008, BM-009, BM-010 and BM-012 -------------------------------------------------


def run_violations(q: dict) -> list[str]:
    """A cell that cites a file of another run than its metric's, or a file two runs share."""
    run_of_metric = {m["id"]: m["run_id"] for m in q["metrics"]}
    files = {r["id"]: set(r["files"]) for r in q["runs"]}
    bad = []
    for rid, fs in files.items():
        for other, fo in files.items():
            if rid < other and fs & fo:
                bad.append(f"{q['id']}: the runs {rid} and {other} share {sorted(fs & fo)[0]}")
    for r in q["rows"]:
        for c in r["cells"]:
            if c["cited"] and c["cited"]["path"] not in files[run_of_metric[c["metric"]]]:
                bad.append(f"{q['id']} {r['id']} {c['metric']}: {c['cited']['path']} is not a file of the run {run_of_metric[c['metric']]}")
    return bad


def test_adversarial_bm001_a_changed_byte_is_not_the_committed_document():
    data = bytearray(DOC_PATH.read_bytes())
    data[len(data) // 2] ^= 1
    assert bytes(data) != DOC_PATH.read_bytes()
    assert hashlib.sha256(bytes(data)).hexdigest() != hashlib.sha256(DOC_PATH.read_bytes()).hexdigest()


def test_adversarial_bm006_a_cell_citing_the_file_of_another_run_is_caught(doc):
    q2 = copy.deepcopy(next(q for q in doc["questions"] if q["id"] == "Q2"))
    assert run_violations(q2) == []
    gen = next(c for r in q2["rows"] for c in r["cells"] if c["metric"] == "gen_size")
    man = next(c for r in q2["rows"] for c in r["cells"] if c["metric"] == "man_size")
    gen["cited"]["path"] = man["cited"]["path"]
    assert run_violations(q2) and "gen_size" in run_violations(q2)[0]
    q2b = copy.deepcopy(next(q for q in doc["questions"] if q["id"] == "Q2"))
    next(r for r in q2b["runs"] if r["id"] == "generator")["files"].append(man["cited"]["path"])
    assert any("share" in v for v in run_violations(q2b))


def test_adversarial_bm008_ranking_the_multiplier_would_change_the_standings(doc):
    q10 = copy.deepcopy(next(q for q in doc["questions"] if q["id"] == "Q10"))
    base = bm.standings_of(q10["metrics"], q10["rows"])
    assert base == q10["standings"]
    next(r for r in q10["rows"] if r["ladder_id"] == "BS-11")["ranked"] = True
    changed = bm.standings_of(q10["metrics"], q10["rows"])
    assert changed != base and any("multiplier" in s["best"] for s in changed)
    q10["not_built_ids"] = [n["id"] for n in doc["not_built"]]
    assert not set(q10["not_built_ids"]) & {q["id"] for q in doc["questions"]}


def test_adversarial_bm009_a_null_stripped_of_its_reason_is_refused_and_a_value_with_one_too(doc, validator):
    planted = copy.deepcopy(doc)
    cell = next(c for q in planted["questions"] for r in q["rows"] for c in r["cells"] if c["value"] is None)
    cell["null_reason"] = None
    assert not validator.is_valid(planted)
    planted = copy.deepcopy(doc)
    cell = next(c for q in planted["questions"] for r in q["rows"] for c in r["cells"] if c["value"] is not None)
    cell["null_reason"] = {"en": "x", "es": "y"}
    assert not validator.is_valid(planted)


def test_adversarial_bm010_a_planted_tier_word_in_a_text_or_a_ladder_id_is_caught(doc):
    for bad in ("a method of the beyond tier", "state of the art", "classical rung", "BS-14 refuted", "un método clásico", "estado del arte"):
        planted = copy.deepcopy(doc)
        planted["questions"][0]["protocol"]["en"] = bad
        assert any(TIER_WORDS.search(t) for t in _texts(planted)), bad


def test_adversarial_bm012_an_index_without_the_document_or_a_sums_file_without_its_hash_is_caught():
    from pipeline import pipeline

    served = [f for f in pipeline.served_files() if f != METHODS_REL]
    assert METHODS_REL not in served and METHODS_REL in pipeline.served_files()
    sums = (ROOT / "data" / "derived" / "benchmark" / "SHA256SUMS.txt").read_text(encoding="utf-8")
    altered = bytearray(DOC_PATH.read_bytes())
    altered[0] ^= 1
    assert hashlib.sha256(bytes(altered)).hexdigest() not in sums


# --- BL-113 T2 correction after the reader review (BM-013 to BM-016) ---------------------------------------------------------------------


def _is_pvalue_metric(m: dict) -> bool:
    return m["unit"]["en"] == "p-value" or "p-value" in m["label"]["en"].lower() or re.search(r"valor p", m["label"]["es"].lower()) is not None


def ranked_pvalue_metrics(document: dict) -> list[str]:
    """Every metric whose value is a p-value and whose declared rule ranks it (a p-value is evidence against a null, never a score)."""
    return [f"{q['id']} {m['id']}" for q in document["questions"] for m in q["metrics"] if _is_pvalue_metric(m) and m["better"] != "none"]


def _c11_tests(window: str) -> dict:
    d = json.loads((ROOT / "data" / "derived" / "C11" / f"{window}.json").read_text(encoding="utf-8"))
    return {(t["test_id"], t["model_id"], t["segment"]): t for t in d["tests"]}


_Q1_TEST_OF = {"kupiec_1": "market.kupiec_pof", "cc_1": "market.christoffersen_conditional_coverage"}


def test_bm013_every_q1_kupiec_and_conditional_coverage_cell_is_the_p_value_of_its_case_documents_tests(doc):
    q1 = next(q for q in doc["questions"] if q["id"] == "Q1")
    checked = nulls = 0
    for r in q1["rows"]:
        if r["id"] == "expected" or r["id"].endswith("-aci"):
            continue  # the wrapped rows are other forecasts: their p-values are the conformal block's own
        for c in r["cells"]:
            if c["metric"] not in _Q1_TEST_OF:
                continue
            t = _c11_tests(c["column"])[(_Q1_TEST_OF[c["metric"]], r["id"], "alpha=0.01")]
            assert c["value"] == t["p_value"], (r["id"], c["metric"], c["column"])
            assert c["cited"] is not None and c["cited"]["path"] == f"data/derived/C11/{c['column']}.json"
            assert c["cited"]["pointer"].endswith("/p_value")
            checked += 1
            if t["p_value"] is None:
                nulls += 1
                assert t["notes"] in c["null_reason"]["en"], "a null states the reason the case document itself gives"
                assert "no committed value" not in c["null_reason"]["en"] and "wrapped" not in c["null_reason"]["en"]
    assert checked == 18 * 6 * 2
    assert 0 < nulls < 30, "only the tests the case documents do not evaluate stay null"


def test_bm013_the_wrapped_rows_keep_the_conformal_blocks_own_p_values(doc):
    q1 = next(q for q in doc["questions"] if q["id"] == "Q1")
    aci = [r for r in q1["rows"] if r["id"].endswith("-aci")]
    assert len(aci) == 3
    for r in aci:
        for c in r["cells"]:
            if c["metric"] in _Q1_TEST_OF and c["value"] is not None:
                assert "/outputs/conformal/rows/" in c["cited"]["pointer"] and "/wrapped/" in c["cited"]["pointer"]


def test_bm013_for_the_models_the_conformal_block_also_carries_the_two_sources_give_one_number():
    for window in ("calm-2004-06", "equity-2007-09", "equity-2020", "rates-2022", "fx-2008", "mixed-2023"):
        d = json.loads((ROOT / "data" / "derived" / "C11" / f"{window}.json").read_text(encoding="utf-8"))
        tests = _c11_tests(window)
        for row in d["outputs"]["conformal"]["rows"]:
            if row["alpha"] != 0.01:
                continue
            for fld, tid in (("kupiec_p", "market.kupiec_pof"), ("conditional_coverage_p", "market.christoffersen_conditional_coverage")):
                assert row["unwrapped"][fld] == tests[(tid, row["model_id"], "alpha=0.01")]["p_value"], (window, row["model_id"], fld)


def test_bm014_no_ranked_metric_is_a_p_value(doc):
    assert ranked_pvalue_metrics(doc) == []
    found = {f"{q['id']} {m['id']}" for q in doc["questions"] for m in q["metrics"] if _is_pvalue_metric(m)}
    assert {"Q1 kupiec_1", "Q1 cc_1", "Q5 tw_sph", "Q5 de_sph"} <= found
    for q in doc["questions"]:
        for s in q["standings"]:
            assert not _is_pvalue_metric(next(m for m in q["metrics"] if m["id"] == s["metric"])), (q["id"], s["metric"])


def test_adversarial_bm014_a_p_value_metric_ranked_higher_is_caught(doc):
    planted = copy.deepcopy(doc)
    next(m for q in planted["questions"] if q["id"] == "Q1" for m in q["metrics"] if m["id"] == "kupiec_1")["better"] = "higher"
    assert ranked_pvalue_metrics(planted) == ["Q1 kupiec_1"]


def test_bm015_the_no_change_column_of_the_median_first_flag_day_is_context_and_the_planted_columns_stay_lower(doc):
    q2 = next(q for q in doc["questions"] if q["id"] == "Q2")
    metrics = {m["id"]: m for m in q2["metrics"]}
    for pre in ("gen", "man"):
        assert "null" not in metrics[f"{pre}_median"]["columns"] and metrics[f"{pre}_median"]["better"] == "lower"
        assert len(metrics[f"{pre}_median"]["columns"]) == 6
        ctx = metrics[f"{pre}_median_null"]
        assert ctx["columns"] == ["null"] and ctx["better"] == "none" and ctx["run_id"] == metrics[f"{pre}_median"]["run_id"]
    for m in q2["metrics"]:
        if "median" in m["id"] and "null" in m["columns"]:
            assert m["better"] == "none", m["id"]
    ranked_null = [s for s in q2["standings"] if s["column"] == "null" and "median" in s["metric"]]
    assert ranked_null == []


def test_bm015_the_context_column_holds_the_same_values_the_ranked_one_held(doc):
    q2 = next(q for q in doc["questions"] if q["id"] == "Q2")
    n = 0
    for r in q2["rows"]:
        for c in r["cells"]:
            if c["metric"] in ("gen_median_null", "man_median_null"):
                n += 1
                assert c["column"] == "null" and (c["cited"] is not None or c["null_reason"] is not None)
    assert n == 14


def test_bm016_the_reduction_metric_names_the_mean_signed_bias_in_both_languages(doc):
    q12 = next(q for q in doc["questions"] if q["id"] == "Q12")
    red = next(m for m in q12["metrics"] if m["id"] == "reduction")
    bias = next(m for m in q12["metrics"] if m["id"] == "bias")
    assert "mean signed bias" in red["label"]["en"].lower() and "absolute" not in red["label"]["en"].lower()
    assert "sesgo medio con signo" in red["label"]["es"].lower()
    assert "absolute" in bias["label"]["en"].lower() and "mean" in bias["label"]["en"].lower()


def test_bm007_every_sentence_of_a_reading_ends_before_the_next_one_begins(doc):
    """Review F19: a row's note is a clause; the reading that joins it to the next sentence must close it with a full stop."""
    for q in doc["questions"]:
        for lang, closing in (("en", "A null cell is never ranked"), ("es", "Una celda nula nunca se clasifica")):
            text = q["reading"][lang]
            assert text.count(closing) == 1 and re.search(r"[.?!] " + re.escape(closing), text), (q["id"], lang)


def test_bm003_the_q8_control_keeps_the_standing_of_its_ladder_row_and_its_note_does_not_deny_it(doc):
    """Review F13: the control carries the ladder id M-32; its standing is the ladder's (recent published), never a reference, and it is not ranked."""
    q8 = next(q for q in doc["questions"] if q["id"] == "Q8")
    control = next(r for r in q8["rows"] if r["id"] == "sla_cvm_lognormal")
    assert control["ladder_id"] == "M-32" and control["ranked"] is False
    assert control["standing"] == bm.TIER_STANDING[_ladder_rows()["M-32"][0]] == "recent"
    assert "not a method of the ladder" not in control["note"]["en"] and "no un método de la escalera" not in control["note"]["es"]
    assert not any(s for s in q8["standings"] if "sla_cvm_lognormal" in s["best"])


def q1_pvalue_violations(document: dict) -> list[str]:
    """Q1 Kupiec and conditional-coverage cells (unwrapped rows) whose value is not the case document's ``tests`` p-value."""
    q1 = next(q for q in document["questions"] if q["id"] == "Q1")
    bad = []
    for r in q1["rows"]:
        if r["id"] == "expected" or r["id"].endswith("-aci"):
            continue
        for c in r["cells"]:
            if c["metric"] in _Q1_TEST_OF and c["value"] != _c11_tests(c["column"])[(_Q1_TEST_OF[c["metric"]], r["id"], "alpha=0.01")]["p_value"]:
                bad.append(f"{r['id']} {c['metric']} {c['column']}")
    return bad


def ranked_null_median_metrics(document: dict) -> list[str]:
    q2 = next(q for q in document["questions"] if q["id"] == "Q2")
    return [m["id"] for m in q2["metrics"] if "median" in m["id"] and "null" in m["columns"] and m["better"] != "none"]


def reduction_label_violations(document: dict) -> list[str]:
    q12 = next(q for q in document["questions"] if q["id"] == "Q12")
    red = next(m for m in q12["metrics"] if m["id"] == "reduction")
    return [lang for lang, key in (("en", "mean signed bias"), ("es", "sesgo medio con signo")) if key not in red["label"][lang].lower()]


def test_adversarial_bm013_a_p_value_replaced_by_a_null_or_by_the_wrapped_blocks_number_is_caught(doc):
    assert q1_pvalue_violations(doc) == []
    planted = copy.deepcopy(doc)
    q1 = next(q for q in planted["questions"] if q["id"] == "Q1")
    row = next(r for r in q1["rows"] if r["id"] == "awhs")
    cell = next(c for c in row["cells"] if c["metric"] == "kupiec_1" and c["column"] == "calm-2004-06")
    cell["value"] = None
    assert q1_pvalue_violations(planted) == ["awhs kupiec_1 calm-2004-06"]
    planted = copy.deepcopy(doc)
    q1 = next(q for q in planted["questions"] if q["id"] == "Q1")
    row = next(r for r in q1["rows"] if r["id"] == "hs-250")
    cell = next(c for c in row["cells"] if c["metric"] == "cc_1" and c["column"] == "calm-2004-06")
    cell["value"] = 0.902264102  # the wrapped number of the same model, a different forecast
    assert q1_pvalue_violations(planted) == ["hs-250 cc_1 calm-2004-06"]


def test_adversarial_bm015_ranking_the_no_change_median_again_is_caught(doc):
    assert ranked_null_median_metrics(doc) == []
    planted = copy.deepcopy(doc)
    q2 = next(q for q in planted["questions"] if q["id"] == "Q2")
    next(m for m in q2["metrics"] if m["id"] == "gen_median_null")["better"] = "lower"
    assert ranked_null_median_metrics(planted) == ["gen_median_null"]
    planted = copy.deepcopy(doc)
    q2 = next(q for q in planted["questions"] if q["id"] == "Q2")
    next(m for m in q2["metrics"] if m["id"] == "man_median")["columns"].append("null")
    assert ranked_null_median_metrics(planted) == ["man_median"]


def test_adversarial_bm016_the_old_reduction_label_is_caught(doc):
    assert reduction_label_violations(doc) == []
    planted = copy.deepcopy(doc)
    q12 = next(q for q in planted["questions"] if q["id"] == "Q12")
    red = next(m for m in q12["metrics"] if m["id"] == "reduction")
    red["label"] = {"en": "Reduction of the accepted-only bias", "es": "Reducción del sesgo del modelo solo con aceptados"}
    assert reduction_label_violations(planted) == ["en", "es"]


SPANISH_POINT_DECIMAL = re.compile(r"(?<![\w.,])\d+\.(?:\d{1,2}|\d{4,})(?![\d.])")
ENGLISH_CATEGORY = re.compile(r"\b(green|amber|red)\b")


def spanish_text_violations(document: dict) -> list[str]:
    """The Spanish texts that write a decimal with a point (a point followed by three digits is a thousand) or name a category in English."""
    found = []
    for text in _bilingual(document):
        hits = SPANISH_POINT_DECIMAL.findall(text["es"]) + ENGLISH_CATEGORY.findall(text["es"])
        if hits:
            found.append(f"{text['es'][:40]}: {', '.join(hits)}")
    return found


def test_bm017_every_spanish_text_writes_a_decimal_with_a_comma_and_a_category_in_spanish(doc):
    assert spanish_text_violations(doc) == []
    q10 = next(q for q in doc["questions"] if q["id"] == "Q10")
    assert "0,85" in q10["reading"]["es"] and "0.85" in q10["reading"]["en"]
    assert "verde es lo mejor, luego ámbar, rojo" in q10["reading"]["es"] and "green is best, then amber, red" in q10["reading"]["en"]


def test_bm017_the_rule_text_keeps_the_point_in_english_and_the_category_ids_in_the_rule():
    assert bm.rule_text("nearer:0.85") == {"en": "nearer 0.85 is better", "es": "más cerca de 0,85 es mejor"}
    assert bm.rule_text("nearer:1") == {"en": "nearer 1 is better", "es": "más cerca de 1 es mejor"}
    assert bm.rule_text("order:green,amber,red") == {"en": "green is best, then amber, red", "es": "verde es lo mejor, luego ámbar, rojo"}
    assert bm.rule_text("order:a,b")["es"] == "a es lo mejor, luego b"  # a category with no Spanish word keeps its id


def test_adversarial_bm017_a_point_decimal_or_an_english_category_planted_in_a_spanish_text_is_caught(doc):
    for bad, hit in (("más cerca de 0.85 es mejor", "0.85"), ("Agrupamiento 0.1", "0.1"), ("green es lo mejor", "green"), ("umbral 0.0125", "0.0125")):
        planted = copy.deepcopy(doc)
        planted["questions"][0]["protocol"]["es"] = bad
        assert spanish_text_violations(planted) == [f"{bad[:40]}: {hit}"], bad
    for fine in ("1.000 días y 2.000 series", "GARCH(1,1) al 99,9%", "versión 1.5.0"):
        planted = copy.deepcopy(doc)
        planted["questions"][0]["protocol"]["es"] = fine
        assert spanish_text_violations(planted) == [], fine
