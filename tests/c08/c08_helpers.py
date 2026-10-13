"""Helpers shared by the C08 tests: the document checks (schema, manifest listing, proxy, clipping, look-ahead, downturn, floors)
and the engine-logic scan. They return findings, so a test can plant a defect and assert that the check finds it."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np

from pipeline.cases.c08 import build as bd
from pipeline.core.schemas import validate_document

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "data" / "derived"
COHORT_IDS = ("2003-06", "2007-08", "2009-10", "2011-13", "2014-19", "2020-23")
VARIANT_IDS = tuple(f"dc-{c}" for c in COHORT_IDS)
#: fields a loan row would carry; no C08 document holds one
RAW_FIELDS = {"BorrName", "BorrStreet", "LocationID", "GrossApproval_amount", "ApprovalDate", "ChargeOffDate", "gross_approval",
              "approval_date", "origination_date", "chargeoff_date", "paid_date", "naics", "account_id", "BorrZip"}
ENGINE_FUNCTIONS = {
    "workout_lgd", "eba_discount_rate", "range_flag", "resolve_incomplete", "closed_before", "lgd_distribution", "endpoint_transform",
    "fit_ols", "fit_fractional_logit", "fit_beta", "fit_hurdle", "fit_tobit", "cure_decomposition", "predict_lgd",
    "identify_downturn", "downturn_add_on", "coverage_shortfall", "lgd_floor", "apply_lgd_floor", "lgd_calibration_by_segment",
    "lgd_calibration_over_time", "lgd_discrimination", "downturn_coverage",
}


def documents(root: Path) -> list[Path]:
    return sorted((root / "C08").glob("*.json"))


def problems(root: Path) -> list[str]:
    """Schema and listing findings of the C08 documents under a derived root (``data/derived`` or a bake's output root)."""
    out = []
    manifest_path = root / "manifests" / "C08.json"
    if not manifest_path.exists():
        return ["no manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        validate_document("data/derived/manifests/C08.json", manifest)
    except Exception as exc:  # noqa: BLE001
        out.append(f"manifest: {exc}")
    listed = {a["path"]: a["bytes"] for a in manifest["artifacts"]}
    files = {f"C08/{p.name}": p for p in documents(root)}
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


def currency_findings(doc) -> list[str]:
    return [f"currency {v}" for k, v in walk(doc) if k == "currency" and v != "USD"]


def freddie_findings(status: dict) -> list[str]:
    ok = status["freddie_mac_available"] is False and status["freddie_mac_reason"] and status["primary_source"] == bd.PRIMARY_SOURCE
    return [] if ok else ["freddie"]


def order_findings(manifest: dict, want=VARIANT_IDS) -> list[str]:
    got = [a["variant_id"] for a in manifest["artifacts"] if a["role"] == "variant"]
    return [] if tuple(got) == tuple(want) else [f"order {got}"]


def out_of_time_findings(outputs: dict, models: dict) -> list[str]:
    """The training cutoff precedes the cohort, every rung is trained to it and the comparison rows are the cohort's or later."""
    out = []
    first = outputs["cohort"]["first_year"]
    cutoff = outputs["training"]["cutoff_date"]
    if not cutoff < f"{first}-01-01":
        out.append(f"cutoff {cutoff} is not before the cohort {outputs['cohort']['id']}")
    for r in models["fit"]["ladder"]:
        if r["training_cutoff"] != cutoff:
            out.append(f"rung {r['rung_id']} trained to {r['training_cutoff']}, not {cutoff}")
    ids = [c["id"] for c in models["fit"]["cohorts"]]
    for row in outputs["realised_vs_predicted"]:
        if ids.index(row["cohort_id"]) < ids.index(outputs["cohort"]["id"]):
            out.append(f"a row of the earlier cohort {row['cohort_id']} is not out of time")
    return out


def lookahead_findings(train_dates: np.ndarray, cutoff: str) -> list[str]:
    late = np.asarray(train_dates, dtype="datetime64[D]") >= np.datetime64(cutoff, "D")
    return [f"{int(late.sum())} training defaults charged off on or after {cutoff}"] if late.any() else []


def open_workout_findings(train_dates: np.ndarray, cutoff: str, window_months: int = 12) -> list[str]:
    import pandas as pd

    end = (pd.Timestamp(cutoff) + pd.DateOffset(months=window_months)).to_datetime64().astype("datetime64[D]")
    d = np.asarray(train_dates, dtype="datetime64[D]")
    inside = (d >= np.datetime64(cutoff, "D")) & (d < end)
    return [f"{int(inside.sum())} open workouts of the window kept in the training set"] if inside.any() else []


def proxy_findings(outputs: dict, y: np.ndarray, charge_off: np.ndarray, approval: np.ndarray) -> list[str]:
    """The exposure sums and the cohort mean of a document against the raw defaults of the cohort."""
    out = []
    if outputs["lgd_proxy"]["exposure_field"] != "GrossApproval" or outputs["lgd_proxy"]["bias_direction"] != "downward":
        out.append("proxy statement")
    e = outputs["exposure"]
    if not np.isclose(e["gross_charge_off_total"], float(np.sum(charge_off)), rtol=1e-9):
        out.append("charge-off total")
    if not np.isclose(e["gross_approval_total"], float(np.sum(approval)), rtol=1e-9):
        out.append("approval total (another denominator)")
    if not np.isclose(outputs["lgd_distribution"]["mean"]["value"], float(np.mean(y)), rtol=1e-6):
        out.append("mean of the proxy")
    return out


def clipping_findings(distribution: dict, y: np.ndarray) -> list[str]:
    out = []
    if distribution["n_above_one"] != int((y > 1).sum()):
        out.append("count above one")
    if distribution["n_below_zero"] != int((y < 0).sum()):
        out.append("count below zero")
    if not np.isclose(distribution["highest"]["value"], float(y.max()), rtol=1e-9):
        out.append("highest value")
    return out


def range_findings(outputs: dict) -> list[str]:
    """Every predicted LGD of a document lies in [0, 1]."""
    out = []
    for row in outputs["realised_vs_predicted"]:
        if not 0.0 <= row["predicted"]["value"] <= 1.0:
            out.append(f"prediction {row['predicted']['value']} of {row['rung_id']}")
    for row in outputs["calibration_by_bucket"]:
        if not 0.0 <= row["predicted"]["value"] <= 1.0:
            out.append(f"bucket prediction {row['predicted']['value']} of {row['rung_id']}")
    for row in outputs["endpoint_sensitivity"]:
        if not 0.0 <= row["mean_predicted"]["value"] <= 1.0:
            out.append(f"endpoint prediction of {row['rung_id']}")
    return out


def result_row_findings(tests: list[dict]) -> list[str]:
    out = []
    for t in tests:
        if t["light"] == "not_evaluated" and any(t[k] is not None for k in ("statistic", "p_value", "metric")):
            out.append(f"{t['test_id']}@{t['model_id']}: a number on a not_evaluated light")
        if t["light"] == "not_evaluated" and not t["notes"]:
            out.append(f"{t['test_id']}@{t['model_id']}: no reason")
        if not t["test_id"].startswith("lgd_ead."):
            out.append(f"{t['test_id']} is not an engine LGD test")
    return out


def addon_findings(downturn: dict, flagged_cohorts: set[str]) -> list[str]:
    out = []
    for r in downturn["rows"]:
        if r["cohort_id"] not in flagged_cohorts:
            out.append(f"row {r['cohort_id']} is not a downturn cohort")
        if abs(r["add_on"] - (r["downturn_lgd"]["value"] - r["long_run_lgd"]["value"])) > 1e-9:
            out.append(f"add-on of {r['cohort_id']}")
    return out


def floor_findings(rows: list[dict]) -> list[str]:
    out = []
    ids = {c["id"]: c for c in bd.floor_cells_block()}
    for r in rows:
        cell = ids.get(r["floor_id"])
        if cell is None or cell["floor"] != r["floor"] or cell["reference"] != r["reference"]:
            out.append(f"{r['segment_id']}: not one of the 12 cells")
        if r["mean_after"]["value"] < r["mean_before"]["value"] or r["uplift"] < 0:
            out.append(f"{r['segment_id']}: a negative uplift")
        if abs(r["uplift"] - (r["mean_after"]["value"] - r["mean_before"]["value"])) > 1e-9:
            out.append(f"{r['segment_id']}: uplift is not the difference of the means")
    return out


def _defined_functions(tree):
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def engine_logic_findings(sources: dict[str, str]) -> list[str]:
    """Findings on a set of ``{file name: source text}``: an engine function defined in the product, or no import of the engine."""
    out = []
    imported = set()
    for name, text in sources.items():
        tree = ast.parse(text)
        for fn in sorted(_defined_functions(tree) & ENGINE_FUNCTIONS):
            out.append(f"{name}: defines {fn}, an engine function")
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("riskvalidation"):
                imported |= {a.name for a in n.names}
    return out + ([] if imported else ["no import from riskvalidation"])
