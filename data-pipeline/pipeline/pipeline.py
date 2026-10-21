"""Offline pipeline orchestrator and CLI.

The canonical bake is an explicit release operation. Tests and smoke runs pass ``--output`` so they cannot mutate
committed scientific evidence. Raw data is read from the device data root (``CONTRASTE_DATA`` or ``--data-root``),
never from the repository.

    python data-pipeline/run.py                  # export the contracts, bake every case, write the index
    python data-pipeline/run.py C01 --seed 7     # one case
    python data-pipeline/run.py --output <dir>   # a sandbox bake
    python data-pipeline/run.py index            # rebuild the 22-case index from the registry (no bake)
    python data-pipeline/run.py readiness        # recompute data/derived/readiness.json (no bake)
"""
from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import registry
from .core import readiness as readiness_mod
from .core.manifest import build_index
from .core.schemas import validate_document
from .io.contract import FAMILIES, export_contracts
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


def _guard_manifest(case_id: str, paths: PipelinePaths, bake) -> dict[str, Any]:
    """Run ``bake`` with the manifest directory staged beside the real one, validate the manifest against its schema
    and only then move it into place: a manifest that fails its schema is never written where the site reads it."""
    staging = paths.root / ".staging" / case_id
    shutil.rmtree(staging, ignore_errors=True)
    try:
        manifest = bake(PipelinePaths(root=paths.root, manifests=staging, models=paths.models))
        validate_document(f"data/derived/manifests/{case_id}.json", manifest)
        paths.manifests.mkdir(parents=True, exist_ok=True)
        for f in staging.glob("*.json"):
            shutil.move(str(f), str(paths.manifests / f.name))
        return manifest
    finally:
        shutil.rmtree(paths.root / ".staging", ignore_errors=True)


def precompute(case_id: str, seed: int = 42, *, output_root: str | Path | None = None,
               data_root: str | Path | None = None) -> dict[str, Any]:
    paths = PipelinePaths.from_output(output_root)
    case = registry.get_built_case(case_id)  # a planned case has nothing to bake: it is declared absent
    root = resolve_data_root(data_root)
    return _guard_manifest(case_id, paths, lambda p: case.bake(seed=seed, paths=p, data_root=root))


def contract_files() -> list[str]:
    """The contract-1 declarations the site serves beside the cases (what export_contract_files writes)."""
    return [*(f"contract/{fam.name}.json" for fam in FAMILIES.values()), "contract/index.json"]


#: the documents beside the cases that a page reads (the regulation page reads the regulatory parity bake, U9-P2)
SERVED_DOCUMENTS = ("regulatory/calculators.json",)


def served_files() -> list[str]:
    """Every file beside the cases that the index declares, so the site build copies it: the contract-1 declarations
    and the served documents."""
    from .governance import served_files as governance_files

    return [*contract_files(), *SERVED_DOCUMENTS, *governance_files(DERIVED)]


def index_document() -> dict[str, Any]:
    """The index of all 22 cases (built and planned), valid against ``common/case-index`` or it raises."""
    doc = build_index(registry.index_entries(), registry.default_case(), served_files())
    validate_document("data/derived/manifests/index.json", doc)
    return doc


def write_index(paths: PipelinePaths) -> int:
    return write_json(paths.manifests / "index.json", index_document())


def write_readiness(paths: PipelinePaths, *, repo_root: Path = REPO_ROOT) -> int:
    """Recompute ``<root>/readiness.json`` from the catalog and the committed documents, validated before writing."""
    doc = readiness_mod.compute(repo_root=repo_root, derived_root=paths.root)
    validate_document("data/derived/readiness.json", doc)
    return readiness_mod.write(paths.root, doc)


def run_all(seed: int = 42, *, output_root: str | Path | None = None,
            data_root: str | Path | None = None) -> list[dict[str, Any]]:
    paths = PipelinePaths.from_output(output_root)
    export_contract_files(paths)
    for case in registry.built_cases():
        precompute(case.id, seed=seed, output_root=paths.root, data_root=data_root)
    write_index(paths)
    write_readiness(paths)
    return registry.index_entries()


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.pipeline")
    ap.add_argument("case", nargs="?", default="all",
                    help="a built case id, 'all' (bake every built case, then the index and the readiness), "
                         "'index' or 'readiness' (rebuild that document from the committed files, no bake)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=Path,
                    help="sandbox output root; omit only for an intentional canonical release bake")
    ap.add_argument("--data-root", help="the device data root (default: $CONTRASTE_DATA)")
    args = ap.parse_args()
    paths = PipelinePaths.from_output(args.output)
    if args.case == "index":
        print(f"index ({write_index(paths):,} bytes) -> {paths.manifests / 'index.json'}")
    elif args.case == "readiness":
        print(f"readiness ({write_readiness(paths):,} bytes) -> {paths.root / 'readiness.json'}")
    elif args.case == "all":
        entries = run_all(args.seed, output_root=args.output, data_root=args.data_root)
        print(f"contracts -> {paths.root / 'contract'}")
        built = {c.id for c in registry.built_cases()}
        print(f"precomputed {len(built)} built cases, {len(entries) - len(built)} planned declared -> {paths.root}")
        for e in entries:
            print(f"  {e['case_id']:6s} [{e['category']['en']}] {'built' if e['case_id'] in built else 'planned'}")
        print(f"index -> {paths.manifests / 'index.json'}; readiness -> {paths.root / 'readiness.json'}")
    else:
        m = precompute(args.case, args.seed, output_root=args.output, data_root=args.data_root)
        print(f"precomputed {args.case}: {len(m['artifacts'])} variants -> {paths.root / args.case}")


if __name__ == "__main__":
    main()
