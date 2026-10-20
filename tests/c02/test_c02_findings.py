"""CT-0215: the findings of a C02 document are about its own rows; the oracle reads the test rows, never the producer's rules."""
from __future__ import annotations

from c02_support import VARIANTS, committed

FORBIDDEN = ("certif", "compliant", "compliance", "approved model", "regulatory threshold")
RULES = (   # (id, test ids, severity when a row is red, when amber)
    ("F-CALIBRATION-LEVEL", ("pd.jeffreys", "pd.binomial"), "S2", "S3"),
    ("F-CALIBRATION-FIT", ("pd.hosmer_lemeshow",), "S3", "S4"),
    ("F-STABILITY", ("stability.psi",), "S2", "S3"),
    ("F-OVERFIT", ("ml.overfit",), "S3", "S3"),
)
LIMITS = {"F-NO-OUT-OF-TIME": ("S4", "accepted", "design:no-date"), "F-HORIZON-MAPPING": ("S3", "open", "design:uci-horizon-mapping"),
          "F-FIRM-OVERLAP": ("S4", "accepted", "design:firm-overlap-unknown")}


def key(r: dict) -> str:
    return f"{r['test_id']}@{r['model_id']}@{r['segment']}"


def expected(doc: dict) -> dict[str, tuple[str, set[str]]]:
    out: dict[str, tuple[str, set[str]]] = {}
    for fid, ids, red, amber in RULES:
        hit = [r for r in doc["tests"] if r["test_id"] in ids and r["model_id"] and r["light"] in ("red", "amber")]
        if hit:
            sev = red if any(r["light"] == "red" for r in hit) else amber
            out[fid] = (sev, {key(r) for r in hit})
    gap = [r for r in doc["tests"] if r["test_id"] == "disc.delong" and r["light"] in ("red", "amber") and r["extras"]["difference"] > 0]
    if gap:
        out["F-CHALLENGER-GAP"] = ("S3" if any(r["light"] == "red" for r in gap) else "S4", {key(r) for r in gap})
    return out


def test_the_committed_findings_cite_only_their_own_rows_and_state_the_limits() -> None:
    for name in VARIANTS:
        doc = committed(name)
        rows = {key(r) for r in doc["tests"]} | {f"{r['test_id']}@{r['model_id']}" for r in doc["tests"]}
        by_id = {f["id"]: f for f in doc["findings"]}
        assert len(by_id) == len(doc["findings"])
        want = expected(doc)
        for fid, (sev, ev) in want.items():
            f = by_id[fid]
            assert f["severity"] == sev and f["status"] == "open" and set(f["evidence"]) == ev, (name, fid)
        assert {k for k in by_id if k not in LIMITS} == set(want), (name, sorted(by_id))
        for fid, (sev, status, ev) in LIMITS.items():
            assert (by_id[fid]["severity"], by_id[fid]["status"], by_id[fid]["evidence"]) == (sev, status, [ev]), (name, fid)
        for f in doc["findings"]:
            assert all(e in rows or e.startswith("design:") for e in f["evidence"]), (name, f["id"])
            blob = (f["title"]["en"] + f["title"]["es"]).lower()
            assert not any(w in blob for w in FORBIDDEN), (name, f["id"])
