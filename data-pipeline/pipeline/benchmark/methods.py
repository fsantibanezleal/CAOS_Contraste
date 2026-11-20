"""The methods-compared step (BL-113 T2): ``python -m pipeline.benchmark.methods`` from ``data-pipeline/``.

It reads the committed case documents (``data/derived/``) and the committed manuscript result files (``manuscripts/*/experiments/``) and
copies each method's metrics, question by question, into ``data/derived/benchmark/methods-compared.json`` with the repository path, the JSON
pointer and the SHA-256 of the file each value was copied from (ADR-0080, contract ``benchmark-methods``). It computes nothing: a cell the
product does not have is null with its reason and the backlog row that fills it.

Three rules the tests hold:

* A method's standing (``established``, ``recent`` or ``proposed``) is read from the tier column of the SDD ``## Method ladder`` table by its
  ladder id, as ``scripts/check_sdd.py`` parses the table (``classical``, ``sota``, ``beyond``); it is never typed per row. A row without a
  ladder row is ``reference``: a comparator that runs on the protocol and has no method row of its own.
* Each question's ``reading`` and ``standings`` are generated from its numbers by the declared rule of each metric (``lower``, ``higher``,
  ``nearer:<value>``, ``nearer-metric:<metric>``, ``order:<best>,...``, or ``none``): the best method per metric and column, ties stated,
  a null never ranked.
* Within a question every metric belongs to one run (one protocol and one seed); the files a run cites are never cited by another run.

The tier words never reach a text of the document (``scripts/check_internal_names.py``); the ladder id stays in the data for the tests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from ..core.lineage import TRUTH_STATUSES
from . import METHODS_REL, SCHEMA_TAG, SUMS_REL

REPO_ROOT = Path(__file__).resolve().parents[3]
SDD_REL = "docs/design/SDD.md"
DERIVED_REL = "data/derived"
SCHEMA_VERSION = "2.0.0"
GENERATORS = ["contraste:benchmark-methods"]
TIER_STANDING = {"classical": "established", "sota": "recent", "beyond": "proposed"}
STANDING_ORDER = {"established": 0, "recent": 1, "proposed": 2, "reference": 3}


def T(en: str, es: str) -> dict[str, str]:
    return {"en": en, "es": es}


class BenchmarkError(Exception):
    """The document cannot be built: a cited file or path is absent, a ladder row is missing, or a rule is broken."""


# --- the ladder (the standing of a method is read here, never typed) ---------------------------------------------------------------------


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def read_ladder(root: Path = REPO_ROOT) -> tuple[dict[str, dict[str, str]], str]:
    """``({ladder id: {"tier", "method"}}, digest)`` of the SDD ``## Method ladder`` table, the digest taken over the normalised rows."""
    text = (Path(root) / SDD_REL).read_text(encoding="utf-8").replace("\r\n", "\n")
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if re.match(r"^##\s+Method ladder\s*$", ln)), None)
    if start is None:
        raise BenchmarkError(f"{SDD_REL} has no '## Method ladder' section")
    rows: dict[str, dict[str, str]] = {}
    for ln in lines[start + 1:]:
        if re.match(r"^##\s", ln):
            break
        if not ln.startswith("|"):
            continue
        cells = _cells(ln)
        if cells[0].lower() == "id" or set(cells[0]) <= set("-: "):
            continue
        if len(cells) != 5:
            raise BenchmarkError(f"{SDD_REL} Method ladder row {cells[0]!r} has {len(cells)} cells, the table has 5")
        rows[cells[0]] = {"tier": cells[1].lower(), "method": cells[2]}
    if not rows:
        raise BenchmarkError(f"{SDD_REL} Method ladder has no rows")
    digest = hashlib.sha256("\n".join(f"{k}|{v['tier']}|{v['method']}" for k, v in sorted(rows.items())).encode("utf-8")).hexdigest()
    return rows, digest


def standing_of(ladder: dict[str, dict[str, str]], ladder_id: str | None) -> str:
    """``established``, ``recent`` or ``proposed`` from the ladder row; ``reference`` when the row has no ladder id. An id the SDD lacks stops the build."""
    if ladder_id is None:
        return "reference"
    row = ladder.get(ladder_id)
    if row is None:
        raise BenchmarkError(f"the ladder id {ladder_id} has no row in {SDD_REL} Method ladder: its standing is not guessed")
    standing = TIER_STANDING.get(row["tier"])
    if standing is None:
        raise BenchmarkError(f"the ladder row {ladder_id} has the tier {row['tier']!r}")
    if standing == "proposed" and not row["method"].lower().startswith("proposed method"):
        raise BenchmarkError(f"the ladder row {ladder_id} is a measurement, not a proposed method: it has no standing in a comparison")
    return standing


def proposed_ids(ladder: dict[str, dict[str, str]]) -> list[str]:
    return sorted((k for k, v in ladder.items() if v["tier"] == "beyond" and v["method"].lower().startswith("proposed method")),
                  key=lambda k: int(k.split("-")[1]))


# --- the cited files and the paths -------------------------------------------------------------------------------------------------------


