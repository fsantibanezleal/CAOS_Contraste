"""Tests of the scripts of the manuscript: the numbers file is current, the experiment results agree with the committed documents,
and the closed forms of the Theory section agree with exact binomial sums.

    python -m pytest manuscripts/size-and-power-of-validation-tests/test_manuscript.py
"""
from __future__ import annotations

import math
import pathlib
import re
import sys

from scipy import stats

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "experiments"))

import analysis as A  # noqa: E402
import make_numbers  # noqa: E402


def test_numbers_file_is_current():
    """tables/numbers.tex is what make_numbers.py writes from the committed documents and the experiment results."""
    make_numbers.M.clear()
    make_numbers.build()
    written = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*?)\}\n", (HERE / "tables" / "numbers.tex").read_text(encoding="utf-8")))
    fresh = {k: v[0] for k, v in make_numbers.M.items()}
    assert written == fresh


def test_every_macro_of_the_text_is_defined():
    """Every control sequence of the text that is shaped like a number macro (n, f, p, z, ... followed by capitals) is defined."""
    defined = set(re.findall(r"\\newcommand\{\\(\w+)\}", (HERE / "tables" / "numbers.tex").read_text(encoding="utf-8")))
    main = (HERE / "main.tex").read_text(encoding="utf-8")
    defined |= set(re.findall(r"\\newcommand\{\\(\w+)\}", main)) | set(re.findall(r"\\DeclareMathOperator\{\\(\w+)\}", main))
    used: set[str] = set()
    for p in list((HERE / "sections").glob("*.tex")) + [HERE / "tables" / f for f in ("design.tex",)]:
        text = re.sub(r"(?<!\\)%.*", "", p.read_text(encoding="utf-8"))
        used |= set(re.findall(r"\\([a-z]+[A-Z]\w*)", text))
    known_latex = {"nrep", "mathrm", "textbf", "texttt", "citep", "citet", "cref", "Cref", "eqref", "includegraphics", "xrightarrow",
                   "mathcal", "binom", "dots", "hat", "widehat", "tfrac", "cite", "caption", "label", "begin", "end", "frac"}
    missing = {u for u in used if u not in defined and u not in known_latex and u[0] in "nfpzsdbhcwyaeiktmrlgo"}
    unknown_number_macros = {m for m in missing if re.fullmatch(r"[a-z]+[A-Z][A-Za-z]*", m) and m not in {
        "textasciitilde", "citep", "citet", "eqref", "mathrm", "Bin", "Phin", "indic", "Prob", "dd", "tfrac"}}
    assert not unknown_number_macros, sorted(unknown_number_macros)


def test_reproduction_of_the_committed_cells_is_exact():
    r = A.result("reproduce.json")
    assert r["equal"] == r["total"] == 21
    doc = {x["key"]: x for x in A.doc("null")["outputs"]["simulations"]}
    for c in r["cells"]:
        row = doc[c["key"]]
        assert (c["k05"], c["k01"], c["seed"], c["n_rep"]) == (
            row["rates"]["p<0.05"]["rejections"], row["rates"]["p<0.01"]["rejections"], row["seed"], row["n_rep"])


def test_totals_of_the_measurement():
    t = A.totals()
    assert (t["sims"], t["reps"], t["rates"], t["exact_rows"], t["generators"]) == (231, 551000, 476, 47, 123)


def test_every_exact_comparison_agrees():
    pairs = A.exact_comparisons()
    assert len(pairs) == 94
    assert all(p["agrees"] for p in pairs)
    assert max(abs(p["z"]) for p in pairs) < 3.29


def test_independent_recomputation_of_the_binomial_exact_values():
    r = A.reconcile_binomial()
    assert r["n"] == 26 and r["max_abs"] < 1e-9


def test_size_rule_matches_the_committed_count():
    """The screen (Algorithm 1) on the committed cells: 19 of 21, as the product's own rule decides."""
    rows = A.size_table()
    assert sum(r["holds"] for r in rows) == 19
    assert {r["test"] for r in rows if not r["holds"]} == {"pd.jeffreys", "pd.normal_multiperiod"}


def test_definition_on_the_committed_cells_and_on_the_pool():
    """The one definition of holding a size: 18 of 21 on the committed cells, 12 of 21 on the pool of 200,000 repetitions."""
    rows = A.size_table()
    assert {r["test"] for r in rows if not r["holds_definition"]} == {"pd.jeffreys", "pd.normal_multiperiod", "rating.markov_order"}
    cv = A.committed_verdict_vs_pooled()
    assert sum(r["pool_definition"] for r in cv) == 12
    assert {r["test"] for r in cv if not r["pool_definition"]} == set(A.groups_by_pooled()["over"])
    assert sum(r["pool_rule"] for r in cv) == 14
    assert sum(r["agree_definition"] for r in cv) == 15 and sum(r["agree_rule"] for r in cv) == 16


