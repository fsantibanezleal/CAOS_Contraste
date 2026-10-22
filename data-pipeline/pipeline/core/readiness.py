"""The readiness document (catalog row readiness, ADR-0080 decisions 3 and 4): what is real in this build, computed
from docs/contracts/catalog.md and the repository state, never written by hand.

Ported from CAOS_PRODUCT_TEMPLATE v0.04.000 (data-pipeline/pipeline/core/readiness.py) and extended for Contraste's
22-case plan: a case of the plan with no built module is declared absent (``partial`` on ``case-manifest``), and the
C01 model slot ``c01-pd-rung`` is ``training`` on the baseline while a rung's fitted record is absent.

A pure function of its inputs: no clock, no randomness, rows in catalog order, ``missing`` sorted. The rules, their
order (first match wins) and their reasons are the catalog's ``## Missing-data states`` table; tests/test_readiness.py
parses that table and holds every reason here to it. Stdlib only, so scripts/check_readiness.py runs in CI without
installing the pipeline's dependencies (ADR-0074): it never imports the case modules, it reads the planned registry
(config/planned_cases.json) and the names in ``cases/``.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "example.readiness/v1"  # the schema's const (common/readiness.schema.json, copied from the template)
CATALOG_REL = "docs/contracts/catalog.md"
INDEX_REL = "manifests/index.json"
PLANNED_REL = "data-pipeline/config/planned_cases.json"
CASES_REL = "data-pipeline/pipeline/cases"
STATUSES = ("real", "active")  # the catalog's status vocabulary, exactly, lower case
SLOT = "c01-pd-rung"
SLOT_CASE = "C01"
#: the rungs every C01 models artifact carries (P4-xgboost only on the Taiwan fit, P5-tabpfn only on the German twin
#: when the optional extra is installed); tests/test_readiness.py ties them to the ladder
C01_RUNGS = ("P0-constant", "P0-single", "P1-scorecard", "P2a-l1", "P2b-pltr", "P3-ebm", "P4-lightgbm")
#: rows read from the case's artifacts: the envelopes (every case) and the per-case rows ``c<NN>-...``
ENVELOPES = ("variant-envelope", "models-envelope")
CASE_ROW = re.compile(r"^c(\d\d)-")
DERIVED_IDS = ("case-index", "case-manifest", "test-result", *ENVELOPES)

# the catalog's reasons as (en, es) templates, in the order of its Missing-data table
T_PROVIDER = ("Served by its provider ({provider}); the real producer is not built yet.",
              "Lo sirve su proveedor ({provider}); el productor real aún no está construido.")
T_NOT_BAKED = ("The pipeline has not baked this build.", "El pipeline no ha generado esta versión.")
T_PLANNED = ("Cases planned and not built yet: {n} of {total} ({ids}).",
             "Casos planificados y aún no construidos: {n} de {total} ({ids}).")
T_MANIFESTS = ("{n} of {total} manifests are absent.", "Faltan {n} de {total} manifiestos.")
T_ARTIFACTS = ("{n} of {total} artifacts are absent.", "Faltan {n} de {total} artefactos.")
T_STALE = ("Baked by {engine_version}; the product is {version}.",
           "Generado por {engine_version}; el producto es {version}.")
T_NO_RUNG = ("Fitted rung absent from the models artifact ({artifacts}): {rungs}; the benchmark rung (P0) answers.",
             "Peldaño ajustado ausente del artefacto de modelos ({artifacts}): {rungs}; responde el benchmark (P0).")
T_API = ("The API lane is dormant; the site reads the committed documents.",
         "La API está inactiva; el sitio lee los documentos versionados.")


def parse_catalog(text: str) -> list[dict[str, str]]:
    """The rows of the ``## Contracts`` table, one dict per row keyed by the lower-cased header cells."""
    lines = text.replace("\r\n", "\n").split("\n")
    start = next(i for i, ln in enumerate(lines) if ln.strip() == "## Contracts")
    table: list[list[str]] = []
    for ln in lines[start + 1:]:
        if ln.startswith("## "):
            break
        if ln.startswith("|"):
            table.append([c.strip() for c in ln.strip().strip("|").split("|")])
    header = [c.lower() for c in table[0]]
    return [dict(zip(header, cells)) for cells in table[2:]]  # table[1] is the separator


