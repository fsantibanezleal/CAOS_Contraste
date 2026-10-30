"""BS-13, the beyond tier of C13: a scale-and-level complement to the FRTB P&L attribution test.

The regulatory PLA (Spearman of the levels, Kolmogorov-Smirnov of the distributions) is blind to a risk model that uses a 20-day-old
volatility: 0.0 percent amber or red in 1,000 replications. The engine (``riskvalidation.market.pla_complement``, 1.1.0, tier beyond)
adds three statistics on the same 250-day pair and a decision calibrated to a stated type I error: the Mincer-Zarnowitz Wald test of
``(a, b) = (0, 1)``, the Spearman correlation of ``|HPL|`` and ``|RTPL|`` and that of their 20-day rolling means. This module is the
product's side: it simulates the null from the C13 generator, calls the engine's calibration and decision, counts the flags on the six
variants and on a lag ladder, and states the verdict of the plan's hypothesis whatever it is. It computes no statistic and no
threshold itself (CT-1305): the statistics, the critical values and the flags are return values of the engine. The complement is added
to the regulatory zone, never substituted for it, and has no regulatory standing.

Fixed before the run and not tuned (the plan, section 4, BS-13): window 20 days, size 1 percent, a null of ten blocks of independent
desk-years of the ``none`` variant under case seeds that meet none of the committed ones, a lag ladder of 5, 10, 20 and 40 days.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.market import frtb
from riskvalidation.market import pla_complement as pc

from ...core.text import number, percent
from . import generator, params
from . import measure as ms

PLAN_ID = "BS-13"
ENGINE_FUNCTION = "riskvalidation.market.pla_complement"
WINDOW = 20
SIZE = 0.01
CORRECTION = "bonferroni"
NULL_CASE_SEEDS = tuple(range(5013, 5023))      # ten null blocks; the committed bake uses case seed 13
MIN_NULL_BLOCK = 100                            # the smallest block that lets a 0.1 percent size resolve (ten blocks, 1,000 desk-years)
LAGS = (5, 10, 20, 40)
SIZES = (0.001, 0.005, 0.01, 0.02, 0.05)
HOLDS_POWER = 0.30                              # the plan: at a size of at most 1 percent the stale-volatility model is flagged in 30 percent
REFUTED_POWER = 0.10                            # refuted below 10 percent
FIELDS = ("wald", "spearman_abs", "spearman_roll")
_FLAG = {"wald": "flag_wald", "spearman_abs": "flag_spearman_abs", "spearman_roll": "flag_spearman_roll"}


def T(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


def verdict(power: float, size: float) -> str:
    """The plan's verdict: ``holds`` at a power of 30 percent or more with the held-out size at most 1 percent, ``refuted`` below a
    power of 10 percent, ``not-established`` otherwise (the power in between, or a size above the limit)."""
    if power < REFUTED_POWER:
        return "refuted"
    return "holds" if power >= HOLDS_POWER and size <= SIZE else "not-established"


def rate(k: int, n: int) -> dict[str, Any]:
    lo, hi = ms.wilson(int(k), int(n))
    return {"k": int(k), "n": int(n), "rate": k / n, "ci_low": lo, "ci_high": hi}


def n_per_block(n_replications: int) -> int:
    return max(int(n_replications), MIN_NULL_BLOCK)


def statistics_of(hpl: np.ndarray, rtpl: np.ndarray) -> list[pc.PLAComplementStatistics]:
    """The engine's three statistics on each replication (rows of ``hpl`` and ``rtpl``)."""
    return [pc.pla_complement_statistics(h, r, WINDOW) for h, r in zip(hpl, rtpl, strict=True)]


def measurement_statistics(m: ms.Measurement) -> list[pc.PLAComplementStatistics]:
    return statistics_of(m.hpl_all.reshape(m.n, params.WINDOW_DAYS), m.rtpl_all.reshape(m.n, params.WINDOW_DAYS))


@dataclass
class Calibration:
    """The critical values of the complement, from the engine's calibration on a null simulated from the generator."""

    n_per_block: int
    null: list[pc.PLAComplementStatistics]
    per_statistic: pc.PLAComplementThresholds       # 1 percent for each statistic
    family: pc.PLAComplementThresholds              # 1 percent for the union (Bonferroni)

    def at(self, size: float) -> pc.PLAComplementThresholds:
        return pc.pla_complement_calibrate(self.null, size, "none")


def calibrate(n_replications: int) -> Calibration:
    """Simulate the null (the ``none`` variant under each null case seed) and calibrate the thresholds with the engine."""
    nb = n_per_block(n_replications)
    null: list[pc.PLAComplementStatistics] = []
    for cs in NULL_CASE_SEEDS:
        for i in range(nb):
            rep = generator.replicate("none", i, cs)
            null.append(pc.pla_complement_statistics(rep.hpl, rep.rtpl, WINDOW))
    return Calibration(nb, null, pc.pla_complement_calibrate(null, SIZE, "none"), pc.pla_complement_calibrate(null, SIZE, CORRECTION))


