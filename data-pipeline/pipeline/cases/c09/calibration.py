"""The calibration of the C09 generator from the Federal Reserve 2025 hypothetical card portfolios (CT-1001).

The three files (``cards-low-risk-2025.csv``, ``cards-typical-risk-2025.csv``, ``cards-high-risk-2025.csv``) are 200 hypothetical
card accounts each, published with the 2025 supervisory stress test (https://www.federalreserve.gov/supervisionreg/dfa-stress-tests-2025.htm).
``calibrate`` reads them from the device data root (``<root>/raw/fed-cards-2025/``), checks every file against the size and hash
committed in ``params.PARAMS["sources"]`` and returns the marginals the generator uses: the credit limit, the utilisation (an
interior Beta, a mass at the full line and a mass above the limit), the credit score and the APR, by risk tier. The result is
committed in ``params.PARAMS["fed_calibration"]``; a test recalculates it from the files whenever they are present, so the committed
numbers cannot drift from the source.
"""
from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
from typing import Any

from . import params

INTERIOR_TOP = 0.995          # a utilisation below this is an interior one; 0.995 to 1.005 is a full line; above it is over the limit
FULL_TOP = 1.005
SOURCE_URL = "https://www.federalreserve.gov/supervisionreg/files/"


class MarginalError(ValueError):
    """A marginal the generator uses has no source, or names one that is not a committed Federal Reserve file."""


def _round(x: float) -> float:
    return float(f"{x:.6g}")


def _read(raw_dir: Path, file: dict[str, Any]) -> list[dict[str, str]]:
    path = Path(raw_dir) / file["name"]
    data = path.read_bytes()
    if len(data) != file["bytes"] or hashlib.sha256(data).hexdigest() != file["sha256"]:
        raise MarginalError(f"{path}: size or hash differ from the committed source {file['url']}")
    return list(csv.DictReader(data.decode("utf-8").splitlines()))


def _moments(x: list[float]) -> tuple[float, float]:
    m = sum(x) / len(x)
    return m, sum((v - m) ** 2 for v in x) / (len(x) - 1)


def calibrate(raw_dir: Path) -> dict[str, dict[str, float]]:
    """The marginals of each risk tier, recalculated from the fetched files (rounded to six significant digits)."""
    out: dict[str, dict[str, float]] = {}
    for file in params.PARAMS["sources"]:
        rows = _read(raw_dir, file)
        limit = [float(r["currentcreditlimit"]) for r in rows]
        bal = [float(r["cycleendingbalance"]) for r in rows]
        if min(limit) <= 0 or min(bal) <= 0:
            raise MarginalError(f"{file['name']}: a zero limit or balance, which the generator's utilisation states do not model")
        util = [b / lim for b, lim in zip(bal, limit, strict=True)]
        n = len(util)
        interior = [u / INTERIOR_TOP for u in util if u < INTERIOR_TOP]
        over = [u - 1.0 for u in util if u > FULL_TOP]
        m, v = _moments(interior)
        k = m * (1.0 - m) / v - 1.0
        logs = [math.log(x) for x in limit]
        lm, lv = _moments(logs)
        score = [float(r["refreshedcreditscoreprimaryborrower"]) for r in rows]
        apr = [float(r["cycleendingretailapr"]) for r in rows]
        sm, sv = _moments(score)
        am, av = _moments(apr)
        out[file["tier"]] = {
            "n": n, "limit_log_mu": _round(lm), "limit_log_sigma": _round(math.sqrt(lv)),
            "p_full": _round(sum(1 for u in util if INTERIOR_TOP <= u <= FULL_TOP) / n), "p_over": _round(len(over) / n),
            "beta_a": _round(m * k), "beta_b": _round((1.0 - m) * k), "over_excess_mean": _round(sum(over) / len(over)),
            "score_mean": _round(sm), "score_sd": _round(math.sqrt(sv)), "apr_mean": _round(am), "apr_sd": _round(math.sqrt(av)),
        }
    return out


def _file(tier: str) -> dict[str, Any]:
    return next(f for f in params.PARAMS["sources"] if f["tier"] == tier)


def _src(tier: str) -> str:
    f = _file(tier)
    return f"{f['url']} (Federal Reserve Board, 2025 supervisory stress test; {f['bytes']} bytes, sha256 {f['sha256']}, fetched {f['fetched']})"


def marginals() -> list[dict[str, Any]]:
    """The ``c09Marginal`` rows of the models document: one per field and tier, each with its source."""
    cal = params.PARAMS["fed_calibration"]
    rows: list[dict[str, Any]] = []

    def row(field: str, dist: str, plist: list[tuple[str, float, str]], source: str) -> None:
        rows.append({"field": field, "distribution": dist, "parameters": [{"name": n, "value": v, "unit": u} for n, v, u in plist],
                     "source": source})

    for t in params.TIERS:
        c = cal[t]
        row(f"credit_limit.{t}", "lognormal", [("mu", c["limit_log_mu"], "ln USD"), ("sigma", c["limit_log_sigma"], "ln USD")], _src(t))
        row(f"utilisation_interior.{t}", "beta (balance over limit, scaled to the interval 0 to 0.995)",
            [("alpha", c["beta_a"], "-"), ("beta", c["beta_b"], "-")], _src(t))
        row(f"utilisation_state.{t}", "categorical (interior, full line, over the limit)",
            [("p_full", c["p_full"], "share"), ("p_over", c["p_over"], "share")], _src(t))
        row(f"utilisation_over_excess.{t}", "exponential, truncated so that utilisation is at most the cap",
            [("mean_excess", c["over_excess_mean"], "share of limit"), ("cap", params.PARAMS["over_cap"], "share of limit")], _src(t))
        row(f"credit_score.{t}", "normal, clipped to 300 to 850", [("mean", c["score_mean"], "points"), ("sd", c["score_sd"], "points")], _src(t))
        row(f"apr.{t}", "normal, clipped to 5 to 35", [("mean", c["apr_mean"], "percent"), ("sd", c["apr_sd"], "percent")], _src(t))
        row(f"tier_share.{t}", "categorical", [("share", params.PARAMS["tier_share"][params.TIERS.index(t)], "share")],
            "assumption of the case: the Fed files hold 200 accounts per tier and give no population mix")
        row(f"default_probability.{t}", "bernoulli", [("pd_12m", params.PARAMS["tier_pd"][params.TIERS.index(t)], "share")],
            "assumption of the case: card default probabilities of the order of the Fed's low, typical and high risk portfolios")
    return rows


def validate_marginals(rows: list[dict[str, Any]]) -> None:
    """Refuse a marginal with no source, with no parameter, or whose source names neither a committed Fed file nor an assumption."""
    known = {f["url"] for f in params.PARAMS["sources"]}
    for r in rows:
        src = r.get("source", "")
        if not src.strip():
            raise MarginalError(f"{r.get('field')}: no source")
        if not r.get("parameters"):
            raise MarginalError(f"{r.get('field')}: no parameters")
        if "assumption of the case" in src:
            continue
        if not any(url in src for url in known):
            raise MarginalError(f"{r['field']}: the source {src!r} is not a committed Federal Reserve file")
