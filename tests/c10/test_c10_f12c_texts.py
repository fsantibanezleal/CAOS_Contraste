"""U16-F12c (R4 batches c12 n7 and m-N3, c13 n5 and n6, C10): the producer's English texts write a percent as the shell does, with a
no-break space before the sign ("99.9 %", "1.77 %", "95 % interval"), beside the view's own; the rung with no Student-t twist says it
does not run. Tested on the producer's functions, constants and source, never by re-baking."""
from __future__ import annotations

import re
from pathlib import Path

from pipeline.cases.c10 import documents
from pipeline.core.text import NBSP

SOURCE = Path(documents.__file__).read_text(encoding="utf-8")


def test_pct_writes_the_shell_form_in_english():
    assert documents.pct(0.0177) == f"1.77{NBSP}%"
    assert documents.pct_es(0.0177) == f"1,77{NBSP}%"


def test_the_size_power_definition_writes_the_interval_with_its_space():
    assert f"95{NBSP}% interval" in documents.SIZE_POWER_DEFINITION["en"]
    assert "95%" not in documents.SIZE_POWER_DEFINITION["en"]


def test_no_english_text_of_the_producer_joins_a_percent_to_its_number():
    # a digit or a format field closed right before the sign ("99.9%", "{x:.1%}") is the English form without the space
    bad = [m.group(0) for m in re.finditer(r"\d%|:\.\d%\}|\}%", SOURCE)]
    assert bad == [], bad


def test_the_rung_with_no_twist_says_it_does_not_run():
    assert "not-evaluated row" not in SOURCE
    assert "no Student-t twist is specified, so the rung does not run" in SOURCE
