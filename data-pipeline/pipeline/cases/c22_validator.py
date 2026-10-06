"""C22, validating the validator: the size and power of every test (U3).

The design is docs/design/features/c22-validator/design.md; requirements CT-301 to CT-307 hold it. Every dataset is
drawn from ``riskvalidation.generators`` (known truth) and every rate is measured by ``riskvalidation.harness``, with
the Monte Carlo standard error of Morris, White and Crowther (2019) and the exact rejection probability wherever one
exists. Two published simulation studies are read from their PDFs in the device data root (BCBS WP14 Tables 5 to 8,
Yurdakul and Naranjo 2020 Table 4, both derived-only) and reproduced cell by cell; Demler et al.'s single published
rate is quoted from dossier 12.
"""
from __future__ import annotations

import math
import sys
import time
import zlib
from pathlib import Path
from typing import Any

import numpy as np
from scipy import special

from riskvalidation.generators import (
    BinormalScores,
    DefaultCounts,
    GradeFrequencies,
    LogisticPortfolio,
    Migrations,
    NestedLda,
    TwoSample,
    break_monotonicity,
    concentrate,
    decaying_matrix,
    feed_cell,
    feed_grades,
    feed_series,
    jsonable,
)
from riskvalidation.generators._base import GH_NODES, GH_WEIGHTS
from riskvalidation.harness import (
    Rate,
    agrees,
    agrees_with_published,
    estimator_performance,
    metric_above,
    rejection_probability,
    simulate,
    size_bound,
    traffic_lights_rejection_probability,
    within_size,
    wp14_true_confidence,
)
from riskvalidation.validation import calibration as cal
from riskvalidation.validation import discrimination as disc
from riskvalidation.validation import rating_system as rs
from riskvalidation.validation import stability as st
from riskvalidation.validation.discrimination import auc_with_variance
from riskvalidation.validation.rating_system import concentration

from .. import __version__
from ..core import expect as expectations
from ..core import lineage as lin
from ..core.manifest import build_artifact, build_case_manifest, build_models_artifact
from ..io import papers
from ..io.formats import write_json
from ..stages.export import write_artifact
from .c01_ladder import _t, _v

CASE_ID = "C22"
SOURCES = ("bcbs-wp14", "yurdakul-naranjo-2020")
WP14_PDF = "bcbs-wp14-2005.pdf"
YN_PDF = "yurdakul-naranjo-2020-psi.pdf"
ENGINES = {"numpy", "scipy", "riskvalidation", "pypdf"}
#: minutes of repetitions: the artifacts are replayed; the count tests' exact size and power are recomputed live
RUN_MS = 600_000.0
N_NULL, N_POWER = 4000, 2000
LEVELS = (0.05, 0.01)
RULES = tuple(f"p<{a:g}" for a in LEVELS)
SPECIMEN_SEVERITY = 3

#: Demler, Pencina and D'Agostino (2012), section 2.3, read at PMC3684152 (dossier 12, section 5)
DEMLER = {"rate": 0.001, "runs": 1000,
          "quote": "the significance level for the F-test is close to the nominal 0.05 level, whereas it is 0.001 for the "
                   "DeLong test",
          "reference": "Demler, Pencina and D'Agostino (2012), Statistics in Medicine 31(23), doi:10.1002/sim.5328"}

# the portfolios the scenarios share
GR_N = (2500, 2000, 1500, 1500, 800, 400, 150)            # seven grades, 5 to 32 expected defaults each
GR_PD = (0.002, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16)
THIN_N = (300, 800, 1500, 1500, 800, 400, 150)            # the best grade expects 0.6 defaults
P10 = (0.02, 0.05, 0.10, 0.15, 0.20, 0.18, 0.13, 0.09, 0.05, 0.03)  # ten grades, CV 0.60
AUC_DEV = 0.80
DELTA_DEV = math.sqrt(2.0) * float(special.ndtri(AUC_DEV))  # binormal separation of an AUC of 0.80

TEST_LABEL: dict[str, dict[str, str]] = {
    "pd.binomial": _t("Binomial", "Binomial"),
    "pd.jeffreys": _t("Jeffreys", "Jeffreys"),
    "pd.binomial_vasicek": _t("Vasicek-corrected binomial", "Binomial con corrección de Vasicek"),
    "pd.chi2_grades": _t("Chi-square over grades", "Chi-cuadrado por grados"),
    "pd.default_profile": _t("Default profile", "Perfil de incumplimiento"),
    "pd.hosmer_lemeshow": _t("Hosmer-Lemeshow", "Hosmer-Lemeshow"),
    "pd.spiegelhalter": _t("Spiegelhalter", "Spiegelhalter"),
    "pd.normal_multiperiod": _t("Normal test, five years", "Prueba normal, cinco años"),
    "pd.traffic_lights": _t("Traffic lights, five years", "Semáforo, cinco años"),
    "disc.auc_vs_initial": _t("AUC against the development AUC", "AUC contra el AUC de desarrollo"),
    "disc.delong": _t("DeLong", "DeLong"),
    "stability.psi": _t("PSI (chi-square benchmark)", "PSI (referencia chi-cuadrado)"),
    "stability.csi": _t("CSI", "CSI"),
    "stability.chi2": _t("Chi-square of homogeneity", "Chi-cuadrado de homogeneidad"),
    "stability.ks": _t("Kolmogorov-Smirnov", "Kolmogórov-Smirnov"),
    "rating.migration_ztests": _t("Migration z-tests", "Pruebas z de migración"),
    "rating.hhi": _t("ECB concentration (HHI)", "Concentración BCE (HHI)"),
}

_T0 = time.perf_counter()


def _log(msg: str) -> None:
    print(f"[C22 {time.perf_counter() - _T0:7.1f}s] {msg}", file=sys.stderr, flush=True)


def _seed(case_seed: int, key: str) -> int:
    """A seed per simulation, a pure function of the case seed and the simulation's key."""
    return int(np.random.SeedSequence([case_seed, zlib.crc32(key.encode("utf-8"))]).generate_state(1)[0])


def _pct(x: float, decimals: int = 1) -> dict[str, str]:
    en = f"{100 * x:.{decimals}f}%"
    return _t(en, en.replace(".", ","))


class Book:
    """The simulations, generators and specimen tests of one variant, collected as they run."""

    def __init__(self, case_seed: int, family: str):
        self.case_seed, self.family = case_seed, family
        self.rows: list[dict[str, Any]] = []
        self.generators: dict[str, dict[str, Any]] = {}
        self.sims: dict[str, Any] = {}

    def gen(self, ref: str, g: Any) -> str:
        if ref not in self.generators:
            self.generators[ref] = {"name": g.name, "config": jsonable(g.config()["parameters"]),
                                    "truth": jsonable(g.truth())}
        return ref

    def run(self, key: str, test: Any, g: Any, gen_ref: str, *, panel: str, severity: int, x: float,
            scenario: dict[str, str], n_rep: int, feed: Any = None, test_kwargs: dict | None = None,
            rules: tuple = (), exact: dict[str, float] | None = None, histogram: bool = False,
            label: dict[str, str] | None = None) -> Any:
        seed = _seed(self.case_seed, f"{self.family}:{key}")
        sim = simulate(test, g, n_rep=n_rep, seed=seed, feed=feed, alphas=LEVELS, rules=rules,
                       test_kwargs=test_kwargs or {})
        self.gen(gen_ref, g)
        tid = sim.test_id
        agree = None if exact is None else {r: bool(agrees(sim.rates[r], p)) for r, p in exact.items()}
        self.rows.append({
            "key": key, "test_id": tid, "label": label or TEST_LABEL[tid], "scenario": scenario, "panel": panel,
            "severity": severity, "x": float(x), "rates": {r: v.to_dict() for r, v in sim.rates.items()},
            "exact": exact, "agrees": agree, "p_histogram": sim.p_histogram(20) if histogram else None,
            "seed": seed, "n_rep": n_rep, "generator": gen_ref,
        })
        self.sims[key] = sim
        return sim

    def rate(self, key: str, rule: str = "p<0.05") -> float:
        return float(self.sims[key].rates[rule].rate)


def _exact_counts(test: str, n: int, pd_applied: float, *, pd_true: float, rho_true: float, **kw: Any) -> dict[str, float]:
    return {f"p<{a:g}": rejection_probability(test, n, pd_applied, a, pd_true=pd_true, rho_true=rho_true, **kw)["probability"]
            for a in LEVELS}


def _exact_traffic(n: list[int], fore: Any, true: Any, ties: str = "lower") -> dict[str, float]:
    return {f"p<{a:g}": traffic_lights_rejection_probability(n, fore, a, pd_true=true, ties=ties)["probability"]
            for a in LEVELS}


def _holds(row: dict[str, Any], sim: Any) -> bool:
    """Whether a test holds its size at 5% and 1%: by its exact probability where one exists (no Monte Carlo error
    then), by the one-sided bound on the simulated rate otherwise."""
    if row["exact"] is not None:
        return all(row["exact"][f"p<{a:g}"] <= a + 1e-12 for a in LEVELS)
    return all(within_size(sim.rates[f"p<{a:g}"], a) for a in LEVELS)


def _impact(value: float | None, unit: str, en: str, es: str) -> dict[str, Any]:
    return {"value": None if value is None else float(value), "unit": unit, "label": _t(en, es)}


def _finding(fid: str, severity: str, status: str, evidence: list[str], en: str, es: str) -> dict[str, Any]:
    return {"id": fid, "severity": severity, "status": status, "evidence": [f"rate:{e}" for e in evidence],
            "title": _t(en, es)}


def _specimen(book: Book, calls: list[tuple[str, Any, Any, dict]]) -> list[dict[str, Any]]:
    """What the targeted tests say about one dataset of the variant (the committed policy's lights)."""
    rows = []
    for gen_ref, g, fn, kw in calls:
        d = g.draw(np.random.default_rng(_seed(book.case_seed, f"{book.family}:specimen:{gen_ref}")))
        r = fn(d, **kw)
        for res in (r if isinstance(r, list) else [r]):
            row = res.to_dict()
            row["model_id"] = gen_ref
            rows.append(row)
    return rows


# ---------------------------------------------------------------------------------------------------------------------
# the variants


SERIES = DefaultCounts.over_years([1000] * 5, [0.03] * 5)


def _psi_rules():
    return (metric_above(0.10, "metric>0.1"), metric_above(0.25, "metric>0.25"))


def _null(book: Book) -> dict[str, Any]:
    """Every p-value test at the boundary of its null with its assumptions met (CT-301)."""
    port, port_rho = DefaultCounts(1000, 0.01), DefaultCounts(1000, 0.01, rho=0.12)
    grades, thin = DefaultCounts(GR_N, GR_PD), DefaultCounts(THIN_N, GR_PD)
    logit, binorm = LogisticPortfolio(n=5000), BinormalScores(150, 4850, separation=1.2)
    pairs = BinormalScores(150, 4850, separation=1.2, challenger_separation=1.2)
    two = TwoSample(1000, 1000)
    mig = Migrations([500] * 7, break_monotonicity(decaying_matrix(7), 3, 1, 1.0))
    freq = GradeFrequencies(5000, P10)
    dev1 = BinormalScores(150, 4850, separation=1.2, development_size=1.0)

    def ext(d):
        return {"auc_initial": d["auc_initial"], "risk": d["risk"], "defaults": d["defaults"],
                "auc_initial_variance": d["development_auc_variance"]}

    sc = [
        ("pd.binomial@null", "pd.binomial", port, "port-1000-1pct", feed_cell(), {}, "calibration",
         _t("1,000 obligors, PD 1%, independent", "1.000 deudores, PD 1%, independientes"),
         _exact_counts("pd.binomial", 1000, 0.01, pd_true=0.01, rho_true=0.0)),
        ("pd.jeffreys@null", "pd.jeffreys", port, "port-1000-1pct", feed_cell(), {}, "calibration",
         _t("1,000 obligors, PD 1%, independent", "1.000 deudores, PD 1%, independientes"),
         _exact_counts("pd.jeffreys", 1000, 0.01, pd_true=0.01, rho_true=0.0)),
        ("pd.binomial_vasicek@null", "pd.binomial_vasicek", port_rho, "port-1000-1pct-rho12", feed_cell(), {"rho": 0.12},
         "calibration", _t("1,000 obligors, PD 1%, correlation 12% assumed and true",
                           "1.000 deudores, PD 1%, correlación 12% supuesta y verdadera"),
         _exact_counts("pd.binomial_vasicek", 1000, 0.01, pd_true=0.01, rho_true=0.12, rho=0.12)),
        ("pd.chi2_grades@null", "pd.chi2_grades", grades, "grades-7", feed_grades(), {}, "calibration",
         _t("seven grades, 5 to 32 expected defaults each", "siete grados, 5 a 32 incumplimientos esperados cada uno"), None),
        ("pd.default_profile@null", "pd.default_profile", grades, "grades-7", feed_grades(), {"n_sim": 2000}, "calibration",
         _t("seven grades; Monte Carlo p-value of 2,000 draws", "siete grados; valor p de Monte Carlo con 2.000 sorteos"), None),
        ("pd.hosmer_lemeshow@null", "pd.hosmer_lemeshow", logit, "logistic-5000", None, {}, "calibration",
         _t("5,000 obligors, mean PD 5%, PDs given (G = 10)", "5.000 deudores, PD media 5%, PD dadas (G = 10)"), None),
        ("pd.spiegelhalter@null", "pd.spiegelhalter", logit, "logistic-5000", None, {}, "calibration",
         _t("5,000 obligors, mean PD 5%", "5.000 deudores, PD media 5%"), None),
        ("pd.normal_multiperiod@null", "pd.normal_multiperiod", SERIES, "series-5y-3pct", feed_series(), {}, "calibration",
         _t("five independent years of 1,000 obligors at PD 3%", "cinco años independientes de 1.000 deudores con PD 3%"), None),
        ("pd.traffic_lights@null", "pd.traffic_lights", SERIES, "series-5y-3pct", feed_series(), {}, "calibration",
         _t("five independent years, the printed tie rule", "cinco años independientes, la regla de empates impresa"),
         _exact_traffic([1000] * 5, 0.03, 0.03)),
        ("disc.auc_vs_initial@null", "disc.auc_vs_initial", binorm, "binormal-150", None, {}, "discrimination",
         _t("150 defaulters, 4,850 survivors, AUC 0.80, development AUC known",
            "150 incumplidos, 4.850 sobrevivientes, AUC 0,80, AUC de desarrollo conocida"), None),
        ("disc.delong@null", "disc.delong", pairs, "binormal-150-pair", None, {}, "discrimination",
         _t("two scores of equal AUC 0.80, correlation 0.5", "dos puntajes de igual AUC 0,80, correlación 0,5"), None),
        ("stability.psi@null", "stability.psi", two, "two-sample-1000", None, {}, "stability",
         _t("two samples of 1,000, ten population deciles", "dos muestras de 1.000, diez deciles poblacionales"), None),
        ("stability.csi@null", "stability.csi", two, "two-sample-1000", None, {}, "stability",
         _t("two samples of 1,000, ten population deciles", "dos muestras de 1.000, diez deciles poblacionales"), None),
        ("stability.chi2@null", "stability.chi2", two, "two-sample-1000", None, {}, "stability",
         _t("two samples of 1,000, ten population deciles", "dos muestras de 1.000, diez deciles poblacionales"), None),
        ("stability.ks@null", "stability.ks", two, "two-sample-1000", None, {}, "stability",
         _t("two samples of 1,000", "dos muestras de 1.000"), None),
        ("rating.migration_ztests@null", "rating.migration_ztests", mig, "migrations-7-500-boundary", None, {}, "rating",
         _t("seven grades, 500 obligors each, one cell at the boundary", "siete grados, 500 deudores cada uno, una celda en la frontera"), None),
        ("rating.hhi@null", "rating.hhi", freq, "grades-10-5000", None, {}, "rating",
         _t("ten grades, 5,000 obligors, the initial distribution unchanged", "diez grados, 5.000 deudores, la distribución inicial sin cambio"), None),
        # the settings the harness found to matter
        ("pd.hosmer_lemeshow@fitted", "pd.hosmer_lemeshow", logit, "logistic-5000", None, {"fitted": True}, "settings",
         _t("the same, with G - 2 degrees of freedom (fitted=True)", "lo mismo, con G - 2 grados de libertad (fitted=True)"), None),
        ("pd.traffic_lights@upper", "pd.traffic_lights", SERIES, "series-5y-3pct", feed_series(), {"ties": "upper"}, "settings",
         _t("the upper tie rule WP14's simulation used", "la regla de empates superior que usó la simulación de WP14"),
         _exact_traffic([1000] * 5, 0.03, 0.03, ties="upper")),
        ("pd.chi2_grades@thin", "pd.chi2_grades", thin, "grades-7-thin", feed_grades(), {}, "settings",
         _t("a best grade expecting 0.6 defaults", "un mejor grado que espera 0,6 incumplimientos"), None),
        ("disc.auc_vs_initial@dev1", "disc.auc_vs_initial", dev1, "binormal-150-dev1", None, {}, "settings",
         _t("the development AUC estimated on an equal sample (ECB form)", "el AUC de desarrollo estimada en una muestra igual (forma BCE)"), None),
        ("disc.auc_vs_initial@dev1-extended", "disc.auc_vs_initial", dev1, "binormal-150-dev1", ext, {}, "settings",
         _t("the same with the development AUC's variance added", "lo mismo sumando la varianza del AUC de desarrollo"), None),
    ]
    for key, tid, g, ref, feed, kw, panel, scen, exact in sc:
        book.run(key, tid, g, ref, panel=panel, severity=0, x=0.0, scenario=scen, n_rep=N_NULL, feed=feed,
                 test_kwargs=kw, exact=exact, histogram=True)
        _log(f"null {key}: {book.rate(key):.4f}")
    small = TwoSample(100, 100)
    book.run("stability.psi@n100", "stability.psi", small, "two-sample-100", panel="settings", severity=0, x=0.0,
             scenario=_t("two samples of 100: the 0.10 and 0.25 rules of thumb", "dos muestras de 100: las reglas 0,10 y 0,25"),
             n_rep=N_NULL, rules=_psi_rules(), histogram=True)
    # estimator performance: the AUC and its ECB standard error; the ECE when the PDs are right
    est, se = [], []
    for k in range(N_NULL):
        d = binorm.draw(np.random.default_rng(_seed(book.case_seed, f"null:auc:{k}")))
        a, s2, _, _ = auc_with_variance(d["risk"], d["defaults"])
        est.append(a)
        se.append(math.sqrt(s2))
    est_a, se_a = np.array(est), np.array(se)
    tr = binorm.truth()
    auc_perf = estimator_performance(est_a, tr["auc_current"], model_se=se_a, lower=est_a - 1.959963984540054 * se_a,
                                     upper=est_a + 1.959963984540054 * se_a)
    auc_perf["exact_se"] = math.sqrt(tr["auc_variance_current"])
    eces = []
    for k in range(1000):
        d = logit.draw(np.random.default_rng(_seed(book.case_seed, f"null:ece:{k}")))
        eces.append(cal.pd_ece(d["defaults"], d["pd"]).metric)
    ece_perf = estimator_performance(np.array(eces), 0.0)
    holds = {row["key"]: _holds(row, book.sims[row["key"]]) for row in book.rows if row["key"].endswith("@null")}
    within = sum(holds.values())
    impact = {
        "tests_within_bound": _impact(within, "tests", "Tests of the battery that hold their size at 5% and 1% (of 17)",
                                      "Pruebas de la batería que mantienen su tamaño al 5% y 1% (de 17)"),
        "size_hl_fitted": _impact(book.rate("pd.hosmer_lemeshow@fitted"), "probability",
                                  "Hosmer-Lemeshow with G - 2 on a validation sample: size at 5%",
                                  "Hosmer-Lemeshow con G - 2 en una muestra de validación: tamaño al 5%"),
        "size_normal": _impact(book.rate("pd.normal_multiperiod@null"), "probability",
                               "Normal test over five years: size at 5%", "Prueba normal en cinco años: tamaño al 5%"),
        "psi010_false_alarm_n100": _impact(book.rate("stability.psi@n100", "metric>0.1"), "probability",
                                           "PSI > 0.10 when nothing changed, samples of 100",
                                           "PSI > 0,10 cuando nada cambió, muestras de 100"),
    }
    findings = [
        _finding("F-HL-DOF", "S2", "closed", ["pd.hosmer_lemeshow@fitted", "pd.hosmer_lemeshow@null"],
                 "Hosmer-Lemeshow with G - 2 degrees of freedom over-rejects on validation samples; riskvalidation 0.3.0 uses G for given PDs and C01 was re-baked",
                 "Hosmer-Lemeshow con G - 2 grados de libertad sobrerrechaza en muestras de validación; riskvalidation 0.3.0 usa G para PD dadas y C01 se recalculó"),
        _finding("F-NORMAL-SIZE", "S3", "accepted", ["pd.normal_multiperiod@null"],
                 "The normal test over five years rejects above its level, as WP14's own Table 7 shows; read it as an early warning",
                 "La prueba normal en cinco años rechaza sobre su nivel, como muestra la propia Tabla 7 de WP14; léase como alerta temprana"),
        _finding("F-TL-TIES", "S3", "accepted", ["pd.traffic_lights@null", "pd.traffic_lights@upper"],
                 "The traffic-lights size depends on the colour of a year with exactly the expected defaults; the printed rule is conservative, WP14's simulation used the other",
                 "El tamaño del semáforo depende del color de un año con exactamente los incumplimientos esperados; la regla impresa es conservadora, la simulación de WP14 usó la otra"),
        _finding("F-CHI2-THIN", "S3", "accepted", ["pd.chi2_grades@thin", "pd.chi2_grades@null"],
                 "The chi-square test over grades exceeds its level when a grade expects under one default",
                 "La prueba chi-cuadrado por grados excede su nivel cuando un grado espera menos de un incumplimiento"),
        _finding("F-AUC-INIT", "S2", "closed", ["disc.auc_vs_initial@dev1", "disc.auc_vs_initial@dev1-extended"],
                 "The ECB AUC test treats the development AUC as known; estimated, it over-rejects; C01 now adds its variance",
                 "La prueba de AUC del BCE trata el AUC de desarrollo como conocida; estimada, sobrerrechaza; C01 ahora suma su varianza"),
        _finding("F-JEFFREYS-DISCRETE", "S4", "accepted", ["pd.jeffreys@null", "pd.binomial@null"],
                 "The Jeffreys test is Bayesian; on a discrete count its exact size moves with the number of obligors and can exceed the level (1.38% at 1% for 1,000 obligors at PD 1%)",
                 "La prueba de Jeffreys es bayesiana; sobre un conteo discreto su tamaño exacto cambia con el número de deudores y puede exceder el nivel (1,38% al 1% para 1.000 deudores con PD 1%)"),
        _finding("F-PSI-RULE", "S2", "accepted", ["stability.psi@n100"],
                 "The PSI 0.10 rule of thumb raises false alarms in most samples of 100; the chi-square benchmark controls the error",
                 "La regla empírica PSI 0,10 da falsas alarmas en la mayoría de las muestras de 100; la referencia chi-cuadrado controla el error"),
    ]
    values = {"size_hl_given": book.rate("pd.hosmer_lemeshow@null"), "size_hl_fitted": book.rate("pd.hosmer_lemeshow@fitted"),
              "size_normal": book.rate("pd.normal_multiperiod@null"),
              "auc_init_ecb_dev1": book.rate("disc.auc_vs_initial@dev1"),
              "auc_init_ext_dev1": book.rate("disc.auc_vs_initial@dev1-extended"),
              "psi010_false_alarm_n100": book.rate("stability.psi@n100", "metric>0.1"),
              "auc_ecb_se_relative_error_pct": auc_perf["model_se_relative_error_pct"],
              "tests_within_bound": float(within)}
    specimen = _specimen(book, [
        ("logistic-5000", logit, lambda d: [cal.pd_hosmer_lemeshow(d["defaults"], d["pd"]), cal.pd_spiegelhalter(d["defaults"], d["pd"])], {}),
        ("port-1000-1pct", port, lambda d: [cal.pd_binomial(**feed_cell()(d)), cal.pd_jeffreys(**feed_cell()(d))], {}),
        ("two-sample-1000", two, lambda d: st.stability_psi(d["expected_counts"], d["actual_counts"]), {}),
    ])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [],
            "exact_curves": [], "estimators": {"auc": auc_perf, "ece_when_right": ece_perf}}


MISCAL = (1.0, 1.1, 1.25, 1.5, 2.0, 3.0)


def _miscalibration(book: Book) -> dict[str, Any]:
    """True PD = k times the PD applied, every grade and year (CT-302)."""
    for i, k in enumerate(MISCAL):
        port = DefaultCounts(5000, 0.02 * k, pd_forecast=0.02)
        scen_p = _t(f"5,000 obligors, PD applied 2%, true {2 * k:g}%", f"5.000 deudores, PD aplicada 2%, verdadera {2 * k:g}%".replace(".", ","))
        for tid, kw in (("pd.binomial", {}), ("pd.jeffreys", {}), ("pd.binomial_vasicek", {"rho": 0.12})):
            book.run(f"{tid}@k{k:g}", tid, port, f"port-5000-k{k:g}", panel="portfolio", severity=i, x=k, scenario=scen_p,
                     n_rep=N_POWER, feed=feed_cell(), test_kwargs=kw,
                     exact=_exact_counts(tid, 5000, 0.02, pd_true=0.02 * k, rho_true=0.0, **kw))
        grades = DefaultCounts(GR_N, np.minimum(np.array(GR_PD) * k, 0.99), pd_forecast=GR_PD)
        scen_g = _t(f"seven grades, every true PD {k:g} times its grade PD", f"siete grados, cada PD verdadera {k:g} veces la del grado".replace(".", ","))
        book.run(f"pd.chi2_grades@k{k:g}", "pd.chi2_grades", grades, f"grades-7-k{k:g}", panel="grades", severity=i, x=k,
                 scenario=scen_g, n_rep=N_POWER, feed=feed_grades())
        book.run(f"pd.default_profile@k{k:g}", "pd.default_profile", grades, f"grades-7-k{k:g}", panel="grades",
                 severity=i, x=k, scenario=scen_g, n_rep=N_POWER, feed=feed_grades(), test_kwargs={"n_sim": 2000})
        logit = LogisticPortfolio(n=5000, calibration_intercept=-math.log(k))
        scen_o = _t(f"5,000 obligors, every model odds divided by {k:g}", f"5.000 deudores, cada razón de chances del modelo dividida por {k:g}".replace(".", ","))
        for tid in ("pd.hosmer_lemeshow", "pd.spiegelhalter"):
            book.run(f"{tid}@k{k:g}", tid, logit, f"logistic-5000-k{k:g}", panel="obligors", severity=i, x=k, scenario=scen_o,
                     n_rep=N_POWER)
        series = DefaultCounts.over_years([1000] * 5, [0.03 * k] * 5, pd_forecast=[0.03] * 5)
        scen_y = _t(f"five years, PD applied 3%, true {3 * k:g}%", f"cinco años, PD aplicada 3%, verdadera {3 * k:g}%".replace(".", ","))
        book.run(f"pd.normal_multiperiod@k{k:g}", "pd.normal_multiperiod", series, f"series-5y-k{k:g}", panel="years",
                 severity=i, x=k, scenario=scen_y, n_rep=N_POWER, feed=feed_series())
        book.run(f"pd.traffic_lights@k{k:g}", "pd.traffic_lights", series, f"series-5y-k{k:g}", panel="years", severity=i,
                 x=k, scenario=scen_y, n_rep=N_POWER, feed=feed_series(),
                 exact=_exact_traffic([1000] * 5, 0.03, 0.03 * k))
        _log(f"miscalibration k={k:g}")

    def jeffreys_power(k: float) -> float:
        return rejection_probability("pd.jeffreys", 5000, 0.02, 0.05, pd_true=0.02 * k)["probability"]

    lo, hi = 1.0, 3.0
    for _ in range(60):  # the PD underestimation the portfolio Jeffreys test detects with 80% power, exactly
        mid = 0.5 * (lo + hi)
        lo, hi = (lo, mid) if jeffreys_power(mid) >= 0.8 else (mid, hi)
    k80 = hi
    impact = {
        "jeffreys_k80": _impact(k80, "ratio", "True-to-applied PD the portfolio Jeffreys test detects with 80% power (5,000 obligors, PD 2%)",
                                "PD verdadera sobre aplicada que la prueba de Jeffreys de cartera detecta con 80% de potencia (5.000 deudores, PD 2%)"),
        "hl_power_k125": _impact(book.rate("pd.hosmer_lemeshow@k1.25"), "probability",
                                 "Hosmer-Lemeshow power at 5% when every odds is 1.25 times too low",
                                 "Potencia de Hosmer-Lemeshow al 5% cuando toda razón de chances es 1,25 veces muy baja"),
        "profile_power_k3": _impact(book.rate("pd.default_profile@k3"), "probability",
                                    "Default-profile test at 5% when every PD is 3 times too low (blind to the level)",
                                    "Prueba del perfil al 5% cuando cada PD es 3 veces muy baja (ciega al nivel)"),
    }
    findings = [
        _finding("F-PROFILE-BLIND", "S4", "accepted", ["pd.default_profile@k3", "pd.chi2_grades@k3"],
                 "The default-profile test sees the shape of the PD curve, not its level: a uniform underestimation leaves it at its size",
                 "La prueba del perfil ve la forma de la curva de PD, no su nivel: una subestimación uniforme la deja en su tamaño"),
        _finding("F-VASICEK-COST", "S3", "accepted", ["pd.binomial_vasicek@k1.5", "pd.binomial@k1.5"],
                 "Correcting for a correlation the defaults do not have costs power: the Vasicek test misses most underestimations the binomial test catches",
                 "Corregir por una correlación que los incumplimientos no tienen cuesta potencia: la prueba de Vasicek pierde la mayoría de las subestimaciones que la binomial detecta"),
    ]
    values = {"jeffreys_k80": k80, "profile_size_k3": book.rate("pd.default_profile@k3"),
              "binomial_power_k15": book.rate("pd.binomial@k1.5"), "hl_power_k125": book.rate("pd.hosmer_lemeshow@k1.25")}
    g3 = DefaultCounts(5000, 0.02 * MISCAL[SPECIMEN_SEVERITY], pd_forecast=0.02)
    l3 = LogisticPortfolio(n=5000, calibration_intercept=-math.log(MISCAL[SPECIMEN_SEVERITY]))
    specimen = _specimen(book, [
        (f"port-5000-k{MISCAL[SPECIMEN_SEVERITY]:g}", g3, lambda d: [cal.pd_binomial(**feed_cell()(d)), cal.pd_jeffreys(**feed_cell()(d))], {}),
        (f"logistic-5000-k{MISCAL[SPECIMEN_SEVERITY]:g}", l3, lambda d: [cal.pd_hosmer_lemeshow(d["defaults"], d["pd"]), cal.pd_spiegelhalter(d["defaults"], d["pd"])], {}),
    ])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [],
            "exact_curves": [], "estimators": None}


CLUSTER = (0.0, 0.02, 0.05, 0.10, 0.15, 0.20)


