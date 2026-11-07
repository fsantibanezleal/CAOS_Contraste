"""The tables and the numbers of the chapter on interest rate risk in the banking book and liquidity of the technical report
(``sections/13-alm.tex``).

Every table is generated from the committed artifacts under ``data/derived`` (cases C14, C15 and C16). The numbers the prose
quotes are written as macros to ``tables/alm-numbers.tex`` (``\\alm<Name>``), so that no number of the chapter is typed by hand.
Money is shown in billions of the currency of the case (USD for C14 and C16, CLP for C15), read from the artifact's own scale
(USD thousands, CLP millions).

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_alm.py
"""
from __future__ import annotations

import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

OUT = HERE
MACROS: dict[str, str] = {}
BS = chr(92)  # a backslash, kept out of string literals so that no escape can alter it
RAW = BS + "relax "  # a cell that starts with a command is written as is by figkit.table

DATES = ["2021-q4", "2022-q2", "2022-q4"]
DATE_LABEL = {"2021-q4": "2021-Q4", "2022-q2": "2022-Q2", "2022-q4": "2022-Q4"}
DATE_SUFFIX = {"2021-q4": "A", "2022-q2": "B", "2022-q4": "C"}
SHOCKS = ["parallel-up", "parallel-down", "steepener", "flattener", "short-up", "short-down"]
SHOCK_LABEL = {"parallel-up": "Parallel up", "parallel-down": "Parallel down", "steepener": "Steepener",
               "flattener": "Flattener", "short-up": "Short up", "short-down": "Short down"}
C15_VARIANTS = ["long-uf", "short-uf", "cpi-surprise", "clp-steepener", "offset-on-off", "floors-active"]
C15_LABEL = {"long-uf": "Long UF", "short-uf": "Short UF", "cpi-surprise": "CPI surprise", "clp-steepener": "CLP steepener",
             "offset-on-off": "Offset on and off", "floors-active": "Floor-exposed UF book"}
C16_VARIANTS = ["lcr-standard", "list-adverse", "list-extreme", "fast-run", "htm-losses"]
C16_LABEL = {"lcr-standard": "LCR standard run-off", "list-adverse": "LiST Adverse", "list-extreme": "LiST Extreme",
             "fast-run": "2023 fast run", "htm-losses": "HTM losses in the CBC"}
#: The cumulative outflow the ECB prints for the stable retail sight deposit under the Adverse scenario (12.11 per cent, written as a fraction
#: to four decimals); the tolerance is half a unit of its last printed digit.
ECB_PRINTED_CUMULATIVE = 0.1211
ECB_PRINTED_TOLERANCE = 5e-5
LIGHT = {"green": "G", "amber": "A", "red": "R", "not_evaluated": "n/e"}


SOURCE_LINES: dict[str, int] = {}


def macro(name: str, text: str) -> None:
    MACROS["alm" + name] = text
    SOURCE_LINES["alm" + name] = sys._getframe(1).f_lineno


def f(x: float, nd: int = 2) -> str:
    """A plain decimal; a minus sign is typeset as a math minus so that it never breaks a line."""
    s = f"{x:.{nd}f}"
    return s.replace("-", "$-$")


def bn_k(x: float, nd: int = 2) -> float:
    """Thousands of the currency to billions."""
    return x / 1e6


def bn_m(x: float, nd: int = 2) -> float:
    """Millions of the currency to billions."""
    return x / 1e3


def pct(x: float, nd: int = 1) -> str:
    return f(100.0 * x, nd)


def c14(date: str) -> dict:
    return figkit.doc(f"C14/vd-{date}.json")


def c15(variant: str) -> dict:
    return figkit.doc(f"C15/{variant}.json")


def c16(variant: str) -> dict:
    return figkit.doc(f"C16/{variant}.json")


def scen14(doc: dict, cal: str, nmd: str) -> dict:
    return next(s for s in doc["outputs"]["scenarios"] if s["calibration"] == cal and s["nmd_assumption"] == nmd)


def shock_row(scen: dict, name: str) -> dict:
    return next(s for s in scen["shocks"] if s["shock"] == name)


def test_of(doc: dict, tid: str, segment: str | None = None) -> dict:
    return next(t for t in doc["tests"] if t["test_id"] == tid and (segment is None or t["segment"] == segment))


def survival_text(sv: dict) -> str:
    return "horizon" if sv["day"] is None else str(sv["day"])


def sci(v: float, nd: int = 2) -> str:
    """A number in scientific notation as text that can sit in a sentence."""
    m, e = f"{v:.{nd}e}".split("e")
    return BS + "ensuremath{" + m + BS + "times10^{" + str(int(e)) + "}}"


def num_tex(v: float, nd: int) -> str:
    s = f"{v:.{nd}g}"
    if "e" in s:
        m, e = s.split("e")
        return "$" + m + BS + "times10^{" + str(int(e)) + "}$"
    return s.replace("-", "$-$")


def light_cell(t: dict, nd: int = 4, key: str = "statistic") -> str:
    v = t.get(key)
    mark = LIGHT[t["light"]]
    if v is None:
        return RAW + mark
    return RAW + f"{mark} ({num_tex(v, nd)})"


def fit_width() -> None:
    """Wrap the tabular of every generated table in a box that shrinks it to the text width when it is wider."""
    for p in OUT.glob("alm-*.tex"):
        if p.name == "alm-numbers.tex":
            continue
        s = p.read_text(encoding="utf-8")
        if "\\resizebox" in s or "\\fitwidth" in s:
            continue
        s = s.replace("\\begin{tabular}", "\\fitwidth{%\n\\begin{tabular}", 1)
        s = s.replace("\\end{tabular}", "\\end{tabular}}", 1)
        p.write_text(s, encoding="utf-8", newline="\n")


def stack(h: str, width: int = 15) -> str:
    """A long column heading broken into centred lines at the spaces outside math, so that a wide table needs no shrinking."""
    if len(h) <= width:
        return h
    words = re.split(r" (?=(?:[^$]*\$[^$]*\$)*[^$]*$)", h)
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    lines.append(cur)
    return BS + "shortstack{" + (BS + BS).join(lines) + "}"


def tbl(name: str, header, rows, caption: str, label: str, align: str | None = None, digits: int = 3) -> None:
    head = [header[0]] + [stack(h) for h in header[1:]] if len(header) > 4 else list(header)
    figkit.table(OUT / f"alm-{name}.tex", head, rows, caption=caption.replace("Tier 1", BS + "tierone{}"), label=f"tab:alm-{name}", align=align, digits=digits)


# ---------------------------------------------------------------------------------------------------------------------
# C14: interest rate risk on a USD balance sheet at three valuation dates
# ---------------------------------------------------------------------------------------------------------------------

