"""Plants for the measured browser gate (`frontend/scripts/gate.mjs`, the shell's caos-shell-gate): CT-106, CT-107 and
the per-case gate requirements CT-211, CT-217, CT-310 and CT-413.

The gate is the shell's; these tests prove that the product's wrapper runs it on the built site and that it fails on the
two defects a reader would meet first: a workbench wider than the viewport, and a site that is not this product. They
need node, the installed frontend packages, a built site (`npm run build`) and a browser installed by Playwright, so
they are `local-only`; a run takes tens of seconds because the gate is limited to one size, one theme and one language.
The plant is not specific to a case: it makes the workbench route, which carries every case, fail."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from planting import NODE, NODE_MODULES, ROOT, link_node_modules, unlink_node_modules

# CONTRASTE_DIST names a built site elsewhere (the checked-out branch cannot build until the web reads the readiness)
DIST = Path(os.environ.get("CONTRASTE_DIST", ROOT / "frontend" / "dist"))
BROWSERS = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""))
READY = NODE is not None and (NODE_MODULES / "playwright").is_dir() and (DIST / "index.html").is_file() \
    and BROWSERS.is_dir() and any(BROWSERS.glob("chromium*"))
pytestmark = pytest.mark.skipif(not READY, reason="needs node, the installed frontend packages, a built site and a Playwright browser")

ARGS = ["--sizes", "1280x800", "--themes", "light", "--langs", "en", "--no-wide-font"]


def _site(tmp: Path) -> Path:
    site = tmp / "site"
    (site / "frontend" / "scripts").mkdir(parents=True)
    shutil.copytree(DIST, site / "frontend" / "dist")
    shutil.copy2(ROOT / "frontend" / "scripts" / "gate.mjs", site / "frontend" / "scripts" / "gate.mjs")
    shutil.copy2(ROOT / "product.json", site / "product.json")
    return site


def _gate(site: Path) -> subprocess.CompletedProcess:
    link_node_modules(site / "frontend")
    try:
        return subprocess.run([NODE, "scripts/gate.mjs", *ARGS], cwd=site / "frontend", capture_output=True, encoding="utf-8",
                              errors="replace", timeout=900)
    finally:
        unlink_node_modules(site / "frontend")


def test_ct106_ct211_ct217_ct310_ct413_a_workbench_wider_than_the_viewport_fails_the_measured_gate(tmp_path: Path) -> None:
    site = _site(tmp_path)
    ok = _gate(site)
    assert ok.returncode == 0, (ok.stdout + ok.stderr)[-2500:]
    # every route's own page: the build materialises one index.html per route (scripts/materialize-routes.mjs), and the
    # gate loads /app and the documentation routes from theirs, so a plant in the root page alone never reaches them
    pages = sorted((site / "frontend" / "dist").rglob("index.html"))
    assert (site / "frontend" / "dist" / "app" / "index.html") in pages, pages
    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert "</head>" in html, page
        page.write_text(html.replace("</head>", "<style>html,body{min-width:2400px !important}</style></head>", 1), encoding="utf-8")
    bad = _gate(site)
    out = bad.stdout + bad.stderr
    assert bad.returncode == 1 and "FAIL" in out, out[-2500:]


def test_ct107_a_site_that_is_not_this_product_fails_the_measured_gate(tmp_path: Path) -> None:
    site = _site(tmp_path)
    ok = _gate(site)
    assert ok.returncode == 0, (ok.stdout + ok.stderr)[-2500:]
    product = (site / "product.json").read_text(encoding="utf-8")
    assert '"name": "Contraste"' in product
    (site / "product.json").write_text(product.replace('"name": "Contraste"', '"name": "Another product"', 1), encoding="utf-8")
    bad = _gate(site)
    out = bad.stdout + bad.stderr
    assert bad.returncode == 1 and "FAIL" in out, out[-2500:]
