"""The SGCD reader: the jsonl records of the Stressed German Credit Dataset (SGCD-v0.1, commit 8403fa9) to typed rows.

Each record holds a label (0 Bad, 1 Good), the batch metadata (S1 to S4 setup, A1 to A10 adaptation, T1 to T6 test), the structured view
(``json_view``, the 20 German credit attributes under the codebook's names) and the text view. A model that reads the structured view
alone is reached only by F1 (a ``null`` in 70 of 128 F1 records, U14 research addendum H4): the reader keeps the ``null`` as missing, never
as a code. The reader refuses a record that lacks a key, a batch outside the 20, a label outside 0 and 1 or a code outside the codebook.

The contract-1 conventions (decision V3 style, labelled): ``id`` is the SGCD identifier, ``observation_date`` is the date the German data
were donated to UCI (the data carry no date; the same stand-in as C01) and ``target`` is 1 for Bad (label 0), the default.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ...io.readers import GERMAN_OBSERVATION_DATE
from ..c01_features import GERMAN_CATEGORICAL, GERMAN_FEATURES

VERSION = "SGCD-v0.1"
SETUP = tuple(f"S{k}" for k in range(1, 5))
ADAPTATION = tuple(f"A{k}" for k in range(1, 11))
TEST = tuple(f"T{k}" for k in range(1, 7))
BATCHES = (*SETUP, *ADAPTATION, *TEST)
SEEN_BATCHES = ("T1", "T2", "T3")
HELD_OUT_BATCHES = ("T4", "T5", "T6")
SEMANTIC = ("F0", "F1", "F2", "F3", "F4")
#: SGCD attribute names (the codebook) to the German features of the C01 ladder; the sensitive and protected attributes are never inputs
FIELD_MAP = {
    "checking_account": "checking_status", "duration": "duration_months", "credit_history": "credit_history", "purpose": "purpose",
    "credit_amount": "credit_amount", "savings_account": "savings", "employment_since": "employment_since",
    "installment_rate": "installment_rate", "other_debtors": "other_debtors", "residence_since": "residence_since",
    "property": "property", "other_installment_plans": "other_installment_plans", "housing": "housing",
    "num_existing_credits": "existing_credits", "job": "job", "num_dependents": "people_liable", "telephone": "telephone"}
#: the three attributes the model never reads (protected or sensitive, never inputs; the codebook keeps them in the structured view)
UNUSED = ("personal_status_sex", "age", "foreign_worker")
JSON_KEYS = (*FIELD_MAP, *UNUSED)
#: the ten categorical fields F1 can drop (U14 research addendum H4 6.3: nulls by field) and the five F4 can contradict (metadata f4_policy)
F1_FIELDS = ("checking_account", "credit_history", "purpose", "savings_account", "employment_since", "other_debtors", "property",
             "other_installment_plans", "housing", "job")
F4_FIELDS = ("purpose", "housing", "other_installment_plans", "property", "job")
NUMERIC = ("duration", "credit_amount", "installment_rate", "residence_since", "num_existing_credits", "num_dependents")
_PERSONAL_SEX = {"A91": "male", "A93": "male", "A94": "male", "A92": "female", "A95": "female"}


class SgcdFormatError(ValueError):
    """A record or a file that does not match the dataset card; nothing is guessed."""


@dataclass
class Record:
    id: str
    label: int
    batch: str
    stage: str
    shock: str
    cosmetic: bool
    shock_field: str | None
    view: dict[str, Any]
    text: str


@dataclass
class Dataset:
    records: list[Record] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def batch_counts(self) -> dict[str, int]:
        return dict(Counter(r.batch for r in self.records))


def read_metadata(path: str | Path) -> dict[str, Any]:
    meta = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("seed", "shock_probabilities", "f4_policy", "numeric_noise_fields", "numeric_noise_probability", "version"):
        if key not in meta:
            raise SgcdFormatError(f"SGCDataset_metadata.json lacks {key!r}")
    if meta["version"] != VERSION or meta["seed"] != 42:
        raise SgcdFormatError(f"SGCDataset_metadata.json is version {meta['version']!r} seed {meta['seed']!r}, expected {VERSION} seed 42")
    return meta


def read_records(path: str | Path) -> list[Record]:
    out: list[Record] = []
    seen: set[str] = set()
    with Path(path).open("r", encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            where = f"{Path(path).name} line {n}"
            try:
                raw = json.loads(line)
                meta, value = raw["metadata"], raw["value"]
                view = value["json_view"]
                rec = Record(str(raw["id"]), int(raw["label"]), str(meta["batch"]), str(meta["stage"]), str(meta["shock_semantic"]),
                             bool(meta["shock_cosmetic"]), meta["shock_field"], dict(view), str(value["text_view"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise SgcdFormatError(f"{where}: {type(exc).__name__}: {exc}") from exc
            if raw.get("version") != VERSION:
                raise SgcdFormatError(f"{where}: version {raw.get('version')!r}, expected {VERSION}")
            if rec.id in seen:
                raise SgcdFormatError(f"{where}: identifier {rec.id} is repeated")
            seen.add(rec.id)
            if rec.label not in (0, 1):
                raise SgcdFormatError(f"{where}: label {rec.label} is neither 0 nor 1")
            if rec.batch not in BATCHES:
                raise SgcdFormatError(f"{where}: batch {rec.batch!r} is outside S1 to S4, A1 to A10 and T1 to T6")
            if rec.shock not in SEMANTIC:
                raise SgcdFormatError(f"{where}: shock {rec.shock!r} is outside F0 to F4")
            if set(rec.view) != set(JSON_KEYS):
                raise SgcdFormatError(f"{where}: json_view keys differ from the codebook: {sorted(set(rec.view) ^ set(JSON_KEYS))}")
            bad_null = [k for k, v in rec.view.items() if v is None and (k not in F1_FIELDS or rec.shock != "F1")]
            if bad_null:
                raise SgcdFormatError(f"{where}: a null in {bad_null} outside an F1 record")
            out.append(rec)
    if not out:
        raise SgcdFormatError(f"{Path(path).name}: no record")
    return out


def read_dataset(records_path: str | Path, metadata_path: str | Path) -> Dataset:
    return Dataset(read_records(records_path), read_metadata(metadata_path))


def sex_of(rec: Record) -> str:
    return _PERSONAL_SEX.get(str(rec.view.get("personal_status_sex")), "unknown")


def contract_records(records: list[Record]) -> list[dict[str, Any]]:
    """The records as contract-1 rows (``scored_sample``, German features of the C01 ladder; a null is a missing value)."""
    rows = []
    for r in records:
        row: dict[str, Any] = {"id": r.id, "observation_date": GERMAN_OBSERVATION_DATE, "target": 1 if r.label == 0 else 0,
                               "protected_attr": sex_of(r)}
        for src, dst in FIELD_MAP.items():
            v = r.view[src]
            row[dst] = None if v is None else (str(v) if dst in GERMAN_CATEGORICAL else v)
        rows.append(row)
    return rows


def feature_names() -> tuple[str, ...]:
    return GERMAN_FEATURES


# --- the text view, read for the consistency check of the shipped F4 shocks -----------------------------------------------------------
import re  # noqa: E402

TEXT_LABEL = {"purpose": "Purpose of credit", "housing": "Housing", "other_installment_plans": "Other installment plans",
              "property": "Property", "job": "Job"}
TEXT_SUFFIXES = (" (reported in application form)", " (as indicated in document)", " (recorded in submission)")


def read_codebook(path: str | Path) -> dict[str, dict[str, str]]:
    """The code to meaning tables of ``codebook.md`` (``### `field` `` headings followed by ``| `A11` | meaning |`` rows)."""
    meaning: dict[str, dict[str, str]] = {}
    cur: str | None = None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"### `(\w+)`", line)
        if m:
            cur = m.group(1)
            meaning[cur] = {}
            continue
        m = re.match(r"\| `(A\d+)` \| (.*) \|", line)
        if m and cur:
            meaning[cur][m.group(1)] = m.group(2)
    missing = [f for f in F4_FIELDS if not meaning.get(f)]
    if missing:
        raise SgcdFormatError(f"codebook.md lacks the tables of {missing}")
    return meaning


def text_meaning(rec: Record, field_name: str) -> str | None:
    """What the text view says about a field, without the F4 suffix variants; None when the sentence is absent."""
    m = re.search(rf"{re.escape(TEXT_LABEL[field_name])}: (.*?)(?: \| |\. [A-Z]|\.$)", rec.text)
    if m is None:
        return None
    value = m.group(1)
    for s in TEXT_SUFFIXES:
        value = value.removesuffix(s)
    return value.strip()


def consistency_pairs(records: list[Record], codebook: dict[str, dict[str, str]]) -> tuple[list[str], list[str]]:
    """The structured meaning and the text meaning of every checkable field of every record, as two equal-length lists (the input of
    ``dq_consistency``). A field is checkable when the structured value is present and the text states a meaning that is in the codebook
    (a coded or vague wording, as in F2, is not a contradiction and is left out)."""
    a: list[str] = []
    b: list[str] = []
    for r in records:
        for f in F4_FIELDS:
            code = r.view.get(f)
            said = text_meaning(r, f)
            if code is None or said is None or said not in codebook[f].values():
                continue
            a.append(codebook[f][str(code)])
            b.append(said)
    return a, b
