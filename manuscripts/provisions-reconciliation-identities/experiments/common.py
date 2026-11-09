"""What the experiment scripts of the provisions reconciliation manuscript share.

Every script is run from the repository root with the product's interpreter::

    python manuscripts/provisions-reconciliation-identities/experiments/<script>.py

and writes one compact JSON next to itself. The scripts read the committed C06 and C07 documents (``data/derived``) and the
engine ``riskvalidation`` 1.1.0; the pipeline's own C07 generator is called by ``e5_regimes.py``.

A *book* is the set of tables the identities of ``riskvalidation.provisions.reconciliation`` are judged on: the allowance
roll-forward by stage (IFRS 7 35H), the gross carrying amount roll-forward by stage (35I), the waterfall lines and the model
ECL by stage. A book is built from a committed document or resampled from one; a defect is a function of a book that returns
a changed copy. The gate is the engine's ``identity_residuals`` judged on the engine's tolerance basis
``tolerance * max(1, G)`` (the function ``limit``); the comparators judged on the same residuals or on a pooled row are the
functions ``gate_full``, ``gate_stage`` and ``gate_total``.
"""
from __future__ import annotations

import copy
import json
import math
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
MANUSCRIPT = HERE.parent
ROOT = HERE.parents[2]
DERIVED = ROOT / "data" / "derived"
sys.path.insert(0, str(ROOT / "data-pipeline"))

from riskvalidation.provisions import reconciliation as rec  # noqa: E402

DATES = ("2006-12", "2008-12", "2010-12", "2019-12", "2020-06", "2023-06")
SCENARIOS = ("base", "recession", "house-price-fall", "consumer-arrears-shock", "uf-inflation-spike", "combined-severe")
STAGES = ("stage1", "stage2", "stage3")
TOLERANCE = 1e-6
#: one base per script, so that no two scripts share a random stream; each script states how it derives its per-run seed
SEED_BASE = 20261104


def doc(rel: str) -> Any:
    """A committed document under ``data/derived`` (``"C06/rd-2008-12.json"``)."""
    return json.loads((DERIVED / rel).read_text(encoding="utf-8"))


def save(name: str, payload: Any) -> pathlib.Path:
    """Write ``experiments/<name>`` as compact, sorted JSON (so that a rerun with the same seeds is byte-identical)."""
    path = HERE / name
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    return path


def load(name: str) -> Any:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


@dataclass
class Book:
    """The tables of one reporting date. Amounts in the currency of the document."""

    allowance: dict[str, dict[str, Any]]      # stage -> {"opening", "movements": {line_id: amount}, "closing"}
    gca: dict[str, dict[str, Any]]
    lines: list[dict[str, Any]]               # waterfall lines: {"id", "kind", "amount", "stage"}
    stage_ecl: dict[str, float]
    label: str = ""
    extras: dict[str, Any] = field(default_factory=dict)

    def copy(self) -> "Book":
        return copy.deepcopy(self)

    def rows(self) -> tuple[list[rec.RollForwardRow], list[rec.RollForwardRow]]:
        """The roll-forward rows as the engine reads them. The dataclass is built directly: a defect may make a closing
        negative, which ``allowance_rollforward`` would refuse before any identity is judged."""
        def build(tab: dict[str, dict[str, Any]]) -> list[rec.RollForwardRow]:
            out = []
            for stage, r in tab.items():
                moves = tuple((k, float(v)) for k, v in r["movements"].items())
                out.append(rec.RollForwardRow(stage=stage, opening=float(r["opening"]), movements=moves, closing=float(r["closing"]),
                                              residual=float(r["closing"]) - (float(r["opening"]) + math.fsum(v for _, v in moves))))
            return out
        return build(self.allowance), build(self.gca)

    def gross(self) -> float:
        """G of the engine: the sum of the absolute closing amounts of the gross carrying amount rows."""
        return rec.gross_total(self.rows()[1])


