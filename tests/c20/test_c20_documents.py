"""CT-2002, CT-2004, CT-2007 to CT-2017, CT-2023, CT-2024: the committed C20 documents, from the real bake."""
from __future__ import annotations

from pathlib import Path

import contract_schemas as cs
from c20_support import (C20, MANIFEST, MODELS, PROHIBITED, SGCD_VARIANTS, TAIWAN_VARIANTS, VARIANTS, all_documents, committed, listing_problems,
                         load, semantics)

from pipeline.cases.c20 import fed, sgcd, v_shift

FAIR_IDS = ("fair.equalized_odds", "fair.equal_opportunity", "fair.calibration_within_groups", "fair.auc_by_group")
FORBIDDEN = ("fair.adverse_impact", "fair.demographic_parity", "four_fifths", "fair.two_proportion_z", "fair.fisher_exact")


def problems(doc: dict, path: Path | None = None) -> list[str]:
    """Schema errors, then the semantic findings, of one committed document."""
    ref = cs.schema_for_document(path or (C20 / "x.json"), doc)
    out = list(cs.errors(ref, doc))
    if "kind" in doc.get("outputs", {}):
        out += semantics().check_c20(doc)
    return out


def group_problems(doc: dict) -> list[str]:
    """The seen and held-out split is the protocol's: T1 to T3 carry F1 and F2, T4 to T6 carry F4 (a free choice is refused)."""
    o = doc["outputs"]
    want = sgcd.SEEN_BATCHES if o["seen_or_held_out"] == "seen" else sgcd.HELD_OUT_BATCHES
    shocks = {"seen": {"F0", "F1", "F2", "F3", "numeric-noise"}, "held-out": {"F0", "F4", "numeric-noise"}}[o["seen_or_held_out"]]
    out = []
    for block in ("shipped", "applied"):
        for r in o[block]["rows"]:
            if sorted(r["batches"]) != sorted(want):
                out.append(f"{block} {r['shock_id']}: batches {r['batches']} are not {list(want)}")
            if r["shock_id"] not in shocks:
                out.append(f"{block} {r['shock_id']}: a {o['seen_or_held_out']} document does not carry this shock")
    return out


def test_every_committed_document_validates_passes_the_checks_and_is_listed_with_its_hash() -> None:
    docs = all_documents()
    assert set(docs) == {*VARIANTS, MODELS}
    for name, doc in docs.items():
        assert problems(doc, C20 / f"{name}.json") == [], name
        for row in doc.get("tests", []):
            assert cs.errors("common/test-result", row) == [], (name, row["test_id"])
    manifest = load(MANIFEST)
    entries = {e["variant_id"]: e for e in manifest["artifacts"]}
    assert set(entries) == {*VARIANTS, MODELS} and manifest["case_id"] == "C20" and manifest["default_variant"] == VARIANTS[0]
    assert listing_problems(C20, manifest) == []
    for name in docs:
        path = C20 / f"{name}.json"
        assert entries[name]["path"] == f"C20/{name}.json" and entries[name]["bytes"] == path.stat().st_size
        if name != MODELS:
            assert entries[name]["models_ref"] == f"C20/{MODELS}.json"
    assert manifest["sources"] == ["santanderai-sgcd", "uci-taiwan", "uci-polish", "fed-stress-tests"] and manifest["expect"]
    assert all(manifest["source_details"][s]["class"] == "mirror-allowed" for s in manifest["sources"])
    assert (C20 / "raw-sources.txt").exists() and set(load(C20 / "raw-sources.txt")["sources"]) == {"santanderai-sgcd", "fed-stress-tests"}


def test_every_sgcd_document_carries_the_prohibited_use_sentence_and_no_other_does() -> None:
    docs = all_documents()
    for name in SGCD_VARIANTS:
        n = docs[name]["outputs"]["sgcd_notice"]
        assert n["quote"] == PROHIBITED and n["commit"] == "8403fa9048f7159d51a0cec5a2d9a2e9712662bd" and n["kind"] == "dataset-card-prohibition"
        assert n["text"]["en"] and n["text"]["es"] and docs[name]["outputs"]["dataset_id"] == "sgcd"
    assert docs[MODELS]["fit"]["sgcd"]["notice"]["quote"] == PROHIBITED and docs[MODELS]["fit"]["sgcd"]["seed"] == 42
    for name in set(VARIANTS) - set(SGCD_VARIANTS):
        assert docs[name]["outputs"]["sgcd_notice"] is None and docs[name]["outputs"]["dataset_id"] != "sgcd"


