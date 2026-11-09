"""The compact validation pipeline the leakage experiments share.

The pipeline is the scorecard path of the product (CAOS_Contraste ``pipeline/model/scorecard.py`` and ``pipeline/stages/split.py``)
reduced to the steps whose reading of outside data the experiments vary: median imputation, standardisation, quantile binning,
weight of evidence (WoE), an association screen, a logistic regression, a selection among configurations and an isotonic
calibration map. Every step takes the row set it reads, so that a leak is exactly "a step reads rows outside the training
slice" and nothing else changes. The AUC and its variance are the engine's (``riskvalidation.validation.discrimination``).

Data model: the whole data set ``(X, y)`` with index sets ``train``, ``cal`` and ``hold`` into it, as the product's split stage
declares them. A perturbation of the data at the outside indices is therefore seen by every step that reads those indices.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import rankdata
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from riskvalidation.validation.discrimination import auc_with_variance

BETA = np.array([0.9, -0.7, 0.6, 0.5, -0.4])
SCREEN_K = 10
CONFIGS = tuple((nb, c) for nb in (3, 5, 10, 20) for c in (0.05, 5.0))
STEPS = ("impute", "scale", "bin", "woe", "screen", "fit")

#: which steps read the outside rows (the holdout) under each leak; ``none`` is the proposed protocol
LEAKS: dict[str, frozenset[str]] = {
    "none": frozenset(),
    "impute_full": frozenset({"impute"}),
    "scale_full": frozenset({"scale"}),
    "bin_full": frozenset({"bin"}),
    "woe_full": frozenset({"woe"}),
    "screen_full": frozenset({"screen"}),
    "fit_full": frozenset(STEPS),
    "select_test": frozenset(),
    "cal_test": frozenset(),
    "cal_overlap": frozenset(),
}
#: the leaks that change the selection or the calibration slice rather than the rows a step reads
SPECIAL = ("select_test", "cal_test", "cal_overlap")


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def planted(n: int, p: int, rng: np.random.Generator, intercept: float = -1.3, missing: float = 0.05) -> tuple[np.ndarray, np.ndarray]:
    """``p`` independent standard normal inputs, five of them informative with coefficients ``BETA``, a binary outcome from the
    logistic model (the true probability is known), and MCAR missing values in ten columns."""
    X = rng.normal(size=(n, p))
    y = (rng.random(n) < sigmoid(intercept + X[:, :5] @ BETA)).astype(int)
    if missing > 0:
        X[:, :10][rng.random((n, 10)) < missing] = np.nan
    return X, y


def fast_auc(score: np.ndarray, y: np.ndarray) -> float:
    r = rankdata(score)
    n1 = int(y.sum())
    n0 = len(y) - n1
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error over equal-count bins of the predicted PD."""
    order = np.argsort(p)
    parts = np.array_split(order, bins)
    return float(sum(len(ix) * abs(p[ix].mean() - y[ix].mean()) for ix in parts) / len(p))


@dataclass
class Fit:
    kind: str
    med: np.ndarray
    mu: np.ndarray | None
    sd: np.ndarray | None
    edges: list | None
    woe: list | None
    keep: np.ndarray
    clf: LogisticRegression
    nb: int
    c: float
    iso: IsotonicRegression | None = None

    def design(self, X: np.ndarray) -> np.ndarray:
        Xf = np.where(np.isnan(X), self.med, X)
        if self.kind == "linear":
            return ((Xf - self.mu) / self.sd)[:, self.keep]
        return np.column_stack([self.woe[j][np.searchsorted(self.edges[j], Xf[:, j], side="right")] for j in self.keep])

    def raw(self, X: np.ndarray) -> np.ndarray:
        return self.clf.predict_proba(self.design(X))[:, 1]

    def pd(self, X: np.ndarray) -> np.ndarray:
        p = self.raw(X)
        return np.clip(self.iso.predict(p), 1e-6, 1 - 1e-6) if self.iso is not None else p

    def transforms(self) -> dict:
        """Everything fitted before the calibration map: what the transform gate compares."""
        return {"med": self.med, "mu": self.mu, "sd": self.sd, "edges": self.edges, "woe": self.woe, "keep": self.keep,
                "coef": self.clf.coef_, "intercept": self.clf.intercept_}

    def calibration(self) -> dict:
        return {"x": self.iso.X_thresholds_, "y": self.iso.y_thresholds_} if self.iso is not None else {}