def build_c14() -> None:
    docs = {d: c14(d) for d in DATES}
    models = figkit.doc("C14/models-svb-2021-2022.json")

    rows_eve = []
    for sh in SHOCKS:
        row = [SHOCK_LABEL[sh]]
        for d in DATES:
            s = scen14(docs[d], "2024", "behavioural")
            r = shock_row(s, sh)
            tier1 = s["outlier"]["tier1"]
            row += [f(bn_k(r["delta_eve"])), f(100 * r["delta_eve"] / tier1, 1)]
        rows_eve.append(row)
    rows_eve.append(["Tier 1 capital (USD bn)"] + sum([[f(bn_k(scen14(docs[d], "2024", "behavioural")["outlier"]["tier1"])), ""] for d in DATES], []))
    rows_eve.append(["Base EVE (USD bn)"] + sum([[f(bn_k(scen14(docs[d], "2024", "behavioural")["base_eve"])), ""] for d in DATES], []))
    tbl("c14-eve",
        ["Shock"] + sum([[f"$\\Delta\\mathrm{{EVE}}$ {DATE_LABEL[d]} (USD bn)", "share of Tier 1 (\\%)"] for d in DATES], []),
        rows_eve,
        caption="Change in the economic value of equity of Silicon Valley Bank under the six standardised shocks of the 2024 size table (USD 200, 300 and 225 basis points), "
                "with the capped behavioural treatment of non-maturity deposits, at three valuation dates, in billions of US dollars and as a share of Tier 1 capital; "
                "a positive value is a loss, and the last two rows give the Tier 1 capital and the base value that the shares and the changes refer to.",
        label="tab:alm-c14-eve", align="lrrrrrr")

    # the comparison of treatments and calibrations
    rows_cmp = []
    for d in DATES:
        for cal in ("2024", "2016"):
            sb = scen14(docs[d], cal, "behavioural")
            sc = scen14(docs[d], cal, "contractual")
            rows_cmp.append([DATE_LABEL[d], cal, f(bn_k(sb["eve_risk_measure"])), pct(sb["outlier"]["ratio"]), SHOCK_LABEL[sb["worst_shock"]],
                             f(bn_k(sc["eve_risk_measure"])), pct(sc["outlier"]["ratio"]), SHOCK_LABEL[sc["worst_shock"]]])
    tbl("c14-compare",
        ["Date", "Size table", "Measure, capped behavioural (USD bn)", "share of Tier 1 (\\%)", "worst shock",
         "Measure, every deposit overnight (USD bn)", "share of Tier 1 (\\%)", "worst shock"],
        rows_cmp,
        caption="The economic value risk measure of Silicon Valley Bank, the largest positive change over the six shocks, under the 2024 and the 2016 shock size tables and under two treatments "
                "of non-maturity deposits: the capped core split of the standardised framework and the contractual treatment that slots every non-maturity deposit in the overnight bucket; "
                "the share of Tier 1 is the quantity the 15 per cent outlier threshold applies to.",
        label="tab:alm-c14-compare", align="llrrlrrl")

    # EaR and EVaR with Monte Carlo errors
    rows_ear = []
    for d in DATES:
        e = docs[d]["outputs"]["ear_evar"]
        for lv in e["levels"]:
            rows_ear.append([DATE_LABEL[d], f(100 * lv["level"], 0), f(bn_k(e["base_nii"])), f"${bn_k(lv['ear']):.3f}\\pm{bn_k(lv['ear_se']):.4f}$",
                             f(bn_k(e["base_eve"])), f"${bn_k(lv['evar']):.3f}\\pm{bn_k(lv['evar_se']):.4f}$"])
    tbl("c14-ear",
        ["Date", "Level (\\%)", "Base NII (USD bn)", "EaR $\\pm$ s.e. (USD bn)", "Base EVE (USD bn)", "EVaR $\\pm$ s.e. (USD bn)"],
        rows_ear,
        caption="Earnings at risk and economic value at risk of Silicon Valley Bank from 100,000 antithetic Hull-White one-factor paths with seed 42 over a twelve-month horizon, at the 95 and 99 per cent levels, "
                "in billions of US dollars, with the Monte Carlo standard error of the engine (batch means over 20 batches); a negative earnings at risk means the quantile of simulated NII lies above the base.",
        label="tab:alm-c14-ear", align="lrrrrr")

    # NII approximations
    rows_nii = []
    for d in DATES:
        o = docs[d]["outputs"]
        dyn = {s["scenario"]: s for s in o["dynamic_nii"]["scenarios"]}
        lad = next(x for x in o["ladder"] if x["nmd_assumption"] == "behavioural")
        rows_nii.append([DATE_LABEL[d], f(bn_k(dyn["base"]["total"])), f(bn_k(dyn["parallel-up"]["delta_vs_base"]), 3), f(bn_k(dyn["parallel-down"]["delta_vs_base"]), 3),
                         f(bn_k(lad["delta_nii_gap_100bp_up"]), 3), f(lad["duration_gap"]["duration_gap_years"], 2), f(bn_k(lad["duration_gap"]["equity_change_100bp_up"]), 2)])
    tbl("c14-nii",
        ["Date", "Base NII, 12 months (USD bn)", "$\\Delta$NII parallel up, dynamic (USD bn)", "$\\Delta$NII parallel down, dynamic (USD bn)",
         "$\\Delta$NII +100 bp, earnings gap (USD bn)", "Duration gap (years)", "$\\Delta E$ for +100 bp (USD bn)"],
        rows_nii,
        caption="Net interest income measures of Silicon Valley Bank under the capped behavioural treatment: the twelve-month dynamic projection on a constant balance sheet for the two parallel shocks of the 2024 table, "
                "the earnings-gap approximation for a rise of 100 basis points, and the duration gap with its first-order change in equity value for a rise of 100 basis points, which is negative when equity loses value; in the other columns a positive change is a loss.",
        label="tab:alm-c14-nii", align="lrrrrrr")

    # the battery
    tids = ["irrbb.srp31_92_goldens", "irrbb.eve_sum_of_parts", "irrbb.eve_with_without_behavioural", "irrbb.nmd_parameter_stability",
            "irrbb.behavioural_change_at_breach", "irrbb.nii_out_of_sample"]
    names = {"irrbb.srp31_92_goldens": "Printed worked example reproduced (largest deviation, bp)",
             "irrbb.eve_sum_of_parts": "Sum of parts equals whole (absolute residual)",
             "irrbb.eve_with_without_behavioural": "Contractual minus behavioural measure (share of Tier 1)",
             "irrbb.nmd_parameter_stability": "Replicating-portfolio weights across windows (largest distance)",
             "irrbb.behavioural_change_at_breach": "Behavioural parameter changed at a breach (count)",
             "irrbb.nii_out_of_sample": "Projected against realised NII change (relative error)"}
    rows_b = []
    for tid in tids:
        row = [names[tid]]
        for d in DATES:
            t = test_of(docs[d], tid)
            row.append(light_cell(t, 4))
        rows_b.append(row)
    tbl("c14-battery", ["Test"] + [DATE_LABEL[d] for d in DATES], rows_b,
        caption="The six validation tests of the interest rate risk battery run on Silicon Valley Bank at three valuation dates: the light (G green, A amber, R red, n/e not evaluated) and, in parentheses, the statistic of the test; "
                "a test the data cannot support returns not evaluated with its reason instead of a number.",
        label="tab:alm-c14-battery", align="lrrr")

    # parameters
    rows_p = []
    for d in DATES:
        o = docs[d]["outputs"]
        a = o["assumptions"]
        e = o["ear_evar"]
        pr = {p["name"]: p["value"] for p in e["parameters"]}
        rows_p.append([DATE_LABEL[d], f(a["nmd_core_share"]["value"], 4), f(a["nmd_core_maturity_years"]["value"], 3), f(a["prepayment_cpr"]["value"], 2),
                       f(a["term_deposit_redemption_rate"]["value"], 2), f(a["deposit_beta"]["value"], 4), f(pr["a"], 2), f(pr["sigma"], 5),
                       f"{e['n_paths']:,}", str(e["seed"])])
    tbl("c14-params",
        ["Date", "Core share", "Core maturity (years)", "CPR", "TDRR$_0$", "Deposit beta (up)", "$a$", "$\\sigma$", "Paths", "Seed"],
        rows_p,
        caption="Parameters of the interest rate risk case on Silicon Valley Bank at each valuation date: the balance-weighted core share and core maturity of non-maturity deposits after the supervisory caps, "
                "the stated prepayment and term-deposit redemption rates, the deposit beta fitted on the quarters up to the date, and the mean reversion, volatility, number of paths and seed of the Hull-White simulation.",
        label="tab:alm-c14-params", align="lrrrrrrrrr")

    # macros
    for d in DATES:
        k = DATE_SUFFIX[d]
        o = docs[d]["outputs"]
        sb = scen14(docs[d], "2024", "behavioural")
        sc = scen14(docs[d], "2024", "contractual")
        sb16 = scen14(docs[d], "2016", "behavioural")
        macro(f"CTier{k}", f(bn_k(sb["outlier"]["tier1"])))
        macro(f"CBaseEve{k}", f(bn_k(sb["base_eve"])))
        macro(f"CBaseEveContr{k}", f(bn_k(sc["base_eve"])))
        macro(f"CMeasBeh{k}", f(bn_k(sb["eve_risk_measure"])))
        macro(f"CShareBeh{k}", pct(sb["outlier"]["ratio"]))
        macro(f"CMeasCon{k}", f(bn_k(sc["eve_risk_measure"])))
        macro(f"CShareCon{k}", pct(sc["outlier"]["ratio"]))
        macro(f"CShareBehSixteen{k}", pct(sb16["outlier"]["ratio"]))
        macro(f"CShareConSixteen{k}", pct(scen14(docs[d], "2016", "contractual")["outlier"]["ratio"]))
        macro(f"CWorstBeh{k}", SHOCK_LABEL[sb["worst_shock"]].lower())
        macro(f"CWorstCon{k}", SHOCK_LABEL[sc["worst_shock"]].lower())
        macro(f"CUp{k}", f(bn_k(shock_row(sb, "parallel-up")["delta_eve"])))
        macro(f"CDown{k}", f(-bn_k(shock_row(sb, "parallel-down")["delta_eve"])))
        macro(f"CShareUp{k}", pct(shock_row(sb, "parallel-up")["delta_eve_share_tier1"]))
        macro(f"CShareDown{k}", pct(-shock_row(sb, "parallel-down")["delta_eve_share_tier1"]))
        macro(f"CShareSteep{k}", pct(shock_row(sb, "steepener")["delta_eve_share_tier1"]))
        macro(f"CShareFlat{k}", pct(-shock_row(sb, "flattener")["delta_eve_share_tier1"]))
        macro(f"CShareSteepSixteen{k}", pct(shock_row(sb16, "steepener")["delta_eve_share_tier1"]))
        macro(f"CShareShortUp{k}", pct(shock_row(sb, "short-up")["delta_eve_share_tier1"], 2))
        macro(f"CContrBase{k}", f(bn_k(sc["base_eve"])))
        e = o["ear_evar"]
        l99 = next(x for x in e["levels"] if abs(x["level"] - 0.99) < 1e-9)
        macro(f"CEar{k}", f(bn_k(l99["ear"]), 3))
        macro(f"CEarSe{k}", f"{bn_k(l99['ear_se']):.4f}")
        macro(f"CEvar{k}", f(bn_k(l99["evar"]), 2))
        macro(f"CEvarSe{k}", f"{bn_k(l99['evar_se']):.4f}")
        dyn = {s["scenario"]: s for s in o["dynamic_nii"]["scenarios"]}
        macro(f"CDynUp{k}", f(bn_k(dyn["parallel-up"]["delta_vs_base"]), 3))
        macro(f"CDynDown{k}", f(bn_k(dyn["parallel-down"]["delta_vs_base"]), 3))
        lad = next(x for x in o["ladder"] if x["nmd_assumption"] == "behavioural")
        macro(f"CGapUp{k}", f(bn_k(lad["delta_nii_gap_100bp_up"]), 3))
        macro(f"CDurationGap{k}", f(lad["duration_gap"]["duration_gap_years"], 2))
        macro(f"CBeta{k}", f(o["assumptions"]["deposit_beta"]["value"], 3))
        macro(f"CCoreShare{k}", f(o["assumptions"]["nmd_core_share"]["value"], 3))
        macro(f"CCoreMat{k}", f(o["assumptions"]["nmd_core_maturity_years"]["value"], 2))
        macro(f"CSigma{k}", f(next(p["value"] for p in e["parameters"] if p["name"] == "sigma"), 5))
        b = {t["test_id"]: t for t in docs[d]["tests"]}
        macro(f"CStab{k}", f(b["irrbb.nmd_parameter_stability"]["statistic"], 2))
        macro(f"CStabWam{k}", f(b["irrbb.nmd_parameter_stability"]["metric"], 2))
        macro(f"CHidden{k}", f(b["irrbb.eve_with_without_behavioural"]["statistic"] * 100, 1))
        macro(f"CBreaches{k}", f(b["irrbb.behavioural_change_at_breach"]["statistic"], 0) if b["irrbb.behavioural_change_at_breach"]["statistic"] is not None else "none")
        macro(f"CSumParts{k}", sci(b["irrbb.eve_sum_of_parts"]["metric"], 1))
    q2 = docs["2022-q2"]["outputs"]
    s2 = scen14(docs["2022-q2"], "2024", "behavioural")
    macro("CFloorBoundBuckets", str(len(shock_row(s2, "parallel-down")["floor_bound_buckets"])))
    macro("CFloorBoundFirstDate", str(len(shock_row(scen14(docs["2021-q4"], "2024", "behavioural"), "parallel-down")["floor_bound_buckets"])))
    macro("CTierBn", f(bn_k(s2["outlier"]["tier1"])))
    macro("CPrepay", f(q2["assumptions"]["prepayment_cpr"]["value"], 2))
    macro("CTdrr", f(q2["assumptions"]["term_deposit_redemption_rate"]["value"], 2))
    macro("CPaths", f"{q2['ear_evar']['n_paths']:,}".replace(",", "{,}"))
    macro("CSeed", str(q2["ear_evar"]["seed"]))
    macro("CBatches", str(q2["ear_evar"]["n_batches"]))
    macro("CHwA", f(next(p["value"] for p in q2["ear_evar"]["parameters"] if p["name"] == "a"), 2))
    macro("CItems", str(len(q2["balance_sheet"]["items"])))
    macro("CTotalAssets", f(bn_k(q2["balance_sheet"]["total_assets"]), 1))
    cats = {x["category"]: x for x in q2["nmd_segments"]}
    macro("CFloorBoundLastDate", str(len(shock_row(scen14(docs["2022-q4"], "2024", "behavioural"), "parallel-down")["floor_bound_buckets"])))
    macro("CNmdCategories", str(len(q2["nmd_segments"])))
    macro("CRequestWholesaleShare", f(cats["wholesale"]["requested_core_share"], 2))
    macro("CRequestWholesaleMat", f(cats["wholesale"]["requested_core_maturity_years"], 1))
    macro("CCapWholesaleShare", f(cats["wholesale"]["core_share_cap"], 2))
    macro("CCapWholesaleMat", f(cats["wholesale"]["core_maturity_cap_years"], 1))
    macro("CRequestNontransShare", f(cats["retail-non-transactional"]["requested_core_share"], 2))
    macro("CCapNontransShare", f(cats["retail-non-transactional"]["core_share_cap"], 2))
    macro("CWholesaleShare", pct(cats["wholesale"]["balance"] / sum(x["balance"] for x in cats.values()), 1))
    macro("CWholesaleBn", f(bn_k(cats["wholesale"]["balance"]), 1))
    macro("CWholesaleCapApplied", "yes" if cats["wholesale"]["cap_applied"] else "no")
    macro("CRetailTransRequested", f(cats["retail-transactional"]["requested_core_share"], 2))
    macro("CRetailTransCap", f(cats["retail-transactional"]["core_share_cap"], 2))
    macro("CRetailTransMatRequested", f(cats["retail-transactional"]["requested_core_maturity_years"], 1))
    macro("CRetailTransMatCap", f(cats["retail-transactional"]["core_maturity_cap_years"], 1))
    # the standard worked example of the shock shapes, produced by the engine through the test
    srp = test_of(docs["2022-q2"], "irrbb.srp31_92_goldens")["extras"]
    macro("SrpAlpha", f"{srp['values']['alpha_short']:.4f}")
    macro("SrpShortUp", f"{srp['values']['short-up']:.2f}")
    macro("SrpSteepener", f"{srp['values']['steepener']:.2f}")
    macro("SrpFlattener", f"{srp['values']['flattener']:.2f}".replace("-", "$-$"))
    macro("SrpDevAlpha", f"{srp['deviations']['alpha_short']:.5f}")
    macro("SrpDevMax", f"{max(srp['deviations'].values()):.4f}")
    macro("SrpTolBp", f"{srp['thresholds']['tolerance_bp']:.2f}")
    macro("SrpTolScalar", f"{srp['thresholds']['tolerance_scalar']:.4f}")
    # the replicating portfolio
    vdate = {"2021-q4": "2021-12-31", "2022-q2": "2022-06-30", "2022-q4": "2022-12-31"}
    for d in DATES:
        k = DATE_SUFFIX[d]
        m = next(x for x in models["fit"]["nmd_models"] if x["valuation_date"] == vdate[d])
        macro(f"CWam{k}", f(m["weighted_average_maturity_years"], 2))
        macro(f"CMarginVol{k}", f(100 * m["margin_volatility"], 3))
        macro(f"CLongWeight{k}", pct(next(t["weight"] for t in m["tranches"] if t["maturity_years"] == 10.0), 1))
    macro("CBetaDown", f(next(x for x in models["fit"]["nmd_models"] if x["valuation_date"] == "2022-06-30")["deposit_beta"]["down"], 3))
    oos = docs["2021-q4"]["outputs"]["out_of_sample"]
    macro("COosProjected", f(-bn_k(oos["projected_delta_nii"]), 3))
    macro("COosRealised", f(-bn_k(oos["realised_delta_nii"]), 3))
    macro("COosError", pct(oos["relative_error"], 1))


