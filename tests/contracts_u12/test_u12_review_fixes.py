"""U12-S, the Opus review of the contracts (wip/contraste/review-u12-s-2026-10-13.md) and the main session's decisions D4 and D5
(plans/contraste/units/U12-sizing.md, "Decisions after U12-S"): one test per finding and per decision.

B1 (F1) es_from_pmf refuses a grid that does not carry the tail; M1 (F2 and D5) the Shevchenko Table 2 indices; M3 (F4 and D5) the
SLA of EUR 647.1 million reproduces; M4 (F5 and D4) the Pareto-Gamma credibility form with the unrestricted prior; M2 (F3) is the
integrator's api bump (a report correction, no test); m1 to m9: the schema constraints (F6), the Monte Carlo reference (F7), the
minimum years (F8), the ILDC note (F9), the LDA capital of the SMA response (F10) and Table 4's forward bound (F11).
"""
from __future__ import annotations

import copy
import functools
import math
import re
from pathlib import Path
from typing import Any

import pytest

import c17_semantic
import contract_schemas as cs

ROOT = cs.ROOT
FIXTURES = ROOT / "docs" / "contracts" / "fixtures" / "c17"
API = ROOT / "docs" / "contracts" / "engine" / "oprisk-api.md"
FINITE = FIXTURES / "variant-tail-index-fixture.json"
INFINITE = FIXTURES / "variant-tail-index-infinite-mean-fixture.json"
MODELS = FIXTURES / "models-fixture.json"
VAR, MOD = "c17/variant-tail-index", "c17/models"
COMMITTED = sorted((ROOT / "data" / "derived" / "C17").glob("*.json")) if (ROOT / "data" / "derived" / "C17").is_dir() else []


def load(path: Path) -> Any:
    return cs.load_json(path)


def sections() -> dict[str, str]:
    parts = re.split(r"^### `([^`]+)`\s*$", API.read_text(encoding="utf-8"), flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts), 2)}


def sec(name: str) -> str:
    return sections()[f"riskvalidation.oprisk.{name}"]


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


@functools.lru_cache(maxsize=None)
def benchmark_cumulative(n_points: int, method: str = "central") -> tuple[float, ...]:
    """Cumulative sums of the Panjer recursion for Poisson(100) with LN(0, 2), step 1 (pure standard library)."""
    cdf = lambda x: 0.0 if x <= 0 else _phi(math.log(x) / 2.0)  # noqa: E731
    if method == "central":
        f = [cdf(0.5)] + [cdf(j + 0.5) - cdf(j - 0.5) for j in range(1, n_points)]
    else:  # forward: the upper bound of Shevchenko eq. 38
        f = [cdf(j + 1) - cdf(j) for j in range(n_points)]
    h = [math.exp(100.0 * (f[0] - 1))]
    for n in range(1, n_points):
        h.append(100.0 / n * sum(j * f[j] * h[n - j] for j in range(1, n + 1)))
    out, run = [], 0.0
    for p in h:
        run += p
        out.append(run)
    return tuple(out)


# --- B1 (F1): es_from_pmf never reads an ES off a grid that does not carry the tail -------------------------------------


def test_b1_es_from_pmf_refuses_a_grid_that_does_not_carry_the_tail() -> None:
    body = sec("aggregate.es_from_pmf")
    assert "max_missing_share" in body and "ValueError" in body
    assert re.search(r"def es_from_pmf\(.*max_missing_share: float = 1e-3", body, flags=re.S)
    assert "tail index of 1 or more" in body and "never computed" in body
    # the scenario of the review: the benchmark on 6000 points has ES 377.8 below its own VaR 5849, with 0.000936 of the mass missing
    cum = benchmark_cumulative(6000)
    missing = 1 - cum[-1]
    assert math.isclose(missing, 0.000936, abs_tol=5e-7)
    assert missing > 1e-3 * (1 - 0.999), "the guard of the contract refuses this grid"
    n_q = next(i for i, c in enumerate(cum) if c >= 0.999)
    h = [cum[0]] + [b - a for a, b in zip(cum, cum[1:])]
    naive = (sum(i * h[i] for i in range(n_q + 1, 6000)) + n_q * (cum[n_q] - 0.999)) / (1 - 0.999)
    assert n_q == 5849 and math.isclose(naive, 377.8, abs_tol=0.05) and naive < n_q
    for needle in ("377.8", "0.000936", "5849"):
        assert needle in body, needle


