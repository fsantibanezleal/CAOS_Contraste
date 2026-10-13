"""Helpers shared by the C03 tests: hand-made loans in the reader's layout, the document checks (schema, manifest listing, the
5-year mark rule, currency) and the engine-logic scan. The checks return findings, so a test can plant a defect and assert that
the check finds it."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd

from pipeline.core.schemas import validate_document

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "data" / "derived"
COHORT_IDS = ("fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20")
#: fields that name or date a single loan: a document carries none (the vintage's gross_approval is a total, part of the contract)
RAW_FIELDS = {"BorrName", "BorrStreet", "LocationID", "GrossApproval", "ApprovalDate", "ChargeOffDate", "approval_date",
              "chargeoff_date", "paid_date", "naics", "approval", "exit_date", "account_id", "loan_id"}

COLUMNS = ["asof_date", "approval_date", "gross_approval", "guaranteed_approval", "interest_rate_pct", "term_months", "naics",
           "status", "paid_date", "chargeoff_date", "chargeoff_amount", "revolver"]


def frame(rows: list[dict]) -> pd.DataFrame:
    """Loans in the layout ``pipeline.io.sba.read_sba`` returns; a row names only what it changes."""
    base = {"asof_date": "2026-06-30", "approval_date": "2010-01-15", "gross_approval": 100_000.0, "guaranteed_approval": 75_000.0,
            "interest_rate_pct": None, "term_months": 120.0, "naics": "722511", "status": "P I F", "paid_date": "2012-06-01",
            "chargeoff_date": None, "chargeoff_amount": None, "revolver": False}
    data = [{**base, **r} for r in rows]
    df = pd.DataFrame(data, columns=COLUMNS)
    for c in ("asof_date", "approval_date", "paid_date", "chargeoff_date"):
        df[c] = pd.to_datetime(df[c])
    df["naics"] = df["naics"].astype("string")
    df["status"] = df["status"].astype("string")
    return df


def documents(root: Path) -> list[Path]:
    return sorted((root / "C03").glob("*.json"))


def problems(root: Path) -> list[str]:
    """Schema and listing findings of the C03 documents under a derived root (``data/derived`` or a bake's output root)."""
    out = []
    manifest_path = root / "manifests" / "C03.json"
    if not manifest_path.exists():
        return ["no manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        validate_document("data/derived/manifests/C03.json", manifest)
    except Exception as exc:  # noqa: BLE001
        out.append(f"manifest: {exc}")
    listed = {a["path"]: a["bytes"] for a in manifest["artifacts"]}
    files = {f"C03/{p.name}": p for p in documents(root)}
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


def walk(obj, path=()):
    """Every (key, value) pair of a document, recursively."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            yield from walk(v, (*path, k))
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, path)


def mark_findings(outputs: dict) -> list[str]:
    """The 5-year rule on a variant's outputs: a number only at an observed mark, null with a reason otherwise."""
    out = []
    asof = outputs["data_status"]["files_as_of"]
    for r in outputs["vintage_summary"]["rows"]:
        observed = r["five_year_mark_date"] <= asof
        if r["mark_observed"] != observed:
            out.append(f"FY{r['fiscal_year']}: mark_observed {r['mark_observed']} but the mark {r['five_year_mark_date']} vs as-of {asof}")
        if not observed and (r["observed_5y_pd"] is not None or r["gap"] is not None or not r["reason"]):
            out.append(f"FY{r['fiscal_year']}: a 5-year value before its mark")
    for s in outputs["stability"]["rows"]:
        row = next(x for x in outputs["vintage_summary"]["rows"] if x["fiscal_year"] == s["fiscal_year"])
        if not row["mark_observed"] and s["observed_5y_pd"] is not None:
            out.append(f"FY{s['fiscal_year']}: stability carries a 5-year value before the mark")
    return out


def currency_findings(doc: dict) -> list[str]:
    out = []
    for k, v in walk(doc):
        if k == "currency" and v != "USD":
            out.append(f"currency {v!r}")
    return out


def order_findings(variant_ids: list[str]) -> list[str]:
    return [] if list(variant_ids) == list(COHORT_IDS[: len(variant_ids)]) or list(variant_ids) == list(COHORT_IDS) else [
        f"variants out of order: {variant_ids}"]


def engine_function_names() -> set[str]:
    """The public function names of the engine's validation modules the case calls."""
    import importlib

    names = set()
    for mod in ("calibration", "discrimination", "stability", "rating_system"):
        m = importlib.import_module(f"riskvalidation.validation.{mod}")
        names |= {n for n in dir(m) if not n.startswith("_") and callable(getattr(m, n))
                  and getattr(getattr(m, n), "__module__", "") == m.__name__}
    return names


def defined_functions(source: str) -> set[str]:
    return {n.name for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
