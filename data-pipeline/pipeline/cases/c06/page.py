"""The result table of ``docs/cases/C06.md``, generated from the committed documents (CT-514), and the claims check.

``python data-pipeline/pipeline/cases/c06/page.py`` rewrites the block between the two markers of the case page from
``data/derived/C06``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MARK_START = "<!-- c06-results:start -->"
MARK_END = "<!-- c06-results:end -->"
PCH_START = "<!-- c06-pch:start -->"
PCH_END = "<!-- c06-pch:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|twin|missing|absent|cannot|isn't|none)\b", re.IGNORECASE)


def claim_findings(text: str) -> list[str]:
    """A line that mentions mortgages or Freddie Mac must also deny a result or say the data is absent or a twin; a page
    that never names the SBA data is a finding."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        low = line.lower()
        if ("mortgage" in low or "freddie" in low) and not NEGATION.search(line):
            out.append(f"line {n}: names mortgages or Freddie Mac without saying they are absent or a twin: {line.strip()[:80]}")
    if "sba" not in text.lower():
        out.append("the page does not name the SBA data")
    return out


def _lines(derived: Path) -> list[dict]:
    manifest = json.loads((derived / "manifests" / "C06.json").read_text(encoding="utf-8"))
    rows = []
    for a in manifest["artifacts"]:
        if a["role"] != "variant":
            continue
        d = json.loads((derived / a["path"]).read_text(encoding="utf-8"))
        o = d["outputs"]
        gca = sum(r["gross_carrying_amount"] for r in o["stage_summary"]["rows"])
        ecl = sum(r["ecl"] for r in o["stage_summary"]["rows"])
        s2 = next(r for r in o["stage_summary"]["rows"] if r["stage"] == "stage2")
        accounts = sum(r["accounts"] for r in o["stage_summary"]["rows"])
        t = {(x["test_id"], x["model_id"], x["segment"]): x for x in d["tests"]}
        ecl_bt = t.get(("ifrs9.ecl_backtest", "L1-dth", None))
        life = t.get(("ifrs9.lifetime_pd_backtest", "L1-dth", "all"))
        sicr = t.get(("ifrs9.sicr_effectiveness", "L1-dth", None))
        cmp = {r["rung_id"]: r for r in o["rung_comparison"]}
        rows.append({
            "date": o["reporting_date"], "accounts": accounts, "gca_bn": gca / 1e9, "s2": s2["gross_carrying_amount"] / gca if gca else 0.0,
            "ecl_m": ecl / 1e6, "cov": ecl / gca if gca else 0.0,
            "bt": None if ecl_bt is None or ecl_bt["metric"] is None else ecl_bt["metric"], "bt_light": ecl_bt["light"] if ecl_bt else "n/a",
            "gap": None if life is None else life["metric"], "gap_light": life["light"] if life else "n/a",
            "sicr": None if sicr is None or sicr["metric"] is None else sicr["metric"], "sicr_light": sicr["light"] if sicr else "n/a",
            "auc": cmp["L1-dth"]["c_index"], "nl": d["impact"]["nl_index"]["value"],
        })
    return rows


def _f(x, fmt):
    return "n/a" if x is None else format(x, fmt)


def results_block(derived: Path) -> str:
    head = ("| Reporting date | Accounts | Gross carrying amount (USD bn) | Stage 2 share | Model ECL (USD m) | Coverage | "
            "Realised 12-month losses over ECL | Largest lifetime PD gap (L1, points) | SICR default-rate ratio | L1 c-index | ECL non-linearity |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|")
    body = []
    for r in _lines(derived):
        body.append(f"| {r['date']} | {r['accounts']:,} | {r['gca_bn']:.1f} | {100 * r['s2']:.1f}% | {r['ecl_m']:,.0f} | {100 * r['cov']:.2f}% | "
                    f"{_f(r['bt'], '.2f')} ({r['bt_light']}) | {_f(None if r['gap'] is None else 100 * r['gap'], '.1f')} ({r['gap_light']}) | "
                    f"{_f(r['sicr'], '.2f')} ({r['sicr_light']}) | {_f(r['auc'], '.3f')} | {100 * r['nl']:.1f}% |")
    return "\n".join([head, *body]) + "\n"


