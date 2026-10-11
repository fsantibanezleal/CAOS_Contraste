# The lane gate

`data-pipeline/pipeline/core/gate.py :: classify_lane()` decides, per artifact and by measurement, whether a
computation is light enough to be rerun live in the browser:

- its engine is pure Python with its wheels in the live set (`numpy`, `scipy`, `statsmodels` and the pure
  `riskvalidation` wheel, all of which Pyodide ships or loads), and
- one run finishes within `RUN_MS_GATE` (1500 ms), and
- the artifact is within `TRACE_BYTES_GATE` (256 KiB).

Otherwise the artifact is `precompute`: the pipeline bakes it and the web replays it. Every C01 artifact is
`precompute`: its rungs need LightGBM, XGBoost, InterpretML and optbinning, and a fit takes seconds to minutes. The
verdict and its reasons are written into the artifact's `lane` block and into its manifest entry (`gate`), and
`scripts/check_artifacts.py` fails when the two disagree.

What the web recomputes live is not an engine run: it is arithmetic on committed records (adding a points table,
adding the EBM's term scores, comparing p-values with the reader's thresholds, interpolating a cut-off curve), held
to the pipeline by parity tests ([04](04_live-lane.md)).

The web has its own gate, measured on the built site: `npm run gate` (`caos-shell-gate`, see [07, deploy](07_deploy.md)).
