# Cases: the taxonomy and the coverage matrix

Twenty-two cases in eleven categories ([the SDD](../design/SDD.md) section 5). Each case states its question, its
data and their licence class, the truth status of every variant, its leakage-safe split and the ranges a reader should
see, checked at bake time. The App shows one case at a time; Experiments and Benchmark read across them.

## Categories

| Category | Why it exists |
|---|---|
| credit-scoring | the most common model and the validator's daily work |
| ratings-calibration | the IRB core and the low-default reality |
| provisions | IFRS 9 and the Chilean carve-out |
| lgd-ead | the other two risk parameters |
| portfolio-capital | what Pillar 1 ignores and ICAAP must cover |
| market-ccr | VaR and ES, exposure, FRTB |
| balance-sheet | IRRBB and liquidity, the 2023 lessons |
| operational | why the advanced measurement approach went away |
| capital-stress | ICAAP, IAPE and the supervisory models |
| ml-ai-risk | the validation and fairness of machine-learning models |
| validator | the size and power of the tests themselves |

## Coverage

| Case | Category | Data (class) | Truth status | Unit | Status |
|---|---|---|---|---|---|
| [C01](C01.md) retail cards PD, champion vs challenger | credit-scoring | UCI Taiwan, German twin (mirror-allowed) | real outcomes; perturbed variants as known truth | U1 | built |
| C02 corporate PD across 1 to 5 year horizons | credit-scoring | UCI Polish bankruptcy (mirror-allowed) | real outcomes | U14 | planned |
| C03 SME PD by vintage through 2008 | credit-scoring | SBA 7(a) FOIA (mirror-allowed) | real outcomes | U6 | planned |
| [C04](C04.md) rating transitions and TTC PD by grade | ratings-calibration | ESMA CEREP (mirror-allowed), three papers (derived-only), a CTMC generator | real aggregates, published answers, known truth | U4 | built |
| [C05](C05.md) low-default portfolios and PD calibration | ratings-calibration | Tasche (2013) and Pluto and Tasche (2005), their tables (derived-only); a Vasicek generator | published answers, known truth | U2 | built |
| C06 mortgage lifetime PD, IFRS 9 staging and ECL | provisions | Freddie Mac (derived-only), Fed scenarios; SBA twin | real outcomes | U5 | planned |
| C07 Chile provisions trilogy: CMF B-1, IFRS 9, BdE Annex 9 | provisions | synthetic Banco Andino calibrated to CMF aggregates | synthetic calibrated | U5 | planned |
| C08 LGD and downturn LGD | lgd-ead | Freddie Mac loss fields; SBA charge-off twin | real outcomes | U6 | planned |
| C09 EAD and CCF for revolving lines | lgd-ead | a generator shaped on the Fed card portfolios | known truth | U6 | planned |
| C10 portfolio credit capital: ASRF, Vasicek fit, copula MC | portfolio-capital | Fed charge-off rates, FDIC failures, a simulator | real aggregates, known truth | U7 | planned |
| C11 market VaR/ES backtesting across 2008, 2020, 2022, 2023 | market-ccr | Kenneth French (derived-only), Treasury, H.10 | real outcomes | U8 | planned |
| C12 swap exposure, CVA and SA-CCR | market-ccr | Treasury curves, synthetic trades; ORE | real market, synthetic trades | U9 | planned |
| C13 FRTB desk eligibility: PLA and desk backtesting | market-ccr | a generator with planted model deficiencies | known truth | U8 | planned |
| C14 IRRBB six shocks on a USD balance sheet (SVB 2022) | balance-sheet | FDIC call reports, the Treasury curve | real aggregates, synthetic behaviour | U10 | planned |
| C15 IRRBB on a CLP/UF balance sheet (RAN 21-13 Annex 1) | balance-sheet | CMF, BCCh F022, Banco Andino | real aggregates, synthetic bank | U10 | planned |
| C16 liquidity stress, LCR and the March 2023 run | balance-sheet | FDIC, H.8, the Fed SVB review, a depositor generator | real event, synthetic deposits | U11 | planned |
| C17 operational risk: LDA vs SMA | operational | a generator calibrated to BCBS LDCE 2008 | synthetic calibrated | U12 | planned |
| C18 ICAAP and IAPE capital aggregation under macro scenarios | capital-stress | Fed 2026, EBA/ESRB 2025, NGFS paths; Banco Andino | real paths, synthetic bank | U13 | planned |
| C19 supervisory stress model replication (known answer) | capital-stress | Fed hypothetical portfolios and published loss rates | published answers | U13 | planned |
| C20 ML model validation: drift, robustness, explanation stability | ml-ai-risk | UCI, SantanderAI SGCD, Fed portfolios as shift probes | real outcomes, known shifts | U14 | planned |
| C21 fair-lending disparity testing | ml-ai-risk | HMDA (mirror-allowed) | real decisions | U14 | planned |
| [C22](C22.md) validating the validator: size and power of every test | validator | riskvalidation's generators with planted defects; WP14 and Yurdakul-Naranjo tables (derived-only) as published answers | known truth | U3 | built |

A case page is written in the unit that builds the case, from [00_TEMPLATE.md](00_TEMPLATE.md).