def book_from_document(art: dict[str, Any], label: str = "") -> Book:
    """The tables of a committed C06 document (``outputs.reconciliation``, ``outputs.waterfall``, ``outputs.stage_summary``)."""
    out = art["outputs"]
    recon = out["reconciliation"]

    def table(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {r["stage"]: {"opening": float(r["opening"]), "movements": {m["line_id"]: float(m["amount"]) for m in r["movements"]},
                             "closing": float(r["closing"])} for r in rows}

    lines = [{"id": l["id"], "kind": l.get("kind", l["id"]), "amount": float(l["amount"]), "stage": l.get("stage")}
             for l in out["waterfall"]["lines"]]
    stage_ecl = {r["stage"]: float(r["ecl"]) for r in out["stage_summary"]["rows"]}
    return Book(table(recon["allowance"]), table(recon["gross_carrying_amount"]), lines, stage_ecl, label=label)


def committed_books() -> dict[str, Book]:
    return {d: book_from_document(doc(f"C06/rd-{d}.json"), d) for d in DATES}


def residuals(book: Book) -> dict[str, float]:
    """The absolute residual of every identity, by name (the engine's function, the carried overlay money read from the
    waterfall lines as the engine's own test reads it)."""
    allow, gca = book.rows()
    lines = [dict(l) for l in book.lines]
    return rec.identity_residuals(allow, gca, lines, book.stage_ecl, carried=rec.carried_from_lines(lines))


def limit(book: Book, tolerance: float = TOLERANCE) -> float:
    """``tolerance * max(1, G)``: the engine's tolerance basis."""
    return float(tolerance) * max(1.0, book.gross())


def family(name: str) -> str:
    """The family of an identity name."""
    return name.split(":")[0]


FAMILIES = ("allowance-rollforward", "gca-rollforward", "waterfall-closes", "waterfall-equals-stage-closings",
            "waterfall-lines-equal-movements", "stage-closing-equals-ecl")


def gate_full(res: dict[str, float], lim: float, drop: str | None = None) -> bool:
    """True when the gate flags the book: some identity (other than the dropped family) exceeds the limit."""
    return any(not v <= lim for k, v in res.items() if family(k) != drop)


def gate_stage(res: dict[str, float], lim: float) -> bool:
    """The disclosure arithmetic: only the two roll-forwards of each stage (IFRS 7 35H and 35I), no cross identity."""
    return any(not v <= lim for k, v in res.items() if family(k) in ("allowance-rollforward", "gca-rollforward"))


def gate_total(book: Book, lim: float) -> bool:
    """The pooled reconciliation: one allowance row and one gross carrying amount row for the whole book (opening plus all
    movements equals closing), judged by the engine on the same limit."""
    flagged = False
    for tab in (book.allowance, book.gca):
        opening = math.fsum(r["opening"] for r in tab.values())
        closing = math.fsum(r["closing"] for r in tab.values())
        moves = math.fsum(v for r in tab.values() for v in r["movements"].values())
        flagged = flagged or not abs(closing - (opening + moves)) <= lim
    return flagged


def gate_absolute(res: dict[str, float], absolute: float) -> bool:
    """A fixed absolute tolerance in units of money, the comparator of the tolerance basis."""
    return any(not v <= absolute for v in res.values())


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """The Wilson score interval of a proportion (Wilson 1927)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def rng_for(*key: int) -> np.random.Generator:
    return np.random.default_rng([SEED_BASE, *key])


# ---- defects: each returns a changed copy of the book ----------------------------------------------------------------

def _movement_ids(book: Book) -> list[str]:
    return list(next(iter(book.allowance.values()))["movements"].keys())


def d_allowance_movement(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """One movement of one stage's allowance changed by ``delta``, the closing left as it was."""
    b = book.copy()
    stage = STAGES[int(rng.integers(len(STAGES)))]
    line = _movement_ids(b)[int(rng.integers(len(_movement_ids(b))))]
    b.allowance[stage]["movements"][line] += delta
    return b


def d_allowance_closing(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """The closing allowance of one stage changed by ``delta``, the movements left as they were."""
    b = book.copy()
    stage = STAGES[int(rng.integers(len(STAGES)))]
    b.allowance[stage]["closing"] += delta
    return b


def d_stage_reallocation(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """``delta`` of allowance booked in stage b that belongs to stage a: both rows still close (a movement line carries the
    amount in each, with opposite signs), the sum of the stage closings, the waterfall and the line totals are unchanged."""
    b = book.copy()
    pair = rng.permutation(len(STAGES))[:2]
    a, c = STAGES[int(pair[0])], STAGES[int(pair[1])]
    line = "remeasurement" if "remeasurement" in b.allowance[a]["movements"] else _movement_ids(b)[0]
    b.allowance[a]["movements"][line] -= delta
    b.allowance[a]["closing"] -= delta
    b.allowance[c]["movements"][line] += delta
    b.allowance[c]["closing"] += delta
    return b


def d_gca_movement(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """One movement of one stage's gross carrying amount changed by ``delta``, the closing left as it was."""
    b = book.copy()
    stage = STAGES[int(rng.integers(len(STAGES)))]
    ids = list(b.gca[stage]["movements"].keys())
    b.gca[stage]["movements"][ids[int(rng.integers(len(ids)))]] += delta
    return b


def d_waterfall_line(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """One movement line of the waterfall changed by ``delta``."""
    b = book.copy()
    idx = [i for i, l in enumerate(b.lines) if l["kind"] not in ("opening", "closing")]
    b.lines[idx[int(rng.integers(len(idx)))]]["amount"] += delta
    return b


def d_waterfall_closing(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """The closing line of the waterfall changed by ``delta``."""
    b = book.copy()
    for l in b.lines:
        if l["kind"] == "closing":
            l["amount"] += delta
    return b


def d_stage_ecl(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """The model ECL of one stage changed by ``delta``."""
    b = book.copy()
    stage = STAGES[int(rng.integers(len(STAGES)))]
    b.stage_ecl[stage] += delta
    return b


def d_line_misclassification(book: Book, delta: float, rng: np.random.Generator) -> Book:
    """``delta`` booked under one movement line instead of another, consistently in the stage row and in the waterfall: every
    sum is unchanged, so no identity can see it (the negative control of the gate)."""
    b = book.copy()
    stage = STAGES[int(rng.integers(len(STAGES)))]
    ids = _movement_ids(b)
    pair = rng.permutation(len(ids))[:2]
    x, y = ids[int(pair[0])], ids[int(pair[1])]
    b.allowance[stage]["movements"][x] += delta
    b.allowance[stage]["movements"][y] -= delta
    for l in b.lines:
        if l["id"] == x:
            l["amount"] += delta
        elif l["id"] == y:
            l["amount"] -= delta
    return b


DEFECTS = {
    "allowance-movement": d_allowance_movement,
    "allowance-closing": d_allowance_closing,
    "stage-reallocation": d_stage_reallocation,
    "gca-movement": d_gca_movement,
    "waterfall-line": d_waterfall_line,
    "waterfall-closing": d_waterfall_closing,
    "stage-ecl": d_stage_ecl,
    "line-misclassification": d_line_misclassification,
}


def resample(book: Book, rng: np.random.Generator, sigma: float = 0.25) -> Book:
    """A clean book of the size and shape of ``book``: every opening and movement is multiplied by ``1 + sigma * eps`` (eps
    standard normal, truncated to keep the sign), every closing is the exact sum, the waterfall lines are the sums over the
    stages and the stage ECL is the stage closing. The identities hold by construction up to floating-point rounding."""
    b = book.copy()

    def jitter(x: float) -> float:
        if x == 0.0:
            return 0.0
        e = float(np.clip(rng.standard_normal(), -3.0, 3.0))
        return x * max(0.05, 1.0 + sigma * e)

    for tab in (b.allowance, b.gca):
        for r in tab.values():
            r["opening"] = jitter(r["opening"])
            r["movements"] = {k: jitter(v) for k, v in r["movements"].items()}
            r["closing"] = r["opening"] + math.fsum(r["movements"].values())
            if r["closing"] < 0:
                r["opening"] -= r["closing"]
                r["closing"] = 0.0
    ids = _movement_ids(b)
    for l in b.lines:
        if l["kind"] == "opening":
            l["amount"] = math.fsum(r["opening"] for r in b.allowance.values())
        elif l["kind"] == "closing":
            l["amount"] = math.fsum(r["closing"] for r in b.allowance.values())
        elif l["id"] in ids:
            l["amount"] = math.fsum(r["movements"][l["id"]] for r in b.allowance.values())
    b.stage_ecl = {s: b.allowance[s]["closing"] for s in b.allowance}
    return b