def test_b1_a_tail_index_of_one_or_more_has_no_finite_es_in_the_contract() -> None:
    text = API.read_text(encoding="utf-8")
    assert "expected shortfall does not exist" in text.lower() or "expected shortfall is infinite" in text.lower()
    assert "ES" in sec("aggregate.es_from_pmf") and "1.1" in sec("aggregate.es_from_pmf")


# --- M1 (F2, D5): Shevchenko Table 2 indices ------------------------------------------------------------------------------


def test_m1_the_benchmark_indices_are_those_of_shevchenko_table_2() -> None:
    cum = benchmark_cumulative(5850)
    assert math.isclose(cum[5847], 0.998999329, abs_tol=5e-10)
    assert math.isclose(cum[5848], 0.998999773, abs_tol=5e-10)
    assert math.isclose(cum[5849], 0.999000217, abs_tol=5e-10)
    assert cum[5848] < 0.999 <= cum[5849]
    text = API.read_text(encoding="utf-8")
    assert "offset" not in text.lower()
    for needle in ("H_5847", "0.998999329", "0.998999773", "0.999000217", "Table 2", "Table 3", "arXiv 1008.1108", "verified"):
        assert needle in text, needle
    assert "`H_5849 = 0.998999329`" not in text and "H_5849 = 0.998999329" not in text.replace("(Table 2 label", "")


def test_m1_table_4_forward_bound_follows_the_table_rows() -> None:
    cum = benchmark_cumulative(5813, "forward")
    assert math.isclose(cum[5811], 0.998999719, abs_tol=5e-10) and math.isclose(cum[5812], 0.999000163, abs_tol=5e-10)
    assert cum[5811] < 0.999 <= cum[5812]
    text = API.read_text(encoding="utf-8")
    assert "5812" in text and "0.998999719" in text and "0.999000163" in text


# --- M3 (F4, D5): the SLA of EUR 647.1 million is the dossier's; the engine goldens do not call it unverified -----------------------


def test_m3_the_sla_section_states_the_reproduction() -> None:
    body = sec("sla.sla_var_poisson_gpd")
    for needle in ("647.1 million", "0.96378", "22349.4", "624.1 million"):
        assert needle in body, needle
    assert "UNVERIFIED" not in body.split("Golden:", 1)[1].split("### ")[0].replace("mean-corrected", ""), \
        "the 647 million figure is reproduced and no longer UNVERIFIED"


# --- M4 (F5, D4): the Pareto-Gamma credibility form, unrestricted prior ----------------------------------------------------


def test_m4_the_credibility_functions_follow_shevchenko_and_wuthrich_with_the_unrestricted_prior() -> None:
    names = [k for k in sections() if k.startswith("riskvalidation.oprisk.scenarios.")]
    assert [k.rsplit(".", 1)[1] for k in names] == [
        "ScenarioPoint", "scenario_pseudo_observations", "fit_tail_to_scenarios", "GammaPrior", "gamma_prior_from_mean_interval",
        "gamma_prior_from_scenarios", "CredibilityFit", "credibility_pareto", "scenario_influence"]
    text = API.read_text(encoding="utf-8")
    for gone in ("kappa", "credibility_gpd", "Decision D1"):
        assert gone not in text, gone
    body = sec("scenarios.credibility_pareto") + sec("scenarios.CredibilityFit") + sec("scenarios.GammaPrior")
    for needle in ("unrestricted", "Gamma", "eq. 24", "eq. 25", "Shevchenko and Wuthrich", "Pareto shape", "alpha = 1 / xi",
                   "tail index 1.1", "0.909"):
        assert needle in body, needle
    mapping = sec("scenarios.gamma_prior_from_scenarios")
    for needle in ("least squares on the log", "alpha_s", "90 percent", "parametric bootstrap", "Poisson", "seed"):
        assert needle in mapping, needle
    assert "log excess quantiles" in sec("scenarios.fit_tail_to_scenarios")


