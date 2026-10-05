# Tasks: U2, case C05 (low-default portfolios and PD calibration)

| # | Task | Requirement | State |
|---|---|---|---|
| 1 | Register `tasche-2013` and `pluto-tasche-2005` (derived-only), fetch both arXiv PDFs into the data root, pin their hashes | CT-201, CT-202, CT-208 | done |
| 2 | PDF readers: Tasche Table 2 (checked against its All row and printed rates), Pluto-Tasche Tables 1 to 14 (checked shapes) | CT-201, CT-202 | done |
| 3 | The Vasicek generator and its replications; coverage and power tables | CT-204, CT-205 | done |
| 4 | `cases/c05_ldp_calibration.py`: six variants, models artifacts, tests, impact, findings, expected ranges, the golden cell table | CT-203, CT-206, CT-207, CT-208 | done |
| 5 | Parity points exported with the artifacts; TypeScript ports (normal distribution, IRB, most prudent bounds, QMM and the case 1 approaches) | CT-209 | done |
| 6 | The C05 instrument: views, rail sections with live read-outs, the case dispatch in the workbench | CT-210 | done |
| 7 | Docs: the C05 case page, the guide to calibrating a PD curve and estimating low-default PDs, framework cards updated | - | done |
| 8 | The measured gate over the whole matrix, screenshots read in light and dark | CT-211 | done |

## Convergence verdict (2026-10-05)

Converged. Two canonical bakes agree on every C05 number, the 20,000 generated years and the Monte Carlo p-values
included; C01 changed only its version fields. The 79 pipeline tests (one skipped: the template's instantiate test,
which runs in the template only), the 95 web tests and every guard pass, and the expected ranges hold on every
variant. The measured gate passes on shell 0.7.2: `caos-shell-gate: OK, 686 measured states` over every route, and
`OK, 386 measured states` on the App route after the last view edits. The screenshots were read in light and dark,
English and Spanish, at 390, 1280 and 1600 px.

The gate runs and the screenshots found what the build had wrong, each fixed at its source. In C05: the rail scrolled
at 1280x800 (the approach chips took three rows), two equations had no caption, a table ran past the page at 1600 px,
the Variants view drew on too little of its viewport, the grade marks buried the curves, raw row keys and a raw
maturity reached the reader. Two base defects were fixed upstream first: the template's residue marker matched a
finding id (template 0.02.004), and every integer axis repeated its tick labels (shell 0.7.2, with the gate check that
now fails it).

Open for later units: the IRB capital of C01 joins its Impact group (U2's second part); the Moody's backtest of Tasche
section 5 needs Moody's yearly grade frequencies; the engine's tests quote the S&P counts (BL-049), a decision before
the engine's public release.
