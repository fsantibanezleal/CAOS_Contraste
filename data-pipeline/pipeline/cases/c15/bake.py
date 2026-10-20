"""The C15 bake: six variants of the Banco Andino book on the BCCh curves of one stated month, through ``riskvalidation.irrbb``.

``build`` makes every document in memory (it reads the raw files of the device data root, which ``pipeline.io.bcch fetch`` wrote, and never the
network); ``bake_case`` writes them with the checksums, the raw-source record and the manifest. The documents are the c15-outputs and c15-models
contracts (docs/contracts/schemas/c15/). Every document passes the schema and ``tests/contracts_u10/semantics.py::check_document`` before it is
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
from ...io.formats import write_json
from ...stages.export import write_artifact
from ..c07 import sources as c07_src
from . import assumptions as asm
from . import book as bk
from . import curves as cv
from . import models
from . import targets
from . import variant as vt
from .book import t

CASE_ID = "C15"
MONTH = "2026-09"
VARIANT_ORDER = tuple(bk.SPECS)
DEFAULT_VARIANT = "long-uf"
FIT_ID = "banco-andino-2026-09"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 20_000.0
#: the measured results are exact in the documents: their identities close to 1e-9 of the money, and rounding to nine significant
#: digits would only add noise to them
EXACT = frozenset({"outputs", "fit", "tests"})
SOURCES = ("bcch-bde",)

#: what a reader should see, declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT: dict[str, tuple[float, float]] = {
    **{f"delta_eve_over_tier1_{v.replace('-', '_')}": (0.0, 1.5) for v in VARIANT_ORDER},
    **{f"delta_nii_over_tier1_{v.replace('-', '_')}": (0.0, 0.8) for v in VARIANT_ORDER},
}
_T0 = time.perf_counter()
REGIME = t("Real Banco Central de Chile F022 curves of the valuation date; synthetic bank calibrated to CMF aggregates; behaviour synthetic, stated "
           "in the document.",
           "Curvas F022 reales del Banco Central de Chile a la fecha de valoración; banco sintético calibrado a agregados de la CMF; comportamiento "
           "sintético, declarado en el documento.")


#: the Spanish chip labels that a rail line cannot hold (the variant title keeps the full wording)
SHORT_ES = {"offset-on-off": "Compensación CLP/CLF"}

def _log(msg: str) -> None:
    print(f"[C15 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Built:
    models: dict[str, Any]
    variants: dict[str, dict[str, Any]]
    values: dict[str, float]
    raw_sources: dict[str, Any]
    contract: dict[str, Any]
    selection: cv.Selection | None = None


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
        rec(vt.MODEL_ID, "cmf-annex1", "RAN 21-13 Annex 1, delta EVE and delta NII", "RAN 21-13 Anexo 1, delta EVE y delta NII",
            {"offset_share": (0.5, "share"), "indexation_rate": (0.025, "share of |PN_UR|"), "ur_floor": (vt.UR_FLOOR, "rate"),
             "other_floor": (vt.OTHER_FLOOR, "rate"), "nii_shock_bp": (vt.NII_BP, "bp")}),
        rec("irrbb-curves-nelson-siegel", "curve-fit", "Nelson-Siegel zero curves", "Curvas cero Nelson-Siegel", {"coupon_frequency": (2.0, "per year")}),
        rec("irrbb-ear-evar-hw1f", "ear-evar", "EaR and EVaR, Hull-White one factor", "EaR y EVaR, Hull-White un factor",
            {"a": (asm.HW1F_A, "per year"), "n_paths": (float(asm.N_PATHS), "paths")}),
        rec("irrbb-dynamic-nii", "dynamic-nii", "Dynamic NII, constant balance sheet", "NII dinámico, balance constante",
            {"horizon_months": (float(asm.HORIZON_MONTHS), "months")}),
    ]


_CLASS = {"none": "contractual", "nmd-retail-operational": "nmd_retail_transactional", "nmd-retail-non-operational": "nmd_retail_non_transactional",
          "nmd-wholesale": "nmd_wholesale", "term-deposit": "redeemable_term_deposit", "prepayable-loan": "prepayable_fixed_rate_loan"}


def _bs_records(b: bk.Book, vd: str) -> list[dict[str, Any]]:
    """The book as contract-1 balance-sheet rows: one per item and bucket, amounts signed in the currency of the leg."""
    rows = []
    req = {asm.CATEGORY_CLASS[c]: r for c, r in asm.REQUESTS.items()}
    for name, leg in b.legs.items():
        for i in leg.items:
            for k in range(19):
                if i.flows[k] != 0.0:
                    rec = {"as_of": vd, "item": i.label["en"], "currency": leg.currency, "amount": float(i.flows[k]),
                           "repricing_bucket": c1.REPRICING_BANDS[k][0], "behavioural_class": _CLASS[i.behavioural_class]}
                    if i.behavioural_class in req:
                        rec["core_share"], rec["core_avg_maturity_years"] = req[i.behavioural_class].share, req[i.behavioural_class].maturity
                    rows.append(rec)
    return rows


def _merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Two contract-1 summaries of one family added into one (the pesos and the UF curve are validated apart: their tenors repeat)."""
    counts = {k: a["counts"][k] + b["counts"][k] for k in a["counts"]}
    by = {}
    for kind in ("rejected", "flagged", "excluded"):
        merged = dict(a["by_rule"].get(kind, {}))
        for r, n in b["by_rule"].get(kind, {}).items():
            merged[r] = merged.get(r, 0) + n
        by[kind] = merged
    return {"family": a["family"], "counts": counts, "by_rule": by, "ignored_columns": sorted(set(a["ignored_columns"]) | set(b["ignored_columns"])),
            "examples": [*a["examples"], *b["examples"]][:5]}


