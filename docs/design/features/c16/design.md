# Design: U11-P, case C16 (liquidity stress, LCR and the March 2023 run, on the call reports of the bank that failed on 2023-03-10)

Status: live. Unit sizing `plans/contraste/units/U11-sizing.md` (CAOS_MANAGE), decisions Q1 to Q14, A1 to A6 and X1 to X4. Contracts:
`c16-outputs`, `c16-outputs-reverse` and `c16-models` (`docs/contracts/schemas/c16/`), `engine-liquidity-api` 1.2.0
(`docs/contracts/engine/liquidity-api.md`).

## Question

Would the LCR and the liquidity stress models have flagged the March 2023 deposit run? The bank is Silicon Valley Bank (FDIC CERT
24735). The valuation date is 2022-12-31, the last call report before the run, with 2021-12-31 and 2022-06-30 as a time block inside
each document; every report is read only up to the date it describes.

## Real aggregates, synthetic behaviour

The call-report items are real (FDIC BankFind financials, thousands of USD). Every behavioural assumption is a named field with its
value and its basis, labelled a convention where the sources give none: the deposit-category mapping and its sensitivity band, the
monetisation schedule, the duration bucket of each securities type, the day calendar, the grids, the target of the reverse stress, the
tolerances and the lights (`assumptions.py`, the conventions block of every document). Nothing is a regulatory threshold.

## What the bake computes, and what the engine computes

The product reads the files, maps the report items to categories (`balance.py`), spreads reported bands over days, and writes the
documents. Every cumulative outflow, ladder, haircut, CBC value, net liquidity position, survival period, cliff, HQLA cap, LCR, reverse
stress solve and validation row is a `riskvalidation` call (ADR-0069); a test scans the package for a run-off, compounding or survival
formula and finds none. The documents pass the schema, `tests/contracts_u11/semantics.py::check_document`, the cross-document checks and
`bake.extra_findings` before they are written.

## Modules

`fetch` (FDIC wide span, H.8 release pages, the Board review; provenance sidecars `provenance-c16.json`), `h8` (the standard library
parser), `anchors` (the event constants with their page, checked against the fetched review), `assumptions` (the conventions),
`balance` (items, deposit segments, securities by type, the contractual ladder, the LCR balances, the maturity profile), `variant`
(one path variant through the engine: scenario, CBC, ladder, LCR, HTM, scoring), `document` (assembly of a scenario document and its
test rows), `reverse`, `models`, `bake` (build, write, manifest) and `page` (the generated blocks of `docs/cases/C16.md`).

## Decisions of this unit

- **The reverse stress input.** The engine's reverse takes no inflows or other outflows; the document hands it the CBC plus the
  cumulative inflows less the cumulative other outflows, which leaves the ladder's NLP at multiplier one (tested).
- **The fast run.** A `FastRun` holds the concentrated uninsured class only, so the other segments run at the LiST Adverse rates; the
  horizon is the five days of the conventions, so its reverse stress (target 30 days) is refused with the reason.
- **The HQLA levels.** Reserves and Treasuries Level 1, agency and agency mortgage-backed Level 2A (GNMA is not split by the report),
  municipal and other debt not HQLA under the Basel text; securities at fair value less the encumbered part, then the Basel haircut.
- **The H.8 record.** Each week takes the value of the latest release that lists it; the record is the observed aggregate of the weeks
  around the run and never an input of a valuation. The Board's CDN answers 403 for a Friday without a page (a holiday), read as "try the
  Thursday".
- **The HTM revaluation.** A par bond per maturity band of the securities book at the par curve one year before the date, priced on the
  curve of the date through `riskvalidation.irrbb` (`bootstrap_zero_curve`, `zero_rates_at`, `eve`), the profile applied to the HTM
  amortised cost; a convention, labelled, compared with the reported fair value by `htm_revaluation_vs_reported`.
- **The generator.** One shared stress chain (enter 0.01, exit 0.05 a day, conventions), no withdrawal in the calm state, the stress
  hazards from the LiST Adverse rate, the calibrated fast-run rate and the full run of a financial customer; 1000 depositors per segment,
  20,000 draws seeded; the worst standardised error is the verification.

## Documents

`C16/lcr-standard.json`, `list-adverse.json`, `list-extreme.json`, `fast-run.json`, `htm-losses.json` (`c16-outputs`),
`C16/reverse-stress.json` (`c16-outputs-reverse`), `C16/models-svb-liquidity.json` (`c16-models`), `C16/SHA256SUMS.txt`,
`C16/raw-sources.txt` and `data/derived/manifests/C16.json`.

## Missing data

A source that does not answer stops the bake and names it; nothing is written for the variants that wait for it. A missing H.8 page
set is the one case the contracts allow to continue: the aggregate record is omitted with its stated reason. A call-report item the
FDIC lacks is a derived amount with its reason (DEPFOR) or taken as zero with an assumption (FREPO, FREPP, OTHBFHLB); an item the sheet
cannot do without (DEPUNA, DEPINS, DEP, DEPDOM) refuses with its name.
