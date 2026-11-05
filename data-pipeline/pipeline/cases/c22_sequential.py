"""C22 beyond the state of the art (method tiers plan, BS-15, unit D15): sequential monitors against fixed-window tests read every day.

A fixed-window test (Kupiec, the Basel traffic light, the chi-square across grades) is valid when it is read once on a window fixed in
advance; a desk reads it every day. The engine's e-process monitors (``riskvalidation.validation.sequential``, 1.1.0) keep their size at
any stopping time (Ville's inequality: reject when the process reaches 1 / 0.05 = 20). This module runs them against the comparators on
the engine's own generators of known truth, with the case's seed, and states the plan's hypothesis with its measured numbers.

Two experiments, each deterministic under the case seed (one seed per scenario, ``derive_seed``):

1. VaR hits (generator ``VarHits``, alpha 1 %, 1,000 days, 2,000 series per scenario): the null, a hit rate 2, 3 and 4 times too high,
   and clustered hits at the right rate. Monitors: the rate e-process, the clustering e-process, their average (the battery).
   Comparators: Kupiec on the first 250 days (one reading), Kupiec on the trailing 250 days and on all days so far read every day, the
   Basel traffic light (first day with the trailing 250-day count outside the green zone), Christoffersen's independence test on the
   trailing 250 days read every day.
2. Defaults against PD by grade: five grades (PD 0.5 to 10 %), 2,000 obligors per grade and year, ten yearly steps, every PD multiplied
   by 1, 1.05, 1.1, 1.25, 1.5 and 2. Monitors: the e-process combined by product and by average. Comparators: the chi-square across the
   grades on the cumulative counts, read once at year 10 and read every year.

The verdict rules (``verdict``) are fixed before the run, from the plan (BS-15): H1 size, H2 detection delay, H3 power cost. The monitors
are not retuned after the run; a rule that fails is reported as failed. The plan's fourth clause (the delay against the traffic light on
C11's real windows) belongs to the C11 unit and is not judged here.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import special, stats

from ..core import text as tx
from .c22_studies import derive_seed

ALPHA, HORIZON, WINDOW, LEVEL = 0.01, 1000, 250, 0.05
N_REPS = 2000
#: the e-process rejects when it reaches 1 / LEVEL (Ville's inequality)
THRESHOLD = 1.0 / LEVEL
PD_BOOK = (0.005, 0.01, 0.02, 0.05, 0.10)
N_OBLIGORS, YEARS, BY_YEAR = 2000, 10, 3
PD_FACTORS = (1.0, 1.05, 1.1, 1.25, 1.5, 2.0)
#: the severities at which the plan judges the delay and the power cost ("severity 3 or more")
JUDGED = ("rate-x3", "rate-x4")
INF = math.inf
ENGINE = "riskvalidation.validation.sequential"

HIT_SCENARIOS: tuple[tuple[str, str, dict[str, float]], ...] = (
    ("null", "null", {}),
    ("rate-x2", "rate", {"rate_factor": 2.0}),
    ("rate-x3", "rate", {"rate_factor": 3.0}),
    ("rate-x4", "rate", {"rate_factor": 4.0}),
    ("cluster-0.1", "cluster", {"cluster": 0.1}),
    ("cluster-0.2", "cluster", {"cluster": 0.2}),
    ("cluster-0.4", "cluster", {"cluster": 0.4}),
)


def _t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


# ---------------------------------------------------------------------------------------------------------------------
# comparators and summaries (vectorised over the series)

def first_true(mask: np.ndarray, start: int = 0) -> np.ndarray:
    """The 1-based first column (day) at or after ``start`` where the row is true; infinity when it never is."""
    m = mask[:, start:]
    any_ = m.any(axis=1)
    idx = np.argmax(m, axis=1) + start + 1
    return np.where(any_, idx, INF).astype(float)


def summarise(days: np.ndarray, by: int) -> dict[str, Any]:
    """The fraction of series ever rejected, rejected by day ``by``, and the median first-rejection day (null when more than half never
    reject) and the median among the rejected series."""
    med = float(np.median(days))
    fin = np.isfinite(days)
    return {"ever": float(np.mean(fin)), "by": float(np.mean(days <= by)), "median_day": None if math.isinf(med) else med,
            "median_day_among_detected": float(np.median(days[fin])) if fin.any() else None}


def kupiec_reject(k: np.ndarray, t: np.ndarray, p: float, level: float = LEVEL) -> np.ndarray:
    """Kupiec's proportion-of-failures test: ``k`` exceptions in ``t`` days against the rate ``p``, true where p-value < level."""
    pi = np.where(t > 0, k / t, 0.0)
    lr = -2.0 * (special.xlogy(t - k, 1 - p) + special.xlogy(k, p) - special.xlogy(t - k, 1 - pi) - special.xlogy(k, pi))
    return stats.chi2.sf(np.maximum(lr, 0.0), 1) < level


