"""The C12 bake: the six variants of the swap book on the Treasury curves, through ``riskvalidation.ccr`` and
``riskvalidation.regulatory``, with the exposure backtest and the ORE 1.8.17.0 and QuantLib 1.44 reconciliations.

``build`` makes every document in memory (it reads the raw files of the device data root, which ``fetch`` wrote, and runs ORE);
``bake_case`` writes them with the checksums, the raw-source record and the manifest. The documents are the c12-outputs and
c12-models contracts (docs/contracts/schemas/c12/). Every document passes its schema and ``tests/contracts_u9/semantics.py``
(``check_c12``, ``check_c12_variants``, ``check_c12_models``) before it is written.

A source that does not answer stops the variants that need it and names its URL (``DeclaredAbsence``); an ORE run that fails
stops the bake with its error: a variant is never published as not-applicable because ORE failed.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import re
import shutil
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
from ..reference_text import with_reference_text
from ...core.schemas import validate_document
from ...io import contract as c1
from ...io import sources as registry
from ...io import treasury
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import backtest as bt
from . import book, calibration, credit, data, fetch, models, ore, reconcile
from . import exposure as xp
from . import variant as vt

CASE_ID = "C12"
DEFAULT_VARIANT = "netting-set"
FIT_ID = "hw1f-treasury-2000-2025"
MODELS_REL = f"{CASE_ID}/models-{FIT_ID}.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
RAW_REL = f"{CASE_ID}/raw-sources.txt"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 20_000.0
EXACT = frozenset({"outputs", "fit", "tests"})
SOURCES = ("treasury-par-curve", "treasury-hqm")
ORE_SAMPLES = 10_000
ORE_VARIANTS = ("single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im")
STRESS_MIN_YEARS = 2.99

#: what a reader should see, declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT: dict[str, tuple[float, float]] = {
    "sa_ccr_ead_netting_set_usd": (5.0e4, 5.0e6),
    "eepe_netting_set_usd": (1.0e3, 5.0e5),
    "cva_netting_set_usd": (0.0, 5.0e4),
    "csa_10d_over_netting_eepe": (0.05, 1.0),
    "ba_cva_capital_netting_set_usd": (1.0e3, 5.0e6),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C12 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Built:
    models: dict[str, Any]
    variants: dict[str, dict[str, Any]]
    raw_sources: dict[str, Any]
    contract: dict[str, Any]
    values: dict[str, float]
    ore_inputs: dict[str, dict[str, str]] = field(default_factory=dict)


def engine_version() -> str:
    """The engine version with the commit that pins it (requirements.txt), so the document names the code that computed it."""
    try:
        ver = md.version("riskvalidation")
    except md.PackageNotFoundError:
        ver = "not installed"
    req = (Path(__file__).resolve().parents[4] / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = re.search(r"CAOS_RiskValidation\.git@([0-9a-f]{40})", req)
    return f"{ver}+{m.group(1)[:7]}" if m else ver


def _model_summaries(ev: str, a: float, sigma: float) -> list[dict[str, Any]]:
    return [{"id": vt.MODEL_ID, "family": "ccr", "rung": "hw1f", "title": vt.text("Hull-White one factor, exposure and CVA", "Hull-White de un factor, exposición y CVA"),
             "short_title": vt.text("HW1F", "HW1F"), "engine": "riskvalidation", "engine_version": ev, "licence": "MIT", "calibration": None,
             "parameters": {"a": {"value": float(a), "unit": "per year"}, "sigma": {"value": float(sigma), "unit": "per square-root year"}},
             "checkpoint_sha256": None}]


def _registry_with_hqm() -> dict[str, registry.Source]:
    reg = dict(registry.load())
    h = fetch.HQM_SOURCE
    reg["treasury-hqm"] = registry.Source(id=h["id"], name=h["name"], publisher=h["publisher"], landing=h["landing"], licence=h["licence"],
                                          klass=h["class"], access=h["access"], cases=tuple(h["cases"]), unverified=tuple(h["unverified"]),
                                          attribution=h["attribution"])
    return reg


def _stress(curves: data.Curves, series: calibration.Series, hqm: dict[str, Any], start: str, end: str) -> tuple[Any, dict[str, Any]]:
    """The stress calibration (a and sigma on the window) and the 5 year HQM spread at the first and the peak month end of it."""
    months = data.months_between(start[:7], end[:7])
    spreads = []
    for me in months:
        key = me[:7]
        if key not in hqm:
            raise treasury.DeclaredAbsence(f"the HQM end-of-month curve of {key} is not in the data root; fetch it from {fetch.HQM_PAGE}")
        tenors, zeros, _ = curves.zero(me)
        spreads.append(max(float(data.hqm_spread(hqm[key], tenors, zeros, np.array([data.SPREAD_YEARS]))[0]), 0.0))
    fit = calibration.fit_at(series, (np.datetime64(end) + 1).astype(str), start=start, min_years=STRESS_MIN_YEARS)
    return fit, {"start": start, "end": end, "spread_start": spreads[0], "spread_peak": max(spreads)}


def build(seed: int, data_root: Path | str | None, *, n_paths: int | None = None, bt_paths: int | None = None, crit_count: int | None = None,
          ore_samples: int | None = None, run_ore: bool = True, date_stride: int | None = None, ore_inputs_dir: Path | None = None,
          work_dir: Path | None = None) -> Built:
    """Every document of the case in memory. ``date_stride`` keeps every n-th backtest date counted back from the last (the tests)."""
    if data_root is None:
        raise FileNotFoundError("C12 reads the raw Treasury files of the device data root: pass --data-root or set CONTRASTE_DATA")
    n_paths = book.PATH_COUNT if n_paths is None else n_paths
    bt_paths = book.BACKTEST_PATHS if bt_paths is None else bt_paths
    crit_count = book.CRITICAL_COUNT if crit_count is None else crit_count
    ore_samples = ORE_SAMPLES if ore_samples is None else ore_samples
    prov = fetch.load_provenance(data_root)
    root = Path(data_root)
    curves = data.read_curves(root)
    series = calibration.series_of(curves)
    dates = curves.backtest_dates(book.BACKTEST_START, curves.last)
    if date_stride is not None:
        dates = dates[::-1][::date_stride][::-1]
    d_last = dates[-1]
    hqm = data.read_hqm([root / "raw" / fetch.HQM_DIR / n for n in fetch.HQM_FILES])
    if d_last[:7] not in hqm:
        raise treasury.DeclaredAbsence(f"the HQM end-of-month curve of {d_last[:7]} is not in the data root; fetch it from {fetch.HQM_PAGE}")
    ev = engine_version()
    reg = _registry_with_hqm()
    man = {"sources": {"treasury-par-curve": {"files": [{"name": r["name"], "sha256": r["sha256"]} for r in prov[fetch.TREASURY_DIR]]},
                       "treasury-hqm": {"files": [{"name": r["name"], "sha256": r["sha256"]} for r in prov[fetch.HQM_DIR]]}}}
    lineage = lin.build(CASE_ID, sources=list(SOURCES), truth_status="synthetic-calibrated", seed=seed, code_version=__version__,
                        riskvalidation_version=ev, manifest=man, reg=reg)
    lane = {"lane": "precompute", "reasons": []}

    # the backtest of the two books and the critical values under the model
    ids = [t[0] for t in book.TRADES]
    res = bt.run(curves, series, dates, seed, bt_paths, {"netting": ids, "single": [book.SINGLE_MEMBER]})
    _log(f"backtest: {len(dates)} dates, {bt_paths} paths")
    cvs = bt.critical_values(dates, res.fits, res.realised_dates, bt_paths, crit_count, seed)
    bt_blocks = {k: bt.backtest_document(res, k, cvs, bt_paths) for k in ("single", "netting")}
    bt_rows = {k: bt.test_rows(res, k, cvs) for k in ("single", "netting")}
    _log("backtest critical values done")

    # the curve date
    fit = res.fits[-1]
    tenors, zeros, par = curves.zero(d_last)
    trades = book.trades_at(par)
    swaps = book.swaps_of(trades)
    report = np.array(book.GRID)
    ccurve = credit.hqm_curve(hqm[d_last[:7]], tenors, zeros, report)
    stress_fit, stress = _stress(curves, series, hqm, book.STRESS_WINDOW[0], book.STRESS_WINDOW[1])
    cal_used = calibration.record(fit, d_last)
    curve_block = {
        "curve_date": d_last, "source": "US Treasury daily par yield curve (home.treasury.gov)", "licence_class": "mirror-allowed",
        "par_yield_unit": "decimal, bond-equivalent", "zero_compounding": "continuous",
        "points": [{"tenor_years": float(t), "par_yield": float(y), "zero_rate": float(z)}
                   for t, y, z in zip(par.tenors(), par.yields(), zeros, strict=True)],
        "tenors_present": [float(t) for t in par.tenors()], "tenors_absent": [float(t) for t in par.missing_tenors()],
        "interpolated_silently": False}
    ctx = {"trades": trades, "tenors": tenors, "zeros": zeros, "credit_curve": ccurve, "stress": stress, "curve_block": curve_block,
           "calibration_used": cal_used, "named": book.named_parameters(seed, n_paths, bt_paths, crit_count)}
    deltas = {10: book.closeout_years(10), 20: book.closeout_years(20)}

    # the other calibrations: stress and plus or minus one standard error (common random numbers)
    cases = [("stress", stress_fit.a, stress_fit.sigma), ("a-plus-1se", fit.a + fit.a_se, fit.sigma), ("a-minus-1se", fit.a - fit.a_se, fit.sigma),
             ("sigma-plus-1se", fit.a, fit.sigma + fit.sigma_se), ("sigma-minus-1se", fit.a, fit.sigma - fit.sigma_se)]
    if fit.a - fit.a_se <= 0.0 or fit.sigma - fit.sigma_se <= 0.0:
        raise ValueError(f"{d_last}: a or sigma minus one standard error is not positive, so the sensitivity case is undefined")
    others: dict[str, dict[str, dict[str, Any]]] = {}
    for name, a, s in cases:
        sim = xp.simulate(tenors, zeros, a, s, n_paths, seed, swaps, deltas)
        others[name] = {sp.variant: vt.core(sim, sp, seed, light=True).mx for sp in vt.SPECS}   # only the measures are kept
        del sim
        _log(f"calibration case {name} done")

    sim = xp.simulate(tenors, zeros, fit.a, fit.sigma, n_paths, seed, swaps, deltas)
    _log(f"base simulation: {n_paths} paths")
    cores = {sp.variant: vt.core(sim, sp, seed) for sp in vt.SPECS}
    ql_rows = reconcile.quantlib_rows(tenors, zeros, fit.a, fit.sigma)

    # ORE
    ore_blocks: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    ore_inputs: dict[str, dict[str, str]] = {}
    extra_rows: dict[str, list[dict[str, Any]]] = {sp.variant: [] for sp in vt.SPECS}
    work = Path(work_dir) if work_dir is not None else root / "ore-runs" / CASE_ID
    if run_ore:
        asof = ore.asof_for(int(d_last[5:7]))
        pd_cache = {}
        for sp in vt.SPECS:
            if sp.variant not in ORE_VARIANTS:
                continue
            c = cores[sp.variant]
            tr = [trades[i] for i in sp.members]
            spec = ore.Spec(sp.variant, asof, tenors, zeros, fit.a, fit.sigma, tr, sp.mpor, sp.im, report, ore_samples, seed)
            run_dir = work / sp.variant
            if run_dir.exists():
                shutil.rmtree(run_dir)
            ore_inputs[sp.variant] = ore.write_inputs(spec, run_dir)
            if ore_inputs_dir is not None:
                ore.write_inputs(spec, Path(ore_inputs_dir) / sp.variant)
            seconds, platform = ore.run(run_dir)
            _log(f"ORE {sp.variant}: {seconds:.0f} s")
            cva_blk = credit.cva_block(c.mx["ee_d"], c.my["ee_d"], c.x_d, c.y_d, report, ccurve, 0.6, 0.008, 0.6)
            scaled = None
            if sp.im:
                scaled = {"se": c.mx["ee_d_se"] * np.sqrt(n_paths / ore_samples)}
            out = reconcile.ore_result(run_dir, report.size, scaled)
            blk, rows, flags = reconcile.block(c, out, seconds, platform, ccurve, 0.6, cva_blk["cva"]["amount"], cva_blk["cva"]["mc_se"])
            if sp.im:
                rows += reconcile.im_block(blk, c, run_dir, flags)
            reconcile.finish(blk, flags)
            ore_blocks[sp.variant] = (blk, rows)
            if sp.mpor is not None and not sp.im:
                spec0 = ore.Spec(sp.variant, asof, tenors, zeros, fit.a, fit.sigma, tr, sp.mpor, False, report, ore_samples, seed, mta=0.0)
                d0 = work / f"{sp.variant}-mta0"
                if d0.exists():
                    shutil.rmtree(d0)
                ore_inputs[f"{sp.variant}-mta0"] = ore.write_inputs(spec0, d0)
                if ore_inputs_dir is not None:
                    ore.write_inputs(spec0, Path(ore_inputs_dir) / f"{sp.variant}-mta0")
                sec0, _ = ore.run(d0)
                c0 = vt.core(sim, sp, seed, None, mta=0.0, light=True)
                out0 = reconcile.ore_result(d0, report.size, None)
                extra_rows[sp.variant].append(reconcile.mta0_row(c0, out0, sec0))
                _log(f"ORE {sp.variant} with MTA 0: {sec0:.0f} s")
        del pd_cache

    values: dict[str, float] = {}
    docs: dict[str, dict[str, Any]] = {}
    for sp in vt.SPECS:
        c = cores[sp.variant]
        sens = [vt.sensitivity_case("base", fit.a, fit.sigma, c.mx)]
        for name, a, s in cases[1:]:
            sens.append(vt.sensitivity_case(name, a, s, others[name][sp.variant]))
        stress_eepe = others["stress"][sp.variant]["eepe"]
        blk, ore_rows = ore_blocks.get(sp.variant, (vt.not_applicable_ore(), []))
        if sp.variant in ORE_VARIANTS and sp.variant not in ore_blocks:
            raise RuntimeError(f"{sp.variant}: no ORE run, so the variant cannot be published (run_ore is off)")
        out = vt.outputs(c, ctx, stress_eepe, sens, blk, bt_blocks[sp.book_key], seed)
        rows = (vt.engine_rows(c, ccurve, 0.6, 3.0, book.PFE_QUANTILE) + bt_rows[sp.book_key] + ql_rows + ore_rows + extra_rows[sp.variant]
)
        rows = [{**r, "model_id": r.get("model_id") or vt.MODEL_ID} for r in rows]    # every row names the model it tests
        impact = {
            "sa_ccr_ead": {"value": out["sa_ccr"]["ead"]["amount"], "unit": "USD", "label": vt.text("SA-CCR exposure at default", "Exposición en incumplimiento SA-CCR")},
            "cva": {"value": out["cva_dva"]["cva"]["amount"], "unit": "USD", "label": vt.text("CVA", "CVA")},
            "eepe": {"value": out["exposure"]["eepe"]["amount"], "unit": "USD", "label": vt.text("Effective EPE", "EPE efectivo")}}
        docs[sp.variant] = build_artifact(case_id=CASE_ID, variant_id=sp.variant, model=_model_summaries(ev, fit.a, fit.sigma), outputs=out,
                                          tests=with_reference_text(rows), impact=impact, findings=vt.findings_of(rows), lineage=lineage, lane=lane)
        values[f"sa_ccr_ead_{sp.variant.replace('-', '_')}_usd"] = out["sa_ccr"]["ead"]["amount"]
        values[f"eepe_{sp.variant.replace('-', '_')}_usd"] = out["exposure"]["eepe"]["amount"]
        values[f"cva_{sp.variant.replace('-', '_')}_usd"] = out["cva_dva"]["cva"]["amount"]
        values[f"ba_cva_capital_{sp.variant.replace('-', '_')}_usd"] = out["ba_cva"]["capital"]["amount"]
        _log(f"{sp.variant}: EAD {out['sa_ccr']['ead']['amount']:.0f}, EEPE {out['exposure']['eepe']['amount']:.0f}, CVA {out['cva_dva']['cva']['amount']:.1f}")
    values["csa_10d_over_netting_eepe"] = values["eepe_csa_mpor_10d_usd"] / values["eepe_netting_set_usd"]
    records = [calibration.record(f, d) for f, d in zip(res.fits, dates, strict=True)]
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=_model_summaries(ev, fit.a, fit.sigma), fit=models.fit_block(records),
                                       lineage=lineage, lane=lane)
    models_doc["model"][0]["details"] = {"curve_date": d_last, "backtest_dates": len(dates)}
    flat = [r for rows in prov.values() for r in rows]
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The rows of data/sources/manifest.json for the raw inputs of C12, in that file's format. The raw files stay in the "
                           "device data root (outside the repository); each file record is measured on the bytes when the bake reads it "
                           "(a record written by a fetch is checked against them), and the bake refuses a file whose bytes differ from it. "
                           "treasury-hqm is proposed to the source registry in changes/U9-P1.md.",
                   "sources": {sid: {"name": reg[sid].name, "publisher": reg[sid].publisher, "landing": reg[sid].landing,
                                     "class": reg[sid].klass, "licence": reg[sid].licence, "attribution": reg[sid].attribution,
                                     "access": reg[sid].access, "files": rows}
                               for sid, rows in (("treasury-par-curve", prov[fetch.TREASURY_DIR]), ("treasury-hqm", prov[fetch.HQM_DIR]))}}
    assert sum(len(v["files"]) for v in raw_sources["sources"].values()) == len(flat)
    cv = c1.validate("curve", [{"date": d_last, "tenor_years": float(a), "rate": float(b), "compounding": "semiannual"}
                              for a, b in zip(par.tenors(), par.yields(), strict=True)])
    if not cv.ok or cv.rejected:
        raise ValueError(f"{d_last}: contract 1 rejects the curve: {cv.counts()}")
    contract = {"treasury-par-curve": cv.summary()}
    return Built(models_doc, docs, raw_sources, contract, values, ore_inputs)


def _semantics():
    repo = Path(__file__).resolve().parents[4]
    path = str(repo / "tests" / "contracts_u9")
    if path not in sys.path:
        sys.path.insert(0, path)
    import semantics

    return semantics


def _check_and_write(root: Path, rel: str, doc: dict[str, Any], kind: str) -> dict[str, Any]:
    """Schema, then the semantic checks of the contract, then the write; any finding refuses the document."""
    validate_document(f"data/derived/{rel}", doc)
    sem = _semantics()
    found = sem.check_c12(doc) if kind == "variant" else sem.check_c12_models(doc)
    if found:
        raise ValueError(f"{rel}: the contract's checks refuse the document: {found[:5]}")
    return write_artifact(root, rel, doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


TITLES = {
    "single-swap": ("Single swap", "Una sola permuta", "One 10 year payer swap of 10M USD, uncollateralised.", "Una permuta pagadora a 10 años de 10M USD, sin colateral."),
    "netting-set": ("Netting set", "Conjunto de neteo", "Four swaps under one netting agreement, uncollateralised.", "Cuatro permutas bajo un acuerdo de neteo, sin colateral."),
    "csa-mpor-10d": ("CSA, MPoR 10 days", "CSA, MPoR de 10 días", "The netting set under a CSA with a margin period of risk of 10 business days.", "El conjunto de neteo bajo un CSA con periodo de margen de riesgo de 10 días hábiles."),
    "csa-mpor-20d": ("CSA, MPoR 20 days", "CSA, MPoR de 20 días", "The netting set under a CSA with a margin period of risk of 20 business days.", "El conjunto de neteo bajo un CSA con periodo de margen de riesgo de 20 días hábiles."),
    "with-im": ("With initial margin", "Con margen inicial", "The 10 day CSA with a dynamic initial margin (a regression proxy, not SIMM).", "El CSA de 10 días con margen inicial dinámico (una aproximación por regresión, no SIMM)."),
    "wrong-way-risk": ("Wrong-way risk", "Riesgo de correlación adversa", "The netting set with a counterparty hazard that rises with the portfolio value.", "El conjunto de neteo con una tasa de riesgo de la contraparte que sube con el valor del portafolio."),
}


#: the regime of every C12 document in the manifest (R4 c15 B1: "permutas" in Spanish, ruling 6 of 2026-10-27)
REGIME = vt.text("US Treasury curves read up to the date, a synthetic USD swap book, ORE and QuantLib as references.",
                 "Curvas del Tesoro de EE. UU. leídas hasta la fecha, un libro sintético de permutas en USD, ORE y QuantLib como referencias.")


def bake_case(seed: int, paths: Any, data_root: Path | str | None, ore_inputs_dir: Path | None = None, **kw: Any) -> dict[str, Any]:
    built = build(seed, data_root, ore_inputs_dir=INPUT_DIR_DEFAULT if ore_inputs_dir is None else ore_inputs_dir, **kw)
    root = Path(paths.root)
    entries, sums = [], []
    regime = REGIME
    e = _check_and_write(root, MODELS_REL, built.models, "models")
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "synthetic-calibrated",
                    "title": vt.text("Calibrations of the Hull-White model, 2000 to 2025", "Calibraciones del modelo Hull-White, 2000 a 2025"),
                    "short_title": vt.text("Models", "Modelos"), "regime": regime, "path": MODELS_REL, **e})
    for sp in vt.SPECS:
        rel = f"{CASE_ID}/{sp.variant}.json"
        e = _check_and_write(root, rel, built.variants[sp.variant], "variant")
        sums.append(_sum(root, rel))
        en, es, _, _ = TITLES[sp.variant]
        entries.append({"role": "variant", "variant_id": sp.variant, "truth_status": "synthetic-calibrated",
                        "title": vt.text(en, es), "short_title": vt.text(en, es), "regime": regime, "models_ref": MODELS_REL, **e})
        _log(f"{sp.variant}: {e['bytes']:,} bytes")
    sem = _semantics()
    found = sem.check_c12_variants({"documents": [built.variants[sp.variant] for sp in vt.SPECS]})
    if found:
        raise ValueError(f"the six variants disagree: {found[:5]}")
    write_json(root / RAW_REL, built.raw_sources)
    sums.append(_sum(root, RAW_REL))
    (root / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built.values)
    from . import CASE
    from ...registry import category as registry_category

    manifest = build_case_manifest(
        depends_on=CASE.depends_on(),
        case_id=CASE_ID, title=dict(CASE.title), category=dict(registry_category(CASE.category_id)),
        question=dict(CASE.question), sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT,
        contract=built.contract, expect=ranges, riskvalidation_version=engine_version(), source_details=_source_details(SOURCES))
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest


INPUT_DIR_DEFAULT = ore.INPUT_DIR


def _source_details(ids: tuple[str, ...]) -> dict[str, dict[str, str]]:
    reg = _registry_with_hqm()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}
