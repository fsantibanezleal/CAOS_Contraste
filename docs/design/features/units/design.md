# Design: the units gates (unit M15, CONTRACT 3 and CONTRACT 3b)

Status: planned. Written in CAOS_MANAGE on 2026-11-15 and brought into the product with task T1 of the 1.01.000 line, with
`requirements.md`, `validation.md` and `tasks.md` of this folder. Sources: the binding rule `conventions/units-gate.md` (CAOS_MANAGE), its reference implementation
in CAOS_RES_Fragua (`data-pipeline/fragua/stages/unit_gate.py`, `scripts/check_unit_constants.py`, the rule names both), the
sizing `wip/contraste/m15-units-gate-sizing-2026-11-14.md` (accepted partial) and the decisions of 2026-11-14
(`plans/contraste/post-1-0-cycle.md`, "The units gate (M15)").

## Why

The rule asks one question no gate of Contraste asks today: is a method's answer in the units of the question. Every gate the
product has asks whether the pipeline ran (schemas, contract 1 on the inputs, contract 2 on the artifacts, determinism, expected
ranges per case). Contraste has more than twenty observables across 21 built cases (probabilities, LGD and CCF fractions, loss
rates, VaR as a decimal of value, exposures in USD, capital in EUR, outflow shares, yields), so every constant written for one of
them is a hypothesis for the others. The sizing found no defect (0 in 30 sampled and 38 targeted literals; 7 dry-run violations,
all honest-but-wrong or conservative by design): the gates are the guard for the next case and the next method, not a repair.

## CONTRACT 3, at runtime: a prediction lives in its observable

### The check

`data-pipeline/pipeline/stages/unit_gate.py`, standard library only (it imports `math`, `json`, `fnmatch` and nothing from the
package), so the shipped check loads the same file by path and the bake and CI judge with one function. Per pair of a prediction
array and its target:

| Class | Meaning | Effect |
|---|---|---|
| `non_finite_prediction` | a prediction is NaN or infinite | blocking |
| `prediction_outside_observable` | every prediction lies outside the target's widened range | blocking |
| `degenerate_constant_prediction` | the prediction is constant while the target varies | advisory, recorded |

`RANGE_SLACK = 1.0` (one full range on each side, as the rule and Fragua). A prediction partly inside the widened range passes:
the gate is about units, never accuracy, and a method may be reported as badly wrong.

