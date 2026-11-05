"""C03 beyond the state of the art (method tiers plan, BS-15, unit D15): the e-process monitor of defaults against the predicted PD by age.

The case reads each vintage once, at its 5-year mark. A desk reads a vintage every year of its life. The engine's
``pd_grade_eprocess`` (``riskvalidation.validation.sequential``, 1.1.0) is fed the vintages of a cohort as its grades and the ages 12 to 60
months as its steps: at each age the defaults of the interval (the increment of the observed cumulative curve times the vintage's loans, a
whole number) against the interval PD (the increment of the predicted cumulative curve). The direction is upper: the monitor looks for a
vintage that defaults more than predicted, the case a validator is paid to find. It rejects the first time the process reaches 20
(Ville: anytime-valid size 5 %). The vintages combine by average (an e-process whatever their dependence, the headline: the vintages of
a cohort share the economy) and by product (independent vintages), both reported.

The builder is a pure function of the vintage curves and the fixed-window rows of the document: nothing is read from the loan file, so it is
the same computation on the committed curves as in the bake. The binomial null has no asset correlation, like the ``pd.binomial`` row it
sits beside; the plan's evaluation on C03 is an illustration on the committed curves (a handful of vintages per cohort), not a power study.
"""
from __future__ import annotations

import importlib.metadata as md
import math
from typing import Any

import numpy as np

from ...core import text as tx

ALPHA_LEVEL = 0.05
THRESHOLD = 1.0 / ALPHA_LEVEL
ENGINE = "riskvalidation.validation.sequential"
DIRECTION = "upper"
HEADLINE = "average"
#: the fixed-window row each vintage's 5-year reading is taken from (the champion's binomial test on the vintage)
FIXED_TEST = "pd.binomial"


