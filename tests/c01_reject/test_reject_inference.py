"""S-6: reject inference on a sample with a known rejected population (the German twin).

The method (pipeline/cases/c01_reject.py) simulates a legacy acceptance policy on a fully labelled population, trains each
reject-inference rung on the accepted applicants only, and scores it on a held-out accept-all population whose outcomes are
all known. These tests hold the mechanics (no rung reads a rejected label, each rung does what its source says) and the
statistics (the interval and the reduction); the committed result is held in test_reject_document.py.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from pipeline.cases import c01_reject as rj

FEATURES = ("x1", "x2", "x3", "grp")
CATEGORICAL = ("grp",)


def population(n: int = 4000, seed: int = 3) -> pd.DataFrame:
    """A known-truth population: P(default | x) is a logit of four inputs, one of them categorical."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"x1": rng.normal(size=n), "x2": rng.normal(size=n), "x3": rng.integers(1, 5, size=n).astype(float),
                       "grp": rng.choice(["a", "b", "c"], size=n)})
    eta = -1.0 + 0.9 * df["x1"] + 0.5 * df["x2"] + 0.3 * (df["x3"] - 2.5) + df["grp"].map({"a": 0.0, "b": 0.4, "c": -0.3})
    df["target"] = (rng.random(n) < 1 / (1 + np.exp(-eta))).astype(int)
    return df


@pytest.fixture(scope="module")
def pop() -> pd.DataFrame:
    return population()