def pch_rows(derived: Path) -> list[dict]:
    """The S-4 evaluation of every reporting date, from the PC-Hazard record of each models document, in date order."""
    manifest = json.loads((derived / "manifests" / "C06.json").read_text(encoding="utf-8"))
    rows = []
    for a in manifest["artifacts"]:
        if a["role"] != "models":
            continue
        d = json.loads((derived / a["path"]).read_text(encoding="utf-8"))
        rec = next(m for m in d["model"] if m["id"] == "L3-pch")
        rows.append({"date": d["fit"]["ladder"][0]["training_cutoff"], "ev": rec["details"].get("evaluation"), "boot": d["fit"]["s4_bootstrap"],
                     "sweep": d["fit"]["pch_sensitivity"]})
    return rows


def _interval(d: dict, scale: float, fmt: str) -> str:
    """One difference with its 95% interval, ``-0.00008 [-0.00012, -0.00004]``; ``n/a`` when a side is not observed, and the difference
    alone, marked, when it has no interval: a number is never invented."""
    if d["difference"] is None:
        return "n/a"
    head = format(scale * d["difference"], "+" + fmt)
    if d["lo"] is None:
        return f"{head} (no interval)"
    return f"{head} [{format(scale * d['lo'], '+' + fmt)}, {format(scale * d['hi'], '+' + fmt)}]"


def sensitivity_block(derived: Path) -> str:
    """The hyper-parameter sensitivity of the PC-Hazard rung: the S-4 numbers of every setting at every date, the verdict of each setting over the
    dates and how many agree with the default's, which stays the verdict of the case."""
    rows = pch_rows(derived)
    first = next((r["sweep"] for r in rows if r["sweep"]["evaluated"]), None)
    if first is None:
        return "No date fitted the PC-Hazard rung: the sensitivity sweep was not written.\n"
    head = ("| Setting | Reporting date | Status | c-index L3 | Integrated Brier L3 | Mean decile gap vs Aalen-Johansen L3 (points) | "
            "Lower Brier than Cox | Smaller decile gap than Cox | Hypothesis at the date |\n|---|---|---|---|---|---|---|---|---|")
    yn = {None: "n/a", True: "yes", False: "no"}
    labels = {e["setting_id"]: e["label"]["en"] for e in first["settings"]}
    body = []
    for sid, label in labels.items():
        for r in rows:
            e = next(x for x in r["sweep"]["settings"] if x["setting_id"] == sid) if r["sweep"]["evaluated"] else None
            if e is None:
                body.append(f"| {label} | {r['date']} | not written | n/a | n/a | n/a | n/a | n/a | n/a |")
                continue
            ev = e["evaluation"]
            if ev is None:
                body.append(f"| {label} | {r['date']} | {e['status']} | n/a | n/a | n/a | n/a | n/a | n/a |")
                continue
            g = ev["mean_decile_gap"]["pch"]
            holds = "not evaluable" if ev["holds_at_date"] is None else ("holds" if ev["holds_at_date"] else "does not hold")
            body.append(f"| {label} | {r['date']} | {e['status']} | {_f(ev['c_index']['pch'], '.4f')} | {_f(ev['integrated_brier']['pch'], '.5f')} | "
                        f"{_f(None if g is None else 100 * g, '.2f')} | {yn[ev['criteria']['lower_integrated_brier']]} | "
                        f"{yn[ev['criteria']['smaller_decile_gap']]} | {holds} |")
    o = first["overall"]
    verdicts = ["| Setting | Dates where the hypothesis holds | Evaluable dates | Verdict | Agrees with the default's verdict |", "|---|---|---|---|---|"]
    for s in o["settings"]:
        verdicts.append(f"| {labels[s['setting_id']]} | {s['holds_at']} | {s['evaluable']} | {s['verdict'] or 'cannot be judged'} | "
                        f"{'yes' if s['agrees'] else 'no'} |")
    word = {"holds": "HOLDS", "refuted": "IS REFUTED", None: "CANNOT BE JUDGED"}[o["case_verdict"]]
    off = [f"{labels[e['setting_id']]} at {r['date']} ({e['status']})" for r in rows if r["sweep"]["evaluated"]
           for e in r["sweep"]["settings"] if e["status"] != "fitted"]
    note = "every fit stopped early" if not off else "not stopped early or failed, with their numbers reported where they exist: " + "; ".join(off)
    tail = (f"\nThe verdict is the default's: the hypothesis {word}. The verdict of a setting agrees with it in {o['agree']} of {o['settings_count']} "
            "settings (the default counted once; a setting with no verdict does not agree). No setting was chosen on the out-of-time data: each "
            "refit trains on the same loans, hold-out split and seed as the main fit and is judged on the same out-of-time accounts, and every "
            f"grid covers {first['covers_months']} months. Status of the fits: {note}.\n")
    return "\n".join(["**Sensitivity to the hyper-parameters.** " + first["method"]["en"], "", head, *body, "", *verdicts]) + "\n" + tail


