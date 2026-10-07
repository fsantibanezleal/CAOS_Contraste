"""Readers of the published tables case C05 is built on (CT-201, CT-202).

Both papers are fetched as arXiv PDFs into the device data root (sources ``tasche-2013`` and ``pluto-tasche-2005``,
derived-only) and parsed there; nothing they contain is committed raw. Each reader checks what it read against the
print itself and refuses a table that does not add up, so a different PDF rendering, a changed version or a parsing
slip stops the bake instead of producing quiet nonsense.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

#: the S&P grades of Tasche (2013) Table 2, best first
SP_GRADES = ("AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-", "B+", "B", "B-",
             "CCC-C")
SP_YEARS = (2009, 2010, 2011)
#: the confidence levels of every Pluto-Tasche table
PT_GAMMAS = (0.50, 0.75, 0.90, 0.95, 0.99, 0.999)
#: the rows each Pluto-Tasche table prints (labels normalised: the hat and the spaces removed, lower case)
PT_ROWS: dict[int, tuple[str, ...]] = {
    1: ("pa",), 2: ("pb",), 3: ("pc",), 4: ("pa",), 5: ("pb",), 6: ("pc",),
    7: ("pa", "pb", "pc"), 8: ("pa", "pb", "pc"),
    9: ("centraltendency", "k", "pa,scaled", "pb,scaled", "pc,scaled"),
    10: ("centraltendency", "k", "pa,scaled", "pb,scaled", "pc,scaled"),
    11: ("upperboundforportfoliopd", "k", "pa,scaled", "pb,scaled", "pc,scaled"),
    12: ("upperboundforportfoliopd", "k", "pa,scaled", "pb,scaled", "pc,scaled"),
    13: ("pa", "pb", "pc"), 14: ("pa", "pb", "pc"),
}


class PaperTableError(ValueError):
    """A table read from a paper does not satisfy its own print."""


def _pages(pdf: Path) -> list[str]:
    from pypdf import PdfReader

    logging.getLogger("pypdf").setLevel(logging.ERROR)  # font-encoding notices of the TeX fonts, not errors
    return [page.extract_text() or "" for page in PdfReader(str(pdf)).pages]


def read_tasche_table2(pdf: Path) -> dict[str, Any]:
    """Tasche (2013) Table 2: obligors rated and defaults by grade (best first) for 2009 to 2011, with the printed
    default rates and the All row. Refused unless the grades add up to the All row and every printed rate (two
    decimals) is the counts' ratio."""
    text = next((t for t in _pages(pdf) if "Table 2:" in t and "Rating grade rated defaults DR" in t), None)
    if text is None:
        raise PaperTableError(f"{pdf.name}: Table 2 not found")
    body = text[text.index("Table 2:"):]
    num = r"(\d+)\s+(\d+)\s+(\d+\.\d{2})"
    rows: dict[str, tuple[float, ...]] = {}
    for label in (*SP_GRADES, "All"):
        m = re.search(rf"^{re.escape(label)}\s+{num}\s+{num}\s+{num}\s*$", body, re.M)
        if m is None:
            raise PaperTableError(f"{pdf.name}: Table 2 has no row {label!r}")
        rows[label] = tuple(float(v) for v in m.groups())
    out: dict[str, Any] = {"grades": list(SP_GRADES), "years": {}}
    for k, year in enumerate(SP_YEARS):
        rated = [int(rows[g][3 * k]) for g in SP_GRADES]
        defaults = [int(rows[g][3 * k + 1]) for g in SP_GRADES]
        printed = [rows[g][3 * k + 2] for g in SP_GRADES]
        total_n, total_d, total_dr = int(rows["All"][3 * k]), int(rows["All"][3 * k + 1]), rows["All"][3 * k + 2]
        if sum(rated) != total_n or sum(defaults) != total_d:
            raise PaperTableError(f"{pdf.name}: Table 2 {year} grades sum to {sum(rated)} and {sum(defaults)}, the All "
                                  f"row prints {total_n} and {total_d}")
        for g, n, d, p in zip(SP_GRADES, rated, defaults, printed, strict=True):
            if d > n or round(100.0 * d / n, 2) != p:
                raise PaperTableError(f"{pdf.name}: Table 2 {year} {g}: {d} of {n} is not the printed {p}%")
        if round(100.0 * total_d / total_n, 2) != total_dr:
            raise PaperTableError(f"{pdf.name}: Table 2 {year} All: {total_d} of {total_n} is not the printed {total_dr}%")
        out["years"][year] = {"rated": rated, "defaults": defaults, "default_rate_printed_pct": printed,
                              "all": {"rated": total_n, "defaults": total_d, "default_rate_printed_pct": total_dr}}
    return out


