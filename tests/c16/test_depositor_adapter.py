"""U16-I (BL-082): the C16 depositor adapter on ``engine-liquidity-api`` 2.0.0. The two stress-chain probabilities belong to the
``DepositorConfig`` (one chain shared by every depositor), the committed ``generator.config.segments`` rows keep both fields per
segment (the ``c16GeneratorSegment`` schema requires them), and the numbers the adapter produces are the ones 1.2.1 gave."""
from __future__ import annotations

import dataclasses

import pytest

from .helpers import committed, sample_report

CONV = {"generator_truth_se_red": {"value": 3.0}}


@pytest.fixture(scope="module")
def captured():
    """The engine configuration the adapter builds, with the block it returns (a small draw: the truth does not depend on it)."""
    from pipeline.cases.c16 import models

    seen: list = []
    real = models.DepositorGenerator

    class Spy(real):  # records the configuration the adapter hands the engine
        def __init__(self, config):
            seen.append(config)
            super().__init__(config)

    models.DepositorGenerator = Spy
    try:
        block, test = models.generator_block(sample_report(), 0.05425839099682417, CONV, 42, 300)
    finally:
        models.DepositorGenerator = real
    return seen[0], block, test


def test_the_chain_probabilities_are_on_the_configuration_not_on_the_segments(captured):
    from pipeline.cases.c16 import models

    cfg, _, _ = captured
    assert cfg.p_enter_stress == models.P_ENTER and cfg.p_exit_stress == models.P_EXIT
    for seg in cfg.segments:
        assert not hasattr(seg, "p_enter_stress") and not hasattr(seg, "p_exit_stress")
    assert [f.name for f in dataclasses.fields(cfg)] == ["segments", "n_depositors", "horizon_days", "p_enter_stress", "p_exit_stress"]


def test_the_document_keeps_both_probabilities_per_segment_and_they_equal_the_configuration(captured):
    cfg, block, _ = captured
    rows = block["config"]["segments"]
    assert [r["segment"] for r in rows] == [s.segment for s in cfg.segments]
    for r in rows:
        assert r["p_enter_stress"] == cfg.p_enter_stress and r["p_exit_stress"] == cfg.p_exit_stress
        assert {"segment", "share_of_deposits", "calm_daily_hazard", "stress_daily_hazard", "p_enter_stress", "p_exit_stress", "basis"} == set(r)


def test_the_truth_rows_equal_the_committed_ones_exactly(captured):
    """The engine says the outputs for an agreeing configuration equal 1.2.1's: the committed truth is reproduced bit for bit."""
    _, block, _ = captured
    assert block["truth"] == committed("models-svb-liquidity")["fit"]["generator"]["truth"]
    cfg_doc = committed("models-svb-liquidity")["fit"]["generator"]["config"]
    for key in ("truth_status", "n_depositors", "horizon_days", "segments"):
        assert block["config"][key] == cfg_doc[key], key
