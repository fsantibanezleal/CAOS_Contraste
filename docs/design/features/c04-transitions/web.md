# C04 web: the instrument and its views

Design: [`design.md`](design.md); outputs: [`contract.md`](contract.md); requirements CT-410 to CT-414. The instrument
follows C22's and C05's pattern (`frontend/src/workbench/c22/instrument.tsx`, `c05/instrument.tsx`): a hook
`useC04Instrument(data, onPick)` returning the rail sections, the four groups, the Variants view and the Context, wired
into `workbench/Workbench.tsx` beside C05's and C22's. Every view states its lane (replay or live) and its provenance;
every chart is a `PlotCard` holding a `UPlotChart` (the shell's interactive chart: series toggles, hover read-outs),
with its axes' units, a caption saying what is drawn and from which definition, and bilingual text (`pick`, EN and
ES). A view that cannot draw (a definition missing for an agency, a grade whose rate is zero on a log axis) says why in
its card's note and draws what exists, a table where no series remains; it never draws an empty chart. `Pending` is
only for data still loading (it declares `data-state="loading"`, which the measured gate waits on).

## Files

| File | Holds |
|---|---|
| `frontend/src/lib/contract.types.ts` | the C04 output types and their descriptors (checked against the baked artifacts by `lib/contract.test.ts`) |
| `frontend/src/workbench/c04/selection.ts` | `C04Sel` (the case data, the grade, the definition, the live inputs, and `act`, the setters the views' own controls call), kind guards (`isAgency`, `isFamily`, `isPublished`), shared labels and colours, the live hooks (`useProjection`, `useIntervals`, `useCapital`) |
| `frontend/src/workbench/c04/instrument.tsx` | the rail and the group layout per kind |
| `frontend/src/workbench/c04/MatrixMap.tsx` | the heat map every matrix is drawn with |
| `frontend/src/workbench/c04/AgencyModelViews.tsx` | the agency variants' Matrix and Generators views |
| `frontend/src/workbench/c04/AgencyValidationViews.tsx` | the agency variants' PD by grade, By year, Definitions and Lifetime views |
| `frontend/src/workbench/c04/AgencyTestsViews.tsx` | the agency variants' Markov tests, Mobility and Semesters views |
| `frontend/src/workbench/c04/FamilyViews.tsx` | the generator families' Model and Validation views |
| `frontend/src/workbench/c04/PublishedViews.tsx` | the papers' views |
| `frontend/src/workbench/c04/LiveViews.tsx` | Impact: the drift, the intervals and the capital, computed live by `engine/transitions.ts` and `engine/credit.ts` |
| `frontend/src/workbench/c04/C04Common.tsx` | Findings, Variants and Context; the rail's read-outs |
| `frontend/src/content/cases/C04.tsx`, `C04Results.tsx` | the case write-up the Context shows (sources, definitions, methods, caveats) and the measured results, read from the artifacts |
| `frontend/src/pages/C04Sections.tsx` | C04's sections of the Experiments and Benchmark pages |
| `frontend/src/workbench/c04.test.tsx` | CT-412 (each module also has its own test file beside it) |

## The rail (up to three sections, each with a live read-out, fitting 1280 x 800 without scrolling)

A section appears only where its controls change something: the published variant has only the Interval section (its
papers' matrices are derived-only, so there is no chain to project). An agency whose transition page has no default
category (Moody's) keeps the Projection section: its portfolio has no route to default, but it still migrates, and
the Drift view draws its composition over the horizon.

1. **Grade and definition.** A grade chip group (AAA to CCC-C) and, on agency variants, a definition chip group (D2
   default ratings, D3 default events, D4 the transition matrix's default column, Keep: withdrawals kept in the
   denominator; D4 and Keep disabled on Moody's with the reason in the chip's hint). On generator variants the second
   chip group picks the estimator (cohort, duration, EM, diagonal, weighted, JLT) where the family has estimators.
   Read-out: the grade's long-run average under the definition with its Jeffreys interval and the number of cohorts
   (agency), or the grade's true PD and the chosen estimator's bias (generator).
2. **Projection.** A starting-portfolio chip group (all in the best grade; the origination mix; uniform; speculative:
   the three worst grades) and a horizon knob (5 to 50 years). Read-out: the TTC default rate, the first year's and the
   horizon's projected default rate, the largest gap to the TTC rate on the path.
3. **Interval.** A default-correlation knob (0 to 5%) and a level chip group (90%, 95%, 99%). Read-out: for the chosen
   grade's pooled counts, the effective number of obligors (Schuermann and Hanson (3.4)) and the widths of the Wald,
   Agresti-Coull and Jeffreys intervals.

## The groups

**Agency variants** (`sp`, `moodys`, `fitch`):

- Model: *Matrix* (the pooled one-year matrix as a heat map, eight states and the withdrawals share of each row, the
  cell values on hover; a cohort knob to show one year's own matrix instead), *Generators* (the one-year PD by grade
  from the pooled matrix, EM, diagonal, weighted and JLT on a log axis; the L1 distances; Theorem 3's verdict naming
  the moves never observed though reachable; stochastic monotonicity) and *Mobility* (M_SVD and the trace index by
  cohort against the speculative-grade default rate: how the matrices move over the cycle).
- Validation (six sub-tabs, the shell's limit for peers, ADR-0071 rule 5): *PD by grade* (the long-run average under
  each definition on a log axis with the Jeffreys interval as whiskers and the last five years' mean as a marker), *By
  year* (the chosen grade's yearly PD under every definition over the cohorts, with the cohort size), *Definitions*
  (the pooled ratios D4/D2 and D3/D2 by grade, the explanation from CEREP's help file), *Lifetime* (CT-415: each
  five-year window's observed defaults against the chained and pooled projections), *Markov tests* (time homogeneity
  across years and semesters; every cohort against the pooled matrix as p-values over the years with the policy's
  thresholds; the ECB migration statistics by year), *Semesters* (two semesters' product against the year, L1 by year
  and the default columns).
- Impact (live): *Drift* (the projected default rate by year for the chosen portfolio under the agency's pooled
  matrix, the TTC rate as a line, the portfolio's composition by grade over the horizon), *Intervals* (the three
  intervals for every grade at the reader's correlation and level, live), *Capital* (the IRB risk weight of the
  agency's cohort mix with the PDs of each definition and generator, at a reader's LGD).

**Generator families**:

- Model: *Generator* (the true one-year matrix exp(Q) as a heat map; the generator's exit rates per year in the design
  table, since the heat map reads cells as probabilities and Q's diagonal is negative; the true PD by grade at one and
  five years; the design: obligors, years, repetitions, the ladder and its unit).
- Validation, by family: `markov` *Estimators* (bias and RMSE of each estimator by grade with MC errors), *Zeros*
  (the share of exactly zero PDs by grade and estimator), *Size* (the four tests at 5% and 1%), *Coverage* (Wald,
  Agresti-Coull, Jeffreys and bootstrap by grade); `momentum` *Power* (the three tests along the ladder) and
  *Projection* (the five-year default frequency against the Markov projections by grade and rung); `cycle` *Power*
  and *PIT and TTC* (the stressed year's PD, the five-year average and the truth); `withdrawals` *Bias* (removed, kept,
  followed against the truth by grade and rung); `thin` *Coverage* (by cohort size and grade) and *Overlap* (adjacent
  grades' Jeffreys intervals).
- Impact (live): the same three tools on the generator's one-year matrix.

**Published**: Validation *Papers* (Israel et al.'s nine distances, Schuermann and Hanson's Table 5 and Engelmann's
section 4, each printed value beside the recomputed one with its agreement; Engelmann's projected PD paths); Model a
short statement of what each paper computes and why its matrices are not shown; Impact the live intervals at Table 5's
inputs.

**Every variant**: Findings (the shared Findings view), Variants (the agencies side by side: each grade's long-run
average under D2 and D4, the TTC default rate, the definition gaps; the families' headline rates), Context (the
write-up).

## Tests (CT-412)

`workbench/c04.test.tsx` renders the instrument on one agency variant, one family per kind of view and the published
variant from the baked artifacts: the six groups in order; lane and provenance on every view; each rail section's
read-out changes when its controls move; Moody's disables D4 and Keep with the reason; no view draws an empty chart.