def _norm(label: str) -> str:
    return re.sub(r"\s+", "", label.replace("ˆ", "").replace("^", "")).lower()


def read_pluto_tasche_tables(pdf: Path) -> dict[int, dict[str, Any]]:
    """Pluto and Tasche (2005) Tables 1 to 14: for each table its six confidence levels and the printed rows (bounds and
    targets in percent, K unitless). Refused unless every table has the six levels and exactly the rows it should."""
    text = "\n".join(_pages(pdf))
    out: dict[int, dict[str, Any]] = {}
    for table, labels in PT_ROWS.items():
        m = re.search(rf"Table {table}:", text)
        if m is None:
            raise PaperTableError(f"{pdf.name}: Table {table} not found")
        block = text[m.end(): m.end() + 1500]
        head = re.search(r"^γ\s+50%\s+75%\s+90%\s+95%\s+99%\s+99\.9%\s*$", block, re.M)
        if head is None:
            raise PaperTableError(f"{pdf.name}: Table {table} has no row of the six confidence levels")
        rows: dict[str, list[float]] = {}
        for line in block[head.end():].splitlines():
            line = line.strip()
            if not line:
                continue
            row = re.match(r"^(?P<label>\D.*?)\s+(?P<vals>(?:\d+\.\d+%?\s*){6})$", line)
            if row is None:
                break
            values = [float(v.rstrip("%")) for v in row.group("vals").split()]
            rows[_norm(row.group("label"))] = values
        if tuple(rows) != labels:
            raise PaperTableError(f"{pdf.name}: Table {table} prints rows {list(rows)}, expected {list(labels)}")
        out[table] = {"gammas": list(PT_GAMMAS), "rows": rows,
                      "units": {k: ("unitless" if k == "k" else "percent") for k in rows}}
    return out


def _grade_rows(block: str, n_values: int, pdf: Path, table: int) -> dict[str, list[float]]:
    """The 17 grade rows of a block, each with ``n_values`` numbers (thousands separators allowed)."""
    rows: dict[str, list[float]] = {}
    number = r"(\d[\d,]*(?:\.\d+)?)"
    for g in SP_GRADES:
        m = re.search(rf"^{re.escape(g)}" + rf"\s+{number}" * n_values + r"\s*$", block, re.M)
        if m is None:
            raise PaperTableError(f"{pdf.name}: Table {table} has no row {g!r} with {n_values} values")
        rows[g] = [float(v.replace(",", "")) for v in m.groups()]
    return rows


