"""The bake of C11 (SDD C11: market VaR and ES back-testing across 2008, 2020, 2022 and 2023).

``bake_all`` reads the three public daily series from the device data root, fixes the hyperparameters on 1995-2003 (cached),
forecasts the ladder window by window (cached), builds the six window documents and the models document through
``documents`` and writes them, with the case manifest, under the output root. The full bake runs locally, never in CI
(ADR-0074): the forecasts are the cost, and ``forecast.py`` states the refit frequency of each rung.
"""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from ... import __version__
from ...core import expect as expectations
from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ..reference_text import with_reference_text
from ...core.lineage import Input, Lineage
from ...io import contract as c1
from ...io.formats import write_json
from ...stages.export import write_artifact
from . import documents as docs
from . import forecast as fc
from . import hyper, portfolio as pf, readers
from ._case import C11, SOURCES
from .constants import CASE_ID, SEED, WINDOWS
from .forecast import Hyper

REQUIREMENTS = Path(__file__).resolve().parents[3] / "requirements.txt"


def engine_pin(requirements: Path = REQUIREMENTS) -> str:
    """The ref the pipeline pins the engine to (a release tag or a commit), read from data-pipeline/requirements.txt, so the
    stamp and the cache key follow the pin and never a copy of it."""
    for line in requirements.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^riskvalidation(?:\[[^\]]*\])?\s*@\s*git\+\S+?@(\S+)\s*$", line.strip())
        if m:
            return m.group(1)
        m = re.match(r"^riskvalidation(?:\[[^\]]*\])?\s*==\s*(\d+)\.(\d+)\.(\d+)\s*$", line.strip())
        if m:  # the PyPI release, stamped as its tag (0.8.1 is v0.08.001)
            return "v%d.%02d.%03d" % tuple(int(x) for x in m.groups())
    raise RuntimeError(f"{requirements}: no riskvalidation pin")


ENGINE_PIN = engine_pin()
ENGINES = {"numpy", "scipy", "pandas", "statsmodels", "riskvalidation", "arch"}
RUN_MS = 3_600_000.0
DEFAULT_VARIANT = "rates-2022"
HYPER_FILE = "hyperparameter-selection.json"
INPUTS_FILE = "inputs.json"
EVIDENCE = Path(__file__).resolve().parents[4] / "docs" / "design" / "features" / "c11"   # not data/derived: every json there is a contract document
_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C11 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def _t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def engine_version() -> str:
    try:
        version = md.version("riskvalidation")
        return version if ENGINE_PIN.startswith("v") else f"{version}@{ENGINE_PIN[:7]}"  # a tag is the release itself
    except md.PackageNotFoundError:
        return "not installed"


def load_series(data_root: Path) -> dict[str, readers.Series]:
    return {"french-daily": readers.read_french(data_root), "treasury-par": readers.read_treasury(data_root),
            "h10-fx": readers.read_h10(data_root)}


def contract_one(series: dict[str, readers.Series]) -> dict[str, Any]:
    """Run each series through the ``market_series`` family of contract 1; a rejected row stops the bake."""
    out = {}
    for sid, s in series.items():
        rep = c1.validate("market_series", s.contract_rows())
        if not rep.ok or rep.rejected:
            raise ValueError(f"{sid}: contract 1 rejects the reader's output: {rep.counts()}")
        out[sid] = rep.summary()
    return out


def _series_fingerprint(series: dict[str, readers.Series]) -> str:
    h = hashlib.sha256()
    for k in sorted(series):
        h.update(k.encode())
        h.update(series[k].dates.astype("datetime64[D]").astype("int64").tobytes())
        h.update(np.ascontiguousarray(series[k].values).tobytes())
    return h.hexdigest()[:20]


