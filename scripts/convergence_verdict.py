#!/usr/bin/env python3
"""The generated convergence verdict of Contraste 1.00.000 (unit U16-V; ADR-0075 section 4; decision D16-2).

Convergence is an explicit check against the SDD: it enumerates each requirement, names its gate and records the gate's result
(ADR-0075). This script writes that check as a document, never by hand: one row for every requirement row of the product
(``docs/design/features/*/requirements.md``) and of the engine (the same path in the engine repository, read only), with the gate
the row names and the result the release run gave it.

The inputs are the result files of the release run, written by the commands in ``docs/design/features/release-1-0/design.md``:

* ``--product-junit`` and ``--engine-junit``, pytest ``--junitxml`` files of each repository (node ids ``tests/x.py::test_y``);
* ``--vitest``, the ``--reporter=json`` report of ``frontend/`` (file and test title);
* the scripts a gate names (``scripts/check_skeleton.py``), which the verdict runs itself with a timeout: the exit code is the result.

A row's result is ``passed`` (every test the gate names ran and passed; a parametrized test passes only if every parameter passed),
``failed``, ``skipped`` (with the reason the run gave) or ``absent`` (the gate is in no result file). Only ``passed`` counts as
passed. The verdict is ``NOT CONVERGED`` (exit 1) while any row is failed or absent, a skip stands, or a feature folder has no rows;
a skip whose reason is a device precondition (``requires_raw``, the data root) is allowed only when the run states the device with
``--device``. A missing result file exits 2, naming the file and the command that writes it, and writes no verdict.

The same result files give the same bytes: rows are sorted by repository, feature and id, and the date comes from the result
files, never from the clock. The requirement rows are parsed by ``scripts/check_sdd.py`` (imported, never copied).

Usage (from the repository root)::

    python scripts/convergence_verdict.py --product-junit F --engine-junit F --engine-repo DIR --vitest F [--device TEXT] [--sample]
        [--out docs/design/features/release-1-0/verdict.md]

Exit codes: 0 converged, 1 not converged, 2 a result file or a repository is missing.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
_argv = sys.argv
sys.argv = _argv[:1]  # check_sdd reads its repository root from argv[1] at import
sys.path.insert(0, str(HERE))
try:
    import check_sdd  # noqa: E402  the parser of the requirement rows (D16-2: reuse by import, never copy)
finally:
    sys.argv = _argv

PRODUCT_NAME = "contraste"
ENGINE_NAME = "riskvalidation"
DEFAULT_OUT = Path("docs/design/features/release-1-0/verdict.md")
DEFAULT_TIMEOUT = 600
DEVICE_SKIP = re.compile(r"requires_raw|data root|CONTRASTE_DATA|raw data|raw file", re.I)
SHOWN = ("passed", "failed", "skipped", "absent")
ORDER = ("failed", "absent", "skipped", "passed")  # the worst result of a gate's parts is the gate's result
# Arguments a script gate needs: the gate cell names the script alone (check_sdd accepts a backticked path, not a command line).
SCRIPT_ARGS: dict[str, list[str]] = {"scripts/check_skeleton.py": ["docs/contracts/catalog.md"]}
RESULT_COMMANDS = {
    "product-junit": "python -m pytest tests --junitxml={file}",
    "engine-junit": "python -m pytest tests --junitxml={file}   (run in the engine repository)",
    "vitest": "npm test -- --reporter=json --outputFile={file}   (run in frontend/)",
}


@dataclass
class Case:
    cls: str | None
    base: str
    full: str
    status: str
    reason: str = ""


@dataclass
class Results:
    """The result files of one repository: JUnit cases by test file, vitest assertions by test file."""

    junit: dict[str, list[Case]] = field(default_factory=dict)
    vitest: dict[str, list[Case]] = field(default_factory=dict)
    dates: list[str] = field(default_factory=list)


@dataclass
class Part:
    result: str
    detail: str
    device_ok: bool = False


@dataclass
class Row:
    repo: str
    feature: str
    rid: str
    gate: str
    result: str
    detail: str
    blocking: bool


# ---------------------------------------------------------------- result files

def load_junit(path: Path) -> tuple[dict[str, list[Case]], list[str]]:
    """pytest ``--junitxml``: {test file: cases}. The dotted classname gives the file; a segment starting ``Test`` is a class."""
    cases: dict[str, list[Case]] = {}
    dates: list[str] = []
    root = ET.parse(path).getroot()
    for suite in root.iter("testsuite"):
        stamp = suite.get("timestamp", "")
        if re.match(r"\d{4}-\d{2}-\d{2}", stamp):
            dates.append(stamp[:10])
    for node in root.iter("testcase"):
        segments = [s for s in node.get("classname", "").split(".") if s]
        cut = next((i for i, s in enumerate(segments) if s.startswith("Test")), len(segments))
        file = "/".join(segments[:cut]) + ".py"
        cls = "::".join(segments[cut:]) or None
        name = node.get("name", "")
        status, reason = "passed", ""
        if node.find("failure") is not None or node.find("error") is not None:
            status = "failed"
        elif (skipped := node.find("skipped")) is not None:
            status, reason = "skipped", (skipped.get("message") or (skipped.text or "")).strip()
        cases.setdefault(file, []).append(Case(cls, name.partition("[")[0], name, status, reason))
    return cases, dates


def load_vitest(path: Path) -> tuple[dict[str, list[Case]], list[str]]:
    """vitest ``--reporter=json``: {absolute test file: assertions}; pending, skipped and todo count as skipped."""
    data = json.loads(path.read_text(encoding="utf-8"))
    dates: list[str] = []
    if isinstance(data.get("startTime"), (int, float)):
        dates.append(datetime.fromtimestamp(data["startTime"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d"))
    files: dict[str, list[Case]] = {}
    for result in data.get("testResults", []):
        name = str(result.get("name", "")).replace("\\", "/")
        for item in result.get("assertionResults", []):
            raw = item.get("status", "")
            status = "passed" if raw == "passed" else "failed" if raw == "failed" else "skipped"
            title = item.get("title", "")
            case = Case(None, title, item.get("fullName", title), status, f"vitest status {raw}" if status == "skipped" else "")
            files.setdefault(name, []).append(case)
    return files, dates


def load_results(junit_file: Path, vitest_file: Path | None) -> Results:
    out = Results()
    out.junit, dates = load_junit(junit_file)
    out.dates += dates
    if vitest_file is not None:
        out.vitest, dates = load_vitest(vitest_file)
        out.dates += dates
    return out


# ---------------------------------------------------------------- gates

def combine(parts: list[Part]) -> tuple[str, str]:
    """The worst result of the parts, and the details of every part that is not passed."""
    if not parts:
        return "absent", "the gate names no file"
    worst = min((p.result for p in parts), key=ORDER.index)
    details = [p.detail for p in parts if p.result != "passed" and p.detail]
    if worst == "passed":
        details = [p.detail for p in parts if p.detail][:1]
    return worst, "; ".join(dict.fromkeys(details))


def verdict_of(cases: list[Case], what: str) -> Part:
    if not cases:
        return Part("absent", f"{what} is in no result file")
    for status in ("failed", "skipped"):
        hit = [c for c in cases if c.status == status]
        if hit:
            if status == "failed":
                return Part("failed", f"{len(hit)} of {len(cases)} cases failed")
            reasons = sorted({c.reason for c in hit if c.reason}) or ["no reason given"]
            return Part("skipped", "; ".join(reasons), device_ok=all(DEVICE_SKIP.search(c.reason) for c in hit))
    return Part("passed", f"{len(cases)} case{'s' if len(cases) != 1 else ''}")


def python_gate(results: Results, rel: str, test: str | None) -> Part:
    cases = results.junit.get(rel, [])
    if test is not None:
        cls, _, name = test.rpartition("::")
        exact = "[" in name
        cases = [c for c in cases if (c.full == name if exact else c.base == name) and (not cls or c.cls == cls)]
    return verdict_of(cases, f"{rel}::{test}" if test else rel)


def vitest_gate(results: Results, rel: str, test: str | None) -> Part:
    cases: list[Case] = []
    for name, found in results.vitest.items():
        if name == rel or name.endswith("/" + rel):
            cases += [c for c in found if test is None or test in (c.base, c.full)]
    return verdict_of(cases, f"{rel}::{test}" if test else rel)


VOLATILE = ((re.compile(r"(?:https?://)?(?:127\.0\.0\.1|localhost):\d+"), "127.0.0.1:PORT"), (re.compile(r"[A-Za-z]:[\\/]\S*"), "<path>"),
            (re.compile(r"\b\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\b"), "<time>"))


def stable(line: str) -> str:
    """A line of a script's output without what changes between two runs on the same files (a port, a path, a clock time)."""
    for pattern, replacement in VOLATILE:
        line = pattern.sub(replacement, line)
    return line


