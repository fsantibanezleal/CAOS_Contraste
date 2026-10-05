# Design: U2, case C05, low-default portfolios and PD calibration

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5.
Sources: research dossier 04 (sections C.1 to C.4), dossier 10 (the golden values, read from the primary sources on
2026-10-05), and the engine pages of `riskvalidation` 0.2.0 on low-default estimation and on PD curve calibration,
which hold the formulas and the cell-by-cell reproductions.

## The question

Two situations a validator meets in rating systems. First, a PD curve estimated on one year must be carried to another:
which way of moving it (keeping the default profile, the accuracy ratio, the shape of the PD curve or the shape of the
likelihood ratio) holds up against what happened, and what capital does each choice imply? Second, a portfolio with
almost no defaults: what can be said about its PDs, how do the most prudent bounds behave when defaults are correlated,
and can the usual tests tell an underestimating model from a sound one?

## Data and inputs

- **Tasche (2013)**, arXiv 1212.3716v6 (Journal of Credit Risk 9(4), doi:10.21314/jcr.2013.169): Table 2, the S&P
  corporate ratings and defaults by grade for 2009, 2010 and 2011, and the paper's results (Tables 5 to 9). Registered
  as `tasche-2013`, **derived-only**: the PDF is fetched into the data root and parsed there; the S&P default studies
  themselves are link-only in the registry, so the artifacts carry the grade default rates, the rating profiles, the
  fitted curves and the test statistics, never the obligor and default counts (CT-208).
- **Pluto and Tasche (2005)**, arXiv cond-mat/0411699v3: the three-grade example (100, 400, 300 obligors; no defaults,
  or 0, 2 and 1) and Tables 1 to 14. Registered as `pluto-tasche-2005`, derived-only, fetched and parsed the same way.
  The example counts are the paper's hypothetical portfolio, not data.
- **The Vasicek generator** (`vasicek-ldp`, Contraste's own): the example's three grades with true PDs 0.05%, 0.10% and
  0.20% and asset correlation 12% (the Basel minimum corporate correlation the paper uses), 20,000 seeded years.

The PDF readers check what they read against the print itself: Table 2's grade counts must add up to its All row and
every printed default rate must equal the counts' ratio at two decimals (CT-201); every Pluto-Tasche table must have
its six confidence levels and its named rows (CT-202). A reader that cannot satisfy these refuses the input.

## The variants

| Variant | What it is | Truth status |
|---|---|---|
| `sp-2010` | the 2009 S&P rating system (QMM-smoothed curve) calibrated to 2010 by every approach of Tasche's cases 1 to 3, tested against the 2010 defaults | published-answer |
| `sp-2011` | the same to 2011 | published-answer |
| `ldp-published` | the Pluto-Tasche example with a hypothetical expert model (0.03%, 0.05%, 0.10%) observed with 0, 2 and 1 defaults; every published bound recomputed | published-answer |
| `ldp-sim-0` | a generated year with no default, the same expert model | synthetic-known-truth |
| `ldp-sim-1` | a generated year with one default | synthetic-known-truth |
| `ldp-sim-3` | a generated year with three defaults | synthetic-known-truth |

The expert model underestimates the generator's truth (0.03% against 0.05%, 0.05% against 0.10%, 0.10% against
0.20%), so the known-truth variants show what the battery and the bounds can and cannot see.

## The calibration approaches (sp variants)

From Tasche (2013) section 4, as `riskvalidation.engines.pd_curve` implements them, every one from the 2009 model:
case 1 (forecast profile and PD known, the PD set to the observed one, "prophetic"): invariant default profile,
invariant accuracy ratio, scaled PDs, scaled likelihood ratio; case 2 (only the PD known): invariant likelihood ratio;
case 3 (only the profile known): invariant PD curve, invariant conditional profiles by least squares and by least
chi-square, invariant likelihood ratio with the PD of theorem 3.3; case 4: the 2009 curve unchanged (the stale
reference). Each is a model record with its constants (c_PD, c_LR, alpha, beta, the forecast PD).

## Tests, impact and findings

- **sp variants**: for every approach, the Monte Carlo default-profile test (`pd.default_profile`, 100,000 samples,
  seed 2013), the chi-square over grades, Jeffreys per grade and for the portfolio; for case 3 the profile chi-square
  (an output, not a registered test). Impact: the IRB capital of the forecast portfolio under each curve (Basel III
  final, corporate, LGD 45% (the F-IRB senior unsecured value for financial institutions, CRE32.6; the S&P universe
  includes them), M = 2.5 years, one unit of EAD per obligor), relative to the scaled likelihood ratio.
- **ldp variants**: the battery on the expert model (Jeffreys per grade and portfolio, the binomial and the
  Vasicek-corrected binomial at 12%); the most prudent bounds at six levels (independent, correlated at 12%, scaled to
  the portfolio's upper bound); in the known-truth variants, the coverage of each bound over the 20,000 years and the
  power of each test, with their binomial standard errors (CT-205). Impact: the IRB capital under the expert PDs, the
  bounds and the truth (corporate exposures, LGD 45%, M = 2.5 years), with the 0.05% PD floor applied and shown, and
  what the confidence level costs: the portfolio's average risk weight under each kind of bound from 50% to 99.5%,
  computed live (it rises fastest near the top: 4.8 points from 50% to 60% for the paper's example, 9.2 points from
  95% to 99%, independent bounds, Basel III, LGD 45%).
- Findings follow the case's severity policy, each citing its tests or a stated design limit.

## The live lane

The browser recomputes, from committed inputs and the engine's parity points: the IRB risk weight by regime (Basel III
final, CRR3, Basel II) for any PD, LGD and maturity; the most prudent bounds for the example's counts at any level,
correlation and scaling (independent by exact binomial sums, correlated by the engine's 256 Gauss-Hermite nodes,
committed in the models artifact); quasi moment matching and the four case 1 approaches for any forecast PD. Parity
(CT-209): every live function equals the engine at the exported points within 1e-9 relative.

## The instrument

The six groups of CT-112 with C05's views: Model (the curves and the rating profiles; the bounds against the level),
Validation (the test table with lights; the golden reproduction; coverage and power), Impact (capital by approach or
estimate, live; for the low-default variants, the capital against the confidence level), Findings, Variants (both
tables, and a chart for the selected kind: the default-profile p-value of every approach in 2010 and 2011 against the
rail's thresholds, or the bounds at 75% of each observed year against the expert PDs and the truth), Context (the two
papers, their licence classes, the generator). Rail sections, each with a live read-out (ADR-0017 rule 3): Calibration
(approach and forecast PD; the constant, the CCC-C PD and whether the model is proper) or Bounds (level, correlation,
scaling); Capital (regime and LGD); Policy (the alpha thresholds). The rail fits 1280x800 without scrolling in both
languages: the four approach chips take two rows (the accuracy ratio goes by "AR"). Grade axes name the letter grades
in their title; the shell's marks are kept for what is selected (the rail's level, this year's defaults).
