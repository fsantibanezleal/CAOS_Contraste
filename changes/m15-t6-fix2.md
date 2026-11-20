- Units gate, second fix of the constant baseline: the three code findings of the re-review are rewritten against their source, each
  with a test (`tests/test_t6_code_findings.py`): a C20 subsample run records the declared range of each observable and compares none
  with a stand-in interval of its own; the C02 and C21 expected ranges are chosen by an explicit key prefix and an unknown key raises;
  the C15 page reads the EVE threshold from the model's `THRESHOLDS`.
- The three remaining `RUN_MS` timeouts (C01, C04, C05) are `run-budget`; the 197 units that hedged with "or" are one unit per literal;
  the 939 entries confirmed from their code line were reread in their enclosing functions and corrected where their unit, class or
  reason was not their own (the re-review's error kinds swept over the whole baseline). Three new guards in
  `tests/test_unit_constants.py` (no unit with the word "or", every `RUN_MS` a `run-budget`, no entry for the removed literals).
- The baseline holds 2,083 entries for 2,083 literals (202 modules).
