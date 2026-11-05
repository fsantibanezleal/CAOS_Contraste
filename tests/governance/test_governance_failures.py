"""U15-P: what the bake does when an input is absent or ambiguous (Missing-data behavior of the brief): it stops and names the file, writes nothing,
and never assigns a variant to a fit by guess.
"""
from __future__ import annotations

import json

import gov_support as gs
import pytest



@pytest.fixture()
def tree(tmp_path):
    return gs.copy_tree(tmp_path / "tree")


def test_adversarial_a_variant_document_the_manifest_names_but_is_absent_stops_the_bake_and_writes_nothing(tree, tmp_path):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    (tree / "data/derived/C07/recession.json").unlink()
    out = tmp_path / "out"
    with pytest.raises(BakeError, match=r"C07/recession\.json"):
        bake.bake(out, root=tree, write_page=False)
    assert not out.exists() or not any(out.rglob("*"))


def test_adversarial_a_models_document_that_is_not_valid_json_stops_the_bake_naming_the_file(tree, tmp_path):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    (tree / "data/derived/C18/models-banco-andino.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(BakeError, match=r"C18/models-banco-andino\.json"):
        bake.build(tree)


def test_the_manifest_of_a_built_case_that_is_absent_stops_the_bake_but_a_planned_case_is_listed(tree):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    (tree / "data/derived/manifests/C09.json").unlink()
    with pytest.raises(BakeError, match=r"manifests/C09\.json"):
        bake.build(tree)


def test_a_case_document_that_states_another_case_stops_the_bake(tree):
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    p = tree / "data/derived/C13/none.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["case_id"] = "C12"
    p.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(BakeError, match=r"C13/none\.json"):
        bake.build(tree)


def test_adversarial_a_release_the_changelog_does_not_know_stops_the_bake(tree):
    """A raised date is the release date of the document's code version: a version with no heading has no date, and no date is invented."""
    from pipeline.governance import bake
    from pipeline.governance.readers import BakeError

    p = tree / "CHANGELOG.md"
    # the code version the committed C08 documents record (1.00.000 since the 1.0 re-bake): its heading goes, so its date does too
    version = json.loads((tree / "data/derived/C08/dc-2007-08.json").read_text(encoding="utf-8"))["provenance"]["code_version"]
    text = p.read_text(encoding="utf-8")
    assert f"## [{version}]," in text
    p.write_text(text.replace(f"## [{version}],", f"## [{version}1],"), encoding="utf-8")
    with pytest.raises(BakeError, match=version.replace(".", r"\.")):
        bake.build(tree)


def test_adversarial_the_pure_rule_leaves_a_variant_it_cannot_place_in_the_excluded_list_with_the_engines_reason(tree):
    """W15-15: C06 has six fits that read the same sources; with the extensions off no variant is assigned by guess."""
    from pipeline.governance import bake

    p = tree / "data-pipeline/pipeline/governance/inputs.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    d["variant_assignment"]["extensions"] = []
    p.write_text(json.dumps(d), encoding="utf-8")
    built = bake.build(tree)
    inv = built.inventory
    keys = {e["key"] for e in inv["entries"]}
    assert not any(k.startswith("C06/") or k.startswith("C08/") for k in keys)
    excl = [x for x in inv["excluded"] if x["case_id"] == "C06" and x["variant_id"]]
    assert {x["variant_id"] for x in excl} == {"rd-2006-12", "rd-2008-12", "rd-2010-12", "rd-2019-12", "rd-2020-06", "rd-2023-06"}
    assert all("fits hold all of the variant's sources" in x["reason"]["en"] for x in excl)
    left = [x for x in inv["excluded"] if x["case_id"] == "C06" and x["variant_id"] is None]
    assert len(left) == 6 and all("C06/" in x["reason"]["en"] for x in left)
    assert all(r["case_id"] != "C06" for r in built.findings["rows"])


def test_the_extensions_place_a_variant_only_on_a_committed_identity(baked):
    """The model-record-ids rule places the C01 Taiwan variants; the variant-id-equals-fit-id rule places C06 and C08; nothing else is guessed."""
    inv = baked.inventory
    by_variant = {(e["case_id"], v["variant_id"]): (e["fit_id"], v["basis"]) for e in inv["entries"] for v in e["variants"]}
    assert by_variant[("C01", "small-sample")][0] == "taiwan-small" and by_variant[("C01", "holdout")][0] == "taiwan"
    assert by_variant[("C01", "german-twin")][0] == "german"
    assert by_variant[("C06", "rd-2020-06")][0] == "rd-2020-06"
    assert "model records" in by_variant[("C01", "holdout")][1]
    assert "variant id equals the fit id" in by_variant[("C06", "rd-2020-06")][1]
    # a variant with no committed identity to a fit stays out
    excluded = {(x["case_id"], x["variant_id"]) for x in inv["excluded"] if x["variant_id"]}
    assert {("C05", "ldp-sim-0"), ("C05", "ldp-sim-1"), ("C05", "ldp-sim-3")} <= excluded
