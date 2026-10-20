# Design: U13-P1, case C18 (ICAAP and IAPE capital aggregation under macro scenarios)

Status: live. Unit sizing `plans/contraste/units/U13-sizing.md` (CAOS_MANAGE), decisions Q1 to Q15, E1 to E6, T1 to T5, W1 to W6, Y1 to Y3, Z1 to Z9.
Contracts: `c18-outputs`, `c18-outputs-aggregation`, `c18-outputs-reverse`, `c18-models` (`docs/contracts/schemas/c18/`),
`engine-aggregation-api` 1.1.0 and `engine-stress-api` (`docs/contracts/engine/`). Engine: `riskvalidation` pinned by commit in
`data-pipeline/requirements.txt` until the batch 3 release is tagged.

## Question

Does Banco Andino, the synthetic bank of C07 and C15, hold its internal capital target for three years under each scenario once credit, market,
IRRBB and operational risk are aggregated, and how much of the answer rests on the aggregation method? The scenarios are the Federal Reserve 2026
baseline and severely adverse paths, the EBA/ESRB 2025 adverse path (United States rows) and the NGFS Phase 5 Delayed transition (the only scenario
NGFS itself classes as disorderly). The headline capital is the simple sum of the four economic capital figures (the IAPE adds up the capital needed
for each risk, and the ECB does not recognise inter-risk diversification in the SREP); every diversified figure is information for the validator.

## What the bake computes, and what the engine computes

The product reads the sources, builds the inputs and writes the documents. Every satellite fit and projection, path transposition, marginal VaR, ES
and expected loss, band row (lower bound, simple sum, variance-covariance, Gaussian and t copula, worst case), Euler contribution, model risk
measure, capital plan row, OI, P2G proxy, Annex 3 row, reverse stress solution and validation test is a `riskvalidation` call (ADR-0069);
`tests/c18/test_c18_engine_calls.py` scans the package for the estimators it must not restate. The cross-field checks of
`tests/contracts_u13/semantics.py` run on every document before it is written and across the set.

## The four marginals (decision Q5)

One horizon (one year) and one confidence level (99.9 percent); EC is VaR less expected loss (dossier 04 l.652-653).

* **Credit**: the engine's grouped copula (`portfolio_from_groups`, `simulate_gaussian`, one systematic factor) on the six C07 segments with their PD,
  LGD and asset correlation. Each segment is a group of representative names that carry its exposure (the accounts number 171,500). The 99.9 percent VaR and ES are measured
  with 400 and with 1,600 names per segment and the same seed; the models document records both, the difference and the Monte Carlo standard error, and the larger
  count is used when the difference exceeds two standard errors (decision Z15).
* **Market**: C11's mixed-portfolio VaR and ES (champion of the 1 percent level, last forecast day) moved to 99.9 percent by the ratio of normal
  quantiles and to one year by the square root of 250 (two conventions, W4), scaled to the market share of RWA (the position value is the market
  RWA). C11 publishes a VaR and an ES, not a distribution: the marginal the copula needs is the zero-mean Student t whose scale and degrees of
  freedom reproduce both, read back through the engine's estimators.
* **IRRBB**: the engine's Hull-White one-factor simulation on C15's committed curve and book, with C15's parameters and seed; the economic value
  lost on each path, the two currency legs added.
* **Operational**: `oprisk.aggregate` (Fourier aggregation of the compound Poisson-generalised Pareto) on the C17 `xi-0-8` parameters, the frequency
  scaled by Banco Andino's assets over the C17 bank's, the euro severities converted at the BCCh rate of the as-of date (series
  `F072.CLP.EUR.N.O.D`, derived at bake time, W5).

The marginals do not depend on the scenario: no macro satellite exists for market, IRRBB or operational risk (decisions Q6 and Q7), so the four
scenario documents and the aggregation variant share them, and the band, the Euler allocation and the diversification are the same in each.

## The satellites and the scenarios (decisions Q6 to Q9, W1)

Five OLS satellites on the Board's net charge-off rates (all banks, seasonally adjusted), AR(1) plus real GDP growth and the unemployment rate at
lags 0 and 1, agency regressors only. The commercial and residential real estate series start in 1991 Q1 and hold quarters of net recoveries, so they
use the identity link; the other three use the probit link from 1985 Q1. All end in 2019 Q4. The expected signs are declared before the fit
(`params.EXPECTED_SIGN`) and the engine counts the violations. The satellites are a US-calibrated adaptation: Banco Andino's commercial, consumer and
mortgage classes map to the Fed loan types with stated weights. The back-cast runs the fits from 2019 Q4 on the realised regressors of 2020 Q1 to
2025 Q4; 2026 Q1 and Q2 are rate-only descriptive rows.

