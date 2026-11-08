"""Tables and numbers of the section on the product's own contributions (sections/17-proposed.tex).

Every table and every number macro is computed from the committed documents of ``data/derived`` (cases C01, C03, C04, C06, C07,
C10, C11, C12, C13, C14, C15, C16, C17, C18, C22), from the committed number files and result files of the sixteen method
manuscripts (``manuscripts/<slug>/tables/numbers.tex``, ``numbers.tex``, ``experiments/results.json``), and, for the sequential
monitor on the C11 windows, from the installed engine ``riskvalidation`` 1.1.0 applied to the committed exceedance days. No value is
copied from the design document: the source of each macro (the file and the key it was read from) is written to
``tables/proposed-numbers-sources.csv``. Output: ``tables/proposed-*.tex`` and ``tables/proposed-numbers.tex``.

Run from the repository root with the Python of the product's virtual environment::

    python manuscripts/contraste-technical-report/tables/make_proposed.py
"""
from __future__ import annotations

import json
import decimal
import pathlib
import re
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "_shared"))
import figkit  # noqa: E402

MS = HERE.parents[1]  # the manuscripts folder
#: macro -> (source file relative to the repository root, key read there), written to proposed-numbers-sources.csv
SOURCES: dict[str, tuple[str, str]] = {}

_MAC = re.compile(r"\\newcommand\{\\(\w+)\}\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}")
_NV = re.compile(r"\\expandafter\\def\\csname num@([^\\]+)\\endcsname\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}")
_PAPER_CACHE: dict[str, tuple[dict[str, tuple[str, str]], str]] = {}


def paper(slug: str) -> tuple[dict[str, tuple[str, str]], str]:
    """The number macros of a method manuscript (newcommand or csname num@key definitions) and, per macro, the value and the file."""
    if slug not in _PAPER_CACHE:
        vals: dict[str, tuple[str, str]] = {}
        files = sorted((MS / slug / "tables").glob("*.tex")) + [MS / slug / "numbers.tex"]
        for p in files:
            if not p.exists():
                continue
            txt = p.read_text(encoding="utf-8")
            rel = f"manuscripts/{slug}/{p.relative_to(MS / slug).as_posix()}"
            for m in list(_MAC.finditer(txt)) + list(_NV.finditer(txt)):
                vals.setdefault(m.group(1), (m.group(2), rel))
        if not vals:
            raise FileNotFoundError(f"no number macros in manuscripts/{slug}")
        _PAPER_CACHE[slug] = (vals, "")
    return _PAPER_CACHE[slug]


def pv(slug: str, key: str) -> str:
    """One value of a method manuscript's number files, as LaTeX text (a thousands brace group becomes a comma)."""
    vals, _ = paper(slug)
    if key not in vals:
        raise KeyError(f"{key} is not defined in the number files of manuscripts/{slug}")
    return vals[key][0].replace("{,}", ",")


def pfile(slug: str, key: str) -> str:
    return paper(slug)[0][key][1]


def results_json(slug: str, rel: str = "experiments/results.json"):
    return json.loads((MS / slug / rel).read_text(encoding="utf-8"))

OUT = HERE
EIGHT = ["null", "miscalibration", "clustering", "drift", "discrimination-decay", "leakage", "broken-monotonicity", "concentration"]
VARIANTS = ["none", "missing-basis", "stale-volatility", "wrong-correlation", "omitted-factor", "time-misalignment"]
VLABEL = {"none": "no deficiency", "missing-basis": "missing basis", "stale-volatility": "stale volatility",
          "wrong-correlation": "wrong correlation", "omitted-factor": "omitted factor", "time-misalignment": "time misalignment"}
WINDOWS = ["equity-2007-09", "fx-2008", "equity-2020", "rates-2022", "calm-2004-06", "mixed-2023"]
STRESS = ["equity-2007-09", "equity-2020", "rates-2022"]
MODEL_LABEL = {"hs-250": "HS-250", "garch-t": "GARCH-t", "fhs": "FHS"}

def D(rel: str):
    d = figkit.doc(rel)
    return d.get("outputs") or d


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def pct_half_up(x: float, d: int = 1) -> str:
    """A share in percent rounded half up on its decimal form (0.0885 prints 8.9, where the binary float prints 8.8)."""
    q = decimal.Decimal(1).scaleb(-d)
    return str((decimal.Decimal(str(x)) * 100).quantize(q, rounding=decimal.ROUND_HALF_UP))


def wilson_str(r: dict) -> str:
    return f"{pct(r['rate'])} ({pct(r['ci_low'])} to {pct(r['ci_high'])})"


def yn(b: bool) -> str:
    return "yes" if b else "no"


# ----------------------------------------------------------------------------------------------------------------- data
def load() -> dict:
    A: dict = {}
    # BS-1: the measurement of C22
    rows, fam = [], {}
    for f in EIGHT:
        o = D(f"C22/{f}.json")
        sims = [s for s in o["simulations"] if not s.get("study")]
        fam[f] = sims
        rows += sims
        if f == "null":
            A["size_bounds"] = o["size_bounds"]
            seen, tests = set(), []
            for s in sims:
                if s["test_id"] not in seen:
                    seen.add(s["test_id"])
                    tests.append(s)
            A["size_tests"] = tests
    A["c22_family"] = fam
    A["c22_rows"] = rows
    leak = D("C22/leakage.json")["simulations"]
    A["leak"] = {(s["test_id"], s["severity"]): s["rates"]["p<0.05"] for s in leak}
    # BS-2: the reconciliation with ORE
    A["ore"] = {}
    for v in ["single-swap", "netting-set", "csa-mpor-10d", "csa-mpor-20d", "with-im"]:
        A["ore"][v] = D(f"C12/{v}.json")["ore_reconciliation"]
    A["ore_paths"] = D("C12/single-swap.json")["named_parameters"]["path_count"]["value"]
    # BS-4
    w = D("C04/withdrawals.json")
    A["wd"] = w
    A["thin"] = D("C04/thin.json")
    A["sp_impact"] = figkit.doc("C04/sp.json")["impact"]
    # BS-7, BS-9, BS-11, BS-12
    A["short_uf"] = D("C15/short-uf.json")
    A["long_uf"] = D("C15/long-uf.json")
    A["band"] = D("C18/baseline.json")["aggregation"]["band"]
    A["rev"] = D("C16/reverse-stress.json")
    A["fast_run"] = D("C16/fast-run.json")
    A["c17"] = {x: D(f"C17/{x}.json") for x in ["xi-0-6", "xi-0-8", "xi-0-96", "xi-1-1"]}
    # BS-13
    A["c13"] = {v: D(f"C13/{v}.json") for v in VARIANTS}
    # BS-14
    A["sp"] = D("C04/sp.json")
    # BS-15
    A["seq"] = D("C22/other-families.json")["sequential"]
    A["c03"] = {x: D(f"C03/{x}.json") for x in ["fy2006-07", "fy2008-10", "fy2011-14", "fy2015-17", "fy2018-20"]}
    A["c11"] = {x: D(f"C11/{x}.json") for x in WINDOWS}
    return A


# ------------------------------------------------------------------------------------------------- sequential on C11
def c11_eprocess(A: dict) -> list[dict]:
    """The rate e-process of the engine (``var_hit_eprocess``, defaults) on the committed exceedance days of every model, per
    window, against the Basel traffic light (first day on which the trailing 250 days hold 5 or more exceptions)."""
    from riskvalidation.validation.sequential import var_hit_eprocess

    out = []
    for wid in WINDOWS:
        doc = A["c11"][wid]
        n = doc["window"]["n_forecast_days"]
        rec = {"window": wid, "days": n, "models": 0, "light": 0, "eproc": 0, "e_days": [], "l_days": [], "both": 0}
        for m in doc["models"]:
            lv = [x for x in m["by_level"] if abs(x["alpha"] - 0.01) < 1e-12]
            if not lv:
                continue
            ex = lv[0]["exceedance_days"]
            assert all(0 <= d < n for d in ex), (wid, m["model_id"])
            hits = np.zeros(n, dtype=int)
            hits[ex] = 1
            rec["models"] += 1
            res = var_hit_eprocess(hits, 0.01)
            e_day = res.rejection_time if res.rejected else None
            csum = np.concatenate([[0], np.cumsum(hits)])
            l_day = None
            for t in range(250, n + 1):
                if csum[t] - csum[t - 250] >= 5:
                    l_day = t
                    break
            if e_day is not None:
                rec["eproc"] += 1
                rec["e_days"].append(e_day)
            if l_day is not None:
                rec["light"] += 1
                rec["l_days"].append(l_day)
            if e_day is not None and l_day is not None:
                rec["both"] += 1
        out.append(rec)
    return out


def med(xs):
    return float(np.median(xs)) if xs else None


