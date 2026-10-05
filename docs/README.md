# Docs, the Contraste wiki

The product wiki (ADR-0056), written as the product is built, unit by unit. The pipeline, its validation and these
documents are the product; the web app is its companion workbench. The design, with every requirement and its gate,
is [design/SDD.md](design/SDD.md); each unit's requirements, design and tasks are under [design/features/](design/features/).

## Map

- **[architecture/](architecture/)**: how the repository works: the lanes and the flow, determinism and the
  artifacts, the lane gate, the live lane, the staged pipeline, the validation and evaluation design, the deploy, and
  the two data contracts with the sources and their licences.
- **[frameworks/](frameworks/)**: one card per engine the pipeline uses (what and why, the pinned install, usage,
  how it is applied here, caveats and licence).
- **[guides/](guides/)**: runnable how-tos: fetch the data and run the pipeline, validate your own scored sample, run
  the dormant API, edit the architecture modal.
- **[cases/](cases/)**: the category taxonomy, the coverage matrix of the 22 cases, and one page per built case.

## Honesty and data policy

- Every number shown comes from a committed artifact or is recomputed live from one; no number is typed into a page.
- Every source carries its licence class; raw rows of a source that is not mirror-allowed never enter the
  repository, and an artifact whose lineage includes a link-only or unusable source is refused at export
  ([architecture/08_data-contracts.md](architecture/08_data-contracts.md)).
- A synthetic institution is labelled synthetic; a perturbed variant of real data is labelled as known truth; a
  threshold is labelled as the policy it is, never as regulation.
