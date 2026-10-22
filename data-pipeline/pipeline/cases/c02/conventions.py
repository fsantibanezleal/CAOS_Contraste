"""The named conventions, the files and the vocabulary of C02 (decisions Q9, Q10 and Q14 of the U14 sizing, V6 of the S review).

Everything here is a statement the documents repeat. Every value that the sources do not give is a *named parameter*: it is written
with its value, its basis and the label "convention", and the schema (``docs/contracts/schemas/c02/``) pins the labels, so a drift
between this module and the contract fails the validation of every document. Nothing here is regulatory.
"""
from __future__ import annotations

from typing import Any

from ...io import polish


def t(en: str, es: str | None = None) -> dict[str, str]:
    """A bilingual text; a quotation keeps its English wording in both languages."""
    return {"en": en, "es": es if es is not None else en}


# --- the files ---------------------------------------------------------------------------------------------------------
#: the publisher's layout lives in ``pipeline/io/polish.py`` (decision G19): the zip, the horizons (the horizon of n years ahead reads the
#: file {6-n}year, decision G21), the counts the UCI page gives and the 64 ratio names
SOURCE_ID = polish.SOURCE_ID
ZIP_NAME = polish.ZIP_NAME
HORIZONS = polish.HORIZONS
POOLED = "pooled"
FILE_COUNTS = polish.FILE_COUNTS
expected_counts = polish.expected_counts
ATTRIBUTES = polish.ATTRIBUTES
HORIZON_FEATURE = "horizon_years"

# --- the ladder: model ids, the rung code each carries in the documents -----------------------------------------------------
#: the ids of ``cases/c01_ladder.fit_ladder`` and the rung codes of the schema (P2 is split into P2a and P2b here)
RUNG_CODE: dict[str, str] = {
    "P0-constant": "P0", "P0-single": "P0", "P1-scorecard": "P1", "P2a-l1": "P2a", "P2b-pltr": "P2b", "P3-ebm": "P3",
    "P4-lightgbm": "P4", "P4-xgboost": "P4",
}
#: the rungs whose battery the documents carry; P0-constant is fitted and recorded in the models document, but a constant PD has no
#: risk groups, so the Hosmer-Lemeshow test of the schema is undefined for it and no number stands in
BATTERY_RUNGS: tuple[str, ...] = ("P0-single", "P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm", "P4-xgboost")
#: the rung per code that the transfer matrix scores (the cells carry the code only, so one model per code)
TRANSFER_RUNGS: tuple[str, ...] = ("P0-single", "P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm")
CHAMPION = "P1-scorecard"
#: the learned rungs compared with the champion in the challenger table
CHALLENGERS: tuple[str, ...] = ("P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm", "P4-xgboost")

# --- the named parameters the main session approved (decision V6, 2026-10-19) ---------------------------------------------
OVERFIT_TOLERANCE = 0.05
N_BOOT = 1000          # paired-bootstrap resamples of the challenger Brier difference (a convention; the engine default level 0.95)
BOOT_SEED_OFFSET = 7919
MISSING_INDICATOR_SHARE = 0.05   # a ratio with at least this share of missing values in the training slice gets a missing indicator
GRADE_NOTCHES = 2      # the grade distance counted as a disagreement (engine-ml-api conventions table)
LGD = 0.45             # the illustrative loss given default of the Impact block (the Basel foundation senior unsecured value, an assumption)
CUTOFF_NOTE = "undiscounted (effective interest rate 0), exposure at default 1"


def parameters() -> list[dict[str, Any]]:
    """The named parameters of the C02 documents: the overfit tolerance is the only one the case uses (the schema allows it alone)."""
    return [{"name": "overfit_tolerance", "value": OVERFIT_TOLERANCE, "unit": "AUC points", "label": "convention",
             "basis": "Train minus test AUC gap beyond which the overfit flag is raised (06 C.7 l.1016-1018 gives no value); about 1.5 to 3 "
                      "standard errors of an AUC on the Polish holdouts (271 to 515 events per file), approved as decision V6"}]


# --- the texts every document repeats ----------------------------------------------------------------------------------------
POOLED_EVENT = t("Bankruptcy of the company within the horizon of its file (h1 to h5, stacked with a horizon indicator)",
                 "Quiebra de la empresa dentro del horizonte de su archivo (h1 a h5, apilados con un indicador de horizonte)")


def event_definition(years: int, file: str) -> dict[str, str]:
    """The event of a horizon document, with the file it read beside the horizon (decision G21)."""
    return t(f"Bankruptcy of the company within {years} year{'s' if years > 1 else ''} of the financial statements (the class label of the file {file})",
             f"Quiebra de la empresa dentro de {years} año{'s' if years > 1 else ''} de los estados financieros (la etiqueta de clase del archivo {file})")


