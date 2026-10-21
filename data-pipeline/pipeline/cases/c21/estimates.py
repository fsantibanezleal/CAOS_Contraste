"""The estimates of C21: every statistic and test comes from ``riskvalidation`` (ADR-0069); this module reads arrays, builds the
design of the permitted controls and writes the blocks of the c21-outputs contract.

Per attribute (race, ethnicity, sex, age) of one year pair, fitted on year t and confirmed on t + 1:

- the selection rates by group, the parity gap and ratio, the adverse impact ratio against the reference group and the four-fifths flag
  against the highest-rate group (``fairness.metrics``), the pooled z-test and the Fisher exact test (``fairness.inference``): all on the
  fit year;
- the controlled decision estimate (``fairness.conditional.fit_decision_model``, the protected indicator at index 1) and the rate-spread
  estimate (``fit_rate_spread_model``), each pairwise: the group against the attribute's reference group, on the rows of those two
  groups with every control usable;
- the confirmation: the same estimate refitted on year t + 1 and compared with the fit by sign and size (``replicate_effect``);
- the situation test on Black or African American applicants against White (``fairness.situation``, decision G15), ceteris paribus
  only, range normalization.

Public HMDA has no credit score: every controlled estimate names it as a missing control. The unconditional rates are indicators only;
the controlled disparity is an approximation of comparative evidence; nothing here is a finding of a violation.

The design of the controls is a named convention (design.md): the debt-to-income ratio as the indicators of its published bins (the
36 to 49 bin is the reference), the natural logarithm of the combined loan-to-value ratio, the income, the loan amount and the property
value, and the indicators of the loan type, the loan purpose, the lien status and the occupancy type (the first code of each the reference).
A row with a control missing or unusable (a non-positive value has no logarithm) is left out of the controlled fits and counted.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Any

import numpy as np
from riskvalidation.fairness import conditional as rv_conditional
from riskvalidation.fairness import inference as rv_inference
from riskvalidation.fairness import metrics as rv_metrics
from riskvalidation.fairness import replication as rv_replication
from riskvalidation.fairness import situation as rv_situation
from riskvalidation.validation import fairness as rv_tests

from . import legal
from .legal import t
from .reader import Sample

LEVEL = 0.95
SITUATION_K = 30
SITUATION_ATTRIBUTE = "derived_race"
SITUATION_PROTECTED = "Black or African American"
MODEL_RATES = "hmda-selection-rates"
MODEL_LOGIT = "hmda-logistic-decision"
MODEL_OLS = "hmda-linear-rate-spread"
MODEL_SITUATION = "hmda-situation-testing"
APPROXIMATION = "approximation of comparative evidence"

DTI_DUMMIES = (0, 1, 2, 4, 5)  # bin 3 (36%-49%) is the reference
NOMINAL_LEVELS = {"loan_type": (2, 3, 4), "loan_purpose": (2, 31, 32, 4, 5), "lien_status": (2,), "occupancy_type": (2, 3)}
SITUATION_CATEGORICAL = np.array([False, False, False, False, False, True, True, True, True])
SITUATION_COLUMNS = ("dti_bin", "ln_combined_loan_to_value_ratio", "ln_income", "ln_loan_amount", "ln_property_value", "loan_type",
                     "loan_purpose", "lien_status", "occupancy_type")


# --- the design of the controls ------------------------------------------------------------------------------------------
@dataclass
class Design:
    """The control columns of every decision row of a sample (NaN where a control is missing) and the rows that are usable."""

    names: list[str]
    matrix: np.ndarray
    usable: np.ndarray
    situation: np.ndarray  # the nine non-protected attributes of the situation test, one column each


def build_design(s: Sample) -> Design:
    with np.errstate(invalid="ignore", divide="ignore"):
        positive = (s.cltv > 0) & (s.income > 0) & (s.loan_amount > 0) & (s.property_value > 0)
    usable = positive & (s.dti_bin >= 0)  # NaN compares false: a missing number is not positive
    logs = [np.where(usable, np.log(np.where(positive, v, 1.0)), np.nan) for v in (s.cltv, s.income, s.loan_amount, s.property_value)]
    names: list[str] = []
    cols: list[np.ndarray] = []
    for b in DTI_DUMMIES:
        names.append(f"debt_to_income_ratio={legal.DTI_BINS[b]}")
        cols.append((s.dti_bin == b).astype(float))
    for nm, lg in zip(("combined_loan_to_value_ratio", "income", "loan_amount", "property_value"), logs):
        names.append(f"ln({nm})")
        cols.append(lg)
    for fld, levels in NOMINAL_LEVELS.items():
        for lv in levels:
            names.append(f"{fld}={lv}")
            cols.append((s.nominal[fld] == lv).astype(float))
    matrix = np.column_stack(cols)
    situation = np.column_stack([s.dti_bin.astype(float), *logs, *(s.nominal[f].astype(float) for f in ("loan_type", "loan_purpose", "lien_status",
                                                                                                    "occupancy_type"))])
    return Design(names, matrix, usable, situation)


# --- a fitted estimate ---------------------------------------------------------------------------------------------------
@dataclass
class Fit:
    """One pairwise estimate: the engine's effect (None with a reason when the model cannot be fitted) and the fitted terms."""

    effect: rv_conditional.Effect | None
    n: int
    reason: str | None
    terms: list[tuple[str, float, float]]
    dropped: tuple[str, ...] = ()


