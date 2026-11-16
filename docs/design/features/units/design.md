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
| `prediction_outside_observable` | every NONZERO prediction lies outside the target's widened range (an exact 0 is not judged) | blocking |
| `prediction_outside_domain` | a pair that declares a `domain` has ANY prediction outside it, element by element | blocking |
| `degenerate_constant_prediction` | the prediction is constant while the target varies | advisory, recorded |

`RANGE_SLACK = 1.0` (one full range on each side, as the rule and Fragua). A prediction partly inside the widened range passes:
the gate is about units, never accuracy, and a method may be reported as badly wrong.

### The scale rule (main session ruling of 2026-11-16, after T2's finding)

T2 found that a scale defect (a PD in percent, an amount in thousands) escaped the range rule wherever one prediction stayed
inside the widened range: an exact 0, or a PD below 0.02 written in percent. Two rules close it, both faithful to the binding
rule (units, never accuracy):

1. **An exact zero carries no evidence about scale.** Zero is the same number in every unit, so the series, binary and scalar
   kinds judge the NONZERO predictions: `prediction_outside_observable` fires when at least one prediction is nonzero and every
   nonzero prediction lies outside the widened range. An all-zero prediction over a varying target stays the advisory
   `degenerate_constant_prediction`; zeros beside nulls leave only the advisory `missing_prediction`.
2. **A bounded observable checks every prediction against its domain.** A pair whose observable is bounded by its definition
   declares `domain` (`[lo, hi]`, `null` an open end) with a one-sentence `domain_reason`: a probability, a default or exceedance
   rate, a coverage, a share is `[0, 1]`; a count or a variance, or an amount that is non-negative by definition, `[0, null]`; a
   difference of two probabilities `[-1, 1]`. The gate checks every prediction against it, element by element: ONE prediction
   outside blocks as `prediction_outside_domain`, because no honest method writes a probability of 22; the edges are inside. An
   observable that is not bounded by definition (an LGD or a CCF, which a workout or a drawn line can push past 1; a loss; a
   return; a yield; a correlation estimate) declares no domain, and a domain is never added to make a defect catchable. A `bound`
   pair keeps its own `domain` and `reason` (its class stays `prediction_outside_observable`); `domain_reason` is the field of the
   other kinds, and the specification is invalid with a domain without its reason, a reason without its domain, or an empty or
   inverted domain (CT-2410).

The 21 domains of the specification: the PD, cumulative PD and published PD pairs of C01 to C06 (`[0, 1]`), the C04 momentum error
(`[-1, 1]`), the C09 EAD and the C12 expected exposure (`[0, null]`) and the C16 shares (`[0, 1]`).

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

- `pairs`: a list of `{id, file, prediction, target, kind, unit, group_by?, zero_scale?, domain?, domain_reason?, reason?}`. `file` is a glob under
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

