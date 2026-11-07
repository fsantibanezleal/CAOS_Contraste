# Tasks: SHOW-1, the guided story and the visualization catalog

This feature is stated by [`requirements.md`](requirements.md), designed in [`design.md`](design.md), checked adversarially in [`validation.md`](validation.md). Its units and their work are recorded in the changelog of the release that ships them (fragment `changes/show-1-story.md`).

## Convergence verdict

The verdict of this feature is generated, never written by hand. Every requirement of [`requirements.md`](requirements.md) has its row, with its gate and the gate's result in the release run, in [`../release-1-0/verdict.md`](../release-1-0/verdict.md) (filter the `feature` column by `story`). `scripts/convergence_verdict.py` writes that document from the result files of the release run; the procedure is in [`../release-1-0/design.md`](../release-1-0/design.md).
