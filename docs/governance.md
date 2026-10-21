# Governance: the model inventory, the tiers, the findings register, the appetite and the validation reports

The Experiments route shows how Contraste governs the models it validates: a **model inventory** with a dependency map and a tier for every entry, a
**findings register** across the cases, the **model risk appetite** metrics and one **validation report** of twelve sections per entry. This page is the
reading guide of those documents and, between its markers, their figures, generated from them.

Contraste approves no model (SDD non-goals 1 and 8). The inventory records Contraste's own models, under a
synthetic bank. The opinion and the recommendation of a report are the rule's output on the evidence; Contraste approves no model.

## What the bake does

`python -m pipeline.governance` from `data-pipeline/` (code `data-pipeline/pipeline/governance/`, contracts `governance-inventory`, `governance-findings`,
`governance-report` and `governance-appetite` 1.0.0, engine contract `engine-governance-api`) reads every committed case document and calls
`riskvalidation.governance` for every computed value: the scope test, the exposure band, the materiality, the complexity, the tier and its sensitivity to the
rubric's readings, the next review dates, the deadlines, the ageing, the overdue flag, the quantitative anchor, the opinion, the appetite metrics and the
report. The product computes none of them (ADR-0069). It writes `data/derived/governance/` (the four documents, one report per entry and `SHA256SUMS.txt`) and
the block below. Two bakes give the same bytes; no clock is read.

- **An entry is one fit** (decision W15-1), keyed `case_id/fit_id`. Its components are the model records of its models document, each with a role (champion,
  challenger, benchmark or reference) that is a convention by rung unless a committed page names the champion.
- **The as-of date** is the date of the newest release heading of `CHANGELOG.md` (W15-13). A raised date is the release date of the code version of the
  document that holds the finding (R4). Both are committed values.
- **A variant belongs to a fit** by the engine's rule (W15-15): the fit whose sources its provenance reads, or the single models document of the case. Where the
  engine finds no fit because several fits read the same sources, the bake tries two committed identities: the variant's model records carry the ids of
  exactly one fit, then the variant id equals the fit id. A variant that no rule places is listed below and never assigned by guess.
- **The tiering inputs** are in `data-pipeline/pipeline/governance/inputs.json`, each with its basis, its tag (`doc`: read in a committed document, `convention`:
  a stated convention) and its document pointer. C02 and C20, built after the research addendum, are scored by the same rubric and evidence standard (W15-18).
- **The dependency edges** are in `data-pipeline/pipeline/governance/edges.json`: document reads and code imports, each with its stated source. A test fails if a
  downstream package stops reading the document or the import line goes away. A related link is never a dependency.
- **The findings** stay in their variant documents with their five fields; the register adds the owner role, the deadline, the ageing, the anchor and the
  workflow state (W15-5). An accepted finding is a stated limit of a synthetic case, mapped to `risk_accepted` with no approver and no expiry.

## What is a convention

Every tier count, exposure band, deadline, frequency and appetite limit is a convention, labelled `convention` in the documents with its basis (item 30 of
the dossier UNVERIFIED list). None is a requirement of any supervisor. The ECB opinion levels and its 5 and 10 percent cut points on an RWEA anchor are the
ECB's (Instructions of February 2019, section 2.4.2); the rule that turns findings into a level is a convention (W15-7).

## Results

<!-- governance-results:begin -->

The documents were baked over the committed case documents with `riskvalidation` 0.9.0 as of 2026-10-20 (the newest release heading of the changelog; a convention, never the clock). 186 paths were read, each listed with its sha256 in the documents.

### The inventory

34 entries (one per fit) for 21 built cases, holding 124 variant documents and 230 model records. 21 dependency edges join the entries, in 3 generations; every entry also depends on the engine node.

