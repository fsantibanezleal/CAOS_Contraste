"""C22 beyond the credit families (U16-P2, BL-091 and BL-075): the engine's named size and power studies.

The 21 registered p-value tests outside discrimination, pd-calibration, rating-system, stability and transitions each
have a named study in ``riskvalidation.generators.size_studies.STUDIES`` (U16-E2): a null generator at the boundary of
the test's null, one stated alternative, seeds and the fixed arguments of the test. Contraste writes no simulation
of its own for them (ADR-0069): this module lists the studies, derives one seed per (variant, key), runs them through
``simulate_study``, the engine's one entry point, in worker processes (a repetition depends on its seed and its index
only, so the pool changes no byte), and holds the texts, panels and checks that the bake owes the reader.

A registered test without a study stops the bake, naming it; so does a missing optional extra (arch, fairlearn, mapie,
statsmodels) and a repetition without a p-value. Nothing is skipped silently.
"""
from __future__ import annotations

import importlib
import os
import re
import sys
import time
import zlib
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from .c01_ladder import _t

#: the five families C22 measured before U16 (CT-301); every other registered p-value family joins in U16-P2
CREDIT_FAMILIES = frozenset({"discrimination", "pd-calibration", "rating-system", "stability", "transitions"})
LEVELS = (0.05, 0.01)
N_NULL, N_POWER = 4000, 2000
#: the optional extras of the engine (market: arch; ml: fairlearn, mapie; stress: statsmodels); the bake runs with all
EXTRAS = ("arch", "fairlearn", "mapie", "statsmodels")
ENGINE_REPOSITORY = "fsantibanezleal/CAOS_RiskValidation"


class StudyRegistryError(RuntimeError):
    """A registered p-value test has no named study, or a study names a test the engine does not register."""


class MissingExtraError(RuntimeError):
    """An optional extra of the engine is not installed."""


class UndefinedRepetitions(RuntimeError):
    """A study's repetitions did not all produce a p-value."""


def derive_seed(case_seed: int, key: str) -> int:
    """A seed per simulation, a pure function of the case seed and the simulation's key."""
    return int(np.random.SeedSequence([case_seed, zlib.crc32(key.encode("utf-8"))]).generate_state(1)[0])


# ---------------------------------------------------------------------------------------------------------------------
# the engine side

def load_studies() -> dict[str, tuple[Any, ...]]:
    """The engine's named studies; their absence (an engine older than U16-E2) stops the bake."""
    try:
        return importlib.import_module("riskvalidation.generators.size_studies").STUDIES
    except ImportError as exc:
        raise StudyRegistryError(
            "riskvalidation.generators.size_studies is not installed: C22's other families need the engine with the named "
            f"size studies (U16-E2; riskvalidation 1.0.0): {exc}") from exc


def registered_other_tests() -> dict[str, str]:
    """Every registered p-value test outside the credit families, with its family."""
    import riskvalidation.validation  # noqa: F401  (registers every test)
    from riskvalidation.core.registry import catalogue

    return {s.test_id: s.family for s in catalogue() if s.decision == "p_value" and s.family not in CREDIT_FAMILIES}


def check_registry(studies: dict[str, tuple[Any, ...]] | None = None) -> None:
    """Every registered p-value test outside the credit families has a study, and every study names a registered test."""
    studies = load_studies() if studies is None else studies
    registered = set(registered_other_tests())
    missing = sorted(registered - set(studies))
    if missing:
        raise StudyRegistryError(f"no named study for the registered p-value test(s): {', '.join(missing)}")
    extra = sorted(set(studies) - registered)
    if extra:
        raise StudyRegistryError(f"a study names a test the engine does not register as a p-value test: {', '.join(extra)}")


def check_extras(import_module: Callable[[str], Any] = importlib.import_module) -> None:
    """The optional extras the engine's tests may read are installed, or the bake stops naming the first that is not."""
    for name in EXTRAS:
        try:
            import_module(name)
        except ImportError as exc:
            raise MissingExtraError(
                f"the optional extra {name!r} of riskvalidation is not installed ({exc}); install "
                "riskvalidation[market,ml,stress] before the C22 bake") from exc


