# The live lane

What the web recomputes in the reader's browser, from the committed artifacts alone, and what holds each to the
pipeline:

| Live computation | Code | Held by |
|---|---|---|
| An applicant's scorecard points, score and PD: the row of each characteristic's points table (numerical bins `[split_(i-1), split_i)`, category sets, the zero-WoE "Missing" row for anything else), the sum of the integer points, and the logistic of the intercept plus the coefficients times the WoE | `frontend/src/engine/scorer.ts` | `frontend/src/engine/parity.test.ts`: points and scores exactly, PDs within 1e-9, on the 50 sampled applicants of every variant that carries them |
| An applicant's EBM logit: the intercept plus each term's score at the applicant's bins (main terms at level 0, pairs at level 1) | `frontend/src/engine/scorer.ts` | the same test: logits within 1e-9 |
| Every light under the reader's policy: red if p < red, amber if p < amber, green otherwise, the rule of `riskvalidation`'s `Threshold.classify` for kind `p_value` | `frontend/src/lib/policy.ts` | the same test: under the committed alphas every committed light is reproduced |
| The decision at the reader's approval rate and LGD: the bad rate, the expected loss (LGD times the sum of PD times EAD) and the exposure of the approved, interpolated on the committed cut-off curves | `frontend/src/workbench/model.ts` (`atApproval`) | the swap-set table at 80% approval, computed applicant by applicant by the pipeline, shown beside it |

Every threshold is labelled as policy, never as regulation, unless the row carries a regulatory reference
(`frontend/src/lib/labels.test.ts`, CT-104).

## Next: the engine in the browser

`riskvalidation` is pure NumPy and SciPy, so it can run in Pyodide and let a reader rerun any test with new
segments, windows or a master scale. It is admitted feature by feature, only when the gate measures its cold start
and run time in the browser and a parity test reproduces the committed value; it waits for the engine's first PyPI
release, from which Pyodide installs it (no wheel is committed to this repository).
