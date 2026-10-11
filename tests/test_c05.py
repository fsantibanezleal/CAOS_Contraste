"""C05 on its committed artifacts (CT-201 to CT-208): the readers, the golden cells, the generator, coverage and power,
the impact, the expected ranges and the derived-only rule. Nothing is re-baked; the readers' own tests use the fetched
PDFs when the device data root holds them, and tampered prints that need no PDF."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path

import numpy as np
import pytest

from pipeline.io import papers

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"
DATA = os.environ.get("CONTRASTE_DATA")
TASCHE = Path(DATA) / "raw" / "tasche-2013" / "tasche-2013-arxiv-1212.3716v6.pdf" if DATA else None
PLUTO = Path(DATA) / "raw" / "pluto-tasche-2005" / "pluto-tasche-arxiv-cond-mat-0411699v3.pdf" if DATA else None
needs_pdfs = pytest.mark.skipif(not (TASCHE and TASCHE.exists() and PLUTO and PLUTO.exists()),
                                reason="the C05 PDFs are fetched into the device data root (CONTRASTE_DATA)")


def _read(rel: str) -> dict:
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _read("manifests/C05.json")


@pytest.fixture(scope="module")
def variants(manifest) -> dict[str, dict]:
    return {a["variant_id"]: _read(a["path"]) for a in manifest["artifacts"] if a["role"] == "variant"}


TABLE2_LINES = [
    "Table 2: S&P's corporate ratings, defaults and default rates (DR, %) in 2009, 2010 and 2011.",
    "Rating grade rated defaults DR rated defaults DR rated defaults DR",
]


def _fake_table2(rows: dict[str, str]) -> str:
    return "\n".join(TABLE2_LINES + [f"{g} {rows[g]}" for g in (*papers.SP_GRADES, "All")])


def _good_rows() -> dict[str, str]:
    rows = {g: "100 0 0.00 100 0 0.00 100 0 0.00" for g in papers.SP_GRADES}
    rows["CCC-C"] = "100 50 50.00 100 10 10.00 100 1 1.00"
    rows["All"] = "1700 50 2.94 1700 10 0.59 1700 1 0.06"
    return rows


def test_table2_reader_checks_the_print(monkeypatch):
    """CT-201: the reader refuses a table whose grades do not add up to its All row, or whose printed rate is not the
    counts' ratio; it accepts a consistent one."""
    monkeypatch.setattr(papers, "_pages", lambda pdf: [_fake_table2(_good_rows())])
    out = papers.read_tasche_table2(Path("fake.pdf"))
    assert out["years"][2009]["defaults"][-1] == 50 and out["years"][2011]["all"]["rated"] == 1700
    bad_sum = _good_rows() | {"All": "1700 51 3.00 1700 10 0.59 1700 1 0.06"}
    monkeypatch.setattr(papers, "_pages", lambda pdf: [_fake_table2(bad_sum)])
    with pytest.raises(papers.PaperTableError, match="All"):
        papers.read_tasche_table2(Path("fake.pdf"))
    bad_rate = _good_rows() | {"CCC-C": "100 50 49.00 100 10 10.00 100 1 1.00"}
    monkeypatch.setattr(papers, "_pages", lambda pdf: [_fake_table2(bad_rate)])
    with pytest.raises(papers.PaperTableError, match="printed"):
        papers.read_tasche_table2(Path("fake.pdf"))


@needs_pdfs
def test_table2_reader_on_the_paper():
    t2 = papers.read_tasche_table2(TASCHE)
    assert {y: (v["all"]["rated"], v["all"]["defaults"]) for y, v in t2["years"].items()} == {
        2009: (5860, 234), 2010: (5522, 63), 2011: (5847, 44)}
    res = papers.read_tasche_results(TASCHE, t2)
    assert res["table7"][2010]["p_value_pct"]["scaled_likelihood_ratio"] == 11.3
    assert res["table8"]["least_squares"][2010]["forecast_pct"] == 4.80


def test_pluto_tasche_reader_reads_every_table(monkeypatch):
    """CT-202: a table without its six levels, or with other rows than the paper prints, is refused."""
    text = "Table 1: Upper bound\nγ 50% 75% 90% 95% 99% 99.9%\nˆpB 0.09% 0.17% 0.29% 0.37% 0.57% 0.86%\n"
    monkeypatch.setattr(papers, "_pages", lambda pdf: [text])
    with pytest.raises(papers.PaperTableError, match="Table 1 prints rows"):
        papers.read_pluto_tasche_tables(Path("fake.pdf"))


@needs_pdfs
def test_pluto_tasche_reader_on_the_paper():
    tables = papers.read_pluto_tasche_tables(PLUTO)
    assert sorted(tables) == list(range(1, 15))
    assert tables[4]["rows"]["pa"][1] == 0.65 and tables[12]["rows"]["pb,scaled"][-1] == 9.54


