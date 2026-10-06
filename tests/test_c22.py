"""C22 on its committed artifacts (CT-301 to CT-307): the size of every test, the power curves, the exact values, the
published reproductions, the findings' evidence, the lineage, determinism and the expected ranges. Nothing is re-baked
except one small simulation, twice, for determinism; the readers' tests use the fetched PDFs when the device data root
holds them."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

from pipeline.cases import c22_validator as c22
from pipeline.io import papers

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
DATA = os.environ.get("CONTRASTE_DATA")
WP14 = Path(DATA) / "raw" / "bcbs-wp14" / c22.WP14_PDF if DATA else None
YN = Path(DATA) / "raw" / "yurdakul-naranjo-2020" / c22.YN_PDF if DATA else None
needs_pdfs = pytest.mark.skipif(not (WP14 and WP14.exists() and YN and YN.exists()),
                                reason="the C22 PDFs are fetched into the device data root (CONTRASTE_DATA)")


def _read(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _read("manifests/C22.json")


@pytest.fixture(scope="module")
def variants(manifest) -> dict[str, dict]:
    return {a["variant_id"]: _read(a["path"]) for a in manifest["artifacts"] if a["role"] == "variant"}


def test_size_of_every_test_reported(variants):
    """CT-301: every registered riskvalidation test with a p-value at its null, 4,000 repetitions, both levels, with the
    Monte Carlo SE, the Wilson interval and the p-value histogram."""
    from riskvalidation.core.registry import catalogue

    null = variants["null"]["outputs"]
    assert {p["measures"] for p in null["panels"]} == {"size"}
    measured = {s["test_id"] for s in null["simulations"] if s["key"].endswith("@null")}
    registered = {s.test_id for s in catalogue() if s.decision == "p_value" and s.family != "selftest"}
    assert measured == registered, measured ^ registered
    for s in null["simulations"]:
        assert s["n_rep"] >= 4000 and s["p_histogram"] and sum(s["p_histogram"]) <= s["n_rep"]
        for rule in c22.RULES:
            r = s["rates"][rule]
            assert r["n"] == s["n_rep"] and r["wilson_low"] <= r["rate"] <= r["wilson_high"]
            assert r["se"] == pytest.approx(np.sqrt(r["rate"] * (1 - r["rate"]) / r["n"]), rel=1e-6, abs=1e-12)


def test_power_curves_complete(variants):
    """CT-302: each defect family measures its tests at severities 0 to 5, at both levels, with its ladder and unit, and
    the generator of every simulation is committed with its configuration and truth."""
    families = {v["id"] for v in c22.VARIANTS} - {"null"}
    assert families <= set(variants)
    for fam in families:
        o = variants[fam]["outputs"]
        assert o["ladder"] and len(o["ladder"]["values"]) == 6 and o["ladder"]["label"]["en"]
        for panel in o["panels"]:
            rows = [s for s in o["simulations"] if s["panel"] == panel["id"]]
            assert rows, (fam, panel)
            # a panel says whether its rates are power against the planted defect or sizes where the model is right
            assert panel["measures"] == ("size" if panel["id"] in c22.SIZE_PANELS.get(fam, ()) else "power"), (fam, panel["id"])
            if fam != "discrimination-decay" or panel["id"] != "development":
                tests = {s["test_id"] for s in rows if s["key"].count("@") == 1}
                for t in tests:
                    sev = sorted(s["severity"] for s in rows if s["test_id"] == t and s["label"] == next(
                        x["label"] for x in rows if x["test_id"] == t))
                    assert sev == list(range(6)) or fam == "leakage" and panel["id"] == "delong", (fam, panel["id"], t, sev)
        for s in o["simulations"]:
            assert set(s["rates"]) >= set(c22.RULES)
            g = o["generators"][s["generator"]]
            assert g["name"] and g["config"] and g["truth"] is not None


def test_exact_agrees_with_simulation(variants):
    """CT-303: wherever an exact rejection probability is committed, the simulated rate agrees with it."""
    count_tests = {"pd.binomial", "pd.jeffreys", "pd.binomial_vasicek"}
    n_exact = 0
    for fam, v in variants.items():
        for s in v["outputs"]["simulations"]:
            if s["test_id"] in count_tests:
                assert s["exact"] is not None, (fam, s["key"])
            if s["exact"] is None:
                continue
            for rule, p in s["exact"].items():
                n_exact += 1
                assert s["agrees"][rule], (fam, s["key"], rule, s["rates"][rule]["rate"], p)
    # 47 simulations carry an exact value (5 at the null, 24 under miscalibration, 18 under clustering; the traffic
    # lights over correlated years have none), at both levels
    assert n_exact == 94


def test_published_reproductions_carried(variants):
    """CT-304: WP14 Tables 7 and 8 in the clustering variant (143 of 144), Yurdakul and Naranjo Table 4 in the drift
    variant (cell by cell, with the systematic offset stated), Demler et al. in the leakage variant."""
    wp = variants["clustering"]["outputs"]["golden"][0]
    assert wp["study"] == "bcbs-wp14" and wp["total"] == 144 and wp["agree"] == 143
    bad = [c for c in wp["cells"] if not c["agrees"]]
    assert [(c["table"], c["row"], c["column"]) for c in bad] == [("Table 8", "DV_LV, traffic", "0.001")]
    yn = variants["drift"]["outputs"]["golden"][0]
    assert yn["study"] == "yurdakul-naranjo-2020" and yn["total"] == 54 and yn["agree"] >= 48
    assert "mean z" in yn["note"]["en"]
    dm = variants["leakage"]["outputs"]["golden"][0]
    assert dm["study"] == "demler-2012" and dm["cells"][0]["published"] == 0.001 and dm["cells"][0]["measured"] < 0.01
    for g in (wp, yn, dm):
        for c in g["cells"]:
            assert {"published", "measured", "z", "agrees"} <= set(c)


def test_findings_cite_rates(variants):
    """CT-305: every C22 finding is evidenced by measured rates of its own artifact."""
    for fam, v in variants.items():
        keys = {f"rate:{s['key']}" for s in v["outputs"]["simulations"]}
        assert v["findings"], fam
        for f in v["findings"]:
            assert f["evidence"] and all(e in keys for e in f["evidence"]), (fam, f["id"])


def test_lineage_and_determinism(manifest, variants):
    """CT-306: synthetic known truth with the generators named; a simulation is a pure function of the case seed."""
    for fam, v in variants.items():
        prov = v["provenance"]
        assert prov["truth_status"] == "synthetic-known-truth" and prov["generators"], fam
        assert prov["seed"] == manifest["seed"]
    srcs = {fam: [i["source"] for i in v["provenance"]["inputs"]] for fam, v in variants.items()}
    assert srcs["clustering"] == ["bcbs-wp14"] and srcs["drift"] == ["yurdakul-naranjo-2020"]
    from riskvalidation.generators import DefaultCounts, feed_cell

    rows = []
    for _ in range(2):
        book = c22.Book(manifest["seed"], "determinism")
        book.run("pd.binomial@x", "pd.binomial", DefaultCounts(1000, 0.01, rho=0.05), "g", panel="p", severity=0, x=0.0,
                 scenario={"en": "x", "es": "x"}, n_rep=500, feed=feed_cell())
        rows.append(book.rows[0])
    assert rows[0] == rows[1]
    assert c22._seed(42, "a") == c22._seed(42, "a") != c22._seed(42, "b")


def test_expected_ranges_hold(manifest):
    """CT-307: the declared ranges are in the manifest; the bake would have refused a result outside them."""
    expect = manifest["expect"]
    assert set(expect) == set(c22.EXPECT)
    for k, (lo, hi) in c22.EXPECT.items():
        assert expect[k] == [lo, hi]


@needs_pdfs
def test_paper_readers_check_the_print():
    """The readers parse the tables from the PDFs and refuse what does not match the print."""
    wp = papers.read_wp14_simulation(WP14)
    assert wp["runs"] == 25_000 and len(wp["table_7_type_i"]) == 8 and len(wp["table_8_type_ii"]) == 4
    assert wp["table_7_type_i"]["I_LC"]["normal"] == [0.13, 0.081, 0.055, 0.037, 0.028, 0.016]
    assert wp["scenarios_type_ii"]["DV_LV"]["true_pct"] == [1.5, 2.5, 3.5, 4.5, 6.5]
    yn = papers.read_yurdakul_naranjo_table4(YN)
    assert [(r["m"], r["n"]) for r in yn["rows"]][2] == (100, 400) and yn["rows"][2]["rates"][7] == 0.787
    with pytest.raises(papers.PaperTableError):
        papers.read_yurdakul_naranjo_table4(WP14)
