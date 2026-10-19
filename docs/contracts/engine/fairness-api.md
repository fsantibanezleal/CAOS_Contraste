# Engine fairness API contract: `engine-fairness-api` 1.0.0

Owner: U14-S (unit sizing `plans/contraste/units/U14-sizing.md`, CAOS_MANAGE). Implemented by U14-E2 in `riskvalidation.fairness` and `riskvalidation.validation.fairness`; called by the C20 and C21 bakes (U14-P2, U14-P3). The tests are written by U14-E2 against this file. Sources: dossier 06 C.7 l.1029-1040, I.6 l.1268-1270; dossier 04 J.3 l.897-905; dossier 07 A.3 l.158-177; the U14 research addendum (`wip/contraste/u14-research-addendum-2026-10-17.md`: H1 field names, H3 legal tests, H5 the situation-testing algorithm). The case documents are `c21-outputs`, `c21-models` (`docs/contracts/schemas/c21/`) and the Taiwan battery rows of the C20 documents. The four-fifths line is an employment benchmark and never a credit-law threshold. HMDA has no outcome (08 l.180-181): the outcome-conditioned tests (equalized odds, equal opportunity, calibration within groups, AUC by group) never run on it. The engine states no legal claim.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `n` rows, `p` features, `q` protected indicators.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); randomness takes a `seed` and uses `numpy.random.default_rng(seed)`. Dataclasses are frozen. The engine imports no learning library: a model enters as a callable on arrays, and the pipeline computes attributions with the pinned `shap`.
- A function that cannot compute because data is missing raises `ValueError` with the reason, or (a validation function) returns the `not_evaluated` light with its reason in `notes`; it never returns a placeholder number.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`). Test ids are prefixed `fair.`.
- Tolerances, grids, counts and cut-offs are conventions, never regulatory thresholds (06 I.6 l.1268-1270); the named parameters of the case documents are listed in the case schemas.
- No golden value is claimed where the dossiers print none: each check is an identity, an independent reference or a size and power run on a planted defect.

## Module `riskvalidation/fairness/metrics.py`

### `riskvalidation.fairness.metrics.group_selection_rates`

```python
def group_selection_rates(decision: numpy.ndarray, group: numpy.ndarray) -> dict[str, SelectionRate]
```

- Units: decision int {0, 1} shape (n,) (1 favourable); group label per row; returns the selection rate per group in [0, 1] with n and the favourable count (06 C.7 l.1029-1033).
- Invariants: Groups with no rows are absent; the rates are favourable / n.
- Check: Hand-computed 2-group table is exact.

### `riskvalidation.fairness.metrics.SelectionRate`

```python
@dataclass(frozen=True)
class SelectionRate: group: str; n: int; favourable: int; rate: float
```

- Units: rate in [0, 1].
- Invariants: Frozen; rate == favourable / n.
- Check: Constructed only by group_selection_rates.

### `riskvalidation.fairness.metrics.demographic_parity_difference`

```python
def demographic_parity_difference(rates: Mapping[str, SelectionRate], reference: str) -> dict[str, float]
```

- Units: Rate of each group minus the reference rate, in [-1, 1].
- Invariants: The reference maps to 0.
- Check: Reconciles with fairlearn demographic_parity_difference (optional extra) for two groups.

### `riskvalidation.fairness.metrics.demographic_parity_ratio`

```python
def demographic_parity_ratio(rates: Mapping[str, SelectionRate], reference: str) -> dict[str, float | None]
```

- Units: Rate of each group over the reference rate, >= 0; None when the reference rate is 0 (never a fabricated number).
- Invariants: The reference maps to 1.
- Check: Reconciles with fairlearn demographic_parity_ratio for two groups.

### `riskvalidation.fairness.metrics.equalized_odds_difference`

```python
def equalized_odds_difference(y: numpy.ndarray, decision: numpy.ndarray, group: numpy.ndarray) -> float
```

- Units: Largest gap across groups in the true positive rate and the false positive rate, in [0, 1] (Hardt, Price and Srebro 2016). Needs an outcome y: never run on HMDA.
- Invariants: Requires both classes in every group, else ValueError.
- Check: Reconciles with fairlearn equalized_odds_difference.

### `riskvalidation.fairness.metrics.equal_opportunity_difference`

```python
def equal_opportunity_difference(y: numpy.ndarray, decision: numpy.ndarray, group: numpy.ndarray) -> float
```

- Units: Largest gap across groups in the true positive rate, in [0, 1]. Needs an outcome y: never run on HMDA.
- Invariants: Requires positives in every group.
- Check: Equals the true positive rate part of equalized odds (identity).

### `riskvalidation.fairness.metrics.adverse_impact_ratio`

```python
def adverse_impact_ratio(rates: Mapping[str, SelectionRate], reference: str) -> dict[str, float | None]
```

- Units: The protected group's selection rate over the reference group's rate (06 C.7 l.1033-1037); None when the reference rate is 0.
- Invariants: Equals demographic_parity_ratio (identity).
- Check: Identity with demographic_parity_ratio.

### `riskvalidation.fairness.metrics.four_fifths_flag`

```python
def four_fifths_flag(air: float | None) -> FourFifths
```

- Units: air dimensionless. The flag is raised when the ratio is below 0.8 (29 CFR 1607.4(D)); the result carries the label 'employment benchmark' and is_credit_law_threshold = False (I.6 l.1268-1270).
- Invariants: None raises no flag.
- Check: Boundary: 0.8 exactly does not flag; just below 0.8 flips the flag (C.7 l.1034).

### `riskvalidation.fairness.metrics.FourFifths`

```python
@dataclass(frozen=True)
class FourFifths: flag: bool; threshold: float; label: str; is_credit_law_threshold: bool
```

- Units: threshold 0.8.
- Invariants: Frozen; label == 'employment benchmark'; is_credit_law_threshold is False.
- Check: Constructed only by four_fifths_flag.

### `riskvalidation.fairness.metrics.calibration_within_groups`

```python
def calibration_within_groups(p: numpy.ndarray, y: numpy.ndarray, group: numpy.ndarray, n_bins: int = 10) -> dict[str, float]
```

- Units: Per group, the expected calibration error of PD p against outcome y, in [0, 1] (04 J.3 l.904-905). Needs an outcome: never run on HMDA.
- Invariants: Groups with fewer rows than n_bins are not evaluated and counted.
- Check: A calibrated simulated group has ECE within Monte Carlo error of zero.

### `riskvalidation.fairness.metrics.auc_by_group`

```python
def auc_by_group(score: numpy.ndarray, y: numpy.ndarray, group: numpy.ndarray) -> dict[str, float]
```

- Units: Per group, AUC in [0, 1] by disc_auc (04 J.3 l.904-905). Needs an outcome: never run on HMDA.
- Invariants: Single-class groups are omitted and counted.
- Check: Equal to disc_auc on each group (identity).

## Module `riskvalidation/fairness/inference.py`

### `riskvalidation.fairness.inference.two_proportion_z_test`

```python
def two_proportion_z_test(x1: int, n1: int, x2: int, n2: int) -> ZResult
```

- Units: Counts of favourable decisions and sizes of two groups; pooled two-sided z statistic and p-value in [0, 1] (06 C.7 l.1038-1039). Smaller differences can matter when statistically significant.
- Invariants: n1, n2 >= 1; a pooled rate of 0 or 1 gives statistic 0 and p 1 with a note.
- Check: Independent reference: scipy.stats.norm for the p-value and statsmodels proportions_ztest.

### `riskvalidation.fairness.inference.ZResult`

```python
@dataclass(frozen=True)
class ZResult: statistic: float; p_value: float; n1: int; n2: int
```

- Units: Statistic dimensionless; p in [0, 1].
- Invariants: Frozen.
- Check: Constructed only by two_proportion_z_test.

### `riskvalidation.fairness.inference.fisher_exact_test`

```python
def fisher_exact_test(x1: int, n1: int, x2: int, n2: int) -> FisherResult
```

- Units: Same inputs; odds ratio >= 0 (None when undefined) and the two-sided exact p-value in [0, 1].
- Invariants: Conditional maximum likelihood is not used: the sample odds ratio is returned.
- Check: Independent reference: scipy.stats.fisher_exact, equal to 1e-12.

### `riskvalidation.fairness.inference.FisherResult`

```python
@dataclass(frozen=True)
class FisherResult: odds_ratio: float | None; p_value: float
```

- Units: p in [0, 1].
- Invariants: Frozen.
- Check: Constructed only by fisher_exact_test.

## Module `riskvalidation/fairness/conditional.py`

### `riskvalidation.fairness.conditional.fit_decision_model`

```python
def fit_decision_model(decision: numpy.ndarray, protected: numpy.ndarray, controls: numpy.ndarray) -> DecisionModel
```

- Units: decision {0, 1} (approval by the C21 convention: action taken 1 or 2 is 1, 3 is 0); protected shape (n, q) indicator columns against the reference; controls shape (n, c) the permitted underwriting controls (debt-to-income recoded to its published bins, combined loan-to-value, income, loan amount, property value, loan type). Logistic model by iteratively reweighted least squares.
- Invariants: Coefficients are log-odds; convergence flag; the missing credit score is the caller's statement (public HMDA has none).
- Check: Independent reference: statsmodels Logit (pipeline), agreement to 1e-6 on the coefficients.

### `riskvalidation.fairness.conditional.DecisionModel`

```python
@dataclass(frozen=True)
class DecisionModel: coefficients: tuple[float, ...]; standard_errors: tuple[float, ...]; n: int; converged: bool
```

- Units: Log-odds units.
- Invariants: Frozen; equal lengths.
- Check: Constructed only by the fit functions.

### `riskvalidation.fairness.conditional.protected_effect`

```python
def protected_effect(model: DecisionModel, index: int, level: float = 0.95) -> Effect
```

- Units: Returns the coefficient, the odds ratio and the Wald interval of one protected indicator.
- Invariants: ci lo <= coefficient <= ci hi; odds ratio = exp(coefficient).
- Check: Interval equals coefficient +/- z * se (identity).

### `riskvalidation.fairness.conditional.Effect`

```python
@dataclass(frozen=True)
class Effect: coefficient: float; odds_ratio: float; lo: float; hi: float; level: float
```

- Units: Log-odds, odds ratio, interval at the level.
- Invariants: Frozen.
- Check: Constructed only by protected_effect.

### `riskvalidation.fairness.conditional.fit_rate_spread_model`

```python
def fit_rate_spread_model(rate_spread: numpy.ndarray, protected: numpy.ndarray, controls: numpy.ndarray) -> DecisionModel
```

- Units: rate_spread in percentage points for the loans that carry it (action taken 1 or 2); linear least squares on the same terms; coefficients in percentage points.
- Invariants: Rows with a missing rate_spread are dropped and counted, never imputed.
- Check: Independent reference: statsmodels OLS to 1e-8.

## Module `riskvalidation/fairness/replication.py`

### `riskvalidation.fairness.replication.replicate_effect`

```python
def replicate_effect(fit: Effect, confirm: Effect) -> Replication
```

- Units: The estimate on year t and the same estimate refitted on year t+1; compared by sign and size (decision Q4): same_sign, and the size ratio confirm over fit (None when the fit coefficient is 0).
- Invariants: No verdict beyond sign and size is returned.
- Check: Planted equal estimates give ratio 1 and same_sign True.

### `riskvalidation.fairness.replication.Replication`

```python
@dataclass(frozen=True)
class Replication: same_sign: bool; size_ratio: float | None; fit_coefficient: float; confirm_coefficient: float
```

- Units: Coefficient units of the fit.
- Invariants: Frozen.
- Check: Constructed only by replicate_effect.

## Module `riskvalidation/fairness/situation.py`

### `riskvalidation.fairness.situation.gower_distance`

```python
def gower_distance(x1: numpy.ndarray, x2: numpy.ndarray, categorical: numpy.ndarray, ranges: numpy.ndarray) -> float
```

- Units: Mean over non-protected attributes of the overlap distance (categorical) or the Manhattan distance over the attribute range (continuous), in [0, 1] (arXiv 2502.01267 equations 3 to 5).
- Invariants: Protected attributes never enter.
- Check: Hand-computed pair.

### `riskvalidation.fairness.situation.k_nearest`

```python
def k_nearest(center: numpy.ndarray, pool: numpy.ndarray, k: int, categorical: numpy.ndarray, ranges: numpy.ndarray) -> numpy.ndarray
```

- Units: Indices of the k nearest rows of the search space by ascending distance; neither the protected attribute nor the decision is used (equations 6 and 7).
- Invariants: Ties broken by row order; k <= len(pool).
- Check: Hand-computed toy fixture of the research addendum 7.6 (4).

### `riskvalidation.fairness.situation.situation_statistic`

```python
def situation_statistic(decision_control: numpy.ndarray, decision_test: numpy.ndarray, negative: int = 0) -> tuple[float, float, float]
```

- Units: Returns (delta_p, p_c, p_t): the proportion of negative decisions in the control group minus the test group (equations 8 and 9), in [-1, 1].
- Invariants: Centers excluded (CST without centers, denominator k).
- Check: Golden (addendum 7.6 (4)): control outcomes 0, 1 and test 1, 1 give p_c 0.5, p_t 0.0, delta 0.5.

### `riskvalidation.fairness.situation.wald_interval_one_sided`

```python
def wald_interval_one_sided(delta: float, p_c: float, p_t: float, k: int, alpha: float = 0.05) -> float
```

- Units: Lower bound delta - z_alpha * sqrt((p_c(1 - p_c) + p_t(1 - p_t)) / k), z_alpha the (1 - alpha) normal quantile (equation 10).
- Invariants: The claim is significant when the lower bound exceeds tau; the plus sign of the numerator, not the EAAMO typo (footnote 7).
- Check: Golden (addendum 7.6 (4)): d_alpha = 1.645 * sqrt(0.25 / 2) = 0.581595, interval [-0.082, 1.082], not significant.

### `riskvalidation.fairness.situation.situation_test`

```python
def situation_test(X: numpy.ndarray, group: numpy.ndarray, decision: numpy.ndarray, k: int, tau: float = 0.0, alpha: float = 0.05, comparator: str = 'ceteris-paribus', counterfactual: numpy.ndarray | None = None) -> SituationResult
```

- Units: Runs the test for every complainant of the protected group. comparator is 'ceteris-paribus' or 'mutatis-mutandis'; the latter needs a caller-supplied counterfactual aligned row by row (the algorithm supplies none; public HMDA gives none, so C21 runs the ceteris paribus comparator only).
- Invariants: Raises ValueError for 'mutatis-mutandis' without a counterfactual.
- Check: Tested against the paper's equations and the golden counts of addendum 7.6, never against the reference code's report columns.

### `riskvalidation.fairness.situation.SituationResult`

```python
@dataclass(frozen=True)
class SituationResult: n_complainants: int; n_cases: int; n_significant: int; k: int; tau: float; alpha: float
```

- Units: Counts.
- Invariants: Frozen; n_significant <= n_cases <= n_complainants.
- Check: Constructed only by situation_test.

### `riskvalidation.fairness.situation.bonferroni_alpha`

```python
def bonferroni_alpha(alpha: float, q: int) -> float
```

- Units: Level alpha / q for q protected attributes (multiple discrimination, Definition 4.6).
- Invariants: q >= 1.
- Check: alpha / q exactly.

## Module `riskvalidation/fairness/plants.py`

### `riskvalidation.fairness.plants.ThresholdBiasPlant`

```python
class ThresholdBiasPlant(GeneratorBase): def __init__(self, n: int, gap: float, seed: int)
```

- Units: gap the group-dependent decision threshold shift.
- Invariants: Built on LogisticPortfolio; truth() gives the true selection-rate gap; gap 0 is the null.
- Check: Size at gap 0 and power at the planted gap (at least 4,000 repetitions).

### `riskvalidation.fairness.plants.LabelNoiseBiasPlant`

```python
class LabelNoiseBiasPlant(GeneratorBase): def __init__(self, n: int, noise: float, seed: int)
```

- Units: noise the group-dependent label flip rate.
- Invariants: truth() gives the flip rate.
- Check: Power of equalized odds against the planted noise.

### `riskvalidation.fairness.plants.ProxyFeaturePlant`

```python
class ProxyFeaturePlant(GeneratorBase): def __init__(self, n: int, proxy_strength: float, seed: int)
```

- Units: proxy_strength the correlation of a feature with the protected attribute.
- Invariants: truth() names the proxy.
- Check: Controlled disparity falls as the proxy is controlled for (power).

## Module `riskvalidation/validation/fairness.py`

### `riskvalidation.validation.fairness.demographic_parity`

```python
def demographic_parity(model_id: str, rates: Mapping[str, SelectionRate], reference: str, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.demographic_parity"
- Light: reported as an indicator; green when the gap is within the policy tolerance (a convention), amber otherwise; never red.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.adverse_impact`

```python
def adverse_impact(model_id: str, rates: Mapping[str, SelectionRate], reference: str) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.adverse_impact"
- Light: amber when the ratio is below 0.8; the four-fifths line is labelled an employment benchmark in `reference` and `notes`, never a credit-law threshold.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.two_proportion_z`

```python
def two_proportion_z(model_id: str, x1: int, n1: int, x2: int, n2: int, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.two_proportion_z"
- Light: by the p-value with alpha_amber and alpha_red.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.fisher_exact`

```python
def fisher_exact(model_id: str, x1: int, n1: int, x2: int, n2: int, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.fisher_exact"
- Light: by the p-value with alpha_amber and alpha_red.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.equalized_odds`

```python
def equalized_odds(model_id: str, y: numpy.ndarray | None, decision: numpy.ndarray, group: numpy.ndarray, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.equalized_odds"
- Light: outcome-conditioned: needs an outcome and returns not_evaluated with its reason when none is supplied; never run on HMDA.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.equal_opportunity`

```python
def equal_opportunity(model_id: str, y: numpy.ndarray | None, decision: numpy.ndarray, group: numpy.ndarray, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.equal_opportunity"
- Light: outcome-conditioned: same rule as equalized_odds.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.calibration_within_groups`

```python
def calibration_within_groups(model_id: str, p: numpy.ndarray, y: numpy.ndarray | None, group: numpy.ndarray, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.calibration_within_groups"
- Light: outcome-conditioned: same rule as equalized_odds.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.auc_by_group`

```python
def auc_by_group(model_id: str, score: numpy.ndarray, y: numpy.ndarray | None, group: numpy.ndarray, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.auc_by_group"
- Light: outcome-conditioned: same rule as equalized_odds.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.conditional_disparity`

```python
def conditional_disparity(model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.conditional_disparity"
- Light: reported as an approximation of comparative evidence with the missing controls named; amber when the interval excludes 0; never a finding of violation.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.rate_spread_disparity`

```python
def rate_spread_disparity(model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.rate_spread_disparity"
- Light: same rule as conditional_disparity.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.replication`

```python
def replication(model_id: str, replication: Replication) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.replication"
- Light: amber when the sign differs between year t and t+1.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.situation_testing`

```python
def situation_testing(model_id: str, result: SituationResult, policy: FairPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.situation_testing"
- Light: reported as individual-level indicators: amber when the significant share exceeds the policy; no legal claim.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

## UNVERIFIED and open items

- The approval and denial classification of HMDA `action_taken` is not settled by any source read (addendum UNVERIFIED); the C21 convention is approval = 1 and 2, denial = 3 and is labelled a convention.
- Ethnicity maps to national origin only by convention (addendum H3, UNVERIFIED).
- The reference situation-testing code differs from the paper in the distance normalisation and has a broken counterfactual-with-centers path: tests use the paper's equations and the golden values of the addendum 7.6.
- A counterfactual generator for HMDA is not supplied by the algorithm: C21 runs the ceteris paribus comparator only.
