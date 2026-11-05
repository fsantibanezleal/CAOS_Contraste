"""Tables and in-text numbers of the market-risk section of the technical report (sections/11-market.tex).

Every number the section prints is produced here from the committed documents of cases C11 (``data/derived/C11``), C13
(``data/derived/C13``) and the size and power studies of C22 (``data/derived/C22``), or from the committed selection records of
C11 (``docs/design/features/c11``); nothing is typed in the LaTeX. The script writes

* ``tables/market-<name>.tex``: one booktabs ``table`` environment per result table (``figkit.table``);
* ``tables/market-numbers.tex``: one ``\\newcommand`` per number the prose quotes (``\\mk...``), so that a new release of the
  documents regenerates the text's figures with the tables.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_market.py

``--registry <file.json>`` also writes every macro with its value and the source it was read from (an audit aid).
The figure script ``figures/make_market.py`` imports ``load`` and the helpers of this module.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

OUT = HERE
ROOT = figkit.ROOT
DESIGN = ROOT / "docs" / "design" / "features" / "c11"

#: the six windows of case C11 in the order of the case page (chronological, the control window first)
WINDOWS = ("calm-2004-06", "equity-2007-09", "fx-2008", "equity-2020", "rates-2022", "mixed-2023")
WLABEL = {
    "calm-2004-06": "Calm 2004--06",
    "equity-2007-09": "Equity 2007--09",
    "fx-2008": "FX 2008--09",
    "equity-2020": "Equity 2020",
    "rates-2022": "Rates 2022",
    "mixed-2023": "Mixed 2023",
}
WSTEM = {"calm-2004-06": "Calm", "equity-2007-09": "Gfc", "fx-2008": "Fx", "equity-2020": "Covid", "rates-2022": "Rates",
         "mixed-2023": "Mixed"}
#: display names of the eighteen models of the C11 ladder
MNAME = {
    "hs-250": "Historical simulation, 250 days",
    "hs-500": "Historical simulation, 500 days",
    "awhs": "Age-weighted historical simulation",
    "dn-rolling": "Delta-normal",
    "cf-rolling": "Cornish-Fisher",
    "ewma": "EWMA",
    "garch-t": "GARCH(1,1)-t",
    "gjr-t": "GJR-GARCH-t",
    "egarch-t": "EGARCH-t",
    "fhs": "Filtered historical simulation",
    "evt-mf": "Conditional EVT",
    "caviar-sav": "CAViaR, absolute value",
    "caviar-as": "CAViaR, asymmetric slope",
    "caviar-es": "ES-CAViaR (two-step)",
    "gas-fz-1": "GAS-FZ, one factor",
    "gas-fz-2": "GAS-FZ, two factors",
    "gas-hybrid": "Hybrid GARCH-FZ",
    "nn-fz": "Quantile network (FZ0)",
}
MSHORT = {
    "hs-250": "HS 250", "hs-500": "HS 500", "awhs": "Age-weighted HS", "dn-rolling": "Delta-normal", "cf-rolling": "Cornish-Fisher",
    "ewma": "EWMA", "garch-t": "GARCH-t", "gjr-t": "GJR-t", "egarch-t": "EGARCH-t", "fhs": "Filtered HS", "evt-mf": "Cond. EVT",
    "caviar-sav": "CAViaR-SAV", "caviar-as": "CAViaR-AS", "caviar-es": "ES-CAViaR", "gas-fz-1": "GAS-FZ 1F",
    "gas-fz-2": "GAS-FZ 2F", "gas-hybrid": "Hybrid GARCH-FZ", "nn-fz": "Quantile network",
}
TEST_ORDER = ("market.kupiec_pof", "market.christoffersen_independence", "market.christoffersen_conditional_coverage",
              "market.duration_test", "market.dynamic_quantile_test", "market.acerbi_szekely")
TEST_NAME = {
    "market.kupiec_pof": "Kupiec proportion of failures",
    "market.christoffersen_independence": "Christoffersen independence",
    "market.christoffersen_conditional_coverage": "Christoffersen conditional coverage",
    "market.duration_test": "Duration test",
    "market.dynamic_quantile_test": "Dynamic quantile test",
    "market.acerbi_szekely": "Acerbi-Szekely $Z_2$",
    "market.mcneil_frey_residual_test": "McNeil-Frey residual test",
    "market.du_escanciano_unconditional": "Du-Escanciano, unconditional",
    "market.du_escanciano_conditional": "Du-Escanciano, conditional",
}
VARIANTS = ("none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment")
VLABEL = {"none": "None (size)", "missing-basis": "Missing basis", "stale-volatility": "Stale volatility",
          "wrong-correlation": "Wrong correlation", "omitted-factor": "Omitted factor", "time-misalignment": "Time misalignment"}

MACROS: dict[str, tuple[str, str]] = {}


def put(name: str, value: Any, source: str, digits: int | None = None) -> None:
    """Register the macro ``\\mk<name>`` with the text of ``value`` and the artifact it was read from."""
    if isinstance(value, float) and digits is not None:
        text = f"{value:.{digits}f}"
    elif isinstance(value, int) and not isinstance(value, bool):
        text = f"{value:,}".replace(",", "{,}") if abs(value) >= 10000 else str(value)
    else:
        text = str(value)
    MACROS[name] = (text, source)


def pct(x: float, digits: int = 1) -> str:
    return f"{100.0 * x:.{digits}f}"


def load() -> dict[str, Any]:
    """Every committed document the section reads, keyed by role."""
    d: dict[str, Any] = {"win": {w: figkit.doc(f"C11/{w}.json") for w in WINDOWS}}
    d["ladder"] = figkit.doc("C11/models-ladder.json")
    d["c13"] = {v: figkit.doc(f"C13/{v}.json") for v in VARIANTS}
    d["c13models"] = figkit.doc("C13/models-generator.json")
    d["c22null"] = figkit.doc("C22/null.json")
    d["c22other"] = figkit.doc("C22/other-families.json")
    d["hyper"] = json.loads((DESIGN / "hyperparameter-selection.json").read_text(encoding="utf-8"))
    d["nethyper"] = json.loads((DESIGN / "network-selection.json").read_text(encoding="utf-8"))
    return d


# ------------------------------------------------------------------------------------------------------------ accessors

def models(D: dict, w: str) -> dict[str, dict]:
    return {m["model_id"]: m for m in D["win"][w]["outputs"]["models"]}


def level(m: dict, alpha: float) -> dict:
    return next(b for b in m["by_level"] if abs(b["alpha"] - alpha) < 1e-12)


def test_row(D: dict, w: str, test_id: str, model_id: str, alpha: float) -> dict:
    seg = f"alpha={alpha}"
    return next(t for t in D["win"][w]["tests"] if t["test_id"] == test_id and t["model_id"] == model_id and t["segment"] == seg)


def champion(D: dict, w: str, alpha: float) -> str | None:
    return next(c for c in D["win"][w]["outputs"]["comparison"]["champions"] if abs(c["alpha"] - alpha) < 1e-12)["model_id"]


def mcs(D: dict, w: str, alpha: float) -> dict:
    return next(c for c in D["win"][w]["outputs"]["comparison"]["mcs"] if abs(c["alpha"] - alpha) < 1e-12)


def in_set(D: dict, w: str, alpha: float, mid: str) -> bool | None:
    for m in mcs(D, w, alpha)["members"]:
        if m["model_id"] == mid:
            return m["in_set"]
    return None


def fz0(D: dict, w: str, mid: str, alpha: float) -> float | None:
    return level(models(D, w)[mid], alpha)["fz0_mean"]


def n_days(D: dict, w: str) -> int:
    return D["win"][w]["outputs"]["window"]["n_forecast_days"]


#: font size and column separation of each table, so that none leaves the text width
SIZES = {"market-ladder": ("scriptsize", 2.5), "market-selection": ("footnotesize", 3.0), "market-windows": ("footnotesize", 3.0),
         "market-exceed": ("scriptsize", 2.0), "market-reds": ("scriptsize", 2.5), "market-nn": ("scriptsize", 2.0),
         "market-rough": ("footnotesize", 4.0), "market-traffic": ("footnotesize", 3.0), "market-tests": ("scriptsize", 2.5),
         "market-sizepower": ("scriptsize", 2.5), "market-pla": ("scriptsize", 2.0), "market-desk": ("scriptsize", 2.0),
         "market-truth": ("footnotesize", 3.0)}


def _table(path: pathlib.Path, header: list, rows: list, **kw: Any) -> None:
    """``figkit.table`` followed by the font size and the column separation of ``SIZES``."""
    figkit.table(path, header, rows, **kw)
    size, tc = SIZES.get(path.stem, ("footnotesize", 3.0))
    txt = path.read_text(encoding="utf-8")
    txt = txt.replace("\\small\n", f"\\{size}\n\\setlength{{\\tabcolsep}}{{{tc}pt}}\n", 1)
    path.write_text(txt, encoding="utf-8", newline="\n")


def tn(test_id: str) -> str:
    """A test name as a raw table cell (some names carry math)."""
    return "\\relax " + TEST_NAME[test_id]


def roughness(var: list[float]) -> float:
    """Mean absolute relative change of a VaR path from one day to the next."""
    return sum(abs(var[i] / var[i - 1] - 1.0) for i in range(1, len(var))) / (len(var) - 1)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson score interval of a share (well behaved at 0 and 1, where the normal interval collapses)."""
    p = k / n
    d = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def known_pearson(D: dict, did: str) -> float:
    """The population Pearson correlation of the hypothetical and the risk-theoretical P&L in closed form from the generator
    parameters of the committed models document (the closed form of ``pipeline.cases.c13.generator.known_pearson``)."""
    g = {p["name"]: p["value"] for p in D["c13models"]["fit"]["generator"]["parameters"]}
    l1, l2, rho, phi, s, res = g["loading_1"], g["loading_2"], g["factor_correlation"], g["vol_persistence"], g["vol_log_sd"], g["residual_sd_share"]
    dev = {p["name"]: p["value"] for p in D["c13"][did]["outputs"]["known_deficiency"]["parameters"]}

    def chol(r: float) -> tuple[float, float, float]:
        return 1.0, r, math.sqrt(1.0 - r * r)

    def direction(r: float) -> tuple[float, float]:
        _, c, d2 = chol(r)
        return l1 + l2 * c, l2 * d2

    a = direction(rho)
    aa = a[0] ** 2 + a[1] ** 2
    v_hpl = aa * (1.0 + res ** 2)
    base_sd = math.sqrt((l1 * l1 + l2 * l2 + 2 * rho * l1 * l2) * (1.0 + res ** 2))

    def share_scale(share: float) -> float:
        return base_sd * share / math.sqrt(1.0 - share * share)

    if did == "time-misalignment":
        return 0.0
    if did == "wrong-correlation":
        b = direction(rho + dev["correlation_error"])
        return (a[0] * b[0] + a[1] * b[1]) / math.sqrt(v_hpl * (b[0] ** 2 + b[1] ** 2))
    v_rt = aa
    cov = v_rt
    if did == "stale-volatility":
        cov = v_rt * math.exp(-s * s * (1.0 - phi ** dev["vol_lag_days"]))
    if did == "missing-basis":
        v_hpl += share_scale(dev["basis_sd_share"]) ** 2
    if did == "omitted-factor":
        v_hpl += share_scale(dev["omitted_loading_share"]) ** 2
    return cov / math.sqrt(v_hpl * v_rt)