def read_tasche_results(pdf: Path, table2: dict[str, Any]) -> dict[str, Any]:
    """Tasche (2013) Tables 5 to 9, the paper's results on its Table 2 data: the smoothed 2009 curve (5), the default
    profiles (6), the 2010 and 2011 forecasts of the four case 1 approaches with their p-values (7), the case 3
    forecasts of the PD (8) and the smoothed likelihood ratios (9). Each table's printed inputs are checked against
    ``table2`` (the observed rates and profiles), so a parsing slip cannot pass."""
    text = "\n".join(_pages(pdf))

    def block(table: int, size: int = 2600) -> str:
        m = re.search(rf"Table {table}:", text)
        if m is None:
            raise PaperTableError(f"{pdf.name}: Table {table} not found")
        return text[m.end(): m.end() + size]

    years = table2["years"]

    def rate(y: int, i: int) -> float:
        return 100.0 * years[y]["defaults"][i] / years[y]["rated"][i]

    t5 = _grade_rows(block(5), 2, pdf, 5)
    for i, g in enumerate(SP_GRADES):
        if round(rate(2009, i), 3) != t5[g][0]:
            raise PaperTableError(f"{pdf.name}: Table 5 {g} default rate {t5[g][0]} is not Table 2's {rate(2009, i):.3f}")
    t6 = _grade_rows(block(6), 2, pdf, 6)
    d09 = years[2009]["defaults"]
    for i, g in enumerate(SP_GRADES):
        if round(100.0 * d09[i] / sum(d09), 4) != t6[g][0]:
            raise PaperTableError(f"{pdf.name}: Table 6 {g} empirical profile {t6[g][0]} is not Table 2's")
    b7 = block(7, 3200)
    split = b7.index("2011: Unconditional default rate")
    panels = {2010: b7[:split], 2011: b7[split:]}
    t7: dict[int, Any] = {}
    for y, part in panels.items():
        head = re.search(rf"{y}: Unconditional default rate (\d+\.\d+)", part)
        pv = re.search(r"^P-value\s+Exact\s+(\d+\.\d)\s+(\d+\.\d)\s+(\d+\.\d)\s+(\d+\.\d)\s*$", part, re.M)
        if head is None or pv is None:
            raise PaperTableError(f"{pdf.name}: Table 7 {y} panel lacks its header or its p-values")
        rows = _grade_rows(part, 5, pdf, 7)
        all_rate = 100.0 * years[y]["all"]["defaults"] / years[y]["all"]["rated"]
        # within one unit of the third decimal: the 2011 header prints 0.752 for 44/5847 = 0.7525% (cut, not
        # rounded), while the forecasts below it use the exact rate (they match it to 0.0002 percentage points)
        if abs(all_rate - float(head.group(1))) > 0.001 + 1e-9:
            raise PaperTableError(f"{pdf.name}: Table 7 {y} unconditional rate {head.group(1)} is not Table 2's")
        for i, g in enumerate(SP_GRADES):
            if round(rate(y, i), 4) != rows[g][0]:
                raise PaperTableError(f"{pdf.name}: Table 7 {y} {g} default rate {rows[g][0]} is not Table 2's")
        t7[y] = {"unconditional_pct": float(head.group(1)),
                 "forecast_pct": {a: [rows[g][k + 1] for g in SP_GRADES] for k, a in enumerate(
                     ("invariant_default_profile", "invariant_accuracy_ratio", "scaled_pds", "scaled_likelihood_ratio"))},
                 "p_value_pct": dict(zip(("invariant_default_profile", "invariant_accuracy_ratio", "scaled_pds",
                                          "scaled_likelihood_ratio"), (float(v) for v in pv.groups()), strict=True))}
    b8 = block(8, 1200)
    t8: dict[str, Any] = {}
    for key, label in (("invariant_pd_curve", r"Invariant PDs \(4\.12\)"), ("least_squares", r"Least squares \(4\.14b\)"),
                       ("least_chi2", r"Least \u03c72"), ("invariant_likelihood_ratio", r"Invariant LR \(4\.10\)")):
        m = re.search(rf"^{label}\s+(\d+\.\d+)%\s+(Exact|\d\.\d+|< 10\S+)\s+(\d+\.\d+)%\s+(Exact|\d\.\d+|< 10\S+)\s*$",
                      b8, re.M)
        if m is None:
            raise PaperTableError(f"{pdf.name}: Table 8 has no row {key}")
        t8[key] = {2010: {"forecast_pct": float(m.group(1)), "p_value": m.group(2)},
                   2011: {"forecast_pct": float(m.group(3)), "p_value": m.group(4)}}
    t9 = _grade_rows(block(9), 3, pdf, 9)
    return {
        "table5": {"default_rate_pct": [t5[g][0] for g in SP_GRADES], "smoothed_pd_pct": [t5[g][1] for g in SP_GRADES]},
        "table6": {"empirical_pct": [t6[g][0] for g in SP_GRADES], "implied_pct": [t6[g][1] for g in SP_GRADES]},
        "table7": t7,
        "table8": t8,
        "table9": {y: [t9[g][k] for g in SP_GRADES] for k, y in enumerate(SP_YEARS)},
    }


# ---------------------------------------------------------------------------------------------------------------------
# C22: the published simulation studies the harness reproduces (CT-304)

#: WP14 Tables 5 to 8: the scenario names, the nominal levels and the five years of each scenario
WP14_SCENARIOS = ("I_SC", "I_LC", "DC_SC", "DC_LC", "I_SV", "I_LV", "DV_SV", "DV_LV")
WP14_TYPE_II = ("I_SV", "I_LV", "DV_SV", "DV_LV")
WP14_LEVELS = (0.1, 0.05, 0.025, 0.01, 0.005, 0.001)


def _join_broken_decimals(text: str) -> str:
    """The extraction splits some decimals ("0. 081", "0 .3", "3. 0"): join them back."""
    text = re.sub(r"(\d)\.\s+(\d)", r"\1.\2", text)
    return re.sub(r"(\d)\s+\.(\d)", r"\1.\2", text)


def _section(text: str, start: str, end: str | None, pdf: Path) -> str:
    if start not in text:
        raise PaperTableError(f"{pdf.name}: {start!r} not found")
    body = text[text.index(start) + len(start):]
    if end is not None:
        if end not in body:
            raise PaperTableError(f"{pdf.name}: {end!r} not found after {start!r}")
        body = body[:body.index(end)]
    return body