def _contract_summaries(b: bk.Book, fits: dict[str, cv.CurveFit], vd: str) -> dict[str, Any]:
    """Contract 1 over what the readers produced: the Banco Andino book (refused when it breaks a rejecting rule) and the observed BCCh curves."""
    bs = c1.validate("balance_sheet", _bs_records(b, vd))
    reports = [c1.validate("curve", [{"date": vd, "tenor_years": p["tenor_years"], "rate": p["observed_yield"], "compounding": "semiannual"}
                                     for p in fits[c].block["points"]]) for c in ("CLP", "UR")]
    if not bs.ok or bs.rejected or any(not r.ok or r.rejected for r in reports):
        raise ValueError(f"{vd}: contract 1 rejects the book or the curves: balance_sheet {bs.counts()}, curves {[r.counts() for r in reports]}")
    return {"bcch-bde": _merge(reports[0].summary(), reports[1].summary()), "_book": bs.summary()}


def build(seed: int, data_root: Path | str | None, *, only: tuple[str, ...] | None = None, n_paths: int | None = None) -> Built:
    """Every document of the case in memory."""
    if data_root is None:
        raise FileNotFoundError("C15 reads the raw BCCh files of the device data root: pass --data-root or set CONTRASTE_DATA")
    raw = cv.load_raw(data_root)                                  # every file is checked against its provenance record
    sel = cv.select(raw.series, raw.infos, MONTH)
    fits = {c: cv.fit_curve(sel, raw.series, c) for c in ("CLP", "UR")}
    uf, uf_source = cv.uf_value(sel, raw.series)
    vd = sel.valuation_date
    prov = [{k: r[k] for k in ("name", "url", "bytes", "sha256", "retrieved")} for r in raw.files]
    manifest_in = {"sources": {"bcch-bde": {"files": [{"name": r["name"], "sha256": r["sha256"]} for r in prov]}}}
    ev = engine_version()
    lineage = lin.build(CASE_ID, sources=list(SOURCES), truth_status="synthetic-calibrated", seed=seed, code_version=__version__,
                        riskvalidation_version=ev, manifest=manifest_in, generators=("banco-andino-irrbb-synthetic/1.0.0",))
    lane = {"lane": "precompute", "reasons": []}
    pub = c07_src.PUBLICATIONS[targets.PUBLICATION]
    calibration_source = (f"{pub['title']}, Cuadro N 1 column Bancos, {pub['url']}, sha256 {pub['sha256']}; the three loan portfolios are the C07 "
                          f"targets; securities, deposits, equity and loans to banks are the other figures of the same table; scaled to the C07 "
                          f"total exposure; the UF shares, profiles, deposit split and behaviour are synthetic")
    docs: dict[str, dict[str, Any]] = {}
    values: dict[str, float] = {}
    contract: dict[str, Any] = {}
    first_book = None
    for vid in VARIANT_ORDER:
        if only is not None and vid not in only:
            continue
        b = bk.build_book(seed, bk.SPECS[vid], uf)
        first_book = first_book or b
        res = vt.bake_variant(vid, b, fits, sel, uf_source, calibration_source, {}, seed, n_paths)
        d = res.document
        docs[vid] = build_artifact(case_id=CASE_ID, variant_id=vid, model=_model_summaries(ev), outputs=d["outputs"], tests=d["tests"],
                                   impact=d["impact"], findings=d["findings"], lineage=lineage, lane=lane)
        contract[vid] = _contract_summaries(b, fits, vd)
        values.update(res.values)
        _log(f"{vid}: delta EVE {d['outputs']['eve']['delta_eve']:,.0f} ({d['outputs']['eve']['delta_eve_share_tier1']:.3f} of Tier 1), "
             f"delta NII {d['outputs']['nii']['delta_nii']:,.0f}")
    if first_book is None:
        raise ValueError("no variant selected")
    fit = models.models_document(first_book, sel, fits, calibration_source)
    records = []
    for rec in _model_summaries(ev):
        rec = dict(rec)
        rec["details"] = {"valuation_date": vd, "month": MONTH}
        records.append(rec)
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=records, fit=fit, lineage=lineage, lane=lane)
    reg = registry.load()
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The row of data/sources/manifest.json for the raw inputs of C15, in that file's format. The raw files stay in the device "
                           "data root (outside the repository); each file record is the one written when it was fetched, and the bake refuses a file "
                           "whose bytes differ from it. The URL of a record never carries the account's user or password.",
                   "sources": {"bcch-bde": {"name": reg["bcch-bde"].name, "publisher": reg["bcch-bde"].publisher, "landing": reg["bcch-bde"].landing,
                                            "class": reg["bcch-bde"].klass, "licence": reg["bcch-bde"].licence,
                                            "attribution": reg["bcch-bde"].attribution, "access": reg["bcch-bde"].access, "files": prov}}}
    return Built(models_doc, docs, values, raw_sources, contract, sel)


