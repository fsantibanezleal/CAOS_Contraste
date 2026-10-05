"""P3, the explainable boosting machine (GA2M), dossier 04 B.2.

g(E[y]) = beta_0 + sum_j f_j(x_j) + sum_(i,j) f_ij(x_i, x_j), the shape functions learned by cyclic gradient boosting
(Lou et al. 2013; Nori et al. 2019, arXiv 1909.09223). Configuration: monotone constraints where a direction is
declared, five pairwise terms, at most 64 bins per main term and 16 per pair (fewer than the library default of
1024, so the exported shape functions stay small and each one reads as a points table), eight outer bags, fixed
seed. The export holds everything an additive score needs; ``score_logit`` evaluates it without the library and is
held to the library's own decision function, and the web's live scorer is held to the exported scores (CT-105).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

MAX_BINS = 64
MAX_INTERACTION_BINS = 16
INTERACTIONS = 5
OUTER_BAGS = 8


@dataclass
class EBM:
    model: Any
    features: list[str]
    categorical: tuple[str, ...]

    def logit(self, X: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.model.decision_function(X[self.features]), dtype=float)

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.logit(X)))


def fit_ebm(X: pd.DataFrame, y: np.ndarray, *, features: list[str], categorical: tuple[str, ...],
            monotone: dict[str, int], seed: int) -> EBM:
    from interpret.glassbox import ExplainableBoostingClassifier

    types = ["nominal" if f in categorical else "continuous" for f in features]
    constraints = [0 if f in categorical else int(monotone.get(f, 0)) for f in features]
    m = ExplainableBoostingClassifier(
        feature_names=list(features), feature_types=types, max_bins=MAX_BINS,
        max_interaction_bins=MAX_INTERACTION_BINS, interactions=INTERACTIONS, outer_bags=OUTER_BAGS,
        monotone_constraints=constraints, random_state=seed, n_jobs=1,
    )
    m.fit(X[list(features)], np.asarray(y, dtype=int))
    return EBM(m, list(features), categorical)


def export(ebm: EBM) -> dict[str, Any]:
    """The additive model as data: per feature its binning, per term its scores (index 0 missing, last unknown)."""
    m = ebm.model
    feats = []
    for i, f in enumerate(ebm.features):
        levels = []
        for level in m.bins_[i]:
            if isinstance(level, dict):
                levels.append({"kind": "nominal", "categories": {str(k): int(v) for k, v in level.items()}})
            else:
                levels.append({"kind": "continuous", "cuts": [float(c) for c in np.asarray(level)]})
        feats.append({"name": f, "levels": levels})
    terms = []
    for t, idx in enumerate(m.term_features_):
        scores = np.asarray(m.term_scores_[t], dtype=float)
        terms.append({"name": m.term_names_[t], "features": [int(i) for i in idx], "scores": scores.tolist(),
                      "shape": list(scores.shape)})
    return {"intercept": float(np.asarray(m.intercept_).ravel()[0]), "features": feats, "terms": terms,
            "config": {"max_bins": MAX_BINS, "max_interaction_bins": MAX_INTERACTION_BINS,
                       "interactions": INTERACTIONS, "outer_bags": OUTER_BAGS}}


def _bin(feature: dict, level: int, value: Any) -> int:
    lv = feature["levels"][min(level, len(feature["levels"]) - 1)]
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0
    if lv["kind"] == "nominal":
        key = str(value if not isinstance(value, float) or not value.is_integer() else int(value))
        return lv["categories"].get(key, len(lv["categories"]) + 1)
    cuts = lv["cuts"]
    return int(np.searchsorted(np.asarray(cuts), float(value), side="right")) + 1


def score_logit(exported: dict[str, Any], X: pd.DataFrame) -> np.ndarray:
    """The additive logit from the export alone: intercept plus each term's score at the record's bins."""
    feats = exported["features"]
    names = [f["name"] for f in feats]
    rows = X[names].to_dict(orient="records")
    out = np.full(len(rows), exported["intercept"], dtype=float)
    for term in exported["terms"]:
        scores = np.asarray(term["scores"], dtype=float)
        level = 0 if len(term["features"]) == 1 else 1
        for r, rec in enumerate(rows):
            idx = tuple(_bin(feats[i], level, rec[names[i]]) for i in term["features"])
            out[r] += scores[idx]
    return out
