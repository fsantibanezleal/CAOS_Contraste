"""Write the booktabs tables of the manuscript into ``tables/`` from the committed C22 documents and the experiment results.

    python manuscripts/size-and-power-of-validation-tests/make_tables.py

Every cell is a number of ``analysis.py``; a new bake of C22 or a new run of the experiments regenerates the tables.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import analysis as A  # noqa: E402
import make_numbers  # noqa: E402  (the detectable excess of the one-sided bound)

OUT = HERE / "tables"
NL = "\n"
SMALL, FOOT = r"\small", r"\footnotesize"
PCT = r"\%"
PM = r"$\pm$"


def pc(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def ci(lo: float, hi: float, d: int = 2) -> str:
    return f"[{pc(lo, d)}, {pc(hi, d)}]"


def write(name: str, header, rows, *, caption: str, label: str, align: str, font: str = SMALL, wide: bool = False) -> None:
    """A booktabs table; every cell is LaTeX already (the callers format the numbers and escape the text)."""
    env = "table*" if wide else "table"
    lines = [rf"\begin{{{env}}}[htbp]", r"\centering", font, rf"\caption{{{caption}}}", rf"\label{{{label}}}",
             rf"\fitwidth{{\begin{{tabular}}{{{align}}}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(str(c) for c in r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}}", rf"\end{{{env}}}", ""]
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}.tex").write_text(NL.join(lines), encoding="utf-8", newline=NL)


def design() -> None:
    fam = {f["variant"]: f for f in A.families_of_defects()}
    spec = [
        ("null", "Null family", "each test at the boundary of its null", "none", "21 tests"),
        ("miscalibration", "Miscalibration", "true PD / PD applied", "1, 1.1, 1.25, 1.5, 2, 3", "9 calibration tests"),
        ("clustering", "Default clustering", "asset correlation, PDs right", "0, 0.02, 0.05, 0.10, 0.15, 0.20", "8 calibration tests"),
        ("drift", "Drift", "mean shift (standard deviations)", "0, 0.05, 0.1, 0.2, 0.3, 0.5", "3 stability and 2 calibration tests"),
        ("discrimination-decay", "Discrimination decay", "AUC drop from 0.80", "0, 0.01, 0.02, 0.03, 0.05, 0.08", "2 discrimination tests"),
        ("leakage", "Leakage", "shift of the leaked feature", "0, 0.25, 0.5, 1, 1.5, 2", "AUC test, CSI, DeLong on nested models"),
        ("broken-monotonicity", "Broken monotonicity", "planted cell / closer neighbour", "1, 1.25, 1.5, 2, 3, 4", "migration z-tests; 2 calibration tests"),
        ("concentration", "Concentration", "share moved into the modal grade", "0, 0.01, 0.02, 0.05, 0.10, 0.50", "2 tests"),
    ]
    rows = []
    for v, name, unit, ladder, tests in spec:
        f = fam[v]
        rows.append([name, unit, ladder, tests, f"{f['sims']}", f"{f['reps']:,}", f"{f['generators']}"])
    write("design", ["Family", "Severity unit", "Ladder", "Tests measured", "Sims", "Repetitions", "Generators"], rows,
          caption="The eight families of the measurement: the defect planted, the unit and values of its severity ladder, the tests measured, "
                  "and the number of simulations, seeded repetitions and generators of known truth in each family (credit-family tests only).",
          label="tab:design", align="llllrrr", font=FOOT, wide=True)


def yn(b: bool) -> str:
    """A judgement cell: a test that does not hold its size is set in bold."""
    return "yes" if b else r"\textbf{no}"


def main_results() -> None:
    cv = {r["test"]: r for r in A.committed_verdict_vs_pooled()}
    rows = []
    for r in A.size_table():
        e = r["exact"]
        c = cv[r["test"]]
        rows.append([r["name"], f"{pc(r['p<0.05']['rate'], 2)} {PM} {pc(r['p<0.05']['se'], 2)}", ci(r["p<0.05"]["lo"], r["p<0.05"]["hi"]),
                     f"{pc(r['p<0.01']['rate'], 2)} {PM} {pc(r['p<0.01']['se'], 2)}", ci(r["p<0.01"]["lo"], r["p<0.01"]["hi"]),
                     f"{pc(e['p<0.05'], 2)} / {pc(e['p<0.01'], 2)}" if e else "--", yn(c["cell_rule"]), yn(c["cell_definition"]),
                     yn(c["pool_definition"])])
    write("main-results", ["Test", rf"Size at 5{PCT} ({PM} SE)", rf"Wilson 95{PCT}", rf"Size at 1{PCT} ({PM} SE)", rf"Wilson 95{PCT}",
                           rf"Exact 5{PCT} / 1{PCT}", "Screen, 4,000", "Holds, 4,000", "Holds, 200,000"], rows,
          caption=r"Measured size, in percent, of the 21 credit-family tests on a generator where each test's null holds at its boundary "
                  r"(4,000 repetitions), with the Monte Carlo standard error, the Wilson 95\% interval and the exact rejection probability where the "
                  r"test has one; then three judgements: the screen of Algorithm 1 on the cell of 4,000 repetitions, the definition of holding a size on the same "
                  r"cell, and the definition on the pool of 50 further blocks (200,000 repetitions, \cref{tab:seed-replication}). By the definition a test "
                  r"holds its size unless its exact rejection probability, or the Wilson interval of its rate, lies above the level at 5\% or at 1\%.",
          label="tab:main-results", align="lrlrlcccc", font=FOOT, wide=True)


def power_summary() -> None:
    rows = []
    for t in A.HAS_POWER:
        curve = A.main_curve(t)
        s = A.severity_at_power(curve)
        v, _panel = A.MAIN_CURVE[t]
        unit = A.doc(v)["outputs"]["ladder"]["label"]["en"]
        pw = [pc(r["rates"]["p<0.05"]["rate"], 1) for r in curve]
        xs = [f"{r['x']:g}" for r in curve]
        if s["x"] is None:
            reach = "not reached"
        else:
            hi = f"{s['x_high']:.3g}" if s["x_high"] is not None else ">" + xs[-1]
            reach = f"{s['x']:.3g} [{s['x_low']:.3g}, {hi}]"
        rows.append([A.NAME[t], f"{unit} ({xs[0]} to {xs[-1]})", *pw, reach])
    write("power-summary", ["Test", "Defect and ladder (severity 0 to 5)", "0", "1", "2", "3", "4", "5", rf"Setting at 80{PCT} power [95{PCT}]"], rows,
          caption=r"Measured power at 5\%, in percent, of the 17 tests with a power curve at the six severities 0 to 5 of the ladder of the "
                  r"defect planted for each (2,000 repetitions per severity), and the setting of the ladder at which the interpolated curve first reaches 80\% "
                  r"with the interval given by the Wilson limits of the points.",
          label="tab:power-summary", align="llrrrrrrl", font=FOOT, wide=True)


def reproductions() -> None:
    rows = []
    for r in A.reproductions():
        dis = "; ".join(f"{c['row']}, {c['column']}: printed {c['published']:.3g}, measured {c['measured']:.4g}"
                        for c in r["disagreeing"]).replace("%", PCT).replace(">", "$>$").replace("_", r"\_") or "none"
        rows.append([r["title"], f"{r['runs_published']:,} / {r['runs']:,}", f"{r['agree']} of {r['total']}", f"{r['mean_z']:+.2f}", dis])
    write("reproductions", ["Published study", "Runs: printed / ours", "Cells agreeing", "Mean z", "Cells that disagree"], rows,
          caption=r"The three published simulation studies rerun by the measurement: the runs of the study and of the rerun, the cells whose printed "
                  r"rate agrees with the measured one within 3.29 pooled standard errors, the mean z of the differences, and each cell that disagrees.",
          label="tab:reproductions", align="p{4.2cm}rrrp{5.3cm}", font=FOOT, wide=True)


def settings() -> None:
    rows = []
    for r in A.settings_rows():
        main = r["p<0.05"]
        extra = ""
        if "metric>0.1" in r:
            extra = f"PSI above 0.10: {pc(r['metric>0.1']['rate'], 1)}; above 0.25: {pc(r['metric>0.25']['rate'], 1)}"
        ex = f"{pc(r['exact']['p<0.05'], 2)} / {pc(r['exact']['p<0.01'], 2)}" if r["exact"] else "--"
        rows.append([A.NAME.get(r["test"], r["test"]), r["scenario"].replace("%", PCT).replace("−", "$-$"), f"{r['n']:,}",
                     f"{pc(main['rate'], 2)} {ci(main['lo'], main['hi'], 1)}", pc(r["p<0.01"]["rate"], 2), ex, extra])
    write("settings", ["Test", "Setting", "Reps", rf"Size at 5{PCT} [Wilson]", rf"Size at 1{PCT}", rf"Exact 5{PCT} / 1{PCT}", "Other rule"], rows,
          caption=r"The settings of a test that change its measured size on the same null generator: Hosmer--Lemeshow with two fewer degrees of freedom, "
                  r"the traffic lights with the upper tie rule, a chi-square over a thin grade, the AUC test with an estimated development AUC and its "
                  r"extension, a longer run of the order test, and the PSI rules of thumb in samples of 100.",
          label="tab:settings", align="p{2.4cm}p{4.6cm}rllcp{2.6cm}", font=FOOT, wide=True)


def seed_replication() -> None:
    rep = A.seed_replication()["tests"]
    cv = {r["test"]: r for r in A.committed_verdict_vs_pooled()}
    size = {r["test"]: r for r in A.size_table()}
    rows = []
    for t in A.TEST_ORDER:
        a, b = rep[t]["p<0.05"], rep[t]["p<0.01"]
        rows.append([A.NAME[t], pc(size[t]["p<0.05"]["rate"], 2), f"{pc(a['pooled'], 2)} {ci(a['pooled_lo'], a['pooled_hi'])}",
                     f"{pc(a['sd_blocks'], 2)} / {pc(a['se_binomial'], 2)}", pc(a["flag_bound_4000"], 0) + " / " + pc(a["flag_naive_4000"], 0),
                     pc(size[t]["p<0.01"]["rate"], 2), f"{pc(b['pooled'], 2)} {ci(b['pooled_lo'], b['pooled_hi'])}",
                     f"{'yes' if cv[t]['cell_rule'] else 'no'} / {'yes' if cv[t]['pool_rule'] else 'no'}",
                     f"{yn(cv[t]['cell_definition'])} / {yn(cv[t]['pool_definition'])}"])
    write("seed-replication", ["Test", rf"Cell 5{PCT}", rf"Pooled 5{PCT} [Wilson]", "SD / SE of blocks", rf"Flagged: bound / naive ({PCT})",
                               rf"Cell 1{PCT}", rf"Pooled 1{PCT} [Wilson]", "Screen: cell / pool", "Definition: cell / pool"], rows,
          caption=r"Fifty independent blocks of 4,000 repetitions (200,000 in all) for each of the 21 tests: the committed cell, the pooled rate with its "
                  r"Wilson interval, the standard deviation of the block rates beside the binomial standard error at 5\%, the share of blocks flagged by "
                  r"the one-sided bound and by the rule that a rate above the level is oversized, and the judgement of the committed cell and of the pool by "
                  r"the screen of Algorithm 1 and by the definition of holding a size (a test does not hold its size when its exact rejection probability, or the Wilson interval "
                  r"of its rate, lies above the level at 5\% or at 1\%).",
          label="tab:seed-replication", align="lrlcrrlcc", font=FOOT, wide=True)


EXT_NAME = {
    "ccr.pfe_exceedance_backtest": "PFE exceedance back-test", "ifrs9.stage_migration_backtest": "IFRS 9 stage-migration back-test",
    "lgd_ead.lgd_calibration_by_segment": "LGD calibration by segment", "lgd_ead.lgd_calibration_over_time": "LGD calibration over time",
    "lgd_ead.downturn_coverage": "Downturn LGD coverage", "market.mcneil_frey_residual_test": "McNeil--Frey residual test",
    "portfolio.tail_backtest": "Tail back-test (LHP quantile)", "portfolio.mc_convergence": "Monte Carlo quantile convergence",
    "portfolio.crp_recursion_vs_mc": "CreditRisk+ recursion against Monte Carlo", "fair.two_proportion_z": "Two-proportion z (fairness)",
    "fair.fisher_exact": "Fisher exact (fairness)", "market.kupiec_pof": "Kupiec proportion of failures",
    "market.christoffersen_independence": "Christoffersen independence",
    "market.christoffersen_conditional_coverage": "Christoffersen conditional coverage",
    "market.duration_test": "Duration test", "market.acerbi_szekely": r"Acerbi--Sz\'ekely ES test",
    "market.du_escanciano_unconditional": "Du--Escanciano, unconditional", "market.du_escanciano_conditional": "Du--Escanciano, conditional",
    "market.dynamic_quantile_test": "Dynamic quantile test", "ml.shift_resilience": "Shift resilience (ML)",
    "ml.conformal_coverage": "Conformal coverage (ML)",
}


def ext_label(e) -> str:
    return (EXT_NAME[e["test"]] + ", " + e["label"]).replace("%", PCT)


def extension() -> None:
    rows = []
    for e in A.extension_table():
        rows.append([ext_label(e), pc(e["size5"], 2), pc(e["size1"], 2), yn(e["holds_definition"]),
                     f"{pc(e['power5'], 1)} {PM} {pc(e['power5_se'], 1)}"])
    write("extension", ["Study", rf"Size at 5{PCT}", rf"Size at 1{PCT}", "Holds", rf"Power at 5{PCT} {PM} SE"], rows,
          caption=r"The 25 named studies of the 21 tests outside the credit families: the measured size at 5\% and 1\% (4,000 repetitions) on the null "
                  r"of each study, whether the study holds its size by the definition (no Wilson interval wholly above the level), and the power at 5\% against the one alternative the study states "
                  r"(2,000 repetitions), in percent.",
          label="tab:extension", align="p{7.4cm}rrcr", font=FOOT, wide=False)


def intervals() -> None:
    iv = A.interval_on_exact_rows()
    ps = ("0.001", "0.005", "0.01", "0.05", "0.5")
    grid = A.interval_coverage_grid(4000, tuple(float(p) for p in ps))
    nd, al = iv["_counts"]["nondegenerate"], iv["_counts"]["all"]
    rows = []
    for name in A.INTERVALS:
        rows.append([name, *[pc(grid[name][f"{float(p):g}"], 1) for p in ps], f"{iv[name]['nondegenerate']} of {nd}", f"{iv[name]['all']} of {al}"])
    write("interval-coverage", ["Interval", rf"$r=0.1${PCT}", rf"0.5{PCT}", rf"1{PCT}", rf"5{PCT}", rf"50{PCT}", f"Exact value inside ({nd})", f"Inside (all {al})"], rows,
          caption=r"Exact coverage, in percent, of five nominal 95\% intervals for a rejection rate measured in 4,000 repetitions, at five true rejection "
                  r"probabilities, and the number of the committed exact rejection probabilities that fall inside the interval of the simulated rate.",
          label="tab:interval-coverage", align="lrrrrrcc", font=FOOT, wide=False)


def resolution() -> None:
    rows = []
    fl = A.flag_rates_by_repetitions()
    for R, label in ((1000, "1,000"), (2000, "2,000"), (4000, "4,000"), (20000, "20,000"), (200000, "200,000")):
        row = [label, pc(make_numbers.detectable(0.05, R), 2), pc(make_numbers.detectable(0.01, R), 2),
               pc(A.interval_detectable(0.05, R), 2), pc(A.interval_detectable(0.01, R), 2)]
        if str(R) in fl:
            f = fl[str(R)]
            row += [pc(f["within_naive"], 1), pc(f["within_bound"], 2), pc(f["within_interval"], 2), pc(f["over_naive"], 1), pc(f["over_bound"], 1),
                    pc(f["over_interval"], 1)]
        else:
            row += ["--"] * 6
        rows.append(row)
    write("resolution", ["Repetitions", rf"Screen sees, 5{PCT}", rf"Screen sees, 1{PCT}", rf"Definition sees, 5{PCT}", rf"Definition sees, 1{PCT}",
                         "Within: naive", "Within: screen", "Within: definition", "Above: naive", "Above: screen", "Above: definition"], rows,
          caption=r"Resolution of a size measurement by the number of repetitions: the excess over the level (percentage points) that the one-sided bound "
                  r"of the screen and the Wilson interval of the definition detect with probability 0.8, and the share of cells (percent) flagged by the naive "
                  r"rule, the screen and the definition among the 10 tests whose pooled size is within the level and among the 9 whose pooled size is "
                  r"above it.",
          label="tab:resolution", align="lrrrrrrrrrr", font=FOOT, wide=True)


def main() -> int:
    OUT.mkdir(exist_ok=True)
    design()
    main_results()
    power_summary()
    reproductions()
    settings()
    seed_replication()
    extension()
    intervals()
    resolution()
    print("tables written to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
