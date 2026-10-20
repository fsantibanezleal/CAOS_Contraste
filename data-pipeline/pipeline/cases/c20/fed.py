"""The Federal Reserve 2025 hypothetical corporate portfolios (typical, higher and lower risk, 200 loans each), read both ways (decision Q7).

Reading (a): the real drift between the three portfolios, a known real shift with no model, the PSI, CSI, KS and chi-square tests of the
engine on each loan variable. Reading (b): the portfolios as the reference of a synthetic shift on the UCI evaluation set (``variants``
calibrates the size of the shift to the drift of the risk-defining variable, the rating).

The files carry loan variables only: no default outcome and no decision, so they cannot pass contract 1 as it stands (``scored_sample``
asks a decision of a sample that declares no outcome); the reader checks the layout itself and the report states the question.
A ``NA`` is a missing value (the term of a revolving line). The rating scale is the usual one, best to worst, a named ordinal convention.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

PORTFOLIOS = ("typical", "higher-risk", "lower-risk")
COLUMNS = ("loan_id", "committed_exposure_amt", "utilized_exposure_amt", "interest_rate", "term", "orig_year", "facility_type_cat",
           "lien_position_cat", "rating", "domestic_flag", "naics_two_digit_cat", "interest_rate_variability", "guarantor_flag")
#: the variables of the real-drift block: numeric amounts and dates, the rating on its ordinal scale and the coded categories
NUMERIC = ("committed_exposure_amt", "utilized_exposure_amt", "interest_rate", "term", "orig_year")
CODED = ("facility_type_cat", "lien_position_cat", "domestic_flag", "naics_two_digit_cat", "interest_rate_variability", "guarantor_flag")
VARIABLES = (*NUMERIC, "rating", *CODED)
RATING_SCALE = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D")
N_LOANS = 200


class FedFormatError(ValueError):
    """A file that does not match the portfolio layout; nothing is guessed."""


@dataclass
class Portfolio:
    name: str
    n: int
    columns: dict[str, np.ndarray]  # numeric arrays (NaN for NA); the rating as its ordinal position (1 = AAA)
    n_missing: dict[str, int]

    def __getitem__(self, key: str) -> np.ndarray:
        return self.columns[key]


def read_portfolio(path: str | Path, name: str, expected_rows: int | None = N_LOANS) -> Portfolio:
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader, None)
        if header is None or tuple(header) != COLUMNS:
            raise FedFormatError(f"{Path(path).name}: the header is not the portfolio layout: {header}")
        rows = [r for r in reader if r]
    if expected_rows is not None and len(rows) != expected_rows:
        raise FedFormatError(f"{Path(path).name}: {len(rows)} loans, the portfolio holds {expected_rows}")
    cols: dict[str, np.ndarray] = {}
    missing: dict[str, int] = {}
    ids = set()
    for j, c in enumerate(COLUMNS):
        vals: list[float] = []
        for i, r in enumerate(rows, start=1):
            if len(r) != len(COLUMNS):
                raise FedFormatError(f"{Path(path).name} loan {i}: {len(r)} cells for {len(COLUMNS)} columns")
            cell = r[j].strip()
            if c == "rating":
                if cell not in RATING_SCALE:
                    raise FedFormatError(f"{Path(path).name} loan {i}: rating {cell!r} is outside the scale {RATING_SCALE}")
                vals.append(float(RATING_SCALE.index(cell) + 1))
            elif cell in ("", "NA"):
                vals.append(float("nan"))
            else:
                try:
                    v = float(cell)
                except ValueError as exc:
                    raise FedFormatError(f"{Path(path).name} loan {i}: {c} {cell!r} is not a number") from exc
                if not np.isfinite(v):
                    raise FedFormatError(f"{Path(path).name} loan {i}: {c} {cell!r} is not finite")
                vals.append(v)
        arr = np.array(vals, dtype=float)
        if c == "loan_id":
            ids = set(arr.tolist())
            if len(ids) != len(arr) or np.isnan(arr).any():
                raise FedFormatError(f"{Path(path).name}: loan_id is not unique and complete")
        cols[c] = arr
        missing[c] = int(np.isnan(arr).sum())
    return Portfolio(name, len(rows), cols, missing)


def counts_for(ref: np.ndarray, cur: np.ndarray, bins: int, coded: bool) -> tuple[np.ndarray, np.ndarray]:
    """Counts of a reference and a current sample on bins fixed from the reference: its quantiles for a numeric variable, the union of
    the codes for a coded one. Missing values are left out."""
    from riskvalidation.validation.stability import bin_counts, quantile_edges

    a, b = ref[~np.isnan(ref)], cur[~np.isnan(cur)]
    if coded:
        levels = np.unique(np.concatenate([a, b]))
        return (np.array([(a == v).sum() for v in levels], dtype=float), np.array([(b == v).sum() for v in levels], dtype=float))
    edges = quantile_edges(a, bins)
    return bin_counts(a, edges).astype(float), bin_counts(b, edges).astype(float)


def drift_variables(ref: Portfolio, cur: Portfolio, model_id: str | None = None) -> tuple[list[dict[str, Any]], list[Any]]:
    """Per variable the PSI (10 reference-quantile bins), the CSI (5 bins), the KS statistic and the chi-square p-value, all through
    ``riskvalidation.validation.stability``; and the engine rows they come from. A coded variable counts its codes in both bins and the KS
    reads the code as an ordinal position (an indicator for the nominal codes, stated)."""
    from riskvalidation.validation import stability as st

    out: list[dict[str, Any]] = []
    rows: list[Any] = []
    for v in VARIABLES:
        coded = v in CODED or v == "rating"
        e10, a10 = counts_for(ref[v], cur[v], 10, coded)
        e5, a5 = counts_for(ref[v], cur[v], 5, coded)
        psi = st.stability_psi(e10, a10, model_id=model_id, segment=f"{ref.name}>{cur.name}:{v}")
        csi = st.stability_csi(e5, a5, model_id=model_id, segment=f"{ref.name}>{cur.name}:{v}")
        ks = st.stability_ks(ref[v][~np.isnan(ref[v])], cur[v][~np.isnan(cur[v])], model_id=model_id, segment=f"{ref.name}>{cur.name}:{v}")
        chi_p: float | None
        try:
            chi = st.stability_chi2(e10, a10, model_id=model_id, segment=f"{ref.name}>{cur.name}:{v}")
            chi_p = None if chi.p_value is None else float(chi.p_value)
            rows.append(chi)
        except ValueError:
            chi_p = None
        rows.extend([psi, csi, ks])
        out.append({"name": v, "psi": float(psi.metric), "csi": float(csi.metric), "ks": float(ks.statistic), "chi2_p_value": chi_p})
    return out, rows
