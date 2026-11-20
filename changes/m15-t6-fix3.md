- Units gate, third fix of the constant baseline: the eight entries of the third review corrected (the four C22 `SWAP` reasons, C15
  `cpi` as `stated-assumption`, the two C12 `IID_CRITICAL` as `ratio`, C13 `ecdf_step` as `probability`) and three sweeps of the same
  error kinds over the whole baseline; the C02 planted run records its declared ranges and compares none, with its test and
  strengthened guards in `tests/test_t6_code_findings.py`.
- The 38 units that listed several meanings are one unit each, the hedged reasons name one role, and four new guards in
  `tests/test_unit_constants.py` refuse a unit with "as its key", a semicolon or a parenthesised list, a reason that hedges with "or",
  a dimension on a `ratio` or `probability`, and a `stated-assumption` that says dimensionless. 2,083 entries for 2,083 literals.
