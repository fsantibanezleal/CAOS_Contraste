"""The reader of the five UCI Polish bankruptcy files (ARFF, ``scipy.io.arff``), the identity convention and contract 1.

A file is a stack of financial statements: 64 ratios (``Attr1`` to ``Attr64``, ``?`` is missing) and the class (1 bankruptcy). There is
no firm identifier and no date, so the reader writes two named conventions for contract 1: ``id`` is ``<horizon>-<row>`` (the row
position in the file) and ``observation_date`` is the end of the span the UCI page gives. Nothing is filtered, recoded or imputed here.
The reader refuses a file whose row and bankruptcy counts differ from the UCI page (7,027, 10,173, 10,503, 9,792 and 5,910 rows with 271,
400, 495, 515 and 410 bankruptcies), so a changed release is a failure and not a silent change of the case.
"""
from __future__ import annotations

import hashlib
import io
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ...io import contract as c1
from ...io import fetch as fetching
from ...stages.ingest import IngestError, raw_file
from . import conventions as cv


class PolishFormatError(ValueError):
    """A file does not have the layout or the counts the case reads."""


class PolishSourceError(RuntimeError):
    """The raw zip is missing and the fetch from the UCI landing did not give it; C02 stops and names the file."""


@dataclass
class Horizon:
    """One file: the ratios as floats (NaN where the file says ``?``) and the class."""

    horizon_id: str
    years: int
    file: str
    X: pd.DataFrame
    y: np.ndarray

    @property
    def rows(self) -> int:
        return int(len(self.y))

    @property
    def events(self) -> int:
        return int(self.y.sum())


def ensure_zip(data_root: Path | str, *, fetcher: Callable[..., Any] | None = None, manifest: dict[str, Any] | None = None) -> Path:
    """The verified zip in ``<root>/raw/uci-polish/``; when it is absent the fetch from the UCI landing runs first, and when that does not
    answer C02 stops with the file named (missing-data rule: nothing stands in for it)."""
    root = Path(data_root)
    path = root / "raw" / cv.SOURCE_ID / cv.ZIP_NAME
    if not path.is_file():
        run = fetcher if fetcher is not None else fetching.fetch
        try:
            run(cv.SOURCE_ID, root=root)
        except Exception as exc:  # the fetch's own errors: network, licence, a changed hash
            raise PolishSourceError(f"C02 stops: {cv.ZIP_NAME} is not in {path.parent} and the fetch from the UCI landing failed ({exc})") from exc
    try:
        return raw_file(cv.SOURCE_ID, cv.ZIP_NAME, root, manifest)
    except IngestError as exc:
        raise PolishSourceError(f"C02 stops: {exc}") from exc


def read_arff(text: str, name: str) -> tuple[pd.DataFrame, np.ndarray]:
    """One ARFF member: the ratios by name and the class. The layout is checked (64 numeric attributes then the class {0,1})."""
    from scipy.io import arff

    try:
        data, meta = arff.loadarff(io.StringIO(text))
    except Exception as exc:  # scipy raises its own ParseArffError and others
        raise PolishFormatError(f"{name}: not a readable ARFF file ({exc})") from exc
    names = list(meta.names())
    if names != [*cv.ATTRIBUTES, "class"]:
        raise PolishFormatError(f"{name}: the attributes are not Attr1 to Attr64 and class: {names[:3]} ... {names[-2:]}")
    df = pd.DataFrame(data)
    cls = df["class"].map(lambda b: b.decode() if isinstance(b, bytes) else str(b))
    if not set(cls) <= {"0", "1"}:
        raise PolishFormatError(f"{name}: class values {sorted(set(cls))} are not 0 and 1")
    X = df[list(cv.ATTRIBUTES)].astype(float)
    return X.reset_index(drop=True), cls.astype(int).to_numpy()


def read_horizons(zip_path: Path | str, *, check_counts: bool = True) -> dict[int, Horizon]:
    """The five horizons by years ahead; the horizon of n years reads the file {6-n}year (decision G21)."""
    out: dict[int, Horizon] = {}
    with zipfile.ZipFile(zip_path) as z:
        for hid, years, member in cv.HORIZONS:
            if member not in z.namelist():
                raise PolishFormatError(f"{cv.ZIP_NAME}: the member {member} is missing")
            X, y = read_arff(z.read(member).decode("utf-8"), member)
            h = Horizon(hid, years, member, X, y)
            if check_counts and (h.rows, h.events) != cv.expected_counts(years):
                raise PolishFormatError(f"{member}: {h.rows} rows and {h.events} bankruptcies, the UCI page gives {cv.expected_counts(years)}")
            out[years] = h
    return out


# --- contract 1 -----------------------------------------------------------------------------------------------------------
def _t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


FIELDS: tuple[c1.Field, ...] = (
    *(c1.Field(a, "float", _t(f"Financial ratio {a} of the UCI Polish bankruptcy files", f"Razón financiera {a} de los archivos de quiebra polacos de UCI"),
               on_missing="flag") for a in cv.ATTRIBUTES),
    c1.Field("vector_key", "str", _t("Hash of the 64 ratios rounded to six decimals, used to count repeated feature vectors",
                                     "Hash de las 64 razones redondeadas a seis decimales, para contar vectores repetidos")),
)


def _duplicates(members: list[tuple[int, dict[str, Any]]], _params: dict[str, Any]) -> list[tuple[int, str]]:
    return [(i, "the same 64 ratios appear in an earlier row (a repeated statement, in this or another file)") for i, _ in members[1:]]


RULES: tuple[c1.Rule, ...] = (
    c1.Rule("C02-DUPLICATE-VECTOR", "group", "flag", "vector_key",
            _t("A row whose 64 ratios repeat an earlier row is kept and counted; the case does not remove it.",
               "Una fila cuyas 64 razones repiten una fila anterior se conserva y se cuenta; el caso no la elimina."),
            _duplicates, group_by=("vector_key",)),
)


def vector_keys(X: pd.DataFrame) -> list[str]:
    r = X.round(6).fillna(-9.99e99).to_numpy(dtype=float)
    return [hashlib.sha1(row.tobytes()).hexdigest() for row in r]


def contract_records(h: Horizon) -> list[dict[str, Any]]:
    keys = vector_keys(h.X)
    vals = h.X.to_numpy()
    recs = []
    for i in range(h.rows):
        rec: dict[str, Any] = {"id": f"{h.horizon_id}-{i + 1}", "observation_date": cv.OBSERVATION_DATE, "target": int(h.y[i]),
                               "vector_key": keys[i]}
        for j, a in enumerate(cv.ATTRIBUTES):
            v = vals[i, j]
            rec[a] = None if np.isnan(v) else float(v)
        recs.append(rec)
    return recs


def validate_contract(horizons: dict[int, Horizon]) -> c1.ContractReport:
    """Contract 1, ``scored_sample`` with the 64 ratios as its features; the report carries the missing counts and the repeated vectors."""
    records = [r for k in sorted(horizons) for r in contract_records(horizons[k])]
    return c1.validate("scored_sample", records, extra_fields=FIELDS, extra_rules=RULES)
