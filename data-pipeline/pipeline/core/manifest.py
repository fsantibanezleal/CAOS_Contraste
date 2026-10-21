"""CONTRACT 2, artifact (pipeline to web), SDD section 2.2.

Three documents, each versioned by its schema id and mirrored by ``frontend/src/lib/contract.types.ts``:

- the index (``data/derived/manifests/index.json``): every case with its bilingual title and category, and the case
  the App opens on;
- one manifest per case (``data/derived/manifests/<case>.json``): the case's question, sources, truth status, the
  contract-1 report of its inputs, its expected ranges, and one entry per variant naming the variant's artifact,
  its byte size and its lane verdict;
- one artifact per variant (``data/derived/<case>/<variant>.json``): the model record, the outputs, the
  ``TestResult`` rows, the impact, the findings, the provenance and the lane.

Every builder checks what it writes; an artifact is built only through ``build_artifact``, which refuses a lineage
with a link-only or unusable input before anything is written. Manifests are pure functions of the inputs and
the seed (no wall-clock), so a re-bake of the same release leaves git clean.
"""
from __future__ import annotations

import ast
import functools
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .. import __version__
from .lineage import Lineage, assert_publishable

INDEX_SCHEMA = "contraste.index/v1"
MANIFEST_SCHEMA = "contraste.manifest/v1"
ARTIFACT_SCHEMA = "contraste.case/v1"
MODELS_SCHEMA = "contraste.models/v1"
ROLES = ("models", "variant")
#: a finding's evidence is a test in the artifact, a contract-1 rule of the case's inputs, or a stated design limit
EVIDENCE_PREFIXES = ("contract:", "design:")
#: or a measured rate of the artifact: ``rate:<key>`` names a row of ``outputs.simulations`` (C22, CT-305)
RATE_PREFIX = "rate:"

#: the keys of ``riskvalidation.TestResult.to_dict()`` (riskvalidation 0.1.0), in its order
TEST_RESULT_KEYS = (
    "test_id", "model_id", "segment", "statistic", "p_value", "metric", "h0", "alternative", "policy_version",
    "alpha_amber", "alpha_red", "light", "n", "n_events", "inputs_hash", "reference", "notes", "extras",
)
LIGHTS = ("green", "amber", "red", "not_evaluated", "error")
SEVERITIES = ("S1", "S2", "S3", "S4")
FINDING_STATUSES = ("open", "accepted", "closed")
MODEL_KEYS = ("id", "family", "rung", "title", "short_title", "engine", "engine_version", "licence",
              "checkpoint_sha256", "calibration", "parameters")
LANES = ("live", "precompute")


class ContractViolation(ValueError):
    """A document about to be written does not satisfy contract 2."""


def _text(v: Any, where: str) -> None:
    if not (isinstance(v, Mapping) and set(v) == {"en", "es"} and all(isinstance(v[k], str) and v[k] for k in v)):
        raise ContractViolation(f"{where}: a reader-facing text is {{'en': ..., 'es': ...}}, both non-empty")


def _check_tests(tests: Sequence[Mapping[str, Any]], where: str) -> set[str]:
    ids: set[str] = set()
    for k, row in enumerate(tests):
        keys = tuple(row)
        if set(keys) != set(TEST_RESULT_KEYS):
            missing = sorted(set(TEST_RESULT_KEYS) - set(keys))
            extra = sorted(set(keys) - set(TEST_RESULT_KEYS))
            raise ContractViolation(f"{where}: test row {k} is not a TestResult (missing {missing}, extra {extra})")
        if row["light"] not in LIGHTS:
            raise ContractViolation(f"{where}: test row {k} light {row['light']!r} is not one of {list(LIGHTS)}")
        if not row["reference"] or not row["h0"] or not row["policy_version"]:
            raise ContractViolation(f"{where}: test row {k} ({row['test_id']}) lacks its reference, H0 or policy")
        tid, model = row["test_id"], row.get("model_id")
        ids.add(tid)
        if model is not None:
            ids.add(f"{tid}@{model}")
            if row.get("segment") is not None:
                ids.add(f"{tid}@{model}@{row['segment']}")
    return ids


def _rate_keys(outputs: Mapping[str, Any]) -> set[str]:
    sims = outputs.get("simulations") or []
    return {f"{RATE_PREFIX}{s['key']}" for s in sims if isinstance(s, Mapping) and isinstance(s.get("key"), str)}


