#!/usr/bin/env python3
"""CONTRACT 3b of the units rule (CAOS_MANAGE ``conventions/units-gate.md``): every constant declares its unit, at author time.

An AST walk of every float literal of the reviewed method and parameter modules under ``data-pipeline/pipeline/``. A literal
needs one entry of ``scripts/unit_constants_baseline.json`` keyed ``module::qualname::value::ordinal`` (the enclosing class and
function path, ``<module>`` at top level; the ordinal numbers equal values of one scope in source order, so two ``0.05`` of one
function are two entries), with

- ``class``, from the closed list ``probability``, ``ratio``, ``relative-tolerance``, ``training-hyperparameter``,
  ``single-observable-limit``, ``unit-conversion``, ``source-cited-input``;
- ``unit``, the unit in words, required;
- ``reason``, one sentence, required.

``TODO`` is what ``--update`` writes for a new literal; it fails the check. The rule's defect class (a literal comparable to a
measured quantity in a path more than one observable can reach) has no class: such a literal is rewritten against a quantity,
never baselined.

``scripts/unit_constants_modules.json`` holds three reviewed lists: ``method`` and ``parameter`` (walked) and ``outside`` (a
module and the one sentence on why no unit-bearing float literal lives there). A module under the pipeline root in none of the
lists fails, so a new module cannot escape review; a module in two lists, or a listed module that no longer exists, fails.

Exempt: ``0.0``, ``1.0``, ``0.5``, ``2.0``, ``10.0`` and ``abs(v) < 1e-5``. ``100.0`` and ``1000.0`` are walked: in Contraste they
are percent and thousand conversions, and a conversion is where the unit is declared. A negative literal is counted once, with its
sign. Integer literals are not walked.

Standard library only. Usage: ``python scripts/check_unit_constants.py [--update] [--counts]``; ``--root``, ``--modules`` and
``--baseline`` point at another pipeline root, module lists and baseline (the tests use a throwaway tree). ``--update`` adds new
literals as ``TODO``, drops the entries whose literal is gone, keeps every reviewed entry and writes the baseline sorted, one
entry per line, so a diff shows only the change. Exit 0 clean, 1 on any finding.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
RULE = "CAOS_MANAGE conventions/units-gate.md (CONTRACT 3b)"
CLASSES = ("probability", "ratio", "relative-tolerance", "training-hyperparameter", "single-observable-limit", "unit-conversion",
           "source-cited-input")
EXEMPT = frozenset({0.0, 1.0, 0.5, 2.0, 10.0})
TINY = 1e-5
TODO = "TODO"
LISTS = ("method", "parameter")


@dataclass(frozen=True)
class Literal:
    module: str
    qualname: str
    value: float
    ordinal: int
    line: int
    path: str

    @property
    def key(self) -> str:
        return f"{self.module}::{self.qualname}::{self.value!r}::{self.ordinal}"


@dataclass
class Walk:
    literals: list[Literal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class _Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.stack: list[str] = []
        self.found: list[tuple[int, int, str, float]] = []

    def _scope(self, node) -> None:
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _scope

    def _record(self, node, value: float) -> None:
        if abs(value) in EXEMPT or abs(value) < TINY:
            return
        self.found.append((node.lineno, node.col_offset, ".".join(self.stack) or "<module>", value))

    def visit_UnaryOp(self, node: ast.UnaryOp) -> None:
        operand = node.operand
        if isinstance(node.op, ast.USub) and isinstance(operand, ast.Constant) and type(operand.value) is float:
            self._record(node, -operand.value)
            return
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if type(node.value) is float:
            self._record(node, node.value)


def module_files(root: Path) -> dict[str, Path]:
    """Every module under ``root``: its name (path under the root, no suffix, forward slashes) to its file."""
    return {p.relative_to(root).with_suffix("").as_posix(): p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts}


def shown(path: Path, root: Path) -> str:
    for base in (REPO, root):
        try:
            return path.relative_to(base).as_posix()
        except ValueError:
            continue
    return path.as_posix()


def walk(root: Path, modules) -> Walk:
    """Every float literal of the named modules, with its key; a module that cannot be read or parsed is an error."""
    files = module_files(root)
    out = Walk()
    for name in sorted(modules):
        path = files.get(name)
        if path is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            out.errors.append(f"{shown(path, root)}: cannot be parsed ({exc})")
            continue
        visitor = _Visitor()
        visitor.visit(tree)
        seen: dict[tuple[str, str], int] = {}
        for line, col, qual, value in sorted(visitor.found, key=lambda t: (t[0], t[1])):
            n = seen.get((qual, repr(value)), 0)
            seen[(qual, repr(value))] = n + 1
            out.literals.append(Literal(name, qual, value, n, line, shown(path, root)))
    return out


def load_lists(path: Path) -> tuple[dict, list[str]]:
    """The module lists and the problems with their shape (never raises on a bad file)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"method": [], "parameter": [], "outside": {}}, [f"{path.name}: cannot be read ({exc})"]
    errs: list[str] = []
    clean: dict = {"method": [], "parameter": [], "outside": {}}
    if not isinstance(data, dict):
        return clean, [f"{path.name}: must be an object with method, parameter and outside"]
    for name in LISTS:
        value = data.get(name)
        if not isinstance(value, list) or not all(isinstance(m, str) and m for m in value):
            errs.append(f"{path.name}: '{name}' must be a list of module names")
        else:
            clean[name] = value
    outside = data.get("outside")
    if not isinstance(outside, dict):
        errs.append(f"{path.name}: 'outside' must be an object of module name to its reason")
    else:
        clean["outside"] = outside
        for mod, reason in outside.items():
            if not isinstance(reason, str) or not reason.strip():
                errs.append(f"{path.name}: outside module '{mod}' needs its one-sentence reason")
    extra = set(data) - {"method", "parameter", "outside"}
    if extra:
        errs.append(f"{path.name}: unknown key(s) {sorted(extra)}")
    return clean, errs


