"""Tables and numbers of the section 'Methods: loss given default and exposure at default' of the technical report.

Every number the section prints comes from here: the committed documents of cases C08 and C09 (``data/derived``) and the
constants of the pipeline source (read with ``ast``, never imported, so the script needs only the standard library and
``figkit``). It writes, into ``tables/``:

* ``lgd-ead-<name>.tex``: one booktabs table environment per table of the section (``\\input`` by the section);
* ``lgd-ead-numbers.tex``: one macro per number the prose quotes, read in the text as ``\\LE{key}``.

Run from the repository root::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/contraste-technical-report/tables/make_lgd-ead.py
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

ROOT = figkit.ROOT
C08_SRC = ROOT / "data-pipeline" / "pipeline" / "cases" / "c08"
C09_SRC = ROOT / "data-pipeline" / "pipeline" / "cases" / "c09"

#: the names a reader sees for the rungs (the ids of the documents are internal labels of the ladder)
RUNG_NAME = {
    "L1-ols": "OLS", "L2-fractional-logit": "Fractional logit", "L3-beta": "Beta regression", "L4-hurdle": "Hurdle",
    "L5-gradient-boosted": "Gradient boosting", "L6-tobit": "Tobit", "L7-random-forest": "Random forest",
    "L8-neural-network": "Neural network",
}
RUNGS = list(RUNG_NAME)
ML = ("L7-random-forest", "L8-neural-network")
EARLIER = tuple(r for r in RUNGS if r not in ML)
LIGHT = {"green": "green", "amber": "amber", "red": "red", "not_evaluated": "not evaluated"}
DESIGN_NAME = {"fixed-horizon": "Fixed horizon", "cohort": "Cohort", "variable-horizon": "Variable horizon"}
TREATMENT_NAME = {"none": "None", "censor": "Censor", "floor-cap": "Floor and cap", "bounded-scale": "Bounded scale"}
MODEL_NAME = {
    "ccf-fixed-horizon-none": "Fixed-horizon CCF, untreated", "ccf-fixed-horizon-censor": "Fixed-horizon CCF, censored",
    "ccf-fixed-horizon-floor-cap": "Fixed-horizon CCF, floor and cap",
    "ccf-fixed-horizon-bounded-scale": "Fixed-horizon CCF, bounded-scale logit",
    "ccf-cohort-floor-cap": "Cohort CCF, floor and cap", "ccf-variable-horizon-floor-cap": "Variable-horizon CCF, floor and cap",
    "direct-ead": "Direct EAD", "utilisation-change": "Utilisation change",
}

NUM: dict[str, str] = {}


# ------------------------------------------------------------------------------------------------ source constants
def module_constants(path: pathlib.Path) -> dict[str, object]:
    """The module-level names of a pipeline source that are plain literals (``ast.literal_eval``); the others are skipped."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: dict[str, object] = {}
    for node in tree.body:
        target, value = None, None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            target, value = node.target.id, node.value
        if target is None:
            continue
        try:
            out[target] = ast.literal_eval(value)
        except (ValueError, SyntaxError):
            continue
    return out


def params_entries(path: pathlib.Path) -> tuple[dict[str, object], dict[str, str]]:
    """The literal entries of the ``PARAMS`` dict of the C09 generator and the trailing comment of each entry's line."""
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines()
    values: dict[str, object] = {}
    notes: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "PARAMS" and isinstance(node.value, ast.Dict):
            for k, v in zip(node.value.keys, node.value.values, strict=True):
                try:
                    key = ast.literal_eval(k)
                    values[key] = ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    continue
                line = lines[k.lineno - 1]
                m = re.search(r"#\s*(.*)$", line)
                notes[key] = m.group(1).strip() if m else ""
    return values, notes


def neg(x: float, digits: int = 3) -> str:
    """A signed number in math mode (a true minus sign)."""
    s = f"{x:.{digits}f}"
    if s.startswith("-") and float(s) == 0.0:
        s = s[1:]
    return f"${s}$" if not s.startswith("-") else f"$-{s[1:]}$"


def plain(x: float, digits: int = 3) -> str:
    """The same number for running text (the macro value): math minus where negative."""
    return neg(x, digits)



def pm(x: float, half: float, digits: int = 3) -> str:
    s = f"{abs(x):.{digits}f}"
    sign = "-" if x < 0 and float(s) != 0.0 else ""
    return f"${sign}{s} \\pm {half:.{digits}f}$"


def pct(x: float, digits: int = 1) -> str:
    return f"{100.0 * x:.{digits}f}\\,\\%"


def cohort_label(cid: str) -> str:
    return cid.replace("-", "--")


