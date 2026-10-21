"""U15-P: docs/governance.md. Its results block is generated from the governance documents as the case pages' blocks are (never typed), states the
tier counts under the four readings, and says when a case holds no finding.
"""
from __future__ import annotations

import gov_support as gs

BEGIN = "<!-- governance-results:begin -->"
END = "<!-- governance-results:end -->"


def block_of(text: str) -> str:
    return gs.lf(text).split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")


def test_the_page_results_block_is_the_one_generated_from_the_documents(baked):
    assert block_of(gs.PAGE.read_text(encoding="utf-8")) == block_of(BEGIN + "\n" + baked.page_block + "\n" + END)


def test_the_page_states_the_tier_counts_of_the_four_readings(baked):
    block = baked.page_block
    for rec in baked.inventory["tier_counts"]:
        line = "/".join(str(n) for n in rec["counts"])
        assert f"| {rec['reading']} |" in block and line in block, rec


def test_the_page_states_the_cases_without_finding_rows_and_the_excluded_variants(baked):
    block = baked.page_block
    held = {r["case_id"] for r in baked.findings["rows"]}
    for case in sorted({e["case_id"] for e in baked.inventory["entries"]} - held):
        assert case in block.split("no finding row in the committed documents:")[1].split("\n")[0], case
    for x in baked.inventory["excluded"]:
        if x["variant_id"]:
            assert f"{x['case_id']}/{x['variant_id']}" in block


def test_the_page_names_no_path_of_this_machine(baked):
    text = gs.PAGE.read_text(encoding="utf-8")
    for bad in ("D:\\", "E:\\", "D:/_", "E:/_", "/Users/", "C:\\"):
        assert bad not in text
    assert "Contraste approves no model" in text


def test_adversarial_the_page_block_is_regenerated_not_typed(baked):
    """A figure typed into the committed block makes it differ from the generated one."""
    block = block_of(gs.PAGE.read_text(encoding="utf-8"))
    planted = block.replace("entries (one per fit)", "entries (one per model)", 1)
    assert planted != block
    nl = chr(10)
    assert block_of(BEGIN + nl + planted + nl + END) != block_of(BEGIN + nl + baked.page_block + nl + END)
