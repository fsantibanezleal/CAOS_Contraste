"""The C02 bake: the five Polish horizon files and the pooled variant, each with a locked holdout and the C01 ladder.

``build`` makes every document in memory (it reads the raw zip of the device data root and fetches it first when it is absent);
``bake_case`` writes them with the checksums, the raw-source record and the manifest. The documents are the c02-outputs and c02-models
contracts (docs/contracts/schemas/c02/). Every document passes the schema and ``tests/contracts_u14/semantics.py::check_c02`` before
it is written. Every statistic is computed by ``riskvalidation`` (``battery``, ``blocks``).
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import importlib.util
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ... import __version__
from ...core import expect as expectations
from ...core import lineage as lin
from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ...core.schemas import validate_document
from ...io import fetch as fetching
from ...io import sources as registry
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import battery, blocks, findings, models, reader
from . import conventions as cv
from .fits import Fit, build_fits

CASE_ID = "C02"
SOURCES = (cv.SOURCE_ID,)
FIT_ID = "polish-horizons"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"
ENGINES = {"numpy", "scipy", "scikit-learn", "optbinning", "statsmodels", "interpret", "lightgbm", "xgboost", "riskvalidation"}
RUN_MS = 600_000.0
#: the measured results are exact in the documents: their identities close to 1e-9 and rounding to nine digits would only add noise
EXACT = frozenset({"outputs", "fit", "tests"})
REQUIREMENTS = [f"CT-02{n:02d}" for n in range(1, 19)]
VARIANT_IDS = ("h1", "h2", "h3", "h4", "h5", cv.POOLED)

#: what a reader should see, declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT_RATE = (0.01, 0.30)       # bankruptcy rate of a file (the five files: 3.9 to 6.9 percent)
EXPECT_AUC = (0.55, 1.0)         # a PD model that ranks better than chance on a holdout
EXPECT_GAP = (-0.10, 0.45)       # train minus holdout AUC

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C02 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Built:
    models: dict[str, Any]
    variants: dict[str, dict[str, Any]]
    values: dict[str, float]
    raw_sources: dict[str, Any]
    contract: dict[str, Any]
    fits: dict[str, Fit] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)


def engine_version() -> str:
    """The engine version with the commit that pins it (requirements.txt), so the document names the code that computed it."""
    try:
        ver = md.version("riskvalidation")
    except md.PackageNotFoundError:
        ver = "not installed"
    req = (Path(__file__).resolve().parents[4] / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = re.search(r"CAOS_RiskValidation\.git@([0-9a-f]{40})", req)
    return f"{ver}+{m.group(1)[:7]}" if m else ver


def _semantics():
    """tests/contracts_u14/semantics.py, loaded under its own module name (several contract suites ship a ``semantics`` of their own)."""
    name = "u14_semantics"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parents[4] / "tests" / "contracts_u14" / "semantics.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def check(doc: dict[str, Any]) -> list[str]:
    """The cross-field checks of the producer (a non-empty list refuses the document)."""
    return list(_semantics().check_c02(doc))


def _split_block(f: Fit, seed: int) -> dict[str, Any]:
    sp = f.sp
    return {"protocol": "locked-stratified-holdout", "seed": seed, "train_rows": int(len(sp.train)), "calibration_rows": int(len(sp.calibration)),
            "holdout_rows": int(len(sp.holdout)), "holdout_events": int(f.yhold.sum()), "fit_on_training_slice_only": True,
            "calibration_map_on_separate_slice": True, "resampling_before_calibration": False, "out_of_time_claim": False}


def _counts(f: Fit) -> dict[str, Any]:
    rows, events = int(len(f.y)), int(f.y.sum())
    return {"rows": rows, "events": events, "event_rate": events / rows, "features": len(cv.ATTRIBUTES) + (1 if f.years is None else 0),
            "event_definition": cv.event_definition(f.years, f.file) if f.years is not None else cv.POOLED_EVENT}


def _lineage(manifest: dict[str, Any] | None, seed: int, ev: str) -> lin.Lineage:
    return lin.build(CASE_ID, sources=list(SOURCES), truth_status="real-outcomes", seed=seed, code_version=__version__,
                     riskvalidation_version=ev, manifest=manifest)


def build(seed: int, data_root: Path | str | None, *, manifest: dict[str, Any] | None = None, check_counts: bool = True,
          fetcher: Any = None, log: Any = _log) -> Built:
    """Every document of the case in memory. A zip that is absent and that the fetch does not give stops C02, naming the file."""
    if data_root is None:
        raise FileNotFoundError("C02 reads the raw UCI Polish zip of the device data root: pass --data-root or set CONTRASTE_DATA")
    registry.assert_case_inputs(CASE_ID, list(SOURCES))
    zip_path = reader.ensure_zip(data_root, fetcher=fetcher, manifest=manifest)
    horizons = reader.read_horizons(zip_path, check_counts=check_counts)
    report = reader.validate_contract(horizons)
    if report.rejected or not report.ok:
        raise ValueError(f"C02: contract 1 rejects the reader's output: {report.counts()}; {report.examples(3)}")
    log(f"read {sum(h.rows for h in horizons.values()):,} rows in five files; contract 1 flagged {report.counts()['flagged']:,} cells and rows")
    fits = build_fits(horizons, seed, log=log)
    ev = engine_version()
    lane = {"lane": "precompute", "reasons": []}
    lineage = _lineage(manifest, seed, ev)
    # the case-level blocks: the same in every document (the five files are read together)
    hz = [fits[f"h{k}"] for k in range(1, 6)]
    rows_by = {k: int(len(fits[f"h{k}"].y)) for k in range(1, 6)}
    events_by = {k: int(fits[f"h{k}"].y.sum()) for k in range(1, 6)}
    term = blocks.term_structure_block(rows_by, events_by)
    champ_pd = np.array([float(np.mean(f.rungs[cv.CHAMPION].pd(f.Xhold))) for f in hz])
    n_hold = np.array([len(f.yhold) for f in hz])
    d_hold = np.array([int(f.yhold.sum()) for f in hz])
    backtest = blocks.backtest_row(champ_pd, n_hold, d_hold)
    cum = np.array([p["cumulative_pd"] for p in term["points"]])
    detail, impact = blocks.impact_block(cum, "the five file event rates of the term-structure block, read as the cumulative PD of horizons 1 to 5")
    docs: dict[str, dict[str, Any]] = {}
    values: dict[str, float] = {}
    for hid in VARIANT_IDS:
        f = fits[hid]
        csi_max, csi_rows = battery.csi_max_and_rows(f)
        rung_blocks, test_rows, pds = [], [], {}
        for rid in cv.BATTERY_RUNGS:
            block, rows, p = battery.rung_result(f, rid, f"{hid}-{rid}", csi_max)
            rung_blocks.append(block)
            test_rows += rows
            pds[rid] = p
        table, ch_rows = battery.challenger_table(f, hid, pds, seed)
        test_rows += ch_rows + csi_rows + [dict(backtest)]
        pooled = None
        caveat = None
        if hid == cv.POOLED:
            pooled = {"files": [{"file": g.file, "years": g.years, "rows": int(len(g.y)), "events": int(g.y.sum())} for g in hz],
                      "horizon_indicator": True, "overlap": cv.OVERLAP_CAVEAT}
            caveat = cv.OVERLAP_CAVEAT
        outputs = {
            "kind": "horizon", "horizon_id": hid, "years": f.years, "counts": _counts(f), "pooled": pooled, "firm_overlap_caveat": caveat,
            "split": _split_block(f, seed), "rungs": rung_blocks, "challenger": table, "transfer": battery.transfer_block(fits, f),
            "term_structure": term, "impact_detail": detail, "parameters": cv.parameters(), "requirements": REQUIREMENTS}
        doc = build_artifact(case_id=CASE_ID, variant_id=hid, model=models.model_records(f, False, cv.BATTERY_RUNGS), outputs=outputs,
                             tests=test_rows, impact=impact, findings=findings.build(test_rows), lineage=lineage, lane=lane)
        docs[hid] = doc
        values[f"event_rate_{hid}"] = outputs["counts"]["event_rate"]
        for r in rung_blocks:
            rid = r["model_id"].removeprefix(f"{hid}-")
            if rid in (cv.CHAMPION, "P4-lightgbm"):
                values[f"auc_{rid}_{hid}"] = r["discrimination"]["auc"]
            if rid == cv.CHAMPION:
                values[f"overfit_gap_{rid}_{hid}"] = r["overfit"]["gap"]
        log(f"{hid}: {len(test_rows)} test rows, P1 AUC {values[f'auc_{cv.CHAMPION}_{hid}']:.3f}, P4 AUC {values[f'auc_P4-lightgbm_{hid}']:.3f}")
    records: list[dict[str, Any]] = []
    for f in fits.values():
        records += models.model_records(f, True)
    pf = fits[cv.POOLED]
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=records, fit=models.fit_document(fits, _split_block(pf, seed)),
                                       lineage=lineage, lane=lane)
    reg = registry.load()
    man = manifest if manifest is not None else fetching.load_manifest()
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The row of data/sources/manifest.json for the raw input of C02, in that file's format. The raw zip stays in the device "
                           "data root (outside the repository); the bake refuses a zip whose bytes differ from this record.",
                   "sources": {cv.SOURCE_ID: {"name": reg[cv.SOURCE_ID].name, "publisher": reg[cv.SOURCE_ID].publisher,
                                              "landing": reg[cv.SOURCE_ID].landing, "class": reg[cv.SOURCE_ID].klass,
                                              "licence": reg[cv.SOURCE_ID].licence, "attribution": reg[cv.SOURCE_ID].attribution,
                                              "access": reg[cv.SOURCE_ID].access, "files": man["sources"][cv.SOURCE_ID]["files"]}}}
    return Built(models_doc, docs, values, raw_sources, report.summary(), fits, list(VARIANT_IDS))


def _check_and_write(root: Path, rel: str, doc: dict[str, Any]) -> dict[str, Any]:
    """Schema, then the semantic checks, then the write; any finding refuses the document."""
    validate_document(f"data/derived/{rel}", doc)
    if doc.get("case_id") == CASE_ID and "kind" in doc.get("outputs", {}):
        found = check(doc)
        if found:
            raise ValueError(f"{rel}: check_c02 refuses the document: {found[:5]}")
    return write_artifact(root, rel, doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def _source_details() -> dict[str, dict[str, str]]:
    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in SOURCES}


def expect_ranges(values: dict[str, float]) -> dict[str, tuple[float, float]]:
    return {k: (EXPECT_RATE if k.startswith("event_rate_") else EXPECT_GAP if k.startswith("overfit_gap_") else EXPECT_AUC) for k in values}


def bake_case(seed: int, paths: Any, data_root: Path | str | None, *, manifest: dict[str, Any] | None = None,
              check_counts: bool = True, fetcher: Any = None, strict_expect: bool = True) -> dict[str, Any]:
    from . import CASE

    built = build(seed, data_root, manifest=manifest, check_counts=check_counts, fetcher=fetcher)
    root = Path(paths.root)
    refused = [f"{rel}: {m}" for rel, doc in [(f"{CASE_ID}/{v}.json", built.variants[v]) for v in built.order] for m in check(doc)]
    if refused:                                  # every document is checked before one is written: a refusal lists them all
        raise ValueError("check_c02 refuses the documents: " + "; ".join(refused[:10]))
    entries, sums = [], []
    regime = cv.t("Real UCI Polish bankruptcy files; a random stratified holdout per file, undated: no out-of-time claim.",
                  "Archivos reales de quiebra polacos de UCI; una muestra reservada estratificada al azar por archivo, sin fechas: sin reclamo fuera del tiempo.")
    e = _check_and_write(root, MODELS_REL, built.models)
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "real-outcomes",
                    "title": cv.t("Fitted ladder, five horizon files and the pooled variant", "Escalera ajustada, cinco archivos de horizonte y la variante agrupada"),
                    "short_title": cv.t("Models", "Modelos"), "regime": regime, "path": MODELS_REL, **e})
    for vid in built.order:
        doc = built.variants[vid]
        rel = f"{CASE_ID}/{vid}.json"
        e = _check_and_write(root, rel, doc)
        sums.append(_sum(root, rel))
        o = doc["outputs"]
        if vid == cv.POOLED:
            title, short = cv.t("Pooled: the five files stacked", "Agrupada: los cinco archivos apilados"), cv.t("Pooled", "Agrupada")
        else:
            title = cv.t(f"{o['years']}-year file", f"Archivo de {o['years']} año{'s' if o['years'] > 1 else ''}")
            short = cv.t(f"{o['years']} y", f"{o['years']} a")
        entries.append({"role": "variant", "variant_id": vid, "truth_status": "real-outcomes", "title": title, "short_title": short,
                        "regime": regime, "models_ref": MODELS_REL, **e})
        _log(f"{vid}: {e['bytes']:,} bytes")
    write_json(root / RAW_REL, built.raw_sources)
    sums.append(_sum(root, RAW_REL))
    (root / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    # the declared ranges are those of the real files; a planted run (tests) passes strict_expect=False and records the widest range
    wanted = expect_ranges(built.values) if strict_expect else {k: (-1.0, 1.0) for k in built.values}
    ranges = expectations.check(CASE_ID, wanted, built.values)
    manifest_doc = build_case_manifest(
        case_id=CASE_ID, title=dict(CASE.title), category={"en": "Credit scoring", "es": "Scoring de crédito"}, question=dict(CASE.question),
        sources=list(SOURCES), seed=seed, variants=entries, default_variant="h1", contract={cv.SOURCE_ID: built.contract},
        expect=ranges, riskvalidation_version=engine_version(), source_details=_source_details())
    write_json(paths.manifests / f"{CASE_ID}.json", manifest_doc)
    return manifest_doc