def read_wp14_simulation(pdf: Path) -> dict[str, Any]:
    """BCBS WP14 Tables 5 to 8: the scenario parameters (factor correlation, asset correlations, forecast and true PDs
    for five years) and the type I and type II errors of the normal and traffic-lights tests at six nominal levels.
    Refused unless every scenario has its 16 parameters, Table 6's forecasts equal Table 5's, every rate lies in
    [0, 1], and the type I and type II tables name exactly the scenarios WP14 lists."""
    text = _join_broken_decimals("\n".join(_pages(pdf)))
    nominal = "Nominal level 0.1 0.05 0.025 0.01 0.005 0.001"
    if text.count(nominal) < 2:
        raise PaperTableError(f"{pdf.name}: the nominal levels of Tables 7 and 8 not found")

    def params(block: str, names: tuple[str, ...], table: int) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        starts = [(m.start(), m.group(1)) for m in re.finditer(r"\b(I_SC|I_LC|DC_SC|DC_LC|I_SV|I_LV|DV_SV|DV_LV)\b", block)]
        for k, (pos, name) in enumerate(starts):
            seg = block[pos + len(name): starts[k + 1][0] if k + 1 < len(starts) else len(block)]
            vals = [float(v) for v in re.findall(r"\d+(?:\.\d+)?", seg)]
            if len(vals) < 16:
                raise PaperTableError(f"{pdf.name}: Table {table} {name} has {len(vals)} numbers, not 16")
            theta, rho, fore, true = vals[0], vals[1:6], vals[6:11], vals[11:16]
            out[name] = {"theta": theta, "rho": rho, "forecast_pct": fore, "true_pct": true}
        if tuple(out) != names:
            raise PaperTableError(f"{pdf.name}: Table {table} lists {list(out)}, not {list(names)}")
        return out

    t5_title = "Parameter settings for type I error simulations"
    t6_title = "Parameter settings for type II error simulations"
    t7_title = "Type I errors (normal = with normal test, traffic = with traffic lights test)"
    t8_title = "Type II errors (normal = with normal test, traffic = with traffic lights test)"
    t5 = params(_section(text, t5_title, "Table 6", pdf).split("(in %)")[-1], WP14_SCENARIOS, 5)
    t6 = params(_section(text, t6_title, "Table 7", pdf).split("(in %)")[-1], WP14_TYPE_II, 6)
    for name in WP14_TYPE_II:
        if t6[name]["forecast_pct"] != t5[name]["forecast_pct"] or t6[name]["rho"] != t5[name]["rho"]:
            raise PaperTableError(f"{pdf.name}: Table 6 {name} forecasts or correlations differ from Table 5")
    for name, sc in t5.items():
        if sc["true_pct"] != sc["forecast_pct"]:
            raise PaperTableError(f"{pdf.name}: Table 5 {name}: a type I scenario's true PDs equal its forecasts")

    def rates(block: str, names: tuple[str, ...], table: int) -> dict[str, dict[str, list[float]]]:
        out: dict[str, dict[str, list[float]]] = {}
        for m in re.finditer(r"\b(I_SC|I_LC|DC_SC|DC_LC|I_SV|I_LV|DV_SV|DV_LV), (normal|traffic)\s+((?:\d\.\d+\s*){6})",
                             block):
            vals = [float(v) for v in m.group(3).split()]
            if any(not 0.0 <= v <= 1.0 for v in vals):
                raise PaperTableError(f"{pdf.name}: Table {table} {m.group(1)} {m.group(2)}: a rate outside [0, 1]")
            out.setdefault(m.group(1), {})[m.group(2)] = vals
        if tuple(out) != names or any(set(v) != {"normal", "traffic"} for v in out.values()):
            raise PaperTableError(f"{pdf.name}: Table {table} rows are {list(out)}, not {list(names)} by both tests")
        return out

    t7 = rates(_section(text, t7_title, "Table 8", pdf), WP14_SCENARIOS, 7)
    t8 = rates(_section(text, t8_title, "Loss given default validation", pdf), WP14_TYPE_II, 8)
    if "Every scenario was investigated with 25,000 simulation runs" not in text.replace("\n", " "):
        raise PaperTableError(f"{pdf.name}: the number of runs (footnote 24) not found")
    return {"levels": list(WP14_LEVELS), "runs": 25_000, "years": 5, "obligors": 1000,
            "scenarios_type_i": t5, "scenarios_type_ii": t6, "table_7_type_i": t7, "table_8_type_ii": t8}