def test_every_test_whose_interval_lies_above_its_level_is_marked_not_holding():
    """No row of the main table that has a Wilson interval wholly above the level (or an exact value above it) holds."""
    for r in A.size_table():
        shown = any(r[lv]["interval_above"] for lv in A.LEVELS) or bool(r["exact"] and any(r["exact"][lv] > A.ALPHA[lv] for lv in A.LEVELS))
        assert r["holds_definition"] == (not shown), r["test"]
    pooled = A.seed_replication()["tests"]
    for r in A.committed_verdict_vs_pooled():
        t = r["test"]
        above = any(pooled[t][lv]["pooled_lo"] > A.ALPHA[lv] for lv in A.LEVELS)
        assert r["pool_definition"] == (not above), t


def test_wilson_interval_is_exact_at_the_edges():
    """In exact arithmetic the interval is [0, x] at k = 0 and [x, 1] at k = n; a residue of 1e-19 excluded exact 0 and 1."""
    assert A.wilson(0, 4000)[0] == 0.0 and A.wilson(4000, 4000)[1] == 1.0
    assert 0.0 < A.wilson(0, 4000)[1] < 0.002
    iv = A.interval_on_exact_rows()
    assert iv["Wilson"]["all"] >= iv["Agresti--Coull"]["all"] - 2


def test_title_states_the_count_of_the_definition():
    """The title carries the number of tests that hold their size on the pool, as a word; it is the number of the text."""
    words = {12: "Twelve", 13: "Thirteen", 11: "Eleven", 14: "Fourteen", 10: "Ten", 9: "Nine"}
    n = sum(r["pool_definition"] for r in A.committed_verdict_vs_pooled())
    title = re.search(r"title\{(.*?)\}\n", (HERE / "main.tex").read_text(encoding="utf-8")).group(1)
    assert title.startswith(words[n] + " of 21 "), (n, title)
    coverage = (HERE / "coverage.json").read_text(encoding="utf-8")
    assert "tab:seed-replication" in coverage and "tab:main-results" in coverage


def test_abstract_is_within_250_words_with_the_macros_expanded():
    nums = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*?)\}\n", (HERE / "tables" / "numbers.tex").read_text(encoding="utf-8")))
    text = (HERE / "sections" / "00-abstract.tex").read_text(encoding="utf-8")
    text = re.sub(r"\\(\w+)(\{\})?", lambda m: nums.get(m.group(1), " "), text)
    assert 150 <= len(text.split()) <= 250, len(text.split())


def test_the_excess_ranges_are_read_at_the_level_that_places_a_test_above():
    """The excess of a test of the group above the level is read at the level at which its pooled interval lies above it."""
    pooled = A.seed_replication()["tests"]
    csi = pooled["stability.csi"]
    assert csi["p<0.05"]["pooled_lo"] <= 0.05 and csi["p<0.01"]["pooled_lo"] > 0.01
    nums = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*?)\}\n", (HERE / "tables" / "numbers.tex").read_text(encoding="utf-8")))
    assert nums["smallExcMin"] == "0.05"


def test_flag_probability_matches_a_direct_binomial_sum():
    import exp_instrument as E

    for alpha in (0.05, 0.01):
        b = A.bound(alpha, 4000)
        direct = sum(stats.binom.pmf(k, 4000, alpha) for k in range(4000 + 1) if k / 4000 > b)
        assert math.isclose(E.flag_probability(alpha, 4000), direct, rel_tol=1e-9)


def test_clustering_limit_is_approached_by_the_exact_size():
    sizes = [A.binomial_size(n, 0.01, 0.10, 0.05) for n in (1000, 10000, 100000, 1000000)]
    assert sizes == sorted(sizes)
    assert abs(sizes[-1] - A.binomial_size_limit(0.01, 0.10)) < 0.01


def test_psi_theory_matches_the_chi_square_tail():
    assert math.isclose(A.psi_fixed_band_false_alarm(100, 0.10), stats.chi2.sf(5.0, 9))


def test_hhi_statistic_cannot_reject_with_ten_grades():
    assert 3.0 * A.hhi_peak_gain(0.6) < stats.norm.ppf(0.95)
    assert A.hhi_min_grades(0.6) == 22