def test_the_shock_documents_split_seen_and_held_out_on_the_locked_test_batches() -> None:
    seen, held = committed("sgcd-seen"), committed("sgcd-held-out")
    assert group_problems(seen) == [] and group_problems(held) == []
    assert seen["outputs"]["seen_or_held_out"] == "seen" and held["outputs"]["seen_or_held_out"] == "held-out"
    assert seen["outputs"]["model_view"] == "json_view" and seen["outputs"]["model_dataset"] == "uci-german"
    for doc in (seen, held):
        o = doc["outputs"]
        assert o["shipped"]["label"] == "shipped" and o["shipped"]["parameters_source"] is None
        assert o["applied"]["label"] == "contraste-applied" and o["applied"]["parameters_source"] == "SGCDataset_metadata.json, seed 42"
        for block in ("shipped", "applied"):
            f0 = next(r for r in o[block]["rows"] if r["shock_id"] == "F0")
            assert f0["performance"]["auc_delta"] == 0.0 and f0["n_reaching_structured_view"] == 0 and f0["attribution_rank_correlation"] == 1.0
            for r in o[block]["rows"]:
                assert r["performance"]["auc"] - f0["performance"]["auc"] == r["performance"]["auc_delta"] or abs(
                    r["performance"]["auc"] - f0["performance"]["auc"] - r["performance"]["auc_delta"]) < 1e-6
                assert set(r["drift"]) == {"psi_max", "csi_max", "chi2_p_value", "variables"} and len(r["drift"]["variables"]) == 17
    # the shipped shocks reach a structured-only model through F1 only (U14 research addendum H4)
    shipped = {r["shock_id"]: r for r in seen["outputs"]["shipped"]["rows"]}
    assert shipped["F1"]["n_reaching_structured_view"] > 0 and shipped["F2"]["n_reaching_structured_view"] == 0
    assert all(r["n_reaching_structured_view"] == 0 for r in held["outputs"]["shipped"]["rows"])
    assert any(r["data_quality"]["consistency"] is not None and r["data_quality"]["consistency"] < 1 for r in held["outputs"]["shipped"]["rows"])


def test_the_fed_real_drift_is_the_engines_and_carries_no_model() -> None:
    doc = committed("fed-shift")
    rd = doc["outputs"]["real_drift"]
    assert rd["label"] == "real-drift-no-model" and rd["model"] is None and rd["portfolios"] == list(fed.PORTFOLIOS)
    assert [(p["a"], p["b"]) for p in rd["pairs"]] == list(v_shift.PAIRS)
    rows = {(r["segment"], r["test_id"]): r for r in doc["tests"] if r["model_id"] is None}
    for p in rd["pairs"]:
        assert [v["name"] for v in p["variables"]] == list(fed.VARIABLES)
        for v in p["variables"]:
            seg = f"{p['a']}>{p['b']}:{v['name']}"
            assert abs(rows[(seg, "stability.psi")]["metric"] - v["psi"]) < 1e-6 and abs(rows[(seg, "stability.csi")]["metric"] - v["csi"]) < 1e-6
            assert abs(rows[(seg, "stability.ks")]["statistic"] - v["ks"]) < 1e-6 and 0 <= v["ks"] <= 1
            if v["chi2_p_value"] is not None:
                assert abs(rows[(seg, "stability.chi2")]["p_value"] - v["chi2_p_value"]) < 1e-6
    rating = {(p["a"], p["b"]): next(v for v in p["variables"] if v["name"] == "rating") for p in rd["pairs"]}
    assert rating[("typical", "higher-risk")]["psi"] > 0.25 and rating[("typical", "lower-risk")]["psi"] > 0.25   # the risk mix is what differs


