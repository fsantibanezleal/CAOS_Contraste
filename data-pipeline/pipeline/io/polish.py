"""The UCI Polish Companies Bankruptcy files: the publisher's layout and the ARFF reader every case shares (decision G19 of the U14 sizing).

The zip holds five ARFF files, ``1year`` to ``5year``: 64 ratios (``Attr1`` to ``Attr64``, ``?`` is missing) and the class (1
bankruptcy). The UCI page labels the file kyear with the bankruptcy status after 6 - k years, so the horizon of n years ahead reads the
file {6-n}year (decision G21). The reader checks the layout and, on request, the row and bankruptcy counts the UCI page gives (7,027,
10,173, 10,503, 9,792 and 5,910 rows with 271, 400, 495, 515 and 410 bankruptcies), so a changed release is a failure and not a silent
change of a case. It maps the files to floats (NaN where the file says ``?``) and the class, and does nothing else: the identity, date
and field conventions of contract 1 are each case's own (C02 in ``cases/c02/reader.py``, C20 in ``cases/c20/data.py``).
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE_ID = "uci-polish"
ZIP_NAME = "polish+companies+bankruptcy+data.zip"
ATTRIBUTES: tuple[str, ...] = tuple(f"Attr{k}" for k in range(1, 65))
#: horizon id, years ahead, ARFF member of the zip: the horizon of n years ahead reads the file {6-n}year (decision G21)
HORIZONS: tuple[tuple[str, int, str], ...] = tuple((f"h{n}", n, f"{6 - n}year.arff") for n in range(1, 6))
#: the rows and bankruptcies the UCI page and the probe of 2026-10-16 give, by file number; the reader refuses a file that differs
FILE_COUNTS: dict[int, tuple[int, int]] = {1: (7027, 271), 2: (10173, 400), 3: (10503, 495), 4: (9792, 515), 5: (5910, 410)}


def member(file_number: int) -> str:
    """The ARFF member of the file ``kyear``."""
    return f"{file_number}year.arff"


def expected_counts(years: int) -> tuple[int, int]:
    """(rows, bankruptcies) of the file that the horizon of ``years`` years ahead reads: the file {6 - years}year."""
    return FILE_COUNTS[6 - years]


class PolishFormatError(ValueError):
    """A file does not have the layout or the counts the dataset page gives; nothing is guessed."""


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


def read_arff(text: str, name: str) -> tuple[pd.DataFrame, np.ndarray]:
    """One ARFF member: the ratios by name and the class. The layout is checked (64 numeric attributes then the class {0,1})."""
    from scipy.io import arff

    try:
        data, meta = arff.loadarff(io.StringIO(text))
    except Exception as exc:  # scipy raises its own ParseArffError and others
        raise PolishFormatError(f"{name}: not a readable ARFF file ({exc})") from exc
    names = list(meta.names())
    if names != [*ATTRIBUTES, "class"]:
        raise PolishFormatError(f"{name}: the attributes are not Attr1 to Attr64 and class: {names[:3]} ... {names[-2:]}")
    df = pd.DataFrame(data)
    cls = df["class"].map(lambda b: b.decode() if isinstance(b, bytes) else str(b))
    if not set(cls) <= {"0", "1"}:
        raise PolishFormatError(f"{name}: class values {sorted(set(cls))} are not 0 and 1")
    X = df[list(ATTRIBUTES)].astype(float)
    return X.reset_index(drop=True), cls.astype(int).to_numpy()


def read_member(zip_path: Path | str, name: str) -> tuple[pd.DataFrame, np.ndarray]:
    """One member of the zip, read and checked by :func:`read_arff`."""
    with zipfile.ZipFile(zip_path) as z:
        if name not in z.namelist():
            raise PolishFormatError(f"{ZIP_NAME}: the member {name} is missing")
        return read_arff(z.read(name).decode("utf-8"), name)


def read_horizons(zip_path: Path | str, *, check_counts: bool = True) -> dict[int, Horizon]:
    """The five horizons by years ahead; the horizon of n years reads the file {6-n}year (decision G21)."""
    out: dict[int, Horizon] = {}
    for hid, years, name in HORIZONS:
        X, y = read_member(zip_path, name)
        h = Horizon(hid, years, name, X, y)
        if check_counts and (h.rows, h.events) != expected_counts(years):
            raise PolishFormatError(f"{name}: {h.rows} rows and {h.events} bankruptcies, the UCI page gives {expected_counts(years)}")
        out[years] = h
    return out
