"""C01 side ladder S-6: reject inference on a sample with a known rejected population (the German twin).

An application scorecard is fitted on the applicants a legacy policy accepted, so the sample it learns from is selected. Reject
inference tries to repair that with the applicants the policy turned away, whose outcomes are never observed. It can only be
tested where the outcomes of the rejected are known, so the case simulates the legacy policy on a fully labelled population (the
1,000 German Credit applicants), hides the outcomes of those it rejects, fits each rung on what a lender would have, and scores it on
a held-out accept-all population whose outcomes are all known (the design Kozodoi et al. 2025 take with an unbiased accepted sample).

The rungs (references in ``RUNG_TEXT``), all on one penalised logistic learner so that only the treatment of the rejected differs:
the accepted-only model (the bias to repair), augmentation by the inverse acceptance probability, a hard cut-off, parcelling with
and without a prudence factor, fuzzy augmentation; the oracle trained on every outcome is the reference no lender can fit.

Four policies, one ``kappa`` each. ``mar`` (0) accepts on the model's inputs and noise, so the outcome plays no part once the inputs
are known (the accepted-only model is then nearly unbiased, the control). ``weak`` (0.25), ``moderate`` (0.5) and ``strong`` (1) add the
underwriter's private signal about the outcome, a judgement the model does not see: the case Hand and Henley (1993) and Crook and
Banasik (2004) say reject inference cannot reliably repair. The hypotheses ``verdicts`` judge ``PRIMARY`` (moderate). A first probe at
kappa = 1 alone let in 2.8 % defaulters against 30 % in the population, a book no lender has, so the strengths became this ladder
before any other regime was run; the design, the rungs and the hypotheses were not changed after that.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ..core.text import number, percent

RUNGS: tuple[str, ...] = ("oracle", "accepted-only", "augmentation", "hard-cutoff", "parcelling", "parcelling-prudent", "fuzzy")
ACCEPT_SHARE = 0.6        # the legacy policy accepts the best 60 % of the development applicants
TEST_SHARE = 0.3          # the accept-all population: 30 % of the rows, stratified, never seen by a policy
N_REPS = 100              # repetitions of split, policy and fit; the interval is over them
WEIGHT_FLOOR = 0.05       # augmentation: no applicant weighs more than 20 times
BANDS = 10                # parcelling: score bands
MIN_ACCEPTED = 10         # parcelling: accepted applicants a band needs for its own rate
PRUDENCE = 2.0            # parcelling-prudent: the rejected are assumed twice as bad as the accepted of their band (Siddiqi 2017)
C_INVERSE_PENALTY = 1.0   # the learner's L2 strength, fixed, never tuned
LEARNER = "scikit-learn LogisticRegression, L2 penalty, C = 1 (fixed, never tuned)"
BOOTSTRAP = 2000          # resamples of the repetitions behind every interval
LEVEL = 0.95
REGIMES: tuple[dict[str, Any], ...] = (
    {"id": "mar", "kappa": 0.0},
    {"id": "weak", "kappa": 0.25},
    {"id": "moderate", "kappa": 0.5},
    {"id": "strong", "kappa": 1.0},
)
#: the regime the hypotheses are judged on, fixed before it was run: a first probe at kappa = 1 let in 2.8 % defaulters against 30 %
#: in the population, which no lender's book looks like, so the strengths became a ladder and the middle one the judged regime
PRIMARY = "moderate"
#: the reduction of the bias a rung must reach for H2, and the AUC gain above which H3 fails
H2_REDUCTION = 0.25
H3_AUC_GAIN = 0.01


def _t(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


RUNG_TEXT: dict[str, dict[str, Any]] = {
    "oracle": {"title": _t("Oracle: every outcome known", "Oráculo: todos los resultados conocidos"),
               "short": _t("Oracle", "Oráculo"), "source": "reference, not a method a lender can run",
               "what": _t("Fitted on all development applicants with their true outcomes; the bound no reject inference can pass.",
                          "Ajustado con todos los solicitantes de desarrollo y sus resultados verdaderos; la cota que ninguna inferencia de rechazados puede pasar.")},
    "accepted-only": {"title": _t("Accepted only (the bias to repair)", "Solo aceptados (el sesgo por reparar)"),
                      "short": _t("Accepted only", "Solo aceptados"), "source": "the usual practice",
                      "what": _t("Fitted on the accepted applicants and their outcomes alone; the rejected are ignored.",
                                 "Ajustado solo con los solicitantes aceptados y sus resultados; los rechazados se ignoran.")},
    "augmentation": {"title": _t("Augmentation by the inverse acceptance probability", "Aumentación por el inverso de la probabilidad de aceptación"),
                     "short": _t("Augmentation", "Aumentación"), "source": "Banasik and Crook 2007; Crook and Banasik 2004",
                     "what": _t("An acceptance model is fitted on every applicant; each accepted applicant weighs 1/p, p floored at 0.05, so the accepted stand for the rejected like them.",
                                "Se ajusta un modelo de aceptación con todos los solicitantes; cada aceptado pesa 1/p, con p acotado abajo en 0,05, de modo que los aceptados representan a los rechazados parecidos."),},
    "hard-cutoff": {"title": _t("Hard cut-off", "Corte duro"), "short": _t("Hard cut-off", "Corte duro"),
                    "source": "Siddiqi 2017",
                    "what": _t("The accepted-only model scores the rejected; the riskiest are labelled bad, in the share the model itself expects (the mean of their PDs); the model is refitted on all.",
                               "El modelo de solo aceptados puntúa a los rechazados; los más riesgosos se etiquetan malos, en la fracción que el propio modelo espera (la media de sus PD); el modelo se reajusta con todos.")},
    "parcelling": {"title": _t("Parcelling", "Parcelación"), "short": _t("Parcelling", "Parcelación"),
                   "source": "Siddiqi 2017",
                   "what": _t("The rejected are split into ten score bands and given random outcomes at the bad rate of the accepted in their band (the model's mean PD where a band has fewer than ten accepted).",
                              "Los rechazados se reparten en diez tramos de puntaje y reciben resultados al azar con la tasa de malos de los aceptados de su tramo (la PD media del modelo si el tramo tiene menos de diez aceptados).")},
    "parcelling-prudent": {"title": _t("Parcelling with a prudence factor of 2", "Parcelación con factor de prudencia 2"),
                           "short": _t("Parcelling x2", "Parcelación x2"), "source": "Siddiqi 2017",
                           "what": _t("Parcelling with the rejected assumed twice as bad as the accepted of their band, capped at 1.",
                                      "Parcelación suponiendo a los rechazados el doble de malos que los aceptados de su tramo, con tope en 1.")},
    "fuzzy": {"title": _t("Fuzzy augmentation", "Aumentación difusa"), "short": _t("Fuzzy", "Difusa"),
              "source": "Siddiqi 2017",
              "what": _t("Each rejected applicant enters twice, as a bad weighing p and as a good weighing 1 - p, p the accepted-only PD.",
                         "Cada rechazado entra dos veces, como malo con peso p y como bueno con peso 1 - p, con p la PD del modelo de solo aceptados.")},
}

REGIME_TEXT: dict[str, dict[str, Any]] = {
    "mar": {"title": _t("Policy on the model's inputs (control)", "Política sobre las entradas del modelo (control)"),
            "short": _t("Inputs only", "Solo entradas"),
            "what": _t("Acceptance depends on the inputs and noise; once the inputs are known the outcome plays no part.",
                       "La aceptación depende de las entradas y de ruido; conocidas las entradas, el resultado no interviene.")},
    "weak": {"title": _t("Policy with a weak private signal (0.25)", "Política con una señal privada débil (0,25)"),
             "short": _t("Weak signal", "Señal débil"),
             "what": _t("Acceptance also depends on a judgement correlated with the outcome that the model does not see, at a quarter of the weight of the inputs.",
                        "La aceptación depende además de un juicio correlacionado con el resultado que el modelo no ve, con un cuarto del peso de las entradas.")},
    "moderate": {"title": _t("Policy with a moderate private signal (0.5), the judged regime", "Política con una señal privada moderada (0,5), el régimen juzgado"),
                 "short": _t("Moderate signal", "Señal moderada"),
                 "what": _t("The same judgement at half the weight of the inputs; the regime the hypotheses are judged on.",
                            "El mismo juicio con la mitad del peso de las entradas; el régimen sobre el que se juzgan las hipótesis.")},
    "strong": {"title": _t("Policy with a strong private signal (1)", "Política con una señal privada fuerte (1)"),
               "short": _t("Strong signal", "Señal fuerte"),
               "what": _t("The judgement weighs as much as the inputs: the accepted book is almost free of defaulters, a limit case.",
                          "El juicio pesa tanto como las entradas: la cartera aceptada casi no tiene incumplidores, un caso límite.")},
}


# ----------------------------------------------------------------------------------------------------------------------
# the design and the learner

def design(df: pd.DataFrame, features: tuple[str, ...], categorical: tuple[str, ...], fit_rows: np.ndarray) -> np.ndarray:
    """The design matrix of every row of ``df``: one-hot categories and standardised numbers, both fitted on ``fit_rows`` alone."""
    cats = [f for f in features if f in categorical]
    nums = [f for f in features if f not in categorical]
    parts = []
    if nums:
        sc = StandardScaler().fit(df.iloc[fit_rows][nums].to_numpy(dtype=float))
        parts.append(sc.transform(df[nums].to_numpy(dtype=float)))
    if cats:
        enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False).fit(df.iloc[fit_rows][cats].astype(str))
        parts.append(enc.transform(df[cats].astype(str)))
    return np.hstack(parts)


def _fit(Z: np.ndarray, y: np.ndarray, w: np.ndarray | None = None) -> LogisticRegression:
    return LogisticRegression(C=C_INVERSE_PENALTY, max_iter=5000).fit(Z, y, sample_weight=w)


def _pd(model: LogisticRegression, Z: np.ndarray) -> np.ndarray:
    return model.predict_proba(Z)[:, 1]


# ----------------------------------------------------------------------------------------------------------------------
# the legacy policy

def policy_z(Z: np.ndarray, y: np.ndarray) -> np.ndarray:
    """The legacy policy's view of the inputs: the standardised logit of a model fitted on every development outcome."""
    p = np.clip(_pd(_fit(Z, y), Z), 1e-6, 1 - 1e-6)
    eta = np.log(p / (1 - p))
    return (eta - eta.mean()) / eta.std()


