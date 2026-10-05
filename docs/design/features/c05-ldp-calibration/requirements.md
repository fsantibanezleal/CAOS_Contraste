# Requirements: U2, case C05 (low-default portfolios and PD calibration)

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.

| ID | Requirement | Gate |
|---|---|---|
| CT-201 | WHEN the C05 bake reads Tasche (2013), THE reader SHALL parse Table 2 from the fetched arXiv PDF and refuse it unless every grade's counts sum to the printed All row and every printed default rate equals the counts' ratio at two decimals. | `tests/test_c05.py::test_table2_reader_checks_the_print` |
| CT-202 | WHEN the C05 bake reads Pluto and Tasche (2005), THE reader SHALL parse Tables 1 to 14 from the fetched arXiv PDF and refuse a table whose shape differs from the paper's (six confidence levels, the grades or rows it names). | `tests/test_c05.py::test_pluto_tasche_reader_reads_every_table` |
| CT-203 | THE published-answer variants SHALL recompute every parsed cell with riskvalidation and record, cell by cell, the printed value, the recomputed one and the gap, failing the bake when a gap exceeds the tolerance the engine documents for that table. | `tests/test_c05.py::test_golden_cells_within_engine_tolerances` |
| CT-204 | THE Vasicek generator SHALL be seeded, and over its replications the share of defaults per grade SHALL recover the true PDs within three binomial standard errors and the overdispersion of the yearly default rate SHALL recover the asset correlation. | `tests/test_c05.py::test_generator_recovers_truth` |
| CT-205 | THE known-truth variants SHALL report, per grade and confidence level, the coverage of the most prudent bounds (independent, correlated, scaled) over the replications with its binomial standard error, and the power of the battery against the underestimating model. | `tests/test_c05.py::test_coverage_and_power_reported` |
| CT-206 | THE C05 impact SHALL give the IRB capital each calibration or estimate implies, with the regime, the asset class, the LGD, the maturity and the PD floor it used. | `tests/test_c05.py::test_impact_states_its_assumptions` |
| CT-207 | WHEN the bake runs C05, THE pipeline SHALL fail if a result lies outside the range the case declares, naming the result. | `tests/test_c05.py::test_expected_ranges_hold` |
| CT-208 | THE C05 artifacts SHALL carry no grade counts of the derived-only S&P table, only rates, results and test statistics derived from it. | `tests/test_c05.py::test_derived_only_counts_not_published` |
| CT-209 | WHERE the web recomputes a C05 quantity live (the IRB risk weight by regime, the most prudent bounds, quasi moment matching and the calibration approaches), THE TypeScript result SHALL equal the committed riskvalidation result on the exported parity points within 1e-9 relative. | `frontend/src/engine/credit.test.ts` |
| CT-210 | THE C05 instrument SHALL keep the six groups in order and show the lane on every view, and each rail section SHALL hold a live read-out that changes with its controls. | `frontend/src/workbench/c05.test.tsx` |
| CT-211 | WHEN the measured gate walks C05 at five sizes, both themes and both languages, THE site SHALL pass every check. | `frontend/scripts/gate.mjs` (G1 to G9) |
