"""The C09 bake: the revolving-line generator at six acceleration levels, estimated through ``riskvalidation`` 0.6.0.

``build`` makes every document in memory (no input file: the Fed marginals are committed in ``params`` with their hashes);
``bake`` writes them, the checksums and the manifest. The documents are the c09-models and c09-outputs contracts
(docs/contracts/schemas/c09/). Development replications fit the EAD models, independent test replications evaluate every
estimate against the known CCF; both sets are fixed by seed (CT-1003).
"""
from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from typing import Any

from ... import __version__
from ...core import expect as expectations
from ...core import lineage as lin
from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import calibration, documents as docs
from . import estimators as est
from . import generator
from . import models as mdl
from . import params
from .params import GENERATOR, LEVELS, PARAMS

CASE_ID = "C09"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 30_000.0
MODELS_REL = f"{CASE_ID}/models-generator.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
DEFAULT_VARIANT = "level-3"
FULL_FACILITIES = 50_000
FULL_REPLICATIONS = 20

#: what a reader should see, declared before the bake (CT-207 form); ranges are wide where the result is a finding
EXPECT: dict[str, tuple[float, float]] = {
    "level0_known_ccf": (0.599, 0.601),
    "level5_known_ccf": (0.75, 0.82),
    "fixed_horizon_mean_bias_max_abs": (0.0, 0.02),
    "cohort_pooled_bias_level0": (-0.40, -0.10),
    "variable_horizon_pooled_bias_level0": (-0.35, -0.05),
    "fixed_horizon_undefined_share": (0.10, 0.35),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C09 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def plan(seed: int, scale: float = 1.0) -> dict[str, Any]:
    """The replication plan: disjoint development and test seeds derived from the case seed, and the sizes."""
    r = FULL_REPLICATIONS if scale >= 1.0 else max(3, min(FULL_REPLICATIONS, round(FULL_REPLICATIONS * scale * 10)))
    n = FULL_FACILITIES if scale >= 1.0 else max(5000, round(FULL_FACILITIES * scale))
    return {"development_seeds": [int(seed) * 1000 + 100 + k for k in range(r)], "test_seeds": [int(seed) * 1000 + 500 + k for k in range(r)],
            "n_facilities": n}


def _observe(d: generator.Defaulters) -> dict[str, est.Observations]:
    return {design: est.observe(d, design) for design in est.DESIGNS}


def build(seed: int, scale: float = 1.0, *, log: bool = False) -> dict[str, Any]:
    """Every document of the case in memory: ``{"models": doc, "variants": {id: doc}, "values": {...}, "data": {level: LevelData}}``."""
    calibration.validate_marginals(calibration.marginals())
    rv = docs.rv_version()
    say = _log if log else (lambda _m: None)
    pl = plan(seed, scale)
    n = pl["n_facilities"]
    dev: dict[int, dict[str, list[est.Observations]]] = {k: {d: [] for d in est.DESIGNS} for k in range(len(LEVELS))}
    n_dev = dict.fromkeys(range(len(LEVELS)), 0)
    for s in pl["development_seeds"]:
        pop = generator.draw_population(s, n)
        for k in range(len(LEVELS)):
            d = generator.realise(pop, k)
            for design, obs in _observe(d).items():
                dev[k][design].append(obs)
            n_dev[k] += d.n_defaults
        say(f"development seed {s}: {pop.tier.size:,} defaults")
    fits, bounded = {}, {}
    for k in range(len(LEVELS)):
        pooled = {design: est.join(parts) for design, parts in dev[k].items()}
        fits[k] = mdl.fit_models(pooled)
        bounded[k] = {design: est.fit_bounded(pooled[design])[0] for design in est.DESIGNS}
    del dev
    runs: dict[int, dict[tuple[str, str, str], list[est.Estimate]]] = {k: {} for k in range(len(LEVELS))}
    test_parts: dict[int, dict[str, list[est.Observations]]] = {k: {d: [] for d in est.DESIGNS} for k in range(len(LEVELS))}
    n_test = dict.fromkeys(range(len(LEVELS)), 0)
    for s in pl["test_seeds"]:
        pop = generator.draw_population(s, n)
        for k in range(len(LEVELS)):
            d = generator.realise(pop, k)
            n_test[k] += d.n_defaults
            for design, obs in _observe(d).items():
                test_parts[k][design].append(obs)
                for treatment in est.TREATMENTS:
                    for agg in est.ESTIMATORS:
                        e = est.aggregate(obs, treatment, agg, bounded[k][design] if treatment == "bounded-scale" else None)
                        runs[k].setdefault((design, treatment, agg), []).append(e)
        say(f"test seed {s}: {pop.tier.size:,} defaults")
    data = {k: docs.LevelData(k, fits[k], bounded[k], runs[k], {design: est.join(parts) for design, parts in test_parts[k].items()},
                              n_dev[k], n_test[k]) for k in range(len(LEVELS))}
    variants: dict[str, dict[str, Any]] = {}
    outs: dict[int, dict[str, Any]] = {}
    for k in range(len(LEVELS)):
        out, tests = docs.outputs_and_tests(pl, k, data[k])
        outs[k] = out
        lineage = _lineage(seed, rv)
        variants[f"level-{k}"] = build_artifact(
            case_id=CASE_ID, variant_id=f"level-{k}", model=docs.model_summaries(k, data[k], rv), outputs=out, tests=tests,
            impact=docs.impact(out), findings=docs.findings(out), lineage=lineage, lane={"lane": "precompute", "reasons": []})
        say(f"level {k}: known CCF {params.known_ccf(k):.4f}")
    models = docs.models_document(pl, data, rv)
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=models["fit_id"], model=models["model"], fit=models["fit"],
                                       lineage=_lineage(seed, rv), lane={"lane": "precompute", "reasons": []})
    return {"models": models_doc, "variants": variants, "values": _values(outs, data), "data": data, "plan": pl}