def _fill(tpl: tuple[str, str], **vals: object) -> dict[str, str]:
    out = []
    for text in tpl:
        for k, v in vals.items():
            text = text.replace("{" + k + "}", str(v))
        out.append(text)
    return {"en": out[0], "es": out[1]}


def _json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _artifact_paths(manifest: dict) -> list[str]:
    """The artifact paths a manifest names, in either form of contract 2."""
    if isinstance(manifest.get("artifacts"), list):
        return [a["path"] for a in manifest["artifacts"] if isinstance(a, dict) and "path" in a]
    single = manifest.get("artifact")
    return [single["path"]] if isinstance(single, dict) and "path" in single else []


def built_ids(cases_dir: str | Path) -> list[str]:
    """The ids of the built cases by the names in ``cases/`` (a module ``c<NN>_*.py`` or a package ``c<NN>/``):
    the stdlib view of ``pipeline.cases.discover`` (tests/test_readiness.py holds them equal)."""
    ids = set()
    for p in Path(cases_dir).iterdir():
        m = re.match(r"^c(\d\d)(?:_.+\.py|\.py)?$", p.name)
        if m and (p.is_file() or (p / "__init__.py").is_file()):
            ids.add(f"C{m.group(1)}")
    return sorted(ids)


def _is_models(path: str) -> bool:
    return Path(path).name.startswith("models-")


class _Facts:
    """What the repository says, read once: the index, the absent manifests and artifacts, the planned cases, the
    rungs the C01 models artifacts lack."""

    def __init__(self, repo_root: Path, derived_root: Path, version: str) -> None:
        self.version = version
        index = _json(derived_root / INDEX_REL)
        self.index: dict | None = index if isinstance(index, dict) else None
        self.engine_version = str(self.index.get("engine_version")) if self.index else ""
        planned = _json(repo_root / PLANNED_REL) or []
        cases_dir = repo_root / CASES_REL
        built = set(built_ids(cases_dir)) if cases_dir.is_dir() else set()
        self.planned = {e["case_id"] for e in planned if e["case_id"] not in built}
        self.cases_total = 0
        self.manifests_missing: dict[str, str] = {}  # manifest path -> case id
        self.artifacts_total: dict[str, int] = {}
        self.artifacts_missing: list[str] = []
        self.rungs_missing: dict[str, list[str]] = {}  # models artifact path -> absent rung ids
        self.slot_artifacts = 0
        if self.index:
            for entry in self.index.get("cases", []):
                rel, cid = entry["manifest_path"], entry["case_id"]
                self.cases_total += 1
                manifest = _json(derived_root / rel)
                if not isinstance(manifest, dict):
                    self.manifests_missing[rel] = cid
                    continue
                for art in _artifact_paths(manifest):
                    self.artifacts_total[cid] = self.artifacts_total.get(cid, 0) + 1
                    if not (derived_root / art).is_file():
                        self.artifacts_missing.append(art)
                    elif cid == SLOT_CASE and _is_models(art):
                        self.slot_artifacts += 1
                        doc = _json(derived_root / art)
                        have = {m.get("id") for m in doc.get("model", [])} if isinstance(doc, dict) else set()
                        gone = [r for r in C01_RUNGS if r not in have]
                        if gone:
                            self.rungs_missing[art] = gone


def _entry(row: dict[str, str], state: str, provenance: str | None, reason: dict | None,
           missing: list[str] | None = None) -> dict:
    return {"id": row["id"], "version": row["version"], "status": row["status"], "provenance": provenance,
            "state": state, "reason": reason, "missing": sorted(missing or [])}


def _artifact_scope(rid: str, f: _Facts) -> tuple[list[str], int] | None:
    """The absent artifacts a row reads and how many it reads in all, or None when the row reads none: an envelope
    reads every case's, ``c<NN>-models*`` the models artifacts of that case, any other ``c<NN>-*`` its variants."""
    if rid in ENVELOPES:
        want = (lambda p: _is_models(p)) if rid == "models-envelope" else (lambda p: not _is_models(p))
        return [p for p in f.artifacts_missing if want(p)], sum(f.artifacts_total.values())
    m = CASE_ROW.match(rid)
    if not m:
        return None
    cid = f"C{m.group(1)}"
    want = (lambda p: _is_models(p)) if "models" in rid else (lambda p: not _is_models(p))
    return [p for p in f.artifacts_missing if p.startswith(f"{cid}/") and want(p)], f.artifacts_total.get(cid, 0)


