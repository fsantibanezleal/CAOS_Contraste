# scripts/

Environment and pipeline scripts in both `*.sh` and `*.ps1`, and the guards CI runs (each runs locally too, with the
standard library only).

## Environment and pipeline

| Script | What it does |
|---|---|
| `setup.sh` / `setup.ps1` | creates `.venv-pipeline` and installs the pinned pipeline requirements |
| `precompute.sh` / `precompute.ps1` | the canonical bake: `python data-pipeline/run.py` (a release operation, never CI) |
| `dev.sh` / `dev.ps1`, `smoke.sh` / `smoke.ps1` | local development and a sandboxed smoke run |
| `instantiate.py` | makes a product from the template (identity, licence, version, deploy place) |

## Guards

| Script | What it enforces |
|---|---|
| `check_artifacts.py` | contract 2: the index, manifests and artifacts agree; each lane matches its gate |
| `check_version_coherence.py` | VERSION is the only source; the package, the changelog and the tags agree with it |
| `check_sdd.py` | the SDD has its sections; every requirement names a gate that exists |
| `check_template_residue.py` | an instantiated product carries none of the example |
| `check_doc_paths.py` | every repository path a document names exists |
| `check_web_baseline.py` | the web's tokens, classes, numbers, images and animation loops |
| `check_deploy_place.py` | one deploy place, and only its files |
| `check_live.py` | after a deploy, the live site is this build (run by the deploy workflow) |
| `check_content_standards.py` | no em-dash and no emoji in tracked content (ADR-0067) |
| `check_ci_budget.py` | CI runs cheap checks only, on the trunks (ADR-0074) |