# ------------------------------------------------------------------------------------------------------------ the tables

def t_ladder(D: dict) -> None:
    rows = []
    for m in D["ladder"]["model"]:
        p = m["parameters"]
        extra = []
        for key, lab in (("lambda", "$\\lambda$"), ("threshold_fraction", "tail share"), ("hidden_units", "hidden units"),
                         ("epochs", "epochs"), ("learning_rate", "learning rate"), ("weight_decay", "weight decay"),
                         ("n_starts", "starts")):
            if key in p:
                v = p[key]["value"]
                extra.append(f"{lab} {v:g}")
        es = m["details"]["es_method"]
        rows.append([MNAME[m["id"]], f"{p['window_days']['value']:g}", f"{p['refit_every_days']['value']:g}",
                     "; ".join(extra) if extra else "--", es[0].upper() + es[1:]])
    _table(
        OUT / "market-ladder.tex",
        ["Model", "Window (days)", "Refit (days)", "Setting", "Expected shortfall rule"],
        [[r[0], r[1], r[2], r[3], r[4]] for r in rows],
        caption=("The eighteen forecasting models of case C11 as the committed models document records them: the estimation window in "
                 "days, the number of forecast days between two refits, the hyperparameters fixed on the span 1995 to 2003 (or by "
                 "the compute limit for the network) and the rule that turns the fitted model into an expected shortfall."),
        label="tab:market-ladder", align="p{3.6cm}rrp{2.6cm}p{5.4cm}")


def t_selection(D: dict) -> None:
    rows = []
    h = D["hyper"]
    for name, g in sorted(h["grid"].items()):
        cands = ", ".join(f"{c['value']:g}: {c['score']:.2f}" for c in g["candidates"])
        rows.append([f"\\texttt{{{name.replace('_', chr(92) + '_')}}}", MSHORT[g["model"]], cands,
                     f"{h['selected'][name]:g}"])
    n = D["nethyper"]
    for name, g in sorted(n["grid"].items()):
        cands = ", ".join(f"{c['value']:g}: {c['score']:.2f}" for c in g["candidates"])
        rows.append([f"\\texttt{{{name.replace('_', chr(92) + '_')}}}", MSHORT[g["model"]], cands,
                     f"{n['selected'][name]:g}"])
    _table(
        OUT / "market-selection.tex",
        ["Hyperparameter", "Model scored", "Candidate: summed average FZ0 (lower is better)", "Selected"],
        rows,
        caption=("The hyperparameters fixed once on 1995 to 2003, before the earliest test window: for each candidate value the sum "
                 "of the average FZ0 loss of the model that uses it over the two selection series and the two tail levels, on every "
                 "fifth forecast day of the span, and the value chosen. The last two rows are the quantile network."),
        label="tab:market-selection", align="llp{6.0cm}r")


