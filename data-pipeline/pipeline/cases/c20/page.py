"""The generated results block of docs/cases/C20.md: every figure is read from the committed documents, never typed.

``results_block`` renders the block between ``BEGIN`` and ``END``; ``write_page`` replaces the block in the page and a test compares the
committed block with a fresh render (CT-2019). The SGCD dataset card sentence heads every table that shows SGCD.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .conv import SGCD_QUOTE

BEGIN = "<!-- c20-results:begin -->"
END = "<!-- c20-results:end -->"
ORDER = ("sgcd-seen", "sgcd-held-out", "fed-shift", "seed-sweep", "perturbation-grid", "leakage-planted")
FAIR_ORDER = ("fair.equalized_odds", "fair.equal_opportunity", "fair.calibration_within_groups", "fair.auc_by_group")
LIGHTS = ("green", "amber", "red", "not_evaluated")


def f3(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.3f}"


def f4(x: float | None) -> str:
    return "n/a" if x is None else f"{x:.4f}"


def pval(p: float | None) -> str:
    return "n/a" if p is None else ("<0.0001" if p < 1e-4 else f"{p:.4f}")


def block_of(text: str) -> str:
    """The generated block of a page, without its markers and the blank lines around it."""
    return text.split(BEGIN, 1)[1].split(END, 1)[0].strip("\n")


def _shock(w: Any, docs: dict[str, dict[str, Any]]) -> None:
    w(f"> {SGCD_QUOTE} (SantanderAI sota-stressed-datasets, SGCD-v0.1, commit 8403fa9, data CC BY 4.0).")
    w("")
    for vid in ("sgcd-seen", "sgcd-held-out"):
        o = docs[vid]["outputs"]
        w(f"#### {vid}: test batches {', '.join(o['shipped']['rows'][0]['batches'])}")
        w("")
        w("The model is the P4 LightGBM rung on the German features, fitted on S1 to S4 and A1 to A10 (700 records) and scored on the locked test "
          "batches. Drift is against the setup batches. Attribution is the rank correlation of the mean absolute TreeSHAP attribution against the "
          "clean rows. Consistency reads the structured and the text view of the five F4 fields.")
        w("")
        w("| Block | Shock | Records | Reach the structured view | AUC | Brier | Change in AUC | PSI max | CSI max | Completeness | Consistency | Attribution rank correlation |")
        w("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for block in ("shipped", "applied"):
            for r in o[block]["rows"]:
                p, d, q = r["performance"], r["drift"], r["data_quality"]
                w(f"| {o[block]['label']} | {r['shock_id']} | {r['n_records']} | {r['n_reaching_structured_view']} | {f3(p['auc'])} | {f3(p['brier'])} | "
                  f"{p['auc_delta']:+.3f} | {f3(d['psi_max'])} | {f3(d['csi_max'])} | {f3(q['completeness'])} | {f3(q['consistency'])} | "
                  f"{f3(r['attribution_rank_correlation'])} |")
        w("")
        fl = o["impact_detail"]["rows"]
        w("Decisions that flip at the fixed cut-off (the worst 20 percent of the baseline scores declined) under each applied shock: "
          + ", ".join(f"{x['shift_id'].removeprefix('applied-')} {x['flip_share'] * 100:.1f} percent of {x['n_decisions']}" for x in fl) + ".")
        w("")


def _shift(w: Any, d: dict[str, Any]) -> None:
    o = d["outputs"]
    rd, s = o["real_drift"], o["synthetic_shift"]
    w("#### Reading (a): real drift between the three Fed portfolios, no model")
    w("")
    w("PSI on ten reference-quantile bins (the rating and the codes on their categories), the Kolmogorov-Smirnov statistic (a coded variable reads "
      "its code as a position) and the chi-square p-value, all computed by `riskvalidation`. The reference is the first portfolio of the pair.")
    w("")
    w("| Pair | Variable | PSI | CSI | KS | Chi-square p |")
    w("|---|---|---:|---:|---:|---:|")
    for p in rd["pairs"]:
        for v in p["variables"]:
            w(f"| {p['a']} to {p['b']} | {v['name']} | {f3(v['psi'])} | {f3(v['csi'])} | {f3(v['ks'])} | {pval(v['chi2_p_value'])} |")
    w("")
    w(f"#### Reading (b): the {s['reference_portfolio']} portfolio as the size of a synthetic shift on the Polish evaluation set")
    w("")
    rows = f", {s['evaluation_rows']:,} rows, locked" if s.get("evaluation_rows") is not None else ""
    w(f"Evaluation set: {s['evaluation_set']}{rows}. The score is the displacement, in robust standard deviations, of the model's five leading features.")
    w("")
    w("| Shift | Score | AUC | Brier | Change in AUC | PSI of the score | Decisions that flip |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for x in s["shifts"]:
        m = x["metric"]
        w(f"| {x['shift_id']} | {x['score']:.3f} | {f3(m['auc'])} | {f3(m['brier'])} | {m['auc_delta']:+.3f} | {f3(x['psi'])} | {x['flip_share'] * 100:.1f} percent |")
    ws = s["worst_subsample"]
    w("")
    w(f"The worst {ws['share'] * 100:.0f} percent of the one-times shifted rows by the resemblance score: AUC {f3(ws['metric']['auc'])}, Brier "
      f"{f3(ws['metric']['brier'])}, change against the full sample {ws['metric']['auc_delta']:+.3f}.")
    c = s["label_free"]["conformal"]
    w("")
    w(f"Split conformal coverage at alpha {c['alpha']} (target {c['target_coverage']:.2f}), pooled {f3(c['coverage'])}, binomial p {pval(c['binomial_p_value'])}:")
    w("")
    w("| Window | Rows | Coverage | Binomial p |")
    w("|---|---:|---:|---:|")
    for x in c["coverage_by_window"]:
        w(f"| {x['window']} | {x['n']:,} | {f3(x['coverage'])} | {pval(x['binomial_p_value'])} |")
    cb = s["label_free"]["cbpe"]
    w("")
    w(f"CBPE, an estimate and never a measurement, on the one-times shifted rows: estimated AUC {f3(cb['estimated_auc'])} (assumptions: "
      + ", ".join(a["id"] for a in cb["assumptions"]) + ").")
    w("")


def _seeds(w: Any, d: dict[str, Any]) -> None:
    o = d["outputs"]
    w("| Rung | Seeds | AUC mean | AUC sd | AUC min | AUC max | Grades changed | Kendall tau mean | Kendall tau min | Reason overlap mean | Reason overlap p05 |")
    w("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in o["rows"]:
        a, t, v = r["auc"], r["attribution_rank_tau"], r["reason_code_overlap"]
        w(f"| {r['rung']} | {r['n_seeds']} | {f4(a['mean'])} | {f4(a['sd'])} | {f4(a['min'])} | {f4(a['max'])} | {r['grade_assignment_changed_share'] * 100:.1f} percent | "
          f"{f3(t['mean'])} | {f3(t['min'])} | {f3(v['mean'])} | {f3(v['p05'])} |")
    w("")
    w("| Rung | Rank correlation of TreeSHAP importance and ALE range | Leading features by importance (ALE range) |")
    w("|---|---:|---|")
    for e in o["explainer_agreement"]:
        top = ", ".join(f"{f['feature']} ({f3(f['effect_range'])})" for f in e["top_features"][:5])
        w(f"| {e['rung']} | {f3(e['rank_correlation'])} | {top} |")
    w("")


def _perturbation(w: Any, d: dict[str, Any]) -> None:
    o = d["outputs"]
    w(f"Preset scale {o['preset_eps']:g}; tolerance 0.02 AUC points (a convention).")
    w("")
    w("| Noise scale | AUC | Brier | Change in AUC | Finding |")
    w("|---:|---:|---:|---:|---|")
    for r in o["rows"]:
        m = r["metric"]
        w(f"| {r['eps']:g} | {f3(m['auc'])} | {f3(m['brier'])} | {m['auc_delta']:+.4f} | {'yes' if r['finding'] else 'no'} |")
    w("")
    fl = o["impact_detail"]["rows"]
    w("Decisions that flip at the fixed cut-off: " + ", ".join(f"{x['shift_id']} {x['flip_share'] * 100:.1f} percent" for x in fl) + ".")
    w("")


def _leakage(w: Any, d: dict[str, Any]) -> None:
    o = d["outputs"]
    s = o["screen"]
    w(f"The planted feature is `{o['planted_feature']}`: the default flag plus Gaussian noise of 0.2, dated one month after the observation date.")
    w("")
    w("| Screen | Planted-leak model | Clean control | Limit (convention) |")
    w("|---|---:|---:|---|")
    rows = {r["model_id"]: r for r in d["tests"] if r["test_id"] == "ml.leakage_screen"}
    ctrl = rows["P4-lightgbm-taiwan"]["extras"]["screens"]
    w(f"| Cells dated after the observation date | {s['temporal_order']['violations']:,} | {ctrl['temporal']['value']:,} | any |")
    w(f"| Largest single-feature AUC (`{s['single_feature_auc']['feature']}`) | {f3(s['single_feature_auc']['max_auc'])} | {f3(ctrl['single']['value'])} | "
      f"above {o['thresholds']['single_feature_auc']['value']} |")
    w(f"| Entity overlap, training and holdout | {f3(s['entity_overlap']['share'])} | {f3(ctrl['overlap']['share'])} | any |")
    w(f"| Resemblance AUC, development and holdout | {f3(s['resemblance_auc'])} | {f3(ctrl['resemblance']['value'])} | above {o['thresholds']['resemblance_auc']['value']} |")
    w("")
    w(f"Caught: {'yes' if o['caught'] else 'no'}. AUC with the leak available {f3(o['performance']['development_auc'])}; at decision time, when the feature "
      f"carries nothing, {f3(o['performance']['decision_time_auc'])}.")
    w("")


def _battery(w: Any, docs: dict[str, dict[str, Any]]) -> None:
    w("Lights of the labelled fairness battery on the Taiwan model (a cut-off declining the worst 20 percent of the baseline decisions; y = 1 is a "
      "default). It is labelled evidence on one benchmark, not a statement about any lender and not a compliance statement.")
    w("")
    names = ("seed-sweep", "perturbation-grid", "leakage-planted")
    w("| Test | Attribute | " + " | ".join(f"{n} value | {n} light" for n in names) + " |")
    w("|---|---|" + "---:|---|" * len(names))
    for t in FAIR_ORDER:
        for a in ("sex", "age", "marital_status"):
            cells = []
            for n in names:
                r = next(x for x in docs[n]["outputs"]["fairness_battery"]["rows"] if x["test_id"] == t and x["attribute"] == a)
                cells.append(f"{f4(r['value'])} | {r['light']}")
            w(f"| {t} | {a} | " + " | ".join(cells) + " |")
    w("")


def results_block(docs: dict[str, dict[str, Any]], models: dict[str, Any]) -> str:
    lines: list[str] = []
    w = lines.append
    w("### The SGCD shocks: seen and held out")
    w("")
    _shock(w, docs)
    w("### The Fed corporate shift probes")
    w("")
    _shift(w, docs["fed-shift"])
    w("### The seed sweep and the reason codes")
    w("")
    _seeds(w, docs["seed-sweep"])
    w("### The perturbation grid")
    w("")
    _perturbation(w, docs["perturbation-grid"])
    w("### The planted leak")
    w("")
    _leakage(w, docs["leakage-planted"])
    w("### The labelled fairness battery")
    w("")
    _battery(w, docs)
    w("### Lights of the test rows (green, amber, red, not evaluated)")
    w("")
    w("An amber or red light says an indicator crossed its convention; every cut point is a convention of the engine's policy, none is a regulatory "
      "threshold, and none is a finding of a defect of any lender.")
    w("")
    w("| Variant | Test rows | Green | Amber | Red | Not evaluated |")
    w("|---|---:|---:|---:|---:|---:|")
    for vid in ORDER:
        rows = docs[vid]["tests"]
        w(f"| {vid} | {len(rows)} | " + " | ".join(str(sum(1 for r in rows if r["light"] == k)) for k in LIGHTS) + " |")
    w("")
    w("### Findings of the documents (statistical findings, no compliance statement)")
    w("")
    w("| Variant | Finding | Severity | Status | Rows cited |")
    w("|---|---|---|---|---:|")
    for vid in ORDER:
        for f in docs[vid]["findings"]:
            cited = sum(1 for e in f["evidence"] if not e.startswith("design:"))
            w(f"| {vid} | {f['id'].removeprefix(vid + '-')} | {f['severity']} | {f['status']} | {cited if cited else 'design limit'} |")
    w("")
    w("### The fitted models")
    w("")
    w("| Rung | Dataset | Train rows | Calibration rows | Holdout rows | Holdout AUC |")
    w("|---|---|---:|---:|---:|---:|")
    for m in models["model"]:
        d = m["details"]
        w(f"| {m['id']} | {d['dataset']} | {d['train_rows']:,} | {d['calibration_rows']:,} | {d['holdout_rows']:,} | {f3(d['holdout_auc'])} |")
    return "\n".join(lines) + "\n"


def write_page(page: Path, docs: dict[str, dict[str, Any]], models: dict[str, Any]) -> None:
    text = page.read_text(encoding="utf-8")
    head, rest = text.split(BEGIN, 1)
    tail = rest.split(END, 1)[1]
    page.write_text(f"{head}{BEGIN}\n{results_block(docs, models)}{END}{tail}", encoding="utf-8", newline="\n")


def main() -> None:
    """Rewrite the results block of docs/cases/C20.md from the committed documents."""
    import json

    repo = Path(__file__).resolve().parents[4]
    derived = repo / "data" / "derived" / "C20"
    docs = {v: json.loads((derived / f"{v}.json").read_text(encoding="utf-8")) for v in ORDER}
    models = json.loads(next(derived.glob("models-*.json")).read_text(encoding="utf-8"))
    write_page(repo / "docs" / "cases" / "C20.md", docs, models)


if __name__ == "__main__":
    main()