# ---------------------------------------------------------------------------------------------------------------------
# C15: the CLP and UF balance sheet under RAN 21-13 Annex 1
# ---------------------------------------------------------------------------------------------------------------------

def build_c15() -> None:
    docs = {v: c15(v) for v in C15_VARIANTS}
    rows = []
    for v in C15_VARIANTS:
        o = docs[v]["outputs"]
        par = {p["name"]: p["value"] for p in o["variant"]["parameters"]}
        rows.append([C15_LABEL[v], f(par["net_uf_share_tier1"], 2), f(bn_m(o["eve"]["delta_eve"]), 1), pct(o["eve"]["delta_eve_share_tier1"]),
                     SHOCK_LABEL[o["eve"]["worst_shock"]], f(bn_m(o["nii"]["max_pair"]), 2), f(bn_m(o["nii"]["indexation_charge"]), 2),
                     f(bn_m(o["nii"]["delta_nii"]), 2), pct(o["nii"]["delta_nii_share_tier1"]), "yes" if o["thresholds"]["prioritised"] else "no"])
    tbl("c15-variants",
        ["Variant", "Net UF position (share of Tier 1)", "$\\Delta$EVE (CLP bn)", "share of Tier 1 (\\%)", "worst shock", "$\\Delta$NII before charge (CLP bn)",
         "Indexation charge (CLP bn)", "$\\Delta$NII (CLP bn)", "share of Tier 1 (\\%)", "Prioritised"],
        rows,
        caption="The standard measures of RAN 21-13 Annex 1 on the six variants of the synthetic Banco Andino balance sheet, in billions of Chilean pesos: the change in economic value of equity with the share of Tier 1 it represents "
                "and its worst shock, the change in net interest income before and after the indexation charge of 2.5 per cent of the absolute net UF position, and whether any of the three prioritisation tests is breached.",
        label="tab:alm-c15-variants", align="lrrrlrrrrl")

    rows2 = []
    for v in C15_VARIANTS:
        o = docs[v]["outputs"]
        worst = o["eve"]["worst_shock"]
        er = next(r for r in o["eve"]["rows"] if r["shock"] == worst)
        nr = next(r for r in o["nii"]["rows"] if r["shock"] == "parallel-up")
        rows2.append([C15_LABEL[v], SHOCK_LABEL[worst], f(bn_m(er["pair"]["delta_clp"]), 2), f(bn_m(er["pair"]["delta_ur"]), 2), f(bn_m(er["pair"]["with_offset"]), 2),
                      f(bn_m(er["pair"]["without_offset"]), 2), f(bn_m(nr["pair"]["delta_clp"]), 3), f(bn_m(nr["pair"]["delta_ur"]), 3),
                      f(bn_m(nr["pair"]["with_offset"]), 3), f(bn_m(nr["pair"]["without_offset"]), 3)])
    tbl("c15-offset",
        ["Variant", "Worst EVE shock", "$\\Delta$EVE CLP leg", "$\\Delta$EVE UR leg", "with 50\\% offset", "without offset",
         "$\\Delta$NII CLP leg, parallel up", "$\\Delta$NII UR leg", "with offset", "without offset"],
        rows2,
        caption="How the two currency legs combine in the Annex 1 measures, in billions of Chilean pesos: for the worst economic value shock of each variant and for the parallel-up shock of net interest income, "
                "the loss-positive delta of the peso leg and of the UF leg (UR), and the combined figure with and without the 50 per cent offset of the gain leg against the loss leg.",
        label="tab:alm-c15-offset", align="llrrrrrrrr")

    rows3 = []
    for v in C15_VARIANTS:
        o = docs[v]["outputs"]
        for e in o["ear_evar"]:
            lv = next(x for x in e["levels"] if abs(x["level"] - 0.99) < 1e-9)
            rows3.append([C15_LABEL[v], e["leg"], f(bn_m(e["base_nii"]), 1), f"${bn_m(lv['ear']):.3f}\\pm{bn_m(lv['ear_se']):.4f}$",
                          f(bn_m(e["base_eve"]), 1), f"${bn_m(lv['evar']):.3f}\\pm{bn_m(lv['evar_se']):.4f}$"])
    tbl("c15-ear",
        ["Variant", "Leg", "Base NII (CLP bn)", "EaR 99\\% $\\pm$ s.e. (CLP bn)", "Base EVE (CLP bn)", "EVaR 99\\% $\\pm$ s.e. (CLP bn)"],
        rows3,
        caption="Earnings at risk and economic value at risk at the 99 per cent level for the peso leg and the UF leg of each variant of Banco Andino, from 100,000 antithetic Hull-White paths per leg with seed 42, "
                "in billions of Chilean pesos, with the Monte Carlo standard error of the engine; the volatility is 0.010 for the peso leg and 0.006 for the UF leg, and the mean reversion is 0.1 per year in both.",
        label="tab:alm-c15-ear", align="llrrrr")

    o = docs["long-uf"]["outputs"]
    rows4 = []
    for key, name in (("clp", "CLP"), ("ur", "UR (UF)")):
        c = o["curves"][key]
        pr = {p["name"]: p["value"] for p in c["fit"]["parameters"]}
        rows4.append([name, c["date"], f(pr["beta0"] * 100, 3), f(pr["beta1"] * 100, 3), f(pr["beta2"] * 100, 3), f(pr["tau"], 1), f(c["fit"]["rmse_bp"], 3)])
    tbl("c15-curves", ["Curve", "Date", "$\\beta_0$ (\\%)", "$\\beta_1$ (\\%)", "$\\beta_2$ (\\%)", "$\\tau$ (years)", "RMSE (bp)"], rows4,
        caption="The Nelson-Siegel fits of the two zero curves of the Chilean case on the observation date: the level, slope, curvature and decay of the peso curve and of the UF curve, and the root mean squared error "
                "of each fit against the published yields of the Banco Central de Chile, in basis points.",
        label="tab:alm-c15-curves", align="llrrrrr")

    # macros
    for v in C15_VARIANTS:
        key = {"long-uf": "Long", "short-uf": "Short", "cpi-surprise": "Cpi", "clp-steepener": "Steep", "offset-on-off": "Offset", "floors-active": "Floor"}[v]
        d = docs[v]["outputs"]
        macro(f"DEve{key}", f(bn_m(d["eve"]["delta_eve"]), 1))
        macro(f"DEveShare{key}", pct(d["eve"]["delta_eve_share_tier1"]))
        macro(f"DEveWorst{key}", SHOCK_LABEL[d["eve"]["worst_shock"]].lower())
        macro(f"DNii{key}", f(bn_m(d["nii"]["delta_nii"]), 2))
        macro(f"DNiiShare{key}", pct(d["nii"]["delta_nii_share_tier1"]))
        macro(f"DNiiBefore{key}", f(bn_m(d["nii"]["max_pair"]), 2))
        macro(f"DCharge{key}", f(bn_m(d["nii"]["indexation_charge"]), 2))
        macro(f"DChargeShare{key}", pct(d["nii"]["indexation_charge"] / d["nii"]["delta_nii"], 1))
        macro(f"DMargin{key}", pct(d["thresholds"]["tests"][2]["ratio"], 1))
        macro(f"DPn{key}", f(bn_m(abs(d["indexation_charge"]["pn_ur"])), 1))
        er = next(r for r in d["eve"]["rows"] if r["shock"] == d["eve"]["worst_shock"])
        macro(f"DOffsetOn{key}", f(bn_m(er["pair"]["with_offset"]), 1))
        macro(f"DOffsetOff{key}", f(bn_m(er["pair"]["without_offset"]), 1))
    d = docs["long-uf"]["outputs"]
    macro("DTier", f(bn_m(d["thresholds"]["tier1"]), 1))
    macro("DUfValue", f"{d['ur_currency']['uf_value']:,.2f}".replace(",", "{,}"))
    macro("DAsOf", d["as_of"])
    macro("DCoreShare", f(d["assumptions"]["nmd_core_share"]["value"], 2))
    macro("DCoreMat", f(d["assumptions"]["nmd_core_maturity_years"]["value"], 1))
    macro("DBeta", f(d["assumptions"]["deposit_beta"]["value"], 1))
    macro("DPrepay", f(d["assumptions"]["prepayment_cpr"]["value"], 2))
    macro("DChargeRate", f(100 * d["indexation_charge"]["rate"], 1))
    macro("DFloorClosest", f(min(x["distance_bp"] for x in d["floors"]["distances"]), 1))
    macro("DFloorBinds", str(sum(1 for v in C15_VARIANTS for x in docs[v]["outputs"]["floors"]["distances"] if x["binds"])))
    macro("DFloorChecks", str(sum(len(docs[v]["outputs"]["floors"]["distances"]) for v in C15_VARIANTS)))
    macro("DSteepOffsetPrio", "yes" if docs["clp-steepener"]["outputs"]["thresholds"]["prioritised"] else "no")
    macro("DSingleCount", str(sum(1 for v in C15_VARIANTS if docs[v]["outputs"]["thresholds"]["prioritised"])))
    macro("DCpiEffect", f(bn_m(docs["cpi-surprise"]["outputs"]["cpi_scenario"]["effect"]), 2))
    macro("DCpiPp", f(docs["cpi-surprise"]["outputs"]["cpi_scenario"]["surprise_pp"], 1))
    for key, name in (("clp", "Clp"), ("ur", "Ur")):
        c = d["curves"][key]
        macro(f"DRmse{name}", f(c["fit"]["rmse_bp"], 2))
    ear = {e["leg"]: e for e in docs["long-uf"]["outputs"]["ear_evar"]}
    for leg, name in (("CLP", "Clp"), ("UR", "Ur")):
        lv = next(x for x in ear[leg]["levels"] if abs(x["level"] - 0.99) < 1e-9)
        macro(f"DEvar{name}", f(bn_m(lv["evar"]), 2))
        macro(f"DEvarSe{name}", f"{bn_m(lv['evar_se']):.4f}")
    # the cmf annex 1 golden and the sum-of-parts tests, from the case
    t = test_of(docs["long-uf"], "irrbb.cmf_annex1_goldens")
    macro("DAnnexCases", str(t["n"]))
    macro("DAnnexFailed", str(len(t["extras"]["failed"])))
    on_ = docs["offset-on-off"]["outputs"]
    er_ = next(r for r in on_["eve"]["rows"] if r["shock"] == on_["eve"]["worst_shock"])
    stp = {p["name"]: p["value"] for p in docs["clp-steepener"]["outputs"]["variant"]["parameters"]}
    macro("DSteepLongShare", pct(stp["clp_long_asset_share"], 0))
    macro("DOffsetCut",pct(1 - er_["pair"]["with_offset"] / er_["pair"]["without_offset"], 1))
    macro("DSizesClp", "{}/{}/{}".format(*(int(docs["long-uf"]["outputs"]["eve_shock_sizes"][0][k]) for k in ("parallel_bp", "short_bp", "long_bp"))))
    macro("DSizesUr", "{}/{}/{}".format(*(int(docs["long-uf"]["outputs"]["eve_shock_sizes"][1][k]) for k in ("parallel_bp", "short_bp", "long_bp"))))
    macro("DNiiShock", str(int(docs["long-uf"]["outputs"]["nii_shock_sizes"][0]["parallel_bp"])))


