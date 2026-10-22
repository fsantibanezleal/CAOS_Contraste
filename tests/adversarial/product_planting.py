"""Helpers of the product's adversarial tests: plant one defect in a copy, run the real gate on it, and prove it ran. They sit beside the template's
`planting.py` (taken verbatim, the helpers the template's own plants use) and stand on the template's `conftest.py` fixtures (`base_copy`, `repo`)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")
NODE_MODULES = ROOT / "frontend" / "node_modules"
WEB_READY = NODE is not None and (NODE_MODULES / "vitest").is_dir()

_CLEAN: dict[tuple[str, ...], str] = {}


def _run(repo: Path, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    # the child writes UTF-8 as the parent reads it (Python's UTF-8 mode): on Windows a pipe defaults to the ANSI code page,
    # and a guard that prints the planted emoji would fail on its own output instead of on the plant
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(args, capture_output=True, encoding="utf-8", errors="replace", cwd=repo, timeout=timeout, env=env)


def pytest_gate(repo: Path, *selectors: str) -> subprocess.CompletedProcess:
    """Run the gate tests ``selectors`` (``path::name``) of the copy, in a fresh interpreter, as a reader would."""
    return _run(repo, [sys.executable, "-m", "pytest", *selectors, "-x", "-p", "no:cacheprovider", "--no-header",
                       "--tb=short"])


def script_gate(repo: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    """Run ``repo/scripts/<script>`` as CI does; proves it ran (the file exists, it returned a code and printed)."""
    path = repo / "scripts" / script
    assert path.is_file(), f"{script} is not in the copy"
    r = _run(repo, [sys.executable, str(path), *args], timeout=120)
    assert isinstance(r.returncode, int) and r.stdout.strip(), f"{script} printed nothing (exit {r.returncode}): {r.stderr[-900:]}"
    return r


def clean_passes(base: Path, *selectors: str) -> None:
    """The unplanted copy passes the gate (cached per selector): a plant is only evidence against a gate that can pass."""
    key = tuple(selectors)
    if key not in _CLEAN:
        r = pytest_gate(base, *selectors)
        assert r.returncode == 0 and " passed" in r.stdout and "skipped" not in r.stdout, f"clean copy: {r.stdout[-1500:]}"
        _CLEAN[key] = r.stdout
    assert _CLEAN[key]


def refute(base: Path, repo: Path, selectors: str | tuple[str, ...], plant: Callable[[Path], Any], *needles: str) -> str:
    """Clean copy passes; ``plant(repo)`` plants one defect; the same gate then FAILS (exit 1, a failed test) and its
    output names each of ``needles``. Returns the planted run's output."""
    sel = (selectors,) if isinstance(selectors, str) else tuple(selectors)
    clean_passes(base, *sel)
    plant(repo)
    r = pytest_gate(repo, *sel)
    assert r.returncode == 1 and " failed" in r.stdout, f"the plant was not caught: exit {r.returncode}\n{r.stdout[-1500:]}"
    for n in needles:
        assert n in r.stdout, f"{n!r} not in the failure output:\n{r.stdout[-2500:]}"
    return r.stdout


# ------------------------------------------------------------------ planting

def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def edit(repo: Path, rel: str, old: str, new: str, *, count: int = 1) -> None:
    """Replace ``old`` by ``new`` in a file of the copy (LF or CRLF); fails when ``old`` is absent: a plant that plants
    nothing is no plant."""
    path = repo / rel
    text = _read(path)
    crlf = "\r\n" in text
    old_f, new_f = (old.replace("\n", "\r\n"), new.replace("\n", "\r\n")) if crlf else (old, new)
    assert old_f in text, f"{rel} does not contain {old!r}: the plant would change nothing"
    path.write_bytes(text.replace(old_f, new_f, count).encode("utf-8"))


def edit_re(repo: Path, rel: str, pattern: str, new: str, *, count: int = 1) -> None:
    path = repo / rel
    text = _read(path)
    out, n = re.subn(pattern, new, text, count=count, flags=re.S)
    assert n >= 1, f"{rel} does not match {pattern!r}: the plant would change nothing"
    path.write_bytes(out.encode("utf-8"))


def edit_json(repo: Path, rel: str, fn: Callable[[Any], Any]) -> None:
    """Load a JSON file of the copy, let ``fn`` mutate it in place (its return value is ignored), write it back."""
    path = repo / rel
    doc = json.loads(_read(path))
    fn(doc)
    path.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def load_json(repo: Path, rel: str) -> Any:
    return json.loads(_read(repo / rel))


# ------------------------------------------------------------------ the web (node and the installed packages)

def link_node_modules(frontend: Path) -> None:
    """Make the copy's frontend/node_modules the real one (a junction on Windows, a symlink elsewhere)."""
    target = frontend / "node_modules"
    if os.path.isjunction(target):
        os.rmdir(target)  # a link left by an earlier run: removes the link, never the real tree
    elif target.exists() and not target.is_symlink():
        shutil.rmtree(target)  # the template's conftest puts the shell's schema in a real node_modules folder of the copy
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(NODE_MODULES)], check=True, capture_output=True)
    else:
        target.symlink_to(NODE_MODULES, target_is_directory=True)


def unlink_node_modules(frontend: Path) -> None:
    target = frontend / "node_modules"
    if target.is_symlink() or os.name == "nt":
        os.rmdir(target)  # removes the link, never the real tree


def vitest_gate(repo: Path, *files: str) -> subprocess.CompletedProcess:
    """Run vitest on test files of the copy's frontend (the installed packages are linked in, then unlinked)."""
    link_node_modules(repo / "frontend")
    try:
        return _run(repo / "frontend", [NODE, "node_modules/vitest/vitest.mjs", "run", *files, "--reporter=default"], timeout=300)
    finally:
        unlink_node_modules(repo / "frontend")


def prune_planned_cases(repo: Path) -> None:
    """The clean baseline of the copy: the index lists the cases the readiness declares absent (their manifests do not
    exist yet), and three web gates read every listed manifest. The copy lists only the cases that exist, so that the
    clean run passes and the plant is the only difference."""
    def mutate(d: dict) -> None:
        d["cases"] = [c for c in d["cases"] if (repo / "data" / "derived" / c["manifest_path"]).is_file()]
        d["n_cases"] = len(d["cases"])

    edit_json(repo, "data/derived/manifests/index.json", mutate)


def refute_web(repo: Path, files: str | tuple[str, ...], plant: Callable[[Path], Any], *needles: str, prepare: Callable[[Path], Any] | None = None) -> str:
    """The web twin of ``refute``: the clean copy's vitest run passes, the planted one fails naming each needle."""
    fs = (files,) if isinstance(files, str) else tuple(files)
    if prepare is not None:
        prepare(repo)
    ok = vitest_gate(repo, *fs)
    assert ok.returncode == 0 and "passed" in ok.stdout + ok.stderr, f"clean copy: {(ok.stdout + ok.stderr)[-1500:]}"
    plant(repo)
    r = vitest_gate(repo, *fs)
    out = r.stdout + r.stderr
    assert r.returncode != 0 and "failed" in out.lower(), f"the plant was not caught: exit {r.returncode}\n{out[-1500:]}"
    for n in needles:
        assert n in out, f"{n!r} not in the failure output:\n{out[-2500:]}"
    return out


def git_init(repo: Path) -> None:
    """Make the copy a git repository with every file added (the guards list the files git tracks)."""
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
