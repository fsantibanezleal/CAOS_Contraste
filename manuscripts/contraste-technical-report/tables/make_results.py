"""Tables and number macros of the framing sections and of the results across the cases of the technical report
(sections/01 to 05 and 18 to 24), built from the committed artifacts under ``data/derived``, the committed source registry
``data-pipeline/config/sources.json``, the design document ``docs/design/SDD.md`` and the macros the method sections
already read from the same artifacts; nothing in those sections is typed by hand.

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_results.py

Writes, into ``tables/``:

* ``results-numbers.tex``: ``\\newcommand`` macros ``\\rs...``, one per number the prose of the framing sections reads;
* ``results-summary.tex``: ``tab:results-summary``, one row per case (question, headline result with its uncertainty,
  opinion level, findings by severity);
* ``results-lights.tex``: ``tab:results-lights``, the test lights of the validation reports of each case;
* ``results-cases.tex``, ``results-sources.tex``, ``results-splits.tex``: the cases, the sources and the leakage-safe splits
  of the data section;
* ``results-protocol.tex``: the seed, the variants and the tests run of each case;
* ``results-versions.tex``: the pinned versions of the reproducibility section.

The figure script imports ``derive`` from this file, so the tables and the figures read the same values.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

ROOT = figkit.ROOT
DERIVED = figkit.DERIVED
OUT = HERE
SEV = ["S1", "S2", "S3", "S4"]
SEV_WORD = {"S1": "One", "S2": "Two", "S3": "Three", "S4": "Four"}
WORDS = {0: "Zero", 1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"}
NUMBER_FILES = ["credit-scoring", "ratings", "provisions", "lgd-ead", "credit-capital", "market", "ccr", "alm", "oprisk",
                "aggregation-stress", "validation-tests", "proposed"]
CATEGORY_MACRO = {"credit-scoring": "CreditScoring", "ratings-calibration": "RatingsCalibration", "provisions": "Provisions",
                  "lgd-ead": "LgdEad", "portfolio-capital": "PortfolioCapital", "market-ccr": "MarketCcr",
                  "balance-sheet": "BalanceSheet", "operational": "Operational", "capital-stress": "CapitalStress",
                  "ml-ai-risk": "MlAiRisk", "validator": "Validator"}
CASE_WITH_NO_RESULT = "C19"

PAT = re.compile(r"\\newcommand\{\\(\w+)\}\{(.*)\}\s*$")
LE_PAT = re.compile(r"\\expandafter\\gdef\\csname lgdead:([^\\]+)\\endcsname\{(.*)\}\s*$")


# ----------------------------------------------------------------------------------------------------------------------
# the macros the method sections already read from the artifacts

def read_numbers() -> tuple[dict[str, str], dict[str, str]]:
    """The ``\\newcommand`` macros of the generated numbers files and the ``\\LE`` keys of the loss section."""
    macros: dict[str, str] = {}
    le: dict[str, str] = {}
    for name in NUMBER_FILES:
        path = HERE / f"{name}-numbers.tex"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            m = PAT.match(line)
            if m:
                macros[m.group(1)] = m.group(2)
            e = LE_PAT.match(line)
            if e:
                le[e.group(1)] = e.group(2)
    return macros, le


MACROS, LE = read_numbers()


def m(name: str) -> str:
    """The invocation of a macro of the method sections; a name that no numbers file defines stops the script."""
    if name not in MACROS:
        raise KeyError(f"macro \\{name} is defined by no numbers file")
    return f"\\{name}{{}}"


def le(key: str) -> str:
    if key not in LE:
        raise KeyError(f"\\LE key {key} is defined by no numbers file")
    return f"\\LE{{{key}}}"


# ----------------------------------------------------------------------------------------------------------------------
# formatting

def group(n: int) -> str:
    return f"{n:,}".replace(",", "{,}")


def f1(x: float) -> str:
    return f"{x:.1f}"


def f2(x: float) -> str:
    return f"{x:.2f}"


def f3(x: float) -> str:
    return f"{x:.3f}"


def f4(x: float) -> str:
    return f"{x:.4f}"


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def signed(x: float, d: int = 3) -> str:
    return f"$-${abs(x):.{d}f}" if x < 0 else f"+{x:.{d}f}"


def esc(text: str) -> str:
    return figkit.tex_escape(text)


def letters(n: int) -> str:
    """A non-negative integer spelled with letters, so that it can sit in a macro name."""
    return "".join(WORDS[int(c)] for c in str(n))


def wilson(k: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


# ----------------------------------------------------------------------------------------------------------------------
# loading

def load(rel: str):
    return figkit.doc(rel)


def impact(doc: dict, key: str) -> dict:
    return doc["impact"][key]


def derive() -> dict:
    """Every value the framing sections and the figures read, from the committed artifacts."""
    index = load("manifests/index.json")
    findings = load("governance/findings.json")
    by_case = {c["case_id"]: c for c in findings["counts"]["by_case"]}
    cases = []
    for entry in index["cases"]:
        cid = entry["case_id"]
        manifest = load(f"manifests/{cid}.json") if cid != CASE_WITH_NO_RESULT else None
        cases.append({"id": cid, "title": entry["title"]["en"], "category_id": entry["category_id"],
                      "category": entry["category"]["en"], "kind": entry["kind"], "manifest": manifest})
    reports: dict[str, list[dict]] = {}
    report_dir = DERIVED / "governance" / "reports"
    for path in sorted(report_dir.glob("*.json")):
        rep = json.loads(path.read_text(encoding="utf-8"))
        cid = path.name.split("-")[0]
        s11 = next(s for s in rep["sections"] if s["key"] == "opinion_and_recommendation")
        reports.setdefault(cid, []).append({"file": path.name, "entry_key": rep["entry_key"], "counts": rep["test_counts"],
                                            "level": s11["opinion"]["level"], "label": s11["opinion"]["level_label"]["en"]})
    for c in cases:
        cid = c["id"]
        c["findings"] = by_case.get(cid)
        c["reports"] = reports.get(cid, [])
        man = c["manifest"]
        if man is None:
            c.update(variants=0, tests=0, p_tests=0, seed=None, truth=[], default=None, sources=[])
            continue
        variants = [a for a in man["artifacts"] if a["role"] == "variant"]
        tests = p_tests = 0
        for a in variants:
            d = load(f"{cid}/{a['variant_id']}.json")
            tests += len(d["tests"])
            p_tests += sum(1 for t in d["tests"] if t.get("p_value") is not None)
        truth = sorted({a["truth_status"] for a in man["artifacts"] if a.get("truth_status")})
        c.update(variants=len(variants), tests=tests, p_tests=p_tests, seed=man["seed"], truth=truth,
                 default=man["default_variant"], sources=man["sources"], question=man["question"]["en"],
                 source_details=man["source_details"], engine=man["engine"])
    sources = load_json_path(ROOT / "data-pipeline" / "config" / "sources.json")
    return {"index": index, "findings": findings, "cases": cases, "reports": reports, "sources": sources}


def load_json_path(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------------------------------------------------
# the headline of each case

def headline(c: dict) -> str:
    """The headline result of a case with its uncertainty, as LaTeX; every number is an artifact value or a macro."""
    cid = c["id"]
    if cid == "C01":
        return (f"Scorecard AUC {m('csHoScAuc')} (95\\,\\% CI {m('csHoScAucLo')} to {m('csHoScAucHi')}) on {m('csHoN')} held-out "
                f"cards; LightGBM adds {m('csHoLgDlDiff')} (DeLong $p$ {m('csHoLgDlP')}).")
    if cid == "C02":
        return (f"One-year file: scorecard AUC {m('csCtwoAScAuc')} (95\\,\\% CI {m('csCtwoAScAucLo')} to {m('csCtwoAScAucHi')}); "
                f"the explainable boosting machine adds {m('csCtwoAEbDiff')} ({m('csCtwoAEbDiffLo')} to {m('csCtwoAEbDiffHi')}).")
    if cid == "C03":
        d = load("C03/fy2008-10.json")
        row = next(r for r in d["outputs"]["rung_comparison"] if r["rung_id"] == "P1-scorecard")
        lgb = next(r for r in d["outputs"]["rung_comparison"] if r["rung_id"] == "P4-lightgbm")
        return (f"FY2008--10 cohort: scorecard AUC {f3(row['auc'])} (95\\,\\% CI {f3(row['auc_ci_low'])} to {f3(row['auc_ci_high'])}), "
                f"LightGBM {f3(lgb['auc'])} ({f3(lgb['auc_ci_low'])} to {f3(lgb['auc_ci_high'])}); "
                f"observed 5-year PD {pct(impact(d, 'observed_5y_pd')['value'])}\\,\\% against "
                f"{pct(impact(d, 'predicted_5y_pd')['value'])}\\,\\% predicted.")
    if cid == "C04":
        return (f"Long-run PD of CCC--C {m('rtgLraSpCCCC')}\\,\\% (S\\&P), {m('rtgLraMoodysCCCC')}\\,\\% (Moody's), "
                f"{m('rtgLraFitchCCCC')}\\,\\% (Fitch); AAA of S\\&P: {m('rtgLradSpAAA')} defaults in {m('rtgLranSpAAA')} "
                f"rating-years, 95\\,\\% Jeffreys upper bound {m('rtgJeffupSpAAA')}\\,\\%.")
    if cid == "C05":
        d = load("C05/sp-2010.json")
        rw = [v["value"] for k, v in d["impact"].items() if k.startswith("rw_") and v["unit"] == "share of EAD"]
        return (f"IRB risk weight of one book under {len(rw)} PD-curve approaches for 2010: {pct(min(rw))}\\,\\% to "
                f"{pct(max(rw))}\\,\\% of EAD (exact recomputation, no sampling interval).")
    if cid == "C06":
        return (f"Cox c-index {m('pvCindexCoxMin')} to {m('pvCindexCoxMax')} and PC-Hazard c-index {m('pvCindexPchMin')} to "
                f"{m('pvCindexPchMax')} over {m('pvDatesTotal')} reporting dates (range over dates, no interval).")
    if cid == "C07":
        d = load("C07/base.json")
        return (f"Base scenario provision (thousand million CLP): CMF B-1 {f1(impact(d, 'provision_cmf_b1')['value'] / 1e9)}, IFRS 9 "
                f"{f1(impact(d, 'provision_ifrs9')['value'] / 1e9)}, Banco de Espa\\~na Annex 9 "
                f"{f1(impact(d, 'provision_bde')['value'] / 1e9)}; IFRS 9 over B-1 {f2(impact(d, 'ifrs9_over_b1')['value'])} "
                f"(synthetic bank, no interval).")
    if cid == "C08":
        return (f"Calibration by segment red in {le('cal-red')} of {le('cal-total')} cohort-by-rung tests, {le('cal-positive')} "
                f"gaps under-predicting; $R^2$ between {le('r2-min')} and {le('r2-max')}; gradient boosting has the lowest RMSE "
                f"in {le('bestcount-L5-gradient-boosted')} of {c['variants']} cohorts.")
    if cid == "C09":
        d = load("C09/level-3.json")
        rows = {r["design"]: r for r in d["outputs"]["ccf_by_design"]["rows"] if r["treatment"] == "none" and r["estimator"] == "pooled"}
        truth = impact(d, "true_ccf")["value"]

        def cell(design: str) -> str:
            r = rows[design]
            return f"{signed(r['bias'])} [{signed(r['ci_low'])}, {signed(r['ci_high'])}]"

        return (f"Untreated pooled CCF bias against the known {f3(truth)}: fixed horizon {cell('fixed-horizon')}, cohort "
                f"{cell('cohort')}, variable horizon {cell('variable-horizon')} (95\\,\\% intervals).")
    if cid == "C10":
        return (f"Fitted asset correlation {m('ccRhoMlRes')} for residential real estate ({m('ccRhoMlLoRes')} to "
                f"{m('ccRhoMlHiRes')}) and {m('ccRhoMlCre')} for commercial real estate ({m('ccRhoMlLoCre')} to "
                f"{m('ccRhoMlHiCre')}), 95\\,\\% profile intervals.")
    if cid == "C11":
        return (f"Eligible models of {m('mkNModels')}: {m('mkEligCalm')} in the calm window, {m('mkEligGfc')} in 2007--09, "
                f"{m('mkEligCovid')} in 2020, {m('mkEligRates')} in the 2022 rates window, {m('mkEligFx')} in the FX window "
                f"(Kupiec, conditional coverage and Acerbi--Szekely tests).")
    if cid == "C12":
        return (f"Netting-set EEPE USD {m('ccrEepeNetting')}; one standard error on the mean reversion ({m('ccrHwA')} "
                f"$\\pm$ {m('ccrHwASe')}) moves it by {m('ccrEepeAPlusPct')}\\,\\% to +{m('ccrEepeAMinusPct')}\\,\\%.")
    if cid == "C13":
        a = load("C13/missing-basis.json")["outputs"]["detection"]
        b = load("C13/stale-volatility.json")["outputs"]["detection"]
        return (f"Profit-and-loss attribution flags the missing-basis model in {pct(a['share_amber_or_red'])}\\,\\% "
                f"({pct(a['ci_low'])} to {pct(a['ci_high'])}) of {group(a['n_replications'])} replications and the "
                f"stale-volatility model in {pct(b['share_amber_or_red'])}\\,\\% ({pct(b['ci_low'])} to {pct(b['ci_high'])}).")
    if cid == "C14":
        d = load("C14/vd-2022-q4.json")
        return (f"EVE risk measure at 2022-Q4 USD {f2(impact(d, 'eve_risk_measure_behavioural')['value'] / 1e6)} thousand million "
                f"with behavioural deposits, {f2(impact(d, 'eve_risk_measure_contractual')['value'] / 1e6)} contractual; "
                f"{pct(impact(d, 'outlier_ratio_behavioural')['value'])}\\,\\% and "
                f"{pct(impact(d, 'outlier_ratio_contractual')['value'])}\\,\\% of Tier 1 capital (no interval).")
    if cid == "C15":
        d = load("C15/long-uf.json")
        return (f"Long-UF variant: $\\Delta$EVE {group(round(impact(d, 'delta_eve')['value']))} and $\\Delta$NII "
                f"{group(round(impact(d, 'delta_nii')['value']))} million CLP; the indexation charge is {m('pxSevenShare')}\\,\\% "
                f"of the $\\Delta$NII of the short-UF variant (no interval).")
    if cid == "C16":
        d = load("C16/list-adverse.json")
        return (f"Survival period {group(round(impact(d, 'survival_days')['value']))} days under the adverse run-off; the "
                f"run-off multiplier that brings it to {m('pxElevenTarget')} days is {m('pxElevenAdverse')} (no interval).")
    if cid == "C17":
        d = load("C17/xi-0-8.json")
        return (f"Tail index 0.8, 10 years: LDA capital EUR {f1(impact(d, 'lda_capital_999')['value'] / 1e6)} million against SMA "
                f"{f1(impact(d, 'sma_orc')['value'] / 1e6)}; the interquartile range of the LDA capital is {m('pxTwelveIqrMin')} to "
                f"{m('pxTwelveIqrMax')} times the truth over {m('pxTwelveHistories')} histories.")
    if cid == "C18":
        d = load("C18/fed-2026-severely-adverse.json")
        return (f"Severely adverse scenario: CET1 ratio {pct(impact(d, 'cet1_ratio_end_stress')['value'], 2)}\\,\\% of RWA at "
                f"the end of year 3; smallest headroom over the internal target {signed(100 * impact(d, 'oi_headroom_min')['value'], 2)} "
                f"points; the band of aggregation methods is shown with the headline capital (no interval).")
    if cid == "C20":
        d = load("C20/sgcd-seen.json")
        return (f"Largest decision-flip share over the applied shocks {pct(impact(d, 'decision_flip_share')['value'])}\\,\\% "
                f"on the stressed German credit sample; no sampling interval is committed.")
    if cid == "C21":
        d = load("C21/pair-2023-24.json")
        row = next(t for t in d["tests"] if t["test_id"] == "fair.two_proportion_z"
                   and t["segment"].startswith("derived_race|Black or African American vs White"))
        e = row["extras"]
        diff = e["rate_1"] - e["rate_2"]
        se = math.sqrt(e["rate_1"] * (1 - e["rate_1"]) / e["n1"] + e["rate_2"] * (1 - e["rate_2"]) / e["n2"])
        return (f"2023--24 pair: approval rate of Black or African American applicants {pct(e['rate_1'])}\\,\\% against "
                f"{pct(e['rate_2'])}\\,\\% for White applicants, a difference of {signed(100 * diff, 1)} points (95\\,\\% Wald "
                f"interval {signed(100 * (diff - 1.959964 * se), 1)} to {signed(100 * (diff + 1.959964 * se), 1)}).")
    if cid == "C22":
        d = load("C22/null.json")
        bound = d["outputs"]["size_bounds"]["p<0.05"]
        return (f"{group(round(impact(d, 'tests_within_bound')['value']))} of {m('pxOneTests')} tests pass the size screen at 5 and "
                f"1\\,\\%; Hosmer--Lemeshow with $G-2$ degrees of freedom rejects {f3(impact(d, 'size_hl_fitted')['value'])} of null "
                f"validation samples (Monte Carlo bound {f3(bound)}); {m('pxOneRates')} rates carry their standard error.")
    if cid == CASE_WITH_NO_RESULT:
        return "No committed result: the case is planned and the report states none."
    raise KeyError(cid)


# ----------------------------------------------------------------------------------------------------------------------
# tables

def long_table(path: pathlib.Path, header: list[str], rows: list[list[str]], *, spec: str, caption: str, label: str,
               size: str = "footnotesize") -> None:
    lines = [f"{{\\{size}", "\\setlength{\\tabcolsep}{3pt}", "\\renewcommand{\\arraystretch}{1.12}",
             f"\\begin{{longtable}}{{{spec}}}", f"\\caption{{{caption}}}\\label{{{label}}}\\\\", "\\toprule",
             " & ".join(header) + " \\\\", "\\midrule", "\\endfirsthead", "\\toprule", " & ".join(header) + " \\\\", "\\midrule",
             "\\endhead", "\\bottomrule", "\\endfoot"]
    lines += [" & ".join(r) + " \\\\" for r in rows]
    lines += ["\\end{longtable}", "}", ""]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def case_label(c: dict) -> str:
    return f"{c['id']} {esc(c['title'])}"


def opinion_cell(c: dict) -> str:
    if not c["reports"]:
        return "--"
    levels = sorted({r["level"] for r in c["reports"]})
    return str(levels[0]) if len(levels) == 1 else f"{levels[0]} to {levels[-1]}"


def summary_table(data: dict) -> None:
    rows = []
    for c in data["cases"]:
        f = c["findings"]
        sev = [str(f["by_severity"][s]) for s in SEV] if f else ["--"] * 4
        question = esc(c["question"]) if c["manifest"] else "Supervisory stress replication against a published answer."
        rows.append([f"\\textbf{{{c['id']}}} {esc(c['title'])}", question, headline(c), opinion_cell(c)] + sev)
    long_table(OUT / "results-summary.tex",
               ["Case", "Question", "Headline result and its uncertainty", "Op.", "S1", "S2", "S3", "S4"], rows,
               spec=">{\\raggedright\\arraybackslash}p{2.6cm}>{\\raggedright\\arraybackslash}p{3.7cm}"
                    ">{\\raggedright\\arraybackslash}p{5.7cm}rrrrr",
               caption=("Results across the cases of Contraste: for each case the question it asks, the headline result read from its "
                        "committed artifacts with the uncertainty the artifact carries, the opinion level of its validation reports "
                        "(Op., from 1 to 4 on the scale of the euro-area supervisor) and the findings it raised by severity S1 "
                        "(critical) to S4 (minor). Case C19 has no committed result."),
               label="tab:results-summary")


def lights_table(data: dict) -> None:
    rows = []
    for c in data["cases"]:
        if not c["reports"]:
            continue
        tot = {k: sum(r["counts"][k] for r in c["reports"]) for k in ["green", "amber", "red", "not_evaluated"]}
        n = sum(tot.values())
        rows.append([f"{c['id']}", str(len(c["reports"])), opinion_cell(c), group(tot["green"]), group(tot["amber"]),
                     group(tot["red"]), group(tot["not_evaluated"]), pct(tot["red"] / n) if n else "--"])
    long_table(OUT / "results-lights.tex", ["Case", "Reports", "Op.", "Green", "Amber", "Red", "Not evaluated", "Red (\\%)"], rows,
               spec="lrrrrrrr",
               caption=("Test lights in the validation reports of each case, summed over the reports of the case (one report for each model "
                        "fit or default variant): the number of reports, their opinion level, the tests that end green, amber, red and "
                        "not evaluated, and the share of red among all tests of the case."),
               label="tab:results-lights")


def sources_table(data: dict) -> None:
    src = data["sources"]["sources"]
    rows = []
    for s in src:
        used = ", ".join(s["cases"]) if s["cases"] else "no case"
        rows.append([esc(s["name"]), esc(s["class"]), esc(used), esc(s["span"].split(";")[0])])
    long_table(OUT / "results-sources.tex", ["Source", "Licence class", "Cases", "Period or extent"], rows,
               spec=">{\\raggedright\\arraybackslash}p{6.4cm}>{\\raggedright\\arraybackslash}p{2.2cm}"
                    ">{\\raggedright\\arraybackslash}p{2.8cm}>{\\raggedright\\arraybackslash}p{3.0cm}",
               caption=("Every data and scenario source of the research basis, as the source registry of the pipeline declares it: the "
                        "publisher's name of the source, its redistribution class (mirror-allowed, derived-only, link-only or unusable), "
                        "the cases that read it and the period or extent it covers; a source that no case reads was researched and "
                        "classified but is not used."),
               label="tab:data-sources")
    # a source whose published name carries its own version (SGCD-v0.1) is a name, not a version narrative of this report
    path = OUT / "results-sources.tex"
    named = re.compile(r"-v\d+(?:\.\d+)*\)")
    lines = path.read_text(encoding="utf-8").split("\n")
    path.write_text("\n".join(f"{ln} % voice-ok: name of an external dataset" if named.search(ln) and "voice-ok" not in ln else ln
                              for ln in lines), encoding="utf-8", newline="\n")


def cases_table(data: dict) -> None:
    rows = []
    for c in data["cases"]:
        if not c["manifest"]:
            rows.append([c["id"], esc(c["title"]), "published tables", "published answers", "0", "--"])
            continue
        classes = sorted({d["class"] for d in c["source_details"].values()})
        rows.append([c["id"], esc(c["title"]), esc(", ".join(c["sources"])) if c["sources"] else "generator",
                     esc(", ".join(classes)) if classes else "generator", esc(", ".join(t.replace("-", " ") for t in c["truth"])),
                     str(c["variants"])])
    long_table(OUT / "results-cases.tex", ["Case", "Title", "Sources", "Licence class", "Truth status", "Variants"], rows,
               spec="l>{\\raggedright\\arraybackslash}p{4.0cm}>{\\raggedright\\arraybackslash}p{2.9cm}"
                    ">{\\raggedright\\arraybackslash}p{2.2cm}>{\\raggedright\\arraybackslash}p{3.0cm}r",
               caption=("The cases of Contraste with the sources of their manifest, the licence classes of those sources, the truth status of "
                        "the committed variants (real outcomes, synthetic with known truth, synthetic calibrated, or published answer) and "
                        "the number of variants; a case with no source in its manifest runs on a generator or on published tables."),
               label="tab:data-cases")


def sdd_table(header_start: str) -> list[list[str]]:
    """The rows of the markdown table of the design document whose header starts with ``header_start``."""
    lines = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8").splitlines()
    i = next(k for k, line in enumerate(lines) if line.startswith(header_start))
    rows = []
    for line in lines[i + 2:]:
        if not line.startswith("|"):
            break
        rows.append([cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")])
    return rows


def splits_table() -> None:
    rows = [[r[0], esc(r[1]), esc(r[2])] for r in sdd_table("| Case | Variants (the regime each shows)")]
    long_table(OUT / "results-splits.tex", ["Case", "Variants (the regime each shows)", "Leakage-safe split"], rows,
               spec="l>{\\raggedright\\arraybackslash}p{6.2cm}>{\\raggedright\\arraybackslash}p{8.0cm}",
               caption=("The variants of each case and the leakage-safe split that keeps information the model could not have had out of the evaluation, as the design document fixes "
                        "them before development: what the model is trained on, what it is tested on and what is applied to the "
                        "evaluation set only."),
               label="tab:data-splits")


def protocol_table(data: dict) -> None:
    rows = []
    for c in data["cases"]:
        if not c["manifest"]:
            continue
        rows.append([c["id"], str(c["seed"]), esc(c["default"]), str(c["variants"]), group(c["tests"]), group(c["p_tests"])])
    long_table(OUT / "results-protocol.tex", ["Case", "Seed", "Default variant", "Variants", "Test rows", "With a $p$-value"], rows,
               spec="lrlrrr",
               caption=("The protocol of each case as the committed artifacts record it: the seed of the bake, the variant the application "
                        "opens on, the number of variants, the test rows (one result of the engine for each test, model and segment) "
                        "written over all its variants, and how many of those rows are decided by a $p$-value."),
               label="tab:protocol-cases")


def resources_table() -> None:
    """Memory and time of the bakes, read from the measured resource table of the design document."""
    rows = []
    for r in sdd_table("| stage | memory | disk | time | where it runs |"):
        stage = r[0]
        if not stage.startswith(("fetch", "bake")):
            continue
        name = re.split(r"\s*\(", stage)[0]
        what = re.search(r"\(`?([^)]*)", stage)
        mem = re.search(r"[\d.,]+ [MG]B( peak)?", r[1])
        sec = re.search(r"[\d.,]+ s\b", r[3])
        rows.append([esc(name), esc(mem.group(0) if mem else r[1][:30]), esc(sec.group(0) if sec else r[3][:30]), esc(r[4].split(",")[0])])
    long_table(OUT / "results-resources.tex", ["Stage", "Memory", "Wall time", "Where it runs"], rows, spec="lrrl",
               caption=("Memory and wall-clock time of the fetch and of the bake of the cases that the design document measured on the development "
                        "workstation, with the process tree polled every 20 ms; the largest bake is the validation of the validator, whose "
                        "simulations run on eight worker processes."),
               label="tab:protocol-resources")


def versions_table() -> None:
    wanted = ["numpy", "scipy", "pandas", "scikit-learn", "statsmodels", "optbinning", "interpret-core", "lightgbm", "xgboost",
              "catboost", "shap", "torch", "tabpfn", "arch", "mapie", "fairlearn", "networkx", "riskvalidation",
              "open-source-risk-engine", "QuantLib", "pytest", "jsonschema"]
    table = {r[1]: r for r in sdd_table("| component | package | version | use | alternative considered |")}
    rows = []
    for name in wanted:
        r = table[name]
        use = re.split(r"[;(]", r[3])[0].strip().replace("state-of-" + "the-art ", "").replace("adversarial", "negative-control")
        rows.append([esc(name), esc(r[2]), esc(use)])
    long_table(OUT / "results-versions.tex", ["Package", "Pinned version", "Use"], rows,
               spec="lr>{\\raggedright\\arraybackslash}p{9.0cm}",
               caption=("The pinned versions of the numerical, modelling and reference packages that produce the committed artifacts, as the "
                        "technology matrix of the design document records them and a repository check keeps in step with the "
                        "requirements files; the web packages are pinned in the lock file of the front end."),
               label="tab:repro-versions")


# ----------------------------------------------------------------------------------------------------------------------
# macros

def numbers(data: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    cases = data["cases"]
    fnd = data["findings"]["counts"]
    with_result = [c for c in cases if c["manifest"]]
    out["rsCases"] = str(len(cases))
    out["rsCasesResult"] = str(len(with_result))
    out["rsCaseNoResult"] = CASE_WITH_NO_RESULT
    out["rsFindTotal"] = group(fnd["total"])
    for s in SEV:
        out[f"rsFindS{SEV_WORD[s]}"] = group(fnd["by_severity"][s])
    out["rsFindOpen"] = group(fnd["by_status"]["open"])
    out["rsFindAccepted"] = group(fnd["by_status"]["risk_accepted"])
    out["rsFindClosed"] = group(fnd["by_status"]["validated_closed"])
    out["rsFindOverdue"] = group(fnd["overdue"])
    out["rsFindOpenShare"] = pct(fnd["by_status"]["open"] / fnd["total"])
    out["rsFindSTwoShare"] = pct(fnd["by_severity"]["S2"] / fnd["total"])
    out["rsFindSThreeShare"] = pct(fnd["by_severity"]["S3"] / fnd["total"])
    out["rsFindMean"] = f1(fnd["total"] / len(with_result))
    by_case = sorted(with_result, key=lambda c: -c["findings"]["total"])
    for rank, name in zip(range(3), ["First", "Second", "Third"]):
        out[f"rsTop{name}Case"] = by_case[rank]["id"]
        out[f"rsTop{name}Count"] = str(by_case[rank]["findings"]["total"])
    out["rsLeastCase"] = by_case[-1]["id"]
    out["rsLeastCount"] = str(by_case[-1]["findings"]["total"])
    out["rsSecondLeastCase"] = by_case[-2]["id"]
    out["rsSecondLeastCount"] = str(by_case[-2]["findings"]["total"])
    sone = [c["id"] for c in with_result if c["findings"]["by_severity"]["S1"]]
    out["rsSOneCases"] = ", ".join(sone)
    out["rsSOneCaseCount"] = str(len(sone))
    out["rsSOneFirstCase"] = sone[0]
    out["rsSOneFirstCount"] = str(next(c for c in with_result if c["id"] == sone[0])["findings"]["by_severity"]["S1"])
    out["rsSOneSecondCase"] = sone[1] if len(sone) > 1 else ""
    out["rsSOneSecondCount"] = str(next(c for c in with_result if c["id"] == sone[1])["findings"]["by_severity"]["S1"]) if len(sone) > 1 else ""
    # findings by category
    cat: dict[str, int] = {}
    for c in with_result:
        cat[c["category_id"]] = cat.get(c["category_id"], 0) + c["findings"]["total"]
    for k, v in cat.items():
        out[f"rsCat{CATEGORY_MACRO[k]}"] = str(v)
    out["rsCategories"] = str(len(cat))
    # reports and lights
    reps = [r for c in cases for r in c["reports"]]
    out["rsReports"] = str(len(reps))
    for k, name in [("green", "Green"), ("amber", "Amber"), ("red", "Red"), ("not_evaluated", "NotEval")]:
        out[f"rsLights{name}"] = group(sum(r["counts"][k] for r in reps))
    total_tests = sum(sum(r["counts"][k] for k in ["green", "amber", "red", "not_evaluated"]) for r in reps)
    out["rsLightsTotal"] = group(total_tests)
    out["rsLightsRedShare"] = pct(sum(r["counts"]["red"] for r in reps) / total_tests)
    out["rsLightsAmberShare"] = pct(sum(r["counts"]["amber"] for r in reps) / total_tests)
    out["rsLightsGreenShare"] = pct(sum(r["counts"]["green"] for r in reps) / total_tests)
    levels = [c for c in with_result]
    lev = {c["id"]: sorted({r["level"] for r in c["reports"]}) for c in levels}
    three = [k for k, v in lev.items() if v == [3]]
    four = [k for k, v in lev.items() if 4 in v]
    out["rsLevelThreeCases"] = str(len(three))
    out["rsLevelFourCases"] = ", ".join(four)
    out["rsLevelFourCount"] = str(len(four))
    out["rsLevelOneTwo"] = str(sum(1 for r in reps if r["level"] <= 2))
    # red share by case
    red = {c["id"]: sum(r["counts"]["red"] for r in c["reports"]) / max(1, sum(sum(r["counts"][k] for k in ["green", "amber", "red", "not_evaluated"]) for r in c["reports"])) for c in with_result}
    hi = max(red, key=red.get)
    lo = min(red, key=red.get)
    out["rsRedHighCase"] = hi
    out["rsRedHighShare"] = pct(red[hi])
    out["rsRedLowCase"] = lo
    out["rsRedLowShare"] = pct(red[lo])
    zero_red = [k for k, v in red.items() if v == 0]
    out["rsRedZeroCases"] = ", ".join(zero_red)
    out["rsRedZeroCount"] = str(len(zero_red))
    # protocol
    out["rsVariants"] = str(sum(c["variants"] for c in with_result))
    out["rsTestRows"] = group(sum(c["tests"] for c in with_result))
    out["rsPTestRows"] = group(sum(c["p_tests"] for c in with_result))
    out["rsSeedDefault"] = str(max(set(c["seed"] for c in with_result), key=[c["seed"] for c in with_result].count))
    out["rsSeedDefaultCases"] = str([c["seed"] for c in with_result].count(int(out["rsSeedDefault"])))
    first = with_result[0]["engine"]
    out["rsEnginePipeline"] = first["pipeline"]
    out["rsEngineRv"] = first["riskvalidation"]
    out["rsAlphaAmber"] = "0.05"
    out["rsAlphaRed"] = "0.01"
    c01 = next(c for c in with_result if c["id"] == "C01")
    d01 = load("C01/holdout.json")
    out["rsCOneTests"] = str(len(d01["tests"]))
    out["rsCOnePTests"] = str(sum(1 for t in d01["tests"] if t.get("p_value") is not None))
    # sources
    srcs = data["sources"]["sources"]
    out["rsSources"] = str(len(srcs))
    out["rsSourcesUsed"] = str(sum(1 for s in srcs if s["cases"]))
    for cls, name in [("mirror-allowed", "Mirror"), ("derived-only", "Derived"), ("link-only", "Link"), ("unusable", "Unusable")]:
        out[f"rsSources{name}"] = str(sum(1 for s in srcs if s["class"] == cls))
        out[f"rsSourcesUsed{name}"] = str(sum(1 for s in srcs if s["class"] == cls and s["cases"]))
    out["rsSourcesResearched"] = data["sources"]["researched"]
    # checksums
    sums = (DERIVED / "governance" / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    table = {line.split()[1]: line.split()[0] for line in sums if line.strip()}
    actual = hashlib.sha256((DERIVED / "governance" / "findings.json").read_bytes()).hexdigest()
    out["rsShaEntries"] = str(len(table))
    out["rsShaFindings"] = table["governance/findings.json"]
    out["rsShaFindingsMatch"] = "matches" if actual == table["governance/findings.json"] else "DIFFERS FROM"
    out["rsShaFindingsShort"] = table["governance/findings.json"][:16]
    ok = sum(1 for rel, h in table.items() if (DERIVED / rel).is_file() and hashlib.sha256((DERIVED / rel).read_bytes()).hexdigest() == h)
    out["rsShaMatching"] = str(ok)
    # versions of the design document
    text = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    py = re.search(r"Python (\d+\.\d+\.\d+) on the\s+development workstation and (\d+\.\d+) in CI, and Node (\d+) in\s+CI \((\d+\.\d+\.\d+) on the workstation\)", text)
    out["rsPythonDev"] = py.group(1)
    out["rsPythonCi"] = py.group(2)
    out["rsNodeCi"] = py.group(3)
    out["rsNodeDev"] = py.group(4)
    for key, pat in [("rsPytest", r"\(`pytest tests`, ([\d,]+) tests collected"), ("rsAdversarial", r"`pytest tests/adversarial`, (\d+) tests collected"),
                     ("rsVitest", r"`npm test` in `frontend/`, (\d+) files, ([\d,]+) tests")]:
        mm = re.search(pat, text)
        out[key] = (mm.group(mm.lastindex).replace(",", "{,}") if mm else "??")
    ram = re.search(r"(\d+) GB of RAM", text)
    out["rsRamGb"] = ram.group(1)
    for key, src in [("rsOneTests", "pxOneTests"), ("rsOneRates", "pxOneRates"), ("rsOneSims", "pxOneSims"), ("rsOneReps", "pxOneReps"),
                     ("rsThirteenPower", "pxThirteenPowerRate"), ("rsThirteenPowerCi", "pxThirteenPower"), ("rsThirteenCiLo", "pxThirteenCiLo"), ("rsThirteenCiHi", "pxThirteenCiHi"), ("rsThirteenPla", "pxThirteenPla"), ("rsThirteenN", "pxThirteenN")]:
        out[key] = MACROS[src]
    out["rsProductVersion"] = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    # splits and contract counts
    out["rsContracts"] = str(len(json.loads((HERE.parent / "coverage.json").read_text(encoding="utf-8"))["contracts"]))
    out["rsMethodRows"] = str(len(json.loads((HERE.parent / "coverage.json").read_text(encoding="utf-8"))["methods"]))
    return out


def case_numbers() -> dict[str, str]:
    """Numbers of single cases that the prose of the results section reads, from the same artifacts as the headline cells."""
    o: dict[str, str] = {}
    d = load("C03/fy2008-10.json")
    row = next(r for r in d["outputs"]["rung_comparison"] if r["rung_id"] == "P1-scorecard")
    o["rsCThreeAuc"] = f3(row["auc"])
    lgb = next(r for r in d["outputs"]["rung_comparison"] if r["rung_id"] == "P4-lightgbm")
    ebm = next(r for r in d["outputs"]["rung_comparison"] if r["rung_id"] == "P3-ebm")
    o["rsCThreeLgbAuc"], o["rsCThreeLgbLo"], o["rsCThreeLgbHi"] = f3(lgb["auc"]), f3(lgb["auc_ci_low"]), f3(lgb["auc_ci_high"])
    o["rsCThreeEbmAuc"] = f3(ebm["auc"])
    o["rsCThreeAucLo"], o["rsCThreeAucHi"] = f3(row["auc_ci_low"]), f3(row["auc_ci_high"])
    o["rsCThreeObs"] = pct(impact(d, "observed_5y_pd")["value"])
    o["rsCThreePred"] = pct(impact(d, "predicted_5y_pd")["value"])
    d = load("C05/sp-2010.json")
    rw = [v["value"] for k, v in d["impact"].items() if k.startswith("rw_") and v["unit"] == "share of EAD"]
    o["rsCFiveRwMin"], o["rsCFiveRwMax"], o["rsCFiveApproaches"] = pct(min(rw)), pct(max(rw)), str(len(rw))
    d = load("C07/base.json")
    o["rsCSevenRatio"] = f2(impact(d, "ifrs9_over_b1")["value"])
    d = load("C09/level-3.json")
    rows = {r["design"]: r for r in d["outputs"]["ccf_by_design"]["rows"] if r["treatment"] == "none" and r["estimator"] == "pooled"}
    o["rsCNineFixed"] = signed(rows["fixed-horizon"]["bias"])
    o["rsCNineCohort"] = signed(rows["cohort"]["bias"])
    o["rsCNineVariable"] = signed(rows["variable-horizon"]["bias"])
    o["rsCNineTruth"] = f3(impact(d, "true_ccf")["value"])
    a = load("C13/missing-basis.json")["outputs"]["detection"]
    b = load("C13/stale-volatility.json")["outputs"]["detection"]
    o["rsCThirteenMissing"], o["rsCThirteenStale"] = pct(a["share_amber_or_red"]), pct(b["share_amber_or_red"])
    d = load("C14/vd-2022-q4.json")
    o["rsCFourteenBeh"] = pct(impact(d, "outlier_ratio_behavioural")["value"])
    o["rsCFourteenCon"] = pct(impact(d, "outlier_ratio_contractual")["value"])
    d = load("C17/xi-0-8.json")
    o["rsCSeventeenLda"] = f1(impact(d, "lda_capital_999")["value"] / 1e6)
    o["rsCSeventeenSma"] = f1(impact(d, "sma_orc")["value"] / 1e6)
    d = load("C18/fed-2026-severely-adverse.json")
    o["rsCEighteenCet"] = pct(impact(d, "cet1_ratio_end_stress")["value"], 2)
    o["rsCEighteenHead"] = signed(100 * impact(d, "oi_headroom_min")["value"], 2)
    d = load("C20/sgcd-seen.json")
    o["rsCTwentyFlip"] = pct(impact(d, "decision_flip_share")["value"])
    d = load("C22/null.json")
    o["rsCTwentyTwoWithin"] = str(round(impact(d, "tests_within_bound")["value"]))
    o["rsCTwentyTwoHl"] = f3(impact(d, "size_hl_fitted")["value"])
    o["rsCTwentyTwoNormal"] = f3(impact(d, "size_normal")["value"])
    o["rsCTwentyTwoPsi"] = f3(impact(d, "psi010_false_alarm_n100")["value"])
    o["rsCTwentyTwoBound"] = f3(d["outputs"]["size_bounds"]["p<0.05"])
    # the two tests that do not hold their size, found by the rule of the pipeline (exact probability where one exists,
    # otherwise the one-sided Monte Carlo bound), and checked against the count the artifact reports
    bounds = d["outputs"]["size_bounds"]
    nulls = [s for s in d["outputs"]["simulations"] if s["key"].endswith("@null") and not s.get("study")]
    failing = [s for s in nulls if not all(
        (s["exact"][lv] <= float(lv[2:]) + 1e-12) if s["exact"] is not None else (s["rates"][lv]["rate"] <= bounds[lv])
        for lv in ("p<0.05", "p<0.01"))]
    assert len(nulls) - len(failing) == round(impact(d, "tests_within_bound")["value"]), "the failing tests differ from the artifact count"
    assert sorted(s["test_id"] for s in failing) == ["pd.jeffreys", "pd.normal_multiperiod"], [s["test_id"] for s in failing]
    jef = next(s for s in failing if s["test_id"] == "pd.jeffreys")
    nor = next(s for s in failing if s["test_id"] == "pd.normal_multiperiod")
    o["rsCTwentyTwoJeffExactOne"] = f3(jef["exact"]["p<0.01"])
    o["rsCTwentyTwoNormalOne"] = f3(nor["rates"]["p<0.01"]["rate"])
    o["rsCTwentyTwoBoundOne"] = f3(bounds["p<0.01"])
    o["rsCTwentyTwoNullReps"] = f"{sum(s['n_rep'] for s in nulls):,}".replace(",", "{,}")
    o["rsCTwentyTwoNullPerTest"] = f"{nulls[0]['n_rep']:,}".replace(",", "{,}")
    o["rsCTwentyTwoWithinFive"] = str(sum(1 for s in nulls if (s["exact"][ "p<0.05"] <= 0.05 + 1e-12 if s["exact"] is not None else s["rates"]["p<0.05"]["rate"] <= bounds["p<0.05"])))
    d = load("C21/pair-2023-24.json")
    row = next(t for t in d["tests"] if t["test_id"] == "fair.two_proportion_z" and t["segment"].startswith("derived_race|Black or African American vs White"))
    e = row["extras"]
    o["rsCTwentyOneBlack"], o["rsCTwentyOneWhite"] = pct(e["rate_1"]), pct(e["rate_2"])
    o["rsCTwentyOneRed"] = str(sum(1 for t in d["tests"] if t["light"] == "red"))
    o["rsCTwentyOneTests"] = str(len(d["tests"]))
    return o


def write_numbers(vals: dict[str, str]) -> None:
    lines = ["% Generated by tables/make_results.py from data/derived, data-pipeline/config/sources.json and docs/design/SDD.md; "
             "do not edit.", ""]
    for k in sorted(vals):
        lines.append(f"\\newcommand{{\\{k}}}{{{vals[k]}}}")
    (OUT / "results-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    data = derive()
    summary_table(data)
    lights_table(data)
    sources_table(data)
    cases_table(data)
    splits_table()
    protocol_table(data)
    versions_table()
    resources_table()
    vals = numbers(data)
    vals.update(case_numbers())
    write_numbers(vals)
    print(f"wrote {len(vals)} macros and 8 table files into {OUT}")


if __name__ == "__main__":
    main()
