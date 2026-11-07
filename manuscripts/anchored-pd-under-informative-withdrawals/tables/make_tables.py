"""Tables and the number macros of the manuscript on the anchored PD under informative rating withdrawals.

Reads only committed documents: ``data/derived/C04/{withdrawals,sp,fitch}.json`` (the product's artifacts) and
``experiments/results/*.json`` (the outputs of ``experiments/extended_study.py`` and ``experiments/theory_checks.py``),
and writes into ``tables/``:

- ``numbers.tex``: one ``\\expandafter\\def\\csname num@<key>\\endcsname{<text>}`` per number the prose quotes, read in the
  text as ``\\nv{<key>}``; no number of the prose is typed;
- ``numbers.json``: each key with its text and the source it was read from (the record the report's table of numbers
  is built from);
- one ``.tex`` per table (booktabs), ``\\input`` by the sections.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/anchored-pd-under-informative-withdrawals/tables/make_tables.py
"""
from __future__ import annotations

import json
import math
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "manuscripts" / "_shared"))
import figkit  # noqa: E402

RES = HERE.parent / "experiments" / "results"
GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"]
GRADE_TEX = {"CCC-C": "CCC to C"}
bs = chr(92)
B = 5
TR = ("industry", "unfollowed", "followed", "identified", "band", "anchored")
TR_NAME = {"industry": "Removed ($k=1$)", "unfollowed": "Kept ($k=0$)", "followed": "Followed (oracle)",
           "identified": "Manski band", "band": "Anchored $k$ band only", "anchored": "Anchored interval"}
INF = (0.0, 1.0, 3.0, 9.0, 19.0)
CAP_LABEL = {"1": "exact", "1.3": "1.3 times", "u1.0-1.6": "1.0 to 1.6 by year", "u1.0-4.0": "1.0 to 4.0 by year"}
DES = {"fy": "first-year cohort", "pool": "five cohorts pooled", "x10": "ten times the cohort"}

NUMS: dict[str, tuple[str, str]] = {}


def num(key: str, text: str, source: str) -> str:
    """Register a number the prose quotes; returns the text so that a table cell can use it."""
    if key in NUMS:
        if NUMS[key][0] != text:
            raise ValueError(f"number key {key} defined twice with different values")
        return text
    NUMS[key] = (text, source)
    return text


def pct(x: float, d: int = 1) -> str:
    return f"{100.0 * x:.{d}f}"


def spct(x: float, d: int = 1) -> str:
    return f"{100.0 * x:+.{d}f}"


def fix(rows):
    """A string cell that mixes text and math (or holds a command) is passed through figkit as it is: prefix it with a
    harmless command so that figkit does not escape its backslashes and dollar signs."""
    out = []
    for r in rows:
        out.append([("\\relax " + v) if isinstance(v, str) and ("$" in v or "\\" in v) and not v.startswith(("$", "\\")) else v
                    for v in r])
    return out


def tbl(path, header, rows, size=None, **kw):
    """figkit's booktabs table; ``size`` replaces the default font command (a wide table is set smaller)."""
    out = figkit.table(path, header, fix(rows), **kw)
    if size:
        text = out.read_text(encoding="utf-8").replace("\\small\n", size + "\n", 1)
        out.write_text(text, encoding="utf-8", newline="\n")
    return out


def load(name: str) -> dict:
    return json.loads((RES / name).read_text(encoding="utf-8"))


def ik(i: float) -> str:
    return f"i{i:g}"


def cell(x: float, se: float | None = None, d: int = 1) -> str:
    if x is None:
        return "--"
    if se is None:
        return f"{100 * x:.{d}f}"
    return f"${100 * x:.{d}f}\\pm{100 * se:.{d}f}$"


