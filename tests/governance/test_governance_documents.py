"""U15-P: the governance documents the bake writes (inventory, findings register, appetite, reports) against their contracts.

Every document validates against its schema and passes the cross-field checker of U15-S (``violations`` and ``cross_violations``); the tiers
recompute through the engine's ``matrix_tier``; the four fixture entries agree with the U15-S fixtures field by field except the fields the full
inventory moves (named below with the reason); every register row traces to a finding of a committed variant document.
"""
from __future__ import annotations

import json
import re

import gov_support as gs
import pytest

SEVERITIES = ["S1", "S2", "S3", "S4"]
OPEN = ("open", "action_plan_agreed", "in_progress", "submitted_for_closure", "overdue")
#: attributes of the fixture entries that the full inventory moves, with the reason (the fixtures were written before the full inventory)
MOVED_ATTRIBUTES = {
    "A09": "the fixture summarises the C07 and C18 books in three classes; the bake lists the segment ids (C07) or the class mapping (C18) the models document holds",
    "A13": "the fixture reads the C01 split and the C18 fit end year in its own shape; the bake reads the same pointers into its value shape",
    "A19": "the fixture counts the C18 named parameters in its own shape; the bake counts the same list",
    "A31": "the fixture names the engine version that built the case document; the bake names the validator at the pinned release (riskvalidation 0.9.0)",
    "A16": "the fixture holds two edges; the full edge table (edges.json, E01 to E15) gives C18 four feeders and C01/german its downstream cases",
    "A38": "the fixture register holds the four fixture entries' findings under the fixture deadlines; the full register is the same rows, so the value agrees unless an entry gains a variant",
}


def docs(baked):
    return {"inventory": baked.inventory, "findings": baked.findings, "appetite": baked.appetite, "reports": baked.reports}


def entry(inv, key):
    return next(e for e in inv["entries"] if e["key"] == key)


def test_every_document_validates_against_its_schema(baked):
    assert gs.schema_errors("inventory", baked.inventory) == []
    assert gs.schema_errors("findings", baked.findings) == []
    assert gs.schema_errors("appetite", baked.appetite) == []
    assert baked.reports
    for key, rep in baked.reports.items():
        assert gs.schema_errors("report", rep) == [], key


def test_every_document_passes_the_cross_field_checker_of_u15_s(baked):
    from pipeline.governance import bake

    sm = gs.load_semantics()
    copied = gs.copied_texts()  # the case documents' own words are replaced by a marker for the text rule only (see bake.check_documents)
    for name in ("inventory", "findings", "appetite"):
        assert sm.violations(bake._neutral(getattr(baked, name), copied)) == [], name
    for key, rep in baked.reports.items():
        assert sm.violations(bake._neutral(rep, copied)) == [], key
    assert sm.cross_violations(docs(baked)) == []


