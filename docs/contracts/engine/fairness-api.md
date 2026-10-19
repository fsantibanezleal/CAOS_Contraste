# Engine fairness API contract: `engine-fairness-api` 1.0.0

Owner: U14-S (unit sizing `plans/contraste/units/U14-sizing.md`, CAOS_MANAGE). Implemented by U14-E2 in `riskvalidation.fairness` and `riskvalidation.validation.fairness`; called by the C20 and C21 bakes (U14-P2, U14-P3). The tests are written by U14-E2 against this file. Sources: dossier 06 C.7 l.1029-1040, I.6 l.1268-1270; dossier 04 J.3 l.897-905; dossier 07 A.3 l.158-177; the U14 research addendum (`wip/contraste/u14-research-addendum-2026-10-17.md`: H1 field names, H3 legal tests, H5 the situation-testing algorithm). The case documents are `c21-outputs`, `c21-models` (`docs/contracts/schemas/c21/`) and the Taiwan battery rows of the C20 documents. The four-fifths line is an employment benchmark and never a credit-law threshold. HMDA has no outcome (08 l.180-181): the outcome-conditioned tests (equalized odds, equal opportunity, calibration within groups, AUC by group) never run on it. The engine states no legal claim.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `n` rows, `p` features, `q` protected indicators.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); randomness takes a `seed` and uses `numpy.random.default_rng(seed)`. Dataclasses are frozen. The engine imports no learning library: a model enters as a callable on arrays, and the pipeline computes attributions with the pinned `shap`.
- A function that cannot compute because data is missing raises `ValueError` with the reason, or (a validation function) returns the `not_evaluated` light with its reason in `notes`; it never returns a placeholder number.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`). Test ids are prefixed `fair.`.
- Tolerances, grids, counts and cut-offs are conventions, never regulatory thresholds (06 I.6 l.1268-1270); the named parameters of the case documents are listed in the case schemas, the light cut points in Policy thresholds and the other values in Conventions table.
- Boundary rule of the lights: see Policy thresholds. `Threshold.classify` is inclusive; a tolerance stated as 'exceeds' is stored one float above, so the light and the strict boolean (`robustness_finding`, `overfit_gap`) agree at the boundary.
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

- Units: The protected group's selection rate over the chosen reference group's rate: the parity ratio (06 C.7 l.1033-1037); None when the reference rate is 0. It is not the four-fifths ratio, which is taken against the highest-rate group (four_fifths_flag).
- Invariants: Equals demographic_parity_ratio (identity).
- Check: Identity with demographic_parity_ratio.

### `riskvalidation.fairness.metrics.four_fifths_flag`

```python
def four_fifths_flag(rates: Mapping[str, SelectionRate]) -> FourFifths
```

- Units: Each group's favourable count x_g and size n_g against the highest-rate group (x_h, n_h), per 29 CFR 1607.4(D) and dossier 06 C.7 l.1034-1035. A group is flagged when 5 * x_g * n_h < 4 * x_h * n_g: decided on the counts in exact arithmetic, never on a float ratio (60/100 over 75/100 is 0.7999999999999999 in IEEE doubles and exactly 4/5). The highest-rate group is the first of the groups of the highest rate, in the order of rates. The result carries ratio_to_highest per group (None when the highest rate is 0), the label 'employment benchmark' and is_credit_law_threshold = False (I.6 l.1268-1270).
- Invariants: A highest rate of 0 raises no flag; the highest-rate group has ratio 1 and no flag; the ratio is for display and the flag never reads it.
- Check: Golden: 60/100 against 75/100 is exactly four-fifths and is not flagged (0.8 exactly does not flag); 5999/10000 against 75/100 is flagged; 6001/10000 is not. Scenario: White 750/1000 (the reference), Asian 900/1000, Black 650/1000: Black is flagged against the highest-rate group (0.722) and would not be against the reference (0.867).

### `riskvalidation.fairness.metrics.FourFifths`

```python
@dataclass(frozen=True)
class FourFifths: highest_rate_group: str; ratio_to_highest: dict[str, float | None]; flag: dict[str, bool]; threshold: float; label: str; is_credit_law_threshold: bool; compared_with: str
```

- Units: threshold 0.8; ratio dimensionless.
- Invariants: Frozen; label == 'employment benchmark'; is_credit_law_threshold is False; compared_with == 'highest-rate-group'.
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
- Invariants: n1, n2 >= 1; a pooled rate of 0 or 1 gives statistic 0 and p 1 and the field note says so (note is None otherwise).
- Check: Independent reference: scipy.stats.norm for the p-value and statsmodels proportions_ztest.

### `riskvalidation.fairness.inference.ZResult`

```python
@dataclass(frozen=True)
class ZResult: statistic: float; p_value: float; n1: int; n2: int; note: str | None
```

- Units: Statistic dimensionless; p in [0, 1]; note a short reason or None.
- Invariants: Frozen; note is None unless the pooled rate is 0 or 1.
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
def gower_distance(x1: numpy.ndarray, x2: numpy.ndarray, categorical: numpy.ndarray, scale: numpy.ndarray, normalization: str = "range") -> float
```

