"""The generated blocks of docs/cases/C15.md: every figure is read from the committed documents, never typed.

Three blocks sit between marker comments: the outcomes of the executive brief (``outcomes``), the raw files with their hash (``files``) and the
results (``results``). ``render`` returns the text of each, ``write_page`` replaces them in the page, and a test compares the committed blocks
with a fresh render (CT-1514). Money is CLP million; UR balances are CLF (UF) million.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

BEGIN = "<!-- c15-results:begin -->"
END = "<!-- c15-results:end -->"
BLOCKS = {"outcomes": ("<!-- c15-outcomes:begin -->", "<!-- c15-outcomes:end -->"),
          "files": ("<!-- c15-files:begin -->", "<!-- c15-files:end -->"),
          "results": (BEGIN, END)}
SHOCKS = ("parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down")
ORDER = ("long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active")


def m(x: float) -> str:
    return f"{x:,.0f}"


def pct(x: float, nd: int = 1) -> str:
    return f"{x * 100:.{nd}f}"


def _ids(variants: dict[str, dict[str, Any]]) -> list[str]:
    return [v for v in ORDER if v in variants] + sorted(set(variants) - set(ORDER))


def distance(o: dict[str, Any]) -> tuple[float, str]:
    """The smallest distance, in bp, between a post-shock rate and its floor, and where it is, from the curve and the shapes of the document."""
    floors = {"clp": o["floors"]["other_floor"], "ur": o["floors"]["ur_floor"]}
    best, where = float("inf"), ""
    for key in ("clp", "ur"):
        r0 = o["curves"][key]["zero_rates_at_midpoints"]
        for row in o["eve"]["rows"]:
            gap = min((r0[k] + row[key]["shape_bp"][k] / 1e4 - floors[key]) * 1e4 for k in range(19))
            if gap < best:
                best, where = gap, f"the {key.upper()} delta EVE under {row['shock']}"
        for row in o["nii"]["rows"]:
            gap = min((r0[k] + row[key]["shock_bp"] / 1e4 - floors[key]) * 1e4 for k in range(6))
            if gap < best:
                best, where = gap, f"the {key.upper()} delta NII under {row['shock']}"
    return best, where


def distance_bp(o: dict[str, Any]) -> float:
    return distance(o)[0]


def _max(rows: list[dict[str, Any]], key: str) -> float:
    return max(r["pair"][key] for r in rows)


def outcomes_block(variants: dict[str, dict[str, Any]]) -> str:
    ids = _ids(variants)
    o = {v: variants[v]["outputs"] for v in ids}
    eve = {v: o[v]["eve"] for v in ids}
    long_ = o["long-uf"]
    lines = ["| Outcome | Proof point | Source |", "|---|---|---|"]
    lines.append(f"| The standardised EVE measure crosses the 15 percent test only where the pesos book is long-dated | delta EVE is {pct(eve['long-uf']['delta_eve_share_tier1'])}, "
                 f"{pct(eve['short-uf']['delta_eve_share_tier1'])} and {pct(eve['floors-active']['delta_eve_share_tier1'])} percent of Tier 1 in the long UF, "
                 f"short UF and floors variants and {pct(eve['clp-steepener']['delta_eve_share_tier1'])} percent in the CLP steepener variant, which is "
                 f"{'above' if eve['clp-steepener']['delta_eve_share_tier1'] > 0.15 else 'below'} the threshold | `eve` of `data/derived/C15/*.json` |")
    ic, d_nii = long_["indexation_charge"]["charge"], long_["nii"]["delta_nii"]
    lines.append(f"| The indexation of the UF position is a large part of the delta NII | in the long UF variant the standard charge is {m(ic)} CLP million, "
                 f"{pct(ic / d_nii, 0)} percent of the delta NII of {m(d_nii)}; it depends on the net UF position, not on the rate shock | "
                 "`indexation_charge`, `nii` of `long-uf.json` |")
    off = o["offset-on-off"]
    w_on, w_off = _max(off["eve"]["rows"], "with_offset"), _max(off["eve"]["rows"], "without_offset")
    lines.append(f"| The 50 percent CLP and CLF offset changes the measure when the legs move in opposite directions | in the offset variant the delta EVE is "
                 f"{m(w_on)} with the offset and {m(w_off)} without it ({m(w_off - w_on)} CLP million of difference) | `eve.rows[].pair` of `offset-on-off.json` |")
    dist, where = distance(o["floors-active"])
    lines.append(f"| The post-shock floors do not bind on the curves of the valuation date | the smallest distance between a post-shock rate and its floor is "
                 f"{dist:.1f} bp, in {where} | `floors` of `floors-active.json` |")
    lines.append(f"| A CPI surprise of 2.5 percentage points moves the value of the net UF position | the effect on the long UF book is "
                 f"{m(o['cpi-surprise']['cpi_scenario']['effect'])} CLP million (negative is a gain) | `cpi_scenario` of `cpi-surprise.json` |")
    return "\n".join(lines) + "\n"


def files_block(raw_sources: dict[str, Any]) -> str:
    lines = ["| Source | File | Bytes | SHA-256 | Retrieved |", "|---|---|---:|---|---|"]
    for sid, row in raw_sources["sources"].items():
        for f in row["files"]:
            lines.append(f"| `{sid}` | `{f['name']}` | {f['bytes']:,} | `{f['sha256']}` | {f['retrieved']} |")
    return "\n".join(lines) + "\n"


def results_block(variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> str:
    ids = _ids(variants)
    o = {v: variants[v]["outputs"] for v in ids}
    lines: list[str] = []
    w = lines.append
    first = o[ids[0]]
    w("### The curves")
    w("")
    w(f"Valuation date {first['as_of']}, the last business day of {first['curves_month']} on which every chosen series has a value; UF value "
      f"{first['ur_currency']['uf_value']:,.2f} CLP per UF. The curves are Contraste's adaptation of the Banco Central de Chile's data.")
    w("")
    w("| Curve | Tenor (years) | Observed yield (percent) | Zero rate (percent, continuous) |")
    w("|---|---:|---:|---:|")
    for key in ("clp", "ur"):
        c = first["curves"][key]
        for p in c["points"]:
            w(f"| {c['curve']} | {p['tenor_years']:.4g} | {p['observed_yield'] * 100:.3f} | {p['zero_rate'] * 100:.3f} |")
    w("")
    w("| Curve | Series | beta0 | beta1 | beta2 | tau (years) | RMSE (bp) |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for key in ("clp", "ur"):
        c = first["curves"][key]
        p = {x["name"]: x["value"] for x in c["fit"]["parameters"]}
        w(f"| {c['curve']} | {', '.join(f'`{s}`' for s in c['series_codes'])} | {p['beta0']:.5f} | {p['beta1']:.5f} | {p['beta2']:.5f} | {p['tau']:.2f} | "
          f"{c['fit']['rmse_bp']:.3f} |")
    w("")
    w("### The six variants")
    w("")
    w("| Variant | Description | Parameters |")
    w("|---|---|---|")
    for v in ids:
        d = o[v]["variant"]
        w(f"| `{v}` {d['label']['en']} | {d['description']['en']} | " + "; ".join(f"{p['name']} {p['value']:g} ({p['unit']})" for p in d["parameters"]) + " |")
    w("")
    w("### The book")
    w("")
    w("| Variant | Tier 1 | CLP assets | CLP liabilities | UR assets (CLF) | UR liabilities (CLF) | Net UF position (CLF) | Net UF position (CLP) | Share of Tier 1 |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for v in ids:
        x = o[v]
        clp, ur = x["legs"]
        pn = x["indexation_charge"]["pn_ur"]
        w(f"| {v} | {m(x['thresholds']['tier1'])} | {m(clp['assets_total'])} | {m(clp['liabilities_total'])} | {m(ur['assets_total'])} | "
          f"{m(ur['liabilities_total'])} | {ur['net_position']:,.1f} | {m(pn)} | {pct(pn / x['thresholds']['tier1'])} percent |")
    w("")
    w("### Delta EVE by shock and leg (CLP million, positive is a loss)")
    w("")
    w("| Variant | Leg | " + " | ".join(SHOCKS) + " |")
    w("|---|---|" + "---:|" * 6)
    for v in ids:
        rows = o[v]["eve"]["rows"]
        w(f"| {v} | CLP | " + " | ".join(m(r["pair"]["delta_clp"]) for r in rows) + " |")
        w(f"| {v} | UR | " + " | ".join(m(r["pair"]["delta_ur"]) for r in rows) + " |")
        w(f"| {v} | pair with the offset | " + " | ".join(m(r["pair"]["with_offset"]) for r in rows) + " |")
        w(f"| {v} | pair without the offset | " + " | ".join(m(r["pair"]["without_offset"]) for r in rows) + " |")
    w("")
    w("### Delta NII, the indexation charge and the thresholds (CLP million, positive is a loss)")
    w("")
    w("| Variant | CLP up | CLP down | UR up | UR down | Largest pair | Indexation charge | Delta NII | Share of Tier 1 | Delta EVE | Share of Tier 1 | "
      "NII over the 12-month margin | Prioritised |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for v in ids:
        x = o[v]
        n, e = x["nii"], x["eve"]
        t = {i["id"]: i for i in x["thresholds"]["tests"]}
        r = n["rows"]
        w(f"| {v} | {m(r[0]['clp']['delta_nii'])} | {m(r[1]['clp']['delta_nii'])} | {m(r[0]['ur']['delta_nii'])} | {m(r[1]['ur']['delta_nii'])} | "
          f"{m(n['max_pair'])} | {m(n['indexation_charge'])} | {m(n['delta_nii'])} | {pct(n['delta_nii_share_tier1'])} percent | {m(e['delta_eve'])} | "
          f"{pct(e['delta_eve_share_tier1'])} percent | {pct(t['nii-margin']['ratio'])} percent | {'yes' if x['thresholds']['prioritised'] else 'no'} |")
    w("")
    w("### The 50 percent CLP and CLF offset, on and off (CLP million)")
    w("")
    w("| Variant | State | Delta EVE with the offset | Delta EVE without | Difference | Largest NII pair with the offset | Without |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for v in ids:
        x = o[v]
        a, b = _max(x["eve"]["rows"], "with_offset"), _max(x["eve"]["rows"], "without_offset")
        c, d = _max(x["nii"]["rows"], "with_offset"), _max(x["nii"]["rows"], "without_offset")
        w(f"| {v} | {x['offset_rule']['state']} | {m(a)} | {m(b)} | {m(b - a)} | {m(c)} | {m(d)} |")
    w("")
    w("### The post-shock floors")
    w("")
    w("| Variant | UR floor | Other floor | Combinations where a floor binds | Smallest distance to a floor (bp) |")
    w("|---|---:|---:|---:|---:|")
    for v in ids:
        f = o[v]["floors"]
        w(f"| {v} | {f['ur_floor'] * 100:.0f} percent | {f['other_floor'] * 100:.0f} percent | {len(f['effects'])} | {distance_bp(o[v]):.2f} |")
    w("")
    w("### The indexation charge and the CPI surprise (CLP million)")
    w("")
    w("| Variant | Net UF position (CLP) | Indexation charge | Share of the delta NII | CPI surprise (pp) | Effect (negative is a gain) |")
    w("|---|---:|---:|---:|---:|---:|")
    for v in ids:
        x = o[v]
        ic, cpi = x["indexation_charge"], x["cpi_scenario"]
        surprise = "n/a" if cpi is None else f"{cpi['surprise_pp']:g}"
        effect = "n/a" if cpi is None else m(cpi["effect"])
        w(f"| {v} | {m(ic['pn_ur'])} | {m(ic['charge'])} | {pct(ic['charge'] / x['nii']['delta_nii'], 0)} percent | {surprise} | {effect} |")
    w("")
    w("### Dynamic NII, 12 months, constant balance sheet (CLP million)")
    w("")
    w("| Variant | Leg | Base | Parallel up (+300 bp) | Parallel down (-300 bp) | Change for up | Change for down |")
    w("|---|---|---:|---:|---:|---:|---:|")
    for v in ids:
        for leg in o[v]["dynamic_nii"]["legs"]:
            b, u, d = leg["scenarios"]
            w(f"| {v} | {leg['leg']} | {m(b['total'])} | {m(u['total'])} | {m(d['total'])} | {m(-u['delta_vs_base'])} | {m(-d['delta_vs_base'])} |")
    w("")
    w("### Deposit assumptions and their caps")
    w("")
    w("| Category | Balance (CLP million) | Requested share | Used share | Requested maturity (years) | Used maturity (years) | Cap applied |")
    w("|---|---:|---:|---:|---:|---:|---|")
    for s in first["nmd_segments"]:
        w(f"| {s['category']} | {m(s['balance'])} | {s['requested_core_share']:.2f} | {s['core_share_used']:.2f} | "
          f"{s['requested_core_maturity_years']:.1f} | {s['core_maturity_used_years']:.1f} | {'yes' if s['cap_applied'] else 'no'} |")
    w("")
    w("### Calibration to the CMF aggregates")
    w("")
    w("| Metric | Target | Achieved | As of |")
    w("|---|---:|---:|---|")
    for t in models["fit"]["calibration_targets"]:
        w(f"| {t['metric']} | {t['target'] * 100:.2f} percent | {t['achieved'] * 100:.2f} percent | {t['as_of']} |")
    w("")
    w("### Validation tests")
    w("")
    w("| Variant | Test | Segment | Light | Statistic |")
    w("|---|---|---|---|---:|")
    for v in ids:
        for tr in variants[v]["tests"]:
            st = "n/a" if tr["statistic"] is None else f"{tr['statistic']:.4g}"
            w(f"| {v} | {tr['test_id']} | {tr['segment'] or 'n/a'} | {tr['light']} | {st} |")
    return "\n".join(lines) + "\n"


def render(variants: dict[str, dict[str, Any]], models: dict[str, Any], raw_sources: dict[str, Any]) -> dict[str, str]:
    return {"outcomes": outcomes_block(variants), "files": files_block(raw_sources), "results": results_block(variants, models)}


def write_page(page: Path, variants: dict[str, dict[str, Any]], models: dict[str, Any], raw_sources: dict[str, Any]) -> None:
    text = page.read_text(encoding="utf-8")
    for name, body in render(variants, models, raw_sources).items():
        begin, end = BLOCKS[name]
        head, rest = text.split(begin, 1)
        tail = rest.split(end, 1)[1]
        text = f"{head}{begin}\n{body}{end}{tail}"
    page.write_text(text, encoding="utf-8", newline="\n")