def fit_contrast(s: Sample, d: Design, field: str, group: str, reference: str, kind: str) -> Fit:
    """The group against the reference group: ``kind`` is ``logistic`` (the approval) or ``linear`` (the rate spread, codes 1 and 2)."""
    attr = s.attribute[field]
    sel = ((attr == group) | (attr == reference)) & d.usable
    if kind == "linear":
        sel &= (s.action <= 2) & ~np.isnan(s.rate_spread)
    n_group, n_ref = int((sel & (attr == group)).sum()), int((sel & (attr == reference)).sum())
    if n_group == 0 or n_ref == 0:
        return Fit(None, int(sel.sum()), f"a group has no usable row ({group}: {n_group}, {reference}: {n_ref})", [])
    prot = (attr[sel] == group).astype(float)[:, None]
    ctrl = d.matrix[sel]
    keep = ctrl.std(axis=0) > 0  # a column constant in this pair of groups is collinear with the intercept
    if kind == "logistic":
        y = s.decision[sel]
        for j in np.flatnonzero(keep):
            on = y[ctrl[:, j] == 1.0] if set(np.unique(ctrl[:, j])) <= {0.0, 1.0} else y
            if on.size and on.min() == on.max():  # an indicator whose rows all share one decision separates the classes completely
                keep[j] = False
    names = [nm for nm, k in zip(d.names, keep) if k]
    try:
        if kind == "logistic":
            model = rv_conditional.fit_decision_model(s.decision[sel], prot, ctrl[:, keep])
        else:
            model = rv_conditional.fit_rate_spread_model(s.rate_spread[sel], prot, ctrl[:, keep])
        if not model.converged:
            return Fit(None, model.n, "the decision model did not converge (the classes are separated or the iteration did not settle)", [])
        effect = rv_conditional.protected_effect(model, 1, LEVEL)
    except ValueError as exc:
        return Fit(None, int(sel.sum()), f"the model cannot be fitted: {exc}", [])
    labels = ["intercept", f"{field}={group}", *names]
    terms = [(lab, float(c), float(e)) for lab, c, e in zip(labels, model.coefficients, model.standard_errors)]
    return Fit(effect, model.n, None, terms, tuple(nm for nm, k in zip(d.names, keep) if not k))


