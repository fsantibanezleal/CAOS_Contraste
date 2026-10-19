"""Writes docs/contracts/engine/ml-api.md and fairness-api.md from api_spec.py (run: ``python tests/contracts_u14/build_docs.py``)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import api_spec as sp  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "contracts" / "engine"
ARR = sp.ARR

ML_TEST_ARGS = {
    "robustness": f"model_id: str, curve: RobustnessCurve, tolerance: float, preset_eps: float, policy: MlPolicy = DEFAULT_POLICY",
    "shift_resilience": "model_id: str, result: SubsampleResult, policy: MlPolicy = DEFAULT_POLICY",
    "seed_stability": "model_id: str, dispersion: SeedDispersion, policy: MlPolicy = DEFAULT_POLICY",
    "reason_code_stability": "model_id: str, overlap: OverlapResult, policy: MlPolicy = DEFAULT_POLICY",
    "effect_agreement": "model_id: str, rho: float, n_features: int, policy: MlPolicy = DEFAULT_POLICY",
    "additivity": "model_id: str, gap: float, tolerance: float = 1e-9",
    "overfit": "model_id: str, result: OverfitResult",
    "weak_spot": "model_id: str, spots: Sequence[WeakSpot], k: float, n_slices: int",
    "conformal_coverage": "model_id: str, result: CoverageResult, policy: MlPolicy = DEFAULT_POLICY",
    "leakage_screen": "model_id: str, temporal: int, single: SingleFeatureAuc, overlap: float, resemblance: AucResult, policy: MlPolicy = DEFAULT_POLICY",
    "data_quality": "model_id: str, counts: Sequence[DataQualityCount], policy: MlPolicy = DEFAULT_POLICY",
    "cbpe_estimate": "model_id: str, estimate: CbpeAuc, labels_supplied: bool = False",
    "challenger_brier": "model_id: str, result: PairedBrier",
}
FAIR_TEST_ARGS = {
    "demographic_parity": "model_id: str, rates: Mapping[str, SelectionRate], reference: str, policy: FairPolicy = DEFAULT_POLICY",
    "adverse_impact": "model_id: str, rates: Mapping[str, SelectionRate], reference: str",
    "two_proportion_z": "model_id: str, x1: int, n1: int, x2: int, n2: int, policy: FairPolicy = DEFAULT_POLICY",
    "fisher_exact": "model_id: str, x1: int, n1: int, x2: int, n2: int, policy: FairPolicy = DEFAULT_POLICY",
    "equalized_odds": f"model_id: str, y: {ARR} | None, decision: {ARR}, group: {ARR}, policy: FairPolicy = DEFAULT_POLICY",
    "equal_opportunity": f"model_id: str, y: {ARR} | None, decision: {ARR}, group: {ARR}, policy: FairPolicy = DEFAULT_POLICY",
    "calibration_within_groups": f"model_id: str, p: {ARR}, y: {ARR} | None, group: {ARR}, policy: FairPolicy = DEFAULT_POLICY",
    "auc_by_group": f"model_id: str, score: {ARR}, y: {ARR} | None, group: {ARR}, policy: FairPolicy = DEFAULT_POLICY",
    "conditional_disparity": "model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]",
    "rate_spread_disparity": "model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]",
    "replication": "model_id: str, replication: Replication",
    "situation_testing": "model_id: str, result: SituationResult, policy: FairPolicy = DEFAULT_POLICY",
}


def section(fq: str, sig: str, units: str, inv: str, check: str, extra: list[str] | None = None) -> str:
    lines = [f"### `{fq}`", "", "```python", sig, "```", "", f"- Units: {units}", f"- Invariants: {inv}"]
    lines += extra or []
    lines += [f"- Check: {check}", ""]
    return "\n".join(lines)


def test_section(prefix: str, name: str, args: str, test_id: str, light: str, family: str) -> str:
    sig = f"def {name}({args}) -> TestResult"
    kind = "ml" if family == "ml" else "fair"
    extra = [f'- Test id: test_id = "{test_id}"', f"- Light: {light}"]
    return section(f"{prefix}.{name}", sig,
                   "A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.",
                   f"Pure and deterministic; ids are prefixed `{kind}.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.",
                   "The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).", extra)


def build(title: str, cid: str, intro: str, modules: dict, tests: list, test_args: dict, prefix_pkg: str, test_mod: str,
          test_prefix: str, family: str, unverified: list[str]) -> str:
    out = [f"# {title}: `{cid}` 1.0.0", "", intro, "",
           "## Conventions (all functions)", "",
           "- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `n` rows, `p` features, `q` protected indicators.",
           "- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); randomness takes a `seed` and uses `numpy.random.default_rng(seed)`. Dataclasses are frozen. The engine imports no learning library: a model enters as a callable on arrays, and the pipeline computes attributions with the pinned `shap`.",
           "- A function that cannot compute because data is missing raises `ValueError` with the reason, or (a validation function) returns the `not_evaluated` light with its reason in `notes`; it never returns a placeholder number.",
           f"- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`). Test ids are prefixed `{test_prefix}`.",
           "- Tolerances, grids, counts and cut-offs are conventions, never regulatory thresholds (06 I.6 l.1268-1270); the named parameters of the case documents are listed in the case schemas.",
           "- No golden value is claimed where the dossiers print none: each check is an identity, an independent reference or a size and power run on a planted defect.", ""]
    for key, (path, pkg, funcs) in modules.items():
        out += [f"## Module `{path}`", ""]
        for name, sig, units, inv, check in funcs:
            out.append(section(f"{pkg}.{name}", sig, units, inv, check))
    out += [f"## Module `riskvalidation/validation/{test_mod}.py`", ""]
    for name, tid, light in tests:
        out.append(test_section(prefix_pkg, name, test_args[name], tid, light, family))
    out += ["## UNVERIFIED and open items", ""] + [f"- {u}" for u in unverified] + [""]
    return "\n".join(out)


ML_INTRO = ("Owner: U14-S (unit sizing `plans/contraste/units/U14-sizing.md`, CAOS_MANAGE). Implemented by U14-E1 in `riskvalidation.ml` and "
            "`riskvalidation.validation.ml` (repository CAOS_RiskValidation); called by the C02 and C20 bakes (U14-P1, U14-P2). The tests of every "
            "function are written by U14-E1 against this file: a function exists with exactly the signature below, and each identity, independent "
            "reference or planted-defect check is a test. Changing a signature or a unit is a breaking change (a new major version of this contract). "
            "Sources: dossier 06 (`wip/contraste/06-model-risk-management-and-validation-2026-10-04.md`, C.7 l.979-1058, I.1 l.1184-1200, I.6), dossier 04 "
            "(J.2 l.881-883, ladder P4 l.968), dossier 07 (D patterns 3 and 6) and the product SDD Method ladder. The case documents this contract feeds are "
            "`c02-outputs`, `c02-models`, `c20-outputs`, `c20-outputs-shift`, `c20-outputs-seeds`, `c20-outputs-perturbation`, `c20-outputs-leakage` and "
            "`c20-models` (`docs/contracts/schemas/c02/`, `c20/`). The engine computes; it states no compliance claim. The drift tests are the existing "
            "`validation/stability.py` (PSI, CSI, chi-square, KS, Wasserstein), reused unchanged.")
FAIR_INTRO = ("Owner: U14-S (unit sizing `plans/contraste/units/U14-sizing.md`, CAOS_MANAGE). Implemented by U14-E2 in `riskvalidation.fairness` and "
              "`riskvalidation.validation.fairness`; called by the C20 and C21 bakes (U14-P2, U14-P3). The tests are written by U14-E2 against this file. "
              "Sources: dossier 06 C.7 l.1029-1040, I.6 l.1268-1270; dossier 04 J.3 l.897-905; dossier 07 A.3 l.158-177; the U14 research addendum "
              "(`wip/contraste/u14-research-addendum-2026-10-17.md`: H1 field names, H3 legal tests, H5 the situation-testing algorithm). The case documents "
              "are `c21-outputs`, `c21-models` (`docs/contracts/schemas/c21/`) and the Taiwan battery rows of the C20 documents. The four-fifths line is an "
              "employment benchmark and never a credit-law threshold. HMDA has no outcome (08 l.180-181): the outcome-conditioned tests (equalized odds, equal "
              "opportunity, calibration within groups, AUC by group) never run on it. The engine states no legal claim.")


def main() -> None:
    ml = build("Engine ML validation API contract", "engine-ml-api", ML_INTRO, sp.ML_MODULES, sp.ML_TESTS, ML_TEST_ARGS,
               "riskvalidation.validation.ml", "ml", "ml.", "ml",
               ["The values of the named parameters (grid, tolerance, seeds, refits, overfit tolerance, weak-spot multiple, shift score, worst share, cut-off) are proposed by U14-S and approved by the main session; the engine takes them as arguments.",
                "The dossiers print no worked example with numbers for these tests: no golden value is claimed (sizing, Modules and functions).",
                "MAPIE and fairlearn are optional reconciliation extras (decision Q11), never imported by the engine core."])
    fair = build("Engine fairness API contract", "engine-fairness-api", FAIR_INTRO, sp.FAIR_MODULES, sp.FAIR_TESTS, FAIR_TEST_ARGS,
                 "riskvalidation.validation.fairness", "fairness", "fair.", "fair",
                 ["The approval and denial classification of HMDA `action_taken` is not settled by any source read (addendum UNVERIFIED); the C21 convention is approval = 1 and 2, denial = 3 and is labelled a convention.",
                  "Ethnicity maps to national origin only by convention (addendum H3, UNVERIFIED).",
                  "The reference situation-testing code differs from the paper in the distance normalisation and has a broken counterfactual-with-centers path: tests use the paper's equations and the golden values of the addendum 7.6.",
                  "A counterfactual generator for HMDA is not supplied by the algorithm: C21 runs the ceteris paribus comparator only."])
    (OUT / "ml-api.md").write_text(ml, encoding="utf-8", newline="\n")
    (OUT / "fairness-api.md").write_text(fair, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