def _check_findings(findings: Sequence[Mapping[str, Any]], test_ids: set[str], where: str,
                    rate_keys: frozenset[str] | set[str] = frozenset()) -> None:
    seen: set[str] = set()
    for f in findings:
        if f.get("id") in seen or not f.get("id"):
            raise ContractViolation(f"{where}: every finding has a unique id")
        seen.add(f["id"])
        if f.get("severity") not in SEVERITIES:
            raise ContractViolation(f"{where}: finding {f['id']} severity {f.get('severity')!r} is not S1 to S4")
        if f.get("status") not in FINDING_STATUSES:
            raise ContractViolation(f"{where}: finding {f['id']} status {f.get('status')!r} is not one of {list(FINDING_STATUSES)}")
        _text(f.get("title"), f"{where}: finding {f['id']} title")
        evidence = f.get("evidence") or []
        if not evidence:
            raise ContractViolation(f"{where}: finding {f['id']} names the tests that evidence it")
        unknown = [e for e in evidence if e not in test_ids and e not in rate_keys and not e.startswith(EVIDENCE_PREFIXES)]
        if unknown:
            kind = "rates" if all(e.startswith(RATE_PREFIX) for e in unknown) else "tests"
            raise ContractViolation(f"{where}: finding {f['id']} cites {kind} not in this artifact: {unknown}")


def _check_models(models: Sequence[Mapping[str, Any]], where: str) -> None:
    if not models:
        raise ContractViolation(f"{where}: an artifact records at least one model")
    for m in models:
        missing = [k for k in MODEL_KEYS if k not in m]
        if missing:
            raise ContractViolation(f"{where}: model {m.get('id')} lacks {missing}")
        _text(m["title"], f"{where}: model {m['id']} title")
        for name, p in (m["parameters"] or {}).items():
            if not isinstance(p, Mapping) or set(p) != {"value", "unit"}:
                raise ContractViolation(f"{where}: model {m['id']} parameter {name} is {{'value', 'unit'}}")
            v = p["value"]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ContractViolation(f"{where}: model {m['id']} parameter {name} is a finite number with its unit")


def _check_impact(impact: Mapping[str, Any], where: str) -> None:
    for name, v in impact.items():
        if not isinstance(v, Mapping) or not {"value", "unit", "label"} <= set(v):
            raise ContractViolation(f"{where}: impact {name} is {{'value', 'unit', 'label'}}")
        if v["value"] is not None and not (isinstance(v["value"], (int, float)) and math.isfinite(v["value"])):
            raise ContractViolation(f"{where}: impact {name} is not finite")
        _text(v["label"], f"{where}: impact {name} label")


def build_artifact(
    *,
    case_id: str,
    variant_id: str,
    model: Sequence[Mapping[str, Any]],
    outputs: Mapping[str, Any],
    tests: Sequence[Mapping[str, Any]],
    impact: Mapping[str, Any],
    findings: Sequence[Mapping[str, Any]],
    lineage: Lineage,
    lane: Mapping[str, Any],
) -> dict[str, Any]:
    """The per-variant artifact. Refuses a non-publishable lineage first (CT-002), then checks every block."""
    assert_publishable(lineage)
    where = f"{case_id}/{variant_id}"
    if lineage.case_id != case_id:
        raise ContractViolation(f"{where}: the lineage belongs to {lineage.case_id}")
    _check_models(model, where)
    test_ids = _check_tests(tests, where)
    _check_findings(findings, test_ids, where, _rate_keys(outputs))
    _check_impact(impact, where)
    if lane.get("lane") not in LANES:
        raise ContractViolation(f"{where}: lane {lane.get('lane')!r} is not one of {list(LANES)}")
    return {
        "schema": ARTIFACT_SCHEMA,
        "case_id": case_id,
        "variant_id": variant_id,
        "model": [dict(m) for m in model],
        "outputs": dict(outputs),
        "tests": [dict(t) for t in tests],
        "impact": dict(impact),
        "findings": [dict(f) for f in findings],
        "provenance": lineage.provenance(),
        "lane": dict(lane),
    }


def build_models_artifact(
    *,
    case_id: str,
    fit_id: str,
    model: Sequence[Mapping[str, Any]],
    fit: Mapping[str, Any],
    lineage: Lineage,
    lane: Mapping[str, Any],
) -> dict[str, Any]:
    """The models of one fit (one training sample): every rung's record and internals (points tables, shape
    functions, partial-dependence grids, stability), and how the fit was made (split, sizes, seeds)."""
    assert_publishable(lineage)
    where = f"{case_id}/models-{fit_id}"
    if lineage.case_id != case_id:
        raise ContractViolation(f"{where}: the lineage belongs to {lineage.case_id}")
    _check_models(model, where)
    if lane.get("lane") not in LANES:
        raise ContractViolation(f"{where}: lane {lane.get('lane')!r} is not one of {list(LANES)}")
    return {"schema": MODELS_SCHEMA, "case_id": case_id, "fit_id": fit_id, "model": [dict(m) for m in model],
            "fit": dict(fit), "provenance": lineage.provenance(), "lane": dict(lane)}


