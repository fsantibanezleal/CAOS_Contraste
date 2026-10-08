# Design: U4, case C04, rating transitions and TTC PD by grade

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5.
Sources: research dossier 13 (ESMA's CEREP help file; Israel, Rosenthal and Wei 2001; Anderson and Goodman 1957;
EBA/GL/2017/16; Schuermann and Hanson 2004; Smith and dos Reis 2018; dos Reis, Pfeuffer and Smith 2020; Engelmann
2024; Jafry and Schuermann 2004), and the transitions section of `riskvalidation` 0.4.0, which holds the formulas, the
measured sizes and power of the tests and the three published reproductions.

## The question

What do the rating agencies' published migrations say about PDs by grade, and how far can a migration matrix be trusted
to give them, to project them, or to tell whether the chain behind them is Markov and stable? A validator meets
migration matrices in TTC PD estimation (EBA/GL/2017/16 Table 1, "TTC E"), in rating-philosophy analysis (paragraphs
66 and 67), in IFRS 9 lifetime PDs and in stress tests; each use rests on choices (the default definition, the
withdrawal treatment, the estimator, the Markov assumption) that change the PD by grade.

## Data and inputs

**ESMA CEREP** (registry `esma-cerep`, mirror-allowed: "Reproduction of all information on this site (REGISTERS
information) is authorised except as otherwise stated, provided the source is acknowledged"; attribution "Source: ESMA
CEREP; tables transformed by Contraste"). The publication interface calls JSON endpoints by POST with a body
`{"filters": {...}}`, each filter `{"filterList": [{"code": ..., "selected": true}]}`: `filters` (the date codes),
`searchStatistics/{tab}`. The fetch plan (CT-401): the agencies' EU entities `STPGB` (Standard & Poor's Credit Market
Services Europe), `MDYGB` (Moody's Investors Service Ltd), `FITGB` (Fitch Ratings Limited); rating type corporate,
horizon long-term, categories; every calendar-year cohort 2000 to 2025 for tabs 2, 3 and 4, and every semester 2010 to
2025 for tab 4: about 315 requests, four seconds or more apart (the service reset the connection after some fifteen
requests a second apart), each response cached in `<data root>/raw/esma-cerep/` and pinned in the manifest. A cohort
with no ratings is recorded and skipped by the case.

What the pages count (CEREP help file, sections 4.2 to 4.4):

- Tab 2, default rates: "The distinct number of ratings included in the 'number of defaults' ... divided by the total
  number of ratings belonging in the initial cohort ... (regardless of whether they include a default or not)".
- Tab 3, defaults by category: rows the category at the beginning of the period, columns "the category or notch of
  the rating at the placement of the default event"; "In case there are multiple default events in a statistics
  period, all default events will be counted".
- Tab 4, transitions: rows the category at the beginning, columns at the end; "If the rating is withdrawn at the end
  of the statistics period, it is included in the 'Withdrawals' column according to the Category or Notch it was rated
  with at the start".
- "For the purposes of reporting into the CEREP, no deterministic definition of a default event has been set up.
  Therefore, the definitions might differ for various CRAs, and users are strongly suggested to refer to the
  Qualitative information provided by each CRA."

The default-rate page and the transition page do not always count the same cohort: S&P's tab 2 rates imply more
ratings than tab 4's rows hold in B and CCC to C from 2001 to 2004 (up to 8.4%) and in BB in 2008 (1,127 against
980, 15%), every other grade and year equal within the printed rounding; ESMA states no reason (a plausible one, the
transition pages leaving out ratings whose scale changed within the period, is UNVERIFIED). D2 is therefore taken
over tab 2's own cohort, and every gap is recorded and shown.

Measured on 2026-10-06 (2010 cohort): S&P's CCC row has 33 default events on tab 3 and 6 ratings ending in D on tab 4
(the rest withdrawn after defaulting or re-rated after a distressed exchange); Moody's transition page has no default
category at all (labels Aaa to C and WR), so its PDs come from tabs 2 and 3 only; Moody's withdrawals are large (169 of
394 Aa ratings in 2010).

**Papers** in the data root (derived-only, as C05 reads Tasche): Israel, Rosenthal and Wei (2001) and Engelmann
(2024); their reprinted agency matrices are read, used, and never written to an artifact. Schuermann and Hanson's
Table 5 is printed results only.

**The generator**: `riskvalidation.generators.paths.RatingPaths` with the EM generator of S&P's pooled annual counts
(seven grades and default), so the known-truth variants carry CEREP-like rates and cohort sizes.

## The grade scale and the default definitions

| Common grade | S&P | Fitch | Moody's |
|---|---|---|---|
| 1 AAA | AAA | AAA | Aaa |
| 2 AA | AA | AA | Aa |
| 3 A | A | A | A |
| 4 BBB | BBB | BBB | Baa |
| 5 BB | BB | BB | Ba |
| 6 B | B | B | B |
| 7 CCC to C | CCC, CC, C | CCC, CC, C | Caa, Ca, C |
| default | R, SD, D | RD, D | (no category on tab 4) |
| withdrawn | Withdrawals, NR | Withdrawals, WD, NR | Withdrawals, WR |