def put(key: str, value: str) -> None:
    NUM[key] = value


# ------------------------------------------------------------------------------------------------ the C08 documents
panel = module_constants(C08_SRC / "panel.py")
ladder_c = module_constants(C08_SRC / "ladder.py")
ml_c = module_constants(C08_SRC / "ml_benchmark.py")
cutoff_c = module_constants(C08_SRC / "cutoff.py")
build_c = module_constants(C08_SRC / "build.py")
COHORTS = [c[0] for c in panel["COHORTS"]]
BOUNDS = {c[0]: (c[1], c[2]) for c in panel["COHORTS"]}
C08 = {cid: figkit.doc(f"C08/dc-{cid}.json") for cid in COHORTS}
C08M = {cid: figkit.doc(f"C08/models-dc-{cid}.json") for cid in COHORTS}
REF = "2009-10"  # the cohort the case page opens first (``DEFAULT_VARIANT`` of the case)


def rung_rows(cid: str) -> dict[str, dict]:
    return {r["rung_id"]: r for r in C08[cid]["outputs"]["rung_comparison"]}


def cal_test(cid: str, rid: str) -> dict:
    seg = f"cohort-{cid}"
    return next(t for t in C08[cid]["tests"] if t["test_id"] == "lgd_ead.lgd_calibration_by_segment" and t["model_id"] == rid
                and t["segment"] == seg)


def fitted_counts(cid: str) -> tuple[int, int]:
    p = C08M[cid]["model"][0]["parameters"]
    return int(p["n_defaults_fitted"]["value"]), int(p["n_out_of_range_left_out"]["value"])


def ml_verdict(wins: int, cohorts: int) -> str:
    """The adoption rule of the pipeline (``ml_benchmark.verdict``): holds from two thirds of the cohorts, refuted up to one third."""
    share = wins / cohorts
    if share >= 2 / 3 - 1e-12:
        return "holds"
    if share <= 1 / 3 + 1e-12:
        return "refuted"
    return "mixed"