def independence_reject(h: np.ndarray, window: int, level: float = LEVEL) -> np.ndarray:
    """Christoffersen's independence LR on the trailing ``window`` days, read every day from day ``window``."""
    a, b = h[:, :-1].astype(float), h[:, 1:].astype(float)
    pairs = {"00": (1 - a) * (1 - b), "01": (1 - a) * b, "10": a * (1 - b), "11": a * b}
    n_rows, n_cols = h.shape
    cs = {k: np.concatenate([np.zeros((n_rows, 1)), np.cumsum(v, axis=1)], axis=1) for k, v in pairs.items()}
    out = np.zeros((n_rows, n_cols), dtype=bool)
    w = window - 1
    with np.errstate(divide="ignore", invalid="ignore"):
        for t in range(window, n_cols + 1):
            n00, n01, n10, n11 = (cs[k][:, t - 1] - cs[k][:, t - 1 - w] for k in ("00", "01", "10", "11"))
            pi = (n01 + n11) / (n00 + n01 + n10 + n11)
            d0, d1 = n00 + n01, n10 + n11
            pi01 = np.divide(n01, d0, out=np.zeros_like(n01), where=d0 > 0)
            pi11 = np.divide(n11, d1, out=np.zeros_like(n11), where=d1 > 0)
            null = special.xlogy(n00 + n10, 1 - pi) + special.xlogy(n01 + n11, pi)
            alt = special.xlogy(n00, 1 - pi01) + special.xlogy(n01, pi01) + special.xlogy(n10, 1 - pi11) + special.xlogy(n11, pi11)
            lr = np.maximum(-2.0 * (null - alt), 0.0)
            out[:, t - 1] = (stats.chi2.sf(lr, 1) < level) & (lr > 0)
    return out


def basel_first_non_green(h: np.ndarray, window: int = WINDOW, coverage: float = 0.99) -> tuple[np.ndarray, int]:
    """The first day on which the trailing ``window``-day count of exceptions is outside the green zone (MAR32.9 at 99 %), per series,
    and the smallest non-green count; infinity when the series never leaves green. The engine's own zone function sets the count."""
    from riskvalidation.market import frtb

    k_min = next(k for k in range(window + 1) if frtb.traffic_light_zone(k, window, coverage) != "green")
    c = np.concatenate([np.zeros((h.shape[0], 1)), np.cumsum(h, axis=1)], axis=1)
    out = np.zeros(h.shape, dtype=bool)
    for t in range(window, h.shape[1] + 1):
        out[:, t - 1] = (c[:, t] - c[:, t - window]) >= k_min
    return first_true(out, window - 1), int(k_min)


# ---------------------------------------------------------------------------------------------------------------------
# the experiments

