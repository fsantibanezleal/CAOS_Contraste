"""Phase 1 of the experiments: simulate every desk-year the manuscript uses and cache its statistic row.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/scale-and-level-complement-to-the-pla-test/experiments/simulate.py \
        [--cache D:/_Temp/ms-scale-and-level-complement-to-the-2026-11-04/cache] [--workers 24]

The jobs (each 1,000 desk-years, replications 0..999 of the C13 generator, deterministic from the seed):

* ``null``: the variant ``none`` under the ten case seeds 5013 to 5022 (seeds that meet none of the committed ones): the
  calibration null of 10,000 desk-years;
* ``committed``: the six variants under the committed case seed 13;
* ``ladder``: the stale-volatility variant at the lags 2, 5, 10, 40 and 80 days under case seed 13 (20 days is committed);
* ``repeat``: the six variants under the case seeds 23, 33, 43, 53 and 63 (five independent bakes, seed ranges that meet no other
  job's), at the committed lag of 20 days;
* ``xform``: the variant ``none`` under case seed 13 with the RTPL multiplied by 0.8, 0.9, 1.1 or 1.25 (a constant mis-scale) or
  shifted by 0.1 or 0.2 of the standard deviation of the HPL (a constant level error): the defects the Mincer-Zarnowitz component
  is meant to see;
* ``altnull``: the variant ``none`` under case seed 23 with one generator parameter changed (volatility persistence, volatility
  dispersion, pricing-noise share), the held-out check of the size.

Output: one ``.npy`` per job under the cache folder, rows in ``stats_core.COLUMNS`` order.
"""
from __future__ import annotations

import argparse
import contextlib
import dataclasses
import multiprocessing as mp
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import stats_core as sc  # noqa: E402

DEFAULT_CACHE = pathlib.Path("D:/_Temp/ms-scale-and-level-complement-to-the-2026-11-04/cache")
NULL_CASE_SEEDS = tuple(range(5013, 5023))
COMMITTED_SEED = 13
LADDER_LAGS = (2, 5, 10, 40, 80)
REPEAT_SEEDS = (23, 33, 43, 53, 63)
ALT_SEED = 23
#: name -> the generator parameter replaced (VOL_PHI, VOL_SD or RESIDUAL_SHARE) and its value
ALT_NULLS = {
    "phi090": ("VOL_PHI", 0.90), "phi0995": ("VOL_PHI", 0.995),
    "sd020": ("VOL_SD", 0.20), "sd050": ("VOL_SD", 0.50),
    "res005": ("RESIDUAL_SHARE", 0.05), "res030": ("RESIDUAL_SHARE", 0.30),
}


@contextlib.contextmanager
def patched(name: str | None, value: float | None):
    """Replace one generator parameter for the duration of a job (the derived constants follow)."""
    g = sc.generator
    if name is None:
        yield
        return
    old = {k: getattr(g, k) for k in ("VOL_PHI", "VOL_SD", "RESIDUAL_SHARE", "_MU", "_ETA")}
    setattr(g, name, value)
    g._MU = -g.VOL_SD ** 2
    g._ETA = g.VOL_SD * np.sqrt(1.0 - g.VOL_PHI ** 2)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(g, k, v)


#: name -> (kind, amount): the RTPL times ``amount`` or plus ``amount`` standard deviations of the HPL
XFORMS = {"scale080": ("scale", 0.8), "scale090": ("scale", 0.9), "scale110": ("scale", 1.1), "scale125": ("scale", 1.25),
          "shift010": ("shift", 0.1), "shift020": ("shift", 0.2)}


def jobs() -> list[tuple]:
    """(file stem, variant, case seed, lag, patched name, patched value, transform)."""
    out: list[tuple] = []
    for cs in NULL_CASE_SEEDS:
        out.append((f"null_{cs}", "none", cs, None, None, None, None))
    for did in sc.params.IDS:
        out.append((f"committed_{did}", did, COMMITTED_SEED, None, None, None, None))
    for lag in LADDER_LAGS:
        out.append((f"ladder_{lag}", "stale-volatility", COMMITTED_SEED, float(lag), None, None, None))
    for cs in REPEAT_SEEDS:
        for did in sc.params.IDS:
            out.append((f"repeat_{cs}_{did}", did, cs, None, None, None, None))
    for name, (pn, pv) in ALT_NULLS.items():
        out.append((f"altnull_{name}", "none", ALT_SEED, None, pn, pv, None))
    for name, xf in XFORMS.items():
        out.append((f"xform_{name}", "none", COMMITTED_SEED, None, None, None, xf))
    return out


def transformed_block(did: str, cs: int, xf: tuple[str, float], n: int = sc.params.N_REPLICATIONS) -> np.ndarray:
    rows = []
    for i in range(n):
        rep = sc.generator.replicate(did, i, cs)
        kind, amount = xf
        rtpl = rep.rtpl * amount if kind == "scale" else rep.rtpl + amount * sc.generator.base_sd()
        rows.append(sc.row(dataclasses.replace(rep, rtpl=rtpl)))
    return np.vstack(rows)


def run(job: tuple, cache: pathlib.Path) -> tuple[str, float]:
    stem, did, cs, lag, pn, pv, xf = job
    path = cache / f"{stem}.npy"
    t0 = time.time()
    if not path.exists():
        with patched(pn, pv):
            arr = transformed_block(did, cs, xf) if xf else sc.block(did, cs, lag=lag)
        np.save(path, arr)
    return stem, time.time() - t0


def _run(args: tuple) -> tuple[str, float]:
    return run(*args)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=pathlib.Path, default=DEFAULT_CACHE)
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with mp.Pool(a.workers) as pool:
        for stem, dt in pool.imap_unordered(_run, [(j, a.cache) for j in jobs()]):
            print(f"{stem}: {dt:.1f} s", flush=True)
    print(f"{len(jobs())} jobs in {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
