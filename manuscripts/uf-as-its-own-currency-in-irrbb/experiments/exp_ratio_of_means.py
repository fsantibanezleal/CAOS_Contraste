"""Experiment 5: the income ratio as a ratio of means, with a bootstrap interval, and as a median of the per-book ratios.

The main comparison (``exp_main.py``) reports the Annex 1 over single-currency delta NII as the mean over the books of the per-book ratio.
That ratio is heavy-tailed because the single-currency delta NII of some books is close to zero, so the Student interval of its mean is not a
reliable statement of uncertainty. This script runs the same 30 books of each variant (seeds 1 to 30, the same book generator and curves) and
reports three summaries of the same quantity: the ratio of the mean Annex 1 delta NII to the mean single-currency delta NII with a 95 percent
percentile bootstrap interval (10,000 resamples of the 30 books with replacement, numpy seed 20261108), the median of the per-book ratios with
its interquartile range, and the mean of the per-book ratios of ``exp_main.py`` for reference. No hypothesis is attached to it.

Run from the repository root with the raw files in ``CONTRASTE_DATA``::

    python manuscripts/uf-as-its-own-currency-in-irrbb/experiments/exp_ratio_of_means.py

It writes ``experiments/ratio_of_means.json`` (the run time is measured).
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

import uf_core as u

SEEDS = tuple(range(1, 31))
RESAMPLES = 10_000
BOOT_SEED = 20261108


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    args = ap.parse_args()
    t0 = time.perf_counter()
    raw = u.load_raw(args.data)
    ctx = u.context(raw)
    rng = np.random.default_rng(BOOT_SEED)
    out: dict = {"valuation_date": ctx.date, "seeds": list(SEEDS), "resamples": RESAMPLES, "bootstrap_seed": BOOT_SEED, "variants": {}}
    for vid in u.bk.SPECS:
        annex, single = [], []
        for seed in SEEDS:
            book = u.book_of(vid, seed, ctx)
            annex.append(u.measures(book, ctx, u.ANNEX1)["delta_nii"])
            single.append(u.measures(book, ctx, u.SINGLE)["delta_nii"])
        a, s = np.array(annex), np.array(single)
        idx = rng.integers(0, a.size, size=(RESAMPLES, a.size))
        boot = a[idx].mean(axis=1) / s[idx].mean(axis=1)
        per_book = a / s
        q1, med, q3 = np.percentile(per_book, [25, 50, 75])
        out["variants"][vid] = {
            "ratio_of_means": float(a.mean() / s.mean()),
            "ratio_of_means_ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
            "per_book_median": float(med), "per_book_q1": float(q1), "per_book_q3": float(q3),
            "per_book_mean": float(per_book.mean()), "per_book_min": float(per_book.min()), "per_book_max": float(per_book.max()),
            "mean_annex_nii": float(a.mean()), "mean_single_nii": float(s.mean())}
    out["seconds"] = time.perf_counter() - t0
    (u.HERE / "ratio_of_means.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote ratio_of_means.json in {out['seconds']:.1f} s")


if __name__ == "__main__":
    main()
