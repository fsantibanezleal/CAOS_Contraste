"""The quantile grids of the C18 models document (c18-models 3.0.0, review MA5 of the U17 sample): the contract test of the produced boundary.

The committed models document carries, for each of the four marginals, its quantile function at a named probability grid, so a notebook
rebuilds the marginals the band was run on from the repository alone. The tests hold the grid to its convention, to the marginal's own
VaR and EL, and to the schema (a defect planted in a copy is refused); the one that needs the bake runs where the raw files are.
"""
from __future__ import annotations

import copy
import json
from statistics import NormalDist

import numpy as np
import pytest
from c18_support import C18, requires_raw

from pipeline.cases.c18 import marginals as mg
from pipeline.cases.c18 import params as P
from pipeline.core.schemas import validate_document

REL = "data/derived/C18/models-banco-andino.json"
RISKS = ["credit", "market", "irrbb", "operational"]


def committed() -> dict:
    return json.loads((C18 / "models-banco-andino.json").read_text(encoding="utf-8"))


def grid_of(doc: dict) -> dict:
    return doc["fit"]["aggregation"]["quantile_grid"]


def test_the_committed_models_document_validates_and_carries_the_grid() -> None:
    doc = committed()
    validate_document(REL, doc)
    g = grid_of(doc)
    conv = g["convention"]
    assert conv["name"] == "standard-normal-z-grid" and (conv["z_min"], conv["z_max"], conv["z_step"], conv["points"]) == (-4.9, 4.9, 0.005, 1961)
    assert conv["unit"] == "CLP millions" and conv["statement"]["en"] and conv["statement"]["es"]
    assert len(g["probabilities"]) == 1961 and [m["risk"] for m in g["marginals"]] == RISKS


def test_the_probabilities_are_the_named_convention() -> None:
    g = grid_of(committed())
    nd = NormalDist()
    z = np.arange(-980, 981) * 0.005
    expected = np.array([nd.cdf(float(x)) for x in z])
    assert np.allclose(g["probabilities"], expected, rtol=0, atol=1e-12)
    assert np.all(np.diff(g["probabilities"]) > 0) and 0 < g["probabilities"][0] < 1e-5 and 1 - 1e-5 < g["probabilities"][-1] < 1
    assert np.allclose(g["probabilities"], mg.quantile_probabilities(), rtol=0, atol=1e-15)
    assert (P.GRID_Z_MAX, P.GRID_Z_STEP, P.GRID_POINTS) == (4.9, 0.005, 1961)


def test_each_quantile_function_is_non_decreasing_and_agrees_with_the_marginals_var_and_el() -> None:
    doc = committed()
    g = grid_of(doc)
    probs = np.array(g["probabilities"])
    agg = json.loads((C18 / "baseline.json").read_text(encoding="utf-8"))["outputs"]["aggregation"]
    for q, m in zip(g["marginals"], agg["marginals"], strict=True):
        x = np.array(q["quantiles"])
        assert q["risk"] == m["risk"] and x.size == 1961 and np.all(np.diff(x) >= 0), q["risk"]
        # the quantile at the 99.9 percent level, between the two grid points around it, is the marginal's VaR to 1 percent
        assert float(np.interp(0.999, probs, x)) == pytest.approx(m["var_clp_m"], rel=1e-2), q["risk"]
        # the mean of the loss under the quantile function is the marginal's expected loss (to the discretisation of the tails the grid cuts at 5e-7)
        mean = float(np.trapezoid(x, probs) + probs[0] * x[0] + (1 - probs[-1]) * x[-1])
        if m["el_clp_m"]:
            assert mean == pytest.approx(m["el_clp_m"], rel=0.03), q["risk"]


def test_a_document_without_the_grid_is_refused_and_each_planted_defect_is_refused() -> None:
    doc = committed()
    without = copy.deepcopy(doc)
    del without["fit"]["aggregation"]["quantile_grid"]
    with pytest.raises(Exception):                    # required since c18-models 3.0.0 (every object closed, nothing optional)
        validate_document(REL, without)
    defects = {
        "a point fewer": lambda g: g["probabilities"].pop(),
        "a quantile list too short": lambda g: g["marginals"][0]["quantiles"].pop(),
        "a marginal missing": lambda g: g["marginals"].pop(),
        "a probability outside (0, 1)": lambda g: g["probabilities"].__setitem__(0, 0.0),
        "another convention": lambda g: g["convention"].__setitem__("z_step", 0.01),
        "a risk that is not a marginal": lambda g: g["marginals"][0].__setitem__("risk", "liquidity"),
    }
    for label, plant in defects.items():
        bad = copy.deepcopy(doc)
        plant(grid_of(bad))
        with pytest.raises(Exception):
            validate_document(REL, bad)
        assert label


@requires_raw
def test_the_grid_is_each_marginals_quantile_function_at_the_grid_probabilities(built) -> None:
    core = built.results["core"]
    g = built.models["fit"]["aggregation"]["quantile_grid"]
    probs = np.array(g["probabilities"])
    for m, q in zip(core.marginals, g["marginals"], strict=True):
        assert q["risk"] == m.risk
        assert np.array_equal(np.array(q["quantiles"]), np.asarray(m.ppf(probs), dtype=float)), m.risk
        # interpolating the grid back at the draws' own positions stays within a small share of the quantile function it was cut from
        u = (np.arange(1, 2001) - 0.5) / 2000
        back, ref = np.interp(u, probs, q["quantiles"]), np.asarray(m.ppf(u), dtype=float)
        assert np.max(np.abs(back - ref)) <= 0.01 * max(abs(ref).max(), 1.0), m.risk