def _check(rel: str, doc: dict[str, Any]) -> None:
    """Schema, then the semantic checks (D3 of the U10 sizing); any finding refuses the document."""
    validate_document(f"data/derived/{rel}", doc)
    found = _semantics().check_document(doc)
    if found:
        raise ValueError(f"{rel}: check_document refuses the document: {found[:5]}")


def _check_and_write(root: Path, rel: str, doc: dict[str, Any]) -> dict[str, Any]:
    _check(rel, doc)
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


def bake_case(seed: int, paths: Any, data_root: Path | str | None) -> dict[str, Any]:
    built = build(seed, data_root)
    root = Path(paths.root)
    entries, sums = [], []
    for rel, doc in ((MODELS_REL, built.models), *((f"{CASE_ID}/{vid}.json", d) for vid, d in built.variants.items())):
        _check(rel, doc)                                    # nothing is written until every document has passed its checks
    e = _check_and_write(root, MODELS_REL, built.models)
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "synthetic-calibrated",
                    "title": t("Fitted curves, tables and behavioural models, September 2026", "Curvas ajustadas, tablas y modelos de comportamiento, "
                                                                                                "septiembre de 2026"),
                    "short_title": t("Models", "Modelos"), "regime": REGIME, "path": MODELS_REL, **e})
    for vid, doc in built.variants.items():
        rel = f"{CASE_ID}/{vid}.json"
        e = _check_and_write(root, rel, doc)
        sums.append(_sum(root, rel))
        label = doc["outputs"]["variant"]["label"]
        # the chip of the variant in the rail is one line of the rail's width (ADR-0071 rule 6): the Spanish title of the offset
        # variant is 43 characters and left the rail by 68 px, so its chip carries the shorter wording; the title stays whole
        short = {**label, "es": SHORT_ES[vid]} if vid in SHORT_ES else label
        entries.append({"role": "variant", "variant_id": vid, "truth_status": "synthetic-calibrated", "title": label, "short_title": short,
                        "regime": REGIME, "models_ref": MODELS_REL, **e})
        _log(f"{vid}: {e['bytes']:,} bytes")
    write_json(root / RAW_REL, built.raw_sources)
    sums.append(_sum(root, RAW_REL))
    (root / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built.values)
    contract = {k: v for k, v in built.contract[DEFAULT_VARIANT].items() if k != "_book"}
    manifest = build_case_manifest(
        case_id=CASE_ID, title=_title(), category={"en": "Balance sheet: IRRBB and liquidity", "es": "Balance: IRRBB y liquidez"},
        question=_question(), sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT, contract=contract,
        expect=ranges, riskvalidation_version=engine_version(), source_details=_source_details(SOURCES))
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
