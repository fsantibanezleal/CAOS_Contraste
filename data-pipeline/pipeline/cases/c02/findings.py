"""The findings of a C02 document: statistical findings about its own test rows, and the stated limits of the case.

The rules are C01's severity policy in its direction (the level of the PD weighs more than its fit across the range, which at thousands
of obligors rejects for deviations too small to matter): a red row sets the first severity, an amber row the second. A finding cites only
rows of its own document (``test_id@model@segment``) or a ``design:`` limit; the manifest builder checks that at write.
"""
from __future__ import annotations

from typing import Any

from ...core import text
from ..c01_ladder import SHORT_TITLES
from .conventions import t

#: the PSI below which the conventional band calls a shift small (the 0.10/0.25 rule of thumb the tests' notes quote)
PSI_CONVENTION = 0.10


def _short(model_id: str, lang: str) -> str:
    """A model by its short title: the id without the file's prefix (h1-, pooled-) names the rung (U16-R2b c03 B3)."""
    bare = model_id.split("-", 1)[1] if model_id.split("-", 1)[0] in ("h1", "h2", "h3", "h4", "h5", "pooled") else model_id
    return SHORT_TITLES.get(bare, {"en": bare, "es": bare})[lang]

#: (finding id, test ids, severity when a row is red, when amber, English title, Spanish title)
RULES = (
    ("F-CALIBRATION-LEVEL", ("pd.jeffreys", "pd.binomial"), "S2", "S3",
     "The mean PD of {models} does not match the observed default rate of the holdout",
     "La PD media de {models} no coincide con la tasa de incumplimiento observada en la muestra reservada"),
    ("F-CALIBRATION-FIT", ("pd.hosmer_lemeshow",), "S3", "S4",
     "The Hosmer-Lemeshow test flags the fit of the PD across the range for {models}",
     "La prueba de Hosmer-Lemeshow alerta el ajuste de la PD a lo largo del rango para {models}"),
    # a PSI row's light is its chi-square p-value: at thousands of firms a PSI far below the 0.10 convention is red, so the title says a
    # detectable shift with the PSI it rests on and its size, never that the distribution "moved" (U16-R4 c03 n5)
    ("F-STABILITY", ("stability.psi",), "S2", "S3",
     "The holdout PD distribution shifts detectably against the training slice for {models} (PSI up to {psi}{small}; the light is the chi-square p-value)",
     "La distribución de la PD de la muestra reservada se desplaza de forma detectable respecto del tramo de entrenamiento para {models} (PSI de hasta {psi}{small}; la luz es el valor p de chi-cuadrado)"),
    ("F-OVERFIT", ("ml.overfit",), "S3", "S3",
     "The train minus holdout AUC gap exceeds the overfit tolerance for {models}",
     "La brecha de AUC entre entrenamiento y muestra reservada supera la tolerancia de sobreajuste para {models}"),
)
LIMITS = (
    ("F-NO-OUT-OF-TIME", "S4", "accepted", "design:no-date",
     "No out-of-time validation is possible: the files carry no date and the holdout is a random stratified one",
     "No es posible validar fuera del tiempo: los archivos no traen fecha y la muestra reservada es estratificada al azar"),
    ("F-PAPER-READING", "S4", "accepted", "design:paper-reading-unverified",
     "The horizon mapping follows the UCI page; the reading of the source paper is UNVERIFIED against Zieba, Tomczak and Tomczak 2016",
     "La correspondencia de horizontes sigue la página de UCI; la lectura del artículo fuente está SIN VERIFICAR contra Zieba, Tomczak y Tomczak 2016"),
    ("F-FIRM-OVERLAP", "S4", "accepted", "design:firm-overlap-unknown",
     "The firm overlap across the five files is unknown, so pooled and transfer results may be flattered by repeated firms",
     "Se desconoce el solapamiento de empresas entre los cinco archivos, así que los resultados agrupados y de transferencia pueden estar "
     "favorecidos por empresas repetidas"),
)


def key(r: dict[str, Any]) -> str:
    return f"{r['test_id']}@{r['model_id']}@{r['segment']}"


def build(test_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for fid, ids, red, amber, en, es in RULES:
        hit = [r for r in test_rows if r["test_id"] in ids and r["model_id"] and r["light"] in ("red", "amber")]
        if not hit:
            continue
        ids = sorted({r["model_id"] for r in hit})
        models_en, models_es = (", ".join(_short(m, lang) for m in ids) for lang in ("en", "es"))
        sev = red if any(r["light"] == "red" for r in hit) else amber
        psi = max((r["statistic"] for r in hit if r["statistic"] is not None), default=None) if fid == "F-STABILITY" else None
        fill = {"en": {}, "es": {}}
        if psi is not None:
            small = psi < PSI_CONVENTION
            fill = {lang: {"psi": text.number(psi, 4, lang=lang),
                           "small": ({"en": ", a small change below the 0.10 convention", "es": ", un cambio pequeño bajo la convención de 0,10"}[lang]
                                     if small else "")} for lang in ("en", "es")}
        out.append({"id": fid, "severity": sev, "status": "open", "evidence": sorted({key(r) for r in hit}),
                    "title": t(en.format(models=models_en, **fill["en"]), es.format(models=models_es, **fill["es"]))})
    gap = [r for r in test_rows if r["test_id"] == "disc.delong" and r["light"] in ("red", "amber") and r["extras"]["difference"] > 0]
    if gap:
        ids = sorted({r["model_id"] for r in gap})
        sev = "S3" if any(r["light"] == "red" for r in gap) else "S4"
        out.append({"id": "F-CHALLENGER-GAP", "severity": sev, "status": "open", "evidence": sorted({key(r) for r in gap}),
                    "title": t(f"A paired DeLong test supports {', '.join(_short(m, 'en') for m in ids)} over the P1 scorecard: the champion is not the best rung",
                               f"Una prueba de DeLong pareada respalda a {', '.join(_short(m, 'es') for m in ids)} sobre la tarjeta de puntuación P1: el campeón no es el mejor peldaño")})
    for fid, sev, status, ev, en, es in LIMITS:
        out.append({"id": fid, "severity": sev, "status": status, "evidence": [ev], "title": t(en, es)})
    return out
