"""The reverse stress of C16 (``c16-outputs-reverse``): the run-off multiplier at which the survival period falls to the target.

Reverse liquidity stress (dossier 05 E.5 rung 5, decision Q9): the multiplier on every segment's daily rate of a base scenario (LiST
Adverse, LiST Extreme, the fast run), capped so that no rate exceeds 1. The solve is the engine's (``riskvalidation.liquidity.reverse``,
contract 1.2.0): the threshold multiplier, the smallest m at which SP(m) is at most the target, with the survival reached there and
the survival just below it (decision X1). The engine's net liquidity position takes no inflows, so the document hands it the CBC
plus the cumulative inflows less the cumulative other outflows, which leaves the ladder's own NLP at m = 1.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
from riskvalidation.liquidity import reverse as ereverse
from riskvalidation.liquidity.scenarios import Scenario
from riskvalidation.validation import liquidity as val

from .assumptions import txt
from .document import Shared, finding, model_summary
from .variant import BANK, UNITS, VARIANT_LABEL, Path, _tr, survival_days

BASES = ("list-adverse", "list-extreme", "fast-run")


def effective_cbc(lad: dict[str, Any]) -> np.ndarray:
    """The CBC the engine's reverse stress takes so that its NLP is the ladder's: CBC + cumulative inflows - cumulative other outflows."""
    seg_out = np.sum([s["outflows"] for s in lad["segments"]], axis=0)
    return np.array(lad["cbc_total"]) + np.cumsum(lad["total_inflows"]) - np.cumsum(np.array(lad["total_outflows"]) - seg_out)


def _es(reason: str, target: int) -> str:
    m = re.match(r"the target of (\d+) days is not below the horizon of (\d+) days", reason)
    if m:
        return f"El objetivo de {m.group(1)} días no es menor que el horizonte de {m.group(2)} días: no existe un intervalo."
    m = re.match(r"the base survival period of (\d+) days is already at or below the target", reason)
    if m:
        return f"El periodo de supervivencia base de {m.group(1)} días ya es menor o igual que el objetivo de {target} días."
    return f"Ningún multiplicador bajo el tope alcanza un periodo de supervivencia de {target} días o menos."


def _horizon_text(reason: str) -> str:
    """The engine's refusal for a target at or above the horizon, completed with why it matters (no survival period under the target
    can be told from surviving the horizon)."""
    if "not below the horizon" in reason:
        return (reason[0].upper() + reason[1:] + ", so a survival period under it cannot be separated from surviving the horizon: "
                "no bracket exists.")
    return reason[0].upper() + reason[1:] + "."


def solved_block(scn: Scenario, cbc_eff: np.ndarray, target: int) -> dict[str, Any]:
    """The solve of the engine as the ``solved`` block of a base, plus ``survival_just_below`` (the survival block at m* - 1e-6, None for
    a refusal) for the round-trip row; the document writer drops that key."""
    sol = ereverse.solve_multiplier(scn, cbc_eff, target)
    if sol.status != "solved":
        en = _horizon_text(sol.reason or "no multiplier reaches the target")
        return {"status": "refused", "multiplier": None, "survival_at_multiplier": None, "target_days": target, "round_trip_error": None,
                "refusal_reason": txt(en, _es(sol.reason or "", target)), "survival_just_below": None}
    below = sol.survival_just_below
    jb = {"kind": "survives-horizon", "day": None, "horizon_days": below.horizon} if below.survives else \
        {"kind": "day", "day": int(below.day), "horizon_days": below.horizon}
    return {"status": "solved", "multiplier": float(sol.multiplier), "survival_at_multiplier": int(sol.survival_at_multiplier), "target_days": target,
            "round_trip_error": float(sol.survival_at_multiplier - target), "refusal_reason": None, "survival_just_below": jb}


def base_block(vid: str, p: Path, conv: dict, target: int) -> tuple[dict[str, Any], dict[str, Any]]:
    """One base of the reverse stress: the SP(m) curve on the grid of the conventions (points beyond the cap omitted), the base survival
    and the solve. Returns the block and the solve with its survival just below."""
    cbc_eff = effective_cbc(p.ladder)
    cap = ereverse.max_multiplier(p.scn)
    grid = np.array([m for m in conv["runoff_multiplier_grid"]["values"] if m <= cap])
    sv = ereverse.survival_vs_multiplier(p.scn, cbc_eff, grid)
    curve = [{"multiplier": float(m), "survival": {"kind": "survives-horizon", "day": None, "horizon_days": s.horizon} if s.survives else
              {"kind": "day", "day": int(s.day), "horizon_days": s.horizon}} for m, s in zip(grid, sv)]
    solved = solved_block(p.scn, cbc_eff, target)
    jb = solved.pop("survival_just_below")
    blk = {"base_id": vid, "parameter_set": vid, "label": txt(*VARIANT_LABEL[vid][:2]), "base_survival": curve[0]["survival"],
           "max_rate_below_one": 1.0 / cap, "max_multiplier": round(cap, 6), "curve": curve, "solved": solved}
    return blk, {"survival_just_below": jb, "solved": solved}


def reverse_document(paths: dict[str, Path], sh: Shared) -> dict[str, Any]:
    """``outputs``, ``tests``, ``impact`` and ``findings`` of the reverse-stress document."""
    conv = sh.conv
    target = conv["reverse_target_days"]["value"]
    tol = conv["round_trip_tolerance_days"]["value"]
    bases, tests = [], []
    for vid in BASES:
        blk, extra = base_block(vid, paths[vid], conv, target)
        bases.append(blk)
        s = blk["solved"]
        jb = extra["survival_just_below"]
        below = None if jb is None else (float("inf") if jb["kind"] == "survives-horizon" else float(jb["day"]))
        tests.append(_tr(val.reverse_stress_round_trip(s["multiplier"], s["survival_at_multiplier"], target, tol, survival_just_below=below), segment=vid))
        days = [survival_days(p["survival"]) for p in blk["curve"]]
        tests.append(_tr(val.survival_monotone_in_severity(days, conv["monotonicity_tolerance_days"]["value"]), segment=vid))

    def mi(b: dict[str, Any], en: str, es: str) -> dict[str, Any]:
        return {"value": b["solved"]["multiplier"], "unit": "multiple of the daily rates", "label": txt(en, es)}

    o = {"kind": "reverse-stress", "valuation_date": "2022-12-31", "currency": "USD", "units": UNITS, "bank": BANK, "conventions": conv,
         "target": {"days": target, "statement": txt(
             f"The run-off multiplier at which the survival period first falls to {target} days (dossier 05 E.5 rung 5): the threshold multiplier, the "
             "smallest one at which the survival period is at most the target, with the survival reached there.",
             f"El multiplicador de salidas con el que el periodo de supervivencia cae por primera vez a {target} días: el multiplicador umbral.")},
         "cap_rule": {"each_rate_below_one": True, "statement": txt(
             "The multiplier scales every segment's daily rate and is capped so that each rate stays at most 1; a rate already at 1 stays.",
             "El multiplicador escala la tasa diaria de cada segmento y se limita para que cada tasa quede como máximo 1.")},
         "bases": bases}
    impact = {"multiplier_list_adverse": mi(bases[0], "Reverse-stress multiplier, LiST Adverse", "Multiplicador del estrés inverso, LiST adverso"),
              "multiplier_list_extreme": mi(bases[1], "Reverse-stress multiplier, LiST Extreme", "Multiplicador del estrés inverso, LiST extremo"),
              "multiplier_fast_run": mi(bases[2], "Reverse-stress multiplier, fast run", "Multiplicador del estrés inverso, corrida rápida")}
    findings = []
    for b in bases:
        if b["solved"]["status"] == "refused":
            findings.append(finding(f"F-liq-reverse-{b['base_id']}", "S4", ["liq.reverse_stress_round_trip"],
                                    f"The reverse stress of the {VARIANT_LABEL[b['base_id']][0]} base is refused: its ladder is shorter than the target",
                                    f"El estrés inverso de la base {VARIANT_LABEL[b['base_id']][1]} se rechaza: su escalera es menor que el objetivo"))
    return {"outputs": o, "tests": tests, "impact": impact, "findings": findings, "models": [model_summary(sh.engine_version, "reverse-stress")]}


__all__ = ["BASES", "base_block", "effective_cbc", "reverse_document", "solved_block"]
