#!/usr/bin/env python3
"""T5: make a product from this template, in one step that leaves nothing of the template's identity behind.

    python scripts/instantiate.py --slug contraste --name Contraste --repo CAOS_Contraste \\
        --deploy pages --domain contraste.fasl-work.com --visibility public \\
        --tagline-en "Financial risk models, built and validated." \\
        --tagline-es "Modelos de riesgo financiero, construidos y validados."

What it does, in order:
  1. refuses unless this tree is the template (the .template-source sentinel is present);
  2. writes product.json (name, slug, taglines in both languages, repository, visibility, licence, holder, year)
     and the frontend package name;
  3. resets VERSION to 0.01.000, starts CHANGELOG.md with the instantiation entry, and records the template release
     it started from in .template-version (ADR-0078: a product adopts a later base deliberately);
  4. writes the MIT LICENSE with the year and the holder;
  5. writes deploy/TARGET and removes the other deploy place (one deploy place, decided first): `pages` removes the
     VPS unit and site templates and, with --domain, writes frontend/public/CNAME; `vps` removes the Pages workflow
     and fills the unit and site templates with the slug and domain;
  6. deletes the sentinel and the template blueprint files (STRUCTURE.md, .vscode/);
  7. writes a README for the product (its name, taglines, badges, how to run it);
  8. unless --no-run: bakes the cases, runs the tests, builds the web once, and reports what of the example remains
     (scripts/check_template_residue.py), which is the list of what the product replaces next.
Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNER = "fsantibanezleal"
HOLDER = "Felipe Santibáñez-Leal"

MIT = """MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def write(rel: str, text: str) -> None:
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"  wrote   {rel}")


def remove(rel: str) -> None:
    path = ROOT / rel
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()
    else:
        return
    print(f"  removed {rel}")


def readme(a: argparse.Namespace) -> str:
    repo = f"{OWNER}/{a.repo}"
    site = f"https://{a.domain}" if a.domain else (f"https://{OWNER}.github.io/{a.repo}/" if a.deploy == "pages" else "")
    badges = [
        f"[![CI](https://img.shields.io/github/actions/workflow/status/{repo}/ci.yml?branch=main&label=CI)](https://github.com/{repo}/actions)",
        f"[![License](https://img.shields.io/github/license/{repo})](LICENSE)",
        f"[![Version](https://img.shields.io/github/v/tag/{repo}?label=version&sort=semver)](https://github.com/{repo}/tags)",
    ]
    if site and a.visibility == "public":
        badges.append(f"[![Live](https://img.shields.io/badge/site-live-2ea44f)]({site})")
    return "\n".join([
        f"# {a.name}",
        "",
        *badges,
        "",
        a.tagline_en,
        "",
        f"*{a.tagline_es}*",
        "",
        "## Run it",
        "",
        "```bash",
        "./scripts/setup.sh                     # the pipeline environment (.venv-pipeline); setup.ps1 on Windows",
        "./scripts/precompute.sh                # the canonical bake into data/derived (a release operation)",
        ".venv-pipeline/bin/python -m pytest    # the pipeline tests, sandboxed",
        "cd frontend && npm ci && npm run build && npm test && npm run gate",
        "```",
        "",
        "## Documentation",
        "",
        "- [docs/design/SDD.md](docs/design/SDD.md): the design, every requirement with its gate.",
        "- [docs/](docs/README.md): architecture, guides, cases and frameworks.",
        "",
        f"Licensed under the MIT License (see [LICENSE](LICENSE)). Deployed to {a.deploy}"
        + (f" at {site}" if site else "")
        + ".",
        "",
    ])


