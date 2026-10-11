# Guide: read a validation report

Every test in Contraste, in a case's artifact or in your own report ([guide 02](02_validate-your-own-model.md)), is
one `TestResult` from the engine `riskvalidation`. This guide reads one row, then the lights, then the findings.

## One row

The portfolio Jeffreys test of the champion on the C01 holdout (`data/derived/C01/holdout.json`, key `tests`):

| Key | Value | Meaning |
|---|---|---|
| `test_id` | `pd.jeffreys` | the test, as the engine names it |
| `model_id`, `segment` | `P1-scorecard`, `portfolio` | the model and the population tested (a grade `G01` to `G12`, or `characteristic:<name>` for an input's CSI) |
| `h0`, `alternative` | the PD applied is at least the true PD; the true PD exceeds it | the hypotheses, in words |
| `statistic`, `p_value` | 0.2212 (the observed default rate), 0.3095 | for a descriptive measure (AUC, Brier, ECE) the value is in `metric` and there is no p-value |
| `n`, `n_events` | 9,000 obligors, 1,991 defaults | the size of the evidence |
| `alpha_amber`, `alpha_red`, `policy_version` | 0.05, 0.01, `riskvalidation-default 2026.10.0` | the policy that classified it |
| `light` | `green` | the classification under that policy |
| `reference` | ECB (2019), section 2.5.3.1; Brown, Cai and DasGupta (2001) | the primary source that defines the test |
| `inputs_hash` | SHA-256 | a fingerprint of the inputs, so a result can be matched to its data |
| `extras` | the PD applied, the default rate, the posterior interval | what the views draw |

Read it as: on 9,000 obligors the champion assigned an average PD of 21.91% and 22.12% defaulted; under a Jeffreys
prior the posterior probability that the true rate is below the applied PD is 0.31, so there is no evidence of
under-estimation.

## The lights are policy, not regulation

Green, amber and red come from the thresholds in the engine's versioned policy file: conventional 5% and 1%
significance levels for the hypothesis tests, and for the PSI the Yurdakul-Naranjo benchmark, with the 0.10 and 0.25
rule-of-thumb bands reported beside it. The ECB's IRB validation instructions and BCBS Working Paper 14 set no pass
or fail thresholds; an institution replaces the file with its own policy. The web labels every threshold as policy
unless the artifact carries a regulatory paragraph for it (CT-104), and the App's policy section lets you move the
amber and red levels and re-lights every committed result the same way the engine does. A light that is
`not_evaluated` means the policy holds no threshold for the test (a descriptive measure) or the statistic is
undefined (a grade with no obligors); `error` means the test raised, with the exception in `notes`.

## Findings and severity

A case turns its lights into findings with its own severity policy. In C01:

| Family | Tests | Red | Amber |
|---|---|---|---|
| calibration level | Jeffreys, binomial, Vasicek-adjusted binomial | S2 | S3 |
| calibration fit | chi-square over grades, Hosmer-Lemeshow, Spiegelhalter | S3 | S4 |
| stability | PSI | S2 | S3 |
| discrimination | AUC against the initial validation | S2 | S3 |

The level weighs more than the fit: at thousands of obligors the fit tests reject deviations too small to matter,
and BCBS WP14 warns that they under-state their type I error when defaults are correlated. On the C01 holdout,
Hosmer-Lemeshow rejects the champion (p = 0.005) while its level is right, so the finding is S3, not S2. Design
limits and data-quality flags are findings too: no out-of-time validation is possible on a single snapshot (S3,
accepted), and the codes outside the codebook are kept as their own bins (S4, accepted).

Every finding names its evidence, and every piece of evidence resolves: `pd.jeffreys@P1-scorecard` is a test row of
the same artifact, `contract:C01-PAY-CODE` a contract-1 rule of the case's inputs, `design:single-snapshot` a stated
limit of the design. Contract 2 refuses a finding whose evidence does not resolve.