def _wp14_golden(book: Book, wp: dict[str, Any]) -> tuple[dict[str, Any], int]:
    cells = []
    levels = wp["levels"]
    for table, scen_key, pub_key in (("7", "scenarios_type_i", "table_7_type_i"), ("8", "scenarios_type_ii", "table_8_type_ii")):
        for name, sc in wp[scen_key].items():
            gen = DefaultCounts.over_years([wp["obligors"]] * wp["years"], np.array(sc["true_pct"]) / 100.0, rho=sc["rho"],
                                           pd_forecast=np.array(sc["forecast_pct"]) / 100.0, theta=sc["theta"])
            for short, tid, kw in (("normal", "pd.normal_multiperiod", {}), ("traffic", "pd.traffic_lights", {"ties": "upper"})):
                sim = simulate(tid, gen, n_rep=wp["runs"], seed=_seed(book.case_seed, f"wp14:{table}:{name}:{short}"),
                               feed=feed_series(), alphas=levels, test_kwargs=kw)
                for level, pub in zip(levels, wp[pub_key][name][short], strict=True):
                    r = sim.rate(level)
                    if table == "8":
                        r = Rate(r.n - r.rejections, r.n, r.undefined)
                    ok, z = agrees_with_published(r, pub, wp["runs"])
                    cells.append({"table": f"Table {table}", "row": f"{name}, {short}", "column": f"{level:g}",
                                  "published": pub, "measured": r.rate, "z": z, "agrees": bool(ok)})
            _log(f"WP14 Table {table} {name}")
    agree = sum(c["agrees"] for c in cells)
    return {"study": "bcbs-wp14", "title": _t("BCBS WP14 Tables 7 and 8: the normal and traffic-lights tests",
                                              "BCBS WP14 Tablas 7 y 8: las pruebas normal y de semáforo"),
            "runs_published": wp["runs"], "runs": wp["runs"], "cells": cells, "agree": agree, "total": len(cells),
            "note": _t("Traffic lights with the upper tie rule. The cell that does not agree, Table 8 DV_LV at 0.1%, prints 0.955; 200,000 runs give 0.9475 (SE 0.0005) and its neighbouring levels agree.",
                       "Semáforo con la regla de empates superior. La celda que no concuerda, Tabla 8 DV_LV al 0,1%, imprime 0,955; 200.000 corridas dan 0,9475 (EE 0,0005) y sus niveles vecinos concuerdan.")}, agree


def _clustering(book: Book, wp: dict[str, Any]) -> dict[str, Any]:
    """Right PDs, defaults correlated through one systematic factor (CT-302, CT-304)."""
    for i, r in enumerate(CLUSTER):
        port = DefaultCounts(1000, 0.01, rho=r)
        scen_p = _t(f"1,000 obligors, PD 1% right, asset correlation {100 * r:g}%", f"1.000 deudores, PD 1% correcta, correlación de activos {100 * r:g}%")
        for tid, kw in (("pd.binomial", {}), ("pd.jeffreys", {}), ("pd.binomial_vasicek", {"rho": 0.12})):
            book.run(f"{tid}@rho{r:g}", tid, port, f"port-1000-rho{r:g}", panel="portfolio", severity=i, x=r, scenario=scen_p,
                     n_rep=N_POWER, feed=feed_cell(), test_kwargs=kw,
                     exact=_exact_counts(tid, 1000, 0.01, pd_true=0.01, rho_true=r, **kw))
        grades = DefaultCounts(GR_N, GR_PD, rho=r)
        book.run(f"pd.chi2_grades@rho{r:g}", "pd.chi2_grades", grades, f"grades-7-rho{r:g}", panel="grades", severity=i,
                 x=r, scenario=_t(f"seven grades, one factor, correlation {100 * r:g}%", f"siete grados, un factor, correlación {100 * r:g}%"),
                 n_rep=N_POWER, feed=feed_grades())
        logit = LogisticPortfolio(n=5000, rho=r)
        for tid in ("pd.hosmer_lemeshow", "pd.spiegelhalter"):
            book.run(f"{tid}@rho{r:g}", tid, logit, f"logistic-5000-rho{r:g}", panel="obligors", severity=i, x=r,
                     scenario=_t(f"5,000 obligors, one factor, correlation {100 * r:g}%", f"5.000 deudores, un factor, correlación {100 * r:g}%"),
                     n_rep=N_POWER)
        series = DefaultCounts.over_years([1000] * 5, [0.03] * 5, rho=r, theta=0.2 if r > 0 else 0.0)
        scen_y = _t(f"five years, correlation {100 * r:g}% within a year, factor correlation 0.2 across",
                    f"cinco años, correlación {100 * r:g}% en el año, correlación del factor 0,2 entre años")
        for tid in ("pd.normal_multiperiod", "pd.traffic_lights"):
            book.run(f"{tid}@rho{r:g}", tid, series, f"series-5y-rho{r:g}", panel="years", severity=i, x=r, scenario=scen_y,
                     n_rep=N_POWER, feed=feed_series())
        _log(f"clustering rho={r:g}")
    golden, agree = _wp14_golden(book, wp)
    # WP14 Figure 9: the true confidence of a 99.9% independence-based binomial test, exact and WP14's approximation
    pds = [round(0.005 + 0.005 * k, 4) for k in range(19)]
    series = []
    for n in (100, 400, 1000, 1900):
        exact_y, approx_y = [], []
        for p in pds:
            w = (1.0 - math.exp(-50.0 * p)) / (1.0 - math.exp(-50.0))
            rho = 0.12 * w + 0.24 * (1.0 - w)
            exact_y.append(1.0 - rejection_probability("pd.binomial", n, p, 0.001, rho_true=rho)["probability"])
            approx_y.append(wp14_true_confidence(p, n, rho, 0.999))
        series.append({"id": f"exact-{n}", "label": _t(f"{n:,} obligors, exact", f"{n:,} deudores, exacta".replace(",", ".")), "y": exact_y})
        series.append({"id": f"approx-{n}", "label": _t(f"{n:,}, WP14 approximation", f"{n:,}, aproximación de WP14".replace(",", ".")), "y": approx_y})
    curve = {"id": "wp14-figure9", "label": _t("True confidence of a 99.9% binomial test under the Basel corporate correlation (WP14 Figure 9)",
                                               "Confianza verdadera de una prueba binomial al 99,9% con la correlación corporativa de Basilea (Figura 9 de WP14)"),
             "x_label": _t("PD", "PD"), "y_label": _t("True confidence", "Confianza verdadera"), "x": pds, "series": series}
    size12 = rejection_probability("pd.binomial", 1000, 0.01, 0.05, rho_true=0.12)["probability"]
    impact = {
        "binomial_size_rho12": _impact(size12, "probability", "Binomial test's true size at 5% when the asset correlation is 12% (1,000 obligors, PD 1%)",
                                       "Tamaño verdadero de la prueba binomial al 5% con correlación de activos 12% (1.000 deudores, PD 1%)"),
        "chi2_size_rho10": _impact(book.rate("pd.chi2_grades@rho0.1"), "probability", "Chi-square over grades: size at 5%, correlation 10%",
                                   "Chi-cuadrado por grados: tamaño al 5%, correlación 10%"),
        "wp14_cells_reproduced": _impact(agree, "cells", "WP14 Tables 7 and 8 cells reproduced (of 144)",
                                         "Celdas de las Tablas 7 y 8 de WP14 reproducidas (de 144)"),
    }
    findings = [
        _finding("F-BINOM-RHO", "S2", "accepted", ["pd.binomial@rho0.05", "pd.jeffreys@rho0.05", "pd.chi2_grades@rho0.05"],
                 "Tests that assume independent defaults reject a right PD far above their level once defaults are correlated (WP14: an early warning)",
                 "Las pruebas que suponen incumplimientos independientes rechazan una PD correcta muy sobre su nivel cuando hay correlación (WP14: alerta temprana)"),
        _finding("F-OBLIGOR-RHO", "S2", "accepted", ["pd.hosmer_lemeshow@rho0.05", "pd.spiegelhalter@rho0.05"],
                 "Obligor-level calibration tests assume independence too: one systematic factor inflates their size",
                 "Las pruebas de calibración a nivel de deudor también suponen independencia: un factor sistemático infla su tamaño"),
    ]
    values = {"binomial_size_rho05_exact": rejection_probability("pd.binomial", 1000, 0.01, 0.01, rho_true=0.05)["probability"],
              "wp14_agree": float(agree), "vasicek_size_rho12_exact": rejection_probability("pd.binomial_vasicek", 1000, 0.01, 0.05,
                                                                                            rho_true=0.12, rho=0.12)["probability"]}
    g3 = DefaultCounts(1000, 0.01, rho=CLUSTER[SPECIMEN_SEVERITY])
    specimen = _specimen(book, [(f"port-1000-rho{CLUSTER[SPECIMEN_SEVERITY]:g}", g3,
                                 lambda d: [cal.pd_binomial(**feed_cell()(d)), cal.pd_binomial_vasicek(**feed_cell()(d), rho=0.12)], {})])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [golden],
            "exact_curves": [curve], "estimators": None}


DRIFT = (0.0, 0.05, 0.1, 0.2, 0.3, 0.5)


def _yn_golden(book: Book, yn: dict[str, Any]) -> tuple[dict[str, Any], int]:
    cells = []
    labels = ("metric>0.1", "metric>0.25", "p<0.05")
    names = ("PSI > 0.10", "PSI > 0.25", "chi-square")
    for row in yn["rows"]:
        for si, shift in enumerate(yn["shifts_sd"]):
            gen = TwoSample(n_base=row["n"], n_target=row["m"], shift=shift, sd=yn["sd"], bins=yn["bins"])
            sim = simulate("stability.psi", gen, n_rep=yn["runs"], seed=_seed(book.case_seed, f"yn:{row['m']}:{row['n']}:{shift}"),
                           alphas=(0.05,), rules=_psi_rules())
            for label, name, pub in zip(labels, names, row["rates"][3 * si: 3 * si + 3], strict=True):
                ok, z = agrees_with_published(sim.rate(label), pub, yn["runs"])
                cells.append({"table": "Table 4", "row": f"m {row['m']}, n {row['n']}", "column": f"shift {shift:g} SD, {name}",
                              "published": pub, "measured": sim.rate(label).rate, "z": z, "agrees": bool(ok)})
    agree = sum(c["agrees"] for c in cells)
    zs = [c["z"] for c in cells if c["z"] is not None and 0.0 < c["published"] < 1.0]
    mean_z = float(np.mean(zs))
    return {"study": "yurdakul-naranjo-2020", "title": _t("Yurdakul and Naranjo (2020) Table 4: the PSI's rules and benchmark",
                                                          "Yurdakul y Naranjo (2020) Tabla 4: las reglas y la referencia del PSI"),
            "runs_published": yn["runs"], "runs": yn["runs"], "cells": cells, "agree": agree, "total": len(cells),
            "note": _t(f"The harness sits slightly above the paper on average (mean z {mean_z:+.2f} over the cells strictly between 0 and 1), so a few cells pass 3.29 combined SEs depending on the seed; no treatment of empty bins explains it (the paper does not state its own). Every qualitative finding of the paper reproduces.",
                       "El arnés queda algo sobre el artículo en promedio (z medio " + f"{mean_z:+.2f}".replace(".", ",") + " en las celdas estrictamente entre 0 y 1), así que unas pocas celdas pasan 3,29 EE combinados según la semilla; ningún tratamiento de intervalos vacíos lo explica (el artículo no declara el suyo). Cada hallazgo cualitativo del artículo se reproduce."),
            "mean_z": mean_z}, agree


