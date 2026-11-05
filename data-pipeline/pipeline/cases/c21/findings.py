"""The findings of a C21 pair document (decision G16 of the U14 sizing, review M4): statistical findings about the document's evidence.

A finding groups what several test rows show; it is never one finding per row. Each cites the rows of its own document as
``test_id@model@segment`` (the check of ``core/manifest.py``), or a stated design limit as ``design:<name>``. Every title says
"no legal claim" and none states a violation: the subject of a finding is the public data and the estimate, never a lender. The
severities run in the product's direction, S1 critical to S4 minor:

- S2 ``open``: a controlled disparity whose 95 percent interval excludes 0 in the fit year and whose sign repeats on t + 1, where the
  protected group's controlled odds ratio is below 1 (approved at lower controlled odds than its reference group);
- S3 ``open``: the repeating ones above 1 (approved at higher controlled odds), a controlled disparity that does not repeat, and a
  repeating rate-spread disparity with a higher spread for the protected group;
- S4 ``open``: the unconditional gap, as an indicator only, with the sentence of the Interagency Procedures, which also takes the
  repeating rate-spread disparities with a lower spread for the protected group;
- S4 ``accepted``: the stated limits (the credit score is missing; the complete-case selection).

The rules read the rows of the document (the interval in ``extras.effect`` and ``same_sign`` of the replication row); no number is
computed here.
"""
from __future__ import annotations

from typing import Any

from . import legal
from .legal import t

LABEL_EN, LABEL_ES = "no legal claim", "sin afirmación legal"
MODEL_RATES, MODEL_LOGIT, MODEL_OLS = "hmda-selection-rates", "hmda-logistic-decision", "hmda-linear-rate-spread"


def _id(row: dict[str, Any]) -> str:
    return f"{row['test_id']}@{row['model_id']}@{row['segment']}"


def favours_elderly(row: dict[str, Any]) -> bool:
    """The controlled row of the 62 contrast whose odds favour the group 62 or over (odds ratio above 1): Regulation B 1002.6(b)(2)(iv)
    permits favourable treatment of an elderly applicant, so the contrast is measured and shown but does not raise the finding of higher
    controlled odds. A disparity against the group (odds ratio below 1) raises its finding as for any group."""
    return row["segment"].startswith(f"{legal.AGE62}|{legal.GROUPS[legal.AGE62][0]} vs ") and row["extras"]["effect"]["odds_ratio"] > 1


def _excludes_zero(row: dict[str, Any]) -> bool:
    effect = (row.get("extras") or {}).get("effect")
    return effect is not None and (effect["lo"] > 0 or effect["hi"] < 0)


def _finding(fid: str, severity: str, status: str, evidence: list[str], en: str, es: str) -> dict[str, Any]:
    return {"id": fid, "severity": severity, "status": status, "evidence": evidence, "title": t(f"{en}; {LABEL_EN}", f"{es}; {LABEL_ES}")}


def contrasts(n: int) -> str:
    """ "1 group contrast", "2 group contrasts" (U16-R3 c21 m4)."""
    return f"{n} group contrast" if n == 1 else f"{n} group contrasts"


def contrastes(n: int) -> str:
    """ "1 contraste de grupos", "2 contrastes de grupos"."""
    return f"{n} contraste de grupos" if n == 1 else f"{n} contrastes de grupos"


