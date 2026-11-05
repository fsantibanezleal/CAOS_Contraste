"""Tables and in-text numbers of the operational-risk chapter of the technical report (sections/14-oprisk.tex).

Every number the chapter prints is produced here from the committed documents of case C17 (``data/derived/C17``) or by a call to
the ``riskvalidation`` engine (the published benchmark of the aggregate loss); nothing is typed in the LaTeX. The one exception
is the study of contaminated histories of the engine documentation, whose cells are constants below with the lines of their
source. The script writes

* ``tables/oprisk-<name>.tex``: one booktabs ``table`` environment per result table (``figkit.table``);
* ``tables/oprisk-numbers.tex``: one ``\\newcommand`` per number the prose quotes (``\\op...``), so that a new release of the
  documents regenerates the text's figures with the tables.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_oprisk.py

``--registry <file.json>`` also writes every macro with its value and the source it was read from (an audit aid).
The figure script ``figures/make_oprisk.py`` imports ``load`` and the helpers of this module.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

OUT = HERE
SRC = "data/derived/C17"
#: (variant id, macro letter, tail index)
VARIANTS = (("xi-0-6", "A", 0.6), ("xi-0-8", "B", 0.8), ("xi-0-96", "C", 0.96), ("xi-1-1", "D", 1.1))
#: (cell id, short label, years, collection threshold in EUR)
CELLS = (
    ("y5-h10000", "5 years, EUR 10,000", 5, 10000),
    ("y5-h20000", "5 years, EUR 20,000", 5, 20000),
    ("y10-h10000", "10 years, EUR 10,000", 10, 10000),
    ("y10-h20000", "10 years, EUR 20,000", 10, 20000),
)
MAIN_CELL = "y10-h20000"
#: (key in the cell document, short name of the rung)
RUNGS = (
    ("lda_lognormal", "Lognormal, threshold ignored"),
    ("lda_lognormal_truncated", "Truncated lognormal"),
    ("lda_splice", "Lognormal and GPD splice"),
    ("sla", "Single loss approximation"),
    ("sla_mean_corrected", "SLA with mean correction"),
    ("scenario", "Scenario credibility"),
    ("sla_mean_adjusted", "GPD by likelihood, mean-adjusted SLA"),
    ("sla_cvm", "GPD by Cram\\'er-von Mises"),
    ("sla_obre", "GPD optimally bias-robust"),
    ("sla_cvm_lognormal", "Lognormal by Cram\\'er-von Mises (control)"),
)
RUNG_NAME = dict(RUNGS)
M24_RUNGS = ("lda_lognormal", "lda_lognormal_truncated", "lda_splice", "sla", "sla_mean_corrected", "scenario")
M32_RUNGS = ("lda_splice", "sla_mean_adjusted", "sla_cvm", "sla_obre", "sla_cvm_lognormal")

#: The study of contaminated histories of the engine documentation (docs/oprisk/06_robust-severity.md of CAOS_RiskValidation,
#: lines 71 to 74 for the ratios and 82 to 85 for the log errors): 250 losses above EUR 20,000, seed 20261028, 148 to 170
#: histories per scenario. Each cell is (median ratio, interquartile range, share of histories below half of the truth).
CONTAM_COLUMNS = ("MLE lognormal", "Cram\\'er-von Mises", "OBRE 95\\%", "OBRE 80\\%", "MLE splice")
CONTAM = (
    ("Lognormal truth", 165, ((0.94, 0.54, 1), (1.01, 0.69, 7), (0.97, 0.59, 2), (0.99, 0.69, 6), (0.74, 1.64, 30)), (0.29, 0.32, 0.30, 0.31, 0.76)),
    ("Lognormal truth, 3\\% gross losses", 160, ((7.70, 7.45, 0), (1.94, 1.98, 1), (3.90, 4.70, 0), (2.24, 2.73, 1), (17.07, 35.7, 0)), (2.04, 0.67, 1.36, 0.81, 2.83)),
    ("Splice truth", 170, ((0.30, 0.13, 92), (0.26, 0.10, 94), (0.27, 0.10, 98), (0.26, 0.10, 97), (0.46, 1.01, 53)), (1.21, 1.34, 1.31, 1.36, 0.99)),
    ("Splice truth, 3\\% gross losses", 148, ((4.52, 6.10, 0), (0.38, 0.21, 73), (0.71, 0.73, 30), (0.42, 0.30, 66), (9.09, 10.2, 0)), (1.51, 0.98, 0.62, 0.88, 2.21)),
)
#: the published values of Shevchenko's benchmark (docs/oprisk/02_aggregate-loss.md of CAOS_RiskValidation, lines 92 to 104)
BENCH_REF = {"mean": 738.9056, "variance": 298095.7987, "skewness": 40.3428, "h5849": 0.999000217, "quantile": 5849}

MACROS: dict[str, tuple[str, str]] = {}


def mac(name: str, value: Any, source: str) -> None:
    """Register ``\\op<name>`` with its value (a string is written as is) and where it was read."""
    MACROS[name] = (str(value), source)



def table(path: pathlib.Path, header, rows, **kw):
    """``figkit.table`` for rows that carry LaTeX: a string cell with math or a command is passed through, not escaped."""
    fixed = [[("\\relax " + c if isinstance(c, str) and ("$" in c or "\\" in c) and not c.startswith(("$", "\\")) else c) for c in r]
             for r in rows]
    out = figkit.table(path, header, fixed, **kw)
    # a table wider than the text is scaled down to the text width, a narrower one keeps its size
    text = out.read_text(encoding="utf-8")
    text = text.replace("\\begin{tabular}", "\\resizebox{\\ifdim\\width>\\textwidth\\textwidth\\else\\width\\fi}{!}{%\n\\begin{tabular}", 1)
    text = text.replace("\\end{tabular}", "\\end{tabular}}", 1)
    out.write_text(text, encoding="utf-8", newline="\n")
    return out


def load() -> dict[str, Any]:
    """The four variant documents and the models document of case C17, keyed by variant id."""
    d = {vid: figkit.doc(f"C17/{vid}.json") for vid, _, _ in VARIANTS}
    d["models"] = figkit.doc("C17/models-generator.json")
    return d


def cell(doc: dict, cid: str) -> dict:
    return next(c for c in doc["outputs"]["cells"] if c["id"] == cid)


def summ(c: dict, rung: str) -> dict | None:
    """The summary of a rung in a cell, None when the rung has no capital there (an infinite mean)."""
    r = c["capital"][rung]
    s = r.get("summary", r)
    return s if s and "ratio_to_truth" in s else None


def f2(x: float) -> str:
    return f"{x:.3f}" if x < 0.1 else f"{x:.2f}"


def eur_m(x: float, d: int = 1) -> str:
    return f"{x / 1e6:,.{d}f}"


def med_iqr(s: dict | None) -> str:
    return "--" if s is None else f"{f2(s['ratio_to_truth']['median'])} ({f2(s['iqr_over_truth'])})"


def share_def(s: dict | None) -> str:
    return "--" if s is None else f"{100 * s['share_underestimating']:.0f}% / {s['n_defined']}"


# ---------------------------------------------------------------------------------------------------------------------
# the cases and the generator
def t_cases(d: dict) -> None:
    fit = d["models"]["fit"]
    rows = []
    for (vid, L, xi), v in zip(VARIANTS, fit["variants"]):
        assert v["variant_id"] == vid
        cal = d[vid]["outputs"]["calibration"]["fit"]
        rows.append([f"{xi:g}", f"{v['lambda_per_year']:.1f}", f"{v['scale_eur']:,.0f}", eur_m(v["true_quantile_999_eur"]),
                     eur_m(v["true_mean_eur"]) if v["true_mean_eur"] is not None else "none", f"{cal['max_abs_log_error']:.3f}"])
        mac(f"Lam{L}", f"{v['lambda_per_year']:.1f}", f"{SRC}/models-generator.json fit.variants[{vid}].lambda_per_year")
        mac(f"Scale{L}", f"{v['scale_eur']:,.0f}", f"{SRC}/models-generator.json fit.variants[{vid}].scale_eur")
        mac(f"TrueQ{L}", eur_m(v["true_quantile_999_eur"]), f"{SRC}/models-generator.json fit.variants[{vid}].true_quantile_999_eur")
        mac(f"TrueMean{L}", eur_m(v["true_mean_eur"]) if v["true_mean_eur"] is not None else "none",
            f"{SRC}/models-generator.json fit.variants[{vid}].true_mean_eur")
        mac(f"CalErr{L}", f"{cal['max_abs_log_error']:.3f}", f"{SRC}/{vid}.json outputs.calibration.fit.max_abs_log_error")
    table(OUT / "oprisk-cases.tex",
                 [r"Tail index $\xi$", r"$\lambda$ (per year)", r"Scale $\beta$ (EUR)", r"True $q_{0.999}$ (EUR m)",
                  r"True mean (EUR m)", "Calibration error"],
                 rows, align="rrrrrr", label="tab:op-cases",
                 caption=r"The four variants of case C17: the tail index of the severity, the Poisson rate of losses at or above the "
                         r"generator floor of EUR 10,000, the fitted GPD scale above the floor, the true 99.9 percent annual loss quantile "
                         r"and mean of the compound loss of the generator, and the largest absolute error of the log excess quantiles against the "
                         r"four loss-collection percentiles. The mean does not exist at $\xi=1.1$.")
    qs = [v["true_quantile_999_eur"] for v in fit["variants"]]
    mac("QRatio", f"{qs[-1] / qs[0]:.0f}", f"{SRC}/models-generator.json fit.variants[*].true_quantile_999_eur, heaviest over lightest")
    cal = d["xi-0-96"]["outputs"]["calibration"]
    tg = cal["targets"]
    pct = tg["severity_percentiles"]
    mac("LdceFreq", f"{tg['frequency']['per_eur_bn_assets']}", f"{SRC}/xi-0-96.json outputs.calibration.targets.frequency")
    mac("LdceIqrLo", f"{tg['frequency']['iqr_low']}", f"{SRC}/xi-0-96.json outputs.calibration.targets.frequency")
    mac("LdceIqrHi", f"{tg['frequency']['iqr_high']}", f"{SRC}/xi-0-96.json outputs.calibration.targets.frequency")
    for k, nm in enumerate(("PA", "PB", "PC", "PD")):
        mac(nm, f"{pct[k]['loss_eur']:,.0f}", f"{SRC}/xi-0-96.json outputs.calibration.targets.severity_percentiles[{k}]")
    assets = d["xi-0-96"]["outputs"]["bank"]["assets_eur"]
    mac("Assets", f"{assets / 1e9:.0f}", f"{SRC}/xi-0-96.json outputs.bank.assets_eur")
    mac("ExpCount", f"{tg['frequency']['per_eur_bn_assets'] * assets / 1e9:.0f}", "0.82 x 50: LDCE frequency times the bank's assets")
    g = fit["grid"]
    mac("NRep", f"{g['n_replications_per_cell']:,}", f"{SRC}/models-generator.json fit.grid.n_replications_per_cell")
    mac("NHist", f"{g['n_replications_per_cell'] * len(VARIANTS) * len(CELLS):,}", "replications x 4 variants x 4 cells")
    mac("SeedBase", f"{g['seed_base']}", f"{SRC}/models-generator.json fit.grid.seed_base")
    ag = fit["aggregation"]
    mac("TruthMc", f"{ag['mc_years_truth']:,}", f"{SRC}/models-generator.json fit.aggregation.mc_years_truth")
    mac("RepMc", f"{ag['mc_years_replication']:,}", f"{SRC}/models-generator.json fit.aggregation.mc_years_replication")
    mac("FftPoints", f"{ag['fft_points']:,}", f"{SRC}/models-generator.json fit.aggregation.fft_points")
    mac("PanjerPoints", f"{ag['panjer_points']:,}", f"{SRC}/models-generator.json fit.aggregation.panjer_points")
    mac("PanjerStep", f"{ag['panjer_step_eur']:,.0f}", f"{SRC}/models-generator.json fit.aggregation.panjer_step_eur")
    mac("FftPad", f"{ag['fft_padding_factor']}", f"{SRC}/models-generator.json fit.aggregation.fft_padding_factor")
    sma = fit["sma"]
    mac("IlmExp", f"{sma['ilm_exponent']}", f"{SRC}/models-generator.json fit.sma.ilm_exponent")
    mac("LossMultiple", f"{sma['loss_multiple']}", f"{SRC}/models-generator.json fit.sma.loss_multiple")


# ---------------------------------------------------------------------------------------------------------------------
# the benchmark of the aggregate loss, computed by the engine
def t_benchmark() -> None:
    import numpy as np
    from riskvalidation.oprisk import aggregate as agg

    lam, sev = 100.0, (0.0, 2.0)
    mom = agg.compound_poisson_moments(lam, "lognormal", sev)
    f = agg.discretise_severity("lognormal", sev, 1.0, 6000, "central")
    h = agg.panjer_recursion("poisson", (lam,), f)
    q_pan = agg.quantile_from_pmf(h, 1.0, 0.999)
    hf = agg.fft_aggregate("poisson", (lam,), f, padding_factor=2)
    q_fft = agg.quantile_from_pmf(hf, 1.0, 0.999)
    cum = np.cumsum(h)
    h5849 = float(cum[5849])
    diff = float(np.max(np.abs(h - hf[: h.size])))
    sample = agg.simulate_annual_losses("poisson", (lam,), "lognormal", sev, 1_000_000, 2010, chunk_years=50_000)
    q_mc, se_mc = agg.mc_quantile(sample.losses, 0.999)
    mc_mean = float(np.mean(sample.losses))
    mc_se_mean = float(np.std(sample.losses, ddof=1) / np.sqrt(sample.losses.size))
    rows = [
        ["Mean $\\E[Z]$", f"{BENCH_REF['mean']:.4f}", f"{mom.mean:.4f}", f"{mc_mean:.2f} $\\pm$ {mc_se_mean:.2f} (Monte Carlo)"],
        ["Variance $\\Var[Z]$", f"{BENCH_REF['variance']:.4f}", f"{mom.variance:.4f}", "--"],
        ["Skewness", f"{BENCH_REF['skewness']:.4f}", f"{mom.skewness:.4f}", "--"],
        ["$H_{5849}$ (Panjer, step 1)", f"{BENCH_REF['h5849']:.9f}", f"{h5849:.9f}", f"{float(np.cumsum(hf)[5849]):.9f} (FFT)"],
        ["99.9\\% quantile, Panjer", f"{BENCH_REF['quantile']}", f"{q_pan:.0f}", "--"],
        ["99.9\\% quantile, FFT", f"{BENCH_REF['quantile']}", f"{q_fft:.0f}", "--"],
        ["99.9\\% quantile, Monte Carlo", "5853.1", f"{q_mc:.1f} $\\pm$ {se_mc:.1f}", "continuous quantile, not the discretised one"],
    ]
    table(OUT / "oprisk-benchmark.tex", ["Quantity", "Published", "Engine", "Second computation"], rows, align="lrrl",
                 label="tab:op-benchmark",
                 caption=r"The benchmark of the aggregate loss of \citet{oprisk:shevchenko2010}: a Poisson count with rate 100 and a lognormal "
                         r"severity with $\mu=0$, $\sigma=2$. Published values against the engine's moments, the Panjer recursion and the FFT on the "
                         r"grid of 6,000 points of step 1, and a Monte Carlo of one million years; the interval is one standard error.")
    mac("BenchMean", f"{mom.mean:.4f}", "engine compound_poisson_moments(100, lognormal, (0, 2))")
    mac("BenchVar", f"{mom.variance:.4f}", "engine compound_poisson_moments(100, lognormal, (0, 2))")
    mac("BenchSkew", f"{mom.skewness:.4f}", "engine compound_poisson_moments(100, lognormal, (0, 2))")
    mac("BenchPanjer", f"{q_pan:.0f}", "engine panjer_recursion + quantile_from_pmf, step 1, 6000 points")
    mac("BenchFft", f"{q_fft:.0f}", "engine fft_aggregate (padding 2) + quantile_from_pmf")
    mac("BenchMcQ", f"{q_mc:.1f}", "engine simulate_annual_losses, 1,000,000 years, seed 2010")
    mac("BenchMcSe", f"{se_mc:.1f}", "engine mc_quantile standard error")
    mac("BenchDiff", f"{diff:.1e}", "largest absolute difference of the Panjer and FFT probabilities per grid point")
    mac("BenchH", f"{h5849:.9f}", "engine Panjer cumulative at index 5849")


# ---------------------------------------------------------------------------------------------------------------------
# the true quantile by three computations and the SLA
def t_aggregation(d: dict) -> None:
    rows = []
    maxdiff = 0.0
    for vid, L, xi in VARIANTS:
        o = d[vid]["outputs"]
        q = o["exceedance"]["quantile_999_eur"]
        mc = o["truth"]["annual_loss_quantile"]["mc_check"]
        fft, pan, sla = q["fft"], q["panjer"], q["sla"]
        rows.append([f"{xi:g}", eur_m(fft), eur_m(pan), f"{eur_m(mc['value_eur'])} $\\pm$ {eur_m(mc['standard_error_eur'])}",
                     eur_m(sla), f"{100 * (sla / fft - 1):+.1f}\\%", f"{(mc['value_eur'] - fft) / mc['standard_error_eur']:+.1f}"])
        mac(f"FftQ{L}", eur_m(fft), f"{SRC}/{vid}.json outputs.exceedance.quantile_999_eur.fft")
        mac(f"PanQ{L}", eur_m(pan), f"{SRC}/{vid}.json outputs.exceedance.quantile_999_eur.panjer")
        mac(f"McQ{L}", eur_m(mc["value_eur"]), f"{SRC}/{vid}.json outputs.truth.annual_loss_quantile.mc_check.value_eur")
        mac(f"McSe{L}", eur_m(mc["standard_error_eur"]), f"{SRC}/{vid}.json outputs.truth.annual_loss_quantile.mc_check.standard_error_eur")
        mac(f"SlaQ{L}", eur_m(sla), f"{SRC}/{vid}.json outputs.exceedance.quantile_999_eur.sla")
        mac(f"SlaRel{L}", f"{100 * (sla / fft - 1):+.1f}", "SLA quantile over the FFT quantile minus one, percent")
        mac(f"PanRel{L}", f"{100 * abs(pan / fft - 1):.3f}", "Panjer quantile over the FFT quantile minus one, absolute percent")
        mac(f"McZ{L}", f"{(mc['value_eur'] - fft) / mc['standard_error_eur']:+.1f}", "(Monte Carlo - FFT) / standard error")
        for c in d[vid]["outputs"]["cells"]:
            maxdiff = max(maxdiff, c["aggregation_agreement"]["max_rel_diff_panjer_fft"])
    mac("McZMax", f"{max(abs((d[v]['outputs']['truth']['annual_loss_quantile']['mc_check']['value_eur'] - d[v]['outputs']['exceedance']['quantile_999_eur']['fft']) / d[v]['outputs']['truth']['annual_loss_quantile']['mc_check']['standard_error_eur']) for v, _, _ in VARIANTS):.1f}", "largest |MC - FFT| / standard error over the variants")
    mac("MaxPanFft", f"{100 * maxdiff:.3f}", "largest max_rel_diff_panjer_fft over the 16 cells, percent")
    table(OUT / "oprisk-aggregation.tex",
                 [r"$\xi$", "FFT (EUR m)", "Panjer (EUR m)", "Monte Carlo (EUR m)", "SLA (EUR m)", "SLA over FFT", r"MC minus FFT ($\mathrm{se}$)"],
                 rows, align="rrrrrrr", label="tab:op-aggregation",
                 caption=r"The true 99.9 percent annual loss quantile of each variant by three aggregations of the generator's compound Poisson "
                         r"loss (Fourier transform, Panjer recursion, Monte Carlo of ten million years with its standard error) and by the single "
                         r"loss approximation; the last two columns give the approximation's relative difference to the Fourier value and the Monte Carlo "
                         r"deviation in standard errors.")


# ---------------------------------------------------------------------------------------------------------------------
# the ladder of the aggregate loss and of the robust estimators in the main cell
def ladder_rows(d: dict, rungs: tuple[str, ...], fn) -> list[list[str]]:
    return [[RUNG_NAME[r]] + [fn(summ(cell(d[vid], MAIN_CELL), r)) for vid, _, _ in VARIANTS] for r in rungs]


def t_ladders(d: dict) -> None:
    hdr = ["Method"] + [rf"$\xi={xi:g}$" for _, _, xi in VARIANTS]
    table(OUT / "oprisk-m24-ratio.tex", hdr, ladder_rows(d, M24_RUNGS, med_iqr), align="lrrrr", label="tab:op-m24-ratio",
                 caption=r"The 99.9 percent capital of the loss distribution approach as a multiple of the true quantile of the generator: median "
                         r"over independent histories and, in brackets, the interquartile range over the same histories, for ten years of data and a "
                         r"collection threshold of EUR 20,000. A ratio of one is unbiased; a dash marks a method with no capital at an infinite mean.")
    table(OUT / "oprisk-m32-ratio.tex", hdr, ladder_rows(d, M32_RUNGS, med_iqr), align="lrrrr", label="tab:op-m32-ratio",
                 caption=r"The 99.9 percent capital of the robust severity estimators with the mean-adjusted single loss approximation, as a multiple "
                         r"of the true quantile: median over independent histories and, in brackets, the interquartile range, for ten years of data and "
                         r"a threshold of EUR 20,000, beside the maximum likelihood splice and the misspecified lognormal control.")
    table(OUT / "oprisk-defined.tex", hdr, ladder_rows(d, tuple(r for r, _ in RUNGS), share_def), align="lrrrr", label="tab:op-defined",
                 caption=r"For each method, the share of histories whose capital falls below the true quantile and, after the slash, the number of the "
                         r"1,000 histories on which the method returns a finite capital, for ten years of data and a threshold of EUR 20,000. A fit that "
                         r"fails or returns a tail index of one or more leaves no capital.")
    # the numbers the prose quotes
    for vid, L, xi in VARIANTS:
        c = cell(d[vid], MAIN_CELL)
        for key, nm in (("lda_lognormal", "Ln"), ("lda_lognormal_truncated", "Tr"), ("lda_splice", "Sp"), ("sla", "Sla"),
                        ("sla_mean_corrected", "Mc"), ("scenario", "Sc"), ("sla_mean_adjusted", "Ma"), ("sla_cvm", "Cvm"),
                        ("sla_obre", "Obre"), ("sla_cvm_lognormal", "Cl")):
            s = summ(c, key)
            if s is None:
                continue
            if key == "lda_splice":
                mac(f"SpQlo{L}", f2(s["ratio_to_truth"]["p25"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].capital.lda_splice.ratio_to_truth.p25")
                mac(f"SpQhi{L}", f2(s["ratio_to_truth"]["p75"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].capital.lda_splice.ratio_to_truth.p75")
            mac(f"Med{nm}{L}", f2(s["ratio_to_truth"]["median"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].capital.{key}.ratio_to_truth.median")
            mac(f"Iqr{nm}{L}", f2(s["iqr_over_truth"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].capital.{key}.iqr_over_truth")
            mac(f"Und{nm}{L}", f"{100 * s['share_underestimating']:.0f}", f"{SRC}/{vid}.json cells[{MAIN_CELL}].capital.{key}.share_underestimating, percent")
            mac(f"Nd{nm}{L}", f"{s['n_defined']:,}", f"{SRC}/{vid}.json cells[{MAIN_CELL}].capital.{key}.n_defined")
    # ranges of the interquartile range of the splice and of the robust fits over the 16 cells
    for key, nm in (("lda_splice", "Sp"), ("sla", "Sla"), ("scenario", "Sc"), ("sla_mean_adjusted", "Ma"), ("sla_cvm", "Cvm"), ("sla_obre", "Obre")):
        vals = [summ(cell(d[vid], cid), key)["iqr_over_truth"] for vid, _, _ in VARIANTS for cid, _, _, _ in CELLS if summ(cell(d[vid], cid), key)]
        mac(f"IqrLo{nm}", f2(min(vals)), f"{SRC}/*.json cells[*].capital.{key}.iqr_over_truth, minimum over 16 cells")
        mac(f"IqrHi{nm}", f2(max(vals)), f"{SRC}/*.json cells[*].capital.{key}.iqr_over_truth, maximum over 16 cells")
    # the same cell of the four variants: spread of the replications and the number of histories lost
    nlost = sum(1000 - summ(cell(d[vid], cid), "lda_splice")["n_defined"] for vid, _, _ in VARIANTS for cid, _, _, _ in CELLS)
    mac("SpliceLost", f"{nlost:,}", "histories without a splice capital, summed over the 16 cells")
    # tests with a light red
    red = tot = 0
    for vid, _, _ in VARIANTS:
        for t in d[vid]["tests"]:
            if t["test_id"] == "oprisk.capital_stability":
                tot += 1
                red += t["light"] == "red"
    mac("CapTests", f"{tot}", "oprisk.capital_stability results over the four documents")
    mac("CapRed", f"{red}", "of them with a red light")


def t_grid(d: dict) -> None:
    rows = []
    for vid, _, xi in VARIANTS:
        for cid, lab, _, _ in CELLS:
            c = cell(d[vid], cid)
            rows.append([f"{xi:g}", lab] + [med_iqr(summ(c, k)) for k in ("lda_splice", "sla_mean_adjusted", "sla_cvm", "sla_obre")])
    table(OUT / "oprisk-grid.tex", [r"$\xi$", "History", "Splice", "GPD by likelihood", "GPD by Cram\\'er-von Mises", "GPD optimally robust"],
                 rows, align="llrrrr", label="tab:op-grid",
                 caption=r"Median ratio of capital to the true quantile and, in brackets, its interquartile range over 1,000 independent histories, "
                         r"for the sixteen cells of the grid (four tail indices, two history lengths, two collection thresholds) and four estimators: "
                         r"the lognormal and GPD splice and the three GPD fits with the mean-adjusted single loss approximation.")


def t_cell_effects(d: dict) -> None:
    """Macros of the effect of the history length and of the threshold on the spread of three methods."""
    for key, nm in (("lda_splice", "Sp"), ("sla_mean_adjusted", "Ma"), ("sla_cvm", "Cvm"), ("sla_obre", "Obre")):
        for vid, L, _ in VARIANTS:
            five = summ(cell(d[vid], "y5-h20000"), key)
            ten = summ(cell(d[vid], "y10-h20000"), key)
            if five and ten:
                mac(f"IqrFive{nm}{L}", f2(five["iqr_over_truth"]), f"{SRC}/{vid}.json cells[y5-h20000].capital.{key}.iqr_over_truth")
                mac(f"IqrTen{nm}{L}", f2(ten["iqr_over_truth"]), f"{SRC}/{vid}.json cells[y10-h20000].capital.{key}.iqr_over_truth")


# ---------------------------------------------------------------------------------------------------------------------
# the engine study of contaminated histories
def t_contam() -> None:
    rows = []
    for name, n, cells, _ in CONTAM:
        rows.append([f"{name} ({n})"] + [f"{m:.2f} ({iq:.2f}; {sh}\\%)" for m, iq, sh in cells])
    table(OUT / "oprisk-contam.tex", ["Scenario (histories)"] + list(CONTAM_COLUMNS), rows, align="lrrrrr", label="tab:op-contam",
                 caption=r"Capital over truth in the study of contaminated histories of the engine, 250 losses above EUR 20,000 per history: median, "
                         r"interquartile range and share of histories below half of the truth. Gross losses are 3 percent of the losses multiplied by 50. "
                         r"The splice column is defined on 143, 74, 136 and 19 histories in the four rows.")
    rows2 = []
    for name, n, _, logs in CONTAM:
        rows2.append([name] + [f"{x:.2f}" for x in logs])
    table(OUT / "oprisk-contam-log.tex", ["Scenario"] + list(CONTAM_COLUMNS), rows2, align="lrrrrr", label="tab:op-contam-log",
                 caption=r"Median absolute log ratio of capital to truth in the study of contaminated histories of the engine: the typical multiplicative "
                         r"error of each estimator, zero for an exact capital and 0.69 for an error by a factor of two, on the same four scenarios.")
    mac("ContamN", "148 to 170", "docs/oprisk/06_robust-severity.md line 63")
    mac("ContamGrossMle", f"{CONTAM[1][3][0]:.2f}", "docs/oprisk/06_robust-severity.md line 83")
    mac("ContamGrossCvm", f"{CONTAM[1][3][1]:.2f}", "docs/oprisk/06_robust-severity.md line 83")
    mac("ContamGrossObre", f"{CONTAM[1][3][2]:.2f}", "docs/oprisk/06_robust-severity.md line 83")
    mac("ContamGrossObreEighty", f"{CONTAM[1][3][3]:.2f}", "docs/oprisk/06_robust-severity.md line 83")
    mac("ContamSplMle", f"{CONTAM[3][3][0]:.2f}", "docs/oprisk/06_robust-severity.md line 85")
    mac("ContamSplCvm", f"{CONTAM[3][3][1]:.2f}", "docs/oprisk/06_robust-severity.md line 85")
    mac("ContamSplObre", f"{CONTAM[3][3][2]:.2f}", "docs/oprisk/06_robust-severity.md line 85")
    mac("ContamObreMedian", f"{CONTAM[1][2][2][0]:.2f}", "docs/oprisk/06_robust-severity.md line 72")
    mac("ContamMleMedian", f"{CONTAM[1][2][0][0]:.2f}", "docs/oprisk/06_robust-severity.md line 72")
    mac("ContamCleanMle", f"{CONTAM[0][3][0]:.2f}", "docs/oprisk/06_robust-severity.md line 82")
    mac("ContamCleanCvm", f"{CONTAM[0][3][1]:.2f}", "docs/oprisk/06_robust-severity.md line 82")
    mac("ContamCleanSplice", f"{CONTAM[0][3][4]:.2f}", "docs/oprisk/06_robust-severity.md line 82")
    mac("ContamCleanIqrMle", f"{CONTAM[0][2][0][1]:.2f}", "docs/oprisk/06_robust-severity.md line 71")
    mac("ContamCleanIqrObre", f"{CONTAM[0][2][2][1]:.2f}", "docs/oprisk/06_robust-severity.md line 71")
    mac("ContamCleanIqrCvm", f"{CONTAM[0][2][1][1]:.2f}", "docs/oprisk/06_robust-severity.md line 71")
    mac("ContamSpliceMed", f"{CONTAM[2][2][1][0]:.2f}", "docs/oprisk/06_robust-severity.md line 73")
    mac("ContamSpliceErrMle", f"{CONTAM[2][3][0]:.2f}", "docs/oprisk/06_robust-severity.md line 84")
    mac("ContamSpliceErrSplice", f"{CONTAM[2][3][4]:.2f}", "docs/oprisk/06_robust-severity.md line 84")


# ---------------------------------------------------------------------------------------------------------------------
# the tail index profile, the standardised approach, the scenarios and the tests
def t_tail(d: dict) -> None:
    rows = []
    for vid, L, xi in VARIANTS:
        c = cell(d[vid], MAIN_CELL)
        for t in c["threshold_stability"]:
            ti = t["tail_index"]
            rows.append([f"{xi:g}", f"{t['threshold_eur']:,.0f}", f"{t['n_exceedances_median']:.0f}",
                         f"{ti['median']:.3f} [{ti['p05']:.3f}, {ti['p95']:.3f}]", f"{100 * t['share_at_least_one']:.1f}%"])
    table(OUT / "oprisk-tail.tex", [r"True $\xi$", "Threshold (EUR)", "Exceedances (median)", r"Fitted $\hat\xi$: median [5th, 95th]", r"Share $\hat\xi\ge1$"],
                 rows, align="rrrrr", label="tab:op-tail",
                 caption=r"The GPD tail index fitted to the excesses over four thresholds, from one to eight times the collection threshold of EUR 20,000, "
                         r"on the 1,000 histories of ten years: median number of exceedances, the median of the fitted tail index with its 5th and 95th "
                         r"percentiles, and the share of histories whose fit reaches one, the point at which the mean does not exist.")
    for vid, L, xi in VARIANTS:
        shares = [cell(d[vid], cid)["threshold_stability"][0]["share_at_least_one"] for cid, _, _, _ in CELLS]
        mac(f"InfLo{L}", f"{100 * min(shares):.0f}", f"{SRC}/{vid}.json cells[*].threshold_stability[0].share_at_least_one, minimum percent")
        mac(f"InfHi{L}", f"{100 * max(shares):.0f}", f"{SRC}/{vid}.json cells[*].threshold_stability[0].share_at_least_one, maximum percent")
        mac(f"FinLo{L}", f"{100 * (1 - max(shares)):.0f}", "100 minus the maximum share at or above one")
        mac(f"FinHi{L}", f"{100 * (1 - min(shares)):.0f}", "100 minus the minimum share at or above one")
        t0 = cell(d[vid], MAIN_CELL)["threshold_stability"]
        mac(f"XiMed{L}", f"{t0[0]['tail_index']['median']:.2f}", f"{SRC}/{vid}.json cells[{MAIN_CELL}].threshold_stability[0].tail_index.median")
        mac(f"XiHi{L}", f"{t0[-1]['tail_index']['p95']:.2f}", f"{SRC}/{vid}.json cells[{MAIN_CELL}].threshold_stability[-1].tail_index.p95")
        mac(f"XiLo{L}", f"{t0[-1]['tail_index']['p05']:.2f}", f"{SRC}/{vid}.json cells[{MAIN_CELL}].threshold_stability[-1].tail_index.p05")


def t_sma(d: dict) -> None:
    rows = []
    for vid, L, xi in VARIANTS:
        c = cell(d[vid], MAIN_CELL)
        s = c["sma"]
        orc = s["orc_eur"]
        ratio = s["orc_over_true_quantile"]
        sp = summ(c, "lda_splice")
        rows.append([f"{xi:g}", eur_m(orc["median"]), f"{eur_m(orc['p05'])} to {eur_m(orc['p95'])}", f"{s['ilm']['median']:.3f}",
                     f2(ratio["median"]), f"{f2(ratio['p05'])} to {f2(ratio['p95'])}", f2(sp["ratio_to_truth"]["median"])])
        mac(f"OrcMed{L}", eur_m(orc["median"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].sma.orc_eur.median")
        mac(f"OrcRatio{L}", f2(ratio["median"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].sma.orc_over_true_quantile.median")
        mac(f"OrcRatioLo{L}", f2(ratio["p05"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].sma.orc_over_true_quantile.p05")
        mac(f"OrcRatioHi{L}", f2(ratio["p95"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].sma.orc_over_true_quantile.p95")
        mac(f"IlmMed{L}", f"{s['ilm']['median']:.3f}", f"{SRC}/{vid}.json cells[{MAIN_CELL}].sma.ilm.median")
        mac(f"LcMed{L}", eur_m(s["lc_eur"]["median"]), f"{SRC}/{vid}.json cells[{MAIN_CELL}].sma.lc_eur.median")
    table(OUT / "oprisk-sma.tex",
                 [r"True $\xi$", "ORC median (EUR m)", "ORC 5th to 95th (EUR m)", "ILM median", "ORC over true quantile", "5th to 95th", "Splice over truth"],
                 rows, align="rrrrrrr", label="tab:op-sma",
                 caption=r"The operational risk capital of the standardised approach on the same histories (ten years, threshold EUR 20,000): median and "
                         r"5th to 95th percentile of the capital, the median internal loss multiplier, the capital as a multiple of the true 99.9 percent "
                         r"quantile of the generator, and for comparison the median ratio of the splice. The business indicator component is the same in every row.")
    om = [cell(d[v], MAIN_CELL)["sma"]["orc_eur"]["median"] for v, _, _ in VARIANTS]
    mac("OrcGrowth", f"{100 * (om[-1] / om[0] - 1):.0f}", "median ORC at xi=1.1 over median ORC at xi=0.6 minus one, percent")
    b = d["xi-0-96"]["outputs"]["bank"]
    mac("Bic", eur_m(b["bic_eur"], 0), f"{SRC}/xi-0-96.json outputs.bank.bic_eur")
    mac("Bi", f"{b['business_indicator']['bi_eur'] / 1e9:.1f}", f"{SRC}/xi-0-96.json outputs.bank.business_indicator.bi_eur")
    mac("BiIldc", eur_m(b["business_indicator"]["ildc_eur"], 0), f"{SRC}/xi-0-96.json outputs.bank.business_indicator.ildc_eur")
    mac("BiSc", eur_m(b["business_indicator"]["sc_eur"], 0), f"{SRC}/xi-0-96.json outputs.bank.business_indicator.sc_eur")
    mac("BiFc", eur_m(b["business_indicator"]["fc_eur"], 0), f"{SRC}/xi-0-96.json outputs.bank.business_indicator.fc_eur")
    mac("Bucket", f"{b['bucket']}", f"{SRC}/xi-0-96.json outputs.bank.bucket")


def t_ilm(d: dict) -> None:
    resp = d["xi-0-96"]["outputs"]["sma_response"]
    bic = resp["bic_eur"]
    rows = []
    for r in resp["rows"]:
        rows.append([f"{r['added_loss_eur'] / bic:g}", eur_m(r["added_loss_eur"]), eur_m(r["lc_eur"]), f"{r['ilm']:.3f}", eur_m(r["orc_eur"]),
                     eur_m(r["lda_capital_eur"])])
    table(OUT / "oprisk-ilm.tex",
                 [r"Added loss over $\mathrm{BIC}$", "Added loss (EUR m)", "$LC$ (EUR m)", "ILM", "ORC (EUR m)", "SLA capital (EUR m)"],
                 rows, align="rrrrrr", label="tab:op-ilm",
                 caption=r"The response of the standardised approach and of the single loss approximation to one large loss added to the latest year of "
                         r"one history of ten years (variant $\xi=0.96$, threshold EUR 20,000): the loss component, the internal loss multiplier, the "
                         r"capital of the standardised approach and the single loss approximation capital of the same history, for losses from zero to the size of the business indicator component.")
    first, last = resp["rows"][0], resp["rows"][-1]
    mid = resp["rows"][3]
    mac("IlmZero", f"{first['ilm']:.3f}", f"{SRC}/xi-0-96.json outputs.sma_response.rows[0].ilm")
    mac("IlmLast", f"{last['ilm']:.3f}", f"{SRC}/xi-0-96.json outputs.sma_response.rows[-1].ilm")
    mac("IlmMid", f"{mid['ilm']:.3f}", f"{SRC}/xi-0-96.json outputs.sma_response.rows[3].ilm")
    mac("IlmMidAdded", eur_m(mid["added_loss_eur"], 0), f"{SRC}/xi-0-96.json outputs.sma_response.rows[3].added_loss_eur")
    mac("OrcZero", eur_m(first["orc_eur"]), f"{SRC}/xi-0-96.json outputs.sma_response.rows[0].orc_eur")
    mac("OrcLast", eur_m(last["orc_eur"]), f"{SRC}/xi-0-96.json outputs.sma_response.rows[-1].orc_eur")
    mac("LdaZero", eur_m(first["lda_capital_eur"]), f"{SRC}/xi-0-96.json outputs.sma_response.rows[0].lda_capital_eur")
    mac("LdaLast", eur_m(last["lda_capital_eur"]), f"{SRC}/xi-0-96.json outputs.sma_response.rows[-1].lda_capital_eur")
    mac("LdaOneLoss", eur_m(resp["rows"][1]["lda_capital_eur"]), f"{SRC}/xi-0-96.json outputs.sma_response.rows[1].lda_capital_eur")
    mac("AddedLast", eur_m(last["added_loss_eur"], 0), f"{SRC}/xi-0-96.json outputs.sma_response.rows[-1].added_loss_eur")
    mac("AddedOne", eur_m(resp["rows"][1]["added_loss_eur"], 0), f"{SRC}/xi-0-96.json outputs.sma_response.rows[1].added_loss_eur")
    t = next(t for t in d["xi-0-96"]["tests"] if t["test_id"] == "oprisk.sma_ilm_response")
    mac("IlmJump", f"{t['metric']:.3f}", f"{SRC}/xi-0-96.json tests[oprisk.sma_ilm_response].metric")
    mac("IlmJumpAdded", eur_m(t["extras"]["added_loss"], 0), f"{SRC}/xi-0-96.json tests[oprisk.sma_ilm_response].extras.added_loss")


def t_scenario(d: dict) -> None:
    si = d["xi-0-96"]["outputs"]["scenario_influence"]
    rows = []
    for s in si["scenarios"]:
        rows.append([s["scenario_id"], s["kind"], f"{s['loss_eur']:,.0f}", f"{s['exceedance_frequency_per_year']:g}", f"{s['influence']:+.3f}"])
    table(OUT / "oprisk-scenario.tex", ["Point", "Kind", "Loss (EUR)", "Frequency (per year)", "Influence"], rows, align="llrrr",
                 label="tab:op-scenario",
                 caption=r"The eight scenario points of the Bayesian credibility rung on one history of ten years (variant $\xi=0.96$, threshold EUR 20,000): "
                         r"the loss, the expected number of events per year at or above it, and the influence, the relative change of the 99.9 percent capital "
                         r"when the point is removed. The capital with all eight points is the base of the influences.")
    mx = max(si["scenarios"], key=lambda s: abs(s["influence"]))
    mac("ScBase", eur_m(si["base_capital_eur"]), f"{SRC}/xi-0-96.json outputs.scenario_influence.base_capital_eur")
    mac("ScMaxInf", f"{abs(mx['influence']):.3f}", f"{SRC}/xi-0-96.json outputs.scenario_influence.scenarios[max |influence|]")
    mac("ScMaxId", mx["scenario_id"], f"{SRC}/xi-0-96.json outputs.scenario_influence.scenarios[max |influence|].scenario_id")
    mac("ScNeg", f"{sum(1 for s in si['scenarios'] if s['influence'] < 0)}", "scenario points whose removal raises the capital")
    mac("ScNPoints", f"{len(si['scenarios'])}", f"{SRC}/xi-0-96.json outputs.scenario_influence.scenarios")


def t_tests(d: dict) -> None:
    names = ("oprisk.benchmark_reproduction", "oprisk.threshold_stability", "oprisk.capital_stability", "oprisk.sma_ilm_response", "oprisk.scenario_influence")
    rows = []
    totals = {"green": 0, "amber": 0, "red": 0, "not_evaluated": 0}
    for n in names:
        cnt = {"green": 0, "amber": 0, "red": 0, "not_evaluated": 0}
        for vid, _, _ in VARIANTS:
            for t in d[vid]["tests"]:
                if t["test_id"] == n:
                    cnt[t["light"]] += 1
        for k in totals:
            totals[k] += cnt[k]
        rows.append([f"\\texttt{{{n.split('.')[1].replace('_', chr(92) + '_')}}}", cnt["green"], cnt["amber"], cnt["red"], cnt["not_evaluated"], sum(cnt.values())])
    table(OUT / "oprisk-tests.tex", ["Test", "Green", "Amber", "Red", "Not evaluated", "Results"], rows, align="lrrrrr", label="tab:op-tests",
                 caption=r"The lights of the five operational-risk validation tests over the four variant documents of case C17. The lights compare a "
                         r"descriptive metric with tolerances of the product, not with a regulatory threshold; the capital stability test is run for ten "
                         r"methods in each of the sixteen cells.")
    mac("TestsTotal", f"{sum(totals.values())}", "results of the five tests over the four documents")
    mac("TestsRed", f"{totals['red']}", "results with a red light")
    mac("TestsGreen", f"{totals['green']}", "results with a green light")
    th = [t for vid, _, _ in VARIANTS for t in d[vid]["tests"] if t["test_id"] == "oprisk.threshold_stability"]
    mac("ThrTests", f"{len(th)}", "threshold stability results")
    bm = d["xi-0-96"]["tests"][0]
    mac("BenchStat", f"{bm['metric']:.3f}", f"{SRC}/xi-0-96.json tests[oprisk.benchmark_reproduction].metric")


def write_numbers(registry: pathlib.Path | None) -> None:
    lines = ["% Generated by tables/make_oprisk.py from data/derived/C17 and the riskvalidation engine; do not edit."]
    for k in sorted(MACROS):
        lines.append(f"\\newcommand{{\\op{k}}}{{{MACROS[k][0]}}}")
    (OUT / "oprisk-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    if registry:
        registry.write_text(json.dumps({k: {"value": v, "source": s} for k, (v, s) in sorted(MACROS.items())}, indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", type=pathlib.Path, help="write every macro with its value and source to this JSON file")
    args = ap.parse_args()
    d = load()
    t_cases(d)
    t_benchmark()
    t_aggregation(d)
    t_ladders(d)
    t_grid(d)
    t_cell_effects(d)
    t_contam()
    t_tail(d)
    t_sma(d)
    t_ilm(d)
    t_scenario(d)
    t_tests(d)
    write_numbers(args.registry)
    print(f"{len(MACROS)} macros, tables written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