def run_hits(seed: int, reps: int = N_REPS, horizon: int = HORIZON) -> dict[str, Any]:
    """The VaR-hit experiment: ``reps`` series of ``horizon`` days per scenario, from the engine's generator ``VarHits``."""
    from riskvalidation.generators import VarHits
    from riskvalidation.validation.sequential import eprocess_battery, var_hit_clustering_eprocess, var_hit_eprocess

    out: dict[str, Any] = {"alpha": ALPHA, "horizon": horizon, "window": WINDOW, "by_day": WINDOW, "reps": reps,
                           "generator": "VarHits", "scenarios": []}
    days = np.arange(1, horizon + 1, dtype=float)
    cross = -math.log(LEVEL)
    for sid, kind, kw in HIT_SCENARIOS:
        gen = VarHits(t=horizon, alpha=ALPHA, with_var=False, **kw)
        rng = np.random.default_rng(derive_seed(seed, f"sequential:hits:{sid}"))
        h = np.array([gen.draw(rng)["hits"] for _ in range(reps)])
        rate_r = [var_hit_eprocess(x, ALPHA) for x in h]
        clus_r = [var_hit_clustering_eprocess(x, ALPHA) for x in h]
        rate = np.array([r.log_e for r in rate_r])
        clus = np.array([r.log_e for r in clus_r])
        bat = np.array([eprocess_battery({"rate": a, "cluster": b}).log_e for a, b in zip(rate_r, clus_r)])
        c = np.cumsum(h, axis=1).astype(float)
        c0 = np.concatenate([np.zeros((reps, 1)), c], axis=1)
        trailing = c0[:, WINDOW:] - c0[:, :-WINDOW]
        kup_trail = np.zeros((reps, horizon), dtype=bool)
        kup_trail[:, WINDOW - 1:] = kupiec_reject(trailing, np.full(trailing.shape, float(WINDOW)), ALPHA)
        kup_cum = kupiec_reject(c, np.broadcast_to(days, c.shape), ALPHA)
        kup_cum[:, :49] = False
        tl_days, k_min = basel_first_non_green(h)
        one_shot = kupiec_reject(c[:, WINDOW - 1], np.full(reps, float(WINDOW)), ALPHA)
        out["scenarios"].append({
            "id": sid, "kind": kind, "factor": kw.get("rate_factor"), "cluster": kw.get("cluster"), "label": hit_label(sid, kw),
            "e_rate": summarise(first_true(rate >= cross), WINDOW),
            "e_cluster": summarise(first_true(clus >= cross), WINDOW),
            "e_battery": summarise(first_true(bat >= cross), WINDOW),
            "kupiec_trailing": summarise(first_true(kup_trail), WINDOW),
            "kupiec_cumulative": summarise(first_true(kup_cum), WINDOW),
            "traffic_light": summarise(tl_days, WINDOW),
            "independence_trailing": summarise(first_true(independence_reject(h, WINDOW)), WINDOW),
            "kupiec_one_shot_power": float(one_shot.mean()),
        })
    out["traffic_light_exceptions"] = k_min
    return out


def run_pd(seed: int, reps: int = N_REPS) -> dict[str, Any]:
    """The PD-book experiment: ``reps`` ten-year books per PD factor, the e-process by grade combined two ways against the chi-square."""
    from riskvalidation.validation.sequential import detection_time, pd_grade_eprocess

    pd = np.array(PD_BOOK)
    out: dict[str, Any] = {"pd": list(PD_BOOK), "obligors_per_grade_year": N_OBLIGORS, "years": YEARS, "by_year": BY_YEAR, "reps": reps,
                           "scenarios": []}
    n = np.full((YEARS, pd.size), float(N_OBLIGORS))
    for factor in PD_FACTORS:
        rng = np.random.default_rng(derive_seed(seed, f"sequential:pd:{factor:g}"))
        d = rng.binomial(N_OBLIGORS, np.minimum(pd * factor, 0.999), size=(reps, YEARS, pd.size)).astype(float)
        prod, avg = [], []
        for r in range(reps):
            prod.append(detection_time(pd_grade_eprocess(d[r], n, pd, combine="product").log_e) or INF)
            avg.append(detection_time(pd_grade_eprocess(d[r], n, pd, combine="average").log_e) or INF)
        cum_d, cum_n = np.cumsum(d, axis=1), np.cumsum(np.broadcast_to(n, d.shape), axis=1)
        chi2 = (((cum_d - cum_n * pd) ** 2) / (cum_n * pd * (1 - pd))).sum(axis=2)
        rej = stats.chi2.sf(chi2, pd.size) < LEVEL
        out["scenarios"].append({
            "id": f"pd-x{factor:g}", "factor": factor, "label": pd_label(factor),
            "e_product": summarise(np.array(prod), BY_YEAR), "e_average": summarise(np.array(avg), BY_YEAR),
            "chi2_one_shot_power": float(rej[:, -1].mean()), "chi2_every_year": summarise(first_true(rej), BY_YEAR),
        })
    return out


