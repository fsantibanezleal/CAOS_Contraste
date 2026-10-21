"""CT-2003, CT-2005: the applied shock families on the structured view, and the German model that never sees its holdout."""
from __future__ import annotations

import pandas as pd
from c20_support import DATA

from pipeline.cases import c01_features as feat
from pipeline.cases.c20 import data, sgcd, shocks
from pipeline.io import contract as c1


def frame_of_sample() -> tuple[pd.DataFrame, sgcd.Dataset]:
    ds = sgcd.read_dataset(DATA / "sgcd-sample.jsonl", DATA / "sgcd-metadata.json")
    rep = c1.validate("scored_sample", sgcd.contract_records(ds.records), extra_fields=feat.GERMAN_FIELDS)
    return pd.DataFrame(rep.accepted), ds


def widened(meta: dict, p: float) -> dict:
    """The metadata with every probability raised to p, so that every record is selected and the conventions are visible."""
    out = {**meta, "numeric_noise_probability": p, "f3_probability": {"adaptation": p, "test_seen": p, "test_unseen": p}}
    out["shock_probabilities"] = {**meta["shock_probabilities"], "test_seen": {"F1": 50 * p, "F2": 50 * p, "clean": 0},
                                  "test_unseen": {"F4": 50 * p, "clean": 0}}
    return out


def test_the_applied_shocks_follow_the_metadata_and_the_stated_conventions() -> None:
    X, ds = frame_of_sample()
    meta = ds.metadata
    assert shocks.probability(meta, "F1", "seen") == 0.2 and shocks.probability(meta, "F2", "seen") == 0.2
    assert shocks.probability(meta, "F4", "held-out") == 0.4 and shocks.probability(meta, "numeric-noise", "seen") == 0.1
    assert shocks.probability(meta, "F3", "seen") == 0.2 and shocks.probability(meta, "F3", "held-out") == 0.0
    modal = shocks.modal_codes(X)
    full = widened(meta, 1.0)
    before = X.copy()
    f1 = shocks.apply("F1", X, full, "seen", modal=modal)
    assert X.equals(before) and f1.n_selected == len(X)                       # never in place; every record selected at probability 1
    changed_cols = {c for c in X.columns if not f1.X[c].equals(X[c])}
    assert changed_cols <= set(shocks.F1_COLUMNS) and f1.n_changed >= 1       # one of the ten categorical fields the shipped F1 drops
    f3 = shocks.apply("F3", X, full, "seen", modal=modal)
    assert f3.X.equals(X) and f3.n_changed == 0                               # cosmetic: the structured view is unchanged by construction
    f4 = shocks.apply("F4", X, full, "held-out", modal=modal)
    moved = [(c, i) for c in shocks.F4_COLUMNS for i in range(len(X)) if not (pd.isna(f4.X.iloc[i][c]) and pd.isna(X.iloc[i][c])) and f4.X.iloc[i][c] != X.iloc[i][c]]
    assert moved and {c for c, _ in moved} <= set(shocks.F4_COLUMNS)
    for c, i in moved:                                                         # an adjacent, domain-valid code of the codebook order
        order = feat._GERMAN_CODES[c]
        assert str(f4.X.iloc[i][c]) in order and abs(order.index(str(f4.X.iloc[i][c])) - order.index(str(X.iloc[i][c]))) == 1
    f2 = shocks.apply("F2", X, full, "seen", modal=modal)
    for c in shocks.F2_COLUMNS:                                                # a change is the modal code of the setup batches
        diff = (f2.X[c] != X[c]) & ~(f2.X[c].isna() & X[c].isna())
        assert (f2.X.loc[diff, c] == modal[c]).all()
    noise = shocks.apply("numeric-noise", X, full, "seen", modal=modal)
    assert (noise.X["duration_months"] % shocks.DURATION_STEP == 0).all() and (noise.X["credit_amount"] % shocks.AMOUNT_STEP == 0).all()
    assert set(noise.X.columns) == set(X.columns) and noise.X["target"].equals(X["target"])    # the labels never move
    again = shocks.apply("F4", X, full, "held-out", modal=modal)
    assert again.X.equals(f4.X) and (again.selected == f4.selected).all()      # seed 42: the same stream gives the same shock
    default = shocks.apply("F1", X, meta, "seen", modal=modal)
    assert default.n_selected <= len(X) and shocks.SEED == 42


def test_the_german_model_is_fitted_on_setup_and_adaptation_batches_only(root) -> None:
    from pipeline.cases.c20 import fetch

    sg = root / "raw" / fetch.SGCD_ID
    ds = sgcd.read_dataset(sg / "SGCDataset.jsonl", sg / "SGCDataset_metadata.json")
    frame = data.load_sgcd(root, 42, ds)
    stage = frame.X["stage"].to_numpy()
    assert set(stage[frame.train]) | set(stage[frame.cal]) <= {"setup", "adaptation"} and set(stage[frame.hold]) == {"test"}
    assert len(frame.train) + len(frame.cal) == 700 and len(frame.hold) == 300
    assert not set(frame.train) & set(frame.hold) and not set(frame.cal) & set(frame.hold) and not set(frame.train) & set(frame.cal)
    assert set(frame.X["batch"].iloc[frame.hold]) == set(sgcd.TEST)
    data.assert_locked(frame)
    assert data.assert_evaluation_only(frame, frame.hold[:5]) is None
    assert "age_years" not in frame.features and "personal_status_sex" not in frame.features and "foreign_worker" not in frame.features
