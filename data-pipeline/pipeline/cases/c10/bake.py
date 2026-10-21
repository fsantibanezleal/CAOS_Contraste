"""The C10 bake: the Federal Reserve charge-off rates by loan type, the Vasicek fit on 1985-2006, the 2007-2012 tail, the
illustrative portfolio's ladder, and the simulator's correlation grid, every number through ``riskvalidation``.

``build`` makes every document in memory from a parsed table; ``bake_case`` reads the saved page, checks it against the pinned
one, writes the documents, the checksums and the manifest. The documents are the c10-outputs, c10-outputs-grid and c10-models
contracts (docs/contracts/schemas/c10/). The full bake runs locally, never in CI (ADR-0074); the tests run ``build`` at a small
scale on a committed sample of the Board's page.

    python -m pipeline.cases.c10.bake --output <dir> [--data-root <dir>] [--scale 1.0] [--seed 42]   (from data-pipeline/)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
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
from . import fed, ladder, simulator
from . import params as P

CASE_ID = P.CASE_ID
ENGINES = {"numpy", "scipy", "riskvalidation"}
RUN_MS = 1_800_000.0
MODELS_REL = f"{CASE_ID}/models-c10.json"
SUMS_REL = f"{CASE_ID}/SHA256SUMS.txt"
SOURCES_REL = f"{CASE_ID}/SOURCES.txt"
TEST_GRID = (0.08, 0.12, 0.16)
#: money keys written without nine-digit compaction: identities close on them to better than the compaction error
EXACT = frozenset({"log_likelihood", "max_log_likelihood", "cutoff"})

#: what a reader should see, declared before the bake (CT-207 form); ranges are wide where the result is a finding
EXPECT: dict[str, tuple[float, float]] = {
    "commercial_industrial_pd_hat": (0.004, 0.012),
    "commercial_real_estate_pd_hat": (0.0002, 0.006),
    "residential_pd_hat": (0.0005, 0.004),
    "credit_cards_pd_hat": (0.02, 0.07),
    "other_consumer_pd_hat": (0.005, 0.015),
    "delta_xi_025_q_999": (4.825, 4.835),
    "size_ml_22_at_null": (0.0, 0.30),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C10 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


class RawError(ValueError):
    """The saved page is not the one the case pins."""


def check_raw(path: Path, table: fed.Table, raw: dict[str, Any], log=lambda _m: None) -> None:
    """The saved page must be the pinned bytes, or carry the pinned numbers over the years used (CT-1111)."""
    first, last = P.FIT["first_year"], P.EVALUATION["last_year"]
    digest = fed.window_digest(table, first, last)
    if raw["sha256"] == P.RAW["sha256"] and raw["bytes"] == P.RAW["bytes"]:
        if digest != P.RAW["window_sha256"]:
            raise RawError(f"{path}: the pinned bytes do not give the pinned window digest ({digest})")
        log(f"raw {path.name}: the pinned bytes ({raw['bytes']:,}), window digest verified")
        return
    if digest != P.RAW["window_sha256"]:
        raise RawError(f"{path}: other bytes ({raw['sha256'][:12]}) and other numbers over {first}-{last} "
                       f"({digest[:12]}, pinned {P.RAW['window_sha256'][:12]}): the Board revised the history; refresh the pin on purpose")
    log(f"raw {path.name}: other bytes than the pin (a per-request script token), same numbers over {first}-{last}")


def seeds_for(seed: int) -> dict[str, int]:
    off = (int(seed) - 42) * 10_000
    return {k: v + off for k, v in P.SEEDS.items()}


def lineage(seed: int, rv: str, raw: dict[str, Any], truth: str, illustrative: bool) -> lin.Lineage:
    """The provenance: the Board's page by name and hash (the licence manifest of the pipeline does not pin this source yet, so
    the input is built here from the saved page), and for a loan-type document the illustrative portfolio as a constructed input."""
    inputs = (lin.Input(P.RAW["source"], "mirror-allowed", ((str(raw["name"]), str(raw["sha256"])),)),) if truth == "real-outcomes" else ()
    gens = ("contraste.c10.illustrative-portfolio",) if illustrative else (P.GENERATOR,)
    return lin.Lineage(CASE_ID, truth, inputs, int(seed), __version__, rv, gens)


def add_illustrative_input(art: dict[str, Any]) -> dict[str, Any]:
    """The constructed portfolio is a provenance input of class ``illustrative`` (engine contract, Conventions): it has no file."""
    prov = art["provenance"]
    prov["inputs"].append({"source": "illustrative-portfolio", "class": "illustrative", "files": []})
    prov["licence_classes"]["illustrative-portfolio"] = "illustrative"
    return art


def build(seed: int, scale: float, table: fed.Table, raw: dict[str, Any], *, workers: int = 1, log: bool = False,
          only: tuple[str, ...] | None = None, lengths: tuple[int, ...] | None = None) -> dict[str, Any]:
    """Every document of the case in memory: ``{"models", "variants", "values", "plan"}``. ``only`` limits the loan types and
    ``lengths`` the series lengths of the grids (the tests; a full bake passes neither)."""
    rv = docs.rv_version()
    say = _log if log else (lambda _m: None)
    run = ladder.Run.scaled(scale)
    run.seeds = seeds_for(seed)
    full = scale >= 1.0
    n_boot = P.FULL_BOOTSTRAP if full else 100
    n_rep = P.FULL_REPLICATIONS if full else 4
    grid_rhos = P.RHO_GRID if full else TEST_GRID
    lengths = tuple(lengths) if lengths is not None else (P.SERIES_LENGTHS if full else (22,))
    types = [lt for lt in P.LOAN_TYPES if only is None or lt["id"] in only]
    variants: dict[str, dict[str, Any]] = {}
    values: dict[str, float] = {}
    first = None
    for lt in types:
        d = docs.loan_type_document(lt, table, run, n_boot, rv, say)
        art = build_artifact(case_id=CASE_ID, variant_id=lt["id"], model=d["model"], outputs=d["outputs"], tests=d["tests"],
                             impact=d["impact"], findings=d["findings"], lineage=lineage(seed, rv, raw, "real-outcomes", True),
                             lane={"lane": "precompute", "reasons": []})
        variants[lt["id"]] = add_illustrative_input(art)
        values[lt["id"].replace("-", "_") + "_pd_hat"] = d["extras"]["pd"]
        if first is None:
            first = (lt, d)
    cells_by_len: dict[int, list] = {}
    for i_len, years in enumerate(P.SERIES_LENGTHS):
        if years not in lengths:
            continue
        cells = []
        for i_rho, rho in enumerate(P.RHO_GRID):
            if rho not in grid_rhos:
                continue
            reps = simulator.run_cell(rho, years, i_rho, i_len, n_rep, seeds_for(seed)["sim"], n_boot=P.SIM_BOOTSTRAP, workers=workers)
            cells.append(simulator.cell_document(rho, years, P.NULL_RHO, P.ALPHA, reps))
            say(f"grid {years} years rho {rho:g}: {sum(r.ok for r in reps)} of {n_rep} replications valid")
        cells_by_len[years] = cells
        g = docs.grid_document(years, cells, n_rep, rv)
        g["outputs"]["generator"]["seed"] = seeds_for(seed)["sim"]
        g["outputs"]["generator"]["rho_grid"] = list(grid_rhos)
        findings = docs.grid_findings(g)
        art = build_artifact(case_id=CASE_ID, variant_id=f"grid-{years}", model=g["model"], outputs=g["outputs"], tests=g["tests"],
                             impact=g["impact"], findings=findings, lineage=lineage(seed, rv, raw, "synthetic-known-truth", False),
                             lane={"lane": "precompute", "reasons": []})
        variants[f"grid-{years}"] = art
        if years == 22:
            values["size_ml_22_at_null"] = g["impact"]["size_ml"]["value"]
    lt0, d0 = first
    cols = {lt["id"]: fed.HEADINGS[fed.COLUMNS[lt["id"]]] + f" (column {fed.COLUMNS[lt['id']]})" for lt in P.LOAN_TYPES}
    example = {"label": lt0["label"], "pd": d0["extras"]["pd"], "rho": d0["extras"]["rho"], "rungs": d0["outputs"]["rungs"],
               "groups": d0["outputs"]["portfolio"]["groups"]}
    fit = docs.models_document(cols, example, run, n_rep)
    fit["simulator"]["seed"] = seeds_for(seed)["sim"]
    if lengths:
        fit["simulator"]["rho_grid"] = list(grid_rhos)
        fit["simulator"]["series_lengths_years"] = list(lengths)
    models = build_models_artifact(case_id=CASE_ID, fit_id="c10", model=docs_models_records(rv), fit=fit,
                                   lineage=lineage(seed, rv, raw, "real-outcomes", True), lane={"lane": "precompute", "reasons": []})
    add_illustrative_input(models)
    values["delta_xi_025_q_999"] = next(x["delta"] for x in d0["outputs"]["granularity"]["levels"] if x["q"] == 0.999)
    return {"models": models, "variants": variants, "values": values, "default": types[0]["id"],
            "plan": {"scale": scale, "n_replications": n_rep, "n_boot": n_boot}}


def docs_models_records(rv: str) -> list[dict[str, Any]]:
    out = []
    for mid, rg, title, short, engine in docs.MODEL_IDS:
        r = docs.model_summary(mid, rg, title, short, engine, rv)
        r["details"] = {}
        out.append(r)
    return out


def _regime(lt: dict[str, Any]) -> dict[str, str]:
    return docs.T(f"{lt['label']['en']}: Federal Reserve net charge-off rates, All Banks SA, fit 1985-2006 and the 2007-2012 tail.",
                  f"{lt['label']['es']}: tasas de castigo netas de la Reserva Federal, todos los bancos AE, ajuste 1985-2006 y la cola 2007-2012.")


def write_all(built: dict[str, Any], root: Path, raw: dict[str, Any], seed: int, log=lambda _m: None) -> list[dict[str, Any]]:
    """Write the models, the variants, the checksum file and the source record; return the manifest entries."""
    entries: list[dict[str, Any]] = []
    sums: list[str] = []
    e = write_artifact(root, MODELS_REL, built["models"], exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
    sums.append(_sum(root, MODELS_REL))
    entries.append({"role": "models", "variant_id": "models-c10", "truth_status": "real-outcomes",
                    "title": docs.T("Portfolio credit capital: loan types, estimators, ladder and simulator",
                                    "Capital de crédito de cartera: tipos de préstamo, estimadores, escalera y simulador"),
                    "short_title": docs.T("Models", "Modelos"),
                    "regime": docs.T("The five loan types, the two estimators, the eight rungs and the simulator grid",
                                     "Los cinco tipos de préstamo, los dos estimadores, los ocho peldaños y la grilla del simulador"),
                    "path": MODELS_REL, **e})
    for lt in P.LOAN_TYPES:
        vid = lt["id"]
        if vid not in built["variants"]:
            continue
        rel = f"{CASE_ID}/{vid}.json"
        e = write_artifact(root, rel, built["variants"][vid], exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
        sums.append(_sum(root, rel))
        log(f"variant {vid}: {e['bytes']:,} bytes")
        entries.append({"role": "variant", "variant_id": vid, "title": lt["label"], "short_title": lt["label"], "regime": _regime(lt),
                        "truth_status": "real-outcomes", "models_ref": MODELS_REL, **e})
    for years in P.SERIES_LENGTHS:
        vid = f"grid-{years}"
        if vid not in built["variants"]:
            continue
        rel = f"{CASE_ID}/{vid}.json"
        e = write_artifact(root, rel, built["variants"][vid], exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
        sums.append(_sum(root, rel))
        log(f"variant {vid}: {e['bytes']:,} bytes")
        entries.append({"role": "variant", "variant_id": vid,
                        "title": docs.T(f"Correlation grid, {years} years", f"Grilla de correlaciones, {years} años"),
                        "short_title": docs.T(f"Grid {years}y", f"Grilla {years}a"),
                        "regime": docs.T(f"Known-correlation simulator, series of {years} years: size and power of the correlation estimates",
                                         f"Simulador de correlación conocida, series de {years} años: tamaño y potencia de las estimaciones"),
                        "truth_status": "synthetic-known-truth", "models_ref": MODELS_REL, **e})
    (Path(root) / SUMS_REL).write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    (Path(root) / SOURCES_REL).write_text(source_record(raw), encoding="utf-8", newline="\n")
    return entries


def source_record(raw: dict[str, Any]) -> str:
    """The record of the saved page the loan-type documents read: URL, size, SHA-256, retrieval and as-of dates."""
    return (f"source: {P.RAW['source']}\nurl: {P.RAW['url']}\nfile: {raw['name']}\nbytes: {raw['bytes']}\nsha256: {raw['sha256']}\n"
            f"retrieved: {P.RAW['retrieved']}\nas_of: {P.RAW['files_as_of']} (the page's 'Last update')\n"
            f"window_sha256: {P.RAW['window_sha256']}\nwindow: quarters {P.FIT['first_year']}Q1 to {P.EVALUATION['last_year']}Q4, five series\n"
            "licence: information on the Board's website is in the public domain and may be copied and distributed without permission\n")


def _sum(root: Path, rel: str) -> str:
    return f"{hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest()}  {rel}"


def raw_path(data_root: Path | None) -> Path:
    if data_root is None:
        raise RawError("no data root: the C10 bake reads the saved Board page under <data root>/raw/fed-chargeoff/")
    return Path(data_root) / "raw" / P.RAW["folder"] / P.RAW["name"]


def bake_case(seed: int, paths: Any, data_root: Path | None, scale: float, title: dict[str, str], question: dict[str, str],
              page: Path | None = None, only: tuple[str, ...] | None = None, lengths: tuple[int, ...] | None = None) -> dict[str, Any]:
    path = Path(page) if page is not None else raw_path(data_root)
    table = fed.read_table(path)
    raw = fed.raw_record(path)
    check_raw(path, table, raw, _log)
    built = build(seed, scale, table, raw, workers=simulator.default_workers() if scale >= 1.0 else 1, log=True, only=only,
                  lengths=lengths)
    entries = write_all(built, Path(paths.root), raw, seed, _log)
    # the declared ranges are checked on the full bake; a reduced run (tests) writes them and does not judge its small numbers by them
    ranges = (expectations.check(CASE_ID, EXPECT, built["values"]) if scale >= 1.0 and only is None
              else {k: [float(lo), float(hi)] for k, (lo, hi) in sorted(EXPECT.items())})
    from . import CASE_C10 as CASE

    manifest = build_case_manifest(
        depends_on=CASE.depends_on(),
        case_id=CASE_ID, title=title, category={"en": "Portfolio capital", "es": "Capital de cartera"}, question=question,
        sources=[P.RAW["source"]], seed=seed, variants=entries, default_variant=built["default"], contract={}, expect=ranges,
        riskvalidation_version=docs.rv_version(), source_details={P.RAW["source"]: _source_details()})
    write_json(Path(paths.manifests) / f"{CASE_ID}.json", manifest)
    return manifest


def _source_details() -> dict[str, str]:
    from ...io import sources as registry

    s = registry.load()[P.RAW["source"]]
    return {"name": s.name, "publisher": s.publisher, "landing": s.landing, "licence": s.licence, "class": s.klass,
            "attribution": s.attribution}


def main(argv: list[str] | None = None) -> int:
    from ...pipeline import PipelinePaths
    from . import CASE_C10 as CASE

    ap = argparse.ArgumentParser(prog="pipeline.cases.c10.bake", description="Bake C10 into --output (a sandbox) or the repository.")
    ap.add_argument("--output", help="the output root (default: the repository's data/derived)")
    ap.add_argument("--data-root", default=os.environ.get("CONTRASTE_DATA"))
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--page", help="a saved page to read instead of <data root>/raw/fed-chargeoff/chgallsa.htm")
    a = ap.parse_args(argv)
    paths = PipelinePaths.from_output(a.output)
    manifest = CASE.bake(a.seed, paths, Path(a.data_root) if a.data_root else None, a.scale, page=Path(a.page) if a.page else None)
    print(json.dumps({"case": manifest["case_id"], "artifacts": len(manifest["artifacts"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