def _woe_tables(idx: np.ndarray, y: np.ndarray, nb_edges: list, smooth: float = 0.5) -> tuple[list, np.ndarray]:
    """WoE per bin of every column (higher WoE, higher default rate) and the information value of each column."""
    e_tot, n_tot = y.sum(), (1 - y).sum()
    tables, iv = [], np.zeros(idx.shape[1])
    for j in range(idx.shape[1]):
        k = len(nb_edges[j]) + 1
        e = np.bincount(idx[:, j], weights=y, minlength=k) + smooth
        n = np.bincount(idx[:, j], weights=1 - y, minlength=k) + smooth
        de, dn = e / (e_tot + smooth * k), n / (n_tot + smooth * k)
        w = np.log(de / dn)
        tables.append(w)
        iv[j] = float(np.sum((de - dn) * w))
    return tables, iv


def _edges(Xf: np.ndarray, nb: int) -> list:
    qs = np.linspace(0, 1, nb + 1)[1:-1]
    return [np.unique(np.quantile(Xf[:, j], qs)) for j in range(Xf.shape[1])]


def _bin(Xf: np.ndarray, edges: list) -> np.ndarray:
    return np.column_stack([np.searchsorted(edges[j], Xf[:, j], side="right") for j in range(Xf.shape[1])])


def fit_model(X: np.ndarray, y: np.ndarray, rows: dict[str, np.ndarray], *, kind: str, nb: int = 10, c: float = 1.0,
              k: int = SCREEN_K) -> Fit:
    """One model fitted with each step reading ``rows[step]`` (the training rows, or the training rows and the holdout)."""
    med = np.nanmedian(X[rows["impute"]], axis=0)
    Xf = np.where(np.isnan(X), med, X)
    p = X.shape[1]
    mu = sd = edges = woe = None
    if kind == "linear":
        mu, sd = Xf[rows["scale"]].mean(0), Xf[rows["scale"]].std(0) + 1e-12
        rs = rows["screen"]
        z = (Xf[rs] - mu) / sd
        score = np.abs([np.corrcoef(z[:, j], y[rs])[0, 1] for j in range(p)])
        keep = np.sort(np.argsort(-score)[:k])
        D = ((Xf[rows["fit"]] - mu) / sd)[:, keep]
    else:
        edges = _edges(Xf[rows["bin"]], nb)
        idx_all = _bin(Xf, edges)
        woe, _ = _woe_tables(idx_all[rows["woe"]], y[rows["woe"]], edges)
        _, iv = _woe_tables(idx_all[rows["screen"]], y[rows["screen"]], edges)
        keep = np.sort(np.argsort(-iv)[:k])
        D = np.column_stack([woe[j][idx_all[rows["fit"], j]] for j in keep])
    clf = LogisticRegression(C=c, max_iter=500).fit(D, y[rows["fit"]])
    return Fit(kind, med, mu, sd, edges, woe, keep, clf, nb, c)


def auc_on(fit: "Fit", X: np.ndarray, y: np.ndarray, rows: np.ndarray) -> float:
    return fast_auc(fit.raw(X[rows]), y[rows])


def fit_pipeline(X: np.ndarray, y: np.ndarray, train: np.ndarray, cal: np.ndarray, hold: np.ndarray, *, kind: str,
                 leak: str = "none") -> Fit:
    """The proposed protocol (``leak="none"``) or one leaked variant of it. Under ``cal_overlap`` the caller declares a calibration
    slice that shares rows with the holdout (``overlapping_calibration``)."""
    reads = LEAKS[leak]
    full = np.concatenate([train, hold])
    rows = {s: (full if s in reads else train) for s in STEPS}
    # the configuration is chosen by three-fold cross-validation inside the training slice under the protocol (the product's folds
    # sit inside the training slice) and on the holdout under ``select_test``
    grid = CONFIGS if kind == "woe" else tuple((10, c) for c in (0.05, 5.0))
    if leak == "select_test":
        scores = [auc_on(fit_model(X, y, rows, kind=kind, nb=nb, c=c), X, y, hold) for nb, c in grid]
    else:
        folds = np.array_split(train[np.random.default_rng(12345).permutation(len(train))], 3)
        scores = []
        for nb, c in grid:
            a = []
            for k in range(3):
                ftr = np.concatenate([folds[j] for j in range(3) if j != k])
                rows_f = {s: (np.concatenate([ftr, hold]) if s in reads else ftr) for s in STEPS}
                a.append(auc_on(fit_model(X, y, rows_f, kind=kind, nb=nb, c=c), X, y, folds[k]))
            scores.append(float(np.mean(a)))
    nb, c = grid[int(np.argmax(scores))]
    best = fit_model(X, y, rows, kind=kind, nb=nb, c=c)
    cal_rows = hold if leak == "cal_test" else cal
    best.iso = IsotonicRegression(y_min=1e-6, y_max=1 - 1e-6, increasing=True, out_of_bounds="clip").fit(
        best.raw(X[cal_rows]), y[cal_rows])
    return best


def overlapping_calibration(cal: np.ndarray, hold: np.ndarray, share: float = 0.2) -> np.ndarray:
    """A faulty split: the calibration slice also holds ``share`` of the holdout rows."""
    return np.concatenate([cal, hold[: max(1, int(share * len(hold)))]])


