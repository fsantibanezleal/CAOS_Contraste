"""Consistency check of experiment 4 against experiment 2 and the committed ladder (a regression test of the ES convention).

    python manuscripts/adaptive-conformal-recalibration-of-var/experiments/check_e4_baseline.py

The unwrapped baseline of experiment 4 is the model's own VaR and ES. Its mean FZ0, hit count and p-values must equal those of the
unwrapped runs of experiment 2 for every window, model and level the two share (the ten level-parametric models), and the mean FZ0
must equal ``fz0_mean`` of the committed C11 window document. A baseline that differs means the ES was altered on the way (the
defect of the first version: ``np.minimum(es, var)`` on positive losses replaced the ES by the VaR). Exit code 0 when every shared
row agrees to 1e-6, 1 otherwise. It reads only committed files.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import common  # noqa: E402

TOL = 1e-6


def main() -> int:
    e2 = common.load("e2_wrap_ladder.json")["rows"]
    e4 = {(r["window"], r["model"], r["alpha"]): r for r in common.load("e4_score_space.json")["rows"] if r["method"] == "unwrapped"}
    bad, checked = [], 0
    for r in e2:
        k = (r["window"], r["model"], r["alpha"])
        if k not in e4:
            continue
        checked += 1
        a, b = r["unwrapped"], e4[k]["scores"]
        d = abs(a["fz0_mean"] - b["fz0_mean"])
        if d > TOL or a["n_hits"] != b["n_hits"]:
            bad.append((k, a["fz0_mean"], b["fz0_mean"]))
    committed_bad = []
    for w in common.WINDOWS:
        for m in common.doc(w)["outputs"]["models"]:
            for bl in m["by_level"]:
                k = (w, m["model_id"], bl["alpha"])
                if k in e4 and e4[k]["has_es"] and bl.get("fz0_mean") is not None:
                    if abs(bl["fz0_mean"] - e4[k]["scores"]["fz0_mean"]) > 5e-5:
                        committed_bad.append((k, bl["fz0_mean"], e4[k]["scores"]["fz0_mean"]))
    print(f"e2 rows shared with e4: {checked}; differing from e2: {len(bad)}; differing from the committed documents: {len(committed_bad)}")
    for x in (bad + committed_bad)[:5]:
        print("  ", x)
    return 0 if checked and not bad and not committed_bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
