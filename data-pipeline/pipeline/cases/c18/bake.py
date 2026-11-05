"""The C18 bake: the capital of Banco Andino under the Fed, EBA and NGFS scenarios, aggregated across credit, market, IRRBB and operational risk.

``build`` makes every document in memory from the raw files of the device data root (``fetch`` wrote them) and the committed documents of C07, C11,
C15 and C17; ``bake_case`` writes them with the checksums, the raw-source record and the manifest. The six variants: the Fed 2026 baseline, the EBA/ESRB
2025 adverse, the Fed 2026 severely adverse and the NGFS Phase 5 Delayed transition (the four scenario documents), the t-copula aggregation on the
baseline and the reverse stress. Every document passes its schema, ``tests/contracts_u13/semantics.py`` ``violations`` and, across the set,
``cross_violations`` before it is written.

Missing data (the Missing data paragraph of the U13 sizing): an absent NGFS read leaves the NGFS variant unwritten and an absent EBA workbook does the
same for its variant, the other variants unaffected, each named with its URL in ``Built.skipped``; an absent Federal Reserve table, charge-off page or
EUR to CLP series, a missing committed document of C07, C15 or C17, or a CMF target that cannot be read, stops C18 whole.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
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
from ...io import contract as c1
from ...io import sources as registry
from ...io.formats import write_json
from ...registry import CATEGORIES
from ...stages.export import write_artifact
from . import aggregation as agg
from . import anchors as anc
from . import capital as cap
from . import documents as docs
from . import documents_more as docs2
from . import eba as eba_reader
from . import fed as fed_reader
from . import fetch, fx, marginals as mg, models, ngfs as ngfs_reader, reverse as rev
from . import params as P
from . import satellites as sat
from . import stress_rungs
from . import scenarios as scn

CASE_ID = P.CASE_ID
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 600_000.0
EXACT = frozenset({"outputs", "fit", "tests"})
SOURCES = ("fed-stress-tests", "fed-chargeoff", "eba-esrb-stress-2025", "ngfs-phase-v", "bcch-bde")
#: what a reader should see, declared before the bake and wide on purpose (a result outside is a finding to read, not to tune away)
EXPECT: dict[str, tuple[float, float]] = {
    "headline_capital_over_rwa": (0.02, 0.30),
    "gaussian_over_simple_sum": (0.40, 1.0),
    "cet1_ratio_end_fed_severe": (-0.20, 0.11),
    "pe_ratio_start": (0.10, 0.25),
    "reverse_mahalanobis_distance": (0.1, 12.0),
}
_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C18 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


@dataclass
class Built:
    models: dict[str, Any]
    variants: dict[str, dict[str, Any]]
    values: dict[str, float]
    raw_sources: dict[str, Any]
    contract: dict[str, Any]
    skipped: dict[str, str] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)


def engine_version() -> str:
    """The engine version with the commit that pins it (requirements.txt), so a document names the code that computed it."""
    try:
        ver = md.version("riskvalidation")
    except md.PackageNotFoundError:
        ver = "not installed"
    req = (Path(__file__).resolve().parents[4] / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = re.search(r"CAOS_RiskValidation\.git@([0-9a-f]{40})", req)
    return f"{ver}+{m.group(1)[:7]}" if m else ver


def _provenance(data_root: Path | str) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    """The sidecars of the files that stop C18 whole, and the reason for each optional folder that is not there."""
    prov = fetch.load_provenance(data_root, (fetch.FED_HIST_DIR, fetch.CHARGEOFF_DIR, fetch.FX_DIR))
    skipped: dict[str, str] = {}
    for key, folder, url in (("eba", fetch.EBA_DIR, fetch.EBA_URL), ("ngfs", fetch.NGFS_DIR, fetch.NGFS_BASE)):
        try:
            prov.update(fetch.load_provenance(data_root, (folder,)))
        except (FileNotFoundError, ValueError) as exc:
            skipped[key] = f"the source did not answer or is not in the data root ({exc}); fetch it from {url}"
    return prov, skipped


def _contract_summaries(scen: dict[str, scn.Scenario], rates: fed_reader.Rates, fxrate: Any) -> dict[str, Any]:
    """Contract 1 over what the readers produced: the published scenario points (macro_path) and the EUR to CLP series (market_series)."""
    out: dict[str, Any] = {}
    for key, source in (("baseline", "fed-stress-tests"), ("eba", "eba-esrb-stress-2025"), ("ngfs", "ngfs-phase-v")):
        if key not in scen:
            continue
        recs = [{"scenario": scen[key].scenario_id, "date": pt["date"], "variable": p["variable"], "value": pt["value"], "unit": p["unit"],
                 "vintage_date": p["vintage_date"]} for p in scen[key].block["paths"] for pt in p["source"]]
        rep = c1.validate("macro_path", recs, params={"observation_date": P.AS_OF})
        if not rep.ok or rep.rejected:
            raise ValueError(f"{source}: contract 1 rejects the scenario reader's output: {rep.counts()}")
        out[source] = rep.summary()
    qs = rates.quarters
    recs = [{"date": q, "series_id": f"fed-chargeoff-{lt}", "value": float(rates.rates[lt][i]), "unit": "rate"}
            for lt in P.FED_TYPES for i, q in enumerate(qs) if np.isfinite(rates.rates[lt][i])]
    rep = c1.validate("market_series", recs)
    if rep.rejected:
        raise ValueError(f"fed-chargeoff: contract 1 rejects the charge-off reader's output: {rep.counts()}")
    out["fed-chargeoff"] = rep.summary()
    return out


def build(seed: int, data_root: Path | str | None, *, n_draws: int | None = None, n_paths: int | None = None, derived: Path | None = None,
          only: tuple[str, ...] | None = None) -> Built:
    """Every document of the case in memory. A missing optional source leaves its variant unwritten; a missing required one stops the case."""
    if data_root is None:
        raise FileNotFoundError("C18 reads the raw files of the device data root: pass --data-root or set CONTRASTE_DATA")
    n_draws = P.N_DRAWS if n_draws is None else n_draws
    n_paths = P.N_PATHS_IRRBB if n_paths is None else n_paths
    anchors = anc.load_anchors(derived)
    prov, skipped = _provenance(data_root)
    fed = fed_reader.read_inputs(data_root)
    rates = fed_reader.read_chargeoffs(data_root)
    fxrate = fx.read_rate(data_root)
    _log(f"inputs read; skipped {sorted(skipped)}")
    sats = sat.fit_all(rates, fed)
    space = rev.factor_space(fed.history)
    ev = engine_version()
    marg = mg.all_marginals(anchors, fxrate.value, n_draws, n_paths)
    _log("marginals: " + ", ".join(f"{m.risk} EC {m.ec:,.0f}" for m in marg))
    op = next(m for m in marg if m.risk == "operational")
    named = models.named_parameters(anchors, fxrate, op.extras, mg.market_scaling())
    corr_base, corr_stress = named["correlation_matrix_base"]["matrix"], named["correlation_matrix_stress"]["matrix"]
    band_base = agg.run_band(marg, corr_base, P.NU_SET, n_draws, seed)
    band_stress = agg.run_band(marg, corr_stress, P.NU_SET, n_draws, seed)
    agg_base = agg.aggregation_block(marg, named, "correlation_matrix_base", band_base, n_draws, seed)
    agg_stress = agg.aggregation_block(marg, named, "correlation_matrix_stress", band_stress, n_draws, seed)
    _log("band: " + ", ".join(f"{r.method}{'' if r.nu is None else r.nu} {r.capital:,.0f}" for r in band_base.rows))
    target = cap.internal_target(named, anchors)
    fit = models.fit_block(anchors, sats, space, named, marg[0].statement, n_draws, seed, mg.quantile_grid(marg))
    recs = [dict(m, details={"engine_commit": ev}) for m in models.model_summaries(ev)]
    backcasts = {lt: sat.backcast(s) for lt, s in sats.items()}
    flat = [r for rows in prov.values() for r in rows]
    by_folder = {fetch.FED_HIST_DIR: "fed-stress-tests", fetch.CHARGEOFF_DIR: "fed-chargeoff", fetch.EBA_DIR: "eba-esrb-stress-2025",
                 fetch.NGFS_DIR: "ngfs-phase-v", fetch.FX_DIR: "bcch-bde"}
    manifest_in = {"sources": {by_folder[f]: {"files": [{"name": r["name"], "sha256": r["sha256"]} for r in rows]} for f, rows in prov.items()}}
    used = [by_folder[f] for f in prov]
    lineage = lin.build(CASE_ID, sources=used, truth_status="synthetic-calibrated", seed=seed, code_version=__version__, riskvalidation_version=ev,
                        manifest=manifest_in)
    lane = {"lane": "precompute", "reasons": []}
    core = docs.Core(anchors, fed, sats, named, marg, band_base, band_stress, agg_base, agg_stress, target, float(anchors.c15["thresholds"]["net_interest_and_indexation_margin_12m"]),
                     np.array(anchors.stage_balances_clp_m), anchors.class_lgd, backcasts, sat.descriptive_2026(rates), space, ev, recs, lineage, lane, seed, n_draws)
    scen: dict[str, scn.Scenario] = {"baseline": scn.fed_scenario("baseline", fed), "fed": scn.fed_scenario("fed", fed)}
    if "eba" not in skipped:
        scen["eba"] = scn.eba_scenario(fed, eba_reader.read_workbook(Path(data_root) / "raw" / fetch.EBA_DIR / fetch.EBA_NAME))
    if "ngfs" not in skipped:
        variables, _facts = ngfs_reader.read_runs(data_root)
        scen["ngfs"] = scn.ngfs_scenario(fed, variables)
    for s in scen.values():
        scn.check_vintages(s.block)
    contract = _contract_summaries(scen, rates, fxrate)
    out: dict[str, dict[str, Any]] = {}
    results: dict[str, Any] = {}
    base_totals: list[float] | None = None
    base_nii: list[float] | None = None
    for key in ("baseline", "eba", "fed", "ngfs"):
        if key not in scen:
            continue
        r = docs.scenario_document(core, scen[key], base_totals, base_nii)
        if key == "baseline":
            base_totals, base_nii = r["total_losses"], r["nii"]
        vid = P.SCENARIOS[key]
        results[vid] = r
        out[vid] = build_artifact(case_id=CASE_ID, variant_id=vid, model=docs.envelope_models(core), outputs=r["outputs"], tests=r["tests"], impact=r["impact"],
                                  findings=r["findings"], lineage=lineage, lane=lane)
        _log(f"{vid}: total 3-year loss {sum(r['total_losses']):,.0f}, CET1 path {[round(x) for x in r['cet1_path']]}")
    a = docs2.aggregation_document(core)
    out[P.FILE_NAMES["aggregation"]] = build_artifact(case_id=CASE_ID, variant_id=P.FILE_NAMES["aggregation"], model=docs.envelope_models(core), outputs=a["outputs"],
                                                      tests=a["tests"], impact=a["impact"], findings=a["findings"], lineage=lineage, lane=lane)

    def credit_loss(x: np.ndarray) -> float:
        tr = {name: scen["baseline"].transposed[name] + x[i] for i, name in enumerate(P.REGRESSORS)}
        proj = sat.project_all(sats, tr)
        return float(sum(sat.credit_losses(sat.class_rates(proj), anchors.class_exposure_clp_m)))

    other = sum((m.el or 0.0) for m in marg if m.risk not in ("credit", "irrbb"))
    ppnr_baseline = float(sum(results[P.SCENARIOS["baseline"]]["ppnr"]))

    def loss_fn(x: np.ndarray) -> float:
        """The three-year loss net of the baseline scenario's cumulative PPNR (decision Z10): the market and operational expected losses are the same in every variant."""
        return credit_loss(np.asarray(x, dtype=float)) + 3.0 * other - ppnr_baseline

    rv = None
    try:
        rv = docs2.reverse_document(core, loss_fn)
    except rev.NotEvaluated as exc:
        skipped["reverse"] = str(exc)
    if rv is not None:
        out[P.FILE_NAMES["reverse"]] = build_artifact(case_id=CASE_ID, variant_id=P.FILE_NAMES["reverse"], model=docs.envelope_models(core), outputs=rv["outputs"],
                                                      tests=rv["tests"], impact=rv["impact"], findings=rv["findings"], lineage=lineage, lane=lane)
    # the state-of-the-art stress rungs sit beside the OLS satellites in the models document only: the variants' own model list is unchanged
    rungs = stress_rungs.build(sats, fed.history)
    models_doc = build_models_artifact(case_id=CASE_ID, fit_id=P.FIT_ID, model=[*recs, *stress_rungs.records(ev, rungs)], fit=fit, lineage=lineage, lane=lane)
    reg = registry.load()
    raw_sources = {"schema": "contraste.sources-manifest-rows/v1",
                   "note": "The rows of data/sources/manifest.json for the raw inputs of C18, in that file's format. The raw files stay in the device data root "
                           "(outside the repository); each file record is the one written when it was fetched, and the bake refuses a file whose bytes differ from it. "
                           "The Federal Reserve files were fetched by other cases; their retrieval date is the file's last write.",
                   "sources": {by_folder[f]: {"name": reg[by_folder[f]].name, "publisher": reg[by_folder[f]].publisher, "landing": reg[by_folder[f]].landing,
                                              "class": reg[by_folder[f]].klass, "licence": reg[by_folder[f]].licence, "attribution": reg[by_folder[f]].attribution,
                                              "access": reg[by_folder[f]].access, "files": rows} for f, rows in prov.items()}}
    assert sum(len(v["files"]) for v in raw_sources["sources"].values()) == len(flat)
    fed_v = results[P.SCENARIOS["fed"]]
    pe0 = (anchors.cet1_clp_m + anchors.at1_clp_m + anchors.t2_clp_m) / anchors.rwa_clp_m
    gauss = next(r for r in band_base.rows if r.method == "gaussian-copula")
    values = {"headline_capital_over_rwa": band_base.headline / anchors.rwa_clp_m, "gaussian_over_simple_sum": gauss.capital / band_base.headline,
              "cet1_ratio_end_fed_severe": fed_v["cet1_path"][-1] / anchors.rwa_clp_m, "pe_ratio_start": pe0,
              "reverse_mahalanobis_distance": rv["solution"].distance if rv else 1.0}
    if only is not None:
        out = {k: v for k, v in out.items() if k in only}
    return Built(models_doc, out, values, raw_sources, contract, skipped, {"core": core, "scenarios": scen, "reverse": rv, "aggregation": a, "scenario": results})