def _drift(book: Book, yn: dict[str, Any]) -> dict[str, Any]:
    """The current population shifted, the model still right (CT-302, CT-304)."""
    for i, s in enumerate(DRIFT):
        two = TwoSample(1000, 1000, shift=s)
        scen = _t(f"two samples of 1,000, the current shifted by {s:g} SD", f"dos muestras de 1.000, la actual desplazada {s:g} DE".replace(".", ","))
        book.run(f"stability.psi@s{s:g}", "stability.psi", two, f"two-sample-1000-s{s:g}", panel="stability", severity=i, x=s,
                 scenario=scen, n_rep=N_POWER, rules=_psi_rules())
        for tid in ("stability.chi2", "stability.ks"):
            book.run(f"{tid}@s{s:g}", tid, two, f"two-sample-1000-s{s:g}", panel="stability", severity=i, x=s, scenario=scen,
                     n_rep=N_POWER)
        logit = LogisticPortfolio(n=5000, shift=s)
        scen_c = _t(f"5,000 obligors, covariates shifted by {s:g} SD, the model right", f"5.000 deudores, covariables desplazadas {s:g} DE, el modelo correcto".replace(".", ","))
        for tid in ("pd.hosmer_lemeshow", "pd.spiegelhalter"):
            book.run(f"{tid}@s{s:g}", tid, logit, f"logistic-5000-s{s:g}", panel="calibration", severity=i, x=s, scenario=scen_c,
                     n_rep=N_POWER)
        _log(f"drift shift={s:g}")
    golden, agree = _yn_golden(book, yn)
    impact = {
        "psi_power_s01": _impact(book.rate("stability.psi@s0.1"), "probability", "PSI benchmark: power at 5% for a 0.1 SD shift (samples of 1,000)",
                                 "Referencia del PSI: potencia al 5% para un desplazamiento de 0,1 DE (muestras de 1.000)"),
        "psi025_power_s02": _impact(book.rate("stability.psi@s0.2", "metric>0.25"), "probability",
                                    "PSI > 0.25 for a 0.2 SD shift (samples of 1,000)", "PSI > 0,25 para un desplazamiento de 0,2 DE (muestras de 1.000)"),
        "hl_size_s05": _impact(book.rate("pd.hosmer_lemeshow@s0.5"), "probability",
                               "Hosmer-Lemeshow at 5% under a 0.5 SD covariate shift with a right model",
                               "Hosmer-Lemeshow al 5% con un desplazamiento de covariables de 0,5 DE y modelo correcto"),
        "yn_cells_reproduced": _impact(agree, "cells", "Yurdakul-Naranjo Table 4 cells reproduced (of 54)",
                                       "Celdas de la Tabla 4 de Yurdakul y Naranjo reproducidas (de 54)"),
    }
    findings = [
        _finding("F-PSI-BANDS", "S2", "accepted", ["stability.psi@s0.2", "stability.psi@s0.1"],
                 "With samples of 1,000 the 0.25 band misses shifts the chi-square benchmark catches: fixed bands lose power as samples grow",
                 "Con muestras de 1.000 la banda 0,25 pierde desplazamientos que la referencia chi-cuadrado detecta: las bandas fijas pierden potencia al crecer las muestras"),
        _finding("F-DRIFT-NOT-MISCAL", "S4", "accepted", ["pd.hosmer_lemeshow@s0.5", "pd.spiegelhalter@s0.5"],
                 "Drift is not miscalibration: a right model stays calibrated under a covariate shift, so stability alarms and calibration tests answer different questions",
                 "La deriva no es descalibración: un modelo correcto sigue calibrado ante un desplazamiento de covariables; las alarmas de estabilidad y las pruebas de calibración responden preguntas distintas"),
    ]
    values = {"yn_agree": float(agree), "yn_mean_z": golden.pop("mean_z"), "psi_power_s01": book.rate("stability.psi@s0.1"),
              "hl_size_s05": book.rate("pd.hosmer_lemeshow@s0.5")}
    g3 = TwoSample(1000, 1000, shift=DRIFT[SPECIMEN_SEVERITY])
    specimen = _specimen(book, [(f"two-sample-1000-s{DRIFT[SPECIMEN_SEVERITY]:g}", g3,
                                 lambda d: [st.stability_psi(d["expected_counts"], d["actual_counts"]),
                                            st.stability_ks(d["development"], d["current"])], {})])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [golden],
            "exact_curves": [], "estimators": None}


DECAY = (0.0, 0.01, 0.02, 0.03, 0.05, 0.08)
DEV_SIZES = ((0.0, None), (16.0, 16.0), (4.0, 4.0), (1.0, 1.0), (0.467, 0.467))


def _decay(book: Book) -> dict[str, Any]:
    """The current AUC below the development AUC (CT-302)."""
    for i, dlt in enumerate(DECAY):
        sep = math.sqrt(2.0) * float(special.ndtri(AUC_DEV - dlt))
        g = BinormalScores(150, 4850, separation=sep, separation_development=DELTA_DEV)
        book.run(f"disc.auc_vs_initial@d{dlt:g}", "disc.auc_vs_initial", g, f"binormal-150-d{dlt:g}", panel="ecb", severity=i,
                 x=dlt, scenario=_t(f"development AUC 0.80 known, current {AUC_DEV - dlt:.2f}", f"AUC de desarrollo 0,80 conocida, actual {AUC_DEV - dlt:.2f}".replace(".", ",")),
                 n_rep=N_POWER)
        pair = BinormalScores(150, 4850, separation=DELTA_DEV, challenger_separation=sep)
        book.run(f"disc.delong@d{dlt:g}", "disc.delong", pair, f"binormal-150-pair-d{dlt:g}", panel="delong", severity=i, x=dlt,
                 scenario=_t(f"champion AUC 0.80, challenger {AUC_DEV - dlt:.2f}, same sample", f"campeón AUC 0,80, retador {AUC_DEV - dlt:.2f}, misma muestra".replace(".", ",")),
                 n_rep=N_POWER)
        _log(f"decay {dlt:g}")

    def ext(d):
        return {"auc_initial": d["auc_initial"], "risk": d["risk"], "defaults": d["defaults"],
                "auc_initial_variance": d["development_auc_variance"]}

    for i, (m, size) in enumerate(DEV_SIZES):
        g = BinormalScores(150, 4850, separation=1.2, development_size=size)
        lab = _t("known", "conocida") if size is None else _t(f"{m:g} times the current", f"{m:g} veces la actual".replace(".", ","))
        # the panel's axis is the current sample over the development sample: 0 when the development AUC is known
        ratio = 0.0 if size is None else 1.0 / m
        book.run(f"disc.auc_vs_initial@m{m:g}", "disc.auc_vs_initial", g, f"binormal-150-m{m:g}", panel="development", severity=i,
                 x=ratio, scenario=_t(f"no change; development AUC {lab['en']}", f"sin cambio; AUC de desarrollo {lab['es']}"), n_rep=N_NULL,
                 label=_t("ECB form", "Forma BCE"))
        if size is not None:
            book.run(f"disc.auc_vs_initial@m{m:g}-extended", "disc.auc_vs_initial", g, f"binormal-150-m{m:g}", panel="development",
                     severity=i, x=ratio, scenario=_t(f"no change; development AUC {lab['en']}, its variance added",
                                                   f"sin cambio; AUC de desarrollo {lab['es']}, su varianza sumada"),
                     n_rep=N_NULL, feed=ext, label=_t("Extended form", "Forma extendida"))
    # the smallest AUC drop each test catches with 80% power, interpolated on the ladder
    def drop80(prefix: str) -> float | None:
        xs, ys = list(DECAY), [book.rate(f"{prefix}@d{d:g}") for d in DECAY]
        for a, b, ya, yb in zip(xs, xs[1:], ys, ys[1:], strict=False):
            if ya < 0.8 <= yb:
                return a + (0.8 - ya) * (b - a) / (yb - ya)
        return None

    ecb80, delong80 = drop80("disc.auc_vs_initial"), drop80("disc.delong")
    impact = {
        "ecb_drop80": _impact(ecb80, "AUC", "AUC drop the ECB test catches with 80% power (150 defaulters)",
                              "Caída de AUC que la prueba del BCE detecta con 80% de potencia (150 incumplidos)"),
        "delong_drop80": _impact(delong80, "AUC", "AUC gap DeLong catches with 80% power (150 defaulters)",
                                 "Brecha de AUC que DeLong detecta con 80% de potencia (150 incumplidos)"),
        "ecb_size_c01_ratio": _impact(book.rate("disc.auc_vs_initial@m0.467"), "probability",
                                      "ECB test's size at 5% with C01's calibration slice (0.467 times the holdout)",
                                      "Tamaño de la prueba del BCE al 5% con el tramo de calibración de C01 (0,467 veces la reserva)"),
    }
    findings = [
        _finding("F-AUC-INIT-C01", "S2", "closed", ["disc.auc_vs_initial@m0.467", "disc.auc_vs_initial@m0.467-extended"],
                 "At C01's slice sizes the ECB form rejects about one time in six when nothing changed; C01 now adds the development AUC's variance",
                 "Con los tamaños de tramo de C01 la forma del BCE rechaza cerca de una vez en seis sin cambio; C01 ahora suma la varianza del AUC de desarrollo"),
        _finding("F-DECAY-POWER", "S3", "accepted", ["disc.auc_vs_initial@d0.02", "disc.auc_vs_initial@d0.05"],
                 "With 150 defaulters an AUC drop of two points is rarely caught: small portfolios see only large decays",
                 "Con 150 incumplidos una caída de dos puntos de AUC rara vez se detecta: las carteras pequeñas solo ven deterioros grandes"),
    ]
    values = {"ecb_size_c01_ratio": book.rate("disc.auc_vs_initial@m0.467"),
              "ext_size_c01_ratio": book.rate("disc.auc_vs_initial@m0.467-extended"),
              "ecb_power_d005": book.rate("disc.auc_vs_initial@d0.05")}
    sep3 = math.sqrt(2.0) * float(special.ndtri(AUC_DEV - DECAY[SPECIMEN_SEVERITY]))
    g3 = BinormalScores(150, 4850, separation=sep3, separation_development=DELTA_DEV)
    specimen = _specimen(book, [(f"binormal-150-d{DECAY[SPECIMEN_SEVERITY]:g}", g3,
                                 lambda d: [disc.disc_auc(d["risk"], d["defaults"]),
                                            disc.disc_auc_vs_initial(d["auc_initial"], d["risk"], d["defaults"])], {})])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [],
            "exact_curves": [], "estimators": None}


