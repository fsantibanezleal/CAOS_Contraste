# Requirements: U2, C01's IRB capital (qualifying revolving retail and other retail)

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.

| ID | Requirement | Gate |
|---|---|---|
| CT-212 | THE C01 impact SHALL give, for every rung and variant, the IRB capital of the approved book along the approval rate under Basel III final, CRR3 and Basel II, for the exposure class of the data (qualifying revolving retail for the Taiwan cards, other retail for the German loans), stating the class, the PD floor, the scaling factor, the EAD convention and the paragraph references it used. | `tests/test_c01.py::test_irb_capital_states_its_assumptions` |
| CT-213 | THE capital the bake computes at every cut-off SHALL equal the sum, over the approved accounts, of riskvalidation's capital requirement at unit LGD times the EAD, within 1e-9 relative; the artifact carries it to nine significant digits. | `tests/test_c01_capital.py::test_capital_curve_sums_the_engine` |
| CT-214 | THE Taiwan cards SHALL be treated as QRRE revolvers, because the Basel framework and CRR3 define a transactor by twelve months of repayment history and the data hold six; THE impact SHALL report the number of accounts that repaid in full or did not use the card in all six months, and the capital if they were transactors. | `tests/test_c01.py::test_transactor_sensitivity_reported` |
| CT-215 | WHERE the web recomputes the capital at the rail's LGD, THE result SHALL equal the committed capital at unit LGD times that LGD (retail capital is linear in the LGD), and the TypeScript retail functions SHALL equal the engine on exported parity points within 1e-9 relative. | `frontend/src/engine/credit.test.ts` |
| CT-216 | WHEN the rail's LGD lies below the Basel III LGD input floor for the class (50% for QRRE, 30% for unsecured other retail; BCBS d424 IRB paragraph 121), THE capital view SHALL say so beside the Basel III number, and SHALL state no CRR3 floor until Article 164(4) has been read. | `frontend/src/workbench/workbench.test.tsx` |
| CT-217 | WHEN the measured gate walks C01's Impact group at five sizes, both themes and both languages, THE site SHALL pass every check. | `frontend/scripts/gate.mjs` (G1 to G9) |