def build(tests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The findings of one pair document, from its test rows (as dicts), in a fixed order."""
    by_key = {_id(r): r for r in tests}
    lower: list[tuple[dict[str, Any], dict[str, Any]]] = []
    higher: list[tuple[dict[str, Any], dict[str, Any]]] = []
    not_repeated: list[tuple[dict[str, Any], dict[str, Any]]] = []
    spread_higher: list[tuple[dict[str, Any], dict[str, Any]]] = []
    spread_lower: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for r in tests:
        if r["test_id"] == "fair.conditional_disparity" and r["model_id"] == MODEL_LOGIT and _excludes_zero(r):
            rep = by_key.get(f"fair.replication@{MODEL_LOGIT}@{r['segment']}|controlled")
            if rep is None:
                continue
            if not rep["extras"]["same_sign"]:
                not_repeated.append((r, rep))
            elif r["extras"]["effect"]["odds_ratio"] < 1:
                lower.append((r, rep))
            elif not favours_elderly(r):                  # 1002.6(b)(2)(iv) permits favouring the elderly: measured, not raised
                higher.append((r, rep))
        elif r["test_id"] == "fair.rate_spread_disparity" and r["model_id"] == MODEL_OLS and _excludes_zero(r):
            rep = by_key.get(f"fair.replication@{MODEL_OLS}@{r['segment']}|rate_spread")
            if rep is not None and rep["extras"]["same_sign"]:
                (spread_higher if r["extras"]["effect"]["coefficient"] > 0 else spread_lower).append((r, rep))
    out: list[dict[str, Any]] = []

    def pairs(items: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[str]:
        return [_id(x) for pair in items for x in pair]

    if lower:
        n = len(lower)
        out.append(_finding(
            "F-CONTROLLED-LOWER-ODDS", "S2", "open", pairs(lower),
            f"Controlled disparity repeated on the next year in {contrasts(n)} where the group is approved at lower controlled odds "
            "than its reference group (odds ratio below 1): an approximation of comparative evidence on public data",
            f"Disparidad controlada que se repite el año siguiente en {contrastes(n)} donde el grupo es aprobado con una menor razón de "
            "probabilidades controlada que su grupo de referencia (razón de probabilidades bajo 1): una aproximación de evidencia comparativa sobre "
            "datos públicos"))
    if higher:
        n = len(higher)
        out.append(_finding(
            "F-CONTROLLED-HIGHER-ODDS", "S3", "open", pairs(higher),
            f"Controlled disparity repeated on the next year in {contrasts(n)} where the group is approved at higher controlled odds "
            "than its reference group (odds ratio above 1): an approximation of comparative evidence on public data",
            f"Disparidad controlada que se repite el año siguiente en {contrastes(n)} donde el grupo es aprobado con una mayor razón de "
            "probabilidades controlada que su grupo de referencia (razón de probabilidades sobre 1): una aproximación de evidencia comparativa "
            "sobre datos públicos"))
    if not_repeated:
        n = len(not_repeated)
        out.append(_finding(
            "F-CONTROLLED-NOT-REPEATED", "S3", "open", pairs(not_repeated),
            f"Controlled disparity that does not repeat on the next year in {contrasts(n)}: the sign differs between the two years",
            f"Disparidad controlada que no se repite el año siguiente en {contrastes(n)}: el signo difiere entre los dos años"))
    if spread_higher:
        n = len(spread_higher)
        out.append(_finding(
            "F-RATE-SPREAD-HIGHER", "S3", "open", pairs(spread_higher),
            f"Rate-spread disparity repeated on the next year in {contrasts(n)} where the group has a higher rate spread than its "
            "reference group, the interval excluding 0",
            f"Disparidad del diferencial de tasa que se repite el año siguiente en {contrastes(n)} donde el grupo tiene un "
            "diferencial de tasa mayor que su grupo de referencia, con el intervalo excluyendo 0"))
    n_attributes = sum(1 for r in tests if r["test_id"] == "fair.demographic_parity")
    gap = [r["segment"] for r in tests if r["test_id"] == "fair.demographic_parity" and r["light"] != "green"]
    # the red rows of the unconditional pairwise tests are the same gross gap, contrast by contrast: this finding cites them, at its S4
    # "indicator only" (U16-R4 c25 M1 and ruling 4 of the R4 triage: every red test row is cited by an open finding)
    red_pairwise = [f"{r['test_id']}@{r['model_id']}@{r['segment']}" for r in tests
                    if r["test_id"] in ("fair.two_proportion_z", "fair.fisher_exact") and r["light"] == "red"]
    if gap or spread_lower or red_pairwise:
        evidence = [f"{tid}@{MODEL_RATES}@{seg}" for seg in gap for tid in ("fair.demographic_parity", "fair.adverse_impact")]
        evidence += [e for e in red_pairwise if e not in evidence]
        evidence += pairs(spread_lower)
        quote = legal.QUOTES["procedures"][1]
        extra_en = (f" and {len(spread_lower)} repeating rate-spread contrasts where the group has a lower rate spread than its reference "
                    "group") if spread_lower else ""
        extra_es = (f" y {len(spread_lower)} contrastes repetidos del diferencial de tasa donde el grupo tiene un diferencial menor que su "
                    "grupo de referencia") if spread_lower else ""
        if red_pairwise:
            # the attributes of the red rows, counted on their own (U16-R5 c27 n2: the parity count read narrower than these rows)
            m = len({e.split("@")[2].split("|")[0] for e in red_pairwise})
            extra_en = (f", {len(red_pairwise)} red rows of the two-proportion z-test and the Fisher exact test in {m} "
                        f"{'attribute' if m == 1 else 'attributes'}") + extra_en
            extra_es = (f", {len(red_pairwise)} filas rojas de la prueba z de dos proporciones y de la prueba exacta de Fisher en {m} "
                        f"{'atributo' if m == 1 else 'atributos'}") + extra_es
        out.append(_finding(
            "F-UNCONDITIONAL-GAP", "S4", "open", evidence,
            f"Unconditional approval-rate gaps, with parity indicators above their tolerance in {len(gap)} of the {n_attributes} attributes{extra_en}, "
            f"are an indicator only: \"{quote}\" (Interagency Fair Lending Examination Procedures)",
            f"Las brechas incondicionales de tasa de aprobación, con indicadores de paridad sobre su tolerancia en {len(gap)} de los {n_attributes} "
            f"atributos{extra_es}, son solo un indicador: "
            f"«{legal.QUOTES_ES['procedures']}» (Procedimientos Interagenciales de Examen de Préstamos Justos; original en inglés: \"{quote}\")"))
    out.append(_finding(
        "F-LIMIT-CREDIT-SCORE", "S4", "accepted", ["design:credit-score-missing"],
        "Limit of the evidence: the credit score is not in public HMDA, so every controlled estimate may be confounded by it",
        "Límite de la evidencia: el puntaje de crédito no está en el HMDA público, de modo que toda estimación controlada puede estar "
        "confundida por él"))
    out.append(_finding(
        "F-LIMIT-COMPLETE-CASES", "S4", "accepted", ["design:complete-case-selection"],
        "Limit of the evidence: the controlled fits use the complete cases, and denied applications miss a control more often than "
        "originated loans",
        "Límite de la evidencia: los ajustes controlados usan los casos completos, y las solicitudes rechazadas carecen de un control "
        "con más frecuencia que los préstamos originados"))
    return out
