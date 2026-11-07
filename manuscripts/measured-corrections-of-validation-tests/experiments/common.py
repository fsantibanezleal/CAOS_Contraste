"""What the three experiment scripts of this manuscript share: single-threaded numerical libraries in every worker, the
seed convention, the cache folder of per-cell results, the compact JSON the manuscript reads, and the rate with its Monte
Carlo standard error.

The environment variable ``CAOS_TEMP_ROOT`` names the temporary root of the device; the cache of a script is
``$CAOS_TEMP_ROOT/contraste-measured-corrections/cache``, or the folder given with ``--cache`` (required when the variable
is unset). Nothing here reads a machine path.
"""
from __future__ import annotations

import os

# One thread per worker: the scripts parallelise over replications, never inside a linear-algebra call.
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_name, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import pathlib  # noqa: E402
from typing import Any  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
RESULTS = HERE / "results"
BASE_SEED = 20261104  # the root of every SeedSequence of the three experiments

#: The miscoverage of the conformal sets (target 0.90) and the level of every test of the study.
CONFORMAL_ALPHA = 0.10
LEVEL = 0.05


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cache", type=pathlib.Path, default=None,
                        help="folder of per-cell results (default: $CAOS_TEMP_ROOT/contraste-measured-corrections/cache)")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                        help="worker processes (default: half of the cores)")
    parser.add_argument("--reps", type=int, default=None, help="replications per cell (default: the study's value)")
    parser.add_argument("--out", type=pathlib.Path, default=RESULTS, help="folder of the compact JSON the manuscript reads")


def cache_folder(arg: pathlib.Path | None, script: str) -> pathlib.Path:
    """The folder that holds the per-cell results of ``script``; created when absent."""
    if arg is None:
        root = os.environ.get("CAOS_TEMP_ROOT")
        if not root:
            raise SystemExit("CAOS_TEMP_ROOT is unset: pass --cache <folder> or export CAOS_TEMP_ROOT")
        arg = pathlib.Path(root) / "contraste-measured-corrections" / "cache"
    folder = arg / script
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def rate(hits: int | float, reps: int) -> dict[str, float]:
    """A rejection rate with its Monte Carlo standard error ``sqrt(r (1 - r) / R)``."""
    r = float(hits) / reps
    return {"rate": r, "se": math.sqrt(r * (1.0 - r) / reps), "reps": reps}


def load_cell(folder: pathlib.Path, key: str) -> Any | None:
    path = folder / f"{key}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save_cell(folder: pathlib.Path, key: str, value: Any) -> None:
    (folder / f"{key}.json").write_text(json.dumps(value), encoding="utf-8")


def write_result(out: pathlib.Path, name: str, value: Any) -> pathlib.Path:
    """The compact JSON a figure or table script reads: sorted keys, no spaces, committed with the manuscript."""
    out.mkdir(parents=True, exist_ok=True)
    path = out / name
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    return path


def versions() -> dict[str, str]:
    import importlib.metadata as md

    return {name: md.version(name) for name in ("riskvalidation", "numpy", "scipy")}
