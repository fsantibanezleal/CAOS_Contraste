# Design: U10-P1, case C14 (IRRBB six shocks on a USD balance sheet, SVB 2022)

Status: live. Unit sizing `plans/contraste/units/U10-sizing.md` (CAOS_MANAGE), decisions D1 to D3. Contracts: `c14-outputs`,
`c14-models` (`docs/contracts/schemas/c14/`), `engine-irrbb-api` 1.1.0 (`docs/contracts/engine/irrbb-api.md`).

## Question

Would the standardised EVE outlier test and the NII sensitivity have flagged the position of the bank that failed in March 2023,
read on its call reports, and how much does the answer hang on the deposit assumptions? The bank is Silicon Valley Bank (FDIC
CERT 24735). The valuation dates are 2021-12-31, 2022-06-30 and 2022-12-31; each is read only up to its date.

## Real aggregates, synthetic behaviour

The call-report items are real (FDIC BankFind financials, thousands of USD). Every behavioural assumption is a named field with
its value, unit, source kind and source: the NMD core share and maturity requests, the prepayment rate, the term-deposit
redemption rate, the open edges of the maturity bands, the HW1F parameters; those not in the report are stated synthetic. The deposit
beta and the replicating-portfolio weights are fitted on the report history and the Treasury curves up to the date.

## What the bake computes, and what the engine computes

The product reads the files, slots the report items into the 19 SRP31.96 buckets (each band of the report spread uniformly over the
buckets it overlaps; the non-maturity deposits through `nmd_split`), builds the inputs, and writes the documents. Every EVE, delta
EVE, delta NII, shock shape, floor, outlier test, gap, duration gap, simulated NII, EaR, EVaR, Monte Carlo error and validation
test row is a `riskvalidation` call (ADR-0069); `tests/contracts_u10/semantics.py::check_document` runs on every document written.

## Documents

`C14/vd-2021-q4.json`, `vd-2022-q2.json`, `vd-2022-q4.json` (`c14-outputs`, one per valuation date, four scenarios each: the 2024
and the 2016 calibrations, with and without behavioural NMD), `C14/models-svb-2021-2022.json` (`c14-models`: the shock tables, the
caps, the multipliers, the replicating-portfolio fits with their stability windows, the parameter changes), `C14/SHA256SUMS.txt`,
`C14/raw-sources.txt` and `data/derived/manifests/C14.json`. The case page is `docs/cases/C14.md`.

## Limits

The scenario cash flows move only the term deposits (the contract's `net_cash_flows` carry the SRP31.125 overlay and nothing
else), so the prepayment multipliers of SRP31.119 are tabled in the models document and not applied per shock; the post-shock
floor is the single number 0 of the contract, not the maturity-dependent floor of SRP31.93; a quarter end on a weekend carries the
previous business day's Treasury curve; the call report buckets by remaining maturity or next repricing and says nothing of the
NMD split by customer, so the retail share is the share of accounts of 250 000 USD or less.