Three one-year PDs by grade and cohort: **D2** (tab 2, distinct defaulted ratings over the cohort, the definition
closest to EBA paragraphs 73, 76 and 77 at the level of ratings), **D3** (tab 3, default events over the cohort), **D4**
(tab 4, ratings in a default category at the end over the cohort less withdrawals, the industry treatment; not on
Moody's). The long-run average default rate is the average of the yearly D2 rates (paragraph 84); its intervals come
from the pooled counts (Wald (2.2), Agresti-Coull (3.3), Jeffreys), with the dependence correction (3.4) live.

## The variants

| Variant | Truth status | Content |
|---|---|---|
| `sp`, `moodys`, `fitch` | real outcomes | the cohorts with data; PD by grade under D2, D3, D4 and their gaps by year; the long-run average with intervals; the pooled matrix; the embedding diagnostics, DA, WA, JLT and EM generators with distances and PDs; M_SVD and the trace index by cohort against the speculative-grade D2 rate; time homogeneity across cohorts and semesters; every cohort against the pooled matrix; two semesters against the year |
| `markov` | synthetic known truth | 200 repetitions of five annual snapshots of S&P-like cohorts from the EM generator: bias and RMSE of the cohort, duration, EM, DA, WA and JLT PDs by grade; zero shares; size of the four tests; coverage of Wald, Agresti-Coull, Jeffreys and the bootstrap; the order test's two forms over 2,000 repetitions |
| `momentum` | synthetic known truth | dos Reis et al.'s momentum, alpha 0, 0.025, 0.05, 0.125, 0.25 (beta 1; 0.125 gives the hazard coefficient they estimate on Moody's data, dossier 13 section 16): the three path tests' rejection rates and the fitted coefficient; the bias of the one-year cohort PDs; the five-year PD of the momentum chain against the Markov projections |
| `cycle` | synthetic known truth | a recession regime multiplying the downgrade rates by 1, 1.25, 1.5, 2, 3 in the third year: time homogeneity's and the reference test's rejection rates; the cohort PDs of the stressed year and the five-year long-run average (EBA paragraph 84) against the truth |
| `withdrawals` | synthetic known truth | informative withdrawal (rate 6% a year, raised by 1 + k, k = 0, 1, 3, 9, within a year of default): the bias of the PD with withdrawals removed (D4), kept, followed (EBA paragraph 76) and latent against the truth; time homogeneity and the last year's reference test |
| `thin` | synthetic known truth | 50, 100, 200, 500, 1,000 obligors per grade: interval coverage by grade, and how often adjacent grades' Jeffreys intervals overlap |
| `published` | published answer | Israel et al.'s nine distances, Schuermann and Hanson's twelve Table 5 cells, Engelmann's TTC portfolio and projection extremes, each beside its print |

Repetitions: 200 per ladder rung (Monte Carlo SE at most 3.5 points on a rate), 500 bootstrap replicates inside the
Markov variant's first 100 repetitions; seeds derived from the case seed per rung, shared by a rung's estimators and
tests, recorded.

## Views

The six groups of CT-112, in order. Agency variants: Model (the pooled matrix as a heat map with its withdrawals
column; the generators: PDs by grade from EM, DA, WA and JLT on a log axis, the distances and Theorem 3's verdict),
Validation (PD by grade under the three definitions with the long-run average's intervals; years: the chosen grade's
D2, D3 and D4 by cohort; tests: time homogeneity, every cohort against the pooled matrix, semesters; mobility by
cohort against the speculative default rate), Impact (live: the drift of a reader's portfolio under the agency's
matrix, the intervals at a reader's correlation, the IRB capital by definition), Findings, Variants (the agencies and
families side by side), Context (sources, definitions, caveats). Generator variants: Model (the generator and the
ladder), Validation (estimators against the truth, test rejection rates by rung, coverage), Impact (the same live
tools), Findings. The published variant: one Papers view in Validation.

## Live parts

Ports in `frontend/src/engine/transitions.ts`: Engelmann's projection and TTC portfolio (power iteration at unit
balance), the Wald and Agresti-Coull intervals with (3.4), the Jeffreys interval (the Beta quantile already ported for
C22), and the IRB risk weight (already ported for C01 and C05). Parity points exported by the bake: projections of
three portfolios under each agency's pooled matrix, intervals at a grid of counts and correlations, risk weights by
definition.

## What not to claim

- CEREP figures are the agencies' EU entities' statistics as ESMA computes them, not the agencies' own studies, and
  ESMA sets no common default definition: every PD names its definition and agency.
- An agency's PD by grade is not a bank's PD; a matrix estimated here is not a supervisory parameter.
- A Markov fit that passes on one-year aggregates says nothing about the order or momentum of the paths CEREP does not
  publish; those are measured on the generator only.
