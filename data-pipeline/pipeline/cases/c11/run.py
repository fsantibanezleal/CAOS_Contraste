"""The command line of the C11 bake: ``fetch`` the raw series, ``select`` the hyperparameters, ``bake`` the documents.

    python data-pipeline/pipeline/cases/c11/run.py fetch  --data-root <data root>/contraste
    python data-pipeline/pipeline/cases/c11/run.py bake   --data-root <data root>/contraste --cache <temp root>/c11-cache --workers 6 [--output <sandbox>]

The bake writes ``data/derived/C11/`` and ``data/derived/manifests/C11.json`` (or the same layout under ``--output``) and is the
only entry point that does; it runs locally (ADR-0074). A second run with the same cache reuses every cached forecast.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[3]))     # data-pipeline/


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("fetch", "select", "bake"))
    ap.add_argument("--data-root", required=True, help="the device data root (outside the repository)")
    ap.add_argument("--cache", default=None, help="folder of the cached forecasts (default <data root>/cache/c11)")
    ap.add_argument("--output", default=None, help="output root (default data/derived)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    from pipeline.cases.c11 import bake as _case, readers
    from pipeline.io.fetch import data_root as resolve
    from pipeline.pipeline import PipelinePaths

    root = resolve(a.data_root)
    cache = Path(a.cache) if a.cache else root / "cache" / "c11"
    if a.command == "fetch":
        files = readers.fetch(root)
        print(f"{len(files)} raw files in {root / 'raw'}")
        return 0
    series = _case.load_series(root)
    if a.command == "select":
        hp, rec = _case.fix_hyperparameters(series, cache, a.workers)
        print(hp)
        return 0
    paths = PipelinePaths.from_output(a.output)
    _case.bake_all(paths.root, root, cache, workers=a.workers, seed=a.seed, series=series)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
