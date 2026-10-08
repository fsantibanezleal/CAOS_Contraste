"""C04, rating transitions and TTC PD by grade (U4).

The design is docs/design/features/c04-transitions/design.md and contract.md; requirements CT-401 to CT-414 hold it.
Inputs: ESMA CEREP's statistics of S&P's, Moody's and Fitch's EU entities (mirror-allowed: "Reproduction of all
information on this site (REGISTERS information) is authorised except as otherwise stated, provided the source is
acknowledged"), read from the device data root by ``pipeline.io.cerep``; the papers of Israel, Rosenthal and Wei
(2001), Engelmann (2024) and Schuermann and Hanson (2004), derived-only, read by ``pipeline.io.papers``; and
riskvalidation's ``RatingPaths`` driven by the EM generator of S&P's pooled annual counts for the known-truth families.
Every computation is riskvalidation 0.4; this module wires the variants, the models artifact, the findings and the
expected ranges.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import expm

from .. import __version__
from ..core import expect as expectations
from ..core import lineage as lin
from ..core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ..io import cerep
from ..io.formats import write_json
from ..stages.export import write_artifact
from . import c04_agency, c04_families, c04_parity, c04_published
from .c01_ladder import _t, _v
from .c05_ldp_calibration import IRB_ASSUMPTIONS, _irb_rw

CASE_ID = "C04"
SOURCES = ("esma-cerep", "israel-rosenthal-wei-2001", "engelmann-2024", "schuermann-hanson-2004")
CEREP_SOURCE = "esma-cerep"
PAPERS = ("israel-rosenthal-wei-2001", "engelmann-2024", "schuermann-hanson-2004")
YEARS = range(2000, 2026)
SEMESTER_YEARS = range(2010, 2026)
#: the five-year windows of the lifetime check (CT-415), each a cohort fixed at its first day
WINDOWS = ((2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024))
REPS = 200
ENGINES = {"numpy", "scipy", "riskvalidation", "pypdf"}
RUN_MS = 600_000.0
#: keys whose values keep full precision in the artifacts: the matrices the live views project with, and the parity
EXACT = frozenset({"matrix", "matrix_state", "generator", "q", "one_year_matrix", "parity"})

AGENCY_VARIANTS = (
    {"id": "sp", "code": "STPGB", "title": _t("S&P's EU entity: CEREP's corporate cohorts", "Entidad UE de S&P: cohortes corporativas de CEREP"),
     "short": _t("S&P", "S&P")},
    {"id": "moodys", "code": "MDYGB", "title": _t("Moody's EU entity: CEREP's corporate cohorts", "Entidad UE de Moody's: cohortes corporativas de CEREP"),
     "short": _t("Moody's", "Moody's")},
    {"id": "fitch", "code": "FITGB", "title": _t("Fitch's EU entity: CEREP's corporate cohorts", "Entidad UE de Fitch: cohortes corporativas de CEREP"),
     "short": _t("Fitch", "Fitch")},
)
FAMILY_VARIANTS = (
    {"id": "markov", "title": _t("Markov chain: the estimators and tests against the truth", "Cadena de Markov: estimadores y pruebas contra la verdad"),
     "short": _t("Markov", "Markov")},
    {"id": "momentum", "title": _t("Rating momentum (dos Reis, Pfeuffer and Smith)", "Momentum de calificación (dos Reis, Pfeuffer y Smith)"),
     "short": _t("Momentum", "Momentum")},
    {"id": "cycle", "title": _t("A recession year in a stable chain", "Un año de recesión en una cadena estable"),
     "short": _t("Cycle", "Ciclo")},
    {"id": "withdrawals", "title": _t("Informative withdrawals", "Retiros informativos"),
     "short": _t("Withdrawals", "Retiros")},
    {"id": "thin", "title": _t("Thin cohorts: intervals for a PD by grade", "Cohortes delgadas: intervalos para una PD por grado"),
     "short": _t("Thin", "Delgadas")},
)
PUBLISHED_VARIANT = {"id": "published", "title": _t("Published answers: three papers recomputed", "Respuestas publicadas: tres artículos recalculados"),
                     "short": _t("Papers", "Artículos")}
DEFAULT_VARIANT = "sp"
REGIME_AGENCY = _t("Corporate long-term ratings, calendar-year and semester cohorts, as ESMA computes them",
                   "Calificaciones corporativas de largo plazo, cohortes anuales y semestrales, como las calcula ESMA")
REGIME_FAMILY = _t("Rating paths from the EM generator of S&P's counts, with the defect planted along a ladder",
                   "Trayectorias desde el generador EM de los conteos de S&P, con el defecto plantado en una escalera")
REGIME_PUBLISHED = _t("The papers read from the data root; their agency matrices never enter the artifact",
                      "Los artículos leídos desde la raíz de datos; sus matrices de agencias nunca entran al artefacto")

#: the expected ranges the bake checks (CT-408). Each has its basis: a count fixed by the pinned fetch, the published
#: agency statistics and the 2000 to 2019 smoke run for S&P, theory for the known-truth families (the binomial and
#: the size bound at 200 repetitions), the calibration of dossier 13 section 16, the papers' prints; ranges for Moody's
#: and Fitch had no prior basis and were set at the first full bake (2026-10-07), wide enough for a re-fetch
EXPECT: dict[str, tuple[float, float]] = {
    # the cohorts CEREP holds for each entity (Fitch: 2000 empty, 2001 all zeros)
    "sp_cohorts": (26.0, 26.0), "moodys_cohorts": (26.0, 26.0), "fitch_cohorts": (24.0, 24.0),
    # S&P: the 2000 to 2019 smoke run gave 26.2%, 0.60%, L1 0.0050 (DA), 0.099 (JLT), 0.69% and 0.35
    "sp_lra_ccc_c": (0.18, 0.36), "sp_lra_bb": (0.003, 0.012), "sp_l1_em": (0.001, 0.03), "sp_l1_jlt": (0.03, 0.2),
    "sp_ttc_default_rate": (0.004, 0.012), "sp_time_homogeneity_p": (0.0, 1e-6), "sp_d4_over_d2_ccc_c": (0.15, 0.6),
    # Moody's and Fitch, set at the first full bake (11.1% and 18.7% CCC to C; Fitch's D4 gap widened by its empty years)
    "moodys_lra_ccc_c": (0.06, 0.25), "moodys_lra_bb": (0.003, 0.012), "moodys_l1_em": (0.0005, 0.01),
    "moodys_l1_jlt": (0.03, 0.2), "moodys_time_homogeneity_p": (0.0, 1e-6),
    "fitch_lra_ccc_c": (0.10, 0.30), "fitch_lra_bb": (0.002, 0.012), "fitch_l1_em": (0.0005, 0.01),
    "fitch_l1_jlt": (0.03, 0.2), "fitch_ttc_default_rate": (0.001, 0.006), "fitch_time_homogeneity_p": (0.0, 1e-6),
    "fitch_d4_over_d2_ccc_c": (0.08, 0.4),
    # the Markov null: AAA's 375 obligor-years at 0.66bp leave no default with probability exp(-0.025) = 0.975, the Wald
    # interval covering only then; sizes within the bound at 200 repetitions (9.76%) for the tests that hold theirs
    "markov_zero_share_aaa": (0.93, 1.0), "markov_wald_coverage_aaa": (0.0, 0.1), "markov_jeffreys_coverage_bb": (0.90, 0.99),
    "markov_size_time_homogeneity": (0.02, 0.0976), "markov_size_matrix_reference": (0.0, 0.0976),
    "markov_size_momentum": (0.02, 0.0976),
    # the order test's chi-square over-rejects on these cohorts (7.0% at 5% and 2.7% at 1% over 2,000 repetitions on
    # S&P's 2000 to 2025 generator, measured 2026-10-07); its likelihood ratio holds
    "markov_size_markov_order": (0.04, 0.16), "markov_order_chi2_size_05": (0.055, 0.09),
    "markov_order_chi2_size_01": (0.012, 0.04), "markov_order_lr_size_05": (0.035, 0.066),
    "markov_order_lr_size_01": (0.003, 0.016),
    # momentum: the calibration (dossier 13 section 16): c 0.336 at alpha 0.125, the hazard test 40% at 0.025
    "momentum_coefficient_alpha_0_125": (0.30, 0.38), "momentum_hazard_alpha_0_025": (0.2, 0.55),
    "momentum_hazard_size": (0.02, 0.0976), "momentum_order_alpha_0_025": (0.03, 0.3),
    "momentum_th_alpha_0_125": (0.03, 0.2), "momentum_projection_error_bbb": (-0.003, 0.001),
    # the cycle: no stress is the null; downgrades times 1.5 for a year were seen 100% of the time on the size study's chain
    "cycle_th_k_1": (0.02, 0.0976), "cycle_th_k_1_5": (0.8, 1.0),
    # informative withdrawal: removing understates the B PD, following understates it less
    "withdrawals_removed_rel_bias_b_k9": (-0.5, -0.2), "withdrawals_followed_rel_bias_b_k9": (-0.3, -0.05),
    # thin cohorts, exact: Wald covers AAA only when a default occurs, 1 - (1 - p)^50 at p = 0.66bp
    "thin_wald_coverage_aaa_50": (0.0030, 0.0036), "thin_jeffreys_coverage_aaa_50": (0.99, 1.0),
    "thin_overlap_aaa_aa_1000": (0.99, 1.0),
    # the papers, as printed
    "published_irw_agree": (8.0, 8.0), "published_irw_jlt_printed_generator": (0.1168995, 0.1169005),
    "published_sr190_agree": (6.0, 6.0), "published_sr190_defaults": (15.0, 15.0),
    "published_engelmann_ttc_pd": (0.011975, 0.011985),
}


def _log(msg: str) -> None:
    print(f"[C04] {msg}", file=sys.stderr, flush=True)


def _agency(code: str, got: dict[str, list[Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """One agency's outputs and test rows, its five-year windows included (the lifetime check, CT-415)."""
    return c04_agency.agency_outputs(code, got["annual"], got["semesters"], got["windows"])


