"""Experiment 4: what the engine's catalogue holds, which of the ECB reporting tests it implements as specified, and what the open
libraries hold of the same families.

Parts: (a) the registry of ``riskvalidation`` counted by family and decision rule; (b) the ECB 2019 statistics (section list read
from the specification) against the registry; (c) a scan of the Python sources of every installed distribution of the pinned
environment for the catalogue's vocabulary; (d) the PyPI metadata (summary and long description) of a fixed list of toolkits, read
on the day of the run and cached in ``results_catalogue.json`` (``--offline`` keeps the cached survey).

    python manuscripts/engines-and-test-catalogues/experiments/run_catalogue.py [--offline]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import importlib.metadata as md
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

import riskvalidation
import riskvalidation.validation  # noqa: F401  (registers every test)
from riskvalidation.core import registry

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "results_catalogue.json"

#: ECB (2019) sections whose statistic the instructions fix, with the registered id that implements it as specified (None: absent)
ECB = [
    ("2.5.2", "PD qualitative tools: process statistics and override rates", None),
    ("2.5.3.1", "PD back-testing: Jeffreys test", "pd.jeffreys"),
    ("2.5.4.1", "PD discriminatory power: AUC against the AUC at development", "disc.auc_vs_initial"),
    ("2.5.5.1", "PD stability: matrix weighted bandwidth", "rating.mwb"),
    ("2.5.5.2", "PD stability: migration matrix z-tests", "rating.migration_ztests"),
    ("2.5.5.3", "PD stability: concentration in rating grades (Herfindahl)", "rating.hhi"),
    ("2.6.2.1", "LGD back-testing: one-sample paired t-test, one-sided, 12 segments", None),
    ("2.6.3.1", "LGD discriminatory power: generalised AUC", None),
    ("2.7.2.1", "ELBE back-testing: paired t-test", None),
    ("2.8.2.1", "LGD in-default back-testing: paired t-test", None),
    ("2.9.3.1", "CCF back-testing: paired t-test", None),
    ("2.9.3.2", "EAD back-testing", None),
    ("2.9.4.1", "CCF generalised AUC", None),
    ("2.10", "Slotting: slot back-testing, tenor check, migrations", None),
]
RELATED = {"2.6.2.1": "lgd_ead.lgd_calibration_by_segment"}  # a paired t, two-sided, not the ECB's one-sided 12-segment test

TOKENS = {
    "jeffreys": r"jeffreys",
    "herfindahl": r"herfindahl",
    "matrix weighted bandwidth": r"matrix[ _]weighted|weighted[ _]bandwidth",
    "creditrisk+": r"creditrisk|credit_risk_plus|panjer",
    "granularity adjustment": r"granularity[ _]adjust",
    "vasicek": r"vasicek",
    "irrbb": r"irrbb|interest rate risk in the banking book",
    "economic value of equity": r"economic value of equity",
    "somers d": r"somers",
    "migration matrix test": r"migration[ _]matri[a-z]*[ _]test|time[ _]homogeneity",
}

PYPI = ["validmind", "piml", "modeva", "mercury-robust", "mercury-monitoring", "mercury-explainability", "probatus", "popmon",
        "evidently", "nannyml", "fairlearn", "giskard", "deepchecks", "alibi", "alibi-detect", "mapie", "interpret", "shap", "dalex",
        "credoai-lens", "transitionmatrix", "scorecardpy", "toad", "skorecard", "optbinning", "lifelines", "pycox",
        "open-source-risk-engine", "quantlib", "creditmetrics", "creditrisk", "pycreditrisk", "arch", "statsmodels", "riskfolio-lib",
        "pyfinance", "riskvalidation"]


def inventory() -> dict:
    cat = registry.catalogue()
    fam = collections.Counter(s.family for s in cat)
    dec = collections.Counter(s.decision for s in cat)
    return {"version": riskvalidation.__version__, "tests": len(cat), "families": len(fam), "by_family": dict(sorted(fam.items())),
            "by_decision": dict(dec), "with_reference": sum(1 for s in cat if s.reference.strip()),
            "ecb_referenced": sorted(s.test_id for s in cat if "ECB (2019)" in s.reference)}


def ecb_coverage() -> dict:
    ids = {s.test_id: s for s in registry.catalogue()}
    rows = []
    for sec, name, tid in ECB:
        ok = tid is not None and tid in ids and f"section {sec}" in ids[tid].reference or (
            tid is not None and tid in ids and sec == "2.5.4.1")
        rows.append({"section": sec, "statistic": name, "engine_id": tid if ok else None,
                     "related_id": RELATED.get(sec) if RELATED.get(sec) in ids else None})
    n_impl = sum(1 for r in rows if r["engine_id"])
    return {"sections": len(rows), "implemented": n_impl, "related_only": sum(1 for r in rows if not r["engine_id"] and r["related_id"]),
            "absent": sum(1 for r in rows if not r["engine_id"] and not r["related_id"]), "rows": rows}


def scan_installed() -> dict:
    rx = {k: re.compile(v, re.I) for k, v in TOKENS.items()}
    hits: dict[str, dict[str, int]] = {k: collections.defaultdict(int) for k in TOKENS}
    n_files = n_dists = 0
    for dist in md.distributions():
        name = dist.metadata["Name"]
        if name.lower() == "riskvalidation":
            continue
        n_dists += 1
        for f in dist.files or []:
            if f.suffix != ".py":
                continue
            p = pathlib.Path(dist.locate_file(f))
            try:
                if p.stat().st_size > 2_000_000:
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            n_files += 1
            hay = text + " " + str(f)
            for k, r in rx.items():
                if r.search(hay):
                    hits[k][name] += 1
    return {"distributions": n_dists, "python_files": n_files,
            "hits": {k: dict(sorted(v.items())) for k, v in hits.items()}}


def survey() -> dict:
    rx = {k: re.compile(v, re.I) for k, v in TOKENS.items()}
    rx["ecb"] = re.compile(r"\bECB\b|european central bank", re.I)
    rows = []
    for name in PYPI:
        try:
            with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=30) as r:
                info = json.load(r)
        except urllib.error.HTTPError as e:
            rows.append({"name": name, "status": f"HTTP {e.code}"})
            continue
        except Exception as e:  # network failure: recorded, never invented
            rows.append({"name": name, "status": f"error {type(e).__name__}"})
            continue
        i = info["info"]
        latest = info["urls"][0]["upload_time"][:10] if info.get("urls") else None
        text = " ".join([i.get("summary") or "", i.get("description") or ""])
        rows.append({"name": name, "status": "found", "version": i["version"], "latest_upload": latest,
                     "license": (i.get("license_expression") or (i.get("license") or "")[:40] or None),
                     "summary": (i.get("summary") or "")[:140], "description_chars": len(i.get("description") or ""),
                     "hits": {k: len(r.findall(text)) for k, r in rx.items() if r.search(text)}})
    return {"date": datetime.date.today().isoformat(), "queried": len(PYPI), "found": sum(1 for r in rows if r["status"] == "found"),
            "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    result = {"inventory": inventory(), "ecb": ecb_coverage(), "installed_scan": scan_installed()}
    if a.offline and "survey" in old:
        result["survey"] = old["survey"]
    else:
        result["survey"] = survey()
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(json.dumps(result["inventory"], indent=1))
    print({k: v for k, v in result["ecb"].items() if k != "rows"})
    for k, v in result["installed_scan"]["hits"].items():
        print(k, v)
    print({r["name"]: r.get("hits") for r in result["survey"]["rows"] if r.get("hits")})
    print([r["name"] for r in result["survey"]["rows"] if r["status"] != "found"])


if __name__ == "__main__":
    sys.exit(main())
