"""C04's published answers (CT-406): Israel, Rosenthal and Wei's nine distances, Schuermann and Hanson's Table 5 and
Engelmann's section 4, recomputed by riskvalidation beside their prints and without the agency matrices the papers
reprint. The reproduction reads the fetched PDFs when the device data root holds them. Everywhere, the case also runs
on synthetic prints: each paper's layout around made-up matrices (a paper's matrix is never committed) printing the
numbers those matrices give (computed once with riskvalidation 0.4.0 and pinned here; Table 5 prints the paper's own
results), so that every output is compared with a direct engine call on known inputs, every agreement check passes on
the print and refuses a changed one, and every refusal of the readers and of the case runs."""
from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path

import numpy as np
import pytest

from riskvalidation.transitions import embedding as emb
from riskvalidation.transitions import ttc
from riskvalidation.transitions.intervals import pd_agresti_coull, pd_wald

from pipeline.cases import c04_published as pub
from pipeline.io import papers

DATA = os.environ.get("CONTRASTE_DATA")
RAW = Path(DATA) / "raw" if DATA else None
IRW = RAW / pub.IRW_SOURCE / pub.IRW_PDF if RAW else None
ENGELMANN = RAW / pub.ENGELMANN_SOURCE / pub.ENGELMANN_PDF if RAW else None
SR190 = RAW / pub.SR190_SOURCE / pub.SR190_PDF if RAW else None
needs_pdfs = pytest.mark.skipif(not all(p is not None and p.exists() for p in (IRW, ENGELMANN, SR190)),
                                reason="the C04 papers are fetched into the device data root (CONTRASTE_DATA)")

#: contract.md section 3, key by key
KEYS = {
    "top": {"kind", "irw", "sr190", "engelmann"},
    "irw": {"rows", "jlt_from_printed_generator", "theorem3_c", "series_terms"},
    "irw_row": {"matrix", "method", "printed", "recomputed", "agrees"},
    "sr190": {"defaults", "n", "rows", "n_dagger"},
    "sr190_row": {"rho", "interval", "printed", "recomputed", "agrees"},
    "engelmann": {"w_ttc", "ttc_pd", "portfolios", "row_sum_deviation"},
    "pair": {"printed", "recomputed", "decimals"},
    "pd0": {"printed", "recomputed", "decimals", "check", "note"},
    "portfolio": {"name", "w0", "pd0", "extreme", "pd_path"},
    "extreme": {"kind", "printed", "recomputed", "decimals"},
}
#: the names the outputs carry, in print order, as the contract states them (never the module's own constants)
MATRICES = ["S&P 1981-1991", "Moody's 1980-1998", "S&P 1999"]
METHODS = ["jlt", "diagonal", "weighted"]
PORTFOLIOS = ["W_init", "W_init 2", "W tilde", "W hat"]
#: the extreme Engelmann prints for each starting portfolio's projection
EXTREMES = {"W_init": None, "W_init 2": "min", "W tilde": "max", "W hat": None}
#: Israel et al.'s nine printed distances (results, not data), by matrix: JLT (3), series with (2), with (2')
IRW_PRINTED = (("0.116900", "0.002736", "0.002686"), ("0.100047", "0.001401", "0.001371"),
               ("0.103516", "0.001096", "0.001088"))
RHO = chr(0x03C1)  # the Greek rho of Table 5's column heads
#: Schuermann and Hanson's Table 5 as the extraction gives it (the paper's own computations, no data)
TABLE5 = "\n".join([
    "-27-", "Assuming", "Independence", "Assuming", f"Dependence ({RHO} = 0.01)", "Assuming",
    f"Dependence ({RHO} = 0.02)",
    "N / N\u2020 531 84.3 45.8",
    "CI with length CI length CI length CI length",
    "Standard Wald (141.56, 423.41) 281.84 (0.00, 636.20) 636.20 (0.00, 762.45) 762.45",
    "Agresti-Coull (168.03, 464.71) 296.68 (38.25, 938.00) 899.75 (0.00, 1,332.56) 1,332.56",
    "Bootstrap (150.09, 433.92) 283.83 N/A N/A N/A N/A",
    "Table 5: Confidence intervals for 2002 BB defau lt probabilities in ba sis points estimated",
    "by cohort method.",
])
#: Table 5's printed cells as fractions: Wald, then Agresti-Coull, each at a correlation of 0, 0.01 and 0.02
TABLE5_FRACTIONS = [[0.014156, 0.042341, 0.028184], [0.0, 0.06362, 0.06362], [0.0, 0.076245, 0.076245],
                    [0.016803, 0.046471, 0.029668], [0.003825, 0.0938, 0.089975], [0.0, 0.133256, 0.133256]]


# ---------------------------------------------------------------------------------------------------------------------
# synthetic prints: each paper's layout around made-up matrices, printing the results those matrices give


def _toy() -> np.ndarray:
    """A made-up one-year matrix over seven grades and default: stay 0.8, one grade up or down 0.1 each (the best
    grade 0.2 down), default absorbing. Its performing block is primitive and every diagonal entry exceeds 1/2."""
    p = np.zeros((8, 8))
    for i in range(7):
        p[i, i] = 0.8
        p[i, i + 1] = 0.1 if i else 0.2
        if i:
            p[i, i - 1] = 0.1
    p[7, 7] = 1.0
    return p


def _toy_moved() -> np.ndarray:
    """The first made-up matrix with a move of two grades: A stays 0.75 and moves to BB 0.05."""
    p = _toy()
    p[2, 2], p[2, 4] = 0.75, 0.05
    return p


