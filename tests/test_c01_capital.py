"""CT-213: C01's IRB capital along the cut-off curve is the engine's, account by account, summed over the approved.

A synthetic sample runs through the same functions the bake uses; every committed point must equal a direct sum of
riskvalidation's capital requirement at unit LGD times the EAD, within 1e-9 relative."""
from __future__ import annotations

import numpy as np
import pytest
from riskvalidation.regulatory import capital_requirement

from pipeline.cases import c01_capital as cap
from pipeline.stages import evaluate


def _sample(n: int = 400, seed: int = 7):
    rng = np.random.default_rng(seed)
    # PDs from below every floor to near certain default, with ties as a calibration map makes them
    pds = np.concatenate([10 ** rng.uniform(-4.5, -0.1, n - 40), np.full(40, 0.02)])
    ead = rng.uniform(0.0, 50_000.0, n)
    ead[:5] = 0.0
    y = (rng.uniform(size=n) < pds).astype(int)
    return pds, ead, y


@pytest.mark.parametrize(("cls", "revolver"), [("qrre", True), ("qrre", False), ("other_retail", False)])
def test_capital_curve_sums_the_engine(cls, revolver):
    pds, ead, y = _sample()
    rev = np.full(len(pds), revolver)
    sums = {"capital_per_lgd": cap.account_capital(cls, pds, ead, rev)}
    curve = evaluate.cutoff_curve(pds, y, ead, sums=sums)
    assert set(curve["capital_per_lgd"]) == set(cap.REGIMES)
    # the cut-offs are the PD quantiles (the committed ones are rounded to six decimals for display)
    cuts = np.unique(np.quantile(pds, np.linspace(0.02, 1.0, 51)))
    for regime in cap.REGIMES:
        for c, got in zip(cuts, curve["capital_per_lgd"][regime], strict=True):
            m = pds <= c
            want = sum(capital_requirement(cls, float(min(max(p, 1e-12), 1 - 1e-12)), 1.0, revolver=revolver,
                                           regime=regime).risk_weight / 12.5 * e for p, e in zip(pds[m], ead[m], strict=True))
            assert got == pytest.approx(want, rel=1e-9, abs=1e-6), (cls, regime, c)
        # approving more never lowers the capital
        assert all(b >= a for a, b in zip(curve["capital_per_lgd"][regime], curve["capital_per_lgd"][regime][1:]))


def test_capital_is_linear_in_the_lgd_for_retail():
    """The web's live capital is the committed unit-LGD capital times the rail's LGD: exact for the retail functions."""
    for cls, revolver in (("qrre", True), ("other_retail", False)):
        for pd in (0.0003, 0.004, 0.05, 0.3):
            for regime in cap.REGIMES:
                unit = capital_requirement(cls, pd, 1.0, revolver=revolver, regime=regime).k
                for lgd in (0.1, 0.45, 0.9):
                    assert capital_requirement(cls, pd, lgd, revolver=revolver, regime=regime).k == pytest.approx(lgd * unit, rel=1e-12)


def test_a_revolver_never_needs_less_capital_than_a_transactor():
    """The revolver's PD floor is the higher one (0.1% against 0.05% in Basel III and CRR3), so treating an account as
    a transactor can only lower its capital, and only below the revolver floor."""
    for regime in cap.REGIMES:
        for pd in (0.0002, 0.0007, 0.0012, 0.01, 0.2):
            rev = cap.unit_capital("qrre", pd, regime, True)
            trn = cap.unit_capital("qrre", pd, regime, False)
            assert rev >= trn
            if pd >= 0.001:
                assert rev == trn
