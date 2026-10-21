"""The C16 bake: the five scenario variants, the reverse stress and the models document of the bank that failed on 2023-03-10, read
up to the valuation date 2022-12-31 (the time block at 2021-12-31 and 2022-06-30, each read up to its own date), through ``riskvalidation``.

``build`` makes every document in memory from the inputs (the raw files of the device data root, read by ``load_inputs``);
``bake_case`` writes them with the checksums, the raw-source record and the manifest. Every document passes the schema and the
cross-field checks of ``tests/contracts_u11/semantics.py`` before it is written (the producer rule of the U11 contracts), and the
conventions are the same in every document of the bake.
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
from ...io import contract as c1
from ...io import fdic
from ...io import sources as registry
from ...io import treasury
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import anchors, assumptions, balance, fetch, h8, models, reverse
from . import document as doc
from . import variant as vt
from .assumptions import VARIANT_IDS, txt

CASE_ID = "C16"
VALUATION_DATE = "2022-12-31"
FIT_ID = "svb-liquidity"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
REVERSE_ID = "reverse-stress"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 20_000.0
N_DRAWS = 20_000
#: the measured results are exact in the documents: their identities close to 1e-9 of the money
EXACT = frozenset({"outputs", "fit", "tests", "impact"})
SOURCES = ("fdic-bankfind", "fed-h8", "fed-svb-review", "treasury-par-curve")
FOLDER_SOURCE = {fetch.FDIC_DIR: "fdic-bankfind", fetch.H8_DIR: "fed-h8", fetch.SVB_DIR: "fed-svb-review", fetch.TREASURY_DIR: "treasury-par-curve"}
DEFAULT_VARIANT = "list-adverse"

#: what a reader should see, declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT: dict[str, tuple[float, float]] = {
    "lcr_ratio_central_2022_12_31": (0.0, 5.0),
    "survival_day_list_adverse_2022_12_31": (1.0, 125.0),
    "survival_day_list_extreme_2022_12_31": (1.0, 125.0),
    "reverse_multiplier_list_adverse": (1.0, 150.0),
    "htm_cbc_removed_share": (0.0, 1.0),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C16 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Inputs:
    """What the bake reads: the call reports of the wide span, the Treasury curves, the H.8 weekly series (or None with a reason), the
    provenance records by raw-file folder and the URLs of the raw files."""

    reports: list[fdic.Report]
    curves: dict[str, treasury.ParCurve]
    h8: dict[str, list[tuple[str, float]]] | None
    h8_reason: str | None
    provenance: dict[str, list[dict[str, Any]]]
    raw_urls: dict[str, str] = field(default_factory=dict)


@dataclass
class Built:
    models: dict[str, Any]
    variants: dict[str, dict[str, Any]]
    reverse: dict[str, Any]
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


def restrict(inputs: Inputs, date: str) -> Inputs:
    """The inputs with every call report and curve dated after ``date`` removed (the dating rule, applied before anything is built)."""
    return Inputs(fdic.up_to(inputs.reports, date), {d: c for d, c in inputs.curves.items() if d <= date}, inputs.h8, inputs.h8_reason,
                  inputs.provenance, inputs.raw_urls)


def load_inputs(data_root: Path | str | None) -> Inputs:
    """Read the raw files of the device data root; refuses a file that differs from its provenance record. The H.8 pages are read with
    the standard library parser: each week takes the value of the latest release that lists it."""
    if data_root is None:
        raise FileNotFoundError("C16 reads the raw FDIC, H.8 and Treasury files of the device data root: pass --data-root or set CONTRASTE_DATA")
    prov = fetch.load_provenance(data_root)
    raw = Path(data_root) / "raw"
    reports = fdic.read_financials(raw / fetch.FDIC_DIR / fetch.fdic_name(), fetch.CERT)
    curves = treasury.read_par(raw / fetch.TREASURY_DIR)
    anchors.verify_review(raw / fetch.SVB_DIR / fetch.SVB_NAME)
    series: dict[str, dict[str, float]] = {"large-domestic-deposits": {}, "small-domestic-deposits": {}}
    for rec in sorted(prov[fetch.H8_DIR], key=lambda r: r["name"]):
        rel = rec["name"][3:11]
        release = h8.parse_release((raw / fetch.H8_DIR / rec["name"]).read_text(encoding="utf-8"), f"{rel[:4]}-{rel[4:6]}-{rel[6:]}")
        for key, table in (("large-domestic-deposits", 6), ("small-domestic-deposits", 8)):
            for d, v in h8.weekly_series(release, table, "Deposits"):
                series[key][d] = v        # the later release is read later: its vintage replaces the earlier one
    h8s = {k: sorted(v.items()) for k, v in series.items()}
    urls = {}
    for folder, rows in prov.items():
        r = rows[0]
        urls[folder] = f"{r['url']} (file {r['name']}, sha256 {r['sha256'][:12]}, retrieved {r['retrieved']})"
    return Inputs(reports, curves, h8s, None, prov, urls)


def _manifest_in(inp: Inputs) -> dict[str, Any]:
    return {"sources": {sid: {"files": [{"name": r["name"], "sha256": r["sha256"]} for r in inp.provenance.get(folder, [])]}
                        for folder, sid in FOLDER_SOURCE.items()}}


def _contract_summaries(inp: Inputs, report: fdic.Report, sheet: dict[str, Any], curves: dict[str, treasury.ParCurve]) -> dict[str, Any]:
    """Contract 1 over what the readers produced: the balance sheet items that carry the liquidity fields, the H.8 lines and the Treasury
    curves of the two dates the HTM revaluation reads."""
    bands = [("ON", 1), ("ON-1M", 30), ("1M-3M", 90)]
    records = []
    for i in sheet["items"]:
        if i["residual_days"] is None:
            continue
        band = next(b for b, upper in bands if i["residual_days"] <= upper)
        rec = {"as_of": sheet["as_of"], "item": i["label"]["en"], "currency": "USD", "amount": i["amount"] if i["side"] == "asset" else -i["amount"],
               "repricing_bucket": band, "behavioural_class": "contractual", "residual_days": i["residual_days"]}
        if i["liquidity_class"] is not None:
            rec["liquidity_class"] = i["liquidity_class"]
        if i["insured"] is not None:
            rec["insured"] = 1 if i["insured"] else 0
        if i["fair_value"] is not None:
            rec["fair_value"] = i["fair_value"] if i["side"] == "asset" else -i["fair_value"]
        records.append(rec)
    bs = c1.validate("balance_sheet", records)
    out = {"fdic-bankfind": bs.summary()}
    bad = [bs]
    if inp.h8 is not None:
        ms = c1.validate("market_series", [{"date": d, "series_id": sid, "value": v, "unit": "level"}
                                           for k, (sid, _, _) in doc.H8_SERIES.items() for d, v in inp.h8[k]])
        out["fed-h8"] = ms.summary()
        bad.append(ms)
    if curves:
        days = sorted({sorted(d for d in curves if d <= date)[-1] for date in (report.report_date, f"{int(report.report_date[:4]) - 1}{report.report_date[4:]}")
                       if any(d <= date for d in curves)})
        cv = c1.validate("curve", [{"date": d, "tenor_years": float(a), "rate": float(b), "compounding": "semiannual"}
                                   for d in days for a, b in zip(curves[d].tenors(), curves[d].yields())])
        out["treasury-par-curve"] = cv.summary()
        bad.append(cv)
    if any((not r.ok) or r.rejected for r in bad):
        raise ValueError(f"contract 1 rejects the readers' output: {[r.counts() for r in bad]}")
    return out


def build(seed: int, inputs: Inputs, *, n_draws: int = N_DRAWS, only: tuple[str, ...] | None = None) -> Built:
    """Every document of the case in memory. Reads each report up to the date it describes; nothing dated later is ever used."""
    inp = restrict(inputs, VALUATION_DATE)
    report = fdic.report_at(inp.reports, VALUATION_DATE)
    earlier = [fdic.report_at(fdic.up_to(inp.reports, d), d) for d in doc.TIME_DATES]
    conv = assumptions.conventions()
    cal, fit = models.calibration(models.pre_2023_rows(), models.RULE)
    gen_block, gen_test = models.generator_block(report, fit.daily_rate, conv, seed, n_draws)
    ev = engine_version()
    lineage = lin.build(CASE_ID, sources=list(SOURCES), truth_status="synthetic-calibrated", seed=seed, code_version=__version__,
                        riskvalidation_version=ev, generators=("riskvalidation.liquidity.deposits.DepositorGenerator",), manifest=_manifest_in(inp))
    lane = {"lane": "precompute", "reasons": []}
    sh = doc.Shared(conv, fit, inp.curves, inp.h8, inp.h8_reason, gen_test, ev)
    sh.survivals = {"list-adverse": vt.path_for("list-adverse", report, conv, fit, basis="amortised-cost").survival}
    wanted = [v for v in VARIANT_IDS if only is None or v in only]
    docs: dict[str, dict[str, Any]] = {}
    paths: dict[str, vt.Path] = {}
    values: dict[str, float] = {}
    for vid in VARIANT_IDS:
        if vid not in wanted and vid not in reverse.BASES:
            continue
        d = doc.scenario_document(vid, report, earlier, sh)
        if d["path"] is not None:
            paths[vid] = d["path"]
        if vid in wanted:
            docs[vid] = build_artifact(case_id=CASE_ID, variant_id=vid, model=[doc.model_summary(ev)], outputs=d["outputs"], tests=d["tests"],
                                       impact=d["impact"], findings=d["findings"], lineage=lineage, lane=lane)
            _log(f"{vid}: survival {d['impact']['survival_days']['value']}, LCR {d['impact']['lcr']['value']}")
            if vid == "lcr-standard":
                values["lcr_ratio_central_2022_12_31"] = d["outputs"]["lcr"]["ratio"]
            if vid == "list-adverse":
                values["survival_day_list_adverse_2022_12_31"] = d["impact"]["survival_days"]["value"] or 125.0
            if vid == "list-extreme":
                values["survival_day_list_extreme_2022_12_31"] = d["impact"]["survival_days"]["value"] or 125.0
            if vid == "htm-losses":
                h = d["outputs"]["htm"]
                values["htm_cbc_removed_share"] = h["cbc_removed"] / h["cbc_without_loss"]
    if only is None or set(reverse.BASES) <= set(paths):
        rv = reverse.reverse_document(paths, sh)
        rev_doc = build_artifact(case_id=CASE_ID, variant_id=REVERSE_ID, model=rv["models"], outputs=rv["outputs"], tests=rv["tests"], impact=rv["impact"],
                                 findings=rv["findings"], lineage=lineage, lane=lane)
        m = rv["outputs"]["bases"][0]["solved"]["multiplier"]
        values["reverse_multiplier_list_adverse"] = m if m is not None else 1.0
    else:
        rev_doc = {}
    fit_doc = models.models_fit(report, conv, cal, gen_block)
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=models.models_summary(ev), fit=fit_doc, lineage=lineage, lane=lane)
    reg = registry.load()
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The rows of data/sources/manifest.json for the raw inputs of C16, in that file's format. The raw files stay in the device data root "
                           "(outside the repository); each file record is the one written when it was fetched, and the bake refuses a file whose bytes differ "
                           "from it. The Treasury files are those fetched by C14.",
                   "sources": {sid: {"name": reg[sid].name, "publisher": reg[sid].publisher, "landing": reg[sid].landing, "class": reg[sid].klass,
                                     "licence": reg[sid].licence, "attribution": reg[sid].attribution, "access": reg[sid].access,
                                     "files": inp.provenance.get(folder, [])} for folder, sid in FOLDER_SOURCE.items()}}
    contract = _contract_summaries(inp, report, balance.balance_sheet(report), inp.curves)
    return Built(models_doc, docs, rev_doc, values, raw_sources, contract)


# ------------------------------------------------------------------------------------------------------ writing


def _semantics():
    path = Path(__file__).resolve().parents[4] / "tests" / "contracts_u11" / "semantics.py"
    spec = importlib.util.spec_from_file_location("c16_semantics_bake", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def extra_findings(document: dict[str, Any]) -> list[str]:
    """What the contracts leave to the producer (CT-1619): a scenario document carries the H.8 aggregate record or the stated reason it is
    absent (never both, never neither) and the two earlier dates of the time block."""
    o = document.get("outputs", {})
    if o.get("kind") != "scenario":
        return []
    out = []
    if (o["aggregate_record"] is None) == (o["aggregate_record_reason"] is None):
        out.append("a scenario document carries the H.8 aggregate record or the reason it is absent, one of the two")
    if [t["as_of"] for t in o["time_block"]] != list(doc.TIME_DATES):
        out.append(f"the time block is not the dates {list(doc.TIME_DATES)}")
    return out


def _check_and_write(root: Path, rel: str, document: dict[str, Any], sem: Any) -> dict[str, Any]:
    """Schema, then the semantic checks of the producer, then the write; any finding refuses the document."""
    validate_document(f"data/derived/{rel}", document)
    found = [*sem.check_document(document), *extra_findings(document)]
    if found:
        raise ValueError(f"{rel}: check_document refuses the document: {found[:5]}")
    return write_artifact(root, rel, document, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def _title() -> dict[str, str]:
    from . import CASE

    return dict(CASE.title)


def _question() -> dict[str, str]:
    from . import CASE

    return dict(CASE.question)


def _source_details(ids: tuple[str, ...]) -> dict[str, dict[str, str]]:
    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence, "class": reg[i].klass,
                "attribution": reg[i].attribution} for i in ids}


def write_documents(root: Path | str, built: Built, manifests: Path | str | None = None, seed: int = 42) -> dict[str, Any]:
    """Write the documents, the checksums, the raw-source record and the manifest under ``root`` (the manifest under ``manifests``, or
    ``root/manifests``). Every document is checked before it is written; the conventions must agree across the documents."""
    root = Path(root)
    manifests = Path(manifests) if manifests is not None else root / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    sem = _semantics()
    every = [*built.variants.values(), built.reverse, built.models]
    found = [*sem.check_conventions_agree(every), *sem.check_cross_document(every)]
    if found:
        raise ValueError(f"C16: the documents disagree: {found[:5]}")
    regime = txt("Call reports read up to the date; real aggregates, synthetic behaviour stated in the document.",
                 "Reportes leídos hasta la fecha; agregados reales, comportamiento sintético declarado en el documento.")
    entries, sums = [], []
    e = _check_and_write(root, MODELS_REL, built.models, sem)
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "synthetic-calibrated",
                    "title": txt("Parameter sets, calibration and generator", "Conjuntos de parámetros, calibración y generador"),
                    "short_title": txt("Models", "Modelos"), "regime": regime, "path": MODELS_REL, **e})
    for vid, d in {**built.variants, **({REVERSE_ID: built.reverse} if built.reverse else {})}.items():
        rel = f"{CASE_ID}/{vid}.json"
        e = _check_and_write(root, rel, d, sem)
        sums.append(_sum(root, rel))
        label = vt.VARIANT_LABEL[vid][:2] if vid in vt.VARIANT_LABEL else ("Reverse stress", "Estrés inverso")
        entries.append({"role": "variant", "variant_id": vid, "truth_status": "synthetic-calibrated", "title": txt(*label), "short_title": txt(*label),
                        "regime": regime, "models_ref": MODELS_REL, **e})
        _log(f"{vid}: {e['bytes']:,} bytes")
    write_json(root / RAW_REL, built.raw_sources)
    sums.append(_sum(root, RAW_REL))
    (root / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built.values)
    default = DEFAULT_VARIANT if DEFAULT_VARIANT in {e["variant_id"] for e in entries} else next(e["variant_id"] for e in entries if e["role"] == "variant")
    from . import CASE

    manifest = build_case_manifest(
        depends_on=CASE.depends_on(),
        case_id=CASE_ID, title=_title(), category={"en": "Balance sheet: IRRBB and liquidity", "es": "Balance: IRRBB y liquidez"}, question=_question(),
        sources=list(SOURCES), seed=built.models["provenance"]["seed"], variants=entries, default_variant=default, contract=built.contract,
        expect=ranges, riskvalidation_version=engine_version(), source_details=_source_details(SOURCES))
    write_json(manifests / f"{CASE_ID}.json", manifest)
    return manifest


def differences(a: Path | str, b: Path | str) -> list[str]:
    """The relative paths (under the C16 folder and the manifest) whose bytes differ between two derived roots, or that exist in one only."""
    a, b = Path(a), Path(b)
    names = {p.relative_to(r).as_posix() for r in (a, b) for p in [*(r / CASE_ID).rglob("*"), r / "manifests" / f"{CASE_ID}.json"] if p.is_file()}
    return sorted(n for n in names if not ((a / n).is_file() and (b / n).is_file() and (a / n).read_bytes() == (b / n).read_bytes()))


def bake_case(seed: int, paths: Any, data_root: Path | str | None, n_draws: int = N_DRAWS) -> dict[str, Any]:
    built = build(seed, load_inputs(data_root), n_draws=n_draws)
    return write_documents(Path(paths.root), built, manifests=paths.manifests, seed=seed)