# ---------------------------------------------------------------------------------------------------------------------
# jobs: one simulation each, run in worker processes

@dataclass(frozen=True)
class Job:
    variant: str
    key: str
    test_id: str
    index: int
    arm: str  # "null" or "alternative": which generator of the study
    n_rep: int
    seed: int


def study_key(test_id: str, index: int, suffix: str) -> str:
    """The key of a study's row: the test id (with ``#index`` from the second study of a test on) and the suffix."""
    return f"{test_id if index == 0 else f'{test_id}#{index}'}@{suffix}"


def jobs_for(case_seed: int, variants: tuple[str, ...]) -> list[Job]:
    """The simulations of the variants `null` (the null of every study, 4,000 repetitions) and `other-families` (two
    points per study, 2,000 repetitions each); any other variant has none."""
    studies = load_studies()
    jobs: list[Job] = []
    for variant in variants:
        if variant not in ("null", "other-families"):
            continue
        for tid, lst in studies.items():
            for i, _ in enumerate(lst):
                points = ((("null", "null", N_NULL),) if variant == "null"
                          else (("d0", "null", N_POWER), ("d1", "alternative", N_POWER)))
                for suffix, arm, n_rep in points:
                    key = study_key(tid, i, suffix)
                    jobs.append(Job(variant, key, tid, i, arm, n_rep, derive_seed(case_seed, f"{variant}:{key}")))
    return jobs


#: seconds per repetition, rounded up from a 20-repetition timing; only the order in which the pool starts jobs
_UNIT_COST = {"ml.shift_resilience": 2.2, "market.duration_test": 0.07, "market.dynamic_quantile_test": 0.013,
              "market.acerbi_szekely": 0.007, "ml.conformal_coverage": 0.004, "fair.fisher_exact": 0.003}


def run_job(job: Job):
    """One simulation in a worker: the engine's study, its arm, the repetitions and the seed of the job."""
    import riskvalidation.validation  # noqa: F401  (registers every test in the worker)
    from riskvalidation.generators.size_studies import simulate_study

    study = load_studies()[job.test_id][job.index]
    return simulate_study(study, job.arm, n_rep=job.n_rep, seed=job.seed)


