"""Offline pipeline orchestrator and CLI.

The canonical bake is an explicit release operation. Tests and smoke runs pass ``--output`` so they cannot mutate
committed scientific evidence. Raw data is read from the device data root (``CONTRASTE_DATA`` or ``--data-root``),
never from the repository.

    python data-pipeline/run.py                  # export the contracts, bake every case, write the index
    python data-pipeline/run.py C01 --seed 7     # one case
    python data-pipeline/run.py --output <dir>   # a sandbox bake
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import registry
from .core.manifest import build_index
from .io.contract import export_contracts
from .io.fetch import data_root as resolve_data_root
from .io.formats import write_json

# data-pipeline/pipeline/pipeline.py -> parents[2] = repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DERIVED = REPO_ROOT / "data" / "derived"
MANIFESTS = DERIVED / "manifests"
MODELS = REPO_ROOT / "models"

STAGES = ("ingest", "preprocess", "split", "feature_extraction", "train", "infer", "evaluate", "export", "validate")


@dataclass(frozen=True)
class PipelinePaths:
    root: Path
    manifests: Path
    models: Path

    @classmethod
    def from_output(cls, output: str | Path | None = None) -> PipelinePaths:
        if output is None:
            return cls(root=DERIVED, manifests=MANIFESTS, models=MODELS)
        root = Path(output).resolve()
        return cls(root=root, manifests=root / "manifests", models=root / "models")


def export_contract_files(paths: PipelinePaths) -> list[str]:
    """Contract 1 as JSON, for the web's bring-your-own-data and the TypeScript mirror."""
    return export_contracts(paths.root / "contract")


def precompute(case_id: str, seed: int = 42, *, output_root: str | Path | None = None,
               data_root: str | Path | None = None) -> dict[str, Any]:
    paths = PipelinePaths.from_output(output_root)
    case = registry.get_case(case_id)
    return case.bake(seed=seed, paths=paths, data_root=resolve_data_root(data_root))


def run_all(seed: int = 42, *, output_root: str | Path | None = None,
            data_root: str | Path | None = None) -> list[dict[str, Any]]:
    paths = PipelinePaths.from_output(output_root)
    contract_files = [f"contract/{name}" for name in export_contract_files(paths)]
    entries = []
    for case in registry.list_cases():
        precompute(case.id, seed=seed, output_root=paths.root, data_root=data_root)
        entries.append({"case_id": case.id, "title": case.title, "category": registry.category(case.category_id),
                        "category_id": case.category_id, "kind": case.kind,
                        "manifest_path": f"manifests/{case.id}.json"})
    if entries:
        write_json(paths.manifests / "index.json", build_index(entries, registry.default_case(), contract_files))
    return entries


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.pipeline")
    ap.add_argument("case", nargs="?", default="all", help="a case id, or 'all'")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path,
                    help="sandbox output root; omit only for an intentional canonical release bake")
    ap.add_argument("--data-root", help="the device data root (default: $CONTRASTE_DATA)")
    args = ap.parse_args()
    paths = PipelinePaths.from_output(args.output)
    if args.case == "all":
        entries = run_all(args.seed, output_root=args.output, data_root=args.data_root)
        print(f"contracts -> {paths.root / 'contract'}")
        print(f"precomputed {len(entries)} cases -> {paths.root}")
        for e in entries:
            print(f"  {e['case_id']:6s} [{e['category']['en']}]")
        if entries:
            print(f"index -> {paths.manifests / 'index.json'}")
    else:
        m = precompute(args.case, args.seed, output_root=args.output, data_root=args.data_root)
        print(f"precomputed {args.case}: {len(m['artifacts'])} variants -> {paths.root / args.case}")


if __name__ == "__main__":
    main()
