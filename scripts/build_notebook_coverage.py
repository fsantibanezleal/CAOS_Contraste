#!/usr/bin/env python3
"""Build ``notebooks/coverage.json`` (CAOS_MANAGE ``conventions/notebook-content-bar.md`` section 5) from the notebooks
themselves, so the map can never drift from them: every method of the SDD's ``## Method ladder`` maps to the notebooks
whose metadata ``caos.methods`` or ``caos.beyond`` names it, or whose topic declares it in
``notebooks/methods-taught/<topic>.json`` (a method of any tier taught at level 2 or higher); every contract of ``docs/contracts/catalog.md`` to the
notebooks whose ``caos.data`` reads a document the contract governs; every pipeline stage
(``data-pipeline/pipeline/stages/*.py``) to the notebooks whose code imports or names it; every method package of
``product.json`` to the notebooks whose ``caos.packages`` pins it. Paths are relative to a language tree, and a notebook
counts only when both trees hold it.

    python scripts/build_notebook_coverage.py           # write notebooks/coverage.json and list what no notebook covers
    python scripts/build_notebook_coverage.py --check   # exit 1 when the committed file differs or a part is uncovered

Standard library only.
"""
from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"
OUT = NB / "coverage.json"


def ladder_ids() -> list[str]:
    text = (ROOT / "docs" / "design" / "SDD.md").read_text(encoding="utf-8")
    start = text.index("## Method ladder")
    end = text.find("\n## ", start + 1)
    return re.findall(r"^\| ((?:M|BS)-\d+) \|", text[start:end], flags=re.M)


def contracts() -> dict[str, list[str]]:
    """Each contract id and the globs of the documents it governs (its documents cell, else its example)."""
    text = (ROOT / "docs" / "contracts" / "catalog.md").read_text(encoding="utf-8")
    start = text.index("## Contracts")
    end = text.find("\n## ", start + 1)
    out: dict[str, list[str]] = {}
    for line in text[start:end].splitlines():
        if not line.startswith("| ") or line.startswith("| id "):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 13 or set(cells[0]) <= {"-", ":"}:
            continue
        cid, example, documents = cells[0], cells[4], cells[5]
        globs = [g.strip() for g in documents.split(",") if g.strip() and g.strip() != "-" and not g.strip().startswith("!")]
        if not globs and example not in ("", "-"):
            globs = [example]
        out[cid] = globs
    return out


def stage_ids() -> list[str]:
    stages = ROOT / "data-pipeline" / "pipeline" / "stages"
    return sorted(p.stem for p in stages.glob("*.py") if not p.stem.startswith("_"))


def packages() -> list[str]:
    doc = json.loads((ROOT / "product.json").read_text(encoding="utf-8"))
    return [p if isinstance(p, str) else p.get("name", "") for p in doc.get("method_packages", [])]


def notebooks() -> dict[str, dict]:
    """Each notebook present in both trees, by its path relative to a tree, with its metadata and its code."""
    found: dict[str, dict] = {}
    for path in sorted((NB / "en").rglob("*.ipynb")):
        rel = path.relative_to(NB / "en").as_posix()
        if not (NB / "es" / rel).is_file():
            continue
        nb = json.loads(path.read_text(encoding="utf-8"))
        code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
        found[rel] = {"caos": nb.get("metadata", {}).get("caos", {}), "code": code}
    return found


TAUGHT = NB / "methods-taught"


