# Tasks: the governance bake (units U15-P and U16-P1b)

This feature is stated by [`requirements.md`](requirements.md), checked adversarially in [`validation.md`](validation.md). Its units and their work are recorded in the changelog of the release that shipped them.

## Convergence verdict

The verdict of this feature is generated, never written by hand. Every requirement of [`requirements.md`](requirements.md) has its row, with its gate and the gate's result in the release run, in [`../release-1-0/verdict.md`](../release-1-0/verdict.md) (filter the `feature` column by `governance`). `scripts/convergence_verdict.py` writes that document from the result files of the release run; the procedure is in [`../release-1-0/design.md`](../release-1-0/design.md).