def run_script(repo: Path, rel: str, timeout: int) -> Part:
    path = repo / rel
    if not path.is_file():
        return Part("absent", f"{rel} does not exist")
    runner = {".py": [sys.executable], ".mjs": ["node"], ".js": ["node"]}.get(path.suffix)
    if runner is None:
        return Part("failed", f"{rel} cannot be run by the verdict")
    command = [*runner, str(path), *SCRIPT_ARGS.get(rel, [])]
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    try:
        done = subprocess.run(command, cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, check=False, env={**os.environ, **env})
    except subprocess.TimeoutExpired:
        return Part("failed", f"{rel} timed out after {timeout} s")
    except OSError as error:
        return Part("failed", f"{rel} cannot start: {error.__class__.__name__}")
    if done.returncode == 0:
        return Part("passed", f"{rel} exit 0")
    first = next((ln.strip() for ln in (done.stdout + "\n" + done.stderr).splitlines() if ln.strip()), "")
    return Part("failed", f"{rel} exit {done.returncode}" + (f": {stable(first)}" if first else ""))


def gate_parts(repo: Path, results: Results, gate: str, timeout: int) -> list[Part]:
    parts: list[Part] = []
    for token in check_sdd.TICKED.findall(gate):
        if not check_sdd.FILE_LIKE.match(token):
            continue
        rel, sep, test = token.partition("::")
        name = test if sep else None
        suffix = Path(rel).suffix
        if suffix == ".py" and (sep or check_sdd.is_test_file(rel)):
            parts.append(python_gate(results, rel, name))
        elif suffix in {".ts", ".tsx"} and check_sdd.is_test_file(rel):
            parts.append(vitest_gate(results, rel, name))
        elif not sep and check_sdd.is_script(rel):
            parts.append(run_script(repo, rel, timeout))
        else:
            parts.append(Part("absent", f"{token} is not a test or a script the verdict can read"))
    return parts


