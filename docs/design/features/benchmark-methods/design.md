# Design: BL-113, the methods compared across the questions of the benchmark

Status: live. Transcribed from the draft of CAOS_MANAGE `wip/contraste/bl113-methods-compared-design-2026-11-15/design.md` and the accepted
sizing `wip/contraste/bl113-t1-sizing-2026-11-15.md` (its D1 per question, D2 and D3), with the decisions of the main session of 2026-11-15
and 2026-11-16. Contract: `benchmark-methods` 2.0.0 (`docs/contracts/schemas/benchmark-methods.schema.json`). It closes gap 1 of the M12
audit: the binding rule asks that the benchmark compare the long-established, recent published and proposed methods on the same data and
protocol, and today only C11 ranks them on one protocol, inside its own Compare view.

## What it is

A document, `data/derived/benchmark/methods-compared.json`, that answers for each question "which method does better, under one protocol?"
for the methods Contraste runs on it. The step recomputes nothing: it reads the committed case documents (`data/derived/`) and the committed
manuscript result files (`manuscripts/<slug>/experiments/`), copies each number from a named JSON path, and records the file's repository
path, the RFC 6901 pointer of the value and the SHA-256 of the file (line endings normalised to LF) beside it. A test re-reads every cell, so
a re-baked case whose numbers move fails until the step is rerun.

The task T3 renders it: an overview tab "Methods compared" in the reading group of the Benchmark page (one row per question, its protocol in
one line, the best method per metric by the declared rule, whether a method proposed in this work is the best, a link to the question's
section, the reasons why Q13 and Q14 are not built) and each question's table and chart in the tab of its case (Q1 in C11, Q2 in C22, Q3 in
C13, Q4 in C04, Q5 and Q12 in C01, Q6 in C06, Q7 in C08, Q8 in C17, Q9 in C14, Q10 in C16, Q11 in C20). The page has six groups, the bound of
ADR-0071, so no seventh group is made.

## The questions

| Q | Question | Case | Runs (protocol and seed) | Metrics (rule) |
|---|---|---|---|---|
| Q1 | VaR and ES forecasts in stress windows | C11 | one rolling schedule, six windows, seed of the documents | FZ0 at two levels (lower), exceedances (nearer the expected count), Basel zone (order), Kupiec and conditional-coverage p (context: a p-value is evidence against a null, never ranked) |
| Q2 | Monitoring calibration and back-tests over time | C22, C11, C03 | four runs: case generator (seed 42), manuscript generator (seed 20261104), real windows, real vintages | size (lower), power (higher), median first-flag day of the planted columns (lower; the no-change column is context, a first flag there is a false alarm); the real runs are shown and never ranked |
| Q3 | P&L attribution of a trading desk | C13 | desk replications | false alarm (lower), detection (higher) |
| Q4 | PD under informative rating withdrawals | C04 | the withdrawal generator, 200 repetitions per design | coverage (higher), width (lower), relative bias (nearer 0), the committed verdict |
| Q5 | Default prediction on a retail book | C01 | two runs: the Taiwan holdout and the German twin | AUC (higher), Brier (lower), expected calibration error (lower), Spiegelhalter p (context, never ranked) |
| Q6 | Lifetime PD by survival models | C06 | out-of-time, six reporting dates | integrated Brier (lower), C-index (higher), gap at 12 months (nearer 0), lifetime back-test gap (lower) |
| Q7 | LGD on defaulted loans | C08 | out-of-time, six default cohorts | rmse, mae (lower), R squared, Spearman (higher), gap (nearer 0) |
| Q8 | Operational-risk capital | C17 | independent histories of known truth, four tail indices | median ratio (nearer 1), spread (lower), share understating (nearer one half) |
| Q9 | A behavioural assumption changed at a limit breach | C14 | planted histories in paired arms (manuscript result) | false flags (lower), detection (higher), ROC area (higher) |
| Q10 | Reverse liquidity stress | C16 | one bank, one labelled run | share lost (nearer the observed 0.85), ratio (nearer 1), light (order); the multiplier is shown, not ranked |
| Q11 | The corrections of three validation tests | C20, C21 | three experiments (manuscript results) | rejection under the null (lower), detection (higher) |
| Q12 | Reject inference with a known rejected population | C01 | the German twin, 100 replications, four regimes | absolute bias (lower), reduction (higher), AUC gain (higher) |

Q13 (the PD curve carried to a new period) and Q14 (the portfolio loss quantile by method) are not built; the document lists each in `not_built`
with its reason. The recent published rows with no question (M-11, M-31, M-36, M-37) are listed in `left_out` with their reasons.

## The document

