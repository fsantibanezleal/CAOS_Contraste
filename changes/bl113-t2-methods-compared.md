- 1.01.000 BL-113 T2: the methods-compared document `data/derived/benchmark/methods-compared.json` (contract `benchmark-methods` 1.0.0, api 41.0.0), written by
  `python -m pipeline.benchmark.methods` from `data-pipeline/`. Twelve questions (Q1 to Q12), each method with its standing read from the SDD Method ladder, every value
  copied from a committed case document or manuscript result file with its path, JSON pointer and SHA-256, every best method and every reading generated from the
  numbers by the declared rule of each metric; a cell the product does not compute is null with its reason and its backlog row (BL-119); Q13 and Q14 are listed as not built.
- Feature folder `docs/design/features/benchmark-methods/` (requirements BM-001 to BM-012 with their adversarial checks) and `tests/test_benchmark_methods.py`; the index
  builder (`pipeline.pipeline.served_files`) lists the document, so the next index rebuild carries it.
- BL-113 T2 correction after the reader review of the technical report (requirements BM-013 to BM-016): the Kupiec and conditional-coverage p-values of all 18 models
  of Q1 are copied from the `tests` of each case document (filled cells 1,529 to 1,694 of 1,844; a test the document does not evaluate is null with the note the
  document gives); no metric whose value is a p-value is ranked (Q1 Kupiec and conditional coverage, Q5 Spiegelhalter); the no-change column of the median first-flag
  day of Q2 is a context metric of its own and the planted columns keep the lower-is-better rule; the Q12 reduction names the mean signed bias, the Q8 control note
  no longer denies its ladder standing, and a reading closes the note of an unranked row with a full stop. Contract `benchmark-methods` stays 1.0.0 (no field, no enum change).
- The technical report's methods-compared tables are regenerated: a column prints the digits that tell a best cell from a cell that would round to it, and the readings of
  questions 1, 2, 8, 10 and 12 are rewritten on the corrected document (the e-backtest comparison is pointed to, not denied).
