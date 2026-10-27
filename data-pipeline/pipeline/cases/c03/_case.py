"""The C03 case object and its bake (CT-801 to CT-812)."""
from __future__ import annotations

import importlib.metadata as md
import sys
import time
from pathlib import Path
from typing import Any
from ..reference_text import with_reference_text

from . import windows

SOURCES = ("sba-foia",)
CASE_ID = "C03"
SEED = 42
COHORTS = windows.COHORTS
FIT_ID = "sba-7a"
#: the default view is the cohort that lived through the crisis on a model trained before it
DEFAULT_VARIANT = "fy2008-10"
RUN_MS = 600_000.0
ENGINES = {"numpy", "scipy", "pandas", "statsmodels", "scikit-learn", "optbinning", "interpret", "lightgbm", "riskvalidation"}
#: every n-th loan of the cleaned file with a recorded rate is checked against the loan_panel family of contract 1
CONTRACT_EVERY = 50

#: What a reader should see, declared before the bake. The basis is the count of charge-offs within 60 months of approval per
#: approval fiscal year over the cleaned SBA 7(a) loans (a preliminary count, before the rungs existed): FY1991-2000 7.1%,
#: FY1991-2002 6.9%, FY1991-2005 8.1%, FY1991-2009 12.3%, FY1991-2012 11.3% for the training windows; FY2006-07 25%, FY2008-10 13%,
#: FY2011-14 3.4%, FY2015-17 4.0%, FY2018-20 3.9% for the test cohorts. Each range is the count widened by about a third; the
#: rungs' AUC is judged only for plausibility (a scorecard on five origination attributes ranks above chance and below 0.85).
EXPECT: dict[str, tuple[float, float]] = {
    "observed_5y_pd@fy2006-07": (0.18, 0.32), "observed_5y_pd@fy2008-10": (0.09, 0.18), "observed_5y_pd@fy2011-14": (0.02, 0.05),
    "observed_5y_pd@fy2015-17": (0.025, 0.06), "observed_5y_pd@fy2018-20": (0.025, 0.055),
    "training_event_rate@fy2006-07": (0.05, 0.09), "training_event_rate@fy2008-10": (0.05, 0.09),
    "training_event_rate@fy2011-14": (0.06, 0.10), "training_event_rate@fy2015-17": (0.10, 0.15),
    "training_event_rate@fy2018-20": (0.09, 0.135),
    "champion_auc@fy2006-07": (0.52, 0.85), "champion_auc@fy2008-10": (0.52, 0.85), "champion_auc@fy2011-14": (0.52, 0.85),
    "champion_auc@fy2015-17": (0.52, 0.85), "champion_auc@fy2018-20": (0.52, 0.85),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C03 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def _v(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "not installed"


def _t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


def _source_details(ids) -> dict[str, dict[str, str]]:
    from ...io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


def contract_summary(loans) -> dict[str, Any]:
    """The loan_panel family of contract 1 applied to every ``CONTRACT_EVERY``-th loan whose rate the file records, as the
    snapshot at origination (the balance is the approved amount, nothing is past due, defaulted, prepaid or written off)."""
    import numpy as np

    from ...io import contract as c1

    sel = np.flatnonzero(np.isfinite(loans.rate))[::CONTRACT_EVERY]
    rows = []
    for i in sel:
        d = str(loans.approval[i])
        rev = bool(loans.revolver[i])
        rows.append({"account_id": f"SBA{int(i):07d}", "reporting_date": d, "origination_date": d, "balance": float(loans.amount[i]),
                     "limit": float(loans.amount[i]) if rev else None, "revolving": 1 if rev else 0, "eir": float(loans.rate[i]),
                     "dpd": 0, "default_flag": 0, "prepay_flag": 0, "writeoff_flag": 0})
    report = c1.validate("loan_panel", rows)
    if not report.ok or report.rejected:
        raise ValueError(f"contract 1 rejects the SBA loans the case reads: {report.counts()}")
    return report.summary()


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {
    "pipeline.cases.c01_ladder": {"en": "Fits the C01 rungs with the C01 ladder (fit_ladder and Rung): the same fitting code, so the rungs of the two cases are the same models.",
        "es": "Ajusta los peldaños de C01 con la escalera de C01 (fit_ladder y Rung): el mismo código de ajuste, de modo que los peldaños de ambos casos son los mismos modelos."},
    "pipeline.cases.c06.panel": {"en": "Uses the C06 panel helpers: the sector groups, the sector index of an industry code and the whole months between two dates.",
        "es": "Usa los auxiliares del panel de C06: los grupos de sectores, el índice de sector de un código de industria y los meses completos entre dos fechas."},
}


class C03:
    id = CASE_ID
    slug = "sme-pd-vintage"
    title = _t("SME PD by vintage through 2008", "PD de pymes por cosecha hasta 2008")
    category_id = "credit-scoring"
    kind = "real"
    question = _t(
        "Does a PD model built on approval cohorts old enough to have been observed for five years stay calibrated for the cohorts that "
        "lived through 2008-2010, and what does a validator find in the cohorts before and after?",
        "¿Se mantiene calibrado un modelo de PD construido con cohortes de aprobación observadas ya por cinco años para las cohortes que "
        "vivieron 2008-2010, y qué encuentra un validador en las cohortes anteriores y posteriores?")
    sources = SOURCES

    def depends_on(self) -> list[dict[str, Any]]:
        """What this case reads of other cases, as the manifest states it (``depends_on``)."""
        from ...core.manifest import derive_depends_on

        return derive_depends_on(self.id, DEPENDS_REASONS)

    def bake(self, seed: int, paths: Any, data_root: Path) -> dict[str, Any]:
        from ... import __version__
        from ...core import expect as expectations
        from ...core import lineage as lin
        from ...core.manifest import build_artifact, build_case_manifest, build_models_artifact
        from ...io import sba
        from ...io import sources as registry
        from ...stages.export import write_artifact
        from ...io.formats import write_json
        from . import models as md_
        from . import panel
        from .variant import bake_cohort

        registry.assert_case_inputs(CASE_ID, list(SOURCES))
        rv = _v("riskvalidation")
        df = sba.read_sba(data_root)
        loans, counts = panel.prepare(df)
        del df
        _log(f"SBA 7(a): {counts['rows-read']:,} rows read, {counts['loans-kept']:,} loans kept; exclusions "
             f"{{{', '.join(f'{k}: {v}' for k, v in counts.items() if k not in ('rows-read', 'loans-kept') and v)}}}")
        contract = {"sba-foia": contract_summary(loans)}
        lineage = lin.build(CASE_ID, sources=list(SOURCES), truth_status="real-outcomes", seed=seed, code_version=__version__,
                            riskvalidation_version=rv)
        lane = {"lane": "precompute", "reasons": []}
        results = []
        for cohort in COHORTS:
            res = bake_cohort(loans, cohort, seed, log=_log)
            _log(f"cohort {cohort.id}: window FY{res.fit.window.first_fy} to FY{res.fit.window.last_fy}, {res.fit.n_loans:,} loans, "
                 f"{res.fit.n_events:,} events, {len(res.document['tests'])} test rows")
            results.append(res)
        last = results[-1]
        cohort_windows = [md_.cohort_window(r.cohort, r.document["outputs"]["training"]) for r in results]
        from .variant import data_status_block, target_block

        fit_doc = {"currency": "USD", "vintage_definition": {"basis": "approval fiscal year", "fiscal_year_start": "10-01",
                                                              "label": _t("SBA fiscal year, 1 October to 30 September",
                                                                          "Año fiscal SBA, 1 de octubre a 30 de septiembre")},
                   "target": target_block(), "cohort_windows": cohort_windows, "ladder": md_.ladder_entries(last.fit),
                   "data_status": data_status_block(str(loans.asof))}
        models_doc = build_models_artifact(case_id=CASE_ID, fit_id=FIT_ID, model=md_.model_records(last.fit), fit=fit_doc,
                                           lineage=lineage, lane=lane)
        rel_m = f"{CASE_ID}/models-{FIT_ID}.json"
        e_m = write_artifact(paths.root, rel_m, models_doc, exact=frozenset({"details", "calibration"}), engines=ENGINES, run_ms=RUN_MS)
        regime_all = _t("A model trained on approvals whose 5-year charge-off outcome is fully observed before the cohort starts; tested on "
                        "each vintage at its 5-year mark. SBA 7(a) small-business loans, as of 2026-06-30.",
                        "Un modelo entrenado con aprobaciones cuyo resultado de castigo a 5 años se observa por completo antes de que "
                        "empiece la cohorte; probado en cada cosecha en su marca de 5 años. Créditos a pequeñas empresas SBA 7(a), a 2026-06-30.")
        entries = [{"role": "models", "variant_id": f"models-{FIT_ID}", "truth_status": "real-outcomes",
                    "title": _t("Fitted models, SBA 7(a)", "Modelos ajustados, SBA 7(a)"),
                    "short_title": _t("Models SBA 7(a)", "Modelos SBA 7(a)"), "regime": regime_all, "path": rel_m,
                    "bytes": e_m["bytes"], "lane": e_m["lane"], "gate": e_m["gate"]}]
        values: dict[str, float] = {}
        for res in results:
            d = res.document
            art = build_artifact(case_id=CASE_ID, variant_id=res.variant_id, model=d["model"], outputs=d["outputs"], tests=with_reference_text(d["tests"]),
                                 impact=d["impact"], findings=d["findings"], lineage=lineage, lane=lane)
            rel = f"{CASE_ID}/{res.variant_id}.json"
            e_v = write_artifact(paths.root, rel, art, exact=frozenset({"calibration"}), engines=ENGINES, run_ms=RUN_MS)
            w = res.fit.window
            regime = _t(f"Trained on FY{w.first_fy} to FY{w.last_fy} (outcomes read up to {w.cutoff}); tested on {res.cohort.name} at each "
                        f"vintage's 5-year mark.",
                        f"Entrenado con AF{w.first_fy} a AF{w.last_fy} (resultados hasta {w.cutoff}); probado en {res.cohort.name} en la "
                        f"marca de 5 años de cada cosecha.")
            entries.append({"role": "variant", "variant_id": res.variant_id,
                            "title": _t(f"Test cohort {res.cohort.name}", f"Cohorte de prueba AF{res.cohort.first_fy}-{str(res.cohort.last_fy)[2:]}"),
                            "short_title": _t(res.cohort.name, f"AF{res.cohort.first_fy}-{str(res.cohort.last_fy)[2:]}"), "regime": regime,
                            "truth_status": "real-outcomes", "models_ref": rel_m, **e_v})
            values.update(res.values)
        ranges = expectations.check(CASE_ID, EXPECT, values)
        manifest = build_case_manifest(
            depends_on=self.depends_on(),
            case_id=CASE_ID, title=self.title, category={"en": "Credit scoring", "es": "Scoring de crédito"}, question=self.question,
            sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT, contract=contract, expect=ranges,
            riskvalidation_version=rv, source_details=_source_details(SOURCES))
        write_json(paths.manifests / f"{CASE_ID}.json", manifest)
        return manifest


CASE = C03()