def _controlled(fit: Fit) -> dict[str, Any]:
    if fit.effect is None:
        return {"estimate": None, "reason": fit.reason}
    e = fit.effect
    return {"estimate": {"model": "logistic-decision-model", "outcome": "approval", "coefficient": e.coefficient, "odds_ratio": e.odds_ratio,
                         "ci": {"lo": e.lo, "hi": e.hi, "level": e.level}, "n": fit.n, "controls": list(legal.CONTROLS),
                         "missing_controls": list(legal.MISSING_CONTROLS), "label": APPROXIMATION}, "reason": None}


def _rate_spread(fit: Fit) -> dict[str, Any]:
    if fit.effect is None:
        return {"estimate": None, "reason": fit.reason}
    e = fit.effect
    return {"estimate": {"model": "linear-rate-spread", "population": "action_taken 1 or 2", "coefficient": e.coefficient,
                         "ci": {"lo": e.lo, "hi": e.hi, "level": e.level}, "n": fit.n, "controls": list(legal.CONTROLS),
                         "missing_controls": list(legal.MISSING_CONTROLS), "label": APPROXIMATION,
                         "unit": "percentage points of rate_spread"}, "reason": None}


def _confirmation(fit: Fit, confirm: Fit, years: tuple[int, int]) -> tuple[dict[str, Any], rv_replication.Replication | None]:
    if fit.effect is None or confirm.effect is None:
        why = fit.reason if fit.effect is None else f"year {years[1]}: {confirm.reason}"
        return {"estimate": None, "reason": f"the estimate cannot be confirmed: {why}"}, None
    r = rv_replication.replicate_effect(fit.effect, confirm.effect)
    return {"estimate": {"fit_year": years[0], "confirm_year": years[1], "fit_coefficient": r.fit_coefficient,
                         "confirm_coefficient": r.confirm_coefficient, "same_sign": r.same_sign, "size_ratio": r.size_ratio},
            "reason": None}, r


# --- one attribute -------------------------------------------------------------------------------------------------------
@dataclass
class AttributeResult:
    block: dict[str, Any]
    tests: list[Any]
    fits: list[dict[str, Any]]


def _segment(result: Any, segment: str) -> Any:
    """The engine row with its segment, for the document.

    A row whose notes do not carry the label (a test that was not evaluated) gets "no legal claim" appended. Nothing else of the row
    changes: every statistic, light and alpha is the engine's (``engine-fairness-api`` 1.2.0 writes null alphas on the two interval
    tests and on the situation test, with their levels in ``extras.thresholds`` and the policy version).
    """
    notes = result.notes if "no legal claim" in result.notes else f"{result.notes}; no legal claim"
    return dataclasses.replace(result, segment=segment, notes=notes)


