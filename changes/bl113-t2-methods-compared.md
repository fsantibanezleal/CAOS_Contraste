- 1.01.000 BL-113 T2: the methods-compared document `data/derived/benchmark/methods-compared.json` (contract `benchmark-methods` 1.0.0, api 41.0.0), written by
  `python -m pipeline.benchmark.methods` from `data-pipeline/`. Twelve questions (Q1 to Q12), each method with its standing read from the SDD Method ladder, every value
  copied from a committed case document or manuscript result file with its path, JSON pointer and SHA-256, every best method and every reading generated from the
  numbers by the declared rule of each metric; a cell the product does not compute is null with its reason and its backlog row (BL-119); Q13 and Q14 are listed as not built.
- Feature folder `docs/design/features/benchmark-methods/` (requirements BM-001 to BM-012 with their adversarial checks) and `tests/test_benchmark_methods.py`; the index
  builder (`pipeline.pipeline.served_files`) lists the document, so the next index rebuild carries it.
