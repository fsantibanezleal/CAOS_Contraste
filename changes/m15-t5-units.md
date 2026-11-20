- The constant check of the units rule (units gates, M15 T5, CONTRACT 3b): `scripts/check_unit_constants.py` walks every float
  literal of the reviewed method and parameter modules under `data-pipeline/pipeline/` and fails on one without a baseline entry
  keyed `module::qualname::value::ordinal` with its class, unit and reason, naming the module, the line and the value; a module in
  none of the three lists in `scripts/unit_constants_modules.json` (172 method, 27 parameter, 78 outside, each outside entry with its
  reason) fails too. `0.0`, `1.0`, `0.5`, `2.0`, `10.0` and `abs(v) < 1e-5` are exempt; `100.0` and `1000.0` are walked.
  `--update` writes `scripts/unit_constants_baseline.json` with the 2,067 literals as `TODO` (T6 classifies them), so the check fails
  by design until then and is not yet in CI or the smoke scripts. Standard library only, about 1.3 s on the whole tree.