def t_windows(D: dict) -> None:
    rows = []
    for w in WINDOWS:
        o = D["win"][w]["outputs"]
        elig = sum(m["eligible"] for m in o["models"])
        c1, c2 = champion(D, w, 0.01), champion(D, w, 0.025)

        def cell(c: str | None, a: float) -> str:
            return "none" if c is None else f"{MSHORT[c]} ({fz0(D, w, c, a):.3f})"

        rows.append([WLABEL[w], o["window"]["asset_class"], n_days(D, w), f"{elig}", cell(c1, 0.01),
                     cell(c2, 0.025), f"{mcs(D, w, 0.01)['n_in_set']}", f"{mcs(D, w, 0.025)['n_in_set']}"])
    _table(
        OUT / "market-windows.tex",
        ["Window", "Book", "Days", "Eligible", "Champion at 1\\%", "Champion at 2.5\\%", "In set 1\\%", "In set 2.5\\%"],
        rows,
        caption=("Case C11, one row per window: the book, the number of forecast days, the number of the eighteen models that pass the "
                 "coverage, conditional coverage and expected shortfall tests at both tail levels, the champion at each level with its "
                 "average FZ0 loss, and the size of the 90 percent model confidence set at each level."),
        label="tab:market-windows", align="llrrp{3.2cm}p{3.2cm}rr")


def t_exceed(D: dict) -> None:
    rows = []
    exp = ["Expected"] + [f"{level(models(D, w)['hs-250'], 0.01)['expected_exceedances']:.1f}" for w in WINDOWS]
    for mid in MNAME:
        r = [MSHORT[mid]]
        for w in WINDOWS:
            b = level(models(D, w)[mid], 0.01)
            red = test_row(D, w, "market.kupiec_pof", mid, 0.01)["light"] == "red"
            r.append("\\relax " + f"{b['n_exceedances']}" + ("$^{\\dagger}$" if red else ""))
        rows.append(r)
    _table(
        OUT / "market-exceed.tex",
        ["Model"] + [WLABEL[w] for w in WINDOWS],
        [exp] + rows,
        caption=("Exceedances of the 99 percent value at risk of each model in each window of case C11, with the number expected under "
                 "correct coverage in the first row; a dagger marks a model whose Kupiec test is red at the 5 percent level in that "
                 "window. The daily forecasts are strictly out of sample."),
        label="tab:market-exceed", align="lrrrrrr")


def red_table(D: dict) -> tuple[list[list[str]], dict[str, dict[str, tuple[int, int]]]]:
    cnt: dict[str, dict[str, tuple[int, int]]] = {}
    rows = []
    for t in TEST_ORDER:
        r = [tn(t)]
        cnt[t] = {}
        for w in WINDOWS:
            tr = [x for x in D["win"][w]["tests"] if x["test_id"] == t]
            ev = [x for x in tr if x["light"] != "not_evaluated"]
            red = sum(1 for x in ev if x["light"] == "red")
            cnt[t][w] = (red, len(ev))
            r.append(f"{red}/{len(ev)}")
        rows.append(r)
    return rows, cnt


def t_reds(D: dict) -> None:
    rows, _ = red_table(D)
    _table(
        OUT / "market-reds.tex",
        ["Test"] + [WLABEL[w] for w in WINDOWS],
        rows,
        caption=("Number of red lights of each back-test over the model and tail-level pairs that the test could evaluate (at most thirty-six "
                 "pairs: eighteen models at two levels), per window of case C11. A test is not evaluated when its statistic is undefined, "
                 "for example with no exceedance or no expected shortfall forecast."),
        label="tab:market-reds", align="lrrrrrr")


def t_nn(D: dict) -> None:
    rows = []
    for w in WINDOWS:
        m = models(D, w)["nn-fz"]
        b1, b2 = level(m, 0.01), level(m, 0.025)
        kp = test_row(D, w, "market.kupiec_pof", "nn-fz", 0.01)["p_value"]
        c1, c2 = champion(D, w, 0.01), champion(D, w, 0.025)

        def best(c: str | None, a: float) -> str:
            return "--" if c is None else f"{fz0(D, w, c, a):.3f}"

        rows.append([WLABEL[w], "yes" if m["eligible"] else "no", f"{b1['n_exceedances']} ({b1['expected_exceedances']:.1f})",
                     "$<0.001$" if kp < 0.0005 else f"{kp:.3f}",
                     f"{b1['fz0_mean']:.3f}", best(c1, 0.01), "yes" if in_set(D, w, 0.01, "nn-fz") else "no",
                     f"{b2['fz0_mean']:.3f}", best(c2, 0.025), "yes" if in_set(D, w, 0.025, "nn-fz") else "no"])
    _table(
        OUT / "market-nn.tex",
        ["Window", "Eligible", "Exc. 1\\% (exp.)", "Kupiec $p$", "FZ0 1\\%", "Best 1\\%", "Set 1\\%", "FZ0 2.5\\%", "Best 2.5\\%", "Set 2.5\\%"],
        rows,
        caption=("The quantile network trained on the FZ0 loss against the ladder in each window of case C11: eligibility, exceedances of its "
                 "99 percent value at risk with the expected number, the Kupiec p-value, its average FZ0 loss, the champion's average FZ0 "
                 "loss at each level and whether the network belongs to the 90 percent model confidence set."),
        label="tab:market-nn", align="lcrrrrcrrc")


def t_rough(D: dict) -> None:
    ids = ("nn-fz", "gjr-t", "ewma", "hs-250")
    rows = []
    for w in WINDOWS:
        r = [WLABEL[w]]
        for mid in ids:
            r.append(f"{roughness(level(models(D, w)[mid], 0.01)['var']):.3f}")
        rows.append(r)
    _table(
        OUT / "market-rough.tex",
        ["Window"] + [MSHORT[i] for i in ids],
        rows,
        caption=("Mean absolute relative change from one day to the next of the 99 percent value at risk forecast by the quantile network and "
                 "by three reference models, in each window of case C11; a larger value is a more volatile forecast path."),
        label="tab:market-rough", align="lrrrr")