def legacy_acceptance(z: np.ndarray, y: np.ndarray, kappa: float, share: float, rng: np.random.Generator) -> np.ndarray:
    """Accept the ``share`` of applicants with the lowest score ``u = z + kappa * standardised outcome + N(0, 1)``.

    ``kappa = 0`` is a policy on the inputs and noise, blind to the outcome; ``kappa > 0`` adds the underwriter's private signal.
    The noise is drawn first, so two policies with one seed share it.
    """
    noise = rng.normal(size=len(z))
    signal = (y - y.mean()) / y.std() if y.std() > 0 else np.zeros(len(z))
    u = z + kappa * signal + noise
    accepted = np.zeros(len(z), dtype=bool)
    accepted[np.argsort(u, kind="stable")[: int(round(share * len(z)))]] = True
    return accepted


# ----------------------------------------------------------------------------------------------------------------------
# the reject-inference rungs

def augmentation_weights(p_accept: np.ndarray) -> np.ndarray:
    """Banasik and Crook's weights: the inverse of the probability of being accepted, floored so no one weighs over 1/floor."""
    return 1.0 / np.maximum(np.asarray(p_accept, dtype=float), WEIGHT_FLOOR)


def hard_cutoff_labels(p0: np.ndarray) -> np.ndarray:
    """The riskiest rejected by the accepted-only PD are bad, in the share the model expects: round(mean PD x count)."""
    k = int(round(float(np.mean(p0)) * len(p0)))
    lab = np.zeros(len(p0), dtype=int)
    lab[np.argsort(-np.asarray(p0, dtype=float), kind="stable")[:k]] = 1
    return lab


