"""P1, the WoE logistic scorecard: optimal monotone binning, logistic regression on WoE, PDO points.

Dossier 04 A.1 to A.3. WoE follows Navas-Palencia (arXiv 2001.08025, section 2.1) and optbinning:
WoE_i = log((r_i^NE / r_T^NE) / (r_i^E / r_T^E)), so a higher WoE means a lower default rate, and every coefficient
of a sound scorecard on WoE inputs is negative. Points follow the PDO scaling verified in dossier 04 A.3 (ING
skorecard ``_scale_scorecard``): Factor = PDO / ln 2, Offset = Score_ref - Factor ln(odds_ref), and for k
characteristics Points_{j,b} = Offset / k - (beta_j WoE_{j,b} + beta_0 / k) Factor, so the total is
Offset - Factor eta = Offset + Factor ln(odds of good). The points are rounded to integers and the score is their
sum, as a scorecard is used; the PD comes from the unrounded model.

Variable selection, on the training slice only: an information-value screen (IV of at least 0.02, the convention
attributed to Siddiqi 2017; the threshold is UNVERIFIED against the book, dossier 04 A.1), then the sign check of
dossier 04 A.6: while a coefficient has the wrong sign (positive on WoE), the wrong-signed variable with the largest
p-value is dropped and the model refitted.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

IV_MIN = 0.02
MIN_BIN_SIZE = 0.05  # each bin at least 5% of the observations (Navas-Palencia, citing practitioner literature)
TREND = {+1: "ascending", -1: "descending", 0: "auto_asc_desc"}


@dataclass
class Scorecard:
    features: list[str]
    binnings: dict[str, Any]
    intercept: float
    coef: dict[str, float]
    pdo: float
    odds_ref: float
    score_ref: float
    iv: dict[str, float]
    dropped: dict[str, str] = field(default_factory=dict)
    table: list[dict[str, Any]] = field(default_factory=list)

    @property
    def factor(self) -> float:
        return self.pdo / math.log(2.0)

    @property
    def offset(self) -> float:
        return self.score_ref - self.factor * math.log(self.odds_ref)

    def woe(self, X: pd.DataFrame) -> np.ndarray:
        return np.column_stack([self.binnings[f].transform(X[f].to_numpy(), metric="woe") for f in self.features])

    def bin_index(self, X: pd.DataFrame) -> np.ndarray:
        """The row of each feature's points table that each record falls in."""
        cols = []
        for f in self.features:
            idx = self.binnings[f].transform(X[f].to_numpy(), metric="indices")
            cols.append(np.asarray(idx, dtype=int))
        return np.column_stack(cols)

    def eta(self, X: pd.DataFrame) -> np.ndarray:
        beta = np.array([self.coef[f] for f in self.features])
        return self.intercept + self.woe(X) @ beta

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.eta(X)))

    def points(self, X: pd.DataFrame) -> np.ndarray:
        """Integer points per record and characteristic, computed from each record's WoE by the PDO formula."""
        k = len(self.features)
        beta = np.array([self.coef[f] for f in self.features])
        raw = self.offset / k - (self.woe(X) * beta + self.intercept / k) * self.factor
        return np.rint(raw).astype(int)

    def table_points(self, X: pd.DataFrame) -> np.ndarray:
        """The same points read from the points table by each record's bin; an index -1 (an unseen category) reads
        the table's last row, the zero-WoE "Missing" bin, which is the WoE optbinning gives it."""
        idx = self.bin_index(X)
        out = np.zeros_like(idx)
        for j, f in enumerate(self.features):
            lookup = np.array([row["points"] for row in self.table if row["feature"] == f], dtype=int)
            out[:, j] = lookup[idx[:, j]]
        return out

    def score(self, X: pd.DataFrame) -> np.ndarray:
        return self.points(X).sum(axis=1)


