"""The date each acceptance criterion this paper reproduces first entered the design document, read once from git.

The tables read the stored result, so a reader without the repository's history (an archive, a shallow clone) can still
rebuild them; this script needs the full history of ``docs/design/SDD.md``.

    python manuscripts/provisions-reconciliation-identities/experiments/sdd_dates.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
OUT = HERE / "sdd_dates.json"
CRITERIA = ("reconciliation identities close within 1e-6",)


def first_entry(criterion: str) -> dict[str, str]:
    """The first commit of ``docs/design/SDD.md`` whose diff adds or removes the criterion's text, with its date."""
    out = subprocess.run(["git", "-C", str(ROOT), "log", "--reverse", "--format=%h %ad", "--date=format:%Y-%m-%d", f"-S{criterion}",
                          "--", "docs/design/SDD.md"], capture_output=True, text=True, check=True).stdout.split("\n")
    first = next((line for line in out if line.strip()), "")
    if not first:
        raise SystemExit(f"criterion not found in the history of the design document: {criterion}")
    commit, date = first.split()
    return {"commit": commit, "date": date}


def main() -> None:
    result = {"source": "git log -S on docs/design/SDD.md, the first commit that holds the criterion's text",
              "criteria": {c: first_entry(c) for c in CRITERIA}}
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result["criteria"]))


if __name__ == "__main__":
    main()
