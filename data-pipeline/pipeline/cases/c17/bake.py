"""The C17 bake: histories of a synthetic bank at four tail indices, through the ladder of ``riskvalidation.oprisk``.

``build`` makes every document in memory; ``bake_case`` writes them, the checksums and the manifest. The documents are the
c17-models and c17-outputs contracts (docs/contracts/schemas/c17/). Per variant (tail index) four cells (5 or 10 years of data,
collection threshold EUR 10,000 or 20,000) of independent replications; the truth of the variant is computed once. The cells are
cached by variant (``data_root/cache/C17``) keyed by the plan and a hash of the package source, so an interrupted bake resumes
and an edited estimator never reuses a stale cell. The estimation of a replication is ``replicate.estimate``.
"""
from __future__ import annotations

import hashlib
import os
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from ... import __version__
from ...core import expect as expectations
from ...core import lineage as lin
from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ...io import contract as contract1
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import documents as docs
from . import extras, truth
from . import params as P
from .generator import Variant, cell_seeds, draw_history, expected_count_above, seed_base, variant, variants
from .replicate import RUNGS, bank_business_indicator, estimate, scenario_points, scenario_prior

CASE_ID = "C17"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 3_600_000.0
MODELS_REL = f"{CASE_ID}/models-generator.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
DEFAULT_VARIANT = "xi-0-8"
EXACT: frozenset[str] = frozenset()

#: what a reader should see, declared before the bake (CT-207 form); the ranges are wide where the result is a finding
EXPECT: dict[str, tuple[float, float]] = {
    "calibration_max_abs_log_error": (0.0, 0.5),
    "frequency_above_20000_per_year": (40.99, 41.01),
    "true_quantile_xi_0_6_eur": (2.0e7, 3.0e8),
    "true_quantile_xi_0_8_eur": (6.0e7, 8.0e8),
    "true_quantile_xi_0_96_eur": (3.0e8, 6.0e9),
    "true_quantile_xi_1_1_eur": (5.0e8, 1.0e10),
    "bank_bic_eur": (1.79e8, 1.81e8),
    "mc_checks_agree": (1.0, 1.0),
    "history_rows_rejected_by_contract_1": (0.0, 0.0),
}

_T0 = time.perf_counter()
MIN_REPLICATIONS = 6


def _log(msg: str) -> None:
    print(f"[C17 {time.perf_counter() - _T0:8.1f}s] {msg}", file=sys.stderr, flush=True)


def plan(seed: int, scale: float = 1.0) -> dict[str, Any]:
    """The replication plan: the number of histories per cell and the Monte Carlo sizes, scaled down for tests (ADR-0074)."""
    if scale >= 1.0:
        return {"n_replications": P.N_REPLICATIONS, "mc_truth": P.MC_YEARS_TRUTH, "mc_rep": P.MC_YEARS_REPLICATION, "check_contract": True}
    n = max(MIN_REPLICATIONS, min(P.N_REPLICATIONS, round(P.N_REPLICATIONS * scale)))
    return {"n_replications": n, "mc_truth": max(200_000, round(P.MC_YEARS_TRUTH * scale)), "mc_rep": max(20_000, round(P.MC_YEARS_REPLICATION * scale)),
            "check_contract": True}


ESTIMATOR_FILES = ("generator.py", "replicate.py", "aggregation.py", "params.py")


def source_hash() -> str:
    """A digest of the modules that produce a replication (generator, estimators, aggregation grid, parameters): a cached cell is reused
    only while they are unchanged; the document writers can change without redoing an hour of replications."""
    h = hashlib.sha256()
    for name in ESTIMATOR_FILES:
        h.update(name.encode() + (Path(__file__).parent / name).read_bytes())
    return h.hexdigest()[:16]


def _work(task: tuple[float, int, float, int, float, Any, int, bool]) -> tuple[dict[str, Any], int]:
    """One replication in a worker: the history through contract 1 (its rows pass or the bake stops), then the ladder."""
    xi, years, threshold, seed, bi, prior, mc_rep, check = task
    v = variant(xi)
    rejected = 0
    if check:
        rows = draw_history(v, seed, years).rows(threshold)
        rep = contract1.validate("loss_events", rows, params={"collection_threshold": threshold, "currency": P.CURRENCY})
        c = rep.counts()
        rejected = c["rejected"] + c["excluded"]
        if rejected or c["accepted"] != c["input"] or not c["input"]:
            raise ValueError(f"seed {seed}: the generator's rows fail contract 1: {rep.summary()}")
    return estimate(v, seed, years, threshold, bi, prior, mc_rep), rejected


