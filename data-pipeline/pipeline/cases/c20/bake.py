"""The C20 bake: six variants on a locked holdout with synthetic shifts on the evaluation set only, and the models document.

``build`` makes every document in memory (it reads the raw files of the device data root, which ``fetch`` and ``data-pipeline/fetch.py``
wrote); ``bake_case`` writes them with the checksums, the raw-source record and the manifest. The documents are the c20-outputs,
c20-outputs-shift, c20-outputs-seeds, c20-outputs-perturbation, c20-outputs-leakage and c20-models contracts
(docs/contracts/schemas/c20/). Every document passes its schema and ``tests/contracts_u14/semantics.py::check_c20`` before it is written,
and every result row passes ``common/test-result``. A source that is not in the data root stops the variants that need it: they are named
with the URL and nothing is written for them.
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

from ... import __version__
from ...core import expect as expectations
from ...core import lineage as lin
from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ...core.schemas import validate_document
from ...io import fetch as fetching
from ...io import sources as registry
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import data, fed, fetch, fits, models, ops, sgcd, v_leak, v_perturb, v_seeds, v_shift, v_shock
from .conv import CASE_ID, SEED, impact_cutoff, t  # noqa: F401

SOURCES = ("santanderai-sgcd", "uci-taiwan", "uci-polish", "fed-stress-tests")
FIT_ID = "c20-ladder"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"
ENGINES = {"numpy", "scipy", "scikit-learn", "optbinning", "statsmodels", "interpret", "lightgbm", "xgboost", "shap", "riskvalidation"}
RUN_MS = 1_800_000.0
EXACT = frozenset({"outputs", "fit", "tests"})
VARIANTS = ("sgcd-seen", "sgcd-held-out", "fed-shift", "seed-sweep", "perturbation-grid", "leakage-planted")
TRUTH = {"sgcd-seen": "synthetic-known-truth", "sgcd-held-out": "synthetic-known-truth", "fed-shift": "synthetic-known-truth",
         "seed-sweep": "real-outcomes", "perturbation-grid": "synthetic-known-truth", "leakage-planted": "synthetic-known-truth"}
NEEDS = {"sgcd-seen": ("santanderai-sgcd",), "sgcd-held-out": ("santanderai-sgcd",), "fed-shift": ("fed-stress-tests",),
         "seed-sweep": (), "perturbation-grid": (), "leakage-planted": ()}
#: declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT = {
    "auc_holdout_taiwan_P4-lightgbm": (0.74, 0.82), "auc_holdout_german-sgcd_P4-lightgbm": (0.62, 0.86),
    "auc_holdout_polish_P4-lightgbm": (0.80, 0.97), "leak_development_auc": (0.97, 1.0), "leak_caught": (1.0, 1.0),
    "seed_auc_sd_P4-lightgbm": (0.0, 0.01), "fed_rating_anchor_psi": (0.3, 3.0), "conformal_baseline_coverage": (0.85, 0.95),
}
TITLES = {
    "sgcd-seen": (t("SGCD shocks the model has seen (F1 and F2)", "Choques de SGCD que el modelo ha visto (F1 y F2)"), t("SGCD seen", "SGCD vistos"),
                  t("Test batches T1 to T3 of the stressed German credit data: the shipped shocks and Contraste's own application of each family to the structured view.",
                    "Lotes de prueba T1 a T3 de los datos de credito aleman estresados: los choques entregados y la aplicacion propia de Contraste de cada familia a la vista estructurada.")),
    "sgcd-held-out": (t("SGCD shocks the model has not seen (F4)", "Choques de SGCD que el modelo no ha visto (F4)"), t("SGCD held out", "SGCD no vistos"),
                      t("Test batches T4 to T6: the contradiction shock held out of the protocol's adaptation phase.",
                        "Lotes de prueba T4 a T6: el choque de contradiccion reservado fuera de la fase de adaptacion del protocolo.")),
    "fed-shift": (t("Fed corporate shift probes", "Sondas de desplazamiento corporativas de la Fed"), t("Fed shift", "Desplazamiento Fed"),
                  t("The three Fed 2025 corporate portfolios read as real drift with no model and as the size of a synthetic shift on the Polish evaluation set.",
                    "Las tres carteras corporativas 2025 de la Fed leidas como deriva real sin modelo y como el tamano de un desplazamiento sintetico sobre el conjunto de evaluacion polaco.")),
    "seed-sweep": (t("Seed sweep and reason-code stability", "Barrido de semillas y estabilidad de codigos de razon"), t("Seeds", "Semillas"),
                   t("The boosted Taiwan rungs refitted across 20 seeds and 100 bootstrap refits.", "Las etapas potenciadas de Taiwan reajustadas con 20 semillas y 100 remuestreos.")),
    "perturbation-grid": (t("Perturbation grid", "Grilla de perturbacion"), t("Noise", "Ruido"),
                          t("Performance of the Taiwan model against Gaussian input noise on the locked holdout.", "Desempeno del modelo de Taiwan frente a ruido gaussiano de entrada en la muestra reservada.")),
    "leakage-planted": (t("Planted leakage", "Fuga plantada"), t("Leakage", "Fuga"),
                        t("A leaking feature planted in the Taiwan training set, caught by the leakage screen while performance collapses at decision time.",
                          "Una variable filtrada plantada en el entrenamiento de Taiwan, detectada por la prueba de fuga mientras el desempeno colapsa al decidir.")),
}
_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C20 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Built:
    models: dict[str, Any] | None
    variants: dict[str, dict[str, Any]]
    values: dict[str, float]
    raw_sources: dict[str, Any]
    contract: dict[str, Any]
    blocked: list[dict[str, Any]] = field(default_factory=list)
    order: list[str] = field(default_factory=list)


def engine_version() -> str:
    try:
        ver = md.version("riskvalidation")
    except md.PackageNotFoundError:
        ver = "not installed"
    req = (Path(__file__).resolve().parents[4] / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = re.search(r"CAOS_RiskValidation\.git@([0-9a-f]{40})", req)
    return f"{ver}+{m.group(1)[:7]}" if m else ver


def _semantics():
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
    """The cross-field checks of the producer (a non-empty list refuses the document) and the schema of every engine row."""
    found = list(_semantics().check_c20(doc))
    cs = _contract_schemas()
    for r in doc.get("tests", []):
        found += [f"test row {r.get('test_id')}: {e}" for e in cs.errors("common/test-result", r)]
    return found


def _contract_schemas():
    from ...core.schemas import _cs

    return _cs()


def _files(data_root: Path, source: str) -> list[dict[str, str]]:
    """The hashed files a document derives from, per source (UCI from the licence manifest, SGCD and Fed from their sidecars)."""
    if source in (fetch.SGCD_ID, fetch.FED_ID):
        rows = fetch.load_provenance(data_root, source)
        return [{"name": r["name"], "sha256": r["sha256"]} for r in rows]
    man = fetching.load_manifest()["sources"].get(source, {"files": []})
    return [{"name": f["name"], "sha256": f["sha256"]} for f in man["files"]]


def _lineage(data_root: Path, sources: list[str], truth: str, seed: int, ev: str) -> lin.Lineage:
    manifest = {"sources": {s: {"files": _files(data_root, s)} for s in sources}}
    gens = () if truth == "real-outcomes" else ("contraste:c20-synthetic-shifts",)
    return lin.build(CASE_ID, sources=sources, truth_status=truth, seed=seed, code_version=__version__, riskvalidation_version=ev,
                     generators=gens, manifest=manifest)


def _summary_models(frame_name: str, ids: list[str], rungs_by_frame: dict[str, dict[str, Any]], frames: dict[str, data.Frame]) -> list[dict[str, Any]]:
    recs = {r["id"]: r for r in models.records(frames[frame_name], rungs_by_frame[frame_name])}
    out = []
    for i in ids:
        r = {k: v for k, v in recs[i].items() if k != "details"}
        out.append(r)
    return out


def build(seed: int, data_root: Path | str | None, *, only: tuple[str, ...] | None = None, max_rows: int | None = None) -> Built:
    """Every document of the case in memory. A variant whose source is not in the data root is blocked, not built. ``max_rows`` keeps a
    stratified subsample of the Taiwan file for the tests; the SGCD, Polish and Fed files are read whole."""
    if data_root is None:
        raise FileNotFoundError("C20 reads the raw files of the device data root: pass --data-root or set CONTRASTE_DATA")
    root = Path(data_root)
    wanted = [v for v in VARIANTS if only is None or v in only]
    blocked = []
    for m in fetch.missing_for(root):
        stopped = [v for v in m["variants"] if v in wanted]
        if stopped:
            blocked.append({"source": m["source"], "variants": stopped, "urls": m["urls"]})
            _log(f"{m['source']} is not in the data root: {', '.join(stopped)} blocked ({'; '.join(m['urls'])}); nothing is written for them")
    stopped_all = {v for b in blocked for v in b["variants"]}
    todo = [v for v in wanted if v not in stopped_all]
    if not todo:
        raise FileNotFoundError("C20: nothing to build: " + "; ".join(f"{b['source']} blocks {b['variants']} ({', '.join(b['urls'])})" for b in blocked))
    ev = engine_version()
    frames: dict[str, data.Frame] = {}
    rungs: dict[str, dict[str, Any]] = {}
    ds = codebook = None
    need_german = any(v in todo for v in ("sgcd-seen", "sgcd-held-out"))
    need_polish = "fed-shift" in todo
    need_taiwan = any(v in todo for v in ("seed-sweep", "perturbation-grid", "leakage-planted"))
    if need_german:
        sg = root / "raw" / fetch.SGCD_ID
        fetch.load_provenance(root, fetch.SGCD_ID)
        ds = sgcd.read_dataset(sg / "SGCDataset.jsonl", sg / "SGCDataset_metadata.json")
        codebook = sgcd.read_codebook(sg / "codebook.md")
        frames["german-sgcd"] = data.load_sgcd(root, seed, ds)
    if need_polish:
        frames["polish"] = data.load_polish(root, seed)        # the whole file: the scorecard needs the events of a 3-year file to be fitted
    if need_taiwan:
        frames["taiwan"] = data.load_taiwan(root, seed, max_rows)
    for name, frame in frames.items():
        _log(f"{name}: {len(frame.X)} rows, train {len(frame.train)}, calibration {len(frame.cal)}, holdout {len(frame.hold)}")
        rungs[name] = fits.fit_rungs(frame, seed, with_xgboost=name == "taiwan", log=_log)
    portfolios: dict[str, fed.Portfolio] = {}
    if "fed-shift" in todo:
        fetch.load_provenance(root, fetch.FED_ID)
        for name, file in fetch.FED_FILES:
            portfolios[name] = fed.read_portfolio(fetch.path_of(root, fetch.FED_ID, file), name)
    values: dict[str, float] = {}
    for name, frame in frames.items():
        Xh, yh = frame.part("hold")
        values[f"auc_holdout_{name}_P4-lightgbm"] = ops.auc_brier(rungs[name]["P4-lightgbm"].pd(Xh), yh)[0]
    parts: dict[str, dict[str, Any]] = {}
    for v in todo:
        _log(f"variant {v}")
        if v in ("sgcd-seen", "sgcd-held-out"):
            parts[v] = v_shock.build(frames["german-sgcd"], rungs["german-sgcd"], ds, codebook, "seen" if v == "sgcd-seen" else "held-out")
        elif v == "fed-shift":
            parts[v] = v_shift.build(frames["polish"], rungs["polish"], portfolios, seed)
            values["fed_rating_anchor_psi"] = float(parts[v]["anchor_psi"])
            values["conformal_baseline_coverage"] = float(parts[v]["outputs"]["synthetic_shift"]["label_free"]["conformal"]["coverage_by_window"][0]["coverage"])
        elif v == "seed-sweep":
            parts[v] = v_seeds.build(frames["taiwan"], rungs["taiwan"], seed)
            values["seed_auc_sd_P4-lightgbm"] = float(parts[v]["outputs"]["rows"][0]["auc"]["sd"])
        elif v == "perturbation-grid":
            parts[v] = v_perturb.build(frames["taiwan"], rungs["taiwan"], seed)
        else:
            parts[v] = v_leak.build(frames["taiwan"], rungs["taiwan"], seed)
            values["leak_development_auc"] = float(parts[v]["outputs"]["performance"]["development_auc"])
            values["leak_caught"] = 1.0 if parts[v]["outputs"]["caught"] else 0.0
    lane = {"lane": "precompute", "reasons": []}
    docs: dict[str, dict[str, Any]] = {}
    src_of = {"sgcd-seen": ["santanderai-sgcd"], "sgcd-held-out": ["santanderai-sgcd"], "fed-shift": ["uci-polish", "fed-stress-tests"],
              "seed-sweep": ["uci-taiwan"], "perturbation-grid": ["uci-taiwan"], "leakage-planted": ["uci-taiwan"]}
    frame_of = {"sgcd-seen": "german-sgcd", "sgcd-held-out": "german-sgcd", "fed-shift": "polish", "seed-sweep": "taiwan",
                "perturbation-grid": "taiwan", "leakage-planted": "taiwan"}
    for v in todo:
        p = parts[v]
        fn = frame_of[v]
        ids = p["models"]
        recs = _summary_models(fn, [i for i in ids if i.endswith(fn)], rungs, frames)
        if v == "leakage-planted":
            leaky = p["leaky"]
            rec = leaky.record()
            recs = [{k: val for k, val in {**rec, "id": ids[0], "family": "ml"}.items() if k != "details"}, *recs]
        tests = p["tests"]
        findings = ops.findings(tests, limits=p["limits"], prefix=v)
        # model summaries must be the keys of contract 2 only
        summaries = [{k: r[k] for k in ("id", "family", "rung", "title", "short_title", "engine", "engine_version", "licence", "calibration",
                                         "parameters", "checkpoint_sha256")} for r in recs]
        used = {t_["model_id"] for t_ in tests if t_.get("model_id")}
        summaries = [s for s in summaries if s["id"] in used or s["id"] in ids]
        doc = build_artifact(case_id=CASE_ID, variant_id=v, model=summaries, outputs=p["outputs"], tests=tests, impact=p["impact"],
                             findings=findings, lineage=_lineage(root, src_of[v], TRUTH[v], seed, ev), lane=lane)
        docs[v] = doc
    fit_models = []
    for name in frames:
        fit_models.extend(models.records(frames[name], rungs[name]))
    fed_rows = sum(p.n for p in portfolios.values()) if portfolios else None
    mdoc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=fit_models, fit=models.fit_block(frames, rungs, fed_rows),
                                 lineage=_lineage(root, [s for s in SOURCES if _present(root, s, todo)], "synthetic-known-truth", seed, ev),
                                 lane=lane)
    reg = registry.load()
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The rows of data/sources/manifest.json for the raw inputs of C20 that no shared fetch pins (the SGCD files at commit 8403fa9 and the "
                           "three Fed 2025 corporate portfolios), in that file's format. The UCI files are already pinned there. The raw files stay in the device "
                           "data root (outside the repository); each file record is the one written when it was fetched, and the bake refuses a file whose bytes "
                           "differ from it.",
                   "sources": {}}
    for sid in (fetch.SGCD_ID, fetch.FED_ID):
        if _present(root, sid, todo):
            raw_sources["sources"][sid] = {"name": reg[sid].name, "publisher": reg[sid].publisher, "landing": reg[sid].landing, "class": reg[sid].klass,
                                           "licence": reg[sid].licence, "attribution": reg[sid].attribution, "access": reg[sid].access,
                                           "files": fetch.load_provenance(root, sid)}
    contract = {name: frames[name].contract for name in frames}
    contract = {data_source(n): c for n, c in contract.items()}
    return Built(mdoc, docs, values, raw_sources, contract, blocked, todo)


def data_source(frame_name: str) -> str:
    return {"german-sgcd": "santanderai-sgcd", "taiwan": "uci-taiwan", "polish": "uci-polish"}[frame_name]


def _present(root: Path, source: str, todo: list[str]) -> bool:
    if source == "santanderai-sgcd":
        return any(v in todo for v in ("sgcd-seen", "sgcd-held-out"))
    if source == "fed-stress-tests":
        return "fed-shift" in todo
    if source == "uci-polish":
        return "fed-shift" in todo
    if source == "uci-taiwan":
        return any(v in todo for v in ("seed-sweep", "perturbation-grid", "leakage-planted"))
    return False


def _check_and_write(root: Path, rel: str, doc: dict[str, Any]) -> dict[str, Any]:
    """Schema, then the semantic checks and the test-result schema of every row, then the write; any finding refuses the document."""
    validate_document(f"data/derived/{rel}", doc)
    if "kind" in doc.get("outputs", {}):
        found = check(doc)
        if found:
            raise ValueError(f"{rel}: check_c20 refuses the document: {found[:5]}")
    return write_artifact(root, rel, doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def _source_details(ids: list[str]) -> dict[str, dict[str, str]]:
    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


def bake_case(seed: int, paths: Any, data_root: Path | str | None, *, only: tuple[str, ...] | None = None, max_rows: int | None = None) -> dict[str, Any]:
    built = build(seed, data_root, only=only, max_rows=max_rows)
    root = Path(paths.root)
    entries, sums = [], []
    e = _check_and_write(root, MODELS_REL, built.models)
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "synthetic-known-truth",
                    "title": t("Fitted ladders: German as carried by SGCD, Taiwan and Polish", "Escaleras ajustadas: aleman segun SGCD, Taiwan y polaco"),
                    "short_title": t("Models", "Modelos"),
                    "regime": t("The C01 ladder rungs fitted on each dataset of C20, with the fit sizes and the named parameters.",
                                "Las etapas de la escalera de C01 ajustadas en cada conjunto de C20, con los tamanos de ajuste y los parametros con nombre."),
                    "path": MODELS_REL, **e})
    for vid in built.order:
        doc = built.variants[vid]
        rel = f"{CASE_ID}/{vid}.json"
        e = _check_and_write(root, rel, doc)
        sums.append(_sum(root, rel))
        title, short, regime = TITLES[vid]
        entries.append({"role": "variant", "variant_id": vid, "truth_status": TRUTH[vid], "title": title, "short_title": short, "regime": regime,
                        "models_ref": MODELS_REL, "path": rel, **e})
        _log(f"{vid}: {e['bytes']:,} bytes")
    write_json(root / RAW_REL, built.raw_sources)
    sums.append(_sum(root, RAW_REL))
    (root / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    # a subsample run (the tests) is not the release bake: its ranges are the unit interval
    wide = {k: (EXPECT[k] if max_rows is None else (-1e9, 1e9)) for k in built.values if k in EXPECT}
    ranges = expectations.check(CASE_ID, wide, built.values)
    used = [s for s in SOURCES if _present(Path(data_root), s, built.order)]
    from . import CASE

    manifest = build_case_manifest(
        case_id=CASE_ID, title=dict(CASE.title), category={"en": "ML and AI model risk", "es": "Riesgo de modelos de ML e IA"},
        question=dict(CASE.question), sources=used, seed=seed, variants=entries, default_variant=built.order[0], contract=built.contract,
        expect=ranges, riskvalidation_version=engine_version(), source_details=_source_details(used))
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest
