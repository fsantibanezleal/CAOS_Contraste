"""The HMDA reader: the Data Browser CSV of one activity year to typed rows, under the conventions of C21.

``read_year`` reads a file whose header uses the Data Browser spellings (hyphenated names, ``loan_to_value_ratio``) or the snapshot
spellings of the data dictionary (addendum H1 2.1) and returns the rows under the snapshot names. The missing markers ``NA``,
``Exempt`` and the empty cell are missing, never a number. The decision convention (C3) keeps action taken 1 and 2 as approval and 3
as denial and leaves 4 to 8 out, counted by code. The reader refuses a file that lacks a required column, holds a state other than
Delaware or another activity year, or holds a category or a code outside the dictionary: nothing is folded into a group.

``contract_records`` and ``validate_contract`` pass the decisions through contract 1 (``scored_sample``, ``outcome: none``, decision
V3): id is ``<activity_year>-<row>`` and the observation date is ``<activity_year>-12-31``, both conventions.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ...io import contract as c1
from . import legal

STATE = "DE"
#: the columns the bake reads, under the snapshot spellings
REQUIRED = ("activity_year", "state_code", "derived_ethnicity", "derived_race", "derived_sex", "applicant_age", "applicant_age_above_62",
            "action_taken",
            "loan_type", "loan_purpose", "lien_status", "occupancy_type", "loan_amount", "combined_loan_to_value_ratio",
            "property_value", "income", "debt_to_income_ratio", "rate_spread")
MISSING_MARKERS = frozenset({"", "NA", "Exempt"})
ATTRIBUTE_VALUES = {f: (*legal.GROUPS[f], *legal.NON_GROUPS[f]) for f in legal.ATTRIBUTES}
NOMINAL = {"loan_type": legal.LOAN_TYPES, "loan_purpose": legal.LOAN_PURPOSES, "lien_status": legal.LIEN_STATUSES,
           "occupancy_type": legal.OCCUPANCY_TYPES}


class HmdaFormatError(ValueError):
    """A file or a row that does not match the data dictionary; nothing is guessed."""


def canonical(name: str) -> str:
    """The snapshot spelling of a column: hyphens are underscores and the loan-to-value ratio is the combined one."""
    n = name.strip().replace("-", "_")
    return "combined_loan_to_value_ratio" if n == "loan_to_value_ratio" else n


def number(raw: str, where: str) -> float | None:
    """A number, or None for a missing marker; a text that is not a finite number is refused."""
    s = raw.strip()
    if s in MISSING_MARKERS:
        return None
    try:
        v = float(s)
    except ValueError as exc:
        raise HmdaFormatError(f"{where}: {raw!r} is not a number") from exc
    if v != v or v in (float("inf"), float("-inf")):
        raise HmdaFormatError(f"{where}: {raw!r} is not finite")
    return v


def dti_bin(raw: str, where: str) -> int | None:
    """The debt-to-income field recoded to the six published bins (index 0 to 5), None for a missing marker (a convention, C2)."""
    s = raw.strip()
    if s in MISSING_MARKERS:
        return None
    if s in legal.DTI_LABELS:
        return legal.DTI_LABELS[s]
    try:
        v = float(s)
    except ValueError as exc:
        raise HmdaFormatError(f"{where}: {raw!r} is not a published debt-to-income value") from exc
    if v < 20:
        return 0
    if v < 30:
        return 1
    if v < 36:
        return 2
    if v < 50:
        return 3
    return 4 if v <= 60 else 5


def nominal(raw: str, field_name: str, where: str) -> int:
    try:
        v = int(raw.strip())
    except ValueError as exc:
        raise HmdaFormatError(f"{where}: {field_name} {raw!r} is not a code") from exc
    if v not in NOMINAL[field_name]:
        raise HmdaFormatError(f"{where}: {field_name} code {v} is outside the dictionary {list(NOMINAL[field_name])}")
    return v


@dataclass
class YearRows:
    """One activity year: the decision rows (codes 1 to 3, in file order) and the count of every action code of the file."""

    year: int
    n_file_rows: int
    action_counts: dict[int, int]
    rows: list[dict[str, Any]] = field(default_factory=list)

    def n_left_out(self) -> int:
        return sum(v for k, v in self.action_counts.items() if k in legal.EXCLUDED_CODES)


def read_year(path: str | Path, year: int, state: str = STATE) -> YearRows:
    """Read one yearly file. ``row`` is the 1-based position of the data row in the file (the identity convention)."""
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise HmdaFormatError(f"{path.name}: the file is empty") from exc
        index: dict[str, int] = {}
        for i, name in enumerate(header):
            index.setdefault(canonical(name), i)
        missing = [c for c in REQUIRED if c not in index]
        if missing:
            raise HmdaFormatError(f"{path.name}: required columns are absent: {missing}")
        ix = {c: index[c] for c in REQUIRED}
        out = YearRows(year, 0, {})
        for n, rec in enumerate(reader, start=1):
            where = f"{path.name} row {n}"
            if len(rec) < len(header):
                raise HmdaFormatError(f"{where}: {len(rec)} cells for {len(header)} columns")
            if rec[ix["activity_year"]].strip() != str(year):
                raise HmdaFormatError(f"{where}: activity_year {rec[ix['activity_year']]!r}, the file is read as {year}")
            if rec[ix["state_code"]].strip() != state:
                raise HmdaFormatError(f"{where}: state_code {rec[ix['state_code']]!r}, the case reads {state}")
            try:
                action = int(rec[ix["action_taken"]].strip())
            except ValueError as exc:
                raise HmdaFormatError(f"{where}: action_taken {rec[ix['action_taken']]!r} is not a code") from exc
            if action not in legal.ACTION_NAMES:
                raise HmdaFormatError(f"{where}: action_taken {action} is outside 1 to 8")
            out.n_file_rows += 1
            out.action_counts[action] = out.action_counts.get(action, 0) + 1
            if action not in (*legal.APPROVAL_CODES, *legal.DENIAL_CODES):
                continue  # the convention leaves codes 4 to 8 out (they are counted above)
            row: dict[str, Any] = {"row": n, "action_taken": action, "decision": 1 if action in legal.APPROVAL_CODES else 0}
            for f in legal.ATTRIBUTES:
                v = rec[ix[f]].strip()
                raw = legal.RAW_VALUES.get(f)
                if raw is not None:                       # a field whose groups are named apart from its raw values (the 62 contrast)
                    if v not in raw:
                        raise HmdaFormatError(f"{where}: {f} {v!r} is outside the dictionary {list(raw)}")
                    v = raw[v]
                elif v not in ATTRIBUTE_VALUES[f]:
                    raise HmdaFormatError(f"{where}: {f} {v!r} is outside the dictionary {list(ATTRIBUTE_VALUES[f])}")
                row[f] = v
            for f in NOMINAL:
                row[f] = nominal(rec[ix[f]], f, where)
            for f in ("loan_amount", "combined_loan_to_value_ratio", "property_value", "income", "rate_spread"):
                row[f] = number(rec[ix[f]], f"{where}: {f}")
            row["dti_bin"] = dti_bin(rec[ix["debt_to_income_ratio"]], f"{where}: debt_to_income_ratio")
            out.rows.append(row)
    if out.n_file_rows == 0:
        raise HmdaFormatError(f"{path.name}: the file holds no data row")
    return out


# --- contract 1 (decision V3) -----------------------------------------------------------------------------------------
def _enum(name: str, values: tuple[str, ...], meaning: str) -> c1.Field:
    return c1.Field(name, "enum", legal.t(meaning), values=tuple(values))


CONTRACT_FIELDS = (
    *(_enum(f, ATTRIBUTE_VALUES[f], f"HMDA {f}, snapshot spelling") for f in legal.ATTRIBUTES),
    c1.Field("action_taken", "int", legal.t("HMDA action taken, 1 to 8"), lo=1, hi=8),
    c1.Field("loan_amount", "float", legal.t("Loan amount, rounded by the public release"), unit="USD", lo=0.0, lo_open=True, required=False),
    c1.Field("income", "float", legal.t("Gross annual income, thousands of USD"), unit="thousand USD", required=False),
    c1.Field("combined_loan_to_value_ratio", "float", legal.t("Combined loan-to-value ratio, percent"), unit="percent", lo=0.0, lo_open=True,
             required=False),
    c1.Field("property_value", "float", legal.t("Property value, rounded by the public release"), unit="USD", lo=0.0, lo_open=True,
             required=False),
)


def contract_records(rows: YearRows) -> list[dict[str, Any]]:
    """The decision rows as contract-1 records (the identity convention of decision V3)."""
    return [{"id": f"{rows.year}-{r['row']}", "observation_date": f"{rows.year}-12-31", "decision": r["decision"],
             **{f: r[f] for f in legal.ATTRIBUTES}, "action_taken": r["action_taken"], "loan_amount": r["loan_amount"],
             "income": r["income"], "combined_loan_to_value_ratio": r["combined_loan_to_value_ratio"],
             "property_value": r["property_value"]} for r in rows.rows]


def validate_contract(years: list[YearRows]) -> c1.ContractReport:
    """Contract 1, ``scored_sample`` with ``outcome: none``: the decision is required, the target is not."""
    records = [rec for y in years for rec in contract_records(y)]
    return c1.validate("scored_sample", records, params={"outcome": "none"}, extra_fields=CONTRACT_FIELDS)


# --- arrays -------------------------------------------------------------------------------------------------------------
@dataclass
class Sample:
    """The decision rows of one year as arrays (missing numbers are NaN, the missing debt-to-income bin is -1)."""

    year: int
    row: np.ndarray
    decision: np.ndarray
    action: np.ndarray
    attribute: dict[str, np.ndarray]
    dti_bin: np.ndarray
    cltv: np.ndarray
    income: np.ndarray
    loan_amount: np.ndarray
    property_value: np.ndarray
    rate_spread: np.ndarray
    nominal: dict[str, np.ndarray]

    def __len__(self) -> int:
        return int(self.decision.shape[0])


def to_sample(rows: YearRows) -> Sample:
    r = rows.rows

    def col(key: str) -> np.ndarray:
        return np.array([np.nan if x[key] is None else x[key] for x in r], dtype=float)

    return Sample(
        year=rows.year, row=np.array([x["row"] for x in r], dtype=np.int64), decision=np.array([x["decision"] for x in r], dtype=np.int64),
        action=np.array([x["action_taken"] for x in r], dtype=np.int64),
        attribute={f: np.array([x[f] for x in r], dtype=object) for f in legal.ATTRIBUTES},
        dti_bin=np.array([-1 if x["dti_bin"] is None else x["dti_bin"] for x in r], dtype=np.int64),
        cltv=col("combined_loan_to_value_ratio"), income=col("income"), loan_amount=col("loan_amount"),
        property_value=col("property_value"), rate_spread=col("rate_spread"),
        nominal={f: np.array([x[f] for x in r], dtype=np.int64) for f in NOMINAL})
