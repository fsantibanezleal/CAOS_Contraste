"""Contraste's offline pipeline (ADR-0057): the scripts that turn public data and known-truth generators into the
committed artifacts the web replays. Invoked by path (`python data-pipeline/run.py`), never installed; the
validation tests and regulatory calculators come from the engine package `riskvalidation`.
"""

from pathlib import Path

# VERSION at the repository root is the only place the version is written (T4); every manifest records it.
__version__ = (Path(__file__).resolve().parents[2] / "VERSION").read_text(encoding="utf-8").strip()
