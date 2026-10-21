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
    "robustness": "model_id: str, curve: RobustnessCurve, tolerance: float, preset_eps: float, policy: Policy | None = None",
    "shift_resilience": "model_id: str, result: SubsampleResult, policy: Policy | None = None",
    "seed_stability": "model_id: str, dispersion: SeedDispersion, policy: Policy | None = None",
    "reason_code_stability": "model_id: str, overlap: OverlapResult, policy: Policy | None = None",
    "effect_agreement": "model_id: str, rho: float, n_features: int, policy: Policy | None = None",
    "additivity": "model_id: str, gap: float, tolerance: float = 1e-9, policy: Policy | None = None",
    "overfit": "model_id: str, result: OverfitResult, policy: Policy | None = None",
    "weak_spot": "model_id: str, spots: Sequence[WeakSpot], k: float, n_slices: int, policy: Policy | None = None",
    "conformal_coverage": "model_id: str, result: CoverageResult, policy: Policy | None = None",
    "leakage_screen": "model_id: str, temporal: int, single: SingleFeatureAuc, overlap: float, resemblance: AucResult, policy: Policy | None = None",
    "data_quality": "model_id: str, counts: Sequence[DataQualityCount], policy: Policy | None = None",
    "cbpe_estimate": "model_id: str, estimate: CbpeAuc, labels_supplied: bool = False",
    "challenger_brier": "model_id: str, result: PairedBrier",
}
FAIR_TEST_ARGS = {
    "demographic_parity": "model_id: str, rates: Mapping[str, SelectionRate], reference: str, policy: Policy | None = None",
    "adverse_impact": "model_id: str, rates: Mapping[str, SelectionRate], reference: str",
    "two_proportion_z": "model_id: str, x1: int, n1: int, x2: int, n2: int, policy: Policy | None = None",
    "fisher_exact": "model_id: str, x1: int, n1: int, x2: int, n2: int, policy: Policy | None = None",
    "equalized_odds": f"model_id: str, y: {ARR} | None, decision: {ARR}, group: {ARR}, policy: Policy | None = None",
    "equal_opportunity": f"model_id: str, y: {ARR} | None, decision: {ARR}, group: {ARR}, policy: Policy | None = None",
    "calibration_within_groups": f"model_id: str, p: {ARR}, y: {ARR} | None, group: {ARR}, policy: Policy | None = None",
    "auc_by_group": f"model_id: str, score: {ARR}, y: {ARR} | None, group: {ARR}, policy: Policy | None = None",
    "conditional_disparity": "model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]",
    "rate_spread_disparity": "model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]",
    "replication": "model_id: str, replication: Replication",
    "situation_testing": "model_id: str, result: SituationResult, policy: Policy | None = None",
}


def section(fq: str, sig: str, units: str, inv: str, check: str, extra: list[str] | None = None) -> str:
    lines = [f"### `{fq}`", "", "```python", sig, "```", "", f"- Units: {units}", f"- Invariants: {inv}"]
    lines += extra or []
    lines += [f"- Check: {check}", ""]
    return "\n".join(lines)


def policy_keys(policy: list, test_id: str) -> list[tuple]:
    return [r for r in policy if r[0] == test_id or r[0].startswith(test_id + ".")]


def test_section(prefix: str, name: str, args: str, test_id: str, light: str, family: str, policy: list) -> str:
    keys = [r for r in policy_keys(policy, test_id) if r[1] != "none"]
    if not keys:
        args = args.replace(", policy: Policy | None = None", "")
    sig = f"def {name}({args}) -> TestResult"
    kind = "ml" if family == "ml" else "fair"
    extra = [f'- Test id: test_id = "{test_id}"', f"- Light: {light}"]
    if keys:
        extra.append("- Policy key: " + ", ".join(f"`{r[0]}` ({r[1]})" for r in keys)
                     + "; the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.")
    else:
        extra.append(f"- Policy: no policy threshold (row `{test_id}` of Policy thresholds states why); the rule above is the whole classification.")
    return section(f"{prefix}.{name}", sig,
                   "A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.",
                   f"Pure and deterministic; ids are prefixed `{kind}.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.",
                   "The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).", extra)


