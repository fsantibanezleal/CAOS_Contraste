"""The invariants of a C10 document set, returned as findings (an empty list when they hold); the tests assert the clean documents
hold them and the adversarial tests plant a defect and assert it is found. The cross-field identities of the contract are
``tests/contracts_u7/c10_checks.violations``, imported, never copied."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "contracts_u7"))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import c10_checks  # noqa: E402
import contract_schemas as cs  # noqa: E402

DERIVED = ROOT / "data" / "derived"


def violations(doc: dict[str, Any]) -> list[str]:
    return c10_checks.violations(doc)


def schema_findings(rel: str, doc: dict[str, Any]) -> list[str]:
    """The schema the document selects and its first errors (an unselected document is a finding)."""
    try:
        ref = cs.schema_for_document(ROOT / rel, doc)
    except cs.SelectionError as exc:
        return [str(exc)]
    return [f"{ref}: {e}" for e in cs.errors(ref, doc)[:3]]


def label_findings(doc: dict[str, Any]) -> list[str]:
    """A loan-type document labels its portfolio illustrative in the block and in the provenance."""
    bad = []
    if doc["outputs"]["portfolio"]["label"] != "illustrative":
        bad.append("portfolio.label is not illustrative")
    inputs = {i["source"]: i["class"] for i in doc["provenance"]["inputs"]}
    if inputs.get("illustrative-portfolio") != "illustrative":
        bad.append("the provenance has no illustrative-portfolio input of class illustrative")
    if doc["provenance"]["licence_classes"].get("illustrative-portfolio") != "illustrative":
        bad.append("licence_classes does not state illustrative-portfolio as illustrative")
    note = doc["outputs"]["portfolio"]["notice"]["en"].lower()
    if "illustrative" not in note or "never a bank" not in note:
        bad.append("the portfolio notice does not say illustrative and never a bank's")
    return bad


def window_findings(doc: dict[str, Any]) -> list[str]:
    """The fit uses fit-window years only: its count is the fit-window years with a rate and no evaluation year carries a fit role."""
    o = doc["outputs"]
    bad = []
    used = sum(1 for r in o["annual_rates"] if r["window"] == "fit" and r["loss_rate"] is not None)
    if o["fit"]["n_years_used"] != used:
        bad.append("fit.n_years_used counts years that are not fit-window years with a rate")
    if o["windows"]["fit"]["last_year"] >= o["windows"]["evaluation"]["first_year"]:
        bad.append("the windows overlap")
    return bad


def hash_findings(root: Path, case_dir: str = "C10") -> list[str]:
    """Every document under ``root/<case_dir>`` is listed by the checksum file with its digest, and by the manifest with its size."""
    bad = []
    sums = dict(reversed(line.split("  ", 1)) for line in (root / case_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    manifest = json.loads((root / "manifests" / f"{case_dir}.json").read_text(encoding="utf-8"))
    listed = {a["path"]: a for a in manifest["artifacts"]}
    files = sorted((root / case_dir).glob("*.json"))
    if set(sums) != {f"{case_dir}/{f.name}" for f in files} or set(listed) != set(sums):
        bad.append("the checksum file, the manifest and the folder do not list the same documents")
    for f in files:
        rel = f"{case_dir}/{f.name}"
        if hashlib.sha256(f.read_bytes()).hexdigest() != sums.get(rel):
            bad.append(f"{rel}: digest differs from the checksum file")
        if listed.get(rel, {}).get("bytes") != f.stat().st_size:
            bad.append(f"{rel}: size differs from the manifest")
    return bad