def default_workers() -> int:
    env = os.environ.get("CONTRASTE_C22_WORKERS")
    return max(1, int(env)) if env else max(1, min(8, (os.cpu_count() or 2) // 2))


def run_jobs(jobs: list[Job], workers: int | None = None, log: Callable[[str], None] | None = None) -> dict[tuple[str, str], Any]:
    """Run the jobs, the longest first, and return ``{(variant, key): Simulation}`` in job order."""
    workers = default_workers() if workers is None else workers
    say = log or (lambda msg: print(msg, file=sys.stderr, flush=True))
    order = sorted(jobs, key=lambda j: -j.n_rep * _UNIT_COST.get(j.test_id, 0.001))
    results: dict[tuple[str, str], Any] = {}
    t0 = time.perf_counter()
    if workers <= 1 or len(order) == 1:
        for j in order:
            results[(j.variant, j.key)] = run_job(j)
            say(f"study {j.variant}:{j.key} {len(results)}/{len(order)} ({time.perf_counter() - t0:.0f} s)")
    else:
        with ProcessPoolExecutor(max_workers=min(workers, len(order))) as pool:
            futures = {pool.submit(run_job, j): j for j in order}
            for fut in as_completed(futures):
                j = futures[fut]
                results[(j.variant, j.key)] = fut.result()
                say(f"study {j.variant}:{j.key} {len(results)}/{len(order)} ({time.perf_counter() - t0:.0f} s)")
    return {(j.variant, j.key): results[(j.variant, j.key)] for j in jobs}


def rejection_label(study: Any) -> str:
    """The label of the rate of the study's own rule (the engine's)."""
    return importlib.import_module("riskvalidation.generators.size_studies").rejection_label(study)


def study_rates(sim: Any) -> dict[str, Any]:
    """The rates of a simulation at both levels, first, then the study's own rule when it is not p < alpha: a study
    whose rule is the red light, the Monte Carlo p <= 0.05 or the light that is not green also reports p < 0.05 and
    p < 0.01 from its p-values, so every test of the null variant carries the same fields."""
    from riskvalidation.harness import Rate

    if all(f"p<{a:g}" in sim.rates for a in LEVELS):
        return dict(sim.rates)
    p = np.asarray(sim.p_values, dtype=float)
    finite = np.isfinite(p)
    undefined = int(p.size - finite.sum())
    out = {f"p<{a:g}": Rate(int(np.sum(p[finite] < a)), int(sim.n_rep), undefined) for a in LEVELS}
    out.update(sim.rates)
    return out


def require_defined(key: str, sim: Any) -> None:
    """Every repetition of a study yields a p-value (the engine's own suites assert it): else the bake stops."""
    n = int(np.sum(~np.isfinite(np.asarray(sim.p_values, dtype=float))))
    if n:
        raise UndefinedRepetitions(f"{key}: {n} of {sim.n_rep} repetitions of {sim.test_id} have no p-value")


# ---------------------------------------------------------------------------------------------------------------------
# the documented excess of the engine (tests/size_kit.py DOCUMENTED_EXCESS, U16-E2)

DOCUMENTED_EXCESS: dict[str, dict[str, Any]] = {
    "portfolio.mc_convergence": {
        "page": "docs/portfolio/07_validation-tests.md", "level": 0.01,
        "engine": _t("The engine's page states the measured size, 1.55% at 1% against a bound of 1.49% (4,000 repetitions): "
                     "the z-test of the sample quantile estimates its standard error from the sample (Woodruff), which "
                     "oversizes it slightly at 1%; with the exact standard error its size is 1.20%, within both bounds.",
                     "La página del motor declara el tamaño medido, 1,55% al 1% contra una cota de 1,49% (4.000 repeticiones): "
                     "la prueba z del cuantil muestral estima su error estándar desde la muestra (Woodruff), lo que la "
                     "sobredimensiona levemente al 1%; con el error estándar exacto su tamaño es 1,20%, dentro de ambas cotas."),
    },
}


def excess_block(test_id: str, rates: dict[str, dict[str, Any]], n_rep: int) -> dict[str, Any] | None:
    """The documented excess of a test: its page, the measured size at the level, the bound and the excess; None for a
    test the engine does not document."""
    from riskvalidation.harness import size_bound

    doc = DOCUMENTED_EXCESS.get(test_id)
    if doc is None:
        return None
    level = doc["level"]
    measured = float(rates[f"p<{level:g}"]["rate"])
    bound = float(size_bound(level, n_rep))
    return {"page": doc["page"], "repository": ENGINE_REPOSITORY, "level": level, "measured": measured, "bound": bound,
            "excess": measured - bound, "exceeds": measured > bound, "engine": doc["engine"]}


# ---------------------------------------------------------------------------------------------------------------------
# the texts, panels and records: English from the engine's studies, Spanish here (the bake stops on a text it has not)

TEST_LABEL: dict[str, dict[str, str]] = {
    "ccr.pfe_exceedance_backtest": _t("PFE exceedance back-test", "Backtest de excedencias de PFE"),
    "ifrs9.stage_migration_backtest": _t("IFRS 9 stage migration back-test", "Backtest de migración de etapas NIIF 9"),
    "lgd_ead.lgd_calibration_by_segment": _t("LGD calibration by segment", "Calibración de LGD por segmento"),
    "lgd_ead.lgd_calibration_over_time": _t("LGD calibration over time", "Calibración de LGD en el tiempo"),
    "lgd_ead.downturn_coverage": _t("Downturn LGD coverage", "Cobertura de LGD de ciclo bajo"),
    "market.mcneil_frey_residual_test": _t("McNeil-Frey residual test", "Prueba de residuos de McNeil-Frey"),
    "portfolio.tail_backtest": _t("Tail back-test (LHP quantile)", "Backtest de cola (cuantil LHP)"),
    "portfolio.mc_convergence": _t("Monte Carlo quantile convergence", "Convergencia del cuantil Monte Carlo"),
    "portfolio.crp_recursion_vs_mc": _t("CreditRisk+ recursion against Monte Carlo", "Recursión de CreditRisk+ contra Monte Carlo"),
    "fair.two_proportion_z": _t("Two-proportion z-test (fairness)", "Prueba z de dos proporciones (equidad)"),
    "fair.fisher_exact": _t("Fisher exact test (fairness)", "Prueba exacta de Fisher (equidad)"),
    "market.kupiec_pof": _t("Kupiec proportion of failures", "Proporción de fallas de Kupiec"),
    "market.christoffersen_independence": _t("Christoffersen independence", "Independencia de Christoffersen"),
    "market.christoffersen_conditional_coverage": _t("Christoffersen conditional coverage", "Cobertura condicional de Christoffersen"),
    "market.duration_test": _t("Duration test", "Prueba de duración"),
    "market.acerbi_szekely": _t("Acerbi-Szekely ES test", "Prueba de ES de Acerbi-Szekely"),
    "market.du_escanciano_unconditional": _t("Du-Escanciano, unconditional", "Du-Escanciano, incondicional"),
    "market.du_escanciano_conditional": _t("Du-Escanciano, conditional", "Du-Escanciano, condicional"),
    "market.dynamic_quantile_test": _t("Dynamic quantile test", "Prueba de cuantil dinámico"),
    "ml.shift_resilience": _t("Shift resilience (ML)", "Resiliencia al desplazamiento (ML)"),
    "ml.conformal_coverage": _t("Conformal coverage (ML)", "Cobertura conforme (ML)"),
}

PANEL_OF: dict[str, str] = {
    "ccr.pfe_exceedance_backtest": "ccr", "ifrs9.stage_migration_backtest": "ifrs9",
    "lgd_ead.lgd_calibration_by_segment": "lgd-ead", "lgd_ead.lgd_calibration_over_time": "lgd-ead",
    "lgd_ead.downturn_coverage": "lgd-ead", "market.mcneil_frey_residual_test": "market-es",
    "portfolio.tail_backtest": "portfolio-credit", "portfolio.mc_convergence": "portfolio-credit",
    "portfolio.crp_recursion_vs_mc": "portfolio-credit", "fair.two_proportion_z": "fairness", "fair.fisher_exact": "fairness",
    "market.kupiec_pof": "market-var", "market.christoffersen_independence": "market-var",
    "market.christoffersen_conditional_coverage": "market-var", "market.duration_test": "market-var",
    "market.acerbi_szekely": "market-es", "market.du_escanciano_unconditional": "market-es",
    "market.du_escanciano_conditional": "market-es", "market.dynamic_quantile_test": "market-var",
    "ml.shift_resilience": "ml", "ml.conformal_coverage": "ml",
}

#: the order of the panels of the null and `other-families` variants (after the credit panels in the null variant)
OTHER_PANELS = ("ccr", "ifrs9", "lgd-ead", "market-var", "market-es", "portfolio-credit", "fairness", "ml")

PANEL_LABEL: dict[str, dict[str, str]] = {
    "ccr": _t("Counterparty credit risk", "Riesgo de crédito de contraparte"),
    "ifrs9": _t("IFRS 9 stages", "Etapas NIIF 9"),
    "lgd-ead": _t("LGD and EAD", "LGD y EAD"),
    "market-var": _t("Market: VaR back-tests", "Mercado: backtests de VaR"),
    "market-es": _t("Market: ES and distribution tests", "Mercado: pruebas de ES y de distribución"),
    "portfolio-credit": _t("Portfolio credit risk", "Riesgo de crédito de cartera"),
    "fairness": _t("Fairness", "Equidad"),
    "ml": _t("Machine learning", "Aprendizaje automático"),
}

# English text of the engine's studies (label, null text, alternative) -> Spanish. A text the engine adds in a later
# release has no entry: the bake stops naming it (the Spanish texts are written, never machine-made).
_ES: dict[str, str] = {
    "PFE at 95%, 1000 dates": "PFE al 95%, 1.000 fechas",
    "three stages, 4000, 1500 and 500 accounts": "tres etapas, 4.000, 1.500 y 500 cuentas",
    "one segment, 250 workouts": "un segmento, 250 recuperaciones",
    "five default years, 60 workouts each": "cinco años de incumplimiento, 60 recuperaciones cada uno",
    "150 downturn workouts, estimate 0.45": "150 recuperaciones de ciclo bajo, estimación 0,45",
    "2500 days at 5%, 125 exceedances expected": "2.500 días al 5%, 125 excedencias esperadas",
    "60 years at the 95% level": "60 años al nivel 95%",
    "250 years at the 99% level": "250 años al nivel 99%",
    "20000 scenarios, the 99% quantile of the LHP loss rate": "20.000 escenarios, el cuantil 99% de la tasa de pérdida LHP",
    "2000 scenarios, 400 obligors in five exposure bands": "2.000 escenarios, 400 deudores en cinco bandas de exposición",
    "2000 applicants, two groups": "2.000 postulantes, dos grupos",
    "1500 days at 5%": "1.500 días al 5%",
    "400 days at 5%": "400 días al 5%",
    "250 days at 2.5%": "250 días al 2,5%",
    "2000 days at 10%": "2.000 días al 10%",
    "250 days at 1%": "250 días al 1%",
    "750 days at 1%": "750 días al 1%",
    "2000 development rows, a quarter worst-subsample share": "2.000 filas de desarrollo, un cuarto en el peor subconjunto",
    "2000 test rows, 90% coverage": "2.000 filas de prueba, cobertura 90%",
    # the null texts
    "no threshold gap": "sin brecha de umbral",
    "independent hits at 5%": "excedencias independientes al 5%",
    "independent hits": "excedencias independientes",
    "normal losses with their true VaR and ES": "pérdidas normales con su VaR y ES verdaderos",
    "uniform PITs": "PIT uniformes",
    "shift 0": "desplazamiento 0",
    "drift 0": "deriva 0",
    # the stated alternatives
    "the PFE forecast is 90% of the true 95% quantile (exceedance frequency 6.94%, not 5%)":
        "el pronóstico de PFE es 90% del cuantil 95% verdadero (frecuencia de excedencia 6,94%, no 5%)",
    "the stage 1 to stage 2 migration is 9.5%, not the predicted 8% (stage 1 staying 88.5%)":
        "la migración de etapa 1 a etapa 2 es 9,5%, no el 8% predicho (la etapa 1 permanece 88,5%)",
    "the realised LGD is 5 points above the predicted one on average":
        "la LGD realizada es en promedio 5 puntos sobre la predicha",
    "in the last of five years the realised LGD is 10 points above the predicted one":
        "en el último de cinco años la LGD realizada es 10 puntos sobre la predicha",
    "the mean realised downturn LGD is 5 points above the 0.45 estimate":
        "la LGD de ciclo bajo realizada es en promedio 5 puntos sobre la estimación de 0,45",
    "the ES forecast is 95% of the true 5% expected shortfall of a normal loss (mean residual 0.103)":
        "el pronóstico de ES es 95% del expected shortfall verdadero al 5% de una pérdida normal (residuo medio 0,103)",
    "the true asset correlation is 0.30, the fit says 0.12 (the 95% quantile is exceeded 9.12% of the years, not 5%)":
        "la correlación de activos verdadera es 0,30, el ajuste dice 0,12 (el cuantil 95% se excede en 9,12% de los años, no 5%)",
    "the true asset correlation is 0.30, the fit says 0.12 (the 99% quantile is exceeded 4.29% of the years, not 1%)":
        "la correlación de activos verdadera es 0,30, el ajuste dice 0,12 (el cuantil 99% se excede en 4,29% de los años, no 1%)",
    "the run simulates correlation 0.13, the anchor is the closed form at 0.12 (quantile 0.0964 against 0.0917)":
        "la corrida simula correlación 0,13, el ancla es la forma cerrada con 0,12 (cuantil 0,0964 contra 0,0917)",
    "the sample has sector variance 0.6, the recursion's pmf 0.5 (loss variance 172 units against 150)":
        "la muestra tiene varianza sectorial 0,6, la pmf de la recursión 0,5 (varianza de pérdida 172 unidades contra 150)",
    "the protected group's decision threshold is lower by 0.3 in log-odds (a selection-rate gap above 8 points)":
        "el umbral de decisión del grupo protegido es 0,3 más bajo en log-odds (una brecha de tasa de selección sobre 8 puntos)",
    "the VaR is exceeded 1.3 times too often (a hit rate of 6.5%, not 5%)":
        "el VaR se excede 1,3 veces más de lo debido (una tasa de excedencia de 6,5%, no 5%)",
    "a hit is followed by a hit with probability 15%, not 5% (clustered exceedances at the same hit rate)":
        "tras una excedencia sigue otra con probabilidad 15%, no 5% (excedencias agrupadas con la misma tasa)",
    "a hit is followed by a hit with probability 40%, not 5% (clustered exceedances at the same hit rate)":
        "tras una excedencia sigue otra con probabilidad 40%, no 5% (excedencias agrupadas con la misma tasa)",
    "a hit is followed by a hit with probability 10%, not 1% (clustered exceedances at the same hit rate)":
        "tras una excedencia sigue otra con probabilidad 10%, no 1% (excedencias agrupadas con la misma tasa)",
    "a hit is followed by a hit with probability 15%, not 2.5% (clustered exceedances at the same hit rate)":
        "tras una excedencia sigue otra con probabilidad 15%, no 2,5% (excedencias agrupadas con la misma tasa)",
    "the realised losses are 1.25 times as dispersed as the VaR and ES forecasts say":
        "las pérdidas realizadas son 1,25 veces más dispersas de lo que dicen los pronósticos de VaR y ES",
    "the lower tail has too much mass (u = r^1.05: 11.2% of the PITs below 0.10, not 10%)":
        "la cola inferior tiene demasiada masa (u = r^1,05: 11,2% de los PIT bajo 0,10, no 10%)",
    "the tail PITs (below 0.10) cluster: one follows another with probability 20%, not 10%":
        "los PIT de cola (bajo 0,10) se agrupan: uno sigue a otro con probabilidad 20%, no 10%",
    "a quarter of the rows shifted 3 sd on feature 0": "un cuarto de las filas desplazado 3 desviaciones estándar en la variable 0",
    "log-odds drift 0.5 between calibration and test": "deriva de 0,5 en log-odds entre calibración y prueba",
}

_NULL_FALLBACK = _t("the test's null holds at its boundary", "la nula de la prueba se cumple en su frontera")


def _es(text: str) -> str:
    try:
        return _ES[text]
    except KeyError:
        raise StudyRegistryError(f"no Spanish text for the engine study text {text!r}: add it to c22_studies._ES") from None


def study_texts(study: Any, index: int) -> dict[str, dict[str, str]]:
    """The study's label, null text and alternative text, in both languages (English from the engine)."""
    null = _t(study.null_text, _es(study.null_text)) if study.null_text else _NULL_FALLBACK
    return {"label": _t(study.label, _es(study.label)), "null": null,
            "alternative": _t(study.alternative_text, _es(study.alternative_text))}


def row_label(test_id: str, study: Any, index: int, n_studies: int) -> dict[str, str]:
    """The row's label: the test's name, with the study's label when the test has several studies."""
    base = TEST_LABEL[test_id]
    if n_studies == 1:
        return base
    t = study_texts(study, index)["label"]
    return _t(f"{base['en']} ({t['en']})", f"{base['es']} ({t['es']})")


GENERATOR_TITLE: dict[str, dict[str, str]] = {
    "PfeSeries": _t("Exposure series with a PFE forecast (counterparty credit risk)", "Serie de exposiciones con un pronóstico de PFE (riesgo de contraparte)"),
    "StageTransitions": _t("Stage migrations of IFRS 9 accounts", "Migraciones de etapa de cuentas NIIF 9"),
    "LgdCalibration": _t("Realised and predicted LGD of workouts", "LGD realizada y predicha de recuperaciones"),
    "DownturnLgd": _t("Downturn workouts against a downturn estimate", "Recuperaciones de ciclo bajo contra una estimación de ciclo bajo"),
    "EsResiduals": _t("Expected shortfall residuals of exceedances", "Residuos de expected shortfall de las excedencias"),
    "LhpLossRates": _t("Yearly loss rates of a large homogeneous portfolio", "Tasas de pérdida anuales de una cartera homogénea grande"),
    "McQuantile": _t("A Monte Carlo quantile of the LHP loss rate", "Un cuantil Monte Carlo de la tasa de pérdida LHP"),
    "CreditRiskPlusSample": _t("A CreditRisk+ loss sample", "Una muestra de pérdidas de CreditRisk+"),
    "ThresholdBiasPlant": _t("Decisions with a planted threshold gap between two groups", "Decisiones con una brecha de umbral plantada entre dos grupos"),
    "VarHits": _t("VaR exceedances (hits), independent or clustered", "Excedencias de VaR, independientes o agrupadas"),
    "EsLosses": _t("Losses with VaR and ES forecasts", "Pérdidas con pronósticos de VaR y ES"),
    "PitSeries": _t("Probability integral transforms of a forecast distribution", "Transformadas integrales de probabilidad de una distribución pronosticada"),
    "CovariateShiftPlant": _t("A model with a planted covariate shift", "Un modelo con un desplazamiento de covariables plantado"),
    "ExchangeabilityBreakPlant": _t("A conformal model with a planted exchangeability break", "Un modelo conforme con una ruptura de intercambiabilidad plantada"),
}


def _kebab(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()


def generator_classes() -> list[dict[str, Any]]:
    """The generator classes of the named studies in order of first use, numbered after the credit families' G1 to G7."""
    seen: dict[str, dict[str, Any]] = {}
    for lst in load_studies().values():
        for st in lst:
            for g in (st.null, st.alternative):
                name = type(g).__name__
                if name not in seen:
                    if name not in GENERATOR_TITLE:
                        raise StudyRegistryError(f"no title for the engine generator class {name!r}: add it to c22_studies.GENERATOR_TITLE")
                    seen[name] = {"id": f"G{8 + len(seen)}-{_kebab(name)}", "class": name, "title": GENERATOR_TITLE[name],
                                  "module": type(g).__module__}
    return list(seen.values())


def model_studies() -> list[dict[str, Any]]:
    """The engine's named studies as the models artifact records them (their fixed arguments, repetitions and seeds)."""
    from riskvalidation.generators._base import jsonable

    out = []
    for tid, lst in load_studies().items():
        for i, st in enumerate(lst):
            out.append({
                "test_id": tid, "index": i, "label": study_texts(st, i)["label"], "rule": st.rule,
                "null_generator": type(st.null).__name__, "alternative_generator": type(st.alternative).__name__,
                "pipeline": None if st.null_runner is None else st.null_runner.__qualname__.split(".")[0],
                "test_kwargs": jsonable(st.test_kwargs), "engine_n_rep": int(st.n_rep),
                "engine_power_n_rep": None if st.power_n_rep is None else int(st.power_n_rep),
                "engine_seed": int(st.seed), "engine_power_seed": int(st.power_seed)})
    return out
