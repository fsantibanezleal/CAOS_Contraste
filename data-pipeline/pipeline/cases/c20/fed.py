"""The Federal Reserve 2025 hypothetical corporate portfolios (typical, higher and lower risk, 200 loans each), read both ways (decision Q7).

Reading (a): the real drift between the three portfolios, a known real shift with no model, the PSI, CSI, KS and chi-square tests of the
engine on each loan variable. Reading (b): the portfolios as the reference of a synthetic shift on the UCI evaluation set (``variants``
calibrates the size of the shift to the drift of the risk-defining variable, the rating).

The files carry loan variables only: no default outcome and no decision. Contract 1 reads them as a population sample (decision G20,
``contract-family`` 1.3.0): a ``scored_sample`` with the dataset parameter ``outcome = population``, whose role is a shift probe, with the
twelve loan variables declared as the case's own fields (``CONTRACT_FIELDS``, ``CONTRACT_RULES``). The conventions are named: ``id`` is
the source ``loan_id`` written as an integer string and ``observation_date`` is ``2025-12-31``, the end of the year of the 2025 stress test
methodology data the files belong to. ``validate_portfolio`` runs the layout checks of ``read_portfolio`` and then contract 1, and stops on
any rejected row, naming the file and the row; nothing is dropped.
A ``NA`` is a missing value (the term of a revolving line). The rating scale is the usual one, best to worst, a named ordinal convention.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ...io import contract as c1
from .conv import t

PORTFOLIOS = ("typical", "higher-risk", "lower-risk")
COLUMNS = ("loan_id", "committed_exposure_amt", "utilized_exposure_amt", "interest_rate", "term", "orig_year", "facility_type_cat",
           "lien_position_cat", "rating", "domestic_flag", "naics_two_digit_cat", "interest_rate_variability", "guarantor_flag")
#: the variables of the real-drift block: numeric amounts and dates, the rating on its ordinal scale and the coded categories
NUMERIC = ("committed_exposure_amt", "utilized_exposure_amt", "interest_rate", "term", "orig_year")
CODED = ("facility_type_cat", "lien_position_cat", "domestic_flag", "naics_two_digit_cat", "interest_rate_variability", "guarantor_flag")
VARIABLES = (*NUMERIC, "rating", *CODED)
RATING_SCALE = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D")
N_LOANS = 200
#: contract 1 convention: the end of the year of the 2025 stress test methodology data the files belong to (fetch.py), as HMDA's is its activity year's 12-31
OBSERVATION_DATE = "2025-12-31"
#: the dataset parameters of the population sample
CONTRACT_PARAMS = {"outcome": "population"}


def _amount(name: str, en: str, es: str) -> c1.Field:
    return c1.Field(name, "float", t(en, es), unit="USD", lo=0.0)


def _code(name: str, en: str, es: str) -> c1.Field:
    return c1.Field(name, "int", t(en, es), unit="code", lo=0.0)


#: the twelve loan variables as extra fields of contract 1. The meanings follow Table 20 of the Federal Reserve's June 2025 supervisory stress
#: test methodology, "List of variables included in portfolios of hypothetical corporate loans"
#: (https://www.federalreserve.gov/publications/2025-june-supervisory-stress-test-methodology-modeled-loss-rates.htm, read 2026-10-20);
#: a unit the table does not state is read from the values of the files and labelled so.
CONTRACT_FIELDS: tuple[c1.Field, ...] = (
    _amount("committed_exposure_amt", "Committed exposure of the loan, in US dollars", "Exposición comprometida del préstamo, en dólares de EE.UU."),
    _amount("utilized_exposure_amt", "Utilized exposure of the loan, in US dollars (zero for an undrawn commitment)",
            "Exposición utilizada del préstamo, en dólares de EE.UU. (cero para un compromiso sin desembolsar)"),
    c1.Field("interest_rate", "float",
             t("Interest rate on the credit facility (Fed Table 20), as a decimal fraction read from the values (the file shows 0.0456 for a loan at 4.56 percent; 0.0 where the loan is undrawn); the table does not state the rate basis (annual, nominal)",
               "Tasa de interés de la facilidad de crédito (tabla 20 de la Fed), como fracción decimal leída de los valores (el archivo muestra 0.0456 para un préstamo al 4.56 por ciento; 0.0 donde el préstamo no está desembolsado); la tabla no indica la base de la tasa (anual, nominal)"),
             unit="decimal fraction", lo=0.0, hi=1.0),
    c1.Field("term", "int", t("Remaining term of the loan in months (Fed Table 20); NA is a missing value (the term of a revolving line), flagged and never imputed",
                              "Plazo remanente del préstamo en meses (tabla 20 de la Fed); NA es un valor faltante (el plazo de una línea rotativa), marcado y nunca imputado"),
             unit="months", lo=0.0, on_missing="flag"),
    c1.Field("orig_year", "int", t("Origination year", "Año de originación"), unit="year", lo=1900.0, hi=2100.0),
    _code("facility_type_cat", "Facility type, a category code", "Tipo de facilidad, un código de categoría"),
    _code("lien_position_cat", "Lien position, a category code", "Posición de gravamen, un código de categoría"),
    c1.Field("rating", "str", t("Internal rating on the usual scale AAA to D, best to worst, a named ordinal convention",
                                "Calificación interna en la escala usual AAA a D, de mejor a peor, una convención ordinal con nombre")),
    _code("domestic_flag", "Domestic borrower, a category code", "Prestatario doméstico, un código de categoría"),
    _code("naics_two_digit_cat", "Two-digit NAICS industry code", "Código de industria NAICS de dos dígitos"),
    _code("interest_rate_variability", "Interest rate variability, a category code", "Variabilidad de la tasa de interés, un código de categoría"),
    _code("guarantor_flag", "Guarantor, a category code (the file shows values beyond 0 and 1)",
          "Garante, un código de categoría (el archivo muestra valores más allá de 0 y 1)"),
)


def _rating_on_scale(rec: Any, _params: Any) -> str | None:
    if rec["rating"] not in RATING_SCALE:
        return f"rating {rec['rating']!r} is outside the scale {', '.join(RATING_SCALE)}"
    return None


CONTRACT_RULES: tuple[c1.Rule, ...] = (
    c1.Rule("C20-FED-RATING", "record", "reject", "rating",
            t("The rating is on the scale AAA, AA, A, BBB, BB, B, CCC, CC, C, D.", "La calificación está en la escala AAA, AA, A, BBB, BB, B, CCC, CC, C, D."),
            _rating_on_scale),
)


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


def contract_records(path: str | Path, expected_rows: int | None = N_LOANS) -> list[dict[str, Any]]:
    """The portfolio as contract 1 rows (the layout is checked by ``read_portfolio`` first): ``id`` is ``loan_id`` as an integer string,
    ``observation_date`` the named convention, the loan variables as the file writes them; ``NA`` is a missing value (None)."""
    read_portfolio(path, Path(path).stem, expected_rows)
    with Path(path).open("r", encoding="utf-8", newline="") as fh:
        rows = []
        for r in csv.DictReader(fh):
            row: dict[str, Any] = {"id": str(int(float(r["loan_id"]))), "observation_date": OBSERVATION_DATE}
            for v in VARIABLES:
                cell = r[v].strip()
                row[v] = None if cell in ("", "NA") else cell
            rows.append(row)
    return rows


def validate_portfolio(path: str | Path, name: str, expected_rows: int | None = N_LOANS) -> c1.ContractReport:
    """Contract 1 on one portfolio as a population sample. A rejected row stops the bake with the file and the row named."""
    rows = contract_records(path, expected_rows)
    report = c1.validate("scored_sample", rows, params=CONTRACT_PARAMS, extra_fields=CONTRACT_FIELDS, extra_rules=CONTRACT_RULES)
    if report.rejected:
        first = report.rejected[0]
        v = first["violations"][0]
        raise FedFormatError(f"{Path(path).name} ({name}): contract 1 rejects {len(report.rejected)} row(s); first is row {first['row'] + 1} "
                             f"(loan_id {first['key'].split()[0]}): {v['field']} {v['value']!r}: {v['reason']}, expected {v['expected']}")
    return report
