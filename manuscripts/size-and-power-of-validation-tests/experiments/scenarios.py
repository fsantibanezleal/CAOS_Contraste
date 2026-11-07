"""The null scenarios of the 21 credit-family tests, rebuilt from the engine's generators.

The scenarios are the ones of the pipeline module ``data-pipeline/pipeline/cases/c22_validator.py`` (function ``_null``): a
generator at the boundary of the test's null with its assumptions met, and the feed that maps a draw to the test's
arguments. ``check_against_document`` compares every rebuilt generator with the configuration committed in
``data/derived/C22/null.json`` and stops on a difference, so a scenario that drifted from the committed one cannot be
measured by mistake.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
from scipy.linalg import expm

from riskvalidation.generators import (
    BinormalScores,
    DefaultCounts,
    GradeFrequencies,
    LogisticPortfolio,
    Migrations,
    TwoSample,
    break_monotonicity,
    decaying_matrix,
    feed_cell,
    feed_grades,
    feed_series,
    jsonable,
)
from riskvalidation.generators.paths import RatingPaths

ROOT = pathlib.Path(__file__).resolve().parents[3]
NULL_DOC = ROOT / "data" / "derived" / "C22" / "null.json"

GR_N = (2500, 2000, 1500, 1500, 800, 400, 150)
GR_PD = (0.002, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16)
P10 = (0.02, 0.05, 0.10, 0.15, 0.20, 0.18, 0.13, 0.09, 0.05, 0.03)
Q6 = (
    (-0.12, 0.10, 0.015, 0.004, 0.00099, 0.00001),
    (0.02, -0.15, 0.11, 0.015, 0.004, 0.001),
    (0.002, 0.04, -0.17, 0.11, 0.015, 0.003),
    (0.0, 0.004, 0.06, -0.22, 0.14, 0.016),
    (0.0, 0.0, 0.005, 0.08, -0.30, 0.215),
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
)


@dataclass
class Scenario:
    """One cell of the null variant: a registered test, a generator and the arguments it is called with."""

    key: str                      # the simulation key of the committed document ("pd.binomial@null")
    test_id: str
    generator: Any
    generator_ref: str            # the key of the committed document's ``generators``
    feed: Callable | None = None
    test_kwargs: dict[str, Any] = field(default_factory=dict)


def credit_null_scenarios() -> list[Scenario]:
    """The 21 scenarios whose key ends in ``@null`` in the committed null variant, in the document's order."""
    port, port_rho = DefaultCounts(1000, 0.01), DefaultCounts(1000, 0.01, rho=0.12)
    grades = DefaultCounts(GR_N, GR_PD)
    logit, binorm = LogisticPortfolio(n=5000), BinormalScores(150, 4850, separation=1.2)
    pairs = BinormalScores(150, 4850, separation=1.2, challenger_separation=1.2)
    two = TwoSample(1000, 1000)
    mig = Migrations([500] * 7, break_monotonicity(decaying_matrix(7), 3, 1, 1.0))
    freq = GradeFrequencies(5000, P10)
    series = DefaultCounts.over_years([1000] * 5, [0.03] * 5)
    chain = RatingPaths(Q6, (1000,) * 5, horizon=5.0, snapshots=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0))
    reference = expm(np.asarray(Q6))
    return [
        Scenario("pd.binomial@null", "pd.binomial", port, "port-1000-1pct", feed_cell()),
        Scenario("pd.jeffreys@null", "pd.jeffreys", port, "port-1000-1pct", feed_cell()),
        Scenario("pd.binomial_vasicek@null", "pd.binomial_vasicek", port_rho, "port-1000-1pct-rho12", feed_cell(), {"rho": 0.12}),
        Scenario("pd.chi2_grades@null", "pd.chi2_grades", grades, "grades-7", feed_grades()),
        Scenario("pd.default_profile@null", "pd.default_profile", grades, "grades-7", feed_grades(), {"n_sim": 2000}),
        Scenario("pd.hosmer_lemeshow@null", "pd.hosmer_lemeshow", logit, "logistic-5000"),
        Scenario("pd.spiegelhalter@null", "pd.spiegelhalter", logit, "logistic-5000"),
        Scenario("pd.normal_multiperiod@null", "pd.normal_multiperiod", series, "series-5y-3pct", feed_series()),
        Scenario("pd.traffic_lights@null", "pd.traffic_lights", series, "series-5y-3pct", feed_series()),
        Scenario("disc.auc_vs_initial@null", "disc.auc_vs_initial", binorm, "binormal-150"),
        Scenario("disc.delong@null", "disc.delong", pairs, "binormal-150-pair"),
        Scenario("stability.psi@null", "stability.psi", two, "two-sample-1000"),
        Scenario("stability.csi@null", "stability.csi", two, "two-sample-1000"),
        Scenario("stability.chi2@null", "stability.chi2", two, "two-sample-1000"),
        Scenario("stability.ks@null", "stability.ks", two, "two-sample-1000"),
        Scenario("rating.migration_ztests@null", "rating.migration_ztests", mig, "migrations-7-500-boundary"),
        Scenario("rating.hhi@null", "rating.hhi", freq, "grades-10-5000"),
        Scenario("rating.time_homogeneity@null", "rating.time_homogeneity", chain, "paths-5x1000-5y",
                 lambda d: {"counts_by_period": [s["counts"] for s in d["steps"]]}),
        Scenario("rating.markov_order@null", "rating.markov_order", chain, "paths-5x1000-5y",
                 lambda d: {"triplets": d["triplets"]}),
        Scenario("rating.matrix_reference@null", "rating.matrix_reference", chain, "paths-5x1000-5y",
                 lambda d: {"counts": d["steps"][0]["counts"], "reference": reference}),
        Scenario("rating.momentum@null", "rating.momentum", chain, "paths-5x1000-5y",
                 lambda d: {"paths": d["segments"]}),
    ]


def committed_null() -> dict[str, Any]:
    return json.loads(NULL_DOC.read_text(encoding="utf-8"))


def check_against_document(scenarios: list[Scenario]) -> None:
    """Stop when a rebuilt generator differs from the configuration committed for the same scenario."""
    doc = committed_null()["outputs"]["generators"]
    for sc in scenarios:
        committed = doc[sc.generator_ref]
        rebuilt = {"name": sc.generator.name, "config": jsonable(sc.generator.config()["parameters"])}
        if rebuilt["name"] != committed["name"] or json.dumps(rebuilt["config"], sort_keys=True) != \
                json.dumps(committed["config"], sort_keys=True):
            raise SystemExit(f"{sc.key}: the rebuilt generator {sc.generator_ref} differs from the committed configuration")
