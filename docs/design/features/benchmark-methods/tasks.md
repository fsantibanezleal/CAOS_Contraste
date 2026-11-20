# Tasks: BL-113, the methods compared (the document, its contract and its page)

This feature is stated by [`requirements.md`](requirements.md), designed in [`design.md`](design.md) and checked adversarially in
[`validation.md`](validation.md). The unit that writes the document and its contract is T2; the page and the pointers are T3 and T4,
each a brief of the main session, test first.

| Task | What | Depends on | State |
|---|---|---|---|
| T1 | Sizing, read only: each question against the SDD ladder and the committed documents, with the JSON path of every metric (CAOS_MANAGE `wip/contraste/bl113-t1-sizing-2026-11-15.md`). | none | done |
| T2 | This folder; the step `data-pipeline/pipeline/benchmark/methods.py`; the contract `benchmark-methods` 1.0.0 and the api contract 41.0.0; `data/derived/benchmark/methods-compared.json`; the determinism, cited-value, coverage, one-run, reading-rule, standing-from-the-SDD, internal-names and contract tests; the index builder lists the document. | T1 and the tier ruling of BL-116 in the SDD | done |
| T3 | The Benchmark page: an overview tab "Methods compared" in the reading group and each question's table and chart in its case's tab, in both languages, with no tier word; vitest; the shell gate over every state. | T2 | done |
| T4 | The Introduction and Experiments pages point at the group; the technical report reads it (with the report's own unit). | T3 | done (the pointers; the technical report reads it with the unit report-1-01-000-delta-2026-11-19) |

## Open items the document states

- Q2: the published e-backtest has no row in the SDD ladder (M-39, backlog BL-121), so it is listed in the question's `absent` and its cells are not shown.
- The twelve computations the sizing lists (K-1 to K-12, backlog BL-119): each empty cell says which one fills it.

## Convergence verdict

The verdict of this feature is generated, never written by hand. Every requirement of [`requirements.md`](requirements.md) has its row,
with its gate and the gate's result in the release run, in [`../release-1-0/verdict.md`](../release-1-0/verdict.md).