def read_yurdakul_naranjo_table4(pdf: Path) -> dict[str, Any]:
    """Yurdakul and Naranjo (2020) Table 4: the rejection rates of PSI > 0.10, PSI > 0.25 and the chi-square benchmark
    for six pairs of sample sizes and shifts of 0, 1/4 and 1/2 standard deviation (10,000 runs). Refused unless the six
    rows of (m, n) are those the paper lists, every rate lies in [0, 1] and the benchmark's rate without a shift is
    close to its level (the paper: "close to alpha = 0.05")."""
    text = "\n".join(_pages(pdf))
    body = _section(text, "TABLE 4 Power comparison", "TABLE 5", pdf)
    rows = []
    for m in re.finditer(r"^\s*(100|200|400)\s+(100|200|400)\s+((?:[01]\.\d{3}\s+){8}[01]\.\d{3})\s*$", body, re.M):
        rows.append({"m": int(m.group(1)), "n": int(m.group(2)), "rates": [float(v) for v in m.group(3).split()]})
    pairs = [(r["m"], r["n"]) for r in rows]
    if pairs != [(100, 100), (100, 200), (100, 400), (200, 200), (200, 400), (400, 400)]:
        raise PaperTableError(f"{pdf.name}: Table 4 rows are {pairs}")
    for r in rows:
        if not 0.04 <= r["rates"][2] <= 0.09:
            raise PaperTableError(f"{pdf.name}: Table 4 ({r['m']}, {r['n']}): the benchmark without a shift is {r['rates'][2]}")
    if "out of 10 000 runs" not in text.replace("\n", " "):
        raise PaperTableError(f"{pdf.name}: the number of runs not found")
    return {"rows": rows, "runs": 10_000, "bins": 10, "sd": 8.0, "shifts_sd": [0.0, 0.25, 0.5],
            "columns": ["shift 0: PSI > 0.10", "shift 0: PSI > 0.25", "shift 0: chi2", "shift 1/4: PSI > 0.10",
                        "shift 1/4: PSI > 0.25", "shift 1/4: chi2", "shift 1/2: PSI > 0.10", "shift 1/2: PSI > 0.25",
                        "shift 1/2: chi2"]}


# ---------------------------------------------------------------------------------------------------------------------
# C04: the published answers the case recomputes (CT-406). The matrices Israel et al. and Engelmann print are agency
# data reprinted there (S&P's and Moody's; Trueck and Rachev's): read here, used by the case, never written to an
# artifact. Schuermann and Hanson's Table 5 holds the paper's own computations only.

#: Israel, Rosenthal and Wei (2001), section 4: the three one-year matrices in print order, each with the words its
#: print follows, and the generator Q_JLT printed for the first
IRW_MATRICES: dict[str, str] = {
    "S&P 1981-1991": r"their\s+Table\s+3",
    "Moody's 1980-1998": r"we\s+obtain\s+the\s+following\s+transition\s+matrix",
    "S&P 1999": r"we\s+obtain\s+the\s+following\s+annual\s+transition\s+matrix",
}
IRW_Q_JLT = r"their\s+approximate\s+generator\s+is"
#: the sentence, printed with the first matrix, that counts the terms of the series (1) and states their accuracy
#: ("summing just the first 16 terms of the series, we compute that the effect of subsequent terms is less than
#: 10 -8"); the extraction sets "first" with the fi ligature (U+FB01)
IRW_SERIES = (r"summing\s+just\s+the\s+(?:first|\ufb01rst)\s+(\d+)\s+terms\s+of\s+the\s+series,[^.]*?less\s+than\s+"
              r"10\s*-\s*(\d+)")
IRW_STATES = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC", "D")
#: the distances printed after each matrix, in print order: JLT (3), the series with (2), the series with (2')
IRW_METHODS = ("jlt", "diagonal", "weighted")
#: how far a printed row may sum from 1 (a generator's from 0): the rounding the authors note ("the row entries of
#: this example matrix P do not add exactly to 1, presumably due to round-off errors")
IRW_ROW_TOL = 3e-4
#: Engelmann's matrix (11) is printed to four digits; its rows sum to 1 +- 0.0001
ENGELMANN_ROW_TOL = 1e-4

#: Engelmann (2024), section 4: each starting portfolio's sentence (its vector, then its printed PD in percent) and
#: the sentence of the extreme printed for its projection. The extraction renders W-tilde as "fW" and W-hat as
#: "cWinit" (the accent comes out as one glyph before the W).
ENGELMANN_PORTFOLIOS: tuple[tuple[str, str, tuple[str, str] | None], ...] = (
    ("W_init", r"current\s+bank\s+portfolio\s+is\s+Winit\s*=\s*\(([^)]*)\)\.?\s*The\s+portfolio\s+PD\s+is\s+"
     r"(\d+\.\d+)%", None),
    ("W_init 2", r"initial\s+portfolio\s+Winit\s*=\s*\(([^)]*)\)\s*which\s+has\s+an\s+average\s+portfolio\s+PD\s+of\s+"
     r"(\d+\.\d+)%", ("min", r"reaches\s+a\s+minimum\s+average\s+PD\s+of\s+(\d+\.\d+)%")),
    ("W tilde", r"initial\s+portfolio\s+\S?W\s*=\s*\(([^)]*)\)\s*with\s+average\s+portfolio\s+PD\s+(\d+\.\d+)%",
     ("max", r"moves\s+up\s+to\s+a\s+maximum\s+of\s+(\d+\.\d+)%")),
    ("W hat", r"initial\s+portfolio\s+is\s+\S?Winit\s*=\s*\(([^)]*)\)\s*with\s+average\s+portfolio\s+PD\s+"
     r"(\d+\.\d+)%", None),
)