def test_golden_cells_within_engine_tolerances(variants):
    """CT-203: every recomputed cell is within the tolerance riskvalidation documents for its table."""
    for vid in ("sp-2010", "sp-2011"):
        g = variants[vid]["outputs"]["golden"]
        if vid == "sp-2010":
            assert all(abs(c["gap"]) <= 0.001 + 1e-9 for c in g["table5"])
            assert all(abs(c["gap"]) <= 1e-4 + 1e-4 * c["printed"] + 1e-9 for c in g["table6"])
            assert all(abs(c["ours"] - c["printed"]) <= 0.005 + 0.002 * c["printed"] for c in g["table9_2009"])
        for cells in g["table7"].values():
            assert all(abs(c["gap"]) <= 1e-4 + 1e-4 * c["printed"] + 1e-9 for c in cells), vid
        for r in g["table7_p_values"]:
            p = r["ours_pct"] / 100.0
            tol = 300 * math.sqrt(p * (1 - p) / 2000) + 3 * r["mc_se_pct"] + 0.05
            assert abs(r["ours_pct"] - r["printed_pct"]) <= tol, (vid, r)
        for r in g["table8"]:
            assert abs(round(r["ours_pct"], 2) - r["printed_pct"]) <= 0.01 + 1e-9, (vid, r)
    cells = variants["ldp-published"]["outputs"]["golden"]["cells"]
    assert len(cells) == 204
    for c in cells:
        t, row, gamma, gap = c["table"], c["row"], c["gamma"], c["gap"]
        if t <= 6:
            assert gap == 0 or (t, gamma) == (4, 0.75), c
        elif t == 7:
            assert abs(gap) <= 0.01 + 1e-9, c
        elif t == 8:
            assert c["ours"] <= c["printed"] + 1e-9 and c["printed"] - c["ours"] <= 0.01, c
        elif t <= 12:
            if (t, row, gamma) == (12, "pb,scaled", 0.999):
                assert abs(gap + 0.10) < 1e-9, c  # the misprint, recorded
            else:
                assert abs(gap) <= (0.01 if row == "k" else 0.02) + 1e-9, c
        else:
            assert c["ours"] <= c["printed"] + 0.005, c
            if gamma >= 0.99:
                assert c["ours"] >= 0.94 * c["printed"], c


def test_generator_recovers_truth(variants):
    """CT-204: the generated default shares recover the true PDs within three binomial standard errors, and the
    overdispersion of the yearly count recovers the asset correlation."""
    out = variants["ldp-sim-1"]["outputs"]
    kt = out["known_truth"]
    years = kt["years"]
    for share, p, n in zip(kt["share_of_defaults_by_grade"], out["true_pd"], out["obligors"], strict=True):
        se = math.sqrt(p * (1 - p) / (years * n))
        # the yearly defaults are correlated, so the standard error of the share is inflated: allow the
        # one-factor design effect at this correlation (a factor below 4 at these sizes)
        assert abs(share - p) <= 3 * 4 * se, (share, p)
    od = kt["overdispersion"]
    assert od["variance_simulated"] > 2.5 * od["variance_independent"]
    assert abs(od["variance_simulated"] / od["variance_model"] - 1.0) <= 0.10
    assert 0.10 <= od["rho_moment_estimate"] <= 0.13


def test_coverage_and_power_reported(variants):
    """CT-205: coverage per method, grade and level with its binomial standard error; size and power per test."""
    kt = variants["ldp-sim-0"]["outputs"]["known_truth"]
    for method in ("independent", "correlated", "scaled", "scaled_correlated"):
        for g in ("A", "B", "C"):
            rows = kt["coverage"][method][g]
            assert [r["gamma"] for r in rows] == [0.5, 0.75, 0.9, 0.95, 0.99]
            for r in rows:
                assert 0.0 <= r["coverage"] <= 1.0
                # artifacts store nine significant digits
                assert r["se"] == pytest.approx(math.sqrt(r["coverage"] * (1 - r["coverage"]) / kt["years"]), rel=1e-8, abs=1e-15)
                assert r["ratio_q25"] <= r["ratio_median"] <= r["ratio_q75"]
    for truth in ("true", "expert"):
        assert set(kt["tests"][truth]) == {"jeffreys_A", "jeffreys_B", "jeffreys_C", "jeffreys_portfolio",
                                           "binomial_portfolio", "vasicek_portfolio"}
    # the correlation-aware test keeps its size; the independent ones do not
    assert kt["tests"]["true"]["vasicek_portfolio"]["reject_5"] <= 0.05 + 3 * math.sqrt(0.05 * 0.95 / kt["years"])
    assert kt["tests"]["true"]["jeffreys_portfolio"]["reject_5"] > 0.08
    assert variants["ldp-sim-0"]["outputs"]["known_truth"] == variants["ldp-sim-3"]["outputs"]["known_truth"]