# ---------------------------------------------------------------- requirements

def read_features(repo: Path) -> tuple[list[tuple[str, list[dict[str, str]]]], list[str]]:
    """(feature, requirement rows) by feature folder, and the folders with none (superseded ones are neither)."""
    features = repo / "docs" / "design" / "features"
    found: list[tuple[str, list[dict[str, str]]]] = []
    empty: list[str] = []
    for folder in sorted(p for p in features.iterdir() if p.is_dir() and not p.name.startswith(".")):
        req = folder / "requirements.md"
        text = req.read_text(encoding="utf-8") if req.is_file() else ""
        marks = [m.group(1).lower() for m in check_sdd.STATUS_ANY.finditer(check_sdd.strip_markup(text))]
        if marks and marks[0] == "superseded":
            continue
        rows, _bad = check_sdd.requirement_rows(text)
        if rows:
            found.append((folder.name, rows))
        else:
            empty.append(folder.name)
    return found, empty


def judge(name: str, repo: Path, results: Results, timeout: int, device: str | None) -> tuple[list[Row], list[str]]:
    features, empty = read_features(repo)
    rows: list[Row] = []
    for feature, reqs in features:
        for req in sorted(reqs, key=lambda r: r["id"]):
            parts = gate_parts(repo, results, req["gate"], timeout)
            result, detail = combine(parts)
            allowed = result == "skipped" and device is not None and all(p.device_ok for p in parts if p.result == "skipped")
            rows.append(Row(name, feature, req["id"], req["gate"], result, detail, blocking=result != "passed" and not allowed))
    return rows, [f"{name}: {folder}" for folder in empty]


# ---------------------------------------------------------------- the document

def cell(text: str, limit: int = 140) -> str:
    one = re.sub(r"\s+", " ", text.replace("|", "/")).strip()
    return one if len(one) <= limit else one[: limit - 3].rstrip() + "..."


def gate_cell(gate: str, repo: str) -> str:
    """The gates a row names. The engine's paths are plain text: in code spans they would read as paths of this repository
    (scripts/check_doc_paths.py checks every code span of a document that starts with one of its folders)."""
    named = [t for t in check_sdd.TICKED.findall(gate) if check_sdd.FILE_LIKE.match(t)]
    if not named:
        return cell(gate)
    return "<br>".join(f"`{t}`" if repo == PRODUCT_NAME else t for t in named)


