# Engine ML validation API contract: `engine-ml-api` 2.0.1

Owner: U14-S (unit sizing `plans/contraste/units/U14-sizing.md`, CAOS_MANAGE). Implemented by U14-E1 in `riskvalidation.ml` and `riskvalidation.validation.ml` (repository CAOS_RiskValidation); called by the C02 and C20 bakes (U14-P1, U14-P2). The tests of every function are written by U14-E1 against this file: a function exists with exactly the signature below, and each identity, independent reference or planted-defect check is a test. Changing a signature or a unit is a breaking change (a new major version of this contract). Sources: dossier 06 (`wip/contraste/06-model-risk-management-and-validation-2026-10-04.md`, C.7 l.979-1058, I.1 l.1184-1200, I.6), dossier 04 (J.2 l.881-883, ladder P4 l.968), dossier 07 (D patterns 3 and 6) and the product SDD Method ladder. The case documents this contract feeds are `c02-outputs`, `c02-models`, `c20-outputs`, `c20-outputs-shift`, `c20-outputs-seeds`, `c20-outputs-perturbation`, `c20-outputs-leakage` and `c20-models` (`docs/contracts/schemas/c02/`, `c20/`). The engine computes; it states no compliance claim. The drift tests are the existing `validation/stability.py` (PSI, CSI, chi-square, KS, Wasserstein), reused unchanged. This version states what the engine implements at f89adac (branch `task/0-08-000-batch3`; `task/u14-ml` at 626c859 carries the same ml code and differs only in the version strings). Code references such as `ml/robustness.py:25-47` are paths under `src/riskvalidation/` of that engine; `review` is `wip/contraste/review-u14-e1-2026-10-19.md`, `fix report` is `wip/contraste/u14-e1-fixes-2026-10-19.md` and G1 to G6 and G18 are the decisions of `plans/contraste/units/U14-sizing.md` (all in CAOS_MANAGE); every clause amended in 2.0.0 names its source in an 'Amended in 2.0.0' line.