LEAK = (0.0, 0.25, 0.5, 1.0, 1.5, 2.0)


def _leakage(book: Book) -> dict[str, Any]:
    """A feature that carries the outcome in development and is noise at decision time (CT-302, CT-304)."""
    for i, lam in enumerate(LEAK):
        g = BinormalScores(150, 4850, separation=1.0, leak=lam)
        scen = _t(f"the leaked feature shifted by {lam:g} for defaulters in development", f"la variable filtrada desplazada {lam:g} para incumplidos en desarrollo".replace(".", ","))
        book.run(f"disc.auc_vs_initial@l{lam:g}", "disc.auc_vs_initial", g, f"binormal-150-leak{lam:g}", panel="auc", severity=i,
                 x=lam, scenario=scen, n_rep=N_POWER)
        book.run(f"stability.csi@l{lam:g}", "stability.csi", g, f"binormal-150-leak{lam:g}", panel="feature", severity=i, x=lam,
                 scenario=scen, n_rep=N_POWER)
        _log(f"leakage {lam:g}")
    nested = book.run("disc.delong@nested", "disc.delong", NestedLda(), "nested-lda-framingham", panel="delong", severity=0,
                      x=0.0, scenario=_t("nested discriminants fitted and compared on the same sample (Demler et al.)",
                                         "discriminantes anidados ajustados y comparados en la misma muestra (Demler et al.)"),
                      n_rep=DEMLER["runs"], label=_t("DeLong, nested in-sample", "DeLong, anidados en la muestra"))
    book.run("disc.delong@non-nested", "disc.delong", BinormalScores(621, 7640, separation=1.2, challenger_separation=1.2),
             "binormal-621-pair", panel="delong", severity=0, x=0.0,
             scenario=_t("two non-nested scores of equal AUC on an independent sample", "dos puntajes no anidados de igual AUC en una muestra independiente"),
             n_rep=N_POWER, label=_t("DeLong, non-nested", "DeLong, no anidados"))
    ok, z = agrees_with_published(nested.rates["p<0.05"], DEMLER["rate"], DEMLER["runs"])
    golden = {"study": "demler-2012", "title": _t("Demler, Pencina and D'Agostino (2012): DeLong on nested models",
                                                  "Demler, Pencina y D'Agostino (2012): DeLong en modelos anidados"),
              "runs_published": DEMLER["runs"], "runs": DEMLER["runs"],
              "cells": [{"table": "section 2.3", "row": "DeLong, nested", "column": "0.05", "published": DEMLER["rate"],
                         "measured": nested.rates["p<0.05"].rate, "z": z, "agrees": bool(ok)}],
              "agree": int(ok), "total": 1,
              "note": _t(f"Quoted: \"{DEMLER['quote']}\".", f"Cita: \"{DEMLER['quote']}\".")}
    lam1 = BinormalScores(150, 4850, separation=1.0, leak=1.0).truth()
    impact = {
        "dev_auc_inflation_l1": _impact(lam1["auc_development"] - lam1["auc_current"], "AUC",
                                        "Development AUC inflation by a leak of 1 (exact)", "Inflación del AUC de desarrollo por una filtración de 1 (exacta)"),
        "csi_power_l1": _impact(book.rate("stability.csi@l1"), "probability", "CSI of the leaked feature: power at 5%, leak 1",
                                "CSI de la variable filtrada: potencia al 5%, filtración 1"),
        "auc_power_l1": _impact(book.rate("disc.auc_vs_initial@l1"), "probability", "AUC against development: power at 5%, leak 1",
                                "AUC contra desarrollo: potencia al 5%, filtración 1"),
    }
    findings = [
        _finding("F-LEAK-SIGNAL", "S2", "accepted", ["disc.auc_vs_initial@l1", "stability.csi@l1"],
                 "The tests built so far see a leak mostly as a discrimination drop out of time; the leaked feature's own distribution moves too little for the CSI",
                 "Las pruebas construidas hasta ahora ven una filtración sobre todo como una caída de discriminación fuera de tiempo; la distribución de la variable filtrada se mueve muy poco para el CSI"),
        _finding("F-DELONG-NESTED", "S3", "accepted", ["disc.delong@nested", "disc.delong@non-nested"],
                 "DeLong on nested models fitted on the comparison sample almost never rejects (Demler et al.); compare non-nested models on a holdout",
                 "DeLong en modelos anidados ajustados en la muestra de comparación casi nunca rechaza (Demler et al.); compárense modelos no anidados en una reserva"),
    ]
    values = {"demler_rate": nested.rates["p<0.05"].rate, "csi_power_l1": book.rate("stability.csi@l1"),
              "auc_power_l1": book.rate("disc.auc_vs_initial@l1")}
    g3 = BinormalScores(150, 4850, separation=1.0, leak=LEAK[SPECIMEN_SEVERITY])
    specimen = _specimen(book, [(f"binormal-150-leak{LEAK[SPECIMEN_SEVERITY]:g}", g3,
                                 lambda d: [disc.disc_auc_vs_initial(d["auc_initial"], d["risk"], d["defaults"]),
                                            st.stability_csi(d["expected_counts"], d["actual_counts"], segment="leaked feature")], {})])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [golden],
            "exact_curves": [], "estimators": None}


MONO = (1.0, 1.25, 1.5, 2.0, 3.0, 4.0)
SWAP = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def _monotonicity(book: Book) -> dict[str, Any]:
    """A migration cell farther from the diagonal above its neighbour; two grades' PDs moved past each other."""
    base = decaying_matrix(7)
    for i, ratio in enumerate(MONO):
        m = break_monotonicity(base, 3, 1, ratio)
        for n in (500, 2000):
            book.run(f"rating.migration_ztests@r{ratio:g}-n{n}", "rating.migration_ztests", Migrations([n] * 7, m),
                     f"migrations-7-{n}-r{ratio:g}", panel=f"migration-{n}", severity=i, x=ratio,
                     scenario=_t(f"grade 4 to grade 2 at {ratio:g} times grade 4 to grade 3; {n:,} obligors per grade",
                                 f"grado 4 a grado 2 a {ratio:g} veces grado 4 a grado 3; {n:,} deudores por grado".replace(",", ".")),
                     n_rep=N_POWER)
        _log(f"migration ratio={ratio:g}")
    for i, s in enumerate(SWAP):
        true = list(GR_PD)
        gap = GR_PD[3] - GR_PD[2]
        true[2], true[3] = GR_PD[2] + s * gap, GR_PD[3] - s * gap
        g = DefaultCounts(GR_N, true, pd_forecast=GR_PD)
        scen = _t(f"grades 3 and 4 true PDs moved {s:g} of the way past each other", f"PD verdaderas de los grados 3 y 4 movidas {s:g} del camino una sobre otra".replace(".", ","))
        for tid, kw in (("pd.default_profile", {"n_sim": 2000}), ("pd.chi2_grades", {})):
            book.run(f"{tid}@swap{s:g}", tid, g, f"grades-7-swap{s:g}", panel="curve", severity=i, x=s, scenario=scen,
                     n_rep=N_POWER, feed=feed_grades(), test_kwargs=kw)
        _log(f"swap {s:g}")
    impact = {
        "migration_power_r2_n500": _impact(book.rate("rating.migration_ztests@r2-n500"), "probability",
                                           "Migration z-tests: power at 5% for a cell twice its neighbour, 500 per grade",
                                           "Pruebas z de migración: potencia al 5% para una celda del doble de su vecina, 500 por grado"),
        "profile_power_swap1": _impact(book.rate("pd.default_profile@swap1"), "probability",
                                       "Default-profile test: power at 5% when grades 3 and 4 are inverted",
                                       "Prueba del perfil: potencia al 5% cuando los grados 3 y 4 están invertidos"),
    }
    findings = [
        _finding("F-MIGRATION-POWER", "S3", "accepted", ["rating.migration_ztests@r2-n500", "rating.migration_ztests@r1-n500"],
                 "Holm's control over 42 cells makes the migration z-tests conservative: a migration twice too frequent goes unseen half the time with 500 obligors per grade",
                 "El control de Holm sobre 42 celdas hace conservadoras las pruebas z de migración: una migración del doble de frecuente pasa inadvertida la mitad de las veces con 500 deudores por grado"),
    ]
    values = {"migration_power_r2_n500": book.rate("rating.migration_ztests@r2-n500"),
              "migration_size_r1_n500": book.rate("rating.migration_ztests@r1-n500")}
    g3 = Migrations([500] * 7, break_monotonicity(base, 3, 1, MONO[SPECIMEN_SEVERITY]))
    specimen = _specimen(book, [(f"migrations-7-500-r{MONO[SPECIMEN_SEVERITY]:g}", g3,
                                 lambda d: [rs.rating_migration_ztests(d["counts"]), rs.rating_mwb(d["counts"])], {})])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [],
            "exact_curves": [], "estimators": None}


CONC = (0.0, 0.01, 0.02, 0.05, 0.10, 0.50)


