- U6 integration: the contract descriptors of C03, C08 and C09 are composed in `frontend/src/lib/contract.types.ts`
  (their partial-key rows stay `json`), so `contract.test.ts` checks the committed artifacts of the three cases again.
- Experiments groups its case tabs by the question family (credit scoring and PD, provisions, loss severity and
  exposure, validating the validator), so no tab row holds more than six peers (ADR-0071 rule 5).
- Experiments and Benchmark read C03, C06, C07, C08 and C09 from their own artifacts (`pages/U6Sections.tsx`): one
  headline row per variant, and a rung comparison per variant for C03, C08 and C09. Before, these cases went through the
  C01 scorecard table and showed "not available" in every cell. A case with no outside file no longer reads "It reads ,".
- Methodology: the LGD and EAD topic has a group of its own, "Loss severity and exposure".
- The vendored template checks move from 0.05.000 to 0.07.000: `check_sdd.py` validates the executive view against
  the shell's schema 2.0.0, `check_live.py` and `check_template_residue.py` know the `/app` route and the example
  executive view, and `tests/test_guards.py` covers the residue marker. `.template-version` is 0.07.000.
