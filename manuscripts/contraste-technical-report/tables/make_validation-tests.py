"""Tables and in-text numbers of the validation-tests section of the technical report (sections/16-validation-tests.tex).

Every number the section prints is produced here from the committed documents of cases C20, C21 and C22
(``data/derived``), from the test catalogue and the policy rows of the installed ``riskvalidation`` engine, or, for the
planted-defect studies of the machine-learning and fairness tests that no document carries, from the measured tables of the
engine's own documentation (``--engine-docs``). Nothing is typed in the LaTeX. The script writes

* ``tables/validation-tests-<name>.tex``: one booktabs ``table`` environment per result table (``figkit.table``);
* ``tables/validation-tests-numbers.tex``: one ``\\newcommand`` per number the prose quotes (``\\vt...``).

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_validation-tests.py \
        --engine-docs <riskvalidation repository>/docs

Without ``--engine-docs`` (or the environment variable ``RISKVALIDATION_DOCS``) the two tables read from the engine's
documentation are left as they are. ``--registry <file.json>`` also writes every macro with its value and its source.
The figure script ``figures/make_validation-tests.py`` imports ``load`` and the helpers of this module.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import os
import pathlib
import re
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

OUT = HERE
C22 = "data/derived/C22"
C20 = "data/derived/C20"
C21 = "data/derived/C21"

#: the C22 variant documents the section reads
C22_FILES = ("null", "miscalibration", "clustering", "drift", "discrimination-decay", "leakage", "concentration",
             "broken-monotonicity", "other-families")
C20_FILES = ("sgcd-seen", "sgcd-held-out", "fed-shift", "perturbation-grid", "seed-sweep", "leakage-planted")
C21_PAIRS = ("2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24")

#: the families of the catalogue that each method covers (the registry's own family names)
M28_FAMILIES = (("pd-calibration", "Calibration of the probability of default"), ("discrimination", "Discriminatory power"),
                ("stability", "Population and characteristic stability"), ("rating-system", "Rating-system stability"),
                ("transitions", "Rating migrations over time"))
M29_FAMILIES = (("ml", "Machine-learning model validation"), ("fairness", "Fairness and disparity"))

TEST_LABEL = {
    "pd.binomial": "Binomial", "pd.jeffreys": "Jeffreys", "pd.binomial_vasicek": "Vasicek-corrected binomial",
    "pd.chi2_grades": "Chi-square over grades", "pd.default_profile": "Default profile", "pd.hosmer_lemeshow": "Hosmer-Lemeshow",
    "pd.spiegelhalter": "Spiegelhalter", "pd.normal_multiperiod": "Normal, several years", "pd.traffic_lights": "Traffic lights",
    "disc.auc_vs_initial": "AUC against development", "disc.delong": "DeLong", "stability.psi": "PSI",
    "stability.csi": "CSI", "stability.chi2": "Chi-square homogeneity", "stability.ks": "Kolmogorov-Smirnov",
    "rating.migration_ztests": "Migration z-tests", "rating.hhi": "Concentration (ECB)", "rating.time_homogeneity": "Time homogeneity",
    "rating.markov_order": "Markov order", "rating.matrix_reference": "Matrix against reference", "rating.momentum": "Momentum",
}

BS = chr(92)
REG: list[tuple[str, str, str]] = []  # (macro, value, source)


def load(rel: str) -> Any:
    return figkit.doc(rel)


def c22(name: str) -> dict:
    return load(f"C22/{name}.json")


def pct(x: float, d: int = 2) -> str:
    return f"{100 * x:.{d}f}"


def rate_cell(r: dict, d: int = 2) -> str:
    """A rejection rate with its Monte Carlo standard error, in percent."""
    return f"${100 * r['rate']:.{d}f}\\pm{100 * r['se']:.{d}f}$"


def sim_index(doc: dict) -> dict[str, dict]:
    return {s["key"]: s for s in doc["outputs"]["simulations"]}


def r05(s: dict) -> dict:
    return s["rates"]["p<0.05"]


def emit(path, header, rows, **kw):
    """figkit.table, then a smaller type size and a tighter column gap so that the table fits the text width."""
    figkit.table(path, header, rows, **kw)
    txt = path.read_text(encoding="utf-8")
    txt = txt.replace(BS + "small", BS + "footnotesize", 1).replace(BS + "centering", BS + "centering" + chr(10) + BS + "setlength{" + BS + "tabcolsep}{3pt}", 1)
    path.write_text(txt, encoding="utf-8", newline=chr(10))


def fn(name: str) -> str:
    """An identifier in a breakable monospace form (a cell starting with a backslash is not escaped)."""
    return BS + "nolinkurl{" + name + "}"


def idcell(text: str) -> str:
    """A leading identifier of a table cell in monospace, the rest as plain escaped text."""
    head, _, rest = text.partition(" ")
    return fn(head) + (" " + figkit.tex_escape(rest) if rest else "")


def macro(name: str, value: Any, source: str) -> None:
    # a control sequence holds letters only: the digits of a name are spelled
    words = 'Zero One Two Three Four Five Six Seven Eight Nine'.split()
    name = re.sub(r'\d', lambda m: words[int(m.group())], name)
    REG.append((name, str(value), source))


def num(x: float, d: int = 4) -> str:
    return f"{x:.{d}f}"


def write_numbers() -> None:
    lines = ["% Generated by tables/make_validation-tests.py: one macro per number the section quotes. Do not edit.",
             "\\makeatletter"]
    for name, value, _ in REG:
        lines.append(f"\\providecommand{{\\{name}}}{{{value}}}")
    lines.append("\\makeatother")
    (OUT / "validation-tests-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- the catalogue and the policy rows


def catalogue_stats() -> dict:
    import riskvalidation
    import riskvalidation.validation  # noqa: F401  (registers every test)
    from riskvalidation.core import registry

    specs = registry.catalogue()
    fam = collections.defaultdict(lambda: [0, 0])
    for s in specs:
        fam[s.family][0] += 1
        if s.decision == "p_value":
            fam[s.family][1] += 1
    return {"version": riskvalidation.__version__, "total": len(specs), "families": len({s.family for s in specs}),
            "p_total": sum(1 for s in specs if s.decision == "p_value"), "fam": dict(fam), "ids": {s.test_id for s in specs}}


def table_catalogue(cat: dict) -> None:
    rows = []
    for group, title in (("M28", M28_FAMILIES), ("M29", M29_FAMILIES)):
        for fam, label in title:
            n, p = cat["fam"][fam]
            rows.append([label, fn(fam), n, p, n - p])
    n28 = sum(cat["fam"][f][0] for f, _ in M28_FAMILIES)
    n29 = sum(cat["fam"][f][0] for f, _ in M29_FAMILIES)
    macro("vtCatTotal", cat["total"], "riskvalidation.core.registry.catalogue()")
    macro("vtCatFamilies", cat["families"], "riskvalidation.core.registry.catalogue()")
    macro("vtCatPValue", cat["p_total"], "riskvalidation.core.registry.catalogue()")
    macro("vtCatClassic", n28, "registry families " + ",".join(f for f, _ in M28_FAMILIES))
    macro("vtCatMl", n29, "registry families ml, fairness")
    macro("vtEngineVersion", cat["version"], "riskvalidation.__version__")
    for fam, label in M28_FAMILIES + M29_FAMILIES:
        key = "vtFam" + "".join(w.capitalize() for w in re.split(r"[-_]", fam))
        macro(key, cat["fam"][fam][0], "registry family " + fam)
    emit(OUT / "validation-tests-catalogue.tex", ["Family", "Registry name", "Tests", "With a p-value", "Descriptive or metric"], rows,
                 caption=(f"The tests of the catalogue that the two methods of this section cover, by registry family, in the engine "
                          f"\\texttt{{riskvalidation}} {cat['version']}: the number of tests registered, of which a p-value decides the light and "
                          "of which a metric against a policy cut point decides it. The remaining families of the catalogue belong to the "
                          "methods of the other sections."),
                 label="tab:vt-catalogue", align="llrrr")


def policy_rows() -> list[tuple[str, dict]]:
    from riskvalidation.fairness.policy import FAIR_ROWS
    from riskvalidation.ml.policy import threshold_rows

    out = []
    for k, v in threshold_rows().items():
        out.append((k, {"kind": v["kind"], "amber": v["amber"], "red": v["red"]}))
    for k, v in FAIR_ROWS.items():
        out.append((k, {"kind": v.kind, "amber": v.amber, "red": v.red}))
    return out


def sci(x: float) -> str:
    """A small number as math with a power of ten."""
    m, e = f"{x:.1e}".split("e")
    return "$" + m + r"\times10^{" + str(int(e)) + "}$"


def sym(text: str) -> str:
    """A cell with a comparison sign: words in text mode, the sign in math mode (a cell starting with a backslash is not escaped)."""
    parts = text.split(">")
    return r"\mbox{" + r"}$>$\mbox{".join(figkit.tex_escape(p) for p in parts) + "}"


def zc(v: float) -> str:
    return f"${v:+.2f}$"


def clean_cut(x: float) -> str:
    if x >= 1e11 or 1.9999 <= x <= 2.0001:
        return "never"
    r = float(f"{x:.6g}")
    if r != 0 and abs(r) < 1e-4:
        return sci(r)
    return f"{r:g}"


def table_policy() -> None:
    rows = []
    for k, v in policy_rows():
        a, r = clean_cut(v["amber"]), clean_cut(v["red"])
        rows.append([fn(k), v["kind"].replace("_", " "), a, r])
    macro("vtPolicyRows", len(rows), "riskvalidation.ml.policy.threshold_rows, riskvalidation.fairness.policy.FAIR_ROWS")
    emit(OUT / "validation-tests-policy.tex", ["Test", "Rule", "Amber cut", "Red cut"], rows,
                 caption=("The policy rows that turn the statistic of each machine-learning and fairness test into a light, read from the "
                          "engine's packaged policy: a p-value rule colours a test amber below its first cut and red below its second; an "
                          "upper-bad rule colours it at or above the cut (strictly above where the engine stores the next float); a lower-bad "
                          "rule colours it at or below the cut. A cut shown as never is a sentinel outside the range of the metric."),
                 label="tab:vt-policy", align="llrr")


# --------------------------------------------------------------------------- the published studies rerun


def golden_cells() -> dict[str, dict]:
    out = {}
    for name in ("clustering", "drift", "leakage"):
        for g in c22(name)["outputs"]["golden"]:
            out[g["study"]] = g
    return out


def table_published(G: dict) -> list[dict]:
    wp, yn, dm = G["bcbs-wp14"], G["yurdakul-naranjo-2020"], G["demler-2012"]
    rows = []
    # WP14: by table and test
    grp = collections.defaultdict(list)
    for c in wp["cells"]:
        kind = "normal" if "normal" in c["row"] else "traffic lights"
        grp[(c["table"], kind)].append(c)
    for (tab, kind), cells in sorted(grp.items()):
        zs = [c["z"] for c in cells]
        rows.append([f"WP14 {tab}", kind, wp["runs_published"], len(cells), sum(c["agrees"] for c in cells), max(abs(z) for z in zs),
                     zc(sum(zs) / len(zs))])
    grp = collections.defaultdict(list)
    for c in yn["cells"]:
        rule = c["column"].split(", ")[1]
        grp[rule].append(c)
    for rule, cells in sorted(grp.items()):
        zs = [c["z"] for c in cells]
        rows.append(["Yurdakul and Naranjo Table 4", sym(rule), yn["runs_published"], len(cells),
                     sum(c["agrees"] for c in cells), max(abs(z) for z in zs), zc(sum(zs) / len(zs))])
    for c in dm["cells"]:
        rows.append(["Demler et al. section 2.3", "DeLong, nested", dm["runs_published"], 1, int(c["agrees"]), abs(c["z"]), zc(c["z"])])
    macro("vtWpAgree", wp["agree"], "data/derived/C22/clustering.json outputs.golden[bcbs-wp14].agree")
    macro("vtWpTotal", wp["total"], "data/derived/C22/clustering.json outputs.golden[bcbs-wp14].total")
    macro("vtWpRuns", f"{wp['runs_published']:,}".replace(",", "{,}"), "golden runs_published")
    macro("vtYnAgree", yn["agree"], "data/derived/C22/drift.json outputs.golden[yurdakul-naranjo-2020].agree")
    macro("vtYnTotal", yn["total"], "outputs.golden total")
    macro("vtYnRuns", f"{yn['runs_published']:,}".replace(",", "{,}"), "golden runs_published")
    macro("vtDmRuns", f"{dm['runs_published']:,}".replace(",", "{,}"), "golden runs_published")
    macro("vtDmPublished", f"{dm['cells'][0]['published']:.3f}", "data/derived/C22/leakage.json demler cell published")
    macro("vtDmMeasured", f"{dm['cells'][0]['measured']:.3f}", "demler cell measured")
    nn = [c for c in wp["cells"] if "normal" in c["row"]]
    tl = [c for c in wp["cells"] if "traffic" in c["row"]]
    macro("vtWpNormalAgree", sum(c["agrees"] for c in nn), "cells whose row names the normal test")
    macro("vtWpNormalTotal", len(nn), "cells whose row names the normal test")
    macro("vtWpTrafficAgree", sum(c["agrees"] for c in tl), "cells whose row names the traffic-lights test")
    macro("vtWpTrafficTotal", len(tl), "cells whose row names the traffic-lights test")
    inner = [c for c in yn["cells"] if 0 < c["published"] < 1 and 0 < c["measured"] < 1]
    macro("vtYnMeanZ", f"{sum(c['z'] for c in inner) / len(inner):+.2f}".replace("+", "$+$"), "mean z of the Yurdakul-Naranjo cells strictly between 0 and 1")
    macro("vtYnInner", len(inner), "Yurdakul-Naranjo cells strictly between 0 and 1")
    per_rule = len(yn["cells"]) // 3
    macro("vtYnSeOfMean", f"{1 / math.sqrt(per_rule):.2f}", "1/sqrt(cells per rule): the standard error of a mean z of 0 over one rule's independent cells")
    emit(OUT / "validation-tests-published.tex",
                 ["Published study", "Test or rule", "Published runs", "Cells", "Agree", "Largest $|z|$", "Mean $z$"], rows,
                 caption=("The published simulation studies rerun by the product, cell by cell: for each table of each study and each test or rule, "
                          "the number of runs the authors report, the number of published rates, the number that agree with the rerun within the pooled "
                          "two-sample bound of 3.29 standard errors, the largest absolute standardised difference and its mean sign."),
                 label="tab:vt-published", align="llrrrrr", digits=2)
    dis = []
    for study, g in (("WP14", wp), ("Yurdakul and Naranjo", yn)):
        for c in g["cells"]:
            if not c["agrees"]:
                dis.append([study, sym(c["table"] + ", " + c["row"]), sym(c["column"]), c["published"],
                            c["measured"], zc(c["z"])])
    emit(OUT / "validation-tests-disagree.tex", ["Study", "Row", "Column", "Published", "Rerun", "$z$"], dis,
                 caption=("The cells of the published studies on which the rerun and the printed rate differ by more than 3.29 pooled standard errors, "
                          "with the printed rate, the rate of the rerun and the standardised difference; every other cell of the three studies agrees."),
                 label="tab:vt-disagree", align="lllrrr", digits=4)
    return dis


# --------------------------------------------------------------------------- size and power on planted defects


def table_size() -> None:
    d = c22("null")
    S = d["outputs"]["simulations"]
    rows = []
    wanted = [s for s in S if s["panel"] in ("calibration", "discrimination", "stability", "rating", "transitions")]
    for s in wanted:
        lab = TEST_LABEL.get(s["test_id"], s["test_id"])
        ex = s["exact"]["p<0.05"] if s.get("exact") else None
        rows.append([lab, s["scenario"]["en"], rate_cell(r05(s)), rate_cell(s["rates"]["p<0.01"]), "--" if ex is None else pct(ex)])
    b5, b1 = d["outputs"]["size_bounds"]["p<0.05"], d["outputs"]["size_bounds"]["p<0.01"]
    macro("vtBoundFive", pct(b5, 2), "data/derived/C22/null.json outputs.size_bounds[p<0.05]")
    macro("vtBoundOne", pct(b1, 2), "outputs.size_bounds[p<0.01]")
    macro("vtNullReps", f"{wanted[0]['n_rep']:,}".replace(",", "{,}"), "simulations[0].n_rep")
    macro("vtHoldSize", int(d["impact"]["tests_within_bound"]["value"]), "impact.tests_within_bound")
    macro("vtHoldSizeOf", 21, "impact.tests_within_bound label (of 21)")
    macro("vtNormalSize", pct(d["impact"]["size_normal"]["value"], 2), "impact.size_normal")
    macro("vtHlFittedSize", pct(d["impact"]["size_hl_fitted"]["value"], 2), "impact.size_hl_fitted")
    macro("vtPsiAlarm", pct(d["impact"]["psi010_false_alarm_n100"]["value"], 1), "impact.psi010_false_alarm_n100")
    idx = sim_index(d)
    macro("vtHlSize", pct(r05(idx["pd.hosmer_lemeshow@null"])["rate"], 2), "null.json pd.hosmer_lemeshow@null")
    macro("vtAucInitSize", pct(r05(idx["disc.auc_vs_initial@null"])["rate"], 2), "null.json disc.auc_vs_initial@null")
    macro("vtAucInitDevOne", pct(r05(idx["disc.auc_vs_initial@dev1"])["rate"], 2), "null.json disc.auc_vs_initial@dev1")
    macro("vtAucInitExt", pct(r05(idx["disc.auc_vs_initial@dev1-extended"])["rate"], 2), "null.json disc.auc_vs_initial@dev1-extended")
    macro("vtMigSize", pct(r05(idx["rating.migration_ztests@null"])["rate"], 2), "null.json rating.migration_ztests@null")
    macro("vtTlLowerSize", pct(r05(idx["pd.traffic_lights@null"])["rate"], 2), "null.json pd.traffic_lights@null")
    macro("vtTlLowerExact", pct(idx["pd.traffic_lights@null"]["exact"]["p<0.05"], 2), "null.json exact")
    macro("vtTlUpperExact", pct(idx["pd.traffic_lights@upper"]["exact"]["p<0.05"], 2), "null.json exact")
    macro("vtTlUpperSize", pct(r05(idx["pd.traffic_lights@upper"])["rate"], 2), "null.json pd.traffic_lights@upper")
    macro("vtBinomExact", pct(idx["pd.binomial@null"]["exact"]["p<0.05"], 2), "null.json exact")
    macro("vtJeffreysExact", pct(idx["pd.jeffreys@null"]["exact"]["p<0.05"], 2), "null.json exact")
    macro("vtVasicekExact", pct(idx["pd.binomial_vasicek@null"]["exact"]["p<0.05"], 2), "null.json exact")
    macro("vtChiThin", pct(r05(idx["pd.chi2_grades@thin"])["rate"], 2), "null.json pd.chi2_grades@thin")
    macro("vtPsiSmallRule", pct(r05(idx["stability.psi@n100"])["rate"], 2), "null.json stability.psi@n100 (benchmark at 5%)")
    est = d["outputs"]["estimators"]["auc"]
    macro("vtAucCover", f"{100 * est['coverage']:.1f}", "outputs.estimators.auc.coverage")
    macro("vtAucBias", f"{est['bias']:.4f}", "outputs.estimators.auc.bias")
    macro("vtAucEmpSe", f"{est['empirical_se']:.4f}", "outputs.estimators.auc.empirical_se")
    macro("vtAucModelSe", f"{est['model_se']:.4f}", "outputs.estimators.auc.model_se")
    macro("vtAucExactSe", f"{est['exact_se']:.4f}", "outputs.estimators.auc.exact_se")
    emit(OUT / "validation-tests-size.tex", ["Test", "Null scenario", "Size at 5\\% (\\%)", "Size at 1\\% (\\%)", "Exact at 5\\% (\\%)"], rows,
                 caption=(f"The size of the tests of the catalogue on data whose null holds at its boundary, from {wanted[0]['n_rep']:,} independent "
                          "repetitions: the rejection rate at the 5 and 1 percent levels with its Monte Carlo standard error, and the exact rejection "
                          f"probability where the test has one. The size bound at 5 percent is {pct(b5, 2)} percent and at 1 percent {pct(b1, 2)} percent."),
                 label="tab:vt-size", align="lp{4.4cm}rrr")


def table_settings() -> None:
    d = c22("null")
    idx = sim_index(d)
    pairs = [
        ("pd.hosmer_lemeshow@null", "pd.hosmer_lemeshow@fitted", "Hosmer-Lemeshow", "$G$ degrees of freedom", "$G-2$ degrees of freedom"),
        ("pd.traffic_lights@null", "pd.traffic_lights@upper", "Traffic lights", "printed tie rule", "tie rule of the WP14 simulation"),
        ("pd.chi2_grades@null", "pd.chi2_grades@thin", "Chi-square over grades", "five or more expected defaults per grade",
         "best grade expecting 0.6 defaults"),
        ("disc.auc_vs_initial@null", "disc.auc_vs_initial@dev1", "AUC against development", "development AUC known",
         "development AUC estimated on an equal sample"),
        ("disc.auc_vs_initial@dev1", "disc.auc_vs_initial@dev1-extended", "AUC against development (estimated reference)",
         "ECB variance", "variance of both AUCs"),
    ]
    rows = []
    for a, b, lab, ta, tb in pairs:
        rows.append([lab, ta, rate_cell(r05(idx[a])), tb, rate_cell(r05(idx[b]))])
    emit(OUT / "validation-tests-settings.tex", ["Test", "Setting A", "Size A (\\%)", "Setting B", "Size B (\\%)"], rows,
                 caption=("Five choices of definition that change the size of a test, each measured on one generator: the degrees of freedom of the "
                          "Hosmer-Lemeshow statistic, the tie rule of the traffic-lights colours, the expected defaults of the thinnest grade, the "
                          "treatment of the development AUC, and the variance used when it is estimated. Rates at the 5 percent level, in percent, with their standard error."),
                 label="tab:vt-settings", align="p{2.8cm}p{2.4cm}rp{2.8cm}r")


def table_miscal() -> None:
    d = c22("miscalibration")
    idx = sim_index(d)
    ks = ["k1", "k1.1", "k1.25", "k1.5", "k2", "k3"]
    tests = ["pd.binomial", "pd.jeffreys", "pd.binomial_vasicek", "pd.chi2_grades", "pd.default_profile", "pd.hosmer_lemeshow",
             "pd.spiegelhalter", "pd.normal_multiperiod", "pd.traffic_lights"]
    rows = []
    for t in tests:
        rows.append([TEST_LABEL[t]] + [rate_cell(r05(idx[f"{t}@{k}"]), 1) for k in ks])
    macro("vtMisReps", f"{idx['pd.binomial@k1.1']['n_rep']:,}".replace(",", "{,}"), "miscalibration.json n_rep")
    macro("vtPowSpieg125", pct(r05(idx["pd.spiegelhalter@k1.25"])["rate"], 1), "miscalibration.json pd.spiegelhalter@k1.25")
    macro("vtPowHl125", pct(r05(idx["pd.hosmer_lemeshow@k1.25"])["rate"], 1), "miscalibration.json pd.hosmer_lemeshow@k1.25")
    macro("vtPowBin125", pct(r05(idx["pd.binomial@k1.25"])["rate"], 1), "miscalibration.json pd.binomial@k1.25")
    macro("vtPowBin125Exact", pct(idx["pd.binomial@k1.25"]["exact"]["p<0.05"], 1), "miscalibration.json exact")
    macro("vtPowJef125", pct(r05(idx["pd.jeffreys@k1.25"])["rate"], 1), "miscalibration.json pd.jeffreys@k1.25")
    macro("vtPowNormal125", pct(r05(idx["pd.normal_multiperiod@k1.25"])["rate"], 1), "miscalibration.json pd.normal_multiperiod@k1.25")
    macro("vtPowTl125", pct(r05(idx["pd.traffic_lights@k1.25"])["rate"], 1), "miscalibration.json pd.traffic_lights@k1.25")
    macro("vtPowTl125Exact", pct(idx["pd.traffic_lights@k1.25"]["exact"]["p<0.05"], 1), "miscalibration.json exact")
    macro("vtPowVas3", pct(r05(idx["pd.binomial_vasicek@k3"])["rate"], 1), "miscalibration.json pd.binomial_vasicek@k3")
    macro("vtPowVas2", pct(r05(idx["pd.binomial_vasicek@k2"])["rate"], 1), "miscalibration.json pd.binomial_vasicek@k2")
    macro("vtPowProfile15", pct(r05(idx["pd.default_profile@k1.5"])["rate"], 1), "miscalibration.json pd.default_profile@k1.5")
    macro("vtPowChi125", pct(r05(idx["pd.chi2_grades@k1.25"])["rate"], 1), "miscalibration.json pd.chi2_grades@k1.25")
    cmp = [(s["key"], s["exact"]["p<0.05"], r05(s)["rate"], r05(s)["se"]) for s in d["outputs"]["simulations"] if s.get("exact")]
    emit(OUT / "validation-tests-miscal.tex", ["Test", "$\\kappa=1$", "1.1", "1.25", "1.5", "2", "3"], rows,
                 caption=("The power of the calibration tests at the 5 percent level, in percent with the Monte Carlo standard error, when every "
                          "grade's true default probability is the probability applied multiplied by the factor $\\kappa$ in the column heading "
                          "(the first column, $\\kappa=1$, is the null). The Vasicek-corrected binomial test is run at the correlation of the generator "
                          "assumed and true."),
                 label="tab:vt-miscal", align="lrrrrrr")
    macro("vtExactCmpN", len(cmp), "miscalibration.json simulations with an exact probability")


def table_cluster() -> None:
    d = c22("clustering")
    idx = sim_index(d)
    rhos = ["rho0", "rho0.02", "rho0.05", "rho0.1", "rho0.15", "rho0.2"]
    tests = ["pd.binomial", "pd.jeffreys", "pd.binomial_vasicek", "pd.chi2_grades", "pd.hosmer_lemeshow", "pd.spiegelhalter",
             "pd.normal_multiperiod", "pd.traffic_lights"]
    rows = []
    for t in tests:
        rows.append([TEST_LABEL[t]] + [rate_cell(r05(idx[f"{t}@{r}"]), 1) for r in rhos])
    ex = ["Exact binomial"] + [pct(idx[f"pd.binomial@{r}"]["exact"]["p<0.05"], 1) for r in rhos]
    rows.append(ex)
    macro("vtClBinRho5", pct(idx["pd.binomial@rho0.05"]["exact"]["p<0.05"], 1), "clustering.json pd.binomial@rho0.05 exact")
    macro("vtClBinRho20", pct(idx["pd.binomial@rho0.2"]["exact"]["p<0.05"], 1), "clustering.json pd.binomial@rho0.2 exact")
    macro("vtClVas5", pct(idx["pd.binomial_vasicek@rho0.05"]["exact"]["p<0.05"], 1), "clustering.json pd.binomial_vasicek@rho0.05 exact")
    macro("vtClVas10", pct(idx["pd.binomial_vasicek@rho0.1"]["exact"]["p<0.05"], 1), "clustering.json pd.binomial_vasicek@rho0.1 exact")
    macro("vtClVas20", pct(idx["pd.binomial_vasicek@rho0.2"]["exact"]["p<0.05"], 1), "clustering.json pd.binomial_vasicek@rho0.2 exact")
    macro("vtClHl20", pct(r05(idx["pd.hosmer_lemeshow@rho0.2"])["rate"], 1), "clustering.json pd.hosmer_lemeshow@rho0.2")
    macro("vtClChi20", pct(r05(idx["pd.chi2_grades@rho0.2"])["rate"], 1), "clustering.json pd.chi2_grades@rho0.2")
    macro("vtClSp20", pct(r05(idx["pd.spiegelhalter@rho0.2"])["rate"], 1), "clustering.json pd.spiegelhalter@rho0.2")
    macro("vtClNormal0", pct(r05(idx["pd.normal_multiperiod@rho0"])["rate"], 1), "clustering.json pd.normal_multiperiod@rho0")
    macro("vtClNormal20", pct(r05(idx["pd.normal_multiperiod@rho0.2"])["rate"], 1), "clustering.json pd.normal_multiperiod@rho0.2")
    macro("vtClTl20", pct(r05(idx["pd.traffic_lights@rho0.2"])["rate"], 1), "clustering.json pd.traffic_lights@rho0.2")
    macro("vtClReps", f"{idx['pd.binomial@rho0']['n_rep']:,}".replace(",", "{,}"), "clustering.json n_rep")
    cmpn = [s for s in d["outputs"]["simulations"] if s.get("exact")]
    macro("vtClAgreeN", sum(all(s["agrees"].values()) for s in cmpn), "clustering.json exact comparisons that agree")
    macro("vtClAgreeOf", len(cmpn), "clustering.json simulations with an exact probability")
    emit(OUT / "validation-tests-cluster.tex", ["Test", "$\\rho=0$", "0.02", "0.05", "0.10", "0.15", "0.20"], rows,
                 caption=("The rejection rate at the 5 percent level, in percent with the Monte Carlo standard error, of the calibration tests when the "
                          "forecast probability of default is right and the defaults are correlated through the one-factor model with the asset correlation "
                          "$\\rho$ in the column heading; the last row is the exact rejection probability of the binomial test."),
                 label="tab:vt-cluster", align="lrrrrrr")


def table_drift() -> None:
    d = c22("drift")
    idx = sim_index(d)
    ss = ["s0", "s0.05", "s0.1", "s0.2", "s0.3", "s0.5"]
    tests = ["stability.psi", "stability.chi2", "stability.ks", "pd.hosmer_lemeshow", "pd.spiegelhalter"]
    rows = []
    for t in tests:
        rows.append([TEST_LABEL[t]] + [rate_cell(r05(idx[f"{t}@{s}"]), 1) for s in ss])
    dd = c22("discrimination-decay")
    di = sim_index(dd)
    ds = ["d0", "d0.01", "d0.02", "d0.03", "d0.05", "d0.08"]
    for t in ("disc.auc_vs_initial", "disc.delong"):
        rows.append([TEST_LABEL[t]] + [rate_cell(r05(di[f"{t}@{s}"]), 1) for s in ds])
    macro("vtDrPsi01", pct(r05(idx["stability.psi@s0.1"])["rate"], 1), "drift.json stability.psi@s0.1")
    macro("vtDrKs01", pct(r05(idx["stability.ks@s0.1"])["rate"], 1), "drift.json stability.ks@s0.1")
    macro("vtDrPsi02", pct(r05(idx["stability.psi@s0.2"])["rate"], 1), "drift.json stability.psi@s0.2")
    macro("vtDrHl05", pct(r05(idx["pd.hosmer_lemeshow@s0.5"])["rate"], 1), "drift.json pd.hosmer_lemeshow@s0.5")
    macro("vtDrSp05", pct(r05(idx["pd.spiegelhalter@s0.5"])["rate"], 1), "drift.json pd.spiegelhalter@s0.5")
    macro("vtDcAuc03", pct(r05(di["disc.auc_vs_initial@d0.03"])["rate"], 1), "discrimination-decay.json disc.auc_vs_initial@d0.03")
    macro("vtDcDel03", pct(r05(di["disc.delong@d0.03"])["rate"], 1), "discrimination-decay.json disc.delong@d0.03")
    macro("vtDcAuc05", pct(r05(di["disc.auc_vs_initial@d0.05"])["rate"], 1), "discrimination-decay.json disc.auc_vs_initial@d0.05")
    macro("vtDcDel05", pct(r05(di["disc.delong@d0.05"])["rate"], 1), "discrimination-decay.json disc.delong@d0.05")
    macro("vtDrReps", f"{idx['stability.psi@s0']['n_rep']:,}".replace(",", "{,}"), "drift.json n_rep")
    lk = c22("leakage")
    li = sim_index(lk)
    macro("vtLkNested", pct(r05(li["disc.delong@nested"])["rate"], 1), "leakage.json disc.delong@nested")
    macro("vtLkNonNested", pct(r05(li["disc.delong@non-nested"])["rate"], 1), "leakage.json disc.delong@non-nested")
    macro("vtLkAuc1", pct(r05(li["disc.auc_vs_initial@l1"])["rate"], 1), "leakage.json disc.auc_vs_initial@l1")
    macro("vtLkCsi1", pct(r05(li["stability.csi@l1"])["rate"], 1), "leakage.json stability.csi@l1")
    macro("vtLkCsi2", pct(r05(li["stability.csi@l2"])["rate"], 1), "leakage.json stability.csi@l2")
    emit(OUT / "validation-tests-drift.tex", ["Test", "Level 0", "1", "2", "3", "4", "5"], rows,
                 caption=("The power at the 5 percent level, in percent with the Monte Carlo standard error, of the stability tests against a mean shift of "
                          "the scored variable of 0, 0.05, 0.1, 0.2, 0.3 and 0.5 standard deviations, of the calibration tests against the same shift, "
                          "and of the discrimination tests against a loss of AUC of 0, 0.01, 0.02, 0.03, 0.05 and 0.08 (the last two rows)."),
                 label="tab:vt-drift", align="lrrrrrr")


def table_structure() -> None:
    cc = c22("concentration")
    ci = sim_index(cc)
    bm = c22("broken-monotonicity")
    bi = sim_index(bm)
    rows = []
    for c in ("c0", "c0.01", "c0.02", "c0.05", "c0.1", "c0.5"):
        rows.append(["Concentration, mass moved to the modal grade " + c[1:] if c != "c0" else "Concentration, no change",
                     rate_cell(r05(ci[f"rating.hhi@{c}"]), 1), rate_cell(r05(ci[f"stability.chi2@{c}"]), 1)])
    macro("vtConHhiMax", pct(max(r05(ci[f"rating.hhi@{c}"])["rate"] for c in ("c0", "c0.01", "c0.02", "c0.05", "c0.1", "c0.5")), 1),
          "concentration.json largest rating.hhi rate")
    macro("vtConChi5", pct(r05(ci["stability.chi2@c0.05"])["rate"], 1), "concentration.json stability.chi2@c0.05")
    macro("vtConChi1", pct(r05(ci["stability.chi2@c0.01"])["rate"], 1), "concentration.json stability.chi2@c0.01")
    macro("vtConChi0", pct(r05(ci["stability.chi2@c0"])["rate"], 1), "concentration.json stability.chi2@c0")
    macro("vtBmR2n500", pct(r05(bi["rating.migration_ztests@r2-n500"])["rate"], 1), "broken-monotonicity.json r2-n500")
    macro("vtBmR2n2000", pct(r05(bi["rating.migration_ztests@r2-n2000"])["rate"], 1), "broken-monotonicity.json r2-n2000")
    macro("vtBmR15n500", pct(r05(bi["rating.migration_ztests@r1.5-n500"])["rate"], 1), "broken-monotonicity.json r1.5-n500")
    macro("vtBmR15n2000", pct(r05(bi["rating.migration_ztests@r1.5-n2000"])["rate"], 1), "broken-monotonicity.json r1.5-n2000")
    macro("vtBmR3n500", pct(r05(bi["rating.migration_ztests@r3-n500"])["rate"], 1), "broken-monotonicity.json r3-n500")
    macro("vtBmR1n500", pct(r05(bi["rating.migration_ztests@r1-n500"])["rate"], 2), "broken-monotonicity.json r1-n500")
    macro("vtBmCurve", pct(r05(bi["pd.default_profile@swap0.4"])["rate"], 1), "broken-monotonicity.json pd.default_profile@swap0.4")
    for r in ("1", "1.25", "1.5", "2", "3", "4"):
        rows.append([f"Migration z-tests, planted cell {r} times its neighbour",
                     rate_cell(r05(bi[f"rating.migration_ztests@r{r}-n500"]), 1), rate_cell(r05(bi[f"rating.migration_ztests@r{r}-n2000"]), 1)])
    emit(OUT / "validation-tests-structure.tex", ["Defect planted", "Rating test (\\%)", "Count test or 2,000 per grade (\\%)"], rows,
                 caption=("The power at the 5 percent level, in percent with the Monte Carlo standard error, against defects of the rating structure. First "
                          "six rows: share of every grade's mass moved into the modal grade, read by the ECB concentration test (second column) and by the "
                          "chi-square test of homogeneity on the counts (third column). Last six rows: a cell two notches from the diagonal planted at "
                          "a multiple of its closer neighbour, read by the migration z-tests with 500 (second column) and 2,000 (third column) obligors per grade."),
                 label="tab:vt-structure", align="p{6.4cm}rr")


def table_other() -> None:
    d = c22("other-families")
    imp = d["impact"]
    S = d["outputs"]["simulations"]
    nulls = [s for s in S if s["study"]["arm"] == "null"]
    alts = [s for s in S if s["study"]["arm"] == "alternative"]
    macro("vtOtherStudies", len(alts), "other-families.json alternative arms")
    macro("vtOtherPowMin", pct(imp["other_power_min"]["value"], 1), "other-families.json impact.other_power_min")
    macro("vtOtherPowMed", pct(imp["other_power_median"]["value"], 1), "other-families.json impact.other_power_median")
    macro("vtOtherPowMax", pct(imp["other_power_max"]["value"], 1), "other-families.json impact.other_power_max")
    macro("vtOtherAbove80", int(imp["other_studies_above_80"]["value"]), "other-families.json impact.other_studies_above_80")
    wanted = [("ml.shift_resilience", "ML shift resilience"), ("ml.conformal_coverage", "ML conformal coverage"),
              ("fair.two_proportion_z", "Two-proportion z"), ("fair.fisher_exact", "Fisher exact")]
    idx = sim_index(d)
    rows = []
    for t, lab in wanted:
        n, a = idx[f"{t}@d0"], idx[f"{t}@d1"]
        rows.append([lab, a["study"]["label"]["en"], rate_cell(r05(n)), a["study"]["text"]["en"], rate_cell(r05(a))])
    macro("vtShiftSize", pct(r05(idx["ml.shift_resilience@d0"])["rate"], 1), "other-families.json ml.shift_resilience@d0")
    macro("vtShiftPow", pct(r05(idx["ml.shift_resilience@d1"])["rate"], 1), "other-families.json ml.shift_resilience@d1")
    macro("vtConfSize", pct(r05(idx["ml.conformal_coverage@d0"])["rate"], 1), "other-families.json ml.conformal_coverage@d0")
    macro("vtConfPow", pct(r05(idx["ml.conformal_coverage@d1"])["rate"], 1), "other-families.json ml.conformal_coverage@d1")
    macro("vtZSize", pct(r05(idx["fair.two_proportion_z@d0"])["rate"], 1), "other-families.json fair.two_proportion_z@d0")
    macro("vtZPow", pct(r05(idx["fair.two_proportion_z@d1"])["rate"], 1), "other-families.json fair.two_proportion_z@d1")
    macro("vtFisherSize", pct(r05(idx["fair.fisher_exact@d0"])["rate"], 1), "other-families.json fair.fisher_exact@d0")
    macro("vtFisherPow", pct(r05(idx["fair.fisher_exact@d1"])["rate"], 1), "other-families.json fair.fisher_exact@d1")
    macro("vtOtherReps", f"{S[0]['n_rep']:,}".replace(",", "{,}"), "other-families.json n_rep")
    emit(OUT / "validation-tests-other.tex", ["Test", "Setting", "Size (\\%)", "Planted departure", "Power (\\%)"], rows,
                 caption=("The size and power at the 5 percent level, in percent with the Monte Carlo standard error, of the four machine-learning and "
                          "fairness tests that case C22 measures as named studies of the engine: the setting, the null, the departure planted in the "
                          "alternative and the rate at which the test rejects it."),
                 label="tab:vt-other", align="lp{2.8cm}rp{4.4cm}r")


_ROW = re.compile(r"^\|(.+)\|\s*$")


def md_rows(text: str, first_cell: str) -> list[list[str]]:
    """The body rows of the first Markdown table whose header starts with ``first_cell``."""
    lines = text.splitlines()
    out: list[list[str]] = []
    on = False
    for ln in lines:
        m = _ROW.match(ln)
        if not on:
            if m and m.group(1).split("|")[0].strip() == first_cell:
                on = True
            continue
        if not m:
            break
        cells = [c.strip() for c in m.group(1).split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        out.append(cells)
    return out


def clean_md(s: str) -> str:
    return s.replace("`", "").replace("**", "")


def tables_engine_docs(docs: pathlib.Path) -> None:
    ml = (docs / "ml" / "08_size-and-power.md").read_text(encoding="utf-8")
    rows = []
    for c in md_rows(ml, "Test"):
        if len(c) < 9:
            continue
        rows.append([idcell(clean_md(c[0])), clean_md(c[1]), f"${100 * float(c[2]):.2f}\\pm{100 * float(c[3]):.2f}$", clean_md(c[5]),
                     f"${100 * float(c[6]):.2f}\\pm{100 * float(c[7]):.2f}$"])
    sizes = [float(c[2]) for c in md_rows(ml, "Test") if len(c) >= 9]
    powers = [float(c[6]) for c in md_rows(ml, "Test") if len(c) >= 9]
    macro("vtMlConditions", len(rows), "docs/ml/08_size-and-power.md the measured table rows")
    macro("vtMlSizeMax", pct(max(sizes), 2), "docs/ml/08_size-and-power.md largest size")
    macro("vtMlPowerMin", pct(min(powers), 2), "docs/ml/08_size-and-power.md smallest power")
    macro("vtMlBoundTwoSe", "5.69", "docs/ml/08_size-and-power.md: 0.05 plus two standard errors at 4,000 repetitions")
    emit(OUT / "validation-tests-ml-size.tex", ["Test", "Null", "Size (\\%)", "Planted defect", "Power (\\%)"], rows,
                 caption=("The size and power at the 5 percent level, in percent with the Monte Carlo standard error, of the machine-learning validation "
                          "tests of the engine on its planted-defect generators, from 4,000 repetitions per condition: each test is fed by a generator whose "
                          "null holds and by the same generator with one defect planted, and a rejection is a light that is not green."),
                 label="tab:vt-ml-size", align="p{3.3cm}p{2.9cm}rp{3.1cm}r")
    fa = (docs / "fairness" / "06_validation-tests.md").read_text(encoding="utf-8")
    frows = []
    for c in md_rows(fa, "Test"):
        if len(c) < 4 or not clean_md(c[0]).startswith("fair."):
            continue
        frows.append([fn(clean_md(c[0])), clean_md(c[1]), clean_md(c[2]), clean_md(c[3])])
    macro("vtFairConditions", len(frows), "docs/fairness/06_validation-tests.md the measured table rows")
    emit(OUT / "validation-tests-fair-size.tex", ["Test", "Size and its null", "Planted bias", "Power"], frows,
                 caption=("The size and power of the fairness tests of the engine on its planted-bias generators, from 4,000 repetitions per condition, as the "
                          "engine's own measured table states them: the rejection rate under no bias with its standard error and the plant, the bias planted, "
                          "and the rate at which the test is not green against it."),
                 label="tab:vt-fair-size", align="p{3.4cm}p{4.8cm}p{3.6cm}p{1.8cm}")


# --------------------------------------------------------------------------- C20 and C21


def c20_docs() -> dict[str, dict]:
    return {n: load(f"C20/{n}.json") for n in C20_FILES}


def table_c20(D: dict[str, dict]) -> None:
    rows = []
    tot = collections.Counter()
    for n in C20_FILES:
        d = D[n]
        c = collections.Counter(t["light"] for t in d["tests"] if t["test_id"].startswith("ml."))
        tot.update(c)
        ids = sorted({t["test_id"].replace("ml.", "") for t in d["tests"] if t["test_id"].startswith("ml.")} |
                     {t["test_id"] for t in d["tests"] if t["test_id"].startswith("stability.")})
        rows.append([n, ", ".join(fn(i) for i in ids), c["green"], c["amber"], c["red"], c["not_evaluated"],
                     f"{100 * d['impact']['decision_flip_share']['value']:.1f}"])
    macro("vtCtwentyRed", tot["red"], "C20 variants: ml.* rows with a red light")
    macro("vtCtwentyAmber", tot["amber"], "C20 variants: ml.* rows with an amber light")
    macro("vtCtwentyGreen", tot["green"], "C20 variants: ml.* rows with a green light")
    emit(OUT / "validation-tests-c20-lights.tex",
                 ["Variant", "Tests run", "Green", "Amber", "Red", "Not eval.", "Flipped (\\%)"], rows,
                 caption=("The lights of the machine-learning tests of case C20 in each of its six variants: the tests that ran, the number of rows with each "
                          "light and the share of the holdout decisions that the variant's shock or perturbation flips at the case's cut-off. Not eval. counts the rows that could not be evaluated. The data-quality "
                          "and stability rows of the shock variants are counted in the first two groups."),
                 label="tab:vt-c20-lights", align="lp{4.2cm}rrrrr")


def find(d: dict, test_id: str, segment: str | None = None, model: str | None = None) -> dict:
    for t in d["tests"]:
        if t["test_id"] == test_id and (segment is None or t["segment"] == segment) and (model is None or t["model_id"] == model):
            return t
    raise KeyError((test_id, segment, model))


def table_c20_stats(D: dict[str, dict]) -> None:
    rows = []

    def add(var, tid, seg, model, label, cell):
        t = find(D[var], tid, seg, model)
        rows.append([label, var, cell(t), t["light"]])

    gap = lambda t: f"{t['metric']:.4f}"
    add("sgcd-seen", "ml.overfit", None, None, "Overfit gap (train minus holdout AUC), LightGBM, German", gap)
    add("fed-shift", "ml.overfit", None, None, "Overfit gap, LightGBM, Polish", gap)
    add("perturbation-grid", "ml.overfit", None, None, "Overfit gap, LightGBM, Taiwan", gap)
    add("seed-sweep", "ml.overfit", None, "P4-xgboost-taiwan", "Overfit gap, XGBoost, Taiwan", gap)
    add("perturbation-grid", "ml.robustness", "preset-eps-0.1", None, "AUC loss at noise scale 0.1, inputs perturbed", gap)
    add("perturbation-grid", "ml.robustness", "control-zeros-kept:preset-eps-0.1", None, "AUC loss at noise scale 0.1, control run", gap)
    add("seed-sweep", "ml.seed_stability", None, "P4-lightgbm-taiwan", "AUC standard deviation over 20 seeds, LightGBM", lambda t: f"{t['metric']:.5f}")
    add("seed-sweep", "ml.seed_stability", None, "P4-xgboost-taiwan", "AUC standard deviation over 20 seeds, XGBoost", lambda t: f"{t['metric']:.5f}")
    add("seed-sweep", "ml.reason_code_stability", None, "P4-lightgbm-taiwan", "Top-four reason overlap over 100 refits, LightGBM", lambda t: f"{t['metric']:.3f}")
    add("seed-sweep", "ml.reason_code_stability", None, "P4-xgboost-taiwan", "Top-four reason overlap over 100 refits, XGBoost", lambda t: f"{t['metric']:.3f}")
    add("seed-sweep", "ml.effect_agreement", None, "P4-lightgbm-taiwan", "Spearman rho of SHAP importance and ALE range, LightGBM", lambda t: f"{t['metric']:.3f}")
    add("seed-sweep", "ml.effect_agreement", None, "P4-xgboost-taiwan", "Spearman rho of SHAP importance and ALE range, XGBoost", lambda t: f"{t['metric']:.3f}")
    add("seed-sweep", "ml.additivity", None, "P4-lightgbm-taiwan", "Largest Shapley additivity gap, LightGBM", lambda t: sci(t["metric"]))
    add("seed-sweep", "ml.additivity", None, "P4-xgboost-taiwan", "Largest Shapley additivity gap, XGBoost", lambda t: sci(t["metric"]))
    lk = D["leakage-planted"]
    rows.append(["Single-feature AUC of the planted future column", "leakage-planted",
                 f"{lk['outputs']['screen']['single_feature_auc']['max_auc']:.4f}", "red"])
    rows.append(["Resemblance AUC, development against out-of-time", "leakage-planted", f"{lk['outputs']['screen']['resemblance_auc']:.3f}", "green"])
    fs = D["fed-shift"]
    sr = find(fs, "ml.shift_resilience")
    rows.append(["AUC drop on the worst subsample against the development-only reference", "fed-shift", f"{sr['metric']:.4f}", sr["light"]])
    for t in fs["tests"]:
        if t["test_id"] == "ml.conformal_coverage" and t["segment"] in ("window:baseline", "window:pooled"):
            rows.append([f"Conformal coverage of the 90 percent sets, {t['segment'].replace('window:', '')} window", "fed-shift", f"{t['metric']:.3f}", t["light"]])
    macro("vtC20LeakAuc", f"{lk['outputs']['screen']['single_feature_auc']['max_auc']:.4f}", "C20/leakage-planted.json outputs.screen.single_feature_auc.max_auc")
    macro("vtC20DevAuc", f"{lk['outputs']['performance']['development_auc']:.4f}", "C20/leakage-planted.json outputs.performance.development_auc")
    macro("vtC20DecAuc", f"{lk['outputs']['performance']['decision_time_auc']:.4f}", "C20/leakage-planted.json outputs.performance.decision_time_auc")
    macro("vtC20LeakViol", f"{lk['outputs']['screen']['temporal_order']['violations']:,}".replace(",", "{,}"), "leakage-planted.json outputs.screen.temporal_order.violations")
    macro("vtC20ResAuc", f"{lk['outputs']['screen']['resemblance_auc']:.3f}", "leakage-planted.json outputs.screen.resemblance_auc")
    pg = D["perturbation-grid"]
    macro("vtC20RobLoss", f"{find(pg, 'ml.robustness', 'preset-eps-0.1')['metric']:.4f}", "perturbation-grid.json ml.robustness preset-eps-0.1")
    macro("vtC20RobCtl", f"{find(pg, 'ml.robustness', 'control-zeros-kept:preset-eps-0.1')['metric']:.4f}", "perturbation-grid.json control")
    ssw = D["seed-sweep"]
    macro("vtC20SeedFlip", f"{100 * ssw['outputs']['rows'][0]['grade_assignment_changed_share']:.1f}", "seed-sweep.json rows[0].grade_assignment_changed_share (LightGBM)")
    macro("vtC20SeedTau", f"{ssw['outputs']['rows'][0]['attribution_rank_tau']['mean']:.3f}", "seed-sweep.json rows[0].attribution_rank_tau.mean")
    macro("vtC20SeedMean", f"{ssw['outputs']['rows'][0]['auc']['mean']:.4f}", "seed-sweep.json rows[0].auc.mean")
    macro("vtC20SeedSd", f"{find(ssw, 'ml.seed_stability', None, 'P4-lightgbm-taiwan')['metric']:.4f}", "seed-sweep.json ml.seed_stability LightGBM metric")
    macro("vtC20ReasonLgbm", f"{find(ssw, 'ml.reason_code_stability', None, 'P4-lightgbm-taiwan')['metric']:.3f}", "seed-sweep.json ml.reason_code_stability LightGBM metric")
    macro("vtC20ReasonXgb", f"{find(ssw, 'ml.reason_code_stability', None, 'P4-xgboost-taiwan')['metric']:.3f}", "seed-sweep.json ml.reason_code_stability XGBoost metric")
    macro("vtC20AddXgb", sci(find(ssw, 'ml.additivity', None, 'P4-xgboost-taiwan')['metric']), "seed-sweep.json ml.additivity XGBoost metric")
    macro("vtC20CovPooled", f"{[t for t in fs['tests'] if t['test_id'] == 'ml.conformal_coverage' and t['segment'] == 'window:pooled'][0]['metric']:.3f}", "fed-shift.json ml.conformal_coverage window:pooled metric")
    macro("vtC20CovBase", f"{[t for t in fs['tests'] if t['test_id'] == 'ml.conformal_coverage' and t['segment'] == 'window:baseline'][0]['metric']:.3f}", "fed-shift.json ml.conformal_coverage window:baseline metric")
    macro("vtC20SrDrop", f"{sr['metric']:.4f}", "fed-shift.json ml.shift_resilience metric")
    macro("vtC20SrP", f"{sr['p_value']:.3f}", "fed-shift.json ml.shift_resilience p_value")
    macro("vtC20SrNullP95", f"{sr['extras']['null_p95']:.4f}", "fed-shift.json ml.shift_resilience extras.null_p95")
    macro("vtC20SrPerm", sr["extras"]["shift_permutations"], "fed-shift.json ml.shift_resilience extras.shift_permutations")
    macro("vtC20SrN", sr["n"], "fed-shift.json ml.shift_resilience n")
    emit(OUT / "validation-tests-c20-stats.tex", ["Statistic", "Variant", "Value", "Light"], rows,
                 caption=("Selected statistics of the machine-learning tests of case C20 and the light each one earns: the overfit gaps of the gradient-boosted "
                          "models, the loss of AUC under input noise with its control, the dispersion of the AUC and of the top-four reasons across retraining "
                          "seeds, the agreement of the two explainers, the additivity gap, the leakage screens on the planted column, and the shift and "
                          "conformal tests on the Federal Reserve shift probes."),
                 label="tab:vt-c20-stats", align="p{6.4cm}lrl")


def c21_pair(pair: str) -> dict:
    d = load(f"C21/pair-{pair}.json")
    BW = "derived_race|Black or African American vs White"
    z = find(d, "fair.two_proportion_z", BW)
    cd = find(d, "fair.conditional_disparity", BW)
    rp = find(d, "fair.replication", BW + "|controlled")
    st = find(d, "fair.situation_testing", "derived_race")
    eff = cd["extras"]["effect"]
    cnt = collections.Counter((t["test_id"], t["light"]) for t in d["tests"])
    return {"pair": pair, "rows_fit": d["outputs"]["scope"]["rows_fit"], "rows_confirm": d["outputs"]["scope"]["rows_confirm"],
            "r1": z["extras"]["rate_1"], "r2": z["extras"]["rate_2"], "gap": z["metric"], "p": z["p_value"], "z_light": z["light"],
            "or": cd["metric"], "or_lo": math.exp(eff["lo"]), "or_hi": math.exp(eff["hi"]), "rep": rp["metric"], "rep_same": rp["extras"]["same_sign"],
            "st_share": st["metric"], "st_sig": st["extras"]["n_significant"], "st_n": st["extras"]["n_complainants"], "st_light": st["light"],
            "z_red": cnt[("fair.two_proportion_z", "red")], "z_n": sum(v for (k, _), v in cnt.items() if k == "fair.two_proportion_z"),
            "rep_amber": cnt[("fair.replication", "amber")], "rep_n": sum(v for (k, _), v in cnt.items() if k == "fair.replication"),
            "air_amber": cnt[("fair.adverse_impact", "amber")], "air_n": sum(v for (k, _), v in cnt.items() if k == "fair.adverse_impact"),
            "cd_n": sum(v for (k, _), v in cnt.items() if k == "fair.conditional_disparity")}


def table_c21() -> list[dict]:
    P = [c21_pair(p) for p in C21_PAIRS]
    rows = []
    for p in P:
        rows.append([p["pair"], p["rows_fit"], p["rows_confirm"], f"{100 * p['r1']:.1f}", f"{100 * p['r2']:.1f}", f"${100 * p['gap']:+.1f}$".replace("+", ""),
                     f"{p['or']:.2f} [{p['or_lo']:.2f}, {p['or_hi']:.2f}]", f"{p['rep']:.2f}"])
    macro("vtC21Pairs", len(P), "C21 variants pair-*")
    macro("vtC21GapMin", f"{min(abs(p['gap']) for p in P) * 100:.1f}", "pair-*.json fair.two_proportion_z Black vs White metric (min abs)")
    macro("vtC21GapMax", f"{max(abs(p['gap']) for p in P) * 100:.1f}", "same (max abs)")
    macro("vtC21OrMin", f"{min(p['or'] for p in P):.2f}", "pair-*.json fair.conditional_disparity odds ratio (min)")
    macro("vtC21OrMax", f"{max(p['or'] for p in P):.2f}", "same (max)")
    macro("vtC21RowsMin", f"{min(p['rows_fit'] for p in P):,}".replace(",", "{,}"), "pair-*.json outputs.scope.rows_fit (min)")
    macro("vtC21RowsMax", f"{max(p['rows_confirm'] for p in P):,}".replace(",", "{,}"), "pair-*.json outputs.scope.rows_confirm (max)")
    macro("vtC21StMin", f"{100 * min(p['st_share'] for p in P):.1f}", "pair-*.json fair.situation_testing metric (min)")
    macro("vtC21StMax", f"{100 * max(p['st_share'] for p in P):.1f}", "same (max)")
    macro("vtC21RepMin", f"{min(p['rep'] for p in P):.2f}", "pair-*.json fair.replication size ratio (min)")
    macro("vtC21RepMax", f"{max(p['rep'] for p in P):.2f}", "same (max)")
    macro("vtC21ZRed", sum(p["z_red"] for p in P), "pair-*.json fair.two_proportion_z rows with a red light")
    macro("vtC21ZN", sum(p["z_n"] for p in P), "pair-*.json fair.two_proportion_z rows")
    macro("vtC21RepAmber", sum(p["rep_amber"] for p in P), "pair-*.json fair.replication rows with an amber light")
    macro("vtC21RepN", sum(p["rep_n"] for p in P), "pair-*.json fair.replication rows")
    macro("vtC21AirAmber", sum(p["air_amber"] for p in P), "pair-*.json fair.adverse_impact rows with an amber light")
    macro("vtC21AirN", sum(p["air_n"] for p in P), "pair-*.json fair.adverse_impact rows")
    macro("vtC21CdN", sum(p["cd_n"] for p in P), "pair-*.json fair.conditional_disparity rows")
    macro("vtC21StAmber", sum(p["st_light"] == "amber" for p in P), "pair-*.json fair.situation_testing rows with an amber light")
    macro("vtC21First", P[0]["pair"], "first pair")
    macro("vtC21Last", P[-1]["pair"], "last pair")
    macro("vtC21Bw1819gap", f"{abs(P[0]['gap']) * 100:.1f}", "pair-2018-19.json Black vs White gap")
    emit(OUT / "validation-tests-c21-pairs.tex",
                 ["Pair", "Rows fit", "Rows confirm", "Black (\\%)", "White (\\%)", "Gap (pp)", "Odds ratio [95\\% interval]", "Size ratio"], rows,
                 caption=("Case C21, Black or African American applicants against White applicants in each fit and confirmation year pair of the Delaware "
                          "HMDA decisions: the rows of the two years, the unconditional approval rates, their difference in percentage points, the odds ratio of "
                          "approval after the permitted controls with its 95 percent interval, and the ratio of the coefficient refitted on the later year to the "
                          "earlier one."),
                 label="tab:vt-c21-pairs", align="lrrrrrlr")
    rows2 = []
    for p in P:
        rows2.append([p["pair"], f"{p['z_red']} of {p['z_n']}", f"{p['air_amber']} of {p['air_n']}", f"{p['cd_n']}",
                      f"{p['rep_amber']} of {p['rep_n']}", f"{100 * p['st_share']:.1f}", f"{p['st_sig']:,} of {p['st_n']:,}"])
    emit(OUT / "validation-tests-c21-lights.tex",
                 ["Pair", "z red", "4/5 amber", "Models", "Repl. amber", "Situation (\\%)", "Significant"],
                 rows2,
                 caption=("The lights of the fairness tests of case C21 in each year pair: the number of two-proportion z-tests that are red, of the "
                          "four-fifths indicators that are amber, the controlled disparity models fitted, the replication rows whose sign changes between the "
                          "years, and the share of complainants whose situation test is significant with the count behind it. In the heading, 4/5 amber is the four-fifths "
                          "indicator, Models the controlled disparity models, and Repl. amber the replication rows whose sign changes."),
                 label="tab:vt-c21-lights", align="lrrrrrr")
    return P


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine-docs", default=os.environ.get("RISKVALIDATION_DOCS"))
    ap.add_argument("--registry", default=None)
    a = ap.parse_args()
    cat = catalogue_stats()
    table_catalogue(cat)
    table_policy()
    G = golden_cells()
    table_published(G)
    table_size()
    table_settings()
    table_miscal()
    table_cluster()
    table_drift()
    table_structure()
    table_other()
    if a.engine_docs:
        tables_engine_docs(pathlib.Path(a.engine_docs))
    elif not (OUT / "validation-tests-ml-size.tex").exists():
        print("note: --engine-docs not given and the engine-docs tables do not exist yet", file=sys.stderr)
    D = c20_docs()
    table_c20(D)
    table_c20_stats(D)
    table_c21()
    write_numbers()
    if a.registry:
        pathlib.Path(a.registry).write_text(json.dumps([{"macro": m, "value": v, "source": s} for m, v, s in REG], indent=1), encoding="utf-8")
    print(f"{len(REG)} macros, tables written to {OUT}")


if __name__ == "__main__":
    main()