#: what a case can depend on: a committed document of another case it reads, or a product module of another case it imports (the engine is implicit, W15-8)
DEPENDENCY_KINDS = ("document", "code")
_CASES_DIR = Path(__file__).resolve().parents[1] / "cases"
#: a document of another case as the producers name it: ``C07/base.json``, or a case manifest, ``manifests/C15.json``
DOCUMENT_REF = re.compile(r"^(?:(C\d\d)/[A-Za-z0-9._-]+\.json|manifests/(C\d\d)\.json)$")
MODULE_REF = re.compile(r"^pipeline\.cases\.c(\d\d)[a-z0-9_.]*$")


def dependency_case(ref: str) -> str:
    """The case a ``depends_on`` reference belongs to (``C07/base.json``, ``manifests/C15.json`` or ``pipeline.cases.c10.fed``)."""
    m = DOCUMENT_REF.match(ref)
    if m:
        return m.group(1) or m.group(2)
    m = MODULE_REF.match(ref)
    if m:
        return f"C{m.group(1)}"
    raise ContractViolation(f"depends_on: {ref!r} is neither a document of a case nor a module of a case")


def case_sources(case_id: str) -> list[Path]:
    """The files of a case's producer: its package ``cases/c<NN>/`` and its flat modules ``cases/c<NN>_*.py``."""
    n = case_id[1:]
    pkg = _CASES_DIR / f"c{n}"
    return [*(sorted(pkg.rglob("*.py")) if pkg.is_dir() else []), *sorted(_CASES_DIR.glob(f"c{n}_*.py"))]


def _import_targets(path: Path, node: ast.ImportFrom | ast.Import) -> list[list[str]]:
    """The dotted modules (as lists of parts) one import statement of ``path`` names, relative imports resolved against the file's package."""
    parts = list(path.relative_to(_CASES_DIR.parents[1]).with_suffix("").parts)     # ['pipeline', 'cases', 'c18', 'fed']
    package = parts[:-1]                                                            # the file's package (for __init__.py, its own directory)
    if isinstance(node, ast.Import):
        return [a.name.split(".") for a in node.names]
    base = package[: len(package) - (node.level - 1)] if node.level else []
    base = base + (node.module.split(".") if node.module else [])
    out = []
    for a in node.names:
        candidate = base + [a.name]
        # ``from ..c10 import fed`` names the module c10.fed when that file or package exists; ``from ..c01_ladder import Rung`` names c01_ladder
        exists = (_CASES_DIR.parents[1] / Path(*candidate)).with_suffix(".py").is_file() or (_CASES_DIR.parents[1] / Path(*candidate)).is_dir()
        out.append(candidate if exists else base)
    return out


def _source_nodes(tree: ast.AST):
    """Every node of a producer's source but the ``DEPENDS_REASONS`` table: its keys name what the producer reads, they are not a read."""
    stack = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "DEPENDS_REASONS":
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


_CASE_ID = re.compile(r"^C\d\d$")
_CASE_PREFIX = re.compile(r"^(C\d\d)/")

#: the flagged occurrences that are not reads (module relative to ``cases/``, the literal): a case id used in a message or a label. Every other flagged
#: occurrence of a producer (a case id, or a string starting with another case's id and a slash that is not a whole document reference, which is how a path
#: built at run time shows in the source) makes ``derive_depends_on`` raise. The scan of the 21 producers found one (U16-P1b fix round).
NOT_READS: dict[tuple[str, str], dict[str, str]] = {
    ("c18/anchors.py", "C17/models-generator.json has no variant "): {
        "en": "The text of the error raised when the C17 generator variant is absent; the document itself is read through the literal C17/models-generator.json.",
        "es": "El texto del error que se levanta cuando falta la variante del generador de C17; el documento se lee mediante el literal C17/models-generator.json."},
}