def _rule(row: dict[str, str], f: _Facts) -> dict:
    """The first rule of the catalog's Missing-data table that matches ``row``."""
    rid = row["id"]
    provider = row.get("provider", "").replace("`", "")
    if row["status"] not in STATUSES:
        raise ValueError(f"catalog row {rid!r}: status {row['status']!r} is not one of "
                         f"{' or '.join(repr(s) for s in STATUSES)} (lower case, no other value)")
    if row["status"] == "active":
        return _entry(row, "provider", provider.split(":", 1)[0] or "stub", _fill(T_PROVIDER, provider=provider))
    scope = _artifact_scope(rid, f)
    derived = rid in DERIVED_IDS or scope is not None or rid == SLOT
    if derived and f.index is None:
        return _entry(row, "missing", None, _fill(T_NOT_BAKED))
    if rid == "case-manifest" and f.manifests_missing:
        gone = f.manifests_missing
        absent_planned = sorted(c for c in gone.values() if c in f.planned)
        if len(absent_planned) == len(gone):
            return _entry(row, "partial", "real",
                          _fill(T_PLANNED, n=len(gone), total=f.cases_total, ids=", ".join(absent_planned)), list(gone))
        return _entry(row, "partial", "real", _fill(T_MANIFESTS, n=len(gone), total=f.cases_total), list(gone))
    if scope is not None and scope[0]:
        return _entry(row, "partial", "real", _fill(T_ARTIFACTS, n=len(scope[0]), total=scope[1]), scope[0])
    if derived and f.engine_version != f.version:
        return _entry(row, "stale", "real", _fill(T_STALE, engine_version=f.engine_version, version=f.version))
    if rid == SLOT and (f.rungs_missing or f.slot_artifacts == 0):
        if f.rungs_missing:
            arts = ", ".join(sorted(f.rungs_missing))
            rungs = ", ".join(sorted({r for v in f.rungs_missing.values() for r in v}, key=C01_RUNGS.index))
        else:
            arts, rungs = "none", ", ".join(C01_RUNGS)
        return _entry(row, "training", "baseline", _fill(T_NO_RUNG, artifacts=arts, rungs=rungs))
    if rid == "api":
        return _entry(row, "missing", None, _fill(T_API))
    return _entry(row, "available", "real", None)


def compute(*, repo_root: str | Path, derived_root: str | Path, models_dir: str | Path | None = None,
            catalog_path: str | Path | None = None, version: str | None = None) -> dict:
    """The readiness document of the repository at ``repo_root``, whose baked documents are under ``derived_root``.
    ``models_dir`` is accepted for the template's signature (Contraste's models are artifacts under ``derived_root``).
    ``catalog_path`` and ``version`` default to the repository's."""
    root = Path(repo_root)
    catalog = Path(catalog_path) if catalog_path else root / CATALOG_REL
    raw = catalog.read_bytes().replace(b"\r\n", b"\n")
    ver = version if version is not None else (root / "VERSION").read_text(encoding="utf-8").strip()
    facts = _Facts(root, Path(derived_root), ver)
    rows = [r for r in parse_catalog(raw.decode("utf-8")) if r["id"] != "readiness"]
    return {"schema": SCHEMA, "product_version": ver, "catalog_sha256": hashlib.sha256(raw).hexdigest(),
            "contracts": [_rule(r, facts) for r in rows]}


def to_bytes(doc: dict) -> bytes:
    """The committed serialisation: compact JSON, UTF-8, no trailing newline (what scripts/check_readiness.py compares)."""
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write(derived_root: str | Path, doc: dict) -> int:
    """Write ``<derived_root>/readiness.json``; return its byte size."""
    path = Path(derived_root) / "readiness.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = to_bytes(doc)
    path.write_bytes(data)
    return len(data)