Version history: 1.0.0, the first contract; 2.0.0 after the U14-E1 review and its two fix rounds (decisions G1 to G6 and G18): the Beta-Binomial conformal null with `n_cal` (G1, review M-2), the CBPE row always `not_evaluated` (G2, review M-4), signed reason codes (G3, review Q3), the shift resilience test read against a reference (G4, review M-3) and then against the development-only reference that replaced the pooled permutation reference (G18), the 14 `ml.` rows in the packaged default policy (G5, review M-1), the 12-decimal rounding of the strict boundaries (review m3), `RIDGE` and `FOLDS` as conventions (review m4) and the text fixes F1, F2, m5 to m7 and deviations 3, 5 and 9 (G6). 2.0.0 (the 1.1.0 of G6 is breaking by this contract's rule, decision G18): `conformal_coverage` takes `n_cal`, `shift_resilience` takes its reference and the development-only `shift_development_reference` is new; the 1.1.0 was never published. 2.0.1, a patch at the 0.13.000 release: the engine-repository files this page cites are named as `CAOS_RiskValidation/<path>`; no clause changes.

## Conventions (all functions)

- Arrays are `numpy.ndarray` of `float64` (integers `int64`, flags `bool`). Shapes: `n` rows, `p` features, `q` protected indicators.
- Every function is pure and deterministic (no hidden state, no I/O, inputs never mutated); randomness takes a `seed` and uses `numpy.random.default_rng(seed)`. Dataclasses are frozen. The engine imports no learning library: a model enters as a callable on arrays, and the pipeline computes attributions with the pinned `shap`.
- A function that cannot compute because data is missing raises `ValueError` with the reason, or (a validation function) returns the `not_evaluated` light with its reason in `notes`; it never returns a placeholder number.
- A validation function returns one `TestResult` of `riskvalidation`, serialised by `TestResult.to_dict()` into a row that validates against `common/test-result` (`docs/contracts/schemas/common/test-result.schema.json`). Test ids are prefixed `ml.`.
- Tolerances, grids, counts and cut-offs are conventions, never regulatory thresholds (06 I.6 l.1268-1270); the named parameters of the case documents are listed in the case schemas, the light cut points in Policy thresholds and the other values in Conventions table.
- Boundary rule of the lights: see Policy thresholds. `Threshold.classify` is inclusive; a tolerance stated as 'exceeds' is stored one float above, so the light and the strict boolean (`robustness_finding`, `overfit_gap`) agree at the boundary. The strict boundaries are decided on a value rounded to 12 decimals (`overfit_gap`, `robustness_finding`, `validation.ml.robustness`, `validation.ml.overfit`), so a gap that is the tolerance in decimals stays in the better colour: 0.80 - 0.75 is 0.050000000000000044 in floats and 0.85 - 0.80 is 0.04999999999999993, and both are 0.05 and green (amended in 2.0.0; source: review m3, decision G6, fix report D3, `ml/generalisation.py:28-39`, `ml/robustness.py:105-115`, `validation/ml.py:137` and `:469-490`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:256-272`).
- No golden value is claimed where the dossiers print none: each check is an identity, an independent reference or a size and power run on a planted defect.

## Module `riskvalidation/ml/robustness.py`

### `riskvalidation.ml.robustness.perturb_features`

```python
def perturb_features(X: numpy.ndarray, eps: float, seed: int, sd: numpy.ndarray | None = None) -> numpy.ndarray
```

- Units: X shape (n, p) float64 features; eps a multiple of each feature's standard deviation (dimensionless); sd shape (p,) in feature units, default the column standard deviation of X; returns shape (n, p).
- Invariants: Pure; the same seed gives the same array; eps = 0 returns X unchanged; the noise of column j is Gaussian with standard deviation eps * sd[j]; applied to the evaluation features only, never to the training slice (06 C.7 l.1009-1012).
- Amended in 2.0.0: the noise is a function of the seed alone, so the same seed gives the same standard normal draws at every eps and the perturbed samples of a grid are nested; the default sd is the column standard deviation with ddof 1 and needs at least two rows; sd must have shape (p,) and be nonnegative, else ValueError. Source: `ml/robustness.py:25-47`. Untested: no test pins the nesting of the draws.
- Check: eps = 0 identity; the sample standard deviation of the noise is eps * sd[j] within 4 Monte Carlo standard errors on 100,000 rows.

### `riskvalidation.ml.robustness.robustness_curve`

```python
def robustness_curve(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, y: numpy.ndarray, grid: Sequence[float], seed: int) -> RobustnessCurve
```

- Units: predict maps (n, p) to PD of shape (n,) in (0, 1); y int {0, 1} shape (n,); grid noise scales (multiples of sd); returns AUC and Brier per scale (both in [0, 1]) and the AUC delta against scale 0.
- Invariants: The first point is scale 0; deltas are metric(eps) - metric(0); the model enters only as a callable (the engine imports no learning library); both classes must be present.
- Amended in 2.0.0: scale 0 is prepended when `grid` lacks it and a 0 inside `grid` is not repeated; the grid must be nonnegative; `predict` must return finite probabilities of shape (n,), else ValueError. Source: `ml/robustness.py:78-102`, `CAOS_RiskValidation/tests/ml/test_ml_robustness.py:102`.
- Check: A constant predictor has AUC 0.5 at every scale; a predictor ignoring the noisy column has a zero delta (identity).

### `riskvalidation.ml.robustness.RobustnessCurve`

```python
@dataclass(frozen=True)
class RobustnessCurve: grid: tuple[float, ...]; auc: tuple[float, ...]; brier: tuple[float, ...]; auc_delta: tuple[float, ...]
```

- Units: Tuples of equal length; auc and brier in [0, 1]; auc_delta in [-1, 1].
- Invariants: Frozen; equal lengths; grid[0] == 0.0.
- Amended in 2.0.0: `__post_init__` raises ValueError when the tuples are empty or of different lengths, when grid[0] is not 0.0, or when auc or brier leave [0, 1] or auc_delta leaves [-1, 1]; a NaN metric is carried, never replaced. Source: `ml/robustness.py:50-71`, `CAOS_RiskValidation/tests/ml/test_ml_robustness.py:122`.
- Check: Constructed only by robustness_curve; length equality asserted in the test.

### `riskvalidation.ml.robustness.robustness_finding`

```python
def robustness_finding(curve: RobustnessCurve, tolerance: float, preset_eps: float) -> bool
```

- Units: tolerance in AUC points (decimal); preset_eps a multiple of sd that must be a grid point.
- Invariants: True exactly when -auc_delta at preset_eps, rounded to 12 decimals, exceeds tolerance; raises ValueError when preset_eps is not on the grid (matched within 1e-12) or the tolerance is negative (06 C.7 l.1009-1012).
- Amended in 2.0.0: the 12-decimal rounding. Source: review m3, decision G6, `ml/robustness.py:105-115`.
- Check: Boundary: a delta equal to the tolerance is not a finding; a loss of exactly 0.02 computed as 0.80 - 0.78, 0.85 - 0.83 or 0.90 - 0.88 is not a finding at tolerance 0.02 (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:256-272`).

### `riskvalidation.ml.robustness.shift_score_rank`

```python
def shift_score_rank(X_dev: numpy.ndarray, X_eval: numpy.ndarray, seed: int) -> numpy.ndarray
```

- Units: Shapes (n_dev, p) and (n_eval, p); returns the shift score of each evaluation row in [0, 1], shape (n_eval,): the cross-fitted probability a resemblance classifier gives to 'evaluation'.
- Invariants: Deterministic for a seed; scores of two identical samples average near 0.5; the classifier is the engine core's ridge-penalised logistic fit (NumPy and SciPy only), not a pipeline classifier.
- Amended in 2.0.0: development rows are class 0 and evaluation rows class 1 with balanced weights n / (2 n_class); the probability of each row comes from folds that did not train on it; rows with an identical feature vector are never split across folds; the ridge strength `RIDGE` = 1 and the number of folds `FOLDS` = 5 are conventions (Conventions table); each sample needs at least `FOLDS` rows and both must have p columns, else ValueError. Source: review m4 and deviation 6, decision G6, `ml/robustness.py:118-130`, `ml/_logistic.py:14-15` and `:57-82`.
- Check: Identical samples give a mean score within 0.05 of 0.5; a planted covariate shift ranks the shifted rows above the rest (power).

### `riskvalidation.ml.robustness.worst_subsample_performance`

```python
def worst_subsample_performance(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, y: numpy.ndarray, score: numpy.ndarray, share: float) -> SubsampleResult
```

- Units: score shape (n,); share in (0, 1) (named parameter worst_subsample_share, a convention); returns AUC and Brier on the share of rows with the highest shift score.
- Invariants: The subsample holds ceil(share * n) rows; ties broken by row order; the full-sample metric is returned beside it (06 C.7 l.1013-1015).
- Amended in 2.0.0: the size is max(1, ceil(share * n)) with the ceiling taken on the exact decimal share (0.1 * 30 is 3.0000000000000004 in floats and gives 3 rows); share must lie in (0, 1]; ties by row order means a stable sort of the descending score; a subsample holding a single class has no AUC and raises `SingleClassSubsampleError` (a ValueError whose message advises raising share). Source: `ml/robustness.py:156-180`, `CAOS_RiskValidation/tests/ml/test_ml_robustness.py:178`, `:198`, `:217`.
- Check: share = 1 returns the full-sample metrics exactly.

### `riskvalidation.ml.robustness.SubsampleResult`

```python
@dataclass(frozen=True)
class SubsampleResult: n: int; auc: float; brier: float; auc_full: float; brier_full: float
```

- Units: n rows; metrics in [0, 1].
- Invariants: Frozen; n >= 1.
- Amended in 2.0.0: `__post_init__` raises ValueError when n is not an integer of at least 1 or a metric leaves [0, 1]. Source: `ml/robustness.py:137-153`.
- Check: Constructed only by worst_subsample_performance.

### `riskvalidation.ml.robustness.SingleClassSubsampleError`

```python
class SingleClassSubsampleError(ValueError): ...
```

- Units: Raised by worst_subsample_performance when the worst subsample holds a single class; a ValueError subclass, so a caller that catches ValueError still catches it.
- Invariants: The message names the subsample size and advises raising share; shift_development_reference catches it and counts the draw in `n_undefined`.
- Amended in 2.0.0: new name (G18 fix report D4). Source: `ml/robustness.py:133-134`, `:177-178`, `:259-261`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:287`.
- Check: The real function raises ValueError with 'single class' in the message (`CAOS_RiskValidation/tests/ml/test_ml_robustness.py:217`); that it is the subclass is exercised through the monkeypatched development reference test.

### `riskvalidation.ml.robustness.ShiftReference`

```python
@dataclass(frozen=True)
class ShiftReference: observed_drop: float; null_drops: tuple[float, ...]; p_value: float; n_permutations: int; share: float; labelled: bool; n_undefined: int = 0; enough_development: bool = True
```

- Units: observed_drop and null_drops in AUC points (auc_full minus auc of the worst subsample); p_value in [0, 1] or NaN; n_permutations the requested R; share the worst-subsample share; labelled whether development labels were given; n_undefined the draws left out for a single-class worst subsample; enough_development whether the development set holds at least twice the evaluation rows.
- Invariants: Frozen; no validation in the constructor; null_drops is empty and p_value NaN when the reference could not be built (no development labels, or enough_development false); otherwise p_value = (1 + #{null_drops >= observed_drop}) / (len(null_drops) + 1).
- Amended in 2.0.0: new type (decision G18; the pooled-permutation `shift_permutation_reference` of the first fix round never reached a release). Source: `ml/robustness.py:183-200`, fix report second round.
- Check: Built by shift_development_reference (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:157`); the light test builds it directly with chosen p-values (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:214`).

### `riskvalidation.ml.robustness.shift_development_reference`

```python
def shift_development_reference(predict: Callable[[numpy.ndarray], numpy.ndarray], X_dev: numpy.ndarray, y_dev: numpy.ndarray | None, X_eval: numpy.ndarray, y_eval: numpy.ndarray, score: numpy.ndarray, share: float, shift_permutations: int = 199, seed: int = 0) -> ShiftReference
```

- Units: X_dev (n_dev, p) and X_eval (n_eval, p) features; y_dev int {0, 1} of shape (n_dev,) or None; y_eval int {0, 1} of shape (n_eval,); score the output of shift_score_rank on the evaluation rows, shape (n_eval,); share the worst-subsample share of worst_subsample_performance; shift_permutations the number of draws R (a convention, default 199, an integer of at least 1); returns a ShiftReference.
- Invariants: The development-only reference for the drop auc_full - auc of worst_subsample_performance. R times, a random subset of the development rows of the evaluation size is drawn without replacement as the pseudo-evaluation set and the other development rows are the pseudo-development set; the shift score is refit as shift_score_rank does (cross-fitted, pseudo-development class 0, pseudo-evaluation class 1) and the drop is computed on the pseudo-evaluation rows at the same share. The null holds no evaluation row (the evaluation rows enter only through their count and the observed drop). A draw whose worst subsample holds a single class is left out and counted in n_undefined. p_value = (1 + #{null drops >= observed drop}) / (len(null_drops) + 1), NaN when no draw is defined. y_dev None returns no null drops, a NaN p_value and labelled false; fewer than twice as many development rows as evaluation rows returns no null drops, a NaN p_value and enough_development false; each sample needs at least `FOLDS` rows and p columns equal, else ValueError. Deterministic for a seed; pure; inputs never mutated.
- Amended in 2.0.0: new function. Under no shift the evaluation rows with the highest shift score are a region of the feature space on which the AUC is lower by range restriction, so the raw drop is positive under the null (review finding F4, M-3: size 0.1055); the pooled permutation reference of decision G4 had power 0.28 because the pooled rows contain the shifted rows; decision G18 replaced it by this reference. Source: decisions G4 and G18, review M-3, fix report second round, `ml/robustness.py:203-264`.
- Check: The formula (1 + #ge) / (R + 1), determinism, purity, the default R of 199, no development labels, development below twice the evaluation rows, a null that does not depend on the evaluation rows, and single-class draws left out and counted (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:157-212` and `:287`). Measured with development 2,000 rows, evaluation 1,000, R = 99 and share 0.25: shift 0: size 0.0418 (se 0.0032); [0.0359, 0.0484]: power a quarter of the rows shifted 3 sd on feature 0 (se 0.9720).

