# Contraste

[![CI](https://img.shields.io/github/actions/workflow/status/fsantibanezleal/CAOS_Contraste/ci.yml?branch=main&label=CI)](https://github.com/fsantibanezleal/CAOS_Contraste/actions)
[![License](https://img.shields.io/github/license/fsantibanezleal/CAOS_Contraste)](LICENSE)
[![Version](https://img.shields.io/github/v/tag/fsantibanezleal/CAOS_Contraste?label=version&sort=semver)](https://github.com/fsantibanezleal/CAOS_Contraste/tags)
[![Live](https://img.shields.io/badge/site-live-2ea44f)](https://contraste.fasl-work.com)

Build financial risk models, then validate them the way a model risk function and a supervisor would.

*Construir modelos de riesgo financiero y validarlos como lo harían una función de riesgo de modelos y un supervisor.*

## Run it

```bash
./scripts/setup.sh                     # the pipeline environment (.venv-pipeline); setup.ps1 on Windows
./scripts/precompute.sh                # the canonical bake into data/derived (a release operation)
.venv-pipeline/bin/python -m pytest    # the pipeline tests, sandboxed
cd frontend && npm ci && npm run build && npm test && npm run gate
```

## Documentation

- [docs/design/SDD.md](docs/design/SDD.md): the design, every requirement with its gate.
- [docs/](docs/README.md): architecture, guides, cases and frameworks.

Licensed under the MIT License (see [LICENSE](LICENSE)). Deployed to pages at https://contraste.fasl-work.com.
