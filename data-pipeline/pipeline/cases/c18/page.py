"""The generated results block of docs/cases/C18.md: every figure is read from the committed documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END``; ``write_page`` replaces the block in the page and a test compares the committed
block with a fresh render (CT-1821). Money is CLP million, ratios are percent of RWA.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

BEGIN = "<!-- c18-results:begin -->"
END = "<!-- c18-results:end -->"
SCENARIO_ORDER = ("baseline", "eba-2025-adverse", "fed-2026-severely-adverse", "ngfs-delayed-transition")
TITLES = {"baseline": "Fed 2026 baseline", "eba-2025-adverse": "EBA/ESRB 2025 adverse", "fed-2026-severely-adverse": "Fed 2026 severely adverse",
          "ngfs-delayed-transition": "NGFS Phase 5 Delayed transition"}


def m(x: float | None) -> str:
    return "n/a" if x is None else f"{x:,.0f}"


def pct(x: float | None, nd: int = 2) -> str:
    return "n/a" if x is None else f"{x * 100:.{nd}f}"


def _case(o: dict[str, Any], name: str) -> dict[str, Any]:
    return next(c for c in o["capital_plan"]["cases"] if c["case"] == name)


def results_block(variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append
    scen = [v for v in SCENARIO_ORDER if v in variants]
    base = variants[scen[0]]["outputs"]
    agg = base["aggregation"]
    start = base["capital_start"]
    w("### The four marginals and the headline capital (one year, 99.9 percent, CLP million)")
    w("")
    w(f"The headline capital is the simple sum of the four economic capital figures, **{m(agg['headline']['capital_clp_m'])}** "
      f"({pct(agg['headline']['capital_clp_m'] / start['rwa_clp_m'])} percent of the RWA of {m(start['rwa_clp_m'])}). Economic capital is the VaR less the expected loss "
      "(dossier 04 l.652-653). Every other figure below is information for the validator, not capital.")
    w("")
    w("| Risk | Expected loss | VaR | ES | EC | Producer |")
    w("|---|---:|---:|---:|---:|---|")
    for x in agg["marginals"]:
        w(f"| {x['risk']} | {m(x['el_clp_m'])} | {m(x['var_clp_m'])} | {m(x['es_clp_m'])} | {m(x['ec_clp_m'])} | {x['producer']} |")
    w("")
    if "t-copula-baseline" in variants:
        a = variants["t-copula-baseline"]["outputs"]
        w("### The dependence band (information, not capital)")
        w("")
        w("| Method | nu | Capital | Share of the simple sum | Status |")
        w("|---|---:|---:|---:|---|")
        for r in a["aggregation"]["band"]:
            nu = "" if r["nu"] is None else f"{r['nu']:g}"
            w(f"| {r['method']} | {nu} | {m(r['capital_clp_m'])} | {pct(r['diversification_factor'], 1)} percent | {r['status']} |")
        w("")
        s = a["correlation_stress"]["aggregation"]
        g0 = next(r for r in a["aggregation"]["band"] if r["method"] == "gaussian-copula")["capital_clp_m"]
        g1 = next(r for r in s["band"] if r["method"] == "gaussian-copula")["capital_clp_m"]
        w(f"With market-credit raised to 0.8 the Gaussian copula figure moves from {m(g0)} to {m(g1)} ({pct(g1 / g0 - 1, 1)} percent). "
          f"The additive approximation exceeds the Gaussian copula figure by {pct(a['rosenberg_schuermann']['case_additive_overestimate'], 1)} percent "
          "(the published 30 to 40 percent is a reference and no gate).")
        w("")
        mr = a["aggregation"]["model_risk"]["barrieu_scandolo"]
        w(f"Model risk over the band: AM {pct(mr['am'], 1)} percent, RM {mr['rm']:.3f} (Barrieu and Scandolo). The Euler allocation of the aggregate expected shortfall "
          "(Gaussian copula):")
        w("")
        w("| Risk | Contribution | Share | Standalone ES | Euler benefit |")
        w("|---|---:|---:|---:|---:|")
        e = a["aggregation"]["euler"]
        for al, mg, b in zip(e["allocation"], a["aggregation"]["marginals"], a["aggregation"]["diversification"]["euler_benefit_by_risk"], strict=True):
            w(f"| {al['risk']} | {m(al['contribution_clp_m'])} | {pct(al['share'], 1)} percent | {m(mg['es_clp_m'])} | {pct(b['benefit'], 1)} percent |")
        w("")
    w("### The three-year CET1 path under each scenario (loss-only depletion, percent of RWA)")
    w("")
    w(f"CET1 at the jump-off is {pct(start['cet1_ratio'])} percent of RWA and the PE ratio {pct(start['pe_ratio'])} percent. The internal target OI is "
      f"{pct(base['internal_capital_target']['oi'])} percent; the labelled PPNR row credits the earnings.")
    w("")
    w("| Scenario | Loss, years 1-3 | CET1 year 1 | CET1 year 2 | CET1 year 3 | CET1 year 3 with PPNR | PE year 3 | Smallest headroom over OI | P2G proxy |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for vid in scen:
        o, imp = variants[vid]["outputs"], variants[vid]["impact"]
        h = o["headline_cet1"]
        sw = _case(o, "stress-without-mitigation")["years"]
        w(f"| {TITLES[vid]} | {m(sum(y['total'] for y in o['losses']['scenario_losses']))} | " + " | ".join(pct(r["cet1_ratio"]) for r in h["rows"]) +
          f" | {pct(h['ppnr']['rows'][-1]['cet1_ratio_with_ppnr'])} | {pct(sw[-1]['pe']['pct_of_rwa'])} | {pct(imp['oi_headroom_min']['value'])} | {pct(o['p2g_proxy']['value'])} |")
    w("")
    w("### Losses of the scenario by risk and year (CLP million)")
    w("")
    w("| Scenario | Year | Credit | Market | IRRBB | Operational | Total |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for vid in scen:
        for y in variants[vid]["outputs"]["losses"]["scenario_losses"]:
            w(f"| {TITLES[vid]} | {y['year']} | {m(y['credit'])} | {m(y['market'])} | {m(y['irrbb'])} | {m(y['operational'])} | {m(y['total'])} |")
    w("")
    w("### The satellites: fit on 1985 to 2019 and out-of-time back-cast of 2020 to 2025")
    w("")
    w("| Fed loan type | Link | Window | Observations | R squared | RMSE 2020-25 | Predicted peak | Realised peak | Timing error (quarters) |")
    w("|---|---|---|---:|---:|---:|---:|---:|---:|")
    bc = {b["fed_loan_type"]: b for b in base["backcast"]["per_loan_type"]}
    for s in models["fit"]["satellites"]:
        b = bc[s["fed_loan_type"]]["metrics"]
        w(f"| {s['fed_loan_type']} | {s['link']} | {s['sample_window']['start']} to {s['sample_window']['end']} | {s['n_obs']} | {s['fit_statistics']['r_squared']:.3f} | "
          f"{pct(b['rmse'], 3)} | {pct(b['peak_predicted'], 2)} ({b['peak_predicted_quarter']}) | {pct(b['peak_realised'], 2)} ({b['peak_realised_quarter']}) | "
          f"{b['peak_timing_error_quarters']} |")
    w("")
    w("### Reverse stress")
    w("")
    if "reverse-stress" in variants:
        r = variants["reverse-stress"]["outputs"]
        sol, fp = r["solution"], r["failure_point"]
        names = [f["id"] for f in r["factor_space"]["factors"]]
        w(f"The failure point is CET1 at the Chilean legal minimum stack, {pct(fp['stack']['total'])} percent of RWA, from {pct(fp['cet1_ratio_start'])} percent. "
          f"The minimum Mahalanobis distance scenario shifts {names[0]} by {sol['x_star'][0]:+.2f} and {names[1]} by {sol['x_star'][1]:+.2f} percentage points, "
          f"a distance of {sol['mahalanobis_distance']:.2f} and a chi-square tail probability of {pct(sol['plausibility']['tail_probability'], 1)} percent; the loss it "
          f"causes is {m(sol['loss_at_z_star_clp_m'])} against the threshold {m(sol['loss_threshold_clp_m'])}.")
        w("")
    w("### Annex 3 summary under the Fed 2026 severely adverse scenario (percent of RWA, CLP million)")
    w("")
    w("| Row | Label | A | B | C | D |")
    w("|---|---|---:|---:|---:|---:|")
    fed = variants["fed-2026-severely-adverse"]["outputs"] if "fed-2026-severely-adverse" in variants else base

    def cell(c: dict[str, Any], ratio: bool) -> str:
        if c["status"] != "value":
            return c["status"]
        return pct(c["value"]) if ratio else m(c["value"])

    for row in fed["annex3"]["rows"]:
        w(f"| {row['row_id']} | {row['label_cmf']} | {cell(row['a'], True)} | {cell(row['b'], False)} | {cell(row['c'], False)} | {cell(row['d'], False)} |")
    w("")
    w("### Named parameters (conventions and case assumptions)")
    w("")
    w("| Parameter | Value | Label |")
    w("|---|---|---|")
    for k, p in models["fit"]["named_parameters"].items():
        val = p.get("values", p.get("value", "matrix"))
        w(f"| {k} | {val if not isinstance(val, float) else f'{val:.6g}'} | {p['label']} |")
    w("")
    w("### Validation tests")
    w("")
    w("| Variant | Test | Segment | Light |")
    w("|---|---|---|---|")
    for vid in [*scen, *(v for v in ("t-copula-baseline", "reverse-stress") if v in variants)]:
        for tr in variants[vid]["tests"]:
            w(f"| {vid} | {tr['test_id']} | {tr['segment'] or ''} | {tr['light']} |")
    return "\n".join(lines) + "\n"


def write_page(page: Path, variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> None:
    text = page.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    page.write_text(f"{head}{BEGIN}\n{results_block(variants, models)}{END}{tail}", encoding="utf-8", newline="\n")