def _origination(outputs: dict[str, Any]) -> list[float]:
    """The agency's average cohort mix by grade, the origination the live projection replenishes with (default 0)."""
    sizes = np.array([c["size"] for c in outputs["cohorts"]], dtype=float).sum(axis=0)
    mix = sizes / sizes.sum()
    return [float(x) for x in mix] + [0.0]


def _generator_from_sp(sp: dict[str, Any]) -> tuple[np.ndarray, list[int]]:
    """The known-truth families' generator: EM on S&P's pooled annual counts; and its cohort size by grade (the mean
    cohort)."""
    q = np.asarray(sp["generators"]["em"]["generator"], dtype=float)
    sizes = np.array([c["size"] for c in sp["cohorts"]], dtype=float).mean(axis=0)
    return q, [int(round(x)) for x in sizes]


# ---------------------------------------------------------------------------------------------------------------------
# model records


def _agency_models(out: dict[str, Any], rv: str) -> list[dict[str, Any]]:
    g = out["generators"]
    rows = [
        ("M1-cohort", "estimator", "cohort", _t("Cohort matrix, pooled over the years (Anderson and Goodman 2.8)", "Matriz de cohortes, agrupada en los años (Anderson y Goodman 2.8)"),
         _t("Cohort", "Cohortes"), "riskvalidation.transitions.estimators.pooled_cohort",
         {"cohorts": {"value": float(out["pooled"]["cohorts"]), "unit": "count"}}),
        ("M2-em", "generator", "em", _t("EM generator of the annual counts (Smith and dos Reis)", "Generador EM de los conteos anuales (Smith y dos Reis)"),
         _t("EM", "EM"), "riskvalidation.transitions.em.em_generator",
         {"l1_distance": {"value": float(g["em"]["l1"]), "unit": "probability"},
          "iterations": {"value": float(g["em"]["iterations"]), "unit": "count"}}),
    ]
    for mid, key, en, es in (("M3-diagonal", "diagonal", "Diagonal adjustment of the log series (Israel et al. (2))", "Ajuste diagonal de la serie logarítmica (Israel et al. (2))"),
                             ("M4-weighted", "weighted", "Weighted adjustment of the log series (Israel et al. (2'))", "Ajuste ponderado de la serie logarítmica (Israel et al. (2'))"),
                             ("M5-jlt", "jlt", "Jarrow, Lando and Turnbull's approximation (Israel et al. (3))", "Aproximación de Jarrow, Lando y Turnbull (Israel et al. (3))")):
        if g.get(key) is None:
            continue  # the engine could not form it: the log series diverges (S >= 1) or some p_ii <= 0
        rows.append((mid, "generator", key, _t(en, es), _t(key.upper() if key == "jlt" else key.capitalize(), key.upper() if key == "jlt" else key.capitalize()),
                     "riskvalidation.transitions.embedding.generator", {"l1_distance": {"value": float(g[key]["l1"]), "unit": "probability"}}))
    return [{"id": mid, "family": fam, "rung": rung, "title": title, "short_title": short, "engine": engine,
             "engine_version": rv, "licence": "MIT", "checkpoint_sha256": None, "calibration": None, "parameters": params}
            for mid, fam, rung, title, short, engine, params in rows]


def _with_details(records: list[dict[str, Any]], out: dict[str, Any]) -> list[dict[str, Any]]:
    """The models artifact's records carry the model itself in ``details``: the pooled matrix of the cohort estimator,
    each generator's rates (S&P's, the agency the families and the live parity are built on)."""
    gen = out["generators"]
    details = {"cohort": {"matrix": out["pooled"]["matrix"]}}
    details.update({k: {"generator": gen[k]["generator"]} for k in ("em", "diagonal", "weighted", "jlt") if gen.get(k)})
    return [{**r, "details": details[r["rung"]]} for r in records]


def _family_models(out: dict[str, Any], rv: str) -> list[dict[str, Any]]:
    return [{"id": "G1-rating-paths", "family": "generator", "rung": out["family"],
             "title": _t("Rating paths with a known generator", "Trayectorias de calificación con un generador conocido"),
             "short_title": _t("RatingPaths", "RatingPaths"), "engine": "riskvalidation.generators.paths.RatingPaths",
             "engine_version": rv, "licence": "MIT", "checkpoint_sha256": None, "calibration": None,
             "parameters": {"repetitions": {"value": float(out["design"]["reps"]), "unit": "count"}}}]


def _published_models(rv: str) -> list[dict[str, Any]]:
    rows = (("P1-irw", _t("Israel, Rosenthal and Wei (2001), section 4", "Israel, Rosenthal y Wei (2001), sección 4"), "riskvalidation.transitions.embedding"),
            ("P2-sr190", _t("Schuermann and Hanson (2004), Table 5", "Schuermann y Hanson (2004), Tabla 5"), "riskvalidation.transitions.intervals"),
            ("P3-engelmann", _t("Engelmann (2024), section 4", "Engelmann (2024), sección 4"), "riskvalidation.transitions.ttc"))
    return [{"id": mid, "family": "reproduction", "rung": "paper", "title": title, "short_title": title, "engine": engine,
             "engine_version": rv, "licence": "MIT", "checkpoint_sha256": None, "calibration": None, "parameters": {}}
            for mid, title, engine in rows]


# ---------------------------------------------------------------------------------------------------------------------
# the bake


