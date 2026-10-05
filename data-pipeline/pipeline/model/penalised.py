"""P2, penalised logistic regression and PLTR (dossier 04 B.4 and the PD ladder).

P2a: L1-penalised logistic regression on the scorecard's WoE inputs (every variable that passed the information
value screen), the penalty chosen by cross-validated log loss on the training folds.

P2b: penalised logistic tree regression, Dumitrescu, Hue, Hurlin and Tokpavi (2022), EJOR 297(3):1178-1192,
DOI 10.1016/j.ejor.2021.06.053: threshold rules extracted from short trees (one split per variable, two splits per
pair of variables) enter, beside the standardised variables, an L1 logistic regression. A categorical variable enters
as its WoE from the scorecard's binning (fitted on the training slice), so its categories are ordered by risk. The
trees are fitted on the training slice only. Rule stability is the Jaccard index between the rules selected on the full training slice and
on each of 20 bootstrap resamples of it.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

C_GRID = (0.003, 0.01, 0.03, 0.1, 0.3, 1.0)


def _cv_choose_c(Z: np.ndarray, y: np.ndarray, folds, *, seed: int) -> float:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import log_loss

    best, best_c = np.inf, C_GRID[-1]
    for c in C_GRID:
        losses = []
        for tr, va in folds:
            m = LogisticRegression(l1_ratio=1.0, solver="liblinear", C=c, max_iter=2000, random_state=seed)
            m.fit(Z[tr], y[tr])
            losses.append(log_loss(y[va], m.predict_proba(Z[va])[:, 1], labels=[0, 1]))
        if np.mean(losses) < best:
            best, best_c = float(np.mean(losses)), c
    return best_c


@dataclass
class PenalisedWoE:
    scorecard: object
    features: list[str]
    model: object
    c: float

    def _z(self, X: pd.DataFrame) -> np.ndarray:
        return np.column_stack([self.scorecard_binnings[f].transform(X[f].to_numpy(), metric="woe")
                                for f in self.features])

    scorecard_binnings: dict = field(default_factory=dict)

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(self._z(X))[:, 1]

    def record(self) -> dict:
        coef = self.model.coef_[0]
        return {"penalty": "l1", "C": self.c, "intercept": float(self.model.intercept_[0]),
                "coefficients": {f: float(b) for f, b in zip(self.features, coef)},
                "selected": [f for f, b in zip(self.features, coef) if b != 0.0],
                "signs_agree_with_woe": bool(all(b <= 0 for b in coef))}


def fit_penalised_woe(scorecard, all_binnings: dict, X: pd.DataFrame, y: np.ndarray, folds, *, seed: int,
                      screened: list[str]) -> PenalisedWoE:
    from sklearn.linear_model import LogisticRegression

    Z = np.column_stack([all_binnings[f].transform(X[f].to_numpy(), metric="woe") for f in screened])
    c = _cv_choose_c(Z, y, folds, seed=seed)
    m = LogisticRegression(l1_ratio=1.0, solver="liblinear", C=c, max_iter=2000, random_state=seed).fit(Z, y)
    return PenalisedWoE(scorecard=scorecard, features=list(screened), model=m, c=c,
                        scorecard_binnings={f: all_binnings[f] for f in screened})


# --- PLTR --------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """A conjunction of at most two threshold conditions: (feature, '<=' or '>', threshold)."""

    conditions: tuple[tuple[str, str, float], ...]

    def label(self) -> str:
        return " and ".join(f"{f} {op} {t:g}" for f, op, t in self.conditions)

    def apply(self, X: pd.DataFrame) -> np.ndarray:
        out = np.ones(len(X), dtype=bool)
        for f, op, t in self.conditions:
            v = X[f].to_numpy(dtype=float)
            out &= (v <= t) if op == "<=" else (v > t)
        return out.astype(float)


def _tree_rules(X: pd.DataFrame, y: np.ndarray, cols: tuple[str, ...], depth: int, seed: int) -> list[Rule]:
    from sklearn.tree import DecisionTreeClassifier

    t = DecisionTreeClassifier(max_depth=depth, min_samples_leaf=0.05, random_state=seed)
    t.fit(X[list(cols)].to_numpy(dtype=float), y)
    tree = t.tree_
    rules: list[Rule] = []

    def walk(node: int, path: tuple[tuple[str, str, float], ...]) -> None:
        if tree.children_left[node] == -1:  # a leaf
            if path:
                rules.append(Rule(path))
            return
        f = cols[tree.feature[node]]
        thr = float(tree.threshold[node])
        walk(tree.children_left[node], (*path, (f, "<=", thr)))
        walk(tree.children_right[node], (*path, (f, ">", thr)))

    walk(0, ())
    # the leaves of a tree partition the space: one leaf indicator is redundant with the intercept
    return rules[:-1] if len(rules) > 1 else rules


def extract_rules(X: pd.DataFrame, y: np.ndarray, features: list[str], *, seed: int) -> list[Rule]:
    rules: list[Rule] = []
    for f in features:
        rules.extend(_tree_rules(X, y, (f,), 1, seed))
    for f, g in itertools.combinations(features, 2):
        rules.extend(_tree_rules(X, y, (f, g), 2, seed))
    unique: dict[str, Rule] = {}
    for r in rules:
        unique.setdefault(r.label(), r)
    return list(unique.values())


def woe_frame(X: pd.DataFrame, features: list[str], woe: dict) -> pd.DataFrame:
    """The variables PLTR reads: numeric ones as they are, categorical ones as their WoE."""
    out = pd.DataFrame(index=X.index)
    for f in features:
        out[f] = woe[f].transform(X[f].to_numpy(), metric="woe") if f in woe else X[f].to_numpy(dtype=float)
    return out


@dataclass
class PLTR:
    features: list[str]
    rules: list[Rule]
    mean: np.ndarray
    scale: np.ndarray
    model: object
    c: float
    stability: dict
    woe: dict = field(default_factory=dict)

    def design(self, X: pd.DataFrame) -> np.ndarray:
        V = woe_frame(X, self.features, self.woe)
        raw = (V[self.features].to_numpy(dtype=float) - self.mean) / self.scale
        return np.column_stack([raw, *(r.apply(V) for r in self.rules)])

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(self.design(X))[:, 1]

    def selected(self) -> list[str]:
        coef = self.model.coef_[0][len(self.features):]
        return [r.label() for r, b in zip(self.rules, coef) if b != 0.0]

    def record(self) -> dict:
        coef = self.model.coef_[0]
        nf = len(self.features)
        return {"penalty": "l1", "C": self.c, "intercept": float(self.model.intercept_[0]),
                "n_candidate_rules": len(self.rules), "selected_rules": [
                    {"rule": r.label(), "coefficient": float(b)} for r, b in zip(self.rules, coef[nf:]) if b != 0.0],
                "variables": {f: float(b) for f, b in zip(self.features, coef[:nf])},
                "woe_encoded": sorted(self.woe),
                "stability": self.stability}


def fit_pltr(X: pd.DataFrame, y: np.ndarray, features: list[str], folds, *, seed: int, n_boot: int = 20,
             woe: dict | None = None) -> PLTR:
    from sklearn.linear_model import LogisticRegression

    woe = woe or {}
    V = woe_frame(X, features, woe)
    rules = extract_rules(V, y, features, seed=seed)
    mean = V[features].to_numpy(dtype=float).mean(axis=0)
    scale = V[features].to_numpy(dtype=float).std(axis=0)
    scale[scale == 0] = 1.0
    base = PLTR(features, rules, mean, scale, None, 0.0, {}, woe)
    Z = base.design(X)
    c = _cv_choose_c(Z, y, folds, seed=seed)
    m = LogisticRegression(l1_ratio=1.0, solver="liblinear", C=c, max_iter=5000, random_state=seed).fit(Z, y)
    base.model, base.c = m, c
    chosen = set(base.selected())
    rng = np.random.default_rng(seed)
    jaccard = []
    for _ in range(n_boot):
        b = rng.integers(0, len(y), len(y))
        mb = LogisticRegression(l1_ratio=1.0, solver="liblinear", C=c, max_iter=5000, random_state=seed).fit(Z[b], y[b])
        sel = {r.label() for r, w in zip(rules, mb.coef_[0][len(features):]) if w != 0.0}
        union = chosen | sel
        jaccard.append(len(chosen & sel) / len(union) if union else 1.0)
    base.stability = {"bootstraps": n_boot, "jaccard_mean": float(np.mean(jaccard)),
                      "jaccard_min": float(np.min(jaccard)), "jaccard": [float(j) for j in jaccard]}
    return base
