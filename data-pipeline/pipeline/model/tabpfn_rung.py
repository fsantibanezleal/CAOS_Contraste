"""P5, the tabular foundation model challenger: TabPFN v2, small cases only (dossier 04 B.3).

Hollmann et al. (2025), Nature 637:319-326, DOI 10.1038/s41586-024-08328-6: in-context learning, no per-dataset
training. The package's default weights (TabPFN-3.5) carry a non-commercial licence, so this rung selects the v2
weights, licensed under the Prior Labs License v1.1 (Apache 2.0 plus attribution: "Built with PriorLabs-TabPFN"),
and every view of it shows that licence. The optional extra installs it (data-pipeline/requirements-tabpfn.txt);
it is not part of the default install. Categorical inputs enter as integer codes learned on the training slice
(an unseen category is -1) and are declared to the model as categorical.

The weights are downloaded once into the device models root: ``TABPFN_MODEL_CACHE_DIR``, or
``<CONTRASTE_MODELS>/tabpfn``; with neither set the rung refuses to run rather than write to a user cache. TabPFN reads
its cache directory into settings when the package is first imported, so the rung also sets that setting itself
(an import made earlier would otherwise have fixed it to the user cache) and refuses a fit whose weights did not come
from the models root.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

WEIGHTS_LICENCE = "code Apache-2.0; TabPFN v2 weights, Prior Labs License v1.1 (Apache 2.0 plus attribution: Built with PriorLabs-TabPFN)"
ATTRIBUTION = "Built with PriorLabs-TabPFN"


def _cache_dir() -> Path:
    if os.environ.get("TABPFN_MODEL_CACHE_DIR"):
        return Path(os.environ["TABPFN_MODEL_CACHE_DIR"])
    root = os.environ.get("CONTRASTE_MODELS")
    if not root:
        raise RuntimeError("TabPFN needs a model cache in the device models root: set CONTRASTE_MODELS (or "
                           "TABPFN_MODEL_CACHE_DIR); it never downloads weights into a user cache")
    path = Path(root) / "tabpfn"
    path.mkdir(parents=True, exist_ok=True)
    os.environ["TABPFN_MODEL_CACHE_DIR"] = str(path)
    return path


@dataclass
class TabPFNRung:
    model: object
    features: list[str]
    categorical: tuple[str, ...]
    codes: dict[str, dict[str, int]]
    n_estimators: int
    version: str = "v2"
    meta: dict = field(default_factory=dict)

    def matrix(self, X: pd.DataFrame) -> np.ndarray:
        cols = []
        for f in self.features:
            if f in self.categorical:
                cols.append(np.array([self.codes[f].get(str(v), -1) for v in X[f]], dtype=float))
            else:
                cols.append(X[f].to_numpy(dtype=float))
        return np.column_stack(cols)

    def predict_pd(self, X: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.model.predict_proba(self.matrix(X))[:, 1], dtype=float)

    def record(self) -> dict:
        return {"weights": "TabPFN v2", "licence": WEIGHTS_LICENCE, "attribution": ATTRIBUTION,
                "n_estimators": self.n_estimators, "categorical_codes": self.codes, **self.meta}


def fit_tabpfn(X: pd.DataFrame, y: np.ndarray, *, features, categorical, seed: int, n_estimators: int = 8) -> TabPFNRung:
    cache = _cache_dir()
    from tabpfn import TabPFNClassifier
    from tabpfn.constants import ModelVersion
    from tabpfn.settings import settings as tabpfn_settings

    tabpfn_settings.tabpfn.model_cache_dir = cache

    codes = {f: {c: k for k, c in enumerate(sorted({str(v) for v in X[f]}))} for f in categorical}
    rung = TabPFNRung(None, list(features), tuple(categorical), codes, n_estimators)
    cat_idx = [i for i, f in enumerate(features) if f in categorical]
    clf = TabPFNClassifier.create_default_for_version(
        ModelVersion.V2, n_estimators=n_estimators, random_state=seed, device="cpu",
        categorical_features_indices=cat_idx or None)
    clf.fit(rung.matrix(X), np.asarray(y, dtype=int))
    weights = sorted(cache.glob("*.ckpt"))
    if not weights:
        raise RuntimeError(f"TabPFN did not load its weights from the device models root {cache}")
    rung.model = clf
    rung.meta = {"cache": cache.name, "model_path": Path(str(clf.model_path)).name}
    return rung