def pch_block(derived: Path) -> str:
    """The S-4 table: the PC-Hazard rung beside Cox at every date, the 95% interval of each difference from the evaluation bootstrap, and the
    verdict on the hypothesis written before the run (the intervals never change it)."""
    from pipeline.cases.c06.backtest import S4_HYPOTHESIS, s4_verdict

    head = ("| Reporting date | c-index L3 | c-index L2 | Integrated Brier L3 | Integrated Brier L2 | Mean decile gap vs Aalen-Johansen L3 (points) | "
            "Mean decile gap L2 (points) | Accounts | Defaults | Follow-up (months) | Hypothesis at the date | "
            "Integrated Brier, L3 minus L2 (95% interval) | Mean decile gap, L3 minus L2, points (95% interval) | Interval excludes zero (both measures) |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    body, holds, blocks = [], [], []
    for r in pch_rows(derived):
        ev, b = r["ev"], r["boot"]
        blocks.append(b)
        diff = {d["measure"]: d for d in b["differences"]}
        cells = f"{_interval(diff['integrated_brier'], 1.0, '.5f')} | {_interval(diff['mean_decile_gap'], 100.0, '.2f')} | " \
                f"{ {None: 'n/a', True: 'yes', False: 'no'}[b['both_exclude_zero']] } |"
        if ev is None:
            body.append(f"| {r['date']} | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not fitted | {cells}")
            holds.append(None)
            continue
        g = ev["mean_abs_decile_gap_aalen_johansen"]
        h = ev["holds_at_date"]
        holds.append(h)
        words = "not evaluable" if h is None else ("holds" if h else "does not hold")
        body.append(f"| {r['date']} | {_f(ev['c_index']['pch'], '.4f')} | {_f(ev['c_index']['cox'], '.4f')} | "
                    f"{_f(ev['integrated_brier']['pch'], '.5f')} | {_f(ev['integrated_brier']['cox'], '.5f')} | "
                    f"{_f(None if g['pch_mean'] is None else 100 * g['pch_mean'], '.2f')} | {_f(None if g['cox_mean'] is None else 100 * g['cox_mean'], '.2f')} | "
                    f"{ev['eligible_accounts']:,} | {ev['defaults_followed']:,} | {ev['follow_up_months']:.1f} | {words} | {cells}")
    v = s4_verdict(holds)
    word = {"holds": "HOLDS", "refuted": "IS REFUTED", None: "CANNOT BE JUDGED"}[v["verdict"]]
    n_excl = sum(1 for h, b in zip(holds, blocks, strict=True) if h and b["both_exclude_zero"])
    first = blocks[0]
    tail = (f"\n**Verdict.** The hypothesis {word}: it holds at {v['holds_at']} of {v['evaluable']} evaluable reporting dates "
            f"({v['dates']} dates in all).\n\n> {S4_HYPOTHESIS['en']}\n\n"
            f"**Intervals.** The 95% interval beside each difference is the 2.5 and 97.5 percentiles of {first['replicates']:,} replicates of an "
            f"evaluation bootstrap (seed {first['seed']}): the out-of-time accounts are resampled with replacement and the predictions of both rungs "
            "are held fixed (nothing is refit), so it measures the sampling noise of the comparison on this book, not the uncertainty of the fits. "
            "A negative difference favours PC-Hazard. The verdict above is the rule written before the run and the intervals do not change it: "
            f"{n_excl} of the {v['holds_at']} dates where the hypothesis holds have both intervals excluding zero.\n")
    return "\n".join([head, *body]) + "\n" + tail + "\n" + sensitivity_block(derived)


def update(page: Path, derived: Path) -> None:
    text = page.read_text(encoding="utf-8")
    pre, rest = text.split(MARK_START, 1)
    _, post = rest.split(MARK_END, 1)
    text = f"{pre}{MARK_START}\n{results_block(derived)}{MARK_END}{post}"
    pre, rest = text.split(PCH_START, 1)
    _, post = rest.split(PCH_END, 1)
    page.write_text(f"{pre}{PCH_START}\n{pch_block(derived)}{PCH_END}{post}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root / "data-pipeline"))
    update(root / "docs" / "cases" / "C06.md", root / "data" / "derived")
    print("updated", root / "docs" / "cases" / "C06.md")
