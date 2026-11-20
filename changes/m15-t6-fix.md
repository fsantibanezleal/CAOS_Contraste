- Units gate, constant baseline fix after the review of T6: every listing-classed entry of `scripts/unit_constants_baseline.json` (1,508)
  reread in its own code line; 570 of the 2,067 entries changed (398 in class); a literal sharing a line with another unit is classified
  one by one; a reason that quotes code must quote its literal's line (new test).
- The closed class list gains `stated-assumption` (a case assumption with a unit and no source) and `run-budget` (a wall-clock or
  iteration limit of a run); `source-cited-input` keeps only literals whose source the file cites; `unit-conversion` only true conversions.
- Three page modules that compute values (`cases/c15/page`, `cases/c08/page`, `cases/c11/page`) move from `outside` to `method`
  with their 19 literals classified (175 method, 27 parameter, 75 outside; 2,086 literals).
- `scripts/smoke.ps1` exits with the failing check's exit code under Windows PowerShell 5.1 (it exited 0 before); tested under
  `powershell.exe`.
