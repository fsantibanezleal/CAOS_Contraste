"""The ECB section list of ``run_catalogue`` covers every group of statistic sections and qualitative tools of the instructions.

    python -m pytest manuscripts/engines-and-test-catalogues/experiments/test_run_catalogue.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_catalogue as rc  # noqa: E402


def test_every_qualitative_tool_section_of_the_instructions_has_a_row():
    rows = {r["section"] for r in rc.ecb_coverage()["rows"]}
    assert {"2.5.2", "2.6.4", "2.9.2", "2.9.5"} <= rows


def test_sections_are_unique_and_in_order():
    secs = [r["section"] for r in rc.ecb_coverage()["rows"]]
    assert len(secs) == len(set(secs))
    key = lambda s: [int(x) for x in s.split(".")]
    assert secs == sorted(secs, key=key)


def test_five_statistics_are_implemented_as_specified_and_the_counts_add_up():
    c = rc.ecb_coverage()
    assert c["implemented"] == 5 and c["implemented"] + c["related_only"] + c["absent"] == c["sections"] == 17
