"""Rerun the deterministic experiments, check that they reproduce the committed outputs, and write ``run-times.json``.

    python manuscripts/reconciliation-against-reference-engines/experiments/run_all.py --out-dir <folder under the temp root>
        [--tm-python <python with transitionMatrix 0.5.1>]

The cheap experiments (the printed answers, the independent routes, the closed forms, the committed documents, the pair
correlations and, with ``--tm-python``, the comparison with ``transitionMatrix``) are run again into ``--out-dir``; their outputs
are compared with the committed ``results_*.json`` after loading both (the seeds are fixed, so a deterministic experiment
reproduces its output exactly), and the wall time of each is recorded. The two long experiments are not rerun here: the size and
power of the rules (``exp_criterion.py``) and the repeated comparisons with ORE (``exp_ore_replicates.py``) record their own wall
time in their outputs, which this script copies into ``run-times.json``; rerunning them with the commands of the manuscript's
Reproducibility section gives the same outputs, because every random number is seeded.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent

STEPS = [("exp_printed.py", "results_printed.json"), ("exp_routes.py", "results_routes.json"), ("exp_closedforms.py", "results_closedforms.json"),
         ("exp_committed.py", "results_committed.json"), ("exp_pairs.py", "results_pairs.json")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--tm-python", default=None)
    args = ap.parse_args()
    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seconds: dict[str, float] = {}
    bad: list[str] = []
    steps = list(STEPS)
    for script, result in steps + ([("exp_transition_matrix.py", "results_transition_matrix.json")] if args.tm_python else []):
        py = args.tm_python if script == "exp_transition_matrix.py" else sys.executable
        target = out_dir / result
        t0 = time.perf_counter()
        proc = subprocess.run([py, str(HERE / script), "--out", str(target)], capture_output=True, text=True, check=False)
        seconds[script] = round(time.perf_counter() - t0, 1)
        if proc.returncode != 0:
            print(proc.stderr[-1500:])
            bad.append(f"{script}: exit {proc.returncode}")
            continue
        same = json.loads(target.read_text(encoding="utf-8")) == json.loads((HERE / result).read_text(encoding="utf-8"))
        print(f"{script:28s} {seconds[script]:8.1f} s  reproduces the committed output: {same}")
        if not same:
            bad.append(f"{script}: output differs from {result}")
    crit = json.loads((HERE / "results_criterion.json").read_text(encoding="utf-8"))
    seconds["exp_criterion.py"] = round(crit["seconds"], 1)
    for v in ("netting-set", "single-swap", "csa-mpor-10d"):
        seconds[f"exp_ore_replicates.py {v}"] = round(json.loads((HERE / f"results_ore_{v}.json").read_text(encoding="utf-8"))["summary"]["wall_seconds"], 1)
    record = {"seconds": seconds, "python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor(),
              "logical_processors": __import__("os").cpu_count(), "criterion_workers": 10, "ore_workers": 4, "mismatches": bad}
    (HERE / "run-times.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("run-times.json written;", "all outputs reproduce" if not bad else f"MISMATCH: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
