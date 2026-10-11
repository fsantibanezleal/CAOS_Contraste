"""Stage export (contract 2): write an artifact through its builder and return the manifest entry for it.

Numbers are written with at most nine significant digits, enough for every statistic and probability the views
show and for the 1e-9 parity of additive scores (whose inputs are exported exactly, not rounded), so the committed
artifacts stay inside the trace budget. Writing is deterministic: the same inputs and seed give the same bytes.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from ..core.gate import classify_lane
from ..io.formats import write_json

SIG = 9


def compact(obj: Any, *, exact: frozenset[str] = frozenset()) -> Any:
    """Round floats to SIG significant digits, recursively; keys in ``exact`` are left untouched."""
    if isinstance(obj, float):
        if not math.isfinite(obj) or obj == 0.0:
            return obj if math.isfinite(obj) else None
        return float(f"{obj:.{SIG}g}")
    if isinstance(obj, dict):
        return {k: (v if k in exact else compact(v, exact=exact)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [compact(v, exact=exact) for v in obj]
    return obj


def write_artifact(root: Path, rel: str, artifact: dict[str, Any], *, exact: frozenset[str] = frozenset(),
                   engines: set[str], run_ms: float) -> dict[str, Any]:
    """Write one artifact; return ``{path, bytes, lane, gate}`` for the manifest.

    The artifact's own ``lane`` block states the verdict and its reasons; the manifest entry carries the measured
    gate with the final byte size. The verdict is measured on the bytes actually written (it is recomputed until
    writing the verdict no longer changes it)."""
    doc = compact(artifact, exact=exact)
    path = Path(root) / rel
    n = write_json(path, doc)
    for _ in range(3):
        gate = classify_lane(pure_python=False, wheels=engines, run_ms=run_ms, trace_bytes=n)
        block = {"lane": gate["lane"], "reasons": gate["reasons"], **{k: v for k, v in doc.get("lane", {}).items()
                                                                       if k not in ("lane", "reasons")}}
        if doc.get("lane") == block:
            break
        doc["lane"] = block
        n = write_json(path, doc)
    gate = classify_lane(pure_python=False, wheels=engines, run_ms=run_ms, trace_bytes=n)
    return {"path": rel, "bytes": n, "lane": gate["lane"], "gate": gate}
