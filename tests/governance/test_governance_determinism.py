"""U15-P: two bakes give byte-identical documents, the committed documents are what the bake writes, and no wall-clock value enters a document."""
from __future__ import annotations

import re

import gov_support as gs


def test_two_bakes_write_the_same_bytes(tmp_path):
    from pipeline.governance import bake

    a, b = tmp_path / "a", tmp_path / "b"
    ma = bake.bake(a, write_page=False)
    mb = bake.bake(b, write_page=False)
    files_a = sorted(p.relative_to(a).as_posix() for p in a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(b).as_posix() for p in b.rglob("*") if p.is_file())
    assert files_a == files_b and files_a
    for rel in files_a:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel
    assert ma == mb


def test_the_bake_writes_the_four_documents_the_views_read_and_one_report_per_entry(tmp_path, baked):
    from pipeline.governance import bake, report_rel

    bake.bake(tmp_path, write_page=False)
    for rel in ("governance/inventory.json", "governance/findings.json", "governance/appetite.json", "governance/SHA256SUMS.txt"):
        assert (tmp_path / rel).is_file(), rel
    for e in baked.inventory["entries"]:
        assert (tmp_path / report_rel(e["key"])).is_file()
    assert report_rel("C01/german") == "governance/reports/C01-german.json"
    assert len(list((tmp_path / "governance/reports").glob("*.json"))) == len(baked.inventory["entries"])


def test_adversarial_the_committed_documents_are_what_the_bake_writes(tmp_path):
    """The production-path check in miniature: the bytes under data/derived/governance equal a fresh bake (a bake that drifts is found here)."""
    from pipeline.governance import bake

    bake.bake(tmp_path, write_page=False)
    fresh = {p.relative_to(tmp_path).as_posix(): p.read_bytes() for p in (tmp_path / "governance").rglob("*") if p.is_file()}
    committed = {p.relative_to(gs.DERIVED).as_posix(): p.read_bytes() for p in gs.COMMITTED.rglob("*") if p.is_file()}
    assert sorted(fresh) == sorted(committed)
    for rel in fresh:
        assert fresh[rel] == committed[rel], rel


def test_the_checksum_file_lists_every_governance_document_with_its_sha256(tmp_path):
    """The manifest of the bake is governance/SHA256SUMS.txt, in the format of the case folders (a JSON manifest would need a schema of its own)."""
    import hashlib

    from pipeline.governance import bake

    bake.bake(tmp_path, write_page=False)
    lines = (tmp_path / "governance/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    listed = dict((rel, sha) for sha, rel in (line.split("  ", 1) for line in lines))
    on_disk = {p.relative_to(tmp_path).as_posix(): p for p in (tmp_path / "governance").rglob("*.json")}
    assert sorted(listed) == sorted(on_disk) and len(listed) > 30
    for rel, p in on_disk.items():
        assert listed[rel] == hashlib.sha256(p.read_bytes()).hexdigest(), rel
    assert lines == sorted(lines, key=lambda x: x.split("  ", 1)[1])


def test_no_wall_clock_value_enters_the_bake():
    """R4: the as-of date and every raised date are committed values. The package reads no clock."""
    for p in gs.PIPE.glob("*.py"):
        text = p.read_text(encoding="utf-8")
        for pattern in (r"datetime\.now", r"date\.today", r"time\.time\(", r"utcnow", r"time\.strftime", r"perf_counter"):
            assert not re.search(pattern, text), (p.name, pattern)


def test_the_bake_defines_none_of_the_engine_computations():
    """ADR-0069: the product reimplements none of the engine's governance functions."""
    names = {"matrix_tier", "exposure_band", "materiality", "complexity", "tier_sensitivity", "next_dates", "add_months", "deadline_days", "due_date",
            "ageing_days", "is_overdue", "opinion_level", "finding_level", "recommendation", "appetite_metrics", "severity_to_ecb",
            "map_product_status", "anchor_from_test_row", "rwea_share_of_anchor", "build_report", "assign_variant", "topological_order"}
    for p in gs.PIPE.glob("*.py"):
        text = p.read_text(encoding="utf-8")
        defined = set(re.findall(r"(?m)^\s*def (\w+)\(", text))
        assert not defined & names, (p.name, sorted(defined & names))


def test_the_served_files_are_the_three_documents_and_every_report(baked):
    from pipeline.governance import report_rel, served_files

    got = served_files(gs.DERIVED)
    assert got[:3] == ["governance/inventory.json", "governance/findings.json", "governance/appetite.json"]
    assert got[3:] == sorted(report_rel(k) for k in baked.reports)
