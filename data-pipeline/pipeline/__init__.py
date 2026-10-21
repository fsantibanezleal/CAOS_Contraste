"""Contraste's offline pipeline (ADR-0057): the scripts that turn public data and known-truth generators into the
committed artifacts the web replays. Invoked by path (`python data-pipeline/run.py`), never installed; the
validation tests and regulatory calculators come from the engine package `riskvalidation`.
"""

import os
from pathlib import Path

# A bake's bytes must not depend on the device's core count (U16 decision D16-18): the BLAS summation order and the
# OpenMP split of LightGBM follow the thread count, so every entry point pins it before numpy or a model library loads.
# The package is imported before any of them (run.py, python -m pipeline.<bake>, the tests' conftest).
PINNED_THREADS = "4"
for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_var] = PINNED_THREADS

# VERSION at the repository root is the only place the version is written (T4); every manifest records it.
__version__ = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