# ---------------------------------------------------------------------------------------------------------------------
# the verdict rules (written before the run)

def _scenario(hits: dict[str, Any], sid: str) -> dict[str, Any]:
    return next(s for s in hits["scenarios"] if s["id"] == sid)


def verdict(hits: dict[str, Any]) -> dict[str, Any]:
    """The plan's hypothesis on the VaR-hit experiment, as three rules fixed before the run.

    H1 size: the rate e-process rejects a correct model in at most 5 % plus three Monte Carlo standard errors of the series over the
       horizon, read every day, while Kupiec read every day (trailing or growing window) rejects more than that.
    H2 delay: at a hit rate 3 and 4 times too high the median first-rejection day of the rate e-process is below the 250-day window and
       below the traffic light's (an undetected series counts as never).
    H3 power cost: at those two factors the power of one Kupiec reading at 250 days minus the e-process's rejection by day 250 is below
       10 points.
    The hypothesis holds when the three hold. The plan's refutation clause on C11's real windows is judged by the C11 unit."""
    reps = hits["reps"]
    bound = LEVEL + 3.0 * math.sqrt(LEVEL * (1.0 - LEVEL) / reps)
    null = _scenario(hits, "null")
    size_e = null["e_rate"]["ever"]
    size_kt, size_kc = null["kupiec_trailing"]["ever"], null["kupiec_cumulative"]["ever"]
    h1 = size_e <= bound and max(size_kt, size_kc) > bound
    h2 = h3 = True
    detail: dict[str, Any] = {}
    for sid in JUDGED:
        s = _scenario(hits, sid)
        e_med, tl_med = s["e_rate"]["median_day"], s["traffic_light"]["median_day"]
        ok2 = e_med is not None and e_med < WINDOW and (tl_med is None or e_med < tl_med)
        cost = s["kupiec_one_shot_power"] - s["e_rate"]["by"]
        ok3 = cost < 0.10
        h2, h3 = h2 and ok2, h3 and ok3
        detail[sid] = {"e_median_day": e_med, "traffic_light_median_day": tl_med, "H2": ok2,
                       "kupiec_power_250": s["kupiec_one_shot_power"], "e_power_by_250": s["e_rate"]["by"], "power_cost": cost,
                       "H3": ok3}
    return {"H1_size": {"holds": h1, "e_process_size": size_e, "kupiec_trailing_size": size_kt, "kupiec_cumulative_size": size_kc,
                        "bound": bound},
            "H2_delay": {"holds": h2}, "H3_power_cost": {"holds": h3}, "detail": detail, "holds": bool(h1 and h2 and h3)}


# ---------------------------------------------------------------------------------------------------------------------
# texts

def _num(x: float, d: int = 1) -> dict[str, str]:
    return tx.bi_number(x, d)


def _pc(x: float, d: int = 1) -> dict[str, str]:
    return tx.bi_percent(x, d)


def _both(f) -> dict[str, str]:
    return {lang: f(lang) for lang in ("en", "es")}


