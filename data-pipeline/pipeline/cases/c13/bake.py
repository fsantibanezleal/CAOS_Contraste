"""The C13 bake: the desk P&L generator at six deficiencies, measured through ``riskvalidation.market``.

``build`` makes every document in memory (no input file: a generator); ``bake`` writes them, the checksums and the manifest. The
documents are the c13-models and c13-outputs contracts (docs/contracts/schemas/c13/). Replication ``i`` of variant ``d`` is a pure
function of its seed ``1000 * case_seed + 1000 * index(d) + i`` (CT-1303).
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from typing import Any

from riskvalidation.market import frtb

from ... import __version__
from ...core import expect as expectations
from ...core import lineage as lin
from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import documents as docs
from . import measure, params
from .params import ALPHAS, GENERATOR, IDS, MAX_REPLICATIONS, N_REPLICATIONS

CASE_ID = "C13"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 60_000.0
MODELS_REL = f"{CASE_ID}/models-generator.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
DEFAULT_VARIANT = "missing-basis"

#: what a reader should see, declared before the full bake from a 100-replication design check (CT-207 form); ranges are wide
#: where the result is a finding
EXPECT: dict[str, tuple[float, float]] = {
    "none_share_amber_or_red": (0.0, 0.10),
    "none_share_desk_over_limit": (0.0, 0.05),
    "missing_basis_share_amber_or_red": (0.80, 1.0),
    "time_misalignment_share_red": (0.90, 1.0),
    "stale_volatility_share_amber_or_red": (0.0, 0.5),
    "wrong_correlation_share_desk_over_limit": (0.3, 1.0),
    "omitted_factor_share_amber_or_red": (0.5, 1.0),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C13 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def replications_for(scale: float) -> int:
    return N_REPLICATIONS if scale >= 1.0 else max(20, min(N_REPLICATIONS, round(N_REPLICATIONS * scale)))


def plan(seed: int, scale: float = 1.0) -> dict[str, Any]:
    """The replication plan: one seed per replication, ``seed_base + index``, disjoint ranges per variant."""
    n = replications_for(scale)
    if n > MAX_REPLICATIONS:
        raise ValueError(f"{n} replications per variant exceed {MAX_REPLICATIONS}")
    return {"n_replications": n, "limits": {a: frtb.desk_exception_limit(a) for a in ALPHAS},
            "variants": [{"deficiency_id": d, "seed_base": params.seed_base(d, seed), "seeds": [params.seed_of(d, i, seed) for i in range(n)]}
                         for d in IDS]}


def _lineage(seed: int, rv: str) -> lin.Lineage:
    return lin.build(CASE_ID, sources=[], truth_status="synthetic-known-truth", seed=seed, code_version=__version__,
                     riskvalidation_version=rv, generators=(GENERATOR,))


def build(seed: int, scale: float = 1.0, *, log: bool = False) -> dict[str, Any]:
    """Every document of the case in memory: ``{"models": doc, "variants": {id: doc}, "values": {...}, "plan": plan}``."""
    rv = docs.rv_version()
    say = _log if log else (lambda _m: None)
    pl = plan(seed, scale)
    n = pl["n_replications"]
    variants: dict[str, dict[str, Any]] = {}
    outs: dict[str, dict[str, Any]] = {}
    for did in IDS:
        m = measure.measure(did, seed, n)
        out, tests = docs.outputs_and_tests(did, m)
        outs[did] = out
        variants[did] = build_artifact(
            case_id=CASE_ID, variant_id=did, model=[docs.model_summary(did, rv)], outputs=out, tests=tests, impact=docs.impact(out),
            findings=docs.findings(out), lineage=_lineage(seed, rv), lane={"lane": "precompute", "reasons": []})
        say(f"{did}: amber or red {out['detection']['share_amber_or_red']:.3f}, red {out['detection']['share_red']:.3f}")
    models = docs.models_document(pl, rv)
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=models["fit_id"], model=models["model"], fit=models["fit"],
                                       lineage=_lineage(seed, rv), lane={"lane": "precompute", "reasons": []})
    return {"models": models_doc, "variants": variants, "values": _values(outs), "plan": pl}


def _values(outs: dict[str, dict[str, Any]]) -> dict[str, float]:
    def share(did: str) -> float:
        return outs[did]["detection"]["share_amber_or_red"]

    def desk(did: str) -> float:
        return max(r["share_over_limit"] for r in outs[did]["desk_backtest"])

    return {"none_share_amber_or_red": share("none"), "none_share_desk_over_limit": desk("none"),
            "missing_basis_share_amber_or_red": share("missing-basis"),
            "time_misalignment_share_red": outs["time-misalignment"]["detection"]["share_red"],
            "stale_volatility_share_amber_or_red": share("stale-volatility"),
            "wrong_correlation_share_desk_over_limit": desk("wrong-correlation"),
            "omitted_factor_share_amber_or_red": share("omitted-factor")}


def _entry_text(did: str) -> dict[str, dict[str, str]]:
    return {"title": docs.TITLE[did], "short_title": docs.T(docs.SHORT[did], docs.SHORT_ES[did]), "regime": docs.MECHANISM[did]}


def bake_case(seed: int, paths: Any, data_root: Path | None, scale: float, title: dict[str, str], question: dict[str, str]) -> dict[str, Any]:
    built = build(seed, scale, log=True)
    entries: list[dict[str, Any]] = []
    sums: list[str] = []
    e = write_artifact(paths.root, MODELS_REL, built["models"], exact=frozenset(), engines=ENGINES, run_ms=RUN_MS)
    sums.append(_sum(paths.root, MODELS_REL))
    entries.append({"role": "models", "variant_id": "models-generator", "truth_status": "synthetic-known-truth",
                    "title": docs.T("The desk P&L generator: its true risk model, the six deficiencies, the PLA thresholds and the desk limits",
                                    "El generador de P&L de mesa: su modelo de riesgo verdadero, las seis deficiencias, los umbrales del PLA y los límites de mesa"),
                    "short_title": docs.T("Models", "Modelos"),
                    "regime": docs.T("The generator, its parameters and the plan of seeds", "El generador, sus parámetros y el plan de semillas"),
                    "path": MODELS_REL, **e})
    for did in IDS:
        rel = f"{CASE_ID}/{did}.json"
        e = write_artifact(paths.root, rel, built["variants"][did], exact=frozenset(), engines=ENGINES, run_ms=RUN_MS)
        sums.append(_sum(paths.root, rel))
        _log(f"variant {did}: {e['bytes']:,} bytes")
        entries.append({"role": "variant", "variant_id": did, **_entry_text(did), "truth_status": "synthetic-known-truth",
                        "models_ref": MODELS_REL, **e})
    (Path(paths.root) / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built["values"])
    manifest = build_case_manifest(
        case_id=CASE_ID, title=title, category={"en": "Market and counterparty risk", "es": "Riesgo de mercado y de contraparte"},
        question=question, sources=[], seed=seed, variants=entries, default_variant=DEFAULT_VARIANT, contract={}, expect=ranges,
        riskvalidation_version=docs.rv_version(), source_details={})
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"