A null prediction (decided by the main session on 2026-11-15, T1's open question) is a missing value: counted as the advisory
`missing_prediction`, never range-checked and never blocking. The bake meets NaN and infinity in memory before any null is written,
as `non_finite_prediction`, which blocks; a null in a committed artifact is therefore a deliberate missing value (an analytic rung
with no Monte Carlo scenario, a method not fitted, each stated by its document). T3 calls the gate on the document as the case
built it, before any conversion of NaN to null. A null in a target is left out of its range; a target of nulls only is an error.

### The target kinds (decisions of 2026-11-14, and this design's for 0/1 outcomes)

| Kind | Target | Widened range | Where |
|---|---|---|---|
| `series` | an observed series | `[lo - span, hi + span]` | C08, C09 EAD, C10, C11, C12 (ORE as the reference), C15 curves, C16 table A1, C18 backcast |
| `binary` | a 0/1 outcome reported as bin or cohort rates | the label's domain `[0, 1]`, widened by its span | C01, C02, C03, C06 PD rows |
| `scalar` | a known truth `t` (span 0) | `[t - abs(t), t + abs(t)]`; when `t` is 0, by the pair's declared `zero_scale` | C04 generator truths, C05 approaches, C07 and C15 calibration targets, C09 CCF, C14, C16 denominators, C17, C22 estimators |
| `bound` | a prediction that is not an estimate of its target | not compared with the target; finite and inside the observable's declared domain (`domain`, for example `[0, 1]` for a probability, `[0, null]` for a non-negative amount) | C05 `outputs.bounds.*` (upper confidence bounds after few defaults); any later conservative-by-design row, with its reason |

`binary` is this design's answer to the sizing's question Q2: a PD model's target is the default indicator, whose observable is
`{0, 1}`, not the range of a few bin or cohort rates. Scored that way, the sizing's violations 1 to 4 (C01 P0 under severe drift,
C03's 2006-07, 2011-14 and 2015-17 cohorts) pass, and a PD written in percent (22 for 0.22) still fails, because 22 lies wholly
outside `[-1, 2]`. A `scalar` pair widened by `abs(t)` passes the 270 honest point targets of the dry run; the literal point rule
would fail 206 of them and the decade rule 12 (C17's lognormal LDA rows, a published finding), and both are accuracy gates, which
the rule forbids. A `bound` pair carries a one-sentence `reason` in the specification; without it the specification is invalid.

### The specification

`data-pipeline/config/unit_pairs.json`, one entry per built case (the registry's `built_cases()`), each one of:

- `pairs`: a list of `{id, file, prediction, target, kind, unit, group_by?, zero_scale?, domain?, reason?}`. `file` is a glob under
  `data/derived/<case>/`; `prediction` and `target` are path expressions in the dotted syntax of the sizing (`outputs.rungs.<m>.
  reliability[].pd`: `[]` walks an array, `<m>` walks a map's keys and binds the method id the violation names). `unit` is the
  observable's unit in words (`probability`, `USD`, `decimal of portfolio value`).
- `bake_only`: `{hook, reason}` for a case whose predictions never reach an artifact with their target (C13's desk VaR per
  replication in `cases/c13/measure.py`, C20's PD arrays in `cases/c20/fits.py`).
- `withheld`: the pairs a case checks in memory because its target may not be published (C11's four `withheld-derived-only`
  windows, decision 3): the artifact records the verdict (`contract.units`: pairs checked, violations, advisories), never a range,
  a minimum or a maximum of the withheld series.
- `not_applicable`: one sentence on why nothing is predicted and scored against a target (C21: estimators of a disparity
  coefficient; the amount blocks of C07 and C15 compare methods with each other on a synthetic bank).

What the sizing left unmapped is mapped or given its reason in task T2: C22's simulated rejection rates (a rate is a probability,
`bound` with `domain [0, 1]` against the nominal level, or `scalar` against an exact curve point), C10's correlation grids, C05's
`ldp-published.json`, C12's `wrong-way-risk.json`, C14's two dates without a realised year, C16's reverse stress, C04's agency
and thin variants.

### The mapping decisions of task T2 (`data-pipeline/config/unit_pairs.json`)

The specification holds the 21 built cases (C01 to C18, C20 to C22): 18 with `pairs` (C11 also with `withheld`), C13 and C20
`bake_only`, C21 `not_applicable`. Every `file` glob matches at least one committed file and every pair resolves on every file it
matches; a pair whose glob is narrower than its family says which files it skips in its `reason` (the field is free on any kind and
required only on a `bound`). The tests `test_every_built_case_is_covered`, `test_every_file_glob_matches_a_committed_file` and
`test_every_pair_resolves_on_every_committed_file_it_matches` keep that true; a case built later fails the first until it is added.
Dry run on the 171 committed documents: 169 pair checks, 0 blocking violations, 70 advisories (63 `missing_prediction`, 7
`degenerate_constant_prediction`, the C01 P0 control).

Kinds decided from the document's content (two differ from the labels of the brief, recorded here):

- `binary`: C01 (reliability and grade bins, the 50-row scorecard sample), C02, C03 (calibration rows, the 5-year vintage summary, the
  vintage curves), C06 (lifetime backtest, decile calibration). The sizing's violations 1 to 4 pass; the replay of the sizing's own
  `series` rule on the same fields reproduces exactly those four.
- `scalar`: C04 `coefficient` and the published parity (Engelmann `ttc_pd` and each portfolio's `pd0`, recomputed against printed), C07
  and C15 calibration targets, C09 CCF per design (`group_by` the row), C10 grid correlation per cell, C14, C16 denominators per
  element, C17 capital quantiles, C22 `null.json` estimators. `zero_scale` 1.0 is declared where the truth can be exactly 0 by
  construction (a share, a rate, a correlation, a coefficient, a difference of two PDs).
- `series` where the target is a vector, not one truth: C04's generator PDs (`estimators.<m>`, `pd_*`, `error_*`; the truth is one PD
  per grade, a vector of seven) and C05 `approaches.<m>.pd` against `default_rate1` (one observed rate per grade, seventeen). `scalar`
  needs exactly one value and would raise on both; this differs from the brief's list (C04, C05 approaches `scalar`).
- `bound` with domain [0, 1] and a reason: C05 `outputs.bounds.*` (the five families, `ldp-published.json` included because a bound
  needs no target), C04's agency PD matrices and estimator vectors (`sp`, `fitch`, `moodys`: real histories, no known truth), C10
  grid rejection rates, C22 simulated rejection rates (`[0, 1]`), C12 `wrong-way-risk.json` exposure (`[0, null]`, the sign every
  exposure has).
- `withheld` (C11): the four `withheld-derived-only` windows, one pair for the VaR and one for the ES, the same paths as the two
  published windows; the committed file holds a null realised loss, so only the bake can run them (T3) on the in-memory document.

What the sizing left unmapped, each decided from the document:

| File | Decision and why |
|---|---|
| C22 simulations (`outputs.simulations[].rates`) of all nine variants | `bound` [0, 1]. The exact reference (`exact.p<..>`) exists for 9 of 48 clustering scenarios only and a pair under `group_by` fails on an element without it, so the elementwise pairing is the case's own parity (`golden`, `exact_curves`). |
| C10 `grid-22.json`, `grid-40.json` | `mean_estimate` against `known_rho` per cell (`scalar`) and `rejection_rate` `bound`. |
| C05 `ldp-published.json` | the bounds as `bound` (no `true_pd` in a published example); `scaled_central_tendency` only where shipped (`ldp-*[!0].json`). |
| C12 `wrong-way-risk.json` | no ORE run (the reconciliation is null), so no reference series: `bound` [0, null]. |
| C14 `vd-2022-q2.json`, `vd-2022-q4.json` | not mapped: `out_of_sample.applicable` is false and projected and realised are null; the pair's `reason` says so. |
| C16 `reverse-stress.json` | not mapped: no `scoring` block. |
| C04 `thin.json` | not mapped: the document ships coverage and interval lengths of the known-truth design, no estimate. `published.json`: mapped (parity). Agency variants: `bound`. |
| C07, C15 scenario files | not mapped: the amounts compare methods with each other on a synthetic bank (no target); only the generator calibration is paired. |
| C18 `reverse-stress.json`, `t-copula-baseline.json` | not mapped: no backcast block. |

A limit the planted tests pin. The gate blocks only when EVERY prediction lies outside the widened range, so a percent-for-fraction
defect (x100) is blocked by 29 of the 37 non-bound pairs and 11 of the 14 bounds (51 pairs in all) on their committed documents; the
others need a larger factor (x1000 or x1e6: C03 calibration rows and vintage curves, C04 markov estimators, momentum errors, cycle
and withdrawals PDs, C05 scaled central tendency, C06 both pairs), the C12 wrong-way bound is planted by a sign flip, and
`c04-moodys-generators` holds only null vectors today (nothing to plant), because a PD below 0.02 written as a percentage is a valid fraction of `[-1, 2]` or because one prediction is exactly 0.
`tests/test_unit_gate.py::test_a_percent_for_fraction_defect_planted_in_a_committed_document_fails_the_pair` records the factor of each
pair. Whether the rule should also look at a share of predictions outside is the main session's decision on the rule, not this table's.

### Where it runs

1. In the bake, at the single choke point. `stages/export.py::write_artifact` (37 call sites in 21 case modules) calls
   `unit_gate.check_document(case, rel, doc, spec)` after the schema validation and before writing. A blocking violation raises
   `UnitGateError` naming the case, the file, the pair, the method and the ranges, and nothing is written. The bake's manifest
   records `contract.units` (pairs checked, advisories) beside `expect` (`core/manifest.py`).
2. In the bake-only hooks (C13, C20) and the withheld windows (C11), on the in-memory arrays, with the same function.
3. Over the shipped artifacts: `scripts/check_units.py`, standard library only, next to `scripts/check_artifacts.py` in `ci.yml`,
   `deploy-pages.yml` and `scripts/smoke.sh`/`smoke.ps1`. It reads the specification and the committed `data/derived/`, so an
   artifact baked before the gate existed cannot ship either (the rule: "run inside the bake AND again over the shipped
   artifacts"). It reads tens of files in well under a second; CI gains one step and no job (the light-CI rule;
   `scripts/check_ci_budget.py` admits it).

## CONTRACT 3b, at author time: every constant declares its unit

`scripts/check_unit_constants.py`, standard library only: an AST walk of every float literal of the covered modules.

- Coverage. `scripts/unit_constants_modules.json` holds three reviewed lists of modules under `data-pipeline/pipeline/`: `method`
  (fit or apply a method; 99 by the sizing's heuristic, reviewed in T5), `parameter` (named constants with their sources: `params`,
  `assumptions`, `constants`, `anchors`, `targets`, the models documents of C14 and C15; 19), and `outside` (pages, documents,
  readers, fetchers, io and core infrastructure), each `outside` entry with its reason. A module in no list fails the check, so a new
  module cannot escape review. Fragua's `SKIP_PARTS = ("/cases/", ...)` is not used: 1,136 of Contraste's 1,161 method literals sit
  under `cases/`.
- Exemptions. The values Fragua exempts except two: `0.0`, `1.0`, `0.5`, `2.0`, `10.0` and `abs(v) < 1e-5` are exempt; `100.0` and
  `1000.0` are not, because in Contraste they are percent and thousand conversions (26 places in method modules) and the
  conversion is where the unit is declared.
- Baseline. `scripts/unit_constants_baseline.json`, one entry per literal keyed `module::qualname::value::ordinal` (Fragua's
  `module::value` collides when one value carries two units in one module, as `0.05` does in `cases/c01_retail_pd.py`), with
  `class` from a closed list (`probability`, `ratio`, `relative-tolerance`, `training-hyperparameter`, `single-observable-limit`,
  `unit-conversion`, `source-cited-input`), `unit` (words, required) and `reason` (required, never `TODO`). `--update` adds new
  literals as `TODO` and removes entries whose literal is gone; a `TODO` fails the check. The rule's defect class (a literal
  comparable to a measured quantity in a path more than one observable can reach) has no class: such a literal is rewritten against
  a quantity (the rule's table "Write against a quantity, not against a number"), never baselined.
- Where it runs: `ci.yml` beside `scripts/check_internal_names.py` (about 2 s) and `scripts/smoke.*`.

## What it does not do

It does not judge accuracy, never fails an honest method for being wrong, and never reads or writes a withheld series' range. It
does not walk integer literals (scenario counts, milliseconds); the rule names float literals.

## Effort and order

The sizing's estimates: CONTRACT 3 about 4 to 5 days of implementer time, CONTRACT 3b about 4 to 5 days, the review of 1,161
method literals and 456 parameter literals the dominant cost (a pattern first pass, then a reviewer). Order in `tasks.md`. The
manifest field means one re-bake of the 21 manifests, folded into 1.01.000's re-bakes.