def _toy_spread() -> np.ndarray:
    """A made-up matrix in which every grade reaches every state within the year (one grade away 0.05, two 0.0003,
    further 0.0001), so Theorem 3(c) does not hold. Its series still has negative entries (a move of two grades is rarer
    than two moves of one) and stops at 1e-8 after 10 terms, where the first matrix's stops after 16."""
    p = np.zeros((8, 8))
    for i in range(7):
        for j in range(8):
            if j != i:
                p[i, j] = 0.05 if abs(i - j) == 1 else 0.0003 if abs(i - j) == 2 else 0.0001
        p[i, i] = round(1.0 - p[i].sum(), 4)
    p[7, 7] = 1.0
    return p


#: Israel et al.'s three matrices, made up and different: the toy, the toy with a move of two grades, every move seen
TOYS = dict(zip(MATRICES, (_toy(), _toy_moved(), _toy_spread()), strict=True))
#: the first matrix's printed Q_JLT: equation (3) to four digits, as the paper prints its own (not P - I)
Q_PRINTED = np.array([[float(f"{x:.4f}") for x in row] for row in emb.jlt_generator(_toy())])
#: the nine distances the made-up matrices give, by matrix: JLT, series with (2), with (2'). As in the paper
#: (F-IRW-JLT), the first JLT distance is the printed Q_JLT's (0.264895), not equation (3)'s on the matrix (0.264833)
IRW_TOY_PRINTED = (("0.264895", "0.169322", "0.161071"), ("0.266329", "0.170382", "0.162120"),
                   ("0.058286", "0.025147", "0.024538"))
#: the paper's sentence counting the first matrix's series terms, with the extraction's ligatures and minus sign
SERIES = ("Indeed, we \ufb01nd that the series (1) for ~Q indeed converges very quickly. In fact, summing just the "
          "\ufb01rst\n16 terms of the series, we compute that the e\ufb00ect of subsequent terms is "
          "less than 10 \u22128, thus giving\nextremely high accuracy.")

#: a made-up matrix (11) over seven grades and default, to four digits; its CCC row sums to 1.0001, as the paper's
#: rows sum to 1 within 0.0001
T_TOY = np.array([
    [0.9000, 0.0800, 0.0150, 0.0040, 0.0010, 0.0000, 0.0000, 0.0000],
    [0.0100, 0.9000, 0.0700, 0.0150, 0.0030, 0.0010, 0.0005, 0.0005],
    [0.0010, 0.0250, 0.9000, 0.0600, 0.0100, 0.0025, 0.0005, 0.0010],
    [0.0005, 0.0030, 0.0500, 0.8800, 0.0500, 0.0120, 0.0020, 0.0025],
    [0.0003, 0.0010, 0.0050, 0.0700, 0.8200, 0.0800, 0.0117, 0.0120],
    [0.0000, 0.0010, 0.0030, 0.0060, 0.0600, 0.8300, 0.0500, 0.0500],
    [0.0000, 0.0000, 0.0040, 0.0080, 0.0200, 0.1000, 0.6200, 0.2481],
    [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 1.0000],
])
O = [0.00, 0.20, 0.30, 0.30, 0.20, 0.00, 0.00, 0.00]
#: the starting portfolios: Engelmann's printed vectors, W hat's made up to four digits
W0 = {"W_init": [0.00, 0.00, 0.20, 0.40, 0.30, 0.10, 0.00, 0.00],
      "W_init 2": [0.70, 0.00, 0.00, 0.00, 0.00, 0.25, 0.05, 0.00],
      "W tilde": [0.01, 0.02, 0.10, 0.30, 0.41, 0.15, 0.01, 0.00],
      "W hat": [0.0150, 0.1300, 0.3300, 0.2700, 0.1400, 0.0950, 0.0200, 0.0000]}
#: what T_TOY gives, printed as the paper prints its own: W_ttc to four digits, PDs in percent. W_init 2's PD (2.4905%)
#: sits on the half-way point and prints half up, as the paper's 2.7245% does; W hat's PD prints 0.0012 percentage
#: points from its four-digit entries' 1.2462%, as the paper's 1.093% lies 0.0015 from 1.0945%
T_TOY_PRINTED = {"w_ttc": "0.0172, 0.1239, 0.2866, 0.2892, 0.1524, 0.1095, 0.0212, 0", "ttc_pd": "1.363",
                 "W_init": "0.980", "W_init 2": "2.491", "min": "0.889", "W tilde": "1.58", "max": "2.07",
                 "W hat": "1.245"}


def _print_rows(m: np.ndarray) -> list[str]:
    """Matrix rows as the extraction gives them: four decimals, split after the first entry ("0 .1000"), the minus
    sign U+2212."""
    lines = []
    for row in m:
        cells = [f"{x:.4f}".replace("-", "\u2212") for x in row]
        lines.append(" ".join([cells[0], *(c.replace(".", " .") for c in cells[1:])]))
    return lines


def _stated(values: list[str], jlt: int) -> str:
    """One matrix's "norm[...] = " statements, the one at index ``jlt`` JLT's (the print puts it first)."""
    lines = []
    for k, v in enumerate(values):
        label = "P \u2212 exp(QJLT )" if k == jlt else "P \u2212 exp(Q)"
        lines.append(f"norm[{label}] = {v.replace('.', ' .')} .")
    return "\n".join(lines)