def main() -> None:
    grid = load("coverage-grid.json")
    scale = load("scale-ladder.json")
    cap = load("capture-ladder.json")
    stab = load("stability.json")
    dur = load("duration.json")
    thy = json.loads((RES / "theory-checks.json").read_text(encoding="utf-8"))
    wd = figkit.doc("C04/withdrawals.json")
    sp = figkit.doc("C04/sp.json")["outputs"]
    fi = figkit.doc("C04/fitch.json")["outputs"]
    out = HERE
    reps = grid["reps"]
    S_GRID, S_SCALE, S_CAP = ("experiments/results/coverage-grid.json", "experiments/results/scale-ladder.json",
                              "experiments/results/capture-ladder.json")

    cells: dict[tuple[str, float], dict] = {}
    for c in grid["data"]:
        cells[("fy" if c["design"] == "first_year" else "pool", c["informative"])] = c
    scale_cells = {(c["scale"], c["informative"]): c for c in scale["data"]}
    for i in INF:
        cells[("x10", i)] = scale_cells[(10, i)]
    cells[("x3", 9.0)] = scale_cells[(3, 9.0)]
    cells[("x30", 9.0)] = scale_cells[(30, 9.0)]

    num("reps", f"{reps:,}", S_GRID)
    num("reps.scale", f"{scale_cells[(3, 9.0)]['reps']:,}", S_SCALE)
    num("reps.duration", str(dur["data"][0]["reps"]), "experiments/results/duration.json")
    num("boot.duration", str(dur["data"][0]["n_boot"]), "experiments/results/duration.json")
    num("truthB", pct(cells[("fy", 9.0)]["truth"][B], 2), "data/derived/C04/withdrawals.json outputs.generator.pd_1y[5]")
    gen = wd["outputs"]["generator"]
    num("obligorsB", f"{gen['obligors'][B]:,}", "data/derived/C04/withdrawals.json outputs.generator.obligors[5]")
    num("withdrawal.rate", f"{100 * wd['outputs']['rungs'][0]['withdrawal_rate']:g}",
        "data/derived/C04/withdrawals.json outputs.rungs[0].withdrawal_rate")
    num("case.seed", str(wd["provenance"]["seed"]), "data/derived/C04/withdrawals.json provenance.seed")
    num("mcse.nominal", pct(math.sqrt(0.95 * 0.05 / reps), 1), "binomial standard error of a coverage of 0.95 at the repetitions of the grid")
    num("mcse.nominal200", pct(math.sqrt(0.95 * 0.05 / 200), 1), "binomial standard error of a coverage of 0.95 at 200 repetitions")

    rb = cells[("fy", 9.0)]["treatments"]["industry"]["rel_bias"][B]
    num("rho.fy.i9", f"{1.0 + rb:.2f}", S_GRID + " first_year informative 9 industry rel_bias: rho = 1 + bias")
    num("rho.hi.fy.i9", f"{1.0 - rb:.2f}", S_GRID + " first_year informative 9 industry rel_bias: 2 - rho = 1 - bias")

    # ---- numbers from the grid, the scale ladder, the capture ladder, the decisions
    for (des, i), c in cells.items():
        for t in TR:
            tt = c["treatments"][t]
            base = f"{des}.{ik(i)}.{t}"
            src = f"{S_SCALE if des in ('x10', 'x3', 'x30') else S_GRID} {c['id']} informative {i:g} treatments.{t}"
            num(f"cov.{base}", pct(tt["coverage"][B]), src)
            num(f"se.{base}", pct(tt["mcse"][B]), src)
            num(f"w.{base}", pct(tt["width"][B], 2), src)
            num(f"bias.{base}", spct(tt["rel_bias"][B]), src)
            num(f"abias.{base}", pct(abs(tt["rel_bias"][B])), src)
            num(f"bse.{base}", pct(tt["rel_bias_mcse"][B]), src)
            for g, name in enumerate(GRADES):
                num(f"covg.{des}.{ik(i)}.{t}.{name}", pct(tt["coverage"][g]), src)
        k = c["k"]
        num(f"kmed.{des}.{ik(i)}", f"{k['anchored_median'][B]:.1f}", f"{src} k.anchored_median")
        if k["true_median"][B] is not None:
            num(f"ktrue.{des}.{ik(i)}", f"{k['true_median'][B]:.1f}", f"{src} k.true_median")
        dec = c["decisions"]["by_treatment"]
        for t in ("industry", "followed", "anchored", "identified"):
            for dl, v in dec[t].items():
                for part, short in (("correct", "c"), ("wrong", "w"), ("undetermined", "u")):
                    num(f"dec.{des}.{ik(i)}.{t}.{dl}.{short}", pct(v[part], 0), f"{src} decisions.by_treatment.{t}.{dl}.{part}")
    for c in cap["data"]:
        base = f"cap.{ik(c['informative'])}.c{c['capture']:g}"
        src = f"{S_CAP} informative {c['informative']:g} capture {c['capture']:g}"
        a = c["treatments"]["anchored"]
        num(f"{base}.cov", pct(a["coverage"][B]), src)
        num(f"{base}.se", pct(a["mcse"][B]), src)
        num(f"{base}.w", pct(a["width"][B], 2), src)
        num(f"{base}.bias", spct(a["rel_bias"][B]), src)
        num(f"{base}.abias", pct(abs(a["rel_bias"][B])), src)
        num(f"{base}.band", pct(c["treatments"]["band"]["coverage"][B]), src)
        num(f"{base}.k", f"{c['k']['anchored_median'][B]:.1f}", src)
        num(f"{base}.ktrue", f"{c['k']['true_median'][B]:.1f}", src)
    for r in dur["data"]:
        src = f"experiments/results/duration.json informative {r['informative']:g}"
        num(f"dur.{ik(r['informative'])}.bias", spct(r["rel_bias"][B]), src)
        num(f"dur.{ik(r['informative'])}.abias", pct(abs(r["rel_bias"][B])), src)
        num(f"dur.{ik(r['informative'])}.bse", pct(r["rel_bias_mcse"][B]), src)
        num(f"dur.{ik(r['informative'])}.cov", pct(r["coverage"][B], 0), src)
        num(f"dur.{ik(r['informative'])}.cse", pct(r["mcse"][B], 0), src)
    for s in stab["data"]:
        base = f"stab.{ik(s['informative'])}.c{s['capture']}.{s['grade']}"
        src = f"experiments/results/stability.json informative {s['informative']:g} capture {s['capture']} grade {s['grade']}"
        num(f"{base}.share", pct(s["mean_share"]), src)
        num(f"{base}.stable", pct(s["share_stable_at_80"]), src)
        if s["median_pooled_k"] is not None:
            num(f"{base}.k", f"{s['median_pooled_k']:.1f}", src)

    # ---- the committed study (200 repetitions) and the committed verdict
    for r in wd["outputs"]["rungs"]:
        for d in r["bounds"]["designs"]:
            for t in d["treatments"]:
                cv = t["coverage"][B]
                src = f"data/derived/C04/withdrawals.json rungs[informative {r['value']:g}].bounds.designs[{d['id']}] {t['id']}"
                num(f"c200.{d['id']}.{ik(r['value'])}.{t['id']}", pct(cv["rate"]), src)
                num(f"c200se.{d['id']}.{ik(r['value'])}.{t['id']}", pct(cv["se"]), src)
    num("c200.reps", str(wd["outputs"]["bounds_verdict"]["reps"]), "data/derived/C04/withdrawals.json outputs.bounds_verdict.reps")

    # ---- real data
    sources = {"sp": ("S&P", sp, "data/derived/C04/sp.json"), "fitch": ("Fitch", fi, "data/derived/C04/fitch.json")}
    for key, (_, o, path) in sources.items():
        num(f"real.{key}.cohorts", str(len(o["cohorts"])), f"{path} outputs.cohorts")
        for g in o["withdrawal_bounds"]["grades"]:
            nm = g["grade"]
            src = f"{path} outputs.withdrawal_bounds.grades[{nm}]"
            if g["pooled"] is None:
                continue
            p = g["pooled"]
            num(f"real.{key}.{nm}.D", f"{p['defaults']:,.0f}", src)
            num(f"real.{key}.{nm}.S", f"{p['survivors']:,.0f}", src)
            num(f"real.{key}.{nm}.W", f"{p['withdrawn']:,.0f}", src)
            num(f"real.{key}.{nm}.A", f"{p['anchor_defaults']:,.0f}", src)
            num(f"real.{key}.{nm}.Na", f"{p['anchor_cohort']:,.0f}", src)
            num(f"real.{key}.{nm}.N", f"{p['defaults'] + p['survivors'] + p['withdrawn']:,.0f}", src)
            num(f"real.{key}.{nm}.pd0", pct(p["defaults"] / (p["defaults"] + p["survivors"] + p["withdrawn"]), 2), src)
            num(f"real.{key}.{nm}.ximp", f"{p['defaults_implied']:,.0f}", src)
            num(f"real.{key}.{nm}.pdind", pct(p["pd_industry"], 2), src)
            num(f"real.{key}.{nm}.pdanc", pct(p["pd_anchored"], 2), src)
            if p["pd_lower"] is not None:
                num(f"real.{key}.{nm}.pdlo", pct(p["pd_lower"], 2), src)
                num(f"real.{key}.{nm}.pdhi", pct(p["pd_upper"], 2), src)
            if p["k"] is not None:
                num(f"real.{key}.{nm}.k", f"{p['k']:.1f}", src)
                num(f"real.{key}.{nm}.klo", f"{p['k_low']:.1f}", src)
                num(f"real.{key}.{nm}.khi", f"{p['k_high']:.1f}", src)
            st = g["stability"]
            if st:
                num(f"real.{key}.{nm}.share", pct(st["share_cohorts_containing_pooled_k"], 0), src)
                num(f"real.{key}.{nm}.contain", str(st["cohorts_containing_pooled_k"]), src)
                num(f"real.{key}.{nm}.usable", str(st["usable_cohorts"]), src)
            kc = g["k_over_cohorts"]
            if kc and kc["median"] is not None:
                num(f"real.{key}.{nm}.kmed", f"{kc['median']:.1f}", src)
            tp = g["tipping"]
            if tp and tp["k"] is not None:
                num(f"real.{key}.{nm}.tip", f"{tp['k']:.1f}", src)
                num(f"real.{key}.{nm}.tipthr", pct(tp["threshold"], 2), src)
                num(f"real.{key}.{nm}.manski", pct(tp["pd_manski_upper"], 1), src)
    empty = [c for c in fi["cohorts"] if sum(r[len(r) - 1] for r in c["counts"]) == 0 and sum(c["defaulted"] or []) > 0]
    fsrc = "data/derived/C04/fitch.json outputs.cohorts (default column of counts empty while the default page counts defaults)"
    num("fitch.empty.n", str(len(empty)), fsrc)
    num("fitch.empty.first", empty[0]["label"], fsrc)
    num("fitch.empty.last", empty[-1]["label"], fsrc)
    num("fitch.empty.lost", f"{sum(sum(c['defaulted']) for c in empty):,.0f}", fsrc)
    gap = sp["definition_gap"]
    num("real.sp.B.d4d2", pct(gap["d4_over_d2"][B], 0), "data/derived/C04/sp.json outputs.definition_gap.d4_over_d2[5]")
    num("real.sp.CCC.d4d2", pct(gap["d4_over_d2"][6], 0), "data/derived/C04/sp.json outputs.definition_gap.d4_over_d2[6]")

    # ---- the numerical checks of the propositions
    cf, bj, tp_, ai, jl, ct = (thy["checks"][k] for k in ("closed_forms", "bijection", "tipping", "anchor_identity", "jeffreys_lemma", "containment"))
    tsrc = "experiments/results/theory-checks.json"
    num("th.draws", f"{thy['draws']:,}", tsrc)
    num("th.lemma.counts", f"{jl['counts_checked']:,.0f}", f"{tsrc} checks.jeffreys_lemma.counts_checked")
    num("th.lemma.nmax", f"{jl['n_max']:,.0f}", f"{tsrc} checks.jeffreys_lemma.n_max")
    num("th.lemma.viol", f"{jl['violations']:.0f}", f"{tsrc} checks.jeffreys_lemma.violations")
    num("th.anchor.k", f"{ai['anchor_k_max_rel']:.1e}", f"{tsrc} checks.anchor_identity.anchor_k_max_rel")
    num("th.anchor.pd", f"{ai['anchor_pd_max_abs']:.1e}", f"{tsrc} checks.anchor_identity.anchor_pd_max_abs")
    num("th.tip.err", f"{tp_['tipping_roundtrip_max_abs']:.1e}", f"{tsrc} checks.tipping.tipping_roundtrip_max_abs")
    num("th.round.rel", f"{bj['roundtrip_max_rel_count']:.1e}", f"{tsrc} checks.bijection.roundtrip_max_rel_count")
    num("th.limit", f"{max(cf['limit_k0_max_abs'], cf['limit_k1_max_abs'], cf['limit_kinf_max_abs']):.1e}", f"{tsrc} checks.closed_forms.limit_*")
    num("th.contain.n", f"{ct['cohorts_checked']:,.0f}", f"{tsrc} checks.containment.cohorts_checked")
    num("th.contain.viol", f"{ct['violations']:.0f}", f"{tsrc} checks.containment.violations")
    num("th.width.med", f"{ct['median_width_ratio']:.2f}", f"{tsrc} checks.containment.median_width_ratio")
    num("th.width.max", f"{ct['max_width_ratio']:.2f}", f"{tsrc} checks.containment.max_width_ratio")
    num("th.lemma.large", ", ".join(f"{x:,.0f}" for x in jl["large_n"]), f"{tsrc} checks.jeffreys_lemma.large_n")
    num("th.half", f"{cf['half_saturation_max_abs']:.1e}", f"{tsrc} checks.closed_forms.half_saturation_max_abs")

    # ================================================================================================ tables
    tbl(
        out / "tab-design.tex", ["Study", "Factor levels", "Repetitions", "Seed key"],
        [["Coverage grid", "informativeness $\\iota\\in\\{0,1,3,9,19\\}$; first-year cohort and five cohorts pooled", f"{reps:,}",
          "\\texttt{ms-bs14:\\allowbreak informative=$\\iota$}"],
         ["Ten-fold cohort", "$\\iota\\in\\{0,1,3,9,19\\}$; every grade's cohort ten times the case's", f"{reps:,}",
          "\\texttt{ms-bs14:\\allowbreak informative=$\\iota$:x10}"],
         ["Scale ladder", "$\\iota=9$; cohorts 3 and 30 times the case's", f"{scale_cells[(3, 9.0)]['reps']:,}",
          "\\texttt{ms-bs14:\\allowbreak informative=9:x3}, \\texttt{:x30}"],
         ["Mismatch ladder", "$\\iota\\in\\{3,9\\}$; the second source counts 0.5, 0.7, 0.8, 0.9, 1.1 or 1.3 times the defaults",
          f"{reps:,}", "the grid's draws of $\\iota$"],
         ["Stability", "$\\iota\\in\\{3,9\\}$; second source exact, counting 1.3 times the defaults, or a multiple drawn each year from 1.0 to 1.6 or from 1.0 to 4.0; BB, B, CCC to C", f"{reps:,}",
          "\\texttt{ms-bs14:\\allowbreak stability:\\allowbreak informative=$\\iota$}"],
         ["Duration estimator", "$\\iota\\in\\{0,1,3,9,19\\}$; five-year paths, withdrawals as right censoring",
          f"{dur['data'][0]['reps']} ({dur['data'][0]['n_boot']} bootstrap replicates)",
          "\\texttt{ms-bs14:\\allowbreak duration:\\allowbreak informative=$\\iota$}"],
         ["Product's committed study", "$\\iota\\in\\{0,1,3,9\\}$; first-year, pooled, 70\\% capture, ten-fold",
          str(wd["outputs"]["bounds_verdict"]["reps"]), "\\texttt{withdrawals-bounds:\\allowbreak informative=$\\iota$}"]],
        caption="Design of the known-truth studies: the factor levels, the repetitions per cell and the seed key from which each cell's "
                "streams are derived with the case seed 42, for the studies of this paper and for the study the product commits.",
        label="tab:design", align="p{2.2cm}p{5.3cm}p{2.3cm}p{4.4cm}")

    # main results at iota 9
    rows = []
    for des in ("fy", "pool", "x10"):
        c = cells[(des, 9.0)]
        for t in TR:
            tt = c["treatments"][t]
            rows.append([DES[des] if t == TR[0] else "", TR_NAME[t], cell(tt["coverage"][B], tt["mcse"][B]),
                         f"{100 * tt['width'][B]:.2f}",
                         "--" if t == "identified" else f"${100 * tt['rel_bias'][B]:+.1f}\\pm{100 * tt['rel_bias_mcse'][B]:.1f}$"])
    d9 = next(r for r in dur["data"] if r["informative"] == 9.0)
    rows.append(["five-year paths", "Duration estimator (censoring)", cell(d9["coverage"][B], d9["mcse"][B], 0), "--",
                 f"${100 * d9['rel_bias'][B]:+.1f}\\pm{100 * d9['rel_bias_mcse'][B]:.1f}$"])
    tbl(
        out / "tab-main-results.tex",
        ["Design", "Treatment", "Coverage (\\%)", "Width (pp)", "Bias (\\%)"], rows,
        caption=f"Coverage of the true one-year PD of grade B ({num('truthB', pct(cells[('fy', 9.0)]['truth'][B], 2), 'x')}\\%) at informativeness 9, by design and treatment: "
                f"coverage with its Monte Carlo standard error over {reps:,} repetitions, mean width of the 95\\% interval in percentage points, and relative "
                "bias of the point estimate with its standard error; the duration estimator row uses 100 repetitions and a resampling bootstrap on five-year paths.",
        label="tab:main-results", align="llrrr", wide=False)

    # coverage grid
    rows = []
    for des in ("fy", "pool", "x10"):
        for t in TR:
            if t in ("unfollowed", "band"):
                continue
            rows.append([DES[des] if t == "industry" else "", TR_NAME[t]]
                        + [cell(cells[(des, i)]["treatments"][t]["coverage"][B]) for i in INF])
    tbl(
        out / "tab-grid.tex", ["Design", "Treatment"] + [f"$\\iota={i:g}$" for i in INF], rows,
        caption=f"Coverage (\\%) of the true one-year PD of grade B by informativeness of withdrawal in the generator, for the first-year cohort, the "
                f"five cohorts pooled and the cohort ten times larger, {reps:,} repetitions per cell; the Monte Carlo standard error of a coverage near "
                f"95\\% is {num('mcse.nominal', pct(math.sqrt(0.95 * 0.05 / reps), 1), 'x')} points.",
        label="tab:grid", align="llrrrrr")

    # scale ladder
    rows = []
    for sc, key in ((1, "fy"), (3, "x3"), (10, "x10"), (30, "x30")):
        c = cells[(key, 9.0)]
        row = [f"$\\times{sc}$", f"{c['reps']:,}"]
        for t in ("industry", "followed", "anchored"):
            row.append(cell(c["treatments"][t]["coverage"][B], c["treatments"][t]["mcse"][B]))
        row += [f"{100 * c['treatments']['anchored']['width'][B]:.2f}", f"{100 * c['treatments']['followed']['width'][B]:.2f}",
                f"{100 * c['treatments']['identified']['width'][B]:.2f}"]
        rows.append(row)
    tbl(
        out / "tab-scale.tex",
        ["Cohort", "Reps", "Removed", "Followed", "Anchored", "$W_{\\rm anch}$", "$W_{\\rm fol}$", "$W_{\\rm Manski}$"], rows,
        caption="Coverage (\\%) of grade B's true one-year PD at informativeness 9 as the cohort grows from the case's size to thirty times it, "
                "for the removed, followed and anchored treatments with Monte Carlo standard errors, and the mean widths in percentage points of the "
                "anchored interval, the followed interval and the Manski band.",
        label="tab:scale", align="llrrrrrr", size=bs + "footnotesize")

    # hypotheses
    v = wd["outputs"]["bounds_verdict"]
    h1 = [cells[(d, i)]["treatments"]["anchored"]["coverage"][B] for d in ("fy", "pool") for i in (1.0, 3.0, 9.0)]
    h1.append(cells[("x10", 9.0)]["treatments"]["anchored"]["coverage"][B])
    num("h1.min", pct(min(h1)), S_GRID + " anchored coverage, minimum over the designs and iota 1, 3, 9")
    h1_19 = cells[("pool", 19.0)]["treatments"]["anchored"]["coverage"][B]
    rows = [
        ["H1", "anchored coverage at $\\iota=1,3,9$", f"{pct(min(h1))} to {pct(max(h1))}", "at least 90", "holds"],
        ["H2", "removed and kept coverage at $\\iota=9$",
         "; ".join(f"{DES[d]} {pct(cells[(d, 9.0)]['treatments']['industry']['coverage'][B], 0)}/{pct(cells[(d, 9.0)]['treatments']['unfollowed']['coverage'][B], 0)}"
                   for d in ("fy", "pool", "x10")), "under 50",
         "holds in two of three designs"],
        ["H2'", "followed (oracle) coverage at $\\iota=9$",
         "; ".join(f"{pct(cells[(d, 9.0)]['treatments']['followed']['coverage'][B], 0)}" for d in ("fy", "pool", "x10")), "under 50", "fails in all three"],
        ["H3", "anchored minus best existing coverage at $\\iota=9$",
         "; ".join(f"{100 * (cells[(d, 9.0)]['treatments']['anchored']['coverage'][B] - max(cells[(d, 9.0)]['treatments'][t]['coverage'][B] for t in ('industry', 'unfollowed', 'followed'))):+.1f}"
                   for d in ("fy", "pool", "x10")), "above 0", "holds"],
        ["H4", "share of cohorts whose band holds the pooled $k$, S\\&P grade B and CCC to C",
         f"{pct(next(g for g in sp['withdrawal_bounds']['grades'] if g['grade'] == 'B')['stability']['share_cohorts_containing_pooled_k'], 0)}; "
         f"{pct(next(g for g in sp['withdrawal_bounds']['grades'] if g['grade'] == 'CCC-C')['stability']['share_cohorts_containing_pooled_k'], 0)}",
         "at least 80", "fails"],
        ["H5", "pooled anchored $k$ of CCC to C, S\\&P", f"{next(g for g in sp['withdrawal_bounds']['grades'] if g['grade'] == 'CCC-C')['pooled']['k']:.1f}", "above 1", "holds"],
    ]
    tbl(
        out / "tab-hypotheses.tex", ["Id", "Quantity", "Measured (\\%, or $k$)", "Criterion", "Outcome"], rows,
        caption="The predictions stated before the experiments and their outcome: the quantity each measures, the value measured in the first-year, "
                "pooled and ten-fold designs (in that order where three are given), the criterion, and whether it held at the repetitions of the grid.",
        label="tab:hypotheses", align="lp{4.6cm}p{4.2cm}p{1.8cm}p{2.4cm}")
    num("h2.fy.ind", pct(cells[("fy", 9.0)]["treatments"]["industry"]["coverage"][B], 1), S_GRID)
    num("h1.pool19", pct(h1_19), S_GRID + " pooled informative 19 anchored")

    # ablation
    rows = []
    variants = (("industry", "Removed estimate with a Jeffreys interval (no anchor, no family)"),
                ("identified", "Manski band (family and its bounds, no anchor)"),
                ("band", "Anchored $k$ band alone, mapped through PD$(k)$ and clipped to the identified set"),
                ("anchored", "Anchored interval (band, clipping and outer Jeffreys interval)"))
    for i in (1.0, 9.0):
        for t, name in variants:
            cs = [cells[(d, i)]["treatments"][t] for d in ("fy", "pool", "x10")]
            rows.append([f"$\\iota={i:g}$" if t == "industry" else "", name]
                        + [cell(c["coverage"][B]) for c in cs]
                        + [f"{100 * cs[0]['width'][B]:.2f}", "--" if t == "identified" else f"${100 * cs[0]['rel_bias'][B]:+.1f}$"])
    tbl(
        out / "tab-ablation.tex",
        ["", "Components retained", "First", "Pooled", "$\\times10$", "$W$ (pp)", "Bias (\\%)"], rows,
        caption="Ablation on grade B at informativeness 1 and 9: coverage (\\%) in the first-year, pooled and ten-fold designs, and the width (percentage "
                "points) and relative bias of the first-year design, as the second source, the family PD$(k)$, the clipping to the identified set and the "
                "outer Jeffreys interval are retained or removed.",
        label="tab:ablation", align="p{0.9cm}p{6.1cm}rrrrr")

    # capture ladder
    rows = []
    for c in sorted((c for c in cap["data"] if c["informative"] == 9.0), key=lambda c: c["capture"]):
        a = c["treatments"]["anchored"]
        rows.append([f"{c['capture']:g}", cell(a["coverage"][B], a["mcse"][B]), cell(c["treatments"]["band"]["coverage"][B]),
                     f"{100 * a['width'][B]:.2f}", f"${100 * a['rel_bias'][B]:+.1f}$", f"{c['k']['anchored_median'][B]:.1f}"])
    c1 = cells[("fy", 9.0)]
    a1 = c1["treatments"]["anchored"]
    rows.append(["1 (exact)", cell(a1["coverage"][B], a1["mcse"][B]), cell(c1["treatments"]["band"]["coverage"][B]),
                 f"{100 * a1['width'][B]:.2f}", f"${100 * a1['rel_bias'][B]:+.1f}$", f"{c1['k']['anchored_median'][B]:.1f}"])
    rows.sort(key=lambda r: float(r[0].split()[0]))
    tbl(
        out / "tab-capture.tex",
        ["Capture $c$", "Anchored (\\%)", "Band alone (\\%)", "Width (pp)", "Bias (\\%)", "Median $k$"], rows,
        caption="Grade B at informativeness 9 when the second source counts $c$ times the true defaults (below 1) or counts them and other events "
                "at rate $c-1$ (above 1): coverage of the anchored interval with its standard error, coverage of the band alone, mean width, "
                "relative bias of the anchored point and the median anchored odds ratio, the realised one being the exact-source row.",
        label="tab:capture", align="lrrrrr")

    # stability
    rows = []
    for s in stab["data"]:
        rows.append([f"$\\iota={s['informative']:g}$", CAP_LABEL[s["capture"]], GRADE_TEX.get(s["grade"], s["grade"]),
                     cell(s["mean_share"], s["mean_share_mcse"]), cell(s["share_stable_at_80"]),
                     f"{s['median_pooled_k']:.1f}" if s["median_pooled_k"] is not None else "--"])
    tbl(
        out / "tab-stability.tex",
        ["Informativeness", "Capture", "Grade", "Cohorts holding pooled $k$ (\\%)", "Repetitions stable (\\%)", "Median pooled $k$"], rows,
        caption=f"Stability criterion on known truth: over {reps:,} repetitions of five annual cohorts, the mean share of cohorts whose anchored $k$ band "
                "contains the pooled anchored $k$ with its standard error, the share of repetitions that reach the 80\\% criterion, and the median pooled "
                "anchored $k$, for an exact second source and one counting 70\\% of the defaults.",
        label="tab:stability", align="lllp{2.6cm}p{2.3cm}r", size=bs + "footnotesize")

    # real data
    rows = []
    for key, (name, o, _) in sources.items():
        for g in o["withdrawal_bounds"]["grades"]:
            p = g["pooled"]
            if p is None or p["k"] is None or g["stability"] is None:
                continue
            st, tp = g["stability"], g["tipping"]
            rows.append([name if g is next(x for x in o["withdrawal_bounds"]["grades"] if x["pooled"] and x["pooled"]["k"] is not None) else "",
                         GRADE_TEX.get(g["grade"], g["grade"]), pct(p["pd_industry"], 2),
                         f"{pct(p['pd_anchored'], 2)} ({pct(p['pd_lower'], 2)} to {pct(p['pd_upper'], 2)})",
                         f"{p['k']:.1f} ({p['k_low']:.1f} to {p['k_high']:.1f})",
                         f"{st['cohorts_containing_pooled_k']} of {st['usable_cohorts']}",
                         f"{tp['k']:.1f}" if tp and tp["k"] is not None else "--"])
    tbl(
        out / "tab-real.tex",
        ["Agency", "Grade", "PD removed (\\%)", "Anchored PD (\\%)", "Pooled $k$ (band)", "Cohorts holding it", "Tipping $k$"], rows,
        caption="Anchored withdrawal bounds on the agencies' real cohorts of ESMA's central repository, the default page as the second source of the "
                "transition page: the pooled PD with withdrawals removed, the anchored PD with its interval, the pooled anchored odds ratio with its band, "
                "the cohorts whose band contains it, and the tipping odds ratio that moves the grade to the next one.",
        label="tab:real", align="llrp{2.4cm}p{2.6cm}rr", size=bs + "footnotesize")

    # decisions
    rows = []
    for des in ("fy", "pool", "x10"):
        c = cells[(des, 9.0)]
        for t in ("industry", "followed", "anchored"):
            d = c["decisions"]["by_treatment"][t]
            rows.append([DES[des] if t == "industry" else "", {"industry": "Removed", "followed": "Followed (oracle)",
                                                               "anchored": "Anchored"}[t]]
                        + [f"{pct(d[k]['correct'], 0)} / {pct(d[k]['wrong'], 0)} / {pct(d[k]['undetermined'], 0)}"
                           for k in ("-0.30", "-0.15", "+0.15", "+0.30")])
    tbl(
        out / "tab-decisions.tex",
        ["Design", "Treatment", "$\\delta=-0.30$", "$\\delta=-0.15$", "$\\delta=+0.15$", "$\\delta=+0.30$"], rows,
        caption=f"Threshold decisions on grade B at informativeness 9, for a threshold $t=\\mathrm{{PD}}(1+\\delta)$ around the true PD: the percentage of "
                f"{reps:,} repetitions in which the 95\\% interval lies on the correct side, on the wrong side, or across the threshold (correct / wrong / "
                "undetermined).",
        label="tab:decisions", align="llrrrr", size=bs + "footnotesize")

    # theory checks
    rows = [["Limits of PD$(k)$ at $k=0,1,\\infty$", "max abs. deviation", f"{max(cf['limit_k0_max_abs'], cf['limit_k1_max_abs'], cf['limit_kinf_max_abs']):.1e}"],
            ["Strict monotonicity of PD$(k)$ on 11 values of $k$", "share of cohorts", f"{cf['strictly_increasing_share']:.2f}"],
            ["Concavity of $X(k)$", "share of cohorts", f"{cf['concave_share']:.2f}"],
            ["Half saturation $X(S/D)=W/2$", "max abs. deviation (ratings)", f"{cf['half_saturation_max_abs']:.1e}"],
            ["Inverse $k(X)$ then $X(k)$", "max rel. deviation", f"{bj['roundtrip_max_rel_count']:.1e}"],
            ["Tipping $k^*$ then PD$(k^*)=t$", "max abs. deviation", f"{tp_['tipping_roundtrip_max_abs']:.1e}"],
            ["Exact anchor returns the realised $k$", "max rel. deviation", f"{ai['anchor_k_max_rel']:.1e}"],
            ["Exact anchor returns $(D+X)/N$", "max abs. deviation", f"{ai['anchor_pd_max_abs']:.1e}"],
            [f"Jeffreys limits bracket $C/N$, every $C$ for $N\\le{jl['n_max']:,.0f}$ and for $N$ = " + ", ".join(f"{x:,.0f}" for x in jl["large_n"]),
             "violations in " + f"{jl['counts_checked']:,.0f}" + " counts", f"{jl['violations']:.0f}"],
            ["Anchored interval contains the oracle's Jeffreys interval (exact anchor)", f"violations in {ct['cohorts_checked']:,.0f} cohorts",
             f"{ct['violations']:.0f}"],
            ["Width of the anchored interval over the oracle's (exact anchor)", "median; maximum", f"{ct['median_width_ratio']:.2f}; {ct['max_width_ratio']:.2f}"]]
    tbl(
        out / "tab-theory-checks.tex", ["Property", "Measure", "Value"], rows,
        caption=f"Numerical checks of the propositions of the theory section on {thy['draws']:,} random cohorts (defaults 1 to 500, survivors 1 to 50,000, "
                "withdrawals 1 to 5,000) and on every binomial count up to the stated cohort size, run through the engine's functions.",
        label="tab:theory-checks", align="p{6.6cm}p{4.4cm}r")

    # numbers
    tex = ["% generated by tables/make_tables.py: do not edit"]
    for k, (text, _) in sorted(NUMS.items()):
        tex.append(f"\\expandafter\\def\\csname num@{k}\\endcsname{{{text}}}")
    (out / "numbers.tex").write_text("\n".join(tex) + "\n", encoding="utf-8", newline="\n")
    (out / "numbers.json").write_text(json.dumps({k: {"text": t, "source": s} for k, (t, s) in sorted(NUMS.items())}, indent=0) + "\n",
                                      encoding="utf-8", newline="\n")
    print(f"{len(NUMS)} numbers, tables written to {out}")


if __name__ == "__main__":
    main()