def hit_label(sid: str, kw: dict[str, float]) -> dict[str, str]:
    if sid == "null":
        return _t("The model is right: hits at the VaR's own 1 % rate", "El modelo es correcto: excepciones a la tasa propia del VaR, 1 %")
    if "rate_factor" in kw:
        k = kw["rate_factor"]
        return _both(lambda lang: (f"Hits {tx.number(k, 0, lang='en')} times too frequent ({tx.number(k, 0, lang='en')} % against 1 %)" if lang == "en"
                                   else f"Excepciones {tx.number(k, 0, lang='es')} veces más frecuentes ({tx.number(k, 0, lang='es')} % contra 1 %)"))
    q = kw["cluster"]
    return _both(lambda lang: (f"Right rate, hits cluster: P(hit after a hit) = {tx.number(q, 1, lang='en')}" if lang == "en"
                               else f"Tasa correcta, excepciones agrupadas: P(excepción tras excepción) = {tx.number(q, 1, lang='es')}"))


def pd_label(factor: float) -> dict[str, str]:
    if factor == 1.0:
        return _t("Every PD right", "Todas las PD correctas")
    return _both(lambda lang: (f"Every true PD is {tx.number(factor, 2 if factor in (1.05, 1.25) else 1, lang='en')} times the predicted one" if lang == "en"
                               else f"Toda PD verdadera es {tx.number(factor, 2 if factor in (1.05, 1.25) else 1, lang='es')} veces la predicha"))


def method_block(engine_version: str) -> dict[str, Any]:
    return {
        "engine": ENGINE, "engine_version": engine_version, "alpha_level": LEVEL, "threshold": THRESHOLD,
        "monitors": ["sequential.var_hits", "sequential.var_hit_clustering", "sequential.battery", "sequential.pd_grades"],
        "label": _t("E-process sequential monitors", "Monitores secuenciales de procesos e"),
        "description": _t(
            "A betting e-process starts at 1 and has expected value at most 1 under the null at every stopping time; the monitor rejects "
            "the first time it reaches 20 (Ville's inequality), so its size is at most 5 % however often it is read. The VaR monitors bet "
            "on the hit rate and on hit clustering, the PD monitor on a multiplicative miscalibration of each grade, and the grades combine "
            "by product (independent grades) or by average (valid whatever the dependence).",
            "Un proceso e de apuesta parte en 1 y tiene valor esperado a lo más 1 bajo la nula en todo tiempo de parada; el monitor rechaza "
            "la primera vez que llega a 20 (desigualdad de Ville), por lo que su tamaño es a lo más 5 % sin importar cuán seguido se lea. "
            "Los monitores de VaR apuestan por la tasa de excepciones y por su agrupamiento, el de PD por una descalibración multiplicativa "
            "de cada grado, y los grados se combinan por producto (grados independientes) o por promedio (válido con cualquier dependencia)."),
    }