def _irw_text(first: list[str] | None = None, *, q: np.ndarray = Q_PRINTED, norms: list[list[str]] | None = None,
              jlt: tuple[int, int, int] = (0, 0, 0), series: str = SERIES, series_late: bool = False) -> str:
    """Section 4 in the print's layout around TOYS: each matrix (``first`` replaces the first one's rows), the first
    one's printed Q_JLT ``q`` and the sentence counting its series' terms (``series_late``: after the second matrix),
    and the printed distances ``norms`` after each matrix, JLT's at index ``jlt``."""
    rows = [_print_rows(m) for m in TOYS.values()]
    norms = norms if norms is not None else [list(v) for v in IRW_TOY_PRINTED]
    return "\n".join([
        "After distributing the weights they obtain the following average transition matrix (their Table 3):", "P =",
        *(rows[0] if first is None else first), ".",
        "To continue the above example, their approximate generator is", "QJLT =", "9", *_print_rows(q), ".",
        "" if series_late else series, _stated(norms[0], jlt[0]),
        "After re-assigning the weights to the other entries, we obtain the", "following transition matrix:", "P =",
        *rows[1], "", _stated(norms[1], jlt[1]), series if series_late else "",
        "Rated weights, we obtain the following annual transition matrix:", "P =", *rows[2], "",
        _stated(norms[2], jlt[2]),
    ])


def _engelmann_text(rows: list[str] | None = None) -> str:
    """Section 4 in the print's layout around T_TOY (``rows`` replaces its rows), with the results it gives."""
    pr = T_TOY_PRINTED
    return "\n".join([
        "To provide some illustrative examples, a transition matrix T from Trueck and Rachev",
        "(2009), page 3, is used", "T =", *(_print_rows(T_TOY) if rows is None else rows), "(11)",
        "together with the origination vector O = (0.00, 0.20, 0.30, 0.30, 0.20, 0.00, 0.00, 0.00).",
        "An application of the iterative algorithm of Theorem 1 leads to the TTC portfolio Wttc =",
        f"({pr['w_ttc']}). The corresponding portfolio",
        f"TTC PD is {pr['ttc_pd']}%.",
        "Suppose the current bank portfolio is Winit = (0.00, 0.00, 0.20, 0.40, 0.30, 0.10, 0.00,",
        f"0.00). The portfolio PD is {pr['W_init']}% which is slightly lower than the PD of the portfolio",
        "The next example is using an even more extreme deviation fromWttc, the initial portfolio",
        "Winit = (0.70, 0.00, 0.00, 0.00, 0.00, 0.25, 0.05, 0.00) which has an average portfolio PD",
        f"of {pr['W_init 2']}%. Before converging to Wttc the portfolio reaches a minimum",
        f"average PD of {pr['min']}% indicating a benign economy.",
        "For the initial portfolio fW = (0.01, 0.02, 0.10, 0.30,",
        f"0.41, 0.15, 0.01, 0.00) with average portfolio PD {pr['W tilde']}% the projection is shown in Figure 3.",
        f"The portfolio PD moves up to a maximum of {pr['max']}% before the portfolio starts converging",
        "In the final example, the initial portfolio is cWinit = (0.0150, 0.1300, 0.3300, 0.2700,",
        f"0.1400, 0.0950, 0.0200, 0.0000) with average portfolio PD {pr['W hat']}%.",
    ])


def _swap(text: str, old: str, new: str) -> str:
    """``text`` with ``old``, which must stand there once, replaced by ``new`` (a corruption that changes nothing
    would test nothing)."""
    assert text.count(old) == 1, old
    return text.replace(old, new)


def _pages_of(text: str):
    return lambda pdf: ["front matter", text]


def _bake(monkeypatch, root: Path, *, irw: str | None = None, engelmann: str | None = None,
          table5: str | None = None) -> dict:
    """The published outputs from synthetic prints, each paper's own unless replaced."""
    texts = {pub.IRW_PDF: _irw_text() if irw is None else irw,
             pub.ENGELMANN_PDF: _engelmann_text() if engelmann is None else engelmann,
             pub.SR190_PDF: TABLE5 if table5 is None else table5}
    monkeypatch.setattr(papers, "_pages", lambda pdf: ["front matter", texts[Path(pdf).name]])
    return pub.published_outputs(root)


# ---------------------------------------------------------------------------------------------------------------------
# checks shared by the synthetic and the real outputs


def _json_leaves(x) -> None:
    """Only dicts with str keys, lists, str, bool, int, finite float and None (no numpy scalar, no tuple)."""
    if isinstance(x, dict):
        assert all(type(k) is str for k in x)
        for v in x.values():
            _json_leaves(v)
    elif type(x) is list:
        for v in x:
            _json_leaves(v)
    else:
        assert x is None or type(x) in (str, bool, int, float), type(x)
        assert type(x) is not float or math.isfinite(x)


def _lists(x, found: list) -> list:
    if isinstance(x, dict):
        for v in x.values():
            _lists(v, found)
    elif isinstance(x, list):
        found.append(x)
        for v in x:
            _lists(v, found)
    return found


def _runs(seq, k: int = 4) -> set[tuple[float, ...]]:
    """Every run of ``k`` consecutive numbers of ``seq``, rounded to twelve digits."""
    values = [round(float(x), 12) for x in seq]
    return {tuple(values[i:i + k]) for i in range(len(values) - k + 1)}


def _assert_no_paper_matrix(out: dict, matrices: list) -> None:
    """Derived-only: no run of four consecutive entries of a printed matrix, along a row, down a column or through the
    flattened matrix, stands in any list of the outputs, which rules out a leaked block, row, column, flattened matrix
    or partial row. Runs with fewer than two non-zero entries are left out: any vector of shares has those."""
    printed = set()
    for m in matrices:
        a = np.asarray(m, dtype=float)
        for seq in (*a, *a.T, a.ravel()):
            printed |= {r for r in _runs(seq) if sum(x != 0.0 for x in r) >= 2}
    for v in _lists(out, []):
        if all(type(x) in (int, float) for x in v):
            assert not _runs(v) & printed, v