def c08_numbers() -> None:
    put("n-cohorts", str(len(COHORTS)))
    put("min-defaults", f"{ladder_c['MIN_DEFAULTS']:,}")
    put("workout-window", str(cutoff_c["WORKOUT_WINDOW_MONTHS"]))
    put("max-ratio", f"{panel['MAX_RATIO']:g}")
    put("seasoning-cap", f"{panel['SEASONING_CAP']:g}")
    put("n-buckets", str(build_c["N_BUCKETS"]))
    for cid in COHORTS:
        o = C08[cid]["outputs"]
        nf, nout = fitted_counts(cid)
        put(f"cutoff-{cid}", o["training"]["cutoff_date"])
        put(f"ntrain-{cid}", f"{o['training']['n_defaults']:,}")
        put(f"nopen-{cid}", f"{o['training']['n_open_workouts_excluded']:,}")
        put(f"nfit-{cid}", f"{nf:,}")
        put(f"nout-{cid}", f"{nout:,}")
        put(f"ntest-{cid}", f"{o['lgd_distribution']['n']:,}")
        put(f"mean-{cid}", f"{o['lgd_distribution']['mean']['value']:.3f}")
        rows = rung_rows(cid)
        for rid in RUNGS:
            r = rows[rid]
            put(f"rmse-{rid}-{cid}", f"{r['rmse']:.3f}")
            put(f"mae-{rid}-{cid}", f"{r['mae']:.3f}")
            put(f"r2-{rid}-{cid}", f"{r['r2']:.3f}")
            put(f"rho-{rid}-{cid}", f"{r['spearman']:.3f}")
            t = cal_test(cid, rid)
            put(f"gap-{rid}-{cid}", plain(t["metric"], 3))
            put(f"gaplo-{rid}-{cid}", plain(t["extras"]["ci_low"], 3))
            put(f"gaphi-{rid}-{cid}", plain(t["extras"]["ci_high"], 3))
            put(f"light-{rid}-{cid}", LIGHT[t["light"]])
        # the realised mean of the test cohort and the share of the proxy above one
        d = o["lgd_distribution"]
        put(f"above1-{cid}", pct(d["share_above_one"], 1))
        put(f"mass1-{cid}", pct(d["mass_at_one"]["share"], 1))
    o = C08[REF]["outputs"]["lgd_distribution"]
    put("ref-median", f"{o['median']['value']:.3f}")
    put("ref-highest", f"{o['highest']['value']:.2f}")
    put("ref-top-bin-share", pct(o["bins"][-1]["share"], 1))
    put("ref-n-above1", f"{o['n_above_one']:,}")
    put("ref-mass0-n", f"{o['mass_at_zero']['n']:,}")
    put("ref-mass1-n", f"{o['mass_at_one']['n']:,}")
    ep = {(cid, e["epsilon"]): e for cid in COHORTS for e in C08[cid]["outputs"]["endpoint_sensitivity"]}
    for (cid, eps), e in ep.items():
        put(f"eps-rmse-{eps:g}-{cid}", f"{e['rmse']:.4f}")
        put(f"eps-mean-{eps:g}-{cid}", f"{e['mean_predicted']['value']:.3f}")
    # beta sensitivity: spread of the RMSE and of the mean prediction over the three epsilons, in the reference cohort
    spread_rmse = max(ep[(REF, e)]["rmse"] for e in ladder_c["EPSILONS"]) - min(ep[(REF, e)]["rmse"] for e in ladder_c["EPSILONS"])
    spread_mean = (max(ep[(REF, e)]["mean_predicted"]["value"] for e in ladder_c["EPSILONS"])
                   - min(ep[(REF, e)]["mean_predicted"]["value"] for e in ladder_c["EPSILONS"]))
    put("eps-spread-rmse", f"{spread_rmse:.4f}")
    put("eps-spread-mean", f"{spread_mean:.3f}")
    # the hypothesis on the two machine-learning rungs
    wins = 0
    gains = {}
    for cid in COHORTS:
        rows = rung_rows(cid)
        best_e = min(((r, rows[r]["rmse"]) for r in EARLIER), key=lambda kv: kv[1])
        best_m = min(((r, rows[r]["rmse"]) for r in ML), key=lambda kv: kv[1])
        gain = best_e[1] - best_m[1]
        gains[cid] = (best_e, best_m, gain)
        wins += gain > 0.0
        put(f"mlgain-{cid}", plain(gain, 4))
        put(f"mlbest-earlier-{cid}", RUNG_NAME[best_e[0]])
        put(f"mlbest-ml-{cid}", RUNG_NAME[best_m[0]])
    put("ml-wins", str(wins))
    put("ml-outcome", ml_verdict(wins, len(COHORTS)))
    put("ml-gain-max", plain(max(g[2] for g in gains.values()), 4))
    put("ml-gain-min", plain(min(g[2] for g in gains.values()), 4))
    # how many of the tests of calibration by segment end red, across rungs and cohorts
    reds = sum(cal_test(cid, rid)["light"] == "red" for cid in COHORTS for rid in RUNGS)
    put("cal-red", str(reds))
    put("cal-total", str(len(COHORTS) * len(RUNGS)))
    pos = sum(cal_test(cid, rid)["metric"] > 0 for cid in COHORTS for rid in RUNGS)
    put("cal-positive", str(pos))
    green_cid = [cid for cid in COHORTS for rid in RUNGS if cal_test(cid, rid)["light"] == "green"]
    put("cal-green", str(len(green_cid)))
    put("cal-green-cohort", cohort_label(green_cid[0]) if green_cid else "none")
    over = [t["light"] for cid in COHORTS for t in C08[cid]["tests"] if t["test_id"] == "lgd_ead.lgd_calibration_over_time"]
    put("time-red", str(sum(x == "red" for x in over)))
    put("time-total", str(len(over)))
    disc = [t["light"] for cid in COHORTS for t in C08[cid]["tests"] if t["test_id"] == "lgd_ead.lgd_discrimination"]
    put("disc-green", str(sum(x == "green" for x in disc)))
    put("disc-total", str(len(disc)))
    # the range of the rank correlation and of R2 over rungs and cohorts
    put("r2-max", f"{max(rung_rows(c)[r]['r2'] for c in COHORTS for r in RUNGS):.3f}")
    put("r2-min", f"{min(rung_rows(c)[r]['r2'] for c in COHORTS for r in RUNGS):.3f}")
    # the best rung by RMSE in each cohort, and how many cohorts each rung wins
    best = {cid: min(RUNGS, key=lambda r: rung_rows(cid)[r]["rmse"]) for cid in COHORTS}
    for r in RUNGS:
        put(f"bestcount-{r}", str(sum(1 for c in COHORTS if best[c] == r)))
    # the calibration by bucket of predicted LGD: lowest and highest bucket, two cohorts, four rungs
    for cid in (REF, "2014-19"):
        for rid in ("L2-fractional-logit", "L5-gradient-boosted", "L7-random-forest", "L8-neural-network"):
            b = [x for x in C08[cid]["outputs"]["calibration_by_bucket"] if x["rung_id"] == rid]
            put(f"bucket-lo-pred-{rid}-{cid}", f"{b[0]['predicted']['value']:.3f}")
            put(f"bucket-lo-real-{rid}-{cid}", f"{b[0]['realised']['value']:.3f}")
            put(f"bucket-hi-pred-{rid}-{cid}", f"{b[-1]['predicted']['value']:.3f}")
            put(f"bucket-hi-real-{rid}-{cid}", f"{b[-1]['realised']['value']:.3f}")
            put(f"bucket-n-{rid}-{cid}", f"{b[0]['n']:,}")
    # the test by rung count with the downturn add-on of the file
    dn = C08[REF]["outputs"]["downturn"]
    put("down-first", str(dn["period"]["first_year"]))
    put("down-last", str(dn["period"]["last_year"]))
    put("down-addon", f"{dn['rows'][0]['add_on']:.3f}")
    # model of the ladder: the catboost settings and the forest and network settings
    put("forest-trees", str(ml_c["FOREST"]["n_estimators"]))
    put("forest-leaf", str(ml_c["FOREST"]["min_samples_leaf"]))
    put("forest-features", f"{ml_c['FOREST']['max_features']:g}")
    put("forest-samples", f"{ml_c['FOREST']['max_samples']:g}")
    put("net-layers", " and ".join(str(h) for h in ml_c["NETWORK"]["hidden_layer_sizes"]))
    put("net-batch", str(ml_c["NETWORK"]["batch_size"]))
    put("net-epochs", str(ml_c["NETWORK"]["max_iter"]))
    put("net-patience", str(ml_c["NETWORK"]["n_iter_no_change"]))
    put("net-valfrac", f"{ml_c['NETWORK']['validation_fraction']:g}")
    put("net-alpha", f"{ml_c['NETWORK']['alpha']:g}")
    put("net-lr", f"{ml_c['NETWORK']['learning_rate_init']:g}")
    put("boost-iter", str(ladder_c["BOOST"]["iterations"]))
    put("boost-depth", str(ladder_c["BOOST"]["depth"]))
    put("boost-lr", f"{ladder_c['BOOST']['learning_rate']:g}")
    put("boost-l2", f"{ladder_c['BOOST']['l2_leaf_reg']:g}")
    put("eps-list", ", ".join(f"{e:g}" for e in ladder_c["EPSILONS"]))
    put("eps-ladder", f"{ladder_c['LADDER_EPSILON']:g}")


