"""The C06 case object and its bake (CT-501 to CT-517)."""
from __future__ import annotations

import importlib.metadata as md
import sys
import time
from pathlib import Path
from typing import Any
from ..reference_text import with_reference_text

SOURCES = ("sba-foia", "fed-stress-tests")
CASE_ID = "C06"
SEED = 42
#: the six variants, in order (SDD section 5, case C06): trained on what is known at the date, tested on what follows
REPORTING_DATES = ("2006-12-31", "2008-12-31", "2010-12-31", "2019-12-31", "2020-06-30", "2023-06-30")
RUN_MS = 600_000.0
DEFAULT_VARIANT = "rd-2020-06"
#: a quarter enters the implied systematic factor with at least this many loans at risk (the young book of the first years
#: has almost no defaults, which is its age and not the cycle)
MIN_QUARTER_AT_RISK = 50_000
ENGINES = {"numpy", "scipy", "pandas", "statsmodels", "riskvalidation", "torch"}
#: the money blocks are written exact: their identities close to 1e-6 of the gross amount, and rounding to nine significant
#: digits would only add noise to them
EXACT = frozenset({"reconciliation", "waterfall", "stage_summary", "ecl_by_scenario", "stage_flows", "overlays", "weight_grid",
                   "non_linearity"})

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C06 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def _v(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "not installed"


def _t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {}


class C06:
    id = CASE_ID
    slug = "lifetime-pd-ecl"
    title = _t("Lifetime PD, IFRS 9 staging and ECL on public small-business loans",
               "PD de por vida, etapas de IFRS 9 y pérdida esperada en préstamos públicos a pequeñas empresas")
    category_id = "provisions"
    kind = "real"
    question = _t(
        "How do lifetime PD, IFRS 9 staging and expected credit loss behave on public small-business loans across reporting dates, "
        "and what does a validator find when the model of each date is tested on what happened after it?",
        "¿Cómo se comportan la PD de por vida, las etapas de IFRS 9 y la pérdida esperada en préstamos públicos a pequeñas empresas "
        "a través de fechas de reporte, y qué encuentra un validador cuando el modelo de cada fecha se prueba con lo que ocurrió después?")
    sources = SOURCES

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path) -> dict[str, Any]:
        from ...core import expect as expectations
        from ...core import lineage as lin
        from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
        from ...io import sources as registry
        from ...io.formats import write_json
        from ...stages.export import write_artifact
        from ... import __version__
        from . import build as bd
        from ...io import sba as readers
        from .panel import prepare
        from .variant import bake_variant

        import numpy as np

        registry.assert_case_inputs(CASE_ID, list(SOURCES))
        rv = _v("riskvalidation")
        absence = None
        try:
            readers.read_freddie(data_root)
        except readers.DeclaredAbsence as exc:
            absence = str(exc)
            _log(absence)
        df = readers.read_sba(data_root)
        fed = readers.read_fed(data_root)
        loans, counts = prepare(df)
        del df
        _log(f"SBA 7(a): {counts['rows-read']:,} rows read, {counts['loans-kept']:,} loans kept; exclusions {{{', '.join(f'{k}: {v}' for k, v in counts.items() if k not in ('rows-read', 'loans-kept') and v)}}}")
        lineage = lin.build(CASE_ID, sources=list(SOURCES), truth_status="real-outcomes", seed=seed, code_version=__version__,
                            riskvalidation_version=rv)
        lane = {"lane": "precompute", "reasons": []}
        entries: list[dict[str, Any]] = []
        values: dict[str, float] = {}
        contract: dict[str, Any] = {}
        panel_every = 10
        for ds in REPORTING_DATES:
            rd = np.datetime64(ds, "D")
            res = bake_variant(loans, fed, rd, seed, panel_every=panel_every, cleaning=counts,
                               min_quarter_at_risk=MIN_QUARTER_AT_RISK)
            vid = res.variant_id
            en_m, es_m, year, iso = bd.month_label(rd)
            title = _t(f"Reporting date {en_m} {year}", f"Fecha de reporte {es_m} de {year}")
            short = _t(f"{en_m[:3]} {year}", f"{es_m[:3].capitalize()} {year}")
            regime = _t("Models trained on the loans, outcomes and macro known at the date; tested on what followed. SBA 7(a) small-business loans, Federal Reserve 2026 scenario shapes.",
                        "Modelos entrenados con los préstamos, resultados y macro conocidos a la fecha; probados con lo que siguió. Préstamos SBA 7(a) a pequeñas empresas, formas de escenarios de la Reserva Federal 2026.")
            models_doc = build_models_artifact(case_id=CASE_ID, fit_id=vid, model=res.models["model"], fit=res.models["fit"],
                                               lineage=lineage, lane=lane)
            rel_m = f"{CASE_ID}/models-{vid}.json"
            e_m = write_artifact(paths.root, rel_m, models_doc, exact=frozenset({"details"}), engines=ENGINES, run_ms=RUN_MS)
            entries.append({"role": "models", "variant_id": f"models-{vid}", "truth_status": "real-outcomes",
                            "title": _t(f"Fitted models, {en_m} {year}", f"Modelos ajustados, {es_m} de {year}"),
                            "short_title": _t(f"Models {en_m[:3]} {year}", f"Modelos {es_m[:3]} {year}"), "regime": regime,
                            "path": rel_m, "bytes": e_m["bytes"], "lane": e_m["lane"], "gate": e_m["gate"]})
            d = res.document
            art = build_artifact(case_id=CASE_ID, variant_id=vid, model=d["model"], outputs=d["outputs"], tests=with_reference_text(d["tests"]),
                                 impact=d["impact"], findings=d["findings"], lineage=lineage, lane=lane)
            rel = f"{CASE_ID}/{vid}.json"
            e_v = write_artifact(paths.root, rel, art, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
            entries.append({"role": "variant", "variant_id": vid, "title": title, "short_title": short, "regime": regime,
                            "truth_status": "real-outcomes", "models_ref": rel_m, **e_v})
            values.update(res.values)
            if vid == DEFAULT_VARIANT:
                contract = {"sba-foia": res.contract["loan_panel"], "fed-stress-tests": res.contract["macro_path"]}
            _log(f"variant {vid}: models {e_m['bytes']:,} bytes, document {e_v['bytes']:,} bytes, {len(d['tests'])} test rows")
            del res
        ranges = expectations.check(CASE_ID, bd.EXPECT, values)
        manifest = build_case_manifest(
            depends_on=self.depends_on(),
            case_id=CASE_ID, title=self.title, category={"en": "Provisions", "es": "Provisiones"}, question=self.question,
            sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT, contract=contract, expect=ranges,
            riskvalidation_version=rv, source_details=_source_details(SOURCES))
        write_json(paths.manifests / f"{CASE_ID}.json", manifest)
        return manifest


def _source_details(ids) -> dict[str, dict[str, str]]:
    from ...io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


CASE = C06()
