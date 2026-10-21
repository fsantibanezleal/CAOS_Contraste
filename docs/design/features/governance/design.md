# Design: U15-P, the governance bake

Status: live. Unit sizing `plans/contraste/units/U15-sizing.md` (CAOS_MANAGE), decisions W15-1 to W15-19. Requirements: [`requirements.md`](requirements.md).
Contracts: `governance-inventory`, `governance-findings`, `governance-report`, `governance-appetite` (`docs/contracts/schemas/governance/`) and
`engine-governance-api` (`docs/contracts/engine/governance-api.md`). The reading guide of the documents is [`docs/governance.md`](../../../governance.md).

## Question

Which of the models Contraste validates matter most, what is open on each, and what does the rule say about them? The bake answers over the committed case
documents with the engine `riskvalidation.governance` (0.9.0, ADR-0069): it computes nothing itself. It approves no model (SDD non-goal 1).

## Pipeline

1. **Read** (`readers.py`): the case index, each built case's manifest and the models and variant documents the manifest's `artifacts` name, the changelog and the
   two input files. Every path is recorded with its sha256 over LF-normalised bytes. An absent or invalid document stops the bake naming the file.
2. **Assign** (`bake._assign`): one entry per fit (W15-1). A variant goes to the fit the engine's `assign_variant` finds (W15-15). Where the engine finds none in a
   case of several fits, two committed identities are tried (the variant's model records carry the ids of exactly one fit; the variant id equals the fit id).
   What neither places stays in `excluded` with the engine's reason.
3. **Tier and schedule** (`bake._tier_block`, `_schedule`): the exposure band, materiality, complexity, the tier under the four readings and the next dates, all
   through the engine, from the inputs of `inputs.json` (each with a tag and a document pointer; C02 and C20 under W15-18).
4. **Register** (`bake._register_rows`): the severity map, the status map, the deadline, due date, ageing, overdue flag, anchor and RWEA share through the engine,
   the raised date from the changelog release of the document's code version.
5. **Attributes** (`attributes.py`): A01 to A40, each with a value, a status and a basis; none invented.
6. **Graph** (`edge_table.py`, `bake._layout`): the case edges are built from the `depends_on` list of every case manifest (the producer states what it reads, U16-P1b) and expand to entries, with the related links of `edges.json`; the engine checks the graph is acyclic and gives depth and
   fan; networkx lays the columns (`topological_generations` must agree with the engine's generations; `multipartite_layout` over sorted layers).
7. **Appetite and reports**: the engine's seven metrics and its twelve-section report per entry; the Spanish accents are restored (`spanish.py`).
8. **Check and write**: the schema and the U15-S checker over every document; any finding refuses all of them. The page `docs/governance.md` and
   `data/derived/governance/` (with `SHA256SUMS.txt`) are written only after the check.

## Decisions of this unit

- **The assignment extensions.** W15-15 names two rules. C06 and C08 have six fits that read the same sources, and C01 has two Taiwan fits, so the engine's rule
  places none of their variants. The two committed identities above place them; `inputs.json` `variant_assignment.extensions` switches them off. This is an open
  question for the main session (the report).
- **Copied texts.** A text copied unchanged from a case document ("approval cohorts", "approval rate") is neither rewritten nor exempted: the checker's text rule
  reads it like any string, and its allow list (`semantics.APPROVAL_ALLOWED`) names the phrases of a credit decision that are metrics, cohorts or applicant
  outcomes, each with its reason. A claim about a model matches none of them and stops the bake.
- **The bake's own arithmetic.** The complexity mean (sum over count, shown beside the engine's rounded C) and the exposure share (a sum, a ratio and a rounding
  of document values) are the only values the bake computes; the engine offers no function for either.
- **The Spanish table** (`spanish.py`) is a stopgap for 0.15.000: the engine 1.0 (U16-E1) returns its bilingual texts with their accents, and U16 removes it.
- **The manifest** is `SHA256SUMS.txt`, as in the case folders: a JSON manifest would need a schema of its own.

## Limits

The scores of the tier inputs are conventions; the register carries no remediation plan; the tests of the bake read the committed documents only (no fit, no CI).

## The `depends_on` derivation and its refusal table (U16-P1b fix round)

`core.manifest.derive_depends_on` reads the source of a case's producer (its package `cases/c<NN>/` and its flat modules `cases/c<NN>_*.py`) and states what it
finds of other cases:

- a `document` read is a string constant that is a whole document reference (`C07/base.json`, the C15 manifest), in a literal path;
- a `code` read is an import of a product module of another case;
- every reference needs a bilingual reason in the case's `DEPENDS_REASONS` (a read without one, or a reason for something not read, is refused).

A path to another case's document built at run time cannot be named, so the derivation refuses it instead of missing it. A **flagged occurrence** is a string
constant equal to another case id (`derived / "C14" / "x.json"`), or a string constant or f-string part that starts with another case id and a slash and is not a
whole document reference (`f"C15/{name}.json"`). A flagged occurrence that is neither a key of the case's reasons nor in the **refusal table** (`NOT_READS`, keyed by
module and literal, each with a bilingual reason) raises, naming the module and the literal. The table holds only occurrences that are not reads: today one, the text of
the missing-variant error of `c18/anchors.py`. A case that must read a document whose name depends on another case's data (C18 and the default variant of C15) reads the
concrete file through a literal (`C15/long-uf.json`), checks at run time that it is still the default variant of the C15 manifest, and a test asserts the same, so a
change of C15's default stops C18 instead of drifting. The test scan in `tests/test_depends_on.py` is written apart from the helper and compares its flagged set with the table.

An edge whose upstream case has no manifest in the inventory (planned or unknown) stops the governance bake naming the edge; an edge from a built case whose every
variant the rule leaves out (W15-15) contributes no edge and its exclusion is recorded.
