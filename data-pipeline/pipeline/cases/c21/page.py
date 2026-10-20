"""The generated results block of docs/cases/C21.md: every figure is read from the committed documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END``; ``write_page`` replaces the block in the page and a test compares the
committed block with a fresh render (CT-2116). Every table is an indicator of statistical disparity in public decisions: no legal claim.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

BEGIN = "<!-- c21-results:begin -->"
END = "<!-- c21-results:end -->"
FIELD_NAMES = {"derived_race": "Race", "derived_ethnicity": "Ethnicity", "derived_sex": "Sex", "applicant_age": "Age"}
TEST_ORDER = ("fair.demographic_parity", "fair.adverse_impact", "fair.two_proportion_z", "fair.fisher_exact", "fair.conditional_disparity",
              "fair.rate_spread_disparity", "fair.replication", "fair.situation_testing")


def pct(x: float) -> str:
    return f"{x * 100:.1f}"


def num(x: float | None, nd: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def pval(p: float) -> str:
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def block_of(text: str) -> str:
    """The generated block of a page, without its markers and the blank lines around it."""
    return text.split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")


def results_block(variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append
    ids = sorted(variants)
    w("### The year pairs")
    w("")
    w("Each pair is fitted on year t and confirmed on t + 1. Rows are the decision rows (action taken 1, 2 or 3) of Delaware; the rates, "
      "their tests, the four-fifths flags and the situation test are computed on the fit year.")
    w("")
    w("| Pair | Rows, fit year | Rows, confirm year | Test rows | Estimates that could not be fitted |")
    w("|---|---:|---:|---:|---:|")
    for vid in ids:
        o = variants[vid]["outputs"]
        failed = sum(1 for a in o["attributes"] for c in a["contrasts"] for k in ("controlled", "rate_spread", "confirmation")
                     if c[k]["estimate"] is None)
        w(f"| {o['pair_id']} | {o['scope']['rows_fit']:,} | {o['scope']['rows_confirm']:,} | {len(variants[vid]['tests'])} | {failed} |")
    w("")
    w("### Approval rate by group, fit year (percent; a star marks the four-fifths flag against the highest-rate group)")
    w("")
    w("The four-fifths line is an employment benchmark (29 CFR 1607.4(D)), never a credit-law threshold. The flag is decided on the counts "
      "in exact arithmetic.")
    w("")
    w("| Attribute | Group | " + " | ".join(str(variants[v]["outputs"]["fit_year"]) for v in ids) + " |")
    w("|---|---|" + "---:|" * len(ids))
    fields = [a["field"] for a in variants[ids[0]]["outputs"]["attributes"]]
    for f in fields:
        groups = [g["group"] for g in next(a for a in variants[ids[0]]["outputs"]["attributes"] if a["field"] == f)["groups"]]
        for g in groups:
            cells = []
            for v in ids:
                a = next(x for x in variants[v]["outputs"]["attributes"] if x["field"] == f)
                row = next((r for r in a["groups"] if r["group"] == g), None)
                flag = next((r["flag"] for r in a["four_fifths"]["groups"] if r["group"] == g), False)
                cells.append("n/a" if row is None else f"{pct(row['selection_rate'])}{'*' if flag else ''}")
            w(f"| {FIELD_NAMES[f]} | {g} | " + " | ".join(cells) + " |")
    w("")
    w("### Each group against the reference group: the unconditional indicators")
    w("")
    w("| Pair | Attribute | Group (reference) | Parity gap (points) | Parity ratio | z-test p | Fisher p |")
    w("|---|---|---|---:|---:|---:|---:|")
    for v in ids:
        o = variants[v]["outputs"]
        for a in o["attributes"]:
            for c in a["contrasts"]:
                w(f"| {o['pair_id']} | {FIELD_NAMES[a['field']]} | {c['group']} ({c['reference_group']}) | {c['parity_gap'] * 100:.2f} | "
                  f"{num(c['parity_ratio'])} | {pval(c['z_test']['p_value'])} | {pval(c['fisher_exact']['p_value'])} |")
    w("")
    w("### After the permitted controls: the odds ratio and the rate-spread estimate, and their confirmation on the next year")
    w("")
    w("The controlled estimate is an approximation of comparative evidence; the credit score is not in public HMDA and is a missing control "
      "of every row. The odds ratio is for the group against the reference group of its attribute, with the 95 percent Wald interval. "
      "The rate spread is in percentage points. Same sign and size ratio compare the fit with the same estimate refitted on t + 1.")
    w("")
    w("| Pair | Attribute | Group | n | Odds ratio [95% interval] | Rate spread, points [95% interval] | Confirm, log-odds | Same sign | Size ratio |")
    w("|---|---|---|---:|---|---|---:|---|---:|")
    for v in ids:
        o = variants[v]["outputs"]
        for a in o["attributes"]:
            for c in a["contrasts"]:
                ce, rs, cf = c["controlled"]["estimate"], c["rate_spread"]["estimate"], c["confirmation"]["estimate"]
                orr = "not fitted" if ce is None else f"{ce['odds_ratio']:.3f} [{_exp(ce['ci']['lo'])}, {_exp(ce['ci']['hi'])}]"
                rss = "not fitted" if rs is None else f"{rs['coefficient']:.3f} [{rs['ci']['lo']:.3f}, {rs['ci']['hi']:.3f}]"
                n_cell = "n/a" if ce is None else format(ce["n"], ",")
                conf = "n/a" if cf is None else f"{cf['confirm_coefficient']:.3f}"
                same = "n/a" if cf is None else ("yes" if cf["same_sign"] else "no")
                ratio = "n/a" if cf is None else num(cf["size_ratio"])
                w(f"| {o['pair_id']} | {FIELD_NAMES[a['field']]} | {c['group']} | {n_cell} | {orr} | {rss} | {conf} | {same} | {ratio} |")
    w("")
    w("### Situation testing on sex, ceteris paribus comparator only")
    w("")
    w("Female applicants against male applicants, k neighbours, the range normalization; the counterfactual test is not run because public "
      "HMDA gives no counterfactual dataset. The complainants are all women of the fit year with every control usable.")
    w("")
    w("| Pair | k | Complainants | Cases (delta p above tau) | Significant | Share significant |")
    w("|---|---:|---:|---:|---:|---:|")
    for v in ids:
        o = variants[v]["outputs"]
        s = o["situation_testing"]
        w(f"| {o['pair_id']} | {s['k']} | {s['n_complainants']:,} | {s['n_cases']:,} | {s['n_significant']:,} | "
          f"{pct(s['n_significant'] / s['n_complainants']) if s['n_complainants'] else 'n/a'} percent |")
    w("")
    w("### Lights of the test rows (green, amber, red, not evaluated)")
    w("")
    w("An amber light says the indicator crossed its convention; none is red by contract; none is a finding of a violation.")
    w("")
    w("| Pair | " + " | ".join(t.removeprefix("fair.") for t in TEST_ORDER) + " |")
    w("|---|" + "---:|" * len(TEST_ORDER))
    for v in ids:
        rows = variants[v]["tests"]
        cells = []
        for t in TEST_ORDER:
            sel = [r["light"] for r in rows if r["test_id"] == t]
            cells.append("/".join(str(sum(1 for x in sel if x == k)) for k in ("green", "amber", "red", "not_evaluated")))
        w(f"| {variants[v]['outputs']['pair_id']} | " + " | ".join(cells) + " |")
    w("")
    w("### The fitted models")
    w("")
    fits = models["fit"]["decision_models"]
    w(f"The models document keeps {len(fits)} fitted pairwise models of the fit years "
      f"({sum(1 for f in fits if f['kind'] == 'logistic')} logistic decision models and {sum(1 for f in fits if f['kind'] == 'linear')} "
      "linear rate-spread models), every term with its standard error.")
    return "\n".join(lines) + "\n"


def _exp(x: float) -> str:
    return f"{math.exp(x):.3f}"


def write_page(page: Path, variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> None:
    text = page.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    page.write_text(f"{head}{BEGIN}\n{results_block(variants, models)}{END}{tail}", encoding="utf-8", newline="\n")


def main() -> None:
    """Rewrite the results block of docs/cases/C21.md from the committed documents."""
    import json

    repo = Path(__file__).resolve().parents[4]
    derived = repo / "data" / "derived" / "C21"
    variants = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(derived.glob("pair-*.json"))}
    models = json.loads(next(derived.glob("models-*.json")).read_text(encoding="utf-8"))
    write_page(repo / "docs" / "cases" / "C21.md", variants, models)


if __name__ == "__main__":
    main()