def run_cell(v: Variant, years: int, threshold: float, first: int, n: int, bi: float, prior: Any, mc_rep: int, check: bool, workers: int,
             cache: Path | None, key: str) -> docs.CellResult:
    path = cache / f"{v.variant_id}-y{years}-h{int(threshold)}-{key}.npz" if cache else None
    if path is not None and path.exists():
        with np.load(path, allow_pickle=False) as z:
            return docs.CellResult(years, threshold, first, {k: z[k] for k in z.files})
    tasks = [(v.tail_index, years, threshold, first + k, bi, prior, mc_rep, check) for k in range(n)]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(_work, tasks, chunksize=max(1, n // (workers * 8))))
    else:
        results = [_work(t) for t in tasks]
    arrays: dict[str, np.ndarray] = {}
    for k in ("failed", "n_losses", "lam_obs", "agree", "lc", "ilm", "orc", *RUNGS):
        arrays[k] = np.array([r[0][k] for r in results], dtype=float)
    arrays["xi"] = np.array([r[0]["xi"] for r in results], dtype=float)
    arrays["n_exceed"] = np.array([r[0]["n_exceed"] for r in results], dtype=float)
    arrays["rejected"] = np.array([r[1] for r in results], dtype=float)
    errs: Counter = Counter()
    for r, _ in results:
        for rung, msg in r["errors"].items():
            errs[f"{rung}: {msg.split(':')[0]}"] += 1
    _log(f"  {v.variant_id} {docs.cell_id(years, threshold)}: {n} histories, undefined {dict(errs)}")
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **arrays)
    return docs.CellResult(years, threshold, first, arrays, {"counts": dict(errs)})


def _semantic(doc: dict[str, Any]) -> None:
    from ...core.schemas import REPO_ROOT

    tests_dir = str(REPO_ROOT / "tests" / "contracts_u12")
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)
    import c17_semantic

    found = c17_semantic.semantic_findings(doc)
    if found:
        raise ValueError("the C17 document fails the semantic gate: " + "; ".join(found[:6]))


def build(seed: int, scale: float = 1.0, *, log: bool = False, workers: int | None = None, cache_dir: Path | None = None,
          tail_indices: tuple[float, ...] | None = None) -> dict[str, Any]:
    """Every document of the case in memory: ``{"models": doc, "variants": {id: doc}, "values": {...}, "cells": ..., "plan": ...}``.

    ``tail_indices`` restricts the variants (the tests use it); the models document needs all four and is ``None`` for a subset."""
    say = _log if log else (lambda _m: None)
    pl = plan(seed, scale)
    workers = workers if workers is not None else int(os.environ.get("C17_WORKERS", min(8, os.cpu_count() or 1)))
    key = hashlib.sha256(f"{seed}-{pl}-{source_hash()}".encode()).hexdigest()[:12]
    rv = docs.rv_version()
    bank = bank_business_indicator()
    vs = [v for v in variants() if tail_indices is None or v.tail_index in tail_indices]
    truths: dict[float, truth.Truth] = {}
    variant_docs: dict[str, dict[str, Any]] = {}
    cells_by_variant: dict[str, list[docs.CellResult]] = {}
    bench = extras.benchmark_row()
    say(f"benchmark row: light {bench['light']}")
    rejected = 0
    for vi, v in enumerate(vs):
        t = truth.compute(v, pl["mc_truth"])
        truths[v.tail_index] = t
        say(f"{v.variant_id}: true 99.9 percent quantile {t.quantile_eur:,.0f} EUR (step {t.grid_step_eur:,.0f}, MC {t.truth_block['annual_loss_quantile']['mc_check']['value_eur']:,.0f})")
        pts = scenario_points(v)
        priors = {}
        for years in P.YEARS:
            priors[years], pseed = scenario_prior(v, pts, years)
            say(f"{v.variant_id}: scenario prior for {years} years, bootstrap seed {pseed}: alpha mean {priors[years].mean:.3f} "
                f"(true {1 / v.tail_index:.3f}), interval {priors[years].interval[0]:.2f} to {priors[years].interval[1]:.2f}")
        cells = []
        for ci, (years, threshold) in enumerate(P.CELLS):
            first, n = cell_seeds(seed, vi, ci, pl["n_replications"])
            c = run_cell(v, years, float(threshold), first, n, bank["bi_eur"], priors[years], pl["mc_rep"], pl["check_contract"], workers,
                         cache_dir / CASE_ID if cache_dir else None, key)
            rejected += int(c.arrays["rejected"].sum())
            cells.append(c)
        cells_by_variant[v.variant_id] = cells
        by_id = {c.id: c for c in cells}
        rc, sc = by_id[P.RESPONSE_CELL], by_id[P.SCENARIO_CELL]
        response = extras.sma_response(v, rc.seed_first, rc.years, rc.threshold, bank)
        scenario = extras.scenario_influence(v, sc.seed_first, sc.years, sc.threshold, pts)
        outputs, tests, impact, findings = docs.variant_document(v, t, bank, cells, response, scenario, bench, rv)
        doc = build_artifact(case_id=CASE_ID, variant_id=v.variant_id, model=docs.model_summaries(rv), outputs=outputs, tests=tests, impact=impact,
                             findings=findings, lineage=_lineage(seed, rv), lane={"lane": "precompute", "reasons": []})
        _semantic(doc)
        variant_docs[v.variant_id] = doc
        say(f"{v.variant_id}: document built")
    models_doc = None
    if len(vs) == len(P.TAIL_INDICES):
        models = docs.models_document(vs, truths, seed_base(seed), pl["n_replications"], pl["mc_truth"], pl["mc_rep"], rv)
        models_doc = build_models_artifact(case_id=CASE_ID, fit_id=models["fit_id"], model=models["model"], fit=models["fit"],
                                           lineage=_lineage(seed, rv), lane={"lane": "precompute", "reasons": []})
        _semantic(models_doc)
    values = {
        "calibration_max_abs_log_error": max(v.max_abs_log_error for v in vs),
        "frequency_above_20000_per_year": min(expected_count_above(v, 20_000.0) for v in vs),
        **{f"true_quantile_{v.variant_id.replace('-', '_')}_eur": truths[v.tail_index].quantile_eur for v in vs},
        "bank_bic_eur": bank["bic_eur"],
        "mc_checks_agree": float(all(t.truth_block["annual_loss_quantile"]["mc_check"]["agrees"] for t in truths.values())),
        "history_rows_rejected_by_contract_1": float(rejected),
    }
    return {"models": models_doc, "variants": variant_docs, "values": values, "cells": cells_by_variant, "plan": pl, "truths": truths, "bank": bank}


