"""The named conventions, the legal label and the group vocabulary of C21 (decisions C2 to C4 and C7 of the U14 sizing, V3).

Everything here is a statement the documents repeat: the sources are the U14 research addendum (H1 the data dictionary, H2 access and
terms, H3 the legal tests and the field-to-basis table) and the sizing. Nothing here is a legal conclusion: the case measures
statistical disparity in public decisions and says "no legal claim". The schema pins each constant (``docs/contracts/schemas/c21/``),
so a drift between this module and the contract fails the validation of every document.
"""
from __future__ import annotations

from typing import Any


def t(en: str, es: str | None = None) -> dict[str, str]:
    """A bilingual text; a quotation keeps its English wording in both languages."""
    return {"en": en, "es": es if es is not None else en}


# --- the attributes, their groups and the reference group of each ----------------------------------------------------
ATTRIBUTES = ("derived_race", "derived_ethnicity", "derived_sex", "applicant_age")

#: the groups of each attribute (addendum H1 2.2), in the order the documents list them
GROUPS: dict[str, tuple[str, ...]] = {
    "derived_race": ("American Indian or Alaska Native", "Asian", "Black or African American",
                     "Native Hawaiian or Other Pacific Islander", "White", "2 or more minority races"),
    "derived_ethnicity": ("Hispanic or Latino", "Not Hispanic or Latino"),
    "derived_sex": ("Male", "Female"),
    "applicant_age": ("<25", "25-34", "35-44", "45-54", "55-64", "65-74", ">74"),
}
#: the categories that are not a protected group: their own excluded groups, never in a pairwise test (decision C2)
NON_GROUPS: dict[str, tuple[str, ...]] = {
    "derived_race": ("Joint", "Free Form Text Only", "Race Not Available"),
    "derived_ethnicity": ("Joint", "Free Form Text Only", "Ethnicity Not Available"),
    "derived_sex": ("Joint", "Sex Not Available"),
    "applicant_age": ("8888",),
}
#: the group every other group of the attribute is contrasted with: the customary comparison group (a convention). For age the
#: contract's fixture names 35-44; no source names a reference age band.
REFERENCE: dict[str, str] = {"derived_race": "White", "derived_ethnicity": "Not Hispanic or Latino", "derived_sex": "Male",
                             "applicant_age": "35-44"}
#: the field-to-basis table of addendum H3 section 5: basis, ECOA, FHA (age is ECOA only; ethnicity maps to national origin by convention)
BASIS: dict[str, tuple[str, bool, bool]] = {
    "derived_race": ("race_color", True, True),
    "derived_ethnicity": ("national_origin_nearest_UNVERIFIED", True, True),
    "derived_sex": ("sex", True, True),
    "applicant_age": ("age_ecoa_only", True, False),
}
FHA_DISPARATE_IMPACT = ("not assessed (disparate impact under the FHA only; gross HMDA disparities are not appropriate for "
                        "disproportionate adverse impact analysis, Interagency Procedures appendix, printed page 26)")
FHA_DISPARATE_IMPACT_AGE = "not applicable (age is a prohibited basis under ECOA only, not in 42 U.S.C. 3605(a))"


def attribute_legal(field: str) -> dict[str, Any]:
    basis, ecoa, fha = BASIS[field]
    return {"basis": basis, "ecoa": ecoa, "fha": fha, "theory": "comparative-evidence-of-disparate-treatment",
            "fha_disparate_impact": FHA_DISPARATE_IMPACT_AGE if field == "applicant_age" else FHA_DISPARATE_IMPACT,
            "note": t("Mapping taken from the research addendum H3 section 5; the ethnicity field maps to national origin by convention "
                      "(UNVERIFIED); no legal claim",
                      "Correspondencia tomada del adendum de investigación H3 sección 5; el campo de etnia corresponde a origen nacional "
                      "por convención (SIN VERIFICAR); sin afirmación legal")}


# --- the legal label (decision C4) and the licence (decision C7) ----------------------------------------------------------
QUOTES = {
    "reg_b": ("12 CFR 1002.6(a), as amended at 91 FR 21668 (2026-04-22, effective 2026-07-21)",
              "The Act does not provide that the 'effects test' applies for determining whether there is discrimination in violation of the Act."),
    "fha": ("91 FR 21620, recital of Texas Department of Housing & Community Affairs v. Inclusive Communities Project, Inc.",
            "the Supreme Court held that disparate-impact claims are cognizable under the Fair Housing Act (FHA)."),
    "procedures": ("Interagency Fair Lending Examination Procedures, August 2009, appendix, printed page 26",
                   "Gross HMDA denial or approval rate disparities are not appropriate for disproportionate adverse impact analysis because "
                   "they typically cannot be attributed to a specific policy or criterion."),
}


def legal_block() -> dict[str, Any]:
    def sentence(k: str) -> dict[str, Any]:
        return {"citation": QUOTES[k][0], "quote": QUOTES[k][1], "text": t(QUOTES[k][1])}

    return {"label": {"en": "no legal claim", "es": "sin afirmacion legal"}, "regulation_b": sentence("reg_b"),
            "fair_housing_act": sentence("fha"), "procedures": sentence("procedures"),
            "unconditional_rates_are": "indicators-only", "controlled_disparity_is": "approximation-of-comparative-evidence",
            "is_a_finding_of_violation": False}


PLATFORM_TERMS = ("As a work of the United States Government, this package (excluding any exceptions listed below) is in the public "
                  "domain within the United States. Additionally, we waive copyright and related rights in the work worldwide through "
                  "the CC0 1.0 Universal public domain dedication.")
MODIFIED_STATEMENT = "The publicly available data are modified to protect applicants' and borrowers' privacy"


