"""The invariants of a C13 document set, returned as violations (an empty list when they hold); the tests assert the clean
documents hold them and the adversarial tests plant a defect and assert it is found."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

IDS = ("none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment")
LIMITS = {0.025: 30, 0.01: 12}


def window_violations(hpl: Any, rtpl: Any, var: dict[float, Any]) -> list[str]:
    """A replication is exactly 250 finite days of HPL, RTPL and desk VaR at both levels."""
    bad = []
    series = {"hpl": hpl, "rtpl": rtpl, **{f"var@{a}": v for a, v in var.items()}}
    if sorted(var) != [0.01, 0.025]:
        bad.append(f"the VaR levels are {sorted(var)}, not 0.01 and 0.025")
    for name, s in series.items():
        a = np.asarray(s, dtype=float)
        if a.shape != (250,):
            bad.append(f"{name}: {a.shape[0] if a.ndim == 1 else a.shape} values, not 250")
        elif not np.isfinite(a).all():
            bad.append(f"{name}: a value is not finite")
    return bad


def independent(plan: dict[str, Any]) -> list[str]:
    """Every replication of the bake has its own seed: none repeats inside a variant or across the variants."""
    bad, seen = [], {}
    for v in plan["variants"]:
        seeds = list(v["seeds"])
        if seeds != [v["seed_base"] + i for i in range(len(seeds))]:
            bad.append(f"{v['deficiency_id']}: the seeds are not seed_base + replication_index")
        for s in seeds:
            if s in seen:
                bad.append(f"seed {s} is shared by {seen[s]} and {v['deficiency_id']}")
            seen[s] = v["deficiency_id"]
    return bad


def known_deficiency(doc: dict[str, Any]) -> list[str]:
    """The variant names its deficiency, carries the planted flag, the role, and the id of the variant is the deficiency."""
    o = doc["outputs"]
    k = o["known_deficiency"]
    bad = []
    if doc["variant_id"] != k["deficiency_id"] or k["deficiency_id"] not in IDS:
        bad.append(f"variant {doc['variant_id']} names deficiency {k['deficiency_id']}")
    if k["planted"] != (k["deficiency_id"] != "none"):
        bad.append("the planted flag contradicts the deficiency")
    if o["detection"]["role"] != ("power" if k["planted"] else "size"):
        bad.append("the detection role is not size for no deficiency and power for a planted one")
    if k["planted"] and not k["parameters"]:
        bad.append("a planted deficiency carries no parameter")
    return bad


def size(doc: dict[str, Any], max_share: float) -> list[str]:
    """The no-deficiency variant lands green: amber and red are at most ``max_share`` of the replications."""
    d = doc["outputs"]["detection"]
    bad = []
    if doc["outputs"]["known_deficiency"]["planted"]:
        bad.append("a planted variant presented as the size run")
    if d["share_amber_or_red"] > max_share:
        bad.append(f"amber or red in {d['share_amber_or_red']:.3f} of the replications, above {max_share}")
    return bad


def closure(doc: dict[str, Any]) -> list[str]:
    """The zone counts close on the replications and the detection block is the zone counts."""
    o = doc["outputs"]
    n = o["generator"]["n_replications"]
    z, d = o["pla"]["zones"], o["detection"]
    bad = []
    for k in ("overall", "spearman", "ks"):
        if sum(z[k].values()) != n:
            bad.append(f"{k}: the zone counts sum to {sum(z[k].values())}, not {n}")
    if d["n_red"] != z["overall"]["red"] or d["n_amber_or_red"] != z["overall"]["amber"] + z["overall"]["red"]:
        bad.append("the detection counts are not the zone counts")
    if not math.isclose(d["share_amber_or_red"], d["n_amber_or_red"] / n, abs_tol=1e-6):
        bad.append("share_amber_or_red is not the count over the replications")
    return bad


def desk_rows(doc: dict[str, Any]) -> list[str]:
    bad = []
    rows = doc["outputs"]["desk_backtest"]
    for r, alpha in zip(rows, (0.025, 0.01), strict=True):
        if r["alpha"] != alpha or r["limit_exceptions"] != LIMITS[alpha] or r["basis"] != "HPL":
            bad.append(f"desk row at {r['alpha']}: limit {r['limit_exceptions']} on {r['basis']}")
    tests = [t for t in doc["tests"] if t["test_id"] == "market.desk_backtest"]
    if sorted(t["segment"] for t in tests) != ["alpha=0.01", "alpha=0.025"]:
        bad.append("the desk back-test rows are not the two tail levels")
    for t in tests:
        a = float(t["segment"].split("=")[1])
        if t["metric"] != LIMITS[a]:
            bad.append(f"{t['segment']}: the row's limit is {t['metric']}")
    return bad


def synthetic(doc: Any) -> list[str]:
    """The document says it is synthetic (truth status and a notice in the generator block, in both languages)."""
    bad = []
    if doc["provenance"]["truth_status"] != "synthetic-known-truth":
        bad.append("the truth status is not synthetic-known-truth")
    if "synthetic" not in repr(doc).lower():
        bad.append("the word synthetic does not appear")
    gen = doc["outputs"]["generator"] if "outputs" in doc else doc["fit"]["generator"]
    if "synthetic" not in gen["notice"]["en"].lower() or "sint" not in gen["notice"]["es"].lower():
        bad.append("the generator notice does not say synthetic in both languages")
    return bad
