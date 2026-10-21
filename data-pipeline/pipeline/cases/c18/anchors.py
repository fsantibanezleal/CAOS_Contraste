"""The Banco Andino anchors C18 takes from the committed documents of C07, C11, C15 and C17 (read, never changed; reservation R3).

Banco Andino is the synthetic bank of C07 and C15: its loan book is the C07 book (six segments with PD, LGD and asset correlation),
its balance sheet the C15 book calibrated to the CMF system aggregates of August 2026. The capital anchors (decision Q4):

* the **Tier 1 proxy** of C15 (the equity of the CMF aggregate, scaled to the book) is the CET1 of the jump-off, and the total RWA is
  that proxy over the 11.0 percent CET1 anchor;
* the RWA is split by the mix of the Banco Santander-Chile Form 20-F 2025 (credit, market, operational), and the buffers of the
  Chilean stack are its ratios (systemic 1.50, conservation 2.50, countercyclical 0.50 percent, Pillar 2 0.125 percent of RWA); the
  20-F is derived-only, so **only ratios** enter the documents (decision E5);
* the effective equity of the 20-F over its RWA gives the PE ratio of the jump-off, which the proxy carries as CET1 plus the rest: the
  sources give no split between AT1 and T2, so the part above CET1 is carried as T2 and AT1 is nil (ratios only, labelled).

A document that is missing, or a number it must hold that it does not, stops C18 whole (the Missing data paragraph of the sizing).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import params as P

REPO = Path(__file__).resolve().parents[4]
DERIVED = REPO / "data" / "derived"


#: the variant of C15 that C18 reads, through the literal ``C15/long-uf.json`` below (depends_on must name a concrete document); it is checked against
#: the default variant of the C15 manifest at every run and by a test
C15_VARIANT = "long-uf"


class MissingDocument(FileNotFoundError):
    """A committed document C18 reads is not there: C18 stops whole, naming it."""


def load(rel: str, derived: Path | None = None) -> dict[str, Any]:
    path = (derived or DERIVED) / rel
    if not path.exists():
        raise MissingDocument(f"{rel} is not committed under {path.parent}: C18 reads the committed documents of C07, C15 and C17 and cannot run without it")
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Segment:
    segment_id: str
    klass: str
    accounts: int
    exposure_clp_m: float
    pd: float
    lgd: float
    rho: float


@dataclass(frozen=True)
class Anchors:
    segments: tuple[Segment, ...]
    class_exposure_clp_m: dict[str, float]
    loans_clp_m: float
    tier1_clp_m: float
    total_assets_clp_m: float
    rwa_clp_m: float
    rwa_mix: dict[str, float]
    rwa_by_risk: dict[str, float]
    cet1_clp_m: float
    at1_clp_m: float
    t2_clp_m: float
    pe_ratio: float
    stack: dict[str, float]
    c15: dict[str, Any]                # the default C15 variant's outputs
    c15_models: dict[str, Any]
    c17: dict[str, Any]                # the C17 variant row of xi-0-8
    c17_generator: dict[str, Any]
    c11_champion: dict[str, Any]
    stage_balances_clp_m: tuple[float, float, float]
    class_lgd: dict[str, float]
    sources: dict[str, Any]


def rwa_mix() -> dict[str, float]:
    s = P.SANTANDER
    credit, market = round(s["credit"] / s["rwa"], 6), round(s["market"] / s["rwa"], 6)
    return {"credit": credit, "market": market, "operational": round(1.0 - credit - market, 10)}


def chilean_stack() -> dict[str, float]:
    return {"cet1_min": P.STACK["cet1_min"], "c_ccob": P.STACK["c_ccob"], "c_ccyb": P.STACK["c_ccyb"], "c_dsib": P.STACK["c_dsib"],
            "p2r": round(P.SANTANDER["pillar2"] / P.SANTANDER["rwa"], 5), "p2_cap": P.P2_CAP}


def _champion(c11: dict[str, Any]) -> dict[str, Any]:
    """The mixed-portfolio VaR and ES of C11 at the 1 percent level: the last forecast day of the champion of that level."""
    o = c11["outputs"]
    champs = [c for c in o["comparison"]["champions"] if abs(c.get("alpha", 0.0) - 0.01) < 1e-12]
    if not champs:
        raise ValueError("C11 mixed-2023 names no champion at the 1 percent level")
    mid = champs[0]["model_id"]
    model = next(m for m in o["models"] if m["model_id"] == mid)
    lv = next(x for x in model["by_level"] if abs(x["alpha"] - 0.01) < 1e-12)
    var, es = [v for v in lv["var"] if v is not None], [v for v in lv["es"] if v is not None]
    return {"model_id": mid, "alpha": 0.01, "date": o["grid"]["dates"][-1], "var": float(var[-1]), "es": float(es[-1]),
            "portfolio": o["portfolio"]["description"]["en"], "currency": o["portfolio"]["currency"]}


def load_anchors(derived: Path | None = None) -> Anchors:
    c07 = load("C07/base.json", derived)
    c07m = load("C07/models-banco-andino.json", derived)
    c15_man = load("manifests/C15.json", derived)
    if c15_man["default_variant"] != C15_VARIANT:
        raise MissingDocument(f"manifests/C15.json: the default variant of C15 is {c15_man['default_variant']!r}, no longer {C15_VARIANT!r}, the document C18 reads "
                              f"(C15/{C15_VARIANT}.json): change the read and the depends_on reason of C18 together")
    c15 = load("C15/long-uf.json", derived)["outputs"]
    c15m = load("C15/models-banco-andino-2026-09.json", derived)
    c17m = load("C17/models-generator.json", derived)
    c11 = load("C11/mixed-2023.json", derived)
    fit07 = {s["segment_id"]: s for s in c07m["fit"]["ifrs9"]["segments"]}
    segs = []
    for s in c07["outputs"]["portfolio"]["segments"]:
        f = fit07[s["segment_id"]]
        segs.append(Segment(s["segment_id"], P.SEGMENT_CLASS[s["segment_id"]], int(s["accounts"]), s["gross_exposure"] / 1e6, f["pd_ttc"], f["lgd"], f["rho"]))
    klass: dict[str, float] = {c: 0.0 for c in P.CLASSES}
    for s in segs:
        klass[s.klass] += s.exposure_clp_m
    loans = sum(klass.values())
    tier1 = float(c15["thresholds"]["tier1"])
    eq_ratio = next(t["target"] for t in c15m["fit"]["calibration_targets"] if t["metric"] == "equity over total assets")
    assets = tier1 / eq_ratio
    rwa = tier1 / P.CMF_ANCHOR_CET1
    mix = rwa_mix()
    by_risk = {k: round(rwa * mix[k], 6) for k in ("credit", "market", "operational")}
    by_risk["operational"] = round(rwa - by_risk["credit"] - by_risk["market"], 6)
    pe_ratio = round(P.SANTANDER["effective_equity"] / P.SANTANDER["rwa"], 6)
    cet1 = tier1
    pe = round(rwa * pe_ratio, 6)
    stages = {x["stage"]: x["gross_carrying_amount"] / 1e6 for x in c07["outputs"]["ifrs9_detail"]["stage_summary"]}
    lgd = {c: sum(g.exposure_clp_m * g.lgd for g in segs if g.klass == c) / klass[c] for c in P.CLASSES}
    gen = next((v for v in c17m["fit"]["variants"] if v["variant_id"] == P.C17_VARIANT), None)
    if gen is None:
        raise MissingDocument(f"C17/models-generator.json has no variant {P.C17_VARIANT}")
    return Anchors(tuple(segs), klass, loans, tier1, assets, rwa, mix, by_risk, cet1, 0.0, round(pe - cet1, 6), pe_ratio, chilean_stack(), c15,
                   c15m["fit"], gen, c17m["fit"]["generator"], _champion(c11),
                   (stages["stage1"], stages["stage2"], stages["stage3"]), lgd,
                   {"c07": c07["outputs"]["scenario_id"], "c15_variant": c15_man["default_variant"], "c17_variant": P.C17_VARIANT})
