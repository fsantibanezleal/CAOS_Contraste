"""Validate your own scored sample offline: contract 1, the master scale and the validation battery.

The door for a reader's own model (docs/guides/02_validate-your-own-model.md). The input is a CSV in the
scored_sample family of contract 1: ``id``, ``observation_date``, ``target`` (1 = default over the horizon) and
``pd``; ``score``, ``grade``, ``segment`` and ``protected_attr`` are optional, and any other column is listed as
ignored, never used. Contract 1 rejects, flags or excludes each record and never coerces one. The accepted records
with a PD are mapped to the master scale (core/calibration.py) and run through the battery of stages/evaluate.py,
which is riskvalidation's tests under its default policy. An optional reference, the development sample in the same
format, enables the tests that compare against the development: the PSI, the AUC against the initial validation and
the grade concentration.

The report is JSON in an output directory outside the repository, never in data/, which holds the committed
artifacts of the release bake.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from . import __version__
from .io import contract
from .io.formats import read_csv_rows

SCHEMA = "contraste.own-validation/v1"
REPO = Path(__file__).resolve().parents[2]
EXAMPLES = REPO / "data" / "examples"


class OwnSampleError(ValueError):
    """The sample cannot be validated as given (no PD, one class only, an output inside the repository)."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scored(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    report = contract.validate("scored_sample", read_csv_rows(path))
    rows = [r for r in report.accepted if r.get("pd") is not None]
    if not rows:
        raise OwnSampleError(f"{path.name}: no accepted record carries a pd; the battery needs one per record")
    pd = np.array([r["pd"] for r in rows], dtype=float)
    y = np.array([r["target"] for r in rows], dtype=int)
    return {"path": path, "report": report, "pd": pd, "y": y, "without_pd": len(report.accepted) - len(rows)}


def _describe(s: dict[str, Any]) -> dict[str, Any]:
    return {"file": s["path"].name, "sha256": _sha256(s["path"]), "contract": s["report"].summary(),
            "battery_records": int(len(s["y"])), "defaults": int(s["y"].sum()),
            "accepted_without_pd": int(s["without_pd"])}


def validate_own(sample: str | Path, *, reference: str | Path | None = None,
                 model_id: str = "own-model") -> dict[str, Any]:
    """The validation report of a scored sample, as a JSON-ready dict (pure: reads the files, writes nothing)."""
    from .stages import evaluate

    s = _scored(sample)
    if s["y"].min() == s["y"].max():
        raise OwnSampleError(f"{s['path'].name}: the battery needs defaults and non-defaults; every target is "
                             f"{int(s['y'][0])}")
    ref = _scored(reference) if reference is not None else None
    tests = evaluate.battery(model_id, s["pd"], s["y"],
                             pd_train=ref["pd"] if ref else None,
                             pd_cal=ref["pd"] if ref else None,
                             y_cal=ref["y"] if ref else None,
                             champion_pd=None)
    lights: dict[str, int] = {}
    for t in tests:
        lights[t["light"]] = lights.get(t["light"], 0) + 1
    from importlib.metadata import version

    return {
        "schema": SCHEMA,
        "model_id": model_id,
        "engine": {"pipeline": __version__, "riskvalidation": version("riskvalidation")},
        "sample": _describe(s),
        "reference": _describe(ref) if ref else None,
        "lights": dict(sorted(lights.items())),
        "tests": tests,
    }


def write_report(report: dict[str, Any], out_dir: str | Path) -> Path:
    out = Path(out_dir).resolve()
    if out == REPO or REPO in out.parents:
        raise OwnSampleError(f"the output {out} is inside the repository; write the report outside it")
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{report['model_id']}-validation.json"
    path.write_bytes((json.dumps(report, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return path


def _summary(report: dict[str, Any]) -> str:
    def num(v: Any) -> str:
        return "" if v is None else f"{v:.4g}"

    lines = [f"{report['model_id']}: {report['sample']['battery_records']:,} records, "
             f"{report['sample']['defaults']:,} defaults; lights {report['lights']}"]
    for t in report["tests"]:
        label, value = ("statistic", t["statistic"]) if t["statistic"] is not None else ("metric", t["metric"])
        lines.append(f"  {t['test_id']:<20} {str(t['segment']):<10} {label:>9} {num(value):>10}  "
                     f"p {num(t['p_value']):>10}  {t['light']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="validate", description="Validate your own scored sample: contract 1 and the battery.")
    ap.add_argument("sample", nargs="?", help="a CSV in the scored_sample family (id, observation_date, target, pd)")
    ap.add_argument("--reference", help="the development sample, same format (enables the PSI, the AUC against the "
                                        "initial validation and the grade concentration)")
    ap.add_argument("--model-id", default="own-model", help="the name the report carries (default: own-model)")
    ap.add_argument("--output", help="the report's directory, outside the repository")
    ap.add_argument("--write-examples", action="store_true",
                    help="regenerate the two known-truth examples in data/examples/ and exit")
    args = ap.parse_args(argv)
    if args.write_examples:
        from .io.examples import write_examples

        for p in write_examples(EXAMPLES):
            print(f"wrote {p.relative_to(REPO).as_posix()}")
        return 0
    if not args.sample or not args.output:
        ap.error("name the sample and --output (or --write-examples)")
    try:
        report = validate_own(args.sample, reference=args.reference, model_id=args.model_id)
        path = write_report(report, args.output)
    except (OwnSampleError, contract.ContractError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(_summary(report))
    c = report["sample"]["contract"]["counts"]
    print(f"contract 1: {c}")
    print(f"report -> {path}")
    return 0
