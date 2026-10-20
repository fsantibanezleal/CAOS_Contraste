"""The UCI Polish Companies Bankruptcy reader, the 3-year file only (the base model of the Fed shift probes, decision Q6 (a)).

The Polish ARFF reader of ``cases/c02/`` belongs to U14-P1 and had not landed when this bake was written (R3 of the U14 sizing: U14-P2
imports it after it lands). This module is the minimal reader C20 needs, stated as a deviation in the report: the integrator replaces its
body by an import of ``cases/c02`` when both exist. It maps the publisher's layout to contract-1 records and does nothing else; the
64 ratios keep their names ``Attr1`` to ``Attr64`` (the files give no other name), a ``?`` is a missing value.

The files carry no firm identifier and no date: ``id`` is the row position in the file (``PL3-<row>``) and ``observation_date`` is the
last day of the dataset's span, 2013-12-31 (both named conventions, as the HMDA and German readers write theirs).
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from ...io.contract import Field

ZIP_NAME = "polish+companies+bankruptcy+data.zip"
SOURCE_ID = "uci-polish"
HORIZON = 3
MEMBER = f"{HORIZON}year.arff"
N_ATTR = 64
ATTRS = tuple(f"Attr{k}" for k in range(1, N_ATTR + 1))
OBSERVATION_DATE = "2013-12-31"


def _t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


FIELDS: tuple[Field, ...] = tuple(
    Field(a, "float", _t(f"Financial ratio {a} of the Polish Companies Bankruptcy data", f"Razón financiera {a} de los datos de quiebra de empresas polacas"),
          unit="ratio", on_missing="flag") for a in ATTRS)
MONOTONE: dict[str, int] = {a: 0 for a in ATTRS}


class PolishFormatError(ValueError):
    """A file that does not match the dataset page; nothing is guessed."""


def read_polish(zip_path: str | Path) -> list[dict[str, Any]]:
    """One record per firm-year row of the 3-year file: ``Attr1`` to ``Attr64`` (None for ``?``) and the bankruptcy flag as the target."""
    from scipy.io import arff

    with zipfile.ZipFile(zip_path) as z:
        text = z.read(MEMBER).decode("utf-8")
    data, meta = arff.loadarff(io.StringIO(text))
    names = list(meta.names())
    if names[:N_ATTR] != list(ATTRS) or names[N_ATTR:] != ["class"]:
        raise PolishFormatError(f"{MEMBER}: the attributes are not Attr1 to Attr{N_ATTR} and class: {names[:3]} ... {names[-2:]}")
    classes = {bytes(c).decode("ascii") for c in data["class"]}
    if not classes <= {"0", "1"}:
        raise PolishFormatError(f"{MEMBER}: class values {sorted(classes)} are not 0 and 1")
    records = []
    for k, row in enumerate(data, start=1):
        rec: dict[str, Any] = {"id": f"PL{HORIZON}-{k:05d}", "observation_date": OBSERVATION_DATE, "target": int(bytes(row["class"]).decode("ascii"))}
        for a in ATTRS:
            v = float(row[a])
            rec[a] = None if not np.isfinite(v) else v
        records.append(rec)
    return records
