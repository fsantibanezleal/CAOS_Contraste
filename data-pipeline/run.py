#!/usr/bin/env python3
"""Repo-local build tooling. Invoked BY PATH, never installed, never a distribution."""
import os

for _var in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):  # D16-18, before numpy loads
    os.environ[_var] = "4"

from pipeline.pipeline import main  # noqa: E402

if __name__ == "__main__":
    main()
