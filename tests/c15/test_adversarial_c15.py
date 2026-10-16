"""The adversarial checks of docs/design/features/c15/validation.md: each plants a defect and the gate must refuse it."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import c15_docs as d
import contract_schemas as cs
import numpy as np
import pytest
import semantics
from c15_support import SEED, VARIANT_IDS, make_series, world
from test_c15_documents import credential_findings
from test_c15_engine_calls import engine_findings

from pipeline.cases.c15 import assumptions as asm
from pipeline.cases.c15 import book, curves, page
from pipeline.io import bcch

LONG = "long-uf"


def test_adversarial_a_refused_answer_and_a_missing_observation_are_not_read_as_data() -> None:
    refused = json.dumps({"Codigo": -5, "Descripcion": "Invalid username or password", "Series": {"Obs": None}}).encode("ascii")
    with pytest.raises(bcch.BcchError):
        bcch.parse_series(refused)
    s = make_series("F022.X", {"2026-09-01": 2.5, "2026-09-02": None, "2026-09-03": 2.6})
    assert s.values() == {"2026-09-01": 2.5, "2026-09-03": 2.6} and s.missing() == ["2026-09-02"]
    latin = "Tasa de interés a 5 años".encode("latin-1")
    assert latin.decode("latin-1") != latin.decode("utf-8", errors="replace")


def test_adversarial_a_later_observation_changes_no_curve() -> None:
    series, infos = world()
    sel = curves.select(series, infos, "2026-09")
    base = curves.fit_curve(sel, series, "UR").block
    absurd = {c: make_series(c, {**s.values(), "2026-09-04": 99.0}) for c, s in series.items()}
    assert curves.fit_curve(sel, absurd, "UR").block == base
    # a series with no value on the valuation date moves the valuation date back to the last day all have one
    holed = dict(series)
    code = "F022.BUF.TIS.AN05.UF.Z.D"
    holed[code] = make_series(code, {**{k: v for k, v in series[code].values().items()}, "2026-09-02": None})
    assert curves.select(holed, infos, "2026-09").valuation_date == "2026-09-01"


def test_adversarial_a_changed_raw_file_and_a_credentialed_url_are_refused(tmp_path: Path) -> None:
    body = json.dumps({"Codigo": 0, "Descripcion": "Success", "Series": {"seriesId": "X", "Obs": []}}).encode("ascii")

    def transport(url: str) -> bytes:
        return body

    rows = bcch.fetch(tmp_path, ["F073.UFF.PRE.Z.D"], "2026-09-01", "2026-09-30", user="u", password="p", today="2026-10-16",
                      transport=transport, sleep=lambda s: None, clock=lambda: 0.0)
    f = tmp_path / "raw" / bcch.BCCH_DIR / rows[1]["name"]
    f.write_bytes(f.read_bytes() + b" ")
    with pytest.raises(ValueError, match="differs from its provenance record"):
        bcch.load_provenance(tmp_path)
    planted = "provenance url: https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?" + "user=someone&" + "pass=hunter2&function=GetSeries"
    assert credential_findings(planted, "planted")


def test_adversarial_an_edited_curve_parameter_is_found_by_the_engine_call_check() -> None:
    doc = d.mutated(d.variant(LONG))
    assert engine_findings(doc["outputs"]) == []
    doc["outputs"]["curves"]["ur"]["fit"]["parameters"][0]["value"] += 0.001
    assert any("fit_nelson_siegel parameters" in f for f in engine_findings(doc["outputs"]))


def test_adversarial_an_unstamped_assumption_and_an_unreconciled_item_are_refused() -> None:
    bad = dict(asm.REGISTRY)
    bad["currency_split"] = asm.Assumption(asm.REGISTRY["currency_split"].value, "share", "synthetic-stated", "stated by the bank")
    assert any("currency_split" in f for f in asm.check_registry(bad))
    doc = d.mutated(d.variant(LONG))
    item = doc["outputs"]["legs"][0]["items"][0]
    item["cash_flows"][0]["amount"] += 1000.0
    assert any("flows do not sum to its amount" in f for f in semantics.check_document(doc))


def test_adversarial_a_share_above_its_cap_without_cap_applied_is_refused() -> None:
    doc = d.mutated(d.variant(LONG))
    seg = next(s for s in doc["outputs"]["nmd_segments"] if s["category"] == "retail-operational")
    assert seg["requested_core_share"] > seg["core_share_cap"] and seg["cap_applied"] is True
    seg["cap_applied"] = False
    assert cs.errors(cs.schema_for_document(d.C15 / "x.json", doc), doc)
    assert any("cap_applied" in f for f in semantics.check_document(doc))
    seg["cap_applied"] = True
    seg["core_share_used"] = seg["requested_core_share"]
    assert any("core_share_used" in f for f in semantics.check_document(doc))


def test_adversarial_an_eve_computed_elsewhere_is_found_by_the_engine_call_check() -> None:
    doc = d.mutated(d.variant(LONG))
    doc["outputs"]["eve"]["rows"][0]["clp"]["delta_eve"] += 1.0
    assert any("delta_eve" in f for f in engine_findings(doc["outputs"]))
    assert semantics.check_document(doc)


def listing_findings(manifest: dict, sums: dict[str, str], docs: dict[str, Path]) -> list[str]:
    found = []
    listed = {a["path"]: a for a in manifest["artifacts"]}
    for name, path in docs.items():
        rel = f"C15/{name}.json"
        if rel not in listed:
            found.append(f"{rel}: not listed by the manifest")
        elif listed[rel]["bytes"] != path.stat().st_size:
            found.append(f"{rel}: size differs from the manifest")
        if sums.get(rel) != d.sha(path):
            found.append(f"{rel}: hash differs from the checksum file")
    return found


def test_adversarial_a_document_changed_after_hashing_and_a_missing_variant_are_found() -> None:
    manifest = d.load(d.DERIVED / "manifests" / "C15.json")
    sums = dict(reversed(line.split("  ", 1)) for line in (d.C15 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    docs = {**{v: d.C15 / f"{v}.json" for v in VARIANT_IDS}, d.MODELS: d.C15 / f"{d.MODELS}.json"}
    assert listing_findings(manifest, sums, docs) == []
    bad_sums = dict(sums)
    bad_sums[f"C15/{LONG}.json"] = "0" * 64
    assert any(LONG in f for f in listing_findings(manifest, bad_sums, docs))
    short = copy.deepcopy(manifest)
    short["artifacts"] = [a for a in short["artifacts"] if not a["path"].endswith("/short-uf.json")]
    assert any("short-uf" in f for f in listing_findings(short, sums, docs))


def test_adversarial_an_offset_not_applied_is_refused() -> None:
    doc = d.mutated(d.variant(LONG))
    assert doc["outputs"]["offset_rule"]["state"] == "on"
    pair = doc["outputs"]["eve"]["rows"][0]["pair"]
    pair["used"] = pair["with_offset"] + 1.0
    assert any("used does not follow the offset state" in f for f in semantics.check_document(doc))


def test_adversarial_a_floor_effect_that_does_not_recompute_is_refused() -> None:
    doc = d.mutated(d.variant(LONG))
    doc["outputs"]["floors"]["effects"].append({"leg": "CLP", "measure": "delta-eve", "shock": "parallel-down", "buckets_floored": 3,
                                                "delta_with_floor": 10.0, "delta_without_floor": 4.0, "effect": 6.0})
    found = semantics.check_document(doc)
    assert any("floor effect" in f or "buckets_floored" in f for f in found)


def test_adversarial_a_wrong_indexation_charge_is_refused() -> None:
    doc = d.mutated(d.variant(LONG))
    ic = doc["outputs"]["indexation_charge"]
    ic["charge"] = 0.03 * ic["abs_pn_ur"]
    assert any("2.5 percent" in f for f in semantics.check_document(doc))


def test_adversarial_an_edited_dynamic_nii_is_refused() -> None:
    doc = d.mutated(d.variant(LONG))
    doc["outputs"]["dynamic_nii"]["legs"][0]["scenarios"][1]["monthly_nii"][3] += 100.0
    assert any("monthly NII does not recompute" in f for f in semantics.check_document(doc))


def test_adversarial_another_seed_changes_the_book() -> None:
    a = book.build_book(SEED, book.SPECS[LONG], 40877.73)
    assert a.digest() == book.build_book(SEED, book.SPECS[LONG], 40877.73).digest()
    assert a.digest() != book.build_book(SEED + 1, book.SPECS[LONG], 40877.73).digest()
    assert not np.array_equal(a.legs["UR"].items[0].flows, book.build_book(SEED + 1, book.SPECS[LONG], 40877.73).legs["UR"].items[0].flows)


def test_adversarial_an_edited_results_block_is_found() -> None:
    text = (d.ROOT / "docs" / "cases" / "C15.md").read_text(encoding="utf-8")
    block = text.split(page.BEGIN, 1)[1].split(page.END, 1)[0]
    variants = {v: d.variant(v) for v in VARIANT_IDS}
    assert block.strip("\n") == page.results_block(variants, d.models()).strip("\n")
    first = next(ch for ch in block if ch.isdigit())
    edited = block.replace(first, str((int(first) + 1) % 10), 1)
    assert edited.strip("\n") != page.results_block(variants, d.models()).strip("\n")