def t_traffic(D: dict) -> None:
    rows = []
    for r in D["ladder"]["fit"]["traffic_light"]["rows"]:
        rows.append([f"{r['exceptions']}", r["zone"], f"{r['frtb_multiplier']:.2f}", f"{r['us_multiplier']:.2f}",
                     f"{r['cumulative_probability_pct']:.2f}"])
    _table(
        OUT / "market-traffic.tex",
        ["Exceptions in 250 days", "Zone", "FRTB multiplier", "US multiplication factor", "Cumulative probability (\\%)"],
        rows,
        caption=("The traffic-light table of the 99 percent value-at-risk back-test over 250 observations as the committed models document "
                 "records it: the zone, the backtesting-dependent multiplier of the Basel framework, the multiplication factor of the "
                 "United States rule and the cumulative binomial probability of the exception count at true coverage."),
        label="tab:market-traffic", align="rlrrr")


def t_tests(D: dict) -> None:
    seen = {}
    for t in D["win"]["equity-2007-09"]["tests"]:
        seen.setdefault(t["test_id"], t)
    rows = []
    for tid in TEST_ORDER:
        t = seen[tid]
        rows.append([tn(tid), t["h0"][0].upper() + t["h0"][1:], t["alternative"],
                     f"{t['alpha_amber']:g}", f"{t['alpha_red']:g}"])
    _table(
        OUT / "market-tests.tex",
        ["Test", "Null hypothesis", "Alternative", "Amber below", "Red below"],
        rows,
        caption=("The six tests the case C11 battery runs on every model at every tail level, with the null hypothesis and the alternative "
                 "as the committed test records state them and the p-value below which the light turns amber and red; the lights are "
                 "internal screening levels of the validation, not regulatory thresholds."),
        label="tab:market-tests", align="p{2.9cm}p{4.4cm}p{4.4cm}rr")


def t_sizepower(D: dict) -> list[dict]:
    out = []
    sims = D["c22other"]["outputs"]["simulations"]
    for s in sims:
        if not s["test_id"].startswith("market."):
            continue
        arm = s["study"]["arm"]
        key = s["rates"][s["study"]["rule_label"]]
        if arm == "null":
            last = (s, key)
        else:
            nl = last
            lab, sc = s["study"]["label"]["en"], s["scenario"]["en"]
            out.append({"test": s["test_id"], "scenario": sc if sc.startswith(lab) else f"{lab}; {sc}", "rule": s["study"]["rule_label"],
                        "size": nl[1], "power": key, "n": s["n_rep"]})
    rows = []
    for r in out:
        sc = r["scenario"].split(";")[0] if ";" in r["scenario"] else r["scenario"]
        nm = tn(r["test"])
        rows.append([nm, r["scenario"], f"{100 * r['size']['rate']:.1f} [{100 * r['size']['wilson_low']:.1f}, {100 * r['size']['wilson_high']:.1f}]",
                     f"{100 * r['power']['rate']:.1f} [{100 * r['power']['wilson_low']:.1f}, {100 * r['power']['wilson_high']:.1f}]"])
    _table(
        OUT / "market-sizepower.tex",
        ["Test", "Sample, level and alternative", "Size (\\%)", "Power (\\%)"],
        rows,
        caption=("Size and power of the nine back-tests measured by the validator of case C22: the rejection rate at the 5 percent level "
                 "when the null holds at its boundary and against one stated alternative, over two thousand repetitions each, with the "
                 "Wilson 95 percent interval in brackets; the size of a test that rejects at its red or Monte Carlo level is read at that level."),
        label="tab:market-sizepower", align="p{2.9cm}p{6.6cm}rr")
    return out


def t_pla(D: dict) -> None:
    rows = []
    for v in VARIANTS:
        o = D["c13"][v]["outputs"]
        z = o["pla"]["zones"]["overall"]
        det = o["detection"]
        n = det["n_replications"]
        sp, ks = o["pla"]["spearman"], o["pla"]["ks"]
        rows.append([VLABEL[v], f"{sp['mean']:.3f} ({sp['sd']:.3f})", f"{ks['mean']:.3f} ({ks['sd']:.3f})", f"{z['green']}", f"{z['amber']}",
                     f"{z['red']}", f"{100 * det['share_amber_or_red']:.1f} [{100 * det['ci_low']:.1f}, {100 * det['ci_high']:.1f}]"])
    _table(
        OUT / "market-pla.tex",
        ["Variant", "Spearman, mean (sd)", "KS, mean (sd)", "Green", "Amber", "Red", "Amber or red (\\%)"],
        rows,
        caption=("Case C13, the P\\&L attribution test on 1,000 replications of each variant: the mean and standard deviation of the Spearman "
                 "correlation and of the Kolmogorov-Smirnov distance, the number of replications in each joint zone, and the share that "
                 "is amber or red with its Wilson 95 percent interval in brackets."),
        label="tab:market-pla", align="lrrrrrr")


def t_desk(D: dict) -> None:
    rows = []
    for v in VARIANTS:
        o = D["c13"][v]["outputs"]
        det = o["detection"]["by_test"]
        n = o["detection"]["n_replications"]
        d99 = next(r for r in o["desk_backtest"] if abs(r["alpha"] - 0.01) < 1e-12)
        d975 = next(r for r in o["desk_backtest"] if abs(r["alpha"] - 0.025) < 1e-12)
        rows.append([VLABEL[v], f"{d99['exceptions']['mean']:.1f} ({d99['exceptions']['sd']:.1f})", f"{100 * d99['share_over_limit']:.1f}",
                     f"{d975['exceptions']['mean']:.1f} ({d975['exceptions']['sd']:.1f})", f"{100 * d975['share_over_limit']:.1f}",
                     f"{det['spearman_flagged']}", f"{det['ks_flagged']}", f"{det['desk_backtest_flagged']}"])
    _table(
        OUT / "market-desk.tex",
        ["Variant", "Exc. 99\\%", "Over 99\\%", "Exc. 97.5\\%", "Over 97.5\\%", "Spearman", "KS", "Desk"],
        rows,
        caption=("Case C13, the desk back-test on 1,000 replications of each variant: the exceptions of the hypothetical P\\&L against the "
                 "risk model's value at risk at the 99 and 97.5 percent levels (mean and standard deviation), the percentage of replications over the "
                 "limit of the framework at each level, and the number of replications flagged by the Spearman statistic, by the "
                 "Kolmogorov-Smirnov statistic and by the desk back-test at either level."),
        label="tab:market-desk", align="lrrrrrrr")


def t_truth(D: dict) -> None:
    rows = []
    for v in VARIANTS:
        o = D["c13"][v]["outputs"]
        k = o["known_deficiency"]
        par = ", ".join(f"{p['name'].replace('_', ' ')} {p['value']:g}" for p in k["parameters"]) or "--"
        rows.append([VLABEL[v], par, k["intended_to_fail"], f"{known_pearson(D, v):.3f}",
                     f"{D['c13'][v]['outputs']['pla']['spearman']['mean']:.3f}"])
    _table(
        OUT / "market-truth.tex",
        ["Variant", "Planted parameter", "Statistic meant to fail", "Population Pearson", "Mean Spearman"],
        rows,
        caption=("The six variants of the desk generator of case C13: the planted parameter, the statistic the deficiency is meant to break, "
                 "the population Pearson correlation of the two P\\&L series in closed form from the generator parameters, and the mean "
                 "Spearman correlation measured over 1,000 replications."),
        label="tab:market-truth", align="lp{4.0cm}lrr")


# ------------------------------------------------------------------------------------------------------------ the numbers

def numbers(D: dict) -> None:
    lad = D["ladder"]
    src_l = "data/derived/C11/models-ladder.json"
    n_models = len(lad["model"])
    put("NModels", n_models, src_l)
    put("NLadder", n_models - 1, src_l)
    put("NWindows", len(WINDOWS), src_l)
    tot = sum(n_days(D, w) for w in WINDOWS)
    put("TotalDays", tot, "data/derived/C11/<window>.json outputs.window.n_forecast_days (sum)")
    for w in WINDOWS:
        s = WSTEM[w]
        o = D["win"][w]["outputs"]
        put(f"Days{s}", n_days(D, w), f"data/derived/C11/{w}.json outputs.window.n_forecast_days")
        put(f"Start{s}", o["window"]["start_date"], f"data/derived/C11/{w}.json outputs.window.start_date")
        put(f"End{s}", o["window"]["end_date"], f"data/derived/C11/{w}.json outputs.window.end_date")
        elig = sum(m["eligible"] for m in o["models"])
        put(f"Elig{s}", elig, f"data/derived/C11/{w}.json outputs.models[].eligible")
        put(f"MissDays{s}", o["data_status"]["missing_days"]["count"], f"data/derived/C11/{w}.json outputs.data_status.missing_days.count")
        for a, tag in ((0.01, "A"), (0.025, "B")):
            c = champion(D, w, a)
            put(f"Champ{tag}{s}", MSHORT[c] if c else "none", f"data/derived/C11/{w}.json outputs.comparison.champions")
            if c:
                put(f"ChampFz{tag}{s}", fz0(D, w, c, a), f"data/derived/C11/{w}.json outputs.models[].by_level[].fz0_mean", 3)
            put(f"Mcs{tag}{s}", mcs(D, w, a)["n_in_set"], f"data/derived/C11/{w}.json outputs.comparison.mcs[].n_in_set")
            put(f"McsN{tag}{s}", len(mcs(D, w, a)["members"]), f"data/derived/C11/{w}.json outputs.comparison.mcs[].members")
        # expected exceedances
        put(f"Exp{s}", level(models(D, w)["hs-250"], 0.01)["expected_exceedances"], f"data/derived/C11/{w}.json by_level.expected_exceedances", 2)
        put(f"ExpB{s}", level(models(D, w)["hs-250"], 0.025)["expected_exceedances"], f"data/derived/C11/{w}.json by_level.expected_exceedances", 2)
        # model exceedance counts used in the text
        for mid, stem in (("hs-250", "Hs"), ("dn-rolling", "Dn"), ("gjr-t", "Gjr"), ("ewma", "Ewma"), ("nn-fz", "Nn"), ("fhs", "Fhs"),
                          ("gas-fz-2", "Gas"), ("evt-mf", "Evt")):
            put(f"Exc{stem}{s}", level(models(D, w)[mid], 0.01)["n_exceedances"], f"data/derived/C11/{w}.json outputs.models[{mid}].by_level[0].n_exceedances")
            put(f"ExcB{stem}{s}", level(models(D, w)[mid], 0.025)["n_exceedances"], f"data/derived/C11/{w}.json outputs.models[{mid}].by_level[1].n_exceedances")
        # reds
        _, cnt = red_table(D)
        for tid, short in (("market.kupiec_pof", "Kup"), ("market.christoffersen_independence", "Ind"),
                           ("market.christoffersen_conditional_coverage", "Cc"), ("market.duration_test", "Dur"),
                           ("market.dynamic_quantile_test", "Dq"), ("market.acerbi_szekely", "Az")):
            put(f"Red{short}{s}", cnt[tid][w][0], f"data/derived/C11/{w}.json tests[test_id={tid}].light")
            put(f"Ev{short}{s}", cnt[tid][w][1], f"data/derived/C11/{w}.json tests[test_id={tid}].light != not_evaluated")
        # network
        m = models(D, w)["nn-fz"]
        b1, b2 = level(m, 0.01), level(m, 0.025)
        put(f"NnExc{s}", b1["n_exceedances"], f"data/derived/C11/{w}.json nn-fz by_level[0].n_exceedances")
        put(f"NnExcB{s}", b2["n_exceedances"], f"data/derived/C11/{w}.json nn-fz by_level[1].n_exceedances")
        put(f"NnFzA{s}", b1["fz0_mean"], f"data/derived/C11/{w}.json nn-fz by_level[0].fz0_mean", 3)
        put(f"NnFzB{s}", b2["fz0_mean"], f"data/derived/C11/{w}.json nn-fz by_level[1].fz0_mean", 3)
        kp = test_row(D, w, "market.kupiec_pof", "nn-fz", 0.01)["p_value"]
        put(f"NnKup{s}", "$<0.001$" if kp < 0.0005 else f"{kp:.3f}", f"data/derived/C11/{w}.json kupiec p-value nn-fz 1%")
        put(f"NnElig{s}", "yes" if m["eligible"] else "no", f"data/derived/C11/{w}.json nn-fz eligible")
        put(f"NnRoughA{s}", roughness(b1["var"]), f"data/derived/C11/{w}.json nn-fz by_level[0].var (script)", 3)
        put(f"GjrRoughA{s}", roughness(level(models(D, w)["gjr-t"], 0.01)["var"]), f"data/derived/C11/{w}.json gjr-t by_level[0].var (script)", 3)
        put(f"HsRoughA{s}", roughness(level(models(D, w)["hs-250"], 0.01)["var"]), f"data/derived/C11/{w}.json hs-250 by_level[0].var (script)", 3)
    # network aggregates
    el = sum(1 for w in WINDOWS if models(D, w)["nn-fz"]["eligible"])
    champ_a = sum(1 for w in WINDOWS if champion(D, w, 0.01) == "nn-fz")
    champ_b = sum(1 for w in WINDOWS if champion(D, w, 0.025) == "nn-fz")
    set_a = sum(1 for w in WINDOWS if in_set(D, w, 0.01, "nn-fz"))
    set_b = sum(1 for w in WINDOWS if in_set(D, w, 0.025, "nn-fz"))
    put("NnEligWindows", el, "data/derived/C11/<window>.json nn-fz eligible")
    put("NnChampA", champ_a, "data/derived/C11/<window>.json comparison.champions")
    put("NnChampB", champ_b, "data/derived/C11/<window>.json comparison.champions")
    put("NnSetA", set_a, "data/derived/C11/<window>.json comparison.mcs members")
    put("NnSetB", set_b, "data/derived/C11/<window>.json comparison.mcs members")
    # network rank by FZ0 among all models with ES every day at 1%, per window
    ranks = []
    for w in WINDOWS:
        fz = {mid: fz0(D, w, mid, 0.01) for mid in MNAME if level(models(D, w)[mid], 0.01)["es_status"] == "forecast"}
        order = sorted(fz, key=lambda k: fz[k])
        ranks.append(order.index("nn-fz") + 1)
        put(f"NnRank{WSTEM[w]}", order.index("nn-fz") + 1, f"data/derived/C11/{w}.json by_level[0].fz0_mean (rank among models with an ES)")
        put(f"NRank{WSTEM[w]}", len(order), f"data/derived/C11/{w}.json by_level[0].es_status == forecast")
    # network parameters
    nm = next(m for m in D["ladder"]["model"] if m["id"] == "nn-fz")["parameters"]
    for key, nme in (("hidden_units", "Hidden"), ("epochs", "Epochs"), ("learning_rate", "Lr"), ("weight_decay", "Wd"), ("n_starts", "Starts"),
                     ("window_days", "Win"), ("refit_every_days", "Refit")):
        v = nm[key]["value"]
        put(f"Nn{nme}", f"{v:g}", f"{src_l} model[nn-fz].parameters.{key}")
    h_units = int(nm["hidden_units"]["value"])
    n_in = 11   # 2 * LAGS + 1 inputs: data-pipeline/pipeline/cases/c11/quantile_net.py:32 and :37
    first_row = 60   # quantile_net.py:34
    n_train = int(nm["window_days"]["value"]) - first_row
    put("NnParams", (n_in + 1) * h_units + 2 * h_units + 2, "quantile_net.py:37 (inputs) with models-ladder hidden_units: (11+1)H + 2H + 2")
    put("NnTrainRows", n_train, "models-ladder window_days minus FIRST_ROW (quantile_net.py:34)")
    put("NnTailA", n_train * 0.01, "NnTrainRows times 0.01 (script)", 1)
    put("NnTailB", n_train * 0.025, "NnTrainRows times 0.025 (script)", 1)
    put("NnCost", int(nm["epochs"]["value"]) * int(nm["n_starts"]["value"]) * n_train, "epochs x starts x training rows (script)")
    nfit = next(r for r in lad["fit"]["ladder"] if r["model_id"] == "nn-fz")["window_fits"]
    put("NnRefits", sum(f["n_refits"] for f in nfit), f"{src_l} fit.ladder[nn-fz].window_fits[].n_refits (both levels)")
    put("NnFailures", sum(f["n_convergence_failures"] for f in nfit), f"{src_l} fit.ladder[nn-fz].window_fits[].n_convergence_failures")
    # selection records
    for name, g in D["hyper"]["grid"].items():
        put("Sel" + "".join(p.capitalize() for p in name.split("_")), f"{D['hyper']['selected'][name]:g}", "docs/design/features/c11/hyperparameter-selection.json selected")
    for name, g in D["nethyper"]["grid"].items():
        put("SelNn" + "".join(p.capitalize() for p in name.split("_")), f"{D['nethyper']['selected'][name]:g}", "docs/design/features/c11/network-selection.json selected")
    put("SpanStart", D["hyper"]["span"][0], "docs/design/features/c11/hyperparameter-selection.json span")
    put("SpanEnd", D["hyper"]["span"][1], "docs/design/features/c11/hyperparameter-selection.json span")
    put("SpanStride", D["hyper"]["stride"], "docs/design/features/c11/hyperparameter-selection.json stride")
    # other hyperparameters
    hp = D["win"]["equity-2007-09"]["outputs"]["hyperparameters"]
    put("EwmaLam", f"{hp['ewma_lambda']:g}", "data/derived/C11/equity-2007-09.json outputs.hyperparameters.ewma_lambda")
    put("AwLam", f"{hp['age_weight_lambda']:g}", "data/derived/C11/equity-2007-09.json outputs.hyperparameters.age_weight_lambda")
    put("EvtFrac", f"{hp['evt_threshold_fraction']:g}", "data/derived/C11/equity-2007-09.json outputs.hyperparameters.evt_threshold_fraction")
    put("EstWin", hp["estimation_window_days"], "data/derived/C11/equity-2007-09.json outputs.hyperparameters.estimation_window_days")
    put("CaviarStarts", hp["caviar_n_starts"], "data/derived/C11/equity-2007-09.json outputs.hyperparameters.caviar_n_starts")
    put("GasStarts", hp["gas_n_starts"], "data/derived/C11/equity-2007-09.json outputs.hyperparameters.gas_n_starts")
    put("Seed", hp["seed"], "data/derived/C11/equity-2007-09.json outputs.hyperparameters.seed")
    oth = {x["name"]: x["value"] for x in hp["others"]}
    for key, nme in (("caviar_refit_every_days", "CaviarRefit"), ("gas_refit_every_days", "GasRefit"), ("hs_short_window", "HsShort"),
                     ("hs_long_window", "HsLong"), ("z2_draws", "ZDraws"), ("mc_draws", "McDraws")):
        put(nme, oth[key], f"data/derived/C11/equity-2007-09.json outputs.hyperparameters.others[{key}]")
    sc = lad["fit"]["scoring"]
    put("McsConf", f"{100 * sc['mcs_confidence']:g}", f"{src_l} fit.scoring.mcs_confidence")
    cmp0 = D["win"]["rates-2022"]["outputs"]["comparison"]
    put("McsBoot", cmp0["mcs"][0]["n_bootstrap"], "data/derived/C11/rates-2022.json outputs.comparison.mcs[0].n_bootstrap")
    put("McsBlock", cmp0["mcs"][0]["block_length"], "data/derived/C11/rates-2022.json outputs.comparison.mcs[0].block_length")
    put("Signif", f"{100 * cmp0['significance']:g}", "data/derived/C11/rates-2022.json outputs.comparison.significance")
    put("HacLags", cmp0["hac_lags"], "data/derived/C11/rates-2022.json outputs.comparison.hac_lags")
    ref = lad["fit"]["es_reference"]
    put("ZRefYellow", f"{-ref['yellow']:.2f}", f"{src_l} fit.es_reference.yellow")
    put("ZRefRed", f"{-ref['red']:.1f}", f"{src_l} fit.es_reference.red")
    put("ZRefN", ref["n_days"], f"{src_l} fit.es_reference.n_days")
    put("ZRefAlpha", f"{100 * ref['alpha']:g}", f"{src_l} fit.es_reference.alpha")
    t0 = D["win"]["equity-2007-09"]["tests"][0]
    put("AmberAlpha", f"{t0['alpha_amber']:g}", "data/derived/C11/equity-2007-09.json tests[0].alpha_amber")
    put("RedAlpha", f"{t0['alpha_red']:g}", "data/derived/C11/equity-2007-09.json tests[0].alpha_red")
    az = next(t for t in D["win"]["equity-2007-09"]["tests"] if t["test_id"] == "market.acerbi_szekely" and t["light"] != "not_evaluated")
    put("AzAmber", f"{az['alpha_amber']:g}", "data/derived/C11/equity-2007-09.json acerbi_szekely alpha_amber")
    put("AzRed", f"{az['alpha_red']:g}", "data/derived/C11/equity-2007-09.json acerbi_szekely alpha_red")
    put("GfcKupStat", test_row(D, "equity-2007-09", "market.kupiec_pof", "hs-250", 0.01)["statistic"], "data/derived/C11/equity-2007-09.json kupiec hs-250 1% statistic", 2)
    put("GfcKupP", test_row(D, "equity-2007-09", "market.kupiec_pof", "hs-250", 0.01)["p_value"], "data/derived/C11/equity-2007-09.json kupiec hs-250 1% p", 8)
    # traffic light of 1% hs-250 in the crisis
    tl = level(models(D, "equity-2007-09")["hs-250"], 0.01)["traffic_light"]
    put("TlGreen", tl["days_green"], "data/derived/C11/equity-2007-09.json hs-250 traffic_light.days_green")
    put("TlAmber", tl["days_amber"], "data/derived/C11/equity-2007-09.json hs-250 traffic_light.days_amber")
    put("TlRed", tl["days_red"], "data/derived/C11/equity-2007-09.json hs-250 traffic_light.days_red")
    put("TlN", tl["n_windows"], "data/derived/C11/equity-2007-09.json hs-250 traffic_light.n_windows")
    put("TlMax", tl["max_rolling_exceedances"], "data/derived/C11/equity-2007-09.json hs-250 traffic_light.max_rolling_exceedances")
    # evaluated traffic lights per model in the gfc window: how many models end in red
    n_red_tl = sum(1 for m in models(D, "equity-2007-09").values() if level(m, 0.01)["traffic_light"]["final_zone"] == "red")
    put("TlFinalRed", n_red_tl, "data/derived/C11/equity-2007-09.json by_level[0].traffic_light.final_zone")
    # window of the traffic light with fewer than 250 days
    put("TlReason", "fewer than 250 forecast days", "data/derived/C11/rates-2022.json traffic_light.reason")
    # the traffic table
    rows = lad["fit"]["traffic_light"]["rows"]
    words = {4: "Four", 5: "Five", 9: "Nine", 10: "Ten"}
    for r in rows:
        if r["exceptions"] in words:
            w_ = words[r["exceptions"]]
            put(f"Tl{w_}Cum", f"{r['cumulative_probability_pct']:.2f}", f"{src_l} fit.traffic_light.rows")
            put(f"Tl{w_}Mult", f"{r['frtb_multiplier']:.2f}", f"{src_l} fit.traffic_light.rows")
            put(f"Tl{w_}Us", f"{r['us_multiplier']:.2f}", f"{src_l} fit.traffic_light.rows")
    # C13
    put("CRep", D["c13"]["none"]["outputs"]["generator"]["n_replications"], "data/derived/C13/none.json outputs.generator.n_replications")
    put("CWin", D["c13"]["none"]["outputs"]["generator"]["window_days"], "data/derived/C13/none.json outputs.generator.window_days")
    g = {p["name"]: p["value"] for p in D["c13models"]["fit"]["generator"]["parameters"]}
    for key, nme in (("loading_1", "LoadA"), ("loading_2", "LoadB"), ("factor_correlation", "Rho"), ("vol_persistence", "Phi"),
                     ("vol_log_sd", "VolSd"), ("residual_sd_share", "ResShare"), ("burn_days", "Burn")):
        put("G" + nme, f"{g[key]:g}", f"data/derived/C13/models-generator.json fit.generator.parameters[{key}]")
    for v in VARIANTS:
        st = "".join(p.capitalize() for p in v.split("-"))
        o = D["c13"][v]["outputs"]
        z = o["pla"]["zones"]
        det = o["detection"]
        n = det["n_replications"]
        sp, ks = o["pla"]["spearman"], o["pla"]["ks"]
        put(f"Sp{st}", sp["mean"], f"data/derived/C13/{v}.json outputs.pla.spearman.mean", 3)
        put(f"SpSd{st}", sp["sd"], f"data/derived/C13/{v}.json outputs.pla.spearman.sd", 3)
        put(f"Ks{st}", ks["mean"], f"data/derived/C13/{v}.json outputs.pla.ks.mean", 3)
        put(f"KsSd{st}", ks["sd"], f"data/derived/C13/{v}.json outputs.pla.ks.sd", 3)
        put(f"Amb{st}", pct(det["share_amber_or_red"]), f"data/derived/C13/{v}.json outputs.detection.share_amber_or_red (percent)")
        put(f"AmbLo{st}", pct(det["ci_low"]), f"data/derived/C13/{v}.json outputs.detection.ci_low (percent)")
        put(f"AmbHi{st}", pct(det["ci_high"]), f"data/derived/C13/{v}.json outputs.detection.ci_high (percent)")
        put(f"Red{st}", pct(det["share_red"]), f"data/derived/C13/{v}.json outputs.detection.share_red (percent)")
        put(f"NRed{st}", z["overall"]["red"], f"data/derived/C13/{v}.json outputs.pla.zones.overall.red")
        put(f"NGreen{st}", z["overall"]["green"], f"data/derived/C13/{v}.json outputs.pla.zones.overall.green")
        put(f"SpFlag{st}", pct(det["by_test"]["spearman_flagged"] / n), f"data/derived/C13/{v}.json outputs.detection.by_test.spearman_flagged / n (percent)")
        put(f"KsFlag{st}", pct(det["by_test"]["ks_flagged"] / n), f"data/derived/C13/{v}.json outputs.detection.by_test.ks_flagged / n (percent)")
        put(f"DeskFlag{st}", pct(det["by_test"]["desk_backtest_flagged"] / n), f"data/derived/C13/{v}.json outputs.detection.by_test.desk_backtest_flagged / n (percent)")
        d99 = next(r for r in o["desk_backtest"] if abs(r["alpha"] - 0.01) < 1e-12)
        d975 = next(r for r in o["desk_backtest"] if abs(r["alpha"] - 0.025) < 1e-12)
        put(f"OverNN{st}", pct(d99["share_over_limit"]), f"data/derived/C13/{v}.json outputs.desk_backtest[0.01].share_over_limit (percent)")
        put(f"OverNF{st}", pct(d975["share_over_limit"]), f"data/derived/C13/{v}.json outputs.desk_backtest[0.025].share_over_limit (percent)")
        put(f"DeskExcNN{st}", d99["exceptions"]["mean"], f"data/derived/C13/{v}.json outputs.desk_backtest[0.01].exceptions.mean", 1)
        put(f"DeskExcNF{st}", d975["exceptions"]["mean"], f"data/derived/C13/{v}.json outputs.desk_backtest[0.025].exceptions.mean", 1)
        put(f"Pearson{st}", known_pearson(D, v), f"data/derived/C13/models-generator.json (closed form, script)", 3)
    put("DeskLimitNN", D["c13"]["none"]["outputs"]["desk_backtest"][1]["limit_exceptions"], "data/derived/C13/none.json outputs.desk_backtest[0.01].limit_exceptions")
    put("DeskLimitNF", D["c13"]["none"]["outputs"]["desk_backtest"][0]["limit_exceptions"], "data/derived/C13/none.json outputs.desk_backtest[0.025].limit_exceptions")
    thr = D["c13"]["none"]["outputs"]["pla"]["thresholds"]
    for key, nme in (("spearman_green", "SpGreen"), ("spearman_red", "SpRed"), ("ks_green", "KsGreen"), ("ks_red", "KsRed")):
        put("Thr" + nme, f"{thr[key]:g}", f"data/derived/C13/none.json outputs.pla.thresholds.{key}")
    extra_numbers(D)