def licence_block() -> dict[str, Any]:
    return {"status": "UNVERIFIED", "platform_terms": PLATFORM_TERMS,
            "platform_terms_cover": "the software package, not the published datasets", "modified_statement": MODIFIED_STATEMENT,
            "note": t("The HMDA data licence sentence is UNVERIFIED: no licence, copyright or terms of use for the data was found. The "
                      "views quote the platform software terms (they cover the software package, not the datasets) and the CFPB "
                      "statement that the public data are modified.",
                      "La frase de licencia de los datos HMDA está SIN VERIFICAR: no se encontró licencia, derechos de autor ni "
                      "términos de uso de los datos. Las vistas citan los términos del software de la plataforma (cubren el paquete "
                      "de software, no los conjuntos de datos) y la declaración de la CFPB de que los datos públicos están modificados.")}


# --- the decision convention (decision C3), the identity convention (V3), the recode of the debt-to-income field -----------
APPROVAL_CODES = (1, 2)
DENIAL_CODES = (3,)
EXCLUDED_CODES = (4, 5, 6, 7, 8)
ID_RULE = "<activity_year>-<row>"
DATE_RULE = "<activity_year>-12-31"
#: the six published bins of the debt-to-income field (addendum H1 2.4 and 2.5): the exact whole percents 36 to 49 are one bin here
DTI_BINS = ("<20%", "20%-<30%", "30%-<36%", "36%-49%", "50%-60%", ">60%")
DTI_LABELS = {"<20%": 0, "20%-<30%": 1, "30%-<36%": 2, "50%-60%": 4, ">60%": 5}

ACTION_NAMES = {1: "loan originated", 2: "application approved but not accepted", 3: "application denied",
                4: "application withdrawn by applicant", 5: "file closed for incompleteness", 6: "purchased loan",
                7: "preapproval request denied", 8: "preapproval request approved but not accepted"}

#: the nominal codes of the dictionary (addendum H1 2.4): a code outside them is refused
LOAN_TYPES = (1, 2, 3, 4)
LOAN_PURPOSES = (1, 2, 31, 32, 4, 5)
LIEN_STATUSES = (1, 2)
OCCUPANCY_TYPES = (1, 2, 3)
AGE_VALUES = (*GROUPS["applicant_age"], *NON_GROUPS["applicant_age"])

#: the nine permitted controls the schema enumerates (the controls HMDA publishes since 2018; credit score is absent)
CONTROLS = ("debt_to_income_ratio", "combined_loan_to_value_ratio", "income", "loan_amount", "property_value", "loan_type",
            "loan_purpose", "lien_status", "occupancy_type")
MISSING_CONTROLS = ("credit_score",)


def conventions_block() -> dict[str, Any]:
    return {
        "label": "convention",
        "outcome": {"approval_codes": list(APPROVAL_CODES), "denial_codes": list(DENIAL_CODES), "excluded_codes": list(EXCLUDED_CODES),
                    "note": t("Approval is action taken 1 (loan originated) and 2 (application approved but not accepted); denial is 3. "
                              "Codes 4 and 5 (withdrawn, closed for incompleteness) have no decision; 6 (purchased) and the "
                              "preapproval codes 7 and 8 are left out. No source classifies the codes: this is a convention. The "
                              "unconditional rates, their tests, the four-fifths flag and the situation test are computed on the fit "
                              "year of the pair; the rate-spread estimate uses the loans of codes 1 and 2.",
                              "La aprobación es la acción 1 (préstamo originado) y 2 (solicitud aprobada pero no aceptada); el rechazo "
                              "es 3. Los códigos 4 y 5 (retirada, archivo cerrado por estar incompleto) no tienen decisión; 6 (comprado) "
                              "y los códigos de preaprobación 7 y 8 se dejan fuera. Ninguna fuente clasifica los códigos: es una "
                              "convención. Las tasas incondicionales, sus pruebas, la marca de cuatro quintos y la prueba de situación se "
                              "calculan en el año de ajuste del par; la estimación del diferencial de tasa usa los préstamos de los "
                              "códigos 1 y 2.")},
        "dti_recode": {"bins": list(DTI_BINS),
                       "note": t("The debt-to-income field mixes exact whole percents (36 to 49) with bins; it is recoded to the six "
                                 "published bins, the exact values 36 to 49 forming one bin. A convention. The missing markers NA and "
                                 "Exempt are missing.",
                                 "El campo de deuda sobre ingreso mezcla porcentajes enteros exactos (36 a 49) con tramos; se recodifica a "
                                 "los seis tramos publicados, y los valores exactos 36 a 49 forman un tramo. Una convención. Los "
                                 "marcadores NA y Exempt son datos faltantes.")},
        "group_exclusion": t("The Joint, Not Available and Free Form Text Only categories are carried as their own groups and excluded "
                             "from the pairwise tests; a convention.",
                             "Las categorías Joint, Not Available y Free Form Text Only se llevan como grupos propios y se excluyen de "
                             "las pruebas por pares; una convención."),
        "identifiers": {"id": ID_RULE, "observation_date": DATE_RULE, "label": "convention",
                        "note": t("Public HMDA withholds the loan identifier and the application and action dates: id is the row "
                                  "position in the source file within its activity year, and the observation date is the activity "
                                  "year's last day. Both are conventions, not source values.",
                                  "El HMDA público omite el identificador del préstamo y las fechas de solicitud y de acción: id es la "
                                  "posición de la fila en el archivo fuente dentro de su año de actividad, y la fecha de observación es el "
                                  "último día del año de actividad. Ambas son convenciones, no valores de la fuente.")}}
