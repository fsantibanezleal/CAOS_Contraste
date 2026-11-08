"""E3: overlays as separate lines. A property sweep of the invariance, and the detection of five ways to book an overlay.

    python manuscripts/provisions-reconciliation-identities/experiments/e3_overlays.py

Part A (invariance, 3,000 draws). Each draw builds a book of three stage ECLs (log-normal), a set of overlays (zero to five,
signed, each a fraction of the model ECL, each in a stage or at portfolio level) and a second set, and passes them to the
engine's ``portfolio_allowance`` with one constructed account per stage. The relation checked is the one the engine documents:
the model ECL and the ECL by stage do not depend on the overlays, and the total allowance is the model ECL plus the sum of
the overlays (exactly rounded). The carried-by-stage rule is checked to sum to the overlay total.

Part B (placement). The six committed C06 tables hold no overlay, so one is constructed for the test: an overlay of a share
q (2%, 10%, 25%, the last the share the ECB found in the performing books of its sample in 2024) of the total allowance.
Booked correctly it sits in the allowance of stage 1 (the portfolio level goes to stage 1), as a movement of that row and as
a line of the waterfall, and the closing of both is raised; every identity must close. Five wrong bookings are planted, each
judged by the full gate, the stage gate and the pooled gate of ``common``:
  not-carried            the waterfall carries the overlay, the stage rows do not;
  wrong-stage            the overlay is carried in the stage 2 row, the waterfall line says portfolio level (stage 1);
  double-carried         the overlay is carried in the stage 1 and the stage 2 rows, once in the waterfall;
  carried-not-in-waterfall  the stage 1 row carries it and the waterfall closing is raised, with no overlay line;
  merged-into-model      the overlay is added to the model ECL of stage 1 and booked under the remeasurement line, so that
                         every table closes (the practice the separate-line rule exists to prevent).

Predictions, written before the first run of this script (the author of the unit, 2026-11-07):
  O1  zero violations of the invariance in 3,000 draws (a violation would be a defect of the engine);
  O2  the correct booking closes every identity on the six dates and the three shares (18 cases of 18);
  O3  the full gate flags the first four wrong bookings in 18 of 18 cases each; the stage gate and the pooled gate flag none
      of not-carried, wrong-stage and double-carried (wrong-stage and double-carried change a stage closing together with its
      movement, so the stage rows close), and flag carried-not-in-waterfall in 0 of 18 (the stage row closes);
  O4  no gate flags merged-into-model in any case (0 of 18): the identities cannot see it.
Repetitions: 3,000 draws in Part A seeded ``[SEED_BASE, 3, 0, draw]``; Part B is a full enumeration (6 dates x 3 shares).
"""
from __future__ import annotations

import math
import sys
import time

import numpy as np

import common as c
from riskvalidation.provisions import ecl as ecl_engine
from riskvalidation.provisions import overlays as ovl
from riskvalidation.provisions import reconciliation as rec

DRAWS = 3000
SHARES = (0.02, 0.10, 0.25)
STAGE_NAMES = (None, "stage1", "stage2", "stage3")


def make_overlays(rng: np.random.Generator, scale: float, tag: str) -> list[ovl.Overlay]:
    k = int(rng.integers(0, 6))
    out = []
    for i in range(k):
        out.append(ovl.Overlay(id=f"{tag}{i}", rationale_en="constructed for the sweep", rationale_es="construido para el barrido",
                               method="expert", target="pd", segment_id=None, stage=STAGE_NAMES[int(rng.integers(4))],
                               amount=float(scale * rng.uniform(-0.3, 0.6)), staging_effect="none", review_date="2026-11-07", currency="USD"))
    return out


def part_a() -> dict:
    bad_model = bad_total = bad_carry = 0
    n_with = 0
    worst_total = 0.0
    for k in range(DRAWS):
        rng = np.random.default_rng([c.SEED_BASE, 3, 0, k])
        e1, e2, e3 = (float(np.exp(rng.normal(18.0, 1.5))) for _ in range(3))
        stage = np.array([1, 2, 3])
        a, b = np.array([e1, 0.0, 0.0]), np.array([0.0, e2, 0.0])
        d = np.array([0.0, 0.0, e3])
        scale = e1 + e2 + e3
        o1, o2 = make_overlays(rng, scale, "A"), make_overlays(rng, scale, "B")
        base = ecl_engine.portfolio_allowance(stage, a, b, d)
        n_with += int(bool(o1) or bool(o2))
        for ovs in (o1, o2):
            run = ecl_engine.portfolio_allowance(stage, a, b, d, overlays=ovs)
            if run.model_total != base.model_total or run.by_stage != base.by_stage:
                bad_model += 1
            expected = base.model_total + math.fsum(o.amount for o in ovs)
            err = abs(run.total - expected)
            worst_total = max(worst_total, err / scale)
            if err > 1e-9 * scale:
                bad_total += 1
            if abs(math.fsum(rec.carried_by_stage(ovs).values()) - math.fsum(o.amount for o in ovs)) > 1e-9 * scale:
                bad_carry += 1
    return {"draws": DRAWS, "sets_checked": 2 * DRAWS, "draws_with_overlays": n_with, "model_changed": bad_model,
            "total_not_model_plus_overlays": bad_total, "carried_not_overlay_total": bad_carry, "worst_relative_total_error": worst_total}


