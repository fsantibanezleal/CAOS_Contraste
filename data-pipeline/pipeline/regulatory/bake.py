"""The regulatory parity bake: the official examples and invariant cases through ``riskvalidation.regulatory`` (unit U9-P2).

``build`` makes the document in memory; ``bake`` checks it (schema, then ``check_regulatory``) and writes it. Every output value is the
return value of an engine function; the inputs come from ``inputs.json`` (the CRE99 trade inputs transcribed from the BIS page, the
constructed invariant inputs, the values the framework prints). The CRE52.61 terms (``credit_addon_terms``), the MAR21.4(5)(b)
fallback flag (``cross_bucket_charge_detail``) and the CRE52.34 trade effective notionals (``credit_trade_effective_notional``,
``commodity_trade_effective_notional``) are the engine's too (engine-regulatory-api 2.2.0); the product derives nothing.
"""
from __future__ import annotations

import importlib.metadata as md
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

from ..core import lineage as lin
from ..core.gate import classify_lane
from ..stages.export import write_artifact
from . import DOCUMENT_REL

REPO_ROOT = Path(__file__).resolve().parents[3]
INPUTS = Path(__file__).with_name("inputs.json")
PIN = re.compile(r"CAOS_RiskValidation(?:\.git)?@([0-9a-f]{40})")
SCENARIOS = ("low", "medium", "high")
ENGINES = {"numpy", "riskvalidation"}
RUN_MS = 1_000.0
#: the sections written exactly: the live ports are held to these values at 1e-9 relative, so they are never rounded
EXACT = frozenset({"official_examples", "invariant_cases", "output_floor_phase_in", "parameter_tables", "cre20_grid"})
#: the sign of the supervisory delta of a linear trade (CRE52.38: the payer, the protection buyer and the long position are +1)
LINEAR_DELTA = {"pay-fixed-receive-floating": 1.0, "pay-floating-receive-fixed": -1.0, "protection-buyer": 1.0,
                "protection-seller": -1.0, "long": 1.0, "short": -1.0}
#: (is_call, is_long) of the option types of CRE52.38 to CRE52.41
OPTION = {"bought-call": (True, True), "sold-call": (True, False), "bought-put": (False, True), "sold-put": (False, False)}
SEED = 0


def _engine():
    """The engine modules, read as attributes at call time (a test may replace one function)."""
    from riskvalidation.regulatory import ba_cva, frtb, output_floor, sa_ccr, standardised

    return sa_ccr, ba_cva, frtb, output_floor, standardised


def engine_version() -> str:
    """The engine version with the commit that pins it (requirements.txt), so the document names the code that computed it."""
    try:
        ver = md.version("riskvalidation")
    except md.PackageNotFoundError:
        ver = "not installed"
    req = (REPO_ROOT / "data-pipeline" / "requirements.txt").read_text(encoding="utf-8")
    m = PIN.search(req)
    return f"{ver}+{m.group(1)[:7]}" if m else ver


def _semantics():
    """tests/contracts_u9/semantics.py under a module name of its own (U10's suite ships a helper of the same name)."""
    name = "contraste_u9_semantics"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "tests" / "contracts_u9" / "semantics.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _terms(trade: dict) -> dict[str, Any]:
    return {v["name"]: v["value"] for v in trade["terms"]}


def _vals(group: list[dict]) -> dict[str, Any]:
    return {v["name"]: v["value"] for v in group}


def _chapter_date(paragraph: str) -> str:
    """The in-force date the engine states for the chapter of ``paragraph``."""
    sa_ccr, ba_cva, frtb, output_floor, standardised = _engine()
    table = {"CRE20": standardised.CRE20_IN_FORCE, "CRE52": sa_ccr.CRE52_IN_FORCE, "CRE99": sa_ccr.CRE52_IN_FORCE,
             "MAR50": ba_cva.MAR50_IN_FORCE, "MAR21": frtb.MAR21_IN_FORCE, "MAR33": frtb.MAR33_IN_FORCE,
             "RBC20": output_floor.RBC_IN_FORCE, "RBC90": output_floor.RBC_IN_FORCE}
    chapter = re.match(r"[A-Z]+\d+", paragraph).group(0)
    return table[chapter]


