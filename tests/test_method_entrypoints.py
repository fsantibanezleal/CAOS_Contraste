"""product.json method_entrypoints is what scripts/method_entrypoints.py derives from the installed engine (the notebook bar's
method cells, template 0.12.000)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("method_entrypoints", ROOT / "scripts" / "method_entrypoints.py")
me = importlib.util.module_from_spec(spec)
spec.loader.exec_module(me)


def test_product_json_declares_the_installed_engines_public_methods() -> None:
    declared = json.loads((ROOT / "product.json").read_text(encoding="utf-8"))["method_entrypoints"]
    assert declared == me.entrypoints()
    assert "riskvalidation.validation.discrimination.auc" in declared or any(n.startswith("riskvalidation.validation.") for n in declared)
    assert not [n for n in declared if ".registry." in n or n.split(".")[-1].startswith("_")]