def test_m4_the_golden_values_of_the_credibility_form_recompute() -> None:
    # Gamma(1, 1) is the exponential: mean 1 and mass 0.9 between its 5th and 95th percentiles
    lo, hi = -math.log(0.95), -math.log(0.05)
    assert math.isclose(math.exp(-lo) - math.exp(-hi), 0.9, abs_tol=1e-12)
    # posterior of a Gamma(shape 2, rate 1) prior after n = 3 excesses with sum ln(x / L) = 3: Gamma(5, 4)
    a, b, n, s = 2.0, 1.0, 3, 3.0
    shape, rate = a + n, b + s
    w = s / (s + b)
    assert (shape, rate, w) == (5.0, 4.0, 0.75)
    assert math.isclose(shape / rate, w * (n / s) + (1 - w) * (a / b), abs_tol=1e-12)
    assert math.isclose(shape / rate, 1.25, abs_tol=1e-12) and math.isclose(math.sqrt(shape) / rate, 0.559017, abs_tol=5e-7)
    xi = 1 / (shape / rate)
    assert math.isclose(xi, 0.8, abs_tol=1e-12) and math.isclose(xi * 1.0, 0.8, abs_tol=1e-12)
    text = sec("scenarios.credibility_pareto") + sec("scenarios.gamma_prior_from_mean_interval")
    for needle in ("0.559017", "1.25", "0.75", "Gamma(5, 4)"):
        assert needle in text, needle


@pytest.mark.parametrize("path", [FINITE, INFINITE], ids=["finite", "infinite"])
def test_m4_the_documents_state_the_prior_on_every_result(path: Path) -> None:
    doc = load(path)
    assert doc["outputs"]["scenario_influence"]["prior_kind"] == "unrestricted-gamma-on-pareto-shape"
    bad = copy.deepcopy(doc)
    bad["outputs"]["scenario_influence"]["prior_kind"] = "restricted-gamma"
    assert cs.errors(VAR, bad) != []
    bad = copy.deepcopy(doc)
    del bad["outputs"]["scenario_influence"]["prior_kind"]
    assert cs.errors(VAR, bad) != []


def test_m4_the_models_document_carries_the_prior_specification() -> None:
    doc = load(MODELS)
    prior = doc["fit"]["scenarios"]["prior"]
    assert prior["kind"] == "unrestricted-gamma-on-pareto-shape" and prior["restricted"] is False and prior["interval_level"] == 0.9
    for key, value in (("kind", "restricted-gamma"), ("restricted", True), ("interval_level", 0.95)):
        bad = copy.deepcopy(doc)
        bad["fit"]["scenarios"]["prior"][key] = value
        assert cs.errors(MOD, bad) != [], key


# --- m1 to m5 (F6): constraints JSON Schema can state ------------------------------------------------------------------------


def _plant(path: Path, ref: str, edit) -> list[str]:
    doc = load(path)
    edit(doc)
    return cs.errors(ref, doc)


def test_m_the_cells_are_exactly_the_cross_of_years_and_thresholds() -> None:
    def four_same(d: dict) -> None:
        d["outputs"]["cells"] = [copy.deepcopy(d["outputs"]["cells"][0]) for _ in range(4)]

    assert _plant(FINITE, VAR, four_same) != []

    def swapped_years(d: dict) -> None:
        d["outputs"]["cells"][1]["years"] = 10  # (10, 20000) twice and no (5, 20000)

    assert _plant(FINITE, VAR, swapped_years) != []


@pytest.mark.parametrize("years", [0, 4, 7, 11])
def test_m_a_cell_of_any_other_length_than_5_or_10_years_is_refused(years: int) -> None:
    assert _plant(FINITE, VAR, lambda d: d["outputs"]["cells"][0].__setitem__("years", years)) != []


