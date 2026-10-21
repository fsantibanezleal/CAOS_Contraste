"""Helpers of the U15-P governance bake tests (ADR-0074: the bake reads the committed documents only, seconds, no fit, no CI)."""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIPE = ROOT / "data-pipeline" / "pipeline" / "governance"
INPUTS = PIPE / "inputs.json"
EDGES = PIPE / "edges.json"
DERIVED = ROOT / "data" / "derived"
COMMITTED = DERIVED / "governance"
FIXTURES = ROOT / "docs" / "contracts" / "fixtures" / "governance"
PAGE = ROOT / "docs" / "governance.md"
CHANGELOG = ROOT / "CHANGELOG.md"
SCHEMAS = "governance/governance-"

#: the four fixture entries of U15-S (docs/contracts/fixtures/governance) and the fields the full inventory moves (named, with the reason)
FIXTURE_ENTRIES = ["C01/german", "C07/banco-andino", "C18/banco-andino", "C22/generators"]


def load_semantics():
    """tests/contracts_u15/semantics.py under a name of its own (other suites ship a helper of the same name)."""
    name = "contraste_u15_semantics"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "tests" / "contracts_u15" / "semantics.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def contract_schemas():
    sys.path.insert(0, str(ROOT / "tests" / "contracts"))
    import contract_schemas as cs

    return cs


def schema_errors(rel_name: str, doc: dict) -> list[str]:
    """The schema errors of a governance document (rel_name: inventory, findings, appetite or report)."""
    return contract_schemas().errors(f"governance/governance-{rel_name}", doc)


def read(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def lf(text: str) -> str:
    return text.replace("\r\n", "\n")


def all_strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from all_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from all_strings(v)


def bilingual_pairs(node):
    """Every ``{"en": ..., "es": ...}`` object of a document."""
    if isinstance(node, dict):
        if set(node) == {"en", "es"} and isinstance(node["en"], str) and isinstance(node["es"], str):
            yield node
        for v in node.values():
            yield from bilingual_pairs(v)
    elif isinstance(node, list):
        for v in node:
            yield from bilingual_pairs(v)


def changelog_dates() -> dict[str, str]:
    return dict(re.findall(r"(?m)^## \[(\d\.\d\d\.\d\d\d)\], (\d{4}-\d\d-\d\d)$", CHANGELOG.read_text(encoding="utf-8")))


TREE = ("data/derived", "CHANGELOG.md", "data-pipeline/pipeline/governance/inputs.json", "data-pipeline/pipeline/governance/edges.json")


def copy_tree(dest: Path) -> Path:
    """The files the bake reads, copied under ``dest`` (18 MB): a test then breaks the copy, never the repository."""
    for rel in TREE:
        src = ROOT / rel
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, out, ignore=shutil.ignore_patterns("governance", "regulatory"))
        else:
            shutil.copyfile(src, out)
    return dest


def copied_texts():
    """The texts the documents copy verbatim from the case documents (see bake._copied_texts)."""
    from pipeline.governance import bake
    from pipeline.governance.readers import Reader, read_corpus

    return bake._copied_texts(read_corpus(Reader())[0])