OVERLAP_CAVEAT = t(
    "The five files are stacked with a horizon indicator. The UCI page gives no firm identifier and no date, so whether a company appears "
    "in several files is unknown (UNVERIFIED, 08 l.855-856). No feature vector is shared by two files, but a company's ratios change from "
    "year to year, so that is not evidence that firms do not repeat. A pooled score may therefore be flattered by repeated firms.",
    "Los cinco archivos se apilan con un indicador de horizonte. La página de UCI no da identificador de empresa ni fecha, de modo que no "
    "se sabe si una empresa aparece en varios archivos (SIN VERIFICAR, 08 l.855-856). Ningún vector de variables se repite entre dos "
    "archivos, pero las razones de una empresa cambian de un año al siguiente, así que eso no es evidencia de que las empresas no se "
    "repitan. Un puntaje agrupado puede por tanto estar favorecido por empresas repetidas.")
TRANSFER_REASON = t(
    "A rung fitted on the training slice of one file and scored on the holdout of another. The firm overlap across the files is unknown, "
    "so a transfer AUC may be inflated by firms that repeat; the block is exploratory and no out-of-time claim is made.",
    "Un peldaño ajustado en el tramo de entrenamiento de un archivo y puntuado en la muestra reservada de otro. El traslape de empresas "
    "entre archivos se desconoce, de modo que el AUC de traslado puede estar inflado por empresas repetidas; el bloque es exploratorio y "
    "no se afirma nada fuera del tiempo.")
TERM_STRUCTURE_REASON = t(
    "The event rates of the five files read as a cumulative PD (cumulative = 1 - product of (1 - hazard)). The files may not draw one "
    "population and their firm overlap is unknown, so the structure is exploratory (decision Q9).",
    "Las tasas de evento de los cinco archivos leídas como una PD acumulada (acumulada = 1 - producto de (1 - riesgo)). Los archivos "
    "pueden no provenir de una sola población y su traslape de empresas se desconoce, así que la estructura es exploratoria (decisión Q9).")
IMPACT_REASON = t(
    "The 12-month and lifetime expected credit loss of one unit of exposure under the horizon PDs of the term-structure block (the five file event rates); an "
    "illustration of how far the horizon moves a provision, not a provision (decision Q10). The loss given default is an assumption.",
    "La pérdida crediticia esperada a 12 meses y de vida de una unidad de exposición bajo las PD por horizonte del bloque de estructura temporal (las cinco tasas de evento de los archivos); una "
    "ilustración de cuánto mueve el horizonte a una provisión, no una provisión (decisión Q10). La pérdida dado el incumplimiento es un "
    "supuesto.")
TERM_SOURCE = "engine-provisions-api from_cumulative and lifetime_pd_backtest (04 E.2 l.479-497)"

# --- the date convention of contract 1 -----------------------------------------------------------------------------------------
#: contract 1 requires an observation date; the files carry none (the UCI page gives the span 2000 to 2013 only). The reader writes the
#: end of the span as a labelled placeholder and the case makes no temporal claim from it.
OBSERVATION_DATE = "2013-12-31"
OBSERVATION_DATE_NOTE = t(
    "The files carry no date. Contract 1 requires an observation date, so the reader writes 2013-12-31, the end of the span the UCI page "
    "gives (2000 to 2013), as a named convention; no out-of-time claim and no temporal order rests on it.",
    "Los archivos no traen fecha. El contrato 1 exige una fecha de observación, así que el lector escribe 2013-12-31, el final del período "
    "que da la página de UCI (2000 a 2013), como convención con nombre; ningún reclamo fuera del tiempo ni orden temporal descansa en ella.")

MAPPING_NOTE = t(
    "The horizon of a document is the dataset's own definition (decision G21): the UCI page describes the file named kyear as the financial "
    "rates of the k-th year of the forecasting period with the class label 'bankruptcy status after' 6 - k years, so the horizon of n years "
    "ahead reads the file {6-n}year (h1 reads 5year, h5 reads 1year). The scorecard's holdout AUC falls with the horizon under this mapping "
    "and rises with it under the file name.",
    "El horizonte de un documento es la definición del propio conjunto de datos (decisión G21): la página de UCI describe el archivo kyear "
    "como las razones financieras del k-ésimo año del período de pronóstico con la etiqueta 'estado de quiebra después de' 6 - k años, así "
    "que el horizonte de n años hacia adelante lee el archivo {6-n}year (h1 lee 5year, h5 lee 1year). El AUC de la scorecard en la muestra "
    "reservada baja con el horizonte bajo esta correspondencia y sube con él bajo el nombre del archivo.")
PAPER_READING = t(
    "The mapping follows the UCI page; the reading of the source paper (Zieba, Tomczak and Tomczak 2016) is UNVERIFIED against Zieba, "
    "Tomczak and Tomczak 2016, which the bake did not open.",
    "La correspondencia sigue la página de UCI; la lectura del artículo fuente (Zieba, Tomczak y Tomczak 2016) está SIN VERIFICAR contra "
    "Zieba, Tomczak and Tomczak 2016, que el bake no abrió.")
