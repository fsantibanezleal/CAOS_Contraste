# Tasks: U2, C01's IRB capital

| # | Task | Requirement | State |
|---|---|---|---|
| 1 | Read the transactor definition and the retail floors at the primary sources; persist them (Contraste dossier 11) | CT-214, CT-216 | done |
| 2 | The capital at unit LGD along the cut-off curve, per regime, from the engine (cached by distinct PD); the class, floors, scaling, EAD convention and references in the artifact | CT-212, CT-213 | done |
| 3 | The transactor sensitivity for the Taiwan cards: the six-month full payers counted, and their capital as transactors | CT-214 | done |
| 4 | Parity points of the retail functions exported with the artifacts; the TypeScript retail functions held to them | CT-215 | done |
| 5 | The Capital sub-view of the Impact group: the three regimes, both models, money and share of EAD, the difference, the sensitivity, the Basel III LGD floor flag, the curve against the approval rate | CT-215, CT-216 | done |
| 6 | Docs: the C01 case page and design, the SDD map, the framework card, the changelog | - | done |
| 7 | The canonical bake, the measured gate over the whole matrix, screenshots read in light and dark | CT-217 | done |

## Convergence verdict (2026-10-05)

Converged. The canonical bake gives every rung of every variant its capital at unit LGD under the three regimes; the
expected ranges hold (the scorecard's whole holdout book needs 8.0% of its EAD at LGD 50%; the transactor effect is
zero). The 87 pipeline tests (one skipped by design) and the 98 web tests pass, the retail parity points among them,
with every guard; `caos-shell-gate: OK, 707 measured states`. C05's artifacts changed only their code version, and
C01's only by the new capital fields and the version.

The first gate failed 26 states on the new view: a capital card that filled the panel drew on 11% to 23% of its stage
(a three-row table beside long notes), and the notes once squeezed the table out of a scrolling card altogether. The
numbers now sit at their own height across the instrument and the curve fills the rest, as the Decision view does.

Open: CRR3's LGD input floors (Article 164(4)) are not read, since EUR-Lex was unavailable; the floors belong in the
engine's regime data (BL-053). The EAD is the drawn balance only.