def extra_numbers(D: dict) -> None:
    """Numbers the reading of the results quotes: the acceptance band of the exceedance count, the best model of each window, the gaps
    of the delta-normal model, the spread of the path roughness and the size and power ranges of the C22 studies."""
    from scipy.stats import binom

    for w in WINDOWS:
        n = n_days(D, w)
        hi = int(binom.ppf(0.975, n, 0.01))
        lo = int(binom.ppf(0.025, n, 0.01))
        put(f"BandHi{WSTEM[w]}", hi, f"scipy.stats.binom.ppf(0.975, {n}, 0.01) (script)")
        put(f"BandLo{WSTEM[w]}", lo, f"scipy.stats.binom.ppf(0.025, {n}, 0.01) (script)")
        above = sum(1 for mid in MNAME if level(models(D, w)[mid], 0.01)["n_exceedances"] > hi)
        put(f"Above{WSTEM[w]}", above, f"data/derived/C11/{w}.json by_level[0].n_exceedances above the band (script)")
        for a, tag in ((0.01, "A"), (0.025, "B")):
            vals = {mid: fz0(D, w, mid, a) for mid in MNAME if level(models(D, w)[mid], a)["es_status"] == "forecast"}
            best = min(vals, key=lambda k: vals[k])
            put(f"BestAny{tag}{WSTEM[w]}", MSHORT[best], f"data/derived/C11/{w}.json lowest average FZ0 among models with an ES (script)")
            put(f"DnGap{tag}{WSTEM[w]}", vals["dn-rolling"] - vals[best], f"data/derived/C11/{w}.json delta-normal minus the lowest average FZ0 (script)", 2)
    long5 = [w for w in WINDOWS if w != "mixed-2023"]
    put("McsMinA", min(mcs(D, w, 0.01)["n_in_set"] for w in long5), "data/derived/C11/<window>.json comparison.mcs (five longer windows)")
    put("McsMaxA", max(mcs(D, w, 0.01)["n_in_set"] for w in long5), "data/derived/C11/<window>.json comparison.mcs (five longer windows)")
    for mid, stem in (("nn-fz", "Nn"), ("gjr-t", "Gjr"), ("hs-250", "Hs"), ("ewma", "Ewma")):
        r = [roughness(level(models(D, w)[mid], 0.01)["var"]) for w in WINDOWS]
        put(f"RoughMin{stem}", min(r), f"data/derived/C11/<window>.json {mid} by_level[0].var (script)", 3)
        put(f"RoughMax{stem}", max(r), f"data/derived/C11/<window>.json {mid} by_level[0].var (script)", 3)
    c = D["hyper"]["grid"]["estimation_window_days"]["candidates"]
    put("SelWinGap", abs(c[-1]["score"] - c[0]["score"]), "docs/design/features/c11/hyperparameter-selection.json grid.estimation_window_days", 2)
    pairs = t_sizepower_rows(D)
    sizes = [100 * p["null"]["rates"][p["null"]["study"]["rule_label"]]["rate"] for p in pairs]
    put("SizeMin", min(sizes), "data/derived/C22/other-families.json simulations[arm=null] (percent)", 1)
    put("SizeMax", max(sizes), "data/derived/C22/other-families.json simulations[arm=null] (percent)", 1)
    put("NStudies", len(pairs), "data/derived/C22/other-families.json simulations[market.*]")

    def power(tid: str, label: str | None = None) -> float:
        for p in pairs:
            if p["test"] == tid and (label is None or p["alt"]["study"]["label"]["en"] == label):
                a = p["alt"]
                return 100 * a["rates"][a["study"]["rule_label"]]["rate"]
        raise KeyError(tid)

    put("PowAz", power("market.acerbi_szekely"), "data/derived/C22/other-families.json market.acerbi_szekely alternative (percent)", 1)
    put("PowInd", power("market.christoffersen_independence"), "data/derived/C22/other-families.json market.christoffersen_independence alternative (percent)", 1)
    put("PowKup", power("market.kupiec_pof"), "data/derived/C22/other-families.json market.kupiec_pof alternative (percent)", 1)
    put("PowDqShort", power("market.dynamic_quantile_test", "250 days at 1%"), "data/derived/C22/other-families.json dynamic_quantile 250 days at 1% alternative (percent)", 1)
    put("PowDqLong", power("market.dynamic_quantile_test", "750 days at 1%"), "data/derived/C22/other-families.json dynamic_quantile 750 days at 1% alternative (percent)", 1)