def scan_source(case_id: str, module: str, source: str) -> tuple[set[str], list[str]]:
    """What one producer module names of other cases: (the documents it names whole, the flagged literals it names otherwise).

    A flagged literal is a string constant equal to another case id, or a string constant or f-string part that starts with another case id and a slash and is
    not a whole document reference: ``derived / "C14" / "x.json"`` and ``f"C15/{name}.json"`` both show so. The derivation cannot say which document such a
    read opens, so it refuses it (``refuse_unnamed``) unless the literal is a label listed in ``NOT_READS``.
    """
    docs: set[str] = set()
    flagged: list[str] = []
    for node in _source_nodes(ast.parse(source)):
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            continue
        v = node.value
        if DOCUMENT_REF.match(v):
            if dependency_case(v) != case_id:
                docs.add(v)
            continue
        m = _CASE_PREFIX.match(v)
        other = v if _CASE_ID.match(v) else (m.group(1) if m else None)
        if other and other != case_id:
            flagged.append(v)
    return docs, flagged


def refuse_unnamed(case_id: str, flagged: Sequence[tuple[str, str]], reasons: Mapping[str, Any]) -> None:
    """Raise, naming the module and the literal, for each flagged occurrence that is neither a reason key nor in ``NOT_READS``."""
    bad = sorted((m, lit) for m, lit in set(flagged) if (m, lit) not in NOT_READS and lit not in reasons)
    if bad:
        shown = "; ".join(f"{m}: {lit!r}" for m, lit in bad)
        raise ContractViolation(
            f"{case_id}: the producer names another case in a way depends_on cannot state as a read ({shown}). Read the document through a literal whole path "
            f"(C07/base.json) and give it a reason, or, if it is a label and not a read, add it to NOT_READS with its reason")


