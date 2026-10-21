"""Helpers shared by the C16 tests: the committed samples (four call reports of the bank, a trimmed H.8 release page, a few Treasury
days), the semantic checks of the contract tests loaded by path (several suites ship a ``semantics.py``), and the checks the
document tests plant defects against. The checks return findings, so a test can plant a defect and assert that the check finds it."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
DERIVED = ROOT / "data" / "derived"
C16 = DERIVED / "C16"
MANIFEST = DERIVED / "manifests" / "C16.json"
CERT = 24735
VD = "2022-12-31"
SEED = 42
VARIANTS = ("lcr-standard", "list-adverse", "list-extreme", "fast-run", "htm-losses")
REVERSE = "reverse-stress"
MODELS = "models-svb-liquidity"
SMALL_DRAWS = 300     # the generator's verification draws at the test size (the committed bake uses 20,000)

for _p in (ROOT / "tests" / "contracts", ROOT / "data-pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


semantics = _load("c16_semantics", ROOT / "tests" / "contracts_u11" / "semantics.py")
import contract_schemas as cs  # noqa: E402  (tests/contracts, put on the path above)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def committed(name: str) -> dict[str, Any]:
    return load(C16 / f"{name}.json")


def committed_documents() -> dict[str, dict[str, Any]]:
    return {n: committed(n) for n in (*VARIANTS, REVERSE, MODELS)}


def mutated(doc: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(doc)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schema_errors(doc: dict[str, Any], name: str = "x") -> list[str]:
    ref = cs.schema_for_document(C16 / f"{name}.json", doc)
    return cs.errors(ref, doc)


def problems(doc: dict[str, Any], name: str = "x") -> list[str]:
    """Schema errors then semantic findings of one document."""
    return [*schema_errors(doc, name), *semantics.check_document(doc)]


def sample_reports():
    from pipeline.io import fdic

    return fdic.read_financials(DATA / "financials-sample.json", CERT)


def sample_report(date: str = VD):
    from pipeline.io import fdic

    return fdic.report_at(sample_reports(), date)


def h8_release():
    from pipeline.cases.c16 import h8

    return h8.parse_release((DATA / "h8-sample-20230317.html").read_text(encoding="utf-8"), "2023-03-17")


def sample_inputs(with_h8: bool = True):
    """The bake's inputs from the committed samples: four call reports, the Treasury days, one H.8 release page."""
    from pipeline.cases.c16 import bake, h8
    from pipeline.io import treasury

    rel = h8_release()
    series = None
    if with_h8:
        series = {"large-domestic-deposits": h8.weekly_series(rel, 6, "Deposits"),
                  "small-domestic-deposits": h8.weekly_series(rel, 8, "Deposits")}
    from pipeline.cases.c16 import fetch

    when = "2026-10-19"
    prov = {
        fetch.FDIC_DIR: [fetch.describe(DATA / "financials-sample.json", fetch.fdic_url(), when)],
        fetch.H8_DIR: [fetch.describe(DATA / "h8-sample-20230317.html", fetch.h8_url("20230317"), when)],
        # the review PDF (4 MB) is not committed: its record is the one of the real file, fetched on 2026-10-19
        fetch.SVB_DIR: [{"name": fetch.SVB_NAME, "url": fetch.SVB_URL, "bytes": 4079524, "retrieved": when,
                         "sha256": "601c32a73e833d3b2a2d6fa5d25a23c56eac85a6fa87558dcd5aa3e30a96f2d6"}],
        fetch.TREASURY_DIR: [fetch.describe(p, "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/", when)
                             for p in sorted((DATA / "treasury-par").glob("*.csv"))]}
    return bake.Inputs(
        reports=sample_reports(), curves=treasury.read_par(DATA / "treasury-par"), h8=series,
        h8_reason=None if with_h8 else "sample inputs without the H.8 release", provenance=prov, raw_urls={})


_BUILT: dict[str, Any] = {}


def built_sample(with_h8: bool = True):
    """The documents of the committed samples at the test size, built once per session."""
    from pipeline.cases.c16 import bake

    key = f"h8={with_h8}"
    if key not in _BUILT:
        _BUILT[key] = bake.build(SEED, sample_inputs(with_h8), n_draws=SMALL_DRAWS)
    return _BUILT[key]


def engine_findings(doc: dict[str, Any]) -> list[str]:
    """Recompute a scenario document's ladder through ``riskvalidation`` from the inputs the document carries and name every
    number that differs (the engine-call check of CT-1609, written so that a test can plant a number computed elsewhere)."""
    import numpy as np
    from riskvalidation.liquidity import ladder, runoff

    out: list[str] = []
    o = doc["outputs"]
    if o["path"] is None:
        return out
    lad = o["path"]["ladder"]
    h = len(lad["nlp"])
    opening = np.array([s["opening_balance"] for s in lad["segments"]])
    rates = np.vstack([np.ones(h) if s["daily_rates"] is None else np.array(s["daily_rates"]) for s in lad["segments"]])
    flows = ladder.behavioural_outflows(opening, rates)
    for k, s in enumerate(lad["segments"]):
        if not np.allclose(s["cumulative_outflow_share"], runoff.cumulative_outflow_path(rates[k]), rtol=1e-9, atol=1e-9):
            out.append(f"segment {s['segment']}: the cumulative outflow share is not the engine's")
        if not np.allclose(s["outflows"], flows[k], rtol=1e-9, atol=1e-6):
            out.append(f"segment {s['segment']}: the outflows are not the engine's")
    total_out = flows.sum(axis=0) + sum((np.array(f["amounts"]) for f in lad["other_outflows"]), np.zeros(h))
    total_in = sum((np.array(f["amounts"]) for f in lad["inflows"]), np.zeros(h))
    nlp = ladder.net_liquidity_position(np.array(lad["cbc_total"]), total_out, total_in)
    if not np.allclose(lad["nlp"], nlp, rtol=1e-9, atol=1e-6):
        out.append("the NLP is not the engine's")
    sv = ladder.survival_period(nlp)
    got = o["path"]["survival"]
    if (got["kind"] == "survives-horizon") != sv.survives or got["day"] != sv.day:
        out.append("the survival period is not the engine's")
    return out


def listing_findings(root: Path) -> list[str]:
    """The checksum file against the files of a derived root, and the manifest's sizes (the listing check of CT-1616)."""
    out: list[str] = []
    for line in (root / "C16" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, rel = line.split("  ", 1)
        if sha(root / rel) != digest:
            out.append(f"{rel}: differs from its checksum")
    manifest = json.loads((root / "manifests" / "C16.json").read_text(encoding="utf-8"))
    for a in manifest["artifacts"]:
        if (root / a["path"]).stat().st_size != a["bytes"]:
            out.append(f"{a['path']}: differs from the size the manifest lists")
    return out