def attribute_result(field: str, fit_s: Sample, fit_d: Design, conf_s: Sample, conf_d: Design) -> AttributeResult:
    """The c21Attribute block of one attribute with its test rows and the fits that the models document keeps."""
    years = (fit_s.year, conf_s.year)
    all_rates = rv_metrics.group_selection_rates(fit_s.decision, fit_s.attribute[field])
    present = [g for g in legal.GROUPS[field] if g in all_rates]
    unknown = sorted(set(all_rates) - set(legal.GROUPS[field]) - set(legal.NON_GROUPS[field]))
    if unknown:
        raise ValueError(f"{field}: categories outside the dictionary: {unknown}")
    reference = legal.REFERENCE[field]
    if reference not in present or len(present) < 2:
        raise ValueError(f"{field}: the reference group {reference!r} or a second group has no decision row in {fit_s.year}")
    rates = {g: all_rates[g] for g in present}  # canonical order: a tie on the highest rate goes to the first group of the list
    ff = rv_metrics.four_fifths_flag(rates)
    gap = rv_metrics.demographic_parity_difference(rates, reference)
    ratio = rv_metrics.demographic_parity_ratio(rates, reference)
    air = rv_metrics.adverse_impact_ratio(rates, reference)
    ref = rates[reference]
    tests: list[Any] = [_segment(rv_tests.demographic_parity(MODEL_RATES, rates, reference), field),
                        _segment(rv_tests.adverse_impact(MODEL_RATES, rates, reference), field)]
    contrasts: list[dict[str, Any]] = []
    fits: list[dict[str, Any]] = []
    for g in present:
        if g == reference:
            continue
        sg = rates[g]
        seg = f"{field}|{g} vs {reference}"
        z = rv_inference.two_proportion_z_test(sg.favourable, sg.n, ref.favourable, ref.n)
        fe = rv_inference.fisher_exact_test(sg.favourable, sg.n, ref.favourable, ref.n)
        tests.append(_segment(rv_tests.two_proportion_z(MODEL_RATES, sg.favourable, sg.n, ref.favourable, ref.n), seg))
        tests.append(_segment(rv_tests.fisher_exact(MODEL_RATES, sg.favourable, sg.n, ref.favourable, ref.n), seg))
        fit_l = fit_contrast(fit_s, fit_d, field, g, reference, "logistic")
        fit_o = fit_contrast(fit_s, fit_d, field, g, reference, "linear")
        conf_l = fit_contrast(conf_s, conf_d, field, g, reference, "logistic")
        conf_o = fit_contrast(conf_s, conf_d, field, g, reference, "linear")
        confirmation, rep_l = _confirmation(fit_l, conf_l, years)
        _, rep_o = _confirmation(fit_o, conf_o, years)
        tests.append(_segment(rv_tests.conditional_disparity(MODEL_LOGIT, fit_l.effect, legal.CONTROLS, legal.MISSING_CONTROLS), seg))
        tests.append(_segment(rv_tests.rate_spread_disparity(MODEL_OLS, fit_o.effect, legal.CONTROLS, legal.MISSING_CONTROLS), seg))
        if rep_l is not None:
            tests.append(_segment(rv_tests.replication(MODEL_LOGIT, rep_l), f"{seg}|controlled"))
        if rep_o is not None:
            tests.append(_segment(rv_tests.replication(MODEL_OLS, rep_o), f"{seg}|rate_spread"))
        for kind, outcome, f in (("logistic", "approval", fit_l), ("linear", "rate_spread", fit_o)):
            if f.effect is not None:
                fits.append({"fit_year": years[0], "kind": kind, "outcome": outcome, "n": f.n, "converged": True,
                             "terms": [{"term": a, "coefficient": b, "se": c} for a, b, c in f.terms]})
        contrasts.append({
            "group": g, "reference_group": reference, "n_group": sg.n, "n_reference": ref.n, "selection_rate_group": sg.rate,
            "selection_rate_reference": ref.rate, "parity_gap": gap[g], "parity_ratio": ratio[g],
            "adverse_impact_ratio": {"value": air[g], "note": t("The adverse impact ratio against the chosen reference group: the parity ratio",
                                                                "La razón de impacto adverso frente al grupo de referencia elegido: la razón de paridad")},
            "z_test": {"statistic": z.statistic, "p_value": z.p_value},
            "fisher_exact": {"odds_ratio": fe.odds_ratio, "p_value": fe.p_value},
            "controlled": _controlled(fit_l), "rate_spread": _rate_spread(fit_o), "confirmation": confirmation})
    excluded = [{"group": g, "n": int(all_rates[g].n),
                 "reason": t("Not a protected group: carried as its own group, excluded from the pairwise tests",
                             "No es un grupo protegido: se lleva como grupo propio y se excluye de las pruebas por pares")}
                for g in legal.NON_GROUPS[field] if g in all_rates]
    block = {
        "field": field, "legal": legal.attribute_legal(field), "reference_group": reference,
        "groups": [{"group": g, "n": rates[g].n, "n_approved": rates[g].favourable, "n_denied": rates[g].n - rates[g].favourable,
                    "selection_rate": rates[g].rate} for g in present],
        "excluded_groups": excluded,
        "four_fifths": {"label": ff.label, "citation": "29 CFR 1607.4(D)", "threshold": ff.threshold, "is_credit_law_threshold": False,
                        "compared_with": ff.compared_with, "decided_on": "exact-counts", "rule": "flag when 5 * x_g * n_h < 4 * x_h * n_g",
                        "highest_rate_group": ff.highest_rate_group,
                        "groups": [{"group": g, "ratio_to_highest": ff.ratio_to_highest[g], "flag": bool(ff.flag[g])} for g in present]},
        "contrasts": contrasts}
    return AttributeResult(block, tests, fits)