POLICY_INTRO = (
    "Lights come from the engine's `riskvalidation.core.policy.Policy`, a named, versioned set of `Threshold(kind, amber, red)` keyed by test id "
    "(`kind` is `p_value`, `upper_bad` or `lower_bad`; the engine's `core/policy.py`). Every validation function below takes "
    "`policy: Policy | None = None`, where None means `default_policy()`, and classifies with `Policy.classify`. The thresholds of this page are "
    "entries of `riskvalidation/policies/default.json` (U14-E1 adds the `ml.` keys and U14-E2 the `fair.` keys; the key sets are disjoint), each "
    "with its `source` text; a policy that lacks a key returns the `not_evaluated` light, never a colour. `Threshold.classify` is inclusive at its "
    "cut points (`upper_bad`: amber when the metric is at or above `amber`, red at or above `red`; `lower_bad`: amber at or below `amber`, red at "
    "or below `red`; `p_value`: red below `red`, amber below `amber`). A rule stated as 'exceeds' (a tolerance) keeps a value equal to the "
    "tolerance in the better colour: the engine stores `math.nextafter(cut, math.inf)` as the cut point of a row marked strict, so a delta equal "
    "to the tolerance is not a finding and is green. The values are conventions, never regulatory thresholds (06 I.6 l.1268-1270): each is a "
    "named parameter for the main session's approval."
)


def policy_section(rows: list) -> list[str]:
    out = ["## Policy thresholds", "", POLICY_INTRO, "",
           "| key | kind | metric read | amber and red | boundary | basis | label |", "|---|---|---|---|---|---|---|"]
    out += [f"| `{k}` | {kind} | {metric} | {cut} | {boundary} | {basis} | {label} |" for k, kind, metric, cut, boundary, basis, label in rows]
    return out + [""]