def table_settings() -> None:
    boost = ", ".join(f"{k}={v}" for k, v in ladder_c["BOOST"].items() if k in ("iterations", "depth", "learning_rate", "l2_leaf_reg", "loss_function"))
    forest = ", ".join(f"{k}={v}" for k, v in ml_c["FOREST"].items() if k != "n_jobs")
    net = ", ".join(f"{k}={v}" for k, v in ml_c["NETWORK"].items())
    rows = [
        ("OLS", "riskvalidation", "fit\\_ols; prediction clipped to [0, 1]"),
        ("Fractional logit", "riskvalidation", "fit\\_fractional\\_logit; Newton iterations with step halving from a zero start"),
        ("Beta regression", "riskvalidation", f"fit\\_beta; endpoint epsilon in {{{', '.join(f'{e:g}' for e in ladder_c['EPSILONS'])}}}, the ladder keeps {ladder_c['LADDER_EPSILON']:g}"),
        ("Hurdle", "riskvalidation", "fit\\_hurdle; logit of a positive loss, then fractional logit of the severity"),
        ("Gradient boosting", "catboost", figkit.tex_escape(boost)),
        ("Tobit", "riskvalidation", "fit\\_tobit; two-limit censored normal at 0 and 1"),
        ("Random forest", "scikit-learn", figkit.tex_escape(forest)),
        ("Neural network", "scikit-learn", figkit.tex_escape(net)),
    ]
    rows = [(a, b, "\\raggedright\\arraybackslash " + c) for a, b, c in rows]
    figkit.table(
        HERE / "lgd-ead-settings.tex", ["Rung", "Library", "Specification and settings"], rows,
        caption="The eight rungs of the loss-given-default ladder with the library that fits each and its fixed settings, read from the "
                "pipeline source of case C08; every rung is fitted on the same training span and the same standardised covariates.",
        label="tab:lgd-ead-settings", align="llp{8.2cm}")