def _numbers(out: dict) -> set[float]:
    """Every number of the serialized outputs, token by token (a number never matches inside a longer one)."""
    return {float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", json.dumps(out))}


def _check_contract(out: dict) -> None:
    """Contract section 3: the keys at every level, the names, kinds and lengths as the contract states them, the
    types, JSON safety."""
    assert set(out) == KEYS["top"] and out["kind"] == "published"
    irw = out["irw"]
    assert set(irw) == KEYS["irw"] and type(irw["series_terms"]) is int
    assert [(r["matrix"], r["method"]) for r in irw["rows"]] == [(m, k) for m in MATRICES for k in METHODS]
    assert all(set(r) == KEYS["irw_row"] and type(r["agrees"]) is bool for r in irw["rows"])
    assert len(irw["theorem3_c"]) == 3 and all(type(x) is bool for x in irw["theorem3_c"])
    sr = out["sr190"]
    assert set(sr) == KEYS["sr190"] and type(sr["defaults"]) is int and type(sr["n"]) is int
    nd = sr["n_dagger"]
    assert set(nd) == KEYS["pair"] and len(nd["printed"]) == len(nd["recomputed"]) == len(nd["decimals"]) == 3
    assert all(type(x) is float for x in nd["printed"] + nd["recomputed"]) and all(type(x) is int for x in nd["decimals"])
    assert [(r["interval"], r["rho"]) for r in sr["rows"]] == [(k, rho) for k in ("wald", "agresti_coull")
                                                                for rho in (0.0, 0.01, 0.02)]
    for r in sr["rows"]:
        assert set(r) == KEYS["sr190_row"] and len(r["printed"]) == len(r["recomputed"]) == 3
        assert type(r["agrees"]) is bool and all(0.0 <= x <= 1.0 for x in r["printed"] + r["recomputed"])
    eng = out["engelmann"]
    assert set(eng) == KEYS["engelmann"] and set(eng["w_ttc"]) == set(eng["ttc_pd"]) == KEYS["pair"]
    assert len(eng["w_ttc"]["printed"]) == len(eng["w_ttc"]["recomputed"]) == len(eng["w_ttc"]["decimals"]) == 8
    assert type(eng["ttc_pd"]["decimals"]) is int
    assert [p["name"] for p in eng["portfolios"]] == PORTFOLIOS
    for p in eng["portfolios"]:
        assert set(p) == KEYS["portfolio"] and set(p["pd0"]) == KEYS["pd0"] and len(p["w0"]) == 8
        assert p["pd0"]["check"] in ("printed digits", "entry rounding")
        assert (p["pd0"]["note"] is None) == (p["pd0"]["check"] == "printed digits")
        # the note is shown in both languages: English and Spanish text, never one language for both
        note = p["pd0"]["note"]
        assert note is None or (set(note) == {"en", "es"} and all(note[k].strip() for k in note) and note["en"] != note["es"])
        # the projected PD by year over Engelmann's 50 years, as fractions, starting at the portfolio's own PD
        assert len(p["pd_path"]) == 50 and p["pd_path"][0] == p["pd0"]["recomputed"]
        assert all(0.0 <= x <= 1.0 for x in p["pd_path"])
        kind = EXTREMES[p["name"]]
        if kind is None:
            assert p["extreme"] is None, p["name"]
        else:
            assert set(p["extreme"]) == KEYS["extreme"] and p["extreme"]["kind"] == kind, p["name"]
            assert p["extreme"]["recomputed"] == (min if kind == "min" else max)(p["pd_path"])
    json.dumps(out, allow_nan=False)
    _json_leaves(out)


# ---------------------------------------------------------------------------------------------------------------------
# the reproduction on the fetched papers


@needs_pdfs
def test_readers_on_the_papers():
    """The readers on the fetched prints: the nine printed distances and the count of the series' terms, Table 5,
    Engelmann's vectors and PDs."""
    irw = papers.read_irw_2001(IRW)
    assert [(d["printed"], d["decimals"]) for d in irw["distances"]] == [(float(v), 6) for m in IRW_PRINTED for v in m]
    assert (irw["series_terms"], irw["series_accuracy"]) == (16, 1e-8)  # "the first 16 terms ... less than 10^-8"
    t5 = papers.read_sr190_table5(SR190)
    assert (t5["n"], t5["rho"], t5["n_dagger"]) == (531, [0.0, 0.01, 0.02], [531.0, 84.3, 45.8])
    assert t5["wald"][0] == [141.56, 423.41, 281.84] and t5["agresti_coull"][2] == [0.0, 1332.56, 1332.56]
    assert t5["bootstrap"] == [150.09, 433.92, 283.83]
    eng = papers.read_engelmann_2024(ENGELMANN)
    assert eng["origination"] == [0.0, 0.2, 0.3, 0.3, 0.2, 0.0, 0.0, 0.0] and eng["ttc_pd_pct"] == 1.198
    assert [(p["name"], p["pd0_pct"], p["extreme"] and (p["extreme"]["kind"], p["extreme"]["pct"]))
            for p in eng["portfolios"]] == [("W_init", 1.161, None), ("W_init 2", 2.725, ("min", 0.722)),
                                            ("W tilde", 1.83, ("max", 2.14)), ("W hat", 1.093, None)]


@needs_pdfs
def test_published_answers():
    """CT-406: every printed value beside its recomputation. Israel et al.: eight distances from the printed matrices,
    the ninth (F-IRW-JLT) from the printed Q_JLT, not from equation (3) on the printed P; the series' 16 terms at the
    printed 1e-8; Table 5's twelve bounds and lengths at the one count of defaults the print allows (15), and its N
    dagger; Engelmann's TTC portfolio and PD, the starting PDs and the extremes, W hat's PD agreeing only within the
    rounding of its entries. No matrix of the papers is in the outputs, as a run of entries or as a number."""
    out = pub.published_outputs(Path(DATA))
    _check_contract(out)
    irw = out["irw"]
    assert [r["printed"] for r in irw["rows"]] == [float(v) for m in IRW_PRINTED for v in m]
    assert [r["agrees"] for r in irw["rows"]] == [False] + [True] * 8
    assert pub.IRW_NOT_FROM_P == ("S&P 1981-1991", "jlt")
    assert pub.prints_as(irw["rows"][0]["recomputed"], 0.116477, 6)  # equation (3) itself on the printed P
    assert pub.prints_as(irw["jlt_from_printed_generator"], 0.116900, 6)  # the printed Q_JLT's distance
    assert irw["theorem3_c"] == [True, True, True] and irw["series_terms"] == 16
    sr = out["sr190"]
    assert (sr["defaults"], sr["n"]) == (15, 531) and all(r["agrees"] for r in sr["rows"])
    assert [r["printed"] for r in sr["rows"]] == TABLE5_FRACTIONS
    nd = sr["n_dagger"]
    assert (nd["printed"], nd["decimals"]) == ([531.0, 84.3, 45.8], [0, 1, 1])
    assert all(pub.prints_as(v, p, d) for v, p, d in zip(nd["recomputed"], nd["printed"], nd["decimals"], strict=True))
    # Engelmann: the outputs hold fractions, compared here in percent at the printed digits
    eng = out["engelmann"]
    assert eng["w_ttc"]["printed"] == [0.0183, 0.1423, 0.3379, 0.2633, 0.1321, 0.0911, 0.015, 0.0]
    assert all(pub.prints_as(v, p, 4) for v, p in zip(eng["w_ttc"]["recomputed"], eng["w_ttc"]["printed"], strict=True))
    assert eng["ttc_pd"]["printed"] == 0.01198 and pub.prints_as(100 * eng["ttc_pd"]["recomputed"], 1.198, 3)
    assert [p["pd0"]["printed"] for p in eng["portfolios"]] == [0.01161, 0.02725, 0.0183, 0.01093]
    pd0 = {p["name"]: 100 * p["pd0"]["recomputed"] for p in eng["portfolios"]}
    printed_pd0 = {"W_init": (1.161, 3), "W_init 2": (2.725, 3), "W tilde": (1.83, 2), "W hat": (1.093, 3)}
    agrees = {k: pub.prints_as(pd0[k], v, d) for k, (v, d) in printed_pd0.items()}
    assert agrees == {"W_init": True, "W_init 2": True, "W tilde": True, "W hat": False}
    # W hat's documented mismatch: its four-digit entries give 1.0945%, which does not print as 1.093% (so the case
    # checks it within the rounding of the entries, ENTRY_ROUNDING, and nothing else is checked that way)
    assert set(pub.ENTRY_ROUNDING) == {"W hat"} and abs(pd0["W hat"] - 1.0945) < 5e-5
    assert [p["extreme"] and (p["extreme"]["kind"], p["extreme"]["printed"]) for p in eng["portfolios"]] == [
        None, ("min", 0.00722), ("max", 0.0214), None]
    assert pub.prints_as(100 * eng["portfolios"][1]["extreme"]["recomputed"], 0.722, 3)
    assert pub.prints_as(100 * eng["portfolios"][2]["extreme"]["recomputed"], 2.14, 2)
    assert eng["row_sum_deviation"] == pytest.approx(1e-4, abs=1e-9)  # the print's four-digit rounding
    paper = papers.read_irw_2001(IRW)
    matrices = [*paper["matrices"].values(), paper["q_jlt"], papers.read_engelmann_2024(ENGELMANN)["matrix"]]
    _assert_no_paper_matrix(out, matrices)
    # and as text: no diagonal entry of a printed matrix (Q_JLT's negative ones included) is a number of the outputs
    numbers = _numbers(out)
    for m in matrices:
        assert not numbers & {float(x) for x in np.diag(np.asarray(m, dtype=float))[:-1]}


# ---------------------------------------------------------------------------------------------------------------------
# everywhere: the outputs against the engine, the agreement rule, the guards, the refusals


def test_published_outputs_on_synthetic_prints(monkeypatch, tmp_path):
    """Contract section 3 on synthetic prints, every output against a direct engine call on the known inputs: the nine
    distances by their literal matrix and method, the first one disagreeing as in the paper and reproduced from the
    printed Q_JLT; Theorem 3(c) on three different matrices; the series' terms at the printed accuracy; Table 5 at its
    15 defaults; the TTC portfolio, the four portfolios' 50-year paths, their printed PDs and extremes; no made-up
    matrix in the outputs; two runs identical."""
    out = _bake(monkeypatch, tmp_path)
    _check_contract(out)
    irw = out["irw"]
    for r in irw["rows"]:
        assert r["recomputed"] == emb.generator(TOYS[r["matrix"]], method=r["method"])["l1_distance"], r
    assert [r["printed"] for r in irw["rows"]] == [float(v) for m in IRW_TOY_PRINTED for v in m]
    assert [r["agrees"] for r in irw["rows"]] == [False] + [True] * 8
    first = TOYS["S&P 1981-1991"]
    assert irw["jlt_from_printed_generator"] == emb.l1_distance(first, Q_PRINTED)
    assert pub.prints_as(irw["jlt_from_printed_generator"], 0.264895, 6)
    assert not pub.prints_as(emb.l1_distance(first, emb.jlt_generator(first)), 0.264895, 6)
    assert irw["theorem3_c"] == [True, True, False]
    # the count is the first matrix's: the third one's series stops after another number of terms
    assert irw["series_terms"] == 16 == emb.log_series(first, tol=1e-8)["terms"]
    assert emb.log_series(TOYS["S&P 1999"], tol=1e-8)["terms"] == 10
    sr = out["sr190"]
    assert (sr["defaults"], sr["n"]) == (15, 531) and all(r["agrees"] for r in sr["rows"])
    assert [r["printed"] for r in sr["rows"]] == TABLE5_FRACTIONS
    for r in sr["rows"]:
        want = (pd_wald if r["interval"] == "wald" else pd_agresti_coull)(15, 531, level=0.95, rho=r["rho"])
        assert r["recomputed"] == [want["lower"], want["upper"], want["length"]]
    assert sr["n_dagger"]["recomputed"] == [pd_wald(15, 531, rho=rho)["n_effective"] for rho in (0.0, 0.01, 0.02)]
    eng = out["engelmann"]
    fit = ttc.ttc_portfolio(T_TOY, O)
    assert eng["w_ttc"]["recomputed"] == list(fit["portfolio"]) and eng["ttc_pd"]["recomputed"] == fit["default_rate"]
    assert eng["w_ttc"]["printed"] == [0.0172, 0.1239, 0.2866, 0.2892, 0.1524, 0.1095, 0.0212, 0.0]
    assert eng["ttc_pd"]["printed"] == 0.01363
    assert [p["pd0"]["printed"] for p in eng["portfolios"]] == [0.0098, 0.02491, 0.0158, 0.01245]
    assert [p["extreme"] and p["extreme"]["printed"] for p in eng["portfolios"]] == [None, 0.00889, 0.0207, None]
    for p in eng["portfolios"]:
        path = ttc.project(T_TOY, W0[p["name"]], O, 50)["default_rate"]
        assert p["w0"] == W0[p["name"]] and p["pd_path"] == list(path), p["name"]
        kind = EXTREMES[p["name"]]
        if kind is not None:
            assert p["extreme"]["recomputed"] == (path.min() if kind == "min" else path.max())
    # W hat's print agrees only within the rounding of its four-digit entries, as in the paper: half a unit of the
    # fourth digit times the performing grades' default rates (0.3141), plus half a unit of the printed PD's third
    hat = 100 * eng["portfolios"][3]["pd0"]["recomputed"]
    assert not pub.prints_as(hat, 1.245, 3) and abs(hat - 1.245) == pytest.approx(0.0012, abs=1e-9)
    assert pub._entry_rounding(T_TOY, [4] * 8, 3) == pytest.approx(100 * 0.5e-4 * 0.3141 + 0.5e-3, abs=1e-12)
    assert eng["row_sum_deviation"] == pytest.approx(1e-4, abs=1e-9)  # the made-up CCC row sums to 1.0001
    _assert_no_paper_matrix(out, [*TOYS.values(), Q_PRINTED, T_TOY])
    assert _bake(monkeypatch, tmp_path) == out


def test_prints_as_within_half_a_unit():
    """A value agrees with its print when it lies within half a unit of the print's last digit, both ends inclusive
    (the engine test's rule): 2.7245 and 2.7255 both agree with 2.725, 2.7244 and 2.7256 do not. The 1e-9 lets
    100 * 0.027245, which lands 1.7e-16 beyond the half-way point in binary, agree with the paper's 2.725."""
    assert pub.prints_as(2.7245, 2.725, 3) and pub.prints_as(2.7255, 2.725, 3)
    assert not pub.prints_as(2.7244, 2.725, 3) and not pub.prints_as(2.7256, 2.725, 3)
    assert abs(100 * 0.027245 - 2.725) > 0.5e-3 and pub.prints_as(100 * 0.027245, 2.725, 3)
    assert pub.prints_as(0.7222, 0.722, 3) and pub.prints_as(2.1396, 2.14, 2)
    assert not pub.prints_as(0.116477, 0.116900, 6)
    assert type(pub.prints_as(np.float64(1.0), 1.0, 2)) is bool


def test_scaled_is_exact_in_decimal():
    """A printed number scales to the float nearest the decimal it prints, whatever its size: 1.198% is 0.01198,
    1,332.56 bp is 0.133256 (the float division gives 0.13325599999999999), 1e-05% is 1e-07."""
    assert pub._scaled(1.198, -2) == 0.01198 and pub._scaled(0.0, -4) == 0.0
    assert pub._scaled(1332.56, -4) == 0.133256 != 1332.56 / 1e4
    assert pub._scaled(1e-05, -2) == 1e-07 and pub._scaled(2.5e-05, -4) == 2.5e-09


def test_derived_only_guard_catches_a_leak():
    """The derived-only check refuses a printed matrix leaked as a block, a row, a column, the flattened matrix or four
    consecutive entries of a row, and lets the vectors of shares the outputs carry pass."""
    t = T_TOY
    for leak in (t.tolist(), t[3].tolist(), t[:, 7].tolist(), t.ravel().tolist(), [0.5, *t[4, 2:6].tolist()]):
        with pytest.raises(AssertionError):
            _assert_no_paper_matrix({"x": {"y": [leak]}}, [t])
    _assert_no_paper_matrix({"w0": list(W0.values()), "o": O}, [t])


def test_irw_reader_refuses_a_changed_print(monkeypatch):
    """The Israel et al. reader accepts the print's layout and refuses: a matrix with a missing row, a row that does not
    sum to 1, a default that is not absorbing; the matrices out of print order; a printed Q_JLT row that is not a
    generator's, a Q_JLT default row that is not zero; a changed count or order of the printed distances; the count of
    the series' terms missing, or printed after another matrix."""
    text = _irw_text()
    monkeypatch.setattr(papers, "_pages", _pages_of(text))
    out = papers.read_irw_2001(Path("fake.pdf"))
    assert list(out["matrices"]) == MATRICES and list(out["matrices"].values()) == [m.tolist() for m in TOYS.values()]
    assert out["q_jlt"] == Q_PRINTED.tolist() != (TOYS["S&P 1981-1991"] - np.eye(8)).tolist()
    assert [d["method"] for d in out["distances"]] == METHODS * 3
    assert out["distances"][0] == {"matrix": "S&P 1981-1991", "method": "jlt", "printed": 0.264895, "decimals": 6}
    assert (out["series_terms"], out["series_accuracy"]) == (16, 1e-8)
    rows = _print_rows(TOYS["S&P 1981-1991"])
    printed = [list(v) for v in IRW_TOY_PRINTED]
    not_a_rate, default_moves = Q_PRINTED.copy(), Q_PRINTED.copy()
    not_a_rate[1] = TOYS["S&P 1981-1991"][1]                     # a probability row: its diagonal is positive
    default_moves[7, 0], default_moves[7, 7] = 0.0001, -0.0001   # a generator's row, but default is not absorbing
    out_of_order = _swap(_swap(text, "following transition matrix:", "following annual transition matrix:"),
                         "Rated weights, we obtain the following annual", "Rated weights, we obtain the following")
    corrupted = [
        ("7 rows", _irw_text(first=rows[:3] + rows[4:])),                                  # a missing row
        ("sums to", _irw_text(first=[rows[0].replace("0 .2000", "0 .2100"), *rows[1:]])),  # a row off by 0.01
        ("absorbing", _irw_text(first=[*rows[:7], _print_rows(np.full((1, 8), 0.125))[0]])),
        ("not printed in the order", out_of_order),                                       # Moody's and S&P 1999
        ("Q_JLT's row 2 is not a generator's row", _irw_text(q=not_a_rate)),
        ("Q_JLT's default row is not zero", _irw_text(q=default_moves)),
        ("8 printed distances", _irw_text(norms=[printed[0][:2], *printed[1:]])),          # one dropped
        ("10 printed distances", _irw_text(norms=[[*printed[0], "0.002600"], *printed[1:]])),  # one added
        ("not JLT's", _irw_text(jlt=(0, 2, 0))),                                          # JLT's printed last
        ("count of the series' terms", _irw_text(series=SERIES.replace("summing just", "summing"))),
        ("count of the series' terms", _irw_text(series_late=True)),                      # after the second matrix
    ]
    for match, corrupt in corrupted:
        monkeypatch.setattr(papers, "_pages", _pages_of(corrupt))
        with pytest.raises(papers.PaperTableError, match=match):
            papers.read_irw_2001(Path("fake.pdf"))


def test_engelmann_reader_refuses_a_changed_print(monkeypatch):
    """The Engelmann reader accepts the print's layout and refuses: a matrix with a missing row or a row off by more
    than the print's rounding; a vector with seven entries; an origination, a W_ttc or a starting portfolio that does
    not sum to 1; the TTC PD missing; the portfolios out of print order; a printed extreme missing, or printed only
    after the next portfolio (it would be another portfolio's)."""
    text = _engelmann_text()
    monkeypatch.setattr(papers, "_pages", _pages_of(text))
    out = papers.read_engelmann_2024(Path("fake.pdf"))
    assert out["matrix"] == T_TOY.tolist() and out["origination"] == O
    assert out["w_ttc_decimals"] == [4] * 7 + [0] and (out["ttc_pd_pct"], out["ttc_pd_decimals"]) == (1.363, 3)
    assert [p["name"] for p in out["portfolios"]] == PORTFOLIOS
    assert [p["w0"] for p in out["portfolios"]] == list(W0.values())
    assert [(p["pd0_pct"], p["pd0_decimals"]) for p in out["portfolios"]] == [(0.98, 3), (2.491, 3), (1.58, 2),
                                                                               (1.245, 3)]
    assert [p["extreme"] for p in out["portfolios"]] == [None, {"kind": "min", "pct": 0.889, "decimals": 3},
                                                         {"kind": "max", "pct": 2.07, "decimals": 2}, None]
    rows = _print_rows(T_TOY)
    hat = text[text.index("In the final example"):]
    hat_first = _swap(text[:text.index("In the final example") - 1], "For the initial portfolio fW",
                      f"{hat}\nFor the initial portfolio fW")
    no_own_minimum = _swap(text, "reaches a minimum\naverage PD of 0.889%", "drops to an\naverage PD of 0.889%")
    corrupted = [
        ("7 rows", _engelmann_text(rows=rows[:5] + rows[6:])),                                     # a missing row
        ("row 1 sums to", _engelmann_text(rows=[rows[0].replace("0 .0800", "0 .0802"), *rows[1:]])),  # 2e-4 off
        ("O prints 7 entries", _swap(text, "O = (0.00, 0.20,", "O = (0.20,")),
        ("vector O sums to", _swap(text, "O = (0.00, 0.20, 0.30, 0.30, 0.20,", "O = (0.00, 0.20, 0.30, 0.30, 0.10,")),
        ("W_ttc sums to 1.010000", _swap(text, "(0.0172, 0.1239", "(0.0272, 0.1239")),
        ("W_init with its PD sums to 1.050000",
         _swap(text, "is Winit = (0.00, 0.00, 0.20,", "is Winit = (0.00, 0.00, 0.25,")),
        ("the TTC PD not found", _swap(text, "TTC PD is", "TTC PD was")),
        ("portfolios are not printed in the order", hat_first),                                # W hat before W tilde
        ("maximum of W tilde's projection not found", _swap(text, "moves up to a maximum of", "rises to")),
        # W_init 2's own minimum gone, another printed later: never bound to W_init 2
        ("minimum of W_init 2's projection not found between",
         f"{no_own_minimum}\nThe last one reaches a minimum average PD of 1.050% as well."),
    ]
    for match, corrupt in corrupted:
        monkeypatch.setattr(papers, "_pages", _pages_of(corrupt))
        with pytest.raises(papers.PaperTableError, match=match):
            papers.read_engelmann_2024(Path("fake.pdf"))


def test_sr190_reader_refuses_a_changed_print(monkeypatch):
    """The Table 5 reader takes the thousands comma ("1,332.56") and refuses: the table missing, a caption that does
    not state basis points by the cohort method, other correlations, the row N / N dagger missing or not falling, a
    missing row, a length that is not the upper bound less the lower one."""
    monkeypatch.setattr(papers, "_pages", _pages_of(TABLE5))
    out = papers.read_sr190_table5(Path("fake.pdf"))
    assert (out["n"], out["n_dagger"], out["n_dagger_decimals"]) == (531, [531.0, 84.3, 45.8], [0, 1, 1])
    assert out["agresti_coull"][2] == [0.0, 1332.56, 1332.56] and out["bootstrap"] == [150.09, 433.92, 283.83]
    corrupted = [
        ("Table 5 not found", _swap(TABLE5, "for 2002 BB", "for 2003 BB")),
        ("caption does not state basis points", _swap(TABLE5, "in ba sis points", "in percent")),
        ("columns are not", _swap(TABLE5, "= 0.02)", "= 0.03)")),
        ("row N / N dagger not found", _swap(TABLE5, "N / N\u2020 531", "N 531")),
        ("does not fall", _swap(TABLE5, "531 84.3 45.8", "531 45.8 84.3")),
        ("row agresti_coull not found", _swap(TABLE5, "Agresti-Coull (168.03", "Agresti Coull (168.03")),
        ("printed length 291.84", _swap(TABLE5, "281.84", "291.84")),
    ]
    for match, corrupt in corrupted:
        monkeypatch.setattr(papers, "_pages", _pages_of(corrupt))
        with pytest.raises(papers.PaperTableError, match=match):
            papers.read_sr190_table5(Path("fake.pdf"))


def test_case_refuses_a_print_it_does_not_reproduce(monkeypatch, tmp_path):
    """Where the outputs carry no agreement the case checks the print, and refuses a value it does not reproduce (a
    misread or misbound print never reaches the outputs): the count of the series' terms; Table 5's count of defaults
    and N dagger; Engelmann's W_ttc, TTC PD, starting PDs and extremes, and W hat's PD beyond the rounding of its
    entries or with a default share; an engine iteration that did not converge."""
    eng = _engelmann_text()
    cases = [
        ("takes 16 terms to 1e-08 .* the print sums 17",
         {"irw": _irw_text(series=SERIES.replace("16 terms", "17 terms"))}),
        # a Wald lower bound no count of the 531 obligors gives (its length kept consistent)
        ("counts of defaults", {"table5": _swap(TABLE5, "(141.56, 423.41) 281.84", "(141.00, 423.41) 282.41")}),
        ("N dagger \\(3.4\\) at a default correlation of 0.01",
         {"table5": _swap(TABLE5, "531 84.3 45.8", "531 8.43 4.58")}),
        ("W_ttc's entry 3", {"engelmann": _swap(eng, "0.2866, 0.2892", "0.2892, 0.2866")}),  # the sum kept
        ("the TTC PD \\(%\\)", {"engelmann": _swap(eng, "TTC PD is 1.363%", "TTC PD is 1.373%")}),
        ("W_init's PD", {"engelmann": _swap(eng, "PD is 0.980%", "PD is 0.990%")}),
        ("W_init 2's PD", {"engelmann": _swap(eng, "PD\nof 2.491%", "PD\nof 2.481%")}),
        ("minimum of W_init 2's projected PD",
         {"engelmann": _swap(eng, "average PD of 0.889%", "average PD of 0.899%")}),
        ("maximum of W tilde's projected PD", {"engelmann": _swap(eng, "maximum of 2.07%", "maximum of 2.14%")}),
        ("W hat's PD is 1.24620% from its printed entries", {"engelmann": _swap(eng, "PD 1.245%", "PD 1.240%")}),
        ("W hat prints a default share", {"engelmann": _swap(eng, "0.0200, 0.0000)", "0.0150, 0.0050)")}),
    ]
    for match, prints in cases:
        with pytest.raises(papers.PaperTableError, match=match):
            _bake(monkeypatch, tmp_path, **prints)
    real_fit, real_series = ttc.ttc_portfolio, emb.log_series
    monkeypatch.setattr(ttc, "ttc_portfolio", lambda t, o, **kw: {**real_fit(t, o, **kw), "converged": False})
    with pytest.raises(papers.PaperTableError, match="did not reach the TTC portfolio"):
        _bake(monkeypatch, tmp_path)
    monkeypatch.setattr(ttc, "ttc_portfolio", real_fit)
    # the series stops short of the printed accuracy (the engine's own calls, at 1e-14, untouched)
    monkeypatch.setattr(emb, "log_series", lambda p, tol=1e-14, max_terms=2000: {
        **real_series(p, tol=tol, max_terms=max_terms), "converged": tol == 1e-14})
    with pytest.raises(papers.PaperTableError, match="converged: False"):
        _bake(monkeypatch, tmp_path)
