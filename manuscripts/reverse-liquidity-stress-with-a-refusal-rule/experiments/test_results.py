"""Tests of the stored results of the experiments: each reproduction value is the one committed in ``data/derived/C16``, every result file
is complete, and the numbers the manuscript quotes are in the files.

    python -m pytest manuscripts/reverse-liquidity-stress-with-a-refusal-rule/experiments/test_results.py
"""
from __future__ import annotations

import json
import pathlib

import pytest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(name: str) -> dict:
    p = HERE / name
    assert p.exists(), f"{name} is missing: run its script"
    return json.loads(p.read_text(encoding="utf-8"))


def committed() -> dict:
    d = json.loads((ROOT / "data" / "derived" / "C16" / "reverse-stress.json").read_text(encoding="utf-8"))
    return {b["base_id"]: b for b in d["outputs"]["bases"]}


def test_the_hypotheses_file_precedes_the_results() -> None:
    h = HERE / "hypotheses.json"
    assert h.exists()
    for name in ("results_corpus.json", "results_reverse_c16.json", "results_theory.json"):
        assert (HERE / name).stat().st_mtime >= h.stat().st_mtime, f"{name} is older than the predictions"


def test_the_c16_reproduction_values_are_the_committed_ones() -> None:
    r = load("results_reverse_c16.json")
    com = committed()
    assert r["R"] == {"R1": True, "R2": True, "R3": True, "R4": True, "R5": True}
    assert r["bases"]["list-adverse"]["engine"]["multiplier"] == pytest.approx(com["list-adverse"]["solved"]["multiplier"], abs=1e-12)
    assert r["bases"]["list-extreme"]["engine"]["multiplier"] == pytest.approx(com["list-extreme"]["solved"]["multiplier"], abs=1e-12)
    assert r["bases"]["fast-run"]["engine"]["status"] == "refused"
    assert all(r["bases"][b]["curve_equals_committed"] for b in r["bases"])


def test_the_labelled_run_rows_equal_the_committed_scoring() -> None:
    r = load("results_reverse_c16.json")["labelled_run"]
    assert all(x["equals_committed"] for x in r["rows"])
    assert r["multiplier_of_labelled_run"] > 1.0
    assert r["share_2d_at_that_multiplier"] == pytest.approx(0.85, abs=1e-9)


def test_the_corpus_result_is_complete_and_covers_every_refusal() -> None:
    r = load("results_corpus.json")
    d = r["design"]
    assert d["instances"] == len(d["seeds"]) * d["banks_per_seed"] * len(d["targets"])
    assert d["solved"] > 0 and d["refused_horizon"] > 0 and d["refused_base"] > 0 and d["refused_unreachable"] > 0
    assert d["solved"] + d["refused_horizon"] + d["refused_base"] + d["refused_unreachable"] == d["instances"]
    for m in ("proposed", "grid_case", "grid_fine", "brent_sp", "bisect_no_refusal", "uncapped", "nearest", "raw_capacity"):
        assert m in r["methods"]
        assert r["methods"][m]["time_us_median"] > 0
    for h in ("H1", "H2", "H3", "H4", "H5", "H6"):
        assert h in r


def test_the_theory_result_holds_its_checks() -> None:
    r = load("results_theory.json")
    assert r["monotone_in_multiplier"]["violations"] == 0
    assert r["closed_form_single_segment"]["max_abs_difference"] < 2e-6
    assert r["monotone_in_target"]["violations"] == 0
    assert r["monotone_in_capacity"]["violations"] == 0