# --- situation testing ---------------------------------------------------------------------------------------------------
def situation_result(fit_s: Sample, fit_d: Design, k: int = SITUATION_K) -> tuple[dict[str, Any], Any]:
    """Ceteris paribus situation testing of Black or African American applicants against White, fit year (decision G15): the engine's
    ``situation_test`` with the range normalization and the four nominal columns marked categorical. The counterfactual test is not run:
    public HMDA gives no counterfactual dataset."""
    attr = fit_s.attribute[SITUATION_ATTRIBUTE]
    sel = ((attr == SITUATION_PROTECTED) | (attr == legal.REFERENCE[SITUATION_ATTRIBUTE])) & fit_d.usable
    x = fit_d.situation[sel]
    res = rv_situation.situation_test(x, (attr[sel] == SITUATION_PROTECTED).astype(np.int64), fit_s.decision[sel], k, tau=0.0,
                                      alpha=0.05, comparator="ceteris-paribus", normalization="range", categorical=SITUATION_CATEGORICAL)
    block = {"label": "situation-testing", "comparator": "ceteris-paribus",
             "counterfactual_test": {"run": False, "reason": t("Public HMDA gives no counterfactual dataset, so the counterfactual test "
                                                              "(mutatis mutandis) is not run",
                                                              "El HMDA público no entrega un conjunto contrafactual, de modo que la prueba "
                                                              "contrafactual (mutatis mutandis) no se ejecuta")},
             "attribute": SITUATION_ATTRIBUTE, "k": k, "alpha": 0.05, "tau": 0, "distance_normalization": "range",
             "label_parameters": "convention", "centers": "excluded", "interval": "one-sided Wald, equation (10) of arXiv 2502.01267",
             "n_complainants": res.n_complainants, "n_cases": res.n_cases, "n_significant": res.n_significant}
    return block, _segment(rv_tests.situation_testing(MODEL_SITUATION, res), SITUATION_ATTRIBUTE)