def _lineage(seed: int, rv: str) -> lin.Lineage:
    return lin.build(CASE_ID, sources=[], truth_status="synthetic-known-truth", seed=seed, code_version=__version__,
                     riskvalidation_version=rv, generators=(GENERATOR,))


def _values(outs: dict[int, dict[str, Any]], data: dict[int, docs.LevelData]) -> dict[str, float]:
    fx = [docs.row_of(o, "fixed-horizon", "none", "mean") for o in outs.values()]
    obs0 = data[0].test["fixed-horizon"]
    return {
        "level0_known_ccf": outs[0]["generator"]["true_ccf"]["value"], "level5_known_ccf": outs[5]["generator"]["true_ccf"]["value"],
        "fixed_horizon_mean_bias_max_abs": max(abs(r["bias"]) for r in fx),
        "cohort_pooled_bias_level0": docs.row_of(outs[0], "cohort", "none", "pooled")["bias"],
        "variable_horizon_pooled_bias_level0": docs.row_of(outs[0], "variable-horizon", "none", "pooled")["bias"],
        "fixed_horizon_undefined_share": float((~(obs0.undrawn > 0)).mean()),
    }


def bake_case(seed: int, paths: Any, data_root: Path | None, scale: float, title: dict[str, str], question: dict[str, str]) -> dict[str, Any]:
    built = build(seed, scale, log=True)
    _check_raw(data_root)
    entries: list[dict[str, Any]] = []
    sums: list[str] = []
    models = built["models"]
    e = write_artifact(paths.root, MODELS_REL, models, exact=docs.EXACT, engines=ENGINES, run_ms=RUN_MS)
    sums.append(_sum(paths.root, MODELS_REL))
    entries.append({"role": "models", "variant_id": "models-generator", "truth_status": "synthetic-known-truth",
                    "title": docs.T("The revolving-line generator: its marginals, levels, designs and EAD models",
                                    "El generador de líneas rotativas: sus marginales, niveles, diseños y modelos de EAD"),
                    "short_title": docs.T("Models", "Modelos"),
                    "regime": docs.T("The generator, its known CCF by level and the Federal Reserve 2025 marginals it follows",
                                     "El generador, su CCF conocido por nivel y las marginales de la Reserva Federal 2025 que sigue"),
                    "path": MODELS_REL, **e})
    for k in range(len(LEVELS)):
        vid = f"level-{k}"
        rel = f"{CASE_ID}/{vid}.json"
        e = write_artifact(paths.root, rel, built["variants"][vid], exact=docs.EXACT, engines=ENGINES, run_ms=RUN_MS)
        sums.append(_sum(paths.root, rel))
        _log(f"variant {vid}: {e['bytes']:,} bytes")
        entries.append({"role": "variant", "variant_id": vid, "title": docs.level_text(k),
                        "short_title": docs.T(f"Level {k}", f"Nivel {k}"), "regime": docs.level_text(k),
                        "truth_status": "synthetic-known-truth", "models_ref": MODELS_REL, **e})
    (Path(paths.root) / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built["values"])
    manifest = build_case_manifest(
        case_id=CASE_ID, title=title, category={"en": "LGD and EAD", "es": "LGD y EAD"}, question=question, sources=[], seed=seed,
        variants=entries, default_variant=DEFAULT_VARIANT, contract={}, expect=ranges, riskvalidation_version=docs.rv_version(),
        source_details={})
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def _check_raw(data_root: Path | None) -> None:
    """The fetched Federal Reserve files, when the device data root holds them, must be the ones whose hash the parameters carry."""
    if data_root is None:
        return
    raw = Path(data_root) / "raw" / "fed-cards-2025"
    for f in PARAMS["sources"]:
        path = raw / f["name"]
        if path.exists():
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            if got != f["sha256"]:
                raise ValueError(f"{path}: sha256 {got} is not the file the calibration names ({f['sha256']})")
            _log(f"raw {f['name']}: sha256 verified")
