# Engine ML validation API contract: `engine-ml-api` 1.0.0

Owner: U14-S (unit sizing `plans/contraste/units/U14-sizing.md`, CAOS_MANAGE). Implemented by U14-E1 in `riskvalidation.ml` and `riskvalidation.validation.ml` (repository CAOS_RiskValidation); called by the C02 and C20 bakes (U14-P1, U14-P2). The tests of every function are written by U14-E1 against this file: a function exists with exactly the signature below, and each identity, independent reference or planted-defect check is a test. Changing a signature or a unit is a breaking change (a new major version of this contract). Sources: dossier 06 (`wip/contraste/06-model-risk-management-and-validation-2026-10-04.md`, C.7 l.979-1058, I.1 l.1184-1200, I.6), dossier 04 (J.2 l.881-883, ladder P4 l.968), dossier 07 (D patterns 3 and 6) and the product SDD Method ladder. The case documents this contract feeds are `c02-outputs`, `c02-models`, `c20-outputs`, `c20-outputs-shift`, `c20-outputs-seeds`, `c20-outputs-perturbation`, `c20-outputs-leakage` and `c20-models` (`docs/contracts/schemas/c02/`, `c20/`). The engine computes; it states no compliance claim. The drift tests are the existing `validation/stability.py` (PSI, CSI, chi-square, KS, Wasserstein), reused unchanged.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `n` rows, `p` features, `q` protected indicators.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); randomness takes a `seed` and uses `numpy.random.default_rng(seed)`. Dataclasses are frozen. The engine imports no learning library: a model enters as a callable on arrays, and the pipeline computes attributions with the pinned `shap`.
- A function that cannot compute because data is missing raises `ValueError` with the reason, or (a validation function) returns the `not_evaluated` light with its reason in `notes`; it never returns a placeholder number.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`). Test ids are prefixed `ml.`.
- Tolerances, grids, counts and cut-offs are conventions, never regulatory thresholds (06 I.6 l.1268-1270); the named parameters of the case documents are listed in the case schemas.
- No golden value is claimed where the dossiers print none: each check is an identity, an independent reference or a size and power run on a planted defect.

## Module `riskvalidation/ml/robustness.py`

### `riskvalidation.ml.robustness.perturb_features`

```python
def perturb_features(X: numpy.ndarray, eps: float, seed: int, sd: numpy.ndarray | None = None) -> numpy.ndarray
```

- Units: X shape (n, p) float64 features; eps a multiple of each feature's standard deviation (dimensionless); sd shape (p,) in feature units, default the column standard deviation of X; returns shape (n, p).
- Invariants: Pure; the same seed gives the same array; eps = 0 returns X unchanged; the noise of column j is Gaussian with standard deviation eps * sd[j]; applied to the evaluation features only, never to the training slice (06 C.7 l.1009-1012).
- Check: eps = 0 identity; the sample standard deviation of the noise is eps * sd[j] within 4 Monte Carlo standard errors on 100,000 rows.

### `riskvalidation.ml.robustness.robustness_curve`

```python
def robustness_curve(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, y: numpy.ndarray, grid: Sequence[float], seed: int) -> RobustnessCurve
```

- Units: predict maps (n, p) to PD of shape (n,) in (0, 1); y int {0, 1} shape (n,); grid noise scales (multiples of sd); returns AUC and Brier per scale (both in [0, 1]) and the AUC delta against scale 0.
- Invariants: The first point is scale 0; deltas are metric(eps) - metric(0); the model enters only as a callable (the engine imports no learning library); both classes must be present.
- Check: A constant predictor has AUC 0.5 at every scale; a predictor ignoring the noisy column has a zero delta (identity).

### `riskvalidation.ml.robustness.RobustnessCurve`

```python
@dataclass(frozen=True)
class RobustnessCurve: grid: tuple[float, ...]; auc: tuple[float, ...]; brier: tuple[float, ...]; auc_delta: tuple[float, ...]
```

- Units: Tuples of equal length; auc and brier in [0, 1]; auc_delta in [-1, 1].
- Invariants: Frozen; equal lengths; grid[0] == 0.0.
- Check: Constructed only by robustness_curve; length equality asserted in the test.

### `riskvalidation.ml.robustness.robustness_finding`

```python
def robustness_finding(curve: RobustnessCurve, tolerance: float, preset_eps: float) -> bool
```

- Units: tolerance in AUC points (decimal); preset_eps a multiple of sd that must be a grid point.
- Invariants: True exactly when -auc_delta at preset_eps exceeds tolerance; raises ValueError when preset_eps is not on the grid (06 C.7 l.1009-1012).
- Check: Boundary: a delta equal to the tolerance is not a finding.

### `riskvalidation.ml.robustness.shift_score_rank`

```python
def shift_score_rank(X_dev: numpy.ndarray, X_eval: numpy.ndarray, seed: int) -> numpy.ndarray
```

- Units: Shapes (n_dev, p) and (n_eval, p); returns the shift score of each evaluation row in [0, 1], shape (n_eval,): the probability a resemblance classifier gives to 'evaluation'.
- Invariants: Deterministic for a seed; scores of two identical samples average near 0.5; the classifier is the pipeline's, passed as the default logistic fit of the engine core (NumPy and SciPy only).
- Check: Identical samples give a mean score within 0.05 of 0.5; a planted covariate shift ranks the shifted rows above the rest (power).

### `riskvalidation.ml.robustness.worst_subsample_performance`

```python
def worst_subsample_performance(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, y: numpy.ndarray, score: numpy.ndarray, share: float) -> SubsampleResult
```

- Units: score shape (n,); share in (0, 1) (named parameter worst_subsample_share, a convention); returns AUC and Brier on the share of rows with the highest shift score.
- Invariants: The subsample holds ceil(share * n) rows; ties broken by row order; the full-sample metric is returned beside it (06 C.7 l.1013-1015).
- Check: share = 1 returns the full-sample metrics exactly.

### `riskvalidation.ml.robustness.SubsampleResult`

```python
@dataclass(frozen=True)
class SubsampleResult: n: int; auc: float; brier: float; auc_full: float; brier_full: float
```

- Units: n rows; metrics in [0, 1].
- Invariants: Frozen; n >= 1.
- Check: Constructed only by worst_subsample_performance.

### `riskvalidation.ml.robustness.oot_window_performance`

```python
def oot_window_performance(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, y: numpy.ndarray, window: numpy.ndarray) -> dict[str, float]
```

- Units: window integer label per row (shape (n,)); returns AUC per window label; windows with a single class are omitted and counted in the result key 'omitted'.
- Invariants: Keys are the window labels as strings; a window with fewer than two classes never gets a number (missing-data rule).
- Check: Planted single-class window is omitted and counted.

## Module `riskvalidation/ml/seeds.py`

### `riskvalidation.ml.seeds.seed_auc_dispersion`

```python
def seed_auc_dispersion(train: Callable[[int], Callable[[numpy.ndarray], numpy.ndarray]], X: numpy.ndarray, y: numpy.ndarray, seeds: Sequence[int]) -> SeedDispersion
```

- Units: train(seed) returns a predict callable (the pipeline supplies it); seeds distinct integers (named parameter n_seeds is their count, a convention); AUC in [0, 1].
- Invariants: Pure given train; mean, sample standard deviation (ddof 1), min and max of the AUC across seeds; at least two seeds (06 I.1 l.1191; ECB paragraph 43).
- Check: A train function that ignores its seed has a zero standard deviation (identity).

### `riskvalidation.ml.seeds.SeedDispersion`

```python
@dataclass(frozen=True)
class SeedDispersion: n_seeds: int; mean: float; sd: float; minimum: float; maximum: float
```

- Units: AUC units, in [0, 1].
- Invariants: Frozen; minimum <= mean <= maximum; sd >= 0.
- Check: Constructed only by seed_auc_dispersion.

### `riskvalidation.ml.seeds.grade_assignment_stability`

```python
def grade_assignment_stability(pd_by_seed: numpy.ndarray, edges: numpy.ndarray) -> float
```

- Units: pd_by_seed shape (n_seeds, n) PD in (0, 1); edges increasing PD cut points shape (g - 1,); returns the share of obligors whose grade differs between at least two seeds, in [0, 1].
- Invariants: Grades are the bins of edges; an obligor counts once; one seed returns 0.
- Check: Identical seeds give 0; a hand-computed 4-obligor table is exact.

### `riskvalidation.ml.seeds.attribution_rank_stability`

```python
def attribution_rank_stability(attributions_by_seed: numpy.ndarray) -> RankStability
```

- Units: attributions_by_seed shape (n_seeds, p) mean absolute attribution per feature; returns the mean and minimum pairwise Kendall tau of the feature ranks, in [-1, 1].
- Invariants: Pairwise over seeds; ties handled by scipy.stats.kendalltau tau-b; at least two seeds.
- Check: Identical rows give tau 1 (identity); the reference is scipy.stats.kendalltau.

### `riskvalidation.ml.seeds.RankStability`

```python
@dataclass(frozen=True)
class RankStability: mean_tau: float; min_tau: float
```

- Units: Kendall tau, dimensionless, in [-1, 1].
- Invariants: Frozen; min_tau <= mean_tau.
- Check: Constructed only by attribution_rank_stability.

## Module `riskvalidation/ml/explanations.py`

### `riskvalidation.ml.explanations.reason_code_overlap`

```python
def reason_code_overlap(attributions_by_refit: numpy.ndarray, top_k: int = 4) -> OverlapResult
```

- Units: attributions_by_refit shape (n_refits, n, p) per-obligor attributions (the pipeline computes them with the pinned shap); returns the mean and 5th percentile over obligors of the share of the top_k reasons kept between each refit and the first (04 J.2 l.881-883; ladder P4 l.968).
- Invariants: top_k is 4 by default and a named parameter of the case; the share is in [0, 1]; identical refits give 1.
- Check: Identity: identical refits give mean 1.0; a planted permutation of columns gives the hand-computed share.

### `riskvalidation.ml.explanations.OverlapResult`

```python
@dataclass(frozen=True)
class OverlapResult: top_k: int; n_refits: int; mean: float; p05: float
```

- Units: Shares in [0, 1].
- Invariants: Frozen; p05 <= mean.
- Check: Constructed only by reason_code_overlap.

### `riskvalidation.ml.explanations.rank_agreement`

```python
def rank_agreement(attribution_importance: numpy.ndarray, effect_range: numpy.ndarray) -> float
```

- Units: Both shape (p,); mean absolute SHAP per feature against the range of its ALE or PDP curve; returns Spearman rho in [-1, 1] (06 C.7 l.1006-1008).
- Invariants: scipy.stats.spearmanr is the reference; constant input raises ValueError.
- Check: Equal vectors give 1.0; reversed give -1.0.

### `riskvalidation.ml.explanations.shapley_additivity_gap`

```python
def shapley_additivity_gap(prediction: numpy.ndarray, base_value: float, attributions: numpy.ndarray) -> float
```

- Units: prediction shape (n,) in the model's output units; attributions shape (n, p) in the same units; returns the maximum over rows of |f(x) - (phi_0 + sum phi_i)| (06 C.7 l.990).
- Invariants: Non-negative; exactly 0 when additivity holds.
- Check: Identity: attributions built as the exact Shapley values of a linear model give a gap below 1e-12.

### `riskvalidation.ml.explanations.sign_check`

```python
def sign_check(effect: numpy.ndarray, expected_sign: int) -> bool
```

- Units: effect shape (m,) ALE or PDP values along a feature grid; expected_sign in {-1, +1} from the stated economic rationale (I.1 l.1192; EBA recommendation 3, A.8 l.480-482).
- Invariants: True when the net change from the first to the last grid point has the expected sign and is nonzero.
- Check: A planted reversed effect returns False.

### `riskvalidation.ml.explanations.monotonicity_check`

```python
def monotonicity_check(effect: numpy.ndarray, expected_sign: int, tolerance: float) -> float
```

- Units: tolerance in the effect's units; returns the largest violation of the expected monotonicity (0 when monotone within tolerance).
- Invariants: Non-negative; 0 for a monotone curve.
- Check: Planted bump of known height returns that height.

## Module `riskvalidation/ml/effects.py`

### `riskvalidation.ml.effects.partial_dependence`

```python
def partial_dependence(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, feature: int, grid: numpy.ndarray) -> numpy.ndarray
```

- Units: X (n, p); grid shape (m,) in the feature's units; returns the average prediction at each grid value, shape (m,), in PD (Friedman 2001).
- Invariants: The other columns keep their observed values; output within the predictor's range.
- Check: On an additive model the curve is the component plus a constant (identity).

### `riskvalidation.ml.effects.ice_curves`

```python
def ice_curves(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, feature: int, grid: numpy.ndarray) -> numpy.ndarray
```

- Units: Same inputs; returns shape (n, m): one curve per row (Goldstein et al. 2015).
- Invariants: Row means equal partial_dependence.
- Check: Mean of the ICE curves equals partial_dependence exactly.

### `riskvalidation.ml.effects.accumulated_local_effects`

```python
def accumulated_local_effects(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, feature: int, n_bins: int) -> tuple[numpy.ndarray, numpy.ndarray]
```

- Units: Returns (bin edges shape (n_bins + 1,), effect shape (n_bins,)) in PD units; the Apley and Zhu estimator centred to mean zero (06 C.7 l.994-1003).
- Invariants: The effect is centred: its count-weighted mean is 0 within 1e-12; quantile bins hold at least one row.
- Check: Identity: on an additive model the centred ALE equals the centred component (C.7 l.1002).

## Module `riskvalidation/ml/generalisation.py`

### `riskvalidation.ml.generalisation.overfit_gap`

```python
def overfit_gap(metric_train: float, metric_test: float, tolerance: float, higher_is_better: bool = True) -> OverfitResult
```

- Units: Metrics in the same units (AUC points or Brier); tolerance in the same units (named parameter overfit_tolerance, a convention).
- Invariants: gap = metric_train - metric_test when higher is better, the reverse otherwise; flag when gap exceeds tolerance (06 C.7 l.1016-1018; I.1 l.1187; ECB 43(a)).
- Check: Boundary: gap equal to the tolerance is not flagged.

### `riskvalidation.ml.generalisation.OverfitResult`

```python
@dataclass(frozen=True)
class OverfitResult: gap: float; tolerance: float; flag: bool
```

- Units: Metric units.
- Invariants: Frozen; flag == (gap > tolerance).
- Check: Constructed only by overfit_gap.

### `riskvalidation.ml.generalisation.weak_spots`

```python
def weak_spots(error: numpy.ndarray, bins: numpy.ndarray, k: float, min_n: int = 30) -> list[WeakSpot]
```

- Units: error shape (n,) per-row loss (Brier terms); bins integer slice label per row; k the weak-spot multiple (a convention); returns the slices whose mean error exceeds k times the overall mean and hold at least min_n rows.
- Invariants: Slices below min_n are never reported (missing-data rule); sorted by decreasing ratio.
- Check: A planted slice with error 3x the rest is returned for k = 2 and absent for k = 4.

### `riskvalidation.ml.generalisation.WeakSpot`

```python
@dataclass(frozen=True)
class WeakSpot: label: int; n: int; mean_error: float; ratio: float
```

- Units: ratio dimensionless.
- Invariants: Frozen; ratio > k.
- Check: Constructed only by weak_spots.

## Module `riskvalidation/ml/conformal.py`

### `riskvalidation.ml.conformal.split_conformal_quantile`

```python
def split_conformal_quantile(scores: numpy.ndarray, alpha: float) -> float
```

- Units: scores shape (n,) nonconformity scores on n calibration points; alpha in (0, 1); returns the quantile of order ceil((n + 1)(1 - alpha)) / n (06 C.7 l.1019-1028).
- Invariants: Order above 1 returns +inf (the set is the whole label space); monotone in alpha.
- Check: Independent reference: MAPIE split conformal (optional extra) and numpy.quantile with method 'higher'.

### `riskvalidation.ml.conformal.conformal_sets`

```python
def conformal_sets(p1: numpy.ndarray, qhat: float) -> numpy.ndarray
```

- Units: p1 shape (n,) predicted PD; returns a boolean array (n, 2): labels {0, 1} whose score 1 - p(label) is at most qhat.
- Invariants: A set may be empty or both labels.
- Check: qhat = +inf gives both labels everywhere.

### `riskvalidation.ml.conformal.conformal_coverage`

```python
def conformal_coverage(sets: numpy.ndarray, y: numpy.ndarray, alpha: float) -> CoverageResult
```

- Units: sets (n, 2) boolean; y shape (n,); returns the empirical coverage in [0, 1] and the two-sided binomial test p-value of the coverage indicators against 1 - alpha.
- Invariants: A coverage loss is read as an exchangeability violation, never as proof; the p-value comes from scipy.stats.binomtest.
- Check: Size under exchangeability about alpha_test; power against the planted exchangeability break (plants).

### `riskvalidation.ml.conformal.CoverageResult`

```python
@dataclass(frozen=True)
class CoverageResult: n: int; coverage: float; target: float; p_value: float
```

- Units: Shares in [0, 1].
- Invariants: Frozen.
- Check: Constructed only by conformal_coverage.

## Module `riskvalidation/ml/leakage.py`

### `riskvalidation.ml.leakage.temporal_order_violations`

```python
def temporal_order_violations(feature_dates: numpy.ndarray, observation_date: numpy.ndarray) -> int
```

- Units: Both datetime64[D] arrays, shapes (n, p) and (n,); returns the number of feature values dated after the observation date (06 C.7 l.1048-1051).
- Invariants: Non-negative; NaT is never a violation.
- Check: A planted future-dated cell is counted.

### `riskvalidation.ml.leakage.single_feature_auc`

```python
def single_feature_auc(X: numpy.ndarray, y: numpy.ndarray, threshold: float = 0.95) -> SingleFeatureAuc
```

- Units: Returns the largest max(AUC, 1 - AUC) over columns, its column and whether it exceeds the near-perfect threshold (a convention); uses disc_auc.
- Invariants: Value in [0.5, 1].
- Check: A planted leaking column is the suspect.

### `riskvalidation.ml.leakage.SingleFeatureAuc`

```python
@dataclass(frozen=True)
class SingleFeatureAuc: max_auc: float; feature: int; suspect: bool
```

- Units: AUC in [0.5, 1]; feature a column index.
- Invariants: Frozen; suspect == (max_auc > threshold used).
- Check: Constructed only by single_feature_auc.

### `riskvalidation.ml.leakage.entity_overlap`

```python
def entity_overlap(train_ids: Sequence[str], test_ids: Sequence[str]) -> float
```

- Units: Returns the share of test entities present in training, in [0, 1].
- Invariants: Identifiers compared as strings; empty test set raises ValueError.
- Check: Disjoint sets give 0; equal sets give 1.

### `riskvalidation.ml.leakage.resemblance_auc`

```python
def resemblance_auc(X_dev: numpy.ndarray, X_oot: numpy.ndarray, seed: int) -> AucResult
```

- Units: Cross-fitted AUC of a classifier separating development from out-of-time rows, with its variance (auc_with_variance).
- Invariants: Near 0.5 when the samples agree.
- Check: Identical samples give an AUC within 2 standard errors of 0.5.

### `riskvalidation.ml.leakage.AucResult`

```python
@dataclass(frozen=True)
class AucResult: auc: float; variance: float; n: int
```

- Units: AUC in [0, 1].
- Invariants: Frozen; variance >= 0.
- Check: Constructed only by resemblance_auc.

## Module `riskvalidation/ml/dataquality.py`

### `riskvalidation.ml.dataquality.dq_completeness`

```python
def dq_completeness(X: numpy.ndarray) -> DataQualityCount
```

- Units: Share of non-NaN cells in [0, 1] and the counts per column (06 C.7 l.1045-1047; ECB 52(h)(vii)).
- Invariants: Counted checks feeding a TestResult; maps to SGCD shock F1.
- Check: Planted NaN cells are counted exactly.

### `riskvalidation.ml.dataquality.dq_validity`

```python
def dq_validity(X: numpy.ndarray, lo: numpy.ndarray, hi: numpy.ndarray) -> DataQualityCount
```

- Units: lo and hi shape (p,) in feature units; counts cells outside [lo, hi].
- Invariants: NaN is not a validity violation.
- Check: Planted out-of-range cells are counted.

### `riskvalidation.ml.dataquality.dq_uniqueness`

```python
def dq_uniqueness(ids: Sequence[str]) -> DataQualityCount
```

- Units: Counts duplicate identifiers.
- Invariants: First occurrence is kept.
- Check: Hand-computed duplicates.

### `riskvalidation.ml.dataquality.dq_consistency`

```python
def dq_consistency(a: Sequence[object], b: Sequence[object]) -> DataQualityCount
```

- Units: Counts rows where two views of the same field disagree (SGCD F4 reading both views).
- Invariants: Equal-length sequences.
- Check: Planted disagreements are counted.

### `riskvalidation.ml.dataquality.dq_timeliness`

```python
def dq_timeliness(dates: Sequence[str], as_of: str, max_age_days: int) -> DataQualityCount
```

- Units: Counts rows older than max_age_days at as_of (ISO dates).
- Invariants: max_age_days >= 0.
- Check: Planted stale rows are counted.

### `riskvalidation.ml.dataquality.dq_label_consistency`

```python
def dq_label_consistency(X: numpy.ndarray, y: numpy.ndarray) -> DataQualityCount
```

- Units: Counts identical feature rows with different labels.
- Invariants: Exact-equality rows only.
- Check: Planted contradictory pair is counted.

### `riskvalidation.ml.dataquality.DataQualityCount`

```python
@dataclass(frozen=True)
class DataQualityCount: check: str; n_checked: int; n_failed: int; share_ok: float
```

- Units: Counts and a share in [0, 1].
- Invariants: Frozen; share_ok == 1 - n_failed / n_checked.
- Check: Constructed only by the dq_ functions.

## Module `riskvalidation/ml/cbpe.py`

### `riskvalidation.ml.cbpe.cbpe_confusion`

```python
def cbpe_confusion(p: numpy.ndarray, threshold: float) -> CbpeConfusion
```

- Units: p shape (n,) calibrated PD; returns the expected true positives, false positives, true negatives and false negatives, summed over observations, with P(yhat = y)_j = 1 - |yhat_j - p_j| (06 C.7 l.1052-1058).
- Invariants: Four counts sum to n.
- Check: Hand-computed rows (C.7 l.1054).

### `riskvalidation.ml.cbpe.CbpeConfusion`

```python
@dataclass(frozen=True)
class CbpeConfusion: tp: float; fp: float; tn: float; fn: float
```

- Units: Expected counts.
- Invariants: Frozen; sum == n.
- Check: Constructed only by cbpe_confusion.

### `riskvalidation.ml.cbpe.cbpe_auc`

```python
def cbpe_auc(p: numpy.ndarray, n_thresholds: int = 101) -> CbpeAuc
```

- Units: Returns the AUC estimated over thresholds and the four assumptions as a tuple of ids (calibrated-probabilities, no-concept-drift, no-extrapolation, adequate-sample).
- Invariants: Always flagged as an estimate; no label is read.
- Check: A perfectly calibrated simulated sample matches the labelled AUC within Monte Carlo error.

### `riskvalidation.ml.cbpe.CbpeAuc`

```python
@dataclass(frozen=True)
class CbpeAuc: estimated_auc: float; label: str; assumptions: tuple[str, ...]
```

- Units: AUC in [0, 1]; label == 'estimate'.
- Invariants: Frozen; four assumptions.
- Check: Constructed only by cbpe_auc.

## Module `riskvalidation/ml/challenger.py`

### `riskvalidation.ml.challenger.paired_brier_bootstrap`

```python
def paired_brier_bootstrap(p_champion: numpy.ndarray, p_challenger: numpy.ndarray, y: numpy.ndarray, n_boot: int, seed: int) -> PairedBrier
```

- Units: Both PD arrays shape (n,); resamples obligors jointly (the existing bootstrap_ci cannot resample two forecasts jointly); returns the Brier difference (challenger minus champion) with a 95 percent percentile interval (06 C.7 l.1041-1044; SS1/23 3.3(b)(iii); ECB 60).
- Invariants: Deterministic for a seed; the interval contains the point estimate for n_boot >= 200.
- Check: Identical forecasts give a zero difference and a zero-width interval.

### `riskvalidation.ml.challenger.PairedBrier`

```python
@dataclass(frozen=True)
class PairedBrier: diff: float; lo: float; hi: float; n_boot: int
```

- Units: Brier units.
- Invariants: Frozen; lo <= hi.
- Check: Constructed only by paired_brier_bootstrap.

### `riskvalidation.ml.challenger.grade_disagreement`

```python
def grade_disagreement(pd_a: numpy.ndarray, pd_b: numpy.ndarray, edges: numpy.ndarray, notches: int = 2) -> float
```

- Units: Share of obligors whose grades differ by at least `notches`, in [0, 1].
- Invariants: Symmetric in a and b.
- Check: Hand-computed 5-obligor table.

## Module `riskvalidation/ml/plants.py`

### `riskvalidation.ml.plants.LeakPlant`

```python
class LeakPlant(GeneratorBase): def __init__(self, n: int, leak_strength: float, seed: int)
```

- Units: Features (n, p) plus a leaking column; leak_strength a signal-to-noise ratio.
- Invariants: Subclass of generators.GeneratorBase built on LogisticPortfolio; truth() names the leaking column; verify() recomputes it.
- Check: Single-feature AUC of the leak rises with leak_strength; verify() passes.

### `riskvalidation.ml.plants.CovariateShiftPlant`

```python
class CovariateShiftPlant(GeneratorBase): def __init__(self, n: int, shift: float, features: Sequence[int], seed: int)
```

- Units: shift in standard deviations on the feature subset.
- Invariants: truth() lists the shifted features and size; shift 0 is the null.
- Check: Size at shift 0 and power at the planted shift by the harness (at least 4,000 repetitions).

### `riskvalidation.ml.plants.NoiseSensitivityPlant`

```python
class NoiseSensitivityPlant(GeneratorBase): def __init__(self, n: int, sensitivity: float, seed: int)
```

- Units: sensitivity the AUC loss per unit eps.
- Invariants: truth() gives the true degradation curve.
- Check: Recovered curve within Monte Carlo error.

### `riskvalidation.ml.plants.SeedUnstablePlant`

```python
class SeedUnstablePlant(GeneratorBase): def __init__(self, n: int, instability: float, seed: int)
```

- Units: instability the standard deviation of the injected seed effect on the score.
- Invariants: truth() gives the true standard deviation across seeds.
- Check: Measured dispersion within Monte Carlo error of truth().

### `riskvalidation.ml.plants.ExchangeabilityBreakPlant`

```python
class ExchangeabilityBreakPlant(GeneratorBase): def __init__(self, n: int, drift: float, seed: int)
```

- Units: drift the label-rate change after the calibration window.
- Invariants: truth() gives the true coverage loss; drift 0 is the null.
- Check: Size of the coverage test at drift 0 and its power at the planted drift.

## Module `riskvalidation/validation/ml.py`

### `riskvalidation.validation.ml.robustness`

```python
def robustness(model_id: str, curve: RobustnessCurve, tolerance: float, preset_eps: float, policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.robustness"
- Light: green when the AUC degradation at the preset scale is within the tolerance (a convention), red when it exceeds it, amber between the tolerance and twice the tolerance; thresholds in extras['thresholds'].
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.shift_resilience`

```python
def shift_resilience(model_id: str, result: SubsampleResult, policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.shift_resilience"
- Light: amber or red by the drop of AUC on the worst subsample against the full sample, thresholds from the policy version (conventions).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.seed_stability`

```python
def seed_stability(model_id: str, dispersion: SeedDispersion, policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.seed_stability"
- Light: amber or red by the standard deviation of the AUC across seeds against the policy thresholds (conventions).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.reason_code_stability`

```python
def reason_code_stability(model_id: str, overlap: OverlapResult, policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.reason_code_stability"
- Light: amber or red by the mean top-four overlap against the policy thresholds (conventions).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.effect_agreement`

```python
def effect_agreement(model_id: str, rho: float, n_features: int, policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.effect_agreement"
- Light: amber or red by the rank correlation against the policy thresholds (conventions).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.additivity`

```python
def additivity(model_id: str, gap: float, tolerance: float = 1e-9) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.additivity"
- Light: red when the Shapley additivity gap exceeds the numeric tolerance, green otherwise.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.overfit`

```python
def overfit(model_id: str, result: OverfitResult) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.overfit"
- Light: red when the gap exceeds overfit_tolerance, green otherwise (a convention, never regulatory).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.weak_spot`

```python
def weak_spot(model_id: str, spots: Sequence[WeakSpot], k: float, n_slices: int) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.weak_spot"
- Light: amber when at least one slice exceeds k times the average error, green otherwise.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.conformal_coverage`

```python
def conformal_coverage(model_id: str, result: CoverageResult, policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.conformal_coverage"
- Light: by the binomial p-value of the coverage against 1 - alpha with alpha_amber and alpha_red.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.leakage_screen`

```python
def leakage_screen(model_id: str, temporal: int, single: SingleFeatureAuc, overlap: float, resemblance: AucResult, policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.leakage_screen"
- Light: red when any of the four screens trips (a future-dated feature, a near-perfect single feature, entity overlap above zero, a resemblance AUC beyond the policy), green otherwise.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.data_quality`

```python
def data_quality(model_id: str, counts: Sequence[DataQualityCount], policy: MlPolicy = DEFAULT_POLICY) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.data_quality"
- Light: amber or red by the share of failed checks against the policy thresholds (conventions).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.cbpe_estimate`

```python
def cbpe_estimate(model_id: str, estimate: CbpeAuc, labels_supplied: bool = False) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.cbpe_estimate"
- Light: not_evaluated when a label is supplied; otherwise an estimate row, never green or red evidence.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

### `riskvalidation.validation.ml.challenger_brier`

```python
def challenger_brier(model_id: str, result: PairedBrier) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.challenger_brier"
- Light: by the paired Brier interval: amber when it excludes zero in the champion's favour, green when it does not.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none).

## UNVERIFIED and open items

- The values of the named parameters (grid, tolerance, seeds, refits, overfit tolerance, weak-spot multiple, shift score, worst share, cut-off) are proposed by U14-S and approved by the main session; the engine takes them as arguments.
- The dossiers print no worked example with numbers for these tests: no golden value is claimed (sizing, Modules and functions).
- MAPIE and fairlearn are optional reconciliation extras (decision Q11), never imported by the engine core.
