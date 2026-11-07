"""Run every experiment script of the manuscript, time it, and check that it reproduces the committed outputs.

    python manuscripts/e-process-sequential-monitors/experiments/run_all.py [--verify] [--out-dir DIR]

With ``--verify`` (default) each script writes into ``--out-dir`` (a folder under the device's temp root, never the repository) and
the output is compared with the committed ``results_*.json`` after dropping nothing: the seeds are fixed, so a deterministic
experiment reproduces its committed output exactly. With ``--commit`` the scripts write the committed files themselves. The wall time of
each script is written to ``run-times.json`` (hardware and Python in the record), which the Reproducibility section quotes.
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

#: (script, committed outputs it writes as option name -> file name)
STEPS: list[tuple[str, dict[str, str]]] = [
    ("exp_hits.py", {"--out": "results_hits.json", "--out-horizon": "results_size_horizon.json"}),
    ("exp_ablation.py", {"--out": "results_ablation.json"}),
    ("exp_x3_seeds.py", {"--out": "results_x3_seeds.json"}),
    ("exp_pd_correlation.py", {"--out": "results_pd_correlation.json"}),
    ("exp_c11.py", {"--out": "results_c11.json"}),
    ("exp_c03.py", {"--out": "results_c03.json"}),
    ("exp_theory.py", {"--out": "results_theory.json"}),
    ("exp_matched.py", {"--out": "results_matched.json"}),
    ("exp_pd_comparators.py", {"--out": "results_pd_comparators.json"}),
]


def upstream(out_dir: pathlib.Path, name: str) -> pathlib.Path:
    """An input produced by an earlier step: the verification copy when this run made one, the committed file otherwise."""
    return out_dir / name if (out_dir / name).exists() else HERE / name


def same(a: object, b: object) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=pathlib.Path, required=False, default=None, help="where the verification outputs go (outside the repository)")
    ap.add_argument("--commit", action="store_true", help="write the committed result files instead of verifying them")
    ap.add_argument("--only", nargs="+", default=None, metavar="SCRIPT",
                    help="run only these scripts (for example exp_matched.py); the times of the others in run-times.json are kept")
    args = ap.parse_args()
    if not args.commit and args.out_dir is None:
        ap.error("--out-dir is required to verify (use a folder under the temp root); or pass --commit")
    if args.out_dir is not None:
        args.out_dir.mkdir(parents=True, exist_ok=True)
    times: dict[str, float] = {}
    ok = True
    for script, outs in STEPS:
        if args.only is not None and script not in args.only:
            continue
        cmd = [sys.executable, str(HERE / script)]
        for opt, name in outs.items():
            target = (HERE / name) if args.commit else (args.out_dir / name)
            cmd += [opt, str(target)]
        if script == "exp_theory.py" and not args.commit:
            cmd += ["--hits", str(upstream(args.out_dir, "results_hits.json"))]
        if script == "exp_pd_comparators.py" and not args.commit:
            cmd += ["--ablation", str(upstream(args.out_dir, "results_ablation.json"))]
        t0 = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True)
        times[script] = round(time.time() - t0, 1)
        if res.returncode != 0:
            print(f"FAILED {script}\n{res.stderr[-1500:]}")
            ok = False
            continue
        if not args.commit:
            for name in outs.values():
                a = json.loads((HERE / name).read_text(encoding="utf-8"))
                b = json.loads((args.out_dir / name).read_text(encoding="utf-8"))
                match = same(a, b)
                ok &= match
                print(f"{script}: {name} {'reproduced exactly' if match else 'DIFFERS'} ({times[script]} s)", flush=True)
        else:
            print(f"{script}: written ({times[script]} s)", flush=True)
    path = HERE / "run-times.json"
    if args.only is not None and path.exists():
        times = {**json.loads(path.read_text(encoding="utf-8"))["seconds"], **times}
    record = {"seconds": times, "total_seconds": round(sum(times.values()), 1), "python": platform.python_version(),
              "platform": platform.platform(), "processor": platform.processor()}
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(json.dumps(record))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
