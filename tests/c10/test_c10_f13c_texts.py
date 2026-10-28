"""U16-F13c (R5 batch c13 N5, C10): the reference of the method of moments writes the second moment as a superscript, "E[L²]", never
the caret notation "E[L^2]" in reader text. Tested on the producer's constant and source, never by re-baking."""
from __future__ import annotations

from pathlib import Path

from pipeline.cases.c10 import documents

SOURCE = Path(documents.__file__).read_text(encoding="utf-8")


def test_the_moments_reference_writes_the_second_moment_as_a_superscript():
    assert documents.MOMENTS_REFERENCE == "dossier 04 C.4 (E[L²] = joint default probability)"


def test_no_reader_text_of_the_producer_writes_a_caret_power():
    assert "^2" not in SOURCE