_NUMBER_ROW = re.compile(r"\s*-?\d+\.\d+(?:\s+-?\d+\.\d+)*\s*")


def _paper_text(pdf: Path) -> str:
    """Every page's text, the extraction's split decimals joined ("0 .0963" to "0.0963") and the minus sign (U+2212)
    written "-"."""
    return "\n".join(_pages(pdf)).replace(" .", ".").replace("\u2212", "-")


def _decimals(printed: str) -> int:
    return len(printed.split(".")[1]) if "." in printed else 0


def _number_block(text: str, anchor: str, pdf: Path, what: str, n: int = 8) -> list[list[float]]:
    """The first block of number lines after the pattern ``anchor``, required to be ``n`` rows of ``n`` numbers: the
    print sets each matrix row on its own line, between lines of bracket glyphs that end the block."""
    m = re.search(anchor, text)
    if m is None:
        raise PaperTableError(f"{pdf.name}: {what} not found (no {anchor!r})")
    rows: list[list[float]] = []
    for k, line in enumerate(text[m.end():].splitlines()):
        if _NUMBER_ROW.fullmatch(line):
            rows.append([float(x) for x in line.split()])
        elif rows:
            if line.strip():
                break
        elif k >= 12:  # the print sets a matrix within a few lines of the words it follows
            break
    if len(rows) != n or any(len(r) != n for r in rows):
        raise PaperTableError(f"{pdf.name}: {what} has {len(rows)} rows of {[len(r) for r in rows]} numbers, not {n} "
                              f"of {n}")
    return rows


def _check_stochastic(p: list[list[float]], tol: float, pdf: Path, what: str) -> None:
    """Every entry in [0, 1], every row summing to 1 within ``tol``, default (the last state) absorbing."""
    for i, row in enumerate(p):
        if min(row) < 0.0 or max(row) > 1.0:
            raise PaperTableError(f"{pdf.name}: {what}, row {i + 1} has an entry outside [0, 1]")
        if abs(sum(row) - 1.0) > tol + 1e-9:
            raise PaperTableError(f"{pdf.name}: {what}, row {i + 1} sums to {sum(row):.6f}, not 1 within {tol:g}")
    if p[-1] != [0.0] * (len(p) - 1) + [1.0]:
        raise PaperTableError(f"{pdf.name}: {what}: default (the last state) is not absorbing")


def read_irw_2001(pdf: Path) -> dict[str, Any]:
    """Israel, Rosenthal and Wei (2001), section 4: the three one-year matrices over AAA to default (S&P 1981 to 1991
    as in Jarrow, Lando and Turnbull's Table 3, Moody's 1980 to 1998, S&P 1999), the first matrix's printed four-digit
    generator Q_JLT ("their approximate generator is"), the nine printed L1 distances, read from the "norm[...] = "
    statements: after each matrix, JLT (3), the series with (2), the series with (2'), and the count of the series'
    terms on the first matrix with the accuracy the paper states for it (16 terms, 1e-8). Refused unless the matrices
    are printed in order, every matrix row sums to 1 within 3e-4 with default absorbing, every row of Q_JLT is a
    generator's row (no negative rate, summing to 0 within 3e-4, default's zero), exactly three distances, JLT's
    first, follow each matrix, and the count of terms is printed between the first matrix and the second."""
    text = _paper_text(pdf)
    matrices: dict[str, list[list[float]]] = {}
    starts: list[int] = []
    for name, anchor in IRW_MATRICES.items():
        m = re.search(anchor, text)
        if m is None:
            raise PaperTableError(f"{pdf.name}: the {name} matrix not found (no {anchor!r})")
        starts.append(m.start())
        matrices[name] = _number_block(text, anchor, pdf, f"the {name} matrix")
        _check_stochastic(matrices[name], IRW_ROW_TOL, pdf, f"the {name} matrix")
    if starts != sorted(starts):
        raise PaperTableError(f"{pdf.name}: the matrices are not printed in the order {list(IRW_MATRICES)}")
    q = _number_block(text, IRW_Q_JLT, pdf, "the printed Q_JLT")
    for i, row in enumerate(q):
        rates = [x for j, x in enumerate(row) if j != i]
        if row[i] > 0.0 or min(rates) < 0.0 or abs(sum(row)) > IRW_ROW_TOL + 1e-9:
            raise PaperTableError(f"{pdf.name}: the printed Q_JLT's row {i + 1} is not a generator's row (sum "
                                  f"{sum(row):.6f})")
    if any(q[-1]):
        raise PaperTableError(f"{pdf.name}: the printed Q_JLT's default row is not zero")
    stated = list(re.finditer(r"norm\[([^\]]*)\]\s*=\s*(\d+\.\d+)", text))
    if len(stated) != len(IRW_METHODS) * len(IRW_MATRICES):
        raise PaperTableError(f"{pdf.name}: {len(stated)} printed distances (norm[...] = ...), not nine")
    distances: list[dict[str, Any]] = []
    for k, name in enumerate(IRW_MATRICES):
        end = starts[k + 1] if k + 1 < len(starts) else len(text)
        own = [s for s in stated if starts[k] <= s.start() < end]
        if ["JLT" in s.group(1) for s in own] != [True, False, False]:
            raise PaperTableError(f"{pdf.name}: the {name} matrix is followed by {len(own)} distances, not JLT's "
                                  "then the series' with (2) and with (2')")
        for method, s in zip(IRW_METHODS, own, strict=True):
            distances.append({"matrix": name, "method": method, "printed": float(s.group(2)),
                              "decimals": _decimals(s.group(2))})
    first = next(iter(IRW_MATRICES))
    series = re.search(IRW_SERIES, text[starts[0]:starts[1]])  # the count is the first matrix's
    if series is None:
        raise PaperTableError(f"{pdf.name}: the count of the series' terms on the {first} matrix (\"summing just the "
                              "first ... terms\") not found before the next matrix")
    return {"states": list(IRW_STATES), "matrices": matrices, "q_jlt": q, "distances": distances,
            "series_terms": int(series.group(1)), "series_accuracy": float(f"1e-{series.group(2)}")}


