"""The C14 bake: three valuation dates of the failed bank, read up to each date, through ``riskvalidation.irrbb``.

``build`` makes every document in memory (it reads the raw files of the device data root, which ``fetch`` wrote); ``bake_case``
writes them with the checksums, the raw-source record and the manifest. The documents are the c14-outputs and c14-models contracts
(docs/contracts/schemas/c14/). Every document passes the schema and ``tests/contracts_u10/semantics.py::check_document`` before it is
written (decision D3 of the U10 sizing).
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ... import __version__
from ...core import expect as expectations
from ...core import lineage as lin
from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ...core.schemas import validate_document
from ...io import contract as c1
from ...io import sources as registry
from ...io import treasury
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import assumptions as asm
from . import fetch, models
from ...io import fdic
from . import variant as vt
from .slotting import build_items, t

CASE_ID = "C14"
CERT = fetch.CERT
DATES = ("2021-12-31", "2022-06-30", "2022-12-31")
DEFAULT_VARIANT = "vd-2022-q4"
FIT_ID = "svb-2021-2022"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 20_000.0
#: the measured results are exact in the documents: their identities close to 1e-9 of the money, and rounding to nine significant
#: digits would only add noise to them
EXACT = frozenset({"outputs", "fit", "tests"})
SOURCES = ("fdic-bankfind", "treasury-par-curve")

#: what a reader should see, declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT: dict[str, tuple[float, float]] = {
    "eve_ratio_2024_contractual_2022q4": (0.2, 3.0),
    "eve_ratio_2024_behavioural_2022q4": (0.0, 2.0),
    "eve_ratio_2024_contractual_2021q4": (0.2, 3.0),
    "base_nii_over_reported_2022q4": (0.4, 2.5),
    "deposit_beta_up_2022q4": (0.0, 1.0),
}

_T0 = time.perf_counter()



def report_source(fd: dict) -> dict[str, str]:
    """The provenance of the FDIC financials file a call report is read from, in both languages (R3 c15 B2: the Spanish Context
    printed "file" and "retrieved"); the URL, the file name, the hash and the date are the same in both."""
    url, name, sha, day = fd["url"], fd["name"], fd["sha256"][:12], fd["retrieved"]
    return {"en": f"{url} (file {name}, sha256 {sha}, retrieved {day})", "es": f"{url} (archivo {name}, sha256 {sha}, obtenido el {day})"}

def _log(msg: str) -> None:
    print(f"[C14 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Built:
    models: dict[str, Any]
    variants: dict[str, dict[str, Any]]
    results: dict[str, vt.VariantResult]
    values: dict[str, float]
    raw_sources: dict[str, Any]
    contract: dict[str, Any]


def engine_version() -> str:
    """The engine version with the commit that pins it (requirements.txt), so the document names the code that computed it."""
    try:
        ver = md.version("riskvalidation")
    except md.PackageNotFoundError:
        ver = "not installed"
    req = (Path(__file__).resolve().parents[4] / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = re.search(r"CAOS_RiskValidation\.git@([0-9a-f]{40})", req)
    return f"{ver}+{m.group(1)[:7]}" if m else ver


def _model_summaries(ev: str) -> list[dict[str, Any]]:
    def rec(mid: str, rung: str, en: str, es: str, params: dict[str, tuple[float, str]]) -> dict[str, Any]:
        return {"id": mid, "family": "irrbb", "rung": rung, "title": t(en, es), "short_title": t(en.split(",")[0], es.split(",")[0]),
                "engine": "riskvalidation", "engine_version": ev, "licence": "MIT", "calibration": None,
                "parameters": {k: {"value": v, "unit": u} for k, (v, u) in params.items()}, "checkpoint_sha256": None}

    return [
        rec("irrbb-gap-duration", "repricing-gap-and-duration-gap", "Repricing gap and duration gap", "Brecha de reprecio y brecha de duración", {}),
        rec(vt.MODEL_ID, "standardised-eve", "Standardised EVE, six shocks", "EVE estandarizado, seis choques",
            {"usd_parallel_bp_2024": (200.0, "bp"), "usd_short_bp_2024": (300.0, "bp"), "usd_long_bp_2024": (225.0, "bp"),
             "outlier_threshold": (0.15, "share of Tier 1"), "floor": (asm.FLOOR, "rate")}),
        rec("irrbb-nmd-replicating", "replicating-portfolio", "Replicating portfolio of the non-maturity deposits",
            "Cartera replicante de los depósitos a la vista", {"fit_quarters": (float(asm.FIT_QUARTERS), "quarters")}),
        rec("irrbb-dynamic-nii", "dynamic-nii", "Dynamic NII with deposit betas", "NII dinámico con betas de depósitos",
            {"horizon_months": (float(asm.HORIZON_MONTHS), "months")}),
        rec("irrbb-ear-evar-hw1f", "ear-evar", "EaR and EVaR, Hull-White one factor", "EaR y EVaR, Hull-White un factor",
            {"a": (asm.HW1F_A, "per year")}),
    ]


def _bs_records(vd: str, items: list) -> list[dict[str, Any]]:
    cls = {"none": "contractual", "nmd-retail-transactional": "nmd_retail_transactional",
           "nmd-retail-non-transactional": "nmd_retail_non_transactional", "nmd-wholesale": "nmd_wholesale",
           "term-deposit": "redeemable_term_deposit", "prepayable-loan": "prepayable_fixed_rate_loan"}
    rows = []
    for i in items:
        for k in range(19):
            if i.behavioural[k] != 0.0:
                rec = {"as_of": vd, "item": i.label["en"], "currency": "USD", "amount": float(i.behavioural[k]),
                       "repricing_bucket": c1.REPRICING_BANDS[k][0], "behavioural_class": cls[i.behavioural_class]}
                if i.behavioural_class.startswith("nmd-"):
                    req = asm.REQUESTS[i.behavioural_class.removeprefix("nmd-")]
                    rec["core_share"], rec["core_avg_maturity_years"] = req.share, req.maturity
                rows.append(rec)
    return rows


def _contract_summaries(vd: str, items: list, curve: treasury.ParCurve) -> dict[str, Any]:
    """Contract 1 over what the readers produced: the slotted balance sheet and the Treasury curve of the date."""
    bs = c1.validate("balance_sheet", _bs_records(vd, items))
    cv = c1.validate("curve", [{"date": vd, "tenor_years": float(a), "rate": float(b), "compounding": "semiannual"}
                              for a, b in zip(curve.tenors(), curve.yields())])
    if not (bs.ok and cv.ok) or bs.rejected or cv.rejected:
        raise ValueError(f"{vd}: contract 1 rejects the readers' output: balance_sheet {bs.counts()}, curve {cv.counts()}")
    return {"fdic-bankfind": bs.summary(), "treasury-par-curve": cv.summary()}


def build(seed: int, data_root: Path | str | None, *, n_paths: int | None = None, drop_after: str | None = None,
          only: tuple[str, ...] | None = None) -> Built:
    """Every document of the case in memory. ``drop_after`` removes every report and curve dated after it (the dating test)."""
    if data_root is None:
        raise FileNotFoundError("C14 reads the raw FDIC and Treasury files of the device data root: pass --data-root or set CONTRASTE_DATA")
    n_paths = asm.N_PATHS if n_paths is None else n_paths
    prov = fetch.load_provenance(data_root)
    raw = Path(data_root) / "raw"
    reports = fdic.read_financials(raw / fetch.FDIC_DIR / fetch.fdic_name(CERT), CERT)
    curves = treasury.read_par(raw / fetch.TREASURY_DIR)
    if drop_after is not None:
        reports = fdic.up_to(reports, drop_after)
        curves = {d: c for d, c in curves.items() if d <= drop_after}
    fd = prov[fetch.FDIC_DIR][0]
    raw_urls = {"fdic": report_source(fd)}
    manifest_in = {"sources": {
        "fdic-bankfind": {"files": [{"name": r["name"], "sha256": r["sha256"]} for r in prov[fetch.FDIC_DIR]]},
        "treasury-par-curve": {"files": [{"name": r["name"], "sha256": r["sha256"]} for r in prov[fetch.TREASURY_DIR]]}}}
    ev = engine_version()
    lineage = lin.build(CASE_ID, sources=list(SOURCES), truth_status="synthetic-calibrated", seed=seed, code_version=__version__,
                        riskvalidation_version=ev, manifest=manifest_in)
    lane = {"lane": "precompute", "reasons": []}
    dates = [d for d in DATES if drop_after is None or d <= drop_after]
    results: dict[str, vt.VariantResult] = {}
    breach: dict[str, bool] = {}
    wam: dict[str, float] = {}
    docs: dict[str, dict[str, Any]] = {}
    contract: dict[str, Any] = {}
    for vd in dates:
        known = fdic.up_to(reports, vd)
        cut = {d: c for d, c in curves.items() if d <= vd}
        res = vt.bake_variant(vd, known, reports, cut, seed, n_paths, dict(breach), dict(wam), raw_urls)
        breach[vd] = res.breached
        wam[vd] = res.fit["fit"]["weighted_average_maturity_years"]
        results[vd] = res
        d = res.document
        vid = vt.variant_id(vd)
        docs[vid] = build_artifact(case_id=CASE_ID, variant_id=vid, model=_model_summaries(ev), outputs=d["outputs"], tests=d["tests"],
                                   impact=d["impact"], findings=d["findings"], lineage=lineage, lane=lane)
        contract[vid] = _contract_summaries(vd, build_items(fdic.report_at(known, vd)), treasury.curve_as_of(cut, vd))
        _log(f"{vid}: ratio 2024 behavioural {res.values['eve_ratio_2024_behavioural']:.3f}, contractual {res.values['eve_ratio_2024_contractual']:.3f}")
    fit = models.models_document(dates, results)
    records = []
    for rec in _model_summaries(ev):
        rec = dict(rec)
        rec["details"] = {"valuation_dates": dates}
        records.append(rec)
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=records, fit=fit, lineage=lineage, lane=lane)
    values = {}
    for vd, res in results.items():
        q = vt.quarter_of(vd).replace("-", "").lower()
        values.update({"eve_ratio_2024_contractual_" + q: res.values["eve_ratio_2024_contractual"],
                       "eve_ratio_2024_behavioural_" + q: res.values["eve_ratio_2024_behavioural"],
                       "base_nii_over_reported_" + q: res.values["base_nii_over_reported"], "deposit_beta_up_" + q: res.values["deposit_beta_up"]})
    flat = [r for rows in prov.values() for r in rows]
    reg = registry.load()
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The rows of data/sources/manifest.json for the two raw inputs of C14, in that file's format. The raw files stay in the "
                           "device data root (outside the repository); each file record is the one written when it was fetched, and the bake "
                           "refuses a file whose bytes differ from it.",
                   "sources": {sid: {"name": reg[sid].name, "publisher": reg[sid].publisher, "landing": reg[sid].landing,
                                     "class": reg[sid].klass, "licence": reg[sid].licence, "attribution": reg[sid].attribution,
                                     "access": reg[sid].access, "files": rows}
                               for sid, rows in (("fdic-bankfind", prov[fetch.FDIC_DIR]), ("treasury-par-curve", prov[fetch.TREASURY_DIR]))}}
    assert sum(len(v["files"]) for v in raw_sources["sources"].values()) == len(flat)
    if only is not None:
        docs = {k: v for k, v in docs.items() if k in only}
    return Built(models_doc, docs, results, values, raw_sources, contract)


def _check_and_write(root: Path, rel: str, doc: dict[str, Any]) -> dict[str, Any]:
    """Schema, then the semantic checks (D3 of the U10 sizing), then the write; any finding refuses the document."""
    validate_document(f"data/derived/{rel}", doc)
    found = _semantics().check_document(doc)
    if found:
        raise ValueError(f"{rel}: check_document refuses the document: {found[:5]}")
    return write_artifact(root, rel, doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def _semantics():
    repo = Path(__file__).resolve().parents[4]
    path = str(repo / "tests" / "contracts_u10")
    if path not in sys.path:
        sys.path.insert(0, path)
    import semantics

    return semantics


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def bake_case(seed: int, paths: Any, data_root: Path | str | None, n_paths: int | None = None) -> dict[str, Any]:
    built = build(seed, data_root, n_paths=n_paths)
    root = Path(paths.root)
    entries, sums = [], []
    regime = t("Call reports and Treasury curve read up to the date; behaviour synthetic, stated in the document.",
               "Reportes y curva del Tesoro leídos hasta la fecha; comportamiento sintético, declarado en el documento.")
    e = _check_and_write(root, MODELS_REL, built.models)
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "synthetic-calibrated",
                    "title": t("Fitted models and tables, 2021 to 2022", "Modelos ajustados y tablas, 2021 a 2022"),
                    "short_title": t("Models", "Modelos"), "regime": regime, "path": MODELS_REL, **e})
    for vid, doc in built.variants.items():
        rel = f"{CASE_ID}/{vid}.json"
        e = _check_and_write(root, rel, doc)
        sums.append(_sum(root, rel))
        q = doc["outputs"]["quarter"]
        entries.append({"role": "variant", "variant_id": vid, "truth_status": "synthetic-calibrated",
                        "title": t(f"Valuation date {doc['outputs']['valuation_date']} ({q})", f"Fecha de valoración {doc['outputs']['valuation_date']} ({q})"),
                        "short_title": t(q, q), "regime": regime, "models_ref": MODELS_REL, **e})
        _log(f"{vid}: {e['bytes']:,} bytes")
    write_json(root / RAW_REL, built.raw_sources)
    sums.append(_sum(root, RAW_REL))
    (root / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built.values)
    from . import CASE

    manifest = build_case_manifest(
        depends_on=CASE.depends_on(),
        case_id=CASE_ID, title=_title(), category={"en": "Balance sheet: IRRBB and liquidity", "es": "Balance: IRRBB y liquidez"},
        question=_question(), sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT,
        contract=built.contract[DEFAULT_VARIANT], expect=ranges, riskvalidation_version=engine_version(),
        source_details=_source_details(SOURCES))
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest


def _title() -> dict[str, str]:
    from . import CASE

    return dict(CASE.title)


def _question() -> dict[str, str]:
    from . import CASE

    return dict(CASE.question)


def _source_details(ids: tuple[str, ...]) -> dict[str, dict[str, str]]:
    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}
