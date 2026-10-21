"""The generated blocks of docs/cases/C16.md: every figure is read from the committed documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END`` from the seven documents; ``raw_block`` renders the table of raw files
from ``raw-sources.txt``; ``write_page`` replaces both in the page, ``findings`` compares a page with a fresh render (CT-1622).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

BEGIN, END = "<!-- c16-results:begin -->", "<!-- c16-results:end -->"
RAW_BEGIN, RAW_END = "<!-- c16-raw:begin -->", "<!-- c16-raw:end -->"


def m(x: float) -> str:
    """USD thousands as USD million with one decimal."""
    return f"{x / 1000.0:,.1f}"


def pct(x: float) -> str:
    return f"{x * 100:.1f}"


def sp(s: dict[str, Any] | None) -> str:
    if s is None:
        return "no daily path"
    return f"survives the {s['horizon_days']}-day horizon" if s["kind"] == "survives-horizon" else f"day {s['day']}"


def results_block(lcr: dict, adv: dict, ext: dict, fast: dict, htm: dict, rev: dict, mod: dict) -> str:
    docs = {"lcr-standard": lcr, "list-adverse": adv, "list-extreme": ext, "fast-run": fast, "htm-losses": htm}
    out: list[str] = []
    w = out.append
    w("### The five scenario variants at 2022-12-31")
    w("")
    w("Survival period: the first relevant day on which the net liquidity position is negative, or the horizon survived. CBC: the "
      "counterbalancing capacity after haircuts, with the pledged securities out (USD million). The LCR is a Basel formula on call-report aggregates, "
      "never the reported or regulatory LCR of the bank.")
    w("")
    w("| Variant | Horizon (days) | Survival period | Minimum NLP (USD million) | CBC (USD million) | LCR |")
    w("|---|---:|---|---:|---:|---:|")
    for vid, d in docs.items():
        o = d["outputs"]
        p = o["path"]
        w(f"| {d['outputs']['variant']['label']['en']} | {o['variant']['horizon_days']} | {sp(p['survival'] if p else None)} | "
          f"{m(p['minimum_nlp']['value']) if p else 'no daily path'} | {m(o['cbc']['total_liquidity_value'])} | "
          f"{pct(o['lcr']['ratio']) + ' percent' if o['lcr'] else 'not run'} |")
    w("")
    w("### The March 2023 scoring, with both denominators")
    w("")
    dep = adv["outputs"]["balance_sheet"]["deposits"]
    w(f"The realised outflow is stated twice. The Board's review says roughly 85 percent of the deposit base; the amounts it gives (over 40 plus "
      f"over 100 billion USD) are {pct(adv['outputs']['scoring']['denominators'][1]['realised_share'])} percent of the call report's DEP "
      f"({m(dep['dep'])} million). The model's outflow is compared at the 2-day event horizon (the LCR, which has one 30-day aggregate, at its own "
      f"horizon). The lights are descriptive, by the named scoring parameters; one observation, no p-value.")
    w("")
    w("| Variant | Modelled share of the model base | Ratio to the Board's 85 percent | Light | Modelled share of DEP | Ratio to the DEP-based share | Light |")
    w("|---|---:|---:|---|---:|---:|---|")
    for vid, d in docs.items():
        a, b = d["outputs"]["scoring"]["denominators"]
        w(f"| {d['outputs']['variant']['label']['en']} | {pct(a['modelled_share'])} percent | {a['ratio']:.3f} | {a['light']} | "
          f"{pct(b['modelled_share'])} percent | {b['ratio']:.3f} | {b['light']} |")
    w("")
    an = fast["outputs"]["scoring"]["svb_anchor"]
    w(f"The SVB observation is a labelled anchor, not a forecast: {pct(an['outflow_share'])} percent in {an['days']} days implies a daily rate of "
      f"{an['implied_daily_rate']:.6f}.")
    w("")
    w("| Table A.1 row | Year | Observed share | Days | Fast-run modelled share | Role |")
    w("|---|---:|---:|---:|---:|---|")
    for r in fast["outputs"]["scoring"]["table_a1_scoring"]:
        w(f"| {r['bank']} | {r['year']} | {pct(r['observed_share'])} percent | {r['horizon_days']} | "
          f"{pct(r['modelled_share']) + ' percent' if r['modelled_share'] is not None else 'beyond the 5-day ladder'} | {r['role']} |")
    w("")
    cal = mod["fit"]["calibration"]
    w(f"The fast-run rate is calibrated on the rows dated before 2023 only ({', '.join(cal['split']['calibrated_on'])}): the "
      f"{mod['fit']['conventions']['fast_run_calibration_rule']['rule']} is {cal['fitted_daily_rate']['value']:.6f} per day. The 2023 rows are scored, never calibrated on.")
    w("")
    w("### The LCR, the mapping and its band")
    w("")
    lc = lcr["outputs"]["lcr"]
    h = lc["hqla"]
    w(f"HQLA {m(h['hqla'])} million (Level 1 {m(h['l1'])}, Level 2A {m(h['l2a'])} before the 40 percent cap, which removes {m(h['adj_40'])}); outflows "
      f"{m(lc['total_outflows'])}, inflows counted {m(lc['inflows_counted'])} (cap {pct(lc['inflow_cap'])} percent of outflows), net outflows {m(lc['net_outflows'])}; "
      f"ratio {pct(lc['ratio'])} percent. A ratio below 100 percent under stress is not a breach.")
    w("")
    w("| Mapping of the uninsured deposits (DEPUNA) | LCR category | Uninsured outflow | Net outflows | Ratio |")
    w("|---|---|---:|---:|---:|")
    for r in lc["mapping_sensitivity"]:
        w(f"| {r['mapping_id']} | {r['lcr_category']} | {m(r['uninsured_outflow'])} | {m(r['net_outflows'])} | {pct(r['ratio'])} percent |")
    w("")
    w("### Held-to-maturity losses in the CBC")
    w("")
    hm = htm["outputs"]["htm"]
    rep = hm["reported"]
    rv = hm["revaluation"]
    w(f"The held-to-maturity book is {m(rep['htm_amortised_cost'])} million at amortised cost and {m(rep['htm_fair_value'])} at fair value, an unrealised loss of "
      f"{m(-rep['htm_unrealised'])}. Applied to the securities book as a whole, it takes the CBC from {m(hm['cbc_without_loss'])} to {m(hm['cbc_with_loss'])} million "
      f"(removing {m(hm['cbc_removed'])}). The counterfactual of the Bank Term Funding Program's par valuation (announced 2023-03-12, after the run) gives "
      f"{m(hm['btfp_par']['cbc_at_par'])} million. ")
    if rv["status"] == "evaluated":
        w(f"The revaluation of the book from its maturity profile under the Treasury curve of {rv['curve_date']} gives {m(rv['model_fair_value'])} million against the "
          f"reported {m(rv['reported_fair_value'])}: {pct(rv['relative_difference'])} percent of the reported unrealised loss.")
    w("")
    w("### The reverse stress")
    w("")
    tgt = rev["outputs"]["target"]["days"]
    w(f"The run-off multiplier at which the survival period falls to {tgt} days: the threshold multiplier, the smallest at which it is at most the target, with "
      f"the survival reached there. A base whose ladder is not longer than the target is refused.")
    w("")
    w("| Base | Base survival | Largest rate below 1 | Cap | Threshold multiplier | Survival at the multiplier |")
    w("|---|---|---:|---:|---:|---|")
    for b in rev["outputs"]["bases"]:
        s = b["solved"]
        w(f"| {b['label']['en']} | {sp(b['base_survival'])} | {b['max_rate_below_one']:.6f} | {b['max_multiplier']:.2f} | "
          f"{s['multiplier'] if s['multiplier'] is not None else 'refused'} | {s['survival_at_multiplier'] if s['survival_at_multiplier'] is not None else s['refusal_reason']['en']} |")
    w("")
    w("### As the held-to-maturity losses grew")
    w("")
    w("| Date | HTM unrealised loss | CBC, amortised cost | CBC, fair value | LiST Adverse survival | LiST Extreme survival | LCR |")
    w("|---|---:|---:|---:|---|---|---:|")
    rows = [(t["as_of"], t["htm_unrealised_loss"], t["cbc_amortised_basis"], t["cbc_fair_value_basis"], sp(ta["survival"]), sp(te["survival"]), tl["lcr_ratio"])
            for t, ta, te, tl in zip(adv["outputs"]["time_block"], adv["outputs"]["time_block"], ext["outputs"]["time_block"], lcr["outputs"]["time_block"])]
    for d_, loss, ca, cf, sa, se, lr in rows:
        w(f"| {d_} | {m(loss)} | {m(ca)} | {m(cf)} | {sa} | {se} | {pct(lr)} percent |")
    w(f"| 2022-12-31 | {m(rep['htm_unrealised'])} | {m(hm['cbc_without_loss'])} | {m(hm['cbc_with_loss'])} | {sp(adv['outputs']['path']['survival'])} | "
      f"{sp(ext['outputs']['path']['survival'])} | {pct(lc['ratio'])} percent |")
    w("")
    w("### The deposit base and the denominators")
    w("")
    w(f"Estimated uninsured deposits (DEPUNA) {m(dep['depuna'])} million and insured deposits (DEPINS) {m(dep['depins'])} cover the domestic offices: "
      f"{pct(dep['uninsured_share_of_depdom'])} percent of DEPDOM ({m(dep['depdom'])}); against the wider DEP ({m(dep['dep'])}, with the foreign offices) the uninsured share "
      f"is {pct(dep['uninsured_share_of_dep'])} percent. Both denominators are stated wherever the share appears.")
    w("")
    ar = adv["outputs"]["aggregate_record"]
    if ar:
        w("### The aggregate record: Federal Reserve H.8, deposits of domestically chartered banks (USD billion, seasonally adjusted)")
        w("")
        w("| Week ending (Wednesday) | Large banks | Small banks |")
        w("|---|---:|---:|")
        small = {p["date"]: p["value"] for p in ar["series"][1]["points"]}
        for p in ar["series"][0]["points"]:
            if "2023-02-01" <= p["date"] <= "2023-03-29":
                w(f"| {p['date']} | {p['value']:,.1f} | {small[p['date']]:,.1f} |")
        w("")
    gv = mod["fit"]["generator"]["verification"]
    w("### The depositor generator")
    w("")
    w(f"A seeded generator with a known truth (a two-state hazard per segment, shared stress state): {gv['n_draws']:,} draws reproduce its exact truth within "
      f"{gv['max_abs_error']:.2e} of the largest error against a Monte Carlo standard error of {gv['mc_standard_error']:.2e} "
      f"({'within' if gv['within_error'] else 'outside'} the named tolerance).")
    return "\n".join(out) + "\n"


def raw_block(raw: dict[str, Any]) -> str:
    out = ["| Source | File | Bytes | SHA-256 | Retrieved |", "|---|---|---:|---|---|"]
    for sid, row in raw["sources"].items():
        files = row["files"]
        shown = files if sid != "fed-h8" else files
        for f in shown:
            out.append(f"| `{sid}` | `{f['name']}` | {f['bytes']:,} | `{f['sha256']}` | {f['retrieved']} |")
    return "\n".join(out) + "\n"


def _replace(text: str, begin: str, end: str, block: str) -> str:
    head, rest = text.split(begin, 1)
    _, tail = rest.split(end, 1)
    return f"{head}{begin}\n{block}{end}{tail}"


def write_page(path: Path, lcr: dict, adv: dict, ext: dict, fast: dict, htm: dict, rev: dict, mod: dict, raw: dict) -> None:
    text = Path(path).read_text(encoding="utf-8")
    text = _replace(text, BEGIN, END, results_block(lcr, adv, ext, fast, htm, rev, mod))
    text = _replace(text, RAW_BEGIN, RAW_END, raw_block(raw))
    Path(path).write_text(text, encoding="utf-8", newline="\n")


def findings(text: str, lcr: dict, adv: dict, ext: dict, fast: dict, htm: dict, rev: dict, mod: dict) -> list[str]:
    """What differs between the results block of a page and a fresh render of the documents."""
    if BEGIN not in text or END not in text:
        return ["the page has no results block"]
    got = text.split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")
    want = results_block(lcr, adv, ext, fast, htm, rev, mod).strip("\n")
    return [] if got == want else ["the results block is not the one generated from the committed documents"]