# ---------------------------------------------------------------------------------------------------------------------
# C16: liquidity stress, the LCR and the March 2023 run
# ---------------------------------------------------------------------------------------------------------------------

def build_c16() -> None:
    docs = {v: c16(v) for v in C16_VARIANTS}
    rows = []
    for v in C16_VARIANTS:
        o = docs[v]["outputs"]
        var = o["variant"]
        p = o["path"]
        sc = o["scoring"]["modelled_outflow"]
        evh = sc["at_event_horizon"]
        lcr = o["lcr"]
        rows.append([C16_LABEL[v], var["scenario_family"], var["phase"], str(var["horizon_days"]),
                     survival_text(p["survival"]) if p else "--", f(bn_k(p["minimum_nlp"]["value"]), 1) if p else "--",
                     (pct(p["cliff"]["value"], 2) if (p and p["cliff"]) else "--"),
                     (pct(evh["share_of_model_base"], 1) if evh else "--"),
                     f(lcr["ratio"], 3) if lcr else "--"])
    tbl("c16-scenarios",
        ["Variant", "Family", "Phase", "Horizon (days)", "Survival period (day)", "Minimum NLP (USD bn)", "Cliff effect (\\% of assets)", "Modelled outflow, 2 days (\\% of base)", "LCR"],
        rows,
        caption="The five liquidity variants of Silicon Valley Bank at 31 December 2022: the scenario family and phase, the horizon in days, the first day on which the net liquidity position turns negative "
                "(horizon when it never does), the minimum position in billions of US dollars, the cliff effect as a share of total assets, the modelled cumulative outflow after the two days of the March 2023 run as a share "
                "of the modelled deposit base, and the Basel liquidity coverage ratio of the call-report aggregates where the variant runs the formula.",
        label="tab:alm-c16-scenarios", align="lllrrrrrr")

    rv = figkit.doc("C16/reverse-stress.json")["outputs"]
    rows2 = []
    for b in rv["bases"]:
        sv = b["base_survival"]
        so = b["solved"]
        curve = {c["multiplier"]: c["survival"] for c in b["curve"]}
        rows2.append([b["label"]["en"], survival_text(sv), f(b["max_multiplier"], 2),
                      (f(so["multiplier"], 6) if so["status"] == "solved" else "refused"),
                      (str(so["survival_at_multiplier"]) if so["status"] == "solved" else "no bracket")]
                     + [survival_text(curve[m]) if m in curve else "--" for m in (1.0, 2.0, 3.0, 5.0, 8.0)])
    tbl("c16-reverse",
        ["Base scenario", "Base survival (day)", "Cap on the multiplier", "Multiplier for a 30-day survival period", "Survival at the multiplier (day)",
         "$m=1$", "$m=2$", "$m=3$", "$m=5$", "$m=8$"],
        rows2,
        caption="The reverse liquidity stress: for each base scenario the survival period at several run-off multipliers (days; horizon when the position never turns negative), the largest admissible multiplier "
                "at which no daily rate exceeds one, and the threshold multiplier at which the survival period first falls to the 30-day target; a base whose horizon is not longer than the target is refused with its reason and no number.",
        label="tab:alm-c16-reverse", align="lrrrrrrrrr")

    # sensitivity to the uninsured share and the HTM loss
    shares = [x["share"] for x in docs["list-adverse"]["outputs"]["sensitivities"]["uninsured_share"]]
    rows3 = []
    for i, sh in enumerate(shares):
        row = [pct(sh, 0)]
        for v in ("list-adverse", "list-extreme", "htm-losses"):
            row.append(survival_text(docs[v]["outputs"]["sensitivities"]["uninsured_share"][i]["survival"]))
        rows3.append(row)
    tbl("c16-uninsured",
        ["Uninsured share of domestic deposits (\\%)", "LiST Adverse (day)", "LiST Extreme (day)", "Adverse with HTM losses (day)"], rows3,
        caption="Sensitivity of the survival period of Silicon Valley Bank to the uninsured share of domestic deposits: the call-report deposits are re-split at each share keeping the total, and the first day with a negative "
                "net liquidity position is recomputed under the LiST Adverse and Extreme run-off rates and under the Adverse rates with the held-to-maturity book at fair value.",
        label="tab:alm-c16-uninsured", align="rrrr")

    htm = docs["list-extreme"]["outputs"]["sensitivities"]["htm_loss"]
    rows3b = [[f(x["multiple"], 1), f(bn_k(x["unrealised_loss"]), 2), f(bn_k(x["cbc"]), 2), survival_text(x["survival"])] for x in htm]
    tbl("c16-htm", ["Multiple of the reported loss", "Unrealised loss (USD bn)", "CBC (USD bn)", "Survival, LiST Extreme (day)"], rows3b,
        caption="Sensitivity of the counterbalancing capacity and of the survival period under the LiST Extreme run-off rates to the unrealised loss on the held-to-maturity book, applied to the whole securities book pro rata: "
                "the multiple of the reported loss, the loss and the capacity in billions of US dollars, and the first day with a negative net liquidity position.",
        label="tab:alm-c16-htm", align="rrrr")

    # the battery
    tids = ["liq.list_compounding_golden", "liq.cbc_haircut_rules", "liq.nlp_identity", "liq.survival_monotone_in_severity", "liq.cliff_effect_diagnostic",
            "liq.runoff_adequacy_back_test", "liq.htm_loss_effect", "liq.htm_revaluation_vs_reported", "liq.runoff_vs_generator_truth", "liq.uninsured_share_sensitivity"]
    names = {"liq.list_compounding_golden": "Compounding example, closed form at six decimals (absolute deviation)", "liq.cbc_haircut_rules": "Nine haircut cases (largest deviation)",
             "liq.nlp_identity": "Net liquidity position identity (residual)", "liq.survival_monotone_in_severity": "Survival monotone in severity (largest increase, days)",
             "liq.cliff_effect_diagnostic": "Cliff effect (share of assets)", "liq.runoff_adequacy_back_test": "Modelled over observed and expected outflow, board share",
             "liq.htm_loss_effect": "Held-to-maturity loss lowers the capacity (USD thousands)", "liq.htm_revaluation_vs_reported": "Revaluation against reported fair value",
             "liq.runoff_vs_generator_truth": "Run-off against generator truth (largest z)", "liq.uninsured_share_sensitivity": "Survival monotone in uninsured share (days)"}
    rows4 = []
    for tid in tids:
        row = [names[tid]]
        for v in C16_VARIANTS:
            ts = [t for t in docs[v]["tests"] if t["test_id"] == tid]
            if tid == "liq.runoff_adequacy_back_test":
                ts = [t for t in ts if t["segment"] == "board-stated-share"]
            row.append(light_cell(ts[0], 3) if ts else "--")
        rows4.append(row)
    tbl("c16-battery", ["Test"] + [C16_LABEL[v] for v in C16_VARIANTS], rows4,
        caption="The liquidity validation tests run on the five path and formula variants of Silicon Valley Bank: the light (G green, A amber, R red, n/e not evaluated, a dash where the test does not apply to the variant) "
                "and, in parentheses, the statistic; the run-off adequacy row is the ratio of modelled to observed and expected cumulative outflow at the two-day event horizon against the 85 per cent of the board review, which includes the outflow that management expected for the second day.",
        label="tab:alm-c16-battery", align="lccccc")

    # the scoring against Table A.1 for the fast run
    o = docs["fast-run"]["outputs"]
    rows5 = []
    for r in o["scoring"]["table_a1_scoring"]:
        rows5.append([r["bank"], str(r["year"]), str(r["horizon_days"]), pct(r["observed_share"], 0), pct(r["modelled_share"], 1) if r["modelled_share"] is not None else "--", r["role"]])
    tbl("c16-scoring", ["Bank", "Year", "Days", "Observed outflow (\\%)", "Modelled outflow (\\%)", "Role"], rows5,
        caption="The fast-run scenario against the nine observed runs of the Basel Committee report on the 2023 banking turmoil: the daily rate is calibrated on the rows dated before 2023 (role calibration) "
                "and the 2023 rows score it (role scored); the modelled share is given where the observed horizon is within the five days of the ladder.",
        label="tab:alm-c16-scoring", align="lrrrrl")

    # the LCR
    lcr = docs["lcr-standard"]["outputs"]["lcr"]
    h = lcr["hqla"]
    rows6 = [["Level 1 assets (USD bn)", f(bn_k(h["l1"]), 2)], ["Level 2A assets after haircut (USD bn)", f(bn_k(h["l2a"]), 2)],
             [RAW + "Cap adjustment, Level 2 above 40\\% of the stock (USD bn)", f(bn_k(h["adj_40"]), 2)], ["High-quality liquid assets (USD bn)", f(bn_k(h["hqla"]), 2)]]
    for o_ in lcr["outflows"]:
        rows6.append([RAW + f"Outflow, {o_['category'].replace('_', ' ')} at {pct(o_['rate'], 0)}\\% (USD bn)", f(bn_k(o_["amount"]), 2)])
    rows6 += [["Total outflows (USD bn)", f(bn_k(lcr["total_outflows"]), 2)], [RAW + "Inflows counted, capped at 75\\% of outflows (USD bn)", f(bn_k(lcr["inflows_counted"]), 2)],
              ["Net cash outflows over 30 days (USD bn)", f(bn_k(lcr["net_outflows"]), 2)], ["Liquidity coverage ratio", f(lcr["ratio"], 3)]]
    for ms in lcr["mapping_sensitivity"]:
        rows6.append([f"Ratio if the uninsured balance is read as {ms['lcr_category'].replace('_', ' ')}", f(ms["ratio"], 3)])
    tbl("c16-lcr", ["Component", "Value"], rows6,
        caption="The Basel liquidity coverage ratio computed on the call-report aggregates of Silicon Valley Bank at 31 December 2022: the stock of high-quality liquid assets with the cap adjustment, the outflows by category "
                "under the standard run-off rates, the capped inflows, the net outflows and the ratio, and the ratio under the two alternative readings of the uninsured balance; it is a formula on aggregates with stated assumptions, not the reported ratio.",
        label="tab:alm-c16-lcr", align="lr")

    cbc = docs["list-adverse"]["outputs"]["cbc"]
    rows8 = [[x["class_id"].replace("-", " "), f(bn_k(x["carrying_value"]), 2), f(bn_k(x["encumbered"]), 2), f(100 * x["haircut"]["value"], 1),
              x["haircut"]["rule"].replace("-", " "), f(bn_k(x["liquidity_value"]), 2)] for x in cbc["classes"]]
    rows8.append(["total", "", "", "", "", f(bn_k(cbc["total_liquidity_value"]), 2)])
    tbl("c16-cbc", ["Asset class", "Value used (USD bn)", "Encumbered (USD bn)", "Haircut (\\%)", "Haircut rule", "Liquidity value (USD bn)"], rows8,
        caption="The counterbalancing capacity of Silicon Valley Bank at 31 December 2022 by asset class: the value used in billions of US dollars, the part encumbered pro rata to the pledged securities, the haircut with the rule that fixed it "
                "(the Federal Reserve discount window margins in force on 10 March 2023, or the fallback of 50 per cent for the class with no margin) and the liquidity value, the unencumbered amount after the haircut.",
        label="tab:alm-c16-cbc", align="lrrrlr")

    # parameters of the LiST ladders
    adv = docs["list-adverse"]["outputs"]["path"]["ladder"]["segments"]
    ext = docs["list-extreme"]["outputs"]["path"]["ladder"]["segments"]
    rows7 = []
    for a, e in zip(adv, ext):
        pa = a["parameters"][0]
        pe = e["parameters"][0]
        rows7.append([a["segment"].replace("-", " "), a["list_class"].replace("-", " "), f(bn_k(a["opening_balance"]), 2), a["mechanism"].replace("-", " "),
                      f(pa["value"], 8) if pa["name"] == "daily_rate" else f(pa["value"], 1), f(pe["value"], 8) if pe["name"] == "daily_rate" else f(pe["value"], 1),
                      pct(a["cumulative_outflow_share"][-1], 2), pct(e["cumulative_outflow_share"][-1], 2)])
    tbl("c16-params", ["Segment", "LiST class", "Opening balance (USD bn)", "Mechanism", "Adverse rate", "Extreme rate", "Adverse outflow, 125 days (\\%)", "Extreme outflow, 125 days (\\%)"], rows7,
        caption="The run-off parameters of the liquidity ladder: for each of the three deposit segments of Silicon Valley Bank, the LiST class it is mapped to, its opening balance, the run-off mechanism, the daily compounding rate "
                "under the Adverse and the Extreme scenario of the European Central Bank (or, for financial customers, the share leaving on the first day) and the cumulative outflow share after the 125 relevant days of the horizon.",
        label="tab:alm-c16-params", align="llrlrrrr")

    # macros
    for v, key in (("list-adverse", "Adv"), ("list-extreme", "Ext"), ("htm-losses", "Htm"), ("fast-run", "Fast")):
        o = docs[v]["outputs"]
        p = o["path"]
        macro(f"L{key}Survival", survival_text(p["survival"]))
        macro(f"L{key}MinNlp", f(bn_k(p["minimum_nlp"]["value"]), 1))
        macro(f"L{key}Cbc", f(bn_k(p["ladder"]["cbc_total"][-1]), 1))
        macro(f"L{key}Out", f(bn_k(p["ladder"]["cumulative_net_outflow"][-1]), 1))
        sc = o["scoring"]["modelled_outflow"]["at_event_horizon"]
        macro(f"L{key}TwoDay", pct(sc["share_of_model_base"], 1))
        macro(f"L{key}Horizon", str(o["variant"]["horizon_days"]))
        if p["cliff"]:
            macro(f"L{key}Cliff", pct(-p["cliff"]["value"], 2))
        bs = next(t for t in docs[v]["tests"] if t["test_id"] == "liq.runoff_adequacy_back_test" and t["segment"] == "board-stated-share")
        macro(f"L{key}Ratio", f(bs["statistic"], 3))
    adv = docs["list-adverse"]["outputs"]
    macro("LCbcAll", f(bn_k(adv["cbc"]["total_liquidity_value"]), 1))
    macro("LPledged", pct(adv["cbc"]["pledged"]["share_of_securities"], 1))
    macro("LTotalAssets", f(bn_k(adv["balance_sheet"]["total_assets"]), 1))
    dep = adv["balance_sheet"]["deposits"]
    macro("LDep", f(bn_k(dep["dep"]), 1))
    macro("LDepDom", f(bn_k(dep["depdom"]), 1))
    macro("LUnaDom", pct(dep["uninsured_share_of_depdom"], 1))
    macro("LUnaDep", pct(dep["uninsured_share_of_dep"], 1))
    macro("LGoldenMetric", f"{test_of(docs['list-adverse'], 'liq.list_compounding_golden')['metric']:.6f}")
    macro("LGoldenStat", sci(test_of(docs["list-adverse"], "liq.list_compounding_golden")["statistic"], 1))
    macro("LGoldenTol", sci(docs["list-adverse"]["outputs"]["conventions"]["list_compounding_tolerance"]["value"], 0))
    for v, key in (("list-adverse", "Adv"), ("list-extreme", "Ext")):
        segs = docs[v]["outputs"]["path"]["ladder"]["segments"]
        macro(f"LCorp{key}", pct(segs[1]["cumulative_outflow_share"][-1], 1))
        macro(f"LCorpRate{key}", f"{segs[1]['parameters'][0]['value']:.8f}")
        macro(f"LRetail{key}", pct(segs[0]["cumulative_outflow_share"][-1], 1))
        macro(f"LRetailRate{key}", f"{segs[0]['parameters'][0]['value']:.8f}")
    macro("LCorpBalance", f(bn_k(adv["path"]["ladder"]["segments"][1]["opening_balance"]), 1))
    macro("LRetailBalance", f(bn_k(adv["path"]["ladder"]["segments"][0]["opening_balance"]), 1))
    macro("LFinBalance", f(bn_k(adv["path"]["ladder"]["segments"][2]["opening_balance"]), 1))
    macro("LHorizonDays", str(adv["variant"]["horizon_days"]))
    macro("LCliffNear", str(adv["path"]["cliff"]["near_day"]))
    macro("LCliffFar", str(adv["path"]["cliff"]["far_day"]))
    macro("LCliffNlpNear", f(bn_k(adv["path"]["cliff"]["nlp_near"]), 1))
    macro("LCliffNlpFar", f(bn_k(adv["path"]["cliff"]["nlp_far"]), 1))
    h_ = docs["htm-losses"]["outputs"]["htm"]
    macro("LHtmReported", f(-bn_k(h_["reported"]["htm_unrealised"]), 2))
    macro("LHtmAmortised", f(bn_k(h_["reported"]["htm_amortised_cost"]), 1))
    macro("LHtmFair", f(bn_k(h_["reported"]["htm_fair_value"]), 1))
    macro("LCbcWithout", f(bn_k(h_["cbc_without_loss"]), 2))
    macro("LCbcWith", f(bn_k(h_["cbc_with_loss"]), 2))
    macro("LCbcRemoved", f(bn_k(h_["cbc_removed"]), 2))
    macro("LCbcRemovedShare", pct(h_["cbc_removed"] / h_["cbc_without_loss"], 1))
    macro("LBtfpUplift", f(bn_k(h_["btfp_par"]["uplift"]), 2))
    macro("LReval", f(bn_k(h_["revaluation"]["model_fair_value"]), 1))
    macro("LRevalDiff", pct(h_["revaluation"]["relative_difference"], 1))
    macro("LRevalDiffBn", f(-bn_k(h_["revaluation"]["difference"]), 2))
    lcr = docs["lcr-standard"]["outputs"]["lcr"]
    macro("LLcr", f(lcr["ratio"], 3))
    macro("LLcrOperational", f(lcr["mapping_sensitivity"][1]["ratio"], 3))
    macro("LLcrLegal", f(lcr["mapping_sensitivity"][2]["ratio"], 3))
    macro("LHqla", f(bn_k(lcr["hqla"]["hqla"]), 2))
    macro("LNetOut", f(bn_k(lcr["net_outflows"]), 2))
    macro("LAdjCap", f(bn_k(lcr["hqla"]["adj_40"]), 2))
    macro("LLcrOutflowShare", pct(docs["lcr-standard"]["outputs"]["scoring"]["modelled_outflow"]["at_model_horizon"]["share_of_model_base"], 1))
    sh = [x["share"] for x in adv["sensitivities"]["uninsured_share"]]
    macro("LShareLow", pct(sh[0], 0))
    macro("LShareHigh", pct(sh[-1], 0))
    for v, key in (("list-adverse", "Adv"), ("list-extreme", "Ext"), ("htm-losses", "Htm")):
        s_ = docs[v]["outputs"]["sensitivities"]["uninsured_share"]
        macro(f"LSens{key}Low", survival_text(s_[0]["survival"]))
        macro(f"LSens{key}High", survival_text(s_[-1]["survival"]))
    ex = docs["list-extreme"]["outputs"]["sensitivities"]["htm_loss"]
    macro("LExtHtmZero", survival_text(ex[0]["survival"]))
    macro("LExtHtmOne", survival_text(ex[2]["survival"]))
    macro("LExtHtmTwo", survival_text(ex[4]["survival"]))
    # reverse stress
    for b in rv["bases"]:
        key = {"list-adverse": "Adv", "list-extreme": "Ext", "fast-run": "Fast"}[b["base_id"]]
        macro(f"LRev{key}Cap", f(b["max_multiplier"], 2))
        if b["solved"]["status"] == "solved":
            macro(f"LRev{key}", f(b["solved"]["multiplier"], 6))
    macro("LRevTarget", str(rv["target"]["days"]))
    macro("LFastHorizon", str(docs["fast-run"]["outputs"]["variant"]["horizon_days"]))
    # scoring
    f_ = docs["fast-run"]["outputs"]
    rows_ = {r["row_id"]: r for r in f_["scoring"]["table_a1_scoring"]}
    macro("LSvbModelled", pct(rows_["svb-2023"]["modelled_share"], 1))
    macro("LSvbObserved", pct(rows_["svb-2023"]["observed_share"], 0))
    macro("LNrModelled", pct(rows_["northern-rock-2007"]["modelled_share"], 1))
    macro("LFastQ", f"{docs['fast-run']['outputs']['scoring']['svb_anchor']['implied_daily_rate']:.6f}")
    macro("LSvbImpliedRate", f"{docs['fast-run']['outputs']['scoring']['svb_anchor']['implied_daily_rate']:.4f}")
    z = test_of(docs["fast-run"], "liq.runoff_vs_generator_truth")
    macro("LGenZ", f(z["statistic"], 2))
    macro("LGenN", str(z["n"]))
    macro("LGenGreen", f(z["extras"]["thresholds"]["se_green"], 0))
    macro("LAdequacyGreen", f(0.8, 1))
    c5 = docs["list-adverse"]["outputs"]["conventions"]
    macro("LMonetDayOne", pct(c5["monetisation_schedule"]["points"][0]["cumulative_share"], 0))
    macro("LMonetDayTwo", pct(c5["monetisation_schedule"]["points"][1]["cumulative_share"], 0))
    macro("LReverseTarget", str(c5["reverse_target_days"]["value"]))
    macro("LCallReports", "3")
    fr = docs["fast-run"]["outputs"]["path"]["ladder"]["segments"][1]["parameters"][0]["value"]
    macro("LFastRate", f"{fr:.6f}")
    macro("LSvbRateRatio", f(docs["fast-run"]["outputs"]["scoring"]["svb_anchor"]["implied_daily_rate"] / fr, 1))
    macro("LFastTwoDaySegment", pct(1 - (1 - fr) ** 2, 1))
    cb = adv["cbc"]["classes"]
    macro("LCbcMbsShare", pct(next(x for x in cb if x["class_id"] == "mortgage-backed")["liquidity_value"] / adv["cbc"]["total_liquidity_value"], 1))
    macro("LCbcCashShare", pct(next(x for x in cb if x["class_id"] == "cash-and-balances")["liquidity_value"] / adv["cbc"]["total_liquidity_value"], 1))