# --- SA-CCR (CRE52, the CRE99 worked examples) --------------------------------------------------------------------------------


def _sa_ccr(e: dict) -> dict[str, Any]:
    sa_ccr, *_ = _engine()
    ins = _vals(e["inputs"])
    mpor = ins.get("mpor_business_days")
    margined = mpor is not None
    mpor = None if mpor is None else int(mpor)
    th, mta, nica = ins.get("th", 0.0), ins.get("mta", 0.0), ins.get("nica", 0.0)
    ir_trades, credit, commodity, v = [], {}, {}, 0.0
    out: dict[str, Any] = {}
    mfs: list[float] = []
    for tr in e["trades"]:
        t = _terms(tr)
        v += t["market_value"]
        ac = t["asset_class"]
        if t.get("option_type", "none") != "none":
            is_call, is_long = OPTION[t["option_type"]]
            delta = sa_ccr.supervisory_delta_option(t["option_price"], t["option_strike"], t["option_volatility"],
                                                    t["option_expiry_years"], is_call, is_long)
            out["swaption_delta"] = delta
        else:
            delta = LINEAR_DELTA[t["position"]]
        if ac == "interest-rate":
            ir_trades.append(sa_ccr.IrTrade(t["currency"], t["start_years"], t["end_years"], t["notional"], delta))
            mfs.append(sa_ccr.maturity_factor(t["end_years"], mpor))
        elif ac == "credit":
            en = sa_ccr.credit_trade_effective_notional(delta, t["notional"], t["start_years"], t["end_years"], mpor)
            mfs.append(sa_ccr.maturity_factor(t["end_years"], mpor))
            row = credit.setdefault(t["entity"], [t["rating"], t["reference_kind"] == "index", 0.0])
            row[2] += en
        elif ac == "commodity":
            mf = sa_ccr.maturity_factor(t["maturity_years"], mpor)
            mfs.append(mf)
            key = "commodity-electricity" if t["commodity_type"] == "electricity" else "commodity-oil-gas-metals-agricultural-other"
            row = commodity.setdefault(t["hedging_set"], {}).setdefault(t["commodity_type"], [key, 0.0])
            row[1] += sa_ccr.commodity_trade_effective_notional(delta, t["adjusted_notional"], t["maturity_years"], mpor)
        else:
            raise ValueError(f"{e['id']}: asset class {ac!r} is not one the CRE99 examples use (CRE99.20 to CRE99.97)")
    if not math.isclose(v, ins["v"], rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{e['id']}: V is {v}, the sum of the market values of the trades, not the input {ins['v']} (CRE99)")
    classes: dict[str, float] = {}
    if ir_trades:
        ir = sa_ccr.ir_addon(ir_trades, mpor)
        for h in ir.hedging_sets:
            out[f"en_{h.hedging_set.lower()}"] = h.effective_notional
            out[f"addon_{h.hedging_set.lower()}"] = h.addon
        out["addon_ir"] = classes["interest_rate"] = ir.addon
    if credit:
        entities = [sa_ccr.CreditEntity(r, idx, en) for r, idx, en in credit.values()]
        terms = sa_ccr.credit_addon_terms(entities)
        if not math.isclose(math.sqrt(terms.systematic + terms.idiosyncratic), terms.addon, rel_tol=1e-12):
            raise ValueError("the engine's systematic and idiosyncratic terms do not recompose its credit add-on (CRE52.61)")
        classes["credit"] = out["addon_credit"] = terms.addon
        out["term_1"], out["term_2"] = terms.systematic, terms.idiosyncratic
    if commodity:
        by_set = {hs: [sa_ccr.CommodityEntity(sa_ccr.supervisory_parameter(k, "supervisory_factor").value,
                                              sa_ccr.supervisory_parameter(k, "correlation").value, en) for k, en in types.values()]
                  for hs, types in commodity.items()}
        for hs, ents in by_set.items():
            out[f"addon_{hs}"] = sa_ccr.commodity_addon({hs: ents})
        classes["commodity"] = out["addon_commodity"] = sa_ccr.commodity_addon(by_set)
    res = sa_ccr.netting_set_ead(v, ins["c"], sa_ccr.AddOnByClass(**classes), margined, th, mta, nica)
    out.update({"rc": res.rc, "addon_aggregate": res.addon_aggregate, "multiplier": res.multiplier, "pfe": res.pfe, "ead": res.ead})
    if margined:
        out["maturity_factor"] = mfs[0]
    return out


# --- the output floor, BA-CVA, SBM, GIRR and the cascade ----------------------------------------------------------------------


def _floor(e: dict) -> dict[str, Any]:
    _, _, _, output_floor, _ = _engine()
    ins = _vals(e["inputs"])
    if ins["floor_factor"] != output_floor.phase_in_factor(2028).value:
        raise ValueError(f"{e['id']}: the floor factor is not the fully phased-in RBC90.1 factor")
    return {"rwa_floored": output_floor.floored_rwa(ins["rwa_nominated"], ins["rwa_sa_only"], ins["floor_factor"], ins.get("cap_share"))}


def _ba_cva(e: dict) -> dict[str, Any]:
    _, ba_cva, *_ = _engine()
    ins = _vals(e["inputs"])
    if "scva_1" in ins:
        scvas = [ins[k] for k in sorted(ins) if k.startswith("scva_")]
        return {"k_reduced": ba_cva.k_reduced(scvas, ins["rho"])}
    return {"k_full": ba_cva.k_full(ins["k_reduced"], ins["k_hedged"], ins["beta"])}


def _sbm_scenarios(e: dict) -> dict[str, Any]:
    _, _, frtb, _, _ = _engine()
    rho = np.array(_vals(e["inputs"])["rho"], dtype=float)
    return {f"rho_{sc}": float(frtb.scenario_correlation(rho, sc)) for sc in SCENARIOS}


def _sbm(e: dict) -> dict[str, Any]:
    _, _, frtb, _, _ = _engine()
    ins = _vals(e["inputs"])
    ws = [np.array(ins[k], dtype=float) for k in sorted(ins) if k.startswith("ws_")]
    rho = [np.array(ins[f"rho_{b + 1}"], dtype=float).reshape(len(w), len(w)) for b, w in enumerate(ws)]
    n = len(ws)
    gamma = np.full((n, n), float(ins["gamma"]))
    np.fill_diagonal(gamma, 1.0)
    out: dict[str, Any] = {}
    cross: dict[str, float] = {}
    for sc in SCENARIOS:
        k_b = np.array([frtb.bucket_charge(w, r, sc) for w, r in zip(ws, rho)])
        s_b = np.array([float(np.sum(w)) for w in ws])
        for b, k in enumerate(k_b):
            out[f"k_b{b + 1}_{sc}"] = float(k)
        detail = frtb.cross_bucket_charge_detail(k_b, s_b, gamma, sc)
        cross[sc] = out[f"cross_bucket_{sc}"] = detail.charge
        out[f"fallback_{sc}"] = 1.0 if detail.fallback_used else 0.0
    zero = {sc: 0.0 for sc in SCENARIOS}
    out["sbm_charge"] = frtb.sbm_capital(cross, zero, zero).capital
    return out


def _girr(e: dict) -> dict[str, Any]:
    _, _, frtb, _, _ = _engine()
    ins = _vals(e["inputs"])
    divided, undivided = frtb.girr_parameters(True), frtb.girr_parameters(False)
    if not (divided.sqrt2_applied and not undivided.sqrt2_applied and ins["sqrt2_division_applied"] == 1.0):
        raise ValueError("the GIRR headline divides the risk weights by sqrt(2) (MAR21.44) and the undivided charge is written beside it")
    s, tenors = np.array(ins["sensitivities"], dtype=float), np.array(ins["tenors"], dtype=float)
    head = frtb.girr_delta_charge(s, tenors, divided)
    beside = frtb.girr_delta_charge(s, tenors, undivided)
    return {"ws_divided": [float(x) for x in head.weighted], "k_low": head.k_by_scenario[0], "k_medium": head.k_by_scenario[1],
            "k_high": head.k_by_scenario[2], "girr_charge": head.charge, "girr_charge_undivided": beside.charge,
            "risk_weight_divisor": frtb.SQRT2}


def _cascade(e: dict) -> dict[str, Any]:
    _, _, frtb, _, _ = _engine()
    ins = _vals(e["inputs"])
    n = len([k for k in ins if k.startswith("lh_")])
    by_horizon = {int(ins[f"lh_{j}"]): ins[f"es_t_p_{j}"] for j in range(2, n + 1)}
    return {"es": frtb.liquidity_cascade_es(ins["es_t_p"], by_horizon, int(ins["t"]))}


COMPUTE = {"sa-ccr": _sa_ccr, "output-floor": _floor, "ba-cva": _ba_cva, "frtb-liquidity-cascade": _cascade}


def _compute(e: dict) -> dict[str, Any]:
    if e["calculator"] == "frtb-sbm":
        return {"sbm-low-and-high-scenarios": _sbm_scenarios, "girr-delta-charge-sqrt2": _girr}.get(e["id"], _sbm)(e)
    return COMPUTE[e["calculator"]](e)


def _holds(e: dict, out: dict[str, Any], ins: dict[str, Any]) -> bool:
    """The statement of an invariant case, evaluated on the engine's outputs (a False is refused by the schema)."""
    def close(a: float, b: float) -> bool:
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)

    i = e["id"]
    if i == "ba-cva-rho-one":
        return close(out["k_reduced"], sum(v for k, v in ins.items() if k.startswith("scva_")))
    if i == "ba-cva-hedges-floor":
        return out["k_full"] >= ins["beta"] * ins["k_reduced"] - 1e-12
    if i == "sbm-low-and-high-scenarios":
        return close(out["rho_medium"], ins["rho"]) and out["rho_low"] <= out["rho_medium"] <= out["rho_high"]
    if i.startswith("sbm-"):
        return close(out["sbm_charge"], max(out[f"cross_bucket_{sc}"] for sc in SCENARIOS))
    if i == "girr-delta-charge-sqrt2":
        return close(out["girr_charge_undivided"], out["girr_charge"] * out["risk_weight_divisor"])
    if i == "cascade-all-lh-ten":
        return close(out["es"], ins["es_t_p"])
    if i == "cascade-two-horizons":
        return out["es"] >= ins["es_t_p"] and close(out["es"], math.sqrt(ins["es_t_p"] ** 2 + (ins["es_t_p_2"] * math.sqrt((ins["lh_2"] - ins["lh_1"]) / ins["t"])) ** 2))
    raise ValueError(f"no statement is evaluated for the invariant case {i!r}")


