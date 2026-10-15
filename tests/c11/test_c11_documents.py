"""CT-608 to CT-614: the documents of a bake of a small size (the first 30 forecast days of each window, a cheap part of the
ladder, few draws): they validate, pass the producer checks, are listed in the manifest, and are the same for the same seed.
The committed documents of the real bake run through the same checks (``test_committed_documents_...``)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from riskvalidation.validation import market as rv_val

from pipeline.cases.c11 import bake as _case, documents as docs
from pipeline.cases.c11.constants import WINDOWS
from pipeline.cases.c11.forecast import SPEC_BY_ID, Hyper
from pipeline.core.schemas import validate_document
from producer_checks import GATES, c11_models_violations, c11_variant_violations

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "data" / "derived"
CHEAP = ("hs-250", "awhs", "dn-rolling", "cf-rolling", "ewma", "garch-t", "fhs", "evt-mf")
BROAD = {f"n_forecast_days@{w.window_id}": (1.0, 1000.0) for w in WINDOWS}
DRAWS = dict(mc_draws=200, z2_draws=300)


def _bake(tmp_path, series, tiny, name, **kw):
    out = tmp_path / name
    args = dict(hp=tiny, model_ids=CHEAP, series=series, expect=BROAD, evidence_dir=None, limit=30, workers=1, **DRAWS)
    args.update(kw)
    return out, _case.bake_all(out, tmp_path, tmp_path / f"cache-{name}", **args)


@pytest.fixture(scope="module")
def mini(tmp_path_factory, series, tiny):
    tmp = tmp_path_factory.mktemp("c11-mini")
    return _bake(tmp, series, tiny, "a")


def load(root: Path, name: str) -> dict:
    return json.loads((root / "C11" / name).read_text(encoding="utf-8"))


def windows_of(root: Path) -> list[dict]:
    return [load(root, f"{w.window_id}.json") for w in WINDOWS]


def test_every_document_validates_and_passes_the_producer_checks(mini):
    root, manifest = mini
    assert [e["variant_id"] for e in manifest["artifacts"] if e["role"] == "variant"] == [w.window_id for w in WINDOWS]
    for doc in windows_of(root):
        validate_document(f"data/derived/C11/{doc['variant_id']}.json", doc)
        assert c11_variant_violations(doc) == [], doc["variant_id"]
        assert {m["rung"] for m in doc["outputs"]["models"]} == {"R1", "R2", "R3", "R4", "R5", "R6", "R7"}
    models = load(root, "models-ladder.json")
    assert c11_models_violations(models) == []
    assert [r["rung"] for r in models["fit"]["ladder"]][-1] == "R10" and models["fit"]["ladder"][-1]["status"] == "challenger-not-run"
    assert models["fit"]["ladder"][-1]["not_run_reason"]


def test_adversarial_a_document_missing_from_the_manifest_is_found(mini, tmp_path):
    root, manifest = mini

    def problems(doc_root: Path, man: dict) -> list[str]:
        listed = {a["path"]: a["bytes"] for a in man["artifacts"]}
        files = {f"C11/{p.name}": p for p in (doc_root / "C11").glob("*.json")}
        out = [f"{r} is not listed" for r in sorted(set(files) - set(listed))]
        out += [f"{r}: bytes differ" for r, p in files.items() if r in listed and listed[r] != p.stat().st_size]
        return out

    assert problems(root, manifest) == [] and len(manifest["artifacts"]) == 7
    broken = copy.deepcopy(manifest)
    broken["artifacts"] = broken["artifacts"][1:]
    assert problems(root, broken) != []
    shrunk = copy.deepcopy(manifest)
    shrunk["artifacts"][2]["bytes"] += 1
    assert problems(root, shrunk) != []
    validate_document("data/derived/manifests/C11.json", manifest)


def test_adversarial_two_bakes_with_one_seed_are_identical_and_another_seed_differs(mini, tmp_path, series, tiny):
    import dataclasses

    root, _ = mini
    again, _ = _bake(tmp_path, series, tiny, "b")              # a fresh cache: the forecasts are recomputed
    for p in sorted((root / "C11").glob("*.json")):
        assert p.read_bytes() == (again / "C11" / p.name).read_bytes(), p.name
    other, _ = _bake(tmp_path, series, dataclasses.replace(tiny, seed=7), "c", window_ids=("mixed-2023",))
    assert (other / "C11" / "mixed-2023.json").read_bytes() != (root / "C11" / "mixed-2023.json").read_bytes()


def test_the_traffic_light_is_not_evaluated_under_250_days_with_its_reason(mini):
    root, _ = mini
    for doc in windows_of(root):
        assert doc["outputs"]["window"]["n_forecast_days"] == 30
        for m in doc["outputs"]["models"]:
            for lv in m["by_level"]:
                tl = lv["traffic_light"]
                if lv["alpha"] == 0.01:
                    assert tl["final_zone"] == "not_evaluated" and "250" in tl["reason"] and tl["days_green"] is None
                else:
                    assert tl is None


def test_the_traffic_light_of_a_full_window_recomputes_from_the_exceedance_days(tmp_path, series, tiny):
    out, _ = _bake(tmp_path, series, tiny, "long", window_ids=("rates-2022",), model_ids=("hs-250", "ewma", "dn-rolling", "garch-t"),
                   limit=None)
    doc = load(out, "rates-2022.json")
    o = doc["outputs"]
    n = o["window"]["n_forecast_days"]
    assert n >= 250 and o["grid"]["realised_loss"]["status"] == "included"      # Treasury only: mirror-allowed
    assert c11_variant_violations(doc) == []                              # the producer recomputes zones, FZ0 and tick from the series
    for m in o["models"]:
        tl = next(lv for lv in m["by_level"] if lv["alpha"] == 0.01)["traffic_light"]
        assert tl["n_windows"] == n - 249 and tl["final_zone"] in ("green", "amber", "red")
        assert tl["days_green"] + tl["days_amber"] + tl["days_red"] == n - 249


def test_derived_only_windows_withhold_the_realised_loss(mini):
    root, _ = mini
    for doc in windows_of(root):
        rl = doc["outputs"]["grid"]["realised_loss"]
        derived = doc["outputs"]["window"]["asset_class"] in ("equity", "mixed")
        assert (rl["status"] == "withheld-derived-only") == derived and (rl["loss"] is None) == derived
        assert (rl["reason"] is not None) == derived


def test_es_is_not_below_var_and_the_champion_is_the_lowest_fz0_among_the_eligible(mini):
    root, _ = mini
    for doc in windows_of(root):
        o = doc["outputs"]
        assert not [v for v in c11_variant_violations(doc) if "ES below" in v]
        fz = {}
        for m in o["models"]:
            for lv in m["by_level"]:
                for var, es in zip(lv["var"], lv["es"], strict=True):
                    assert es is None or es >= var
                if lv["fz0_mean"] is not None and lv["n_fz0"] == lv["n_scored"]:
                    fz[(m["model_id"], lv["alpha"])] = lv["fz0_mean"]
        elig = {m["model_id"]: m["eligible"] for m in o["models"]}
        for c in o["comparison"]["champions"]:
            pool = {k[0]: v for k, v in fz.items() if k[1] == c["alpha"] and elig[k[0]]}
            if pool:
                assert c["model_id"] == min(pool, key=pool.get) and c["reason"] is None
            else:
                assert c["model_id"] is None and c["reason"]
        cf = next(m for m in o["models"] if m["model_id"] == "cf-rolling")
        assert all(lv["es_status"] == "not-forecast" and lv["fz0_mean"] is None and lv["fz0_reason"] for lv in cf["by_level"])


def test_adversarial_a_red_gate_makes_a_model_ineligible(mini):
    root, _ = mini
    doc = windows_of(root)[2]
    assert c11_variant_violations(doc) == []
    victim = doc["outputs"]["models"][0]
    row = next(t for t in doc["tests"] if t["model_id"] == victim["model_id"] and t["test_id"] == "market.kupiec_pof" and t["segment"] == "alpha=0.01")
    row["light"] = "red"                                                   # plant a red gate without moving the model's flag
    assert any("eligible or failed_gates" in v for v in c11_variant_violations(doc))
    assert all(r in GATES for r in victim["failed_gates"])


def test_adversarial_a_forecast_that_uses_its_own_day_is_found_by_the_producer_checks(mini):
    root, _ = mini
    doc = windows_of(root)[0]
    assert c11_variant_violations(doc) == []
    bad = copy.deepcopy(doc)
    g = bad["outputs"]["grid"]
    g["estimation_end"][5] = g["dates"][5]                                 # the window now ends on the forecast day
    assert any("not after its estimation end" in v for v in c11_variant_violations(bad))
    g2 = copy.deepcopy(doc)["outputs"]
    assert all(e < d for e, d in zip(g2["grid"]["estimation_end"], g2["grid"]["dates"], strict=True))


def test_adversarial_es_below_var_and_a_wrong_traffic_light_are_found(mini):
    root, _ = mini
    doc = windows_of(root)[2]
    lv = doc["outputs"]["models"][1]["by_level"][0]
    lv["es"][3] = lv["var"][3] * 0.5
    assert any("ES below VaR" in v for v in c11_variant_violations(doc))
    doc2 = windows_of(root)[2]
    doc2["outputs"]["models"][0]["by_level"][0]["traffic_light"]["final_zone"] = "green"
    doc2["outputs"]["models"][0]["by_level"][0]["traffic_light"]["reason"] = None
    assert any("must be not_evaluated" in v for v in c11_variant_violations(doc2))     # 30 days: decision D3


def _z2(loss, var, es, a, draws=2000):
    rows, null = docs.window_tests(SPEC_BY_ID["hs-250"], a, loss, var, es, Hyper(), mc=100, z2=draws)
    return next(r for r in rows if r["test_id"] == "market.acerbi_szekely"), null


def test_adversarial_the_z2_null_has_known_truth():
    """Losses drawn from the null's own law pass; the same losses against an ES halved fail, and the null is the engine's."""
    import sim

    n, a = 250, 0.025
    rng = np.random.default_rng(11)
    var = np.full(n, 0.02)
    es = np.full(n, 0.03)
    hit = rng.random(n) < a
    loss = np.where(hit, var + rng.exponential(1.0, n) * (es - var), 0.0)
    ok, null = _z2(loss, var, es, a)
    assert ok["light"] in ("green", "amber") and ok["p_value"] > 0.001 and null is not None
    assert null["n_draws"] == 2000 and sum(null["histogram"]["counts"]) == 2000 and len(null["histogram"]["edges"]) == 21
    heavy = np.where(hit, var + rng.exponential(1.0, n) * (es - var) * 6.0, 0.0)        # a true tail six times the stated one
    heavy[:5] = 0.2                                                                         # and five clear breaches
    bad, _ = _z2(heavy, var, es, a, 20000)       # red needs a p-value below 1e-4, which 20,000 draws can resolve
    assert bad["light"] == "red" and bad["statistic"] < ok["statistic"]
    na, none = _z2(loss, var, np.where(np.arange(n) == 4, np.nan, es), a)
    assert na["light"] == "not_evaluated" and none is None and na["statistic"] is None
    assert sim.iid_t(5, 5, 1).size == 5


def test_adversarial_the_simulator_known_truth_separates_the_oracle_from_a_misspecified_var():
    import sim

    n, alpha = 4000, 0.01
    losses = -sim.iid_t(n, 5, 21)                                  # unit-variance Student-t(5) returns, known law
    from scipy import stats

    oracle = -stats.t.ppf(alpha, 5) * np.sqrt(3.0 / 5.0)            # the true 1 percent loss quantile
    normal = -stats.norm.ppf(alpha)                                 # a normal VaR with the true volatility
    k_oracle = rv_val.kupiec_pof((losses > oracle).astype(int), alpha, "oracle")
    k_normal = rv_val.kupiec_pof((losses > normal).astype(int), alpha, "normal")
    assert k_oracle.light.value != "red" and k_normal.light.value == "red"


def test_the_findings_cite_tests_of_the_document(mini):
    root, _ = mini
    for doc in windows_of(root):
        ids = {t["test_id"] for t in doc["tests"]}
        assert doc["findings"] and all(set(f["evidence"]) <= ids for f in doc["findings"])


def committed_files() -> list[Path]:
    return sorted((COMMITTED / "C11").glob("*.json")) if (COMMITTED / "C11").exists() else []


def test_committed_documents_validate_pass_the_producer_checks_and_are_listed_with_their_hash():
    files = committed_files()
    assert len(files) == 7, "the six window documents and the models document are committed"
    manifest = json.loads((COMMITTED / "manifests" / "C11.json").read_text(encoding="utf-8"))
    validate_document("data/derived/manifests/C11.json", manifest)
    listed = {a["path"]: a["bytes"] for a in manifest["artifacts"]}
    for p in files:
        doc = json.loads(p.read_text(encoding="utf-8"))
        validate_document(f"data/derived/C11/{p.name}", doc)
        assert listed[f"C11/{p.name}"] == p.stat().st_size
        if p.name.startswith("models-"):
            assert c11_models_violations(doc) == []
        else:
            assert c11_variant_violations(doc) == [], p.name
    page = (ROOT / "docs" / "cases" / "C11.md").read_text(encoding="utf-8")
    for p in files:
        assert hashlib.sha256(p.read_bytes()).hexdigest() in page, f"the case page lists the hash of {p.name}"


def spanish_strings(node):
    """Every Spanish string of a document: the value under an ``es`` key of a bilingual text."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "es" and isinstance(v, str):
                yield v
            else:
                yield from spanish_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from spanish_strings(v)


def decimal_point_findings(doc) -> list[str]:
    import re

    return [s for s in spanish_strings(doc) if re.search(r"\d\.\d", s)]


def test_adversarial_no_spanish_string_writes_a_decimal_with_a_point(mini):
    root, _ = mini
    docs_ = windows_of(root) + [load(root, "models-ladder.json")]
    docs_ += [json.loads(p.read_text(encoding="utf-8")) for p in committed_files()]
    for d in docs_:
        assert decimal_point_findings(d) == []
    assert decimal_point_findings({"title": {"en": "lambda 0.94", "es": "lambda 0.94"}}) == ["lambda 0.94"]    # the planted defect is found
    assert decimal_point_findings({"title": {"en": "lambda 0.94", "es": "lambda 0,94"}}) == []
