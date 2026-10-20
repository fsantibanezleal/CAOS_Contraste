"""The generated results block of docs/cases/C02.md: every figure is read from the committed documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END``; ``write_page`` replaces the block in the page and a test compares the
committed block with a fresh render (CT-0213). Transfer, term structure and Impact are exploratory and say so.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

BEGIN = "<!-- c02-results:begin -->"
END = "<!-- c02-results:end -->"
HORIZONS = ("h1", "h2", "h3", "h4", "h5", "pooled")
HEAD = {"h1": "1y", "h2": "2y", "h3": "3y", "h4": "4y", "h5": "5y", "pooled": "pooled"}
RUNG_ORDER = ("P0-single", "P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm", "P4-xgboost")


def block_of(text: str) -> str:
    """The generated block of a page, without its markers and the blank lines around it."""
    return text.split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")


def rid(model_id: str) -> str:
    return model_id.split("-", 1)[1]


def rung(doc: dict[str, Any], r: str) -> dict[str, Any]:
    return next(x for x in doc["outputs"]["rungs"] if rid(x["model_id"]) == r)


def pval(p: float) -> str:
    return "<0.0001" if p < 1e-4 else f"{p:.4f}"


def table(w, head: list[str], rows: list[list[str]], right_from: int = 1) -> None:
    w("| " + " | ".join(head) + " |")
    w("|" + "|".join("---" if i < right_from else "---:" for i in range(len(head))) + "|")
    for r in rows:
        w("| " + " | ".join(r) + " |")
    w("")


def results_block(variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append
    docs = {h: variants[h] for h in HORIZONS}
    w("### The six documents")
    w("")
    w("Each document is one file (or the five stacked, with a horizon indicator) with a locked stratified holdout of 30 percent, a calibration "
      "slice of 20 percent of the rest and the training slice. The files carry no date: no out-of-time claim is made. The horizon of a file is "
      "its name (see the open decision in Limits).")
    w("")
    rows = []
    for h in HORIZONS:
        o = docs[h]["outputs"]
        c, s = o["counts"], o["split"]
        rows.append([HEAD[h], f"{c['rows']:,}", f"{c['events']:,}", f"{c['event_rate'] * 100:.2f}", f"{s['train_rows']:,}", f"{s['calibration_rows']:,}",
                     f"{s['holdout_rows']:,}", f"{s['holdout_events']:,}"])
    table(w, ["Document", "Rows", "Bankruptcies", "Rate (percent)", "Train", "Calibration", "Holdout", "Holdout events"], rows)
    w("### Discrimination by horizon: holdout AUC (DeLong 95 percent interval)")
    w("")
    rows = []
    for r in RUNG_ORDER:
        cells = []
        for h in HORIZONS:
            d = rung(docs[h], r)["discrimination"]
            cells.append(f"{d['auc']:.3f} [{d['auc_ci']['lo']:.3f}, {d['auc_ci']['hi']:.3f}]")
        rows.append([r, *cells])
    table(w, ["Rung", *(HEAD[h] for h in HORIZONS)], rows)
    w("KS and Gini of the champion (P1) and of the best rung of each document:")
    w("")
    rows = []
    for h in HORIZONS:
        best = max(docs[h]["outputs"]["rungs"], key=lambda x: x["discrimination"]["auc"])
        p1 = rung(docs[h], "P1-scorecard")["discrimination"]
        rows.append([HEAD[h], f"{p1['gini']:.3f}", f"{p1['ks']:.3f}", rid(best["model_id"]), f"{best['discrimination']['auc']:.3f}",
                     f"{best['discrimination']['gini']:.3f}", f"{best['discrimination']['ks']:.3f}"])
    table(w, ["Document", "P1 Gini", "P1 KS", "Best rung", "Best AUC", "Best Gini", "Best KS"], rows)
    w("### Calibration: Hosmer-Lemeshow p-value, Brier score and expected calibration error")
    w("")
    rows = []
    for r in RUNG_ORDER:
        cells = []
        for h in HORIZONS:
            c = rung(docs[h], r)["calibration"]
            cells.append(f"{pval(c['hosmer_lemeshow']['p_value'])} / {c['brier']:.4f} / {c['ece']:.4f}")
        rows.append([r, *cells])
    table(w, ["Rung (p / Brier / ECE)", *(HEAD[h] for h in HORIZONS)], rows)
    w("### Overfit gap: train AUC minus holdout AUC (a star marks a gap above the 0.05 tolerance, a convention)")
    w("")
    rows = []
    for r in RUNG_ORDER:
        rows.append([r, *(f"{rung(docs[h], r)['overfit']['gap']:.3f}{'*' if rung(docs[h], r)['overfit']['flag'] else ''}" for h in HORIZONS)])
    table(w, ["Rung", *(HEAD[h] for h in HORIZONS)], rows)
    w("### Challenger against the P1 scorecard: AUC difference (DeLong 95 percent interval), DeLong p-value, Brier difference, grade disagreement")
    w("")
    rows = []
    for h in HORIZONS:
        for c in docs[h]["outputs"]["challenger"]:
            a, b = c["auc_diff_ci"], c["brier_diff_ci"]
            rows.append([HEAD[h], rid(c["challenger"]), f"{c['auc_diff']:+.3f} [{a['lo']:+.3f}, {a['hi']:+.3f}]", pval(c["delong_p_value"]),
                         f"{c['brier_diff']:+.4f} [{b['lo']:+.4f}, {b['hi']:+.4f}]", f"{c['grade_disagreement_share'] * 100:.1f}"])
    table(w, ["Document", "Challenger", "AUC difference", "DeLong p", "Brier difference", "Two-notch grade disagreement (percent)"], rows, 2)
    w("### Exploratory: cross-file transfer, AUC of a rung fitted on one file and scored on the locked holdout of another")
    w("")
    w("Exploratory: the firm overlap across the files is unknown, so a transfer AUC may be inflated by firms that repeat. The diagonal is the "
      "within-file holdout AUC.")
    w("")
    for code, name in (("P1", "P1 scorecard"), ("P3", "P3 EBM"), ("P4", "P4 LightGBM")):
        w(f"{name}:")
        w("")
        rows = []
        for k in range(1, 6):
            cells = {c["scored_on_years"]: c["auc"] for c in docs[f"h{k}"]["outputs"]["transfer"]["cells"] if c["rung"] == code}
            rows.append([f"fitted on {k}y", *(f"{cells[j]:.3f}" for j in range(1, 6))])
        table(w, ["Fitted on", *(f"scored on {j}y" for j in range(1, 6))], rows)
    w("### Exploratory: the five event rates as a cumulative PD")
    w("")
    ts = docs["h1"]["outputs"]["term_structure"]
    w("Exploratory: the files may not draw one population, and the UCI page reads the horizons the other way round (see Limits).")
    w("")
    table(w, ["Years", "Cumulative PD (percent)", "Hazard (percent)"], [[str(p["years"]), f"{p['cumulative_pd'] * 100:.3f}", f"{p['hazard'] * 100:.3f}"] for p in ts["points"]])
    bt = next(r for r in docs["h1"]["tests"] if r["test_id"] == "ifrs9.lifetime_pd_backtest")
    w(f"The engine's lifetime back-test of the champion's mean PD on each holdout against the holdout event rate: the largest gap is "
      f"{bt['metric'] * 100:.3f} percentage points, light {bt['light']} (relative-gap rule of the engine, a convention).")
    w("")
    w("### Exploratory: the 12-month and lifetime ECL of one unit of exposure under the horizon PDs of the term-structure block")
    w("")
    im = docs["h1"]["outputs"]["impact_detail"]
    if im["ecl_12m_effect"] is None:
        w(f"No ECL is computed: {im['reason_if_null']}.")
    else:
        w(f"With a loss given default of {im['lgd']['value'] * 100:.0f} percent (an assumption) and no discounting, the 12-month ECL is "
          f"{im['ecl_12m_effect'] * 100:.3f} percent of the exposure and the lifetime ECL is {im['ecl_lifetime_effect'] * 100:.3f} percent, a ratio of "
          f"{im['ecl_lifetime_effect'] / im['ecl_12m_effect']:.2f}. An illustration of how far the horizon moves a provision, not a provision.")
    w("")
    w("### Lights of the test rows (green, amber, red, not evaluated)")
    w("")
    ids = sorted({r["test_id"] for h in HORIZONS for r in docs[h]["tests"]})
    rows = []
    for t in ids:
        cells = []
        for h in HORIZONS:
            sel = [r["light"] for r in docs[h]["tests"] if r["test_id"] == t]
            cells.append("/".join(str(sum(1 for x in sel if x == k)) for k in ("green", "amber", "red", "not_evaluated")))
        rows.append([t, *cells])
    table(w, ["Test", *(HEAD[h] for h in HORIZONS)], rows)
    w("### Findings of the documents")
    w("")
    rows = []
    for h in HORIZONS:
        for f in docs[h]["findings"]:
            cited = sum(1 for e in f["evidence"] if not e.startswith("design:"))
            rows.append([HEAD[h], f["id"], f["severity"], f["status"], str(cited) if cited else "design limit"])
    table(w, ["Document", "Finding", "Severity", "Status", "Test rows cited"], rows, 4)
    w("### The fitted models")
    w("")
    recs = models["model"]
    w(f"The models document keeps {len(recs)} fitted models: eight rungs (P0 constant, P0 single variable, P1, P2a, P2b, P3, P4 LightGBM, "
      f"P4 XGBoost) for each of the five files and the pooled variant, and the fitted preprocessing of each fit (training medians and the "
      f"missing indicators) with the constant.")
    return "\n".join(lines) + "\n"


def write_page(page: Path, variants: dict[str, dict[str, Any]], models: dict[str, Any]) -> None:
    text = page.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    page.write_text(f"{head}{BEGIN}\n{results_block(variants, models)}{END}{tail}", encoding="utf-8", newline="\n")


def main() -> None:
    """Rewrite the results block of docs/cases/C02.md from the committed documents."""
    import json

    repo = Path(__file__).resolve().parents[4]
    derived = repo / "data" / "derived" / "C02"
    variants = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(derived.glob("*.json")) if not p.stem.startswith("models-")}
    models = json.loads(next(derived.glob("models-*.json")).read_text(encoding="utf-8"))
    write_page(repo / "docs" / "cases" / "C02.md", variants, models)


if __name__ == "__main__":
    main()