def parcel_rates(p0: np.ndarray, accepted: np.ndarray, y: np.ndarray, *, prudence: float, bands: int = BANDS,
                 min_accepted: int = MIN_ACCEPTED) -> np.ndarray:
    """The bad rate each rejected applicant is given: the bad rate of the accepted in its score band times ``prudence``, capped at 1.

    Bands are deciles of the accepted-only PD over all development applicants (the PD needs no outcome). A band with fewer than
    ``min_accepted`` accepted applicants has no rate of its own and takes the model's mean PD of its rejected.
    """
    p0 = np.asarray(p0, dtype=float)
    edges = np.quantile(p0, np.linspace(0, 1, bands + 1)[1:-1])
    band = np.searchsorted(edges, p0, side="right")
    rate = np.empty(bands)
    for b in range(bands):
        acc = accepted & (band == b)
        rej = ~accepted & (band == b)
        if acc.sum() >= min_accepted:
            rate[b] = y[acc].mean()
        elif rej.any():
            rate[b] = p0[rej].mean()
        else:
            rate[b] = p0[band == b].mean() if (band == b).any() else 0.0
    return np.minimum(1.0, prudence * rate[band[~accepted]])


def parcel_labels(rates: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """One random outcome per rejected applicant at its parcel rate."""
    return (rng.random(len(rates)) < rates).astype(int)


def fuzzy_rows(p0: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fuzzy augmentation: every rejected applicant as two rows, bad with weight p and good with weight 1 - p."""
    p0 = np.asarray(p0, dtype=float)
    idx = np.repeat(np.arange(len(p0)), 2)
    label = np.tile([1, 0], len(p0))
    weight = np.stack([p0, 1.0 - p0], axis=1).ravel()
    return idx, label, weight


def repetition(Z_dev: np.ndarray, y_true: np.ndarray, accepted: np.ndarray, Z_test: np.ndarray,
               rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Every rung fitted on one development sample and scored on the accept-all population.

    ``y_true`` holds every development outcome; the rungs other than the oracle read it only at the accepted rows (the rejected rows
    are masked here, before anything is fitted), which tests/c01_reject holds by scrambling the rejected outcomes.
    """
    y_seen = np.where(accepted, y_true, -1)
    out: dict[str, np.ndarray] = {"oracle": _pd(_fit(Z_dev, y_true), Z_test)}
    base = _fit(Z_dev[accepted], y_seen[accepted])
    out["accepted-only"] = _pd(base, Z_test)
    rej = ~accepted
    p_acc = _pd(_fit(Z_dev, accepted.astype(int)), Z_dev[accepted])
    out["augmentation"] = _pd(_fit(Z_dev[accepted], y_seen[accepted], augmentation_weights(p_acc)), Z_test)
    p0_all = _pd(base, Z_dev)
    p0_rej = p0_all[rej]
    lab = hard_cutoff_labels(p0_rej)
    out["hard-cutoff"] = _pd(_fit(np.vstack([Z_dev[accepted], Z_dev[rej]]), np.concatenate([y_seen[accepted], lab])), Z_test)
    for rung, prudence in (("parcelling", 1.0), ("parcelling-prudent", PRUDENCE)):
        labels = parcel_labels(parcel_rates(p0_all, accepted, y_seen, prudence=prudence), rng)
        out[rung] = _pd(_fit(np.vstack([Z_dev[accepted], Z_dev[rej]]), np.concatenate([y_seen[accepted], labels])), Z_test)
    idx, label, weight = fuzzy_rows(p0_rej)
    Zr = Z_dev[rej]
    out["fuzzy"] = _pd(_fit(np.vstack([Z_dev[accepted], Zr[idx]]), np.concatenate([y_seen[accepted], label]),
                            np.concatenate([np.ones(int(accepted.sum())), weight])), Z_test)
    return {r: out[r] for r in RUNGS}


# ----------------------------------------------------------------------------------------------------------------------
# the statistics

def interval(values: np.ndarray, seed: int, level: float = LEVEL, resamples: int = BOOTSTRAP) -> tuple[float, float, float]:
    """The mean of the repetitions and the percentile interval of that mean over bootstrap resamples of the repetitions."""
    v = np.asarray(values, dtype=float)
    idx = np.random.default_rng(seed).integers(0, len(v), size=(resamples, len(v)))
    means = v[idx].mean(axis=1)
    a = (1 - level) / 2
    return float(v.mean()), float(np.quantile(means, a)), float(np.quantile(means, 1 - a))


def reduction(b0: np.ndarray, br: np.ndarray, seed: int, level: float = LEVEL,
              resamples: int = BOOTSTRAP) -> tuple[float, float, float]:
    """The reduction of the bias: 1 - |mean bias of the rung| / |mean bias of the accepted-only model|, with its percentile
    interval over paired bootstrap resamples of the repetitions (both models see the same split, policy and noise)."""
    b0 = np.asarray(b0, dtype=float)
    br = np.asarray(br, dtype=float)
    idx = np.random.default_rng(seed).integers(0, len(b0), size=(resamples, len(b0)))
    ratio = 1.0 - np.abs(br[idx].mean(axis=1)) / np.maximum(np.abs(b0[idx].mean(axis=1)), 1e-12)
    a = (1 - level) / 2
    point = 1.0 - abs(float(br.mean())) / max(abs(float(b0.mean())), 1e-12)
    return float(point), float(np.quantile(ratio, a)), float(np.quantile(ratio, 1 - a))


def _stat(mean_lo_hi: tuple[float, float, float]) -> dict[str, float]:
    m, lo, hi = mean_lo_hi
    return {"mean": m, "lo": lo, "hi": hi}


def run(df: pd.DataFrame, features: tuple[str, ...], categorical: tuple[str, ...], *, seed: int, reps: int = N_REPS,
        population: str = "labelled population") -> dict[str, Any]:
    """The experiment on the fully labelled population ``df`` (a ``target`` column): ``reps`` repetitions per policy."""
    y_all = df["target"].to_numpy(dtype=int)
    n = len(df)
    regimes_out = []
    n_dev = n_test = 0
    for r_i, regime in enumerate(REGIMES):
        bias = {r: np.empty(reps) for r in RUNGS}
        auc = {r: np.empty(reps) for r in RUNGS}
        brier = {r: np.empty(reps) for r in RUNGS}
        acc_rate, rej_rate, pop_rate = np.empty(reps), np.empty(reps), np.empty(reps)
        for rep in range(reps):
            rng = np.random.default_rng([seed, 6001, r_i, rep])
            dev, test = train_test_split(np.arange(n), test_size=TEST_SHARE, stratify=y_all, random_state=int(seed + 100 * rep))
            n_dev, n_test = len(dev), len(test)
            Z = design(df, features, categorical, dev)
            z = policy_z(Z[dev], y_all[dev])
            accepted = legacy_acceptance(z, y_all[dev], regime["kappa"], ACCEPT_SHARE, rng)
            preds = repetition(Z[dev], y_all[dev], accepted, Z[test], rng)
            y_t = y_all[test]
            for rung, p in preds.items():
                bias[rung][rep] = float(p.mean() - y_t.mean())
                auc[rung][rep] = float(roc_auc_score(y_t, p))
                brier[rung][rep] = float(brier_score_loss(y_t, p))
            acc_rate[rep] = y_all[dev][accepted].mean()
            rej_rate[rep] = y_all[dev][~accepted].mean()
            pop_rate[rep] = y_all[dev].mean()
        rungs_out = []
        for k, rung in enumerate(RUNGS):
            s = seed + 31 * r_i + k
            red = reduction(bias["accepted-only"], bias[rung], s)
            beats = float(np.mean(np.abs(bias[rung]) < np.abs(bias["accepted-only"])))
            rungs_out.append({
                "id": rung,
                "bias": _stat(interval(bias[rung], s)),
                "abs_bias": float(np.abs(bias[rung]).mean()),
                "reduction": {"value": red[0], "lo": red[1], "hi": red[2]},
                "beats_share": 0.0 if rung == "accepted-only" else beats,
                "auc": _stat(interval(auc[rung], s)),
                "auc_vs_accepted_only": _stat(interval(auc[rung] - auc["accepted-only"], s)),
                "brier": _stat(interval(brier[rung], s)),
                "reps": {"bias": [round(float(x), 6) for x in bias[rung]], "auc": [round(float(x), 6) for x in auc[rung]]},
            })
        regimes_out.append({
            "id": regime["id"], "kappa": regime["kappa"], "title": REGIME_TEXT[regime["id"]]["title"],
            "short_title": REGIME_TEXT[regime["id"]]["short"], "what": REGIME_TEXT[regime["id"]]["what"],
            "default_rate": {"population": float(pop_rate.mean()), "accepted": float(acc_rate.mean()), "rejected": float(rej_rate.mean())},
            "rungs": rungs_out,
        })
    result: dict[str, Any] = {
        "design": {"population": population, "learner": LEARNER, "n_rows": n, "n_dev": n_dev, "n_test": n_test, "reps": reps, "accept_share": ACCEPT_SHARE, "test_share": TEST_SHARE,
                   "weight_floor": WEIGHT_FLOOR, "bands": BANDS, "min_accepted": MIN_ACCEPTED, "prudence": PRUDENCE,
                   "c_inverse_penalty": C_INVERSE_PENALTY, "bootstrap": BOOTSTRAP, "level": LEVEL,
                   "h2_reduction": H2_REDUCTION, "h3_auc_gain": H3_AUC_GAIN},
        "rungs": [{"id": r, "title": RUNG_TEXT[r]["title"], "short_title": RUNG_TEXT[r]["short"], "source": RUNG_TEXT[r]["source"],
                   "what": RUNG_TEXT[r]["what"]} for r in RUNGS],
        "regimes": regimes_out,
    }
    result["hypotheses"] = verdicts(result)
    return result


# ----------------------------------------------------------------------------------------------------------------------
# the hypotheses, written before the run and reported whatever it shows

def _regime(result: dict[str, Any], rid: str) -> dict[str, dict[str, Any]]:
    return {r["id"]: r for g in result["regimes"] if g["id"] == rid for r in g["rungs"]}


def _signed(x: float, d: int, lang: str) -> str:
    return ("+" if x > 0 else "") + number(x, d, lang=lang)


def verdicts(result: dict[str, Any]) -> list[dict[str, Any]]:
    """H1 to H3 evaluated on the measured numbers of the judged regime; each states what it asserts, its value and the outcome."""
    mnar = _regime(result, PRIMARY)
    ao = mnar["accepted-only"]
    reducers = {k: v for k, v in mnar.items() if k not in ("oracle", "accepted-only")}
    best = max(reducers.values(), key=lambda r: r["reduction"]["value"]) if reducers else None
    top_gain = max(reducers.values(), key=lambda r: r["auc_vs_accepted_only"]["mean"]) if reducers else None
    out: list[dict[str, Any]] = []

    h1 = ao["bias"]["hi"] < 0
    b = ao["bias"]
    out.append({
        "id": "H1", "holds": bool(h1), "value": b["mean"], "lo": b["lo"], "hi": b["hi"], "rung": "accepted-only",
        "statement": _t("Under the moderate private signal the accepted-only model under-states the default rate of the full population: the 95 % interval of its level bias lies below 0.",
                        "Con la señal privada moderada, el modelo de solo aceptados subestima la tasa de incumplimiento de la población completa: el intervalo 95 % de su sesgo de nivel queda bajo 0."),
        "outcome": _t(f"{'Holds' if h1 else 'Does not hold'}: the level bias is {_signed(b['mean'] * 100, 2, 'en')} points (95 % interval {_signed(b['lo'] * 100, 2, 'en')} to {_signed(b['hi'] * 100, 2, 'en')}).",
                      f"{'Se cumple' if h1 else 'No se cumple'}: el sesgo de nivel es {_signed(b['mean'] * 100, 2, 'es')} puntos (intervalo 95 % de {_signed(b['lo'] * 100, 2, 'es')} a {_signed(b['hi'] * 100, 2, 'es')}).")})

    if best is None:
        raise ValueError("verdicts need at least one reject-inference rung in the judged regime")
    r = best["reduction"]
    h2 = r["value"] >= H2_REDUCTION and r["lo"] > 0
    out.append({
        "id": "H2", "holds": bool(h2), "value": r["value"], "lo": r["lo"], "hi": r["hi"], "rung": best["id"],
        "statement": _t(f"At least one rung cuts the absolute level bias by {percent(H2_REDUCTION, 0, lang='en')} or more, with a 95 % interval above 0.",
                        f"Al menos un peldaño reduce el sesgo de nivel absoluto en {percent(H2_REDUCTION, 0, lang='es')} o más, con intervalo 95 % sobre 0."),
        "outcome": _t(f"{'Holds' if h2 else 'Does not hold'}: the best rung is {RUNG_TEXT.get(best['id'], {'short': _t(best['id'], best['id'])})['short']['en']}, {percent(r['value'], 1, lang='en')} (95 % interval {percent(r['lo'], 1, lang='en')} to {percent(r['hi'], 1, lang='en')}).",
                      f"{'Se cumple' if h2 else 'No se cumple'}: el mejor peldaño es {RUNG_TEXT.get(best['id'], {'short': _t(best['id'], best['id'])})['short']['es']}, {percent(r['value'], 1, lang='es')} (intervalo 95 % de {percent(r['lo'], 1, lang='es')} a {percent(r['hi'], 1, lang='es')}).")})

    g = top_gain["auc_vs_accepted_only"]
    h3 = g["mean"] <= H3_AUC_GAIN
    out.append({
        "id": "H3", "holds": bool(h3), "value": g["mean"], "lo": g["lo"], "hi": g["hi"], "rung": top_gain["id"],
        "statement": _t(f"No rung ranks the full population better than the accepted-only model by more than {number(H3_AUC_GAIN, 2, lang='en')} AUC (the literature finds little ranking gain).",
                        f"Ningún peldaño ordena a la población completa mejor que el modelo de solo aceptados en más de {number(H3_AUC_GAIN, 2, lang='es')} de AUC (la literatura halla poca ganancia de ordenamiento)."),
        "outcome": _t(f"{'Holds' if h3 else 'Does not hold'}: the largest gain is {RUNG_TEXT.get(top_gain['id'], {'short': _t(top_gain['id'], top_gain['id'])})['short']['en']}, {_signed(g['mean'], 4, 'en')} AUC (95 % interval {_signed(g['lo'], 4, 'en')} to {_signed(g['hi'], 4, 'en')}).",
                      f"{'Se cumple' if h3 else 'No se cumple'}: la mayor ganancia es {RUNG_TEXT.get(top_gain['id'], {'short': _t(top_gain['id'], top_gain['id'])})['short']['es']}, {_signed(g['mean'], 4, 'es')} de AUC (intervalo 95 % de {_signed(g['lo'], 4, 'es')} a {_signed(g['hi'], 4, 'es')}).")})
    return out