A limit the planted tests pin. Before the scale rule the gate blocked only when EVERY prediction lay outside the widened range, so
a percent-for-fraction defect (x100) was caught on 51 of the pairs on their committed documents and 9 needed x1000 or x1e6 (C03
calibration rows and vintage curves, C04 markov estimators, momentum errors, cycle and withdrawals PDs, C05 scaled central tendency,
C06 both pairs), because a PD below 0.02 written as a percentage is a valid fraction of `[-1, 2]` or because one prediction is
exactly 0. With the scale rule (T2b) every one of them is caught at x100 except `c05-bound-scaled-central`: its scaled central
tendency is below 0.01 everywhere, so a PD written in percent (0.5 for 0.005) is a valid probability and no rule about units can
see it (its domain [0, 1] is already declared). The C12 wrong-way bound is planted by a sign flip, and `c04-moodys-generators`
holds only null vectors today (nothing to plant).
`tests/test_unit_gate.py::test_a_percent_for_fraction_defect_planted_in_a_committed_document_fails_the_pair` records the factor of each
pair. T2b dry run over the committed documents of the 21 cases: 162 documents, 169 pair checks, 0 blocking violations, 70
advisories (unchanged).

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
  `unit-conversion`, `source-cited-input`, `stated-assumption`, `run-budget`), `unit` (words, required) and `reason` (required, never `TODO`). `--update` adds new
  literals as `TODO` and removes entries whose literal is gone; a `TODO` fails the check. The rule's defect class (a literal
  comparable to a measured quantity in a path more than one observable can reach) has no class: such a literal is rewritten against
  a quantity (the rule's table "Write against a quantity, not against a number"), never baselined.
- Where it runs: `ci.yml` beside `scripts/check_internal_names.py` (about 1.3 s, measured on the whole tree) and `scripts/smoke.*`,
  added by T6 when its baseline holds no `TODO` (before that the check fails by design).

### The classes after the review of T6 (the fix, 2026-11-16)

The closed list has nine classes. An entry's `unit` is the unit of that literal, never the group's, and its `reason` names what the
literal is in its own code line.

- `probability`, `ratio`, `relative-tolerance`, `training-hyperparameter`, `single-observable-limit`: as the rule defines them.
  An absolute tolerance on one observable (CCF points, AUC points) is a `single-observable-limit`, not a `relative-tolerance`.
- `unit-conversion`: only a literal that converts one unit to another (a percent, a thousand, days per year, a basis point, a
  label-to-number map of a tenor name). A time, a maturity or a repricing time is never one by being in years.
- `source-cited-input`: only a literal whose source the module or its parameter file cites; the reason names the source.
- `stated-assumption`: a modelling assumption of a case that carries a unit (an amount, a rate per year, a maturity, a repricing
  time); the unit and a reason saying what it assumes and why, no source required. It is never compared with a measured quantity:
  a literal that is, is the rule's defect class and is rewritten against a quantity.
- `run-budget`: a wall-clock or iteration limit of a run (a run timeout, a fetcher timeout, a back-off, a pause), its unit
  seconds, milliseconds or iterations.

### The decisions of task T5 (`scripts/check_unit_constants.py`)

- **The lists were reviewed, not copied from the sizing's heuristic.** All 277 modules were read by docstring and, where they hold a
  non-exempt float literal, by the literals themselves. The rule of the review: a module is `outside` only when no unit-bearing
  float literal can live in it (a package marker, a command line, the rendering of a case page from committed documents, a
  fetcher whose floats are timeouts in seconds, a reader of text formats, the registry, the schemas, the rng, the lineage); every
  `outside` entry carries its one-sentence reason in the file. A module that fits or applies a method, builds a document of numbers,
  holds expected ranges or thresholds (`bake`, `_case`, `documents`, `build`), reads a source into a family with a conversion (a
  percent into a decimal, cents into a rate) or holds a named constant with its source is walked: `method` or `parameter`. The two
  walked lists are treated alike by the check; the split is for the reader of the baseline.
- **Result: 172 method modules (1,523 literals), 27 parameter modules (544), 78 outside (58 literals, not walked: display scales,
  level keys and timeouts), 277 in all.** Against the sizing's 99 modules with 1,161 literals (and 19 with 456): 75 modules join
  the method list (356 literals: 137 in the `bake` modules' expected ranges and grids, 99 in the `documents` modules' thresholds and
  confidence levels, 35 in the `build` modules, 33 in the `_case` objects, 52 in panels, readers and others); `100.0` and `1000.0`,
  which the sizing exempted, are 42 of the 1,523 (37 and 5); `cases/c11/run` goes outside (a command line) and `cases/c12/book` to the parameter list (its
  docstring: "the named parameters of C12"), which also takes the models documents of C12, C16 and C18, `core/gate`, the contract-1
  field bounds (`io/contract`), the examples (`io/examples`) and the published tables (`io/papers`). The workload of T6 is therefore
  2,067 literals, not the sizing's 1,617.
- **The key** is `module::qualname::value::ordinal` with the module as the path under `data-pipeline/pipeline/` without suffix, the
  qualname the enclosing class and function path (a default argument and a decorator belong to the function, a lambda to its
  enclosing function), the value as Python's `repr` of the float (`1e-05`, `-0.25`, `100.0`), and the ordinal the position among the
  equal values of the same scope in source order. A negative literal is one entry, with its sign. A literal inserted above an equal
  one in the same function shifts the ordinals below it: `--update` then rewrites those keys as new `TODO` entries, and the review
  of the diff shows it.
- **A stale entry fails.** A baseline entry with no literal in the walked modules fails the check (and `--update` drops it), so the
  baseline never keeps a justification for code that is gone.
- **The outputs.** A finding names `path:line`, the value and the key; `--counts` prints the literals per list and per case group;
  `--update` prints how many entries it added, dropped and left `TODO`. The baseline is written sorted, one entry per line.

### The decisions of task T6 (`scripts/unit_constants_baseline.json`)

- **The classification is by group, from the code's own names.** The 2,067 literals were listed per module with their enclosing
  assignment, dictionary key, keyword argument or call, and each group of literals sharing one meaning received one class, one unit
  and one sentence naming the constant (the entry's reason starts with `<label> = <value>:`). 559 entries are assigned by a pattern
  and say so (`pattern: <rule>` at the start of the reason): the name of a probability level (`LEVEL`, `ALPHA`, a quantile), a value
  inside an expected-range dict, a percent, basis point or period conversion, a learning rate, decay or sampling fraction of a model
  constructor. The other 1,508 were read from the listing of their group with the line they sit on.
- **Counts by class:** ratio 637, single-observable-limit 447, source-cited-input 346, probability 338, unit-conversion 211,
  training-hyperparameter 59, relative-tolerance 29 (the sum is 2,067; the baseline is the record, `--counts` gives the per group
  figures).
- **An expected-range dict is a `single-observable-limit`.** Each range is read by the check of its own key only (`expectations.check`
  looks the key up), so the one observable that reaches it is the key; the reason says so and the entry's unit is the key's unit.
  A run timeout (`RUN_MS`), a fetcher timeout and a back-off are `single-observable-limit` too: the only quantity that reaches them is
  the wall-clock time of the run itself, which no case observable enters.
- **A named constant of a parameter module is `source-cited-input`** when its file gives it a source, a standard text or an
  assumption of the case stated in the file; a share or a probability the file calls an assumption is classed `ratio` or `probability`.
- **No literal of the defect class was found** (a constant comparable to a measured quantity in a path that more than one observable can
  reach). The literals examined for it, each reached by one observable (named in its entry), are in the T6 report: the C09 CCF features
  (log limit 8.0, score 700 and 100), the C09 generator clips, the C12 cube-mean tolerance 0.02, the C14 open-bucket stand-in 1e9
  years, the C17 severity-scale bounds 100 to 1e7 EUR, the C06 unemployment dead band 0.1, the C10 correlation grid bounds, the C15
  and C18 UR floor, and the C20 `(-1e9, 1e9)` stand-in range, which every dimensionless C20 key can reach and none can approach.

## What it does not do

It does not judge accuracy, never fails an honest method for being wrong, and never reads or writes a withheld series' range. It
does not walk integer literals (scenario counts, milliseconds); the rule names float literals.

## Effort and order

The sizing's estimates: CONTRACT 3 about 4 to 5 days of implementer time, CONTRACT 3b about 4 to 5 days, the review of 1,161
method literals and 456 parameter literals the dominant cost (a pattern first pass, then a reviewer). Order in `tasks.md`. The
manifest field means one re-bake of the 21 manifests, folded into 1.01.000's re-bakes.