def split(pop: pd.DataFrame, seed: int):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(pop))
    test, dev = idx[: len(pop) * 3 // 10], idx[len(pop) * 3 // 10:]
    return dev, test


def one(pop: pd.DataFrame, kappa: float, seed: int, y_dev: np.ndarray | None = None):
    dev, test = split(pop, seed)
    Z = rj.design(pop, FEATURES, CATEGORICAL, dev)
    y = pop["target"].to_numpy()
    rng = np.random.default_rng(seed + 1)
    z = rj.policy_z(Z[dev], y[dev])
    accepted = rj.legacy_acceptance(z, y[dev], kappa, rj.ACCEPT_SHARE, rng)
    yd = y[dev] if y_dev is None else y_dev
    preds = rj.repetition(Z[dev], yd, accepted, Z[test], np.random.default_rng(seed + 2))
    return dev, test, accepted, preds, y


def test_the_policy_accepts_exactly_its_share_and_the_mnar_policy_is_informative(pop: pd.DataFrame) -> None:
    dev, _ = split(pop, 1)
    Z = rj.design(pop, FEATURES, CATEGORICAL, dev)
    y = pop["target"].to_numpy()[dev]
    z = rj.policy_z(Z[dev], y)
    mar = rj.legacy_acceptance(z, y, 0.0, 0.6, np.random.default_rng(5))
    mnar = rj.legacy_acceptance(z, y, 1.0, 0.6, np.random.default_rng(5))
    assert mar.sum() == mnar.sum() == round(0.6 * len(dev))
    # the private signal of the underwriter lets in fewer defaulters at the same share
    assert y[mnar].mean() < y[mar].mean() - 0.02


def test_a_policy_without_private_signal_never_sees_the_outcome(pop: pd.DataFrame) -> None:
    dev, _ = split(pop, 1)
    Z = rj.design(pop, FEATURES, CATEGORICAL, dev)
    y = pop["target"].to_numpy()[dev]
    z = rj.policy_z(Z[dev], y)
    a = rj.legacy_acceptance(z, y, 0.0, 0.6, np.random.default_rng(9))
    b = rj.legacy_acceptance(z, np.random.default_rng(1).permutation(y), 0.0, 0.6, np.random.default_rng(9))
    assert (a == b).all()


def test_accepted_only_is_biased_low_under_the_private_signal_and_not_without_it(pop: pd.DataFrame) -> None:
    bias: dict[float, list[float]] = {0.0: [], 1.0: []}
    for kappa in bias:
        for seed in range(12):
            _, test, _, preds, y = one(pop, kappa, seed)
            bias[kappa].append(preds["accepted-only"].mean() - y[test].mean())
    assert np.mean(bias[1.0]) < -0.03, "the accepted-only PD must under-state the default rate of the full population"
    assert abs(np.mean(bias[0.0])) < 0.012, "an ignorable policy leaves the accepted-only level near the truth"


def test_no_rung_but_the_oracle_reads_a_rejected_label(pop: pd.DataFrame) -> None:
    dev, _ = split(pop, 2)
    y = pop["target"].to_numpy()
    _, _, accepted, base, _ = one(pop, 1.0, 2)
    scrambled = y[dev].copy()
    scrambled[~accepted] = 1 - scrambled[~accepted]
    _, _, _, other, _ = one(pop, 1.0, 2, y_dev=scrambled)
    assert set(base) == set(rj.RUNGS)
    for rung in rj.RUNGS:
        same = np.array_equal(base[rung], other[rung])
        assert same == (rung != "oracle"), rung


def test_augmentation_weights_are_the_inverse_acceptance_probability_with_a_floor() -> None:
    p = np.array([1.0, 0.5, 0.2, 0.001])
    w = rj.augmentation_weights(p)
    assert np.allclose(w, [1.0, 2.0, 5.0, 1 / rj.WEIGHT_FLOOR])
    assert w.max() <= 1 / rj.WEIGHT_FLOOR + 1e-12


def test_the_hard_cutoff_labels_the_riskiest_rejects_in_the_share_the_model_expects() -> None:
    p0 = np.array([0.05, 0.9, 0.3, 0.6, 0.1, 0.2, 0.7, 0.4])
    lab = rj.hard_cutoff_labels(p0)
    k = int(round(p0.mean() * len(p0)))
    assert lab.sum() == k
    assert set(np.argsort(-p0)[:k]) == set(np.flatnonzero(lab == 1))


def test_parcelling_assigns_the_band_rate_of_the_accepted_with_the_prudence_factor_and_a_fallback() -> None:
    rng = np.random.default_rng(0)
    n = 6000
    p0 = rng.random(n)
    accepted = p0 < 0.7
    y = (rng.random(n) < p0).astype(int)
    rates = rj.parcel_rates(p0, accepted, y, prudence=1.0, bands=10, min_accepted=10)
    assert rates.shape == (int((~accepted).sum()),)
    # the riskiest band has no accepted applicant: it takes the model's mean PD of its rejects
    top = p0[~accepted] > 0.9
    assert abs(rates[top].mean() - p0[~accepted][top].mean()) < 0.03
    doubled = rj.parcel_rates(p0, accepted, y, prudence=2.0, bands=10, min_accepted=10)
    assert np.allclose(doubled, np.minimum(1.0, 2 * rates))
    labels = rj.parcel_labels(rates, np.random.default_rng(4))
    assert set(np.unique(labels)) <= {0, 1} and abs(labels.mean() - rates.mean()) < 0.03


def test_fuzzy_augmentation_enters_every_reject_twice_with_weights_that_sum_to_one() -> None:
    p0 = np.array([0.2, 0.7, 0.05])
    idx, label, w = rj.fuzzy_rows(p0)
    assert len(idx) == 6 and sorted(idx.tolist()) == [0, 0, 1, 1, 2, 2]
    for i in range(3):
        m = idx == i
        assert w[m].sum() == pytest.approx(1.0)
        assert w[m & (label == 1)][0] == pytest.approx(p0[i])


def test_the_interval_brackets_its_mean_is_seeded_and_narrows_with_more_repetitions() -> None:
    x = np.random.default_rng(1).normal(0.3, 1.0, 200)
    m, lo, hi = rj.interval(x, seed=5)
    assert lo < m < hi and (m, lo, hi) == rj.interval(x, seed=5)
    _, lo2, hi2 = rj.interval(np.random.default_rng(2).normal(0.3, 1.0, 800), seed=5)
    assert hi2 - lo2 < hi - lo


def test_the_reduction_of_the_bias_is_one_minus_the_ratio_of_mean_absolute_biases() -> None:
    b0 = -0.1 + np.random.default_rng(0).normal(0, 0.01, 300)
    br = 0.5 * b0 + np.random.default_rng(1).normal(0, 0.01, 300)
    point, lo, hi = rj.reduction(b0, br, seed=3)
    assert point == pytest.approx(1 - abs(br.mean()) / abs(b0.mean())) and 0.4 < point < 0.6 and lo < point < hi
    same, *_ = rj.reduction(b0, b0, seed=3)
    assert same == pytest.approx(0.0)


def test_the_run_reports_every_regime_and_rung_and_is_deterministic(pop: pd.DataFrame) -> None:
    a = rj.run(pop, FEATURES, CATEGORICAL, seed=11, reps=6)
    b = rj.run(pop, FEATURES, CATEGORICAL, seed=11, reps=6)
    assert a == b
    assert [r["id"] for r in a["regimes"]] == ["mar", "weak", "moderate", "strong"]
    for reg in a["regimes"]:
        assert [r["id"] for r in reg["rungs"]] == list(rj.RUNGS)
        for r in reg["rungs"]:
            assert len(r["reps"]["bias"]) == 6 and r["bias"]["lo"] <= r["bias"]["mean"] <= r["bias"]["hi"]
    assert a["design"]["reps"] == 6 and a["design"]["n_rows"] == len(pop)


def _result(bias_hi: float, red_lo: float, auc_gain: float) -> dict:
    def rung(i: str, red: float, d: float) -> dict:
        return {"id": i, "bias": {"mean": -0.08, "lo": -0.1, "hi": bias_hi},
                "reduction": {"value": red, "lo": red_lo, "hi": red + 0.1},
                "auc_vs_accepted_only": {"mean": d, "lo": d - 0.01, "hi": d + 0.01}}
    return {"regimes": [{"id": "mar", "rungs": [rung("accepted-only", 0.0, 0.0)]},
                        {"id": "moderate", "rungs": [rung("accepted-only", 0.0, 0.0), rung("augmentation", 0.4, auc_gain)]}]}


def test_the_hypotheses_follow_the_numbers_and_a_negative_result_is_reported() -> None:
    held = rj.verdicts(_result(-0.05, 0.2, 0.004))
    assert [v["id"] for v in held] == ["H1", "H2", "H3"] and all(v["holds"] for v in held)
    refuted = rj.verdicts(_result(0.01, -0.1, 0.03))
    assert [v["holds"] for v in refuted] == [False, False, False]
    for v in refuted:
        assert v["statement"]["en"] and v["statement"]["es"] and v["outcome"]["en"] and v["outcome"]["es"]
