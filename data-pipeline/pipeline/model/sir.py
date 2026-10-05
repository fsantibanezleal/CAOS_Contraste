"""EXAMPLE engine: a deterministic SIR epidemic, forward Euler at a quarter-day step. It is the reference of the live
lane: frontend/src/engine/sir.ts is a step-for-step TypeScript port, and its parity test holds it to the traces
this engine bakes. Replace with the product's research-chosen engine."""
from __future__ import annotations

import numpy as np

from ..io.schema import SIRParams, SIRResult


def simulate(p: SIRParams, dt: float = 0.25) -> SIRResult:
    steps = max(1, int(round(p.days / dt)))
    S = float(p.N - p.I0)
    I = float(p.I0)
    R = 0.0
    beta_over_N = (p.beta / p.N) if p.N > 0 else 0.0
    ts = [0.0]
    Ss = [S]
    Is = [I]
    Rs = [R]
    for k in range(1, steps + 1):
        new_inf = beta_over_N * S * I * dt
        new_rec = p.gamma * I * dt
        S = max(0.0, S - new_inf)
        I = max(0.0, I + new_inf - new_rec)
        R = R + new_rec
        ts.append(k * dt)
        Ss.append(S)
        Is.append(I)
        Rs.append(R)
    peak_idx = int(np.argmax(Is))
    return SIRResult(
        case_id=p.case_id,
        t=ts, S=Ss, I=Is, R=Rs,
        peak_I=float(Is[peak_idx]),
        t_peak=float(ts[peak_idx]),
        attack_rate=float(Rs[-1] / p.N) if p.N > 0 else 0.0,
    )