def stratified_slices(y: np.ndarray, rng: np.random.Generator, holdout: float = 0.30, calibration: float = 0.20) -> tuple:
    """The product's split (``pipeline.stages.split.stratified_split`` without the folds): a locked stratified holdout, then a
    calibration slice of the remaining development rows, both stratified on the outcome."""
    idx = np.arange(len(y))
    parts = {}
    for label in (0, 1):
        ix = rng.permutation(idx[y == label])
        nh = int(round(holdout * len(ix)))
        dev = ix[nh:]
        nc = int(round(calibration * len(dev)))
        parts.setdefault("hold", []).append(ix[:nh])
        parts.setdefault("cal", []).append(dev[:nc])
        parts.setdefault("train", []).append(dev[nc:])
    return tuple(np.sort(np.concatenate(parts[s])) for s in ("train", "cal", "hold"))


def score_sample(fit: Fit, X: np.ndarray, y: np.ndarray, *, with_variance: bool = False) -> dict:
    p = fit.pd(X)
    out = {"auc": fast_auc(p, y), "brier": brier(p, y), "ece": ece(p, y)}
    if with_variance:
        auc, s2, _, _ = auc_with_variance(p, y)
        out["auc"], out["s2"] = auc, s2
    return out


# ---- the three gates and the screens ----------------------------------------------------------------------------------

def _same(a, b) -> bool:
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(_same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(_same(u, v) for u, v in zip(a, b))
    if a is None or b is None:
        return a is None and b is None
    return bool(np.array_equal(np.asarray(a), np.asarray(b), equal_nan=True))


def perturbed(X: np.ndarray, y: np.ndarray, where: np.ndarray, rng: np.random.Generator, *, features: bool = True,
              labels: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """The data with the rows ``where`` replaced: inputs far from the training range (the product's test moves them to a
    normal with mean 5 and standard deviation 4), labels redrawn at random."""
    X2, y2 = X.copy(), y.copy()
    if features:
        X2[where] = rng.normal(5.0, 4.0, size=(len(where), X.shape[1]))
    if labels:
        y2[where] = rng.integers(0, 2, size=len(where))
    return X2, y2


def gates(X, y, train, cal, hold, *, kind: str, leak: str, seed: int = 0, draws: int = 1) -> dict:
    """The three gates of the protocol on the pipeline under ``leak``: True means the gate passed (no dependence found).

    G1 (transforms on the training slice only): the inputs outside the training slice are replaced and every transform fitted
    before the calibration map must be unchanged. G2 (calibration slice disjoint from the test slice): the index sets are
    disjoint and the calibration map is unchanged when the holdout labels are flipped. G3 (outside-information invariance): the
    holdout rows are perturbed in input and label and every fitted parameter, the calibration map included, is unchanged.
    The non-vacuity control changes training labels and requires the fit to change. ``draws`` perturbations are made for G3 and the
    gate fails when any of them changes a parameter."""
    rng = np.random.default_rng(seed)
    if leak == "cal_overlap":
        cal = overlapping_calibration(cal, hold)
    base = fit_pipeline(X, y, train, cal, hold, kind=kind, leak=leak)
    outside = np.setdiff1d(np.arange(len(y)), train)
    # G1: inputs outside the training slice moved, labels kept
    X1, y1 = perturbed(X, y, outside, rng, labels=False)
    f1 = fit_pipeline(X1, y1, train, cal, hold, kind=kind, leak=leak)
    g1 = _same(base.transforms(), f1.transforms())
    # G2: disjoint index sets and calibration map invariant to the holdout labels
    disjoint = not (set(cal) & set(hold) or set(cal) & set(train) or set(train) & set(hold))
    y2 = y.copy()
    y2[hold] = 1 - y2[hold]
    f2 = fit_pipeline(X, y2, train, cal, hold, kind=kind, leak=leak)
    g2 = disjoint and _same(base.calibration(), f2.calibration())
    # G3: holdout inputs and labels perturbed, everything fitted unchanged
    g3 = True
    for _ in range(draws):
        X3, y3 = perturbed(X, y, hold, rng)
        f3 = fit_pipeline(X3, y3, train, cal, hold, kind=kind, leak=leak)
        g3 = g3 and _same(base.transforms(), f3.transforms()) and _same(base.calibration(), f3.calibration())
    # non-vacuity: a training label changed must change the fit
    y4 = y.copy()
    k = train[:100]
    y4[k] = 1 - y4[k]
    f4 = fit_pipeline(X, y4, train, cal, hold, kind=kind, leak=leak)
    sensitive = not _same(base.transforms(), f4.transforms())
    return {"G1": bool(g1), "G2": bool(g2), "G3": bool(g3), "non_vacuous": bool(sensitive), "disjoint": bool(disjoint)}
