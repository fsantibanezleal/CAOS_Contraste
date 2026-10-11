# Tasks: U4, case C04

| # | Task | Requirement | State |
|---|---|---|---|
| 1 | The CEREP fetch kind in the registry and the fetcher (paced, cached, pinned), with a fake-opener test; the fetch run | CT-401 | done |
| 2 | The CEREP reader: labels to the common scale, the three default definitions, the consistency checks | CT-402 | done |
| 3 | The agency variants: PDs under three definitions, the long-run average with intervals, the pooled matrix, embedding and generators, mobility, time homogeneity, reference and semester checks | CT-403, CT-404, CT-407 | done |
| 4 | The known-truth families on the EM generator of S&P's counts: Markov, momentum, cycle, withdrawals, thin | CT-405 | done |
| 5 | The published variant: Israel et al., Schuermann and Hanson, Engelmann | CT-406 | done |
| 6 | Findings, expected ranges, lineage, determinism; the bake and a second bake | CT-408, CT-409 | done |
| 6b | The lifetime check: five-year windows of CEREP against the chained one-year matrices | CT-415 | done |
| 7 | The live ports (projection, intervals, capital) with parity tests | CT-410, CT-411 | done |
| 8 | The C04 instrument and its views; the content page; the methodology and coverage entries | CT-412, CT-414 | done |
| 9 | The case page in docs; the measured gate; screenshots read; version 0.05.000, changelog, PR | CT-413, CT-414 | done |

Task 9 closed on 2026-10-10 with 0.06.000 (shell 0.10.0): the case page `docs/cases/C04.md`; `caos-shell-gate` OK on
910 measured states; every App view captured and read (light English and dark Spanish at 1280 x 800, light English at
390 x 844), which found and fixed the Drift, Definitions, Findings, Markov rail and matrix map defects listed in the
CHANGELOG; 0.05.000 merged into develop (PR #11) and 0.06.000 released with it.

Found on the way and fixed where it lives, before C04 used it: riskvalidation 0.4.1 (a PD of 0 refused although the
function floors PDs; CAOS_RiskValidation#24), 0.4.2 (the MSE and RMSE with their Monte Carlo errors; the exact
coverage and overlap of the intervals, which C04 had computed itself; #27), 0.4.3 (a NaN rate passed `RatingPaths`'
checks and made a draw run without end; the order test's form measured on three chains; #30); in this repository,
C01's TabPFN weights loaded from the home directory because the cache setting came after the import.