def read_engelmann_2024(pdf: Path) -> dict[str, Any]:
    """Engelmann (2024), section 4: the matrix (11) (Trueck and Rachev 2009, seven grades and default, after "page 3,
    is used"), the origination vector O, the printed TTC portfolio W_ttc and its PD (1.198%), and the four starting
    portfolios with their printed PDs and the extremes printed for their projections: W_init (1.161%), the second
    W_init (2.725%, "reaches a minimum average PD of 0.722%"), W tilde (1.83%, "moves up to a maximum of 2.14%") and W
    hat (1.093%). PDs are in percent as printed, each with its decimals. Refused unless the matrix rows sum to 1 within
    1e-4 with default absorbing, O sums to 1, W_ttc and every portfolio have eight entries summing to 1 within 1e-4,
    the portfolios are printed in that order, and each printed extreme stands between its portfolio's sentence and the
    next portfolio's (a portfolio never takes another one's extreme)."""
    text = _paper_text(pdf)
    t = _number_block(text, r"page\s+3,\s+is\s+used", pdf, "the matrix (11)")
    _check_stochastic(t, ENGELMANN_ROW_TOL, pdf, "the matrix (11)")

    def vector(pattern: str, what: str, tol: float) -> tuple[re.Match[str], list[float], list[int]]:
        m = re.search(pattern, text)
        if m is None:
            raise PaperTableError(f"{pdf.name}: {what} not found")
        parts = [x.strip() for x in m.group(1).split(",")]
        if len(parts) != 8 or not all(re.fullmatch(r"\d+(?:\.\d+)?", x) for x in parts):
            raise PaperTableError(f"{pdf.name}: {what} prints {len(parts)} entries, not eight numbers")
        values = [float(x) for x in parts]
        if abs(sum(values) - 1.0) > tol + 1e-9:
            raise PaperTableError(f"{pdf.name}: {what} sums to {sum(values):.6f}, not 1")
        return m, values, [_decimals(x) for x in parts]

    _, o, _ = vector(r"origination\s+vector\s+O\s*=\s*\(([^)]*)\)", "the origination vector O", 0.0)
    _, w_ttc, w_ttc_dec = vector(r"TTC\s+portfolio\s+Wttc\s*=\s*\(([^)]*)\)", "the TTC portfolio W_ttc",
                                 ENGELMANN_ROW_TOL)
    pd = re.search(r"TTC\s+PD\s+is\s+(\d+\.\d+)%", text)
    if pd is None:
        raise PaperTableError(f"{pdf.name}: the TTC PD not found")
    found = [(name, *vector(pattern, f"the portfolio {name} with its PD", ENGELMANN_ROW_TOL), extreme)
             for name, pattern, extreme in ENGELMANN_PORTFOLIOS]
    starts = [m.start() for _, m, _, _, _ in found]
    if any(a >= b for a, b in zip(starts, starts[1:])):
        raise PaperTableError(f"{pdf.name}: the starting portfolios are not printed in the order "
                              f"{[name for name, _, _ in ENGELMANN_PORTFOLIOS]}")
    portfolios: list[dict[str, Any]] = []
    for k, (name, m, w0, w0_dec, extreme) in enumerate(found):
        entry: dict[str, Any] = {"name": name, "w0": w0, "w0_decimals": w0_dec, "pd0_pct": float(m.group(2)),
                                 "pd0_decimals": _decimals(m.group(2)), "extreme": None}
        if extreme is not None:
            kind, phrase = extreme
            # printed after its portfolio and before the next one (the last portfolio, W hat, prints no extreme)
            end = starts[k + 1] if k + 1 < len(found) else len(text)
            e = re.search(phrase, text[m.end():end])
            if e is None:
                raise PaperTableError(f"{pdf.name}: the {kind}imum of {name}'s projection not found between its "
                                      "portfolio and the next")
            entry["extreme"] = {"kind": kind, "pct": float(e.group(1)), "decimals": _decimals(e.group(1))}
        portfolios.append(entry)
    return {"matrix": t, "origination": o, "w_ttc": w_ttc, "w_ttc_decimals": w_ttc_dec,
            "ttc_pd_pct": float(pd.group(1)), "ttc_pd_decimals": _decimals(pd.group(1)), "portfolios": portfolios}