class C04:
    id = CASE_ID
    slug = "rating-transitions"
    title = _t("Rating transitions and TTC PD by grade", "Transiciones de calificación y PD TTC por grado")
    category_id = "ratings-calibration"
    kind = "real"  # the agency variants read CEREP; the generator variants are labelled synthetic
    question = _t("What do the agencies' published migrations say about PDs by grade, and how far can a migration matrix be trusted to give them, project them, or show the chain is Markov and stable?",
                  "¿Qué dicen las migraciones publicadas por las agencias sobre las PD por grado, y cuánto se puede confiar en una matriz de migración para darlas, proyectarlas o mostrar que la cadena es de Markov y estable?")
    sources = SOURCES

    def bake(self, seed: int, paths: Any, data_root: Path) -> dict[str, Any]:
        from ..io import sources as registry

        registry.assert_case_inputs(CASE_ID, list(SOURCES))
        rv = _v("riskvalidation")
        t0 = time.time()
        agencies: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
        for v in AGENCY_VARIANTS:
            got = cerep.read_agency(Path(data_root), v["code"], YEARS, SEMESTER_YEARS, source_id=CEREP_SOURCE,
                                    windows=WINDOWS)
            if not got["annual"]:
                raise RuntimeError(f"{CASE_ID}: no CEREP cohorts for {v['code']} in the data root (fetch esma-cerep)")
            agencies[v["id"]] = _agency(v["code"], got)
            _log(f"{v['code']}: {len(got['annual'])} annual, {len(got['semesters'])} semester and "
                 f"{len(got['windows'])} five-year cohorts")
        q, obligors = _generator_from_sp(agencies["sp"][0])
        families = {f["id"]: c04_families.family_outputs(f["id"], q, obligors, seed, reps=REPS) for f in FAMILY_VARIANTS}
        one_year = expm(q)
        for out in families.values():
            # the live projection's matrix on a generator variant: the one-year matrix of the true generator
            out["generator"]["one_year_matrix"] = one_year.tolist()
        _log(f"families: {time.time() - t0:.0f} s")
        published = c04_published.published_outputs(Path(data_root))
        # the live projection needs a default column: Moody's transition page has none
        parity = c04_parity.parity({v["code"]: np.asarray(agencies[v["id"]][0]["pooled"]["matrix"]) for v in AGENCY_VARIANTS
                                    if _has_default(agencies[v["id"]][0])}, _origination(agencies["sp"][0]))
        models_rel = f"{CASE_ID}/models-transitions.json"
        lineage_models = lin.build(CASE_ID, sources=[CEREP_SOURCE], truth_status="real-outcomes", seed=seed,
                                   code_version=__version__, riskvalidation_version=rv)
        models_doc = build_models_artifact(
            case_id=CASE_ID, fit_id="transitions", model=_with_details(_agency_models(agencies["sp"][0], rv), agencies["sp"][0]),
            fit={"parity": parity, "generator": {"q": q.tolist(), "obligors": obligors,
                                                 "source": "EM on S&P's pooled annual counts (CEREP)"}},
            lineage=lineage_models, lane={"lane": "precompute", "reasons": []})
        models_entry = write_artifact(paths.root, models_rel, models_doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
        entries: list[dict[str, Any]] = [{"role": "models", "variant_id": "models-transitions", "truth_status": "real-outcomes",
                                           "title": _t("The pooled matrices, the generator and the live parity", "Las matrices agrupadas, el generador y la paridad en vivo"),
                                           "short_title": _t("Models", "Modelos"), "regime": REGIME_AGENCY, **models_entry}]
        values: dict[str, float] = {}

        for v in AGENCY_VARIANTS:
            out, tests = agencies[v["id"]]
            out = {**out, "origination": _origination(out), "irb": dict(IRB)}
            lineage = lin.build(CASE_ID, sources=[CEREP_SOURCE], truth_status="real-outcomes", seed=seed,
                                code_version=__version__, riskvalidation_version=rv)
            findings = agency_findings(v, out, tests)
            art = build_artifact(case_id=CASE_ID, variant_id=v["id"], model=_agency_models(out, rv), outputs=out,
                                 tests=tests, impact=agency_impact(out), findings=findings, lineage=lineage,
                                 lane={"lane": "precompute", "reasons": []})
            entries.append(self._write(paths, v, art, REGIME_AGENCY, "real-outcomes", models_rel))
            values.update(agency_values(v["id"], out))

        for f in FAMILY_VARIANTS:
            out = families[f["id"]]
            lineage = lin.build(CASE_ID, sources=[], truth_status="synthetic-known-truth", seed=seed,
                                code_version=__version__, riskvalidation_version=rv, generators=("RatingPaths",))
            art = build_artifact(case_id=CASE_ID, variant_id=f["id"], model=_family_models(out, rv), outputs=out,
                                 tests=[], impact=family_impact(out), findings=family_findings(f, out), lineage=lineage,
                                 lane={"lane": "precompute", "reasons": []})
            entries.append(self._write(paths, f, art, REGIME_FAMILY, "synthetic-known-truth", models_rel))
            values.update(family_values(f["id"], out))

        lineage = lin.build(CASE_ID, sources=list(PAPERS), truth_status="published-answer", seed=seed,
                            code_version=__version__, riskvalidation_version=rv)
        art = build_artifact(case_id=CASE_ID, variant_id=PUBLISHED_VARIANT["id"], model=_published_models(rv),
                             outputs=published, tests=[], impact=published_impact(published),
                             findings=published_findings(published), lineage=lineage,
                             lane={"lane": "precompute", "reasons": []})
        entries.append(self._write(paths, PUBLISHED_VARIANT, art, REGIME_PUBLISHED, "published-answer", models_rel))
        values.update(published_values(published))

        ranges = expectations.check(CASE_ID, EXPECT, values)
        manifest = build_case_manifest(
            case_id=CASE_ID, title=self.title, category={"en": "Ratings and calibration", "es": "Calificaciones y calibración"},
            question=self.question, sources=list(SOURCES), seed=seed, variants=entries, default_variant=DEFAULT_VARIANT,
            # no contract-1 family: CEREP's answers are checked by pipeline.io.cerep (labels, tab 2 against tab 4) and the
            # papers by pipeline.io.papers against their own print; a reader that cannot satisfy them refuses the bake
            contract={}, expect=ranges, riskvalidation_version=rv, source_details=_source_details(SOURCES))
        write_json(paths.manifests / f"{CASE_ID}.json", manifest)
        _log(f"baked in {time.time() - t0:.0f} s")
        return manifest

    @staticmethod
    def _write(paths: Any, v: dict[str, Any], art: dict[str, Any], regime: dict[str, str], truth: str,
               models_rel: str) -> dict[str, Any]:
        rel = f"{CASE_ID}/{v['id']}.json"
        entry = write_artifact(paths.root, rel, art, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)
        _log(f"variant {v['id']}: {len(art['tests'])} test results, {len(art['findings'])} findings, {entry['bytes']:,} bytes")
        return {"role": "variant", "variant_id": v["id"], "title": v["title"], "short_title": v["short"], "regime": regime,
                "truth_status": truth, "models_ref": models_rel, **entry}


def _source_details(ids) -> dict[str, dict[str, str]]:
    from ..io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing,
                "licence": reg[i].licence, "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


# ---------------------------------------------------------------------------------------------------------------------
# impact, findings and the values the expected ranges check: written against the first bake's numbers


GRADES = cerep.GRADES
SPECULATIVE = (4, 5, 6)  # BB, B, CCC to C
#: the IRB convention of the impact is C05's, one source for both cases and the live parity (Basel III final,
#: corporate, F-IRB LGD 45%, maturity 2.5 years): a grade with no default in any cohort has a long-run average of 0,
#: which the engine floors at the regime's floor (CRE32.4; riskvalidation 0.4.1)
IRB = IRB_ASSUMPTIONS
#: the momentum strength whose fitted hazard coefficient is dos Reis et al.'s on Moody's data (c = 0.33; dossier 13
#: section 16: alpha 0.125 gives c = 0.336 on the EM generator of S&P's counts)
EMPIRICAL_ALPHA = 0.125


def _pct(x: float, decimals: int = 2) -> tuple[str, str]:
    en = f"{100 * x:.{decimals}f}%"
    return en, en.replace(".", ",")


def _miles(x: float) -> str:
    """A count as the Spanish texts write it: a point between thousands."""
    return f"{x:,.0f}".replace(",", ".")


def _num(x: float, decimals: int = 2) -> tuple[str, str]:
    en = f"{x:.{decimals}f}"
    return en, en.replace(".", ",")


def _rw(pd: float) -> float:
    return float(_irb_rw(pd))


def _lifetime_gap(out: dict[str, Any]) -> dict[str, Any] | None:
    """The lifetime check's headline (CT-415): in the latest five-year window with every value, the speculative grade
    whose lived five-year default rate (tab 2's window, rated defaulters over its cohort) the chained annual matrices
    miss most. None where no window has the chain (Moody's: no default category)."""
    best = None
    for w in reversed(out.get("lifetime") or []):
        obs, proj = w["observed"], w["projected"]
        lived, chain, pooled, end = obs.get("cumulative_d2"), proj.get("chain_state"), proj.get("pooled_power"), obs.get("default_end")
        if lived is None or chain is None or pooled is None or end is None:
            continue
        for g in SPECULATIVE:
            if None in (lived[g], chain[g], pooled[g], end[g]) or not w["size"][g]:
                continue
            gap = lived[g] - chain[g]
            if best is None or gap > best["gap"]:
                best = {"label": w["label"], "grade": GRADES[g], "lived": lived[g], "chain": chain[g],
                        "pooled": pooled[g], "end": end[g], "gap": gap}
        if best is not None:
            return best
    return None


def _poss(name: str) -> str:
    """The possessive of an agency's short name: S&P's, Fitch's, Moody's (already one)."""
    return name if name.endswith("'s") else f"{name}'s"


def _p(p: float) -> str:
    """A p-value as the findings print it; one that underflows to zero is said to be below the smallest double."""
    return "p < 1e-300" if p == 0.0 else f"p = {p:.1e}"


def _span(labels: list[str]) -> str:
    """Year labels as runs: "2006 to 2014" for consecutive years, runs joined by commas."""
    years = sorted(int(x) for x in labels)
    runs, start = [], years[0]
    for a, b in zip(years, years[1:] + [None], strict=True):
        if b != a + 1:
            runs.append(str(start) if start == a else f"{start} to {a}")
            start = b
    return ", ".join(runs)


def _has_default(out: dict[str, Any]) -> bool:
    """Whether the agency's transition page has a default category (Moody's has none: its matrix never reaches D)."""
    return out["pd"].get("d4") is not None


def _mix(sizes: list[float]) -> np.ndarray:
    s = np.asarray(sizes, dtype=float)
    return s / s.sum()


def _portfolio_rw(pds: list[float | None], mix: np.ndarray) -> float | None:
    """The IRB risk weight of a portfolio with the grade mix ``mix`` and one PD per grade (None where undefined)."""
    if any(p is None for p, w in zip(pds, mix, strict=True) if w > 0):
        return None
    return float(sum(w * _rw(p) for p, w in zip(pds, mix, strict=True) if w > 0))


def _ttc(out: dict[str, Any]) -> dict[str, float]:
    """Engelmann's TTC portfolio of the pooled matrix with the agency's cohort mix as origination, its default rate, and
    the default rate of the latest cohort's mix under the same matrix."""
    from riskvalidation.transitions import ttc

    p = np.asarray(out["pooled"]["matrix"], dtype=float)
    r = ttc.ttc_portfolio(p, out["origination"])
    latest = np.append(_mix(out["cohorts"][-1]["size"]), 0.0)
    return {"ttc_default_rate": float(r["default_rate"]), "latest_default_rate": float(latest @ p[:, -1]),
            "ttc_l1_to_latest": float(np.abs(np.asarray(r["portfolio"]) - latest).sum())}


def agency_impact(out: dict[str, Any]) -> dict[str, Any]:
    lra, mix = out["lra"], _mix(np.asarray([c["size"] for c in out["cohorts"]], dtype=float).sum(axis=0))
    items: dict[str, Any] = {}
    for d, en, es in (("d2", "default page (D2)", "página de incumplimientos (D2)"),
                      ("d4", "transition matrix (D4)", "matriz de transición (D4)")):
        if lra.get(d) is None:
            continue
        items[f"lra_{d}_ccc_c"] = {"value": lra[d]["rate"][6], "unit": "probability",
                                   "label": _t(f"Long-run average PD of CCC to C, {en}", f"PD promedio de largo plazo de CCC a C, {es}")}
        rw = _portfolio_rw(lra[d]["rate"], mix)
        if rw is not None:
            items[f"rw_{d}"] = {"value": rw, "unit": "share of EAD",
                                "label": _t(f"IRB risk weight of the cohort mix, PDs of the {en}",
                                            f"Ponderador IRB de la mezcla de cohortes, PD de la {es}")}
    rw_em = _portfolio_rw(out["generators"]["em"]["pd_1y"], mix) if _has_default(out) else None
    if rw_em is not None:
        items["rw_em"] = {"value": rw_em, "unit": "share of EAD",
                          "label": _t("IRB risk weight of the cohort mix, PDs of the EM generator",
                                      "Ponderador IRB de la mezcla de cohortes, PD del generador EM")}
    if not _has_default(out):
        return items
    t = _ttc(out)
    items["ttc_default_rate"] = {"value": t["ttc_default_rate"], "unit": "probability",
                                 "label": _t("Default rate of the pooled matrix's TTC portfolio (Engelmann)",
                                             "Tasa de incumplimiento del portafolio TTC de la matriz agrupada (Engelmann)")}
    items["latest_default_rate"] = {"value": t["latest_default_rate"], "unit": "probability",
                                    "label": _t("Default rate of the latest cohort's mix under the pooled matrix",
                                                "Tasa de incumplimiento de la mezcla de la última cohorte con la matriz agrupada")}
    return items


def agency_findings(v: dict[str, Any], out: dict[str, Any], tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    code, name = v["code"], v["short"]["en"]
    lra, f = out["lra"], []
    # the default definitions (dossier 13 section 15; CEREP help file sections 4.2 to 4.4)
    gap = (out.get("definition_gap") or {}).get("d4_over_d2")
    if lra.get("d4") is not None and lra.get("d2") is not None and gap is not None:
        r = [gap[5], gap[6]]
        if r[1] is not None and r[1] < 0.8:
            d4, d2 = _pct(lra["d4"]["rate"][6]), _pct(lra["d2"]["rate"][6])
            rb = "" if r[0] is None else f" and {100 * r[0]:.0f}% for B"
            rb_es = "" if r[0] is None else f" y {100 * r[0]:.0f}% para B"
            f.append({"id": "F-DEF-GAP", "severity": "S2", "status": "open", "evidence": ["design:definition_gap"],
                      "title": _t(f"{name}: the transition matrix's default column gives {100 * r[1]:.0f}% of the default page's PD for CCC to C{rb}, pooled over the years both pages hold (long-run averages {d4[0]} against {d2[0]}): a PD read from CEREP's migration matrix understates speculative defaults",
                                  f"{name}: la columna de incumplimiento de la matriz de transición da {100 * r[1]:.0f}% de la PD de la página de incumplimientos para CCC a C{rb_es}, agrupada en los años que ambas páginas cubren (promedios de largo plazo {d4[1]} contra {d2[1]}): una PD leída de la matriz de migración de CEREP subestima los incumplimientos especulativos")})
    elif lra.get("d4") is None:
        f.append({"id": "F-NO-D4", "severity": "S3", "status": "accepted", "evidence": ["design:definition_gap"],
                  "title": _t(f"{_poss(name)} transition page has no default category: its PDs come from the default pages only, and a migration matrix read from CEREP carries no default column",
                              f"La página de transiciones de {name} no tiene categoría de incumplimiento: sus PD vienen solo de las páginas de incumplimientos, y una matriz de migración leída de CEREP no trae columna de incumplimiento")})
    # years whose transition page has default categories with no rating in them while the default page counts
    # defaulted ratings (Fitch's EU entity, 2006 to 2014: its defaulted ratings sit in the withdrawals column)
    if _has_default(out):
        empty = [c for c in out["cohorts"] if c.get("defaulted") is not None and sum(c["defaulted"]) > 0
                 and sum(row[7] for row in c["counts"]) == 0]
        if empty:
            lost = int(sum(sum(c["defaulted"]) for c in empty))
            labels = [c["label"] for c in empty]
            span = _span(labels)
            f.append({"id": "F-D4-EMPTY", "severity": "S2", "status": "open", "evidence": ["design:cohorts.counts"],
                      "title": _t(f"{name}: the transition page's default categories hold no rating in {len(empty)} of {len(out['cohorts'])} years ({span}) while the default page counts {lost:,} defaulted ratings in them; their defaulted ratings sit in the withdrawals column, so a migration matrix read from those years gives every grade a one-year PD of zero",
                                  f"{name}: las categorías de incumplimiento de la página de transiciones no tienen calificación alguna en {len(empty)} de {len(out['cohorts'])} años ({span.replace(' to ', ' a ')}) mientras la página de incumplimientos cuenta {_miles(lost)} calificaciones incumplidas en ellos; sus calificaciones incumplidas quedan en la columna de retiros, así que una matriz de migración leída de esos años da a cada grado una PD anual de cero")})
    diffs = [(c["label"], g, c["defaulted_cohort"][g], c["size"][g]) for c in out["cohorts"]
             if c.get("defaulted_cohort") is not None for g in range(7) if c["defaulted_cohort"][g] != c["size"][g]]
    if diffs:
        lab, g, t2n, t4n = max(diffs, key=lambda x: abs(x[2] - x[3]))
        years = sorted({x[0] for x in diffs})
        f.append({"id": "F-TAB2-COHORT", "severity": "S3", "status": "accepted", "evidence": ["design:cohorts.defaulted_cohort"],
                  "title": _t(f"{name}: ESMA's default page and transition page count different cohorts in {len(years)} of {len(out['cohorts'])} years, most in the grades with many defaults (largest: {GRADES[g]} in {lab}, {t2n:,.0f} ratings against {t4n:,.0f}); D2 is taken over the default page's own cohort",
                              f"{name}: la página de incumplimientos y la de transiciones de ESMA cuentan cohortes distintas en {len(years)} de {len(out['cohorts'])} años, sobre todo en los grados con muchos incumplimientos (la mayor: {GRADES[g]} en {lab}, {_miles(t2n)} calificaciones contra {_miles(t4n)}); D2 se toma sobre la cohorte de la propia página de incumplimientos")})
    # the Markov and time-homogeneity checks on the aggregates
    th = out["homogeneity"]["annual"]
    if th and th.get("p_value") is not None and th["p_value"] < 0.01:
        f.append({"id": "F-HOMOG", "severity": "S2", "status": "open", "evidence": [f"rating.time_homogeneity@{code}@annual"],
                  "title": _t(f"{name}: the one-year matrix is not the same every year (chi-square {th['statistic']:.0f} on {th['dof']} degrees of freedom, {_p(th['p_value'])}); a matrix pooled over the years averages different regimes",
                              f"{name}: la matriz anual no es la misma cada año (chi-cuadrado {_num(th['statistic'], 0)[1]} con {th['dof']} grados de libertad, {_p(th['p_value'])}); una matriz agrupada en los años promedia regímenes distintos")})
    refs = [r for r in out["homogeneity"]["reference"] if r.get("p_value") is not None]
    rejected = [r for r in refs if r["p_value"] < 0.01]
    if rejected:
        top = sorted(rejected, key=lambda r: -r["statistic"] / max(r["dof"], 1))[:3]
        worst = ", ".join(r["label"] for r in top)
        f.append({"id": "F-YEARS", "severity": "S3", "status": "open",
                  "evidence": [f"rating.matrix_reference@{code}@{r['label']}" for r in rejected],
                  "title": _t(f"{name}: {len(rejected)} of {len(refs)} years' migrations depart from the pooled matrix at 1%, most in {worst} (likelihood ratio per degree of freedom); with cohorts of thousands of ratings the test sees every year's own conditions",
                              f"{name}: las migraciones de {len(rejected)} de {len(refs)} años se apartan de la matriz agrupada al 1%, más en {worst} (razón de verosimilitud por grado de libertad); con cohortes de miles de calificaciones la prueba ve las condiciones propias de cada año")})
    # the embedding problem
    emb, gen = out["embedding"], out["generators"]
    if emb["exact_generator_excluded"] and _has_default(out):
        moves = len(emb["theorem3"]["c"])
        em0, coh0 = gen["em"]["pd_1y"][0], np.asarray(out["pooled"]["matrix"])[0, -1]
        mono = "" if emb["stochastically_monotone"] else "; it is not stochastically monotone either"
        mono_es = "" if emb["stochastically_monotone"] else "; tampoco es estocásticamente monótona"
        f.append({"id": "F-EMBED", "severity": "S3", "status": "accepted", "evidence": ["design:embedding"],
                  "title": _t(f"{name}: no generator reproduces the pooled matrix ({moves} moves reachable but never observed, Israel et al.'s Theorem 3(c){mono}); the EM generator gives AAA a one-year PD of {1e4 * em0:.2f}bp where the cohort gives {1e4 * coh0:.2f}bp",
                              f"{name}: ningún generador reproduce la matriz agrupada ({moves} movimientos alcanzables pero nunca observados, Teorema 3(c) de Israel et al.{mono_es}); el generador EM da a AAA una PD anual de {_num(1e4 * em0)[1]}pb donde la cohorte da {_num(1e4 * coh0)[1]}pb")})
    if gen.get("jlt") and gen.get("diagonal") and gen["jlt"]["l1"] > 5 * gen["diagonal"]["l1"]:
        ratio = gen["jlt"]["l1"] / gen["diagonal"]["l1"]
        f.append({"id": "F-JLT", "severity": "S3", "status": "open", "evidence": ["design:generators"],
                  "title": _t(f"{name}: the JLT approximation is {ratio:.0f} times further from the pooled matrix than the diagonal adjustment (L1 {gen['jlt']['l1']:.4f} against {gen['diagonal']['l1']:.4f})",
                              f"{name}: la aproximación JLT está {ratio:.0f} veces más lejos de la matriz agrupada que el ajuste diagonal (L1 {_num(gen['jlt']['l1'], 4)[1]} contra {_num(gen['diagonal']['l1'], 4)[1]})")})
    # what the PDs by grade can and cannot tell apart
    d = lra.get("d2") or lra.get("d3")
    if d is not None:
        rates = d["rate"]
        inv = [(GRADES[g], GRADES[g + 1]) for g in range(6) if rates[g] is not None and rates[g + 1] is not None and rates[g] > rates[g + 1]]
        if inv:
            pairs = ", ".join(f"{a} above {b}" for a, b in inv)
            pairs_es = ", ".join(f"{a} sobre {b}" for a, b in inv)
            f.append({"id": "F-MONOTONE", "severity": "S2", "status": "open", "evidence": ["design:lra"],
                      "title": _t(f"{name}: the long-run average PD is not monotone by grade ({pairs})",
                                  f"{name}: la PD promedio de largo plazo no es monótona por grado ({pairs_es})")})
        lo, hi = d["jeffreys"]["lower"], d["jeffreys"]["upper"]
        overlap = [f"{GRADES[g]} and {GRADES[g + 1]}" for g in range(3)
                   if None not in (lo[g], hi[g], lo[g + 1], hi[g + 1]) and hi[g] >= lo[g + 1]]
        if overlap:
            f.append({"id": "F-NOTCH", "severity": "S3", "status": "open", "evidence": ["design:lra"],
                      "title": _t(f"{name}: the investment grades' long-run averages cannot be told apart for {'; '.join(overlap)} (their Jeffreys intervals overlap)",
                                  f"{name}: los promedios de largo plazo de los grados de inversión no se distinguen para {'; '.join(x.replace(' and ', ' y ') for x in overlap)} (sus intervalos de Jeffreys se traslapan)")})
        rows = out["pd"]["d2"] if out["pd"].get("d2") is not None else out["pd"]["d3"]
        top = [r[0] for r in rows if r[0] is not None]
        zero = sum(1 for x in top if x == 0)
        if top and zero:
            em0 = (gen.get("em") or {}).get("pd_1y")
            em0 = None if em0 is None else em0[0]
            tail = "" if em0 is None else f", while the EM generator gives {1e4 * em0:.2f}bp"
            tail_es = "" if em0 is None else f", mientras el generador EM da {_num(1e4 * em0)[1]}pb"
            f.append({"id": "F-COHORT-ZERO", "severity": "S3", "status": "accepted", "evidence": ["design:pd"],
                      "title": _t(f"{name}: the cohort PD of AAA is zero in {zero} of {len(top)} years{tail}",
                                  f"{name}: la PD de cohorte de AAA es cero en {zero} de {len(top)} años{tail_es}")})
    life = _lifetime_gap(out)
    if life is not None:
        f.append({"id": "F-LIFETIME", "severity": "S2", "status": "open", "evidence": ["design:lifetime"],
                  "title": _t(f"{name}: of the ratings in {life['grade']} at the start of {life['label']}, {_pct(life['lived'])[0]} defaulted within the five years (the default page's window); the window's own annual matrices chained give {_pct(life['chain'])[0]} and the pooled matrix to the fifth power {_pct(life['pooled'])[0]}, while the window's transition page shows {_pct(life['end'])[0]} in default at its end (defaulted ratings withdrawn): a lifetime PD chained from one-year matrices understates what the cohort lived",
                              f"{name}: de las calificaciones en {life['grade']} al inicio de {life['label'].replace('-', ' a ')}, {_pct(life['lived'])[1]} incumplieron dentro de los cinco años (la página de incumplimientos de la ventana); las matrices anuales de la propia ventana encadenadas dan {_pct(life['chain'])[1]} y la matriz agrupada a la quinta potencia {_pct(life['pooled'])[1]}, mientras la página de transiciones de la ventana muestra {_pct(life['end'])[1]} en incumplimiento al final (calificaciones incumplidas retiradas): una PD de vida encadenada desde matrices anuales subestima lo que vivió la cohorte")})
    # the drift a projection inherits from the matrix (Engelmann 2024); a matrix without a default column has none
    if not _has_default(out):
        return f
    t = _ttc(out)
    f.append({"id": "F-TTC-DRIFT", "severity": "S3", "status": "open", "evidence": ["design:ttc"],
              "title": _t(f"{name}: the pooled matrix's TTC portfolio defaults at {_pct(t['ttc_default_rate'])[0]} a year; the latest cohort's mix under the same matrix at {_pct(t['latest_default_rate'])[0]}: an unstressed projection moves by the difference with no scenario at all",
                          f"{name}: el portafolio TTC de la matriz agrupada incumple {_pct(t['ttc_default_rate'])[1]} al año; la mezcla de la última cohorte con la misma matriz {_pct(t['latest_default_rate'])[1]}: una proyección sin estrés se mueve en la diferencia sin escenario alguno")})
    return f


def agency_values(vid: str, out: dict[str, Any]) -> dict[str, float]:
    lra = out["lra"]
    d = lra.get("d2") or lra.get("d3")
    vals = {f"{vid}_cohorts": float(len(out["cohorts"])), f"{vid}_lra_ccc_c": float(d["rate"][6]),
            f"{vid}_lra_bb": float(d["rate"][4]), f"{vid}_l1_em": float(out["generators"]["em"]["l1"]),
            **({f"{vid}_l1_jlt": float(out["generators"]["jlt"]["l1"])} if out["generators"].get("jlt") else {})}
    if _has_default(out):
        vals[f"{vid}_ttc_default_rate"] = _ttc(out)["ttc_default_rate"]
    if out["homogeneity"]["annual"]:
        vals[f"{vid}_time_homogeneity_p"] = float(out["homogeneity"]["annual"]["p_value"])
    if lra.get("d4") is not None and lra.get("d2") is not None and lra["d2"]["pooled_rate"][6]:
        vals[f"{vid}_d4_over_d2_ccc_c"] = float(lra["d4"]["pooled_rate"][6] / lra["d2"]["pooled_rate"][6])
    return vals


def _sim(out: dict[str, Any], key: str, rule: str = "p<0.05") -> float:
    return float(next(s for s in out["simulations"] if s["key"] == key)["rates"][rule]["rate"])


def _rung(out: dict[str, Any], value: float) -> dict[str, Any]:
    return next(r for r in out["rungs"] if r["value"] == value)


def family_impact(out: dict[str, Any]) -> dict[str, Any]:
    fid = out["family"]
    if fid == "markov":
        r = out["rungs"][0]
        z = r["estimators"]["cohort"]["zero"][0]["rate"]
        cov = r["coverage"]["wald"][0]["rate"]
        return {"zero_share_aaa": {"value": z, "unit": "probability", "label": _t("Share of repetitions with a cohort PD of exactly zero for AAA", "Proporción de repeticiones con PD de cohorte exactamente cero para AAA")},
                "wald_coverage_aaa": {"value": cov, "unit": "probability", "label": _t("Coverage of the 95% Wald interval for AAA", "Cobertura del intervalo de Wald al 95% para AAA")}}
    if fid == "momentum":
        r = _rung(out, EMPIRICAL_ALPHA)
        err = r["error_cohort_power"]["mean"][3]
        return {"projection_error_bbb": {"value": err, "unit": "probability difference", "label": _t("Markov projection error of the five-year BBB PD at the empirical momentum (alpha 0.125)", "Error de la proyección de Markov de la PD a cinco años de BBB con el momentum empírico (alfa 0,125)")},
                "momentum_power_weak": {"value": _sim(out, "rating.momentum@alpha0.025"), "unit": "probability", "label": _t("The momentum test's rejection rate at a fifth of the empirical strength (alpha 0.025)", "Tasa de rechazo de la prueba de momentum a un quinto de la fuerza empírica (alfa 0,025)")}}
    if fid == "cycle":
        return {"th_power_k_1_5": {"value": _sim(out, "rating.time_homogeneity@k1.5"), "unit": "probability", "label": _t("Time homogeneity's rejection rate with downgrades times 1.5 for a year", "Tasa de rechazo de homogeneidad temporal con rebajas por 1,5 durante un año")}}
    if fid == "withdrawals":
        r = _rung(out, 9.0)
        return {"removed_bias_b": {"value": r["pd_removed"]["bias"][5], "unit": "probability difference", "label": _t("Bias of the B PD with withdrawals removed, informative k 9", "Sesgo de la PD de B con retiros eliminados, informativo k 9")}}
    r = _rung(out, 50)
    return {"wald_coverage_aaa_50": {"value": r["coverage"]["wald"][0], "unit": "probability", "label": _t("Exact coverage of the 95% Wald interval for AAA with 50 obligors", "Cobertura exacta del intervalo de Wald al 95% para AAA con 50 deudores")}}


def family_findings(f: dict[str, Any], out: dict[str, Any]) -> list[dict[str, Any]]:
    from riskvalidation.harness import size_bound

    fid, res = out["family"], []
    if fid == "markov":
        r = out["rungs"][0]
        est, reps = r["estimators"], out["design"]["reps"]
        z = est["cohort"]["zero"][0]["rate"]
        truth = out["generator"]["pd_1y"][0]
        res.append({"id": "F-COHORT-ZERO", "severity": "S3", "status": "accepted", "evidence": ["design:rungs.estimators.zero"],
                    "title": _t(f"With S&P-like cohorts over five years, the pooled cohort PD of AAA is exactly zero in {100 * z:.0f}% of repetitions (true {1e4 * truth:.2f}bp); the duration and EM estimates are positive in every one",
                                f"Con cohortes como las de S&P en cinco años, la PD de cohorte agrupada de AAA es exactamente cero en {100 * z:.0f}% de las repeticiones (verdadera {_num(1e4 * truth)[1]}pb); las estimaciones de duración y EM son positivas en todas")})
        snap = ("em", "diagonal", "weighted", "cohort")
        b = {m: est[m]["bias"][0] for m in (*snap, "duration")}
        se = {m: est[m]["bias_mcse"][0] for m in (*snap, "duration")}
        rm = {m: est[m]["rmse"][0] for m in (*snap, "duration")}
        # do the snapshot estimators' biases differ beyond their Monte Carlo errors (two SEs of a difference)?
        apart = any(abs(b[a] - b[c]) > 2 * (se[a] ** 2 + se[c] ** 2) ** 0.5 for a in snap for c in snap if a < c)
        verdict = ("their biases differ beyond their Monte Carlo errors" if apart else
                   "their biases agree within their Monte Carlo errors, so EM's smaller overstatement of the top grade "
                   "that Smith and dos Reis report does not show at these sizes")
        verdict_es = ("sus sesgos difieren más allá de sus errores de Monte Carlo" if apart else
                      "sus sesgos coinciden dentro de sus errores de Monte Carlo, así que la menor sobreestimación del mejor "
                      "grado que Smith y dos Reis reportan para EM no se ve con estos tamaños")
        lo_rm, hi_rm = min(rm[m] for m in snap), max(rm[m] for m in snap)
        res.append({"id": "F-EM-RARE", "severity": "S3", "status": "open", "evidence": ["design:rungs.estimators"],
                    "title": _t(f"AAA's one-year PD ({1e4 * truth:.2f}bp) from annual snapshots: EM, the diagonal and weighted adjustments and the cohort all miss it by {1e4 * lo_rm:.1f}bp to {1e4 * hi_rm:.1f}bp in RMSE (biases {1e4 * b['em']:+.2f}, {1e4 * b['diagonal']:+.2f}, {1e4 * b['weighted']:+.2f} and {1e4 * b['cohort']:+.2f}bp, Monte Carlo error about {1e4 * se['em']:.2f}bp), and {verdict}; the duration estimator, which needs the transition times CEREP's stock model does not publish, reaches {1e4 * rm['duration']:.2f}bp",
                                f"La PD anual de AAA ({_num(1e4 * truth)[1]}pb) desde instantáneas anuales: EM, los ajustes diagonal y ponderado y la cohorte la yerran en {_num(1e4 * lo_rm, 1)[1]}pb a {_num(1e4 * hi_rm, 1)[1]}pb de RMSE (sesgos {_num(1e4 * b['em'])[1]}, {_num(1e4 * b['diagonal'])[1]}, {_num(1e4 * b['weighted'])[1]} y {_num(1e4 * b['cohort'])[1]}pb, error de Monte Carlo cerca de {_num(1e4 * se['em'])[1]}pb), y {verdict_es}; el estimador de duración, que necesita los tiempos de transición que el modelo de stock de CEREP no publica, llega a {_num(1e4 * rm['duration'])[1]}pb")})
        bound = size_bound(0.05, reps)
        nulls = [s for s in out["simulations"] if s["key"].endswith("@null")]
        over = [s["test_id"] for s in nulls if s["rates"]["p<0.05"]["rate"] > bound]
        res.append({"id": "F-SIZE", "severity": "S2" if over else "S4", "status": "open" if over else "closed",
                    "evidence": [f"rate:{s['key']}" for s in nulls],
                    "title": _t(f"The four transition tests on the S&P-like chain: {'above their size bound: ' + ', '.join(over) if over else 'all hold their size at 5%'} ({reps} repetitions)",
                                f"Las cuatro pruebas de transición en la cadena como la de S&P: {'sobre su cota de tamaño: ' + ', '.join(over) if over else 'todas mantienen su tamaño al 5%'} ({reps} repeticiones)")})
        forms = {s["key"].rsplit("-", 1)[1]: s for s in out["simulations"] if s["key"].startswith("rating.markov_order@form-")}
        if set(forms) == {"chi2", "lr"}:
            def _holds(s: dict[str, Any]) -> bool:
                return all(s["rates"][f"p<{a:g}"]["rate"] <= size_bound(a, s["n_rep"]) for a in (0.05, 0.01))

            c2, lr = forms["chi2"], forms["lr"]
            rates = {k: [100 * s["rates"][f"p<{a:g}"]["rate"] for a in (0.05, 0.01)] for k, s in forms.items()}
            verdict = ("only the likelihood ratio holds its size" if _holds(lr) and not _holds(c2) else
                       "only the chi-square holds its size" if _holds(c2) and not _holds(lr) else
                       "both forms hold their size" if _holds(c2) else "neither form holds its size")
            verdict_es = ("solo la razón de verosimilitud mantiene su tamaño" if _holds(lr) and not _holds(c2) else
                          "solo la chi-cuadrado mantiene su tamaño" if _holds(c2) and not _holds(lr) else
                          "ambas formas mantienen su tamaño" if _holds(c2) else "ninguna forma mantiene su tamaño")
            sev = "S4" if _holds(c2) else "S2"
            res.append({"id": "F-ORDER-FORM", "severity": sev, "status": "closed" if sev == "S4" else "open",
                        "evidence": [f"rate:{c2['key']}", f"rate:{lr['key']}"],
                        "title": _t(f"The order test on S&P-like cohorts ({c2['n_rep']:,} repetitions of a Markov chain): its chi-square form rejects {rates['chi2'][0]:.2f}% at 5% and {rates['chi2'][1]:.2f}% at 1%, its likelihood ratio {rates['lr'][0]:.2f}% and {rates['lr'][1]:.2f}%: {verdict}. riskvalidation defaults to the chi-square, chosen on an even five-grade chain; which form holds depends on the cohorts' sparsity",
                                    f"La prueba de orden en cohortes como las de S&P ({_miles(c2['n_rep'])} repeticiones de una cadena de Markov): su forma chi-cuadrado rechaza {_num(rates['chi2'][0])[1]}% al 5% y {_num(rates['chi2'][1])[1]}% al 1%, su razón de verosimilitud {_num(rates['lr'][0])[1]}% y {_num(rates['lr'][1])[1]}%: {verdict_es}. riskvalidation usa por defecto la chi-cuadrado, elegida en una cadena pareja de cinco grados; qué forma se sostiene depende de lo ralas que sean las cohortes")})
        cw, cj = r["coverage"]["wald"][0]["rate"], r["coverage"]["jeffreys"][0]["rate"]
        if cw < 0.9:
            res.append({"id": "F-WALD", "severity": "S2", "status": "open", "evidence": ["design:rungs.coverage"],
                        "title": _t(f"The 95% Wald interval covers the true AAA PD in {100 * cw:.0f}% of repetitions, Jeffreys in {100 * cj:.0f}%",
                                    f"El intervalo de Wald al 95% cubre la PD verdadera de AAA en {100 * cw:.0f}% de las repeticiones, Jeffreys en {100 * cj:.0f}%")})
    elif fid == "momentum":
        weak, emp = 0.025, EMPIRICAL_ALPHA
        tests = {k: {a: _sim(out, f"rating.{k}@alpha{a:g}") for a in (weak, emp)} for k in ("time_homogeneity", "momentum")}
        c = _rung(out, emp).get("coefficient") or {}
        c_en = f" (fitted c {c['mean']:.2f}; dos Reis et al. estimate 0.33 on Moody's data)" if c else ""
        c_es = f" (c ajustado {_num(c['mean'])[1]}; dos Reis et al. estiman 0,33 con datos de Moody's)" if c else ""
        th_e, th_w = 100 * tests["time_homogeneity"][emp], 100 * tests["time_homogeneity"][weak]
        hz_e, hz_w = 100 * tests["momentum"][emp], 100 * tests["momentum"][weak]
        res.append({"id": "F-MOMENTUM-TESTS", "severity": "S3", "status": "open",
                    "evidence": [f"rate:rating.{k}@alpha{a:g}" for k in ("time_homogeneity", "momentum") for a in (weak, emp)],
                    "title": _t(f"Momentum at the empirical strength, alpha 0.125{c_en}, is seen by the hazard test in {hz_e:.0f}% of repetitions and by time homogeneity in {th_e:.0f}%; at a fifth of it (alpha 0.025) in {hz_w:.0f}% and {th_w:.0f}%",
                                f"El momentum con la fuerza empírica, alfa 0,125{c_es}, lo ve la prueba de riesgo en {hz_e:.0f}% de las repeticiones y la homogeneidad temporal en {th_e:.0f}%; a un quinto de ella (alfa 0,025) en {hz_w:.0f}% y {th_w:.0f}%")})
        r = _rung(out, emp)
        err, freq = r["error_cohort_power"]["mean"][3], r["pd_5y_frequency"]["mean"][3]
        err_se = r["error_cohort_power"]["bias_mcse"][3]
        chained = r["pd_5y_cohort_power"]["mean"][3]
        base = _rung(out, 0.0)["pd_5y_frequency"]["mean"][3]
        rel = 100 * err / freq if freq else float("nan")
        z = err / err_se if err_se else float("inf")
        res.append({"id": "F-MOMENTUM-PROJECTION", "severity": "S3", "status": "open", "evidence": ["design:rungs.error_cohort_power"],
                    "title": _t(f"Momentum at the empirical strength (alpha 0.125) raises the BBB cohort's five-year default frequency from {_pct(base)[0]} (no momentum) to {_pct(freq)[0]}; the one-year matrix estimated from the same paths, to the fifth power, gives {_pct(chained)[0]}: it carries most of the effect and misses {100 * err:+.2f} points ({rel:+.0f}%, {abs(z):.1f} Monte Carlo errors)",
                                f"El momentum con la fuerza empírica (alfa 0,125) sube la frecuencia de incumplimiento a cinco años de la cohorte BBB de {_pct(base)[1]} (sin momentum) a {_pct(freq)[1]}; la matriz anual estimada de las mismas trayectorias, a la quinta potencia, da {_pct(chained)[1]}: lleva la mayor parte del efecto y yerra {_num(100 * err)[1]} puntos ({rel:+.0f}%, {_num(abs(z), 1)[1]} errores de Monte Carlo)")})
        r = _rung(out, 0.25)
        err, freq = r["error_cohort_power"]["mean"][3], r["pd_5y_frequency"]["mean"][3]
        chained = r["pd_5y_cohort_power"]["mean"][3]
        res.append({"id": "F-MOMENTUM-PROJECTION-STRONG", "severity": "S3", "status": "open", "evidence": ["design:rungs.error_cohort_power"],
                    "title": _t(f"At twice the empirical momentum (alpha 0.25) the BBB cohort defaults {_pct(freq)[0]} within five years and the one-year matrix to the fifth power gives {_pct(chained)[0]}, {100 * err:+.2f} points",
                                f"Con el doble del momentum empírico (alfa 0,25) la cohorte BBB incumple {_pct(freq)[1]} en cinco años y la matriz anual a la quinta potencia da {_pct(chained)[1]}, {_num(100 * err)[1]} puntos")})
    elif fid == "cycle":
        th = _sim(out, "rating.time_homogeneity@k1.5")
        r = _rung(out, 2.0)
        sy, pooled, base = r["pd_stressed_year"]["mean"][4], r["pd_lra"]["mean"][4], r["pd_true_base"][4]
        res.append({"id": "F-CYCLE", "severity": "S3", "status": "open", "evidence": ["rate:rating.time_homogeneity@k1.5", "design:rungs.pd_stressed_year"],
                    "title": _t(f"One year with downgrades times 1.5 is caught by time homogeneity in {100 * th:.0f}% of repetitions; times 2, the BB PD of that year is {sy / base:.1f} times the stable chain's and the five-year long-run average (EBA paragraph 84) {pooled / base:.2f} times",
                                f"Un año con rebajas por 1,5 lo detecta la homogeneidad temporal en {100 * th:.0f}% de las repeticiones; por 2, la PD de BB de ese año es {_num(sy / base, 1)[1]} veces la de la cadena estable y el promedio de largo plazo de cinco años (párrafo 84 de la EBA) {_num(pooled / base)[1]} veces")})
    elif fid == "withdrawals":
        r9, r0 = _rung(out, 9.0), _rung(out, 0.0)
        rem, fol = r9["pd_removed"]["bias"][5], r9["pd_followed"]["bias"][5]
        truth = r9["pd_removed"]["truth"][5]
        b0, se0 = r0["pd_removed"]["bias"][5], r0["pd_removed"]["bias_mcse"][5]
        if b0 > 2 * se0:
            why = " (removing a withdrawn rating drops its time at risk while the others' defaults stay)"
            why_es = " (eliminar una calificación retirada quita su tiempo en riesgo mientras los incumplimientos de las demás quedan)"
        elif abs(b0) <= 2 * se0:
            why, why_es = ", within its Monte Carlo error", ", dentro de su error de Monte Carlo"
        else:
            why = why_es = ""
        res.append({"id": "F-WITHDRAW", "severity": "S2", "status": "open", "evidence": ["design:rungs.pd_removed", "design:rungs.pd_followed"],
                    "title": _t(f"With informative withdrawals (k 9) the B PD with withdrawals removed is off by {100 * rem / truth:+.0f}% of the truth, followed (EBA paragraph 76) by {100 * fol / truth:+.0f}%; without informativeness by {100 * b0 / truth:+.0f}%{why}",
                                f"Con retiros informativos (k 9) la PD de B con retiros eliminados se desvía {100 * rem / truth:+.0f}% de la verdad, seguida (párrafo 76 de la EBA) {100 * fol / truth:+.0f}%; sin información {100 * b0 / truth:+.0f}%{why_es}")})
    else:
        r50, r1000 = _rung(out, 50), _rung(out, 1000)
        res.append({"id": "F-THIN", "severity": "S2", "status": "open", "evidence": ["design:rungs.coverage"],
                    "title": _t(f"Exact coverage of the 95% intervals for AAA with 50 obligors: Wald {_pct(r50['coverage']['wald'][0])[0]} (it collapses to zero width at no default, the usual case), Agresti-Coull {_pct(r50['coverage']['agresti_coull'][0])[0]}, Jeffreys {_pct(r50['coverage']['jeffreys'][0])[0]}",
                                f"Cobertura exacta de los intervalos al 95% para AAA con 50 deudores: Wald {_pct(r50['coverage']['wald'][0])[1]} (colapsa a ancho cero sin incumplimientos, el caso usual), Agresti-Coull {_pct(r50['coverage']['agresti_coull'][0])[1]}, Jeffreys {_pct(r50['coverage']['jeffreys'][0])[1]}")})
        ov = r1000["overlap_jeffreys"]
        res.append({"id": "F-NOTCH", "severity": "S3", "status": "open", "evidence": ["design:rungs.overlap_jeffreys"],
                    "title": _t(f"Even with 1,000 obligors per grade the Jeffreys intervals of AAA and AA overlap with probability {ov[0]:.4f}, of A and BBB {ov[2]:.4f}: their PDs cannot be told apart by the intervals",
                                f"Aun con 1.000 deudores por grado los intervalos de Jeffreys de AAA y AA se traslapan con probabilidad {_num(ov[0], 4)[1]}, de A y BBB {_num(ov[2], 4)[1]}: los intervalos no distinguen sus PD")})
    return res


def family_values(fid: str, out: dict[str, Any]) -> dict[str, float]:
    if fid == "markov":
        r = out["rungs"][0]
        return {"markov_zero_share_aaa": r["estimators"]["cohort"]["zero"][0]["rate"],
                "markov_wald_coverage_aaa": r["coverage"]["wald"][0]["rate"],
                "markov_jeffreys_coverage_bb": r["coverage"]["jeffreys"][4]["rate"],
                **{f"markov_size_{s['test_id'].split('.')[1]}": s["rates"]["p<0.05"]["rate"] for s in out["simulations"]
                   if s["key"].endswith("@null")},
                **{f"markov_order_{s['key'].rsplit('-', 1)[1]}_size_{lv}": s["rates"][f"p<0.{lv}"]["rate"]
                   for s in out["simulations"] if s["key"].startswith("rating.markov_order@form-") for lv in ("05", "01")}}
    if fid == "momentum":
        c = _rung(out, EMPIRICAL_ALPHA).get("coefficient") or {}
        return {"momentum_th_alpha_0_125": _sim(out, "rating.time_homogeneity@alpha0.125"),
                "momentum_order_alpha_0_025": _sim(out, "rating.markov_order@alpha0.025"),
                "momentum_hazard_alpha_0_025": _sim(out, "rating.momentum@alpha0.025"),
                "momentum_hazard_size": _sim(out, "rating.momentum@alpha0"),
                "momentum_projection_error_bbb": _rung(out, EMPIRICAL_ALPHA)["error_cohort_power"]["mean"][3],
                **({"momentum_coefficient_alpha_0_125": float(c["mean"])} if c else {})}
    if fid == "cycle":
        return {"cycle_th_k_1_5": _sim(out, "rating.time_homogeneity@k1.5"),
                "cycle_th_k_1": _sim(out, "rating.time_homogeneity@k1")}
    if fid == "withdrawals":
        r = _rung(out, 9.0)
        return {"withdrawals_removed_rel_bias_b_k9": r["pd_removed"]["bias"][5] / r["pd_removed"]["truth"][5],
                "withdrawals_followed_rel_bias_b_k9": r["pd_followed"]["bias"][5] / r["pd_followed"]["truth"][5]}
    return {"thin_wald_coverage_aaa_50": _rung(out, 50)["coverage"]["wald"][0],
            "thin_jeffreys_coverage_aaa_50": _rung(out, 50)["coverage"]["jeffreys"][0],
            "thin_overlap_aaa_aa_1000": _rung(out, 1000)["overlap_jeffreys"][0]}


def _agreed(rows: list[dict[str, Any]]) -> int:
    return sum(1 for r in rows if r["agrees"])


def published_impact(out: dict[str, Any]) -> dict[str, Any]:
    irw, sr, en = out["irw"], out["sr190"], out["engelmann"]
    return {
        "irw_agree": {"value": float(_agreed(irw["rows"])), "unit": "count",
                      "label": _t("Israel et al.'s distances recomputed from the printed matrices to six digits (of 9)",
                                  "Distancias de Israel et al. recalculadas desde las matrices impresas a seis dígitos (de 9)")},
        "sr190_agree": {"value": float(_agreed(sr["rows"])), "unit": "count",
                        "label": _t(f"Schuermann and Hanson's Table 5 intervals recomputed (of {len(sr['rows'])})",
                                    f"Intervalos de la Tabla 5 de Schuermann y Hanson recalculados (de {len(sr['rows'])})")},
        "engelmann_ttc_pd": {"value": float(en["ttc_pd"]["recomputed"]), "unit": "probability",
                             "label": _t("Engelmann's TTC portfolio default rate, recomputed",
                                         "Tasa de incumplimiento del portafolio TTC de Engelmann, recalculada")},
    }


def published_findings(out: dict[str, Any]) -> list[dict[str, Any]]:
    irw, sr, en = out["irw"], out["sr190"], out["engelmann"]
    k, n = _agreed(irw["rows"]), len(irw["rows"])
    missed = [r for r in irw["rows"] if not r["agrees"]]
    tail = ""
    tail_es = ""
    if missed:
        r = missed[0]
        tail = (f"; the {r['matrix']} {r['method'].upper()} distance ({r['printed']:.6f}) follows only from the paper's "
                f"printed four-digit generator, which gives {irw['jlt_from_printed_generator']:.6f}, while equation (3) on the "
                f"printed matrix gives {r['recomputed']:.6f}")
        tail_es = (f"; la distancia {r['method'].upper()} de {r['matrix']} ({r['printed']:.6f}) solo resulta del generador "
                   f"impreso a cuatro dígitos, que da {irw['jlt_from_printed_generator']:.6f}, mientras la ecuación (3) sobre la "
                   f"matriz impresa da {r['recomputed']:.6f}")
    out_f = [{"id": "F-IRW", "severity": "S4", "status": "closed", "evidence": ["design:irw"],
              "title": _t(f"Israel, Rosenthal and Wei (2001): {k} of {n} distances recomputed to the printed six digits{tail}",
                          f"Israel, Rosenthal y Wei (2001): {k} de {n} distancias recalculadas a los seis dígitos impresos{tail_es}")}]
    out_f.append({"id": "F-SR190", "severity": "S4", "status": "closed", "evidence": ["design:sr190"],
                  "title": _t(f"Schuermann and Hanson (2004), Table 5: {_agreed(sr['rows'])} of {len(sr['rows'])} analytical intervals recomputed to the printed digits with {sr['defaults']} defaults out of {sr['n']} (the count is not printed; it is the only one that gives every bound)",
                              f"Schuermann y Hanson (2004), Tabla 5: {_agreed(sr['rows'])} de {len(sr['rows'])} intervalos analíticos recalculados a los dígitos impresos con {sr['defaults']} incumplimientos de {sr['n']} (el conteo no está impreso; es el único que da cada cota)")})
    ok = en["ttc_pd"]["recomputed"]
    out_f.append({"id": "F-ENGELMANN", "severity": "S4", "status": "closed", "evidence": ["design:engelmann"],
                  "title": _t(f"Engelmann (2024), section 4: the TTC portfolio and its PD ({_pct(ok, 3)[0]}) recomputed to the printed digits, only with the printed matrix kept as printed (its rows sum to 1 within {en['row_sum_deviation']:.4f}) at constant balance",
                              f"Engelmann (2024), sección 4: el portafolio TTC y su PD ({_pct(ok, 3)[1]}) recalculados a los dígitos impresos, solo con la matriz impresa tal cual (sus filas suman 1 dentro de {_num(en['row_sum_deviation'], 4)[1]}) a saldo constante")})
    return out_f


def published_values(out: dict[str, Any]) -> dict[str, float]:
    return {"published_irw_agree": float(_agreed(out["irw"]["rows"])),
            "published_irw_jlt_printed_generator": float(out["irw"]["jlt_from_printed_generator"]),
            "published_sr190_agree": float(_agreed(out["sr190"]["rows"])),
            "published_sr190_defaults": float(out["sr190"]["defaults"]),
            "published_engelmann_ttc_pd": float(out["engelmann"]["ttc_pd"]["recomputed"])}


CASE = C04()