def _lineage(seed: int, rv: str) -> lin.Lineage:
    return lin.build(CASE_ID, sources=[], truth_status="synthetic-known-truth", seed=seed, code_version=__version__, riskvalidation_version=rv,
                     generators=(P.GENERATOR,))


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def bake_case(seed: int, paths: Any, data_root: Path | None, scale: float, title: dict[str, str], question: dict[str, str]) -> dict[str, Any]:
    cache = Path(data_root) / "cache" if data_root is not None else None
    built = build(seed, scale, log=True, cache_dir=cache)
    entries: list[dict[str, Any]] = []
    sums: list[str] = []
    e = write_artifact(paths.root, MODELS_REL, built["models"], exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
    sums.append(_sum(paths.root, MODELS_REL))
    entries.append({"role": "models", "variant_id": "models-generator", "truth_status": "synthetic-known-truth",
                    "title": docs.T("The loss-history generator: its LDCE calibration, the true annual loss quantiles, the ladder and the SMA",
                                    "El generador de historias de pérdida: su calibración a la LDCE, los cuantiles anuales verdaderos, la escalera y el SMA"),
                    "short_title": docs.T("Models", "Modelos"),
                    "regime": docs.T("The synthetic bank, the four tail indices with their true parameters and the engine's ladder",
                                     "El banco sintético, los cuatro índices de cola con sus parámetros verdaderos y la escalera del motor"),
                    "path": MODELS_REL, **e})
    for v in variants():
        vid = v.variant_id
        rel = f"{CASE_ID}/{vid}.json"
        e = write_artifact(paths.root, rel, built["variants"][vid], exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
        sums.append(_sum(paths.root, rel))
        _log(f"variant {vid}: {e['bytes']:,} bytes")
        text = docs.T(f"Tail index {v.tail_index:g}" + (": no finite mean" if v.infinite_mean else ""),
                      f"Índice de cola {docs.es_num(v.tail_index, 'g')}" + (": sin media finita" if v.infinite_mean else ""))
        entries.append({"role": "variant", "variant_id": vid, "title": text, "short_title": docs.T(f"xi {v.tail_index:g}", f"xi {docs.es_num(v.tail_index, 'g')}"),
                        "regime": text, "truth_status": "synthetic-known-truth", "models_ref": MODELS_REL, **e})
    (Path(paths.root) / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built["values"])
    manifest = build_case_manifest(
        case_id=CASE_ID, title=title, category={"en": "Operational risk", "es": "Riesgo operacional"}, question=question, sources=[], seed=seed,
        variants=entries, default_variant=DEFAULT_VARIANT, contract={}, expect=ranges, riskvalidation_version=docs.rv_version(), source_details={})
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest
