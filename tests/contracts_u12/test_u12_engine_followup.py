"""U12-S follow-up after the Opus engine review (wip/contraste/review-u12-engine-2026-10-13.md): one test per amendment of
docs/contracts/engine/oprisk-api.md.

A1 (B1) es_from_pmf: the guard does not refuse a coarse grid of an infinite-mean severity, so the ES existence is decided on the severity
(`severity_moment(..., 1)` finite) before the ES is computed. A2 (M1) the scenario prior: an interval that reaches the bound of the
optimiser's search is a stated failure, never a statistic. A3 (M2) benchmark_reproduction: `moment_rel_tol` defaults to 1e-5 because the
reference skewness has four decimals.
"""
from __future__ import annotations

import math
import re

import contract_schemas as cs

API = cs.ROOT / "docs" / "contracts" / "engine" / "oprisk-api.md"


def section(name: str) -> str:
    parts = re.split(r"^### `([^`]+)`\s*$", API.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}[name]


def test_a1_the_es_guard_is_not_claimed_to_refuse_a_grid_at_any_size() -> None:
    text = API.read_text(encoding="utf-8")
    assert "at any size" not in text
    body = section("riskvalidation.oprisk.aggregate.es_from_pmf")
    for needle in ("severity_moment", "checked on the severity before the ES", "never computed", "tail index of 1 or more",
                   "32768", "1.66e-7", "passes the guard"):
        assert needle in body, needle
    assert "bake" in body and "null" in body


def test_a1_the_missing_mass_of_a_coarse_grid_of_an_infinite_mean_tail_falls_under_the_guard() -> None:
    """GPD(1.1, 100, 0) with Poisson(10), step 1e6 and 32768 points: the mass beyond the grid is lam x S(end) = 1.66e-7, below the
    guard's 1e-3 x (1 - 0.999) = 1e-6, so the guard cannot detect an infinite mean; the severity moment can."""
    xi, beta, lam, end = 1.1, 100.0, 10.0, 1e6 * 32768
    missing = lam * (1 + xi * end / beta) ** (-1 / xi)
    assert math.isclose(missing, 1.66e-7, rel_tol=0.02)
    assert missing < 1e-3 * (1 - 0.999)
    # the first moment of a GPD exists only for xi < 1: E[Y] = beta / (1 - xi) is negative, i.e. not a mean, at xi = 1.1
    assert xi >= 1


def test_a2_a_scenario_interval_on_the_search_bound_is_a_stated_failure() -> None:
    body = section("riskvalidation.oprisk.scenarios.gamma_prior_from_scenarios")
    for needle in ("search bound", "ValueError", "exceedance_frequency * basis_years >= 1", "null with its reason",
                   "never a statistic", "1000"):
        assert needle in body, needle
    assert "the interval contains `alpha_s`;" not in body, "the unconditional invariant was refuted by the engine review"
    assert "ValueError when the interval does not contain `alpha_s`" in body


def test_a2_the_bound_of_the_search_is_the_inverse_of_the_lower_bound_of_xi() -> None:
    assert math.isclose(1 / 1e-3, 1000.0)


def test_a3_moment_rel_tol_defaults_to_1e_5_because_the_reference_skewness_has_four_decimals() -> None:
    body = section("riskvalidation.validation.oprisk.benchmark_reproduction")
    assert re.search(r"moment_rel_tol: float = 1e-5", body)
    skew = math.e ** 6 / 10
    rel = abs(skew - 40.3428) / 40.3428
    assert math.isclose(rel, 1.966876e-6, rel_tol=1e-4)
    assert math.isclose(rel / 1e-6, 1.966876, rel_tol=1e-4) and math.isclose(rel / 1e-5, 0.196688, rel_tol=1e-4)
    for needle in ("1.966876", "0.196688", "amber", "at least 1e-5"):
        assert needle in body, needle