def check_lists(lists: dict, files: dict[str, Path]) -> list[str]:
    errs: list[str] = []
    seen: dict[str, list[str]] = {}
    for name in LISTS:
        for mod in lists[name]:
            seen.setdefault(mod, []).append(name)
    for mod in lists["outside"]:
        seen.setdefault(mod, []).append("outside")
    for mod, where in sorted(seen.items()):
        if len(where) > 1:
            errs.append(f"{mod}: is in more than one list ({', '.join(where)}); a module is in exactly one")
        if mod not in files:
            errs.append(f"{mod}: is listed ({', '.join(where)}) but the module does not exist under the pipeline root")
    for mod in sorted(set(files) - set(seen)):
        errs.append(f"{mod}: is in no list (method, parameter or outside); review it and add it to scripts/unit_constants_modules.json")
    return errs


def load_baseline(path: Path) -> tuple[dict, list[str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}, []
    except (OSError, ValueError) as exc:
        return {}, [f"{path.name}: cannot be read ({exc})"]
    if not isinstance(data, dict):
        return {}, [f"{path.name}: must be an object keyed module::qualname::value::ordinal"]
    return data, []


def check_entry(key: str, entry) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{key}: the baseline entry must be an object with class, unit and reason"]
    if all(entry.get(name) == TODO for name in ("class", "unit", "reason")):
        return [f"{key}: TODO (class, unit and reason are not written); classify it or rewrite the literal against a quantity"]
    errs: list[str] = []
    klass = entry.get("class")
    if klass == TODO:
        errs.append(f"{key}: class is TODO; classify it (one of {', '.join(CLASSES)}) or rewrite the literal against a quantity")
    elif klass not in CLASSES:
        errs.append(f"{key}: class {klass!r} is not in the closed list ({', '.join(CLASSES)})")
    for name in ("unit", "reason"):
        value = entry.get(name)
        if not isinstance(value, str) or not value.strip():
            errs.append(f"{key}: {name} is required (words, never empty)")
        elif value.strip() == TODO:
            errs.append(f"{key}: {name} is TODO; write it")
    return errs


def write_baseline(path: Path, data: dict) -> None:
    rows = []
    for key in sorted(data):
        entry = data[key]
        ordered = {k: entry[k] for k in ("class", "unit", "reason") if k in entry} | {k: v for k, v in entry.items() if k not in ("class", "unit", "reason")}
        rows.append(f"{json.dumps(key, ensure_ascii=False)}: {json.dumps(ordered, ensure_ascii=False)}")
    body = "{\n" + ",\n".join(rows) + "\n}\n" if rows else "{}\n"
    path.write_text(body, encoding="utf-8", newline="\n")


def group_of(module: str) -> str:
    m = re.match(r"cases/c(\d\d)", module)
    return f"C{m.group(1)}" if m else module.split("/")[0]


def counts(lists: dict, found: Walk) -> list[str]:
    lines = []
    for name in LISTS:
        mods = set(lists[name])
        lits = [x for x in found.literals if x.module in mods]
        groups: dict[str, int] = {}
        for x in lits:
            groups[group_of(x.module)] = groups.get(group_of(x.module), 0) + 1
        lines.append(f"{name}: {len(mods)} modules, {len(lits)} literals")
        lines.append("  per group: " + ", ".join(f"{g} {n}" for g, n in sorted(groups.items(), key=lambda t: (-t[1], t[0]))))
    lines.append(f"outside: {len(lists['outside'])} modules")
    return lines


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=REPO / "data-pipeline" / "pipeline", help="the pipeline root to walk")
    ap.add_argument("--modules", type=Path, default=HERE / "unit_constants_modules.json", help="the reviewed module lists")
    ap.add_argument("--baseline", type=Path, default=HERE / "unit_constants_baseline.json", help="the reviewed literal baseline")
    ap.add_argument("--update", action="store_true", help="add new literals as TODO and drop the entries whose literal is gone")
    ap.add_argument("--counts", action="store_true", help="print the literals per list and per case group")
    args = ap.parse_args(argv)

    lists, problems = load_lists(args.modules)
    files = module_files(args.root)
    problems += check_lists(lists, files)
    found = walk(args.root, [*lists["method"], *lists["parameter"]])
    problems += found.errors
    base, base_problems = load_baseline(args.baseline)
    problems += base_problems

    if args.counts:
        print("\n".join(counts(lists, found)))

    if args.update:
        if problems:
            print(f"check_unit_constants: --update refused, the lists or the sources have problems ({RULE}):")
            print("\n".join(f"  {p}" for p in problems))
            return 1
        keys = {x.key for x in found.literals}
        new = {k: base[k] for k in keys if k in base}
        added = sorted(keys - set(base))
        for k in added:
            new[k] = {"class": TODO, "unit": TODO, "reason": TODO}
        dropped = sorted(set(base) - keys)
        write_baseline(args.baseline, new)
        todo = sum(1 for e in new.values() if isinstance(e, dict) and e.get("class") == TODO)
        print(f"check_unit_constants: baseline written, {len(new)} entries ({len(added)} added, {len(dropped)} dropped, {todo} TODO)")
        return 0

    by_key = {x.key: x for x in found.literals}
    for key, lit in sorted(by_key.items(), key=lambda t: (t[1].path, t[1].line)):
        if key not in base:
            problems.append(f"{lit.path}:{lit.line}: float literal {lit.value!r} has no baseline entry ({key}); justify it with its "
                            f"class, unit and reason, or rewrite it against a quantity (--update adds it as TODO)")
    for key in sorted(base):
        if key in by_key:
            problems += check_entry(key, base[key])
        else:
            problems.append(f"{key}: the baseline entry has no literal in the walked modules; run --update to drop it")

    walked = len(set(lists["method"]) | set(lists["parameter"]))
    if problems:
        print(f"check_unit_constants: {len(problems)} finding(s) ({RULE}):")
        print("\n".join(f"  {p}" for p in problems))
        print(f"{walked} modules walked, {len(found.literals)} literals, {len(base)} baseline entries")
        return 1
    print(f"check_unit_constants: OK, {walked} modules walked, {len(found.literals)} literals, {len(base)} baseline entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