def _flags(stats: list[pc.PLAComplementStatistics], th: pc.PLAComplementThresholds) -> dict[str, np.ndarray]:
    dec = [pc.pla_complement_decide(s, th) for s in stats]
    out = {f: np.array([getattr(d, _FLAG[f]) for d in dec], dtype=bool) for f in FIELDS}
    out["any"] = np.array([d.flagged for d in dec], dtype=bool)
    return out


def _rates(flags: dict[str, np.ndarray]) -> dict[str, dict[str, Any]]:
    return {k: rate(int(v.sum()), v.size) for k, v in flags.items()}


def _flag_block(stats: list[pc.PLAComplementStatistics], zones: list[str], cal: Calibration) -> dict[str, Any]:
    plain, fam = _flags(stats, cal.per_statistic), _flags(stats, cal.family)
    pla = np.array([z != "green" for z in zones], dtype=bool)
    return {"per_statistic": _rates(plain), "family": _rates(fam), "pla_amber_or_red": rate(int(pla.sum()), pla.size),
            "family_with_pla": rate(int((fam["any"] | pla).sum()), pla.size)}


def _thresholds(th: pc.PLAComplementThresholds) -> dict[str, float]:
    return {"wald": th.wald, "spearman_abs": th.spearman_abs, "spearman_roll": th.spearman_roll}


def lag_ladder(cal: Calibration, n: int, case_seed: int) -> list[dict[str, Any]]:
    """The stale-volatility variant at each lag of the ladder, on the committed seeds: the regulatory zone and the complement."""
    rows = []
    for lag in LAGS:
        stats, zones = [], []
        for i in range(n):
            rep = generator.replicate("stale-volatility", i, case_seed, vol_lag_days=float(lag))
            stats.append(pc.pla_complement_statistics(rep.hpl, rep.rtpl, WINDOW))
            zones.append(frtb.pla_zone(frtb.pla_spearman(rep.hpl, rep.rtpl), frtb.pla_ks(rep.hpl, rep.rtpl)))
        b = _flag_block(stats, zones, cal)
        rows.append({"lag_days": lag, "per_statistic": b["per_statistic"], "family_any": b["family"]["any"],
                     "pla_amber_or_red": b["pla_amber_or_red"]})
    return rows


def _by_size(stats: list[pc.PLAComplementStatistics], held: list[pc.PLAComplementStatistics], cal: Calibration) -> list[dict[str, Any]]:
    rows = []
    for size in SIZES:
        th = cal.at(size)
        power, null = _flags(stats, th), _flags(held, th)
        rows.append({"size": size, **{f: rate(int(power[f].sum()), power[f].size) for f in FIELDS},
                     **{f + "_held_out": rate(int(null[f].sum()), null[f].size) for f in FIELDS}})
    return rows


def _p(x: float, lang: str) -> str:
    return percent(x, 1, lang=lang)


def _n(x: int) -> str:
    return number(x, 0, lang="es")


def hypothesis_block(flags: dict[str, Any], held_out: dict[str, Any], n_null: int) -> dict[str, Any]:
    power, size = flags["family"]["spearman_roll"], held_out["family"]["spearman_roll"]
    v = verdict(power["rate"], size["rate"])
    plain = flags["per_statistic"]["spearman_roll"]
    pla = flags["pla_amber_or_red"]
    word = {"holds": T("holds", "se sostiene"), "refuted": T("is refuted", "se refuta"),
            "not-established": T("is not established", "no queda establecida")}[v]
    n, nn = power["n"], size["n"]
    reading = T(
        f"The hypothesis {word['en']}: the rolling-mean complement flags the stale-volatility model in {_p(power['rate'], 'en')} of "
        f"{n:,} replications ({_p(power['ci_low'], 'en')} to {_p(power['ci_high'], 'en')}) at a size of 1% for the union of the three "
        f"statistics, and in {_p(plain['rate'], 'en')} at 1% for each statistic; the regulatory zone flags {_p(pla['rate'], 'en')}. "
        f"Its false-alarm rate on {nn:,} held-out exact-model replications is {_p(size['rate'], 'en')} "
        f"({_p(size['ci_low'], 'en')} to {_p(size['ci_high'], 'en')}); the thresholds come from {n_null:,} independent null desk-years. "
        f"The plan asks for at least {_p(HOLDS_POWER, 'en')} at a size of at most {_p(SIZE, 'en')} and refutes below {_p(REFUTED_POWER, 'en')}.",
        f"La hipótesis {word['es']}: el complemento de la media móvil marca el modelo con volatilidad rezagada en {_p(power['rate'], 'es')} de "
        f"{_n(n)} replicaciones ({_p(power['ci_low'], 'es')} a {_p(power['ci_high'], 'es')}) con un tamaño de 1 % para la unión de los tres "
        f"estadísticos, y en {_p(plain['rate'], 'es')} con 1 % para cada estadístico; la zona regulatoria marca {_p(pla['rate'], 'es')}. "
        f"Su tasa de falsas alarmas en {_n(nn)} replicaciones de reserva con el modelo exacto es {_p(size['rate'], 'es')} "
        f"({_p(size['ci_low'], 'es')} a {_p(size['ci_high'], 'es')}); los umbrales vienen de {_n(n_null)} años de mesa nulos independientes. "
        f"El plan pide al menos {_p(HOLDS_POWER, 'es')} con un tamaño de a lo sumo {_p(SIZE, 'es')} y la refuta bajo {_p(REFUTED_POWER, 'es')}.")
    return {
        "plan_id": PLAN_ID,
        "statement": T("At a size of at most 1%, the complement flags the model that uses a 20-day-old volatility in at least 30% of "
                       "replications, where the regulatory PLA flags none; refuted below 10%.",
                       "Con un tamaño de a lo sumo 1 %, el complemento marca el modelo que usa una volatilidad de hace 20 días en al "
                       "menos 30 % de las replicaciones, donde el PLA regulatorio no marca ninguna; se refuta bajo 10 %."),
        "statistic": "spearman_roll", "size_basis": "family-1pct-bonferroni",
        "power_threshold": HOLDS_POWER, "refuted_below": REFUTED_POWER, "size_limit": SIZE,
        "measured_power": power, "held_out_size": size, "pla_power": pla, "n_null_desk_years": n_null,
        "verdict": v, "reading": reading}


