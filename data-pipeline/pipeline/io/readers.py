"""Readers for the raw files the cases read, each returning plain records for contract 1.

A reader maps the publisher's layout to the family's field names and does nothing else: no filtering, no recoding,
no imputation. What the data says outside its codebook is left for contract 1 to flag.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

# --- UCI Default of Credit Card Clients (Taiwan), Yeh and Lien (2009) ---------------------------------------------

TAIWAN_FILE = "default of credit card clients.xls"
TAIWAN_TARGET = "default payment next month"
TAIWAN_PAY = ("PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6")
TAIWAN_BILL = tuple(f"BILL_AMT{k}" for k in range(1, 7))
TAIWAN_PAID = tuple(f"PAY_AMT{k}" for k in range(1, 7))
#: the payment records run April to September 2005; the target is default in the next month
TAIWAN_OBSERVATION_DATE = "2005-09-30"


def read_taiwan(zip_path: str | Path) -> list[dict[str, Any]]:
    """One record per card holder: the 23 explanatory variables, the target, and SEX as the protected attribute."""
    import pandas as pd

    with zipfile.ZipFile(zip_path) as z:
        raw = z.read(TAIWAN_FILE)
    # the sheet has two header rows (X1..X23, Y and then the names); the names are the second
    df = pd.read_excel(io.BytesIO(raw), header=1, engine="xlrd")
    expected = {"ID", "LIMIT_BAL", "SEX", "EDUCATION", "MARRIAGE", "AGE", *TAIWAN_PAY, *TAIWAN_BILL, *TAIWAN_PAID,
                TAIWAN_TARGET}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"{TAIWAN_FILE}: the layout changed, missing columns {sorted(missing)}")
    sex = {1: "male", 2: "female"}
    records = []
    for row in df.to_dict(orient="records"):
        rec = {
            "id": f"TW{int(row['ID']):05d}",
            "observation_date": TAIWAN_OBSERVATION_DATE,
            "target": int(row[TAIWAN_TARGET]),
            "protected_attr": sex.get(int(row["SEX"]), f"code {row['SEX']}"),
            # MARRIAGE and AGE are passed through so contract 1 lists them as ignored: they are never model inputs
            "MARRIAGE": row["MARRIAGE"],
            "AGE": row["AGE"],
            "LIMIT_BAL": row["LIMIT_BAL"],
            "EDUCATION": row["EDUCATION"],
        }
        for col in (*TAIWAN_PAY, *TAIWAN_BILL, *TAIWAN_PAID):
            rec[col] = row[col]
        records.append(rec)
    return records


# --- UCI Statlog German Credit, Hofmann (1994) -------------------------------------------------------------------

GERMAN_FILE = "german.data"
#: attribute names, in file order (german.doc, section 7); attributes 9, 13 and 20 are protected and never inputs
GERMAN_ATTRIBUTES = (
    "checking_status", "duration_months", "credit_history", "purpose", "credit_amount", "savings",
    "employment_since", "installment_rate", "personal_status_sex", "other_debtors", "residence_since", "property",
    "age_years", "other_installment_plans", "housing", "existing_credits", "job", "people_liable", "telephone",
    "foreign_worker",
)
GERMAN_NUMERIC = ("duration_months", "credit_amount", "installment_rate", "residence_since", "age_years",
                  "existing_credits", "people_liable")
#: the data carry no date; the date the dataset was donated to UCI stands in for the observation date
GERMAN_OBSERVATION_DATE = "1994-11-16"
_GERMAN_SEX = {"A91": "male", "A93": "male", "A94": "male", "A92": "female", "A95": "female"}


def read_german(zip_path: str | Path) -> list[dict[str, Any]]:
    """One record per applicant: the 20 attributes by name, the target (1 = bad), sex as the protected attribute."""
    with zipfile.ZipFile(zip_path) as z:
        lines = z.read(GERMAN_FILE).decode("ascii").splitlines()
    records = []
    for k, line in enumerate(ln for ln in lines if ln.strip()):
        parts = line.split()
        if len(parts) != 21:
            raise ValueError(f"{GERMAN_FILE} line {k + 1}: {len(parts)} fields, expected 21")
        rec: dict[str, Any] = {"id": f"DE{k + 1:04d}", "observation_date": GERMAN_OBSERVATION_DATE}
        for name, value in zip(GERMAN_ATTRIBUTES, parts[:20]):
            rec[name] = value  # numbers stay text here; contract 1 parses them by their declared kind
        cls = parts[20]
        if cls not in ("1", "2"):
            raise ValueError(f"{GERMAN_FILE} line {k + 1}: class {cls!r}, expected 1 (good) or 2 (bad)")
        rec["target"] = 1 if cls == "2" else 0
        rec["protected_attr"] = _GERMAN_SEX.get(rec["personal_status_sex"], "unknown")
        records.append(rec)
    return records
