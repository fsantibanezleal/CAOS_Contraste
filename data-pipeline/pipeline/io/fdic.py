"""The FDIC BankFind financials reader (contract family ``balance_sheet`` through ``pipeline.io.contract``), shared by C14 and
C16; moved here from ``pipeline/cases/c14/fdic.py`` at the batch 3 integration (U11 sizing R2, as ``io/treasury.py`` was).

One file holds every quarterly call-report row of one bank (amounts in thousands of USD, ratios in percent). The reader is the
dating rule of C14 (SDD section 5): ``up_to`` returns only the reports dated on or before a valuation date, and every function
the bake calls for a valuation date takes that result, never the whole file. The one function that reads a later report is
``realised_nii``, the out-of-sample row, which names its period and refuses a period that does not start after the date.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class MissingField(ValueError):
    """A field the bake needs is not in the report (the FDIC returns null for an item the bank did not report)."""


@dataclass(frozen=True)
class Report:
    """One call report: ``report_date`` ISO, ``values`` the FDIC fields (numbers, or None where not reported)."""

    report_date: str
    values: Mapping[str, Any]

    def get(self, name: str) -> float:
        v = self.values.get(name)
        if v is None:
            raise MissingField(f"{self.report_date}: field {name} is not reported")
        return float(v)

    def sum(self, *names: str) -> float:
        return sum(self.get(n) for n in names)


def iso(repdte: str) -> str:
    s = str(repdte)
    if len(s) != 8 or not s.isdigit():
        raise ValueError(f"REPDTE {repdte!r} is not YYYYMMDD")
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def read_financials(path: str | Path, cert: int) -> list[Report]:
    """Every report of the file, in date order; refuses a file of another bank or a repeated date."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    out: list[Report] = []
    for row in doc["data"]:
        d = row["data"]
        if int(d["CERT"]) != cert:
            raise ValueError(f"{path}: row of CERT {d['CERT']}, expected {cert}")
        out.append(Report(iso(d["REPDTE"]), dict(d)))
    out.sort(key=lambda r: r.report_date)
    dates = [r.report_date for r in out]
    if len(set(dates)) != len(dates):
        raise ValueError(f"{path}: a report date is repeated")
    return out


def up_to(reports: list[Report], valuation_date: str) -> list[Report]:
    """The reports dated on or before the valuation date: nothing later is ever returned (the dating rule)."""
    return [r for r in reports if r.report_date <= valuation_date]


def report_at(reports: list[Report], valuation_date: str) -> Report:
    """The call report of the valuation date itself, chosen among the reports up to it."""
    known = up_to(reports, valuation_date)
    if not known or known[-1].report_date != valuation_date:
        raise ValueError(f"no call report dated {valuation_date} (latest up to it: {known[-1].report_date if known else None})")
    return known[-1]


def realised_nii(reports: list[Report], valuation_date: str, period_start: str, period_end: str) -> float:
    """Net interest income realised in a period that starts after the valuation date: the out-of-sample row only.

    A FDIC income field is year to date; a full calendar year is the report dated the end of that year. A period that is not
    a full calendar year after the valuation date is refused (a part of a year would need a difference of two reports)."""
    if not period_start > valuation_date:
        raise ValueError(f"the realised period {period_start}..{period_end} does not start after the valuation date {valuation_date}")
    year = period_end[:4]
    if period_start != f"{year}-01-01" or period_end != f"{year}-12-31":
        raise ValueError("the realised period must be one full calendar year")
    hit = [r for r in reports if r.report_date == period_end]
    if not hit:
        raise ValueError(f"no call report dated {period_end}")
    return hit[0].get("NIM")
