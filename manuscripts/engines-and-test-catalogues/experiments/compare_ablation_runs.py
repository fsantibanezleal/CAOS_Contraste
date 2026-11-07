"""Compare the detection matrices of several runs of ``run_ablation.py`` and write ``results_ablation_reproduction.json``.

    python manuscripts/engines-and-test-catalogues/experiments/compare_ablation_runs.py results_ablation.json results_ablation_rerun1.json ...

The first file is the reference (the committed result); the others are reruns written with ``run_ablation.py --out``.  A run counts as
reproducing the reference when every layer detects exactly the same defects and both false-alarm checks are clean.  Exit 1 when a rerun
differs, so that a difference is never reported as a reproduction.
"""
from __future__ import annotations

import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
LAYERS = "ABCDE"


def matrix(doc: dict) -> dict[str, str]:
    return {m["id"]: "".join(k for k in LAYERS if m["detected_by"][k]) or "-" for m in doc["mutants"]}


def compare(reference: dict, reruns: list[dict]) -> dict:
    ref = matrix(reference)
    rows = []
    for doc in [reference] + reruns:
        mat = matrix(doc)
        rows.append({"matrix_equals_reference": mat == ref, "differences": {k: [ref[k], mat.get(k)] for k in ref if mat.get(k) != ref[k]},
                     "false_alarms": sum(doc["baseline_false_alarms"].values()) + sum(doc["after_restore"].values()),
                     "retries": len(doc.get("retries", [])), "seconds": doc.get("run", {}).get("seconds"),
                     "peak_working_set_mb": doc.get("run", {}).get("peak_working_set_mb")})
    return {"runs": len(rows), "reruns": len(reruns), "reproduced": sum(r["matrix_equals_reference"] and r["false_alarms"] == 0 for r in rows[1:]),
            "reference_matrix": ref, "per_run": rows}


def main() -> int:
    files = [pathlib.Path(a) for a in sys.argv[1:]]
    if len(files) < 2:
        print(__doc__)
        return 2
    docs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    out = compare(docs[0], docs[1:])
    out["files"] = [f.name for f in files]
    (HERE / "results_ablation_reproduction.json").write_text(json.dumps(out, indent=1), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in out.items() if k != "per_run"}, indent=1))
    return 0 if out["reproduced"] == out["reruns"] else 1


if __name__ == "__main__":
    sys.exit(main())