def _fit_binning(name: str, x: np.ndarray, y: np.ndarray, categorical: bool, direction: int):
    from optbinning import OptimalBinning

    ob = OptimalBinning(
        name=name, dtype="categorical" if categorical else "numerical", solver="cp",
        monotonic_trend=TREND[direction], min_bin_size=MIN_BIN_SIZE, max_n_prebins=20,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ob.fit(x, y)
    return ob


def _logit(W: np.ndarray, y: np.ndarray):
    import statsmodels.api as sm

    return sm.Logit(y, sm.add_constant(W, has_constant="add")).fit(disp=0, method="newton", maxiter=100)


def fit_scorecard(
    X: pd.DataFrame,
    y: np.ndarray,
    *,
    features: list[str] | tuple[str, ...],
    categorical: tuple[str, ...],
    monotone: dict[str, int],
    pdo: float = 20.0,
    odds_ref: float = 50.0,
    score_ref: float = 600.0,
) -> Scorecard:
    """Fit the scorecard on the training slice (X, y). Nothing here sees the calibration slice or the holdout."""
    y = np.asarray(y, dtype=int)
    binnings: dict[str, Any] = {}
    iv: dict[str, float] = {}
    dropped: dict[str, str] = {}
    for f in features:
        ob = _fit_binning(f, X[f].to_numpy(), y, f in categorical, monotone.get(f, 0))
        binnings[f] = ob
        iv[f] = float(ob.binning_table.build().loc["Totals", "IV"])
        if iv[f] < IV_MIN:
            dropped[f] = f"information value {iv[f]:.4f} below {IV_MIN}"
    kept = [f for f in features if f not in dropped]
    while True:
        W = np.column_stack([binnings[f].transform(X[f].to_numpy(), metric="woe") for f in kept])
        res = _logit(W, y)
        beta = np.asarray(res.params[1:])
        pvals = np.asarray(res.pvalues[1:])
        wrong = [k for k, b in enumerate(beta) if b > 0]
        if not wrong:
            break
        worst = max(wrong, key=lambda k: pvals[k])
        dropped[kept[worst]] = f"wrong sign on WoE (coefficient {beta[worst]:+.4f}, p = {pvals[worst]:.3g})"
        kept.pop(worst)
    sc = Scorecard(features=kept, binnings={f: binnings[f] for f in kept}, intercept=float(res.params[0]),
                   coef={f: float(b) for f, b in zip(kept, beta)}, pdo=pdo, odds_ref=odds_ref, score_ref=score_ref,
                   iv=iv, dropped=dropped)
    sc.table = _points_table(sc)
    return sc


def _points_table(sc: Scorecard) -> list[dict[str, Any]]:
    k = len(sc.features)
    rows = []
    for f in sc.features:
        table = sc.binnings[f].binning_table.build()
        body = table.drop(index="Totals")
        for i, (_, r) in enumerate(body.iterrows()):
            woe = float(r["WoE"])
            raw = sc.offset / k - (sc.coef[f] * woe + sc.intercept / k) * sc.factor
            rows.append({
                "feature": f, "row": i, "bin": _bin_label(r["Bin"]), "count": int(r["Count"]),
                "events": int(r["Event"]), "event_rate": float(r["Event rate"]) if r["Count"] else None,
                "woe": woe, "iv": float(r["IV"]), "points_raw": raw, "points": int(round(raw)),
            })
    return rows


def _bin_label(b: Any) -> str:
    """The bin as text: an interval for a numerical variable, the set of categories for a categorical one (the
    binning table holds those as numpy or pandas arrays)."""
    if not isinstance(b, str) and hasattr(b, "__iter__"):
        return "{" + ", ".join(str(v) for v in b) + "}"
    return str(b)


def bins(sc: Scorecard) -> dict[str, Any]:
    """Each characteristic's bins as numbers, so a scorer outside Python reads the same row without parsing labels:
    a numerical value x falls in row bisect_right(splits, x) (bins are [split_(i-1), split_i)); a categorical value in
    the row whose categories hold it; anything else in the table's last row, the zero-WoE "Missing" bin."""
    out: dict[str, Any] = {}
    for f in sc.features:
        ob = sc.binnings[f]
        if ob.dtype == "categorical":
            out[f] = {"kind": "categorical", "categories": [[str(v) for v in b] for b in ob.splits]}
        else:
            out[f] = {"kind": "numerical", "splits": [float(v) for v in np.asarray(ob.splits, dtype=float)]}
    return out


def record(sc: Scorecard) -> dict[str, Any]:
    """The model record contract 2 writes: parameters with units, and the points table."""
    return {
        "intercept": sc.intercept, "coefficients": sc.coef, "features": sc.features, "dropped": sc.dropped,
        "iv": sc.iv, "scaling": {"pdo": sc.pdo, "odds_ref": sc.odds_ref, "score_ref": sc.score_ref,
                                 "factor": sc.factor, "offset": sc.offset},
        "points_table": sc.table,
        "bins": bins(sc),
    }
