"""Real data, VaR back-tests (case C11): the e-process monitors on the committed exceedance days of every model and window.

Reads the six committed windows ``data/derived/C11/<window>.json`` (the exceedance days of each model at the 99 % and the
97.5 % VaR level, from strictly rolling one-day-ahead forecasts on public series) and reads each model's exceedance stream
with the rules of the VaR-hit experiment, every day: the engine's rate e-process (two-sided and upper), the e-backtest of
Wang, Wang and Ziegel (2022), the Kupiec test on all days so far (from day 50) at the nominal level and at the Sidak level of
its looks, the Kupiec test on the last 250 days (windows of 250 days or more), the Basel traffic light (99 % only, windows
of 250 days or more) and the single Kupiec reading at the end of the window (what the case's eligibility gate reads).

There is no known truth in these windows: the table says which rule fires and when, not which is right. The calm window
2004 to 2006 is the control (a mixed book in a quiet market).

    python manuscripts/e-process-sequential-monitors/experiments/exp_c11.py
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from importlib import metadata

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as cm  # noqa: E402

WINDOWS = ("calm-2004-06", "equity-2007-09", "fx-2008", "equity-2020", "rates-2022", "mixed-2023")
LEVELS = (0.01, 0.025)
RULES = ("e_rate", "e_rate_upper", "e_wwz", "kupiec_cumulative", "kupiec_sidak", "kupiec_trailing", "traffic_light", "kupiec_end")


def day(mask_days: np.ndarray) -> int | None:
    d = float(mask_days[0])
    return None if math.isinf(d) else int(d)


def read_model(h: np.ndarray, p: float, n_days: int) -> dict[str, int | None]:
    looks = max(n_days - cm.FIRST_LOOK + 1, 1)
    lr = cm.cumulative_lr(h, p)
    res: dict[str, int | None] = {
        "e_rate": day(cm.first_true(cm.engine_paths(h, p) >= cm.CROSS)),
        "e_rate_upper": day(cm.first_true(cm.engine_paths(h, p, direction="upper") >= cm.CROSS)),
        "e_wwz": day(cm.first_true(cm.wwz_log_e(h, p) >= cm.CROSS)),
        "kupiec_cumulative": day(cm.first_true(stats.chi2.sf(lr, 1) < cm.LEVEL, cm.FIRST_LOOK - 1)) if n_days >= cm.FIRST_LOOK else None,
        "kupiec_sidak": day(cm.first_true(stats.chi2.sf(lr, 1) < cm.sidak_level(looks), cm.FIRST_LOOK - 1)) if n_days >= cm.FIRST_LOOK else None,
        "kupiec_trailing": None, "traffic_light": None,
    }
    if n_days >= cm.WINDOW:
        res["kupiec_trailing"] = day(cm.first_true(cm.trailing_kupiec(h, p)))
        if abs(p - 0.01) < 1e-12:
            res["traffic_light"] = day(cm.traffic_light_days(h)[0])
    end = bool(cm.kupiec_reject(np.array([float(h.sum())]), np.array([float(n_days)]), p)[0])
    res["kupiec_end"] = n_days if end else None
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "results_c11.json")
    args = ap.parse_args()
    out: dict = {"meta": {"engine_version": metadata.version("riskvalidation"), "levels": list(LEVELS), "script": "experiments/exp_c11.py",
                          "rules": list(RULES), "first_look": cm.FIRST_LOOK, "window": cm.WINDOW}, "windows": {}}
    for w in WINDOWS:
        doc = json.loads((cm.DERIVED / "C11" / f"{w}.json").read_text(encoding="utf-8"))
        n_days = doc["outputs"]["window"]["n_forecast_days"]
        wout: dict = {"n_days": n_days, "start": doc["outputs"]["window"]["start_date"], "end": doc["outputs"]["window"]["end_date"],
                      "asset_class": doc["outputs"]["window"]["asset_class"], "levels": {}}
        for p in LEVELS:
            rows = []
            for m in doc["outputs"]["models"]:
                lvl = next(b for b in m["by_level"] if abs(b["alpha"] - p) < 1e-12)
                h = np.zeros((1, n_days), dtype=bool)
                h[0, lvl["exceedance_days"]] = True
                rows.append({"model": m["model_id"], "exceedances": int(h.sum()), **read_model(h, p, n_days)})
            summary: dict = {"expected": p * n_days, "n_models": len(rows)}
            for rule in RULES:
                fired = [r[rule] for r in rows if r[rule] is not None]
                summary[rule] = {"flagged": len(fired), "median_day": float(np.median(fired)) if fired else None,
                                 "first_day": min(fired) if fired else None}
            e = [r for r in rows if r["e_rate"] is not None]
            tl = [r for r in rows if r["traffic_light"] is not None]
            k_end = [r for r in rows if r["kupiec_end"] is not None]
            summary["overlap"] = {
                "e_and_kupiec_end": sum(r["e_rate"] is not None and r["kupiec_end"] is not None for r in rows),
                "e_only_vs_kupiec_end": sum(r["e_rate"] is not None and r["kupiec_end"] is None for r in rows),
                "kupiec_end_only_vs_e": sum(r["e_rate"] is None and r["kupiec_end"] is not None for r in rows),
                "e_and_light": sum(r["e_rate"] is not None and r["traffic_light"] is not None for r in rows),
                "light_missed_by_e": sum(r["e_rate"] is None for r in tl),
                "median_e_day_among_light_flagged": float(np.median([r["e_rate"] if r["e_rate"] is not None else np.inf for r in tl])) if tl else None,
                "median_light_day": float(np.median([r["traffic_light"] for r in tl])) if tl else None,
                "e_before_kupiec_end": sum(r["e_rate"] is not None and r["kupiec_end"] is not None and r["e_rate"] < r["kupiec_end"] for r in rows),
            }
            del e, k_end
            wout["levels"][f"{p:g}"] = {"summary": summary, "models": rows}
            s = summary
            print(f"[{w} {p:g}] n={n_days} e {s['e_rate']['flagged']} (med {s['e_rate']['median_day']}) light {s['traffic_light']['flagged']}"
                  f" (med {s['traffic_light']['median_day']}) kup-end {s['kupiec_end']['flagged']} kup-cum {s['kupiec_cumulative']['flagged']}"
                  f" wwz {s['e_wwz']['flagged']}", flush=True)
        out["windows"][w] = wout
    args.out.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
