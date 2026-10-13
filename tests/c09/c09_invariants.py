"""The invariants of a C09 document set, returned as violations (an empty list when they hold); the tests assert the clean
documents hold them and the adversarial tests plant a defect and assert it is found."""
from __future__ import annotations

import math
from typing import Any

import numpy as np

LEVELS = tuple(range(6))


def known_truth(out: dict[str, Any]) -> list[str]:
    """Every estimate sits beside the generator's known CCF of its level, and bias and tolerance flag are consistent."""
    bad = []
    truth = out["generator"]["true_ccf"]["value"]
    tol = out["ccf_by_design"]["tolerance"]
    for r in out["ccf_by_design"]["rows"]:
        key = (r["design"], r["treatment"], r["estimator"])
        if "truth" not in r or r["truth"]["value"] != truth:
            bad.append(f"{key}: the truth is not the generator's known CCF")
            continue
        if not math.isclose(r["bias"], r["estimate"]["value"] - r["truth"]["value"], abs_tol=1e-6):
            bad.append(f"{key}: bias is not estimate minus truth")
        if r["within_tolerance"] != (abs(r["bias"]) <= tol + 1e-9):
            bad.append(f"{key}: within_tolerance disagrees with the bias")
    return bad


def synthetic(doc: Any) -> list[str]:
    """The document says it is synthetic (provenance truth status, and a notice in the generator block or the models record)."""
    bad = []
    if doc["provenance"]["truth_status"] != "synthetic-known-truth":
        bad.append("the truth status is not synthetic-known-truth")
    text = repr(doc).lower()
    if "synthetic" not in text:
        bad.append("the word synthetic does not appear")
    gen = doc["outputs"]["generator"] if "outputs" in doc else doc["fit"]["generator"]
    if "synthetic" not in gen["notice"]["en"].lower() or "sint" not in gen["notice"]["es"].lower():
        bad.append("the generator notice does not say synthetic in both languages")
    return bad


def independent(plan: dict[str, Any]) -> list[str]:
    dev, test = list(plan["development_seeds"]), list(plan["test_seeds"])
    bad = []
    if set(dev) & set(test):
        bad.append("a seed is shared by the development and the test replications")
    if len(set(dev)) != len(dev) or len(set(test)) != len(test):
        bad.append("a seed repeats inside a set")
    return bad


def unclipped(raw: np.ndarray, treated: np.ndarray) -> list[str]:
    """An untreated CCF set keeps its values outside [0, 1]."""
    raw = raw[np.isfinite(raw)]
    if np.array_equal(np.sort(raw), np.sort(treated)):
        return []
    return ["the untreated CCFs are not the observed ones (clipped or dropped)"]


def undefined_is_nan(ccf: np.ndarray, undrawn: np.ndarray) -> list[str]:
    """Where the undrawn amount is not positive the CCF is NaN, never 0 or 1."""
    bad = np.flatnonzero((undrawn <= 0) & ~np.isnan(ccf))
    return [] if bad.size == 0 else [f"{bad.size} lines with no undrawn amount carry a CCF"]
