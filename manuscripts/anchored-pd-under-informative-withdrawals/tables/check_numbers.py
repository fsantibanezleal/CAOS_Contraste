"""Checks the number macros of the manuscript: every ``\\nv{key}`` of the sources is defined in ``numbers.json``, and writes
the table of the numbers the prose quotes (key, text, section file and source) to ``numbers-used.csv``.

Run from the repository root after ``make_tables.py``::

    E:/_venvs/contraste-u16-i/Scripts/python.exe manuscripts/anchored-pd-under-informative-withdrawals/tables/check_numbers.py

Exit code 0 when every key is defined, 1 otherwise (an undefined key is silently empty in LaTeX).
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
MS = HERE.parent
NUM = re.compile(r"\\nv\{([^}]+)\}")


def main() -> int:
    numbers = json.loads((HERE / "numbers.json").read_text(encoding="utf-8"))
    files = sorted((MS / "sections").glob("*.tex")) + [MS / "main.tex"] + sorted(HERE.glob("tab-*.tex"))
    used: dict[str, set[str]] = {}
    missing: list[tuple[str, str]] = []
    for f in files:
        text = re.sub(r"(?<!\\)%.*", "", f.read_text(encoding="utf-8"))
        for m in NUM.finditer(text):
            key = m.group(1)
            used.setdefault(key, set()).add(f.name)
            if key not in numbers:
                missing.append((f.name, key))
    with (HERE / "numbers-used.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "text", "where", "source"])
        for k in sorted(used):
            if k in numbers:
                w.writerow([k, numbers[k]["text"], ";".join(sorted(used[k])), numbers[k]["source"]])
    for f, k in missing:
        print(f"undefined number key {k!r} in {f}")
    print(f"{len(used)} keys used, {len(numbers)} defined, {len(missing)} undefined")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
