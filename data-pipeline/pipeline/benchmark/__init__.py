"""The methods-compared benchmark (BL-113, task T2): one document that puts each question's methods side by side, read from the
committed case documents and manuscript result files, every number with the path, the JSON pointer and the SHA-256 of the file it
was copied from. ``python -m pipeline.benchmark.methods`` from ``data-pipeline/`` writes ``data/derived/benchmark/``.

The step recomputes nothing: a missing number is a null with its reason (the backlog row that fills it), never an estimate.
"""
from __future__ import annotations

BENCHMARK_DIR = "benchmark"
METHODS_REL = "benchmark/methods-compared.json"
SUMS_REL = "benchmark/SHA256SUMS.txt"
SCHEMA_TAG = "contraste.benchmark.methods-compared/v1"


def served_files() -> list[str]:
    """The benchmark documents the site serves, relative to the derived-data root (the index appends them, as it does the governance documents)."""
    return [METHODS_REL]