def fix_hyperparameters(series: dict[str, readers.Series], cache_dir: Path, workers: int, base: Hyper | None = None) -> tuple[Hyper, dict]:
    """The hyperparameters fixed on the span, cached by a hash of the span's data and the grid."""
    base = base or Hyper()
    key = hashlib.sha256(json.dumps([_series_fingerprint(hyper.cut(series)), asdict(base), hyper.GRID, hyper.STRIDE, ENGINE_PIN],
                                    sort_keys=True).encode()).hexdigest()[:20]
    path = Path(cache_dir) / f"hyperparameters.{key}.json"
    if path.exists():
        rec = json.loads(path.read_text(encoding="utf-8"))
        return Hyper(**rec["hyper"]), rec["record"]
    hp, record = hyper.select(series, base, workers, _log)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"hyper": asdict(hp), "record": record}), encoding="utf-8")
    return hp, record


def _lineage(series: dict[str, readers.Series], seed: int) -> Lineage:
    src = {"french-daily": ("french-data-library", "derived-only"), "treasury-par": ("treasury-par-curve", "mirror-allowed"),
           "h10-fx": ("fred-public-domain", "mirror-allowed")}
    inputs = tuple(Input(src[k][0], src[k][1], tuple((f.name, f.sha256) for f in series[k].files)) for k in series)
    return Lineage(CASE_ID, "real-outcomes", inputs, seed, __version__, engine_version(), ("contraste:c11-bake",))


def inputs_record(series: dict[str, readers.Series]) -> dict:
    """The raw files read, with URL, size, hash and date (the raw files themselves stay in the data root)."""
    return {"case": CASE_ID, "note": "Raw files stay in the device data root. The Kenneth French file is derived-only: only its hash and size are published.",
            "series": {k: {"unit": s.unit, "first": str(s.dates[0]), "last": str(s.dates[-1]), "n_observed": int(len(s)),
                           "n_missing": len(s.missing), "files": [f.to_json() for f in s.files]} for k, s in series.items()}}