def hypotheses(v: dict[str, Any], hits: dict[str, Any]) -> list[dict[str, Any]]:
    """H1 to H3 as the document states them: the rule, what was measured and whether it holds."""
    reps = hits["reps"]
    h1, d = v["H1_size"], v["detail"]
    x3, x4 = d["rate-x3"], d["rate-x4"]
    p = lambda x, k=1: _pc(x, k)  # noqa: E731
    day = lambda x, lang: ("never" if lang == "en" else "nunca") if x is None else tx.number(x, 0, lang=lang)  # noqa: E731
    return [
        {"id": "H1", "holds": bool(h1["holds"]),
         "rule": _t("Size: read every day over 1,000 days, the e-process rejects a correct VaR in at most 5 % plus three standard errors of "
                    "the series, and Kupiec read every day rejects more.",
                    "Tamaño: leído todos los días durante 1.000 días, el proceso e rechaza un VaR correcto en a lo más 5 % más tres errores "
                    "estándar de las series, y Kupiec leído todos los días rechaza más."),
         "measured": _both(lambda lang: (
             f"E-process {p(h1['e_process_size'])[lang]}; Kupiec on the trailing 250 days {p(h1['kupiec_trailing_size'])[lang]}, on all days so far "
             f"{p(h1['kupiec_cumulative_size'])[lang]}; bound {p(h1['bound'])[lang]}; {tx.number(reps, 0, lang=lang)} series."
             if lang == "en" else
             f"Proceso e {p(h1['e_process_size'])[lang]}; Kupiec en los últimos 250 días {p(h1['kupiec_trailing_size'])[lang]}, en todos los días "
             f"hasta la fecha {p(h1['kupiec_cumulative_size'])[lang]}; cota {p(h1['bound'])[lang]}; {tx.number(reps, 0, lang=lang)} series.")),
         "values": [{"id": "e_process_size", "value": h1["e_process_size"]}, {"id": "kupiec_trailing_size", "value": h1["kupiec_trailing_size"]},
                    {"id": "kupiec_cumulative_size", "value": h1["kupiec_cumulative_size"]}, {"id": "bound", "value": h1["bound"]}]},
        {"id": "H2", "holds": bool(v["H2_delay"]["holds"]),
         "rule": _t("Delay: at a hit rate 3 and 4 times too high the median detection day of the e-process is below 250 and below the "
                    "traffic light's.",
                    "Retardo: con una tasa de excepciones 3 y 4 veces mayor la mediana del día de detección del proceso e es menor que 250 y "
                    "menor que la del semáforo."),
         "measured": _both(lambda lang: (
             f"Factor 3: day {day(x3['e_median_day'], lang)} against {day(x3['traffic_light_median_day'], lang)}; factor 4: day "
             f"{day(x4['e_median_day'], lang)} against {day(x4['traffic_light_median_day'], lang)}. The light cannot speak before day 250."
             if lang == "en" else
             f"Factor 3: día {day(x3['e_median_day'], lang)} contra {day(x3['traffic_light_median_day'], lang)}; factor 4: día "
             f"{day(x4['e_median_day'], lang)} contra {day(x4['traffic_light_median_day'], lang)}. El semáforo no puede hablar antes del día 250.")),
         "values": [{"id": "x3_e_median_day", "value": x3["e_median_day"]}, {"id": "x3_traffic_light_median_day", "value": x3["traffic_light_median_day"]},
                    {"id": "x4_e_median_day", "value": x4["e_median_day"]}, {"id": "x4_traffic_light_median_day", "value": x4["traffic_light_median_day"]}]},
        {"id": "H3", "holds": bool(v["H3_power_cost"]["holds"]),
         "rule": _t("Power cost: at those two factors one Kupiec reading at 250 days has less than 10 points more power than the e-process "
                    "has by day 250.",
                    "Costo de potencia: con esos dos factores una lectura de Kupiec a los 250 días tiene menos de 10 puntos más de potencia "
                    "que el proceso e al día 250."),
         "measured": _both(lambda lang: (
             f"Factor 3: {p(x3['kupiec_power_250'])[lang]} against {p(x3['e_power_by_250'])[lang]}, {_num(100 * x3['power_cost'])[lang]} points; factor 4: "
             f"{p(x4['kupiec_power_250'])[lang]} against {p(x4['e_power_by_250'])[lang]}, {_num(100 * x4['power_cost'])[lang]} points."
             if lang == "en" else
             f"Factor 3: {p(x3['kupiec_power_250'])[lang]} contra {p(x3['e_power_by_250'])[lang]}, {_num(100 * x3['power_cost'])[lang]} puntos; factor 4: "
             f"{p(x4['kupiec_power_250'])[lang]} contra {p(x4['e_power_by_250'])[lang]}, {_num(100 * x4['power_cost'])[lang]} puntos.")),
         "values": [{"id": "x3_power_cost", "value": x3["power_cost"]}, {"id": "x4_power_cost", "value": x4["power_cost"]}]},
    ]