@functools.lru_cache(maxsize=None)
def _reads(case_id: str) -> tuple[frozenset[str], frozenset[str], frozenset[tuple[str, str]]]:
    docs: set[str] = set()
    mods: set[str] = set()
    flagged: set[tuple[str, str]] = set()
    for path in case_sources(case_id):
        source = path.read_text(encoding="utf-8")
        for node in _source_nodes(ast.parse(source)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for target in _import_targets(path, node):
                    ref = ".".join(target)
                    if MODULE_REF.match(ref) and dependency_case(ref) != case_id:
                        mods.add(ref)
        d, f = scan_source(case_id, path.relative_to(_CASES_DIR).as_posix(), source)
        docs |= d
        flagged |= {(path.relative_to(_CASES_DIR).as_posix(), lit) for lit in f}
    return frozenset(docs), frozenset(mods), frozenset(flagged)


def derive_depends_on(case_id: str, reasons: Mapping[str, Mapping[str, str]]) -> list[dict[str, Any]]:
    """The ``depends_on`` list of a case, built from what its producer reads: the committed documents of other cases that its sources name (a string
    literal ``C07/base.json`` or ``manifests/C15.json``) and the modules of other cases they import. ``reasons`` gives the bilingual reason of each,
    keyed by the document reference or the module name: a read without a reason, or a reason for something the producer does not read, is refused, so a
    list cannot drift from the code. A path to another case's document built at run time (``derived / "C14" / name``, ``f"C15/{name}.json"``) cannot be
    named, so it is refused too (``refuse_unnamed``). Sorted by kind then reference; an empty list says the case reads nothing of another case."""
    docs, mods, flagged = _reads(case_id)
    refuse_unnamed(case_id, sorted(flagged), reasons)
    read = docs | mods
    missing = sorted(read - set(reasons))
    if missing:
        raise ContractViolation(f"{case_id}: no reason is stated for what the producer reads: {missing}")
    extra = sorted(set(reasons) - read)
    if extra:
        raise ContractViolation(f"{case_id}: a reason is stated for what the producer does not read (not read: {extra})")
    out = [{"kind": "document" if ref in docs else "code", "ref": ref, "reason": dict(reasons[ref])} for ref in read]
    out.sort(key=lambda d: (d["kind"], d["ref"]))
    _check_depends_on(case_id, out)
    return out


def _check_depends_on(case_id: str, depends_on: Sequence[Mapping[str, Any]]) -> None:
    keys = []
    for d in depends_on:
        if set(d) != {"kind", "ref", "reason"} or d["kind"] not in DEPENDENCY_KINDS:
            raise ContractViolation(f"{case_id}: a depends_on entry is {{kind in {list(DEPENDENCY_KINDS)}, ref, reason}}")
        if (d["kind"] == "document") != bool(DOCUMENT_REF.match(d["ref"])) or dependency_case(d["ref"]) == case_id:
            raise ContractViolation(f"{case_id}: depends_on {d['ref']!r} is not a {d['kind']} of another case")
        _text(d["reason"], f"{case_id} depends_on {d['ref']} reason")
        keys.append((d["kind"], d["ref"]))
    if keys != sorted(set(keys)):
        raise ContractViolation(f"{case_id}: depends_on is sorted by kind then ref, without repeats")


def add_depends_on(manifest: Mapping[str, Any], depends_on: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """A committed manifest with its ``depends_on`` stated (the manifests-only step): the other fields are untouched, the list goes where
    ``build_case_manifest`` puts it (last)."""
    _check_depends_on(manifest["case_id"], depends_on)
    out = {k: v for k, v in manifest.items() if k != "depends_on"}
    out["depends_on"] = [dict(d, reason=dict(d["reason"])) for d in depends_on]
    return out


def build_case_manifest(
    *,
    case_id: str,
    title: Mapping[str, str],
    category: Mapping[str, str],
    question: Mapping[str, str],
    sources: Sequence[str],
    seed: int,
    variants: Sequence[Mapping[str, Any]],
    default_variant: str,
    contract: Mapping[str, Any],
    expect: Mapping[str, Sequence[float]],
    riskvalidation_version: str | None,
    depends_on: Sequence[Mapping[str, Any]],
    source_details: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """The case manifest. ``variants`` are the artifact entries: ``{role, variant_id, title, short_title, regime,
    truth_status, path, bytes, lane, gate}``, with ``models_ref`` (the path of a models entry) on every variant entry.
    ``short_title`` is the label a chip shows; ``title`` the full name. ``depends_on`` is what the producer reads of other cases
    (``derive_depends_on``), possibly empty."""
    _check_depends_on(case_id, depends_on)
    for name, v in (("title", title), ("category", category), ("question", question)):
        _text(v, f"{case_id} {name}")
    if any(v.get("role") not in ROLES for v in variants):
        raise ContractViolation(f"{case_id}: every artifact entry has a role in {list(ROLES)}")
    var = [v for v in variants if v["role"] == "variant"]
    if not var:
        raise ContractViolation(f"{case_id}: a case has at least one variant")
    ids = [v["variant_id"] for v in variants]
    if len(set(ids)) != len(ids):
        raise ContractViolation(f"{case_id}: variant ids repeat")
    if default_variant not in [v["variant_id"] for v in var]:
        raise ContractViolation(f"{case_id}: the default variant {default_variant!r} is not among the variants")
    model_paths = {v["path"] for v in variants if v["role"] == "models"}
    for v in variants:
        _text(v["title"], f"{case_id}/{v['variant_id']} title")
        _text(v.get("short_title"), f"{case_id}/{v['variant_id']} short_title")
        _text(v["regime"], f"{case_id}/{v['variant_id']} regime")
        if v.get("lane") not in LANES or (v.get("gate") or {}).get("lane") != v.get("lane"):
            raise ContractViolation(f"{case_id}/{v['variant_id']}: the lane and the gate verdict disagree")
        if v["role"] == "variant" and v.get("models_ref") not in model_paths:
            raise ContractViolation(f"{case_id}/{v['variant_id']}: models_ref names no models artifact of this case")
    if not expect:
        raise ContractViolation(f"{case_id}: no expected range declared (every case states what a reader should see)")
    missing = [s for s in sources if s not in (source_details or {})]
    if missing:
        raise ContractViolation(f"{case_id}: no registry details for the sources {missing}")
    return {
        "schema": MANIFEST_SCHEMA,
        "case_id": case_id,
        "title": dict(title),
        "category": dict(category),
        "question": dict(question),
        "sources": list(sources),
        "source_details": {k: dict(v) for k, v in (source_details or {}).items()},
        "seed": seed,
        "engine": {"pipeline": __version__, "riskvalidation": riskvalidation_version},
        "default_variant": default_variant,
        "artifacts": [dict(v) for v in variants],
        "contract": dict(contract),
        "expect": {k: [float(lo), float(hi)] for k, (lo, hi) in sorted(expect.items())},
        "depends_on": [dict(d, reason=dict(d["reason"])) for d in depends_on],
    }


def build_index(entries: Sequence[Mapping[str, Any]], default_case: str, files: Sequence[str] = ()) -> dict[str, Any]:
    """entries: ``[{case_id, title, category, category_id, manifest_path}]``: the flat inventory, with the case the
    App opens on. ``files`` are the further files the site serves (the contract-1 declarations)."""
    if default_case not in {e["case_id"] for e in entries}:
        raise ContractViolation(f"default case {default_case!r} is not among the baked cases")
    return {
        "schema": INDEX_SCHEMA,
        "engine_version": __version__,
        "n_cases": len(entries),
        "default_case": default_case,
        "cases": sorted((dict(e) for e in entries), key=lambda e: e["case_id"]),
        "files": list(files),
    }
