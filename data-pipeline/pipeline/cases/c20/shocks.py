"""Contraste's own application of the SGCD shock families to the structured view (decision C5 of the U14 sizing), labelled.

The shipped SGCD shocks reach a model that reads ``json_view`` only through F1 (70 records); F2, F3, F4 and the numeric noise alter the text
view alone. So the second block of C20 applies each family to the structured view itself, with the parameters of
``SGCDataset_metadata.json`` (the fields, the probabilities, the seed 42). What the metadata does not say is a named convention, stated
here and in the documents:

- F1 (missingness): a selected record loses one field, drawn uniformly from the ten categorical fields the shipped F1 drops;
- F2 (ambiguity): a selected record has one or two fields (``uniform_1_to_max``, ``f2_max_fields`` 2) drawn uniformly from the thirteen
  categorical fields replaced by the modal code of the setup batches (a vague value that is still domain-valid); the metadata's
  ``f2_core_weight`` 0.7 names a core field set the metadata does not list, so it is not applied;
- F3 (cosmetic): surface formatting of the text; the structured view is unchanged by construction, so no record reaches it;
- F4 (contradiction): a selected record has one field of ``f4_policy.fields`` set to an adjacent domain-valid code of the codebook order
  (``adjacent_sampling``), the structured view then contradicting what the text view states;
- numeric noise: a selected record has ``duration`` rounded to the nearest 6 months and ``credit_amount`` to the nearest 500 DM (the
  text view says "roughly"; the metadata names the fields and the probability 0.1).

Each family selects a record with the probability of the metadata for the evaluation group (``test_seen``: 10 of 50 for F1 and F2, 0.2
for F3; ``test_unseen``: 20 of 50 for F4; 0.1 for the noise), from a random stream of seed 42. The unit of the draw is a record of the
group's batches that carries no shipped semantic shock.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..c01_features import _GERMAN_CODES
from .sgcd import F1_FIELDS, F4_FIELDS, FIELD_MAP

SEED = 42
F1_COLUMNS = tuple(FIELD_MAP[f] for f in F1_FIELDS)
F4_COLUMNS = tuple(FIELD_MAP[f] for f in F4_FIELDS)
F2_COLUMNS = tuple(_GERMAN_CODES)
F2_MAX_FIELDS = 2
DURATION_STEP = 6.0
AMOUNT_STEP = 500.0
FAMILIES = ("F1", "F2", "F3", "F4", "numeric-noise")
_STREAM = {name: k for k, name in enumerate(FAMILIES)}


@dataclass
class Applied:
    """The shocked frame and which records the shock changed (a record is selected when the draw picks it; it is changed when its
    structured view differs from the base)."""

    X: pd.DataFrame
    selected: np.ndarray
    changed: np.ndarray

    @property
    def n_selected(self) -> int:
        return int(self.selected.sum())

    @property
    def n_changed(self) -> int:
        return int(self.changed.sum())


def probability(meta: dict[str, Any], family: str, group: str) -> float:
    """The probability the metadata gives a family in an evaluation group (``seen`` or ``held-out``)."""
    probs = meta["shock_probabilities"]
    size = int(meta["batch_size"])
    if group == "seen":
        block = probs["test_seen"]
        if family in ("F1", "F2"):
            return block[family] / size
        if family == "F3":
            return float(meta["f3_probability"]["test_seen"])
    else:
        if family == "F4":
            return probs["test_unseen"]["F4"] / size
        if family == "F3":
            return float(meta["f3_probability"]["test_unseen"])
    if family == "numeric-noise":
        return float(meta["numeric_noise_probability"])
    raise KeyError(f"no probability for {family} in the {group} group")


def modal_codes(X_setup: pd.DataFrame) -> dict[str, str]:
    """The most frequent code of each categorical field on the setup batches (ties by code order)."""
    out = {}
    for col in F2_COLUMNS:
        counts = X_setup[col].dropna().astype(str).value_counts()
        top = counts[counts == counts.max()].index.tolist()
        out[col] = sorted(top)[0]
    return out


def adjacent(col: str, code: str, pick: int) -> str:
    """An adjacent domain-valid code of the codebook order (the single neighbour at an end of the list)."""
    order = _GERMAN_CODES[col]
    k = order.index(code)
    nb = [order[j] for j in (k - 1, k + 1) if 0 <= j < len(order)]
    return nb[pick % len(nb)]


def rng_for(family: str, group: str) -> np.random.Generator:
    return np.random.default_rng([SEED, _STREAM[family], 0 if group == "seen" else 1])


def apply(family: str, X: pd.DataFrame, meta: dict[str, Any], group: str, *, modal: dict[str, str]) -> Applied:
    """Apply a family to ``X`` (never in place) with the metadata probability of ``group`` and the seed-42 stream of the family."""
    p = probability(meta, family, group)
    rng = rng_for(family, group)
    n = len(X)
    pick = rng.random(n) < p
    out = X.copy()
    changed = np.zeros(n, dtype=bool)
    draws = rng.random((n, 4))
    if family == "F1":
        for i in np.flatnonzero(pick):
            col = F1_COLUMNS[int(draws[i, 0] * len(F1_COLUMNS))]
            if out.iloc[i][col] is not None and not (isinstance(out.iloc[i][col], float) and np.isnan(out.iloc[i][col])):
                out.iat[i, out.columns.get_loc(col)] = None
                changed[i] = True
    elif family == "F2":
        for i in np.flatnonzero(pick):
            k = 1 + int(draws[i, 0] * F2_MAX_FIELDS)
            first = int(draws[i, 1] * len(F2_COLUMNS))
            cols = [F2_COLUMNS[first]] + ([F2_COLUMNS[(first + 1 + int(draws[i, 2] * (len(F2_COLUMNS) - 1))) % len(F2_COLUMNS)]] if k == 2 else [])
            for col in cols:
                if out.iloc[i][col] != modal[col]:
                    out.iat[i, out.columns.get_loc(col)] = modal[col]
                    changed[i] = True
    elif family == "F3":
        pass  # cosmetic: the structured view is unchanged by construction
    elif family == "F4":
        for i in np.flatnonzero(pick):
            col = F4_COLUMNS[int(draws[i, 0] * len(F4_COLUMNS))]
            cur = out.iloc[i][col]
            if cur is not None and str(cur) in _GERMAN_CODES[col]:
                out.iat[i, out.columns.get_loc(col)] = adjacent(col, str(cur), int(draws[i, 1] * 2))
                changed[i] = True
    elif family == "numeric-noise":
        for i in np.flatnonzero(pick):
            d, a = float(out.iloc[i]["duration_months"]), float(out.iloc[i]["credit_amount"])
            nd, na = max(DURATION_STEP, round(d / DURATION_STEP) * DURATION_STEP), max(AMOUNT_STEP, round(a / AMOUNT_STEP) * AMOUNT_STEP)
            if nd != d or na != a:
                out.iat[i, out.columns.get_loc("duration_months")] = nd
                out.iat[i, out.columns.get_loc("credit_amount")] = na
                changed[i] = True
    else:
        raise KeyError(f"unknown family {family!r}")
    return Applied(out, pick, changed)