def read_sr190_table5(pdf: Path) -> dict[str, Any]:
    """Schuermann and Hanson (2004), Table 5: intervals for the 2002 BB PD by the cohort method, in basis points,
    independent (N = 531) and with a default correlation of 1% and 2% (N dagger 84.3 and 45.8): the Wald and
    Agresti-Coull rows as (lower, upper) and length at each correlation, and the bootstrap row of the independent
    column. A number may carry a thousands comma ("1,332.56"). Refused unless the columns are independence, 0.01 and
    0.02, N dagger starts at N and falls, and every printed length is its upper bound less its lower bound within the
    rounding of the three (0.015 basis points)."""
    caption = r"Table\s+5:\s+Confidence\s+intervals\s+for\s+2002\s+BB"
    page = next((t for t in _pages(pdf) if re.search(caption, t)), None)
    if page is None:
        raise PaperTableError(f"{pdf.name}: Table 5 not found")
    cut = re.search(caption, page)
    body, title = page[:cut.start()], re.sub(r"\s+", "", page[cut.start():])  # the extraction splits "ba sis"
    if "inbasispoints" not in title or "bycohortmethod" not in title:
        raise PaperTableError(f"{pdf.name}: Table 5's caption does not state basis points by the cohort method")
    rhos = [float(x) for x in re.findall(r"Dependence\s*\(\s*\u03c1\s*=\s*(\d+\.\d+)\s*\)", body)]
    if "Independence" not in body or rhos != [0.01, 0.02]:
        raise PaperTableError(f"{pdf.name}: Table 5's columns are not independence, 0.01 and 0.02 ({rhos})")
    nline = re.search(r"^N\s*/\s*N\u2020\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s*$", body, re.M)
    if nline is None:
        raise PaperTableError(f"{pdf.name}: Table 5's row N / N dagger not found")
    n = int(nline.group(1))
    n_dagger = [float(x) for x in nline.groups()]
    if not n_dagger[0] > n_dagger[1] > n_dagger[2] > 0:
        raise PaperTableError(f"{pdf.name}: Table 5's N dagger {n_dagger} does not fall with the correlation")
    num = r"(\d{1,3}(?:,\d{3})*\.\d{2})"
    cell = rf"\(\s*{num},\s*{num}\s*\)\s+{num}"
    rows: dict[str, list[list[float]]] = {}
    for key, label, cells in (("wald", r"Standard\s+Wald", 3), ("agresti_coull", r"Agresti-Coull", 3),
                              ("bootstrap", r"Bootstrap", 1)):
        tail = r"(?:\s+N/A){4}" if cells == 1 else ""
        m = re.search(rf"^{label}\s+" + r"\s+".join([cell] * cells) + tail + r"\s*$", body, re.M)
        if m is None:
            raise PaperTableError(f"{pdf.name}: Table 5's row {key} not found with {cells} intervals")
        v = [float(x.replace(",", "")) for x in m.groups()]
        rows[key] = [v[3 * k: 3 * k + 3] for k in range(cells)]
        for lo, hi, length in rows[key]:
            if not 0.0 <= lo <= hi <= 1e4 or abs(hi - lo - length) > 0.015 + 1e-9:
                raise PaperTableError(f"{pdf.name}: Table 5's {key} interval ({lo}, {hi}) does not have the printed "
                                      f"length {length}")
    return {"n": n, "rho": [0.0, *rhos], "n_dagger": n_dagger,
            "n_dagger_decimals": [_decimals(x) for x in nline.groups()], "wald": rows["wald"],
            "agresti_coull": rows["agresti_coull"], "bootstrap": rows["bootstrap"][0], "decimals": 2,
            "unit": "basis points"}
