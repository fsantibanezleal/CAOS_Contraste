"""Helpers shared by the C06 tests: the document checks (schema, manifest listing, reconciliation) and the engine-logic scan.
They return findings, so a test can plant a defect and assert that the check finds it."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from riskvalidation.provisions import reconciliation as RC

from pipeline.cases.c06 import build as bd
from pipeline.core.schemas import validate_document

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "data" / "derived"
SIX = ("2006-12-31", "2008-12-31", "2010-12-31", "2019-12-31", "2020-06-30", "2023-06-30")
BATTERY = {"ifrs9.lifetime_pd_backtest", "ifrs9.sicr_effectiveness", "ifrs9.sicr_threshold_stability", "ifrs9.stage_migration_backtest",
           "ifrs9.ecl_backtest", "ifrs9.scenario_sensitivity", "ifrs9.nonlinearity", "ifrs9.overlay_diagnostics",
           "ifrs9.reconciliation_identities"}
RAW_FIELDS = {"BorrName", "BorrStreet", "LocationID", "GrossApproval", "ApprovalDate", "ChargeOffDate", "gross_approval", "approval_date",
              "origination_date", "chargeoff_date", "paid_date", "naics"}
def documents(root: Path) -> list[Path]:
    return sorted((root / "C06").glob("*.json"))


def problems(root: Path) -> list[str]:
    """Schema and listing findings of the C06 documents under a derived root (``data/derived`` or a bake's output root)."""
    out = []
    manifest_path = root / "manifests" / "C06.json"
    if not manifest_path.exists():
        return ["no manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        validate_document("data/derived/manifests/C06.json", manifest)
    except Exception as exc:  # noqa: BLE001
        out.append(f"manifest: {exc}")
    listed = {a["path"]: a["bytes"] for a in manifest["artifacts"]}
    files = {f"C06/{p.name}": p for p in documents(root)}
    for rel in sorted(set(files) - set(listed)):
        out.append(f"{rel} is not listed in the manifest")
    for rel in sorted(set(listed) - set(files)):
        out.append(f"{rel} is listed and missing")
    for rel, p in files.items():
        if rel in listed and listed[rel] != p.stat().st_size:
            out.append(f"{rel}: the manifest says {listed[rel]} bytes, the file has {p.stat().st_size}")
        try:
            validate_document(f"data/derived/{rel}", json.loads(p.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            out.append(f"{rel}: {exc}")
    return out


def walk(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def _rows(block):
    return [RC.RollForwardRow(r["stage"], r["opening"], tuple((m["line_id"], m["amount"]) for m in r["movements"]), r["closing"], r["residual"])
            for r in block]


def reconciliation_findings(out) -> list[str]:
    rec = out["reconciliation"]
    stage_ecl = {r["stage"]: r["ecl"] for r in out["stage_summary"]["rows"]} | {"poci": 0.0}
    overlays = [bd.Overlay(o["id"], o["rationale"]["en"], o["rationale"]["es"], o["method"], o["target"], o["segment_id"], o["stage"],
                           o["amount"], o["staging_effect"], o["review_date"], o["currency"]) for o in out["overlays"]]
    return RC.check_identities(_rows(rec["allowance"]), _rows(rec["gross_carrying_amount"]), out["waterfall"]["lines"], stage_ecl, overlays)



def battery_findings(tests: list[dict]) -> list[str]:
    ids = {t["test_id"] for t in tests}
    return [f"missing {i}" for i in sorted(BATTERY - ids)]


def currency_findings(doc) -> list[str]:
    return [f"currency {v}" for k, v in walk(doc) if k == "currency" and v != "USD"]


def trigger_findings(outputs: dict) -> list[str]:
    allowed = {"none", "relative-absolute", "threefold"}
    return [f"trigger {p['trigger']}" for p in outputs["sicr_points"] if p["trigger"] not in allowed]


def freddie_findings(outputs: dict) -> list[str]:
    st = outputs["data_status"]
    return [] if st["freddie_mac_available"] is False and st["freddie_mac_reason"] and st["primary_source"] == "sba-7a" else ["freddie"]


def order_findings(manifest: dict, dates=SIX) -> list[str]:
    want = [bd.variant_id(__import__("numpy").datetime64(d)) for d in dates]
    got = [a["variant_id"] for a in manifest["artifacts"] if a["role"] == "variant"]
    return [] if got == want else [f"order {got}"]


def _defined_functions(tree):
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def engine_logic_findings(sources: dict[str, str]) -> list[str]:
    """Findings on a set of ``{file name: source text}``: an engine function defined in the product, or called from a place
    other than an import of ``riskvalidation``."""
    out = []
    imported = set()
    for name, text in sources.items():
        tree = ast.parse(text)
        for fn in _defined_functions(tree) & ENGINE_FUNCTIONS:
            out.append(f"{name}: defines {fn}, an engine function")
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("riskvalidation"):
                imported |= {a.name for a in n.names}
    return out + ([] if imported else ["no import from riskvalidation"])



ENGINE_FUNCTIONS = {
    "from_hazard", "from_marginal", "from_cumulative", "forward_pd", "annualise_pd", "competing_risks", "ttc_to_pit", "implied_z",
    "weighted_pit_pd", "gauss_hermite_pit_pd", "sicr_quantitative", "allocate_stages", "apply_cure_probation", "collective_transfer",
    "discount_factors", "ecl_scenario", "probability_weighted_ecl", "stage3_ecl", "poci_allowance", "simplified_matrix_ecl",
    "commitment_ead", "non_linearity_index", "weight_sensitivity", "portfolio_allowance", "overlay_lines", "overlay_share",
    "total_allowance", "allowance_rollforward", "gca_rollforward", "check_identities", "lifetime_pd_backtest", "sicr_effectiveness",
    "sicr_threshold_stability", "stage_migration_backtest", "ecl_backtest", "scenario_sensitivity", "nonlinearity_test",
    "overlay_diagnostics", "reconciliation_identities",
}
