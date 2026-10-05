# Guide: fetch the data and bake the cases

From a fresh clone to the committed artifacts the web replays. Everything runs in the isolated `.venv-pipeline`;
nothing is installed globally, and no raw file is written into the repository.

## 1. The environment

```bash
./scripts/setup.sh            # Windows: scripts\setup.ps1
```

It creates `.venv-pipeline` and installs the pinned engines (`data-pipeline/requirements.txt`, through
`requirements-precompute.txt`) and the dev tools (`requirements-dev.txt`). The TabPFN challenger is an optional extra
([its card](../frameworks/09_tabpfn/tabpfn.md)); without it the bake skips P5.

Copy `.env.example` to `.env` and set the two device roots, both outside the repository:

| Variable | What lands there |
|---|---|
| `CONTRASTE_DATA` | the raw downloads, `<root>/raw/<source>/` |
| `CONTRASTE_MODELS` | downloaded weights, `<root>/tabpfn` |

The fetcher and the pipeline also take `--data-root`; a root inside the repository is refused (CT-010).

## 2. Fetch the sources

```bash
.venv-pipeline/bin/python data-pipeline/fetch.py --all          # or name sources: uci-taiwan uci-german
```

Each source is declared in `data-pipeline/config/sources.json` with its licence class and the verbatim fragment of
its licence; a link-only or unusable source is never fetched (CT-009). Every file is streamed with its SHA-256, and
the licence manifest `data/sources/manifest.json` records the URL, the retrieval date, the class, the licence and the
hash and size of each file (CT-008). A second fetch that finds different bytes fails and names the file (CT-011);
`--refresh` accepts a new release deliberately.

## 3. Bake

```bash
.venv-pipeline/bin/python data-pipeline/run.py C01 --output <a temp folder>   # a sandbox bake, outside the repository
.venv-pipeline/bin/python data-pipeline/run.py                                       # the canonical release bake
```

A sandbox bake writes everything under `--output` and leaves `data/` untouched; use it while working. The canonical
bake (no `--output`) rewrites `data/derived/` and is run for a release. It exports the contract declarations, fits the
ladder of every case, runs the battery, checks the expected ranges (a value outside its range fails the bake) and
writes the artifacts through contract 2, refusing any whose lineage includes a link-only or unusable source. The bake
is a pure function of the inputs and the seed (42 by default): a second canonical bake leaves git clean. C01 takes
about twelve minutes on a laptop CPU.

## 4. Check

```bash
.venv-pipeline/bin/python -m pytest              # the sandboxed tests; they never write data/
./scripts/smoke.sh                               # contract 2 on disk: index, manifests and artifacts agree
.venv-pipeline/bin/python scripts/check_provenance.py
.venv-pipeline/bin/python scripts/check_data_classes.py
cd frontend && npm ci && npm test && npm run build && npm run gate
```

`npm run gate` serves the build as GitHub Pages does and walks every route, group, sub-tab and variant at five sizes,
both themes and both languages; its captures (`frontend/gate-output/shots`) are read by a person before a release.
The stages and their roles are in [architecture 05](../architecture/05_precompute-pipeline.md).