def sha256_of(path: Path) -> str:
    """SHA-256 of the file with line endings normalised to LF (a Windows checkout hashes as a Linux one)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _esc(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def pointer_get(doc: Any, pointer: str) -> Any:
    """The value at an RFC 6901 pointer; raises ``KeyError`` when the path is absent."""
    if pointer == "":
        return doc
    node = doc
    for raw in pointer.split("/")[1:]:
        tok = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, list):
            node = node[int(tok)]
        elif isinstance(node, dict):
            node = node[tok]
        else:
            raise KeyError(pointer)
    return node


def _split(template: str) -> list[tuple[str, Any]]:
    """The steps of a path template: ``("key", name)``, ``("index", n)`` or ``("select", {field: value})``.

    Grammar: dotted keys; ``[n]`` an array index; ``[k=v,k2=v2]`` the one array element whose fields equal the values; ``['key']`` a literal key."""
    steps: list[tuple[str, Any]] = []
    i, n, key = 0, len(template), ""
    while i < n:
        ch = template[i]
        if ch == ".":
            if key:
                steps.append(("key", key))
                key = ""
            i += 1
        elif ch == "[":
            if key:
                steps.append(("key", key))
                key = ""
            if template[i + 1] == "'":
                end = template.index("']", i + 2)
                steps.append(("key", template[i + 2:end]))
                i = end + 2
            else:
                end = template.index("]", i)
                body = template[i + 1:end]
                if re.fullmatch(r"\d+", body):
                    steps.append(("index", int(body)))
                else:
                    pairs = {}
                    for part in body.split(","):
                        k, _, v = part.partition("=")
                        pairs[k] = v
                    steps.append(("select", pairs))
                i = end + 1
        else:
            key += ch
            i += 1
    if key:
        steps.append(("key", key))
    return steps


def _same(value: Any, text: str) -> bool:
    if isinstance(value, bool):
        return str(value).lower() == text.lower()
    if isinstance(value, (int, float)):
        try:
            return float(text) == float(value)
        except ValueError:
            return False
    return str(value) == text


def resolve(doc: Any, template: str) -> tuple[Any, str]:
    """``(value, pointer)`` of a path template in a document.

    A null met on the way (the parent of the wanted key is null) returns ``(None, pointer of that null)``; a key or an element that does not
    exist raises :class:`BenchmarkError`, so a document that moved never passes as a null."""
    node, pointer = doc, ""
    for kind, arg in _split(template):
        if node is None:
            return None, pointer
        if kind == "key":
            if not isinstance(node, dict) or arg not in node:
                raise BenchmarkError(f"the path {template!r} has no key {arg!r} at {pointer or '/'}")
            node, pointer = node[arg], f"{pointer}/{_esc(arg)}"
        elif kind == "index":
            if not isinstance(node, list) or arg >= len(node):
                raise BenchmarkError(f"the path {template!r} has no index {arg} at {pointer or '/'}")
            node, pointer = node[arg], f"{pointer}/{arg}"
        else:
            if not isinstance(node, list):
                raise BenchmarkError(f"the path {template!r} selects {arg} in a non-list at {pointer or '/'}")
            hits = [(j, el) for j, el in enumerate(node) if isinstance(el, dict) and all(k in el and _same(el[k], v) for k, v in arg.items())]
            if len(hits) != 1:
                raise BenchmarkError(f"the path {template!r} selects {arg} and finds {len(hits)} elements at {pointer or '/'}")
            node, pointer = hits[0][1], f"{pointer}/{hits[0][0]}"
    return node, pointer


class Corpus:
    """The files read, each parsed once, with its repository path and hash."""

    def __init__(self, root: Path = REPO_ROOT):
        self.root = Path(root)
        self._docs: dict[str, tuple[Any, str]] = {}

    def load(self, rel: str) -> tuple[Any, str]:
        if rel not in self._docs:
            path = self.root / rel
            if not path.is_file():
                raise BenchmarkError(f"the cited file {rel} is not committed")
            self._docs[rel] = (json.loads(path.read_text(encoding="utf-8")), sha256_of(path))
        return self._docs[rel]

    def documents(self) -> list[dict[str, str]]:
        return [{"path": rel, "sha256": sha} for rel, (_, sha) in sorted(self._docs.items())]


# --- ranking: the declared rule of a metric ----------------------------------------------------------------------------------------------


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def best_of(better: str, values: dict[str, Any], reference: float | None = None) -> tuple[list[str], Any] | None:
    """The best row ids (ties kept) and their value among ``values`` ({row id: value}) under the rule ``better``; ``None`` when nothing is rankable.

    ``lower`` and ``higher`` compare the numbers; ``nearer:<x>`` and ``nearer-metric:<m>`` (``reference`` is the column's value of ``m``) the distance to
    the target; ``order:<a>,<b>,...`` the position in the list (a value outside it is not ranked); ``none`` ranks nothing. A null is never ranked."""
    live = {k: v for k, v in values.items() if v is not None}
    if better == "none" or not live:
        return None
    if better.startswith("order:"):
        order = better[len("order:"):].split(",")
        scored = {k: order.index(v) for k, v in live.items() if isinstance(v, str) and v in order}
        if not scored:
            return None
        top = min(scored.values())
        return [k for k in values if scored.get(k) == top], order[top]
    nums = {k: float(v) for k, v in live.items() if _is_num(v)}
    if not nums:
        return None
    if better == "lower":
        key = {k: v for k, v in nums.items()}
    elif better == "higher":
        key = {k: -v for k, v in nums.items()}
    elif better.startswith("nearer:") or better.startswith("nearer-metric:"):
        target = float(better.split(":", 1)[1]) if better.startswith("nearer:") else reference
        if target is None:
            return None
        key = {k: abs(v - target) for k, v in nums.items()}
    else:
        raise BenchmarkError(f"the rule {better!r} is not declared")
    top = min(key.values())
    winners = [k for k in values if k in key and key[k] == top]
    return winners, live[winners[0]]


# The Spanish word of an ordered category in the text of a rule (the cells keep the ids; the page names them).
CATEGORY_ES = {"green": "verde", "amber": "ámbar", "red": "rojo"}


def rule_text(better: str, ref_label: dict[str, str] | None = None) -> dict[str, str]:
    if better == "lower":
        return T("lower is better", "menor es mejor")
    if better == "higher":
        return T("higher is better", "mayor es mejor")
    if better.startswith("nearer:"):
        x = better.split(":", 1)[1]
        return T(f"nearer {x} is better", f"más cerca de {x.replace('.', ',')} es mejor")
    if better.startswith("nearer-metric:"):
        lab = ref_label or T("the reference", "la referencia")
        return T(f"nearer {lab['en']} is better", f"más cerca de {lab['es']} es mejor")
    if better.startswith("order:"):
        order = better[len("order:"):].split(",")
        es = [CATEGORY_ES.get(c, c) for c in order]
        return T(f"{order[0]} is best, then {', '.join(order[1:])}", f"{es[0]} es lo mejor, luego {', '.join(es[1:])}")
    return T("context, not ranked", "contexto, sin clasificar")


# --- the specification is data; the build turns it into the document ----------------------------------------------------------------------


class Null:
    """A cell the product does not have: null with its reason, no citation."""

    def __init__(self, reason: dict[str, str]):
        self.reason = reason


def fill(template: str, subs: dict[str, str]) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: str(subs[m.group(1)]), template)


def _ladder_key(ladder_id: str | None) -> tuple[int, int]:
    if ladder_id is None:
        return (9, 0)
    prefix, _, num = ladder_id.partition("-")
    return (0 if prefix == "M" else 1, int(num))


def _cite(corpus: Corpus, rel: str, pointer: str) -> dict[str, str]:
    return {"path": rel, "pointer": pointer, "sha256": corpus.load(rel)[1]}


#: The notes a case document gives for a test it does not evaluate, in Spanish (an unknown note stops the build: no reason is guessed).
NOTE_ES = {"not evaluated: no exceedance": "no evaluado: sin excesos"}


def _note_reason(doc: Any, pointer: str, metric: dict[str, Any]) -> dict[str, str] | None:
    """The reason a null p-value cell gives: the ``notes`` the case document itself writes beside it (metrics with ``note_reason`` only)."""
    if not metric.get("note_reason"):
        return None
    parent = pointer_get(doc, pointer.rsplit("/", 1)[0])
    note = (parent.get("notes") or "").strip() if isinstance(parent, dict) else ""
    if not note:
        return None
    if note not in NOTE_ES:
        raise BenchmarkError(f"the case document's note {note!r} has no Spanish text in NOTE_ES: the reason is not guessed")
    return T(f"the case document gives no p-value for this model in this window and states: {note}",
             f"el documento del caso no trae un valor p para este modelo en esta ventana e indica: {NOTE_ES[note]}")


def build_cells(q: dict[str, Any], corpus: Corpus) -> dict[str, list[dict[str, Any]]]:
    """``{row id: cells}``: every cell copied from its cited path, or null with its reason."""
    runs = {r["id"]: r for r in q["runs"]}
    out: dict[str, list[dict[str, Any]]] = {}
    for row in q["rows"]:
        cells: list[dict[str, Any]] = []
        for metric in q["metrics"]:
            spec = row["cells"].get(metric["id"])
            if spec is None:
                continue
            run = runs[metric["run"]]
            cols = {c["id"]: c for c in run["columns"]}
            for col_id in metric["columns"]:
                col = cols[col_id]
                subs = {"v": col_id, **{k: v for k, v in col.items() if k not in ("id", "label")}}
                cell: dict[str, Any] = {"metric": metric["id"], "column": col_id, "value": None, "null_reason": None, "cited": None}
                if isinstance(spec, Null):
                    cell["null_reason"] = spec.reason
                else:
                    file_tpl, ptr_tpl = spec if isinstance(spec, tuple) else (row.get("file") or metric["file"], spec)
                    rel = fill(file_tpl, subs)
                    doc, _ = corpus.load(rel)
                    try:
                        value, pointer = resolve(doc, fill(ptr_tpl, subs))
                    except BenchmarkError as exc:
                        raise BenchmarkError(f"{q['id']} {row['id']} {metric['id']} {col_id}: {rel}: {exc}") from exc
                    cell["value"] = value
                    cell["cited"] = _cite(corpus, rel, pointer)
                    if value is None:
                        cell["null_reason"] = (row.get("null_reasons", {}).get(metric["id"]) or _note_reason(doc, pointer, metric) or metric.get("null_reason")
                                               or T("the committed document holds no value here", "el documento versionado no trae un valor aquí"))
                cells.append(cell)
        out[row["id"]] = cells
    return out


def truth_status_of(q_id: str, run: dict[str, Any], files: list[str], corpus: Corpus) -> str:
    """The truth status of the data a run rests on, copied from the case documents it cites (``provenance.truth_status``) and never typed.

    A run that cites case documents takes their one status; documents that disagree, a document without a status or with one outside the closed
    list, and a declared status on such a run stop the build. The manuscript result files state no status, so a run that cites only those declares
    it in the specification (``"truth": (status, reason)``); a run that cites both kinds takes the case documents' status and its declared one must
    equal it."""
    where = f"{q_id} {run['id']}"
    declared = run.get("truth")
    if declared is not None and declared[0] not in TRUTH_STATUSES:
        raise BenchmarkError(f"{where}: the declared truth status {declared[0]!r} is not in the closed list {list(TRUTH_STATUSES)}")
    case_files = [f for f in files if f.startswith(f"{DERIVED_REL}/")]
    other_files = [f for f in files if f not in case_files]
    if not files:
        raise BenchmarkError(f"{where}: the run cites no file, so it has no truth status to copy")
    if not case_files:
        if declared is None:
            raise BenchmarkError(f"{where}: the run cites only manuscript result files, which state no truth status: the specification must declare one with its reason")
        return declared[0]
    by_status: dict[str, list[str]] = {}
    for rel in case_files:
        doc, _ = corpus.load(rel)
        status = (doc.get("provenance") or {}).get("truth_status") if isinstance(doc, dict) else None
        if status not in TRUTH_STATUSES:
            raise BenchmarkError(f"{where}: the case document {rel} states the truth status {status!r}, not one of {list(TRUTH_STATUSES)}")
        by_status.setdefault(status, []).append(rel)
    if len(by_status) > 1:
        raise BenchmarkError(f"{where}: the case documents it cites state different truth statuses: " + "; ".join(f"{s}: {', '.join(fs)}" for s, fs in sorted(by_status.items())))
    status = next(iter(by_status))
    if declared is not None and not other_files:
        raise BenchmarkError(f"{where}: the run cites only case documents and must not declare a truth status: the copied value ({status}) is the only source")
    if declared is not None and declared[0] != status:
        raise BenchmarkError(f"{where}: the declared truth status {declared[0]} differs from the status of the case documents it cites ({status})")
    return status


def build_run(run: dict[str, Any], q: dict[str, Any], rows_cells: dict[str, list[dict[str, Any]]], corpus: Corpus) -> dict[str, Any]:
    metric_run = {m["id"]: m["run"] for m in q["metrics"]}
    files = sorted({c["cited"]["path"] for cs in rows_cells.values() for c in cs if c["cited"] and metric_run[c["metric"]] == run["id"]})
    seed = None
    if run.get("seed"):
        file_tpl, ptr_tpl = run["seed"]
        first = run["columns"][0]
        subs = {"v": first["id"], **{k: v for k, v in first.items() if k not in ("id", "label")}}
        rel = fill(file_tpl, subs)
        doc, _ = corpus.load(rel)
        try:
            value, pointer = resolve(doc, fill(ptr_tpl, subs))
        except BenchmarkError:
            value, pointer = None, ""
        if value is not None:
            seed = {"value": value, "cited": _cite(corpus, rel, pointer)}
    return {"id": run["id"], "label": run["label"], "protocol": run["protocol"], "seed": seed, "files": files,
            "truth_status": truth_status_of(q["id"], run, files, corpus),
            "columns":[{"id": c["id"], "label": c["label"]} for c in run["columns"]]}


def standings_of(metrics: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The best method per metric and column by the metric's declared rule, from the cells as written (the tests recompute it the same way)."""
    out = []
    ranked = {r["id"] for r in rows if r["ranked"]}
    by_metric: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        for c in r["cells"]:
            by_metric.setdefault(c["metric"], {}).setdefault(c["column"], {})[r["id"]] = c["value"]
    for m in metrics:
        if m["better"] == "none":
            continue
        for col in m["columns"]:
            cell_vals = by_metric.get(m["id"], {}).get(col, {})
            values = {rid: v for rid, v in cell_vals.items() if rid in ranked}
            ref = None
            if m["better"].startswith("nearer-metric:"):
                ref_m = m["better"].split(":", 1)[1]
                refs = [v for v in by_metric.get(ref_m, {}).get(col, {}).values() if _is_num(v)]
                ref = float(refs[0]) if refs else None
            res = best_of(m["better"], values, ref)
            if res is not None:
                best, value = res
                out.append({"metric": m["id"], "column": col, "best": best, "value": value, "tie": len(best) > 1,
                            "n_ranked": sum(1 for v in values.values() if v is not None)})
    return out


def _full_stop(text: str) -> str:
    """The text ending in a full stop (a note of a row is a clause with none; the reading joins sentences)."""
    t = text.strip()
    return t if t.endswith((".", "?", "!")) else t + "."


def reading_of(metrics: list[dict[str, Any]], rows: list[dict[str, Any]], standings: list[dict[str, Any]]) -> dict[str, str]:
    """The reading in words, generated from the standings: the method that does best on each metric, how often, and where a proposed method stands."""
    name = {r["id"]: r["method"] for r in rows}
    en: list[str] = []
    es: list[str] = []
    labels = {m["id"]: m["label"] for m in metrics}
    for m in metrics:
        if m["better"] == "none":
            continue
        st = [s for s in standings if s["metric"] == m["id"]]
        if not st:
            continue
        wins: dict[str, int] = {}
        for s in st:
            for b in s["best"]:
                wins[b] = wins.get(b, 0) + 1
        order = [r["id"] for r in rows]
        top = sorted(wins, key=lambda k: (-wins[k], order.index(k)))[:3]
        ties = any(s["tie"] for s in st)
        ref_label = labels.get(m["better"].split(":", 1)[1]) if m["better"].startswith("nearer-metric:") else None
        rule = rule_text(m["better"], ref_label)
        n = len(st)
        en.append(f"{m['label']['en']} ({rule['en']}): best in " + ", ".join(f"{name[k]['en']} {wins[k]} of {n}" for k in top)
                  + ("; ties count for each method tied." if ties else "."))
        es.append(f"{m['label']['es']} ({rule['es']}): mejor en " + ", ".join(f"{name[k]['es']} {wins[k]} de {n}" for k in top)
                  + ("; los empates cuentan para cada método empatado." if ties else "."))
    for r in rows:
        if r["standing"] != "proposed":
            continue
        if not r["ranked"]:
            en.append(f"{r['method']['en']}, proposed in this work, is not ranked: " + _full_stop(r["note"]["en"] if r["note"] else "it has no score on these metrics."))
            es.append(f"{r['method']['es']}, propuesto en este trabajo, no se clasifica: " + _full_stop(r["note"]["es"] if r["note"] else "no tiene puntaje en estas métricas."))
            continue
        scored = [s for s in standings if any(c["metric"] == s["metric"] and c["column"] == s["column"] and c["value"] is not None for c in r["cells"])]
        won = [s for s in scored if r["id"] in s["best"]]
        if not scored:
            en.append(f"{r['method']['en']}, proposed in this work, has no scored cell: it is not ranked.")
            es.append(f"{r['method']['es']}, propuesto en este trabajo, no tiene una celda con puntaje: no se clasifica.")
        else:
            en.append(f"{r['method']['en']}, proposed in this work, is best in {len(won)} of {len(scored)} scored cells and not best in {len(scored) - len(won)}.")
            es.append(f"{r['method']['es']}, propuesto en este trabajo, es el mejor en {len(won)} de {len(scored)} celdas con puntaje y no es el mejor en {len(scored) - len(won)}.")
    en.append("A null cell is never ranked; each states why it is null.")
    es.append("Una celda nula nunca se clasifica; cada una dice por qué es nula.")
    return {"en": " ".join(en), "es": " ".join(es)}


CONCEPT_DOI_MACRO = re.compile(r"\\newcommand\{\\conceptdoi\}\{([^}]+)\}")


def concept_doi(manuscript: str, root: Path = REPO_ROOT) -> str:
    """The concept DOI a manuscript's ``\\conceptdoi`` macro defines, checked against exactly one ``product.json`` ``manuscripts`` entry."""
    tex = Path(root) / manuscript
    if not tex.is_file():
        raise BenchmarkError(f"the manuscript {manuscript} is not committed")
    found = CONCEPT_DOI_MACRO.search(tex.read_text(encoding="utf-8"))
    if found is None:
        raise BenchmarkError(f"{manuscript} defines no \\conceptdoi macro: its concept DOI is not guessed")
    doi = found.group(1).strip()
    product = json.loads((Path(root) / "product.json").read_text(encoding="utf-8"))
    entries = [m for m in product.get("manuscripts", []) if m.get("concept_doi") == doi]
    if len(entries) != 1:
        raise BenchmarkError(f"{manuscript} defines the concept DOI {doi}, which is in {len(entries)} entries of product.json manuscripts (exactly one is required)")
    return doi


def build_negative_results(q: dict[str, Any], corpus: Corpus) -> list[dict[str, Any]]:
    """Each negative result with the concept DOI of its manuscript (the reader sees the published title and DOI, not the file path)."""
    return [{"rows": n["rows"], "manuscript": n["manuscript"], "concept_doi": concept_doi(n["manuscript"], corpus.root), "text": n["text"]}
            for n in q.get("negative_results", [])]


def build_question(q: dict[str, Any], corpus: Corpus, ladder: dict[str, dict[str, str]]) -> dict[str, Any]:
    cells = build_cells(q, corpus)
    rows = []
    for r in q["rows"]:
        src = SOURCES[r["source"]] if r.get("source") else None
        rows.append({
            "id": r["id"], "method": r["method"], "ladder_id": r["ladder"], "standing": standing_of(ladder, r["ladder"]),
            "ranked": r["ranked"], "note": r.get("note"),
            "source": None if src is None else {"text": src["text"], "url": src.get("url")},
            "year": None if src is None else src.get("year"),
            "cells": cells[r["id"]],
        })
    rows.sort(key=lambda r: (STANDING_ORDER[r["standing"]], _ladder_key(r["ladder_id"]), r["id"]))
    metrics = [{"id": m["id"], "label": m["label"], "run_id": m["run"], "better": m["better"], "unit": m["unit"], "columns": m["columns"]} for m in q["metrics"]]
    standings = standings_of(metrics, rows)
    absent = [{"method": a["method"], "ladder_id": a.get("ladder"), "standing": standing_of(ladder, a["ladder"]) if a.get("ladder") else None,
               "reason": a["reason"], "backlog": a.get("backlog")} for a in q.get("absent", [])]
    return {
        "id": q["id"], "title": q["title"], "case_ids": q["case_ids"], "protocol": q["protocol"],
        "runs": [build_run(run, q, cells, corpus) for run in q["runs"]],
        "metrics": metrics, "rows": rows, "absent": absent, "standings": standings,
        "reading": reading_of(metrics, rows, standings),
        "negative_results": build_negative_results(q, corpus),
    }


def build(root: Path = REPO_ROOT) -> dict[str, Any]:
    """The whole document, built in memory from the committed files."""
    ladder, ladder_digest = read_ladder(root)
    corpus = Corpus(root)
    questions = [build_question(q, corpus, ladder) for q in QUESTIONS]
    questions.sort(key=lambda q: int(q["id"][1:]))
    for item in LEFT_OUT:
        standing_of(ladder, item["ladder"])
    version = (Path(root) / "VERSION").read_text(encoding="utf-8").strip()
    return {
        "schema": SCHEMA_TAG,
        "case_id": "BENCHMARK-METHODS",
        "schema_version": SCHEMA_VERSION,
        "provenance": {
            "code_version": version,
            "generators": GENERATORS,
            "ladder": {"path": SDD_REL, "rows_sha256": ladder_digest},
            "documents": corpus.documents(),
            "hash_rule": "SHA-256 of the file with line endings normalised to LF",
        },
        "questions": questions,
        "left_out": [{"ladder_id": i["ladder"], "method": i["method"], "reason": i["reason"], "backlog": i["backlog"]} for i in LEFT_OUT],
        "not_built": NOT_BUILT,
    }


def serialise(doc: dict[str, Any]) -> bytes:
    """Compact JSON, UTF-8, LF, no trailing newline (the form of every other committed document)."""
    return json.dumps(doc, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def bake(output_root: Path | str, root: Path = REPO_ROOT) -> dict[str, str]:
    """Build and write ``<output_root>/benchmark/`` (the document and SHA256SUMS.txt); returns the path to sha256 map."""
    data = serialise(build(root))
    sums = {METHODS_REL: hashlib.sha256(data).hexdigest()}
    out = Path(output_root)
    (out / METHODS_REL).parent.mkdir(parents=True, exist_ok=True)
    (out / METHODS_REL).write_bytes(data)
    (out / SUMS_REL).write_bytes("".join(f"{sha}  {rel}\n" for rel, sha in sorted(sums.items())).encode("utf-8"))
    return sums


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Bake data/derived/benchmark/methods-compared.json from the committed case documents and manuscript results")
    ap.add_argument("--output-root", default=str(REPO_ROOT / DERIVED_REL), help="the derived-data root (default data/derived of this repository)")
    args = ap.parse_args(argv)
    sums = bake(args.output_root)
    print(f"wrote {len(sums)} document under {Path(args.output_root) / 'benchmark'}", file=sys.stderr)
    return 0


# --- the specification: the questions, their runs, metrics and methods ---------------------------------------------------------------------
# (kept at the end of the module: the data below is read only by build())


def col(cid: str, en: str, es: str, **extra: str) -> dict[str, str]:
    return {"id": cid, "label": T(en, es), **extra}


SOURCES: dict[str, dict[str, Any]] = {
    "kupiec": {"text": "Kupiec (1995)", "url": "https://doi.org/10.3905/jod.1995.407942", "year": 1995},
    "christoffersen": {"text": "Christoffersen (1998)", "url": "https://doi.org/10.2307/2527341", "year": 1998},
    "pritsker": {"text": "Pritsker (2001)", "url": "https://www.federalreserve.gov/Pubs/feds/2001/200127/200127pap.pdf", "year": 2001},
    "boudoukh": {"text": "Boudoukh, Richardson and Whitelaw (1998)", "url": "https://pages.stern.nyu.edu/~rwhitela/papers/hybrid%20risk98.pdf", "year": 1998},
    "riskmetrics": {"text": "RiskMetrics Technical Document (1996)", "url": "https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a", "year": 1996},
    "cornish": {"text": "Cornish and Fisher (1938)", "url": "https://doi.org/10.2307/1400905", "year": 1938},
    "bollerslev": {"text": "Bollerslev (1986)", "url": "https://doi.org/10.1016/0304-4076(86)90063-1", "year": 1986},
    "glosten": {"text": "Glosten, Jagannathan and Runkle (1993)", "url": "https://doi.org/10.1111/j.1540-6261.1993.tb05128.x", "year": 1993},
    "nelson": {"text": "Nelson (1991)", "url": "https://doi.org/10.2307/2938260", "year": 1991},
    "mcneil": {"text": "McNeil and Frey (2000)", "url": "https://doi.org/10.1016/S0927-5398(00)00012-8", "year": 2000},
    "engle": {"text": "Engle and Manganelli (2004)", "url": "https://doi.org/10.1198/073500104000000370", "year": 2004},
    "patton": {"text": "Patton, Ziegel and Chen (2019)", "url": "https://doi.org/10.1016/j.jeconom.2018.10.008", "year": 2019},
    "taylor": {"text": "Taylor (2019)", "url": "https://doi.org/10.1080/07350015.2017.1281815", "year": 2019},
    "manski": {"text": "Manski (1989)", "url": "https://doi.org/10.2307/145818", "year": 1989},
    "shevchenko": {"text": "Shevchenko (2010)", "url": "https://arxiv.org/abs/1008.1108", "year": 2010},
    "cox": {"text": "Cox (1972)", "url": "https://doi.org/10.1111/j.2517-6161.1972.tb00899.x", "year": 1972},
    "spiegelhalter": {"text": "Spiegelhalter (1986)", "url": "https://doi.org/10.1002/sim.4780050506", "year": 1986},
}

C11 = "data/derived/C11/{v}.json"
MS_EPROC = "manuscripts/e-process-sequential-monitors"
MS_BS14 = "manuscripts/anchored-pd-under-informative-withdrawals"
MS_BS8 = "manuscripts/behavioural-assumption-test-at-a-limit-breach"
MS_BS10 = "manuscripts/measured-corrections-of-validation-tests"
K_BACKLOG = "BL-119"


def _m(mid: str, label: dict[str, str], run: str, better: str, unit: dict[str, str], columns: list[str], file: str, null_reason: dict[str, str] | None = None,
       note_reason: bool = False) -> dict[str, Any]:
    return {"id": mid, "label": label, "run": run, "better": better, "unit": unit, "columns": columns, "file": file, "null_reason": null_reason, "note_reason": note_reason}


def _row(rid: str, method: dict[str, str], ladder: str | None, cells: dict[str, Any], source: str | None = None, ranked: bool = True,
         note: dict[str, str] | None = None, file: str | None = None, null_reasons: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    return {"id": rid, "method": method, "ladder": ladder, "cells": cells, "source": source, "ranked": ranked, "note": note, "file": file,
            "null_reasons": null_reasons or {}}


# --- Q1: VaR and ES forecasts in stress windows (C11) --------------------------------------------------------------------------------------

Q1_WINDOWS = [col("calm-2004-06", "Calm 2004 to 2006", "Calma 2004 a 2006"), col("equity-2007-09", "Equities 2007 to 2009", "Acciones 2007 a 2009"),
              col("equity-2020", "Equities 2020", "Acciones 2020"), col("rates-2022", "Rates 2022", "Tasas 2022"),
              col("fx-2008", "Currencies 2008", "Divisas 2008"), col("mixed-2023", "Mixed 2023", "Mixto 2023")]


def _c11(mid: str, field: str, level: str = "0.01") -> str:
    return f"outputs.models[model_id={mid}].by_level[alpha={level}].{field}"


def _c11t(test: str, mid: str, level: str = "0.01") -> str:
    return f"tests[test_id={test},model_id={mid},segment=alpha={level}].p_value"


def _c11w(mid: str, side: str, field: str, level: str = "0.01") -> str:
    return f"outputs.conformal.rows[model_id={mid},alpha={level}].{side}.{field}"


_FZ0_NULL = T("the rule forecasts no expected shortfall, so its FZ0 loss is undefined", "la regla no pronostica la pérdida esperada de cola, así que su pérdida FZ0 no está definida")

# (model id, English, Spanish, ladder id, source key)
_Q1_RULES = [
    ("hs-250", "Historical simulation, 250 days", "Simulación histórica, 250 días", "M-18", "pritsker"),
    ("hs-500", "Historical simulation, 500 days", "Simulación histórica, 500 días", "M-18", "pritsker"),
    ("awhs", "Age-weighted historical simulation", "Simulación histórica ponderada por antigüedad", "M-18", "boudoukh"),
    ("ewma", "EWMA (RiskMetrics)", "EWMA (RiskMetrics)", "M-18", "riskmetrics"),
    ("garch-t", "GARCH(1,1) with Student-t errors", "GARCH(1,1) con errores t de Student", "M-18", "bollerslev"),
    ("dn-rolling", "Delta-normal on rolling moments", "Delta-normal con momentos móviles", "M-18", "riskmetrics"),
    ("cf-rolling", "Cornish-Fisher on rolling moments", "Cornish-Fisher con momentos móviles", "M-18", "cornish"),
    ("gjr-t", "GJR-GARCH with Student-t errors", "GJR-GARCH con errores t de Student", "M-18", "glosten"),
    ("egarch-t", "EGARCH with Student-t errors", "EGARCH con errores t de Student", "M-18", "nelson"),
    ("fhs", "Filtered historical simulation", "Simulación histórica filtrada", "M-18", None),
    ("evt-mf", "Conditional extreme value theory (McNeil and Frey)", "Teoría de valores extremos condicional (McNeil y Frey)", "M-18", "mcneil"),
    ("caviar-sav", "CAViaR, symmetric absolute value", "CAViaR, valor absoluto simétrico", "M-38", "engle"),
    ("caviar-as", "CAViaR, asymmetric slope", "CAViaR, pendiente asimétrica", "M-38", "engle"),
    ("caviar-es", "ES-CAViaR (Taylor)", "CAViaR de pérdida esperada (Taylor)", "M-38", "taylor"),
    ("gas-fz-1", "GAS under the FZ0 loss, one factor", "GAS bajo la pérdida FZ0, un factor", "M-38", "patton"),
    ("gas-fz-2", "GAS under the FZ0 loss, two factors", "GAS bajo la pérdida FZ0, dos factores", "M-38", "patton"),
    ("gas-hybrid", "Hybrid GARCH-FZ", "GARCH-FZ híbrido", "M-38", "patton"),
    ("nn-fz", "Quantile network trained on the FZ0 loss", "Red de cuantiles entrenada con la pérdida FZ0", "M-30", None),
]
_Q1_WRAPPED = [("hs-250", "Historical simulation, 250 days", "Simulación histórica, 250 días"), ("garch-t", "GARCH(1,1) with Student-t errors", "GARCH(1,1) con errores t de Student"),
               ("fhs", "Filtered historical simulation", "Simulación histórica filtrada")]


def _q1_rows() -> list[dict[str, Any]]:
    rows = []
    for mid, en, es, ladder, src in _Q1_RULES:
        cells: dict[str, Any] = {
            "fz0_1": _c11(mid, "fz0_mean"), "fz0_25": _c11(mid, "fz0_mean", "0.025"), "exceed_1": _c11(mid, "n_exceedances"),
            "zone_1": _c11(mid, "traffic_light.final_zone"),
            "kupiec_1": _c11t("market.kupiec_pof", mid),
            "cc_1": _c11t("market.christoffersen_conditional_coverage", mid),
        }
        rows.append(_row(mid, T(en, es), ladder, cells, src))
    for mid, en, es in _Q1_WRAPPED:
        rows.append(_row(f"{mid}-aci", T(f"{en}, with adaptive conformal recalibration", f"{es}, con recalibración conformal adaptativa"), "BS-16", {
            "fz0_1": _c11w(mid, "wrapped", "fz0_mean"), "fz0_25": _c11w(mid, "wrapped", "fz0_mean", "0.025"), "exceed_1": _c11w(mid, "wrapped", "n_exceedances"),
            "zone_1": Null(T("the conformal block carries no Basel zone", "el bloque conformal no trae la zona de Basilea")),
            "kupiec_1": _c11w(mid, "wrapped", "kupiec_p"), "cc_1": _c11w(mid, "wrapped", "conditional_coverage_p")},
            None, True))
    rows.append(_row("expected", T("Expected exceedances of a correct model", "Excesos esperados de un modelo correcto"), None,
                     {"expected_1": _c11("hs-250", "expected_exceedances")}, None, False))
    return rows


Q1 = {
    "id": "Q1", "title": T("VaR and ES forecasts in stress windows", "Pronósticos de VaR y ES en ventanas de estrés"), "case_ids": ["C11"],
    "protocol": T("One rolling schedule per window: every rule forecasts day t from data up to t-1 on an estimation window of 1,000 days, with its hyperparameters fixed on 1995 to 2003 and never tuned on the test window; the adaptive conformal recalibration runs on the same days.",
                  "Un calendario móvil por ventana: cada regla pronostica el día t con datos hasta t-1 sobre una ventana de estimación de 1.000 días, con sus hiperparámetros fijados en 1995 a 2003 y nunca ajustados en la ventana de prueba; la recalibración conformal adaptativa corre sobre los mismos días."),
    "runs": [{"id": "rolling", "label": T("Rolling schedule, six windows", "Calendario móvil, seis ventanas"),
              "protocol": T("Rolling forecasts on the C11 windows, 1,000-day estimation window, one document per window.", "Pronósticos móviles en las ventanas del caso C11, ventana de estimación de 1.000 días, un documento por ventana."),
              "seed": (C11, "provenance.seed"), "columns": Q1_WINDOWS}],
    "metrics": [
        _m("fz0_1", T("Mean FZ0 loss, 1% level", "Pérdida FZ0 media, nivel 1%"), "rolling", "lower", T("FZ0 loss", "pérdida FZ0"), [c["id"] for c in Q1_WINDOWS], C11, _FZ0_NULL),
        _m("fz0_25", T("Mean FZ0 loss, 2.5% level", "Pérdida FZ0 media, nivel 2,5%"), "rolling", "lower", T("FZ0 loss", "pérdida FZ0"), [c["id"] for c in Q1_WINDOWS], C11, _FZ0_NULL),
        _m("exceed_1", T("Exceedances, 1% level", "Excesos, nivel 1%"), "rolling", "nearer-metric:expected_1", T("days", "días"), [c["id"] for c in Q1_WINDOWS], C11),
        _m("expected_1", T("Expected exceedances, 1% level", "Excesos esperados, nivel 1%"), "rolling", "none", T("days", "días"), [c["id"] for c in Q1_WINDOWS], C11),
        _m("zone_1", T("Basel zone of the last 250 days, 1% level", "Zona de Basilea de los últimos 250 días, nivel 1%"), "rolling", "order:green,amber,red", T("zone", "zona"), [c["id"] for c in Q1_WINDOWS], C11),
        _m("kupiec_1", T("Kupiec p-value, 1% level", "Valor p de Kupiec, nivel 1%"), "rolling", "none", T("p-value", "valor p"), [c["id"] for c in Q1_WINDOWS], C11, None, True),
        _m("cc_1", T("Conditional-coverage p-value, 1% level", "Valor p de cobertura condicional, nivel 1%"), "rolling", "none", T("p-value", "valor p"), [c["id"] for c in Q1_WINDOWS], C11, None, True),
    ],
    "rows": _q1_rows(),
    "absent": [],
    "negative_results": [],
}


# --- Q2: monitoring calibration and back-tests over time (C22, C11, C03) -----------------------------------------------------------------------

Q2_COLS = [col("null", "No change (size)", "Sin cambio (tamaño)"), col("rate-x2", "Hit rate x2", "Tasa de excesos x2"), col("rate-x3", "Hit rate x3", "Tasa de excesos x3"),
           col("rate-x4", "Hit rate x4", "Tasa de excesos x4"), col("cluster-0.1", "Clustering 0.1", "Agrupamiento 0,1"),
           col("cluster-0.2", "Clustering 0.2", "Agrupamiento 0,2"), col("cluster-0.4", "Clustering 0.4", "Agrupamiento 0,4")]
Q2_POWER = [c["id"] for c in Q2_COLS[1:]]
Q2_C03 = [("fy2006-07", 2006), ("fy2006-07", 2007), ("fy2008-10", 2008), ("fy2008-10", 2009), ("fy2008-10", 2010), ("fy2011-14", 2011), ("fy2011-14", 2012),
          ("fy2011-14", 2013), ("fy2011-14", 2014), ("fy2015-17", 2015), ("fy2015-17", 2016), ("fy2015-17", 2017), ("fy2018-20", 2018), ("fy2018-20", 2019), ("fy2018-20", 2020)]
Q2_GEN = "data/derived/C22/other-families.json"
Q2_MAN = f"{MS_EPROC}/experiments/results_hits.json"
Q2_REAL = f"{MS_EPROC}/experiments/results_c11.json"
_NEVER = T("the median stream is never flagged within the horizon", "la serie mediana nunca se señala dentro del horizonte")
_Q2_RULES = [
    ("e_rate", "Rate e-process", "Proceso e de tasa", "BS-15", None),
    ("e_cluster", "Clustering e-process", "Proceso e de agrupamiento", "BS-15", None),
    ("e_battery", "Battery e-process", "Proceso e de batería", "BS-15", None),
    ("kupiec_trailing", "Kupiec POF on the trailing 250 days", "Kupiec POF sobre los últimos 250 días", "M-19", "kupiec"),
    ("kupiec_cumulative", "Kupiec POF on all days so far", "Kupiec POF sobre todos los días hasta la fecha", "M-19", "kupiec"),
    ("traffic_light", "Basel traffic light (5 exceptions)", "Semáforo de Basilea (5 excepciones)", "M-19", None),
    ("independence_trailing", "Christoffersen independence test on the trailing 250 days", "Prueba de independencia de Christoffersen sobre los últimos 250 días", "M-19", "christoffersen"),
]


def _q2_rows() -> list[dict[str, Any]]:
    rows = []
    for key, en, es, ladder, src in _Q2_RULES:
        cells: dict[str, Any] = {}
        for field, suffix in (("ever", "size"), ("ever", "power"), ("median_day", "median"), ("median_day", "median_null")):
            cells[f"gen_{suffix}"] = f"outputs.sequential.hits.scenarios[id={{v}}].{key}.{field}"
            cells[f"man_{suffix}"] = f"scenarios['{{v}}'].methods.{key}.{field}"
        if key in ("e_rate", "kupiec_cumulative", "kupiec_trailing", "traffic_light"):
            cells["real_median"] = f"windows.{{v}}.levels['0.01'].summary.{key}.median_day"
        if key == "e_rate":
            cells["c03_month"] = "outputs.sequential.vintages[fiscal_year={fy}].rejection_month"
        if key == "traffic_light":
            cells["c03_light"] = "outputs.sequential.vintages[fiscal_year={fy}].five_year_light"
        rows.append(_row(key, T(en, es), ladder, cells, src))
    return rows


def _q2_cells_hack(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each metric of a run reads its own file: the manuscript metrics take the manuscript file as a tuple, the others the case file."""
    for r in rows:
        for k, v in list(r["cells"].items()):
            if k.startswith("man_"):
                r["cells"][k] = (Q2_MAN, v)
            elif k.startswith("real_"):
                r["cells"][k] = (Q2_REAL, v)
    return rows


Q2 = {
    "id": "Q2", "title": T("Monitoring calibration and back-tests over time", "Monitoreo de la calibración y pruebas retrospectivas en el tiempo"),
    "case_ids": ["C22", "C11", "C03"],
    "protocol": T("The generator runs are the comparison: one stream generator feeds every rule, so the size of each rule (hit rate unchanged) and its power (hit rate multiplied, hits clustered) are measured on the same streams. The real windows and the real vintages have no known truth: they show when each rule fires, not which is right, and are never ranked. The case document (seed 42) and the manuscript run (another seed) are two runs and are never mixed in one cell.",
                  "Las corridas del generador son la comparación: un generador de series alimenta a cada regla, así que el tamaño de cada regla (tasa de excesos sin cambio) y su potencia (tasa multiplicada, excesos agrupados) se miden sobre las mismas series. Las ventanas y las cosechas reales no tienen verdad conocida: muestran cuándo dispara cada regla, no cuál acierta, y nunca se clasifican. El documento del caso (semilla 42) y la corrida del manuscrito (otra semilla) son dos corridas y nunca se mezclan en una celda."),
    "runs": [
        {"id": "generator", "label": T("Generator streams, case document", "Series del generador, documento del caso"),
         "protocol": T("1,000 days, daily VaR level 1%, 2,000 streams per scenario, seed of the case document.", "1.000 días, nivel de VaR diario 1%, 2.000 series por escenario, semilla del documento del caso."),
         "seed": (Q2_GEN, "outputs.sequential.seed"), "columns": Q2_COLS},
        {"id": "manuscript", "label": T("Generator streams, manuscript run", "Series del generador, corrida del manuscrito"),
         "protocol": T("The same generator, 2,000 streams per scenario, the seed of the manuscript's experiment.", "El mismo generador, 2.000 series por escenario, la semilla del experimento del manuscrito."),
         "seed": (Q2_MAN, "meta.seed"), "columns": Q2_COLS,
         "truth": ("synthetic-known-truth", T("the manuscript experiment draws its streams from the engine generator of known truth", "el experimento del manuscrito extrae sus series del generador del motor de verdad conocida"))},
        {"id": "real-windows", "label": T("Real windows of the VaR ladder", "Ventanas reales de la escalera de VaR"),
         "protocol": T("Each rule reads every model's exceedance days of a C11 window; the median first-flag day over the models flagged.", "Cada regla lee los días de exceso de cada modelo de una ventana de C11; la mediana del primer día de alerta entre los modelos señalados."),
         "seed": None, "columns": Q1_WINDOWS,
         "truth": ("real-outcomes", T("the rules read the exceedance days of the committed real-market windows of C11", "las reglas leen los días de exceso de las ventanas de mercado real versionadas de C11"))},
        {"id": "vintages", "label": T("Real vintages of the SME book", "Cosechas reales de la cartera de pymes"),
         "protocol": T("The e-process on observed defaults against predicted PD, against the traffic light at the five-year mark, per vintage.", "El proceso e sobre los incumplimientos observados contra la PD predicha, contra el semáforo a los cinco años, por cosecha."),
         "seed": None, "columns": [col(str(y), f"Vintage {y}", f"Cosecha {y}", file=f, fy=str(y)) for f, y in Q2_C03]},
    ],
    "metrics": [
        _m("gen_size", T("Share of streams flagged at any day, no change (size)", "Proporción de series señaladas en algún día, sin cambio (tamaño)"), "generator", "lower", T("share of streams", "proporción de series"), ["null"], Q2_GEN),
        _m("gen_power", T("Share of streams flagged at any day, planted change (power)", "Proporción de series señaladas en algún día, cambio plantado (potencia)"), "generator", "higher", T("share of streams", "proporción de series"), Q2_POWER, Q2_GEN),
        _m("gen_median", T("Median first-flag day, planted change (delay)", "Mediana del primer día de alerta, cambio plantado (retraso)"), "generator", "lower", T("days", "días"), Q2_POWER, Q2_GEN, _NEVER),
        _m("gen_median_null", T("Median first-flag day, no change (a false alarm: context, not ranked)", "Mediana del primer día de alerta, sin cambio (una falsa alarma: contexto, sin clasificar)"), "generator", "none", T("days", "días"), ["null"], Q2_GEN, _NEVER),
        _m("man_size", T("Share of streams flagged at any day, no change (size)", "Proporción de series señaladas en algún día, sin cambio (tamaño)"), "manuscript", "lower", T("share of streams", "proporción de series"), ["null"], Q2_MAN),
        _m("man_power", T("Share of streams flagged at any day, planted change (power)", "Proporción de series señaladas en algún día, cambio plantado (potencia)"), "manuscript", "higher", T("share of streams", "proporción de series"), Q2_POWER, Q2_MAN),
        _m("man_median", T("Median first-flag day, planted change (delay)", "Mediana del primer día de alerta, cambio plantado (retraso)"), "manuscript", "lower", T("days", "días"), Q2_POWER, Q2_MAN, _NEVER),
        _m("man_median_null", T("Median first-flag day, no change (a false alarm: context, not ranked)", "Mediana del primer día de alerta, sin cambio (una falsa alarma: contexto, sin clasificar)"), "manuscript", "none", T("days", "días"), ["null"], Q2_MAN, _NEVER),
        _m("real_median", T("Median first-flag day over the models flagged", "Mediana del primer día de alerta entre los modelos señalados"), "real-windows", "none", T("days", "días"), [c["id"] for c in Q1_WINDOWS], Q2_REAL,
           T("no model of the window is flagged by this rule", "ningún modelo de la ventana es señalado por esta regla")),
        _m("c03_month", T("Month of the e-process rejection", "Mes del rechazo del proceso e"), "vintages", "none", T("months", "meses"), [str(y) for _, y in Q2_C03], "data/derived/C03/{file}.json",
           T("the e-process never rejects in this vintage", "el proceso e nunca rechaza en esta cosecha")),
        _m("c03_light", T("Traffic light at the five-year mark", "Semáforo a los cinco años"), "vintages", "none", T("light", "semáforo"), [str(y) for _, y in Q2_C03], "data/derived/C03/{file}.json"),
    ],
    "rows": _q2_cells_hack(_q2_rows()),
    "absent": [
        {"method": T("E-backtest of Wang, Wang and Ziegel (2022)", "Prueba retrospectiva-e de Wang, Wang y Ziegel (2022)"), "ladder": None, "backlog": "BL-121",
         "reason": T("The published e-backtest is scored only in the manuscript result files and the product's list of methods does not include it yet, so it has no standing in this comparison and its cells are not shown.",
                     "La prueba retrospectiva-e publicada se puntúa solo en los archivos de resultados del manuscrito y la lista de métodos del producto todavía no la incluye, así que no tiene un lugar en esta comparación y sus celdas no se muestran.")},
        {"method": T("Beta-mixture e-process, sequential probability ratio e-process, calibrated Kupiec and calibrated CUSUM", "Proceso e de mezcla beta, proceso e de razón de probabilidad secuencial, Kupiec calibrado y CUSUM calibrado"), "ladder": None, "backlog": None,
         "reason": T("The manuscript run also scores these rules; none is in the product's list of methods, so none has a standing here.",
                     "La corrida del manuscrito también puntúa estas reglas; ninguna figura en la lista de métodos del producto, así que ninguna tiene un lugar aquí.")},
    ],
    "negative_results": [
        {"rows": ["e_rate", "e_cluster", "e_battery"], "manuscript": f"{MS_EPROC}/main.tex",
         "text": T("The manuscript reports a partial result: the size is held under optional stopping, but the delay and the power-cost clauses are not met at a hit rate of three times over twenty seeds and hold at four times.",
                   "El manuscrito reporta un resultado parcial: el tamaño se mantiene bajo parada opcional, pero las cláusulas de retraso y de costo de potencia no se cumplen con una tasa de excesos de tres veces en veinte semillas y sí con cuatro veces.")},
    ],
}

# --- Q3: P&L attribution of a trading desk (C13) -----------------------------------------------------------------------------------------

Q3_COLS = [col("none", "No defect (size)", "Sin defecto (tamaño)"), col("stale-volatility", "Stale volatility", "Volatilidad desactualizada"),
           col("wrong-correlation", "Wrong correlation", "Correlación errónea"), col("missing-basis", "Missing basis", "Base omitida"),
           col("omitted-factor", "Omitted factor", "Factor omitido"), col("time-misalignment", "Time misalignment", "Desfase temporal")]
Q3_F = "data/derived/C13/{v}.json"
Q3 = {
    "id": "Q3", "title": T("P&L attribution of a trading desk", "Atribución de P&L de una mesa de negociación"), "case_ids": ["C13"],
    "protocol": T("One desk P&L generator drives all six variants and every replication is scored by the regulatory attribution test and by the complement: the false-alarm rate is read where the desk has no defect, the detection rate where a defect is planted.",
                  "Un generador de P&L de mesa alimenta las seis variantes y cada réplica es puntuada por la prueba regulatoria de atribución y por el complemento: la tasa de falsas alarmas se lee donde la mesa no tiene defecto, la tasa de detección donde se planta un defecto."),
    "runs": [{"id": "desk", "label": T("Desk P&L replications", "Réplicas de P&L de mesa"),
              "protocol": T("1,000 replications per variant, a 250-day window.", "1.000 réplicas por variante, ventana de 250 días."),
              "seed": (Q3_F, "outputs.generator.seed_base"), "columns": Q3_COLS}],
    "metrics": [
        _m("false_alarm", T("False-alarm rate, desk without defect", "Tasa de falsas alarmas, mesa sin defecto"), "desk", "lower", T("share of replications", "proporción de réplicas"), ["none"], Q3_F),
        _m("detection", T("Detection rate, planted defect", "Tasa de detección, defecto plantado"), "desk", "higher", T("share of replications", "proporción de réplicas"), [c["id"] for c in Q3_COLS[1:]], Q3_F),
    ],
    "rows": [
        _row("pla", T("Profit-and-loss attribution test of the Basel market-risk standard (Spearman and Kolmogorov-Smirnov, amber or red)", "Prueba de atribución de pérdidas y ganancias del estándar de riesgo de mercado de Basilea (Spearman y Kolmogorov-Smirnov, ámbar o rojo)"), "M-19",
             {"false_alarm": "outputs.detection.share_amber_or_red", "detection": "outputs.detection.share_amber_or_red"}),
        _row("complement", T("Scale-and-level complement to the attribution test (family-wise size 1%)", "Complemento de escala y nivel a la prueba de atribución (tamaño conjunto 1%)"), "BS-13",
             {"false_alarm": "outputs.pla_complement.flags.family.any.rate", "detection": "outputs.pla_complement.flags.family.any.rate"}),
        _row("complement-pla", T("Complement united with the attribution test zone", "Complemento unido a la zona de la prueba de atribución"), "BS-13",
             {"false_alarm": "outputs.pla_complement.flags.family_with_pla.rate", "detection": "outputs.pla_complement.flags.family_with_pla.rate"}),
    ],
    "absent": [
        {"method": T("A recent published alternative to the attribution test", "Una alternativa publicada recientemente a la prueba de atribución"), "ladder": None, "backlog": None,
         "reason": T("The product runs none and its list of methods has no entry for one. Whether one exists outside the repository was not searched, so no absence is claimed outside the product.",
                     "El producto no ejecuta ninguna y su lista de métodos no tiene una entrada para ella. No se buscó si existe una fuera del repositorio, así que no se afirma una ausencia fuera del producto.")},
    ],
    "negative_results": [],
}

# --- Q4: PD under informative rating withdrawals (C04) ----------------------------------------------------------------------------------

Q4_COLS = [col("first_year", "First-year cohort", "Cohorte del primer año"), col("pooled", "Five cohorts pooled", "Cinco cohortes agrupadas"),
           col("capture70", "Second source counts 70%", "Segunda fuente cuenta el 70%"), col("first_year_x10", "Ten times the cohort", "Diez veces la cohorte")]
Q4_F = "data/derived/C04/withdrawals.json"
Q4_ALL = [c["id"] for c in Q4_COLS]


def _q4(tid: str, field: str) -> str:
    return f"outputs.rungs[value=9.0].bounds.designs[id={{v}}].treatments[id={tid}].{field}"


def _q4_row(rid: str, en: str, es: str, tid: str, ladder: str | None, src: str | None = None, ranked: bool = True, note: dict[str, str] | None = None) -> dict[str, Any]:
    cells = {"coverage": _q4(tid, "coverage[5].rate"), "width": _q4(tid, "mean_width[5]"), "bias": _q4(tid, "relative_bias[5]")}
    if tid == "anchored":
        v = "outputs.bounds_verdict.summary"
        cells.update({"v_refuted": f"{v}.refuted", "v_coverage": f"{v}.coverage_better_than_every_treatment.holds", "v_stable": f"{v}.anchored_k_stable_across_years.holds"})
    return _row(rid, T(en, es), ladder, cells, src, ranked, note)


Q4 = {
    "id": "Q4", "title": T("PD under informative rating withdrawals", "PD con retiros de calificación informativos"), "case_ids": ["C04"],
    "protocol": T("One generator of known truth, fitted on a rating agency's pooled annual counts, with withdrawals that are informative: the odds of withdrawal before default are nine times those of staying (the grade-B PD is read). Every treatment is scored on the same 200 repetitions per design, against the true PD.",
                  "Un generador de verdad conocida, ajustado a los conteos anuales agrupados de una agencia calificadora, con retiros informativos: las probabilidades de retiro antes del incumplimiento son nueve veces las de permanecer (se lee la PD del grado B). Cada tratamiento se puntúa sobre las mismas 200 repeticiones por diseño, contra la PD verdadera."),
    "runs": [{"id": "withdrawals", "label": T("Withdrawal generator, odds ratio nine", "Generador de retiros, razón de probabilidades nueve"),
              "protocol": T("200 repetitions per design; the verdict block of the same document repeats the experiment with more repetitions.", "200 repeticiones por diseño; el bloque de veredicto del mismo documento repite el experimento con más repeticiones."),
              "seed": (Q4_F, "provenance.seed"), "columns": Q4_COLS + [col("verdict", "Verdict of the document", "Veredicto del documento")]}],
    "metrics": [
        _m("coverage", T("Coverage of the true grade-B PD, 95% interval", "Cobertura de la PD verdadera del grado B, intervalo del 95%"), "withdrawals", "higher", T("share of repetitions", "proporción de repeticiones"), Q4_ALL, Q4_F),
        _m("width", T("Mean interval width", "Ancho medio del intervalo"), "withdrawals", "lower", T("PD", "PD"), Q4_ALL, Q4_F),
        _m("bias", T("Relative bias of the point value", "Sesgo relativo del valor puntual"), "withdrawals", "nearer:0", T("relative", "relativo"), Q4_ALL, Q4_F),
        _m("v_refuted", T("Document verdict: refuted", "Veredicto del documento: refutado"), "withdrawals", "none", T("verdict", "veredicto"), ["verdict"], Q4_F),
        _m("v_coverage", T("Verdict clause: coverage better than every treatment", "Cláusula del veredicto: cobertura mejor que todo tratamiento"), "withdrawals", "none", T("verdict", "veredicto"), ["verdict"], Q4_F),
        _m("v_stable", T("Verdict clause: the anchored parameter is stable across years", "Cláusula del veredicto: el parámetro anclado es estable entre años"), "withdrawals", "none", T("verdict", "veredicto"), ["verdict"], Q4_F),
    ],
    "rows": [
        _q4_row("industry", "Cohort estimator with the withdrawn ratings removed", "Estimador de cohortes con las calificaciones retiradas eliminadas", "industry", "M-7"),
        _q4_row("unfollowed", "Cohort estimator with the withdrawn ratings kept", "Estimador de cohortes con las calificaciones retiradas conservadas", "unfollowed", "M-7"),
        _q4_row("followed", "Withdrawn ratings followed to their outcome", "Calificaciones retiradas seguidas hasta su desenlace", "followed", None, None, False,
                T("an oracle reading that needs the outcome of every withdrawn name", "una lectura de oráculo que necesita el desenlace de cada nombre retirado")),
        _q4_row("identified", "Identified band (Manski)", "Banda identificada (Manski)", "identified", None, "manski"),
        _q4_row("anchored", "Anchored tipping-point PD", "PD de punto de inflexión anclada", "anchored", "BS-14"),
    ],
    "absent": [
        {"method": T("Duration estimators of the transition matrix", "Estimadores de duración de la matriz de transición"), "ladder": "M-9", "backlog": f"{K_BACKLOG} (K-4)",
         "reason": T("The duration estimators are not run on the withdrawal generator, so there is no cell to compare; a later computation adds the treatment.",
                     "Los estimadores de duración no se ejecutan sobre el generador de retiros, así que no hay una celda que comparar; un cálculo posterior agrega el tratamiento.")},
    ],
    "negative_results": [
        {"rows": ["anchored"], "manuscript": f"{MS_BS14}/main.tex",
         "text": T("The committed verdict is refuted on both clauses: the anchored interval does not cover better than Manski's band, which covers as often with a wider interval, and the anchored parameter is not stable across years.",
                   "El veredicto versionado es refutado en ambas cláusulas: el intervalo anclado no cubre mejor que la banda de Manski, que cubre igual de seguido con un intervalo más ancho, y el parámetro anclado no es estable entre años.")},
    ],
}


# --- Q5: default prediction on a retail book (C01) ---------------------------------------------------------------------------------------

Q5_TW = "data/derived/C01/holdout.json"
Q5_DE = "data/derived/C01/german-twin.json"


def _q5(test: str, rung: str, field: str = "metric") -> str:
    return f"tests[test_id={test},model_id={rung},segment=portfolio].{field}"


_Q5_RUNGS = [
    ("P0-constant", "Constant PD", "PD constante", None, False),
    ("P0-single", "One-variable PD", "PD de una variable", None, False),
    ("P1-scorecard", "Weight-of-evidence logistic scorecard", "Tarjeta de puntuación logística con peso de la evidencia", "M-1", True),
    ("P2a-l1", "L1-penalised logistic regression on weight-of-evidence", "Regresión logística penalizada L1 sobre peso de la evidencia", "M-2", True),
    ("P2b-pltr", "Penalised logistic tree regression", "Regresión logística penalizada con árboles", "M-3", True),
    ("P3-ebm", "Explainable boosting machine", "Máquina de potenciación explicable", "M-4", True),
    ("P4-lightgbm", "Monotone gradient boosting (LightGBM) with isotonic calibration", "Potenciación de gradiente monótona (LightGBM) con calibración isotónica", "M-5", True),
    ("P4-xgboost", "Monotone gradient boosting (XGBoost), second engine", "Potenciación de gradiente monótona (XGBoost), segundo motor", "M-5", True),
    ("P5-tabpfn", "TabPFN", "TabPFN", "M-6", True),
]
_TABPFN_TW = Null(T("TabPFN runs only on the small cases (the German document), never on the 9,000-row holdout", "TabPFN corre solo en los casos pequeños (el documento alemán), nunca en el holdout de 9.000 filas"))
_NOT_RUN_DE = Null(T("the German document runs one gradient-boosting engine only", "el documento alemán ejecuta un solo motor de potenciación de gradiente"))


def _q5_rows() -> list[dict[str, Any]]:
    rows = []
    for rid, en, es, ladder, ranked in _Q5_RUNGS:
        cells: dict[str, Any] = {}
        for pre, f in (("tw", Q5_TW), ("de", Q5_DE)):
            miss = _TABPFN_TW if (rid == "P5-tabpfn" and pre == "tw") else _NOT_RUN_DE if (rid == "P4-xgboost" and pre == "de") else None
            for mid, test, field in (("auc", "disc.auc", "metric"), ("brier", "pd.brier", "metric"), ("ece", "pd.ece", "metric"), ("sph", "pd.spiegelhalter", "p_value")):
                cells[f"{pre}_{mid}"] = miss if miss is not None else (f, _q5(test, rid, field))
        rows.append(_row(rid, T(en, es), ladder, cells, None, ranked))
    return rows


def _q5_metrics() -> list[dict[str, Any]]:
    out = []
    for pre, run, f, colid in (("tw", "taiwan", Q5_TW, "holdout"), ("de", "german", Q5_DE, "german-twin")):
        out += [
            _m(f"{pre}_auc", T("Area under the ROC curve", "Área bajo la curva ROC"), run, "higher", T("AUC", "AUC"), [colid], f),
            _m(f"{pre}_brier", T("Brier score", "Puntaje de Brier"), run, "lower", T("Brier", "Brier"), [colid], f),
            _m(f"{pre}_ece", T("Expected calibration error", "Error de calibración esperado"), run, "lower", T("error", "error"), [colid], f),
            _m(f"{pre}_sph", T("Spiegelhalter calibration p-value (evidence against calibration, not a score)", "Valor p de calibración de Spiegelhalter (evidencia contra la calibración, no un puntaje)"), run, "none", T("p-value", "valor p"), [colid], f),
        ]
    return out


Q5 = {
    "id": "Q5", "title": T("Default prediction on a retail book", "Predicción de incumplimiento en una cartera minorista"), "case_ids": ["C01"],
    "protocol": T("A locked stratified holdout of 30%, with repeated stratified five-fold cross-validation inside the training part; every rung of one document is scored on the same held-out rows. The two documents hold different data and are never ranked together. The calibration slope is not in any committed document; the expected calibration error and the Spiegelhalter p-value are.",
                  "Un holdout estratificado bloqueado del 30%, con validación cruzada estratificada repetida de cinco pliegues dentro de la parte de entrenamiento; cada peldaño de un documento se puntúa sobre las mismas filas retenidas. Los dos documentos tienen datos distintos y nunca se clasifican juntos. La pendiente de calibración no está en ningún documento versionado; el error de calibración esperado y el valor p de Spiegelhalter sí."),
    "runs": [
        {"id": "taiwan", "label": T("Taiwan credit-card holdout", "Holdout de tarjetas de crédito de Taiwán"),
         "protocol": T("9,000 held-out rows.", "9.000 filas retenidas."), "seed": (Q5_TW, "provenance.seed"), "columns": [col("holdout", "Holdout", "Holdout")]},
        {"id": "german", "label": T("German credit twin", "Gemelo del crédito alemán"),
         "protocol": T("300 held-out rows; the only document that runs TabPFN.", "300 filas retenidas; el único documento que ejecuta TabPFN."),
         "seed": (Q5_DE, "provenance.seed"), "columns": [col("german-twin", "German twin", "Gemelo alemán")]},
    ],
    "metrics": _q5_metrics(),
    "rows": _q5_rows(),
    "absent": [], "negative_results": [],
}

# --- Q6: lifetime PD by survival models (C06) ---------------------------------------------------------------------------------------------

Q6_COLS = [col(d, f"Reporting date {d}", f"Fecha de reporte {d}") for d in ("2006-12", "2008-12", "2010-12", "2019-12", "2020-06", "2023-06")]
Q6_F = "data/derived/C06/rd-{v}.json"
Q6_ALL = [c["id"] for c in Q6_COLS]
_Q6_RUNGS = [("L0-km", "Kaplan-Meier", "Kaplan-Meier", "M-10"), ("L1-dth", "Discrete-time hazard with macro covariates", "Riesgo en tiempo discreto con covariables macro", "M-10"),
             ("L2-cox", "Cox proportional hazards", "Riesgos proporcionales de Cox", "M-10"), ("L3-pch", "PC-Hazard neural survival", "Supervivencia neuronal PC-Hazard", "M-33")]


def _q6_rows() -> list[dict[str, Any]]:
    rows = []
    for rid, en, es, ladder in _Q6_RUNGS:
        rc = f"outputs.rung_comparison[rung_id={rid}]"
        cells = {"ibs": f"{rc}.integrated_brier", "cidx": f"{rc}.c_index", "gap12": f"{rc}.calibration_gap_12m",
                 "life": f"tests[test_id=ifrs9.lifetime_pd_backtest,model_id={rid},segment=all].metric"}
        rows.append(_row(rid, T(en, es), ladder, cells, "cox" if rid == "L2-cox" else None, True, None, None,
                         {"cidx": T("one pooled curve for every account: it orders no accounts, so it has no C-index", "una sola curva agrupada para todas las cuentas: no ordena cuentas, así que no tiene índice C")}))
    return rows


Q6 = {
    "id": "Q6", "title": T("Lifetime PD by survival models", "PD de por vida con modelos de supervivencia"), "case_ids": ["C06"],
    "protocol": T("One document per reporting date: every rung is trained on accounts up to the date and tested on the later, out-of-time accounts, so the four rungs share the same test accounts. Integrated Brier lower, C-index higher, the signed calibration gap at 12 months nearer 0, the largest gap of the 36-month lifetime back-test lower. A decile gap per rung is not in the committed documents.",
                  "Un documento por fecha de reporte: cada peldaño se entrena con cuentas hasta la fecha y se prueba en las cuentas posteriores, fuera de tiempo, así que los cuatro peldaños comparten las mismas cuentas de prueba. Brier integrado menor, índice C mayor, la brecha de calibración con signo a 12 meses más cerca de 0, la mayor brecha de la prueba retrospectiva de vida a 36 meses menor. Una brecha por decil para cada peldaño no está en los documentos versionados."),
    "runs": [{"id": "out-of-time", "label": T("Out-of-time reporting dates", "Fechas de reporte fuera de tiempo"),
              "protocol": T("Train up to the reporting date, test later.", "Se entrena hasta la fecha de reporte, se prueba después."), "seed": (Q6_F, "provenance.seed"), "columns": Q6_COLS}],
    "metrics": [
        _m("ibs", T("Integrated Brier score", "Puntaje de Brier integrado"), "out-of-time", "lower", T("Brier", "Brier"), Q6_ALL, Q6_F),
        _m("cidx", T("C-index", "Índice C"), "out-of-time", "higher", T("index", "índice"), Q6_ALL, Q6_F),
        _m("gap12", T("Calibration gap at 12 months (signed)", "Brecha de calibración a 12 meses (con signo)"), "out-of-time", "nearer:0", T("PD", "PD"), Q6_ALL, Q6_F),
        _m("life", T("Largest gap of the lifetime back-test, 36 months", "Mayor brecha de la prueba retrospectiva de vida, 36 meses"), "out-of-time", "lower", T("PD", "PD"), Q6_ALL, Q6_F),
    ],
    "rows": _q6_rows(), "absent": [], "negative_results": [],
}

# --- Q7: LGD on defaulted loans (C08) -----------------------------------------------------------------------------------------------------

Q7_COLS = [col(d, f"Default cohort {d}", f"Cohorte de incumplimiento {d}") for d in ("2003-06", "2007-08", "2009-10", "2011-13", "2014-19", "2020-23")]
Q7_F = "data/derived/C08/dc-{v}.json"
Q7_ALL = [c["id"] for c in Q7_COLS]
_Q7_RUNGS = [("L1-ols", "Linear regression, predictions clipped", "Regresión lineal, predicciones acotadas", "M-14"), ("L2-fractional-logit", "Fractional logit", "Logit fraccional", "M-14"),
             ("L3-beta", "Beta regression", "Regresión beta", "M-14"), ("L4-hurdle", "Two-stage hurdle", "Modelo de dos etapas con umbral", "M-14"),
             ("L5-gradient-boosted", "Gradient-boosted trees", "Árboles con potenciación de gradiente", "M-14"), ("L6-tobit", "Two-limit Tobit", "Tobit de dos límites", "M-14"),
             ("L7-random-forest", "Random forest", "Bosque aleatorio", "M-34"), ("L8-neural-network", "Neural network", "Red neuronal", "M-34")]


def _q7_rows() -> list[dict[str, Any]]:
    rows = []
    for rid, en, es, ladder in _Q7_RUNGS:
        rc = f"outputs.rung_comparison[rung_id={rid}]"
        rows.append(_row(rid, T(en, es), ladder, {"rmse": f"{rc}.rmse", "mae": f"{rc}.mae", "r2": f"{rc}.r2", "spearman": f"{rc}.spearman", "gap": f"{rc}.calibration_gap"}))
    return rows


Q7 = {
    "id": "Q7", "title": T("LGD on defaulted loans", "LGD en préstamos en incumplimiento"), "case_ids": ["C08"],
    "protocol": T("One document per default cohort: all eight rungs are trained up to a cutoff date and tested on the later cohort, out of time, with workouts closed before the cutoff.",
                  "Un documento por cohorte de incumplimiento: los ocho peldaños se entrenan hasta una fecha de corte y se prueban en la cohorte posterior, fuera de tiempo, con recuperaciones cerradas antes del corte."),
    "runs": [{"id": "out-of-time", "label": T("Out-of-time default cohorts", "Cohortes de incumplimiento fuera de tiempo"),
              "protocol": T("Train up to the cutoff, test on the later cohort.", "Se entrena hasta el corte, se prueba en la cohorte posterior."), "seed": (Q7_F, "provenance.seed"), "columns": Q7_COLS}],
    "metrics": [
        _m("rmse", T("Root mean squared error", "Raíz del error cuadrático medio"), "out-of-time", "lower", T("LGD", "LGD"), Q7_ALL, Q7_F),
        _m("mae", T("Mean absolute error", "Error absoluto medio"), "out-of-time", "lower", T("LGD", "LGD"), Q7_ALL, Q7_F),
        _m("r2", T("R squared", "R cuadrado"), "out-of-time", "higher", T("R squared", "R cuadrado"), Q7_ALL, Q7_F),
        _m("spearman", T("Spearman rank correlation", "Correlación de rangos de Spearman"), "out-of-time", "higher", T("correlation", "correlación"), Q7_ALL, Q7_F),
        _m("gap", T("Calibration gap (signed)", "Brecha de calibración (con signo)"), "out-of-time", "nearer:0", T("LGD", "LGD"), Q7_ALL, Q7_F),
    ],
    "rows": _q7_rows(), "absent": [], "negative_results": [],
}

# --- Q8: operational-risk capital (C17) ----------------------------------------------------------------------------------------------------

Q8_COLS = [col("0-6", "Tail index 0.6", "Índice de cola 0,6"), col("0-8", "Tail index 0.8", "Índice de cola 0,8"), col("0-96", "Tail index 0.96", "Índice de cola 0,96"),
           col("1-1", "Tail index 1.1 (infinite mean)", "Índice de cola 1,1 (media infinita)")]
Q8_F = "data/derived/C17/xi-{v}.json"
Q8_ALL = [c["id"] for c in Q8_COLS]
_Q8_MEAN_UNDEFINED = T("the tail index is 1 or more: the severity has an infinite mean and the mean correction does not exist", "el índice de cola es 1 o más: la severidad tiene media infinita y la corrección de la media no existe")
# (key under capital, summary wrapper, English, Spanish, ladder, ranked)
_Q8_RULES = [
    ("lda_lognormal", False, "Loss distribution approach, lognormal by Monte Carlo, collection threshold ignored", "Enfoque de distribución de pérdidas, lognormal por Monte Carlo, umbral de recolección ignorado", "M-24", True),
    ("lda_lognormal_truncated", False, "Loss distribution approach, truncated lognormal by Panjer", "Enfoque de distribución de pérdidas, lognormal truncada por Panjer", "M-24", True),
    ("lda_splice", False, "Loss distribution approach, lognormal body and generalised Pareto tail by FFT", "Enfoque de distribución de pérdidas, cuerpo lognormal y cola de Pareto generalizada por FFT", "M-24", True),
    ("sla", False, "Single loss approximation", "Aproximación de pérdida única", "M-24", True),
    ("sla_mean_corrected", True, "Single loss approximation with the mean correction", "Aproximación de pérdida única con corrección de la media", "M-24", True),
    ("sla_mean_adjusted", True, "Mean-adjusted single loss approximation, generalised Pareto by maximum likelihood", "Aproximación de pérdida única ajustada por la media, Pareto generalizada por máxima verosimilitud", "M-24", True),
    ("scenario", True, "Scenario combination by Bayesian credibility", "Combinación de escenarios por credibilidad bayesiana", "M-24", True),
    ("sla_cvm", True, "Robust generalised Pareto by Cramer-von Mises, in the mean-adjusted single loss approximation", "Pareto generalizada robusta por Cramer-von Mises, en la aproximación de pérdida única ajustada por la media", "M-32", True),
    ("sla_obre", True, "Optimally bias-robust generalised Pareto, in the mean-adjusted single loss approximation", "Pareto generalizada óptimamente robusta al sesgo, en la aproximación de pérdida única ajustada por la media", "M-32", True),
    ("sla_cvm_lognormal", True, "Robust lognormal by Cramer-von Mises (control)", "Lognormal robusta por Cramer-von Mises (control)", "M-32", False),
]


def _q8_rows() -> list[dict[str, Any]]:
    rows = []
    for key, wrapped, en, es, ladder, ranked in _Q8_RULES:
        base = f"outputs.cells[id=y10-h10000].capital.{key}" + (".summary" if wrapped else "")
        rows.append(_row(key, T(en, es), ladder, {"ratio": f"{base}.ratio_to_truth.median", "iqr": f"{base}.iqr_over_truth", "under": f"{base}.share_underestimating",
                                                  "defined": f"{base}.n_defined"},
                         "shevchenko" if key.startswith("lda_") else None, ranked,
                         T("a control for the robust estimators: the Cramer-von Mises criterion with a lognormal severity, shown with the standing of that group and not ranked", "un control para los estimadores robustos: el criterio de Cramer-von Mises con una severidad lognormal, mostrado con el lugar de ese grupo y sin clasificar") if not ranked else None,
                         None, {m: _Q8_MEAN_UNDEFINED for m in ("ratio", "iqr", "under", "defined")} if key == "sla_mean_corrected" else {}))
    return rows


Q8 = {
    "id": "Q8", "title": T("Operational-risk capital", "Capital por riesgo operacional"), "case_ids": ["C17"],
    "protocol": T("One generator of known truth per tail index, a Poisson-Pareto whose 99.9% annual-loss quantile is computed by FFT and checked by Monte Carlo; every estimator is run on the same 1,000 independent simulated ten-year histories with a collection threshold of 10,000 euros. The capital over the truth should be near 1, the spread low and the share of histories that understate near one half.",
                  "Un generador de verdad conocida por índice de cola, un Poisson-Pareto cuyo cuantil de pérdida anual al 99,9% se calcula por FFT y se verifica con Monte Carlo; cada estimador se ejecuta sobre las mismas 1.000 historias simuladas independientes de diez años con un umbral de recolección de 10.000 euros. El capital sobre la verdad debería estar cerca de 1, la dispersión baja y la proporción de historias que subestiman cerca de la mitad."),
    "runs": [{"id": "histories", "label": T("Independent histories of known truth", "Historias independientes de verdad conocida"),
              "protocol": T("1,000 histories per tail index, cell of ten years and a 10,000-euro threshold.", "1.000 historias por índice de cola, celda de diez años y umbral de 10.000 euros."), "seed": None, "columns": Q8_COLS}],
    "metrics": [
        _m("ratio", T("Median capital over the truth", "Mediana del capital sobre la verdad"), "histories", "nearer:1", T("ratio", "razón"), Q8_ALL, Q8_F, T("the estimator returns no capital here", "el estimador no entrega capital aquí")),
        _m("iqr", T("Interquartile range over the truth", "Rango intercuartil sobre la verdad"), "histories", "lower", T("ratio", "razón"), Q8_ALL, Q8_F, T("the estimator returns no capital here", "el estimador no entrega capital aquí")),
        _m("under", T("Share of histories that understate the capital", "Proporción de historias que subestiman el capital"), "histories", "nearer:0.5", T("share", "proporción"), Q8_ALL, Q8_F, T("the estimator returns no capital here", "el estimador no entrega capital aquí")),
        _m("defined", T("Histories with a defined capital, of 1,000", "Historias con capital definido, de 1.000"), "histories", "none", T("histories", "historias"), Q8_ALL, Q8_F),
    ],
    "rows": _q8_rows(), "absent": [], "negative_results": [],
}


# --- Q9: a behavioural assumption changed at a limit breach (C14) -----------------------------------------------------------------------

Q9_F = f"{MS_BS8}/experiments/results_stated.json"
Q9_COLS = [col("lam-0.05", "Unrelated changes 0.05, breach prevalence 0.10", "Cambios no relacionados 0,05, prevalencia de brechas 0,10", lam="0.05", prev="0.1"),
           col("lam-0.10", "Unrelated changes 0.10, breach prevalence 0.25", "Cambios no relacionados 0,10, prevalencia de brechas 0,25", lam="0.1", prev="0.25"),
           col("lam-0.20", "Unrelated changes 0.20, breach prevalence 0.50", "Cambios no relacionados 0,20, prevalencia de brechas 0,50", lam="0.2", prev="0.5")]
Q9_ALL = [c["id"] for c in Q9_COLS]
_Q9_RULES = [
    ("engine", "Breach test, as the engine reads a stated parameter", "Prueba de brecha, como el motor lee un parámetro declarado", "BS-8", True),
    ("any_change", "Any change of the parameter (the plain stability reading)", "Cualquier cambio del parámetro (la lectura simple de estabilidad)", "M-22", True),
    ("fisher", "Fisher exact test on the flag counts", "Prueba exacta de Fisher sobre los conteos de alertas", None, True),
    ("mannwhitney", "Mann-Whitney U test on the parameter", "Prueba U de Mann-Whitney sobre el parámetro", None, True),
    ("welch", "Welch t test on the parameter", "Prueba t de Welch sobre el parámetro", None, True),
    ("shift", "Break in level at an unknown date (conformal, 5%)", "Quiebre de nivel en una fecha desconocida (conformal, 5%)", None, True),
    ("shift_at_breach", "Break in level restricted to breach dates (conformal, 5%)", "Quiebre de nivel restringido a fechas de brecha (conformal, 5%)", None, True),
]


def _q9_rows() -> list[dict[str, Any]]:
    rows = []
    for key, en, es, ladder, ranked in _Q9_RULES:
        sel = "cells[lam={lam},prevalence={prev},pi_m=0.5]"
        rows.append(_row(key, T(en, es), ladder, {"false_flag": f"{sel}.rates.null.{key}.rate", "detect": f"{sel}.rates.alt.{key}.rate", "auc": f"{sel}.auc.{key}.auc"}, None, ranked))
    return rows


Q9 = {
    "id": "Q9", "title": T("A behavioural assumption changed at a limit breach", "Un supuesto de comportamiento que cambia en una brecha de límite"), "case_ids": ["C14"],
    "protocol": T("Planted histories of 12 quarters in paired arms, 4,000 per arm: the same breach chain and the same unrelated changes in both arms, the parameter lengthening at a breach with probability one half in the second arm. The two shift tests are calibrated at 5% on separate null histories; every rule is scored on the same histories. The committed bank documents show that the test operates on one bank, not that the bank behaved as the test flags, so they are not scored here.",
                  "Historias plantadas de 12 trimestres en brazos pareados, 4.000 por brazo: la misma cadena de brechas y los mismos cambios no relacionados en ambos brazos, con el parámetro alargándose en una brecha con probabilidad de un medio en el segundo brazo. Las dos pruebas de quiebre se calibran al 5% en historias nulas separadas; cada regla se puntúa sobre las mismas historias. Los documentos del banco versionados muestran que la prueba opera en un banco, no que el banco se comportó como la prueba señala, así que aquí no se puntúan."),
    "runs": [{"id": "planted", "label": T("Planted histories, paired arms", "Historias plantadas, brazos pareados"),
              "protocol": T("12 quarters, 4,000 histories per arm.", "12 trimestres, 4.000 historias por brazo."), "seed": (Q9_F, "seed"), "columns": Q9_COLS,
              "truth": ("synthetic-known-truth", T("the experiment plants the changes in simulated histories", "el experimento planta los cambios en historias simuladas"))}],
    "metrics": [
        _m("false_flag", T("Flag rate with unrelated changes only (false flags)", "Tasa de alertas con cambios no relacionados solamente (falsas alertas)"), "planted", "lower", T("share of histories", "proporción de historias"), Q9_ALL, Q9_F),
        _m("detect", T("Flag rate with a change at a breach (detection)", "Tasa de alertas con un cambio en una brecha (detección)"), "planted", "higher", T("share of histories", "proporción de historias"), Q9_ALL, Q9_F),
        _m("auc", T("ROC area of the statistic", "Área ROC del estadístico"), "planted", "higher", T("area", "área"), Q9_ALL, Q9_F),
    ],
    "rows": _q9_rows(), "absent": [],
    "negative_results": [
        {"rows": ["engine"], "manuscript": f"{MS_BS8}/main.tex",
         "text": T("The breach test as the engine reads a stated parameter flags unrelated changes far above the nominal 5%, where the calibrated break-in-level tests stay near it; the table shows it losing on false flags.",
                   "La prueba de brecha como el motor lee un parámetro declarado señala cambios no relacionados muy por encima del 5% nominal, donde las pruebas de quiebre calibradas se quedan cerca; la tabla la muestra perdiendo en falsas alertas.")},
    ],
}

# --- Q10: reverse liquidity stress (C16) --------------------------------------------------------------------------------------------------

Q10_DIR = "data/derived/C16"
Q10_COLS = [col("run", "The labelled run of March 2023", "La corrida etiquetada de marzo de 2023"),
            col("b-list-adverse", "Base: adverse run-off", "Base: salida adversa", base="list-adverse"),
            col("b-list-extreme", "Base: extreme run-off", "Base: salida extrema", base="list-extreme"),
            col("b-fast-run", "Base: calibrated fast run", "Base: corrida rápida calibrada", base="fast-run")]
Q10_BASES = ["b-list-adverse", "b-list-extreme", "b-fast-run"]
_SC = "outputs.scoring"


def _q10_row(rid: str, en: str, es: str, ladder: str | None, file: str, survival: bool, src: str | None = None, ranked: bool = True) -> dict[str, Any]:
    cells: dict[str, Any] = {"share": f"{_SC}.modelled_outflow.at_event_horizon.share_of_model_base", "ratio": f"{_SC}.denominators[id=board-stated-share].ratio",
                             "light": f"{_SC}.denominators[id=board-stated-share].light"}
    if survival:
        cells["survival"] = "outputs.path.survival.day"
    return _row(rid, T(en, es), ladder, cells, src, ranked, None, file,
                {"share": T("the formula has no daily path, so it has no outflow at the two-day horizon", "la fórmula no tiene una trayectoria diaria, así que no tiene una salida al horizonte de dos días"),
                 "survival": T("the base survives its horizon", "la base sobrevive su horizonte")})


Q10 = {
    "id": "Q10", "title": T("Reverse liquidity stress", "Estrés de liquidez inverso"), "case_ids": ["C16"],
    "protocol": T("One bank, one balance sheet and one labelled run: every variant document scores the modelled outflow against the same observed share of deposits lost in the two days of March 2023. The ratio and the light are read against that observed share, which is a label and never a forecast. The run-off multiplier is a threshold on a base, not a forecast: it has no score of its own, so it is shown beside the others and not ranked.",
                  "Un banco, un balance y una corrida etiquetada: cada documento de variante puntúa la salida modelada contra la misma proporción observada de depósitos perdidos en los dos días de marzo de 2023. La razón y el semáforo se leen contra esa proporción observada, que es una etiqueta y nunca un pronóstico. El multiplicador de salida es un umbral sobre una base, no un pronóstico: no tiene puntaje propio, así que se muestra junto a los demás y no se clasifica."),
    "runs": [{"id": "labelled-run", "label": T("The labelled run", "La corrida etiquetada"),
              "protocol": T("Balance sheet at 2022-12-31 with synthetic deposit behaviour; event of 9 and 10 March 2023, horizon 2 days.", "Balance al 2022-12-31 con comportamiento sintético de depósitos; evento del 9 y 10 de marzo de 2023, horizonte de 2 días."),
              "seed": (f"{Q10_DIR}/list-adverse.json", "provenance.seed"), "columns": Q10_COLS}],
    "metrics": [
        _m("share", T("Share of deposits lost in the two-day event horizon", "Proporción de depósitos perdidos en el horizonte de dos días"), "labelled-run", "nearer:0.85", T("share", "proporción"), ["run"], Q10_DIR + "/x.json"),
        _m("ratio", T("Ratio to the observed share", "Razón a la proporción observada"), "labelled-run", "nearer:1", T("ratio", "razón"), ["run"], Q10_DIR + "/x.json"),
        _m("light", T("Light against the observed run", "Semáforo contra la corrida observada"), "labelled-run", "order:green,amber,red", T("light", "semáforo"), ["run"], Q10_DIR + "/x.json"),
        _m("survival", T("Survival period of the run-off ladder", "Periodo de supervivencia de la escalera de salidas"), "labelled-run", "none", T("days", "días"), ["run"], Q10_DIR + "/x.json"),
        _m("multiplier", T("Run-off multiplier at the 30-day target", "Multiplicador de salida a la meta de 30 días"), "labelled-run", "none", T("multiplier", "multiplicador"), Q10_BASES, Q10_DIR + "/reverse-stress.json",
           T("the base is refused: it falls below the 30-day target before any multiplier applies", "la base se rechaza: cae bajo la meta de 30 días antes de aplicar cualquier multiplicador")),
    ],
    "rows": [
        _q10_row("lcr", "Liquidity coverage ratio formula, 30-day aggregate", "Fórmula de la razón de cobertura de liquidez, agregado a 30 días", "M-21", f"{Q10_DIR}/lcr-standard.json", False),
        _q10_row("list-adverse", "Supervisory run-off, adverse path", "Salida supervisora, trayectoria adversa", "M-23", f"{Q10_DIR}/list-adverse.json", True),
        _q10_row("list-extreme", "Supervisory run-off, extreme path", "Salida supervisora, trayectoria extrema", "M-23", f"{Q10_DIR}/list-extreme.json", True),
        _q10_row("fast-run", "Daily compounding calibrated on the rows before 2023", "Capitalización diaria calibrada con las filas anteriores a 2023", None, f"{Q10_DIR}/fast-run.json", True),
        {**_row("multiplier", T("Reverse-stress run-off multiplier with a refusal rule", "Multiplicador de salida de estrés inverso con regla de rechazo"), "BS-11", {
            "share": (f"{Q10_DIR}/fast-run.json", f"{_SC}.modelled_outflow.at_event_horizon.share_of_model_base"),
            "ratio": (f"{Q10_DIR}/fast-run.json", f"{_SC}.denominators[id=board-stated-share].ratio"),
            "light": (f"{Q10_DIR}/fast-run.json", f"{_SC}.denominators[id=board-stated-share].light"),
            "multiplier": "outputs.bases[base_id={base}].solved.multiplier"},
            None, False, T("the multiplier is a threshold on a base, not a forecast: the score shown is the one of its calibrated fast-run base, and the comparators carry no score on the multiplier",
                           "el multiplicador es un umbral sobre una base, no un pronóstico: el puntaje mostrado es el de su base de corrida rápida calibrada, y los comparadores no tienen puntaje sobre el multiplicador")), },
    ],
    "absent": [],
    "negative_results": [],
}
Q10["rows"][-1]["file"] = f"{Q10_DIR}/reverse-stress.json"

# --- Q11: the corrections of three validation tests (manuscript results) --------------------------------------------------------------------

Q11_COV = f"{MS_BS10}/experiments/results/coverage.json"
Q11_SHIFT = f"{MS_BS10}/experiments/results/shift.json"
Q11_SIT = f"{MS_BS10}/experiments/results/situation.json"
_Q11_NOTE = T("the rule belongs to the machine-learning validation and fairness tests; the product's list of methods holds them in one entry", "la regla pertenece a las pruebas de validación y de equidad de aprendizaje automático; la lista de métodos del producto las reúne en una entrada")
Q11 = {
    "id": "Q11", "title": T("The corrections of three validation tests", "Las correcciones de tres pruebas de validación"), "case_ids": ["C20", "C21"],
    "protocol": T("Three experiments, each scoring every rule on the same replications of its cell: the coverage test under exchangeability, the shift light without and with a two-standard-deviation shift, and the situation-testing cut without and with a gap. A rule is better when it rejects less under the null and more under the planted change. The experiments live in the manuscript result files; the committed case documents hold one instance of each corrected statistic, not its rate.",
                  "Tres experimentos, cada uno puntúa cada regla sobre las mismas réplicas de su celda: la prueba de cobertura bajo intercambiabilidad, el semáforo de cambio sin y con un cambio de dos desviaciones estándar, y el corte de la prueba de situación sin y con una brecha. Una regla es mejor cuando rechaza menos bajo la nula y más bajo el cambio plantado. Los experimentos viven en los archivos de resultados del manuscrito; los documentos de caso versionados traen una instancia de cada estadístico corregido, no su tasa."),
    "runs": [
        {"id": "coverage", "label": T("Coverage test under exchangeability", "Prueba de cobertura bajo intercambiabilidad"),
         "protocol": T("4,000 replications per cell.", "4.000 réplicas por celda."), "seed": (Q11_COV, "meta.seed"), "truth": ("synthetic-known-truth", T("scores drawn uniformly under exchangeability", "puntajes extraídos de forma uniforme bajo intercambiabilidad")),
         "columns": [col("equal", "Calibration 1,000, test 1,000", "Calibración 1.000, prueba 1.000", sel="n=1000,m=1000"), col("x4", "Calibration 1,000, test 4,000", "Calibración 1.000, prueba 4.000", sel="n=1000,m=4000")]},
        {"id": "shift", "label": T("Shift light", "Semáforo de cambio"), "protocol": T("About 400 draws per cell, 500 evaluation rows.", "Cerca de 400 sorteos por celda, 500 filas de evaluación."), "seed": (Q11_SHIFT, "meta.seed"), "truth": ("synthetic-known-truth", T("samples drawn from the engine covariate-shift plant", "muestras extraídas de la planta de cambio de covariables del motor")),
         "columns": [col("no-shift", "No shift", "Sin cambio", sel="shift=0.0"), col("shift-2sd", "Shift of two standard deviations", "Cambio de dos desviaciones estándar", sel="shift=2.0")]},
        {"id": "situation", "label": T("Situation-testing cut", "Corte de la prueba de situación"), "protocol": T("1,000 replications per cell, 400 applicants.", "1.000 réplicas por celda, 400 solicitantes."), "seed": (Q11_SIT, "meta.seed"), "truth": ("synthetic-known-truth", T("datasets drawn from the engine threshold-bias plant", "conjuntos de datos extraídos de la planta de sesgo de umbral del motor")),
         "columns": [col("no-gap", "No gap", "Sin brecha", sel="gap=0.0"), col("gap-0.2", "A gap of 0.2", "Una brecha de 0,2", sel="gap=0.2")]},
    ],
    "metrics": [
        _m("cov_size", T("Rejection rate of the coverage test under exchangeability", "Tasa de rechazo de la prueba de cobertura bajo intercambiabilidad"), "coverage", "lower", T("share of replications", "proporción de réplicas"), ["equal", "x4"], Q11_COV),
        _m("shift_fa", T("False-alarm rate of the shift light without a shift", "Tasa de falsas alarmas del semáforo de cambio sin cambio"), "shift", "lower", T("share of draws", "proporción de sorteos"), ["no-shift"], Q11_SHIFT),
        _m("shift_det", T("Detection rate of the shift light under a shift", "Tasa de detección del semáforo de cambio con un cambio"), "shift", "higher", T("share of draws", "proporción de sorteos"), ["shift-2sd"], Q11_SHIFT),
        _m("sit_null", T("Rejection rate of the situation-testing rule with no gap", "Tasa de rechazo de la regla de situación sin brecha"), "situation", "lower", T("share of replications", "proporción de réplicas"), ["no-gap"], Q11_SIT),
        _m("sit_det", T("Detection rate of the situation-testing rule under a gap", "Tasa de detección de la regla de situación con una brecha"), "situation", "higher", T("share of replications", "proporción de réplicas"), ["gap-0.2"], Q11_SIT),
    ],
    "rows": [
        _row("cov-binomial", T("Coverage test, binomial count of covered points", "Prueba de cobertura, conteo binomial de puntos cubiertos"), "M-29", {"cov_size": "cells[{sel},b=1.0].rates.bin.rate"}, None, True, _Q11_NOTE),
        _row("cov-betabinomial", T("Coverage test, Beta-Binomial", "Prueba de cobertura, Beta-Binomial"), "BS-10", {"cov_size": "cells[{sel},b=1.0].rates.bb.rate"}),
        _row("shift-fixed-05", T("Shift light, fixed drop of 0.05 in the area under the curve", "Semáforo de cambio, caída fija de 0,05 en el área bajo la curva"), "M-29",
             {"shift_fa": "cells[{sel},n_eval=500].rules['fixed_0.05'].rate", "shift_det": "cells[{sel},n_eval=500].rules['fixed_0.05'].rate"}, None, True, _Q11_NOTE),
        _row("shift-fixed-10", T("Shift light, fixed drop of 0.10 in the area under the curve", "Semáforo de cambio, caída fija de 0,10 en el área bajo la curva"), "M-29",
             {"shift_fa": "cells[{sel},n_eval=500].rules['fixed_0.10'].rate", "shift_det": "cells[{sel},n_eval=500].rules['fixed_0.10'].rate"}, None, True, _Q11_NOTE),
        _row("shift-permutation", T("Shift light, permutation reference (199 draws)", "Semáforo de cambio, referencia por permutación (199 sorteos)"), "BS-10",
             {"shift_fa": "cells[{sel},n_eval=500].rules.perm_199.rate", "shift_det": "cells[{sel},n_eval=500].rules.perm_199.rate"}),
        _row("sit-cut-10", T("Situation testing, amber cut at 0.10", "Prueba de situación, corte ámbar en 0,10"), "M-29",
             {"sit_null": "cells[{sel},n=400].rules['cut_0.1'].rate", "sit_det": "cells[{sel},n=400].rules['cut_0.1'].rate"}, None, True, _Q11_NOTE),
        _row("sit-count", T("Situation testing, binomial count rule", "Prueba de situación, regla de conteo binomial"), "M-29",
             {"sit_null": "cells[{sel},n=400].rules.count_binomial.rate"}, None, True, _Q11_NOTE),
        _row("sit-cut-20", T("Situation testing, amber cut at 0.20", "Prueba de situación, corte ámbar en 0,20"), "BS-10",
             {"sit_null": "cells[{sel},n=400].rules['cut_0.2'].rate", "sit_det": "cells[{sel},n=400].rules['cut_0.2'].rate"}),
    ],
    "absent": [],
    "negative_results": [
        {"rows": ["shift-permutation"], "manuscript": f"{MS_BS10}/main.tex",
         "text": T("The permutation reference detects a two-standard-deviation shift less often than the fixed drop of 0.05, because the fixed drop also fires without a shift; the table shows both rates.",
                   "La referencia por permutación detecta un cambio de dos desviaciones estándar con menos frecuencia que la caída fija de 0,05, porque la caída fija también dispara sin cambio; la tabla muestra ambas tasas.")},
    ],
}
# Q11 files: the metrics carry them, but the C20 and C21 case ids stay in the question: their documents are not cited here.

# --- Q12: reject inference with a known rejected population (C01) -----------------------------------------------------------------------------

Q12_F = "data/derived/C01/german-twin.json"
Q12_COLS = [col("mar", "Missing at random", "Faltante al azar"), col("weak", "Weak selection", "Selección débil"), col("moderate", "Moderate selection", "Selección moderada"), col("strong", "Strong selection", "Selección fuerte")]
Q12_ALL = [c["id"] for c in Q12_COLS]
_Q12_RUNGS = [("accepted-only", "Model fitted on the accepted applicants only", "Modelo ajustado solo con los solicitantes aceptados", "M-1", True),
              ("augmentation", "Reject inference by augmentation", "Inferencia de rechazados por aumentación", "M-35", True),
              ("hard-cutoff", "Reject inference by hard cutoff", "Inferencia de rechazados por corte duro", "M-35", True),
              ("parcelling", "Reject inference by parcelling", "Inferencia de rechazados por parcelación", "M-35", True),
              ("parcelling-prudent", "Reject inference by parcelling with prudence", "Inferencia de rechazados por parcelación con prudencia", "M-35", True),
              ("fuzzy", "Reject inference by fuzzy parcelling", "Inferencia de rechazados por parcelación difusa", "M-35", True),
              ("oracle", "The full population, not runnable by a lender", "La población completa, que un prestamista no puede ejecutar", None, False)]


def _q12_rows() -> list[dict[str, Any]]:
    rows = []
    for rid, en, es, ladder, ranked in _Q12_RUNGS:
        r = f"outputs.reject_inference.regimes[id={{v}}].rungs[id={rid}]"
        rows.append(_row(rid, T(en, es), ladder, {"bias": f"{r}.abs_bias", "reduction": f"{r}.reduction.value", "auc_gain": f"{r}.auc_vs_accepted_only.mean"}, None, ranked,
                         T("the oracle uses the outcomes of the rejected applicants, which a lender never has", "el oráculo usa los desenlaces de los solicitantes rechazados, que un prestamista nunca tiene") if not ranked else None))
    return rows


Q12 = {
    "id": "Q12", "title": T("Reject inference with a known rejected population", "Inferencia de rechazados con una población rechazada conocida"), "case_ids": ["C01"],
    "protocol": T("A sample of 1,000 rows with the outcomes of the rejected applicants known, an acceptance share of 0.6 and 100 replications, in four selection regimes; every rung is scored on the same replications against the full population. A negative reduction means the method worsens the bias of the accepted-only model.",
                  "Una muestra de 1.000 filas con los desenlaces de los solicitantes rechazados conocidos, una proporción de aceptación de 0,6 y 100 réplicas, en cuatro regímenes de selección; cada peldaño se puntúa sobre las mismas réplicas contra la población completa. Una reducción negativa significa que el método empeora el sesgo del modelo solo con aceptados."),
    "runs": [{"id": "twin", "label": T("German credit twin, 100 replications", "Gemelo del crédito alemán, 100 réplicas"),
              "protocol": T("1,000 rows, acceptance share 0.6.", "1.000 filas, proporción de aceptación 0,6."), "seed": (Q12_F, "provenance.seed"), "columns": Q12_COLS}],
    "metrics": [
        _m("bias", T("Mean absolute bias of the portfolio PD over the replications", "Sesgo absoluto medio de la PD de la cartera sobre las réplicas"), "twin", "lower", T("PD", "PD"), Q12_ALL, Q12_F),
        _m("reduction", T("Reduction of the mean signed bias of the accepted-only model", "Reducción del sesgo medio con signo del modelo solo con aceptados"), "twin", "higher", T("ratio", "razón"), Q12_ALL, Q12_F),
        _m("auc_gain", T("Gain in the area under the curve over the accepted-only model", "Ganancia del área bajo la curva sobre el modelo solo con aceptados"), "twin", "higher", T("area", "área"), Q12_ALL, Q12_F),
    ],
    "rows": _q12_rows(), "absent": [], "negative_results": [],
}

QUESTIONS = [Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, Q11, Q12]

NOT_BUILT = [
    {"id": "Q13", "title": T("PD curve carried to a new period", "Curva de PD llevada a un período nuevo"),
     "reason": T("The scaled approaches are given the new period's PD as an input and rescale the curve, so their forecast equals the observed PD and cannot be ranked against it; no proposed method exists for this question.",
                 "Los enfoques escalados reciben la PD del período nuevo como entrada y reescalan la curva, así que su pronóstico es igual a la PD observada y no se puede clasificar contra ella; no existe un método propuesto para esta pregunta.")},
    {"id": "Q14", "title": T("Portfolio loss quantile by method", "Cuantil de pérdida de cartera por método"),
     "reason": T("No truth exists for a portfolio loss quantile, so the methods can be compared by their dispersion only, not by which does better.",
                 "No existe una verdad para el cuantil de pérdida de una cartera, así que los métodos solo se pueden comparar por su dispersión, no por cuál lo hace mejor.")},
]

LEFT_OUT = [
    {"ladder": "M-11", "method": T("IFRS 9 expected-credit-loss engine", "Motor de pérdida crediticia esperada de IFRS 9"), "backlog": f"{K_BACKLOG} (K-9)",
     "reason": T("No competing method runs on a protocol: the weighted-scenario loss is committed beside the mean-path loss, but there is no outcome to score and no incurred-loss comparator is computed.",
                 "Ningún método competidor corre sobre un protocolo: la pérdida ponderada por escenarios está versionada junto a la pérdida de la trayectoria media, pero no hay un desenlace que puntuar ni se calcula un comparador de pérdida incurrida.")},
    {"ladder": "M-31", "method": T("Conditional-forecast and growth-at-risk quantile satellites", "Satélites de pronóstico condicional y de cuantil de crecimiento en riesgo"), "backlog": f"{K_BACKLOG} (K-10)",
     "reason": T("No numbers are committed: the stress document holds only the linear and probit satellites.",
                 "No hay números versionados: el documento de estrés trae solo los satélites lineales y probit.")},
    {"ladder": "M-36", "method": T("PD curve calibration carried to a new period", "Calibración de la curva de PD llevada a un período nuevo"), "backlog": None,
     "reason":T("The scaled approaches take the new period's PD as an input, so there is nothing to rank (question 13 is not built).",
                 "Los enfoques escalados toman la PD del período nuevo como entrada, así que no hay nada que clasificar (la pregunta 13 no se construye).")},
    {"ladder": "M-37", "method": T("The published size and power studies of the validation tests, rerun", "Los estudios publicados de tamaño y potencia de las pruebas de validación, repetidos"), "backlog": None,
     "reason": T("They reproduce published cells and do not compete with another method on a common stream.",
                 "Reproducen celdas publicadas y no compiten con otro método sobre una serie común.")},
]


if __name__ == "__main__":
    sys.exit(main())