def test_the_synthetic_shift_touches_the_evaluation_rows_only() -> None:
    doc = committed("fed-shift")
    s = doc["outputs"]["synthetic_shift"]
    assert s["label"] == "synthetic-shift-fed-reference" and s["reference_portfolio"] == "higher-risk" and "locked" in s["evaluation_set"]
    n = int(s["evaluation_set"].split("(")[1].split(" rows")[0].replace(",", ""))
    assert n == round(0.30 * 10503) or abs(n - 0.30 * 10503) < 1                          # the stratified 30 percent holdout of the 3-year file
    assert {r["n_decisions"] for r in doc["outputs"]["impact_detail"]["rows"]} == {n}
    assert {w["n"] for w in s["label_free"]["conformal"]["coverage_by_window"]} == {n}
    shifts = {x["shift_id"]: x for x in s["shifts"]}
    assert list(shifts) == [f"fed-higher-risk-x{m:g}" for m in v_shift.MULTIPLES]
    anchor = next(v["psi"] for p in doc["outputs"]["real_drift"]["pairs"] if (p["a"], p["b"]) == v_shift.ANCHOR_PAIR
                  for v in p["variables"] if v["name"] == "rating")
    for m, x in zip(v_shift.MULTIPLES, s["shifts"]):
        assert abs(x["psi"] - m * anchor) / (m * anchor) < 0.02 and x["score"] > 0           # sized by the Fed rating drift
        assert 0 <= x["flip_share"] <= 1 and x["metric"]["auc_delta"] < 0 or x["metric"]["auc"] <= 1
    assert [x["score"] for x in s["shifts"]] == sorted(x["score"] for x in s["shifts"])
    assert doc["provenance"]["truth_status"] == "synthetic-known-truth"


def test_conformal_cbpe_and_the_shift_reference_are_the_engines_and_the_cbpe_is_an_estimate() -> None:
    doc = committed("fed-shift")
    lf = doc["outputs"]["synthetic_shift"]["label_free"]
    c = lf["conformal"]
    assert c["alpha"] == 0.1 and c["target_coverage"] == 0.9 and c["label"] == "convention"
    assert [w["window"] for w in c["coverage_by_window"]] == ["baseline", *[f"fed-higher-risk-x{m:g}" for m in v_shift.MULTIPLES]]
    cb = lf["cbpe"]
    assert cb["label"] == "estimate" and [a["id"] for a in cb["assumptions"]] == [i for i, _ in v_shift.ASSUMPTIONS]
    rows = {(r["test_id"], r["segment"]): r for r in doc["tests"]}
    est = rows[("ml.cbpe_estimate", "fed-higher-risk-x1")]
    assert est["light"] == "not_evaluated" and est["statistic"] is None and est["metric"] is None and est["extras"]["estimate"]["label"] == "estimate"
    assert abs(est["extras"]["estimate"]["estimated_auc"] - cb["estimated_auc"]) < 1e-6 and "measured" not in str(cb).lower()
    pooled = rows[("ml.conformal_coverage", "window:pooled")]
    assert abs(pooled["metric"] - c["coverage"]) < 1e-6 and pooled["extras"]["target"] == 0.9 and pooled["extras"]["n_cal"] > 0
    assert abs(pooled["extras"]["p_value_binomial"] - c["binomial_p_value"]) < 1e-9 if "p_value_binomial" in pooled["extras"] else True
    sr = rows[("ml.shift_resilience", "fed-higher-risk-x1")]
    assert sr["extras"]["shift_permutations"] == 199 and sr["extras"]["share"] == 0.1 and sr["p_value"] is not None
    w = doc["outputs"]["synthetic_shift"]["worst_subsample"]
    assert w["share"] == 0.1 and abs(w["metric"]["auc_delta"] + sr["metric"]) < 1e-6


def test_the_seed_sweep_has_twenty_seeds_per_boosted_rung_and_the_engines_statistics() -> None:
    doc = committed("seed-sweep")
    rows = {r["rung"]: r for r in doc["outputs"]["rows"]}
    assert list(rows) == ["P4-lightgbm", "P4-xgboost"]
    tests = {(r["test_id"], r["model_id"]): r for r in doc["tests"]}
    for rung, r in rows.items():
        mid = f"{rung}-taiwan"
        ss = tests[("ml.seed_stability", mid)]
        assert r["n_seeds"] == 20 == ss["n"] and abs(ss["metric"] - r["auc"]["sd"]) < 1e-9 and abs(ss["extras"]["mean"] - r["auc"]["mean"]) < 1e-9
        assert 0 <= r["grade_assignment_changed_share"] <= 1 and -1 <= r["attribution_rank_tau"]["min"] <= r["attribution_rank_tau"]["mean"] <= 1
    assert doc["outputs"]["impact_detail"]["rows"][0]["shift_id"] == "seed-42" and len(doc["outputs"]["impact_detail"]["rows"]) == 20


