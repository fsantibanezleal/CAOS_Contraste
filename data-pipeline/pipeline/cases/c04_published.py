"""C04, the published answers: three papers recomputed by riskvalidation beside their prints (U4, CT-406).

The design is docs/design/features/c04-transitions/design.md (the published variant) and contract.md section 3. The
papers are read from the device data root by ``pipeline.io.papers``, each reader checking what it read against the
print and refusing otherwise. They are derived-only: the agency matrices two of them reprint are used here and never
written to the outputs.

- Israel, Rosenthal and Wei (2001), Finding generators for Markov chains via empirical transition matrices, with
  applications to credit ratings, Mathematical Finance 11(2), 245-265, doi:10.1111/1467-9965.00114 (authors'
  version), section 4: the L1 distance of exp(Q) to P for Jarrow, Lando and Turnbull's generator (3) and for the log
  series (1) repaired by the diagonal (2) and weighted (2') adjustments, on three one-year matrices; Theorem 3(c); the
  terms the series (1) takes on the first matrix at the accuracy the paper states ("summing just the first 16 terms
  of the series, we compute that the effect of subsequent terms is less than 10^-8").
- Schuermann and Hanson (2004), Estimating probabilities of default, FRBNY Staff Report 190, Table 5: the Wald (2.2)
  and Agresti-Coull (3.2)-(3.3) intervals for BB in 2002 (531 obligors, cohort method), independent and with a default
  correlation of 1% and 2% through the effective number of obligors N dagger (3.4).
- Engelmann (2024), Spurious default probability projections in credit risk stress testing models, arXiv
  2401.08892v1, section 4: the TTC portfolio of the matrix (11) under the origination O (Theorem 1, equation (10)), and
  four starting portfolios projected by (9) over 50 years under the unstressed matrix.

Every number is riskvalidation 0.4 (``transitions.embedding``, ``transitions.intervals``, ``transitions.ttc``). A
recomputed value agrees with its print when it lies within half a unit of the print's last digit, both ends inclusive
(2.7245 and 2.7255 both agree with 2.725: a print does not say how it was rounded), with 1e-9 for the binary
representation (100 * 0.027245 lands 1.7e-16 beyond the half-way point). Where the contract carries the agreement
(Israel et al.'s nine distances, Table 5's twelve cells) it is reported; where it does not (Table 5's N dagger, the
count of the series' terms, every Engelmann value) the print is checked here and a value that does not agree stops the
bake (``PaperTableError``), so a misread or misbound print never reaches the outputs.

What the prints do not give is stated, never fitted: the first matrix's JLT distance (0.116900) follows from the printed
four-digit Q_JLT, not from (3) on the printed P (dossier 13, finding F-IRW-JLT), so its row does not agree and
``jlt_from_printed_generator`` carries the reproduction; Table 5 does not print its count of defaults, which is the one
count whose Wald lower bound prints as the table's; Engelmann built W hat under a correlation he does not state and
prints the PD of its unrounded entries, so its print is checked within the rounding of the printed four-digit entries
(dossier 13, section 14), not at the printed digits.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np

from riskvalidation.transitions import embedding as emb
from riskvalidation.transitions import ttc
from riskvalidation.transitions.intervals import pd_agresti_coull, pd_wald

from ..io import papers

#: each paper in the data root, at raw/<source id>/<file>, and how a refusal names it
IRW_SOURCE, IRW_PDF = "israel-rosenthal-wei-2001", "israel-rosenthal-wei-2001-wei.pdf"
ENGELMANN_SOURCE, ENGELMANN_PDF = "engelmann-2024", "engelmann-2024-arxiv-2401.08892v1.pdf"
SR190_SOURCE, SR190_PDF = "schuermann-hanson-2004", "schuermann-hanson-2004-sr190.pdf"
SOURCES = (IRW_SOURCE, ENGELMANN_SOURCE, SR190_SOURCE)
IRW_PAPER, ENGELMANN_PAPER = "Israel, Rosenthal and Wei (2001)", "Engelmann (2024)"
SR190_PAPER = "Schuermann and Hanson (2004), Table 5"

#: Engelmann's figures project each portfolio "over 50 years using T without stress"
YEARS = 50
#: Schuermann and Hanson's intervals are at 95% (section 3.1: "the Wald 95% confidence interval")
LEVEL = 0.95
#: the matrix Jarrow et al.'s Table 3 prints, the one whose Q_JLT and log series Israel et al. print
FIRST_MATRIX = next(iter(papers.IRW_MATRICES))
#: the one printed distance equation (3) does not give from the printed P (F-IRW-JLT): 0.116477 against the printed
#: 0.116900, which the printed Q_JLT gives to the printed six digits; its row reports the disagreement
IRW_NOT_FROM_P = (FIRST_MATRIX, "jlt")
#: starting portfolios whose printed PD is that of entries more precise than the printed ones, checked within the
#: rounding of the printed entries instead of at the printed digits, and why
ENTRY_ROUNDING = {
    "W hat": {
        "en": "built by stressing the matrix with z = 1 and propagating W_ttc one year, under a correlation the paper "
              "does not state; its printed four-digit entries give 1.0945% against the printed 1.093%, 0.0015 "
              "percentage points apart, within the 0.0021 that their rounding and the PD's allow",
        "es": "construido estresando la matriz con z = 1 y propagando W_ttc un año, con una correlación que el "
              "artículo no declara; sus entradas impresas de cuatro dígitos dan 1,0945% frente al 1,093% impreso, a "
              "0,0015 puntos porcentuales, dentro de los 0,0021 que permiten su redondeo y el de la PD",
    },
}


def prints_as(value: float, printed: float, decimals: int) -> bool:
    """Whether ``value`` lies within half a unit of the last printed digit of ``printed`` (``decimals`` digits), both
    ends inclusive, with 1e-9 for the binary representation: how a recomputed number agrees with its print, the engine
    test's rule. 2.7245 and 2.7255 both agree with 2.725 (rounding half up would print the second as 2.726, but a print
    does not say how it was rounded); 2.7244 does not."""
    return bool(abs(float(value) - float(printed)) <= 0.5 * 10.0 ** -decimals + 1e-9)


def _scaled(printed: float, exponent: int) -> float:
    """A printed number times 10**exponent, as the float nearest the decimal it prints (1.198% is 0.01198), scaled in
    decimal arithmetic so that any float a reader returns scales exactly (1e-05 percent is 1e-07)."""
    return float(Decimal(repr(float(printed))).scaleb(exponent))


def _check(paper: str, what: str, value: float, printed: float, decimals: int) -> None:
    """Stop the bake unless ``value`` agrees with its print: where the outputs carry no agreement, a value that does not
    print as the paper is a misread or misbound print, never published."""
    if not prints_as(value, printed, decimals):
        raise papers.PaperTableError(f"{paper}: {what} is {value:.{decimals + 3}f} recomputed, which does not print as "
                                     f"the printed {printed:.{decimals}f}")


def _irw(read: dict[str, Any]) -> dict[str, Any]:
    """Israel et al.'s nine distances recomputed from the printed matrices by equations (3), (1) with (2), and (1) with
    (2'); the first matrix's distance from its printed Q_JLT; Theorem 3(c) for each matrix (a move reachable but never
    observed: no exact generator); the terms Theorem 1's series takes on the first matrix, summed until a term's
    largest entry falls below the accuracy the paper states (1e-8), which must be the count it prints (16)."""
    mats = {name: np.asarray(p, dtype=float) for name, p in read["matrices"].items()}
    rows = []
    for d in read["distances"]:
        value = float(emb.generator(mats[d["matrix"]], method=d["method"])["l1_distance"])
        rows.append({"matrix": d["matrix"], "method": d["method"], "printed": float(d["printed"]),
                     "recomputed": value, "agrees": prints_as(value, d["printed"], d["decimals"])})
    first = mats[FIRST_MATRIX]
    series = emb.log_series(first, tol=read["series_accuracy"])
    if not series["converged"] or series["terms"] != read["series_terms"]:
        raise papers.PaperTableError(f"{IRW_PAPER}: the series (1) on the {FIRST_MATRIX} matrix takes "
                                     f"{series['terms']} terms to {read['series_accuracy']:g} (converged: "
                                     f"{series['converged']}), the print sums {read['series_terms']}")
    return {
        "rows": rows,
        "jlt_from_printed_generator": float(emb.l1_distance(first, np.asarray(read["q_jlt"], dtype=float))),
        "theorem3_c": [bool(emb.embedding_diagnostics(p)["theorem3_c"]) for p in mats.values()],
        "series_terms": int(series["terms"]),
    }


def _sr190(read: dict[str, Any]) -> dict[str, Any]:
    """Table 5's twelve analytical bounds and lengths recomputed at the count of defaults the print implies; bounds as
    fractions, compared with the print in basis points. N dagger (3.4) at each correlation must print as the table's
    row N / N dagger."""
    n, dec = int(read["n"]), int(read["decimals"])
    printed_lower = read["wald"][0][0]
    # Table 5 does not print the count of defaults: it is the count whose independent Wald lower bound prints as the
    # table's, and it must be the only one
    lowers = pd_wald(np.arange(n + 1), n, level=LEVEL)["lower"]
    found = [d for d in range(n + 1) if prints_as(1e4 * lowers[d], printed_lower, dec)]
    if len(found) != 1:
        raise papers.PaperTableError(f"{SR190_PAPER}: {len(found)} counts of defaults out of {n} give the printed Wald "
                                     f"lower bound of {printed_lower} bp ({found}), not one")
    d = found[0]
    rows = []
    for key, interval in (("wald", pd_wald), ("agresti_coull", pd_agresti_coull)):
        for rho, printed in zip(read["rho"], read[key], strict=True):
            r = interval(d, n, level=LEVEL, rho=rho)
            recomputed = [float(r["lower"]), float(r["upper"]), float(r["length"])]
            rows.append({"rho": float(rho), "interval": key, "printed": [_scaled(x, -4) for x in printed],
                         "recomputed": recomputed,
                         "agrees": all(prints_as(1e4 * v, p, dec) for v, p in zip(recomputed, printed, strict=True))})
    n_dagger: dict[str, list[Any]] = {"printed": [], "recomputed": [], "decimals": []}
    for rho, printed, n_dec in zip(read["rho"], read["n_dagger"], read["n_dagger_decimals"], strict=True):
        value = float(pd_wald(d, n, level=LEVEL, rho=rho)["n_effective"])
        _check(SR190_PAPER, f"N dagger (3.4) at a default correlation of {rho:g}", value, printed, n_dec)
        n_dagger["printed"].append(float(printed))
        n_dagger["recomputed"].append(value)
        n_dagger["decimals"].append(int(n_dec))
    return {"defaults": d, "n": n, "rows": rows, "n_dagger": n_dagger}


def _entry_rounding(t: np.ndarray, decimals: list[int], pd_decimals: int) -> float:
    """How far, in percentage points, the PD of a portfolio printed with ``decimals`` digits per entry may lie from a
    printed PD (``pd_decimals`` digits) of the unrounded portfolio: half a unit of each performing entry's last digit
    times that grade's one-year default rate, plus half a unit of the PD's last digit. The default share counts for
    nothing, since (9) writes the defaulted balance off and re-originates it: a propagated portfolio holds none."""
    entries = sum(0.5 * 10.0 ** -dec * float(rate) for dec, rate in zip(decimals[:-1], t[:-1, -1], strict=True))
    return 100.0 * entries + 0.5 * 10.0 ** -pd_decimals


def _engelmann(read: dict[str, Any]) -> dict[str, Any]:
    """Section 4 recomputed under the matrix (11) as printed, the balance held at one (the paper's step 5, the
    engine's convention): the TTC portfolio and its PD, and each starting portfolio's PD, its projected PD by year and
    the extreme the paper prints for that path. PDs are fractions. Every printed value must agree with its
    recomputation (W hat's PD within the rounding of its entries, ``ENTRY_ROUNDING``)."""
    t = np.asarray(read["matrix"], dtype=float)
    o = read["origination"]
    fit = ttc.ttc_portfolio(t, o)
    if not fit["converged"]:
        raise papers.PaperTableError(f"{ENGELMANN_PAPER}: iterating (9) did not reach the TTC portfolio (10) in "
                                     f"{fit['iterations']} steps")
    for k, (value, printed, dec) in enumerate(zip(fit["portfolio"], read["w_ttc"], read["w_ttc_decimals"],
                                                  strict=True)):
        _check(ENGELMANN_PAPER, f"W_ttc's entry {k + 1}", float(value), printed, dec)
    _check(ENGELMANN_PAPER, "the TTC PD (%)", 100.0 * fit["default_rate"], read["ttc_pd_pct"], read["ttc_pd_decimals"])
    portfolios = []
    for p in read["portfolios"]:
        name = p["name"]
        path = ttc.project(t, p["w0"], o, YEARS)["default_rate"]
        pd0 = 100.0 * float(path[0])
        check, note = "printed digits", None
        if name in ENTRY_ROUNDING:
            check, note = "entry rounding", ENTRY_ROUNDING[name]
            if p["w0"][-1] != 0.0:
                raise papers.PaperTableError(f"{ENGELMANN_PAPER}: {name} prints a default share of {p['w0'][-1]}, "
                                             "which a portfolio propagated by (9) does not hold")
            band = _entry_rounding(t, p["w0_decimals"], p["pd0_decimals"])
            if abs(pd0 - p["pd0_pct"]) > band + 1e-9:
                raise papers.PaperTableError(f"{ENGELMANN_PAPER}: {name}'s PD is {pd0:.5f}% from its printed entries, "
                                             f"beyond their rounding ({band:.5f} percentage points) of the printed "
                                             f"{p['pd0_pct']}%")
        else:
            _check(ENGELMANN_PAPER, f"{name}'s PD (%)", pd0, p["pd0_pct"], p["pd0_decimals"])
        ext = p["extreme"]
        extreme = None
        if ext is not None:
            value = float(path.min() if ext["kind"] == "min" else path.max())
            _check(ENGELMANN_PAPER, f"the {ext['kind']}imum of {name}'s projected PD (%)", 100.0 * value, ext["pct"],
                   ext["decimals"])
            extreme = {"kind": ext["kind"], "printed": _scaled(ext["pct"], -2), "recomputed": value,
                       "decimals": int(ext["decimals"]) + 2}
        portfolios.append({"name": name, "w0": [float(x) for x in p["w0"]],
                           "pd0": {"printed": _scaled(p["pd0_pct"], -2), "recomputed": float(path[0]),
                                   "decimals": int(p["pd0_decimals"]) + 2, "check": check, "note": note},
                           "extreme": extreme, "pd_path": [float(x) for x in path]})
    # every print above agrees with its recomputation (the bake stops otherwise): "decimals" is the print's precision
    # as a fraction (1.198% is 0.01198, five decimals), "check" how the agreement was judged
    return {
        "w_ttc": {"printed": [float(x) for x in read["w_ttc"]], "recomputed": [float(x) for x in fit["portfolio"]],
                  "decimals": [int(x) for x in read["w_ttc_decimals"]]},
        "ttc_pd": {"printed": _scaled(read["ttc_pd_pct"], -2), "recomputed": float(fit["default_rate"]),
                   "decimals": int(read["ttc_pd_decimals"]) + 2},
        "portfolios": portfolios,
        "row_sum_deviation": float(fit["row_sum_deviation"]),
    }


def published_outputs(data_root: Path) -> dict[str, Any]:
    """The published variant's outputs (contract section 3) from the three papers under ``<data_root>/raw``; no matrix
    a paper prints enters them."""
    raw = Path(data_root) / "raw"
    return {
        "kind": "published",
        "irw": _irw(papers.read_irw_2001(raw / IRW_SOURCE / IRW_PDF)),
        "sr190": _sr190(papers.read_sr190_table5(raw / SR190_SOURCE / SR190_PDF)),
        "engelmann": _engelmann(papers.read_engelmann_2024(raw / ENGELMANN_SOURCE / ENGELMANN_PDF)),
    }