def bake_all(output_root: Path, data_root: Path, cache_dir: Path, *, workers: int = 4, seed: int = SEED, hp: Hyper | None = None,
             model_ids: tuple[str, ...] | None = None, window_ids: tuple[str, ...] | None = None, series: dict | None = None,
             expect: dict | None = None, evidence_dir: Path | None = EVIDENCE, mc_draws: int = docs.MC_DRAWS, z2_draws: int = docs.Z2_DRAWS,
             limit: int | None = None) -> dict[str, Any]:
    series = series or load_series(Path(data_root))
    contract = contract_one(series)
    record = None
    if hp is None:
        hp, record = fix_hyperparameters(series, Path(cache_dir), workers)
        hp = Hyper(**{**asdict(hp), "seed": seed})
    _log(f"hyperparameters {asdict(hp)}")
    windows = [w for w in WINDOWS if window_ids is None or w.window_id in window_ids]
    ports = {w.window_id: pf.build(w.window_id, series) for w in windows}
    jobs = {wid: (p.returns, pf.forecast_positions(p, limit)) for wid, p in ports.items()}
    runs = fc.forecast_windows(jobs, hp, Path(cache_dir), ENGINE_PIN, model_ids, workers, _log)
    lineage = _lineage(series, seed)
    root = Path(output_root)
    entries: list[dict[str, Any]] = []
    values: dict[str, float] = {}
    ev = engine_version()
    lane = {"lane": "precompute", "reasons": []}
    all_runs = {wid: runs[wid] for wid in runs}
    # the models document needs every window; a partial bake (a test) passes the windows it has
    mdoc = docs.build_models({w.window_id: ports[w.window_id] for w in windows}, all_runs, hp, code_version=__version__,
                             engine_version=ev, provenance=lineage.provenance(), model_ids=model_ids) if len(windows) == len(WINDOWS) else None
    rel_m = f"{CASE_ID}/models-ladder.json"
    regime = _t("Rolling one-step forecasts on public daily series; hyperparameters fixed on 1995 to 2003 and never tuned on a test window.",
                "Pronósticos móviles a un día sobre series diarias públicas; hiperparámetros fijados en 1995 a 2003 y nunca ajustados en una ventana de prueba.")
    if mdoc is not None:
        models_art = build_models_artifact(case_id=CASE_ID, fit_id="ladder", model=mdoc["model"], fit=mdoc["fit"], lineage=lineage, lane=lane)
        e_m = write_artifact(root, rel_m, models_art, engines=ENGINES, run_ms=RUN_MS)
        entries.append({"role": "models", "variant_id": "models-ladder", "truth_status": "real-outcomes",
                        "title": _t("Fitted ladder", "Escalera ajustada"), "short_title": _t("Models", "Modelos"), "regime": regime,
                        "path": rel_m, "bytes": e_m["bytes"], "lane": e_m["lane"], "gate": e_m["gate"]})
    for w in windows:
        d = docs.build_window(ports[w.window_id], runs[w.window_id], hp, code_version=__version__, engine_version=ev, model_ids=model_ids,
                           mc_draws=mc_draws, z2_draws=z2_draws, limit=limit)
        art = build_artifact(case_id=CASE_ID, variant_id=w.window_id, model=d["model"], outputs=d["outputs"], tests=with_reference_text(d["tests"]),
                             impact=d["impact"], findings=d["findings"], lineage=lineage, lane=lane)
        rel = f"{CASE_ID}/{w.window_id}.json"
        e_v = write_artifact(root, rel, art, engines=ENGINES, run_ms=RUN_MS)
        entries.append({"role": "variant", "variant_id": w.window_id, "title": _t(w.en, w.es), "short_title": _t(w.en.split(":")[0], w.es.split(":")[0]),
                        "regime": regime, "truth_status": "real-outcomes", "models_ref": rel_m, **e_v})
        o = d["outputs"]
        values[f"n_forecast_days@{w.window_id}"] = float(o["window"]["n_forecast_days"])
        values[f"eligible_models@{w.window_id}"] = d["impact"]["eligible_models"]["value"]
        rates = [lv["n_exceedances"] / lv["n_scored"] for m in o["models"] for lv in m["by_level"] if lv["alpha"] == 0.01]
        values[f"mean_exceedance_rate_1pct@{w.window_id}"] = float(np.mean(rates))
        _log(f"window {w.window_id}: {o['window']['n_forecast_days']} days, {len(d['tests'])} test rows, {e_v['bytes']:,} bytes")
    if mdoc is None:
        return {"windows": [e["variant_id"] for e in entries]}
    if evidence_dir is not None:
        Path(evidence_dir).mkdir(parents=True, exist_ok=True)
        write_json(Path(evidence_dir) / INPUTS_FILE, inputs_record(series))
        if record is not None:
            (Path(evidence_dir) / HYPER_FILE).write_text(hyper.dumps(record), encoding="utf-8")
    ranges = expectations.check(CASE_ID, expect if expect is not None else EXPECT, values)
    from ._case import CASE

    manifest = build_case_manifest(
        depends_on=CASE.depends_on(),
        case_id=CASE_ID, title=C11.title, category={"en": "Market and counterparty risk", "es": "Riesgo de mercado y de contraparte"}, question=C11.question,
        sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT, contract=contract, expect=ranges,
        riskvalidation_version=ev, source_details=source_details())
    write_json(root / "manifests" / f"{CASE_ID}.json", manifest)
    return manifest


#: what a reader should see, per window; a result outside its range stops the bake (a broken pipeline, not a finding)
EXPECT: dict[str, tuple[float, float]] = {}
for _w, (_lo, _hi) in {"equity-2007-09": (495, 515), "equity-2020": (100, 115), "rates-2022": (245, 255), "fx-2008": (245, 255),
                       "mixed-2023": (60, 68), "calm-2004-06": (740, 760)}.items():
    EXPECT[f"n_forecast_days@{_w}"] = (_lo, _hi)
    EXPECT[f"eligible_models@{_w}"] = (0, 17)
    EXPECT[f"mean_exceedance_rate_1pct@{_w}"] = (0.0, 0.2)

def source_details() -> dict[str, dict[str, str]]:
    """What the Context view shows of each source, from the source registry (the H.10 is registered with FRED's public-domain
    series, which names it)."""
    from ...io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in SOURCES}
