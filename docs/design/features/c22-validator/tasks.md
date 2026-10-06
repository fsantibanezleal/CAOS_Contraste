# Tasks: U3, case C22 (validating the validator)

| # | Task | Requirement | State |
|---|---|---|---|
| 1 | riskvalidation 0.3.0 (generators, harness, published reproductions) released; 0.3.1 (the Yurdakul-Naranjo offset stated) and 0.3.2 (exact Wilson bounds at 0 and n, found by this case) released; pinned to v0.03.002 | all | done |
| 2 | Contract 2: `rate:` evidence, the validator outputs in the TypeScript types (with each panel's own axis) | CT-305 | done |
| 3 | The C22 case module: eight variants, ladders, simulations with exact values, golden cells, impact, findings, expected ranges | CT-301 to CT-307 | done |
| 4 | C05 on the engine's `DefaultCounts`, its bake unchanged; C01's Hosmer-Lemeshow with G degrees of freedom and its AUC test with the development variance, re-baked | CT-311 to CT-313 | done |
| 5 | The live calculator: TypeScript ports, parity points over the rail's corners, tests | CT-308 | done |
| 6 | The C22 instrument: rail, Model, Validation, Impact, Findings, Variants, Context; C22's sections of Methodology, Experiments and Benchmark | CT-309 | done |
| 7 | Docs: the case page, the SDD map, the changelog; the canonical bake twice; the measured gate; screenshots read | CT-306, CT-310 | done |

## Convergence verdict (2026-10-06)

Converged. Two C22 bakes are byte-identical, file by file; C05's artifacts differ from 0.03.000 only in their version
fields; C01 changed as the two corrections predict (Hosmer-Lemeshow's p rises with G degrees of freedom, the AUC test's
p rises with the development variance) and nothing else. Every expected range holds. The pipeline tests, the web
tests and every guard pass.

The measured gate passes: `caos-shell-gate: OK, 737 measured states` over every route, tab and case at five sizes,
both themes and both languages, and `OK, 417 measured states` on the App route after the last view edit, run from
the shell's tagged 0.7.3 source until 0.7.3 is on npm (under 0.7.2's gate the four false failures of known shell
defect 25 remain). The screenshots were read in light and dark, English and Spanish, at 1280, 1600 and 2560 px.

What the build had wrong, each fixed at its source:

- Expected ranges declared before the first bake were guesses in two places (the Jeffreys 80% ratio; the
  Yurdakul-Naranjo count, which depends on the seed through a systematic offset of about 0.65 SE); corrected after it
  and stated.
- The engine's Wilson interval was not exact at zero rejections (riskvalidation 0.03.002, CAOS_RiskValidation#18).
- The live calculator's binomial tail ran every term when its first term underflowed: 13 to 15 s of blocked page per
  move at 10,000 obligors, now about 10 ms; its parity points now span the rail's knobs to their corners (564).
- The development panel's x was not monotone and its two series had different lengths; each panel now carries its
  own axis, and says whether its rates are power against a planted defect or sizes where the model is right (the
  clustering family, drift's calibration panel, the development AUC, the DeLong designs): the first versions counted
  false alarms as power in Benchmark's verdict.
- The first gate run failed 167 of 737 states: seven peer tabs on Methodology (now grouped by the reader's question),
  the C22 rail scrolling at 1280x800 (now two compact sections, every panel of a family drawn at once instead of a
  panel control), C22's Variants underfilling (now the detection matrix), C01's Findings underfilling on a very wide
  screen (the evidence now drawn beside the table). Four failures were the gate's own (known shell defect 25: its
  pointer probe pushed an element with less slack than its 8px margin out of its scroll container), fixed in the
  shell first (0.7.3, CAOS_APP_SHELL#56).
