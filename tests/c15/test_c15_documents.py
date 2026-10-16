"""CT-1503, CT-1508 to CT-1512: the committed C15 documents."""
from __future__ import annotations

import re

import c15_docs as d
import contract_schemas as cs
import pytest
import semantics
from c15_support import ROOT, VARIANT_IDS


def test_the_six_variants_and_the_models_document_validate_pass_the_checks_and_are_listed_with_their_hash() -> None:
    files = list(d.C15.iterdir())
    names = sorted([*(f"{v}.json" for v in VARIANT_IDS), f"{d.MODELS}.json", "raw-sources.txt", "SHA256SUMS.txt"])
    assert sorted(f.name for f in files) == names
    manifest = d.load(d.DERIVED / "manifests" / "C15.json")
    assert cs.errors("common/case-manifest", manifest) == []
    docs = [f for f in files if f.suffix == ".json"]
    listed = {a["path"]: a for a in manifest["artifacts"]}
    sums = dict(reversed(line.split("  ", 1)) for line in (d.C15 / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    assert set(listed) == {f"C15/{f.name}" for f in docs} and set(sums) == set(listed) | {"C15/raw-sources.txt"}
    for f in docs:
        doc = d.load(f)
        assert d.problems(doc, f) == [], f.name
        assert doc["provenance"]["truth_status"] == "synthetic-calibrated"
        assert listed[f"C15/{f.name}"]["bytes"] == f.stat().st_size
        assert sums[f"C15/{f.name}"] == d.sha(f)
        out = doc["outputs"] if "outputs" in doc else doc["fit"]
        assert out["bank"]["synthetic"] is True and out["bank"]["name"] == "Banco Andino"
    for vid in VARIANT_IDS:
        doc = d.variant(vid)
        o = doc["outputs"]
        assert doc["variant_id"] == vid and o["variant"]["id"] == vid and o["kind"] == "annex1-variant"
        assert o["curves"]["clp"]["observed_kind"] == "secondary-market-yield" and o["curves"]["ur"]["observed_kind"] == "secondary-market-yield"
        assert o["as_of"] == o["curves"]["clp"]["date"] == o["curves"]["ur"]["date"] == o["ur_currency"]["uf_date"]
        assert o["balance_sheet_month"] == o["curves_month"] == "2026-09" and o["as_of"].startswith("2026-09-")
        assert "F073.UFF.PRE.Z.D" in o["ur_currency"]["uf_source"] and "Banco Central de Chile" in o["ur_currency"]["uf_source"]
        assert [i["source"] for i in doc["provenance"]["inputs"]] == ["bcch-bde"]
    assert d.sha(d.C15 / "raw-sources.txt") == sums["C15/raw-sources.txt"]
    assert d.models()["fit"]["curve_models"][0]["attribution"] and len(d.models()["fit"]["calibration_targets"]) >= 6


def test_the_offset_is_applied_in_every_variant_and_compared_on_and_off_in_one() -> None:
    for vid in VARIANT_IDS:
        o = d.variant(vid)["outputs"]
        want = "compared" if vid == "offset-on-off" else "on"
        assert o["offset_rule"]["state"] == want and o["offset_rule"]["share"] == 0.5
        pairs = [r["pair"] for r in o["eve"]["rows"]] + [r["pair"] for r in o["nii"]["rows"]]
        for p in pairs:
            assert p["without_offset"] >= p["with_offset"] - 1e-9 and p["used"] == p["with_offset"]
            assert p["opposite_signs"] == (p["delta_clp"] * p["delta_ur"] < 0)
            assert p["with_offset"] == pytest.approx(semantics.cmf_pair(p["delta_clp"], p["delta_ur"], True))
    o = d.variant("offset-on-off")["outputs"]
    opposite = [r for r in o["eve"]["rows"] if r["pair"]["opposite_signs"]]
    assert opposite and any(r["pair"]["with_offset"] < r["pair"]["without_offset"] for r in opposite)


def _distance_bp(o: dict) -> float:
    """The smallest distance, in bp, between a post-shock rate and its floor, recomputed from the document."""
    floors = {"clp": o["floors"]["other_floor"], "ur": o["floors"]["ur_floor"]}
    best = float("inf")
    for key in ("clp", "ur"):
        r0 = o["curves"][key]["zero_rates_at_midpoints"]
        for row in o["eve"]["rows"]:
            best = min(best, min((r0[k] + row[key]["shape_bp"][k] / 1e4 - floors[key]) * 1e4 for k in range(19)))
        for row in o["nii"]["rows"]:
            best = min(best, min((r0[k] + row[key]["shock_bp"] / 1e4 - floors[key]) * 1e4 for k in range(6)))
    return best


def test_the_floors_are_applied_and_the_distance_to_them_is_stated() -> None:
    for vid in VARIANT_IDS:
        o = d.variant(vid)["outputs"]
        f = o["floors"]
        assert (f["ur_floor"], f["other_floor"]) == (-0.02, 0.0)
        for e in f["effects"]:
            assert e["buckets_floored"] >= 1 and e["effect"] == pytest.approx(e["delta_with_floor"] - e["delta_without_floor"], abs=1e-6)
        text = f["rule"]["en"]
        m = re.search(r"smallest distance[^.]*? is (-?[0-9.]+) bp", text)
        assert m, text
        assert float(m.group(1)) == pytest.approx(_distance_bp(o), abs=0.01)
        assert "smallest distance" in f["rule"]["es"].lower() or "menor distancia" in f["rule"]["es"].lower()
        bound = [b for r in o["eve"]["rows"] for k in ("clp", "ur") for b in r[k]["floor_bound_buckets"]]
        assert bool(f["effects"]) == bool(bound or [b for r in o["nii"]["rows"] for k in ("clp", "ur") for b in r[k]["floor_bound_buckets"]])


def test_the_indexation_charge_and_the_cpi_surprise_are_the_stated_formulas_on_the_engine_values() -> None:
    from riskvalidation.irrbb import eve_nii

    for vid in VARIANT_IDS:
        o = d.variant(vid)["outputs"]
        ic, n = o["indexation_charge"], o["nii"]
        uf = o["ur_currency"]["uf_value"]
        ur = next(leg for leg in o["legs"] if leg["leg"] == "UR")
        pn = ur["net_position"] * uf
        assert ic["rate"] == 0.025 and ic["pn_ur"] == pytest.approx(pn) and ic["abs_pn_ur"] == pytest.approx(abs(pn))
        assert ic["charge"] == pytest.approx(eve_nii.indexation_charge(pn)) and n["indexation_charge"] == pytest.approx(ic["charge"])
        assert n["delta_nii"] == pytest.approx(n["max_pair"] + ic["charge"])
        assert ic["net_position_uf_units"] == pytest.approx(ur["net_position"])
        cpi = o["cpi_scenario"]
        if vid == "cpi-surprise":
            assert cpi["surprise_pp"] == 2.5 and cpi["effect"] == pytest.approx(-pn * 2.5 / 100)
        else:
            assert cpi is None
        if vid == "long-uf":
            assert pn > 0
        if vid == "short-uf":
            assert pn < 0
    assert d.variant("long-uf")["outputs"]["eve"]["delta_eve"] != d.variant("short-uf")["outputs"]["eve"]["delta_eve"]


def test_the_dynamic_nii_carries_both_legs_under_the_base_and_the_two_parallel_shocks() -> None:
    for vid in VARIANT_IDS:
        o = d.variant(vid)["outputs"]
        dn = o["dynamic_nii"]
        assert dn["horizon_months"] == 12 and dn["balance_sheet_assumption"]["kind"] == "constant" and dn["balance_sheet_assumption"]["growth_annual"] == 0
        assert [leg["leg"] for leg in dn["legs"]] == ["CLP", "UR"]
        beta = o["assumptions"]["deposit_beta"]["value"]
        for leg in dn["legs"]:
            assert [s["scenario"] for s in leg["scenarios"]] == ["base", "parallel-up", "parallel-down"]
            assert [s["shock_bp"] for s in leg["scenarios"]] == [0.0, 300.0, -300.0]
            assert all(len(s["monthly_nii"]) == 12 and len(s["short_rate_path"]) == 12 for s in leg["scenarios"])
            assert {i["side"] for i in leg["items"]} == {"asset", "liability"}
        clp = dn["legs"][0]
        assert any(i["side"] == "liability" and i["beta"] == pytest.approx(beta) for i in clp["items"])


def test_the_ear_evar_of_each_leg_carries_the_engine_monte_carlo_errors() -> None:
    for vid in VARIANT_IDS:
        o = d.variant(vid)["outputs"]
        assert [e["leg"] for e in o["ear_evar"]] == ["CLP", "UR"]
        for e, dl in zip(o["ear_evar"], o["dynamic_nii"]["legs"]):
            assert e["method"] == "hw1f" and e["n_paths"] >= 100000 and e["seed"] == 42 and e["n_batches"] == 20
            assert e["mc_error_method"] == "batch-means" and e["horizon_months"] == o["dynamic_nii"]["horizon_months"]
            assert e["base_nii"] == pytest.approx(dl["scenarios"][0]["total"], rel=1e-9)
            assert e["base_eve"] == pytest.approx(o["eve"]["base_eve_clp" if e["leg"] == "CLP" else "base_eve_ur"], rel=1e-9)
            assert {p["name"] for p in e["parameters"]} == {"a", "sigma"} and [lv["level"] for lv in e["levels"]] == [0.95, 0.99]
            for lv in e["levels"]:
                assert 0 < lv["ear_se"] < abs(lv["ear"]) and 0 < lv["evar_se"] < abs(lv["evar"])
                assert lv["ear"] == pytest.approx(e["base_nii"] - lv["nii_quantile"], abs=1e-3)
                assert lv["evar"] == pytest.approx(e["base_eve"] - lv["eve_quantile"], abs=1e-3)
            assert e["levels"][1]["ear"] >= e["levels"][0]["ear"] and e["levels"][1]["evar"] >= e["levels"][0]["evar"]


SCAN = ("data/derived/C15", "data/derived/manifests/C15.json", "docs/cases/C15.md", "docs/design/features/c15", "tests/c15", "data/sources/manifest.json",
        "data-pipeline/pipeline/io/bcch.py", "data-pipeline/pipeline/cases/c15", "changes/U10-P2.md")
URL_CREDENTIAL = re.compile(r"[?&](user|pass|password)=", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def committed_text_files() -> list:
    out = []
    for rel in SCAN:
        p = ROOT / rel
        out += [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file() and f.suffix in (".json", ".txt", ".md", ".py", ".csv")]
    return out


def credential_findings(text: str, name: str) -> list[str]:
    found = [f"{name}: a URL with a user or pass parameter" for _ in URL_CREDENTIAL.finditer(text)]
    found += [f"{name}: an e-mail address ({m.group(0)[:3]}...)" for m in EMAIL.finditer(text) if not m.group(0).endswith(("@example.org", "@example.com"))]
    return found


def test_no_committed_file_carries_a_credential_or_a_credentialed_url() -> None:
    files = committed_text_files()
    assert len(files) > 20
    findings = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        findings += credential_findings(text, f.relative_to(ROOT).as_posix())
    assert findings == []
    # the scan itself works
    assert credential_findings("see https://si3.bcentral.cl/x?" + "user=a&" + "pass=b", "x") and credential_findings("write to someone" + "@bank.cl", "y")
    for rows in d.load(d.C15 / "raw-sources.txt")["sources"].values():
        for r in rows["files"]:
            assert "pass" not in r["url"].lower() and "user" not in r["url"].lower() and r["sha256"] and r["bytes"] > 0 and r["retrieved"]