def methods_taught(nbs: dict[str, dict], ladder: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """The ladder methods each topic declares it teaches, from ``notebooks/methods-taught/<topic>.json``.

    ``check_notebooks.py`` (template) keeps ``caos.methods`` for the sota methods a level 3 notebook runs and ``caos.beyond``
    for the claims of a level 4 notebook, so a method of another tier taught at level 2 or 3 has no metadata key. Each topic
    therefore declares ``{"<ladder id>": ["<topic>/<notebook>.ipynb", ...]}`` in its own file; a declaration counts only
    when the id is a ladder row and the notebook exists in both trees at level 2 or higher, so it cannot drift silently."""
    taught: dict[str, list[str]] = {}
    problems: list[str] = []
    for path in sorted(TAUGHT.glob("*.json")):
        rel = f"notebooks/methods-taught/{path.name}"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{rel}: cannot read ({exc})")
            continue
        if not isinstance(doc, dict):
            problems.append(f"{rel}: must be an object of ladder id to notebook paths")
            continue
        for mid, paths in doc.items():
            if mid not in ladder:
                problems.append(f"{rel}: {mid!r} is not a row of the SDD's Method ladder")
                continue
            if not isinstance(paths, list) or not all(isinstance(p, str) for p in paths):
                problems.append(f"{rel}: {mid} must list notebook paths")
                continue
            for p in paths:
                if not p.startswith(f"{path.stem}/"):
                    problems.append(f"{rel}: {mid} names {p}, outside the topic {path.stem}")
                elif p not in nbs:
                    problems.append(f"{rel}: {mid} names {p}, which is not in both trees")
                elif nbs[p]["caos"].get("level", 0) < 2:
                    problems.append(f"{rel}: {mid} names {p}, a level 1 notebook (methods count from level 2)")
                else:
                    taught.setdefault(mid, []).append(p)
    return taught, problems


def build() -> tuple[dict, list[str], list[str]]:
    nbs = notebooks()
    cov: dict[str, dict[str, list[str]]] = {"methods": {}, "contracts": {}, "stages": {}, "packages": {}}
    missing: list[str] = []
    ladder = ladder_ids()
    taught, problems = methods_taught(nbs, ladder)
    for mid in ladder:
        hits = [p for p, n in nbs.items()
                if mid in (n["caos"].get("methods") or []) + (n["caos"].get("beyond") or []) and n["caos"].get("level", 0) >= 2]
        hits += [p for p in taught.get(mid, []) if p not in hits]
        cov["methods"][mid] = hits
        if not hits:
            missing.append(f"method {mid}")
    for cid, globs in contracts().items():
        hits = [p for p, n in nbs.items()
                if any(fnmatch.fnmatch(d, g) for d in n["caos"].get("data") or [] for g in globs)]
        cov["contracts"][cid] = hits
        if not hits:
            missing.append(f"contract {cid}")
    for sid in stage_ids():
        pat = re.compile(rf"\bstages\.{sid}\b|\bstages import [^\n]*\b{sid}\b|stages/{sid}\.py")
        hits = [p for p, n in nbs.items() if pat.search(n["code"])]
        cov["stages"][sid] = hits
        if not hits:
            missing.append(f"stage {sid}")
    for pk in packages():
        hits = [p for p, n in nbs.items() if any(str(x).split("==")[0].split("[")[0] == pk for x in n["caos"].get("packages") or [])]
        cov["packages"][pk] = hits
        if not hits:
            missing.append(f"package {pk}")
    for group in cov:
        cov[group] = {k: v for k, v in cov[group].items() if v}
    return cov, missing, problems


def main() -> int:
    cov, missing, declared = build()
    text = json.dumps(cov, indent=1, ensure_ascii=False) + "\n"
    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        problems = (["notebooks/coverage.json is not current: run python scripts/build_notebook_coverage.py"]
                    if current != text else []) + [f"no notebook covers {m}" for m in missing] + declared
        for p in problems:
            print(f"  - {p}")
        print("notebook coverage: OK" if not problems else f"notebook coverage: {len(problems)} findings")
        return 1 if problems else 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}: " + ", ".join(f"{len(v)} {k}" for k, v in cov.items()))
    for m in missing:
        print(f"  uncovered: {m}")
    for d in declared:
        print(f"  declaration: {d}")
    return 1 if declared else 0


if __name__ == "__main__":
    sys.exit(main())
