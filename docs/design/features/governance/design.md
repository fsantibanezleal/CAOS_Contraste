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
6. **Graph** (`edge_table.py`, `bake._layout`): the case edges of `edges.json` expand to entries; the engine checks the graph is acyclic and gives depth and
   fan; networkx lays the columns (`topological_generations` must agree with the engine's generations; `multipartite_layout` over sorted layers).
7. **Appetite and reports**: the engine's seven metrics and its twelve-section report per entry; the Spanish accents are restored (`spanish.py`).
8. **Check and write**: the schema and the U15-S checker over every document; any finding refuses all of them. The page `docs/governance.md` and
   `data/derived/governance/` (with `SHA256SUMS.txt`) are written only after the check.

## Decisions of this unit

- **The assignment extensions.** W15-15 names two rules. C06 and C08 have six fits that read the same sources, and C01 has two Taiwan fits, so the engine's rule
  places none of their variants. The two committed identities above place them; `inputs.json` `variant_assignment.extensions` switches them off. This is an open
  question for the main session (the report).
- **Copied texts.** A text copied unchanged from a case document ("approval cohorts", "approval rate") is the case's own: it is neither rewritten nor read by the
  checker's text rule (the bake replaces it by a marker for that rule only). This is an open question for U15-S (the report).
- **The manifest** is `SHA256SUMS.txt`, as in the case folders: a JSON manifest would need a schema of its own.

## Limits

The scores of the tier inputs are conventions; the register carries no remediation plan; the tests of the bake read the committed documents only (no fit, no CI).