# --------------------------------------------------------------------------------------------------------------- build
def build() -> dict:
    A = load()
    N: dict[str, str] = {}

    current: list = [None]

    def use(file, key):
        """The source of the macros put until the next call: the file(s) they are read from and what is read there."""
        current[0] = (file, key)

    def put(k, v, src=None):
        s = src or current[0]
        if s is None or not s[0] or s[0] == "data/derived":
            raise ValueError(f"macro {k} names no source file")
        N[k] = str(v)
        SOURCES[k] = s

    def ppt(k, slug, key):
        """A number copied from the number file of a method manuscript, with its source."""
        put(k, pv(slug, key), (pfile(slug, key), key))

    # ---- BS-1
    C22 = "data/derived/C22/{null,miscalibration,clustering,drift,discrimination-decay,leakage,broken-monotonicity,concentration}.json"
    use(C22, "simulations[] (n_rep, rates, exact) and size_bounds; the null family decides the size counts, leakage.json the leakage rates")
    rows = A["c22_rows"]
    put("oneSims", len(rows))
    put("oneReps", f"{sum(s['n_rep'] for s in rows):,}")
    put("oneRates", sum(len(s["rates"]) for s in rows))
    put("oneExact", sum(1 for s in rows if s.get("exact")))
    put("oneGens", len({s["generator"] for s in rows if s.get("generator")}))
    put("oneFamilies", len(EIGHT))
    tests = A["size_tests"]
    b05 = A["size_bounds"]["p<0.05"]
    put("oneTests", len(tests))
    put("oneBound", f"{100 * b05:.2f}")
    over = [s for s in tests if s["rates"]["p<0.05"]["rate"] > b05]
    put("oneOver", len(over))
    # the rule of the pipeline: the exact rejection probability where one exists, the one-sided Monte Carlo bound otherwise
    within_both = [s for s in tests if all(
        (s["exact"][lv] <= float(lv[2:]) + 1e-12) if s["exact"] is not None else (s["rates"][lv]["rate"] <= A["size_bounds"][lv])
        for lv in ("p<0.05", "p<0.01"))]
    assert len(within_both) == round(figkit.doc("C22/null.json")["impact"]["tests_within_bound"]["value"])
    put("oneWithinBoth", len(within_both))
    put("oneOverName", figkit.tex_escape(over[0]["test_id"]) if over else "none")
    put("oneOverRate", pct(over[0]["rates"]["p<0.05"]["rate"], 2) if over else "0")
    put("oneNullReps", f"{tests[0]['n_rep']:,}")
    put("oneNullTotal", f"{sum(s['n_rep'] for s in tests):,}")
    lk = A["leak"]
    put("oneLeakAucOne", pct_half_up(lk[("disc.auc_vs_initial", 1)]["rate"], 1))
    put("oneLeakAucTwo", pct_half_up(lk[("disc.auc_vs_initial", 2)]["rate"], 1))
    put("oneLeakCsiFive", pct_half_up(lk[("stability.csi", 5)]["rate"], 1))
    put("oneLeakCsiOne", pct_half_up(lk[("stability.csi", 1)]["rate"], 1))
    put("oneLeakReps", f"{lk[('disc.auc_vs_initial', 1)]['n']:,}")
    put("oneHoldFive", len(tests) - len(over))
    jeff = [s for s in tests if s["test_id"] == "pd.jeffreys"][0]
    put("oneJeffExactOne", pct(jeff["exact"]["p<0.01"], 2), ("data/derived/C22/null.json", "pd.jeffreys exact p<0.01"))
    put("oneJeffExactFive", pct(jeff["exact"]["p<0.05"], 2), ("data/derived/C22/null.json", "pd.jeffreys exact p<0.05"))
    hhi = [s for s in tests if s["test_id"] == "rating.hhi"][0]
    put("oneHhiRate", pct(hhi["rates"]["p<0.05"]["rate"], 2), ("data/derived/C22/null.json", "rating.hhi rate p<0.05"))
    mig = [s for s in tests if s["test_id"] == "rating.migration_ztests"][0]
    put("oneMigRate", pct(mig["rates"]["p<0.05"]["rate"], 2), ("data/derived/C22/null.json", "rating.migration_ztests rate p<0.05"))
    put("oneBoundOne", f"{100 * A['size_bounds']['p<0.01']:.2f}")
    put("oneLeakPowerReps", f"{lk[('disc.auc_vs_initial', 1)]['n']:,}")
    put("oneLeakCsiThree", pct(lk[("stability.csi", 3)]["rate"], 1))
    put("oneLeakCsiTwo", pct(lk[("stability.csi", 2)]["rate"], 1))
    put("oneLeakCsiFour", pct(lk[("stability.csi", 4)]["rate"], 1))
    # ---- BS-2
    use("data/derived/C12/{single-swap,netting-set,csa-mpor-10d,csa-mpor-20d,with-im}.json",
        "ore_reconciliation.agreement, eepe_agreement, cva_agreement (differences over combined standard errors)")
    for v, key in [("single-swap", "Single"), ("netting-set", "Netting"), ("csa-mpor-10d", "CsaTen"), ("csa-mpor-20d", "CsaTwenty"),
                   ("with-im", "Im")]:
        r = A["ore"][v]
        ag = r["agreement"]
        put(f"two{key}Dates", len(ag))
        put(f"two{key}Out", sum(1 for x in ag if not x["within_two_se"]))
        put(f"two{key}Max", f"{max(abs(x['difference']) / x['combined_se'] for x in ag):.1f}")
        put(f"two{key}Eepe", f"{abs(r['eepe_agreement']['difference']) / r['eepe_agreement']['combined_se']:.2f}")
        put(f"two{key}Cva", f"{abs(r['cva_agreement']['difference']) / r['cva_agreement']['combined_se']:.2f}")
    put("twoOreVersion", A["ore"]["single-swap"]["ore_version"])
    put("twoEnginePaths", f"{A['ore_paths']:,}", ("data/derived/C12/single-swap.json", "outputs.named_parameters.path_count"))
    m = re.search(r"(\d+) samples", A["ore"]["single-swap"]["platform"])
    put("twoOreSamples", f"{int(m.group(1)):,}", ("data/derived/C12/single-swap.json", "outputs.ore_reconciliation.platform"))
    # ---- BS-4
    use("data/derived/C04/withdrawals.json", "rungs (the rung whose value is 9.0, grade B: pd_removed, pd_kept, pd_followed mean and n; rung 0 for the zero case)")
    wd = A["wd"]
    r9 = [r for r in wd["rungs"] if r["value"] == 9.0][0]
    ib = 5  # grade B
    tr = r9["pd_latent"]["truth"][ib] if "truth" in r9["pd_latent"] else None
    truth = wd["rungs"][0]["pd_removed"]["truth"][ib]
    put("fourTruthB", pct(truth, 2))
    for k, nm in [("pd_removed", "Removed"), ("pd_kept", "Kept"), ("pd_followed", "Followed")]:
        put(f"four{nm}B", f"{100 * (r9[k]['mean'][ib] - truth) / truth:.0f}")
    r0 = wd["rungs"][0]
    put("fourRemovedZero", f"{100 * (r0['pd_removed']['mean'][ib] - truth) / truth:+.0f}")
    for k, nm in [("pd_removed", "Removed"), ("pd_kept", "Kept"), ("pd_followed", "Followed")]:
        put(f"four{nm}Se", f"{100 * r9[k]['bias_mcse'][ib] / truth:.1f}", ("data/derived/C04/withdrawals.json", f"rungs[value == 9.0].{k}.bias_mcse"))
    put("fourRemovedZeroSe", f"{100 * r0['pd_removed']['bias_mcse'][ib] / truth:.1f}", ("data/derived/C04/withdrawals.json", "rungs[0].pd_removed.bias_mcse"))
    put("fourReps", r9["pd_removed"]["n"][ib] if isinstance(r9["pd_removed"]["n"], list) else r9["pd_removed"]["n"])
    sims = {s["key"]: s for s in wd["simulations"]}
    for tid, nm in [("rating.time_homogeneity", "Th"), ("rating.matrix_reference", "Mr")]:
        rr = sims[f"{tid}@k9"]["rates"]["p<0.05"]
        put(f"four{nm}Nine", pct(rr["rate"], 1), ("data/derived/C04/withdrawals.json", f"simulations {tid}@k9 p<0.05"))
        put(f"four{nm}NineHi", pct(rr["wilson_high"], 1), ("data/derived/C04/withdrawals.json", f"simulations {tid}@k9 wilson_high"))
    sp_imp = A["sp_impact"]
    put("oneRegCerepLong", f"{100 * sp_imp['lra_d2_ccc_c']['value']:.2f}", ("data/derived/C04/sp.json", "impact.lra_d2_ccc_c"))
    put("oneRegTransLong", f"{100 * sp_imp['lra_d4_ccc_c']['value']:.2f}", ("data/derived/C04/sp.json", "impact.lra_d4_ccc_c"))
    put("fourRwBefore", f"{100 * sp_imp['rw_d2']['value']:.1f}", ("data/derived/C04/sp.json", "impact.rw_d2"))
    put("fourRwAfter", f"{100 * sp_imp['rw_d4']['value']:.1f}", ("data/derived/C04/sp.json", "impact.rw_d4"))
    use("data/derived/C04/thin.json", "rungs[0].coverage (wald, jeffreys) and value")
    thin = A["thin"]["rungs"][0]
    put("fourThinN", thin["value"])
    put("fourWaldAaa", pct(thin["coverage"]["wald"][0], 2))
    put("fourJeffAaa", pct(thin["coverage"]["jeffreys"][0], 1))
    # ---- BS-7
    use("data/derived/C15/short-uf.json", "indexation_charge, nii.delta_nii, floors.distances")
    su = A["short_uf"]
    put("sevenCharge", f"{su['indexation_charge']['charge']:,.1f}")
    put("sevenShare", pct(su["indexation_charge"]["charge"] / su["nii"]["delta_nii"], 1))
    put("sevenFloorBp", f"{min(d['distance_bp'] for d in su['floors']['distances'] if d['leg'] != 'CLP'):.2f}")
    put("sevenChargeUnit", su["indexation_charge"].get("unit", "currency units"))
    # ---- BS-9
    use("data/derived/C18/baseline.json", "aggregation.band (capital_clp_m and mc_se_clp_m by method and nu)")
    band = A["band"]
    sums = {(r["method"], r["nu"]): r["capital_clp_m"] for r in band}
    put("nineSum", f"{sums[('simple-sum', None)]:,.0f}")
    put("nineLower", f"{sums[('lower-bound', None)]:,.0f}")
    put("nineWorst", f"{sums[('worst-case', None)]:,.0f}")
    put("nineGauss", f"{sums[('gaussian-copula', None)]:,.0f}")
    put("nineVc", f"{sums[('variance-covariance', None)]:,.0f}")
    put("nineTfour", f"{sums[('t-copula', 4.0)]:,.0f}")
    put("nineRows", len(band))
    se = {(r["method"], r["nu"]): r["mc_se_clp_m"] for r in band}
    put("nineGaussSe", f"{se[('gaussian-copula', None)]:,.0f}", ("data/derived/C18/baseline.json", "aggregation.band mc_se_clp_m"))
    put("nineTfourSe", f"{se[('t-copula', 4.0)]:,.0f}", ("data/derived/C18/baseline.json", "aggregation.band mc_se_clp_m"))
    put("nineTfourEightSe", f"{se[('t-copula', 8.0)]:,.0f}", ("data/derived/C18/baseline.json", "aggregation.band mc_se_clp_m"))
    put("nineWorstRatio", f"{sums[('worst-case', None)] / sums[('simple-sum', None)]:.2f}")
    put("nineGaussRatio", f"{sums[('gaussian-copula', None)] / sums[('simple-sum', None)]:.2f}")
    # ---- BS-8
    import glob
    lights = []
    for f in sorted(glob.glob(str(figkit.DERIVED / "C14" / "vd-*.json"))):
        d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        for tt in d["tests"]:
            if tt["test_id"] == "irrbb.behavioural_change_at_breach":
                lights.append(tt["light"])
    put("eightRedDates", sum(1 for x in lights if x == "red"), ("data/derived/C14/vd-*.json", "irrbb.behavioural_change_at_breach light"))
    put("eightDatesEvaluated", sum(1 for x in lights if x != "not_evaluated"), ("data/derived/C14/vd-*.json", "irrbb.behavioural_change_at_breach light"))
    put("eightDates", len(lights), ("data/derived/C14/vd-*.json", "irrbb.behavioural_change_at_breach light"))
    # ---- BS-11
    use("data/derived/C16/reverse-stress.json", "bases[] (solved, base_survival, max_multiplier) and target.days")
    for b in A["rev"]["bases"]:
        s = b["solved"]
        key = {"list-adverse": "Adverse", "list-extreme": "Extreme", "fast-run": "Fast"}[b["base_id"]]
        put(f"eleven{key}", f"{s['multiplier']:.6f}" if s["status"] == "solved" else "refused")
        put(f"eleven{key}Day", b["base_survival"]["day"] if b["base_survival"]["day"] else b["base_survival"]["horizon_days"])
    put("elevenTarget", A["rev"]["target"]["days"])
    put("elevenSvb", f"{A['fast_run']['scoring']['denominators'][0]['modelled_share']:.4f}", ("data/derived/C16/fast-run.json", "outputs.scoring.denominators[0].modelled_share"))
    put("elevenCapAdverse", f"{[b for b in A['rev']['bases'] if b['base_id'] == 'list-adverse'][0]['max_multiplier']:.1f}")
    # ---- BS-12
    use("data/derived/C17/{xi-0-6,xi-0-8,xi-0-96,xi-1-1}.json", "cells[] (capital.lda_splice.iqr_over_truth, replications.n_replications)")
    cells = []
    for tag, doc in A["c17"].items():
        for c in doc["cells"]:
            cells.append((doc["tail_index"], c))
    iqr = [c["capital"]["lda_splice"]["iqr_over_truth"] for _, c in cells if c["capital"]["lda_splice"]]
    put("twelveCells", len(cells))
    put("twelveHistories", f"{sum(c['replications']['n_replications'] for _, c in cells):,}")
    put("twelveIqrMin", f"{min(iqr):.2f}")
    put("twelveIqrMax", f"{max(iqr):.2f}")
    rows12 = [tt for tag in A["c17"] for tt in figkit.doc(f"C17/{tag}.json")["tests"] if tt["test_id"] == "oprisk.capital_stability"]
    put("twelveRedRows", sum(1 for tt in rows12 if tt["light"] == "red"), ("data/derived/C17/xi-*.json", "tests oprisk.capital_stability light"))
    put("twelveRows", len(rows12), ("data/derived/C17/xi-*.json", "tests oprisk.capital_stability"))
    put("twelveRungs", len({tt["model_id"] for tt in rows12}), ("data/derived/C17/xi-*.json", "tests oprisk.capital_stability model_id"))
    share = {}
    for tag in ("xi-0-96", "xi-1-1"):
        share[tag] = [x["share_at_least_one"] for c in A["c17"][tag]["cells"] for x in c["threshold_stability"]
                      if x["threshold_eur"] == c["collection_threshold_eur"]]
    put("twelveInfLow", pct(min(share["xi-0-96"]), 1), ("data/derived/C17/xi-0-96.json", "cells[].threshold_stability.share_at_least_one"))
    put("twelveInfHigh", pct(max(share["xi-0-96"]), 1), ("data/derived/C17/xi-0-96.json", "cells[].threshold_stability.share_at_least_one"))
    put("twelveFiniteLow", pct(1 - max(share["xi-1-1"]), 1), ("data/derived/C17/xi-1-1.json", "cells[].threshold_stability.share_at_least_one"))
    put("twelveFiniteHigh", pct(1 - min(share["xi-1-1"]), 1), ("data/derived/C17/xi-1-1.json", "cells[].threshold_stability.share_at_least_one"))
    c096 = A["c17"]["xi-0-96"]["cells"][0]["capital"]
    put("twelveLnShare", pct(c096["lda_lognormal"]["share_underestimating"], 0), ("data/derived/C17/xi-0-96.json", "cells[0].capital.lda_lognormal.share_underestimating"))
    put("twelveLnIqr", pct(c096["lda_lognormal"]["iqr_over_truth"], 2), ("data/derived/C17/xi-0-96.json", "cells[0].capital.lda_lognormal.iqr_over_truth"))
    put("twelveTruncShare", pct(c096["lda_lognormal_truncated"]["share_underestimating"], 0), ("data/derived/C17/xi-0-96.json", "cells[0].capital.lda_lognormal_truncated.share_underestimating"))
    put("twelveHistoriesPerCell", A["c17"]["xi-0-96"]["cells"][0]["replications"]["n_replications"])
    # ---- BS-13
    use("data/derived/C13/{none,missing-basis,stale-volatility,wrong-correlation,omitted-factor,time-misalignment}.json",
        "pla_complement (n_replications, flags, calibration, lag_ladder, against_ks, hypothesis), detection, pla.thresholds, generator")
    c13 = A["c13"]
    stale = c13["stale-volatility"]["pla_complement"]
    h = stale["hypothesis"]
    put("thirteenN", f"{stale['n_replications']:,}")
    put("thirteenNull", f"{stale['calibration']['n_null']:,}")
    put("thirteenWindow", stale["window_days"])
    put("thirteenPower", wilson_str(h["measured_power"]))
    put("thirteenPowerRate", pct(h["measured_power"]["rate"]))
    put("thirteenCiLo", pct(h["measured_power"]["ci_low"]))
    put("thirteenCiHi", pct(h["measured_power"]["ci_high"]))
    put("thirteenUnionPower", pct(stale["flags"]["family"]["any"]["rate"]))
    put("thirteenUnionK", stale["flags"]["family"]["any"]["k"])
    put("thirteenHeld", pct(h["held_out_size"]["rate"]))
    put("thirteenHeldCi", f"{pct(h['held_out_size']['ci_low'], 2)} to {pct(h['held_out_size']['ci_high'], 2)}")
    put("thirteenPla", pct(h["pla_power"]["rate"]))
    put("thirteenThresholdPower", pct(h["power_threshold"], 0))
    put("thirteenRefuted", pct(h["refuted_below"], 0))
    put("thirteenSize", pct(h["size_limit"], 0))
    thr = stale["calibration"]["thresholds_family"]
    put("thirteenWaldCut", f"{thr['wald']:.3f}")
    put("thirteenAbsCut", f"{thr['spearman_abs']:.4f}")
    put("thirteenRollCut", f"{thr['spearman_roll']:.4f}")
    thr1 = stale["calibration"]["thresholds_per_statistic"]
    put("thirteenWaldCutOne", f"{thr1['wald']:.3f}")
    put("thirteenAbsCutOne", f"{thr1['spearman_abs']:.4f}")
    put("thirteenRollCutOne", f"{thr1['spearman_roll']:.4f}")
    put("thirteenKsFlag", stale["against_ks"]["ks_flagged"])
    put("thirteenWaldFlag", stale["against_ks"]["wald_flagged"])
    put("thirteenMisalignRoll", pct(c13["time-misalignment"]["pla_complement"]["flags"]["per_statistic"]["spearman_roll"]["rate"]))
    put("thirteenMisalignPla", pct(c13["time-misalignment"]["detection"]["share_amber_or_red"], 1))
    put("thirteenWrongRoll", pct(c13["wrong-correlation"]["pla_complement"]["flags"]["per_statistic"]["spearman_roll"]["rate"]))
    put("thirteenWrongPla", pct(c13["wrong-correlation"]["detection"]["share_amber_or_red"], 1))
    put("thirteenNullUnion", pct(c13["none"]["pla_complement"]["flags"]["family"]["any"]["rate"]))
    put("thirteenMissingWald", pct(c13["missing-basis"]["pla_complement"]["flags"]["per_statistic"]["wald"]["rate"]))
    put("thirteenMissingPla", pct(c13["missing-basis"]["detection"]["share_amber_or_red"], 1))
    put("thirteenMissingAbs", pct(c13["missing-basis"]["pla_complement"]["flags"]["per_statistic"]["spearman_abs"]["rate"]))
    lag = {x["lag_days"]: x for x in stale["lag_ladder"]}
    for L_ in (5, 10, 20, 40):
        put(f"thirteenLag{ {5: 'Five', 10: 'Ten', 20: 'Twenty', 40: 'Forty'}[L_] }", pct(lag[L_]["per_statistic"]["spearman_roll"]["rate"]))
        put(f"thirteenLagPla{ {5: 'Five', 10: 'Ten', 20: 'Twenty', 40: 'Forty'}[L_] }", pct(lag[L_]["pla_amber_or_red"]["rate"]))
    th = c13["none"]["pla"]["thresholds"]
    put("thirteenSpGreen", f"{th['spearman_green']}")
    put("thirteenSpRed", f"{th['spearman_red']}")
    put("thirteenKsGreen", f"{th['ks_green']}")
    put("thirteenKsRed", f"{th['ks_red']}")
    put("thirteenPlaDays", th["window_days"])
    kd = c13["stale-volatility"]["known_deficiency"]["parameters"][0]
    put("thirteenVolLag", f"{kd['value']:.0f}")
    put("thirteenFactors", c13["stale-volatility"]["generator"]["n_risk_factors"])
    put("thirteenNullSeeds", len(stale["calibration"]["null_case_seeds"]))
    put("thirteenNullBlock", f"{stale['calibration']['n_per_block']:,}")
    put("thirteenSeedBase", c13["stale-volatility"]["generator"]["seed_base"])
    # ---- BS-14
    use("data/derived/C04/withdrawals.json", "bounds_verdict.rows (coverage by design, informativeness and treatment), design.years, rungs[0].withdrawal_rate")
    bv = wd["bounds_verdict"]
    put("fourteenExitRate", pct(wd["rungs"][0]["withdrawal_rate"], 0))
    put("fourteenYears", wd["design"]["years"])
    cov = {}
    for r in bv["rows"]:
        cov[(r["design"], r["informative"], r["treatment"])] = r
    put("fourteenReps", bv["reps"])
    put("fourteenAnchoredOne", pct(cov[("first_year", 1.0, "anchored")]["value"]))
    put("fourteenAnchoredThree", pct(cov[("first_year", 3.0, "anchored")]["value"]))
    put("fourteenAnchoredNine", pct(cov[("first_year", 9.0, "anchored")]["value"]))
    put("fourteenIndustryNine", pct(cov[("first_year", 9.0, "industry")]["value"]))
    put("fourteenUnfollowedNine", pct(cov[("first_year", 9.0, "unfollowed")]["value"]))
    put("fourteenFollowedNine", pct(cov[("first_year", 9.0, "followed")]["value"]))
    put("fourteenFollowedTen", pct(cov[("first_year_x10", 9.0, "followed")]["value"]))
    put("fourteenExistingFirstYearHold", sum(1 for r in bv["rows"] if r["id"] == "existing-coverage" and r["design"] == "first_year" and r["holds"]))
    assert not bv["summary"]["existing_under_50"], "the second clause is written as failed; the artifact says it holds"
    put("fourteenIndustryPooled", pct(cov[("pooled", 9.0, "industry")]["value"]))
    put("fourteenUnfollowedPooled", pct(cov[("pooled", 9.0, "unfollowed")]["value"]))
    put("fourteenFollowedPooled", pct(cov[("pooled", 9.0, "followed")]["value"]))
    put("fourteenIndustryTen", pct(cov[("first_year_x10", 9.0, "industry")]["value"]))
    put("fourteenUnfollowedTen", pct(cov[("first_year_x10", 9.0, "unfollowed")]["value"]))
    put("fourteenCoverTarget", pct(bv["rows"][0]["threshold"], 0))
    put("fourteenExistingTarget", pct([r for r in bv["rows"] if r["id"] == "existing-coverage"][0]["threshold"], 0))
    use("data/derived/C04/sp.json", "withdrawal_bounds.grades[] (pooled k and band, stability) and stability_share")
    grades = {g["grade"]: g for g in A["sp"]["withdrawal_bounds"]["grades"]}
    ccc = grades["CCC-C"]
    put("fourteenCccK", f"{ccc['pooled']['k']:.1f}")
    put("fourteenCccLow", f"{ccc['pooled']['k_low']:.1f}")
    put("fourteenCccHigh", f"{ccc['pooled']['k_high']:.1f}")
    put("fourteenCccShare", pct(ccc["stability"]["share_cohorts_containing_pooled_k"], 0))
    put("fourteenStability", pct(A["sp"]["withdrawal_bounds"]["stability_share"], 0))
    put("fourteenBK", f"{grades['B']['pooled']['k']:.1f}")
    put("fourteenBShare", pct(grades["B"]["stability"]["share_cohorts_containing_pooled_k"], 0))
    put("fourteenBTruth", pct(truth, 2), ("data/derived/C04/withdrawals.json", "rungs[0].pd_removed.truth[B]"))
    # ---- BS-15
    OF = "data/derived/C22/other-families.json"
    use(OF, "sequential.hits.scenarios, sequential.pd_grades.scenarios, sequential.method and hypotheses[].values")
    seq = A["seq"]
    sc = {s["id"]: s for s in seq["hits"]["scenarios"]}
    put("fifteenThreshold", f"{seq['method']['threshold']:.0f}")
    put("fifteenAlpha", pct(seq["method"]["alpha_level"], 0))
    put("fifteenReps", f"{seq['hits']['reps']:,}")
    put("fifteenHorizon", f"{seq['hits']['horizon']:,}")
    put("fifteenWindow", seq["hits"]["window"])
    put("fifteenENull", pct(sc["null"]["e_rate"]["ever"]))
    put("fifteenKupTrail", pct(sc["null"]["kupiec_trailing"]["ever"]))
    put("fifteenKupCum", pct(sc["null"]["kupiec_cumulative"]["ever"]))
    put("fifteenLightNull", pct(sc["null"]["traffic_light"]["ever"]))
    put("fifteenXThreeDay", f"{sc['rate-x3']['e_rate']['median_day']:.0f}")
    put("fifteenXFourDay", f"{sc['rate-x4']['e_rate']['median_day']:.0f}")
    put("fifteenXThreeKupDay", f"{sc['rate-x3']['kupiec_cumulative']['median_day']:.0f}")
    put("fifteenXFourKupDay", f"{sc['rate-x4']['kupiec_cumulative']['median_day']:.0f}")
    put("fifteenLightDay", f"{sc['rate-x3']['traffic_light']['median_day']:.0f}")
    hyp = {x["id"]: x for x in seq["hypotheses"]}
    vals = {x["id"]: x["value"] for h_ in seq["hypotheses"] for x in h_["values"]}
    put("fifteenCostThree", pct_half_up(vals["x3_power_cost"]))
    put("fifteenCostFour", pct_half_up(vals["x4_power_cost"]))
    put("fifteenBound", pct(vals["bound"]))
    # the pooled replication of the case document (20 seeds of 2,000 streams) decides the delay and power clauses
    rpl = seq["replication"]
    fac = {f["id"]: f for f in rpl["factors"]}
    f3, f4 = fac["rate-x3"], fac["rate-x4"]
    kf = "sequential.replication.factors"
    put("fifteenPoolSeeds", rpl["seeds"], (OF, "sequential.replication.seeds"))
    put("fifteenPoolReps", f"{rpl['reps']:,}", (OF, "sequential.replication.reps"))
    put("fifteenPoolThreeMed", f"{f3['pooled_median']:.0f}", (OF, f"{kf}[rate-x3].pooled_median"))
    put("fifteenPoolThreeLo", f"{f3['pooled_median_ci'][0]:.0f}", (OF, f"{kf}[rate-x3].pooled_median_ci[0]"))
    put("fifteenPoolThreeHi", f"{f3['pooled_median_ci'][1]:.0f}", (OF, f"{kf}[rate-x3].pooled_median_ci[1]"))
    put("fifteenPoolFourMed", f"{f4['pooled_median']:.0f}", (OF, f"{kf}[rate-x4].pooled_median"))
    put("fifteenPoolLight", f"{f3['pooled_traffic_light_median']:.0f}", (OF, f"{kf}[rate-x3].pooled_traffic_light_median"))
    put("fifteenPoolCostThree", pct_half_up(f3["pooled_power_cost"]), (OF, f"{kf}[rate-x3].pooled_power_cost"))
    put("fifteenPoolCostThreeSe", pct_half_up(f3["pooled_power_cost_se"]), (OF, f"{kf}[rate-x3].pooled_power_cost_se"))
    put("fifteenPoolCostFour", pct_half_up(f4["pooled_power_cost"]), (OF, f"{kf}[rate-x4].pooled_power_cost"))
    put("fifteenPoolCostFourSe", pct_half_up(f4["pooled_power_cost_se"]), (OF, f"{kf}[rate-x4].pooled_power_cost_se"))
    assert not hyp["H2"]["holds"] and not hyp["H3"]["holds"], "the text states both clauses as failed at three times"
    put("fifteenHeld", "H1 and H2 held" if hyp["H1"]["holds"] and hyp["H2"]["holds"] else "see table")
    pdg = {s["id"]: s for s in seq["pd_grades"]["scenarios"]}
    put("fifteenPdNullProduct", pct(pdg["pd-x1"]["e_product"]["ever"]))
    put("fifteenPdNullAverage", pct(pdg["pd-x1"]["e_average"]["ever"]))
    put("fifteenPdNullChi", pct(pdg["pd-x1"]["chi2_every_year"]["ever"]))
    put("fifteenPdTenProduct", pct(pdg["pd-x1.1"]["e_product"]["ever"]))
    put("fifteenPdTenAverage", pct(pdg["pd-x1.1"]["e_average"]["ever"]))
    put("fifteenPdFiveAverage", pct(pdg["pd-x1.05"]["e_average"]["ever"]))
    put("fifteenPdFiveChi", pct(pdg["pd-x1.05"]["chi2_one_shot_power"]))
    put("fifteenPdYears", seq["pd_grades"]["years"])
    c11e = c11_eprocess(A)
    A["c11e"] = c11e
    use("data/derived/C11/{equity-2007-09,fx-2008,equity-2020,rates-2022,calm-2004-06,mixed-2023}.json",
        "models[].by_level[].exceedance_days, read through var_hit_eprocess of riskvalidation 1.1.0 and the traffic light rule")
    byw = {r["window"]: r for r in c11e}
    put("fifteenCeSevenFlag", byw["equity-2007-09"]["eproc"])
    put("fifteenCeSevenLight", byw["equity-2007-09"]["light"])
    put("fifteenCeSevenModels", byw["equity-2007-09"]["models"])
    put("fifteenCeSevenDay", f"{med(byw['equity-2007-09']['e_days']):.0f}")
    put("fifteenCeFxFlag", byw["fx-2008"]["eproc"])
    put("fifteenCeFxLight", byw["fx-2008"]["light"])
    put("fifteenCeFxDay", f"{med(byw['fx-2008']['e_days']):.0f}")
    put("fifteenCeFxLightDay", f"{med(byw['fx-2008']['l_days']):.0f}")
    use("data/derived/C03/{fy2006-07,fy2008-10,fy2011-14,fy2015-17,fy2018-20}.json", "sequential.average.rejection_month and max_log_e")
    c03rej = []
    for tag, d in A["c03"].items():
        sq = d["sequential"]
        c03rej.append((tag, sq["average"]["rejection_month"], sq["average"]["max_log_e"]))
    put("fifteenCzeroRejected", sum(1 for _, m, _ in c03rej if m is not None))
    put("fifteenCzeroCohorts", len(c03rej))
    # ---- BS-16
    use("data/derived/C11/equity-2007-09.json", "conformal (method, hypothesis, rows[hs-250, 0.01])")
    cf = A["c11"]["equity-2007-09"]["conformal"]
    hy = cf["hypothesis"]
    put("sixteenGamma", f"{cf['method']['gamma']}")
    put("sixteenBandLow", f"{cf['method']['level_min']}")
    put("sixteenBandHigh", f"{cf['method']['level_max']}")
    put("sixteenCells", hy["n_cells"])
    put("sixteenCellsHold", hy["n_cells_hold"])
    put("sixteenFzTol", pct(hy["run"]["fz0_tolerance"], 0))
    put("sixteenStressDays", hy["run"]["n_stress_days"])
    put("sixteenRuns", hy["run"]["n_runs"])
    extra = sum(c["extra_windows"] for c in hy["cells"])
    put("sixteenExtra", extra)
    worst = max(c["worst_fz0_change"] for c in hy["cells"])
    put("sixteenWorstFz", pct(worst, 1))
    ind = [x["independence_p"] for x in hy["independence_2007_09"]]
    put("sixteenIndMin", f"{min(ind):.3f}")
    put("sixteenIndFails", sum(1 for x in hy["independence_2007_09"] if x["fails"]))
    r_hs = [r for r in cf["rows"] if r["model_id"] == "hs-250" and abs(r["alpha"] - 0.01) < 1e-12][0]
    put("sixteenHsHitUn", f"{r_hs['unwrapped']['hit_rate']:.3f}")
    put("sixteenHsHitWr", f"{r_hs['wrapped']['hit_rate']:.3f}")
    put("sixteenHsFz", pct(r_hs["fz0_change"], 1))
    put("sixteenHsClipped", r_hs["n_clipped"])
    put("sixteenHsKupUn", f"{r_hs['unwrapped']['kupiec_p']:.1e}")
    put("sixteenHsKupWr", f"{r_hs['wrapped']['kupiec_p']:.3f}")
    use("data/derived/C11/equity-2020.json", "conformal.rows[hs-250, 0.01]")
    rows20 = [r for r in A["c11"]["equity-2020"]["conformal"]["rows"] if r["model_id"] == "hs-250" and abs(r["alpha"] - 0.01) < 1e-12][0]
    put("sixteenTwentyHsFz", pct(rows20["fz0_change"], 1))
    put("sixteenTwentyHsPassWr", yn(rows20["wrapped"]["passes_coverage"]))
    # ---- BS-5 and BS-6 (read here from the committed provisions and portfolio documents)
    use("data/derived/C06/rd-2008-12.json", "reconciliation (tolerance, allowance residuals) and non_linearity")
    c06 = D("C06/rd-2008-12.json")
    nl = c06["non_linearity"]
    put("fiveTolerance", "10^{-%d}" % round(-np.log10(c06["reconciliation"]["tolerance"])))
    put("fiveMaxResidual", f"{max(abs(a['residual']) for a in c06['reconciliation']['allowance']):.1e}")
    put("fivePdWeighted", f"{100 * nl['pd_weighted']:.3f}")
    put("fivePdMean", f"{100 * nl['pd_at_mean_z']:.3f}")
    put("fiveEclWeighted", f"{nl['ecl_weighted'] / 1e6:,.1f}")
    put("fiveEclMean", f"{nl['ecl_at_mean_path'] / 1e6:,.1f}")
    put("fiveIndex", f"{100 * nl['index']:.2f}")
    put("fiveRho", f"{nl['parameters']['rho']}")
    use("data/derived/C07/base.json", "regimes[] (total_provision, coverage_rate) and gap_bridge.steps")
    c07 = D("C07/base.json")
    reg = {r["regime"]: r for r in c07["regimes"]}
    put("fiveCmf", f"{reg['cmf-b1']['total_provision'] / 1e9:,.1f}")
    put("fiveIfrs", f"{reg['ifrs9']['total_provision'] / 1e9:,.1f}")
    put("fiveBde", f"{reg['bde-annex9']['total_provision'] / 1e9:,.1f}")
    put("fiveCmfCov", pct(reg["cmf-b1"]["coverage_rate"], 2))
    put("fiveIfrsCov", pct(reg["ifrs9"]["coverage_rate"], 2))
    put("fiveBdeCov", pct(reg["bde-annex9"]["coverage_rate"], 2))
    steps = {x["id"]: x["amount"] for x in c07["gap_bridge"]["steps"]}
    put("fiveBridgeBasis", f"{steps['measurement-basis'] / 1e9:,.1f}")
    put("fiveBridgeLife", f"{steps['lifetime-horizon'] / 1e9:,.1f}")
    put("fiveBridgeForward", f"{steps['forward-looking'] / 1e9:,.1f}")
    put("fiveBridgeDisc", f"{steps['discounting'] / 1e9:,.1f}")
    put("fiveBridgeOverlay", f"{steps['ifrs9-overlays'] / 1e9:,.1f}")
    use("data/derived/C04/sp.json", "definition_gap.d4_over_d2")
    gap = [x for x in A["sp"]["definition_gap"]["d4_over_d2"] if x is not None]
    put("fourGapMin", pct(min(gap), 0))
    put("fourGapMax", pct(max(gap), 0))
    use("data/derived/C10/grid-22.json", "cells[0] (known_rho, series_length_years, n_replications, estimators) and generator.known_pd")
    g22 = D("C10/grid-22.json")
    c0 = g22["cells"][0]
    est = {e["estimator"]: e for e in c0["estimators"]}
    put("sixRhoKnown", c0["known_rho"])
    put("sixYears", c0["series_length_years"])
    put("sixReps", c0["n_replications"])
    put("sixMlBias", f"{est['maximum-likelihood']['bias']:.4f}")
    put("sixMlRmse", f"{est['maximum-likelihood']['rmse']:.4f}")
    put("sixMlCov", pct(est["maximum-likelihood"]["coverage"], 1))
    put("sixMomCov", pct(est["moments"]["coverage"], 1))
    put("sixMomRmse", f"{est['moments']['rmse']:.4f}")
    put("sixPd", g22["generator"]["known_pd"])
    # ---- counts the other sections of the report quote, read from the reconciliation manuscript and the documents
    ppt("twoPrinted", "reconciliation-against-reference-engines", "nPrintedN")
    ppt("twoReproduced", "reconciliation-against-reference-engines", "nPrintedAgree")
    ppt("twoGridCases", "reconciliation-against-reference-engines", "nGridCases")
    im = D("C12/with-im.json")
    ore_dim = np.array(im["ore_reconciliation"]["ore_dim"]["values"], dtype=float)
    eng_dim = np.array(im["initial_margin"]["dim"]["values"], dtype=float)
    put("twoImDimRatio", f"{float(np.mean(ore_dim / eng_dim)):.2f}", ("data/derived/C12/with-im.json", "ore_reconciliation.ore_dim over initial_margin.dim, mean over the dates"))
    c07_ids = [(D(f"C07/{p.name}") or {}).get("scenario_id") for p in sorted((figkit.DERIVED / "C07").glob("*.json")) if p.name != "models-banco-andino.json"]
    put("fiveScenarios", sum(1 for x in c07_ids if x), ("data/derived/C07/*.json", "documents with a scenario_id"))
    src = (figkit.ROOT / "data-pipeline" / "pipeline" / "stages" / "split.py").read_text(encoding="utf-8")
    m = re.search(r"holdout: float = ([0-9.]+), calibration: float = ([0-9.]+),\s+repeats: int = (\d+)", src)
    put("threeHoldout", m.group(1), ("data-pipeline/pipeline/stages/split.py", "stratified_split holdout"))
    put("threeCalibration", m.group(2), ("data-pipeline/pipeline/stages/split.py", "stratified_split calibration"))
    put("threeRepeats", m.group(3), ("data-pipeline/pipeline/stages/split.py", "stratified_split repeats"))
    use(C22, "simulations[0].n_rep and leakage n: the binomial standard error sqrt(.05 .95 / n)")
    put("oneSeNull", f"{100 * (0.05 * 0.95 / int(tests[0]['n_rep'])) ** 0.5:.2f}")
    put("oneHalfWidth", f"{196 * (0.05 * 0.95 / int(tests[0]['n_rep'])) ** 0.5:.1f}")
    put("oneSePower", f"{100 * (0.05 * 0.95 / int(lk[('disc.auc_vs_initial', 1)]['n'])) ** 0.5:.2f}")
    use("make_proposed.py", "worked example computed from the parameters stated in the text")
    # ---- BS-5: the worked example of the non-linearity (PD 2 %, rho 0.12, three scenarios), computed from its parameters
    from scipy.stats import norm

    z = np.array([1.0, 0.0, -2.0])
    wts = np.array([0.25, 0.5, 0.25])
    pd_ttc, rho_ex = 0.02, 0.12
    pz = norm.cdf((norm.ppf(pd_ttc) - np.sqrt(rho_ex) * z) / np.sqrt(1 - rho_ex))
    put("fiveWeighted", f"{100 * float(wts @ pz):.2f}", ("make_proposed.py", "worked example: PD 2 %, rho 0.12, z = 1, 0, -2, weights 0.25, 0.5, 0.25"))
    put("fiveAverage", f"{100 * float(norm.cdf((norm.ppf(pd_ttc) - np.sqrt(rho_ex) * float(wts @ z)) / np.sqrt(1 - rho_ex))):.2f}",
        ("make_proposed.py", "worked example at the weighted mean factor"))
    put("fiveExPd", f"{100 * pd_ttc:g}")
    put("fiveExRho", f"{rho_ex}")
    # the capital of eq:bs4-irb (LGD = 1, confidence 0.999) as a function of the default probability: where it peaks
    grid = np.arange(1, 10000) / 10000.0
    peaks = {}
    for r_ in (0.03, 0.24):
        kk = norm.cdf((norm.ppf(grid) + np.sqrt(r_) * norm.ppf(0.999)) / np.sqrt(1 - r_)) - grid
        peaks[r_] = float(grid[int(np.argmax(kk))])
    put("fourIrbPeakLow", f"{peaks[0.24]:.2f}", ("make_proposed.py", "argmax over PD in (0, 1), step 0.0001, of K(PD) of eq:bs4-irb with LGD = 1 and R = 0.24"))
    put("fourIrbPeakHigh", f"{peaks[0.03]:.2f}", ("make_proposed.py", "argmax over PD in (0, 1), step 0.0001, of K(PD) of eq:bs4-irb with LGD = 1 and R = 0.03"))
    put("fourIrbRhoLow", "0.03", ("make_proposed.py", "the lower asset correlation of the range stated in the text"))
    put("fourIrbRhoHigh", "0.24", ("make_proposed.py", "the upper asset correlation of the range stated in the text"))
    # ---- BS-6: the coverage of the maximum-likelihood estimator over the 24 committed cells
    use("data/derived/C10/{grid-22,grid-40}.json", "cells[].n_replications: the binomial band 0.95 +- 1.96 sqrt(.95 .05 / n)")
    cov, reps24 = [], []
    for g in ("C10/grid-22.json", "C10/grid-40.json"):
        for c in D(g)["cells"]:
            e = {x["estimator"]: x for x in c["estimators"]}["maximum-likelihood"]
            cov.append(e["coverage"])
            reps24.append(c["n_replications"])
    half = [1.96 * np.sqrt(0.95 * 0.05 / n) for n in reps24]
    inside = [c for c, h in zip(cov, half) if abs(c - 0.95) <= h]
    put("sixCells", len(cov), ("data/derived/C10/grid-22.json and grid-40.json", "cells"))
    put("sixCovOutside", len(cov) - len(inside), ("data/derived/C10/grid-22.json and grid-40.json", "cells[].estimators.coverage against 0.95 +- 1.96 sqrt(.95 .05 / n)"))
    put("sixCovInMin", pct(min(inside), 1), ("data/derived/C10", "coverage of the cells inside the band"))
    put("sixCovInMax", pct(max(inside), 1), ("data/derived/C10", "coverage of the cells inside the band"))
    put("sixBandLow", pct(0.95 - half[0], 1))
    put("sixBandHigh", pct(0.95 + half[0], 1))

    # ---- the sixteen method manuscripts: the outcome of each, read from its committed number file
    SPEC = {
        "One": ("size-and-power-of-validation-tests", {
            "Tests": "nTests", "Hold": "nHold", "NotHold": "nNotHold", "Reps": "nRepsPooled", "JeffExact": "jeffExactOne",
            "Norm": "pooledNorm", "NormLo": "pooledNormLo", "NormHi": "pooledNormHi", "Res": "detIntFiveFour", "HoldCell": "nHoldCellDef",
            "BinRho": "binRhoOneZeroExact", "Psi": "psiHundred", "PowerTests": "nPowerTests", "Reach": "nReach", "NullReps": "nNullReps"}),
        "Two": ("reconciliation-against-reference-engines", {
            "PrintedAgree": "nPrintedAgree", "PrintedN": "nPrintedN", "WithinTwo": "nAgreeTwoUnits", "Beyond": "nBinBeyond",
            "MissTested": "nMissTested", "MissTotal": "nMissTotal", "GridJeff": "nGridJeffMax", "GridCases": "nGridCases",
            "ClosedWithin": "nClosedWithin", "ClosedCases": "nClosedCases", "Hw": "nWWAtwoUnits", "Single": "nSingleEquivalence",
            "Netting": "nNettingEquivalence", "CsaTenMax": "nCsaTenMaxZ", "CsaTwentyMax": "nCsaTwentyMaxZ", "ImMax": "nImMaxZ",
            "ReplFail": "nReplCsaFail", "ReplN": "nReplCsaN", "Overstate": "nOverstateLast", "SizeProd": "nSizeProdNetting",
            "SizeProdLo": "nSizeProdNettingLo", "SizeProdHi": "nSizeProdNettingHi", "PowerProd": "nPowerProdSigmaTwo",
            "PowerProdLo": "nPowerProdSigmaTwoLo", "PowerProdHi": "nPowerProdSigmaTwoHi", "SizeFamily": "nSizePairNetting",
            "SizeRefine": "nSizeRefineNetting", "PowerRefine": "nPowerRefineSigmaTwo", "SizeMaxt": "nSizePairMaxtNetting",
            "PowerMaxt": "nPowerPairMaxtSigmaTwo", "CritReps": "nCritReps"}),
        "Three": ("leakage-safe-validation-protocol", {
            "NoneBias": "syn.w.none.bias", "NoneCi": "syn.w.none.ci", "NoneCov": "syn.w.none.cov", "TwN": "tw.n",
            "WoeBias": "syn.w.woe.bias", "FitBias": "syn.w.fit.bias", "FitCov": "syn.w.fit.cov", "Leaks": "h5.total",
            "Draws": "e2.reps", "AucDev": "e3.s0.5.auc_test", "CsiDev": "e3.s1.0.csi_test", "MaxZ": "e4.maxz",
            "OotGap": "e4.2006-07.sc.aoot_gap", "Held": "h.held", "NotHeld": "h.notheld"}),
        "Four": ("default-definition-withdrawals-thin-grades", {
            "CccDefault": "spLraDtwoCcc", "CccTransition": "spLraDfourCcc", "GapIndex": "spPtRatioCcc", "GapLo": "spRatioCccLo",
            "GapHi": "spRatioCccHi", "RwBefore": "spRwDtwo", "RwAfter": "spRwDfour", "Removed": "removedBkNine",
            "RemovedSe": "removedBkNinese", "Followed": "followedBkNine", "FollowedSe": "followedBkNinese", "Duration": "durBkNine",
            "DurationSe": "durBkNinese", "Th": "testthkNinefive", "ThLo": "testthkNinefivelo", "ThHi": "testthkNinefivehi",
            "Mr": "testmrkNinefive", "MrLo": "testmrkNinefivelo", "MrHi": "testmrkNinefivehi", "MrNineteen": "testmrkNineteenfive",
            "MrNineteenLo": "testmrkNineteenfivelo", "MrNineteenHi": "testmrkNineteenfivehi", "Wald": "waldAaaFifty"}),
        "Five": ("provisions-reconciliation-identities", {
            "AboveFullK": "eoneAboveFullK", "AboveFullN": "eoneAboveFullN", "AboveStageK": "eoneAboveStageK",
            "AbsCommittedK": "etwoAbsCommittedK", "ConvexN": "efourConvexN", "MixedNeg": "efourMixedNeg", "MixedN": "efourMixedN",
            "AdhocMed": "efourAdhocMed", "BaseMean": "efiveBaseMean", "BaseLo": "efiveBaseLo", "BaseHi": "efiveBaseHi",
            "Seeds": "efiveSeeds", "HypTotal": "hypTotal", "HypRefuted": "hypRefuted", "RoundMillion": "etwoRoundMillionPct"}),
        "Six": ("engines-and-test-catalogues", {
            "Tests": "testsTotal", "Absent": "ecbAbsent", "Sections": "ecbSections", "EcbMax": "ecbAllMax", "EcbInputs": "ecbInputs",
            "Disagree": "disagreeFive", "Cells": "cCells", "McReps": "mcReps", "McScen": "mcScen", "RegenRel": "regenRel",
            "QlMax": "irrQlMax", "Legs": "irrLegs", "MlBelow": "gridMlBelow", "MlCells": "gridMlCells", "MlFail": "gridMlFail",
            "Mutants": "ablMutants", "Any": "ablAny", "Real": "ablReal", "Only": "ablOnly", "Pypi": "pypiFound", "Dist": "distScanned"}),
        "Seven": ("uf-as-its-own-currency-in-irrbb", {
            "ValDate": "valDate", "RatioLng": "rmRatioLng", "RatioSht": "rmRatioSht", "RatioOff": "rmRatioOff", "RatioLo": "rmLoLng",
            "RatioHi": "rmHiOff", "EveLng": "mainEveShortLng", "EveLngCi": "mainEveShortLngCi", "EveSht": "mainEveShortSht",
            "EveShtCi": "mainEveShortShtCi", "EveOff": "mainEveShortOff", "EveOffCi": "mainEveShortOffCi",
            "ShareLo": "mainChargeShareLo", "ShareHi": "mainChargeShareHi", "FloorRaise": "floorsRaise", "FloorTotal": "floorsTotalNii",
            "SweepLo": "sweepMajLo", "SweepHi": "sweepMajHi", "SweepFirst": "sweepFirstDiff", "HFour": "hFourLo"}),
        "Eight": ("behavioural-assumption-test-at-a-limit-breach", {
            "StatedAlt": "statedAltEngine", "StatedNull": "statedNullEngine", "Fisher": "statedAltFisher", "Mw": "statedAltMw",
            "Welch": "statedAltWelch", "FitNull": "fitNullEngine", "FitAuc": "fitAucCEngine", "FitAucLo": "fitAucLoCEngine",
            "FitAucHi": "fitAucHiCEngine", "TolNull": "fitNullTol", "TolAuc": "fitAucCTol", "TolTwo": "fitAddCTol", "TolFour": "fitAddDTol",
            "BreakTwo": "fitAddCShiftB", "BreakFour": "fitAddDShiftB", "BreakNull": "fitNullShiftB", "MisTol": "fitMisCTol",
            "MisTolLo": "fitMisCTolLo", "MisTolHi": "fitMisCTolHi", "MisBreak": "fitMisCShiftB", "WTop": "wTopAuc", "WReal": "wRealTopAuc",
            "Held": "hypothesesHeld", "Refuted": "hypothesesRefuted"}),
        "Nine": ("dependence-band-with-every-aggregate", {
            "Lower": "bdLower", "Worst": "bdWorst", "Headline": "bdHeadline", "WidthSe": "bdWidthOverSe", "Gauss": "bdGauss",
            "GaussSe": "bdGaussSe", "Width": "bdAblFullWidth", "Interior": "bdCovInterior", "InteriorStress": "bdCovInteriorStress",
            "GaussWithin": "bdGaussWithin"}),
        "Ten": ("measured-corrections-of-validation-tests", {
            "BinomEqual": "CovSinBinB", "BinomEqualSe": "CovSeBinB", "BetaBin": "CovSinBBB", "BetaBinMax": "CovBBMaxExact",
            "PowGap": "ExPowGapMax", "FixedFive": "ShRateFixedFiveCZ", "Perm": "ShRatePermCZ", "PermPower": "ShRatePermCT",
            "FixedPower": "ShRateFixedFiveCT", "CutTwenty": "SiRateCutTwentySmallZ", "CutTen": "SiRateCutTenSmallZ",
            "HypTotal": "HypTotal", "HypRefuted": "HypRefuted", "HypPartial": "HypPartial", "CutTenLarge": "SiRateCutTenLargeZ",
            "PowTenGapTwo": "SiRateCutTenSmallB", "PowTwentyGapTwo": "SiRateCutTwentySmallB", "FixedFiveSe": "ShSeFixedFiveCZ",
            "PermSe": "ShSePermCZ", "CutTwentySe": "SiSeCutTwentySmallZ", "CutTenSe": "SiSeCutTenSmallZ", "PermPowerSe": "ShSePermCT",
            "FixedPowerSe": "ShSeFixedFiveCT"}),
        "Eleven": ("reverse-liquidity-stress-with-a-refusal-rule", {
            "Inst": "kInst", "ScanFalse": "kGFalse", "ScanErr": "kGErrPc", "Adv": "mAdv", "Ext": "mExt", "SvbModel": "svbModel",
            "SvbRatio": "svbRatio", "SvbMult": "mSvb", "JointDev": "jointDevAdv", "LowSlow": "lowSlowM"}),
        "Twelve": ("instability-of-operational-risk-capital", {
            "Per": "nPer", "Cells": "nCells", "IqrMin": "spIqrMin", "MinLo": "spMinLo", "MinHi": "spMinHi", "IqrMax": "spIqrMax",
            "MaxLo": "spMaxLo", "MaxHi": "spMaxHi", "Red": "redTotal", "InfLo": "infLo", "InfHi": "infHi", "FinLo": "finLo",
            "FinHi": "finHi", "ThErr": "thSdMaxErr", "YrsMin": "yrsMin", "YrsMax": "yrsMax"}),
        "Fourteen": ("anchored-pd-under-informative-withdrawals", {
            "TruthB": "truthB", "Reps": "reps", "CovMin": "h1.min", "PoolIndustry": "cov.pool.i9.industry",
            "PoolIndustrySe": "se.pool.i9.industry", "WidthAnchored": "w.fy.i9.anchored", "WidthFollowed": "w.fy.i9.followed",
            "WidthManskiLo": "wr.fy.i9", "WidthManskiHi": "wr.x10.i9", "CccK": "real.sp.CCC-C.k", "ShareB": "stab.i9.cdobs.B.share",
            "ShareCcc": "stab.i9.cdobs.CCC-C.share"}),
        "Fifteen": ("e-process-sequential-monitors", {
            "KupTrail": "nNullSizeKupTrail", "ENull": "nNullSizeE", "ENullLo": "nNullSizeELo", "ENullHi": "nNullSizeEHi",
            "FourMed": "nSeedsFourMed", "ThreeMed": "nSeedsThreeMed", "ThreeMedLo": "nSeedsThreeMedLo", "ThreeMedHi": "nSeedsThreeMedHi",
            "ThreeCost": "nSeedsThreeCost", "ThreeCostSe": "nSeedsThreeCostSe", "UpThreeMed": "nSeedsUpThreeMed",
            "UpThreeCost": "nSeedsUpThreeCost", "UpThreeCostSe": "nSeedsUpThreeCostSe", "RhoAvg": "nRhoZeroThreeAvg",
            "VasTrue": "nPdcZeroThreeVasTrueEvery", "MatchedSize": "nPdcMatchedSize", "ChiMatched": "nPdcOneZeroFiveChiMatched",
            "PdAvg": "nPdOneZeroFiveAvg", "ChiSim": "nPdcOneZeroFiveChiSim"}),
        "Sixteen": ("adaptive-conformal-recalibration-of-var", {
            "DevUnw": "tenHitDevUnw", "DevAci": "tenHitDevAci", "WorstFz": "tenWorstFz", "PassAci": "tenPassAci", "Runs": "tenRuns",
            "PassUnw": "tenPassUnw", "DispAci": "dispBOneOneAciPass", "DispUnw": "dispBOneOneUnwPass", "WrapCal": "dispCWrapCal",
            "UnwExact": "dispCUnwExact", "HoneGain": "dispCHoneGainCal", "Cells": "hypCells", "ScaleRatio": "thCCmaxOne",
            "RollOver": "cmpRollTenFzOver"}),
    }
    missing = []
    for num, (slug, mp) in SPEC.items():
        for name, key in mp.items():
            try:
                ppt(f"pp{num}{name}", slug, key)
            except KeyError:
                missing.append((slug, key))
    assert not missing, missing
    put("ppTwelvePer", f"{int(pv('instability-of-operational-risk-capital', 'nPer')):,}", (pfile("instability-of-operational-risk-capital", "nPer"), "nPer"))
    # the e-process paper writes its macros with a leading n
    # ---- the scale-and-level complement: its results file
    pla = results_json("scale-and-level-complement-to-the-pla-test")
    src_pla = "manuscripts/scale-and-level-complement-to-the-pla-test/experiments/results.json"
    mn = pla["main"]
    put("ppThirteenUnion", pct(mn["stale-volatility"]["union"]["rate"], 1), (src_pla, "main.stale-volatility.union.rate"))
    put("ppThirteenUnionLo", pct(mn["stale-volatility"]["union"]["lo"], 1), (src_pla, "main.stale-volatility.union.lo"))
    put("ppThirteenUnionHi", pct(mn["stale-volatility"]["union"]["hi"], 1), (src_pla, "main.stale-volatility.union.hi"))
    put("ppThirteenHeld", pct(mn["none"]["union"]["rate"], 1), (src_pla, "main.none.union.rate"))
    put("ppThirteenHeldLo", pct(mn["none"]["union"]["lo"], 1), (src_pla, "main.none.union.lo"))
    put("ppThirteenHeldHi", pct(mn["none"]["union"]["hi"], 1), (src_pla, "main.none.union.hi"))
    put("ppThirteenZone", pct(mn["stale-volatility"]["pla"]["rate"], 1), (src_pla, "main.stale-volatility.pla.rate"))
    put("ppThirteenWrong", pct(mn["wrong-correlation"]["roll20"]["rate"], 1), (src_pla, "main.wrong-correlation.roll20.rate"))
    put("ppThirteenMisalign", pct(mn["time-misalignment"]["roll20"]["rate"], 1), (src_pla, "main.time-misalignment.roll20.rate"))
    put("ppThirteenMisalignAbs", pct(mn["time-misalignment"]["abs_spearman"]["rate"], 1), (src_pla, "main.time-misalignment.abs_spearman.rate"))
    put("ppThirteenMissingWald", pct(mn["missing-basis"]["wald_hc3"]["rate"], 1), (src_pla, "main.missing-basis.wald_hc3.rate"))
    put("ppThirteenMissingKs", pct(mn["missing-basis"]["ks_alone"]["rate"], 1), (src_pla, "main.missing-basis.ks_alone.rate"))
    put("ppThirteenPersist", pct(pla["altnull"]["phi0995"]["union"]["rate"], 1), (src_pla, "altnull.phi0995.union.rate"))
    put("ppThirteenDisp", pct(pla["altnull"]["sd050"]["union"]["rate"], 1), (src_pla, "altnull.sd050.union.rate"))
    put("ppThirteenNoise", pct(pla["altnull"]["res030"]["union"]["rate"], 1), (src_pla, "altnull.res030.union.rate"))
    put("ppThirteenNull", f"{pla['n_null']:,}", (src_pla, "n_null"))
    # ---- BS-10: the rank of the conformal set computed on the float product and on the exact decimal
    import math
    from decimal import Decimal, ROUND_CEILING

    pairs = []
    for a in range(1, 100):
        al, ald = a / 100, Decimal(a) / Decimal(100)
        for n in range(1, 3000):
            rf = math.ceil((n + 1) * (1 - al))
            rx = int((Decimal(n + 1) * (1 - ald)).to_integral_value(rounding=ROUND_CEILING))
            if rf != rx:
                pairs.append((a, n, rf, rx))
    first = pairs[0]
    put("tenRankPairs", f"{len(pairs):,}", ("make_proposed.py", "exhaustive count over the levels 0.01 to 0.99 and the sizes 1 to 2,999"))
    put("tenRankFirstN", first[1])
    put("tenRankFirstAlpha", f"{first[0] / 100:.2f}")
    put("tenRankFloat", first[2])
    put("tenRankExact", first[3])
    byn = min(pairs, key=lambda x: (x[1], x[0]))
    put("tenRankSmallN", byn[1])
    put("tenRankSmallAlpha", f"{byn[0] / 100:.2f}")
    # ---- BS-12: the benchmark of the aggregation engines
    bench = [tt for tt in figkit.doc("C17/xi-0-96.json")["tests"] if tt["test_id"] == "oprisk.benchmark_reproduction"][0]["h0"]
    mq = re.search(r"quantile of (\d+) to (\d+) by Panjer", bench)
    put("twelveBenchQLow", f"{int(mq.group(1)):,}", ("data/derived/C17/xi-0-96.json", "tests oprisk.benchmark_reproduction h0"))
    put("twelveBenchQHigh", f"{int(mq.group(2)):,}", ("data/derived/C17/xi-0-96.json", "tests oprisk.benchmark_reproduction h0"))
    mm = re.search(r"E\[Z\] = ([0-9.]+)", bench)
    put("twelveBenchMean", mm.group(1), ("data/derived/C17/xi-0-96.json", "tests oprisk.benchmark_reproduction h0"))
    # ---- the titles of the sixteen manuscripts
    NUMW = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen",
            "Fifteen", "Sixteen"]
    for nm in NUMW:
        slug = SPEC[nm][0] if nm in SPEC else {"Thirteen": "scale-and-level-complement-to-the-pla-test"}[nm]
        put(f"paperTitle{nm}", paper_title(slug), (f"manuscripts/{slug}/main.tex", "title"))
    # ---- the sources of the macros, for the reader who wants to check one
    A["sources"] = dict(SOURCES)
    A["N"] = N
    return A


