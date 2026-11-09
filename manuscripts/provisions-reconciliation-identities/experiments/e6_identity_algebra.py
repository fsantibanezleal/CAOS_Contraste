"""E6: the identities as a linear map on the table entries, checked against the engine, and what that map can see.

    python manuscripts/provisions-reconciliation-identities/experiments/e6_identity_algebra.py

The engine's identities (``riskvalidation.provisions.reconciliation.identity_residuals``) are linear in the entries of the
tables. This script writes the signed map ``A`` (one row per equation, one column per table entry) from the definitions of
the identities, plants a perturbation of 1,000,000 currency units on each entry in turn, and compares the engine's residual
of every identity with ``|A_j|`` times the perturbation (the engine takes the largest over the waterfall lines for one of its
identities, so the comparison for that identity is with the largest over the corresponding rows). It then reads from ``A``:
the rank, the entries no identity sees (zero columns), the number of identities that see each entry, and the groups of
entries that no pattern of failing identities can tell apart (equal columns up to sign).

Predictions, written before the first run of this script (the author of the unit, 2026-11-07):
  A1  the engine's residuals equal ``|A_j|`` times the perturbation for every entry of the six dates (largest deviation below
      1e-9 of the perturbation);
  A2  exactly one entry of the tables is seen by no identity: the model ECL of the POCI stage, which has no roll-forward row in
      the committed books;
  A3  the signed map has full row rank (no equation is a combination of the others), so the number of independent equations
      equals the number of equations (the engine's twelve identities, with the line identity counted once for each waterfall
      line);
  A4  the largest group of entries that no failing pattern distinguishes holds the opening, the closing and the movements of
      one stage row of the gross carrying amount (at least 11 entries), because those entries appear in one identity only.
Data: the six committed C06 documents. No random draw.
"""
from __future__ import annotations

import sys
from collections import defaultdict

import numpy as np

import common as c

DELTA = 1.0e6


def variables(book: c.Book) -> list[tuple]:
    v: list[tuple] = []
    for tag, tab in (("A", book.allowance), ("G", book.gca)):
        for s in c.STAGES:
            v.append((tag, s, "open"))
            v += [(tag, s, "mov", k) for k in tab[s]["movements"]]
            v.append((tag, s, "close"))
    v += [("W", i, l["kind"], l["id"]) for i, l in enumerate(book.lines)]
    v += [("E", s) for s in book.stage_ecl]
    return v


def bump(book: c.Book, var: tuple, delta: float) -> c.Book:
    b = book.copy()
    if var[0] in ("A", "G"):
        row = (b.allowance if var[0] == "A" else b.gca)[var[1]]
        if var[2] == "open":
            row["opening"] += delta
        elif var[2] == "close":
            row["closing"] += delta
        else:
            row["movements"][var[3]] += delta
    elif var[0] == "W":
        b.lines[var[1]]["amount"] += delta
    else:
        b.stage_ecl[var[1]] += delta
    return b


def equations(book: c.Book) -> list[tuple[str, dict[tuple, float]]]:
    """The signed equations: (identity name, {variable: coefficient})."""
    eqs: list[tuple[str, dict[tuple, float]]] = []
    for tag, name in (("A", "allowance-rollforward"), ("G", "gca-rollforward")):
        tab = book.allowance if tag == "A" else book.gca
        for s in c.STAGES:
            row = {(tag, s, "close"): 1.0, (tag, s, "open"): -1.0}
            row.update({(tag, s, "mov", k): -1.0 for k in tab[s]["movements"]})
            eqs.append((f"{name}:{s}", row))
    w_open = [(("W", i, l["kind"], l["id"])) for i, l in enumerate(book.lines) if l["kind"] == "opening"]
    w_close = [(("W", i, l["kind"], l["id"])) for i, l in enumerate(book.lines) if l["kind"] == "closing"]
    w_mov = [(("W", i, l["kind"], l["id"])) for i, l in enumerate(book.lines) if l["kind"] not in ("opening", "closing")]
    eqs.append(("waterfall-closes", {**{v: 1.0 for v in w_open}, **{v: 1.0 for v in w_mov}, **{v: -1.0 for v in w_close}}))
    eqs.append(("waterfall-equals-stage-closings", {**{("A", s, "close"): 1.0 for s in c.STAGES}, **{v: -1.0 for v in w_close}}))
    for v in w_mov:
        row = {v: 1.0}
        row.update({("A", s, "mov", v[3]): -1.0 for s in c.STAGES if v[3] in book.allowance[s]["movements"]})
        eqs.append(("waterfall-lines-equal-movements", row))
    for s in c.STAGES:
        eqs.append((f"stage-closing-equals-ecl:{s}", {("A", s, "close"): 1.0, ("E", s): -1.0}))
    return eqs


def analyse(date: str, book: c.Book) -> dict:
    vs = variables(book)
    eqs = equations(book)
    index = {v: j for j, v in enumerate(vs)}
    a = np.zeros((len(eqs), len(vs)))
    for i, (_, row) in enumerate(eqs):
        for v, coef in row.items():
            a[i, index[v]] = coef
    names = [n for n, _ in eqs]
    base = c.residuals(book)
    worst = 0.0
    for j, v in enumerate(vs):
        res = c.residuals(bump(book, v, DELTA))
        predicted: dict[str, float] = defaultdict(float)
        for i, n in enumerate(names):
            predicted[n] = max(predicted[n], abs(a[i, j]) * DELTA)
        for n, value in res.items():
            worst = max(worst, abs(value - predicted[n]) / DELTA)
    blind = [vs[j] for j in range(len(vs)) if not a[:, j].any()]
    seen_by = [int(np.count_nonzero(a[:, j])) for j in range(len(vs))]
    groups: dict[tuple, list[int]] = defaultdict(list)
    for j in range(len(vs)):
        if a[:, j].any():
            col = a[:, j] * (1.0 if a[np.flatnonzero(a[:, j])[0], j] > 0 else -1.0)
            groups[tuple(col.tolist())].append(j)
    sizes = sorted((len(g) for g in groups.values()), reverse=True)
    biggest = max(groups.values(), key=len)
    rank = int(np.linalg.matrix_rank(a))
    return {"entries": len(vs), "equations": len(eqs), "engine_identities": len(base), "rank": rank, "kernel_dimension": len(vs) - rank,
            "blind_entries": [list(map(str, b)) for b in blind], "worst_deviation_over_delta": worst,
            "seen_by_histogram": {str(k): seen_by.count(k) for k in sorted(set(seen_by))},
            "distinct_patterns": len(groups), "largest_group": sizes[0], "group_sizes_top5": sizes[:5],
            "largest_group_members": [list(map(str, vs[j])) for j in biggest][:14],
            "matrix": a.astype(int).tolist() if date == "2008-12" else None,
            "equation_names": names if date == "2008-12" else None,
            "variable_names": ["/".join(map(str, v)) for v in vs] if date == "2008-12" else None}


def main() -> int:
    books = c.committed_books()
    out = {d: analyse(d, b) for d, b in books.items()}
    c.save("e6_identity_algebra.json", {"meta": {"delta": DELTA, "dates": list(c.DATES)}, "dates": out})
    for d, r in out.items():
        print(d, {k: r[k] for k in ("entries", "equations", "engine_identities", "rank", "kernel_dimension", "worst_deviation_over_delta",
                                    "distinct_patterns", "largest_group")}, r["blind_entries"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
