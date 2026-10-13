"""The C07 bake: the synthetic Banco Andino under CMF B-1, IFRS 9 and BdE Annex 9, six scenario variants.

``build`` makes every document in memory (no input or output file but the committed targets); ``bake`` writes them, the
checksums and the manifest. The documents are the c07-models and c07-outputs contracts (docs/contracts/schemas/c07/).
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
from . import documents as docs
from . import generator, ifrs9, scenarios, sources

CASE_ID = "C07"
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 30_000.0
MODELS_REL = f"{CASE_ID}/models-banco-andino.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"

#: what a reader should see, declared before the bake (CT-207 form); ranges are wide where the result is a finding
EXPECT: dict[str, tuple[float, float]] = {
    "calibration_max_relative_error": (0.0, 0.01),
    "weights_sum": (1.0 - 1e-9, 1.0 + 1e-9),
    "bridge_max_abs_residual_clp": (0.0, 1.0),
    "rollforward_max_residual_clp": (0.0, 1e-3),
    "base_ifrs9_over_b1": (0.4, 1.5),
    "recession_ifrs9_over_b1": (0.5, 2.0),
    "combined_severe_ifrs9_over_b1": (0.8, 2.5),
    "recession_b1_over_base": (1.0, 2.0),
    "combined_severe_bde_over_base": (1.0, 5.0),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C07 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def build(seed: int, scale: float = 1.0, *, log: bool = False) -> dict[str, Any]:
    """Every document of the case in memory: ``{"models": doc, "variants": {id: doc}, "values": {...}, "book": Book}``."""
    sources.validate_targets()
    scenarios.validate_scenarios()
    rv = docs.rv_version()
    say = _log if log else (lambda _m: None)
    book = generator.generate(seed, scale)
    say(f"book: {book.n:,} accounts, {book.e.sum():,.0f} CLP, sha256 {book.digest()[:12]}")
    evs: dict[str, dict[str, Any]] = {}
    for s in scenarios.SCENARIOS:
        evs[s["id"]] = docs.evaluate(book, s)
        say(f"evaluated {s['id']}")
    base = evs["base"]
    overlays = ifrs9.overlays_for(base["ifrs"], book, docs.CURRENCY)
    outs: dict[str, dict[str, Any]] = {}
    rows_by: dict[str, list[dict[str, Any]]] = {}
    rolls: dict[str, dict[str, Any]] = {}
    for sid, ev in evs.items():
        roll = ifrs9.rollforward(base["ifrs"], ev["ifrs"], book, overlays)
        rolls[sid] = roll
        out = docs.variant_outputs(book, ev, base, overlays, roll)
        outs[sid] = out
        rows_by[sid] = ifrs9.battery_rows(ev["ifrs"], book, ev["state"], overlays, roll, "IFRS9-ecl")
    models = docs.models_document(book, base, overlays, rv)
    variants: dict[str, dict[str, Any]] = {}
    for sid, out in outs.items():
        scen = scenarios.scenario(sid)
        rows = rows_by[sid]
        lineage = lin.build(CASE_ID, sources=[], truth_status="synthetic-calibrated", seed=seed, code_version=__version__,
                            riskvalidation_version=rv, generators=(docs.GENERATOR,))
        variants[sid] = build_artifact(
            case_id=CASE_ID, variant_id=sid, model=docs.model_summaries(out, rv, scen), outputs=out, tests=rows, impact=docs.impact(out),
            findings=docs.findings(out, rows, {"ifrs9": "IFRS9-ecl"}), lineage=lineage, lane={"lane": "precompute", "reasons": []})
    models_doc = _models_artifact(models, seed, rv)
    values = _values(models, outs, rows_by)
    return {"models": models_doc, "variants": variants, "values": values, "book": book, "evaluations": evs, "overlays": overlays}


def _models_artifact(models: dict[str, Any], seed: int, rv: str) -> dict[str, Any]:
    lineage = lin.build(CASE_ID, sources=[], truth_status="synthetic-calibrated", seed=seed, code_version=__version__,
                        riskvalidation_version=rv, generators=(docs.GENERATOR,))
    return build_models_artifact(case_id=CASE_ID, fit_id=models["fit_id"], model=models["model"], fit=models["fit"], lineage=lineage,
                                 lane={"lane": "precompute", "reasons": []})


def _values(models: dict[str, Any], outs: dict[str, dict[str, Any]], rows_by: dict[str, list[dict[str, Any]]]) -> dict[str, float]:
    targets = models["fit"]["calibration_targets"]
    err = []
    for t in targets:
        tol_ok = abs(t["achieved"] - t["target"]) / t["target"]
        err.append(tol_ok)
    tot = {sid: {r["regime"]: r["total_provision"] for r in o["regimes"]} for sid, o in outs.items()}
    resid = max(abs(sum(s["amount"] for s in o["gap_bridge"]["steps"]) - (tot[sid]["ifrs9"] - tot[sid]["cmf-b1"])) for sid, o in outs.items())
    roll = max(r["metric"] for rows in rows_by.values() for r in rows if r["test_id"] == "ifrs9.reconciliation_identities")
    w = sum(c["weight"] for c in outs["base"]["ifrs9_detail"]["weighted_components"])
    return {
        "calibration_max_relative_error": max(err), "weights_sum": w, "bridge_max_abs_residual_clp": resid,
        "rollforward_max_residual_clp": roll,
        "base_ifrs9_over_b1": tot["base"]["ifrs9"] / tot["base"]["cmf-b1"],
        "recession_ifrs9_over_b1": tot["recession"]["ifrs9"] / tot["recession"]["cmf-b1"],
        "combined_severe_ifrs9_over_b1": tot["combined-severe"]["ifrs9"] / tot["combined-severe"]["cmf-b1"],
        "recession_b1_over_base": tot["recession"]["cmf-b1"] / tot["base"]["cmf-b1"],
        "combined_severe_bde_over_base": tot["combined-severe"]["bde-annex9"] / tot["base"]["bde-annex9"],
    }


_REGIME_TEXT = {
    "base": ("Base: the three regimes on the reporting-date state of the book", "Base: los tres regímenes sobre el estado de la cartera a la fecha de reporte"),
    "recession": ("Recession: factor -1.0, house prices -5%", "Recesión: factor -1,0, precios de viviendas -5 %"),
    "consumer-arrears-shock": ("Consumer arrears shock: 3% of consumer accounts in default", "Shock de mora de consumo: 3 % de las cuentas de consumo en incumplimiento"),
    "house-price-fall": ("House price fall of 15%: collateral values", "Caída de 15 % de los precios de viviendas: valores de garantías"),
    "uf-inflation-spike": ("UF inflation 4 points above base", "Inflación UF 4 puntos sobre el base"),
    "combined-severe": ("Combined severe: factor -2.0, house prices -25%", "Severo combinado: factor -2,0, precios de viviendas -25 %"),
}


def bake_case(seed: int, paths: Any, data_root: Path | None, scale: float, title: dict[str, str], question: dict[str, str]) -> dict[str, Any]:
    built = build(seed, scale, log=True)
    _check_raw(data_root)
    entries: list[dict[str, Any]] = []
    sums: list[str] = []
    exact = docs.EXACT
    models = built["models"]
    e = write_artifact(paths.root, MODELS_REL, models, exact=exact, engines=ENGINES, run_ms=RUN_MS)
    sums.append(_sum(paths.root, MODELS_REL))
    entries.append({"role": "models", "variant_id": "models-banco-andino", "truth_status": "synthetic-calibrated",
                    "title": docs.T("Banco Andino: the synthetic bank, the calibration and the transcribed regime tables",
                                    "Banco Andino: el banco sintético, la calibración y las tablas transcritas de cada régimen"),
                    "short_title": docs.T("Models", "Modelos"),
                    "regime": docs.T("The synthetic bank, its calibration targets and the B-1, IFRS 9 and Annex 9 parameters",
                                     "El banco sintético, sus objetivos de calibración y los parámetros de B-1, IFRS 9 y Anejo 9"),
                    "path": MODELS_REL, **e})
    for s in scenarios.SCENARIOS:
        sid = s["id"]
        rel = f"{CASE_ID}/{sid}.json"
        e = write_artifact(paths.root, rel, built["variants"][sid], exact=exact, engines=ENGINES, run_ms=RUN_MS)
        sums.append(_sum(paths.root, rel))
        _log(f"variant {sid}: {e['bytes']:,} bytes")
        en, es_ = _REGIME_TEXT[sid]
        entries.append({"role": "variant", "variant_id": sid, "title": s["label"], "short_title": s["label"],
                        "regime": docs.T(en, es_), "truth_status": "synthetic-calibrated", "models_ref": MODELS_REL, **e})
    (Path(paths.root) / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built["values"])
    manifest = build_case_manifest(
        case_id=CASE_ID, title=title, category={"en": "Provisions", "es": "Provisiones"}, question=question, sources=[], seed=seed,
        variants=entries, default_variant="base", contract={}, expect=ranges, riskvalidation_version=docs.rv_version(), source_details={})
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def _check_raw(data_root: Path | None) -> None:
    """The fetched CMF publications, when the device data root holds them, must be the ones whose hash the targets carry."""
    if data_root is None:
        return
    for key, pub in sources.PUBLICATIONS.items():
        f = Path(data_root) / "raw" / "cmf-public" / pub["file"]
        if f.exists():
            got = hashlib.sha256(f.read_bytes()).hexdigest()
            if got != pub["sha256"]:
                raise ValueError(f"{f}: sha256 {got} is not the {key} publication the calibration targets name ({pub['sha256']})")
            _log(f"raw {pub['file']}: sha256 verified")
