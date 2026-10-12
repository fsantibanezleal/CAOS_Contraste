"""The cases (SDD section 5), registered by discovery, never by a list.

A case is a module ``cases/c<NN>_<name>.py`` or a package ``cases/c<NN>/`` that exposes ``CASE``, an object with ``id``
(``C<NN>``, the same number as the module's name), ``slug``, ``title``, ``category_id``, ``kind``, ``question``,
``sources`` and ``bake(seed, paths, data_root) -> manifest``. A module of the same prefix without ``CASE`` is a
helper and is not a case. ``CASES`` lists the discovered cases in id order; two modules that declare the same id
fail at import with both paths. A case is added by the unit that builds it, end to end, by adding its module or
package: no other file changes (the planned entry of its id in config/planned_cases.json is then ignored).
"""
from __future__ import annotations

import importlib
import pkgutil
import re
from pathlib import Path
from typing import Any

_NAME = re.compile(r"^c(\d\d)(?:_.+)?$")


def discover(directory: Path | None = None, package: str | None = None) -> list[Any]:
    """Every ``CASE`` of the modules and packages named ``c<NN>`` or ``c<NN>_*`` in ``directory``, in id order."""
    directory = Path(directory) if directory is not None else Path(__file__).resolve().parent
    package = package if package is not None else __name__
    found: dict[str, tuple[Any, str]] = {}
    for info in sorted(pkgutil.iter_modules([str(directory)]), key=lambda i: i.name):
        m = _NAME.match(info.name)
        if m is None:
            continue
        module = importlib.import_module(f"{package}.{info.name}")
        case = getattr(module, "CASE", None)
        if case is None:
            continue
        where = str(getattr(module, "__file__", info.name))
        if case.id != f"C{m.group(1)}":
            raise ValueError(f"{where}: module {info.name} declares case {case.id!r}; the id must be C{m.group(1)}")
        if case.id in found:
            raise ValueError(f"case {case.id} is declared twice: {found[case.id][1]} and {where}")
        found[case.id] = (case, where)
    return [found[k][0] for k in sorted(found)]


CASES: list = discover()