def block(did: str, m: ms.Measurement, stats: list[pc.PLAComplementStatistics], cal: Calibration,
          held: list[pc.PLAComplementStatistics], held_flags: dict[str, Any], ladder: list[dict[str, Any]] | None) -> dict[str, Any]:
    """The ``pla_complement`` member of a variant's outputs. ``held`` are the statistics of the ``none`` variant (its committed
    replications share no seed with the null), ``held_flags`` its flag block; for ``none`` they are its own."""
    flags = _flag_block(stats, m.zone, cal)
    wald, ks = flags["per_statistic"]["wald"]["k"], m.n_ks_flagged
    against = None if did == "none" else {"ks_flagged": ks, "wald_flagged": wald, "wald_at_least_ks": wald >= ks}
    return {
        "tier": "beyond", "plan_id": PLAN_ID, "engine_function": ENGINE_FUNCTION, "window_days": WINDOW, "size": SIZE,
        "correction": CORRECTION, "role": "size" if did == "none" else "power", "n_replications": m.n,
        "calibration": {"null_case_seeds": list(NULL_CASE_SEEDS), "n_per_block": cal.n_per_block, "n_null": len(cal.null),
                        "thresholds_per_statistic": _thresholds(cal.per_statistic), "thresholds_family": _thresholds(cal.family)},
        "flags": flags, "against_ks": against, "by_size": _by_size(stats, held, cal), "lag_ladder": ladder,
        "hypothesis": hypothesis_block(flags, held_flags, len(cal.null)) if did == "stale-volatility" else None}


def finding(did: str, b: dict[str, Any]) -> dict[str, Any]:
    """The F-COMPLEMENT finding of a variant: what the complement flags beside the regulatory zone."""
    fam, pla = b["flags"]["family"]["any"], b["flags"]["pla_amber_or_red"]
    n = b["n_replications"]
    pe, pn = (lambda x: _p(x, "en")), (lambda x: _p(x, "es"))
    if did == "none":
        ok = fam["rate"] <= SIZE
        return {"id": "F-COMPLEMENT", "severity": "S4" if ok else "S3", "status": "accepted" if ok else "open", "evidence": ["market.pla_test"],
                "title": T(f"With no deficiency the scale-and-level complement flags {pe(fam['rate'])} of {n:,} replications at a size of 1% "
                           f"(the regulatory PLA {pe(pla['rate'])}): its false-alarm rate",
                           f"Sin deficiencia el complemento de escala y nivel marca {pn(fam['rate'])} de {_n(n)} replicaciones con un tamaño de 1 % "
                           f"(el PLA regulatorio {pn(pla['rate'])}): su tasa de falsas alarmas")}
    sev, status = ("S4", "accepted") if fam["rate"] >= 0.95 else (("S3", "open") if fam["rate"] >= 0.5 else ("S2", "open"))
    return {"id": "F-COMPLEMENT", "severity": sev, "status": status, "evidence": ["market.pla_test"],
            "title": T(f"The scale-and-level complement, added beside the PLA, flags the planted deficiency in {pe(fam['rate'])} of {n:,} replications "
                       f"at a size of 1% (95% interval {pe(fam['ci_low'])} to {pe(fam['ci_high'])}); the regulatory PLA flags {pe(pla['rate'])}",
                       f"El complemento de escala y nivel, agregado junto al PLA, marca la deficiencia sembrada en {pn(fam['rate'])} de {_n(n)} "
                       f"replicaciones con un tamaño de 1 % (intervalo de 95 % {pn(fam['ci_low'])} a {pn(fam['ci_high'])}); el PLA regulatorio marca {pn(pla['rate'])}")}
