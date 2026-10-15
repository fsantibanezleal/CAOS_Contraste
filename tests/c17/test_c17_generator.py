"""CT-1705, CT-1706 and CT-1707: the recorded history, contract 1 and the independence of the replications."""
from __future__ import annotations

import numpy as np
from pipeline.cases.c17 import generator, replicate
from pipeline.cases.c17 import params as P
from pipeline.io import contract
from riskvalidation.oprisk import distributions as dist


def test_losses_below_the_collection_threshold_are_removed_before_every_fit(variants_, monkeypatch):
    v = variants_[0.8]
    h = generator.draw_history(v, seed=11, n_years=10)
    assert h.amount_eur.min() >= P.FLOOR_EUR  # the truth counts every loss at or above the floor
    for thr in (10_000.0, 20_000.0):
        rec = h.recorded(thr)
        assert rec.amounts.min() >= thr and rec.amounts.size == np.count_nonzero(h.amount_eur >= thr)
        assert rec.counts.sum() == rec.amounts.size and np.isclose(rec.annual.sum(), rec.amounts.sum())
    assert h.recorded(20_000.0).amounts.size < h.recorded(10_000.0).amounts.size
    seen: list[float] = []
    real = dist.fit_severity

    def spy(law, losses, collection_threshold=0.0, truncated=True):
        seen.append(float(np.min(losses)))
        return real(law, losses, collection_threshold, truncated)

    monkeypatch.setattr(dist, "fit_severity", spy)
    out = replicate.estimate(v, seed=11, years=10, threshold=20_000.0, bi=1.4e9, prior=None, mc_years=20_000)
    assert seen and min(seen) >= 20_000.0 and out["failed"] == 0.0
    assert out["n_losses"] == h.recorded(20_000.0).amounts.size


def test_every_recorded_history_passes_the_loss_events_contract(variants_):
    for xi, v in variants_.items():
        for seed in (1, 2, 3):
            for thr in (10_000.0, 20_000.0):
                rows = generator.draw_history(v, seed, 10).rows(thr)
                rep = contract.validate("loss_events", rows, params={"collection_threshold": thr, "currency": "EUR"})
                c = rep.counts()
                assert c["input"] == len(rows) > 0 and c["accepted"] == c["input"] and c["rejected"] == 0, (xi, seed, thr, rep.summary())
                assert len({r["event_id"] for r in rows}) == len(rows)


def test_a_history_is_reproduced_by_its_seed_and_the_seed_ranges_are_disjoint(variants_):
    v = variants_[0.96]
    a, b, c = (generator.draw_history(v, s, 5) for s in (7, 7, 8))
    assert np.array_equal(a.amount_eur, b.amount_eur) and np.array_equal(a.year_index, b.year_index) and np.array_equal(a.event_type, b.event_type)
    assert a.amount_eur.size != c.amount_eur.size or not np.array_equal(a.amount_eur, c.amount_eur)
    # the amounts do not depend on the labels, nor on the threshold the bank later applies
    assert np.array_equal(generator.draw_history(v, 7, 5).recorded(20_000.0).amounts, a.amount_eur[a.amount_eur >= 20_000.0])
    for case_seed in (42, 43):
        spans = []
        for vi in range(4):
            for ci in range(4):
                first, n = generator.cell_seeds(case_seed, vi, ci, 1000)
                spans.append((first, first + n - 1))
        spans.sort()
        assert all(x[1] < y[0] for x, y in zip(spans, spans[1:])) and len(spans) == 16
    assert generator.cell_seeds(42, 3, 3, 1000)[0] != generator.cell_seeds(43, 3, 3, 1000)[0]
    assert generator.seed_base(42) == generator.cell_seeds(42, 0, 0, 1000)[0]
