"""The generated results block of docs/governance.md: every figure is read from the governance documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END``; ``write_page`` replaces the block in the page (as the case pages' blocks are) and a test
compares the committed block with a fresh render. The page states the rule's output on the evidence; Contraste approves no model.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

BEGIN = "<!-- governance-results:begin -->"
END = "<!-- governance-results:end -->"
SEVERITIES = ("S1", "S2", "S3", "S4")
STATES = ("open", "action_plan_agreed", "in_progress", "submitted_for_closure", "validated_closed", "overdue", "risk_accepted")
READING_NAMES = {"A": ("literal", "mean"), "B": ("graded", "mean"), "C": ("literal", "maximum"), "D": ("graded", "maximum")}


def block_of(text: str) -> str:
    """The generated block of a page, without its markers and the blank lines around it."""
    return text.replace("\r\n", "\n").split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")


def table(w, head: list[str], rows: list[list[str]], right_from: int = 1) -> None:
    w("| " + " | ".join(head) + " |")
    w("|" + "|".join("---" if i < right_from else "---:" for i in range(len(head))) + "|")
    for r in rows:
        w("| " + " | ".join(str(c) for c in r) + " |")
    w("")


def results_block(inv: dict[str, Any], fnd: dict[str, Any], app: dict[str, Any], reports: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    w = lines.append
    entries = inv["entries"]
    rows = fnd["rows"]
    cases = sorted({e["case_id"] for e in entries})
    n_var = sum(len(e["variants"]) for e in entries)
    w(f"The documents were baked over the committed case documents with `riskvalidation` {inv['provenance']['riskvalidation_version']} as of {inv['as_of']} "
      f"(the newest release heading of the changelog; a convention, never the clock). {len(inv['provenance']['documents_read'])} paths were read, each listed with its "
      "sha256 in the documents.")
    w("")
    w("### The inventory")
    w("")
    w(f"{len(entries)} entries (one per fit) for {len(cases)} built cases, holding {n_var} variant documents and {sum(len(e['components']) for e in entries)} model records. "
      f"{len(inv['edges'])} dependency edges join the entries, in {max(e['graph']['depth'] for e in entries) + 1} generations; every entry also depends on the engine node.")
    w("")
    levels = {k: r["sections"][10]["opinion"]["level"] for k, r in reports.items()}
    tbl = []
    for e in entries:
        mine = [r for r in rows if r["entry_key"] == e["key"]]
        open_by = e["attributes"]["A37"]["value"]
        tb = e["tier_block"]
        tbl.append([f"`{e['key']}`", tb["tier"], tb["materiality"]["m"]["graded"], tb["complexity"]["c"]["mean"], levels[e["key"]], len(e["variants"]), len(mine),
                    *[open_by[s] for s in SEVERITIES], e["schedule"]["next_review"]])
    table(w, ["Entry", "Tier", "M", "C", "Opinion level", "Variants", "Register rows", "Open S1", "Open S2", "Open S3", "Open S4", "Next review"], tbl, 1)
    w("### Tier counts under the four readings")
    w("")
    w("The tier is the matrix of materiality and complexity (06 B.3). Two inputs of the rubric are open, so the tier is shown under four readings and the "
      "adopted one is B (regulatory use graded, complexity the mean rounded half up; decision W15-3). Each cell is the number of entries in Tier 1/2/3/4.")
    w("")
    table(w, ["Reading", "Regulatory use", "Complexity", "Entries in Tier 1/2/3/4"],
          [[rec["reading"], READING_NAMES[rec["reading"]][0], READING_NAMES[rec["reading"]][1], "/".join(str(n) for n in rec["counts"])] for rec in inv["tier_counts"]], 1)
    w("### The dependency edges")
    w("")
    w("A document edge means the downstream package reads the upstream case's committed document, a code edge that it imports the upstream case's code. "
      "A page statement, a shared method or a shared source is a related link and is not listed here.")
    w("")
    by_pair: dict[tuple[str, str], set[str]] = {}
    for ed in inv["edges"]:
        by_pair.setdefault((ed["upstream"], ed["downstream"]), set()).add(ed["kind"])
    table(w, ["Upstream", "Downstream", "Kind"], [[f"`{u}`", f"`{d}`", ", ".join(sorted(k))] for (u, d), k in sorted(by_pair.items())], 2)
    w("### The findings register")
    w("")
    c = fnd["counts"]
    w(f"{c['total']} rows from the {len(inv['entries'])} entries' variant documents ({c['overdue']} overdue). The register enriches the five fields of a finding with its "
      "owner role, deadline, ageing, anchor and workflow state; no case document is rewritten.")
    w("")
    table(w, ["Severity", "ECB F", *STATES], [[s, fnd["conventions"]["severity_scale"]["rows"][i]["ecb_f"], *[sum(1 for r in rows if r["severity"] == s and r["status"] == st) for st in STATES]]
                                                for i, s in enumerate(SEVERITIES)], 2)
    left = sum(int(m) for x in inv["excluded"] if x["variant_id"] for m in re.findall(r"its (\d+) finding rows", x["reason"]["en"]))
    w(f"Finding rows in the variant documents: {c['total'] + left}; in the register: {c['total']}; in the variants no fit could be determined for: {left}.")
    w("")
    held = {r["case_id"] for r in rows}
    none = [cs for cs in cases if cs not in held]
    w("Cases with no finding row in the committed documents: " + (", ".join(none) if none else "none") + ".")
    w("")
    table(w, ["Case", "Rows", "S1", "S2", "S3", "S4", "Overdue"],
          [[x["case_id"], x["total"], *[x["by_severity"][s] for s in SEVERITIES], x["overdue"]] for x in c["by_case"]], 1)
    w("### The model risk appetite")
    w("")
    w("The seven metrics of 06 B.6 with their thresholds. Every limit is a convention (item 30 of the dossier UNVERIFIED list); a metric with no population has no value.")
    w("")
    table(w, ["Metric", "Value", "Numerator", "Denominator", "Light"],
          [[m["name"]["en"], "not evaluated" if m["value"] is None else (f"{m['value']:.4f}".rstrip("0").rstrip(".") if isinstance(m["value"], float) else m["value"]),
            "-" if m["numerator"] is None else m["numerator"], "-" if m["denominator"] is None else m["denominator"], m["light"]] for m in app["metrics"]], 1)
    w("### The reports")
    w("")
    w(f"{len(reports)} validation reports of twelve sections, one per entry. The opinion is the rule's output on the evidence; Contraste approves no model.")
    w("")
    count = {lv: sum(1 for v in levels.values() if v == lv) for lv in (1, 2, 3, 4)}
    table(w, ["Opinion level", "Entries"], [[lv, n] for lv, n in count.items()], 1)
    w("### What the bake leaves out")
    w("")
    planned = [x["case_id"] for x in inv["excluded"] if x["variant_id"] is None and "planned" in x["reason"]["en"]]
    w("Planned cases with no committed document: " + (", ".join(planned) if planned else "none") + ".")
    w("")
    gone = [x for x in inv["excluded"] if x["variant_id"]]
    if gone:
        w("Variants no fit could be determined for (decision W15-15: never assigned by guess), each with the engine's reason:")
        w("")
        for x in gone:
            w(f"- `{x['case_id']}/{x['variant_id']}`: {x['reason']['en']}")
        w("")
    unlisted = [x for x in inv["excluded"] if x["variant_id"] is None and "planned" not in x["reason"]["en"]]
    for x in unlisted:
        w(f"- {x['reason']['en']}")
    if unlisted:
        w("")
    return "\n".join(lines).rstrip("\n") + "\n"


def write_page(path: Path, block: str) -> None:
    """Replace the generated block of the page at ``path`` (the markers must be there)."""
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if BEGIN not in text or END not in text:
        raise ValueError(f"{path}: the page lacks the markers {BEGIN} and {END}")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    path.write_text(f"{head}{BEGIN}\n\n{block.strip(chr(10))}\n\n{END}{tail}", encoding="utf-8", newline="\n")