def test_the_reason_codes_use_100_refits_and_the_attributions_add_up() -> None:
    doc = committed("seed-sweep")
    tests = {(r["test_id"], r["model_id"]): r for r in doc["tests"]}
    for r in doc["outputs"]["rows"]:
        ov = r["reason_code_overlap"]
        row = tests[("ml.reason_code_stability", f"{r['rung']}-taiwan")]
        assert ov["top_k"] == 4 and ov["n_refits"] == 100 == row["n"] and abs(row["metric"] - ov["mean"]) < 1e-9
        assert 0 <= ov["p05"] <= 1 and 0 <= ov["mean"] <= 1 and row["extras"]["thresholds"]["top_k"] == 4
        add = tests[("ml.additivity", f"{r['rung']}-taiwan")]
        assert add["metric"] < 1e-5                                         # TreeSHAP adds up to the margin (float32 in XGBoost)
    assert tests[("ml.additivity", "P4-lightgbm-taiwan")]["light"] == "green"


def test_the_explainer_agreement_reads_shap_against_the_ale_ranges() -> None:
    doc = committed("seed-sweep")
    tests = {(r["test_id"], r["model_id"]): r for r in doc["tests"]}
    for e in doc["outputs"]["explainer_agreement"]:
        assert e["effect_reference"] == "ale" and e["n_features"] == 20 and len(e["top_features"]) <= 10
        assert e["rank_correlation"] is not None and e["reason_if_null"] is None
        row = tests[("ml.effect_agreement", f"{e['rung']}-taiwan")]
        assert abs(row["metric"] - e["rank_correlation"]) < 1e-9
        imps = [f["shap_importance"] for f in e["top_features"]]
        assert imps == sorted(imps, reverse=True)
        for f in e["top_features"]:
            assert len(f["ale"]["effect"]) == len(f["ale"]["edges"]) - 1 and abs(max(f["ale"]["effect"]) - min(f["ale"]["effect"]) - f["effect_range"]) < 1e-9


def test_the_perturbation_grid_adds_the_noise_to_the_evaluation_set_and_the_finding_is_the_engines() -> None:
    doc = committed("perturbation-grid")
    o = doc["outputs"]
    assert [r["eps"] for r in o["rows"]] == [0.0, 0.05, 0.1, 0.25, 0.5, 1.0] and o["preset_eps"] == 0.1
    assert o["rows"][0]["metric"]["auc_delta"] == 0.0 and o["rows"][0]["finding"] is False
    aucs = [r["metric"]["auc"] for r in o["rows"]]
    assert aucs == sorted(aucs, reverse=True)                                 # more noise never helps this model
    row = next(r for r in doc["tests"] if r["test_id"] == "ml.robustness")
    preset = next(r for r in o["rows"] if r["eps"] == 0.1)
    assert abs(row["metric"] + preset["metric"]["auc_delta"]) < 1e-6 and row["extras"]["preset_eps"] == 0.1
    assert preset["finding"] == (-preset["metric"]["auc_delta"] > 0.02) and row["extras"]["grid"] == [r["eps"] for r in o["rows"]]


def test_the_overfit_and_weak_spot_rows_and_the_decision_flip_impact_use_the_fixed_cutoff() -> None:
    for name in VARIANTS:
        doc = committed(name)
        ib = doc["outputs"]["impact_detail"]
        assert ib["label"] == "decision-flip" and ib["cutoff"] == {"rule": "reject-worst-share-of-baseline-scores", "reject_share": 0.2, "label": "convention"}
        flips = [r["flip_share"] for r in ib["rows"]]
        assert flips and all(0 <= f <= 1 for f in flips) and abs(doc["impact"]["decision_flip_share"]["value"] - max(flips)) < 1e-6
        assert doc["impact"]["decision_flip_share"]["unit"] == "share" and "cut-off" in doc["impact"]["decision_flip_share"]["label"]["en"]
        if name != "leakage-planted":
            assert any(r["test_id"] == "ml.overfit" for r in doc["tests"]), name
    pert = committed("perturbation-grid")
    assert any(r["test_id"] == "ml.weak_spot" and r["extras"]["thresholds"] for r in pert["tests"])
    assert [r["shift_id"] for r in pert["outputs"]["impact_detail"]["rows"]] == [f"noise-{e:g}" for e in (0.05, 0.1, 0.25, 0.5, 1.0)]