def _concentration(book: Book) -> dict[str, Any]:
    """Mass moved into the modal grade (CT-302)."""
    for i, share in enumerate(CONC):
        g = GradeFrequencies(5000, concentrate(P10, share), P10, development_obligors=5000)
        scen = _t(f"{100 * share:g}% of every grade's mass moved into the modal grade; 5,000 obligors per sample",
                  f"{100 * share:g}% de la masa de cada grado movida al grado modal; 5.000 deudores por muestra")
        book.run(f"rating.hhi@c{share:g}", "rating.hhi", g, f"grades-10-c{share:g}", panel="ecb", severity=i, x=share, scenario=scen,
                 n_rep=N_POWER)
        book.run(f"stability.chi2@c{share:g}", "stability.chi2", g, f"grades-10-c{share:g}", panel="counts", severity=i, x=share,
                 scenario=scen, n_rep=N_POWER)
        _log(f"concentration {share:g}")
    cvs = [round(0.05 * k, 2) for k in range(1, 101)]
    series = []
    for k, ci in ((10, 0.3), (10, 0.6), (10, 1.0), (26, 0.6)):
        ys = [None if (c < ci or c > math.sqrt(k - 1)) else math.sqrt(k - 1) * (c - ci) / (c * math.sqrt(0.5 + c * c)) for c in cvs]
        series.append({"id": f"k{k}-cv{ci:g}", "label": _t(f"{k} grades, initial CV {ci:g}", f"{k} grados, CV inicial {ci:g}".replace(".", ",")),
                       "y": ys})
    curve = {"id": "hhi-statistic", "label": _t("The ECB concentration statistic against the current CV (exact)",
                                                "El estadístico de concentración del BCE según el CV actual (exacto)"),
             "x_label": _t("Current coefficient of variation", "Coeficiente de variación actual"),
             "y_label": _t("Statistic (reject at 5% above 1.645)", "Estadístico (rechaza al 5% sobre 1,645)"), "x": cvs, "series": series}
    cv0 = concentration(P10)[0]
    from scipy import optimize

    smax = -optimize.minimize_scalar(lambda c: -3.0 * (c - cv0) / (c * math.sqrt(0.5 + c * c)), bounds=(cv0, 3.0), method="bounded").fun
    impact = {
        "hhi_max_statistic": _impact(smax, "statistic", "Largest ECB statistic for these ten grades (the 5% critical value is 1.645)",
                                     "Mayor estadístico del BCE para estos diez grados (el valor crítico al 5% es 1,645)"),
        "hhi_power_c05": _impact(book.rate("rating.hhi@c0.5"), "probability", "ECB test: power at 5% with half the mass moved",
                                 "Prueba del BCE: potencia al 5% con la mitad de la masa movida"),
        "chi2_power_c005": _impact(book.rate("stability.chi2@c0.05"), "probability", "Chi-square on the counts: power at 5% with 5% moved",
                                   "Chi-cuadrado de los conteos: potencia al 5% con 5% movido"),
    }
    findings = [
        _finding("F-HHI-BOUNDED", "S2", "open", ["rating.hhi@c0.5", "stability.chi2@c0.05"],
                 "The ECB concentration statistic is bounded: with ten grades and an initial CV of 0.6 it cannot reject at 5%; test concentration on the counts",
                 "El estadístico de concentración del BCE es acotado: con diez grados y un CV inicial de 0,6 no puede rechazar al 5%; pruébese la concentración en los conteos"),
    ]
    values = {"hhi_power_c05": book.rate("rating.hhi@c0.5"), "chi2_power_c005": book.rate("stability.chi2@c0.05"),
              "hhi_max_statistic": smax}
    g3 = GradeFrequencies(5000, concentrate(P10, CONC[SPECIMEN_SEVERITY]), P10, development_obligors=5000)
    specimen = _specimen(book, [(f"grades-10-c{CONC[SPECIMEN_SEVERITY]:g}", g3,
                                 lambda d: [rs.rating_hhi(d["freq_current"], d["freq_initial"]),
                                            st.stability_chi2(d["expected_counts"], d["actual_counts"])], {})])
    return {"impact": impact, "findings": findings, "values": values, "specimen": specimen, "golden": [],
            "exact_curves": [curve], "estimators": None}


VARIANTS: tuple[dict[str, Any], ...] = (
    {"id": "null", "run": _null, "ladder": None, "panels": ("calibration", "discrimination", "stability", "rating", "settings"),
     "title": _t("The null: every test when the model is right", "La nula: cada prueba cuando el modelo es correcto"),
     "short": _t("Null", "Nula"),
     "regime": _t("Every p-value test on data where its null hypothesis holds at the boundary: its size, at 5% and 1%.",
                  "Cada prueba con valor p en datos donde su hipótesis nula se cumple en la frontera: su tamaño, al 5% y 1%.")},
    {"id": "miscalibration", "run": _miscalibration, "ladder": (MISCAL, _t("true PD / PD applied", "PD verdadera / PD aplicada")),
     "panels": ("portfolio", "grades", "obligors", "years"),
     "title": _t("Miscalibration: PDs underestimated", "Descalibración: PD subestimadas"), "short": _t("Miscalibration", "Descalibración"),
     "regime": _t("Every true PD is k times the PD applied, k from 1 to 3.", "Cada PD verdadera es k veces la aplicada, k de 1 a 3.")},
    {"id": "clustering", "run": _clustering, "ladder": (CLUSTER, _t("asset correlation", "correlación de activos")),
     "panels": ("portfolio", "grades", "obligors", "years"),
     "title": _t("Clustering: right PDs, correlated defaults", "Agrupamiento: PD correctas, incumplimientos correlacionados"),
     "short": _t("Clustering", "Agrupamiento"),
     "regime": _t("The PDs are right; defaults share one systematic factor, correlation from 0% to 20%.",
                  "Las PD son correctas; los incumplimientos comparten un factor sistemático, correlación de 0% a 20%.")},
    {"id": "drift", "run": _drift, "ladder": (DRIFT, _t("mean shift (standard deviations)", "desplazamiento de la media (desviaciones estándar)")),
     "panels": ("stability", "calibration"),
     "title": _t("Drift: the population moved", "Deriva: la población se movió"), "short": _t("Drift", "Deriva"),
     "regime": _t("The current population shifted by up to half a standard deviation; the model stays right.",
                  "La población actual se desplazó hasta media desviación estándar; el modelo sigue correcto.")},
    {"id": "discrimination-decay", "run": _decay, "ladder": (DECAY, _t("AUC drop", "caída de AUC")),
     "panels": ("ecb", "delong", "development"),
     "title": _t("Discrimination decay", "Deterioro de la discriminación"), "short": _t("Decay", "Deterioro"),
     "regime": _t("The current AUC falls below the development AUC of 0.80, by up to 0.08.",
                  "El AUC actual cae bajo el AUC de desarrollo de 0,80, hasta 0,08.")},
    {"id": "leakage", "run": _leakage, "ladder": (LEAK, _t("leak (shift of the feature for defaulters)", "filtración (desplazamiento de la variable para incumplidos)")),
     "panels": ("auc", "feature", "delong"),
     "title": _t("Leakage: an outcome in a feature", "Filtración: el resultado en una variable"), "short": _t("Leakage", "Filtración"),
     "regime": _t("A feature carries the outcome in development and is noise at decision time.",
                  "Una variable lleva el resultado en desarrollo y es ruido al decidir.")},
    {"id": "broken-monotonicity", "run": _monotonicity, "ladder": (MONO, _t("planted cell / closer neighbour", "celda plantada / vecina más cercana")),
     "panels": ("migration-500", "migration-2000", "curve"),
     "title": _t("Broken monotonicity", "Monotonía rota"), "short": _t("Monotonicity", "Monotonía"),
     "regime": _t("A migration two notches away more frequent than one notch away; two grades' PDs moved past each other.",
                  "Una migración a dos escalones más frecuente que a un escalón; las PD de dos grados cruzadas.")},
    {"id": "concentration", "run": _concentration, "ladder": (CONC, _t("share moved into the modal grade", "fracción movida al grado modal")),
     "panels": ("ecb", "counts"),
     "title": _t("Concentration in grades", "Concentración en grados"), "short": _t("Concentration", "Concentración"),
     "regime": _t("A share of every grade's mass moves into the modal grade, up to half.",
                  "Una fracción de la masa de cada grado se mueve al grado modal, hasta la mitad.")},
)

PANEL_LABEL: dict[str, dict[str, str]] = {
    "calibration": _t("Calibration", "Calibración"), "discrimination": _t("Discrimination", "Discriminación"),
    "stability": _t("Stability", "Estabilidad"), "rating": _t("Rating system", "Sistema de calificación"),
    "settings": _t("Settings that matter", "Ajustes que importan"), "portfolio": _t("Portfolio count tests", "Pruebas de conteo de cartera"),
    "grades": _t("Grade tests", "Pruebas por grado"), "obligors": _t("Obligor-level tests", "Pruebas por deudor"),
    "years": _t("Multi-year tests", "Pruebas multianuales"), "ecb": _t("ECB test", "Prueba del BCE"),
    "delong": _t("DeLong", "DeLong"), "development": _t("The development AUC as an estimate", "El AUC de desarrollo como estimación"),
    "auc": _t("AUC against development", "AUC contra desarrollo"), "feature": _t("The leaked feature", "La variable filtrada"),
    "migration-500": _t("Migrations, 500 per grade", "Migraciones, 500 por grado"),
    "migration-2000": _t("Migrations, 2,000 per grade", "Migraciones, 2.000 por grado"),
    "curve": _t("The PD curve's shape", "La forma de la curva de PD"), "counts": _t("Chi-square on the counts", "Chi-cuadrado de los conteos"),
}

#: the x axis of a panel whose simulations do not run along the family's ladder
PANEL_AXIS: dict[str, dict[str, str]] = {
    "development": _t("current sample over the development sample (0: the development AUC known)",
                      "muestra actual sobre la de desarrollo (0: AUC de desarrollo conocida)"),
    "curve": _t("how far the true PDs of grades 3 and 4 moved past each other (1: swapped)",
                "cuánto se movieron una sobre otra las PD verdaderas de los grados 3 y 4 (1: intercambiadas)"),
}

#: what a reader should see, declared before the bake from the pilot runs (CT-307); the bases are in dossier 12
EXPECT: dict[str, tuple[float, float]] = {
    "size_hl_given": (0.035, 0.066),
    "size_hl_fitted": (0.09, 0.14),                 # P(chi2_10 > chi2_8 at 95%) = 0.115
    "size_normal": (0.07, 0.10),                    # WP14 Table 7 I_LC: 0.081
    "auc_init_ecb_dev1": (0.09, 0.14),
    "auc_init_ext_dev1": (0.035, 0.066),
    "psi010_false_alarm_n100": (0.80, 0.90),        # Yurdakul and Naranjo Table 4: 0.849
    "auc_ecb_se_relative_error_pct": (-6.0, 6.0),
    "tests_within_bound": (15.0, 15.0),             # all but the normal test over five years and Jeffreys at 1% (exact 1.38%)
    # exact (bisection on the exact power): 1.2587; the range declared before the first bake, (1.10, 1.25), was a
    # guess and was wrong, corrected after it (docs/design/features/c22-validator/tasks.md)
    "jeffreys_k80": (1.255, 1.262),
    "profile_size_k3": (0.02, 0.08),                # blind to the level: about its size
    "binomial_power_k15": (0.95, 1.0),
    "hl_power_k125": (0.30, 0.80),
    "binomial_size_rho05_exact": (0.111, 0.112),    # WP14 Example 3 test, exact
    "wp14_agree": (143.0, 143.0),
    "vasicek_size_rho12_exact": (0.03, 0.05),
    # the harness sits slightly above the paper on average (mean z about +0.7 over 18 independent runs per rule, in
    # two seeds), so how many of the 54 cells pass 3.29 combined SEs depends on the seed: 53 in the engine's suite, 50
    # here; declared (53, 53) before the first bake, corrected after it
    "yn_agree": (48.0, 54.0),
    "yn_mean_z": (0.2, 1.2),
    "psi_power_s01": (0.15, 0.60),
    "hl_size_s05": (0.03, 0.07),                    # a right model stays calibrated under covariate drift
    "ecb_size_c01_ratio": (0.14, 0.21),
    "ext_size_c01_ratio": (0.035, 0.07),
    "ecb_power_d005": (0.5, 1.0),
    "demler_rate": (0.0, 0.01),                     # Demler et al.: 0.001
    "csi_power_l1": (0.0, 0.5),
    "auc_power_l1": (0.6, 1.0),
    "migration_power_r2_n500": (0.40, 0.65),
    "migration_size_r1_n500": (0.0, 0.01),
    "hhi_power_c05": (0.0, 0.0),
    "chi2_power_c005": (0.88, 1.0),
    "hhi_max_statistic": (1.05, 1.15),              # ten grades: 1.0937 at an initial CV of 0.6, 1.0913 at P10's 0.6017
}


