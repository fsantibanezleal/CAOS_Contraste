- Every red test ROW is cited by an open finding (R5 ruling 1): the generic step of `pipeline/core/red_findings.py` reads the
  rows the open findings cite (`cited_rows`), so a finding that cites one row of a test no longer covers its other red rows; the
  generic finding of a test cites its uncited red rows, and its title drops the developer clause.
- The C01 Findings view matches its evidence by the full row id (test, model and segment; `test@-@segment` and a bare test too), so
  a finding's evidence lines show the rows it cites and no other row of the same test.
- The C10 grid ladder prints its simulated-grid inputs on the LHP rung only; every other rung says it does not run on the simulated
  grid.
- The Spanish test references join their authors with "y" (Christoffersen y Pelletier, Engle y Manganelli); English titles keep
  their words.
- The C15 case page's results block is regenerated from the re-baked documents (the variant labels).
