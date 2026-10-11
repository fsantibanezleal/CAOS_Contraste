# The live lane

What the web recomputes in the reader's browser, from the committed artifacts alone, and what holds each to the
pipeline:

| Live computation | Code | Held by |
|---|---|---|
| An applicant's scorecard points, score and PD: the row of each characteristic's points table (numerical bins `[split_(i-1), split_i)`, category sets, the zero-WoE "Missing" row for anything else), the sum of the integer points, and the logistic of the intercept plus the coefficients times the WoE | `frontend/src/engine/scorer.ts` | `frontend/src/engine/parity.test.ts`: points and scores exactly, PDs within 1e-9, on the 50 sampled applicants of every variant that carries them |
| An applicant's EBM logit: the intercept plus each term's score at the applicant's bins (main terms at level 0, pairs at level 1) | `frontend/src/engine/scorer.ts` | the same test: logits within 1e-9 |
| Every light under the reader's policy: red if p < red, amber if p < amber, green otherwise, the rule of `riskvalidation`'s `Threshold.classify` for kind `p_value` | `frontend/src/lib/policy.ts` | the same test: under the committed alphas every committed light is reproduced |
| The decision at the reader's approval rate and LGD: the bad rate, the expected loss (LGD times the sum of PD times EAD) and the exposure of the approved, interpolated on the committed cut-off curves | `frontend/src/workbench/model.ts` (`atApproval`) | the swap-set table at 80% approval, computed applicant by applicant by the pipeline, shown beside it |
| C01's capital at the reader's approval rate and LGD: the pipeline commits each book's capital at unit LGD along its cut-off curve under each regime; retail capital is linear in the LGD, so the view multiplies and interpolates, exactly | `frontend/src/workbench/CapitalView.tsx` | `frontend/src/engine/credit.test.ts`: the retail risk weight equals `regulatory.irb` on the points C01 exports (CT-215) |
| C05's PD curve of each case 1 approach at a reader's forecast PD (Tasche 2013, quasi moment matching), the most prudent bounds at a reader's confidence and correlation (Pluto and Tasche 2005) and the IRB capital of each by regime | `frontend/src/engine/credit.ts` (`calibrate`, `qmm`, `mostPrudent`, `mostPrudentScaled`, `irbCapital`) | `frontend/src/engine/credit.test.ts`: `engines.pd_curve`, `engines.low_default` and `regulatory.irb` on the points C05 exports, 1e-9 relative (CT-209) |
| C22's exact size and power of the binomial, Vasicek-corrected binomial and Jeffreys tests for a reader's portfolio: the critical count under the PD applied and the tail of the count's true distribution there | `frontend/src/engine/sizepower.ts` | `frontend/src/engine/sizepower.test.ts`: `harness.exact.rejection_probability` and the tests' p-values on the points C22 exports, 1e-9 relative (CT-308) |
| C04's projection of a portfolio by grade under a one-year rating matrix with an origination mix (Engelmann 2024, the propagation (9)) and the TTC portfolio it drifts to (his Theorem 1); the Wald and Agresti-Coull intervals of a grade's PD at a reader's default correlation (Schuermann and Hanson 2004, (2.2), (3.3), (3.4)) and the Jeffreys interval; the IRB risk weight of a portfolio by grade under each default definition | `frontend/src/engine/transitions.ts` | `frontend/src/engine/transitions.test.ts`: `transitions.ttc`, `transitions.intervals` and `regulatory.irb` on the parity points of C04's models artifact, 1e-9 relative (CT-410, CT-411) |

Every threshold is labelled as policy, never as regulation, unless the row carries a regulatory reference
(`frontend/src/lib/labels.test.ts`, CT-104).

## Next: the engine in the browser

`riskvalidation` is pure NumPy and SciPy, so it can run in Pyodide and let a reader rerun any test with new
segments, windows or a master scale. It is admitted feature by feature, only when the gate measures its cold start
and run time in the browser and a parity test reproduces the committed value; it waits for the engine's first PyPI
release, from which Pyodide installs it (no wheel is committed to this repository).
