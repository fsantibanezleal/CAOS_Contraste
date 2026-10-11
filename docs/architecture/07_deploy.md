# Deploy

One deploy place, decided first and written in `deploy/TARGET`: GitHub Pages, with the custom domain
`contraste.fasl-work.com` (`frontend/public/CNAME`). The repository is public and every capability is static replay or
client-side compute, so no backend trigger exists (ADR-0002); `scripts/check_deploy_place.py` fails if the files of a
second place appear.

## Before a deploy

Locally: the sandboxed pipeline tests (`pytest`), the canonical bake when the science changed
(`python data-pipeline/run.py`), `npm run build`, `npm test`, and `npm run gate`, which serves `dist/` as Pages would
(no fallback) and walks every route, group, sub-tab, case and variant at five sizes, in both themes and both languages.
A person reads its captures (`frontend/gate-output/shots`): the gate measures, it does not judge content.

## The deploy

`.github/workflows/deploy-pages.yml` runs after CI succeeds on `main`, on that same commit. It checks the committed
artifacts and the deploy place, builds the site with the base path `/` (the custom domain), deploys, and runs
`scripts/check_live.py` against the live site: `build.json` names the pushed commit, every route answers with the app
with and without its trailing slash, a missing file answers 404, and the artifact index answers JSON. It never trains,
rebakes or recomputes (ADR-0069, ADR-0074).

## CI

`.github/workflows/ci.yml`, on `develop` and `main`: lint, the workflow files parse, contract 2, the provenance of
every artifact, the data classes, the licences of the default install, the version, the SDD, the deploy place; a web
job (install, build, unit and component tests, the web baseline); and the guards (tracked secrets, venvs, binaries,
raw data, machine paths, template residue, document paths, content standards, the CI budget). Every step runs under
`bash -eo pipefail`.