def render(rows: list[Row], empty: list[str], dates: list[str], device: str | None, sample: bool) -> str:
    converged = not empty and not any(r.blocking for r in rows)
    counts = {k: sum(1 for r in rows if r.result == k) for k in ORDER}
    first = "# Convergence verdict: Contraste release 1.0" + (" (SAMPLE RUN)" if sample else "")
    lines = [first, ""]
    if sample:
        lines += ["This is a SAMPLE written from small partial result files to show the format. It is replaced by the verdict of the "
                  "release run (`design.md`, the release procedure); until then every figure below is a sample, not a verdict.", ""]
    lines += [f"Verdict: **{'CONVERGED' if converged else 'NOT CONVERGED'}**", "",
              f"Run date: {max(dates) if dates else 'unknown'} (from the result files).",
              f"Device: {device if device else 'not stated (a skip for a device precondition is then not allowed)'}.",
              f"Rows: {len(rows)}. Generated by `scripts/convergence_verdict.py`; never edit by hand.", "",
              "| result | rows |", "|---|---|"]
    lines += [f"| {k} | {counts[k]} |" for k in ORDER]
    lines += ["", "| repository | passed | failed | skipped | absent |", "|---|---|---|---|---|"]
    for repo in sorted({r.repo for r in rows}):
        lines.append(f"| {repo} | " + " | ".join(str(sum(1 for r in rows if r.repo == repo and r.result == k)) for k in SHOWN) + " |")
    lines += ["", "## Features with no requirement rows", ""]
    lines += [f"- {e}" for e in empty] or ["None."]
    owners: dict[tuple[str, str], list[str]] = {}
    for r in rows:
        owners.setdefault((r.repo, r.rid), []).append(r.feature)
    lines += ["", "## Requirement IDs used by more than one feature (every row is still listed)", ""]
    lines += [f"- {repo} {rid}: {', '.join(sorted(features))}" for (repo, rid), features in sorted(owners.items()) if len(features) > 1] or ["None."]
    lines += ["", "## Requirements", "", "| repository | feature | id | gate | result | detail |", "|---|---|---|---|---|---|"]
    ordered = sorted(rows, key=lambda r: (r.repo, r.feature, r.rid))
    lines += [f"| {r.repo} | {r.feature} | {r.rid} | {gate_cell(r.gate, r.repo)} | {r.result} | {cell(r.detail)} |" for r in ordered]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    root = HERE.parent
    parser = argparse.ArgumentParser(description="Write the generated convergence verdict of Contraste release 1.0 (ADR-0075 section 4).")
    parser.add_argument("--product-junit", type=Path, required=True, help="pytest --junitxml file of this repository")
    parser.add_argument("--engine-junit", type=Path, required=True, help="pytest --junitxml file of the engine repository")
    parser.add_argument("--engine-repo", type=Path, required=True, help="the engine repository (read only)")
    parser.add_argument("--vitest", type=Path, required=True, help="vitest --reporter=json file of frontend/")
    parser.add_argument("--product-repo", type=Path, default=root, help="this repository (default: the one holding the script)")
    parser.add_argument("--out", type=Path, default=None, help=f"the verdict file (default {DEFAULT_OUT} in the product repository)")
    parser.add_argument("--device", default=None, help="the device the release run states; allows a skip for a device precondition")
    parser.add_argument("--script-timeout", type=int, default=DEFAULT_TIMEOUT, help="seconds a script gate may run (default 600)")
    parser.add_argument("--sample", action="store_true", help="mark the document as a sample run")
    args = parser.parse_args(argv)

    product, engine = args.product_repo.resolve(), args.engine_repo.resolve()
    missing = [(args.product_junit, "product-junit"), (args.engine_junit, "engine-junit"), (args.vitest, "vitest")]
    problems = [f"missing result file {p}; write it with: {RESULT_COMMANDS[key].format(file=p)}" for p, key in missing if not p.is_file()]
    problems += [f"missing repository folder {r / 'docs' / 'design' / 'features'}" for r in (product, engine)
                 if not (r / "docs" / "design" / "features").is_dir()]
    if problems:
        for line in problems:
            print(f"convergence_verdict: {line}", file=sys.stderr)
        return 2

    mine = load_results(args.product_junit, args.vitest)
    theirs = load_results(args.engine_junit, None)
    rows, empty = judge(PRODUCT_NAME, product, mine, args.script_timeout, args.device)
    more, empty_engine = judge(ENGINE_NAME, engine, theirs, args.script_timeout, args.device)
    rows += more
    text = render(rows, empty + empty_engine, mine.dates + theirs.dates, args.device, args.sample)
    out = args.out if args.out is not None else product / DEFAULT_OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    converged = not (empty + empty_engine) and not any(r.blocking for r in rows)
    counts = ", ".join(f"{k} {sum(1 for r in rows if r.result == k)}" for k in ORDER)
    print(f"convergence_verdict: {'CONVERGED' if converged else 'NOT CONVERGED'}, {len(rows)} rows ({counts}); wrote {out}")
    return 0 if converged else 1


if __name__ == "__main__":
    sys.exit(main())
