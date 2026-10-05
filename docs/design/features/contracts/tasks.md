# Tasks: U0, the contracts, the sources and their licences

| # | Task | Requirement | State |
|---|---|---|---|
| 1 | The eight family contracts with fields, units, ranges, cross-field rules, reject and flag policy; export to `data/derived/contract/` | CT-001 | done |
| 2 | The source registry from dossier 08 (every source, class, verbatim licence fragment, cases) | CT-009 | done |
| 3 | The fetcher: data root outside the repository, SHA-256 streaming, the licence manifest, hash pinning, manual placement | CT-008, CT-010, CT-011 | done |
| 4 | Lineage and the export refusal; provenance written from the lineage | CT-002, CT-003 | done |
| 5 | The TypeScript mirror of contract 1 and contract 2 and its two-way test | CT-004 | done (contract 2 with the C01 artifacts, U1) |
| 6 | `scripts/check_licences.py` and the licence table | CT-005 | done |
| 7 | `scripts/check_data_classes.py` | CT-006 | done |
| 8 | Fetch every direct-download source a case of U1 to U3 reads, and record it in the manifest | CT-008 | the four UCI datasets fetched and pinned (2026-10-05); each later unit fetches its own sources |
| 9 | Remove the template's example from the pipeline, the tests and the data | (residue guard) | done (the web example went with U1) |
| 10 | The bring-your-own-model door: `data-pipeline/validate.py` (contract 1, the master scale and the battery on a reader's scored sample, an optional development sample, the report outside the repository) and the two known-truth examples in `data/examples/` | CT-012, CT-013, CT-014 | done |