def run(cmd: list[str], cwd: Path) -> bool:
    print(f"  $ {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, cwd=cwd, check=False).returncode == 0
    except OSError as e:
        print(f"    could not run: {e}")
        return False


def main() -> int:
    p = argparse.ArgumentParser(prog="instantiate")
    p.add_argument("--slug", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--repo", required=True, help="the GitHub repository name, for example CAOS_Contraste")
    p.add_argument("--deploy", required=True, choices=("pages", "vps"))
    p.add_argument("--domain", default="", help="the custom domain, for example contraste.fasl-work.com")
    p.add_argument("--visibility", required=True, choices=("public", "private"))
    p.add_argument("--tagline-en", required=True)
    p.add_argument("--tagline-es", required=True)
    p.add_argument("--holder", default=HOLDER)
    p.add_argument("--year", type=int, default=dt.date.today().year)
    p.add_argument("--no-run", action="store_true", help="skip the bake, tests and build")
    a = p.parse_args()

    if not (ROOT / ".template-source").exists():
        print("instantiate: this tree is not the template (no .template-source); it was instantiated already")
        return 2
    if not re.fullmatch(r"[a-z][a-z0-9-]*", a.slug):
        print("instantiate: --slug is lower-case letters, digits and hyphens")
        return 2
    if a.name.strip() in {"", "CAOS Product"} or not a.tagline_en.strip() or not a.tagline_es.strip():
        print("instantiate: --name, --tagline-en and --tagline-es must be the product's own")
        return 2
    if a.deploy == "vps" and not a.domain:
        print("instantiate: a VPS deploy needs --domain")
        return 2

    template_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    print(f"instantiate: {a.name} ({a.slug}) from CAOS_PRODUCT_TEMPLATE {template_version}")

    product = {
        "name": a.name,
        "slug": a.slug,
        "tagline": {"en": a.tagline_en, "es": a.tagline_es},
        "repo": f"https://github.com/{OWNER}/{a.repo}",
        "visibility": a.visibility,
        "license": "MIT",
        "holder": a.holder,
        "year": a.year,
    }
    write("product.json", json.dumps(product, indent=2, ensure_ascii=False) + "\n")
    pkg_path = ROOT / "frontend" / "package.json"
    pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    pkg.update({"name": f"{a.slug}-frontend", "version": "0.1.0", "license": "MIT"})
    write("frontend/package.json", json.dumps(pkg, indent=2) + "\n")

    write("VERSION", "0.01.000\n")
    # The release tag names the template commit; the product repository cannot see it (a repository created from a
    # GitHub template starts a new history, and a copy has the product's own HEAD).
    write(".template-version", f"CAOS_PRODUCT_TEMPLATE {template_version} (tag v{template_version})\n")
    today = dt.date.today().isoformat()
    write("CHANGELOG.md", "\n".join([
        "# Changelog",
        "",
        "All notable changes to this product. Versions are X.XX.XXX (VERSION is the single source); every release is",
        "tagged.",
        "",
        f"## [0.01.000], {today}",
        "",
        "### Added",
        "",
        f"- Instantiated from CAOS_PRODUCT_TEMPLATE {template_version}: the pipeline, the two contracts, the lanes, the",
        "  workbench on the shared shell, the six routes, the guards and the measured gate.",
        "",
    ]))
    write("LICENSE", MIT.format(year=a.year, holder=a.holder))

    write("deploy/TARGET", f"{a.deploy}\n")
    if a.deploy == "pages":
        remove("deploy/fasl-slug.service")
        remove("deploy/domain.nginx")
        if a.domain:
            write("frontend/public/CNAME", f"{a.domain}\n")
    else:
        remove(".github/workflows/deploy-pages.yml")
        remove("deploy/pages.md")
        for src, dst in (("deploy/fasl-slug.service", f"deploy/fasl-{a.slug}.service"), ("deploy/domain.nginx", f"deploy/{a.domain}.nginx")):
            text = (ROOT / src).read_text(encoding="utf-8").replace("<slug>", a.slug).replace("<domain>", a.domain)
            write(dst, text)
            remove(src)

    for rel in (".template-source", "STRUCTURE.md", ".vscode"):
        remove(rel)
    write("README.md", readme(a))

    if a.no_run:
        print("instantiate: done (--no-run). Next: replace the example; scripts/check_template_residue.py lists it.")
        return 0
    venv = next((c for c in (ROOT / ".venv-pipeline" / "Scripts" / "python.exe", ROOT / ".venv-pipeline" / "bin" / "python") if c.exists()), None)
    py = str(venv) if venv else sys.executable
    ok = run([py, "data-pipeline/run.py"], ROOT) and run([py, "-m", "pytest", "-q"], ROOT)
    npm = shutil.which("npm")
    if npm:
        front = ROOT / "frontend"
        ok = run([npm, "ci"], front) and run([npm, "run", "build"], front) and run([npm, "test"], front) and ok
    else:
        print("  npm not found: build the web with `cd frontend && npm ci && npm run build`")
    run([py, "scripts/check_template_residue.py"], ROOT)
    print("instantiate: done. The residue list above is what this product replaces next (the example model, cases,")
    print("pages and diagrams); the guards fail until it is gone.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