# --------------------------------------------------------------------------------------------------------------- write
def paper_title(slug: str) -> str:
    """The title of a method manuscript, read from its main.tex with the braces balanced."""
    txt = (MS / slug / "main.tex").read_text(encoding="utf-8")
    i = txt.index("\\title{") + len("\\title{")
    depth, j = 1, i
    while depth:
        depth += {"{": 1, "}": -1}.get(txt[j], 0)
        j += 1
    return " ".join(txt[i:j - 1].split())


def write_sources(N: dict) -> None:
    lines = ["macro,source,key"]
    for k in sorted(N):
        s, key = SOURCES.get(k, ("data/derived", "computed by make_proposed.py"))
        lines.append(f"px{k[0].upper() + k[1:]},\"{s}\",\"{key}\"")
    (OUT / "proposed-numbers-sources.csv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_numbers(N: dict) -> None:
    lines = ["% Generated by tables/make_proposed.py from data/derived; do not edit.", ""]
    for k, v in sorted(N.items()):
        lines.append(f"\\newcommand{{\\px{k[0].upper() + k[1:]}}}{{{v}}}")
    (OUT / "proposed-numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_tables(A: dict) -> None:
    # --- summary of the twelve measurements
    N = A["N"]
    T = OUT
    figkit.table(T / "proposed-summary.tex", ["Method", "Case", "Quantity measured", "Value"], [
        ["Size and power of the tests", "C22", "tests of the null family within the size bound at 5%",
         f"{len(A['size_tests']) - int(N['oneOver'])} of {N['oneTests']}"],
        ["Size and power of the tests", "C22", "tests of the null family within the size bound at 5% and at 1%",
         f"{N['oneWithinBoth']} of {N['oneTests']}"],
        ["Reconciliation with ORE", "C12", "single swap, dates within two combined standard errors",
         f"{int(N['twoSingleDates']) - int(N['twoSingleOut'])} of {N['twoSingleDates']}"],
        ["Reconciliation with ORE", "C12", "CSA with 10 days, dates within two combined standard errors",
         f"{int(N['twoCsaTenDates']) - int(N['twoCsaTenOut'])} of {N['twoCsaTenDates']}"],
        ["Informative withdrawals", "C04", "relative error of the B probability of default, withdrawals removed, informativeness 9 (%)",
         N["fourRemovedB"]],
        ["Thin grades", "C04", "coverage of the Wald interval for the first grade at 50 obligors (%)", N["fourWaldAaa"]],
        ["UF as its own currency", "C15", "indexation charge over the change in net interest income, short-UF variant (%)",
         N["sevenShare"]],
        ["Dependence band", "C18", "worst-case capital over the simple sum", N["nineWorstRatio"]],
        ["Reverse liquidity stress", "C16", "run-off multiplier at the 30-day target, adverse base", N["elevenAdverse"]],
        ["Reverse liquidity stress", "C16", "fast-run base", N["elevenFast"]],
        ["Operational-risk instability", "C17", "interquartile range over the truth, splice rung, range over the cells",
         f"{N['twelveIqrMin']} to {N['twelveIqrMax']}"],
    ], caption="Headline quantities of twelve of the sixteen contributions, read from the stored documents of the case named in the second "
               "column, each as a count or a point value without an interval; the Monte Carlo errors are printed beside each value in the "
               "text of the method, and the four methods of Sections~\\ref{sec:bs13} to~\\ref{sec:bs16} report theirs in the tables on the complement to the attribution "
               "test, the anchored probability of default, the sequential monitors and the conformal recalibration.",
        label="tab:proposed-summary", align="lllr")

    # --- the sixteen methods and their manuscripts
    SLUGS = ["size-and-power-of-validation-tests", "reconciliation-against-reference-engines", "leakage-safe-validation-protocol",
             "default-definition-withdrawals-thin-grades", "provisions-reconciliation-identities", "engines-and-test-catalogues",
             "uf-as-its-own-currency-in-irrbb", "behavioural-assumption-test-at-a-limit-breach", "dependence-band-with-every-aggregate",
             "measured-corrections-of-validation-tests", "reverse-liquidity-stress-with-a-refusal-rule",
             "instability-of-operational-risk-capital", "scale-and-level-complement-to-the-pla-test",
             "anchored-pd-under-informative-withdrawals", "e-process-sequential-monitors", "adaptive-conformal-recalibration-of-var"]
    CASES = ["C22", "C12", "C01, C03", "C04", "C06, C07", "C10, C14", "C15", "C14", "C18", "C20, C21", "C16", "C17", "C13", "C04", "C22, C11, C03", "C11"]
    rows = []
    for i, (slug, case) in enumerate(zip(SLUGS, CASES), start=1):
        rows.append([f"\\ref{{sec:bs{i}}}", case, "\\raggedright\\arraybackslash " + paper_title(slug)])
    figkit.table(T / "proposed-papers.tex", ["Section", "Case", "Manuscript of the method"], rows,
                 caption="The sixteen contributions, the case that carries each, and the title of the manuscript that reports it "
                         "on its own; each subsection ends with what that manuscript found.", label="tab:proposed-papers",
                 align="llp{0.78\\textwidth}")

    # --- reconciliation with ORE
    ore_rows = []
    nm = {"single-swap": "Single swap", "netting-set": "Four-swap netting set", "csa-mpor-10d": "CSA, 10 days",
          "csa-mpor-20d": "CSA, 20 days", "with-im": "CSA with initial margin"}
    for v, r in A["ore"].items():
        ag = r["agreement"]
        out = sum(1 for x in ag if not x["within_two_se"])
        ore_rows.append([nm[v], f"{len(ag) - out} of {len(ag)}", f"{max(abs(x['difference']) / x['combined_se'] for x in ag):.1f}",
                         f"{abs(r['eepe_agreement']['difference']) / r['eepe_agreement']['combined_se']:.2f}",
                         f"{abs(r['cva_agreement']['difference']) / r['cva_agreement']['combined_se']:.2f}"])
    figkit.table(T / "proposed-ore.tex", ["Variant", "Dates within 2 SE", "Largest EE gap (SE)", "EEPE gap (SE)", "CVA gap (SE)"], ore_rows,
                 caption="Agreement of the engine's exposure profile with the Open Source Risk Engine on case C12: the number of the "
                         "33 report dates at which the expected exposure lies within two combined Monte Carlo standard errors, and the "
                         "largest gap of the profile, of the effective expected positive exposure and of the credit valuation adjustment, "
                         "each in combined standard errors.", label="tab:proposed-ore", align="lrrrr")

    # --- BS-13
    rows = []
    for v in VARIANTS:
        d = A["c13"][v]
        ps = d["pla_complement"]["flags"]["per_statistic"]
        fam = d["pla_complement"]["flags"]["family"]["any"]
        rows.append([VLABEL[v], pct(d["detection"]["share_amber_or_red"]), pct(ps["wald"]["rate"]), pct(ps["spearman_abs"]["rate"]),
                     pct(ps["spearman_roll"]["rate"]), wilson_str(fam)])
    figkit.table(T / "proposed-pla.tex", ["Variant", "Regulatory zone", "Wald", "Absolute Spearman", "Rolling Spearman", "Union at 1\\% (95\\% interval)"],
                 rows, caption="Share of the 1,000 replications of each C13 variant flagged, in percent: by the regulatory attribution test (amber or "
                               "red), by each of the three statistics of the complement at 1\\% per statistic, and by their union at a family size of "
                               "1\\% with its Wilson interval.", label="tab:proposed-pla", align="lrrrrr")
    lag = {x["lag_days"]: x for x in A["c13"]["stale-volatility"]["pla_complement"]["lag_ladder"]}
    rows = [[f"{L}", pct(lag[L]["pla_amber_or_red"]["rate"]), pct(lag[L]["per_statistic"]["wald"]["rate"]),
             pct(lag[L]["per_statistic"]["spearman_abs"]["rate"]), pct(lag[L]["per_statistic"]["spearman_roll"]["rate"]),
             pct(lag[L]["family_any"]["rate"])] for L in (5, 10, 20, 40)]
    figkit.table(T / "proposed-lag.tex", ["Lag (days)", "Regulatory zone", "Wald", "Absolute Spearman", "Rolling Spearman", "Union (family 1\\%)"], rows,
                 caption="Share of 1,000 replications flagged, in percent, when the risk model scales the day's shocks with a volatility that is "
                         "5, 10, 20 and 40 days old: the regulatory attribution test and the statistics of the complement.",
                 label="tab:proposed-lag", align="rrrrrr")

    # --- BS-14
    bv = A["wd"]["bounds_verdict"]["rows"]
    cov = {(r["design"], r["informative"], r["treatment"]): r for r in bv}
    dl = {"first_year": "first-year cohort", "pooled": "five cohorts pooled", "first_year_x10": "first year, ten times the cohort"}
    rows = []
    for dsg in ["first_year", "pooled", "first_year_x10"]:
        for k in (1.0, 3.0, 9.0):
            cells = []
            for tr in ["industry", "unfollowed", "followed", "anchored"]:
                r = cov.get((dsg, k, tr))
                cells.append("--" if r is None else f"${pct(r['value'])} \\pm {100 * 1.96 * r['mcse']:.1f}$")
            if all(c == "--" for c in cells):
                continue
            rows.append([dl[dsg], f"{k:.0f}"] + cells)
    figkit.table(T / "proposed-anchored.tex", ["Design", "Informativeness $\\iota$", "Industry", "Unfollowed", "Followed", "Anchored"], rows,
                 caption="Coverage in percent, with a 95\\% Monte Carlo half-width, of the true one-year probability of default of the B grade by the "
                         "interval of each treatment of rating withdrawals over 200 repetitions of the rating-path generator; a dash marks a "
                         "design and informativeness that the evaluation did not run.", label="tab:proposed-anchored", align="llrrrr")
    sp = A["sp"]["withdrawal_bounds"]["grades"]
    rows = []
    for g in sp:
        p = g["pooled"]
        if p.get("k") is None:
            continue
        rows.append([g["grade"], f"{p['k']:.1f}", f"{p['k_low']:.1f} to {p['k_high']:.1f}", g["stability"]["usable_cohorts"],
                     g["stability"]["cohorts_containing_pooled_k"], yn(g["stability"]["stable"])])
    figkit.table(T / "proposed-realk.tex", ["Grade", "Pooled $k$", "Band", "Usable cohorts", "Cohorts containing it", "Stable"], rows,
                 caption="The anchored odds multiplier of withdrawal in the year of default, by grade, from the 26 annual cohorts of the S\\&P "
                         "transition and default pages of case C04: the pooled value, its band, and the number of cohorts whose band contains "
                         "the pooled value.", label="tab:proposed-realk", align="lrrrrr")

    # --- BS-15
    seq = A["seq"]
    rows = []
    lbl = {"null": "right model", "rate-x2": "rate 2 times", "rate-x3": "rate 3 times", "rate-x4": "rate 4 times",
           "cluster-0.1": "clustering 0.1", "cluster-0.2": "clustering 0.2", "cluster-0.4": "clustering 0.4"}

    def md(x):
        return "--" if x is None else f"{x:.0f}"
    for s in seq["hits"]["scenarios"]:
        rows.append([lbl[s["id"]], pct(s["e_rate"]["ever"]), md(s["e_rate"]["median_day"]), pct(s["kupiec_trailing"]["ever"]),
                     pct(s["kupiec_cumulative"]["ever"]), md(s["kupiec_cumulative"]["median_day"]), pct(s["traffic_light"]["ever"]),
                     md(s["traffic_light"]["median_day"])])
    figkit.table(T / "proposed-sequential.tex", ["Scenario", "E-process ever", "day", "Kupiec trailing ever", "Kupiec cumulative ever", "day", "Light ever", "day"],
                 rows, caption="Share of 2,000 simulated 1,000-day series, on one seed (the seed of the case), in which each reading of the 99\\% VaR back-test rejects at some day "
                               "(in percent) and the median first day of rejection (a dash when fewer than half reject), for the e-process, "
                               "the Kupiec test on the trailing 250 days and on all days so far, and the traffic light; the pooled replication over " + str(seq["replication"]["seeds"]) + " seeds that decides the delay and power clauses is given in the text.",
                 label="tab:proposed-sequential", align="lrrrrrrr", wide=True)
    rows = []
    for s in seq["pd_grades"]["scenarios"]:
        rows.append([f"{s['factor'] if 'factor' in s else s['id']}", pct(s["e_product"]["ever"]), pct(s["e_average"]["ever"]),
                     pct(s["chi2_one_shot_power"]), pct(s["chi2_every_year"]["ever"])])
    figkit.table(T / "proposed-pdgrades.tex", ["PD factor", "E-process, product", "E-process, average", "Chi-square at year 10", "Chi-square every year"], rows,
                 caption="Share of 2,000 simulated ten-year histories of five rating grades in which each monitor rejects the predicted default "
                         "probabilities, in percent, when every grade's probability is multiplied by the factor of the first column.",
                 label="tab:proposed-pdgrades", align="rrrrr")
    rows = []
    for r in A["c11e"]:
        rows.append([r["window"], r["days"], r["models"], r["light"], r["eproc"], md(med(r["l_days"])), md(med(r["e_days"]))])
    figkit.table(T / "proposed-c11e.tex", ["Window", "Days", "Models", "Light flags", "E-process flags", "Light median day", "E-process median day"], rows,
                 caption="The e-process of the engine applied to the committed exceedance days of every model of the C11 ladder at the 99\\% level, "
                         "against the traffic light: the number of models each flags and the median first day on which each flags a model.",
                 label="tab:proposed-c11e", align="lrrrrrr")

    # --- BS-16
    rows = []
    for w in STRESS:
        for r in A["c11"][w]["conformal"]["rows"]:
            u, wr = r["unwrapped"], r["wrapped"]
            rows.append([w, MODEL_LABEL[r["model_id"]], f"{100 * r['alpha']:g}%", f"{u['hit_rate']:.3f}", f"{wr['hit_rate']:.3f}",
                         yn(u["passes_coverage"]), yn(wr["passes_coverage"]), f"{100 * r['fz0_change']:+.1f}"])
    figkit.table(T / "proposed-conformal.tex", ["Window", "Model", "Level", "Hit rate", "Wrapped", "Pass", "Wrapped", "FZ0 change (\\%)"], rows,
                 caption="Adaptive conformal recalibration of three models on the three stress windows of C11: the hit rate of each model without "
                         "and with the wrapper, whether Kupiec and conditional coverage both pass at 5\\%, and the relative change of the mean FZ0 "
                         "loss (negative is an improvement).", label="tab:proposed-conformal", align="llrrrllr")
    rows = []
    for c in A["c11"]["equity-2007-09"]["conformal"]["hypothesis"]["cells"]:
        rows.append([MODEL_LABEL[c["model_id"]], f"{100 * c['alpha']:g}%", c["windows_passed_unwrapped"], c["windows_passed_wrapped"],
                     c["extra_windows"], f"{100 * c['worst_fz0_change']:+.1f}", yn(c["holds"])])
    figkit.table(T / "proposed-conformal-cells.tex", ["Model", "Level", "Windows passed", "Windows passed wrapped", "Extra windows", "Worst FZ0 change (\\%)", "Holds"],
                 rows, caption="The six cells of the evaluation of the conformal wrapper: for each model and tail level, the stress windows passed "
                               "without and with the wrapper, the gain, the worst change of the mean FZ0 loss in any stress window, and whether the "
                               "criterion holds in the cell.", label="tab:proposed-conformal-cells", align="lrrrrrl")


def fit_width(path: pathlib.Path) -> None:
    """Scale a table down to the text width when it is wider (a no-op for a table that fits)."""
    s = path.read_text(encoding="utf-8")
    if "resizebox" in s:
        return
    s = s.replace("\\begin{tabular}", "\\fitwidth{%\n\\begin{tabular}", 1)
    s = s.replace("\\end{tabular}", "\\end{tabular}}", 1)
    path.write_text(s, encoding="utf-8", newline="\n")


def main() -> None:
    A = build()
    write_numbers(A["N"])
    write_sources(A["N"])
    write_tables(A)
    for p in OUT.glob("proposed-*.tex"):
        if p.name != "proposed-numbers.tex":
            fit_width(p)
    print("numbers:", len(A["N"]), "tables written to", OUT)


if __name__ == "__main__":
    main()