def test_the_leakage_screen_catches_the_planted_leak_and_not_the_control() -> None:
    doc = committed("leakage-planted")
    o = doc["outputs"]
    assert o["planted_feature"] == "future_status_code" and o["caught"] is True
    s = o["screen"]
    assert s["single_feature_auc"]["feature"] == "future_status_code" and s["single_feature_auc"]["suspect"] and s["single_feature_auc"]["max_auc"] > 0.95
    assert s["temporal_order"]["violations"] > 0 and s["entity_overlap"]["share"] == 0.0 and 0.0 <= s["resemblance_auc"] <= 1.0
    assert o["thresholds"]["single_feature_auc"] == {"value": 0.95, "label": "convention"}
    assert o["thresholds"]["resemblance_auc"] == {"value": 0.7, "label": "convention"}
    assert o["performance"]["development_auc"] > 0.97 and o["performance"]["decision_time_auc"] < 0.65      # performance collapses at decision time
    rows = {r["model_id"]: r for r in doc["tests"] if r["test_id"] == "ml.leakage_screen"}
    assert rows["P4-lightgbm-taiwan-planted-leak"]["light"] == "red" and rows["P4-lightgbm-taiwan"]["light"] == "green"     # the control passes
    assert rows["P4-lightgbm-taiwan"]["extras"]["screens"]["temporal"]["value"] == 0


def test_the_fairness_battery_runs_on_the_taiwan_model_only_with_twelve_labelled_rows() -> None:
    for name in VARIANTS:
        doc = committed(name)
        b = doc["outputs"]["fairness_battery"]
        ids = {r["test_id"] for r in doc["tests"]}
        assert not ids & set(FORBIDDEN), name                                  # no four-fifths flag and no group-rate test in C20
        if name in TAIWAN_VARIANTS:
            assert b["label"] == "labelled-fairness-battery" and b["model"] == "uci-taiwan" and doc["outputs"]["model_dataset"] == "uci-taiwan"
            assert len(b["rows"]) == 12 and {(r["test_id"], r["attribute"]) for r in b["rows"]} == {(t, a) for t in FAIR_IDS for a in ("sex", "age", "marital_status")}
            assert "not a compliance statement" in b["notice"]["en"] and b["notice"]["es"]
            fair = {(r["test_id"], r["segment"]): r for r in doc["tests"] if r["test_id"] in FAIR_IDS}
            assert len(fair) == 12
            for r in b["rows"]:
                t = fair[(r["test_id"], r["attribute"])]
                assert t["light"] == r["light"] and t["model_id"].endswith("taiwan") or t["model_id"].endswith("planted-leak")
                assert r["value"] is None or abs(t["metric"] - r["value"]) < 1e-9
                assert len(r["groups"]) >= 2 and all(g["n"] >= 1 for g in r["groups"])
        else:
            assert b is None and not ids & set(FAIR_IDS)


def test_the_findings_cite_only_rows_of_their_own_document() -> None:
    from pipeline.cases.c20.ops import evidence_id

    for name in VARIANTS:
        doc = committed(name)
        known = {evidence_id(r) for r in doc["tests"]} | {r["test_id"] for r in doc["tests"]}
        assert doc["findings"], name
        for f in doc["findings"]:
            assert f["evidence"] and set(f["evidence"]) <= known | {e for e in f["evidence"] if e.startswith("design:")}, (name, f["id"])
            assert f["severity"] in ("S2", "S3", "S4") and f["status"] in ("open", "accepted")
            if f["severity"] == "S4":
                assert f["status"] == "accepted" and all(e.startswith("design:") for e in f["evidence"])
            else:
                assert f["status"] == "open" and "not a compliance statement" in f["title"]["en"]
    assert any(f["id"].endswith("sgcd-not-for-scoring") for f in committed("sgcd-seen")["findings"])


def test_the_models_document_lists_the_ladders_with_their_datasets() -> None:
    doc = committed(MODELS)
    fit = doc["fit"]
    assert {d["id"] for d in fit["datasets"]} == {"sgcd", "uci-taiwan", "uci-polish", "fed-2025-corporate"}
    by = {}
    for r in fit["ladder"]:
        by.setdefault(r["dataset"], []).append(r["rung"])
    assert set(by) == {"uci-german", "uci-taiwan", "uci-polish"} and "P4-xgboost" in by["uci-taiwan"] and "P4-xgboost" not in by["uci-polish"]
    ids = {m["id"] for m in doc["model"]}
    assert len(ids) == len(doc["model"]) and all(m["family"] == "ml" and m["details"]["holdout_auc"] >= 0.5 for m in doc["model"])
    for name in VARIANTS:                                                      # the rungs a variant validates are in the models document
        assert {m["id"] for m in committed(name)["model"]} <= ids | {"P4-lightgbm-taiwan-planted-leak"}
    assert {p["name"] for p in fit["parameters"]} == set(semantics().APPROVED_PARAMS)
