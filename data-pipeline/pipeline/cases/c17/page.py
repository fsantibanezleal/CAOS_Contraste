"""The result tables of ``docs/cases/C17.md``, generated from the committed documents (CT-1715), and the claims check.

``python -m pipeline.cases.c17.page`` (run from ``data-pipeline``) rewrites the block between the two markers of the case page from
``data/derived/C17``; the test compares the page's block with ``results_block`` so the page cannot drift from the documents.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import params as P
from .documents import S3_NAME, S3_RUNGS, s3_counts, s3_verdict

MARK_START = "<!-- c17-results:start -->"
MARK_END = "<!-- c17-results:end -->"
NEGATION = re.compile(r"\b(not|no|never|without|synthetic|invented|neither|nor)\b", re.IGNORECASE)
REAL = re.compile(r"\breal\b.*\b(banks?|losses|portfolios?|institutions?)\b|\b(banks?|losses)\b.*\breal\b", re.IGNORECASE)


def claim_findings(text: str) -> list[str]:
    """A line that calls the generated bank or losses real must also deny it; a page that never says synthetic, or never names the
    BCBS loss data collection exercise the calibration follows, is a finding."""
    out = []
    for n, line in enumerate(text.splitlines(), start=1):
        if REAL.search(line) and not NEGATION.search(line):
            out.append(f"line {n}: calls the generated bank or losses real without denying it: {line.strip()[:80]}")
    low = text.lower()
    if "synthetic" not in low:
        out.append("the page does not say the data are synthetic")
    if "ldce" not in low:
        out.append("the page does not name the BCBS loss data collection exercise")
    return out


def _docs(derived: Path) -> list[dict]:
    manifest = json.loads((derived / "manifests" / "C17.json").read_text(encoding="utf-8"))
    return [json.loads((derived / a["path"]).read_text(encoding="utf-8")) for a in manifest["artifacts"] if a["role"] == "variant"]


def _models(derived: Path) -> dict:
    return json.loads((derived / "C17" / "models-generator.json").read_text(encoding="utf-8"))


def _m(x: float) -> str:
    return f"{x / 1e6:,.1f}"


def _s3_block(derived: Path) -> str:
    """S-3 of the method tiers plan: the robust rungs beside the splice LDA, and the verdict on the hypothesis written before the bake."""
    head = ("| Tail index | Years | Threshold (EUR) | Splice LDA | Mean-adjusted SLA, GPD by likelihood | Cramer-von Mises GPD | "
            "Optimally bias-robust GPD | Cramer-von Mises lognormal (control) |")
    rows = [head, "|" + "---|" * 8]

    def cell(s: dict | None, n: int) -> str:
        if s is None:
            return "none"
        r = s["ratio_to_truth"]
        defined = "" if s["n_defined"] == n else f", n={s['n_defined']}"
        return f"{r['median']:.2f} ({s['iqr_over_truth']:.2f}{defined})"

    caps = []
    for doc in _docs(derived):
        o = doc["outputs"]
        for c in o["cells"]:
            cap = c["capital"]
            n = c["replications"]["n_replications"]
            caps.append({"lda_splice": cap["lda_splice"], **{k: cap[k]["summary"] for k, _ in S3_RUNGS}})
            rows.append(f"| {o['tail_index']:g} | {c['years']} | {c['collection_threshold_eur']:,} | {cell(cap['lda_splice'], n)} | "
                        + " | ".join(cell(cap[k]["summary"], n) for k, _ in S3_RUNGS) + " |")
    lines = []
    for key, mid in S3_RUNGS[1:3]:
        n, sp, bi = s3_counts(caps, key)
        lines.append(f"- {S3_NAME[mid]['en']}: smaller spread than the splice LDA in {sp} of {n} cells, smaller bias in {bi} of {n}: "
                     f"hypothesis **{s3_verdict(n, sp, bi)}**.")
    h = P.S3_HYPOTHESIS
    return ("### S-3, the robust severity rungs\n\n" + "\n".join(rows) + "\n\n"
            "Each cell is the median ratio of the 99.9 percent capital to the true quantile and, in brackets, the interquartile range of that ratio; "
            "n is the number of histories with a capital when it is below the number of histories.\n\n"
            f"Hypothesis, written before the bake: {h['statement']['en']}\n\n" + "\n".join(lines) + "\n")


def results_block(derived: Path) -> str:
    models = _models(derived)
    head1 = "| Tail index | Frequency (losses a year from EUR 10,000) | Scale (EUR) | True 99.9 percent quantile (EUR m) | True mean (EUR m) | LDCE fit, largest log error |"
    rows1 = [head1, "|" + "---|" * 6]
    for doc in _docs(derived):
        o = doc["outputs"]
        t, cal = o["truth"], o["calibration"]["fit"]
        mean = t["annual_loss_mean"]["value_eur"]
        rows1.append(f"| {o['tail_index']:g} | {t['frequency']['lambda_per_year']:.1f} | {t['severity']['scale_eur']:,.0f} | "
                     f"{_m(t['annual_loss_quantile']['value_eur'])} | {'none (infinite mean)' if mean is None else _m(mean)} | {cal['max_abs_log_error']:.3f} |")
    head2 = ("| Tail index | Years | Threshold (EUR) | Truncated lognormal LDA | Splice LDA | Lognormal LDA, threshold ignored | "
             "Single loss approximation | Scenario | SMA ORC |")
    rows2 = [head2, "|" + "---|" * 9]

    def cell(c: dict | None, n: int) -> str:
        if c is None:
            return "none"
        r = c["ratio_to_truth"]
        defined = "" if c["n_defined"] == n else f", n={c['n_defined']}"
        return f"{r['median']:.2f} ({r['p25']:.2f} to {r['p75']:.2f}{defined})"

    for doc in _docs(derived):
        o = doc["outputs"]
        for c in o["cells"]:
            cap = c["capital"]
            n = c["replications"]["n_replications"]
            sma = c["sma"]["orc_over_true_quantile"]
            rows2.append(f"| {o['tail_index']:g} | {c['years']} | {c['collection_threshold_eur']:,} | {cell(cap['lda_lognormal_truncated'], n)} | "
                         f"{cell(cap['lda_splice'], n)} | {cell(cap['lda_lognormal'], n)} | {cell(cap['sla'], n)} | {cell(cap['scenario']['summary'], n)} | "
                         f"{sma['median']:.2f} ({sma['p25']:.2f} to {sma['p75']:.2f}) |")
    s3 = _s3_block(derived)
    n = models["fit"]["grid"]["n_replications_per_cell"]
    note = (f"Each cell is the median of the 99.9 percent capital over {n} independent histories as a multiple of the true quantile, "
            "with the first and third quartiles in brackets; n is the number of histories on which the engine returned the capital when it is "
            "below the number of histories.")
    return "\n".join(rows1) + "\n\n" + "\n".join(rows2) + "\n\n" + note + "\n\n" + s3


def write(page_path: Path, derived: Path) -> None:
    text = page_path.read_text(encoding="utf-8")
    head, rest = text.split(MARK_START, 1)
    tail = rest.split(MARK_END, 1)[1]
    page_path.write_text(f"{head}{MARK_START}\n{results_block(derived)}{MARK_END}{tail}", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[4]
    write(root / "docs" / "cases" / "C17.md", root / "data" / "derived")
    print("docs/cases/C17.md: results block written")