def _entry(e: dict) -> dict[str, Any]:
    if e["in_force_date"] != _chapter_date(e["paragraph"]):
        raise ValueError(f"{e['id']}: the in-force date {e['in_force_date']} is not the engine's for {e['paragraph']}")
    values = _compute(e)
    specs = e["output_specs"]
    missing = [s["name"] for s in specs if s["name"] not in values]
    if missing:
        raise ValueError(f"{e['id']}: the engine path does not produce {missing}")
    outputs = [{**s, "value": values[s["name"]]} for s in specs]
    invariant = e["kind"] == "invariant"
    return {"id": e["id"], "calculator": e["calculator"], "title": e["title"], "kind": e["kind"], "paragraph": e["paragraph"],
            "paragraph_range": e["paragraph_range"], "in_force_date": e["in_force_date"], "published_date": e["published_date"],
            "source": e["source"], "trades": e["trades"], "inputs": e["inputs"], "outputs": outputs,
            "published": e["published"], "statement": e["statement"] if invariant else None,
            "holds": _holds(e, values, _vals(e["inputs"])) if invariant else None, "tolerance_relative": 1e-09}


# --- the tables, the phase-in and the CRE20 grid -------------------------------------------------------------------------------


def _phase_in() -> list[dict[str, Any]]:
    _, _, _, output_floor, _ = _engine()
    rows = []
    for year in range(2023, 2029):
        p = output_floor.phase_in_factor(year)
        rows.append({"year": year, "effective_from": f"{year}-01-01", "factor": p.value, "table": p.table, "paragraph": p.paragraph,
                     "in_force_date": p.in_force})
    return rows