Each published path keeps its shape (its change from its own jump-off) and takes the last observed value of the United States history (2025 Q4):
the Fed paths start the quarter after it; the EBA annual values are read as year-end levels joined linearly from year-end 2024; the NGFS variables are the baseline run plus the
Delayed transition deviation of 2031 to 2033, put on the same jump-off. Banco Andino's credit loss of a year is the exposure of each class times the
mean of the year's four quarterly rates. Market has no position book in C07 or C15 and no source maps a macro path to the operational loss, so both carry their
expected loss in every scenario and year and the stressed loss is a floor. An EVE change is not a profit-and-loss item of the banking book: the IRRBB loss of a scenario is
nil and the rate path acts on the net interest income of the PPNR row (below).

## Capital (decisions Q4, Q10, W3)

RWA is the C15 Tier 1 proxy over the 11.0 percent CET1 anchor, split by the mix of the Banco Santander-Chile Form 20-F 2025 (ratios only,
derived-only); the buffers are its ratios; the PE ratio is its effective-equity ratio and, since no source splits the part above CET1, that part is
carried as T2 with AT1 nil (an UNVERIFIED assumption, decision Z12: no CET1 figure depends on it and Tier 1 equals CET1). The headline CET1 path is the loss-only
depletion; a labelled row adds PPNR: the NII of each year is the C15 twelve-month margin less the engine's `irrbb.eve_nii.delta_nii` on C15's book and curve, the curve
shifted in parallel by the variant's transposed rate change from the jump-off with C15's floors (the Fed prime rate or the NGFS policy rate where the variant carries
a short rate, the EBA 10-year rate otherwise, named in the document), plus the fee ratio 0.25 and the cost ratio 0.55, case assumptions (decision Z11). The OI adds the named c_P2 and c_d to the Chilean stack; the 4 percent cap binds the art.
66 quinquies requirement `p2r`. No mitigation is assumed (EBA para 33), so row 10.2 of the Annex 3 is N/A.

## The reverse stress (decisions Q11 and Z10)

The failure point is CET1/RWA at the Chilean legal minimum stack. The loss-only path of the baseline already ends below the stack (earnings are not credited), which is
the headline finding; the reverse stress therefore runs on the labelled PPNR path: CET1 at the jump-off plus the cumulative PPNR less the cumulative losses reaches the
stack when the three-year loss net of the baseline's cumulative PPNR equals the headroom of CET1 over the stack at the jump-off. It rests on the assumptions of the PPNR
row and says so in both languages. If the PPNR baseline also ended below the stack the reverse stress would be not evaluated, with that reason, and the loss would never be
redefined. The factors are real GDP growth and the unemployment rate, shifted together for the twelve quarters; their covariance is that of 1985 Q1 to 2019 Q4. The engine
finds the minimum Mahalanobis distance scenario from four starts.

## Documents

`C18/baseline.json`, `eba-2025-adverse.json`, `fed-2026-severely-adverse.json`, `ngfs-delayed-transition.json` (`c18-outputs`),
`t-copula-baseline.json` (`c18-outputs-aggregation`), `reverse-stress.json` (`c18-outputs-reverse`), `models-banco-andino.json` (`c18-models`),
`SHA256SUMS.txt`, `raw-sources.txt` and `data/derived/manifests/C18.json`. The case page is `docs/cases/C18.md`.

## Limits

* The satellites do not hold out of time: they predict a large 2020 peak that the stimulus of 2020 prevented (the back-cast is red for every loan type).
* Some coefficients have the opposite of the expected sign; the sensitivity test is red and the documents say so.
* Only credit responds to the scenario through the satellites, and the PPNR row's NII through the rate path; market and operational losses are expected losses and the stressed loss is a floor.
* The IRRBB correlations of the base matrix are a convention labelled UNVERIFIED (decision T2).
* The AT1/T2 split is not in any source (an UNVERIFIED assumption). The EBA values are annual averages read as year-end levels (UNVERIFIED, F6).
* The loss-only path ignores earnings, so even the baseline ends below the CET1 stack; the PPNR row is labelled and shown beside it, and the reverse stress rests on it.
* The stressed credit path rests on satellites that fail their own 2020 to 2025 back-cast; the documents state it in the headline.
