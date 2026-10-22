- The U15 governance fixtures and the engine-governance-api worked examples follow the 1.0 documents (engine-governance-api 1.1.2, a patch):
  84 findings, 42 distinct, open-high-severity (5, 42, 5, 9), findings_overdue n 50 metric 0.1400; the golden tests and the governance
  workbench test pin the regenerated counts.
- The governance fixture builder reads the 1.0 packaged battery labels (`contraste-<battery> X.Y.Z`): the extract copies the policy file's entries for the
  tested ids, and every report-fixture policy identity equals `resolve_policy` of the engine.
