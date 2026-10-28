"""U16-F13e (fix round 6, the fifth capture review R5, batch c26): the C20 producer.

B1 the bake passes every test row through ``with_reference_text``, so a document carries the reference of each row in both languages
and its English names the engine's ML contract in words (R4 ruling 1: "contract engine-ml-api 2.0.0" is a raw id); the contract test of
the consumer side runs the bake's own step over every committed C20 test row. B2 the small-groups limit states the record range of
the document's own shock rows (R5 ruling 9: "30 to 90 records" beside a row of 27 is a sentence its row contradicts), m5 the same on
the held-out document (60 to 90)."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from pipeline.cases.c20 import bake, v_shock
from pipeline.core.schemas import _cs

ROOT = Path(__file__).resolve().parents[2]
DOCS = sorted((ROOT / "data" / "derived" / "C20").glob("*.json"))


def _variant_docs() -> list[tuple[str, dict]]:
    out = []
    for p in DOCS:
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("tests"):
            out.append((p.stem, d))
    return out


def test_b1_the_bake_step_gives_every_committed_row_its_reference_in_both_languages() -> None:
    docs = _variant_docs()
    assert len(docs) == 6
    cs = _cs()
    for name, d in docs:
        rows = bake.document_tests(d["tests"])
        assert len(rows) == len(d["tests"]), name
        for r in rows:
            ref = r["extras"]["reference_text"]
            assert set(ref) == {"en", "es"} and ref["en"] and ref["es"], (name, r["test_id"])
            assert "engine-ml-api" not in ref["en"] and "engine-ml-api" not in ref["es"], (name, r["test_id"], ref["en"])
            assert cs.errors("common/test-result", r) == [], (name, r["test_id"])
        # a copy: the rows the bake was given keep no reference text
        assert all("reference_text" not in (t.get("extras") or {}) for t in d["tests"]), name


def test_b1_the_bake_writes_the_rows_of_its_bake_step() -> None:
    # the document's tests are the bake step's rows, not the raw engine rows
    tree = ast.parse(Path(bake.__file__).read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "build_artifact"]
    assert calls
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords}
        if "tests" in kw:
            v = kw["tests"]
            assert isinstance(v, ast.Call) and getattr(v.func, "id", None) == "document_tests", ast.unparse(v)


def _row(n: int) -> dict:
    return {"n_records": n}


def test_b2_the_small_groups_limit_states_the_range_of_its_rows() -> None:
    seen = v_shock.small_groups_limit([_row(90), _row(30), _row(30), _row(27)], [_row(90), _row(90)])
    assert "27 to 90 records" in seen["en"] and "30 to 90" not in seen["en"], seen["en"]
    assert "de 27 a 90 registros" in seen["es"], seen["es"]
    held = v_shock.small_groups_limit([_row(90), _row(60)], [_row(90), _row(90)])
    assert "60 to 90 records" in held["en"] and "de 60 a 90 registros" in held["es"], held


def test_b2_a_range_of_one_size_and_grouped_counts() -> None:
    one = v_shock.small_groups_limit([_row(90)], [_row(90)])
    assert "90 records" in one["en"] and " to " not in one["en"].split(",")[0], one["en"]
    assert "90 registros" in one["es"], one["es"]
    big = v_shock.small_groups_limit([_row(1200)], [_row(30)])
    assert "30 to 1,200 records" in big["en"] and "de 30 a 1.200 registros" in big["es"], big


def test_b2_the_committed_seen_document_contradicts_its_limit_until_the_rebake() -> None:
    # the committed limit is the hard-coded sentence; the function's sentence follows the committed rows
    d = json.loads((ROOT / "data" / "derived" / "C20" / "sgcd-seen.json").read_text(encoding="utf-8"))
    o = d["outputs"]
    sizes = [r["n_records"] for r in o["shipped"]["rows"] + o["applied"]["rows"]]
    lim = v_shock.small_groups_limit(o["shipped"]["rows"], o["applied"]["rows"])
    assert f"{min(sizes)} to {max(sizes)} records" in lim["en"]