def test_m_the_tail_index_is_one_of_the_four_of_the_sdd() -> None:
    for where in ("outputs", "truth", "calibration"):
        def edit(d: dict, where: str = where) -> None:
            if where == "outputs":
                d["outputs"]["tail_index"] = 0.5
            elif where == "truth":
                d["outputs"]["truth"]["severity"]["tail_index"] = 0.5
            else:
                d["outputs"]["calibration"]["fit"]["tail_index"] = 0.5

        assert _plant(FINITE, VAR, edit) != [], where

    def all_at_06(d: dict) -> None:
        for v in d["fit"]["variants"]:
            v["tail_index"] = 0.6
            v["infinite_mean"] = False
            v["true_mean_eur"] = 1.0e7
            v["true_mean_reason"] = None

    assert _plant(MODELS, MOD, all_at_06) != [], "four variants at the same tail index validate"

    assert c17_semantic.semantic_findings({**load(MODELS), "fit": {**load(MODELS)["fit"], "variants": list(reversed(load(MODELS)["fit"]["variants"]))}}) != [], "variants out of order"


def test_m_a_discretion_that_sets_the_ilm_to_one_carries_an_ilm_of_one() -> None:
    def national_with_other_ilm(d: dict) -> None:
        d["outputs"]["cells"][0]["sma"]["discretion_applied"] = "national-ilm-one"

    assert _plant(FINITE, VAR, national_with_other_ilm) != [], "national discretion with an ILM other than 1 validates"

    def national_with_ilm_one(d: dict) -> None:
        sma = d["outputs"]["cells"][0]["sma"]
        sma["discretion_applied"] = "national-ilm-one"
        sma["ilm"] = {k: 1.0 for k in sma["ilm"]}

    assert _plant(FINITE, VAR, national_with_ilm_one) == []


def test_m_a_truth_that_fails_its_own_monte_carlo_check_is_not_published() -> None:
    assert _plant(FINITE, VAR, lambda d: d["outputs"]["truth"]["annual_loss_quantile"]["mc_check"].__setitem__("agrees", False)) != []


# --- m6 to m9 (F6, semantic layer): the cross-field rules, over the fixtures and every committed C17 document ------------------


@pytest.mark.parametrize("path", [FINITE, INFINITE, MODELS] + COMMITTED, ids=lambda p: p.name)
def test_semantic_findings_are_empty_for_every_fixture_and_committed_c17_document(path: Path) -> None:
    assert c17_semantic.semantic_findings(load(path)) == []


def _semantic(edit, path: Path = FINITE) -> list[str]:
    doc = load(path)
    edit(doc)
    return c17_semantic.semantic_findings(doc)


def test_semantic_truth_tail_index_differs_from_the_variants() -> None:
    assert _semantic(lambda d: d["outputs"]["truth"]["severity"].__setitem__("tail_index", 1.1)) != []
    assert _semantic(lambda d: d["outputs"]["calibration"]["fit"].__setitem__("tail_index", 0.6)) != []


def test_semantic_percentiles_are_ordered() -> None:
    def disorder(d: dict) -> None:
        cap = d["outputs"]["cells"][0]["capital"]["lda_splice"]["capital_eur"]
        cap["p05"], cap["p95"] = cap["p95"], cap["p05"]

    assert _semantic(disorder) != []


def test_semantic_exceedance_curves_have_the_grid_length_and_do_not_increase() -> None:
    assert _semantic(lambda d: d["outputs"]["exceedance"]["panjer"]["exceedance"].pop()) != []

    def rising(d: dict) -> None:
        e = d["outputs"]["exceedance"]["fft"]["exceedance"]
        e[-1] = min(1.0, e[-2] + 0.01) if e[-2] < 1 else e[-1]
        e[3] = e[2] + 0.0001 if e[2] < 1 else e[3] + 0.5

    assert _semantic(rising) != []