| Entry | Tier | M | C | Opinion level | Variants | Register rows | Open S1 | Open S2 | Open S3 | Open S4 | Next review |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `C01/german` | 2 | 3 | 2 | 2 | 1 | 3 | 0 | 0 | 2 | 0 | 2027-10-12 |
| `C01/taiwan` | 2 | 3 | 2 | 3 | 5 | 32 | 0 | 12 | 9 | 1 | 2027-10-12 |
| `C01/taiwan-small` | 2 | 3 | 2 | 2 | 1 | 4 | 0 | 0 | 2 | 0 | 2027-10-12 |
| `C02/polish-horizons` | 2 | 3 | 2 | 3 | 6 | 39 | 0 | 1 | 20 | 0 | 2027-10-20 |
| `C03/sba-7a` | 2 | 3 | 2 | 3 | 5 | 40 | 0 | 19 | 11 | 0 | 2027-10-13 |
| `C04/transitions` | 1 | 4 | 1 | 3 | 9 | 43 | 0 | 13 | 17 | 0 | 2027-10-12 |
| `C05/ldp` | 1 | 4 | 1 | 3 | 1 | 3 | 0 | 1 | 1 | 0 | 2027-10-12 |
| `C05/sp2009` | 1 | 4 | 1 | 3 | 2 | 9 | 0 | 3 | 2 | 0 | 2027-10-12 |
| `C06/rd-2006-12` | 1 | 4 | 1 | 3 | 1 | 9 | 0 | 3 | 1 | 0 | 2027-10-12 |
| `C06/rd-2008-12` | 1 | 4 | 1 | 3 | 1 | 8 | 0 | 2 | 1 | 0 | 2027-10-12 |
| `C06/rd-2010-12` | 1 | 4 | 1 | 3 | 1 | 8 | 0 | 2 | 1 | 0 | 2027-10-12 |
| `C06/rd-2019-12` | 1 | 4 | 1 | 3 | 1 | 8 | 0 | 1 | 1 | 1 | 2027-10-12 |
| `C06/rd-2020-06` | 1 | 4 | 1 | 3 | 1 | 10 | 0 | 4 | 1 | 0 | 2027-10-12 |
| `C06/rd-2023-06` | 1 | 4 | 1 | 3 | 1 | 8 | 0 | 1 | 1 | 1 | 2027-10-12 |
| `C07/banco-andino` | 1 | 4 | 1 | 3 | 6 | 29 | 0 | 3 | 14 | 0 | 2027-10-12 |
| `C08/dc-2003-06` | 2 | 3 | 2 | 3 | 1 | 2 | 0 | 1 | 1 | 0 | 2027-10-13 |
| `C08/dc-2007-08` | 2 | 3 | 2 | 3 | 1 | 2 | 0 | 1 | 1 | 0 | 2027-10-13 |
| `C08/dc-2009-10` | 2 | 3 | 2 | 3 | 1 | 2 | 0 | 1 | 1 | 0 | 2027-10-13 |
| `C08/dc-2011-13` | 2 | 3 | 2 | 2 | 1 | 1 | 0 | 0 | 1 | 0 | 2027-10-13 |
| `C08/dc-2014-19` | 2 | 3 | 2 | 3 | 1 | 2 | 0 | 1 | 1 | 0 | 2027-10-13 |
| `C08/dc-2020-23` | 2 | 3 | 2 | 3 | 1 | 2 | 0 | 1 | 1 | 0 | 2027-10-13 |
| `C09/generator` | 2 | 3 | 1 | 3 | 6 | 36 | 0 | 6 | 15 | 0 | 2027-10-13 |
| `C10/c10` | 1 | 4 | 1 | 3 | 7 | 34 | 0 | 7 | 13 | 0 | 2027-10-15 |
| `C11/ladder` | 2 | 3 | 2 | 3 | 6 | 8 | 0 | 5 | 2 | 1 | 2027-10-15 |
| `C12/hw1f-treasury-2000-2025` | 1 | 4 | 1 | 3 | 6 | 27 | 0 | 27 | 0 | 0 | 2027-10-20 |
| `C13/generator` | 2 | 3 | 1 | 3 | 6 | 17 | 0 | 2 | 8 | 0 | 2027-10-15 |
| `C14/svb-2021-2022` | 1 | 4 | 1 | 4 | 3 | 12 | 3 | 4 | 5 | 0 | 2027-10-20 |
| `C15/banco-andino-2026-09` | 1 | 4 | 2 | 3 | 6 | 24 | 0 | 1 | 17 | 6 | 2027-10-20 |
| `C16/svb-liquidity` | 1 | 4 | 1 | 3 | 6 | 11 | 0 | 8 | 2 | 1 | 2027-10-20 |
| `C17/generator` | 1 | 4 | 1 | 3 | 4 | 13 | 0 | 5 | 8 | 0 | 2027-10-15 |
| `C18/banco-andino` | 1 | 4 | 2 | 4 | 6 | 29 | 2 | 2 | 17 | 8 | 2027-10-20 |
| `C20/c20-ladder` | 2 | 3 | 2 | 3 | 6 | 39 | 0 | 18 | 9 | 0 | 2027-10-20 |
| `C21/hmda-de-2018-2023` | 1 | 4 | 1 | 3 | 6 | 38 | 0 | 6 | 14 | 6 | 2027-10-20 |
| `C22/generators` | 4 | 1 | 1 | 3 | 8 | 20 | 0 | 1 | 0 | 0 | 2029-10-12 |