def table_rmse() -> None:
    header = ["Rung"] + [cohort_label(c) for c in COHORTS]
    rows = []
    best = {cid: min(RUNGS, key=lambda r: rung_rows(cid)[r]["rmse"]) for cid in COHORTS}
    for rid in RUNGS:
        row = [RUNG_NAME[rid]]
        for cid in COHORTS:
            v = f"{rung_rows(cid)[rid]['rmse']:.3f}"
            row.append(f"\\textbf{{{v}}}" if best[cid] == rid else v)
        rows.append(row)
    rows.append(["Test defaults"] + [f"{C08[c]['outputs']['lgd_distribution']['n']:,}" for c in COHORTS])
    figkit.table(
        HERE / "lgd-ead-rmse.tex", header, rows,
        caption="Root mean squared error of each rung on the defaults of its own test cohort (SBA 7(a) charge-offs, loss given default proxy); "
                "every rung is trained only on the defaults whose charge-off closed before the cohort starts, and the lowest value "
                "of each column is in bold.",
        label="tab:lgd-ead-rmse", align="l" + "r" * len(COHORTS))


def table_ladder_ref() -> None:
    rows = []
    for rid in RUNGS:
        r = rung_rows(REF)[rid]
        t = cal_test(REF, rid)
        rows.append([RUNG_NAME[rid], f"{r['rmse']:.3f}", f"{r['mae']:.3f}", f"{r['r2']:.3f}", f"{r['spearman']:.3f}", neg(t["metric"]),
                     f"$[{t['extras']['ci_low']:.3f},\\ {t['extras']['ci_high']:.3f}]$", LIGHT[t["light"]]])
    figkit.table(
        HERE / "lgd-ead-ladder.tex", ["Rung", "RMSE", "MAE", "$R^2$", "Spearman $\\rho$", "Gap", "95\\% interval of the gap", "Light"], rows,
        caption=f"The ladder on the {cohort_label(REF)} default cohort ({C08[REF]['outputs']['lgd_distribution']['n']:,} defaults): error, rank "
                "correlation and the calibration gap, the mean realised minus the mean predicted loss given default, with its 95\\% interval "
                "and the light of the paired t-test of calibration by segment.",
        label="tab:lgd-ead-ladder", align="lrrrrrcl")


def table_ml() -> None:
    rows = []
    wins = 0
    for cid in COHORTS:
        rows_c = rung_rows(cid)
        be = min(((r, rows_c[r]["rmse"]) for r in EARLIER), key=lambda kv: kv[1])
        bm = min(((r, rows_c[r]["rmse"]) for r in ML), key=lambda kv: kv[1])
        gain = be[1] - bm[1]
        wins += gain > 0
        rows.append([cohort_label(cid), RUNG_NAME[be[0]], f"{be[1]:.4f}", RUNG_NAME[bm[0]], f"{bm[1]:.4f}", neg(gain, 4), "yes" if gain > 0 else "no"])
    rows.append(["Cohorts won", "", "", "", "", "", f"{wins} of {len(COHORTS)}"])
    figkit.table(
        HERE / "lgd-ead-ml.tex", ["Cohort", "Best of the six earlier rungs", "RMSE", "Better of forest and network", "RMSE", "Gain", "Wins"],
        rows,
        caption="The hypothesis on the random forest and the neural network: in each test cohort the lowest RMSE of the six earlier rungs "
                "against the lower of the two machine-learning rungs, their difference (positive when the machine-learning rung wins) and "
                f"the count of cohorts won, which the adoption rule reads as {ml_verdict(wins, len(COHORTS))}.",
        label="tab:lgd-ead-ml", align="lllrlrr")


def table_endpoint() -> None:
    eps = ladder_c["EPSILONS"]
    header = ["Cohort"] + [f"RMSE, $\\epsilon={e:g}$" for e in eps] + [f"Mean, $\\epsilon={e:g}$" for e in eps]
    rows = []
    for cid in COHORTS:
        e = {x["epsilon"]: x for x in C08[cid]["outputs"]["endpoint_sensitivity"]}
        rows.append([cohort_label(cid)] + [f"{e[x]['rmse']:.4f}" for x in eps] + [f"{e[x]['mean_predicted']['value']:.3f}" for x in eps])
    figkit.table(
        HERE / "lgd-ead-endpoint.tex", header, rows,
        caption="Sensitivity of the beta regression to the endpoint adjustment: for each test cohort the root mean squared error and the "
                "mean predicted loss given default at each of the three values of the adjustment epsilon, the three fits sharing the same "
                "training span and covariates.",
        label="tab:lgd-ead-endpoint", align="lrrrrrr")


# ------------------------------------------------------------------------------------------------ the C09 documents
LEVELS = list(range(6))
C09 = {lv: figkit.doc(f"C09/level-{lv}.json") for lv in LEVELS}
ccf_p = module_constants(C09_SRC / "params.py")
PVALS, PNOTES = params_entries(C09_SRC / "params.py")
est_c = module_constants(C09_SRC / "estimators.py")