def test_semantic_ratio_to_truth_is_capital_over_the_true_quantile() -> None:
    assert _semantic(lambda d: d["outputs"]["cells"][1]["capital"]["lda_splice"]["ratio_to_truth"].__setitem__("median", 9.7)) != []


def test_semantic_sma_response_and_scenario_influence_name_a_cell() -> None:
    assert _semantic(lambda d: d["outputs"]["sma_response"].__setitem__("cell_id", "y4-h10000")) != []
    assert _semantic(lambda d: d["outputs"]["scenario_influence"].__setitem__("cell_id", "nowhere")) != []


def test_semantic_the_truth_floor_is_at_or_below_every_collection_threshold() -> None:
    def high_floor(d: dict) -> None:
        d["outputs"]["truth"]["severity"]["location_eur"] = 20000.0
        d["outputs"]["truth"]["frequency"]["counted_above_eur"] = 20000.0

    assert _semantic(high_floor) != []


def test_semantic_the_cell_ids_the_seed_ranges_and_the_bank_identities() -> None:
    assert _semantic(lambda d: d["outputs"]["cells"][0].__setitem__("id", "y10-h10000")) != []

    def overlap(d: dict) -> None:
        d["outputs"]["cells"][1]["replications"]["seed_first"] = d["outputs"]["cells"][0]["replications"]["seed_first"] + 5

    assert _semantic(overlap) != []
    assert _semantic(lambda d: d["outputs"]["bank"]["business_indicator"].__setitem__("bi_eur", 9.9e8)) != []
    assert _semantic(lambda d: d["outputs"]["bank"].__setitem__("bic_eur", 1.0e8)) != []
    assert _semantic(lambda d: d["outputs"]["cells"][2]["sma"]["ilm"].__setitem__("median", 5.0)) != []


def test_semantic_the_models_variants_match_the_truth_rules() -> None:
    def not_increasing(d: dict) -> None:
        d["fit"]["variants"][0]["true_quantile_999_eur"] = 5.0e10

    assert _semantic(not_increasing, MODELS) != [], "the true quantile must increase with the tail index"


def test_semantic_layer_is_named_in_the_rows_fragment_as_the_gate_of_the_bake() -> None:
    catalog = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")   # the U12 rows, merged at 0.11.000
    rows = "\n".join(ln for ln in catalog.splitlines() if ln.startswith(("| c17-", "| engine-oprisk-api")))
    assert "semantic_findings" in rows


# --- m10 to m13 (F7 to F10) ---------------------------------------------------------------------------------------------------


def test_m_the_monte_carlo_reference_is_the_continuous_quantile_5853_1() -> None:
    body = sections()["riskvalidation.validation.oprisk.benchmark_reproduction"]
    for needle in ("5853.1", "0.801285", "0.008013", "Table 3", "Table 7"):
        assert needle in body, needle
    assert "5849.5" not in body.split("Golden:", 1)[1], "the mid-point 5849.5 no longer references the Monte Carlo quantile"


def test_m_sma_capital_refuses_a_minimum_below_five_years() -> None:
    body = sec("sma.sma_capital")
    assert re.search(r"ValueError[^.]*minimum_years", body) and "OPE25.15" in body


def test_m_the_ildc_note_is_2_667() -> None:
    body = sec("sma.ildc")
    assert "2.667" in body and "4.667" not in body
    assert math.isclose(abs((10 + 2 + 10) / 3 - (2 + 10 + 2) / 3), 2.667, abs_tol=5e-4)


@pytest.mark.parametrize("path", [FINITE, INFINITE], ids=["finite", "infinite"])
def test_m_the_sma_response_carries_the_lda_capital_of_the_same_history(path: Path) -> None:
    rows = load(path)["outputs"]["sma_response"]["rows"]
    lda = [r["lda_capital_eur"] for r in rows]
    assert all(x > 0 for x in lda) and lda == sorted(lda)
    bad = copy.deepcopy(load(path))
    del bad["outputs"]["sma_response"]["rows"][0]["lda_capital_eur"]
    assert cs.errors(VAR, bad) != []
