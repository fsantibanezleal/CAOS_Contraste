"""Offline pipeline orchestrator and CLI.

The canonical bake is an explicit release operation. Tests and CI smoke runs
must pass ``--output`` so they cannot mutate committed scientific evidence.

    python data-pipeline/run.py            # all cases
    python data-pipeline/run.py EX02_epidemic --seed 7
    python data-pipeline/run.py EX02_epidemic --output build/smoke
"""
from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

from . import registry
from .core import expect as expectations
from .core.manifest import build_index
from .core.rng import make_rng
from .io.contract import validate_rows
from .io.formats import write_json
from .io.schema import SIRParams
from .stages import evaluate, export, infer, train

# data-pipeline/pipeline/pipeline.py -> parents[2] = repo root (works under `pip install -e .` too)
REPO_ROOT = Path(__file__).resolve().parents[2]
DERIVED = REPO_ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"
MODELS = REPO_ROOT / "models"

STAGES = ("preprocess", "feature_extraction", "train", "infer", "evaluate", "export")


@dataclass(frozen=True)
class PipelinePaths:
    root: Path
    manifests: Path
    models: Path

    @classmethod
    def from_output(cls, output: str | Path | None = None) -> "PipelinePaths":
        if output is None:
            return cls(root=DERIVED, manifests=MANIFESTS, models=MODELS)
        root = Path(output).resolve()
        return cls(root=root, manifests=root / "manifests", models=root / "models")


def _train_model(models_dir: Path) -> dict:
    # didactic surrogate: train on the non-degenerate case params; held-out eval uses a disjoint synthetic draw
    params = [c.params for c in registry.list_cases() if c.params.I0 > 0]
    return train.run(params, str(models_dir))


def _holdout_params(seed: int) -> list[SIRParams]:
    rng = make_rng(seed + 999)  # disjoint from training => leakage-safe
    out: list[SIRParams] = []
    for i in range(20):
        out.append(SIRParams(f"_holdout{i}", beta=float(rng.uniform(0.15, 1.2)),
                             gamma=float(rng.uniform(0.15, 0.40)), N=100_000.0, I0=50.0))
    return out


def _engine_ms(params: SIRParams, repeats: int = 5) -> float:
    """The cost the lane gate judges: one engine run, after a warm-up, as the median of several. Timing the whole case
    (validation, evaluation, the cold start of the first case in a bake) made the verdict depend on bake order: the
    first case baked was once labelled precompute while it runs in microseconds (found 2026-10-04)."""
    infer.run(params)
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        infer.run(params)
        times.append((time.perf_counter() - t0) * 1000.0)
    return sorted(times)[repeats // 2]


def precompute(
    case_id: str,
    seed: int = 42,
    model: dict | None = None,
    *,
    output_root: str | Path | None = None,
) -> dict:
    paths = PipelinePaths.from_output(output_root)
    case = registry.get_case(case_id)
    if model is None:
        model = _train_model(paths.models)
    # run CONTRACT 1 on the case params (proves the gate + carries flags); a real product reads raw data here
    rep = validate_rows([{"case_id": case.params.case_id, "beta": case.params.beta, "gamma": case.params.gamma,
                          "N": case.params.N, "I0": case.params.I0, "days": case.params.days}])
    params = rep.accepted[0] if rep.accepted else case.params
    result = infer.run(params)
    expect = expectations.check(case.id, case.expect, result)  # a result outside its declared range fails the bake
    run_ms = _engine_ms(params)
    metrics = evaluate.run(model, _holdout_params(seed))
    return export.run(case=case, params=params, result=result, seed=seed, run_ms=run_ms,
                      flags=rep.flagged, metrics=metrics, expect=expect, derived_dir=str(paths.root),
                      manifests_dir=str(paths.manifests))


def run_all(seed: int = 42, *, output_root: str | Path | None = None) -> list[dict]:
    paths = PipelinePaths.from_output(output_root)
    model = _train_model(paths.models)
    entries = []
    for c in registry.list_cases():
        precompute(c.id, seed=seed, model=model, output_root=paths.root)
        entries.append({"case_id": c.id, "title": c.title, "category": c.category, "manifest_path": f"manifests/{c.id}.json"})
    write_json(paths.manifests / "index.json", build_index(entries, registry.default_case()))
    return entries


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.pipeline")
    ap.add_argument("case", nargs="?", default="all", help="a case id, or 'all'")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path,
                    help="sandbox output root; omit only for an intentional canonical release bake")
    args = ap.parse_args()
    paths = PipelinePaths.from_output(args.output)
    if args.case == "all":
        entries = run_all(args.seed, output_root=args.output)
        print(f"precomputed {len(entries)} cases -> {paths.root}")
        for e in entries:
            print(f"  {e['case_id']:20s} [{e['category']['en']}]")
        print(f"index -> {paths.manifests / 'index.json'}")
    else:
        m = precompute(args.case, args.seed, output_root=args.output)
        print(f"precomputed {args.case}: lane={m['lane']} bytes={m['artifact']['bytes']} "
              f"metrics={m['metrics']} -> {paths.root / m['artifact']['path']}")


if __name__ == "__main__":
    main()