def test_impact_states_its_assumptions(variants):
    """CT-206: the capital names its regime, class, LGD, maturity and floor, and it recomputes from the curves."""
    from riskvalidation.regulatory import capital_requirement

    for vid, v in variants.items():
        irb = v["outputs"]["irb"]
        assert {irb["regime"], irb["asset_class"]} == {"basel3", "corporate"} and irb["lgd"] == 0.45
        assert irb["maturity"] == 2.5 and irb["pd_floor"] == 0.0005 and irb["references"]["lgd"].startswith("CRE32.6")

        def rw(pd: float) -> float:
            return capital_requirement("corporate", pd, irb["lgd"], maturity=irb["maturity"], regime=irb["regime"]).risk_weight

        if vid.startswith("sp-"):
            pi = np.array(v["outputs"]["profile1"])
            curve = v["outputs"]["approaches"]["A4-slr"]["curve"]
            assert v["impact"]["rw_A4-slr"]["value"] == pytest.approx(float(np.sum(pi * [rw(p) for p in curve])), rel=1e-8)
        else:
            n = np.array(v["outputs"]["obligors"], dtype=float)
            expert = v["outputs"]["expert_pd"]
            assert v["impact"]["rw_expert"]["value"] == pytest.approx(float(np.sum(n * [rw(p) for p in expert]) / n.sum()), rel=1e-8)


def test_expected_ranges_hold(manifest, variants):
    """CT-207: every expected range, re-derived here from the artifacts, holds."""
    values: dict[str, float] = {}
    for vid in ("sp-2010", "sp-2011"):
        o = variants[vid]["outputs"]
        values[f"c_pd_{vid}"] = o["approaches"]["A3-spd"]["constants"]["c_pd"]
        values[f"c_lr_{vid}"] = o["approaches"]["A4-slr"]["constants"]["c_lr"]
        for aid in ("C2-ls", "C4-ilr"):
            values[f"forecast_pd_{aid}_{vid}"] = o["approaches"][aid]["pd"]
        for t in variants[vid]["tests"]:
            if t["test_id"] == "pd.default_profile":
                values[f"p_profile_{t['model_id']}_{vid}"] = t["p_value"]
    o = variants["sp-2010"]["outputs"]
    values["qmm_alpha_2009"], values["qmm_beta_2009"] = o["qmm0"]["alpha"], o["qmm0"]["beta"]
    values["golden_max_gap_table7_pct"] = o["golden"]["max_gap_table7_pct_beyond_relative"]
    b = variants["ldp-published"]["outputs"]["bounds"]
    values["bound_A_independent_50_ldp-published"] = b["independent"][0][0]
    values["bound_A_correlated_50_ldp-published"] = b["correlated"][0][0]
    kt = variants["ldp-sim-0"]["outputs"]["known_truth"]

    def cov(method: str, g: str, gamma: float, key: str = "coverage") -> float:
        return next(r for r in kt["coverage"][method][g] if r["gamma"] == gamma)[key]

    values["coverage_independent_C_90"] = cov("independent", "C", 0.9)
    values["coverage_correlated_C_90"] = cov("correlated", "C", 0.9)
    values["ratio_independent_C_90_median"] = cov("independent", "C", 0.9, "ratio_median")
    values["coverage_scaled_C_50"] = cov("scaled", "C", 0.5)
    values["power_jeffreys_portfolio_expert"] = kt["tests"]["expert"]["jeffreys_portfolio"]["reject_5"]
    values["true_pd_recovered_C"] = kt["share_of_defaults_by_grade"][2]
    assert manifest["expect"]
    for name, (lo, hi) in manifest["expect"].items():
        assert name in values, name
        assert lo <= values[name] <= hi, (name, values[name], lo, hi)


def test_derived_only_counts_not_published(variants):
    """CT-208: the S&P variants carry rates and results, never the table's counts per grade."""
    def walk(node, path=""):
        if isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            if len(node) == 17 and all(isinstance(x, int) and not isinstance(x, bool) for x in node):
                yield path
            for i, v in enumerate(node):
                yield from walk(v, f"{path}[{i}]")

    for vid in ("sp-2010", "sp-2011"):
        v = variants[vid]
        assert list(walk(v)) == [], (vid, list(walk(v))[:3])
        for t in v["tests"]:
            if t["segment"] not in (None, "portfolio"):
                assert t["n"] is None and t["n_events"] is None, (vid, t["test_id"], t["segment"])
        assert v["provenance"]["licence_classes"] == {"tasche-2013": "derived-only"}


def test_generator_is_the_engines():
    """CT-311: C05's generator is riskvalidation's DefaultCounts, consuming its stream exactly as the inline generator
    it replaced did (factors first, then the binomial counts), so the bake is unchanged."""
    import inspect

    from scipy.special import ndtr, ndtri

    from pipeline.cases import c05_ldp_calibration as c05

    assert "DefaultCounts" in inspect.getsource(c05._generator)
    g = c05._generator(7)
    rng = np.random.default_rng(7)
    z = rng.standard_normal(c05.N_YEARS)
    cond = ndtr((ndtri(np.array(c05.TRUE_PD))[None, :] - np.sqrt(c05.RHO) * z[:, None]) / np.sqrt(1.0 - c05.RHO))
    assert np.array_equal(g["z"], z) and np.array_equal(g["defaults"], rng.binomial(np.array(c05.LDP_N)[None, :], cond))