### Tier counts under the four readings

The tier is the matrix of materiality and complexity (06 B.3). Two inputs of the rubric are open, so the tier is shown under four readings and the adopted one is B (regulatory use graded, complexity the mean rounded half up; decision W15-3). Each cell is the number of entries in Tier 1/2/3/4.

| Reading | Regulatory use | Complexity | Entries in Tier 1/2/3/4 |
|---|---:|---:|---:|
| A | literal | mean | 33/0/0/1 |
| B | graded | mean | 18/15/0/1 |
| C | literal | maximum | 33/0/0/1 |
| D | graded | maximum | 31/2/0/1 |

### The dependency edges

A document edge means the downstream package reads the upstream case's committed document, a code edge that it imports the upstream case's code. A page statement, a shared method or a shared source is a related link and is not listed here.

| Upstream | Downstream | Kind |
|---|---|---:|
| `C01/taiwan` | `C02/polish-horizons` | code |
| `C01/taiwan` | `C03/sba-7a` | code |
| `C01/taiwan` | `C04/transitions` | code |
| `C01/taiwan` | `C05/ldp` | code |
| `C01/taiwan` | `C05/sp2009` | code |
| `C01/taiwan` | `C20/c20-ladder` | code |
| `C01/taiwan` | `C22/generators` | code |
| `C05/sp2009` | `C04/transitions` | code |
| `C06/rd-2020-06` | `C03/sba-7a` | code |
| `C06/rd-2020-06` | `C08/dc-2003-06` | code |
| `C06/rd-2020-06` | `C08/dc-2007-08` | code |
| `C06/rd-2020-06` | `C08/dc-2009-10` | code |
| `C06/rd-2020-06` | `C08/dc-2011-13` | code |
| `C06/rd-2020-06` | `C08/dc-2014-19` | code |
| `C06/rd-2020-06` | `C08/dc-2020-23` | code |
| `C07/banco-andino` | `C15/banco-andino-2026-09` | code |
| `C07/banco-andino` | `C18/banco-andino` | document |
| `C10/c10` | `C18/banco-andino` | code |
| `C11/ladder` | `C18/banco-andino` | document |
| `C15/banco-andino-2026-09` | `C18/banco-andino` | document |
| `C17/generator` | `C18/banco-andino` | document |

### The findings register

572 rows from the 34 entries' variant documents (0 overdue). The register enriches the five fields of a finding with its owner role, deadline, ageing, anchor and workflow state; no case document is rewritten.

| Severity | ECB F | open | action_plan_agreed | in_progress | submitted_for_closure | validated_closed | overdue | risk_accepted |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| S1 | F4 | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| S2 | F3 | 162 | 0 | 0 | 0 | 3 | 0 | 5 |
| S3 | F2 | 200 | 0 | 0 | 0 | 0 | 0 | 35 |
| S4 | F1 | 25 | 0 | 0 | 0 | 4 | 0 | 133 |

Finding rows in the variant documents: 588; in the register: 572; in the variants no fit could be determined for: 16.

Cases with no finding row in the committed documents: none.

