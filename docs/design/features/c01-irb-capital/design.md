# Design: U2, C01's IRB capital

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md); the case's own design,
[`../c01-retail-pd/design.md`](../c01-retail-pd/design.md), whose impact section promised this. Sources: Contraste
research dossier 01 (sections A.3 to A.5 and L: the retail functions, the floors and the scaling factor, read from
the Basel Framework and CRR3), CRR3 Article 4(1), point (152), for the transactor (read 2026-10-05), and the engine
pages of `riskvalidation` 0.2.0 on the IRB calculators.

## The question

What capital does each model's approved book require, and how far does the choice of model move it at the same
approval rate? The decision view already prices the approved book in expected loss; capital is the other half of its
cost.

## The exposure classes

- **Taiwan** (UCI Default of Credit Card Clients): credit-card balances of individuals, qualifying revolving retail
  (QRRE), with $R = 0.04$ (CRE31.15) in the retail function
  $K = LGD\cdot N\big(G(PD)/\sqrt{1-R} + \sqrt{R/(1-R)}\,G(0.999)\big) - PD\cdot LGD$ (CRE31.13), which has no maturity
  adjustment.
- **German twin** (UCI Statlog German Credit): instalment loans to individuals, other retail, with
  $R = 0.03\,\frac{1-e^{-35PD}}{1-e^{-35}} + 0.16\,\big[1-\frac{1-e^{-35PD}}{1-e^{-35}}\big]$ (CRE31.16).
- **Revolvers and transactors.** Basel III defines transactors as "obligors in relation to facilities such as credit
  cards and charge cards where the balance has been repaid in full at each scheduled repayment date for the previous
  12 months" (BCBS d424, standardised approach, paragraph 56), and in the IRB approach "All exposures that are not QRRE
  transactors are QRRE revolvers" (d424, IRB paragraph 25); CRR3 Article 4(1), point (152), also asks for at least
  twelve months of repayment history. The Taiwan data record six months (April to September 2005, `PAY_0` to
  `PAY_6`), so no account can be shown to be a transactor: every card is a QRRE revolver, whose PD floor is the higher
  one. The sensitivity treats as transactors the accounts that repaid in full or did not
  use the card in all six months (codes -1 and -2): 5,195 of the 30,000 (17.3%), whose default rate is 14.2%, so the
  floor rarely binds for them.

## The parameters, by regime

| | Basel III final | CRR3 | Basel II |
|---|---|---|---|
| PD floor, QRRE revolvers | 0.1% (d424 IRB paragraph 121; CRE32.58) | 0.1% (Articles 160 and 163) | 0.03% (old CRE32.51) |
| PD floor, QRRE transactors and other retail | 0.05% (same) | 0.05% | 0.03% |
| Scaling factor | none (CRE31.5) | none (Article 153(1)) | 1.06 (old CRE30.4) |
| LGD input floor, QRRE | 50% (d424 IRB paragraph 121 and its table; CRE32.58) | Article 164(4), not read: EUR-Lex was unavailable on 2026-10-05 | none |
| LGD input floor, unsecured other retail | 30% (same; CRE32.59) | as above | none |

The engine holds the PD floors and the scaling factor as regime data; it takes the LGD as given. The capital view uses
the rail's LGD (default 50%, the QRRE floor) and says when it lies below the Basel III input floor (CT-216); for CRR3
it states no number until Article 164(4) is read (Contraste dossier 11). Moving the input floors into the engine's
regimes is backlog work.

**EAD**, as in the decision view: the current bill (`BILL_AMT1`, floored at 0) for the cards and the credit amount for
the German loans. It is the drawn amount only: an undrawn limit would add a conversion factor times the undrawn line
(the own-estimate EAD floor uses 50% of the standardised factor, CRE32.64), so the level of the capital is understated
while the comparison of two models at the same approval rate keeps its direction.

## The computation

Along the 51 cut-offs of the existing cut-off curve, for every rung and variant and each regime $r$:

$$C_r(c) = \sum_{i:\,PD_i \le c} K_r(PD_i;\ LGD = 1)\; s_r\; EAD_i,$$

the capital (8% of the RWA) at unit LGD, with $s_r$ the scaling factor. Retail capital is linear in the LGD, so the
capital at the rail's LGD $L$ is $L\,C_r(c)$, exactly. $K_r$ is riskvalidation's `capital_requirement`, cached by
distinct PD (a calibration map is a step function). The variant artifact carries, per rung, `capital_per_lgd` by
regime beside `pd_ead` and `ead`, and for Taiwan `capital_per_lgd_transactors`; `outputs.irb` states the class, the
floors, the scaling, the EAD convention, the references and the number of six-month full payers.

## The web

The Impact group gets two sub-views: **Decision** (unchanged) and **Capital**. Capital shows, at the rail's approval
rate and LGD, the capital of the champion and the challenger under the three regimes, in money and as a share of the
EAD, the difference between the two models, and the transactor sensitivity; and a chart of the capital against the
approval rate under Basel III for both models. The parity points of the retail functions (QRRE revolver and
transactor, other retail, three regimes) are exported with the artifacts and held to 1e-9 (CT-215).