def conventions_section(rows: list) -> list[str]:
    out = ["## Conventions table", "", "Values that are arguments of a function and not Policy thresholds; each is a convention for the main session's approval, never regulatory.", "",
           "| value | meaning |", "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    return out + [""]


def build(title: str, cid: str, intro: str, modules: dict, tests: list, test_args: dict, prefix_pkg: str, test_mod: str,
          test_prefix: str, family: str, unverified: list[str], policy: list, conventions: list, names: str, findings: list[str] | None = None) -> str:
    out = [f"# {title}: `{cid}` 1.0.0", "", intro, "",
           "## Conventions (all functions)", "",
           "- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `n` rows, `p` features, `q` protected indicators.",
           "- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); randomness takes a `seed` and uses `numpy.random.default_rng(seed)`. Dataclasses are frozen. The engine imports no learning library: a model enters as a callable on arrays, and the pipeline computes attributions with the pinned `shap`.",
           "- A function that cannot compute because data is missing raises `ValueError` with the reason, or (a validation function) returns the `not_evaluated` light with its reason in `notes`; it never returns a placeholder number.",
           f"- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`). Test ids are prefixed `{test_prefix}`.",
           "- Tolerances, grids, counts and cut-offs are conventions, never regulatory thresholds (06 I.6 l.1268-1270); the named parameters of the case documents are listed in the case schemas, the light cut points in Policy thresholds and the other values in Conventions table.",
           "- Boundary rule of the lights: see Policy thresholds. `Threshold.classify` is inclusive; a tolerance stated as 'exceeds' is stored one float above, so the light and the strict boolean (`robustness_finding`, `overfit_gap`) agree at the boundary.",
           "- No golden value is claimed where the dossiers print none: each check is an identity, an independent reference or a size and power run on a planted defect.", ""]
    for key, (path, pkg, funcs) in modules.items():
        out += [f"## Module `{path}`", ""]
        for name, sig, units, inv, check in funcs:
            out.append(section(f"{pkg}.{name}", sig, units, inv, check))
    out += [f"## Module `riskvalidation/validation/{test_mod}.py`", ""]
    for name, tid, light in tests:
        out.append(test_section(prefix_pkg, name, test_args[name], tid, light, family, policy))
    out += policy_section(policy) + conventions_section(conventions)
    out += ["## Names", "", names, ""]
    if findings:
        out += ["## Findings", ""] + [f"- {f}" for f in findings] + [""]
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


ML_NAMES = ("The function names of this page are ratified as `engine-ml-api` 1.0.0 (decision V5, 2026-10-19); U14-E1 and U14-E2 amend them only through a contract "
            "bump. Two names exist in two modules and are easy to confuse: `ml.conformal.conformal_coverage` (the pure function, "
            "`from riskvalidation.ml.conformal import conformal_coverage`) and `validation.ml.conformal_coverage` (the TestResult function, "
            "`from riskvalidation.validation.ml import conformal_coverage`). Import each from the module named in its heading and never both unqualified.")
FAIR_NAMES = ("The function names of this page are ratified as `engine-fairness-api` 1.0.0 (decision V5, 2026-10-19); U14-E1 and U14-E2 amend them only through a contract "
              "bump. Two pairs exist in two modules and are easy to confuse: `fairness.metrics.calibration_within_groups` and `auc_by_group` (the pure "
              "metrics, `from riskvalidation.fairness.metrics import auc_by_group`) against `validation.fairness.calibration_within_groups` and `auc_by_group` "
              "(the TestResult functions, `from riskvalidation.validation.fairness import auc_by_group`). Import each from the module named in its heading and never both unqualified.")
FAIR_FINDINGS = [
    "F1, the distance normalization. The paper's text (arXiv 2502.01267, equation 5) divides the continuous distance by the range max - min of the attribute. "
    "The reference code (SantanderAI `SituationTesting` at commit 38e2c5b) standardizes with a scikit-learn StandardScaler by default, so its per-attribute distance is "
    "the absolute z-score difference; with normalize=False it divides by max - min of the search set (addendum 7.5). The published counts of addendum 7.6 (2) "
    "were produced under the standard scaler, so they are claimed only under normalization='standard'. C21 uses 'range' (decision V4).",
    "F2, the one-sided interval. The reference code's report rounds z to 1.645 (0.581595 for the toy fixture of addendum 7.6 (4)) and reports the symmetric two-sided "
    "interval [-0.082, 1.082]; equation (10) with the exact quantile gives w_alpha 0.58154 and the one-sided interval [-0.0815, +inf). This page claims equation (10).",
    "F3, the counterfactual paths. The reference code standardizes the counterfactual dataset with its own scaler and its include_centers=True path is broken on pandas 3 "
    "(DataFrame.append); tests use the paper's equations and the goldens of addendum 7.6, never the code's report columns.",
]


def main() -> None:
    ml = build("Engine ML validation API contract", "engine-ml-api", ML_INTRO, sp.ML_MODULES, sp.ML_TESTS, ML_TEST_ARGS,
               "riskvalidation.validation.ml", "ml", "ml.", "ml",
               ["The values of the named parameters (grid, tolerance, seeds, refits, overfit tolerance, weak-spot multiple, shift score, worst share, cut-off) were proposed by U14-S and approved by the main session (decision V6, 2026-10-19); the engine takes them as arguments. The other Policy thresholds are proposed for approval.",
                "MAPIE 1.5.0's exact split-conformal quantile call was not read: the reconciliation test of `split_conformal_quantile` states its parameterisation (UNVERIFIED until U14-E1 reads it).",
                "The dossiers print no worked example with numbers for these tests: no golden value is claimed (sizing, Modules and functions).",
                "MAPIE and fairlearn are optional reconciliation extras (decision Q11), never imported by the engine core."],
               sp.ML_POLICY, sp.ML_CONVENTIONS, ML_NAMES)
    fair = build("Engine fairness API contract", "engine-fairness-api", FAIR_INTRO, sp.FAIR_MODULES, sp.FAIR_TESTS, FAIR_TEST_ARGS,
                 "riskvalidation.validation.fairness", "fairness", "fair.", "fair",
                 ["The approval and denial classification of HMDA `action_taken` is not settled by any source read (addendum UNVERIFIED); the C21 convention is approval = 1 and 2, denial = 3 and is labelled a convention.",
                  "Ethnicity maps to national origin only by convention (addendum H3, UNVERIFIED).",
                  "A counterfactual generator for HMDA is not supplied by the algorithm: C21 runs the ceteris paribus comparator only.",
                  "The Policy thresholds of the four outcome-conditioned battery tests and of the situation-testing share are proposed for the main session's approval; no source gives a value."],
                 sp.FAIR_POLICY, sp.FAIR_CONVENTIONS, FAIR_NAMES, FAIR_FINDINGS)
    for name, text in (("ml-api.md", ml), ("fairness-api.md", fair)):
        _write_unless_amended(OUT / name, text)


def _write_unless_amended(path: Path, text: str) -> None:
    """This builder writes the 1.0.0 pages of U14-S. A page amended since (its heading names a later version, for example
    fairness-api 1.1.0 after the U14-E2 review) is the record and is kept, so a re-run never reverts a contract."""
    if path.exists():
        head = path.read_text(encoding="utf-8").splitlines()[0]
        if not head.endswith(" 1.0.0"):
            print(f"kept {path.name}: {head.split(': ')[-1]} was amended after the 1.0.0 generation")
            return
    path.write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