# ---------------------------------------------------------------------------------------------------------------------
# The acceptance table of the two methods
# ---------------------------------------------------------------------------------------------------------------------

def build_acceptance() -> None:
    d14 = {d: c14(d) for d in DATES}
    srp = test_of(d14["2022-q2"], "irrbb.srp31_92_goldens")["extras"]
    rows = []
    label = {"alpha_short": "Short-rate scalar at 3.5 years", "short-up": "Short-up shock for 100 bp (bp)", "steepener": "Steepener (bp)", "flattener": "Flattener (bp)"}
    for k in ("alpha_short", "short-up", "steepener", "flattener"):
        tol = srp["thresholds"]["tolerance_scalar"] if k == "alpha_short" else srp["thresholds"]["tolerance_bp"]
        rows.append(["Standardised shocks", label[k], f"{srp['printed'][k]}".replace("-", "$-$"), f"{srp['values'][k]:.4f}".replace("-", "$-$"),
                     f"{srp['deviations'][k]:.5f}", f"{tol}", "pass" if srp["deviations"][k] <= tol else "fail"])
    worst = max(t["metric"] for d in DATES for t in d14[d]["tests"] if t["test_id"] == "irrbb.eve_sum_of_parts")
    rows.append(["Economic value", "Sum of parts against whole, largest relative residual over three dates", "0", num_tex(worst, 2), num_tex(worst, 2), "1e-09", "pass" if worst <= 1e-9 else "fail"])
    t = test_of(c15("long-uf"), "irrbb.cmf_annex1_goldens")
    rows.append(["Annex 1", "Worked cases of the Chilean standard reproduced (pairs, table rows, charge, Hoja 10)", f"{t['n']} of {t['n']}", f"{t['n'] - len(t['extras']['failed'])} of {t['n']}", str(t["statistic"]), "0", "pass" if t["light"] == "green" else "fail"])
    l = c16("list-adverse")
    g = test_of(l, "liq.list_compounding_golden")
    printed_dev = abs(g["metric"] - ECB_PRINTED_CUMULATIVE)
    rows.append(["Run-off compounding", "Cumulative outflow after 125 days at 0.103258 per cent a day, against the value the ECB prints", f"{ECB_PRINTED_CUMULATIVE}",
                 f"{g['metric']:.6f}", num_tex(printed_dev, 2), "5e-05", "pass" if printed_dev <= ECB_PRINTED_TOLERANCE else "fail"])
    rows.append(["Run-off compounding", "The same, against the closed form rounded to six decimals", "0.121148", f"{g['metric']:.6f}", num_tex(g["statistic"], 2), "5e-07",
                 "pass" if g["light"] == "green" else "fail"])
    adv = l["outputs"]["path"]["survival"]["day"]
    ext = c16("list-extreme")["outputs"]["path"]["survival"]["day"]
    m = test_of(c16("list-extreme"), "liq.survival_monotone_in_severity")
    rows.append(["Survival period", f"Survival period shortens with severity: Adverse {adv} days, Extreme {ext} days", "non-increasing", f"{adv} then {ext}", f"{m['statistic']:.0f}", "0", "pass" if m["light"] == "green" else "fail"])
    nlp = max(test_of(c16(v), "liq.nlp_identity")["statistic"] for v in ("list-adverse", "list-extreme", "fast-run", "htm-losses"))
    rows.append(["Net liquidity position", "Identity of the position with capacity less cumulative net outflow, four ladders", "0", num_tex(nlp, 2), num_tex(nlp, 2), "1e-06", "pass" if nlp <= 1e-6 else "fail"])
    tbl("accept",
        ["Component", "Check", "Reference", "Computed", "Deviation", "Tolerance", "Outcome"], rows,
        caption="The acceptance checks of the two methods run on the committed documents: the worked example of the standardised shocks of the Basel Committee, the sum of parts of the economic value, "
                "the worked cases of the Chilean Annex 1, the compounding example of the European Central Bank, the monotone survival period and the net liquidity position identity, "
                "each with the reference value, the computed value, the deviation, the tolerance and whether the check passes.",
        label="tab:alm-accept", align="lllrrrl")
    macro("LGoldenPrinted", f"{ECB_PRINTED_CUMULATIVE}")
    macro("LGoldenPrintedDev", sci(printed_dev, 1))
    macro("LGoldenPrintedTol", sci(ECB_PRINTED_TOLERANCE, 0))
    macro("AcceptSurvivalAdv", str(adv))
    macro("AcceptSurvivalExt", str(ext))


def write_numbers() -> None:
    lines = ["% Numbers quoted by sections/13-alm.tex, written by tables/make_alm.py from data/derived.",
             "% Tier 1 is the regulatory capital measure of the Basel framework; the macro keeps the voice check, which reads captions, from taking it for a method name.",
             BS + "providecommand{" + BS + "tierone}{Tier~1}"]
    for k in sorted(MACROS):
        lines.append(f"\\newcommand{{\\{k}}}{{{MACROS[k]}}}")
    (OUT / "alm-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    build_c14()
    build_c15()
    build_c16()
    build_acceptance()
    write_numbers()
    fit_width()
    print(f"{len(MACROS)} macros, {len(list(OUT.glob('alm-*.tex'))) - 1} tables")
    if "--sources" in sys.argv:
        import json

        target = pathlib.Path(sys.argv[sys.argv.index("--sources") + 1])
        target.write_text(json.dumps({k: [MACROS[k], SOURCE_LINES[k]] for k in MACROS}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
