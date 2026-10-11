"""C01's TabPFN rung keeps the weights in the device models root. TabPFN fixes its cache directory when it is first
imported, so checking for the optional extra must not import it: an early import fixed the cache to a user directory
on the system drive before the rung set the models root (found 2026-10-07, the weights were in %APPDATA%\\tabpfn)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_availability_check_does_not_import_tabpfn():
    code = ("import sys; sys.path.insert(0, 'data-pipeline'); from pipeline.cases import c01_retail_pd as c; "
            "c._tabpfn_available(); print('tabpfn' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip().splitlines()[-1] == "False"


def test_the_rung_refuses_without_a_models_root(monkeypatch):
    from pipeline.model import tabpfn_rung

    monkeypatch.delenv("TABPFN_MODEL_CACHE_DIR", raising=False)
    monkeypatch.delenv("CONTRASTE_MODELS", raising=False)
    try:
        tabpfn_rung._cache_dir()
    except RuntimeError as exc:
        assert "never downloads weights into a user cache" in str(exc)
    else:
        raise AssertionError("the rung ran without a models root")