def test_the_inventory_holds_one_entry_per_fit_and_lists_what_it_excludes(baked):
    inv = baked.inventory
    models = sorted(p.name for p in (gs.DERIVED).glob("C*/models-*.json"))
    assert len(models) == 34
    keys = [e["key"] for e in inv["entries"]]
    assert keys == sorted(keys)
    fits_all = set()
    for p in gs.DERIVED.glob("C*/models-*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        fits_all.add(f"{d['case_id']}/{d['fit_id']}")
    # every models document is an entry, or is listed in excluded (variant_id null) with a reason that names its fit key
    left = fits_all - set(keys)
    for fit_key in left:
        assert any(x["variant_id"] is None and x["case_id"] == fit_key.split("/")[0] and fit_key in x["reason"]["en"] for x in inv["excluded"]), fit_key
    assert set(keys) <= fits_all
    planned = {x["case_id"] for x in inv["excluded"] if x["variant_id"] is None}
    assert "C19" in planned
    for x in inv["excluded"]:
        assert x["reason"]["en"].strip() and x["reason"]["es"].strip()


def test_every_variant_is_in_exactly_one_entry_or_excluded_with_its_reason(baked):
    inv = baked.inventory
    seen: dict[tuple[str, str], str] = {}
    for e in inv["entries"]:
        for v in e["variants"]:
            k = (e["case_id"], v["variant_id"])
            assert k not in seen, f"{k} is in {seen[k]} and {e['key']}"
            seen[k] = e["key"]
            assert v["basis"].strip()
    excluded = {(x["case_id"], x["variant_id"]) for x in inv["excluded"] if x["variant_id"]}
    assert not excluded & set(seen)
    on_disk = set()
    for p in gs.DERIVED.glob("C*/*.json"):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema") == "contraste.case/v1" and "variant_id" in d:
            on_disk.add((d["case_id"], d["variant_id"]))
    assert on_disk == set(seen) | excluded
    assert len(on_disk) == 127


def test_the_tier_is_the_engine_matrix_of_its_scores_under_every_reading(baked):
    from riskvalidation.governance import tiering

    for e in baked.inventory["entries"]:
        tb = e["tier_block"]
        mat, cx = tb["materiality"], tb["complexity"]
        scores = [f["score"] for f in cx["factors"] if f["score"] is not None]
        band = tiering.exposure_band(mat["exposure"]["share"])
        assert mat["exposure"]["band"] == band
        m = {"literal": tiering.materiality(band, mat["regulatory_use"]["literal"], mat["decision_criticality"]["score"]),
             "graded": tiering.materiality(band, mat["regulatory_use"]["graded"], mat["decision_criticality"]["score"])}
        assert mat["m"] == m
        c = {"mean": tiering.complexity(scores), "maximum": tiering.complexity(scores, "maximum")}
        assert cx["c"] == c
        rows = {r["reading"]: r for r in tb["tier_sensitivity"]}
        assert rows["A"]["tier"] == tiering.matrix_tier(m["literal"], c["mean"])
        assert rows["B"]["tier"] == tiering.matrix_tier(m["graded"], c["mean"])
        assert rows["C"]["tier"] == tiering.matrix_tier(m["literal"], c["maximum"])
        assert rows["D"]["tier"] == tiering.matrix_tier(m["graded"], c["maximum"])
        assert tb["computed_tier"] == rows["B"]["tier"] == tb["tier"]
        assert tb["override"] is None
        # the engine's own sensitivity function gives the same four rows
        eng = tiering.tier_sensitivity(mat["exposure"]["share"], mat["regulatory_use"]["literal"], mat["regulatory_use"]["graded"],
                                       mat["decision_criticality"]["score"], scores)
        assert [(r[0], r[3], r[4], r[5]) for r in eng] == [(r["reading"], r["m"], r["c"], r["tier"]) for r in tb["tier_sensitivity"]]


def test_the_tier_counts_under_the_four_readings_are_stated(baked):
    from riskvalidation.governance import tiering

    inv = baked.inventory
    n = len(inv["entries"])
    assert [r["reading"] for r in inv["tier_counts"]] == ["A", "B", "C", "D"]
    for i, rec in enumerate(inv["tier_counts"]):
        tiers = [e["tier_block"]["tier_sensitivity"][i]["tier"] for e in inv["entries"]]
        assert rec["counts"] == list(tiering.tier_counts(tiers))
        assert sum(rec["counts"]) == n


def test_the_addendum_tiers_of_the_built_cases_hold_for_every_fit_of_the_case(baked):
    """A D2 3.4 (the 19 cases of the addendum) and the C02 and C20 rows of W15-18: the tier of a case under each reading."""
    expected = {"C01": (1, 2, 1, 1), "C03": (1, 2, 1, 1), "C04": (1, 1, 1, 1), "C05": (1, 1, 1, 1), "C06": (1, 1, 1, 1), "C07": (1, 1, 1, 1),
                "C08": (1, 2, 1, 1), "C09": (1, 2, 1, 2), "C10": (1, 1, 1, 1), "C11": (1, 2, 1, 1), "C12": (1, 1, 1, 1), "C13": (1, 2, 1, 2),
                "C14": (1, 1, 1, 1), "C15": (1, 1, 1, 1), "C16": (1, 1, 1, 1), "C17": (1, 1, 1, 1), "C18": (1, 1, 1, 1), "C21": (1, 1, 1, 1),
                "C22": (4, 4, 4, 4)}
    seen = set()
    for e in baked.inventory["entries"]:
        row = tuple(r["tier"] for r in e["tier_block"]["tier_sensitivity"])
        if e["case_id"] in expected:
            assert row == expected[e["case_id"]], e["key"]
        seen.add(e["case_id"])
    # C02 and C20 (W15-18): M graded 3, C mean 2, C maximum 3
    assert tuple(r["tier"] for r in entry(baked.inventory, "C02/polish-horizons")["tier_block"]["tier_sensitivity"]) == (1, 2, 1, 1)
    assert tuple(r["tier"] for r in entry(baked.inventory, "C20/c20-ladder")["tier_block"]["tier_sensitivity"]) == (2, 2, 1, 1)
    assert {"C02", "C20"} <= seen


def _no_basis(node):
    """The numbers and tags of a block, without the prose that cites the pointer (the bake adds the pointer it read to each basis)."""
    if isinstance(node, dict):
        return {k: _no_basis(v) for k, v in node.items() if k != "basis"}
    if isinstance(node, list):
        return [_no_basis(v) for v in node]
    return node


def test_the_four_fixture_entries_agree_with_the_u15_s_fixtures_except_the_named_fields(baked):
    fx = gs.read("docs/contracts/fixtures/governance/inventory-fixture.json")
    differs: dict[str, list[str]] = {}
    for fe in fx["entries"]:
        e = entry(baked.inventory, fe["key"])
        for block in ("title", "case_id", "fit_id", "tier_block", "lifecycle"):
            assert _no_basis(e[block]) == _no_basis(fe[block]), (fe["key"], block)
        assert e["scope"]["answers"] == fe["scope"]["answers"]
        assert [(p["profile"], p["in_scope"]) for p in e["scope"]["profiles"]] == [(p["profile"], p["in_scope"]) for p in fe["scope"]["profiles"]]
        for field in ("profile", "review_kind", "last_validation", "next_review", "next_full_revalidation", "next_monitoring", "null_reason"):
            got, want = e["schedule"][field], fe["schedule"][field]
            if field == "null_reason" and got:   # the fixture's Spanish has no accents; the English is the engine's table and must agree
                got, want = got["en"], want["en"]
            assert got == want, (fe["key"], field)
        assert [(c["key"], c["role"]) for c in e["components"]] == [(c["key"], c["role"]) for c in fe["components"]], fe["key"]
        for aid, fa in fe["attributes"].items():
            a = e["attributes"][aid]
            if a["status"] != fa["status"] or a["value"] != fa["value"]:
                differs.setdefault(fe["key"], []).append(aid)
    named = {k: sorted(v) for k, v in differs.items()}
    for key, aids in named.items():
        for aid in aids:
            assert aid in MOVED_ATTRIBUTES or aid in ("A37", "A38"), (key, aid, "differs from the fixture and no reason is named")


def test_the_fixture_dependent_fields_are_the_ones_the_full_inventory_moves(baked):
    """The appetite population and the graph metrics depend on the whole inventory: they differ from the four-entry fixtures by design."""
    fx_app = gs.read("docs/contracts/fixtures/governance/appetite-fixture.json")
    assert baked.appetite["population"]["entries"] > fx_app["population"]["entries"]
    assert baked.appetite["population"]["findings"] > fx_app["population"]["findings"]
    fx_inv = gs.read("docs/contracts/fixtures/governance/inventory-fixture.json")
    assert len(baked.inventory["entries"]) > len(fx_inv["entries"])


def test_every_register_row_traces_to_its_variant_document_and_finding_id(baked):
    rows = baked.findings["rows"]
    assert rows
    entries = {e["key"]: e for e in baked.inventory["entries"]}
    total = 0
    cache: dict[str, dict] = {}
    for r in rows:
        path = f"data/derived/{r['case_id']}/{r['variant_id']}.json"
        doc = cache.setdefault(path, gs.read(path))
        f = next(x for x in doc["findings"] if x["id"] == r["id"])
        assert r["severity"] == f["severity"] and r["product_status"] == f["status"] and r["evidence"] == f["evidence"]
        assert r["title"] == f["title"]
        assert r["variant_id"] in [v["variant_id"] for v in entries[r["entry_key"]]["variants"]]
        assert r["key"] == f"{r['case_id']}/{r['variant_id']}/{r['id']}"
    # every finding of every assigned variant is a row
    for e in entries.values():
        for v in e["variants"]:
            doc = gs.read(f"data/derived/{e['case_id']}/{v['variant_id']}.json")
            total += len(doc["findings"])
    assert total == len(rows)
    assert len({r["key"] for r in rows}) == len(rows)


def test_c12_and_c21_hold_no_finding_rows_and_the_register_says_so(baked):
    """R6: the register reads whatever the committed documents hold; an empty list is stated as empty, never filled."""
    held = {c: sum(len(gs.read(str(p.relative_to(gs.ROOT)))["findings"]) for p in gs.DERIVED.glob(f"{c}/*.json")
                   if "variant_id" in gs.read(str(p.relative_to(gs.ROOT)))) for c in ("C12", "C21")}
    in_register = {c: sum(1 for r in baked.findings["rows"] if r["case_id"] == c) for c in ("C12", "C21")}
    assert in_register == held
    for c, n in held.items():
        assert (c in {x["case_id"] for x in baked.findings["counts"]["by_case"]}) == (n > 0)


def test_the_dates_come_from_the_changelog_and_never_from_the_clock(baked):
    dates = gs.changelog_dates()
    newest = max(dates.values())
    assert baked.inventory["as_of"] == baked.findings["as_of"] == baked.appetite["as_of"] == newest
    assert baked.inventory["as_of_basis"]["label"] == "convention"
    for r in baked.findings["rows"]:
        doc = gs.read(f"data/derived/{r['case_id']}/{r['variant_id']}.json")
        assert r["raised"] == dates[doc["provenance"]["code_version"]]
    for e in baked.inventory["entries"]:
        md = gs.read(next(d["path"] for d in baked.inventory["provenance"]["documents_read"] if d["path"].endswith(f"{e['case_id']}/models-{e['fit_id']}.json")))
        assert e["schedule"]["last_validation"]["date"] == dates[md["provenance"]["code_version"]]
    assert baked.inventory["provenance"]["code_version"] == json.loads(gs.INPUTS.read_text(encoding="utf-8"))["release"]["code_version"]
    assert baked.inventory["provenance"]["riskvalidation_version"] == "0.9.0"


def test_every_path_read_is_listed_with_its_sha256_over_lf_normalised_bytes(baked):
    import hashlib

    listed = {d["path"]: d["sha256"] for d in baked.inventory["provenance"]["documents_read"]}
    assert "CHANGELOG.md" in listed and "data/derived/manifests/index.json" in listed
    assert "data-pipeline/pipeline/governance/inputs.json" in listed and "data-pipeline/pipeline/governance/edges.json" in listed
    for path, sha in listed.items():
        raw = (gs.ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(raw).hexdigest() == sha, path
    for p in [q for q in gs.DERIVED.glob("C*/*.json") if re.fullmatch(r"C\d\d", q.parent.name)]:
        assert str(p.relative_to(gs.ROOT).as_posix()) in listed
    for p in (gs.DERIVED / "manifests").glob("C*.json"):
        assert str(p.relative_to(gs.ROOT).as_posix()) in listed


def test_the_opinion_and_the_recommendation_are_labelled_the_rules_output(baked):
    from riskvalidation.governance.opinion import LABEL

    for key, rep in baked.reports.items():
        op = rep["sections"][10]["opinion"]
        assert op["label"]["en"] == LABEL
        assert 1 <= op["level"] <= 4
        assert rep["sections"][0]["opinion_level"] == op["level"]


def test_one_report_per_entry_of_twelve_sections(baked):
    assert sorted(baked.reports) == sorted(e["key"] for e in baked.inventory["entries"])
    for rep in baked.reports.values():
        assert len(rep["sections"]) == 12
        assert [s["number"] for s in rep["sections"]] == list(range(1, 13))


def test_the_appetite_is_the_engines_over_the_inventory_and_the_register(baked):
    from datetime import date

    from riskvalidation.governance import appetite

    inv, fnd = baked.inventory, baked.findings
    want = appetite.appetite_metrics(inv["entries"], fnd["rows"], date.fromisoformat(inv["as_of"]))
    assert [m["id"] for m in baked.appetite["metrics"]] == [m["id"] for m in want]
    for got, exp in zip(baked.appetite["metrics"], want):
        assert got["value"] == exp["value"] and got["numerator"] == exp["numerator"] and got["denominator"] == exp["denominator"]
        assert got["light"] == exp["light"] and got["register_rows"] == exp["register_rows"]
    assert baked.appetite["population"] == appetite.appetite_population(inv["entries"], fnd["rows"])


def test_the_engine_computes_the_values_the_bake_writes(baked):
    """Each register row's deadline, due date, ageing and overdue flag are the engine's functions of the row (no arithmetic of the bake's own)."""
    from datetime import date

    from riskvalidation.governance import findings as eng

    as_of = date.fromisoformat(baked.findings["as_of"])
    for r in baked.findings["rows"][:400]:
        days = eng.deadline_days(r["severity"], r["tier"])
        due = eng.due_date(date.fromisoformat(r["raised"]), days)
        assert (r["deadline_days"], r["due"]) == (days, due.isoformat())
        assert r["ageing_days"] == eng.ageing_days(date.fromisoformat(r["raised"]), as_of)
        assert r["overdue"] == eng.is_overdue(r["status"], due, as_of)
        assert r["ecb_f"] == eng.severity_to_ecb(r["severity"]) and r["status"] == eng.map_product_status(r["product_status"])
    assert baked.findings["counts"] == eng.register_counts(baked.findings["rows"])
