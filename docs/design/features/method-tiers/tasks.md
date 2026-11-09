# Tasks: method tiers

This feature is stated by [`requirements.md`](requirements.md), checked adversarially in [`validation.md`](validation.md). It came with the product template 0.15.006 (taken at its adoption, Contraste 1.00.000); its gates are tests Contraste already carries (`tests/test_method_tiers.py`, `tests/test_check_manuscripts.py`, `tests/test_check_internal_names.py`). Its units and their work are recorded in the changelog of the release that shipped them.

## Convergence verdict

The verdict of this feature is generated, never written by hand. Every requirement of [`requirements.md`](requirements.md) has its row, with its gate and the gate's result in the release run, in [`../release-1-0/verdict.md`](../release-1-0/verdict.md) (filter the `feature` column by `method-tiers`). `scripts/convergence_verdict.py` writes that document from the result files of the release run; the procedure is in [`../release-1-0/design.md`](../release-1-0/design.md).