def _grid(keys: list[dict]) -> list[dict[str, Any]]:
    *_, standardised = _engine()
    rows = []
    for k in keys:
        p = standardised.lookup(k["exposure_class"], k["key"], short_term=k["short_term"],
                                cash_flow_dependent=k["cash_flow_dependent"], counterparty_weight=k["counterparty_weight"])
        rows.append({**k, "risk_weight": p.value, "table": p.table, "paragraph": p.paragraph, "in_force_date": p.in_force})
    return rows


def _tables(heads: list[dict]) -> list[dict[str, Any]]:
    sa_ccr, ba_cva, frtb, _, _ = _engine()
    source = {"cre52-72-table-2": (sa_ccr.SUPERVISORY_PARAMETERS, "decimal"), "mar50-16-table-1": (ba_cva.SECTOR_RISK_WEIGHTS, "decimal"),
              "mar33-12-table-2": (frtb.LIQUIDITY_HORIZONS_TABLE_2, "days"), "mar33-4-table-1": (frtb.LIQUIDITY_HORIZONS_TABLE_1, "days")}
    tables = []
    for h in heads:
        data, unit = source[h["id"]]
        params = list(data.values())
        for p in params:
            if (p.paragraph, p.table, p.in_force) != (params[0].paragraph, params[0].table, params[0].in_force):
                raise ValueError(f"{h['id']}: the rows of the engine's table do not share one paragraph, table and in-force date")
        tables.append({**h, "table": params[0].table, "paragraph": params[0].paragraph, "in_force_date": params[0].in_force,
                       "rows": [{"key": k, "parameter": name, "value": p.value, "unit": unit} for (k, name), p in data.items()]})
    return tables