def interval_counts(curve: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The defaults, the loans at risk and the predicted PD of each age interval of a vintage's curve.

    The observed cumulative curve is a count over the vintage's loans, so its increments times ``n`` are whole numbers; an age that is
    not observed has no loans and no defaults (it contributes a factor 1 to the e-process)."""
    n_loans = float(curve["n"])
    pred = np.asarray(curve["predicted_cumulative_pd"], dtype=float)
    p = np.diff(np.concatenate([[0.0], pred]))
    d = np.zeros(pred.size)
    n = np.zeros(pred.size)
    prev = 0.0
    for k, o in enumerate(curve["observed_cumulative_pd"]):
        if o is None:
            break
        d[k] = round((float(o) - prev) * n_loans)
        n[k] = n_loans
        prev = float(o)
    return d, n, np.clip(p, 1e-9, 1.0 - 1e-9)


def _path(log_e: np.ndarray, observed: np.ndarray) -> list[float | None]:
    return [round(float(v), 6) if obs else None for v, obs in zip(log_e, observed)]


def _month(step: int | None, months: list[int]) -> int | None:
    return None if step is None else int(months[step - 1])


def _text(b: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    last = b["months"][-1]
    m = b[HEADLINE]["rejection_month"]
    mp = b["product"]["rejection_month"]
    n_rej = sum(v["rejection_month"] is not None for v in b["vintages"])
    n_v = len(b["vintages"])
    if m is not None:
        en = (f"Read at every age, the e-process first rejects this cohort at month {m}, {last - m} months before the {last}-month mark at which the "
              f"fixed-window tests read; {n_rej} of {n_v} vintages reject on their own (the product of the vintages rejects at month {mp}).")
        es = (f"Leído en cada edad, el proceso e rechaza esta cohorte por primera vez en el mes {m}, {last - m} meses antes de la marca de {last} meses "
              f"en que leen las pruebas de ventana fija; {n_rej} de {n_v} cosechas rechazan por sí solas (el producto de las cosechas rechaza en el mes {mp}).")
    else:
        top = b[HEADLINE]["max_log_e"]
        dd, pp = sum(v["defaults"] for v in b["vintages"]), sum(v["predicted_defaults"] for v in b["vintages"])
        en = (f"Read at every age, the e-process never reaches 20 for this cohort: the largest log value of the average is {tx.number(top, 1, lang='en')} "
              f"(20 is log {tx.number(math.log(THRESHOLD), 1, lang='en')}). Over the observed ages the cohort has {tx.number(dd, 0, lang='en')} charge-offs "
              f"against {tx.number(pp, 0, lang='en')} predicted, so a monitor looking for under-prediction has little to say. "
              f"{n_rej} of {n_v} vintages reject on their own.")
        es = (f"Leído en cada edad, el proceso e nunca llega a 20 para esta cohorte: el mayor valor logarítmico del promedio es {tx.number(top, 1, lang='es')} "
              f"(20 es log {tx.number(math.log(THRESHOLD), 1, lang='es')}). En las edades observadas la cohorte tiene {tx.number(dd, 0, lang='es')} castigos "
              f"contra {tx.number(pp, 0, lang='es')} predichos, así que un monitor que busca subestimación tiene poco que decir. "
              f"{n_rej} de {n_v} cosechas rechazan por sí solas.")
    early = [v for v in b["vintages"] if v["rejection_month"] is not None and v["five_year_light"] == "green" and v["defaults"] < v["predicted_defaults"]]
    if early:
        fy = ", ".join(f"FY{v['fiscal_year']}" for v in early)
        fye = ", ".join(f"AF{v['fiscal_year']}" for v in early)
        en += (f" {fy} rejects although its 5-year binomial light is green: the early ages default faster than the predicted curve while the total ends "
               f"below it, a defect of the curve's timing that the single reading at the mark does not see.")
        es += (f" {fye} rechaza aunque su luz binomial a 5 años es verde: las primeras edades incumplen más rápido que la curva predicha mientras el total "
               f"termina bajo ella, un defecto del calendario de la curva que la lectura única en la marca no ve.")
    limits = {
        "en": "The null is a binomial with no asset correlation, like the binomial row beside it, so a rejection can also reflect the correlation of the "
              "vintage's loans. The vintages of a cohort share the economy: the average is the valid combination, the product assumes they are independent. "
              "A cohort has two to three vintages: this is an illustration on the committed curves, not a measure of power. Loans observed for less than the "
              "age without a charge-off count as non-events, as in the curves.",
        "es": "La nula es una binomial sin correlación de activos, como la fila binomial vecina, así que un rechazo puede reflejar también la correlación "
              "de los créditos de la cosecha. Las cosechas de una cohorte comparten la economía: el promedio es la combinación válida, el producto supone "
              "que son independientes. Una cohorte tiene de dos a tres cosechas: es una ilustración sobre las curvas versionadas, no una medida de potencia. "
              "Los créditos observados menos que la edad sin castigo cuentan como no eventos, igual que en las curvas.",
    }
    return {"en": en, "es": es}, limits


def build(curves: list[dict[str, Any]], tests: list[dict[str, Any]], champion: str) -> dict[str, Any]:
    """The ``sequential`` block of a cohort document: the e-process of every vintage and of the cohort, read at every age.

    ``curves`` are the document's ``vintage_curves``; ``tests`` its rows (the champion's binomial row of each vintage gives the 5-year
    light the monitor is set beside). A cohort with no observed age is refused."""
    from riskvalidation.validation.sequential import detection_time, pd_grade_eprocess

    months = [int(m) for m in curves[0]["months"]]
    if any([int(m) for m in c["months"]] != months for c in curves):
        raise ValueError("the vintages of a cohort share the same ages")
    parts = [interval_counts(c) for c in curves]
    if not any(n.sum() > 0 for _, n, _ in parts):
        raise ValueError("no vintage of the cohort has an observed age: nothing to monitor")
    d = np.stack([q[0] for q in parts], axis=1)
    n = np.stack([q[1] for q in parts], axis=1)
    p = np.stack([q[2] for q in parts], axis=1)
    grades = [str(c["fiscal_year"]) for c in curves]
    observed = n.sum(axis=1) > 0
    res = {c: pd_grade_eprocess(d, n, p, direction=DIRECTION, combine=c, grades=grades, alpha_level=ALPHA_LEVEL)
           for c in ("average", "product")}
    light = {r["segment"]: r["light"] for r in tests if r["test_id"] == FIXED_TEST and r["model_id"] == champion}
    step_months = months[1] - months[0]
    vint = []
    for j, c in enumerate(curves):
        g = res[HEADLINE].grade_log_e[:, j]
        obs_j = n[:, j] > 0
        rej = _month(detection_time(g, ALPHA_LEVEL), months) if obs_j.any() else None
        vint.append({"fiscal_year": int(c["fiscal_year"]), "n": int(c["n"]), "months_observed": int(obs_j.sum()) * step_months,
                     "defaults": int(d[:, j].sum()), "predicted_defaults": round(float((n[:, j] * p[:, j]).sum()), 2),
                     "rejection_month": rej, "max_log_e": round(float(g[obs_j].max()), 6) if obs_j.any() else None,
                     "log_e": _path(g, obs_j), "five_year_light": light.get(f"fy{c['fiscal_year']}"),
                     "months_before_the_mark": None if rej is None else months[-1] - rej})
    out: dict[str, Any] = {
        "engine": ENGINE, "engine_version": md.version("riskvalidation"), "alpha_level": ALPHA_LEVEL, "threshold": THRESHOLD,
        "direction": DIRECTION, "headline": HEADLINE, "months": months, "vintages": vint,
    }
    for k in ("average", "product"):
        r = res[k]
        out[k] = {"log_e": _path(r.log_e, observed), "rejection_month": _month(r.rejection_time, months),
                  "anytime_p_value": round(float(r.anytime_p_value), 12), "max_log_e": round(float(r.log_e[observed].max()), 6)}
    out["reading"], out["limits"] = _text(out)
    return out