def verdict_block(v: dict[str, Any]) -> dict[str, Any]:
    held = [k for k, ok in (("H1", v["H1_size"]["holds"]), ("H2", v["H2_delay"]["holds"]), ("H3", v["H3_power_cost"]["holds"])) if ok]
    failed = [k for k in ("H1", "H2", "H3") if k not in held]
    x3 = v["detail"]["rate-x3"]
    if v["holds"]:
        text = _t("The hypothesis holds on C22's generators: anytime-valid size, a detection day below the traffic light's and a power cost "
                  "under 10 points.",
                  "La hipótesis se sostiene en los generadores de C22: tamaño válido en todo momento, un día de detección menor que el del "
                  "semáforo y un costo de potencia menor que 10 puntos.")
    else:
        text = _both(lambda lang: (
            f"The hypothesis does not hold as stated: {', '.join(failed)} failed ({', '.join(held) or 'none'} held). At a hit rate 3 times too high "
            f"the e-process loses {_num(100 * x3['power_cost'])['en']} points of power at 250 days against one Kupiec reading. Reported as measured; "
            f"the monitors were not retuned."
            if lang == "en" else
            f"La hipótesis no se sostiene tal como se planteó: fallaron {', '.join(failed)} ({', '.join(held) or 'ninguna'} se sostuvo). Con una tasa "
            f"de excepciones 3 veces mayor el proceso e pierde {_num(100 * x3['power_cost'])['es']} puntos de potencia a los 250 días frente a una "
            f"lectura de Kupiec. Se informa lo medido; los monitores no se reajustaron."))
    return {"holds": v["holds"], "held": held, "failed": failed, "text": text,
            "scope": _t("Judged on C22's generators only. The plan's clause on C11's real windows is judged in C11.",
                        "Juzgada solo en los generadores de C22. La cláusula del plan sobre las ventanas reales de C11 se juzga en C11.")}


def build_block(seed: int, engine_version: str, reps: int = N_REPS, horizon: int = HORIZON) -> dict[str, Any]:
    """The ``sequential`` block of the other-families variant: the method, both experiments, the three hypotheses and the verdict."""
    hits = run_hits(seed, reps, horizon)
    pd = run_pd(seed, reps)
    v = verdict(hits)
    return {"method": method_block(engine_version), "seed": int(seed), "hits": hits, "pd_grades": pd, "hypotheses": hypotheses(v, hits),
            "verdict": verdict_block(v)}


def impact_items(block: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The impact entries of the block (``other_seq_*``): the numbers the hypothesis is judged on."""
    v = verdict(block["hits"])
    h1, d3 = v["H1_size"], v["detail"]["rate-x3"]

    def item(value: float | None, unit: str, en: str, es: str) -> dict[str, Any]:
        return {"value": value, "unit": unit, "label": _t(en, es)}

    return {
        "other_seq_size_e_process": item(h1["e_process_size"], "probability",
                                         "Rate e-process: share of correct VaR series ever rejected, read every day over 1,000 days",
                                         "Proceso e de la tasa: parte de las series de VaR correcto alguna vez rechazadas, leído todos los días en 1.000 días"),
        "other_seq_size_kupiec_trailing": item(h1["kupiec_trailing_size"], "probability",
                                               "Kupiec on the trailing 250 days read every day: share of correct VaR series ever rejected",
                                               "Kupiec en los últimos 250 días leído todos los días: parte de las series de VaR correcto alguna vez rechazadas"),
        "other_seq_delay_x3": item(d3["e_median_day"], "days",
                                   "Rate e-process: median detection day at a hit rate 3 times too high",
                                   "Proceso e de la tasa: día mediano de detección con una tasa de excepciones 3 veces mayor"),
        "other_seq_power_cost_x3": item(d3["power_cost"], "probability",
                                        "Power of one Kupiec reading at 250 days minus the e-process's by day 250, hit rate 3 times too high",
                                        "Potencia de una lectura de Kupiec a los 250 días menos la del proceso e al día 250, tasa 3 veces mayor"),
    }


def values(block: dict[str, Any]) -> dict[str, float]:
    """The scalars the expected ranges judge."""
    v = verdict(block["hits"])
    return {"seq_e_process_size": v["H1_size"]["e_process_size"], "seq_kupiec_trailing_size": v["H1_size"]["kupiec_trailing_size"]}