### `riskvalidation.ml.robustness.oot_window_performance`

```python
def oot_window_performance(predict: Callable[[numpy.ndarray], numpy.ndarray], X: numpy.ndarray, y: numpy.ndarray, window: numpy.ndarray) -> dict[str, float]
```

- Units: window integer label per row (shape (n,)); returns AUC per window label; windows with a single class are omitted and counted in the result key 'omitted'.
- Invariants: Keys are the window labels as strings; a window with fewer than two classes never gets a number (missing-data rule); the value of the key 'omitted' is the count of omitted windows as a float; window must be a one-dimensional integer array (`ml/robustness.py:267-286`).
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

- Units: attributions_by_refit shape (n_refits, n, p) per-obligor attributions on the log-odds of the event (the pipeline computes them with the pinned shap), n_refits at least 2, n at least 1, finite; a positive attribution pushes toward default; returns the mean and 5th percentile over obligors of the share of the top_k reasons kept between each refit after the first and the first refit (04 J.2 l.881-883; ladder P4 l.968).
- Invariants: top_k is 4 by default and a named parameter of the case, an integer in [1, p]; the share is in [0, 1]; identical refits give 1. The reasons of an obligor in a refit are its top_k largest signed contributions toward the event, in descending order, ties by column order; a large negative attribution is never a reason. The share of an obligor is averaged over the refits after the first, and the mean and the 5th percentile (numpy.percentile, linear interpolation) are then taken over obligors, not over (refit, obligor) pairs.
- Amended in 2.0.0: signed attribution replaces the absolute reading of 1.0.0 (decision G3; review Q3 and deviation 4; dossier 04 J.2 l.878-883: SHAP shortfalls play the role of Delta_j, Regulation B comment 9(b)(2)-5); the percentile is over obligors (review m7, decision G6). Source: `ml/explanations.py:40-63`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:114-139`.
- Check: Identity: identical refits give mean 1.0; a planted permutation of columns gives the hand-computed share. Golden: attribution rows (-9, 5, 4, 3, 2, 1) and (6, 5, 4, 3, 2, 1) give 0.75 (by absolute value the share would be 1); with top_k = 1, rows (-9, 0.5, 0.9, 0.3, 0.2, 0.1) and (9, 0.5, 0.9, 0.3, 0.2, 0.1) give 0.0; a row with only one large negative attribution compared with itself gives 1.0; ties are broken by column order (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:114-139`).

### `riskvalidation.ml.explanations.OverlapResult`

```python
@dataclass(frozen=True)
class OverlapResult: top_k: int; n_refits: int; mean: float; p05: float
```

- Units: Shares in [0, 1].
- Invariants: Frozen; top_k >= 1 and n_refits >= 2 and mean and p05 in [0, 1], else ValueError in the constructor; p05 is not forced below the mean.
- Amended in 2.0.0: the 1.0.0 invariant 'p05 <= mean' is removed because it is not a theorem of a share distribution: 96 obligors at 1 and 4 at 0 give a 5th percentile of 1.0 against a mean of 0.96 (review F1, deviation 8 F1 and m5; decision G6). Source: `ml/explanations.py:21-37`, `CAOS_RiskValidation/tests/ml/test_ml_seeds_explanations.py:146-155`.
- Check: Constructed only by reason_code_overlap.

### `riskvalidation.ml.explanations.rank_agreement`

```python
def rank_agreement(attribution_importance: numpy.ndarray, effect_range: numpy.ndarray) -> float
```

