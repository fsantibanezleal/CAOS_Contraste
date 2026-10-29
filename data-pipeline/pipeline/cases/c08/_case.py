"""The C08 case object and its bake (CT-901 to CT-917)."""
from __future__ import annotations

import importlib.metadata as md
import sys
import time
from pathlib import Path
from typing import Any
from ..reference_text import with_reference_text

SOURCES = ("sba-foia",)
CASE_ID = "C08"
SEED = 42
#: the variants are the six default cohorts of ``panel.COHORTS``, in order; the one a reader opens first
DEFAULT_VARIANT = "dc-2009-10"
RUN_MS = 600_000.0
ENGINES = {"numpy", "scipy", "pandas", "statsmodels", "riskvalidation", "catboost", "scikit-learn"}
#: the contract-1 check reads every ``PANEL_EVERY``-th default that carries an initial rate
PANEL_EVERY = 5
#: money blocks are written exact: their sums are of the order of 1e10 USD and nine significant digits would round them
EXACT = frozenset({"exposure"})

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C08 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def _v(pkg: str) -> str:
    try:
        return md.version(pkg)
    except md.PackageNotFoundError:
        return "not installed"


def _t(en: str, es: str) -> dict:
    return {"en": en, "es": es}


#: why this case reads what it reads of other cases, keyed by the document or the module its producer names: ``depends_on`` refuses a list that differs
#: from the source (core.manifest.derive_depends_on), so the manifest cannot state what the code does not do
DEPENDS_REASONS: dict[str, dict[str, str]] = {
    "pipeline.cases.c06.panel": {"en": "Uses the C06 panel helpers: the sector groups and the sector index of an industry code.",
        "es": "Usa los auxiliares del panel de C06: los grupos de sectores y el índice de sector de un código de industria."},
}