def ccf_row(lv: int, design: str, treatment: str, agg: str) -> dict:
    return next(r for r in C09[lv]["outputs"]["ccf_by_design"]["rows"]
                if r["design"] == design and r["treatment"] == treatment and r["estimator"] == agg)


def c09_numbers() -> None:
    d0 = C09[3]["outputs"]
    put("ccf-tol", f"{d0['ccf_by_design']['tolerance']:.2f}")
    put("ccf-horizon", str(ccf_p["HORIZON"]))
    put("ccf-months", str(ccf_p["MONTHS"]))
    put("ccf-nrep", str(d0["replications"]["test"]["n_replications"]))
    put("ccf-nfac", f"{d0['replications']['test']['n_facilities']:,}")
    put("ccf-ndef-test", f"{d0['replications']['test']['n_defaults']:,}")
    put("ccf-ndef-dev", f"{d0['replications']['development']['n_defaults']:,}")
    put("ccf-anchor", f"{PVALS['ccf_anchor']:.2f}")
    put("ccf-frailty", f"{PVALS['frailty_shape']:g}")
    put("ccf-noise", f"{PVALS['ccf_noise_sd']:g}")
    put("ccf-small", f"{PVALS['small_undrawn_threshold']:g}")
    put("ccf-thinning", ", ".join(str(k) for k in est_c["THINNING"]))
    for lv in LEVELS:
        o = C09[lv]["outputs"]
        put(f"truth-{lv}", f"{o['generator']['true_ccf']['value']:.3f}")
        put(f"factor-{lv}", f"{o['generator']['acceleration_factor']:g}")
        put(f"window-{lv}", str(o["generator"]["acceleration_window_months"]))
        for r in o["ccf_by_design"]["rows"]:
            k = f"{r['design']}-{r['treatment']}-{r['estimator']}-{lv}"
            put(f"bias-{k}", plain(r["bias"], 3))
            put(f"biasfine-{k}", plain(r["bias"], 4))
            put(f"half-{k}", f"{(r['ci_high'] - r['ci_low']) / 2:.3f}")
            put(f"rmse-{k}", f"{r['rmse']:.3f}")
            put(f"est-{k}", f"{r['estimate']['value']:.3f}")
            put(f"within-{k}", "within" if r["within_tolerance"] else "outside")
    fh = d0["ccf_by_design"]["rows"][0]
    put("ccf-below0", pct(fh["share_below_zero"], 1))
    put("ccf-above1", pct(fh["share_above_one"], 1))
    put("ccf-dist-n", f"{d0['ccf_distribution']['n']:,}")
    put("ccf-undefined-share", pct(1.0 - d0["ccf_distribution"]["n"] / d0["replications"]["test"]["n_defaults"], 1))
    put("ccf-dist-below0", f"{d0['ccf_distribution']['n_below_zero']:,}")
    put("ccf-dist-above1", f"{d0['ccf_distribution']['n_above_one']:,}")
    # how many of the 24 rows of one level sit within the tolerance, by level
    for lv in LEVELS:
        rows = C09[lv]["outputs"]["ccf_by_design"]["rows"]
        put(f"within-count-{lv}", str(sum(r["within_tolerance"] for r in rows)))
        put(f"within-total-{lv}", str(len(rows)))
        fh_in = [r for r in rows if r["design"] == "fixed-horizon" and r["within_tolerance"]]
        put(f"within-fh-{lv}", str(len(fh_in)))
        put(f"within-nonfh-{lv}", str(sum(r["within_tolerance"] for r in rows if r["design"] != "fixed-horizon")))
    # EAD models
    dm = next(m for m in d0["ead_models"] if m["kind"] == "direct-ead")
    put("direct-clipped-above", f"{dm['n_clipped_above']:,}")
    put("direct-clipped-below", f"{dm['n_clipped_below']:,}")
    for mid in MODEL_NAME:
        rows = [r for r in d0["ead_backtest"]["rows"] if r["model_id"] == mid]
        worst = max(rows, key=lambda r: abs(r["relative_gap"]))
        put(f"ead-worst-{mid}", plain(worst["relative_gap"], 3))
        put(f"ead-worst-band-{mid}", worst["band_id"])
        t = next(t for t in C09[3]["tests"] if t["test_id"] == "lgd_ead.ead_backtest_by_band" and t["model_id"] == mid)
        put(f"ead-metric-{mid}", f"{t['metric']:.3f}")
        put(f"ead-light-{mid}", LIGHT[t["light"]])
        tot_p = sum(r["predicted_ead"] for r in rows)
        tot_r = sum(r["realised_ead"] for r in rows)
        put(f"ead-total-gap-{mid}", plain((tot_p - tot_r) / tot_r, 3))
    put("ead-bands", str(len(d0["ead_backtest"]["bands"]) - 1))
    put("small-switched", f"{d0['small_undrawn']['n_switched']:,}")
    # worst-band EAD gap of the direct model at every level
    for lv in LEVELS:
        rows = [r for r in C09[lv]["outputs"]["ead_backtest"]["rows"] if r["model_id"] == "direct-ead"]
        put(f"ead-direct-worst-{lv}", plain(max(rows, key=lambda r: abs(r["relative_gap"]))["relative_gap"], 3))
    # the floor bite of the supervisory EAD floor
    fl = d0["ead_floor"]["rows"]
    put("floor-binding", pct(max(r["share_binding"] for r in fl), 1))