def t_sizepower_rows(D: dict) -> list[dict]:
    out = []
    last = None
    for s in D["c22other"]["outputs"]["simulations"]:
        if not s["test_id"].startswith("market."):
            continue
        if s["study"]["arm"] == "null":
            last = s
            continue
        out.append({"test": s["test_id"], "null": last, "alt": s})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", type=pathlib.Path, default=None, help="also write every macro with its value and source as JSON")
    args = ap.parse_args()
    D = load()
    for fn in (t_ladder, t_selection, t_windows, t_exceed, t_reds, t_nn, t_rough, t_traffic, t_tests, t_sizepower, t_pla, t_desk, t_truth):
        fn(D)
    numbers(D)
    lines = ["% Generated by tables/make_market.py from data/derived (C11, C13, C22) and docs/design/features/c11: do not edit.",
             "% One macro per number the market section quotes."]
    for name in sorted(MACROS):
        lines.append(f"\\newcommand{{\\mk{name}}}{{{MACROS[name][0]}}}")
    (OUT / "market-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    if args.registry:
        args.registry.write_text(json.dumps({k: {"value": v[0], "source": v[1]} for k, v in sorted(MACROS.items())}, indent=1), encoding="utf-8")
    print(f"market tables written to {OUT}; {len(MACROS)} macros")


if __name__ == "__main__":
    main()
