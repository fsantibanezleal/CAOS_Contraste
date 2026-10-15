"""The generated blocks of ``docs/cases/C11.md``: results per window, the exceedance matrix, the selection of the hyperparameters, the
raw files read and the hash of each committed document (CT-615). Everything is read from the committed documents and the
evidence files of ``docs/design/features/c11``; the test compares the page's blocks with ``blocks``, so the page cannot drift.

    python data-pipeline/pipeline/cases/c11/page.py
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MARK_START = "<!-- c11-results:start -->"
MARK_END = "<!-- c11-results:end -->"
WINDOW_ORDER = ("calm-2004-06", "equity-2007-09", "fx-2008", "equity-2020", "rates-2022", "mixed-2023")
NEGATION = re.compile(r"\b(not|no|never|without|derived-only|withheld|only)\b", re.IGNORECASE)


def claim_findings(text: str) -> list[str]:
    """A page that says it publishes French returns must say they are derived-only; a page that does not name the sources or the
    Z2 null assumption is a finding."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        if line.startswith("|"):
            continue                     # table rows describe files and series, not a claim
        if "french" in line.lower() and ("return" in line.lower() or "raw" in line.lower()) and not NEGATION.search(line):
            out.append(f"line {n}: names French returns without saying they are derived-only or withheld: {line.strip()[:80]}")
    low = text.lower()
    for need in ("treasury", "h.10", "tail-consistent", "derived-only"):
        if need not in low:
            out.append(f"the page does not mention {need!r}")
    return out


def _docs(derived: Path) -> dict[str, dict]:
    return {w: json.loads((derived / "C11" / f"{w}.json").read_text(encoding="utf-8")) for w in WINDOW_ORDER}


def _fmt(x, f=".3f") -> str:
    return "n/a" if x is None else format(x, f)


def results_table(docs: dict[str, dict]) -> str:
    head = ("| Window | Forecast days | Portfolio | Models passing every gate | Champion at 99% (average FZ0) | Champion at 97.5% (average FZ0) | "
            "Models in the 90% set at 97.5% |\n|---|---|---|---|---|---|---|")
    rows = []
    for w, d in docs.items():
        o = d["outputs"]
        fz = {(m["model_id"], lv["alpha"]): lv["fz0_mean"] for m in o["models"] for lv in m["by_level"]}
        ch = {c["alpha"]: c for c in o["comparison"]["champions"]}
        cell = lambda a: "none" if ch[a]["model_id"] is None else f"{ch[a]['model_id']} ({_fmt(fz[(ch[a]['model_id'], a)])})"   # noqa: E731
        mcs = next((s["n_in_set"] for s in o["comparison"]["mcs"] if s["alpha"] == 0.025), None)
        rows.append(f"| {w} | {o['window']['n_forecast_days']} | {o['window']['asset_class']} | "
                    f"{sum(m['eligible'] for m in o['models'])} of {len(o['models'])} | {cell(0.01)} | {cell(0.025)} | {'n/a' if mcs is None else mcs} |")
    return "\n".join([head, *rows])


def exceedance_matrix(docs: dict[str, dict]) -> str:
    ids = [m["model_id"] for m in next(iter(docs.values()))["outputs"]["models"]]
    head = "| Model | " + " | ".join(docs) + " |\n|---|" + "---|" * len(docs)
    exp = ["expected at 99%"] + [f"{0.01 * d['outputs']['window']['n_forecast_days']:.1f}" for d in docs.values()]
    rows = ["| " + " | ".join(exp) + " |"]
    for mid in ids:
        cells = []
        for d in docs.values():
            m = next(x for x in d["outputs"]["models"] if x["model_id"] == mid)
            lv = next(x for x in m["by_level"] if x["alpha"] == 0.01)
            cells.append(f"{lv['n_exceedances']}{'' if m['eligible'] else ' x'}")
        rows.append(f"| {mid} | " + " | ".join(cells) + " |")
    return "\n".join([head, *rows]) + "\n\nA trailing `x` marks a model that fails an eligibility gate in that window."


def selection_table(evidence: Path) -> str:
    rec = json.loads((evidence / "hyperparameter-selection.json").read_text(encoding="utf-8"))
    rows = ["| Hyperparameter | Model scored | Candidates (summed average FZ0, lower is better) | Selected |", "|---|---|---|---|"]
    for name, g in rec["grid"].items():
        cands = ", ".join(f"{c['value']}: {c['score']:.4f}" for c in g["candidates"])
        rows.append(f"| `{name}` | {g['model']} | {cands} | {rec['selected'][name]} |")
    return "\n".join(rows)


def inputs_table(evidence: Path) -> str:
    rec = json.loads((evidence / "inputs.json").read_text(encoding="utf-8"))
    rows = ["| Series | Unit | First | Last | Observed days | Missing days | Raw files | Total bytes |", "|---|---|---|---|---|---|---|---|"]
    for sid, s in rec["series"].items():
        rows.append(f"| {sid} | {s['unit']} | {s['first']} | {s['last']} | {s['n_observed']:,} | {s['n_missing']:,} | {len(s['files'])} | "
                    f"{sum(f['bytes'] for f in s['files']):,} |")
    rows += ["", "| Raw file | URL | Bytes | SHA-256 | Retrieved |", "|---|---|---|---|---|"]
    for sid, s in rec["series"].items():
        for f in s["files"] if len(s["files"]) <= 3 else [s["files"][0], s["files"][-1]]:
            rows.append(f"| {f['name']} | {f['url']} | {f['bytes']:,} | `{f['sha256']}` | {f['retrieved']} |")
        if len(s["files"]) > 3:
            rows.append(f"| ({len(s['files']) - 2} further yearly files of {sid}) | same pattern per year | | listed in the document provenance | |")
    return "\n".join(rows)


def hash_table(derived: Path) -> str:
    rows = ["| Document | Bytes | SHA-256 |", "|---|---|---|"]
    for p in sorted((derived / "C11").glob("*.json")):
        b = p.read_bytes()
        rows.append(f"| `data/derived/C11/{p.name}` | {len(b):,} | `{hashlib.sha256(b).hexdigest()}` |")
    return "\n".join(rows)


def blocks(derived: Path, evidence: Path) -> str:
    docs = _docs(derived)
    return "\n\n".join([
        "### Results per window\n\n" + results_table(docs),
        "### Exceedances of the 99 percent VaR per model and window\n\n" + exceedance_matrix(docs),
        "### The hyperparameters, fixed on 1995-01-01 to 2003-12-31\n\n" + selection_table(evidence),
        "### The raw files read\n\n" + inputs_table(evidence),
        "### The committed documents\n\n" + hash_table(derived)]) + "\n"


def update(page: Path, derived: Path, evidence: Path) -> None:
    text = page.read_text(encoding="utf-8")
    pre, rest = text.split(MARK_START, 1)
    _, post = rest.split(MARK_END, 1)
    page.write_text(f"{pre}{MARK_START}\n{blocks(derived, evidence)}{MARK_END}{post}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    update(ROOT / "docs" / "cases" / "C11.md", ROOT / "data" / "derived", ROOT / "docs" / "design" / "features" / "c11")
    print("updated docs/cases/C11.md")