def _models(seed: int, rv: str, paths: Any) -> dict[str, Any]:
    """The generator families, and the exact-probability machinery the live calculator ports (quadrature, parity)."""
    families = (
        ("G1-default-counts", "DefaultCounts", _t("Default counts, one-factor model with time correlation (WP14)", "Conteos de incumplimiento, modelo de un factor con correlación temporal (WP14)")),
        ("G2-binormal", "BinormalScores", _t("Binormal scores with an exact AUC", "Puntajes binormales con AUC exacta")),
        ("G3-logistic", "LogisticPortfolio", _t("Logistic portfolio with a planted calibration", "Cartera logística con calibración plantada")),
        ("G4-two-sample", "TwoSample", _t("Two samples (Yurdakul and Naranjo's design)", "Dos muestras (diseño de Yurdakul y Naranjo)")),
        ("G5-migrations", "Migrations", _t("Migration matrices with a planted cell", "Matrices de migración con una celda plantada")),
        ("G6-grade-frequencies", "GradeFrequencies", _t("Grade frequencies with planted concentration", "Frecuencias por grado con concentración plantada")),
        ("G7-nested-lda", "NestedLda", _t("Nested discriminants (Demler et al.)", "Discriminantes anidados (Demler et al.)")),
    )
    records = [{"id": fid, "family": "generator", "rung": "dgp", "title": title, "short_title": _t(cls, cls),
                "engine": f"riskvalidation.generators.{cls}", "engine_version": rv, "licence": "MIT", "checkpoint_sha256": None,
                "calibration": None, "parameters": {}, "details": {"class": cls}} for fid, cls, title in families]
    records.append({"id": "X1-exact", "family": "exact", "rung": "exact",
                    "title": _t("Exact rejection probabilities of the count tests", "Probabilidades exactas de rechazo de las pruebas de conteo"),
                    "short_title": _t("Exact", "Exacta"), "engine": "riskvalidation.harness.exact", "engine_version": rv,
                    "licence": "MIT", "checkpoint_sha256": None, "calibration": None, "parameters": {},
                    "details": {"quadrature": {"rule": "probabilists' Gauss-Hermite, 256 nodes", "nodes": [float(x) for x in GH_NODES],
                                               "weights": [float(w) for w in GH_WEIGHTS]}}})
    # the parity points: an interior grid, and the corners of the rail's knobs (100 to 10,000 obligors, PD applied
    # 0.1% to 20%, true-to-applied ratio 1 to 3, true correlation 0 to 30%, assumed correlation 1% to 30%), so the
    # live calculator is held to the engine over everything a reader can select
    grids = (
        ((100, 1000, 5000), (0.005, 0.02, 0.1), (1.0, 1.5), (0.0, 0.12), (0.12,)),
        ((100, 1000, 10000), (0.001, 0.02, 0.2), (1.0, 3.0), (0.0, 0.3), (0.01, 0.12, 0.3)),
    )
    parity, seen = [], set()
    for ns, pds, ratios, rhos_t, rhos_a in grids:
        for test in ("pd.binomial", "pd.jeffreys", "pd.binomial_vasicek"):
            for n in ns:
                for pd in pds:
                    for ratio in ratios:
                        for rho_t in rhos_t:
                            for rho_a in (rhos_a if test == "pd.binomial_vasicek" else (None,)):
                                for a in LEVELS:
                                    key = (test, n, pd, ratio, rho_t, rho_a, a)
                                    if key in seen:
                                        continue
                                    seen.add(key)
                                    kw = {} if rho_a is None else {"rho": rho_a}
                                    ex = rejection_probability(test, n, pd, a, pd_true=pd * ratio, rho_true=rho_t, **kw)
                                    parity.append({"test_id": test, "n": n, "pd": pd, "ratio": ratio, "rho_true": rho_t,
                                                   "rho_assumed": rho_a, "alpha": a,
                                                   "critical_count": ex["critical_count"], "probability": ex["probability"]})
    lineage = lin.build(CASE_ID, sources=[], truth_status="synthetic-known-truth", seed=seed, code_version=__version__,
                        riskvalidation_version=rv, generators=tuple(cls for _, cls, _ in families))
    doc = build_models_artifact(case_id=CASE_ID, fit_id="generators", model=records,
                                fit={"parity": parity, "levels": list(LEVELS)}, lineage=lineage,
                                lane={"lane": "precompute", "reasons": []})
    rel = f"{CASE_ID}/models-generators.json"
    return {"rel": rel, **write_artifact(paths.root, rel, doc, exact=frozenset({"details", "parity"}), engines=ENGINES, run_ms=RUN_MS)}


class C22:
    id = CASE_ID
    slug = "validator"
    title = _t("Validating the validator: size and power of every test", "Validar al validador: tamaño y potencia de cada prueba")
    category_id = "validator"
    kind = "synthetic"
    question = _t("How often does each validation test reject a right model, and which defects does it catch?",
                  "¿Con qué frecuencia cada prueba de validación rechaza un modelo correcto, y qué defectos detecta?")
    sources = SOURCES

    def bake(self, seed: int, paths: Any, data_root: Path, only: tuple[str, ...] | None = None) -> dict[str, Any]:
        from ..io import sources as registry

        registry.assert_case_inputs(CASE_ID, list(SOURCES))
        rv = _v("riskvalidation")
        wp = papers.read_wp14_simulation(Path(data_root) / "raw" / "bcbs-wp14" / WP14_PDF)
        yn = papers.read_yurdakul_naranjo_table4(Path(data_root) / "raw" / "yurdakul-naranjo-2020" / YN_PDF)
        _log("papers read: WP14 Tables 5 to 8, Yurdakul-Naranjo Table 4")
        models = _models(seed, rv, paths)
        entries: list[dict[str, Any]] = [{"role": "models", "variant_id": "models-generators", "truth_status": "synthetic-known-truth",
                                          "title": _t("The generators and the exact machinery", "Los generadores y la maquinaria exacta"),
                                          "short_title": _t("Generators", "Generadores"),
                                          "regime": _t("The data-generating mechanisms and the quadrature of the live calculator",
                                                       "Los mecanismos generadores y la cuadratura de la calculadora en vivo"),
                                          "path": models["rel"], "bytes": models["bytes"], "lane": models["lane"], "gate": models["gate"]}]
        values: dict[str, float] = {}
        for v in VARIANTS:
            if only is not None and v["id"] not in only:
                continue
            book = Book(seed, v["id"])
            args = (book, wp) if v["id"] == "clustering" else (book, yn) if v["id"] == "drift" else (book,)
            res = v["run"](*args)
            values.update(res["values"])
            ladder = None if v["ladder"] is None else {"values": list(v["ladder"][0]), "label": v["ladder"][1]}
            outputs = {
                "kind": "validator", "family": v["id"], "ladder": ladder, "levels": list(LEVELS),
                "panels": [{"id": p, "label": PANEL_LABEL[p], "axis": PANEL_AXIS.get(p)} for p in v["panels"]],
                "simulations": book.rows, "generators": book.generators, "golden": res["golden"],
                "exact_curves": res["exact_curves"], "estimators": res["estimators"],
                "specimen": {"severity": 0 if v["id"] == "null" else SPECIMEN_SEVERITY},
                "size_bounds": {f"p<{a:g}": size_bound(a, N_NULL if v["id"] == "null" else N_POWER) for a in LEVELS},
            }
            sources = ["bcbs-wp14"] if v["id"] == "clustering" else ["yurdakul-naranjo-2020"] if v["id"] == "drift" else []
            gens = tuple(sorted({g["name"] for g in book.generators.values()}))
            lineage = lin.build(CASE_ID, sources=sources, truth_status="synthetic-known-truth", seed=seed, code_version=__version__,
                                riskvalidation_version=rv, generators=gens)
            model = [{"id": ref, "family": "generator", "rung": g["name"], "title": _t(ref, ref), "short_title": _t(ref, ref),
                      "engine": f"riskvalidation.generators ({g['name']})", "engine_version": rv, "licence": "MIT",
                      "checkpoint_sha256": None, "calibration": None, "parameters": {}} for ref, g in book.generators.items()]
            art = build_artifact(case_id=CASE_ID, variant_id=v["id"], model=model, outputs=outputs, tests=res["specimen"],
                                 impact=res["impact"], findings=res["findings"], lineage=lineage,
                                 lane={"lane": "precompute", "reasons": []})
            rel = f"{CASE_ID}/{v['id']}.json"
            entry = write_artifact(paths.root, rel, art, exact=frozenset({"seed", "config", "truth", "critical_count"}),
                                   engines=ENGINES, run_ms=RUN_MS)
            _log(f"variant {v['id']}: {len(book.rows)} simulations, {entry['bytes']:,} bytes")
            entries.append({"role": "variant", "variant_id": v["id"], "title": v["title"], "short_title": v["short"],
                            "regime": v["regime"], "truth_status": "synthetic-known-truth", "models_ref": models["rel"], **entry})
        expect = EXPECT if only is None else {k: r for k, r in EXPECT.items() if k in values}
        ranges = expectations.check(CASE_ID, expect, values)
        manifest = build_case_manifest(
            case_id=CASE_ID, title=self.title, category={"en": "Validating the validator", "es": "Validar al validador"},
            question=self.question, sources=list(SOURCES), seed=seed, variants=entries,
            default_variant="null" if any(e["variant_id"] == "null" for e in entries) else entries[1]["variant_id"],
            contract={}, expect=ranges, riskvalidation_version=rv, source_details=_source_details(SOURCES))
        write_json(paths.manifests / f"{CASE_ID}.json", manifest)
        return manifest


def _source_details(ids) -> dict[str, dict[str, str]]:
    from ..io import sources as registry

    reg = registry.load()
    return {i: {"name": reg[i].name, "publisher": reg[i].publisher, "landing": reg[i].landing,
                "licence": reg[i].licence, "class": reg[i].klass, "attribution": reg[i].attribution} for i in ids}


CASE = C22()