def table_ccf_params() -> None:
    rows = [[lv, f"{ccf_p['LEVELS'][lv]['factor']:g}", ccf_p["LEVELS"][lv]["window"], C09[lv]["outputs"]["generator"]["true_ccf"]["value"]]
            for lv in LEVELS]
    figkit.table(
        HERE / "lgd-ead-levels-def.tex", ["Level", "Drawing factor", "Window (months)", "Known CCF at 12 months"], rows,
        caption="The six acceleration levels of the revolving-line generator: the factor that multiplies the monthly drawing weight inside "
                "the last months before default, the length of that window and the known credit conversion factor each level implies, "
                "computed in closed form from the generator parameters.",
        label="tab:lgd-ead-levels-def", align="rrrr", digits=3)
    keys = [("tier_share", "Risk-group shares (low, typical, high)"), ("tier_pd", "Twelve-month default probability by risk group"),
            ("ccf_anchor", "Known CCF of level 0"), ("frailty_shape", "Gamma shape of the line frailty"),
            ("tier_rate_multiplier", "Drawing-rate multiplier by risk group"), ("ccf_noise_sd", "Noise on the CCF (standard deviation)"),
            ("fee_sd", "Capitalised interest and fees, scale"), ("path_noise_sd", "Month-to-month balance noise, share of the limit"),
            ("over_cap", "Cap on utilisation over the limit"), ("small_undrawn_threshold", "Small-undrawn threshold (USD)")]
    rows = []
    for k, name in keys:
        v = PVALS[k]
        val = ", ".join(f"{x:g}" for x in v) if isinstance(v, (tuple, list)) else f"{v:g}"
        note = PNOTES.get(k, "")
        note = re.sub(r"^assumption of the case:\s*", "", note) or "from the Federal Reserve files"
        if PNOTES.get(k, "").startswith("assumption of the case"):
            origin = "case assumption"
        elif k == "over_cap":
            origin = "truncation of the Federal Reserve files"
        elif k == "small_undrawn_threshold":
            origin = "the switch of Qi (2009)"
        else:
            origin = "source file"
        rows.append([name, val, origin])
    figkit.table(
        HERE / "lgd-ead-generator.tex", ["Parameter", "Value", "Origin"], rows,
        caption="Fixed parameters of the revolving-line generator, read from the pipeline source of case C09: the origin column separates the "
                "values the case assumes from those that come from a rule of the engine or a source file; the marginals of limit, utilisation, "
                "score and rate come from the Federal Reserve 2025 card portfolios.",
        label="tab:lgd-ead-generator", align="p{6.6cm}lp{4.6cm}")


def table_ccf_designs() -> None:
    rows = []
    for design in DESIGN_NAME:
        for tr in TREATMENT_NAME:
            m, p = ccf_row(3, design, tr, "mean"), ccf_row(3, design, tr, "pooled")
            rows.append([DESIGN_NAME[design], TREATMENT_NAME[tr], pm(m["bias"], (m["ci_high"] - m["ci_low"]) / 2), "yes" if m["within_tolerance"] else "no",
                         pm(p["bias"], (p["ci_high"] - p["ci_low"]) / 2), "yes" if p["within_tolerance"] else "no"])
    figkit.table(
        HERE / "lgd-ead-designs.tex", ["Design", "Treatment", "Bias, mean", "In tol.", "Bias, pooled", "In tol."], rows,
        caption=f"Bias of the credit conversion factor estimators against the known value {C09[3]['outputs']['generator']['true_ccf']['value']:.3f} at level 3, "
                f"for each reference-date design, treatment of values outside [0, 1] and aggregator; the entry is the mean over {C09[3]['outputs']['replications']['test']['n_replications']} "
                "independent test replications with the half-width of its 95\\% interval, and the tolerance columns say whether the bias is "
                f"within {C09[3]['outputs']['ccf_by_design']['tolerance']:.2f}.",
        label="tab:lgd-ead-designs", align="llrcrc")