# ------------------------------------------------------------------------------------------------ checks and writing


def _semantics():
    """The cross-field checks of the contract (``tests/contracts_u13/semantics.py``), loaded by path under a name of their own: several suites ship a
    helper called ``semantics`` and Python would hand back the one it cached first."""
    import importlib.util

    name = "c18_semantics"
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parents[4] / "tests" / "contracts_u13" / "semantics.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def check_set(built: Built) -> list[str]:
    """``violations`` of every document and ``cross_violations`` across the set; a non-empty list refuses the bake."""
    sem = _semantics()
    keymap = {P.SCENARIOS[k]: k for k in P.SCENARIOS}
    keymap[P.FILE_NAMES["aggregation"]] = "aggregation"
    keymap[P.FILE_NAMES["reverse"]] = "reverse"
    found, docs_by_key = [], {"models": built.models}
    for vid, doc in built.variants.items():
        found += [f"{vid}: {m}" for m in sem.violations(doc)]
        docs_by_key[keymap[vid]] = doc
    found += [f"models: {m}" for m in sem.violations(built.models)]
    found += [f"set: {m}" for m in sem.cross_violations(docs_by_key)]
    return found


def _check_and_write(root: Path, rel: str, doc: dict[str, Any]) -> dict[str, Any]:
    validate_document(f"data/derived/{rel}", doc)
    return write_artifact(root, rel, doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def bake_case(seed: int, paths: Any, data_root: Path | str | None, n_draws: int | None = None, n_paths: int | None = None) -> dict[str, Any]:
    built = build(seed, data_root, n_draws=n_draws, n_paths=n_paths)
    found = check_set(built)
    if found:
        raise ValueError(f"C18: the checks of the contract refuse the bake ({len(found)} findings): {found[:6]}")
    for key, why in built.skipped.items():
        _log(f"SKIPPED the {key} variant: {why}")
    root = Path(paths.root)
    entries, sums = [], []
    regime = P.text("Fed, EBA and NGFS paths transposed onto the last observed value, satellites fitted on 1985 to 2019; Banco Andino is synthetic and the satellites are a "
                    "US-calibrated adaptation.",
                    "Trayectorias Fed, EBA y NGFS trasladadas al último valor observado, satélites ajustados sobre 1985 a 2019; Banco Andino es sintético y los satélites son una "
                    "adaptación calibrada en EE. UU.")
    e = _check_and_write(root, P.MODELS_REL, built.models)
    sums.append(_sum(root, P.MODELS_REL))
    entries.append({"role": "models", "variant_id": f"models-{P.FIT_ID}", "truth_status": "synthetic-calibrated",
                    "title": P.text("Fitted satellites, aggregation parameters and anchors", "Satélites ajustados, parámetros de agregación y anclas"),
                    "short_title": P.text("Models", "Modelos"), "regime": regime, "path": P.MODELS_REL, **e})
    titles = {
        P.SCENARIOS["baseline"]: ("Baseline (Fed 2026)", "Base (Fed 2026)"), P.SCENARIOS["eba"]: ("EBA 2025 adverse", "Adverso EBA 2025"),
        P.SCENARIOS["fed"]: ("Fed 2026 severely adverse", "Severamente adverso Fed 2026"), P.SCENARIOS["ngfs"]: ("NGFS delayed transition", "Transición tardía NGFS"),
        P.FILE_NAMES["aggregation"]: ("t-copula aggregation", "Agregación con cópula t"), P.FILE_NAMES["reverse"]: ("Reverse stress", "Tensión inversa")}
    # the chip of the variant in the rail is one line of the rail's width, in the wide font too (ADR-0071): the Spanish title of the Fed
    # scenario is 28 characters and overran it by 25 px, so its short title is the shorter wording (the title stays whole)
    short_es = {P.SCENARIOS["fed"]: "Fed 2026 severo"}
    for vid in [*P.SCENARIOS.values(), P.FILE_NAMES["aggregation"], P.FILE_NAMES["reverse"]]:
        if vid not in built.variants:
            continue
        rel = f"{P.CASE_ID}/{vid}.json"
        e = _check_and_write(root, rel, built.variants[vid])
        sums.append(_sum(root, rel))
        en, es = titles[vid]
        entries.append({"role": "variant", "variant_id": vid, "truth_status": "synthetic-calibrated", "title": P.text(en, es), "short_title": P.text(en, short_es.get(vid, es)),
                        "regime": regime, "models_ref": P.MODELS_REL, **e})
        _log(f"{vid}: {e['bytes']:,} bytes")
    write_json(root / P.RAW_REL, built.raw_sources)
    sums.append(_sum(root, P.RAW_REL))
    (root / P.SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    ranges = expectations.check(CASE_ID, EXPECT, built.values)
    from . import CASE

    manifest = build_case_manifest(
        depends_on=CASE.depends_on(),
        case_id=CASE_ID, title=_title(), category=CATEGORIES["capital-stress"], question=_question(),
        sources=[s for s in SOURCES if s in built.raw_sources["sources"]], seed=seed, variants=entries, default_variant=P.DEFAULT_VARIANT,
        contract=built.contract, expect=ranges, riskvalidation_version=engine_version(),
        source_details=_source_details([s for s in SOURCES if s in built.raw_sources["sources"]]))
    write_json(paths.manifests / f"{CASE_ID}.json", manifest)
    return manifest


def _title() -> dict[str, str]:
    from . import CASE

    return dict(CASE.title)


def _question() -> dict[str, str]:
    from . import CASE

    return dict(CASE.question)


def _source_details(ids: list[str]) -> dict[str, dict[str, str]]:
    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence, "class": reg[i].klass,
                "attribution": reg[i].attribution} for i in ids}
