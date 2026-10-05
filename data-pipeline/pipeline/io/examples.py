"""The examples of the bring-your-own-model guide: two synthetic scored samples with a known truth (data/examples/).

- ``scored_sample_development.csv``: 2,000 obligors observed on 2024-12-31, PD ~ Beta(1.2, 20) and the default a
  Bernoulli draw at that PD, so the PDs are calibrated by construction;
- ``scored_sample_current.csv``: 2,000 obligors observed on 2025-12-31 from a riskier population, PD ~ Beta(1.2, 16),
  whose defaults arrive at 1.5 times the PD (capped at 1): the population shifted, the ranking is intact (the
  defaults still rise with the PD) and the model under-estimates the level by a third.

A sound battery finds the development sample calibrated; it finds the current sample shifted against the
development (a PSI near 0.06, inside the conventional 0.10 band and still detected by the statistical benchmark),
discriminating as well as at development, and under-estimated (the level tests). The truth status of both is
synthetic-known-truth. The files are a pure function of the seed: regenerating them writes identical bytes
(tests/test_own_sample.py).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SEED = 2026
N = 2000
PD_MIN, PD_MAX = 1e-6, 1.0 - 1e-6  # contract 1 holds a PD inside the open interval (0, 1)
SAMPLES: dict[str, dict] = {
    "development": {"date": "2024-12-31", "beta": (1.2, 20.0), "default_multiplier": 1.0, "offset": 0},
    "current": {"date": "2025-12-31", "beta": (1.2, 16.0), "default_multiplier": 1.5, "offset": 1},
}
HEADER = "id,observation_date,target,pd,segment\n"


def sample_csv(name: str, *, seed: int = SEED) -> bytes:
    spec = SAMPLES[name]
    rng = np.random.default_rng(seed + spec["offset"])
    a, b = spec["beta"]
    pd = np.clip(np.round(rng.beta(a, b, N), 6), PD_MIN, PD_MAX)
    target = (rng.uniform(size=N) < np.minimum(1.0, spec["default_multiplier"] * pd)).astype(int)
    prefix = "D" if name == "development" else "C"
    lines = [HEADER]
    for k in range(N):
        lines.append(f"{prefix}{k + 1:05d},{spec['date']},{target[k]},{pd[k]:.6f},retail\n")
    return "".join(lines).encode("utf-8")


def write_examples(out_dir: str | Path, *, seed: int = SEED) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name in SAMPLES:
        path = out / f"scored_sample_{name}.csv"
        path.write_bytes(sample_csv(name, seed=seed))
        written.append(path)
    return written
