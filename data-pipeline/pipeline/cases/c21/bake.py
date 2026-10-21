"""The C21 bake: HMDA decisions of Delaware, the six year pairs 2018-19 to 2023-24, each fitted on year t and confirmed on t + 1.

``build`` makes every document in memory (it reads the raw files of the device data root, which ``fetch`` wrote); ``bake_case`` writes
them with the checksums, the raw-source record and the manifest. The documents are the c21-outputs and c21-models contracts
(docs/contracts/schemas/c21/). Every document passes the schema and ``tests/contracts_u14/semantics.py::check_c21`` before it is
written. The findings are statistical findings about each document's own test rows (``findings.py``, decision G16). A year that is
not in the data root stops the pairs that need it: they are named with the URL and nothing is written for them.
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
from ...io import sources as registry
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import estimates as est
from . import fetch, findings, legal, models, reader
from .legal import t

CASE_ID = "C21"
SOURCES = ("hmda",)
FIT_ID = "hmda-de-2018-2023"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 600_000.0
#: the measured results are exact in the documents: their identities close to 1e-9 and rounding to nine digits would only add noise
EXACT = frozenset({"outputs", "fit", "tests"})
REQUIREMENTS = [f"CT-21{n:02d}" for n in range(1, 23)]

#: what a reader should see, declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT_APPROVAL = (0.55, 0.95)   # approvals over decisions, Delaware, any year
EXPECT_PARITY = (0.50, 1.20)     # Black or African American over White, parity ratio, any year

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C21 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def variant_id(pair_id: str) -> str:
    return f"pair-{pair_id}"


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
    """The engine version with the commit that pins it (requirements.txt), so the document names the code that computed it."""
    try:
        ver = md.version("riskvalidation")
    except md.PackageNotFoundError:
        ver = "not installed"
    req = (Path(__file__).resolve().parents[4] / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = re.search(r"CAOS_RiskValidation\.git@([0-9a-f]{40})", req)
    return f"{ver}+{m.group(1)[:7]}" if m else ver


def model_summaries(ev: str, k: int) -> list[dict[str, Any]]:
    def rec(mid: str, rung: str, en: str, es: str, params: dict[str, tuple[float, str]]) -> dict[str, Any]:
        return {"id": mid, "family": "fairness", "rung": rung, "title": t(en, es), "short_title": t(en.split(",")[0], es.split(",")[0]),
                "engine": "riskvalidation", "engine_version": ev, "licence": "MIT", "calibration": None,
                "parameters": {n: {"value": v, "unit": u} for n, (v, u) in params.items()}, "checkpoint_sha256": None}

    return [
        rec(est.MODEL_RATES, "selection-rates", "Selection rates by group, with the z-test and the Fisher exact test",
            "Tasas de selección por grupo, con la prueba z y la prueba exacta de Fisher", {"interval_level": (est.LEVEL, "probability")}),
        rec(est.MODEL_LOGIT, "logistic-decision-model", "Logistic decision model with the permitted controls",
            "Modelo logístico de decisión con los controles permitidos", {"interval_level": (est.LEVEL, "probability")}),
        rec(est.MODEL_OLS, "linear-rate-spread", "Linear rate-spread model with the permitted controls",
            "Modelo lineal del diferencial de tasa con los controles permitidos", {"interval_level": (est.LEVEL, "probability")}),
        rec(est.MODEL_SITUATION, "situation-testing", "Situation testing, ceteris paribus comparator",
            "Prueba de situación, comparador ceteris paribus",
            {"k": (float(k), "neighbours"), "alpha": (0.05, "probability"), "tau": (0.0, "share")}),
    ]


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
    return list(_semantics().check_c21(doc))


def _lineage(prov: list[dict[str, Any]], years: set[int], seed: int, ev: str) -> lin.Lineage:
    files = [{"name": r["name"], "sha256": r["sha256"]} for r in prov if fetch.year_of(r) in years]
    return lin.build(CASE_ID, sources=list(SOURCES), truth_status="real-outcomes", seed=seed, code_version=__version__,
                     riskvalidation_version=ev, manifest={"sources": {"hmda": {"files": files}}})


def build(seed: int, data_root: Path | str | None, *, k: int = est.SITUATION_K, only: tuple[str, ...] | None = None) -> Built:
    """Every document of the case in memory. A pair whose year is not in the data root is blocked, not built."""
    if data_root is None:
        raise FileNotFoundError("C21 reads the raw HMDA files of the device data root: pass --data-root or set CONTRASTE_DATA")
    prov = fetch.load_provenance(data_root)
    by_year = {fetch.year_of(r): r for r in prov}
    ok_pairs, blocked = fetch.pairs_status(by_year)
    for b in blocked:
        _log(f"pair {b['pair_id']} blocked: no file for {b['missing_years']} ({'; '.join(b['urls'])}); nothing is written for it")
    if only is not None:
        ok_pairs = [p for p in ok_pairs if variant_id(p[0]) in only]
    if not ok_pairs:
        raise FileNotFoundError("C21: no year pair has both of its years in the data root: " + "; ".join(
            f"{b['pair_id']} needs {b['missing_years']} ({', '.join(b['urls'])})" for b in blocked))
    raw = Path(data_root) / "raw" / fetch.HMDA_DIR
    needed = sorted({y for _, a, b in ok_pairs for y in (a, b)})
    rows: dict[int, reader.YearRows] = {}
    samples: dict[int, reader.Sample] = {}
    designs: dict[int, est.Design] = {}
    for y in needed:
        rows[y] = reader.read_year(raw / by_year[y]["name"], y)
        samples[y] = reader.to_sample(rows[y])
        designs[y] = est.build_design(samples[y])
        _log(f"{y}: {rows[y].n_file_rows} rows, {len(samples[y])} decisions")
    report = reader.validate_contract([rows[y] for y in needed])
    if report.rejected or not report.ok:
        raise ValueError(f"C21: contract 1 rejects the reader's output: {report.counts()}; {report.examples(3)}")
    ev = engine_version()
    lane = {"lane": "precompute", "reasons": []}
    docs: dict[str, dict[str, Any]] = {}
    fits: list[dict[str, Any]] = []
    values: dict[str, float] = {}
    for pid, a, b in ok_pairs:
        fs, cs, fd, cd = samples[a], samples[b], designs[a], designs[b]
        attrs, tests = [], []
        for f in legal.ATTRIBUTES:
            why = est.not_evaluated(f, fs)
            if why is not None:
                _log(f"{pid}: {f} {why['en']}")
                continue
            res = est.attribute_result(f, fs, fd, cs, cd)
            attrs.append(res.block)
            tests.extend(res.tests)
            fits.extend(res.fits)
        sit, sit_test = est.situation_result(fs, fd, k)
        tests.append(sit_test)
        outputs = {
            "kind": "year-pair", "pair_id": pid, "fit_year": a, "confirm_year": b,
            "scope": {"state": reader.STATE, "source": fetch.SOURCE_ID, "rows_fit": len(fs), "rows_confirm": len(cs)},
            "legal": legal.legal_block(), "licence": legal.licence_block(), "conventions": legal.conventions_block(),
            "attributes": attrs, "situation_testing": sit, "data_notes": est.data_notes(fs, rows[a].action_counts),
            "requirements": REQUIREMENTS}
        test_rows = [r.to_dict() for r in tests]
        doc = build_artifact(case_id=CASE_ID, variant_id=variant_id(pid), model=model_summaries(ev, k), outputs=outputs,
                             tests=test_rows, impact={}, findings=findings.build(test_rows), lineage=_lineage(prov, {a, b}, seed, ev), lane=lane)
        docs[variant_id(pid)] = doc
        values[f"approval_rate_{a}"] = float(fs.decision.mean())
        race = next(x for x in attrs if x["field"] == "derived_race")
        bw = next((c for c in race["contrasts"] if c["group"] == "Black or African American"), None)
        if bw is not None and bw["parity_ratio"] is not None:
            values[f"black_over_white_parity_ratio_{a}"] = float(bw["parity_ratio"])
        _log(f"{pid}: {len(tests)} test rows, situation {sit['n_significant']} of {sit['n_complainants']}")
    fit_years = {a for _, a, _ in ok_pairs}
    notes = est.data_notes()
    fit_doc = models.fit_document(fits, notes)
    records = []
    for rec in model_summaries(ev, k):
        rec = dict(rec)
        rec["details"] = {"fit_years": sorted(fit_years)}
        records.append(rec)
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=records, fit=fit_doc, lineage=_lineage(prov, fit_years, seed, ev),
                                       lane=lane)
    reg = registry.load()
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The row of data/sources/manifest.json for the raw inputs of C21, in that file's format. The raw files stay in the "
                           "device data root (outside the repository); each file record is the one written when it was fetched, and the bake "
                           "refuses a file whose bytes differ from it.",
                   "sources": {"hmda": {"name": reg["hmda"].name, "publisher": reg["hmda"].publisher, "landing": reg["hmda"].landing,
                                        "class": reg["hmda"].klass, "licence": reg["hmda"].licence, "attribution": reg["hmda"].attribution,
                                        "access": reg["hmda"].access, "files": sorted(prov, key=fetch.year_of)}}}
    return Built(models_doc, docs, values, raw_sources, report.summary(), blocked, [variant_id(p[0]) for p in ok_pairs])


def _check_and_write(root: Path, rel: str, doc: dict[str, Any]) -> dict[str, Any]:
    """Schema, then the semantic checks, then the write; any finding refuses the document."""
    validate_document(f"data/derived/{rel}", doc)
    if doc.get("case_id") == CASE_ID and "pair_id" in doc.get("outputs", {}):
        found = check(doc)
        if found:
            raise ValueError(f"{rel}: check_c21 refuses the document: {found[:5]}")
    return write_artifact(root, rel, doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def _source_details() -> dict[str, dict[str, str]]:
    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in SOURCES}


def bake_case(seed: int, paths: Any, data_root: Path | str | None) -> dict[str, Any]:
    built = build(seed, data_root)
    root = Path(paths.root)
    entries, sums = [], []
    regime = t("Real public HMDA decisions of Delaware; statistical disparity only, no legal claim.",
               "Decisiones reales del HMDA público de Delaware; solo disparidad estadística, sin afirmación legal.")
    e = _check_and_write(root, MODELS_REL, built.models)
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "real-outcomes",
                    "title": t("Fitted decision models, fit years 2018 to 2023", "Modelos de decisión ajustados, años de ajuste 2018 a 2023"),
                    "short_title": t("Models", "Modelos"), "regime": regime, "path": MODELS_REL, **e})
    for vid in built.order:
        doc = built.variants[vid]
        rel = f"{CASE_ID}/{vid}.json"
        e = _check_and_write(root, rel, doc)
        sums.append(_sum(root, rel))
        o = doc["outputs"]
        entries.append({"role": "variant", "variant_id": vid, "truth_status": "real-outcomes",
                        "title": t(f"Fitted on {o['fit_year']}, confirmed on {o['confirm_year']}", f"Ajustado en {o['fit_year']}, confirmado en {o['confirm_year']}"),
                        "short_title": t(o["pair_id"], o["pair_id"]), "regime": regime, "models_ref": MODELS_REL, **e})
        _log(f"{vid}: {e['bytes']:,} bytes")
    write_json(root / RAW_REL, built.raw_sources)
    sums.append(_sum(root, RAW_REL))
    (root / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, expect_ranges(built.values), built.values)
    manifest = build_case_manifest(
        case_id=CASE_ID, title=_title(), category={"en": "ML and AI model risk", "es": "Riesgo de modelos de ML e IA"}, question=_question(),
        sources=list(SOURCES), seed=seed, variants=entries, default_variant=built.order[-1], contract={"hmda": built.contract},
        expect=ranges, riskvalidation_version=engine_version(), source_details=_source_details())
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest


def expect_ranges(values: dict[str, float]) -> dict[str, tuple[float, float]]:
    return {k: (EXPECT_APPROVAL if k.startswith("approval_rate_") else EXPECT_PARITY) for k in values}


def _title() -> dict[str, str]:
    from . import CASE

    return dict(CASE.title)


def _question() -> dict[str, str]:
    from . import CASE

    return dict(CASE.question)
