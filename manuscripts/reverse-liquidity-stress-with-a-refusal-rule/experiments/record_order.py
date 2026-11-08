"""Record the file times and SHA-256 digests of the predictions and of the three stored results into ``file_times.json``.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/experiments/record_order.py

The order of the predictions and the runs is attested only by the modification times that the files had in the working copy where the
experiments were run; a clone does not keep them. This script writes them down once, from that working copy, with the digests of the
files, and states when it ran. Run it again only from a working copy whose file times are the original ones: it refuses when a result
file is older than the predictions.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
FILES = ("hypotheses.json", "results_reverse_c16.json", "results_theory.json", "results_corpus.json")


def stamp(p: pathlib.Path) -> dict:
    t = dt.datetime.fromtimestamp(p.stat().st_mtime).astimezone()
    return {"modified": t.isoformat(timespec="seconds"), "clock": t.strftime("%H:%M:%S"), "date": t.strftime("%Y-%m-%d"),
            "utc_offset": t.strftime("%z"), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main() -> int:
    rec = {name: stamp(HERE / name) for name in FILES}
    h = (HERE / FILES[0]).stat().st_mtime
    for name in FILES[1:]:
        if (HERE / name).stat().st_mtime < h:
            print(f"{name} is older than the predictions: the file times are not the original ones")
            return 1
    out = {"recorded_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
           "note": "modification times of the working copy where the experiments were run; not a commit order", "files": rec}
    (HERE / "file_times.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("wrote file_times.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
