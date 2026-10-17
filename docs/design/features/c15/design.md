# Design: U10-P2, case C15 (IRRBB on a CLP and UF balance sheet, RAN 21-13 Annex 1)

Status: live. Unit sizing `plans/contraste/units/U10-sizing.md` (CAOS_MANAGE), decisions D1 to D3 and reservations R3 and R4. Contracts:
`c15-outputs`, `c15-models` (`docs/contracts/schemas/c15/`), `engine-irrbb-api` 1.1.0 (`docs/contracts/engine/irrbb-api.md`).

## Question

How much EVE and NII does a synthetic Chilean bank with a UF position lose under the shocks of RAN 21-13 Annex 1 on the Banco Central de
Chile curves, how much of it is the indexation charge and not rate risk, and what does the 50 percent CLP and CLF offset change? The bank is
Banco Andino (the synthetic bank of C07); the month is September 2026, the last complete month; the six variants are the SDD's: long UF,
short UF, CPI surprise, CLP steepener, CLP and CLF offset on and off, floors active.

## Real curves, synthetic bank

The yields are real: the BDE table F022 of the Banco Central, read through its API with the project's account (owner prerequisite 7). The book
is synthetic. Its three loan portfolios and its total exposure are C07's calibration (read, never changed: reservation R3); its securities,
deposits, equity and loans to banks are the other figures of the same CMF table (Cuadro N 1, column Bancos, August 2026), scaled by the same
factor; everything else (the UF share of each portfolio, the repricing profile of each item, the deposit split, the NMD requests, the
prepayment and redemption rates, the deposit beta, the margins of the dynamic NII) is a named assumption stated synthetic, with its value, unit
and source (`assumptions.py`, gate `check_registry`). The extension of C07's book is stated: C07 holds a credit book only.

## The valuation date and the dating rule

The chosen series are those of the F022 table with at least one value in the month; a series without one is left out with the last observation
the BCCh lists for it. The valuation date is the last business day of the month on which every chosen series, the UF value included, has a value
(2026-09-03). The whole month is fetched and kept in the raw files; `Series.values(up_to=...)` is the only way the curve code reads a value, so
nothing dated after the valuation date enters a fit (tested on a planted later value and on the real month).

## What the bake computes, and what the engine computes

The product reads the files, builds the inputs and writes the documents. Every zero rate and fit parameter (`bootstrap_zero_curve`,
`fit_nelson_siegel`, `nelson_siegel_yield`), the slotting (`slot_cash_flows`, `nmd_split`), every shape, floor, EVE, delta EVE, delta NII, offset
pair, indexation charge, prioritised-bank test, simulated NII and validation test row is a `riskvalidation` call (ADR-0069). The product computes
only what the contract states as a field: the buckets where a floor binds (a comparison), the smallest distance to a floor (a minimum of engine
outputs), the effect of the CPI surprise (`-PN_UR x surprise / 100`, the formula of the contract) and the construction of the synthetic book.
`tests/contracts_u10/semantics.py::check_document` runs on every document before it is written (decision D3).

## Documents

`C15/long-uf.json`, `short-uf.json`, `cpi-surprise.json`, `clp-steepener.json`, `offset-on-off.json`, `floors-active.json` (`c15-outputs`),
`C15/models-banco-andino-2026-09.json` (`c15-models`), `C15/SHA256SUMS.txt`, `C15/raw-sources.txt` and `data/derived/manifests/C15.json`. The case
page is `docs/cases/C15.md`. The raw files stay in the device data root under `raw/bcch-f022/`; `pipeline.io.bcch fetch` writes them with a
provenance record (URL without user and password, size, SHA-256, retrieval date), the bake refuses a file that differs from its record and never
reads the credentials.

## Open questions and limits

1. **The pesos curve has three published tenors.** The engine's `fit_nelson_siegel` needs four points (`ValueError` below that) and the F022
   table publishes pesos yields at 2, 5 and 10 years only (the 1-year series has no value after 2025-12-24). The bake adds the monetary policy rate
   (`F022.TPM.TIN.D001.NO.Z.D`, the Central Bank's overnight rate) as the fourth point at 1/360 year and says so in the `source` of the curve and in a
   finding. It is a policy rate, not a secondary-market yield, while the contract fixes `observed_kind` at `secondary-market-yield`. Alternatives:
   a curve without a Nelson-Siegel fit (the contract requires `fit`), an engine fit that accepts three points with a stated `tau`, or a `fit.model`
   value for an anchored fit. Recommendation: accept the anchor and add `policy-rate-anchor` to the contract's curve description.
2. **EaR and EVaR are not in the C15 documents.** The `c15-outputs` schema has no block for them (`additionalProperties: false`, and the `dynamic_nii`
   description says the EaR and EVaR wait for the BCCh curves, which are now available). A field the bake cannot fill is a question, not a schema change
   (ADR-0080). Proposed amendment: add `ear_evar` to `c15Outputs` with the shape of C14's block (method, number of paths, seed, horizon, parameters,
   levels with `ear`, `evar`, `ear_se`, `evar_se`, `mc_error_method`, `n_batches`) and its semantic check; the engine functions exist
   (`hw1f_scenarios`, `ear_evar`, `ear_evar_mc_error`).
3. **The floors never bind on the September 2026 curves.** The smallest distance between a post-shock rate and its floor is 20 bp (UR delta NII,
   parallel decrease); the `floors-active` variant therefore carries no effect row and states the distance. A variant that makes the floors bind
   needs a curve the Banco Central did not publish, so it is not made up.
4. The valuation date is 2026-09-03 because the 30-year UF yield and one pesos tenor have no value on later days; the CMF aggregates are those of
   August 2026, published on 2026-09-29, after the valuation date.
5. The yields are read as semiannual bond-equivalent par yields (UNVERIFIED against the Banco Central's methodology note); the prepayment
   multipliers are tabled and not applied per shock (the outstanding notional of SRP31.121 is UNVERIFIED in the engine contract); the floor is the
   single number of the contract; the dynamic NII of the UR leg carries the real rate only, so the 12-month margin of the thresholds is understated.
6. No hedge is modelled; a Chilean bank closes most of its UF position with derivatives, so the net UF position of a variant is larger than a hedged
   bank's. Tier 1 is the equity of the CMF aggregate (a synthetic proxy).