def carried(book: c.Book, q: float, row_stage: str = "stage1", with_line: bool = True, line_stage: str | None = None,
            raise_waterfall_closing: bool = True) -> c.Book:
    b = book.copy()
    b.allowance[row_stage]["movements"]["overlay-X"] = b.allowance[row_stage]["movements"].get("overlay-X", 0.0) + q
    b.allowance[row_stage]["closing"] += q
    if with_line:
        b.lines.append({"id": "overlay-X", "kind": "overlay", "amount": q, "stage": line_stage})
    if raise_waterfall_closing:
        for line in b.lines:
            if line["kind"] == "closing":
                line["amount"] += q
    return b


def booking(book: c.Book, q: float, kind: str) -> c.Book:
    if kind == "correct":
        return carried(book, q)
    if kind == "not-carried":
        b = book.copy()
        b.lines.append({"id": "overlay-X", "kind": "overlay", "amount": q, "stage": None})
        for line in b.lines:
            if line["kind"] == "closing":
                line["amount"] += q
        return b
    if kind == "wrong-stage":
        return carried(book, q, row_stage="stage2", line_stage=None)
    if kind == "double-carried":
        b = carried(book, q)
        b.allowance["stage2"]["movements"]["overlay-X"] = q
        b.allowance["stage2"]["closing"] += q
        return b
    if kind == "carried-not-in-waterfall":
        return carried(book, q, with_line=False)
    if kind == "merged-into-model":
        b = book.copy()
        b.stage_ecl["stage1"] += q
        b.allowance["stage1"]["movements"]["remeasurement"] += q
        b.allowance["stage1"]["closing"] += q
        for line in b.lines:
            if line["id"] == "remeasurement" or line["kind"] == "closing":
                line["amount"] += q
        return b
    raise ValueError(kind)


KINDS = ("correct", "not-carried", "wrong-stage", "double-carried", "carried-not-in-waterfall", "merged-into-model")


def part_b() -> dict:
    books = c.committed_books()
    out = {k: {"full": [0, 0], "stage": [0, 0], "total": [0, 0], "identities": []} for k in KINDS}
    for d in c.DATES:
        total_allowance = math.fsum(r["closing"] for r in books[d].allowance.values())
        for q in SHARES:
            amount = q * total_allowance
            for kind in KINDS:
                bk = booking(books[d], amount, kind)
                res, lim = c.residuals(bk), c.limit(bk)
                cell = out[kind]
                for gate, verdict in (("full", c.gate_full(res, lim)), ("stage", c.gate_stage(res, lim)), ("total", c.gate_total(bk, lim))):
                    cell[gate][0] += int(verdict)
                    cell[gate][1] += 1
                cell["identities"].append(sum(1 for v in res.values() if not v <= lim))
    for k in KINDS:
        ids = out[k].pop("identities")
        out[k]["identities_flagged_min"], out[k]["identities_flagged_max"] = int(min(ids)), int(max(ids))
    return {"cases_per_booking": len(c.DATES) * len(SHARES), "shares": list(SHARES), "bookings": out}


def main() -> int:
    t0 = time.perf_counter()
    payload = {"meta": {"draws": DRAWS, "shares": list(SHARES), "seed_base": c.SEED_BASE}, "invariance": part_a(), "placement": part_b()}
    # the C07 committed overlays: the share they hold of the IFRS 9 allowance, and the model-ECL overstatement a merge would cause
    base = c.doc("C07/base.json")["outputs"]["ifrs9_detail"]
    ov = math.fsum(o["amount"] for o in base["overlays"])
    model = math.fsum(r["ecl"] for r in base["stage_summary"])
    payload["c07_base"] = {"overlay_total": ov, "model_ecl": model, "allowance": model + ov, "overlay_share_of_allowance": ov / (model + ov),
                           "merge_overstates_model_ecl_by": ov / model, "n_overlays": len(base["overlays"])}
    payload["meta"]["seconds"] = round(time.perf_counter() - t0, 1)
    c.save("e3_overlays.json", payload)
    print("done in", payload["meta"]["seconds"], "s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
