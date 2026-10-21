"""The c02-models document: every fitted rung of the five files and the pooled variant, with its internals, and the protocol."""
from __future__ import annotations

from typing import Any

from . import conventions as cv
from .fits import Fit


def summary(rung_record: dict[str, Any], hid: str, rid: str, with_details: bool) -> dict[str, Any]:
    """The model record of one rung of one document: the ladder's record with the document's id and the schema's rung code."""
    rec = dict(rung_record)
    rec["id"] = f"{hid}-{rid}"
    rec["rung"] = cv.RUNG_CODE[rid]
    if not with_details:
        rec.pop("details", None)
    return rec


def model_records(fit: Fit, with_details: bool, only: tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    out = []
    for rid, rung in fit.rungs.items():
        if only is not None and rid not in only:
            continue
        rec = summary(rung.record(), fit.horizon_id, rid, with_details)
        if with_details and rid == "P0-constant":
            rec["details"] = {**rec["details"], "preprocessing": fit.pp.record()}      # the fitted state, recorded once per fit
        out.append(rec)
    return out


def fit_document(fits: dict[str, Fit], protocol: dict[str, Any]) -> dict[str, Any]:
    first = next(iter(fits.values()))
    ladder = [{"rung": cv.RUNG_CODE[rid], "label": r.title, "engine": r.engine, "reference": "04 PD ladder P0 to P4 (application scorecards)"}
              for rid, r in first.rungs.items()]
    files = [{"horizon_id": f.horizon_id, "years": f.years, "file": f.file, "rows": int(len(f.y)), "events": int(f.y.sum())}
             for f in fits.values() if f.years is not None]
    return {"files": files, "ladder": ladder, "protocol": protocol, "parameters": cv.parameters()}
