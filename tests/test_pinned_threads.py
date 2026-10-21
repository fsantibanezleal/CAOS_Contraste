"""U16 decision D16-18: every entry point of the pipeline pins the thread counts before numpy or a model library loads."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")


def test_importing_the_pipeline_pins_the_thread_counts_whatever_the_caller_set():
    env = {**os.environ, **{v: "17" for v in VARS}}
    code = ("import sys; sys.path.insert(0, 'data-pipeline'); import pipeline, os; "
            "print(','.join(os.environ[v] for v in %r))" % (VARS,))
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, check=True).stdout.strip()
    assert out == ",".join([__import__("pipeline").PINNED_THREADS] * 3)


def test_run_py_pins_them_before_any_import_of_the_pipeline_or_numpy():
    text = (ROOT / "data-pipeline" / "run.py").read_text(encoding="utf-8")
    pin = min(text.index(f'"{v}"') for v in VARS)
    first_import = re.search(r"^(from|import) (pipeline|numpy)", text, re.M)
    assert first_import is not None and pin < first_import.start()
