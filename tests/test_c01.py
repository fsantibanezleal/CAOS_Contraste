"""C01 on its committed artifacts: CT-108 to CT-111. The shipped evidence is what these read; nothing is re-baked."""
from __future__ import annotations

import bisect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
BATTERY = ("disc.auc", "pd.jeffreys", "pd.binomial", "pd.binomial_vasicek", "pd.spiegelhalter", "pd.brier", "pd.ece",
           "rating.hhi")
# a constant PD ranks nobody and puts everyone in one grade: these are undefined for it, by design
NOT_FOR_CONSTANT = ("disc.ks", "stability.psi", "disc.auc_vs_initial", "pd.hosmer_lemeshow", "pd.chi2_grades")


def _read(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _read("manifests/C01.json")


def _variants(manifest: dict) -> list[tuple[dict, dict, dict]]:
    out = []
    for a in manifest["artifacts"]:
        if a["role"] == "variant":
            out.append((a, _read(a["path"]), _read(a["models_ref"])))
    return out


def _table_points(sc: dict, feature: str, value) -> int:
    """The points of the row a value falls in, from the committed points table and bins alone."""
    rows = [r for r in sc["points_table"] if r["feature"] == feature]
    spec = sc["bins"][feature]
    if value is None:
        return rows[-1]["points"]
    if spec["kind"] == "numerical":
        k = bisect.bisect_right(spec["splits"], float(value))
    else:
        k = next((i for i, cats in enumerate(spec["categories"]) if str(value) in cats), len(rows) - 1)
    return rows[k]["points"]


def test_points_table_recomputes_scores(manifest):
    checked = 0
    for a, v, models in _variants(manifest):
        sample = v["outputs"]["sample"]
        if sample is None:
            continue
        sc = next(m for m in models["model"] if m["id"] == "P1-scorecard")["details"]
        for i in range(len(sample["ids"])):
            points = [_table_points(sc, f, sample["inputs"][f][i]) for f in sc["features"]]
            assert points == sample["scorecard_points"][i], (a["variant_id"], sample["ids"][i])
            assert sum(points) == sample["scorecard_score"][i]
            checked += 1
    assert checked >= 100  # the holdout and the German twin, 50 applicants each


def test_every_rung_reports_the_battery(manifest):
    for a, v, _ in _variants(manifest):
        tests = {(t["test_id"], t["model_id"]) for t in v["tests"] if t["segment"] == "portfolio"}
        for m in v["model"]:
            for tid in BATTERY:
                assert (tid, m["id"]) in tests, (a["variant_id"], m["id"], tid)
            if m["id"] != "P0-constant":
                for tid in NOT_FOR_CONSTANT:
                    assert (tid, m["id"]) in tests, (a["variant_id"], m["id"], tid)
            if m["id"] not in ("P0-constant", "P1-scorecard"):
                assert ("disc.delong", m["id"]) in tests, (a["variant_id"], m["id"])
            auc = next(t for t in v["tests"] if t["test_id"] == "disc.auc" and t["model_id"] == m["id"])
            if m["id"] != "P0-constant":
                assert auc["extras"]["ci95_low"] < auc["metric"] < auc["extras"]["ci95_high"]
            grades = [t for t in v["tests"] if t["test_id"] == "pd.jeffreys" and t["model_id"] == m["id"]
                      and t["segment"] != "portfolio"]
            assert grades, (a["variant_id"], m["id"])  # calibration by grade is reported


def test_gbm_monotone_on_pdp_grid(manifest):
    for a in manifest["artifacts"]:
        if a["role"] != "models":
            continue
        models = _read(a["path"])
        for m in models["model"]:
            if m["rung"] != "P4":
                continue
            mono = m["details"]["monotonicity"]
            assert mono["monotone"], (a["variant_id"], m["id"])
            for f, spec in mono["features"].items():
                pdp = np.asarray(spec["pdp"])
                assert np.all(np.diff(pdp) * spec["direction"] >= -1e-12), (m["id"], f)
                assert spec["max_violation"] <= 1e-12, (m["id"], f)


def test_monotonicity_check_catches_a_violation():
    """The check is not vacuous: an unconstrained model of a U-shaped effect is caught."""
    from pipeline.model import gbm

    rng = np.random.default_rng(0)
    x = rng.normal(size=3000)
    y = (rng.random(3000) < 1 / (1 + np.exp(-(x**2 - 1)))).astype(int)
    X = pd.DataFrame({"x": x, "z": rng.normal(size=3000)})
    free = gbm.fit_lightgbm(X, y, (), features=["x", "z"], categorical=(), monotone={"x": 0, "z": 0}, seed=1,
                            rounds=60)
    free.constraints = [1, 0]  # declare a direction the model was never held to
    assert not gbm.monotonicity(free, X, seed=1)["monotone"]


def test_expected_ranges_hold(manifest):
    values: dict[str, float] = {}
    for a, v, _ in _variants(manifest):
        for t in v["tests"]:
            if t["segment"] != "portfolio":
                continue
            key = f"{t['model_id']}_{a['variant_id']}"
            if t["test_id"] == "disc.auc":
                values[f"auc_{key}"] = t["metric"]
            elif t["test_id"] == "stability.psi":
                values[f"psi_{key}"] = t["metric"] if t["metric"] is not None else t["statistic"]
            elif t["test_id"] == "pd.jeffreys":
                values[f"jeffreys_p_{key}"] = t["p_value"]
        if a["variant_id"] == "holdout":
            values["holdout_default_rate"] = v["outputs"]["defaults"] / v["outputs"]["n"]
            cut = v["outputs"]["rungs"]["P1-scorecard"]["cutoff"]
            rev, trn = cut["capital_per_lgd"]["basel3"][-1], cut["capital_per_lgd_transactors"]["basel3"][-1]
            values["capital_share_P1-scorecard_holdout"] = 0.5 * rev / cut["ead"][-1]
            values["transactor_effect_P1-scorecard_holdout"] = (rev - trn) / rev
    assert manifest["expect"], "the case declares its expected ranges"
    for name, (lo, hi) in manifest["expect"].items():
        assert name in values, name
        assert lo <= values[name] <= hi, (name, values[name], lo, hi)


def test_irb_capital_states_its_assumptions(manifest):
    """CT-212: every rung of every variant carries the capital at unit LGD along its cut-offs under the three regimes,
    and the variant states the class, the floors, the scaling, the EAD convention and the references it used."""
    for a, v, _ in _variants(manifest):
        irb = v["outputs"]["irb"]
        cards = a["variant_id"] != "german-twin"
        assert irb["asset_class"] == ("qrre" if cards else "other_retail")
        assert irb["regimes"] == ["basel3", "crr3", "basel2"]
        for regime in irb["regimes"]:
            facts = irb["by_regime"][regime]
            assert facts["name"] and facts["references"]["pd_floor"] and facts["references"]["scaling"]
            assert facts["scaling"] == (1.06 if regime == "basel2" else 1.0)
            assert facts["pd_floor"] == (0.0003 if regime == "basel2" else 0.0005)
            if cards:
                assert facts["pd_floor_revolver"] == (0.0003 if regime == "basel2" else 0.001)
        assert irb["lgd_floor_basel3"] == (0.5 if cards else 0.3) and "d424" in irb["lgd_floor_source"]
        assert irb["ead"]["en"] and irb["ead"]["es"]
        for rid, rung in v["outputs"]["rungs"].items():
            cut = rung["cutoff"]
            for regime in irb["regimes"]:
                curve = cut["capital_per_lgd"][regime]
                assert len(curve) == len(cut["approval_rate"]), (a["variant_id"], rid, regime)
                assert all(y >= x for x, y in zip(curve, curve[1:])), "approving more never lowers the capital"
                assert 0.0 < curve[-1] <= cut["ead"][-1], "capital at unit LGD is a fraction of the EAD"
        for key in ("capital_champion", "capital_challenger"):
            assert v["impact"][key]["value"] > 0 and "Basel III" in v["impact"][key]["label"]["en"]


def test_transactor_sensitivity_reported(manifest):
    """CT-214: the cards are all revolvers, the six-month full payers are counted, and their capital as transactors
    is reported, never above the revolvers' (the transactor's PD floor is the lower one)."""
    for a, v, _ in _variants(manifest):
        irb = v["outputs"]["irb"]
        if a["variant_id"] == "german-twin":
            assert irb["six_month_full_payers"] is None and not irb["revolvers_only"]
            assert all(r["cutoff"]["capital_per_lgd_transactors"] is None for r in v["outputs"]["rungs"].values())
            continue
        assert irb["revolvers_only"] is True
        assert 0 < irb["six_month_full_payers"] < v["outputs"]["n"]
        assert "d424" in irb["transactor_source"] and "152" in irb["transactor_source"]
        for rung in v["outputs"]["rungs"].values():
            cut = rung["cutoff"]
            for regime in irb["regimes"]:
                for rev, trn in zip(cut["capital_per_lgd"][regime], cut["capital_per_lgd_transactors"][regime], strict=True):
                    assert trn <= rev * (1 + 1e-12)


def test_hosmer_lemeshow_uses_g_on_the_holdout(manifest):
    """CT-312: the PDs were fitted on other data, so Hosmer-Lemeshow uses as many degrees of freedom as groups."""
    n = 0
    for _, v, _ in _variants(manifest):
        for t in v["tests"]:
            if t["test_id"] == "pd.hosmer_lemeshow":
                assert t["extras"]["dof"] == t["extras"]["groups"] and t["extras"]["fitted"] is False, t["model_id"]
                n += 1
    assert n > 0


def test_auc_vs_initial_carries_the_development_variance(manifest):
    """CT-313: the calibration slice's AUC is an estimate on rows disjoint from the evaluation set: its variance is
    added to the ECB statistic, and the result says so."""
    n = 0
    for _, v, _ in _variants(manifest):
        for t in v["tests"]:
            if t["test_id"] == "disc.auc_vs_initial" and t["p_value"] is not None:
                assert t["extras"]["auc_initial_variance"] > 0 and "extension" in t["notes"], t["model_id"]
                assert t["extras"]["s2_total"] == pytest.approx(t["extras"]["s2"] + t["extras"]["auc_initial_variance"])
                n += 1
    assert n > 0


# BL-114: M-3's acceptance criterion (a stable rule set) is not met on these data, and the committed record says so.
PLTR_STABILITY = {  # fit id -> (bootstraps, mean Jaccard, minimum Jaccard) as committed in the models documents
    "taiwan": (20, 0.4111636883971241, 0.36666666666666664),
    "taiwan-small": (20, 0.3488954306403951, 0.2808219178082192),
    "german": (20, 0.28042128235694763, 0.19642857142857142),
}
UNSTABLE_BELOW = 0.5  # a mean Jaccard below this reads as an unstable rule set


def _pltr_stability(fit_id: str) -> dict:
    doc = _read(f"C01/models-{fit_id}.json")
    (rung,) = [m for m in doc["model"] if m["id"] == "P2b-pltr"]
    return rung["details"]["stability"]


@pytest.mark.parametrize("fit_id", sorted(PLTR_STABILITY))
def test_pltr_rule_sets_are_unstable_across_20_bootstraps(fit_id):
    """BL-114, M-3: the committed Jaccard stability of the PLTR rule sets over 20 bootstraps, read as a measured result.
    The means are below 0.5, so the rule sets are unstable on these data; the criterion is the measurement, not a pass."""
    boots, mean, low = PLTR_STABILITY[fit_id]
    s = _pltr_stability(fit_id)
    assert s["bootstraps"] == boots == len(s["jaccard"])
    assert s["jaccard_mean"] == pytest.approx(mean, abs=1e-12)
    assert s["jaccard_min"] == pytest.approx(low, abs=1e-12)
    assert s["jaccard_mean"] == pytest.approx(float(np.mean(s["jaccard"])), abs=1e-12)
    assert s["jaccard_min"] == pytest.approx(min(s["jaccard"]), abs=1e-12)
    assert 0.0 <= s["jaccard_min"] <= s["jaccard_mean"] < UNSTABLE_BELOW


def test_the_unstable_pltr_rule_sets_are_said_in_plain_words_where_the_stability_is_stated():
    """BL-114: the SDD row, the C01 page and the live view state the instability instead of leaving the numbers bare."""
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    (row,) = [ln for ln in sdd.splitlines() if ln.startswith("| M-3 |")]
    assert "unstable" in row and "partial result" in row and "0.411" in row and "0.349" in row and "0.280" in row
    page = (ROOT / "docs" / "cases" / "C01.md").read_text(encoding="utf-8")
    assert "unstable" in page and "0.411" in page and "0.280" in page
    view = (ROOT / "frontend" / "src" / "workbench" / "ModelViews.tsx").read_text(encoding="utf-8")
    assert "unstable" in view and "inestable" in view


# BL-115: M-5 reports the Brier and the reliability before and after the calibration map.
def test_the_brier_before_and_after_calibration_is_stored_for_every_rung(manifest):
    """BL-115, M-5: `brier` (the evaluated PD) beside `brier_raw` (the raw score, before the map; null for a rung with no
    map), on every rung of every variant, and the first is the Brier of the battery's own row."""
    n_cal = 0
    for _, v, _ in _variants(manifest):
        rows = {t["model_id"]: t["metric"] for t in v["tests"] if t["test_id"] == "pd.brier"}
        for rid, r in v["outputs"]["rungs"].items():
            assert r["brier"] == pytest.approx(rows[rid], abs=1e-8), (v["variant_id"], rid)
            if r["reliability_raw"] is None:
                assert r["brier_raw"] is None, (v["variant_id"], rid)
            else:
                assert 0.0 < r["brier_raw"] < 1.0 and r["brier_raw"] != r["brier"], (v["variant_id"], rid)
                n_cal += 1
    assert n_cal > 0


# BL-116: the tier ruling of 2026-11-15 in the Method ladder.
def _ladder() -> dict[str, tuple[str, str, str]]:
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    section = sdd.split("\n## Method ladder", 1)[1].split("\n## ", 1)[0]
    out = {}
    for ln in section.splitlines():
        cells = [c.strip() for c in ln.strip().strip("|").split(" | ")] if ln.startswith("| ") else []
        if len(cells) >= 5 and cells[0][:2] in ("M-", "BS"):
            out[cells[0]] = (cells[1], cells[2], cells[4])
    return out


RULED_CLASSICAL = ("M-10", "M-17", "M-18", "M-20", "M-22", "M-24", "M-25", "M-35")
RULED_SOTA = ("M-3", "M-4", "M-5", "M-6", "M-9", "M-11", "M-23", "M-29", "M-30", "M-31", "M-32", "M-33", "M-34", "M-36",
              "M-37", "M-38")  # M-39 is not yet a row: it needs a level 3 notebook (BLOCKED in the report of tiers-closure-fixes-2026-11-15)


def _tier_findings(ladder: dict[str, tuple[str, str, str]]) -> list[str]:
    """Every way a ladder departs from the ruling of 2026-11-15 on the tiers (BL-116)."""
    out = [f"{m} is {ladder[m][0]}, ruled classical" for m in RULED_CLASSICAL if ladder.get(m, ("absent",))[0] != "classical"]
    out += [f"{m} is {ladder.get(m, ('absent',))[0]}, ruled sota" for m in RULED_SOTA if ladder.get(m, ("absent",))[0] != "sota"]
    out += [f"BS-{n} is not beyond" for n in range(1, 17) if ladder.get(f"BS-{n}", ("absent",))[0] != "beyond"]
    sota = sorted(k for k, v in ladder.items() if v[0] == "sota")
    out += [f"the sota rows are {sota}"] if set(sota) - set(RULED_SOTA) - {"M-39"} else []
    return out


def test_the_ladder_carries_the_ruled_tiers():
    ladder = _ladder()
    assert _tier_findings(ladder) == []
    # M-38 holds CAViaR and the GAS models; M-18 keeps the classical estimators of the extension
    assert "CAViaR" in ladder["M-38"][1] and "GAS" in ladder["M-38"][1] and "FZ0" in ladder["M-38"][1]
    assert "historical simulation" in ladder["M-18"][1] and "GJR" in ladder["M-18"][1] and "CAViaR" not in ladder["M-18"][1]
    # M-4's live-equals-offline clause is asserted by the parity test, which its gate names
    assert "frontend/src/engine/parity.test.ts" in ladder["M-4"][2] and "tests/test_c01.py" in ladder["M-4"][2]


def test_adversarial_a_ladder_with_a_ruled_method_in_the_wrong_tier_is_refused():
    ladder = _ladder()
    assert _tier_findings(ladder) == []
    for mid, wrong in (("M-24", "sota"), ("M-38", "classical"), ("M-3", "classical"), ("BS-8", "classical")):
        planted = dict(ladder)
        planted[mid] = (wrong, *ladder[mid][1:])
        assert any(mid in f for f in _tier_findings(planted)), mid
    planted = dict(ladder)
    del planted["M-38"]
    assert any("M-38 is absent" in f for f in _tier_findings(planted))
    planted = dict(ladder)
    planted["M-99"] = ("sota", "an unruled method", "x")
    assert any("the sota rows" in f for f in _tier_findings(planted))


def test_bs8_bs10_and_bs11_count_as_proposed_methods():
    sdd = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    ladder = _ladder()
    for mid in ("BS-8", "BS-10", "BS-11"):
        assert ladder[mid][1].startswith("Proposed method:"), mid
    assert "BS-1 to BS-12 are what Contraste does" not in sdd
    beyond = sdd.split("\n## Beyond the state of the art", 1)[1].split("\n## ", 1)[0]
    assert "count as proposed methods since the ruling of 2026-11-15" in beyond.split("- **BS-1**", 1)[0]
    for mid in ("BS-8", "BS-10", "BS-11"):  # the after-the-fact notes stay
        assert f"- **{mid}**" in beyond


def test_the_coverage_and_the_ladder_name_the_same_methods():
    ladder = _ladder()
    coverage = json.loads((ROOT / "notebooks" / "coverage.json").read_text(encoding="utf-8"))["methods"]
    assert set(coverage) == set(ladder)
    assert coverage["M-38"]
