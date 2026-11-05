#!/usr/bin/env python3
"""Write ``product.json`` ``method_entrypoints``: every public function and class the method package ``riskvalidation`` defines.

The notebook bar (template 0.12.000, ``scripts/check_notebooks.py``) counts a code cell as a method cell when it calls one of the
dotted names ``product.json`` declares, or a method of an object built from one. Contraste's method is its engine,
``riskvalidation`` (``product.json`` ``method_packages``); this script lists what the installed engine defines, so the
declaration follows the pinned release (``notebooks/requirements.txt``) and is never typed by hand.

Left out: private modules and names (a leading ``_``), the modules that register or describe instead of computing
(``registry``, ``io``, ``schema``, ``config``, ``contracts``, ``version``, ``cli``), exceptions, and record classes with no
public method (a dataclass or named tuple, which runs nothing).

    python scripts/method_entrypoints.py           # write product.json
    python scripts/method_entrypoints.py --check   # exit 1 when product.json differs from the installed engine
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "product.json"
SKIP = {"io", "schema", "schemas", "registry", "config", "contracts", "version", "cli", "__main__", "spec", "specs"}


def entrypoints() -> list[str]:
    """The dotted names of the installed engine's public functions and classes, sorted."""
    import riskvalidation

    names = set()
    for m in pkgutil.walk_packages(riskvalidation.__path__, "riskvalidation."):
        parts = m.name.split(".")[1:]
        if any(p.startswith("_") or p in SKIP for p in parts):
            continue
        try:
            mod = importlib.import_module(m.name)
        except ImportError:
            continue  # an optional extra that is not installed defines no method of this release's notebooks
        for n, obj in vars(mod).items():
            if n.startswith("_") or getattr(obj, "__module__", None) != m.name:
                continue
            if inspect.isfunction(obj):
                names.add(f"{m.name}.{n}")
            elif inspect.isclass(obj) and not issubclass(obj, BaseException):
                if [k for k, v in vars(obj).items() if not k.startswith("_") and callable(v)]:
                    names.add(f"{m.name}.{n}")
    return sorted(names)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail when product.json differs from the installed engine")
    a = ap.parse_args(argv)
    doc = json.loads(PRODUCT.read_text(encoding="utf-8"))
    want = entrypoints()
    if a.check:
        if doc.get("method_entrypoints") != want:
            have = set(doc.get("method_entrypoints") or [])
            print(f"method_entrypoints: product.json differs from the installed engine ({len(set(want) - have)} missing, "
                  f"{len(have - set(want))} extra); run python scripts/method_entrypoints.py")
            return 1
        print(f"method_entrypoints: OK, {len(want)} names")
        return 0
    doc["method_entrypoints"] = want
    PRODUCT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"method_entrypoints: wrote {len(want)} names to product.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
