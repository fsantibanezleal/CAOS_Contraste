#!/usr/bin/env python3
"""T6: every repository path a document names exists (failure class 12: docs that point at files that moved).

Checks, in every tracked Markdown file:
  - relative link targets ([text](path), images included), resolved against the file's folder;
  - inline code spans that name a repository path (start with a top-level folder or file of this repository).
External links, anchors, globs and placeholders (<...>, {...}, *) are skipped. Exit 1 on any missing path.
Usage: python scripts/check_doc_paths.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE = re.compile(r"`([^`\s]+)`")
SKIP = re.compile(r"^(?:[a-z]+:|#|mailto:)|[<>{}*$]|\.\.\.")


def tracked() -> list[str]:
    # tracked and untracked, ignored excluded: a tree not yet committed is checked too
    cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return sorted({ln.strip() for ln in out.splitlines() if ln.strip()})


def main() -> int:
    files = [f for f in tracked() if (ROOT / f).is_file()]
    if not any(f.endswith(".md") for f in files):
        print("doc paths: no Markdown file to check; this is not a product tree")
        return 1
    tops = {f.split("/", 1)[0] for f in files}
    missing: list[str] = []
    for rel in files:
        # the changelog records history, including files that were removed
        if not rel.endswith(".md") or rel == "CHANGELOG.md":
            continue
        md = ROOT / rel
        text = md.read_text(encoding="utf-8", errors="ignore")
        in_fence = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for target in LINK.findall(line):
                target = target.split("#", 1)[0]
                if not target or SKIP.search(target):
                    continue
                if not (md.parent / target).resolve().exists():
                    missing.append(f"{rel}:{n}: link to {target}")
            for span in CODE.findall(line):
                # a test id (file::test) names its file here; check_sdd.py checks the test itself
                span = span.split("::", 1)[0].rstrip(".,;:")
                head = span.split("/", 1)[0]
                if "/" not in span and span not in tops:
                    continue
                if head not in tops or SKIP.search(span):
                    continue
                if not (ROOT / span).exists():
                    missing.append(f"{rel}:{n}: names {span}")
    for m in missing:
        print(f"doc paths: {m}")
    if not missing:
        print("doc paths: OK, every named path exists")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