def table_ccf_levels() -> None:
    cols = [("fixed-horizon", "none", "mean", "Fixed horizon, mean"), ("fixed-horizon", "none", "pooled", "Fixed horizon, pooled"),
            ("fixed-horizon", "bounded-scale", "mean", "Fixed horizon, bounded scale"), ("cohort", "none", "pooled", "Cohort, pooled"),
            ("variable-horizon", "none", "pooled", "Variable horizon, pooled")]
    rows = []
    for lv in LEVELS:
        row = [lv, f"{C09[lv]['outputs']['generator']['true_ccf']['value']:.3f}"]
        for d, t, a, _ in cols:
            r = ccf_row(lv, d, t, a)
            row.append(pm(r["bias"], (r["ci_high"] - r["ci_low"]) / 2))
        rows.append(row)
    always = [c[3] for c in cols if all(ccf_row(lv, c[0], c[1], c[2])["within_tolerance"] for lv in LEVELS)]
    tol = C09[3]["outputs"]["ccf_by_design"]["tolerance"]
    if always:
        tail = f"the only column whose bias stays inside the tolerance of {tol:.2f} at every level is {always[0].lower()}."
    else:
        tail = f"no column keeps its bias inside the tolerance of {tol:.2f} at every level."
    figkit.table(
        HERE / "lgd-ead-levels.tex", ["Level", "Known CCF"] + [c[3] for c in cols], rows,
        caption="Bias of five credit conversion factor estimators at each of the six acceleration levels, as the mean over the independent "
                "test replications with the half-width of its 95\\% interval; " + tail,
        label="tab:lgd-ead-levels", align="rrrrrrr", wide=True)
    put("always-within", always[0] if always else "none")


def table_ead() -> None:
    d0 = C09[3]["outputs"]
    rows = []
    for mid, name in MODEL_NAME.items():
        rs = [r for r in d0["ead_backtest"]["rows"] if r["model_id"] == mid]
        tp, tr_ = sum(r["predicted_ead"] for r in rs), sum(r["realised_ead"] for r in rs)
        worst = max(rs, key=lambda r: abs(r["relative_gap"]))
        t = next(t for t in C09[3]["tests"] if t["test_id"] == "lgd_ead.ead_backtest_by_band" and t["model_id"] == mid)
        rows.append([name, f"{tp / 1e6:,.1f}", f"{tr_ / 1e6:,.1f}", neg((tp - tr_) / tr_), f"{worst['band_id']}", neg(worst["relative_gap"]), LIGHT[t["light"]]])
    figkit.table(
        HERE / "lgd-ead-backtest.tex", ["Model", "Predicted (USD m)", "Realised (USD m)", "Total gap", "Worst band", "Gap in it", "Light"], rows,
        caption="Back-test in currency of the eight exposure-at-default models on the independent test replications of level 3: predicted "
                "and realised exposure at default in millions of US dollars over all seven utilisation bands, the relative gap of the "
                "total, the band with the largest relative gap and the light of the band back-test.",
        label="tab:lgd-ead-backtest", align="lrrrcrl", wide=True)


def fit_width(name: str) -> None:
    """Scale a wide tabular down to the text width (graphicx resizebox) so that it never overfills the page."""
    path = HERE / f"lgd-ead-{name}.tex"
    text = path.read_text(encoding="utf-8")
    text = text.replace("\\begin{tabular}", "\\resizebox{\\textwidth}{!}{%\n\\begin{tabular}", 1)
    text = text.replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    c08_numbers()
    c09_numbers()
    table_settings()
    table_rmse()
    table_ladder_ref()
    table_ml()
    table_endpoint()
    table_ccf_params()
    table_ccf_designs()
    table_ccf_levels()
    table_ead()
    for name in ("ladder", "ml", "endpoint", "levels", "backtest", "designs"):
        fit_width(name)
    lines = ["% Generated by tables/make_lgd-ead.py: the numbers the section 'lgd-ead' quotes. Read in the text as \\LE{key}.", ""]
    for k in sorted(NUM):
        lines.append(f"\\expandafter\\gdef\\csname lgdead:{k}\\endcsname{{{NUM[k]}}}")
    (HERE / "lgd-ead-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {len(NUM)} numbers and the tables into {HERE}")


if __name__ == "__main__":
    main()
