# The specification area

Where Contraste states what it builds and proves the statement can fail. It is written before any code (ADR-0075) and
kept current with it: a guard fails when a part is missing or disagrees with the repository. The area is `docs/design/`
(the design), `docs/contracts/` (the contracts as code) and `tests/` (the tests, with `tests/adversarial/` for the
planted defects). The structure follows the template this product is built on (CAOS_PRODUCT_TEMPLATE 0.05.000, whose
`docs/design/README.md` is the generic version of this page).

## The order

Research, then the executive brief, then sizing, contracts and the units.

1. **Research basis.** What was researched before the plan and what it decided: each claim with a source (a DOI or a
   URL), at least three distinct sources, and a line starting `UNVERIFIED:` for what stayed unverified. Section
   `Research basis` of [`SDD.md`](SDD.md). The dossiers behind it are persisted in the coordination repository.
2. **Executive brief.** The problem in its real context, in business language: the Initiative (the owner, the
   initiative, the quantified reason to act now), the Outcomes, the Positioning and the Credibility, every number with
   its source. Section `Executive brief` of [`SDD.md`](SDD.md), right after `Problem and non-goals`. How to write it:
   [`https://github.com/fsantibanezleal/CAOS_PRODUCT_TEMPLATE/blob/v0.05.000/docs/guides/06_executive-brief.md`](https://github.com/fsantibanezleal/CAOS_PRODUCT_TEMPLATE/blob/v0.05.000/docs/guides/06_executive-brief.md).
3. **Sizing, summarised.** Sections `Sizing and contracts`, `Technology and versions` and `Resources` of
   [`SDD.md`](SDD.md): the components and boundaries (the sizing itself is kept with the coordination records), every
   pinned dependency with the version actually pinned (`scripts/check_tech_matrix.py`) and the measured resources of
   each stage.
4. **Contracts.** One row per boundary and per model slot in [`../contracts/catalog.md`](../contracts/catalog.md), one
   schema file each, an example, a test on each side, the missing-data behavior and a provider. Versions follow the
   schemas by semver; [`../contracts/versions.lock.json`](../contracts/versions.lock.json) holds the digest of each
   schema (`scripts/check_contract_versions.py`).
5. **Requirements.** Per feature, `features/<feature>/requirements.md`: `| ID | statement | gate |`, every statement
   with SHALL, every gate a test or guard that exists and can fail.
6. **Tests, red first.** Each requirement becomes a test that fails for the right reason before the code exists
   (`tests/`, `frontend/src/**/*.test.ts`).
7. **Adversarial validation.** Per feature, `features/<feature>/validation.md`: `| requirement | adversarial check |
   gate |`, one row per requirement, the check stated as what was planted and the gate the test under
   `tests/adversarial/` that plants it. A plant copies the committed files the guard reads into a temporary directory,
   plants one defect (an edit of a source file or of a committed artifact), runs the existing gate on the copy and
   asserts that the clean copy passes and the planted copy fails with the gate's own message. The plants never read a raw
   data file and never write outside the temporary directory. A row whose plants need node and the installed frontend
   packages says `local-only` in its check cell.

## Where each part lives

| part | file | guard |
|---|---|---|
| research basis, executive brief | `docs/design/SDD.md` | `scripts/check_sdd.py` |
| sizing summary, technology, resources | `docs/design/SDD.md` | `scripts/check_sdd.py`, `scripts/check_tech_matrix.py` |
| contracts, providers, states | `docs/contracts/catalog.md`, `docs/contracts/schemas/` | `scripts/check_contracts.py`, `scripts/check_skeleton.py`, `scripts/check_readiness.py` |
| contract versions and history | `docs/contracts/catalog.md` (`History`), `docs/contracts/versions.lock.json` | `scripts/check_contract_versions.py` |
| requirements | `docs/design/features/<feature>/requirements.md` | `scripts/check_sdd.py` |
| adversarial validation | `docs/design/features/<feature>/validation.md`, `tests/adversarial/` | `scripts/check_sdd.py`, `python -m pytest tests/adversarial` |

## The features

| feature | requirements | validation |
|---|---|---|
| contracts | CT-001 to CT-014 | [`features/contracts/validation.md`](features/contracts/validation.md) |
| c01-retail-pd | CT-101 to CT-105, CT-108 to CT-111 | [`features/c01-retail-pd/validation.md`](features/c01-retail-pd/validation.md) |
| web | CT-106, CT-107, CT-112 to CT-114 | [`features/web/validation.md`](features/web/validation.md) |
| c05-ldp-calibration | CT-201 to CT-211 | [`features/c05-ldp-calibration/validation.md`](features/c05-ldp-calibration/validation.md) |
| c01-irb-capital | CT-212 to CT-217 | [`features/c01-irb-capital/validation.md`](features/c01-irb-capital/validation.md) |
| c22-validator | CT-301 to CT-313 | [`features/c22-validator/validation.md`](features/c22-validator/validation.md) |
| c04-transitions | CT-401 to CT-415 | [`features/c04-transitions/validation.md`](features/c04-transitions/validation.md) |

## Known limits of the plants

Listed so nobody takes a pass for more than it is.

- A plant proves that the gate named in `requirements.md` fails on the defect it plants; it does not prove that the
  defect is the only way the requirement can break. The adversarial name of a test is a claim a reviewer verifies.
- Several plants edit a committed artifact (a JSON file under `data/derived/`) and not the code that wrote it, because
  ADR-0074 forbids a bake in CI and the gate tests read those artifacts; the defect is then the one a wrong bake would
  have written.
- The leakage plants (CT-101 to CT-103) and the C01 plants run the real fitting path and take seconds to tens of seconds,
  not milliseconds.
- The measured browser gate (`frontend/scripts/gate.mjs`) is planted in `tests/adversarial/test_adv_gate.py`, which needs
  node, the installed frontend packages, a built site (`CONTRASTE_DIST` may name one elsewhere) and a browser installed by
  Playwright; the rows that cite it say `local-only`. Its two plants take minutes, not seconds, and are not specific to a
  case: one makes the workbench route (which carries every case) wider than the viewport, the other makes the site
  another product. They show that the wrapper runs the shell's gate on the built site and that it fails on those
  defects; the per-case rows (CT-211, CT-217, CT-310, CT-413) rest on that, not on a plant inside the case.
- On this branch the site cannot be built from the committed index, which lists the 18 planned cases whose manifests do
  not exist yet (the web reads no readiness before unit CF-C): the web plants prune the index in their copy first, and
  the gate plants run on a build made that way.