- Units: Mean over non-protected attributes of the overlap distance (categorical) or the Manhattan distance over the attribute scale (continuous), in [0, 1] under 'range' (arXiv 2502.01267 equations 3 to 5). normalization 'range' (the default, the paper's text, and C21's choice): scale holds max - min of each continuous attribute over the search space. normalization 'standard' (the reference code's default, a StandardScaler): scale holds the population standard deviation (ddof 0) of the attribute, so the continuous term is the absolute z-score difference and is not bounded by 1. Any other value raises ValueError.
- Invariants: Protected attributes never enter; a zero scale raises ValueError.
- Check: Hand-computed pair under each normalization.

### `riskvalidation.fairness.situation.k_nearest`

```python
def k_nearest(center: numpy.ndarray, pool: numpy.ndarray, k: int, categorical: numpy.ndarray, scale: numpy.ndarray, normalization: str = "range") -> numpy.ndarray
```

- Units: Indices of the k nearest rows of the search space by ascending distance (the normalization of gower_distance); neither the protected attribute nor the decision is used (equations 6 and 7).
- Invariants: Ties broken by row order; k <= len(pool).
- Check: Hand-computed toy fixture of the research addendum 7.6 (4), which holds under both normalizations (one continuous attribute: the distance order is the same).

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

- Units: Lower bound delta - z_alpha * sqrt((p_c(1 - p_c) + p_t(1 - p_t)) / k), z_alpha = Phi^-1(1 - alpha) the exact normal quantile (equation 10); returns the lower bound.
- Invariants: The claim is significant when the lower bound exceeds tau; the plus sign of the numerator, not the EAAMO typo (footnote 7).
- Check: Golden (addendum 7.6 (4) with the exact quantile Phi^-1(0.95) = 1.644854): w_alpha = 0.58154 to 1e-5 and lower bound -0.0815 to 1e-4, so the toy claim is not significant (the lower bound is below tau = 0). The reference code's figures for the same fixture use z rounded to 1.645 and a symmetric two-sided interval: recorded under Findings, not claimed.

### `riskvalidation.fairness.situation.situation_test`

```python
def situation_test(X: numpy.ndarray, group: numpy.ndarray, decision: numpy.ndarray, k: int, tau: float = 0.0, alpha: float = 0.05, comparator: str = 'ceteris-paribus', counterfactual: numpy.ndarray | None = None, normalization: str = 'range') -> SituationResult
```

- Units: Runs the test for every complainant of the protected group. comparator is 'ceteris-paribus' or 'mutatis-mutandis'; the latter needs a caller-supplied counterfactual aligned row by row (the algorithm supplies none; public HMDA gives none, so C21 runs the ceteris paribus comparator only, with normalization 'range').
- Invariants: Raises ValueError for 'mutatis-mutandis' without a counterfactual.
- Check: Tested against the paper's equations and the toy golden of addendum 7.6 (4) (under both normalizations). The loan-application counts of addendum 7.6 (2) (ST 55 cases and 44 significant at k = 15, then 65 and 57, 84 and 65, 107 and 85, 204 and 148 at k = 30, 50, 100, 250) were produced by the reference code with its StandardScaler, so they are claimed only under normalization='standard'; nothing claims them under 'range'. Never tested against the reference code's report columns.

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
def demographic_parity(model_id: str, rates: Mapping[str, SelectionRate], reference: str, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.demographic_parity"
- Light: reported as an indicator: green when the largest absolute parity gap is at most the tolerance (a convention), amber above it; never red.
- Policy key: `fair.demographic_parity` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.adverse_impact`

```python
def adverse_impact(model_id: str, rates: Mapping[str, SelectionRate], reference: str) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.adverse_impact"
- Light: amber when four_fifths_flag raises a flag for any group (decided on the exact counts, against the highest-rate group), green otherwise; the four-fifths line is labelled an employment benchmark in `reference` and `notes`, never a credit-law threshold.
- Policy: no policy threshold (row `fair.adverse_impact` of Policy thresholds states why); the rule above is the whole classification.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.two_proportion_z`

```python
def two_proportion_z(model_id: str, x1: int, n1: int, x2: int, n2: int, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.two_proportion_z"
- Light: by the p-value: red below alpha_red, amber below alpha_amber, green otherwise.
- Policy key: `fair.two_proportion_z` (p_value); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.fisher_exact`

```python
def fisher_exact(model_id: str, x1: int, n1: int, x2: int, n2: int, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.fisher_exact"
- Light: by the p-value: red below alpha_red, amber below alpha_amber, green otherwise.
- Policy key: `fair.fisher_exact` (p_value); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.equalized_odds`

```python
def equalized_odds(model_id: str, y: numpy.ndarray | None, decision: numpy.ndarray, group: numpy.ndarray, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.equalized_odds"
- Light: outcome-conditioned: needs an outcome and returns not_evaluated with its reason when none is supplied; never run on HMDA; with an outcome (the Taiwan battery) green below the amber cut point, amber from it, red from the red cut point (conventions).
- Policy key: `fair.equalized_odds` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.equal_opportunity`

```python
def equal_opportunity(model_id: str, y: numpy.ndarray | None, decision: numpy.ndarray, group: numpy.ndarray, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.equal_opportunity"
- Light: outcome-conditioned: same rule as equalized_odds.
- Policy key: `fair.equal_opportunity` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.calibration_within_groups`

```python
def calibration_within_groups(model_id: str, p: numpy.ndarray, y: numpy.ndarray | None, group: numpy.ndarray, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.calibration_within_groups"
- Light: outcome-conditioned: same rule as equalized_odds.
- Policy key: `fair.calibration_within_groups` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.auc_by_group`

```python
def auc_by_group(model_id: str, score: numpy.ndarray, y: numpy.ndarray | None, group: numpy.ndarray, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.auc_by_group"
- Light: outcome-conditioned: same rule as equalized_odds.
- Policy key: `fair.auc_by_group` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.conditional_disparity`

```python
def conditional_disparity(model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.conditional_disparity"
- Light: reported as an approximation of comparative evidence with the missing controls named; amber when the 95 percent interval excludes 0; never a finding of violation.
- Policy: no policy threshold (row `fair.conditional_disparity` of Policy thresholds states why); the rule above is the whole classification.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.rate_spread_disparity`

```python
def rate_spread_disparity(model_id: str, effect: Effect, controls: Sequence[str], missing_controls: Sequence[str]) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.rate_spread_disparity"
- Light: same rule as conditional_disparity.
- Policy: no policy threshold (row `fair.rate_spread_disparity` of Policy thresholds states why); the rule above is the whole classification.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.replication`

```python
def replication(model_id: str, replication: Replication) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.replication"
- Light: amber when the sign differs between year t and t+1.
- Policy: no policy threshold (row `fair.replication` of Policy thresholds states why); the rule above is the whole classification.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.fairness.situation_testing`

```python
def situation_testing(model_id: str, result: SituationResult, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `fair.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "fair.situation_testing"
- Light: reported as individual-level indicators: amber when the significant share of the complainants reaches the cut point; never red; no legal claim.
- Policy key: `fair.situation_testing` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `default_policy()`.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

## Policy thresholds

Lights come from the engine's `riskvalidation.core.policy.Policy`, a named, versioned set of `Threshold(kind, amber, red)` keyed by test id (`kind` is `p_value`, `upper_bad` or `lower_bad`; engine v0.07.000 `core/policy.py`). Every validation function below takes `policy: Policy | None = None`, where None means `default_policy()`, and classifies with `Policy.classify`. The thresholds of this page are entries of `riskvalidation/policies/default.json` (U14-E1 adds the `ml.` keys and U14-E2 the `fair.` keys; the key sets are disjoint), each with its `source` text; a policy that lacks a key returns the `not_evaluated` light, never a colour. `Threshold.classify` is inclusive at its cut points (`upper_bad`: amber when the metric is at or above `amber`, red at or above `red`; `lower_bad`: amber at or below `amber`, red at or below `red`; `p_value`: red below `red`, amber below `amber`). A rule stated as 'exceeds' (a tolerance) keeps a value equal to the tolerance in the better colour: the engine stores `math.nextafter(cut, math.inf)` as the cut point of a row marked strict, so a delta equal to the tolerance is not a finding and is green. The values are conventions, never regulatory thresholds (06 I.6 l.1268-1270): each is a named parameter for the main session's approval.

| key | kind | metric read | amber and red | boundary | basis | label |
|---|---|---|---|---|---|---|
| `fair.demographic_parity` | upper_bad | largest absolute difference of a group's selection rate from the reference rate | amber 0.05, red 2.0 | strict | amber: proposed, no dossier value; red 2.0 is a sentinel above the metric's range (at most 1): never red | convention |
| `fair.adverse_impact` | none | the four-fifths flag of four_fifths_flag, decided on exact counts | none | not applicable | rule, not a convention: the 0.8 line is the 29 CFR 1607.4(D) employment benchmark, never a credit-law threshold | rule, not a convention |
| `fair.two_proportion_z` | p_value | two-sided p-value of the pooled z-test | amber 0.05 (alpha_amber), red 0.01 (alpha_red) | inclusive | the engine default p-value cut points | convention |
| `fair.fisher_exact` | p_value | two-sided exact p-value | amber 0.05 (alpha_amber), red 0.01 (alpha_red) | inclusive | the engine default p-value cut points | convention |
| `fair.equalized_odds` | upper_bad | equalized odds difference (largest true or false positive rate gap) | amber 0.05, red 0.10 | inclusive | proposed for the Taiwan battery: no dossier value (06 C.7 l.1029-1033) | convention |
| `fair.equal_opportunity` | upper_bad | equal opportunity difference (largest true positive rate gap) | amber 0.05, red 0.10 | inclusive | proposed for the Taiwan battery: no dossier value | convention |
| `fair.calibration_within_groups` | upper_bad | largest expected calibration error over the groups | amber 0.05, red 0.10 | inclusive | proposed for the Taiwan battery: no dossier value (04 J.3 l.904-905) | convention |
| `fair.auc_by_group` | upper_bad | largest AUC gap between two groups | amber 0.05, red 0.10 | inclusive | proposed for the Taiwan battery: no dossier value (04 J.3 l.904-905) | convention |
| `fair.conditional_disparity` | none | the 95 percent Wald interval of the protected effect: amber when it excludes 0 | none | not applicable | the interval level 0.95 is a convention; no numeric cut point | convention |
| `fair.rate_spread_disparity` | none | the 95 percent interval of the rate-spread effect: amber when it excludes 0 | none | not applicable | the interval level 0.95 is a convention; no numeric cut point | convention |
| `fair.replication` | none | the sign of the effect on year t and on year t+1 | none | not applicable | rule, not a convention: sign and size are the replication test (decision Q4) | rule, not a convention |
| `fair.situation_testing` | upper_bad | n_significant over n_complainants | amber 0.10, red 2.0 | inclusive | amber: proposed, no source value; red 2.0 is a sentinel above the metric's range (at most 1): never red | convention |

## Conventions table

Values that are arguments of a function and not Policy thresholds; each is a convention for the main session's approval, never regulatory.

| value | meaning |
|---|---|
| situation k = 30 | the neighbourhood size, 'a common size used in non-algorithmic situation testing' (arXiv 2502.01267, section 5.1) |
| situation alpha = 0.05 and tau = 0 | the level and the accepted deviation of the experiments of the paper (section 5.1: tau 'often 0') |
| situation distance normalization = range | C21's choice: the paper's text (equation 5); 'standard' follows the reference code |
| calibration_within_groups n_bins = 10 | the number of calibration bins per group |
| interval level 0.95 | the level of every Wald interval of the decision and rate-spread models |

## Names

The function names of this page are ratified as `engine-fairness-api` 1.0.0 (decision V5, 2026-10-19); U14-E1 and U14-E2 amend them only through a contract bump. Two pairs exist in two modules and are easy to confuse: `fairness.metrics.calibration_within_groups` and `auc_by_group` (the pure metrics, `from riskvalidation.fairness.metrics import auc_by_group`) against `validation.fairness.calibration_within_groups` and `auc_by_group` (the TestResult functions, `from riskvalidation.validation.fairness import auc_by_group`). Import each from the module named in its heading and never both unqualified.

## Findings

- F1, the distance normalization. The paper's text (arXiv 2502.01267, equation 5) divides the continuous distance by the range max - min of the attribute. The reference code (SantanderAI `SituationTesting` at commit 38e2c5b) standardizes with a scikit-learn StandardScaler by default, so its per-attribute distance is the absolute z-score difference; with normalize=False it divides by max - min of the search set (addendum 7.5). The published counts of addendum 7.6 (2) were produced under the standard scaler, so they are claimed only under normalization='standard'. C21 uses 'range' (decision V4).
- F2, the one-sided interval. The reference code's report rounds z to 1.645 (0.581595 for the toy fixture of addendum 7.6 (4)) and reports the symmetric two-sided interval [-0.082, 1.082]; equation (10) with the exact quantile gives w_alpha 0.58154 and the one-sided interval [-0.0815, +inf). This page claims equation (10).
- F3, the counterfactual paths. The reference code standardizes the counterfactual dataset with its own scaler and its include_centers=True path is broken on pandas 3 (DataFrame.append); tests use the paper's equations and the goldens of addendum 7.6, never the code's report columns.

## UNVERIFIED and open items

- The approval and denial classification of HMDA `action_taken` is not settled by any source read (addendum UNVERIFIED); the C21 convention is approval = 1 and 2, denial = 3 and is labelled a convention.
- Ethnicity maps to national origin only by convention (addendum H3, UNVERIFIED).
- A counterfactual generator for HMDA is not supplied by the algorithm: C21 runs the ceteris paribus comparator only.
- The Policy thresholds of the four outcome-conditioned battery tests and of the situation-testing share are proposed for the main session's approval; no source gives a value.
