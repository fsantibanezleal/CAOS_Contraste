# Guide: make a product from this template

The product's research and plan come first, and its SDD (`docs/design/SDD.md`) is written before any code
(ADR-0075). This guide starts after that.

## 1. Create the repository and instantiate

Create the repository from the template on GitHub (`gh repo create <owner>/<Repository> --template
fsantibanezleal/CAOS_PRODUCT_TEMPLATE`), clone it, set up the pipeline environment (`scripts/setup.sh`), and run:

```bash
python scripts/instantiate.py --slug <slug> --name "<Name>" --repo <Repository> \
  --deploy pages --domain <slug>.fasl-work.com --visibility public \
  --tagline-en "<one line>" --tagline-es "<una línea>"
```

- `--deploy` is the one deploy place, decided now: `pages` (a static site) or `vps` (only for a product with an
  active backend). The other place's files are removed; `scripts/check_deploy_place.py` keeps it that way.
- `--visibility private` hides every source link in the app.
- `--domain` writes a CNAME file into `frontend/public/` for Pages; without it the site is a project page under the repository
  name, and the deploy builds with that base path.

The script writes `product.json`, the frontend package name, `VERSION` (0.01.000), a fresh `CHANGELOG.md`, the MIT
`LICENSE`, `deploy/TARGET` and a product `README.md`; it deletes `.template-source` and `.vscode/`;
then it bakes, tests and builds once and runs `scripts/check_template_residue.py`. That list is the work that
follows.

## 2. Replace the example, unit by unit

Build vertically: each unit (a method, a case family, a page) is finished, with its code, tests and documentation,
before the next starts.

1. **The engine.** Replace `data-pipeline/pipeline/model/` and the stage bodies with the method ladder of the SDD.
   Each method meets its acceptance criterion (ADR-0069) and gets a card in `docs/frameworks/`, its dependency
   pinned in `data-pipeline/requirements.txt` (or the precompute or GPU file).
2. **Contract 1.** Rewrite `data-pipeline/pipeline/io/contract.py` for the product's raw data (columns, units,
   ranges, outlier policy) with a sample in `data/examples/`; update `tests/test_contract.py` and `data/README.md`.
3. **The cases.** Rewrite `data-pipeline/pipeline/cases/` and the registry: bilingual titles, categories and expected
   bands, and numeric expected ranges for every case (`core/expect.py` fails the bake outside them). Set the default
   case. Document the coverage matrix in `docs/cases/`.
4. **Contract 2.** Rename the schema ids (`example.*`) to the product's, change the trace and manifest shapes as the
   method needs, and change `frontend/src/lib/contract.types.ts` with them: the descriptors and `contract.test.ts`
   fail on any key or type that one side has and the other does not.
5. **The live engine.** If a method runs live, port it to `frontend/src/engine/` and hold it to the baked artifacts
   with a parity test, as `sir.parity.test.ts` does. If none can, the workbench replays only and declares
   `replayOnly`.
6. **The workbench.** Rewrite `frontend/src/workbench/`: the case's question groups, its variants, its parameters
   and live values in the rail. Views are `PlotCard`s with lane, provenance and the selection key; drawings go in a
   `Stage` or a `UPlotChart`; a table sits above the drawing of the same numbers.
7. **The pages and the diagrams.** Rewrite `frontend/src/pages/` from the product's dossiers (equations with
   captions, references with DOIs that resolve) and the five diagrams in `frontend/src/architecture/` (bilingual,
   shell tokens only).
8. **The SDD requirements.** Replace `docs/design/features/workbench/` with the product's features; every
   requirement names a test or guard that exists.

## 3. Verify, then release

In separate steps: the sandboxed tests, the canonical bake (`scripts/precompute.sh`), `scripts/check_artifacts.py`,
`npm run build`, `npm test`, `npm run gate`, and every guard in `.github/workflows/ci.yml`. Read the gate's
captures (written under `frontend/`, in gate-output/shots) yourself: the gate measures, it does not judge content.

A release bumps `VERSION`, `frontend/package.json` and the top of `CHANGELOG.md` together, merges `develop` into
`main` through a pull request, and tags `vX.XX.XXX`. The deploy runs after CI succeeds on `main` and checks the live
site; after it, run the gate against the deployed origin: `npm run gate -- --url https://<domain>`.

On GitHub Pages, before the first deploy, enable Pages with the Actions source and set the custom domain by API
(the Pages runbook in `deploy/`, kept only in a Pages product).
