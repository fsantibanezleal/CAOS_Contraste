# Tasks: manuscript content and native LaTeX sources

Adopted whole from the product template 0.15.012 (1.01.000 M0): the manuscript blueprints under `templates/manuscripts/` and the content gate of [`requirements.md`](requirements.md). The template's own implementation map of this feature stays in the template; Contraste's manuscripts meet the gate in their 1.01.000 versions (CAOS_MANAGE `plans/contraste/post-1-0-cycle.md`).

## Convergence verdict

The verdict of this feature is generated, never written by hand. Every requirement of [`requirements.md`](requirements.md) has its row, with its gate and the gate's result in the release run, in [`../release-1-0/verdict.md`](../release-1-0/verdict.md) (filter the `feature` column by `manuscript-content`). `scripts/convergence_verdict.py` writes that document from the result files of the release run; the procedure is in [`../release-1-0/design.md`](../release-1-0/design.md).