Closed objects (the schema forbids any other key). `questions[]`: `id`, `title`, `case_ids`, `protocol`, `runs[]` (`id`, `label`, `protocol`,
`seed` with its citation, `files`, `truth_status`, `columns`), `metrics[]` (`id`, `label`, `run_id`, `better`, `unit`, `columns`), `rows[]`, `absent[]`,
`standings[]`, `reading`, `negative_results[]` (`rows`, `manuscript`, `concept_doi`, `text`). `rows[]`: `method`, `ladder_id` (kept for the tests, never rendered), `standing`, `ranked`,
`note`, `source` and `year` where the SDD gives them, `cells[]` (`metric`, `column`, `value`, `null_reason`, `cited` with `path`, `pointer`,
`sha256`). Every text is `{en, es}`. The document also holds `provenance` (code version, the digest of the ladder rows read, every file read
with its hash), `left_out[]` (`ladder_id`, `method`, `reason`, `backlog`) and `not_built[]`.

Rules the document keeps:

- **Standing from the SDD.** `established`, `recent` or `proposed` is the tier of the method's row in the SDD Method ladder, read by code. A
  method with no ladder row has the standing `reference` (a comparator that runs on the protocol; the flag `ranked` says whether it takes
  part in the ranking). The words on the page are "long-established", "recent published" and "proposed in this work".
- **One run per metric (F-5).** A question whose methods sit in runs of different seeds splits by run; the case document's run (seed 42) and the
  manuscript's run (seed 20261104) of Q2 are separate metrics with their own columns and seeds, and no file serves two runs.
- **The reading is generated.** For each metric and column the best row by the metric's rule (`lower`, `higher`, `nearer:<value>`,
  `nearer-metric:<metric>`, `order:<best>,...`), ties stated, a null never ranked; the words of `reading` are built from those standings. A
  proposed method that loses is shown losing and the question cites the manuscript that reports the negative or partial result (BS-14 refuted on
  both clauses in the committed C04 verdict; BS-15 not as stated; BS-8 losing on false flags).
- **Nulls.** A cell the product does not have is null with its reason; the backlog row that fills a method the comparison does not show or leaves out (BL-119, K-1 to K-12) is the structured field `backlog` of its `absent[]` or `left_out[]` entry, never a reader text (BM-019). Nothing is estimated. The Kupiec and conditional-coverage p-values of Q1 are not among them: they are copied from the `tests` of every case document for all 18 models, and a test the document does not evaluate is null with that document's own note.
- **No p-value is ranked.** A p-value is evidence against a null, never a score of quality (it rewards a rule with few exceedances as much as one near the target): every metric whose value is a p-value is declared `none` (context). The traffic light and the distance of the exceedance count from its expected value are the ranked readings.
- **The rule is per metric.** The schema declares `better` once per metric, so a column that needs another rule is a metric of its own: the no-change column of the median first-flag day (Q2) is `gen_median_null` and `man_median_null`, declared `none`, beside `gen_median` and `man_median` over the planted columns (`lower`). The contract is unchanged.
- **The truth status of a run (BM-018).** Each chart is labelled real, synthetic or published by what its data rest on, and that is a fact of the
  case documents the run cites, not of the page: the builder copies `provenance.truth_status` from every case document of the run and stops
  when they disagree or one lacks it (no "mixed", no default), so a new run cannot be labelled by a default nobody decided. Two runs were
  mislabelled by the list of run ids the page first held (Q10's labelled run is `synthetic-calibrated`, Q12's twin `real-outcomes`). The
  manuscript result files state no status, so a run that cites only those declares one in the specification, with its reason, read against the
  experiment script the file names (the generator of known truth, the plant, or the committed real windows); a run that cites case documents
  declares nothing, and one that cites both takes the case documents' status. The same change keeps a manuscript's concept DOI in each
  negative result (read from its `conceptdoi` macro, checked against `product.json`) so the page shows the published title and not a file path.
- **Q10 (F-8).** The multiplier of the reverse liquidity stress is a threshold on a base, not a forecast: its row shows the score of its
  calibrated fast-run base and its multipliers, and is not ranked.

## Decisions carried from the sizing

F-1: the document cites committed files wherever they are (case documents or manuscript result files). F-3, F-4, F-7: the tier ruling of BL-116
and its extension (M-10, M-17, M-18 with every variant, M-20, M-22, M-24, M-25, M-35 long-established; M-11, M-38 recent published); the published
e-backtest of Q2 has no ladder row (M-39 is backlog BL-121) and is therefore listed in `absent`, not ranked. F-6: C04's verdict is read from the
committed file, refuted on both clauses since BL-118.

## Tests and gates

`tests/test_benchmark_methods.py` (BM-001 to BM-016, [`requirements.md`](requirements.md)); the contract checks of `docs/contracts/catalog.md`
(`scripts/check_contract_versions.py`, `npm run check:contracts`); `scripts/check_internal_names.py` for the words of the page.

## Where it runs

`python -m pipeline.benchmark.methods` from `data-pipeline/`; CAOS_MANAGE `tools/contraste/rebake.py` runs it after the cases and before the
index when the module exists; `pipeline.pipeline.served_files` lists the document, so the index carries it and the site build copies it.

## Not in scope

New computations: a cell whose computation the product lacks stays null with its reason. The case documents and their builders, the SDD
ladder's tiers, the page (T3) and the manuscripts.