| Case | Rows | S1 | S2 | S3 | S4 | Overdue |
|---|---:|---:|---:|---:|---:|---:|
| C01 | 39 | 0 | 12 | 20 | 7 | 0 |
| C02 | 39 | 0 | 1 | 20 | 18 | 0 |
| C03 | 40 | 0 | 19 | 16 | 5 | 0 |
| C04 | 43 | 0 | 13 | 27 | 3 | 0 |
| C05 | 12 | 0 | 4 | 3 | 5 | 0 |
| C06 | 51 | 0 | 13 | 6 | 32 | 0 |
| C07 | 29 | 0 | 3 | 14 | 12 | 0 |
| C08 | 11 | 0 | 5 | 6 | 0 | 0 |
| C09 | 36 | 0 | 6 | 21 | 9 | 0 |
| C10 | 34 | 0 | 7 | 13 | 14 | 0 |
| C11 | 8 | 0 | 5 | 2 | 1 | 0 |
| C12 | 27 | 0 | 27 | 0 | 0 | 0 |
| C13 | 17 | 0 | 2 | 8 | 7 | 0 |
| C14 | 12 | 3 | 4 | 5 | 0 | 0 |
| C15 | 24 | 0 | 1 | 17 | 6 | 0 |
| C16 | 11 | 0 | 8 | 2 | 1 | 0 |
| C17 | 13 | 0 | 5 | 8 | 0 | 0 |
| C18 | 29 | 2 | 2 | 17 | 8 | 0 |
| C20 | 39 | 0 | 18 | 9 | 12 | 0 |
| C21 | 38 | 0 | 6 | 14 | 18 | 0 |
| C22 | 20 | 0 | 9 | 7 | 4 | 0 |

### The model risk appetite

The seven metrics of 06 B.6 with their thresholds. Every limit is a convention (item 30 of the dossier UNVERIFIED list); a metric with no population has no value. The metrics that count findings include the inventory's own findings (GOV-RUBRIC-BLIND-SPOT, GOV-INDEPENDENCE-NOT-ESTABLISHED), beside the register rows.

| Metric | Value | Numerator | Denominator | Light |
|---|---:|---:|---:|---:|
| Share of Tier 1 entries validated on time | 1 | 18 | 18 | green |
| Open high-severity findings (S1 and S2) | 91 | 91 | 261 | red |
| Overdue remediation | 0 | 0 | 261 | green |
| Entries used under exception | 0 | 0 | 34 | green |
| Entries in breach of their thresholds (a red test row) | 32 | 32 | 34 | red |
| PMA magnitude relative to the model output | 0.0033 | 324129997.0 | 97592002519.53 | green |
| Share of entries with an owner role and a complete record | 0 | 0 | 34 | red |

### The reports

34 validation reports of twelve sections, one per entry. The opinion is the rule's output on the evidence; Contraste approves no model.

| Opinion level | Entries |
|---|---:|
| 1 | 0 |
| 2 | 3 |
| 3 | 29 |
| 4 | 2 |

### What the bake leaves out

Planned cases with no committed document: C19.

Variants no fit could be determined for (decision W15-15: never assigned by guess), each with the engine's reason:

- `C05/ldp-sim-0`: no fit can be assigned to the variant: the variant's provenance names no source, so no fit can be determined; its 5 finding rows are not in the register
- `C05/ldp-sim-1`: no fit can be assigned to the variant: the variant's provenance names no source, so no fit can be determined; its 5 finding rows are not in the register
- `C05/ldp-sim-3`: no fit can be assigned to the variant: the variant's provenance names no source, so no fit can be determined; its 6 finding rows are not in the register

<!-- governance-results:end -->

## Limits

- The inventory has 40 attributes (06 B.2). Eighteen of them have no committed source in most entries and are `missing` or `not-applicable` with their reason; the
  completeness counts are in `inventory.json`. A32 and A33 are `not-applicable` for every entry: there is no approver and no approval date, because Contraste approves no model.
- The independence of the validator is not established, because the pipeline and the engine are built in the same programme (finding
  `GOV-INDEPENDENCE-NOT-ESTABLISHED`, S2). The tier rubric has no materiality term for fan-out (finding `GOV-RUBRIC-BLIND-SPOT`, S3).
- Inline `contraste-<family>-battery` policy strings have no policy file, so a report states the kind of a threshold and leaves its direction null with the reason
  (backlog BL-085, done at the next re-bake).
- UNVERIFIED, carried from the dossier: the SS1/23 2026 text against the 2023 text (not diffed), the OSFI 2017 rescission, the EU AI Act Annex III 5(b) reading on
  a reproduction, a post-2019 ECB reporting instruction, the EBA draft RTS on material model changes. OSFI's transition is "an 18-month transition period" in
  OSFI's own words.

Sources: dossier 06 (model risk management and validation), the U15 research addendum (D1 to D6), the U15 unit sizing and its decisions W15-1 to W15-19, and
SR 26-2, PRA SS1/23, OSFI E-23 and the ECB instructions of February 2019, confirmed from their primary sources in the addendum.
