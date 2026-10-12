- The pipeline publishes all 22 planned cases: cases are discovered (modules `cases/c<NN>_*.py` and packages
  `cases/c<NN>/` that expose `CASE`; two modules claiming one id fail with both paths), and the 18 cases not built yet
  are declared once in `data-pipeline/config/planned_cases.json` (title, category, data kind, owner unit, question)
  and listed in `data/derived/manifests/index.json` with no manifest and no data.
- A readiness document (`data/derived/readiness.json`, `python data-pipeline/run.py readiness`) states what is real in
  the build: the planned cases are a partial `case-manifest` with their manifest paths, a missing rung of the C01
  ladder is `training` on the baseline. `scripts/check_readiness.py` recomputes it from committed files (stdlib only).
- Export refuses a document that fails its schema before writing it: artifacts, the manifest of each case and the
  index (`pipeline/core/schemas.py`); `python data-pipeline/run.py index` rebuilds the index without baking.
- The C01 model slot `c01-pd-rung` has a baseline (P0, `model/benchmark.py`) that answers in place of any rung.
- The dormant API serves `/api/readiness`, answers 503 with the declared state for a planned case and 404 for an
  unknown one; `scripts/check_artifacts.py` accepts an absent manifest only when the current readiness declares it.
