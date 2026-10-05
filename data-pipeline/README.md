# data-pipeline/, the offline engine

The scripts of Contraste's science, invoked by path; the product declares no package of its own. The validation
tests and the regulatory calculators come from the engine package `riskvalidation`. They run in `.venv-pipeline`
(`scripts/setup.sh` or `scripts/setup.ps1`), on a workstation, never in CI.

    python data-pipeline/fetch.py uci-taiwan uci-german --data-root <device data root>
    python data-pipeline/run.py [all|<case>] [--seed N] [--output <sandbox>] [--data-root <device data root>]

## Layout

- `fetch.py`, `run.py`: the two entry points (fetch sources; export the contracts and bake the cases)
- `config/sources.json`: every source with its licence fragment and class; `config/licences.json`: the verified
  licence of every package of the default install
- `pipeline/pipeline.py`: the orchestrator and its CLI; `pipeline/registry.py`: the cases by category, the default case
- `pipeline/io/`: `contract.py` (contract 1, the eight ingestion families), `sources.py` (the registry and licence
  classes), `fetch.py` (the fetcher and the licence manifest), `formats.py` (readers and writers)
- `pipeline/core/`: `manifest.py` (contract 2), `lineage.py` (licence lineage and provenance), `expect.py` (the
  expected ranges every result is checked against), `gate.py` (the lane gate), `rng.py` (seeded determinism)
- `pipeline/model/`: the model rungs of each family, thin pinned wrappers over the engines in `docs/frameworks/`
- `pipeline/stages/`: ingest, preprocess, split, feature extraction, train, infer, evaluate, export, validate
- `pipeline/cases/`: the cases, each with its sources, variants, leakage-safe split and expected ranges

See [../docs/architecture/08_data-contracts.md](../docs/architecture/08_data-contracts.md) and
[../docs/design/SDD.md](../docs/design/SDD.md).