- Units: Both shape (p,), any two per-feature vectors: mean absolute SHAP per feature against the range of its ALE or PDP curve (the explainer agreement of C20, ml.effect_agreement, 06 C.7 l.1006-1008), or the mean absolute SHAP on the clean batches against the shocked batches (the shock row's attribution_rank_correlation); returns Spearman rho in [-1, 1].
- Invariants: scipy.stats.spearmanr is the reference; constant input raises ValueError (the case document then carries null and its reason). The engine computes the Pearson correlation of the average ranks as S_ab / sqrt(S_aa S_bb), clamped to [-1, 1], so equal vectors give exactly 1.0 and reversed ones exactly -1.0 (spearmanr returns 0.9999999999999999 for equal vectors); the shapes must be equal and there must be at least two features, else ValueError (`ml/explanations.py:66-83`).
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
- Amended in 2.0.0: the gap is rounded to 12 decimals before it is compared and returned; the tolerance must be nonnegative. Source: review m3 and minor m5, decision G6, `ml/generalisation.py:28-39`.
- Check: Boundary: gap equal to the tolerance is not flagged; overfit_gap(0.80, 0.75, 0.05) and overfit_gap(0.85, 0.80, 0.05) both have gap 0.05 and no flag, and overfit_gap(0.8501, 0.80, 0.05) is flagged (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:256-262`).

### `riskvalidation.ml.generalisation.OverfitResult`

```python
@dataclass(frozen=True)
class OverfitResult: gap: float; tolerance: float; flag: bool
```

- Units: Metric units.
- Invariants: Frozen; flag == (gap > tolerance), enforced by `__post_init__` (ValueError otherwise; `ml/generalisation.py:16-25`).
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

- Units: scores shape (n,) nonconformity scores on n calibration points; alpha in (0, 1); returns the k-th smallest score, k = ceil((n + 1)(1 - alpha)), with k computed on the exact decimal alpha (fractions.Fraction(str(alpha))) so that 101 * 0.9 cannot round the wrong way (06 C.7 l.1019-1028).
- Invariants: k above n returns +inf (the set is the whole label space); monotone in alpha; alpha must lie in (0, 1) and scores must be a finite vector, else ValueError (`ml/conformal.py:28-52`).
- Amended in 2.0.0: the golden text and the float-trap example are corrected. The 1.0.0 examples 101 * 0.9 and 20 * 0.95 do not misround in IEEE doubles (101 * 0.9 is 90.9 and 20 * 0.95 is 19.0; review F2); a pair that does is n = 149 and alpha = 0.18, where the exact decimal gives k = ceil(150 * 0.82) = 123 and the float product 150 * (1 - 0.18) ceils to 124. The 1.0.0 sentence 'the `higher` method returns 92.0' holds at the level k / n = 0.91, not at 0.9, where numpy returns 91.0 (review m6). Source: review D4 8 F2, m5 and m6, decision G6, `CAOS_RiskValidation/tests/ml/test_ml_conformal.py:21-33`.
- Check: Independent reference: numpy.sort(scores)[k - 1], equal to numpy.quantile(scores, k / n, method='inverted_cdf'); the `higher` method of numpy.quantile is NOT the reference: at the level k / n = 0.91 it returns the (k + 1)-th order statistic, 92.0. Golden: scores 1 to 100 and alpha 0.1 give k = 91 and the 91st smallest score, 91.0; n = 19 and alpha 0.05 give k = 19; n = 149 and alpha = 0.18 give k = 123 (scores 1 to 149 give 123.0); n = 5 and alpha = 0.1 give k = 6, above n, so +inf. MAPIE reconciliation (optional extra): the test fits MAPIE's split conformal on the same scores and alpha and compares its quantile with this function. This is no longer UNVERIFIED: the review read the installed MAPIE 1.5.0, `mapie/utils.py` `_compute_classification_quantile`, which calls np.quantile(scores, ((n + 1) * (1 - alpha)) / n) with the `higher` method, the k-th or (k + 1)-th order statistic; recorded as a finding (review D4 8 F3), the definition above unchanged (`CAOS_RiskValidation/tests/ml/test_ml_conformal.py:134`, run only when MAPIE is installed).

### `riskvalidation.ml.conformal.conformal_sets`

```python
def conformal_sets(p1: numpy.ndarray, qhat: float) -> numpy.ndarray
```

- Units: p1 shape (n,) predicted PD; returns a boolean array (n, 2): labels {0, 1} whose score 1 - p(label) is at most qhat.
- Invariants: A set may be empty or both labels; p1 must lie in [0, 1] and qhat must not be NaN, else ValueError; label 0 has score p1 and label 1 has score 1 - p1 (`ml/conformal.py:55-63`).
- Check: qhat = +inf gives both labels everywhere.

### `riskvalidation.ml.conformal.conformal_coverage`

```python
def conformal_coverage(sets: numpy.ndarray, y: numpy.ndarray, alpha: float, *, n_cal: int) -> CoverageResult
```

- Units: sets (n, 2) boolean and non-empty; y int {0, 1} shape (n,); alpha in (0, 1); n_cal (keyword-only) the number of calibration scores the quantile came from, an integer of at least 1; returns the empirical coverage c / m in [0, 1] (the share of rows whose set holds the true label), the target 1 - alpha, the two-sided Beta-Binomial p-value and the two-sided binomial p-value of the covered count c of the m rows.
- Invariants: With k = ceil((n_cal + 1)(1 - alpha)) on the exact decimal alpha, the coverage of a split conformal set given the calibration is Beta(k, n_cal + 1 - k) under exchangeability, so the covered count c of m test rows is Beta-Binomial(m, k, n_cal + 1 - k) (scipy.stats.betabinom). p_value is the sum of the probabilities of every count no more likely than c (the minimum-likelihood rule of scipy.stats.binomtest, with the relative tolerance 1 + 1e-7), clipped to [0, 1]; it is the value the light reads. p_value_binomial is the two-sided scipy.stats.binomtest of the covered count against 1 - alpha (06 C.7 l.1019-1028), reported beside it and never driving the light: it ignores the randomness of the calibration quantile and is oversized when m is not small against n_cal. When k > n_cal the set is every label, the coverage is 1 by construction and p_value is NaN. A coverage loss is read as an exchangeability violation, never as proof. n_cal omitted or passed positionally raises TypeError; n_cal below 1 or not an integer raises ValueError.
- Amended in 2.0.0: the Beta-Binomial null and the required keyword `n_cal` (decision G1; review Q1 and M-2; fix report D2 and D4). Source: `ml/conformal.py:82-116`.
- Check: Golden: m = 2,000, n_cal = 2,000, alpha 0.1 and 1,830 covered give k = 1801, a binomial p-value below 0.05 and a Beta-Binomial p-value above 0.05, equal within 1e-12 to the sum of betabinom probabilities not above that of the observed count (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:48-60`); 10 rows with 8 covered at alpha 0.1 and n_cal = 99 give k = 90 and p_value_binomial equal to binomtest(8, 10, 0.9, two-sided) (`CAOS_RiskValidation/tests/ml/test_ml_conformal.py:82-103`); all 10 rows covered at alpha 0.5 and n_cal = 19 give k = 10 and a two-sided binomial value above the 'greater' one (`CAOS_RiskValidation/tests/ml/test_ml_conformal.py:106-115`). Size under exchangeability and power against the planted exchangeability break: drift 0: size 0.0475 (se 0.0034); [0.0413, 0.0545]: power log-odds drift 0.5 (se 0.9995); drift 0: size 0.0493 (se 0.0034); [0.0429, 0.0563]: power log-odds drift 0.5 (se 0.9845); drift 0: size 0.0522 (se 0.0035); [0.0457, 0.0595]: power log-odds drift 0.5 (se 0.9545). Size of the binomial value at the same three split ratios, a one-off study and not a test: 0.062, 0.1625 and 0.380 (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`).

### `riskvalidation.ml.conformal.CoverageResult`

```python
@dataclass(frozen=True)
class CoverageResult: n: int; coverage: float; target: float; p_value: float; n_cal: int; k: int; p_value_binomial: float
```

- Units: Shares and p-values in [0, 1]; n the rows tested (m); n_cal the calibration size; k = ceil((n_cal + 1)(1 - alpha)).
- Invariants: Frozen; p_value is NaN when k > n_cal; p_value_binomial is the two-sided binomtest value.
- Amended in 2.0.0: new fields n_cal, k and p_value_binomial (decision G1; fix report D4). Source: `ml/conformal.py:66-79`.
- Check: Constructed only by conformal_coverage; the test compares a whole CoverageResult for equality (`CAOS_RiskValidation/tests/ml/test_ml_conformal.py:82-91`).

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

- Units: Returns the share of distinct test entities present in training, in [0, 1] (`ml/leakage.py:63-72`).
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

- Units: Share of non-NaN cells in [0, 1] and the counts per column (06 C.7 l.1045-1047; ECB 52(h)(vii)); returns a `CompletenessCount`, a subclass of DataQualityCount that also carries `by_column`, the NaN count of each column (amended in 2.0.0; source: review deviation 9, decision G6, `ml/dataquality.py:40-68`, `CAOS_RiskValidation/tests/ml/test_ml_leakage_dq.py:118`).
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
- Invariants: Frozen; share_ok == 1 - n_failed / n_checked (within 1e-15; ValueError otherwise, as for a blank check name, n_checked below 1 or n_failed outside [0, n_checked]; `ml/dataquality.py:20-37`).
- Check: Constructed only by the dq_ functions.

### `riskvalidation.ml.dataquality.CompletenessCount`

```python
@dataclass(frozen=True)
class CompletenessCount(DataQualityCount): by_column: tuple[int, ...] = ()
```

- Units: by_column the number of NaN cells of each column, in column order; the inherited fields count cells (n_checked = X.size).
- Invariants: Frozen; a DataQualityCount, so every consumer of DataQualityCount accepts it.
- Amended in 2.0.0: new name (review deviation 9, decision G6). Source: `ml/dataquality.py:40-45`, `:60-68`.
- Check: Constructed only by dq_completeness; planted NaN cells per column are (2, 0, 1) (`CAOS_RiskValidation/tests/ml/test_ml_leakage_dq.py:118`).

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

- Units: sensitivity is the standardised separation of the fragile column (the signal column is x_0 = sensitivity * y + N(0, 1), prevalence 0.3, plus a pure-noise column), not 'the AUC loss per unit eps'.
- Invariants: truth() gives the true degradation curve: the AUC at scale eps is Phi(sensitivity / sqrt(2 (1 + eps^2 (1 + sensitivity^2 pi (1 - pi))))) and its delta against scale 0; sensitivity 0 has no signal to lose (AUC 0.5 at every scale).
- Amended in 2.0.0: the unit of `sensitivity`. The AUC at scale eps has zero slope at eps 0 and no constant loss per unit eps, so the 1.0.0 unit cannot be a parameter of this construction; the loss per unit eps is an output of truth() (review deviation 5, decision G6; `ml/plants.py:219-272`).
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

## Module `riskvalidation/ml/policy.py`

The cut points of the `ml.` lights as entries of the engine's `Policy` (amended in 2.0.0: the module is public and is the source of the 14 rows in `policies/default.json`; source: decision G5, review M-1, fix report D3, `ml/policy.py`).

### `riskvalidation.ml.policy.strict`

```python
def strict(cut: float) -> float
```

- Units: cut in the metric's units; returns math.nextafter(float(cut), math.inf), the cut point of a rule stated as 'exceeds'.
- Invariants: Pure; a value equal to the cut stays in the better colour under the inclusive Threshold.classify, so the light and the strict boolean agree at the boundary.
- Check: The strict rows store the nextafter floats: `ml.robustness` amber is math.nextafter(0.02, math.inf) = 0.020000000000000004 (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:274-283`). Source: `ml/policy.py:41-43`.

### `riskvalidation.ml.policy.ml_thresholds`

```python
def ml_thresholds(perturbation_tolerance: float = 0.02, overfit_tolerance: float = 0.05, weak_spot_multiple: float = 2.0, additivity_tolerance: float = 1e-9) -> dict[str, Threshold]
```

- Units: The four named parameters of decision V6 in AUC points, AUC points, a multiple and prediction units; returns the 14 rows of Policy thresholds keyed by test id, each a `Threshold(kind, amber, red, source)`.
- Invariants: The keys are `ML_KEYS` in the order of the table; the other cut points are the contract's proposals for the main session's approval; every source text ends with the label suffix '(engine-ml-api 2.0.0, Policy thresholds)' preceded by 'convention' or 'rule, not a convention' (at f89adac the suffix still reads 1.1.0, at 626c859 it reads 2.0.0).
- Check: The 14 keys, kinds and cut points against the Policy thresholds table (`CAOS_RiskValidation/tests/ml/test_ml_validation.py:36`). Source: `ml/policy.py:46-152`.

### `riskvalidation.ml.policy.threshold_rows`

```python
def threshold_rows(**parameters: float) -> dict[str, dict[str, float | str]]
```

- Units: The keyword arguments are those of ml_thresholds; returns {key: {'kind', 'amber', 'red', 'source'}} for the 14 keys, amber and red as floats.
- Invariants: The form the integrator writes into `policies/default.json` as it stands; the strict rows hold their nextafter floats.
- Check: The keys equal `ML_KEYS` and each row equals the Threshold fields of ml_thresholds (`CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:274-284`). Source: decision G5, `ml/policy.py:155-162`.

### `riskvalidation.ml.policy.ml_policy`

```python
def ml_policy(base: Policy | None = None, **parameters: float) -> Policy
```

- Units: base a Policy (None means the packaged default policy); the keyword arguments are those of ml_thresholds; returns a Policy with the base's policy_id and version and a description that names the `ml.` rows.
- Invariants: A row the base does not hold is added; a row the base holds at its packaged default (the packaged policy carries the `ml.` rows, so a default row is no customisation) is replaced by the parameterised one; a row the base customised is kept as it stands. Every `validation.ml` function resolves `policy=None` through ml_policy().
- Amended in 2.0.0: the replacement of a default row (source: commit 84d2edc, `ml/policy.py:165-182`).
- Check: Only the missing keys of a base policy are filled, and a packaged-default row is replaced while a customised row is kept (`CAOS_RiskValidation/tests/ml/test_ml_validation.py:61` and `:409`).

## Module `riskvalidation/validation/ml.py`

### `riskvalidation.validation.ml.robustness`

```python
def robustness(model_id: str, curve: RobustnessCurve, tolerance: float, preset_eps: float, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.robustness"
- Light: green when the degradation is at most the tolerance, amber above the tolerance up to twice the tolerance, red above twice the tolerance; the degradation is -auc_delta at the preset scale and the tolerance is the named parameter perturbation_tolerance (a convention); thresholds in extras['thresholds'].
- Amended in 2.0.0: the degradation is rounded to 12 decimals before it is classified (a loss that is the tolerance in decimals stays green); `tolerance` must be the one the policy's cut points state (amber the nextafter of the tolerance, red the nextafter of twice it), else ValueError naming `ml_policy(tolerance=...)`; preset_eps must be a grid point (within 1e-12), else ValueError. Source: review m3 and deviation 7, decision G6, `validation/ml.py:102-111`, `:118-184`, `CAOS_RiskValidation/tests/ml/test_ml_validation.py:111-118`.
- Policy key: `ml.robustness` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): sensitivity 0.25: size 0.0278 (se 0.0026); [0.0230, 0.0333]: power sensitivity 2.5 (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.shift_resilience`

```python
def shift_resilience(model_id: str, result: SubsampleResult, reference: ShiftReference, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic = metric = the AUC of the full sample minus the AUC of the worst subsample (AUC points; negative when the worst subsample scores better), p_value = reference.p_value in [0, 1], alpha_amber 0.05 and alpha_red 0.01, n = result.n (the subsample rows).
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; `extras['thresholds']` holds the alpha cut points and extras carries auc_full, auc_worst, brier_full, brier_worst, shift_permutations, n_undefined and share, and, when evaluated, null_mean and null_p95 (the mean and the 95th percentile of the null drops). When the reference is labelled and reference.observed_drop differs from the drop of result by more than 1e-9 the function raises ValueError (build the reference from the same predict, rows, score and share). It returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null when the policy lacks the key, when the reference is labelled but the development set holds fewer than twice the evaluation rows, when there are no development labels, or when the drop or the p-value is not finite or the null drops are empty.
- Test id: test_id = "ml.shift_resilience"
- Light: by the permutation p-value of the drop against the development-only reference: red below alpha_red (0.01), amber below alpha_amber (0.05), green otherwise (a p-value of exactly 0.05 is green and of exactly 0.01 amber). The raw drop is not read against a cut point: under no shift it is positive by range restriction on the worst subsample (review finding F4, size 0.1055 of the 1.0.0 design).
- Amended in 2.0.0: the `reference` argument, the p_value kind and the development-only reference (decisions G4 and G18; review M-3 and Q4; fix report D2, D4 and second round). Source: `validation/ml.py:252-379`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:214-251`.
- Policy key: `ml.shift_resilience` (p_value); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): shift 0: size 0.0418 (se 0.0032); [0.0359, 0.0484]: power a quarter of the rows shifted 3 sd on feature 0 (se 0.9720). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`). Lights: p-values 0.5 and 0.05 green, 0.0499 and 0.01 amber, 0.0099 and 0.005 red.

### `riskvalidation.validation.ml.seed_stability`

```python
def seed_stability(model_id: str, dispersion: SeedDispersion, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.seed_stability"
- Light: by the standard deviation of the AUC across seeds: green below the amber cut point, amber from it, red from the red cut point (conventions).
- Policy key: `ml.seed_stability` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): instability 0.2: size 0.0000 (se 0.0000); [0.0000, 0.0009]: power instability 1.0 (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.reason_code_stability`

```python
def reason_code_stability(model_id: str, overlap: OverlapResult, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.reason_code_stability"
- Light: by the mean top-four overlap: green above the amber cut point, amber at or below it, red at or below the red cut point (conventions).
- Policy key: `ml.reason_code_stability` (lower_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): refit noise 0.1: size 0.0000 (se 0.0000); [0.0000, 0.0009]: power refit noise 1.5 (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.effect_agreement`

```python
def effect_agreement(model_id: str, rho: float, n_features: int, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.effect_agreement"
- Light: by the Spearman rank correlation of SHAP against ALE or PDP: green above the amber cut point, amber at or below it, red at or below the red cut point (conventions).
- Policy key: `ml.effect_agreement` (lower_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): effect range follows importance: size 0.0135 (se 0.0018); [0.0103, 0.0175]: power independent (se 0.9870). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.additivity`

```python
def additivity(model_id: str, gap: float, tolerance: float = 1e-9, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.additivity"
- Light: red when the Shapley additivity gap exceeds the numeric tolerance, green otherwise.
- Amended in 2.0.0: `tolerance` must be the one the policy's cut points state (the nextafter of the tolerance for amber and red), else ValueError; a gap that is not finite or negative is not evaluated (`validation/ml.py:445-466`, `CAOS_RiskValidation/tests/ml/test_ml_validation.py:204-235`). Source: review deviation 7 and m3, decision G6.
- Policy key: `ml.additivity` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): exact Shapley values: size 0.0000 (se 0.0000); [0.0000, 0.0009]: power first column off by 1e-6 (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.overfit`

```python
def overfit(model_id: str, result: OverfitResult, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.overfit"
- Light: red when the gap exceeds overfit_tolerance, green otherwise (a named parameter, a convention, never regulatory).
- Amended in 2.0.0: the gap is the 12-decimal value of overfit_gap and the result's tolerance must be the one the policy's cut points state, else ValueError (`validation/ml.py:469-490`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:256-272`). Source: review deviation 7 and m3, decision G6.
- Policy key: `ml.overfit` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): equal separation: size 0.0127 (se 0.0018); [0.0097, 0.0167]: power train separation 2, test 1 (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.weak_spot`

```python
def weak_spot(model_id: str, spots: Sequence[WeakSpot], k: float, n_slices: int, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.weak_spot"
- Light: amber when the worst slice's error exceeds k times the average error (k is the named parameter weak_spot_multiple), green otherwise; never red.
- Amended in 2.0.0: `k` must be the one the policy's cut points state (amber the nextafter of k, red the nextafter of 1e12), else ValueError; the metric is the worst ratio, 0.0 when no slice qualifies, and n is the number of slices examined (`validation/ml.py:492-525`). Source: review deviation 7 and m3, decision G6.
- Policy key: `ml.weak_spot` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): calibrated slices: size 0.0000 (se 0.0000); [0.0000, 0.0009]: power slice 0 predicts 1 - p (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.conformal_coverage`

```python
def conformal_coverage(model_id: str, result: CoverageResult, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: p_value = result.p_value (the Beta-Binomial value) in [0, 1], metric = the empirical coverage, statistic = coverage minus target, alpha_amber 0.05 and alpha_red 0.01, n = result.n.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; `extras['thresholds']` holds the alpha cut points and extras carries target, n_cal, k and p_value_binomial (the dossier's binomial value, beside the light's and never driving it); `policy_version` records target and n_cal. When k > n_cal the set is every label and the coverage is 1 by construction: the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null. The same light results when the policy lacks the key or the coverage or its p-value is not finite. A coverage loss is read as an exchangeability violation, never as proof.
- Test id: test_id = "ml.conformal_coverage"
- Light: by the Beta-Binomial p-value of the coverage against 1 - alpha given the calibration size: red below alpha_red, amber below alpha_amber, green otherwise.
- Amended in 2.0.0: the Beta-Binomial p-value drives the light, the binomial value moved to extras, and the statistic is coverage minus target (decision G1; review M-2 and minor m1 on the statistic sign; fix report D2). Source: `validation/ml.py:528-612`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:48-86`.
- Policy key: `ml.conformal_coverage` (p_value); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): drift 0: size 0.0475 (se 0.0034); [0.0413, 0.0545]: power log-odds drift 0.5 (se 0.9995); drift 0: size 0.0493 (se 0.0034); [0.0429, 0.0563]: power log-odds drift 0.5 (se 0.9845); drift 0: size 0.0522 (se 0.0035); [0.0457, 0.0595]: power log-odds drift 0.5 (se 0.9545). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.leakage_screen`

```python
def leakage_screen(model_id: str, temporal: int, single: SingleFeatureAuc, overlap: float, resemblance: AucResult, policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.leakage_screen"
- Light: the worst of the four screen lights: red when any screen trips (a future-dated feature, a near-perfect single feature, any entity overlap, a resemblance AUC beyond its limit), green otherwise.
- Amended in 2.0.0: statistic is the number of screens that tripped and n the rows of the resemblance sample; `extras['screens']` holds the key, value, light and cut points of each screen; the entity-overlap screen reads the indicator 1 when the overlap share is above 0 (the share sits in `extras['screens']['overlap']['share']`, the value is 0.0 or 1.0), so any overlap is red; the single-feature screen trips strictly above 0.95 and the resemblance screen strictly above 0.70; a missing policy key, a non-finite screen value or an overlap outside [0, 1] is not evaluated. Source: review deviation 3, decision G6, `validation/ml.py:615-713`.
- Policy key: `ml.leakage_screen.single_feature_auc` (upper_bad), `ml.leakage_screen.resemblance_auc` (upper_bad), `ml.leakage_screen.temporal_order` (upper_bad), `ml.leakage_screen.entity_overlap` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): leak strength 0: size 0.0000 (se 0.0000); [0.0000, 0.0009]: power leak strength 4 (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.data_quality`

```python
def data_quality(model_id: str, counts: Sequence[DataQualityCount], policy: Policy | None = None) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.data_quality"
- Light: by the largest share of failed checks: green below the amber cut point, amber from it, red from the red cut point (conventions).
- Policy key: `ml.data_quality` (upper_bad); the cut points are the rows of Policy thresholds, a `policy` argument of None means `ml_policy()` (the packaged default policy, which carries the `ml.` rows, completed for any `ml.` key it lacks by the rows of `riskvalidation/ml/policy.py`; amended in 2.0.0, source: `validation/ml.py:64-65`).
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): NaN rate 0.2 percent: size 0.0000 (se 0.0000); [0.0000, 0.0009]: power NaN rate 3 percent (se 1.0000). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

### `riskvalidation.validation.ml.cbpe_estimate`

```python
def cbpe_estimate(model_id: str, estimate: CbpeAuc, labels_supplied: bool = False) -> TestResult
```

- Units: A TestResult row validating against common/test-result: always the `not_evaluated` light, so statistic, p_value and metric are null once serialised; the estimated AUC, its label 'estimate' and the four assumptions are in `extras['estimate']` (keys estimated_auc, label, assumptions).
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled. The reason in `notes` is 'an estimate, not a test: CBPE estimates performance without labels (06 C.7 l.1052-1058)', followed by the four assumptions and 'it complements, never replaces, back-testing'; when a label is supplied it is 'a label is supplied: read the labelled AUC, an estimate is not evidence when labels exist'.
- Test id: test_id = "ml.cbpe_estimate"
- Light: always not_evaluated, so the row never moves `SuiteRun.worst()` (a battery of green rows plus this row is green); the estimate is never green, amber or red evidence.
- Amended in 2.0.0: the amber row of 1.0.0 became a `not_evaluated` row with the estimate in extras and no TestResult schema change (decision G2; review Q2 and M-4; fix report D3). Source: `validation/ml.py:769-800`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:89-111`.
- Policy: no policy threshold (row `ml.cbpe_estimate` of Policy thresholds states why); the rule above is the whole classification.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). The row is not a test, so its study is the bias of the estimate against the labelled AUC over 4,000 samples of 600 probabilities: unbiased within 0.01 when the probabilities are calibrated, more than 0.03 away when the labels follow p squared (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`).

### `riskvalidation.validation.ml.challenger_brier`

```python
def challenger_brier(model_id: str, result: PairedBrier) -> TestResult
```

- Units: A TestResult row validating against common/test-result: statistic, p_value in [0, 1] or null, metric, alphas decimals, n and n_events integers.
- Invariants: Pure and deterministic; ids are prefixed `ml.`; `reference`, `h0` and `alternative` are filled; the policy version records every tolerance as a parameter in `extras['thresholds']` (conventions, never regulatory); missing data returns the `not_evaluated` light with the reason in `notes` and statistic, p_value and metric all null.
- Test id: test_id = "ml.challenger_brier"
- Light: by the paired Brier interval: amber when it excludes zero in the champion's favour (the challenger's Brier is higher), green when it does not.
- Policy: no policy threshold (row `ml.challenger_brier` of Policy thresholds states why); the rule above is the whole classification.
- Check: The size under the null and the power against the planted defect at alpha 0.05, with Monte Carlo error, at no fewer than 4,000 repetitions (SDD l.335); no golden value is claimed (the dossiers print none). Measured (engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, 4,000 repetitions): equal noise: size 0.0302 (se 0.0027); [0.0254, 0.0360]: power challenger noise 0.15 above (se 0.9952). Design bounds: size at most 0.0569 (0.05 plus two Monte Carlo standard errors at 4,000 repetitions) and power at least POWER_MIN = 0.90, for every test, with no exception (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`).

## Policy thresholds

Lights come from the engine's `riskvalidation.core.policy.Policy`, a named, versioned set of `Threshold(kind, amber, red)` keyed by test id (`kind` is `p_value`, `upper_bad` or `lower_bad`; engine v0.07.000 `core/policy.py`). Every validation function below takes `policy: Policy | None = None`, where None means `ml_policy()` (the packaged default policy, completed for any `ml.` key it lacks) and classifies with `Policy.classify`. The packaged default policy `riskvalidation/policies/default.json` carries the 14 `ml.` rows below, each with its `source` text, as `riskvalidation.ml.policy.threshold_rows()` returns them at its defaults: 14 `ml.` keys among 43 thresholds, the policy label staying 2026.10.1 (decision G5; engine commit e20cbdf; the `fair.` keys are U14-E2's and the two key sets are disjoint). A policy that lacks a key returns the `not_evaluated` light, never a colour. The `ml_policy` rule: a row the base holds at its packaged default is replaced by the parameterised one, and a customised row is kept as it stands. `Threshold.classify` is inclusive at its cut points (`upper_bad`: amber when the metric is at or above `amber`, red at or above `red`; `lower_bad`: amber at or below `amber`, red at or below `red`; `p_value`: red below `red`, amber below `amber`, so a p-value at the cut is the better colour). A rule stated as 'exceeds' (a tolerance) keeps a value equal to the tolerance in the better colour: the engine stores `math.nextafter(cut, math.inf)` as the cut point of a row marked strict, so a delta equal to the tolerance is not a finding and is green; the table gives the stored floats. Each source text in the engine ends with the label suffix '(engine-ml-api 2.0.0, Policy thresholds)' (1.1.0 at f89adac, 2.0.0 at 626c859). The values are conventions, never regulatory thresholds (06 I.6 l.1268-1270): each is a named parameter for the main session's approval. Amended in 2.0.0; source: decision G5, review M-1, fix report D3, `ml/policy.py:46-182`, `CAOS_RiskValidation/tests/ml/test_ml_review_fixes.py:274-284`.

| key | kind | metric read | amber and red | boundary | basis | label |
|---|---|---|---|---|---|---|
| `ml.robustness` | upper_bad | AUC degradation at the preset scale, -auc_delta, rounded to 12 decimals (AUC points) | amber 0.02 (perturbation_tolerance), stored 0.020000000000000004; red 0.04 (twice it), stored 0.04000000000000001 | strict | the named parameter; twice it for red | convention |
| `ml.shift_resilience` | p_value | Monte Carlo p-value of the AUC drop on the worst subsample against the drops of random development subsets of the evaluation size (statistic: the drop, AUC points) | amber 0.05, red 0.01 | p_value rule (at the cut, the better colour) | Monte Carlo p-value of the AUC drop on the worst subsample by shift score against the drop of random development subsets of the evaluation size (06 C.7 l.1013-1015 gives the construction only): the engine default p-value cut points (alpha_amber 0.05, alpha_red 0.01) | convention |
| `ml.seed_stability` | upper_bad | standard deviation of the AUC across seeds (AUC points) | amber 0.01, red 0.02 | inclusive | proposed: about the sampling standard error of a Taiwan holdout AUC (0.008) | convention |
| `ml.reason_code_stability` | lower_bad | mean top-four reason overlap across refits (share) | amber 0.80, red 0.60 | inclusive | proposed: no dossier value (04 J.2 l.881-883) | convention |
| `ml.effect_agreement` | lower_bad | Spearman rho of mean absolute SHAP against the range of the ALE curve | amber 0.70, red 0.40 | inclusive | proposed: no dossier value (06 C.7 l.1006-1008) | convention |
| `ml.additivity` | upper_bad | maximum Shapley additivity gap (prediction units) | amber and red 1e-9 (the argument tolerance), stored 1.0000000000000003e-09 | strict | the numeric tolerance of the check (the argument tolerance) | convention |
| `ml.overfit` | upper_bad | train minus holdout AUC gap, rounded to 12 decimals (AUC points) | amber and red 0.05 (overfit_tolerance), stored 0.05000000000000001 | strict | the named parameter | convention |
| `ml.weak_spot` | upper_bad | error ratio of the worst slice to the average error (0 when no slice qualifies) | amber 2.0 (weak_spot_multiple), stored 2.0000000000000004; red 1e12, stored 1000000000000.0001 | strict | the named parameter; red 1e12 is a sentinel no ratio reaches, so never red | convention |
| `ml.conformal_coverage` | p_value | Beta-Binomial p-value of the coverage against 1 - alpha given the calibration size n_cal | amber 0.05 (alpha_amber), red 0.01 (alpha_red) | p_value rule (at the cut, the better colour) | the engine default p-value cut points (the binomial value of 1.0.0 is oversized when the test window is not small against the calibration window) | convention |
| `ml.leakage_screen.single_feature_auc` | upper_bad | largest single-feature max(AUC, 1 - AUC) | amber and red 0.95, stored 0.9500000000000001 | strict | near-perfect: the default of single_feature_auc, no dossier value | convention |
| `ml.leakage_screen.resemblance_auc` | upper_bad | cross-fitted AUC separating development from out-of-time rows | amber and red 0.70, stored 0.7000000000000001 | strict | proposed: the usual lower edge of acceptable discrimination, no dossier value | convention |
| `ml.leakage_screen.temporal_order` | upper_bad | number of feature values dated after the observation date | amber 1, red 1 | inclusive | rule, not a convention: a single future-dated value is a leak by definition (06 C.7 l.1048-1051) | rule, not a convention |
| `ml.leakage_screen.entity_overlap` | upper_bad | the indicator 1 when the share of test entities present in training is above 0, else 0 | amber 1, red 1 | inclusive | rule, not a convention: an entity in both slices is a leak by definition; the row reads the indicator and not the share (review deviation 3) | rule, not a convention |
| `ml.data_quality` | upper_bad | largest share of failed checks over the dq_ counts (1 - share_ok) | amber 0.01, red 0.05 | inclusive | proposed: no dossier value (06 C.7 l.1045-1047) | convention |
| `ml.cbpe_estimate` | none | the CBPE estimate row: always not_evaluated, never green, amber or red | none | not applicable | the estimate is not evidence and not a test (06 C.7 l.1052-1058; decision G2) | rule, not a convention |
| `ml.challenger_brier` | none | the 95 percent paired-bootstrap interval of the Brier difference | none | not applicable | the interval level 0.95 is a convention; no numeric cut point | convention |

The `source` texts of the rows as the engine returns them (the part before the label suffix), where the table above shortens them: `ml.robustness` 'AUC degradation at the preset scale: amber above perturbation_tolerance (0.02), red above twice it, a delta equal to the tolerance green'; `ml.seed_stability` 'standard deviation of the AUC across seeds: proposed, about the sampling standard error of a Taiwan holdout AUC (0.008)'; `ml.reason_code_stability` 'mean top-four reason overlap across refits: proposed, no dossier value (04 J.2 l.881-883)'; `ml.effect_agreement` 'Spearman rho of mean absolute SHAP against the range of the ALE curve: proposed, no dossier value (06 C.7 l.1006-1008)'; `ml.additivity` 'maximum Shapley additivity gap: red above the numeric tolerance (1e-09)'; `ml.overfit` 'train minus holdout AUC gap: red above overfit_tolerance (0.05)'; `ml.weak_spot` 'error ratio of the worst slice to the average error: amber above weak_spot_multiple (2.0); red 1e12 is a sentinel no ratio reaches, so never red'; `ml.conformal_coverage` 'Beta-Binomial p-value of the coverage against 1 - alpha given the calibration size: the engine default p-value cut points (alpha_amber 0.05, alpha_red 0.01)'; `ml.leakage_screen.single_feature_auc` 'largest single-feature max(AUC, 1 - AUC): near-perfect above 0.95, no dossier value'; `ml.leakage_screen.resemblance_auc` 'cross-fitted development against out-of-time AUC: proposed, no dossier value'; `ml.leakage_screen.temporal_order` 'feature values dated after the observation date: one is a leak by definition (06 C.7 l.1048-1051)'; `ml.leakage_screen.entity_overlap` 'any test entity present in training (the indicator 1 when the overlap share is above 0): a leak by definition'; `ml.data_quality` 'largest share of failed checks over the dq_ counts: proposed, no dossier value (06 C.7 l.1045-1047)'; `ml.shift_resilience` as in the table. Source: `ml/policy.py:46-152`, read by running `threshold_rows()` at f89adac.

## Measured size and power

Read from `CAOS_RiskValidation/docs/ml/08_size-and-power.md` of the engine at f89adac (run by `pytest tests/ml/test_ml_size_power.py -s`, marker `sizepower`, 4,000 repetitions per condition, seed 20261019 for the null and 20261020 for the defect). The design bounds hold for every test with no exception: size at most 0.05 plus two Monte Carlo standard errors (0.0569 at 4,000 repetitions) and power at least `POWER_MIN` = 0.90 (`CAOS_RiskValidation/tests/ml/test_ml_size_power.py:28-49`). The two exceptions of the first design (size 0.10 for the conformal test and 0.15 for the worst-subsample test) were set after the runs and are withdrawn (review M-3, decision G4).

| Test | Null | Size | se | Defect | Power | se |
|---|---|---|---|---|---|---|
| `ml.robustness` | sensitivity 0.25 | 0.0278 | 0.0026 | [0.0230, 0.0333] | sensitivity 2.5 | 1.0000 |
| `ml.shift_resilience` (development 2,000, evaluation 1,000, R = 99, share 0.25) | shift 0 | 0.0418 | 0.0032 | [0.0359, 0.0484] | a quarter of the rows shifted 3 sd on feature 0 | 0.9720 |
| `ml.seed_stability` | instability 0.2 | 0.0000 | 0.0000 | [0.0000, 0.0009] | instability 1.0 | 1.0000 |
| `ml.reason_code_stability` | refit noise 0.1 | 0.0000 | 0.0000 | [0.0000, 0.0009] | refit noise 1.5 | 1.0000 |
| `ml.effect_agreement` | effect range follows importance | 0.0135 | 0.0018 | [0.0103, 0.0175] | independent | 0.9870 |
| `ml.additivity` | exact Shapley values | 0.0000 | 0.0000 | [0.0000, 0.0009] | first column off by 1e-6 | 1.0000 |
| `ml.overfit` | equal separation | 0.0127 | 0.0018 | [0.0097, 0.0167] | train separation 2, test 1 | 1.0000 |
| `ml.weak_spot` | calibrated slices | 0.0000 | 0.0000 | [0.0000, 0.0009] | slice 0 predicts 1 - p | 1.0000 |
| `ml.conformal_coverage` (n_cal 20,000, m 2,000) | drift 0 | 0.0475 | 0.0034 | [0.0413, 0.0545] | log-odds drift 0.5 | 0.9995 |
| `ml.conformal_coverage` (n_cal = m = 2,000) | drift 0 | 0.0493 | 0.0034 | [0.0429, 0.0563] | log-odds drift 0.5 | 0.9845 |
| `ml.conformal_coverage` (n_cal 1,000, m 4,000) | drift 0 | 0.0522 | 0.0035 | [0.0457, 0.0595] | log-odds drift 0.5 | 0.9545 |
| `ml.leakage_screen` | leak strength 0 | 0.0000 | 0.0000 | [0.0000, 0.0009] | leak strength 4 | 1.0000 |
| `ml.data_quality` | NaN rate 0.2 percent | 0.0000 | 0.0000 | [0.0000, 0.0009] | NaN rate 3 percent | 1.0000 |
| `ml.challenger_brier` | equal noise | 0.0302 | 0.0027 | [0.0254, 0.0360] | challenger noise 0.15 above | 0.9952 |

The shift study uses 2,000 development rows, 1,000 evaluation rows, R = 99 and share 0.25 (the engine default R is 199), and ran 17,495 s. Several nulls give size 0 and several defects power 1 because the null and the defect are far apart: those studies show that the light separates the two, not where its boundary sits (review m2). `ml.cbpe_estimate` has no size or power (always not_evaluated; its study is the bias of the estimate, see its entry). The figures are those of the planted defects at these sample sizes, not of a portfolio. Source: engine `CAOS_RiskValidation/docs/ml/08_size-and-power.md`, fix report D2 and second round.

## Conventions table

Values that are arguments of a function and not Policy thresholds; each is a convention for the main session's approval, never regulatory.

| value | meaning |
|---|---|
| weak_spots min_n = 30 | the smallest slice reported as a weak spot (06 C.7 l.1016-1018 gives no value) |
| shift-kind conformal alpha = 0.10 | the miscoverage of the conformal check in the C20 shift kind; the case document labels it a convention |
| reason_code_overlap top_k = 4 | the number of reasons compared (04 J.2 l.881-883, ladder P4 l.968) |
| grade_disagreement notches = 2 | the grade distance counted as a disagreement |
| cbpe_auc n_thresholds = 101 | the threshold grid of the estimate |
| `RIDGE` = 1 | the ridge strength of the engine core's logistic fit behind `shift_score_rank` and `resemblance_auc`, the default of scikit-learn's C = 1 (amended in 2.0.0; source: review m4 and deviation 6, decision G6, `ml/_logistic.py:14`); it changes the numbers put into the C20 documents |
| `FOLDS` = 5 | the cross-fitting folds of the same fit (amended in 2.0.0; source: `ml/_logistic.py:15`) |
| shift_permutations = 199 | the draws R of `shift_development_reference` (the size and power study uses 99); a convention (amended in 2.0.0; source: decision G4, `ml/robustness.py:211`) |
| decimals = 12 | the rounding of the gap and the AUC loss before a strict boundary is decided (amended in 2.0.0; source: review m3, `ml/generalisation.py:38`) |
| minimum-likelihood tolerance = 1 + 1e-7 | the relative tolerance on 'no more likely than the observed count' in the Beta-Binomial p-value, the one of scipy.stats.binomtest (amended in 2.0.0; source: `ml/conformal.py:25`) |

## Names

The function names of this page are ratified as `engine-ml-api` 1.0.0 (decision V5, 2026-10-19); U14-E1 and U14-E2 amend them only through a contract bump. Two names exist in two modules and are easy to confuse: `ml.conformal.conformal_coverage` (the pure function, `from riskvalidation.ml.conformal import conformal_coverage`) and `validation.ml.conformal_coverage` (the TestResult function, `from riskvalidation.validation.ml import conformal_coverage`). Import each from the module named in its heading and never both unqualified. 2.0.0 adds the names `ml.robustness.SingleClassSubsampleError`, `ml.robustness.ShiftReference`, `ml.robustness.shift_development_reference`, `ml.dataquality.CompletenessCount` and the module `ml.policy` (`strict`, `ml_thresholds`, `threshold_rows`, `ml_policy`); every public name of `riskvalidation.ml.*` and `riskvalidation.validation.ml` has an entry on this page and no entry names a function the engine lacks (checked both ways against f89adac in the delivery report of 2.0.0).

## UNVERIFIED and open items

- The values of the named parameters (grid, tolerance, seeds, refits, overfit tolerance, weak-spot multiple, shift score, worst share, cut-off) were proposed by U14-S and approved by the main session (decision V6, 2026-10-19); the engine takes them as arguments. The other Policy thresholds are proposed for approval.
- MAPIE 1.5.0's split-conformal quantile call was read by the review (the `higher` method at the level ((n + 1)(1 - alpha)) / n; review D4 8 F3): no longer open.
- Behaviours stated from the code that no engine test pins (untested): the nesting of the `perturb_features` draws across eps; the values `RIDGE` = 1 and `FOLDS` = 5 (no test asserts the constants); that `SingleClassSubsampleError` is raised by the real `worst_subsample_performance` as the subclass (the real function is tested for ValueError with 'single class', the subclass through a monkeypatch); the relative tolerance 1 + 1e-7 of the Beta-Binomial minimum-likelihood rule.
- The engine at f89adac still cites `engine-ml-api` 1.1.0 in module docstrings and in the `ml_policy` description (626c859 changes only the `CONVENTION` and `RULE` suffixes and the `DOSSIER_06_C7` string to 2.0.0); the integrator aligns them with this version.
- The dossiers print no worked example with numbers for these tests: no golden value is claimed (sizing, Modules and functions).
- MAPIE and fairlearn are optional reconciliation extras (decision Q11), never imported by the engine core.
