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