# --- the document -----------------------------------------------------------------------------------------------------------------


def build() -> dict[str, Any]:
    """The regulatory-calculators document, every value computed by the engine. Deterministic: no clock, no random draw."""
    data = json.loads(INPUTS.read_text(encoding="utf-8"))
    ev = engine_version()
    lineage = lin.build("REGULATORY", sources=[], truth_status="published-answer", seed=SEED, code_version="regulatory-parity-bake/1",
                        riskvalidation_version=ev, generators=("regulatory-parity-bake",))
    doc = {
        "schema": "contraste.regulatory/v1", "case_id": "REGULATORY", "document_id": f"regulatory-calculators-{ev.split('+')[-1]}",
        "engine": {"name": "riskvalidation", "version": ev},
        "units": {"money": "as stated per value (USD thousands for CRE99, index points for RBC20.13)", "rate": "decimal", "dates": "ISO-8601"},
        "official_examples": [_entry(e) for e in data["official_examples"]],
        "invariant_cases": [_entry(e) for e in data["invariant_cases"]],
        "output_floor_phase_in": _phase_in(),
        "parameter_tables": _tables(data["parameter_tables"]),
        "cre20_grid": _grid(data["cre20_grid_keys"]),
        "provenance": lineage.provenance(),
        "lane": {"lane": "precompute", "reasons": []},
    }
    size = len(json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    gate = classify_lane(pure_python=False, wheels=ENGINES, run_ms=RUN_MS, trace_bytes=size)
    doc["lane"] = {"lane": gate["lane"], "reasons": gate["reasons"]}
    return doc


def bake(output_root: Path | str) -> dict[str, Any]:
    """Build, check and write ``<output_root>/regulatory/calculators.json``; any finding of the contract checker refuses the document."""
    doc = build()
    found = _semantics().check_regulatory(doc)
    if found:
        raise ValueError(f"{DOCUMENT_REL}: check_regulatory refuses the document: {found[:5]}")
    return write_artifact(Path(output_root), DOCUMENT_REL, doc, exact=EXACT, engines=ENGINES, run_ms=RUN_MS)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from ..pipeline import DERIVED

    ap = argparse.ArgumentParser(description="Bake data/derived/regulatory/calculators.json through riskvalidation.regulatory")
    ap.add_argument("--output-root", default=None, help=f"the derived-data root (default {DERIVED})")
    args = ap.parse_args(argv)
    entry = bake(args.output_root or DERIVED)
    print(f"wrote {entry['path']} ({entry['bytes']:,} bytes, lane {entry['lane']})", file=sys.stderr)
    return 0
