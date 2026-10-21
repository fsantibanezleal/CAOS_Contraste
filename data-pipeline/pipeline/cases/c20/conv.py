"""The named parameters, the conventions and the texts of C20 (decision V6 of the U14 sizing: the approved values).

Every value here is a convention, never a regulatory threshold (dossier 06 I.6 l.1268-1270). The approved parameter values are the
ones `tests/contracts_u14/semantics.py` checks every document against (`APPROVED_PARAMS`); a test pins this copy to
`tests/contracts_u14/values.py` (the bases) and to the semantics (the values).
"""
from __future__ import annotations

from typing import Any

CASE_ID = "C20"
SEED = 42
SGCD_COMMIT = "8403fa9048f7159d51a0cec5a2d9a2e9712662bd"
SGCD_QUOTE = ("It is provided for research and benchmarking only and must not be used for real-world credit scoring or any "
              "production decision-making about individuals.")


def t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


PERTURBATION_GRID = [0.05, 0.1, 0.25, 0.5, 1.0]
PRESET_EPS = 0.1
PERTURBATION_TOLERANCE = 0.02
N_SEEDS = 20
N_BOOTSTRAP_REFITS = 100
OVERFIT_TOLERANCE = 0.05
WEAK_SPOT_MULTIPLE = 2.0
SHIFT_SCORE = "resemblance-classifier-probability"
WORST_SUBSAMPLE_SHARE = 0.10
REJECT_SHARE = 0.20
CONFORMAL_ALPHA = 0.10
TOP_K = 4

#: (name, value, unit, basis); the bases are those of the approved list (decision V6)
PARAMETERS: tuple[tuple[str, Any, str, str], ...] = (
    ("perturbation_grid", PERTURBATION_GRID, "multiple of each feature's standard deviation",
     "Noise scales for the perturbation robustness grid (06 C.7 l.1009-1012 gives the construction, no values)."),
    ("perturbation_tolerance", PERTURBATION_TOLERANCE, "AUC points",
     "Degradation of AUC tolerated at the preset scale 0.1; about 2.5 standard errors of an AUC on the Taiwan holdout (about 6,000 holdout rows)."),
    ("n_seeds", N_SEEDS, "retraining seeds",
     "Seeds of the seed sweep (06 I.1 l.1191 gives none); 20 gives a standard deviation of the AUC with a relative error near 16 percent."),
    ("n_bootstrap_refits", N_BOOTSTRAP_REFITS, "bootstrap refits", "Refits of the reason-code stability (04 J.2 l.881-883 gives none)."),
    ("overfit_tolerance", OVERFIT_TOLERANCE, "AUC points",
     "Train minus test AUC gap beyond which the overfit flag is raised (06 C.7 l.1016-1018 gives no value)."),
    ("weak_spot_multiple", WEAK_SPOT_MULTIPLE, "multiple of the average test error",
     "k: a slice is a weak spot when its test error exceeds k times the average (06 C.7 l.1016-1018)."),
    ("shift_score", SHIFT_SCORE, "name of the score",
     "The shift score ranking subsamples; a classifier of development against evaluation rows (06 C.7 l.1048-1051 resemblance AUC)."),
    ("worst_subsample_share", WORST_SUBSAMPLE_SHARE, "share of the evaluation rows", "The dossier's example is the worst 10 percent (06 C.7 l.1013-1014)."),
    ("decision_cutoff_reject_share", REJECT_SHARE, "share of baseline decisions declined",
     "The cut-off is the baseline score quantile that declines this share; held fixed under every shift (decision Q10)."),
)


def parameters_block() -> list[dict[str, Any]]:
    return [{"name": n, "value": v, "unit": u, "label": "convention", "basis": b} for n, v, u, b in PARAMETERS]


def sgcd_notice() -> dict[str, Any]:
    return {"kind": "dataset-card-prohibition", "quote": SGCD_QUOTE, "commit": SGCD_COMMIT,
            "text": t("The SGCD dataset card forbids real-world credit scoring and production decisions about individuals",
                      "La ficha del conjunto SGCD prohíbe el scoring de crédito real y las decisiones de producción sobre personas")}


def impact_cutoff() -> dict[str, Any]:
    return {"rule": "reject-worst-share-of-baseline-scores", "reject_share": REJECT_SHARE, "label": "convention"}