class C08:
    id = CASE_ID
    slug = "lgd-downturn"
    title = _t("LGD and downturn LGD", "LGD y LGD de recesión")
    category_id = "lgd-ead"
    kind = "real"
    question = _t(
        "How does loss given default move across default cohorts, and what does a downturn LGD add?",
        "¿Cómo se mueve la pérdida dado el incumplimiento entre cohortes de incumplimiento, y qué agrega una LGD de recesión?")
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
        from ...io import contract as c1
        from ...io import sba as readers
        from ...io import sources as registry
        from ...io.formats import write_json
        from ...stages.export import write_artifact
        from . import build as bd
        from . import downturn as dn
        from . import models as md_
        from .panel import COHORTS, annual_rate, prepare
        from .variant import bake_variant

        registry.assert_case_inputs(CASE_ID, list(SOURCES))
        rv = _v("riskvalidation")
        try:
            readers.read_freddie(data_root)
            raise RuntimeError("the Freddie Mac slot returned a body: wire its reader before this case claims the data")
        except readers.DeclaredAbsence as exc:
            freddie_reason = str(exc)
            _log(freddie_reason)
        df = readers.read_sba(data_root)
        defaults, counts = prepare(df)
        annual = annual_rate(df)
        del df
        _log(f"SBA 7(a): {counts['charge-offs-read']:,} charge-offs read, {counts['defaults-kept']:,} kept; exclusions "
             f"{{{', '.join(f'{k}: {v}' for k, v in counts.items() if k not in ('charge-offs-read', 'defaults-kept') and v)}}}")
        contract = {"sba-foia": _contract_summary(c1, defaults)}
        down = dn.plan(defaults, annual)
        _log(f"downturn {down.period['first_year']}-{down.period['last_year']} (threshold {down.threshold:.4f}); cohorts {down.downturn_cohorts}")
        lineage = lin.build(CASE_ID, sources=list(SOURCES), truth_status="real-outcomes", seed=seed, code_version=__version__,
                            riskvalidation_version=rv)
        lane = {"lane": "precompute", "reasons": []}
        entries: list[dict[str, Any]] = []
        values: dict[str, float] = {"n-defaults-total": float(defaults.n)}
        for cid, lo, hi in COHORTS:
            res = bake_variant(defaults, cid, seed, down, freddie_reason)
            vid = res.variant_id
            title = _t(f"Default cohort {cid}", f"Cohorte de incumplimientos {cid}")
            short = _t(cid, cid)
            regime = _t(
                f"Models trained on the SBA 7(a) defaults charged off before {res.cutoff}; tested on the defaults of {lo} to {hi} "
                "(and the later cohorts). The LGD is a proxy: charge-off over the approved amount.",
                f"Modelos entrenados con los incumplimientos SBA 7(a) castigados antes de {res.cutoff}; probados con los de {lo} a "
                f"{hi} (y las cohortes posteriores). La LGD es una aproximación: castigo sobre el monto aprobado.")
            models_doc = build_models_artifact(case_id=CASE_ID, fit_id=vid, model=md_.model_records(res),
                                               fit=md_.fit_block(res, freddie_reason, down), lineage=lineage, lane=lane)
            rel_m = f"{CASE_ID}/models-{vid}.json"
            e_m = write_artifact(paths.root, rel_m, models_doc, exact=frozenset({"details"}), engines=ENGINES, run_ms=RUN_MS)
            entries.append({"role": "models", "variant_id": f"models-{vid}", "truth_status": "real-outcomes",
                            "title": _t(f"Fitted models, cohort {cid}", f"Modelos ajustados, cohorte {cid}"),
                            "short_title": _t(f"Models {cid}", f"Modelos {cid}"), "regime": regime, "path": rel_m,
                            "bytes": e_m["bytes"], "lane": e_m["lane"], "gate": e_m["gate"]})
            art = build_artifact(case_id=CASE_ID, variant_id=vid, model=md_.model_summaries(res), outputs=res.outputs,
                                 tests=with_reference_text(res.tests), impact=res.impact, findings=res.findings, lineage=lineage, lane=lane)
            rel = f"{CASE_ID}/{vid}.json"
            e_v = write_artifact(paths.root, rel, art, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
            entries.append({"role": "variant", "variant_id": vid, "title": title, "short_title": short, "regime": regime,
                            "truth_status": "real-outcomes", "models_ref": rel_m, **e_v})
            values.update(res.values)
            rungs = ", ".join(f"{r}={'ok' if res.ladder.rungs[r].evaluated else 'not evaluated'}" for r in res.ladder.rungs)
            _log(f"variant {vid}: {res.n_train:,} training defaults, {res.n_open:,} open workouts excluded; {rungs}")
            del res
        ranges = expectations.check(CASE_ID, bd.EXPECT, values)
        manifest = build_case_manifest(
            depends_on=self.depends_on(),
            case_id=CASE_ID, title=self.title, category={"en": "LGD and EAD", "es": "LGD y EAD"}, question=self.question,
            sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT, contract=contract, expect=ranges,
            riskvalidation_version=rv, source_details=_source_details(SOURCES))
        write_json(paths.manifests / f"{CASE_ID}.json", manifest)
        return manifest


def _contract_summary(c1, defaults) -> dict[str, Any]:
    """Run the ``loan_panel`` family of contract 1 over the charge-offs that carry an initial rate (the contract's ``eir``
    is required, and the file has none for most old loans; the rest are not offered to it, none is invented). The
    summary goes to the manifest."""
    import numpy as np

    idx = np.flatnonzero(np.isfinite(defaults.rate))[::PANEL_EVERY]
    rows = []
    for i in idx:
        rev = bool(defaults.revolver[i])
        rows.append({"account_id": f"SBA{int(i):07d}", "reporting_date": str(defaults.chargeoff_date[i]),
                     "origination_date": str(defaults.approval_date[i]), "balance": float(defaults.chargeoff_amount[i]),
                     "limit": float(defaults.gross_approval[i]) if rev else None, "revolving": 1 if rev else 0,
                     "eir": float(defaults.rate[i]), "dpd": 0, "default_flag": 1, "prepay_flag": 0, "writeoff_flag": 1,
                     "workout_closed": 1})
    return c1.validate("loan_panel", rows, params={"workout_cutoff": str(defaults.chargeoff_date.max())}).summary()


def _source_details(ids) -> dict[str, dict[str, str]]:
    from ...io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing, "licence": reg[i].licence,
                "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


CASE = C08()