# --- data notes ----------------------------------------------------------------------------------------------------------
def data_notes(s: Sample | None = None, action_counts: dict[int, int] | None = None) -> list[dict[str, Any]]:
    """What the public release withholds, bins or rounds. With a sample (the fit year of a pair) the notes carry its counts; without
    one (the models document, which spans the fit years) the counts are null, a nullable value and never a fabricated number."""
    def missing(a: np.ndarray) -> int | None:
        return None if s is None else int(np.isnan(a).sum())

    def unusable(name: str) -> tuple[str, str]:
        """The sentence on the values that are present and not positive (no logarithm), with their count when a sample is given."""
        if s is None:
            return "", ""
        a = getattr(s, name)
        k = int(((a <= 0) & ~np.isnan(a)).sum())
        return f" ({k} present values are not positive)", f" ({k} valores presentes no son positivos)"

    if action_counts is None:
        left_out = ("The rows of codes 4 to 8 are left out of every rate by the decision convention; their counts by code are in the "
                    "outputs documents.",
                    "Las filas de los códigos 4 a 8 quedan fuera de toda tasa por la convención de decisión; sus conteos por código están en "
                    "los documentos de resultados.")
    else:
        by_code = ", ".join(f"{k}: {action_counts.get(k, 0)}" for k in legal.EXCLUDED_CODES)
        n_left_out = sum(v for k, v in action_counts.items() if k in legal.EXCLUDED_CODES)
        left_out = (f"{n_left_out} rows of codes 4 to 8 are left out of every rate by the decision convention (by code, {by_code}).",
                    f"{n_left_out} filas de los códigos 4 a 8 quedan fuera de toda tasa por la convención de decisión (por código, {by_code}).")
    ls = None if s is None else s.action <= 2
    return [
        {"field": "action_taken", "treatment": "unmodified", "n_missing": None,
         "reason": t(f"Disclosed without modification. {left_out[0]}", f"Se divulga sin modificación. {left_out[1]}")},
        {"field": "applicant_age", "treatment": "top-coded",
         "n_missing": None if s is None else int((s.attribute["applicant_age"] == "8888").sum()),
         "reason": t("Binned, bottom-coded under 25 and top-coded over 74; the code 8888 is not available and is an excluded group",
                     "En tramos, con tope inferior bajo 25 y superior sobre 74; el código 8888 es no disponible y es un grupo excluido")},
        {"field": "debt_to_income_ratio", "treatment": "binned", "n_missing": None if s is None else int((s.dti_bin < 0).sum()),
         "reason": t("Exact from 36 to 49 percent and binned outside, bottom-coded under 20 and top-coded above 60 in the public release; "
                     "the missing markers NA and Exempt count here; the rows without it are left out of the controlled fits",
                     "Exacto de 36 a 49 por ciento y en tramos fuera, con tope bajo 20 y sobre 60 en la publicación pública; los "
                     "marcadores NA y Exempt cuentan aquí; las filas sin él quedan fuera de los ajustes controlados")},
        {"field": "combined_loan_to_value_ratio", "treatment": "unmodified", "n_missing": None if s is None else missing(s.cltv),
         "reason": t("Disclosed without modification; entered as its natural logarithm, so a non-positive value is unusable and the row is "
                     f"left out of the controlled fits{unusable('cltv')[0]}",
                     "Se divulga sin modificación; entra como su logaritmo natural, de modo que un valor no positivo es inutilizable y la "
                     f"fila queda fuera de los ajustes controlados{unusable('cltv')[1]}")},
        {"field": "income", "treatment": "unmodified", "n_missing": None if s is None else missing(s.income),
         "reason": t("Disclosed without modification, in thousands of dollars, with no upper limit and outliers; entered as its natural "
                     f"logarithm, so a non-positive value is unusable and the row is left out of the controlled fits{unusable('income')[0]}",
                     "Se divulga sin modificación, en miles de dólares, sin límite superior y con valores atípicos; entra como su logaritmo "
                     f"natural, de modo que un valor no positivo es inutilizable y la fila queda fuera de los ajustes controlados{unusable('income')[1]}")},
        {"field": "loan_amount", "treatment": "rounded", "n_missing": None if s is None else missing(s.loan_amount),
         "reason": t("Rounded to the midpoint of the $10,000 interval in the public release; entered as its natural logarithm",
                     "Redondeado al punto medio del intervalo de $10.000 en la publicación pública; entra como su logaritmo natural")},
        {"field": "property_value", "treatment": "rounded", "n_missing": None if s is None else missing(s.property_value),
         "reason": t("Rounded to the midpoint of the $10,000 interval in the public release; entered as its natural logarithm",
                     "Redondeado al punto medio del intervalo de $10.000 en la publicación pública; entra como su logaritmo natural")},
        {"field": "rate_spread", "treatment": "not-applicable",
         "n_missing": None if s is None else int(np.isnan(s.rate_spread[ls]).sum()),
         "reason": t("Reported for originated loans and approved applications not accepted that carry it (codes 1 and 2); the rate-spread "
                     "estimate reads those loans only, and the loans without it are left out",
                     "Se reporta para préstamos originados y solicitudes aprobadas no aceptadas que lo tienen (códigos 1 y 2); la estimación "
                     "del diferencial de tasa lee solo esos préstamos y los préstamos sin él quedan fuera")},
    ]
