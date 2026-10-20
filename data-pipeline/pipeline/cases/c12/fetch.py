"""The raw inputs of C12 and their fetch: the US Treasury par yield curves (2024 to the current year, beside the years the
data root already holds) and the Treasury HQM corporate bond spot curves (end of month).

Both sources are public: ``treasury-par-curve`` is registered (class mirror-allowed); ``treasury-hqm`` is proposed in the
changes fragment ``changes/U9-P1.md`` and described here by :data:`HQM_SOURCE` until the integrator adds its registry row. The
bake reads files from the device data root and never the network; ``fetch`` writes them there, with a sidecar per folder (URL,
size, SHA-256, retrieval date), and ``load_provenance`` recomputes every hash: a file that differs from its record is refused.

    python data-pipeline/pipeline/cases/c12/fetch.py --data-root <root>      writes them
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

from ...io import treasury

TREASURY_DIR = treasury.TREASURY_DIR
HQM_DIR = "treasury-hqm"
PROVENANCE = "provenance.json"
#: the sidecar this case writes next to the one an earlier unit wrote in the same folder
C12_PROVENANCE = "provenance-c12.json"
FIRST_TREASURY_YEAR = 1990
FETCH_FROM_YEAR = 2024
HQM_BASE = "https://home.treasury.gov/system/files/226/"
HQM_PAGE = "https://home.treasury.gov/data/treasury-coupon-issues-and-corporate-bond-yield-curve/corporate-bond-yield-curve"
#: the end-of-month spot-rate blocks the bake reads: the stress window (2007 to 2009) and the curve date's block
HQM_FILES = ("hqmeom_04_08.xls", "hqmeom_09_13.xls", "hqmeom_24_28.xls")
USER_AGENT = "Mozilla/5.0 (Contraste data fetch; contact: Contraste maintainers)"
HQM_SOURCE = {
    "id": "treasury-hqm", "name": "US Treasury High Quality Market (HQM) corporate bond yield curve, end-of-month spot rates",
    "publisher": "U.S. Department of the Treasury", "landing": HQM_PAGE, "class": "mirror-allowed",
    "licence": "no licence sentence found on home.treasury.gov; FRED tags the series Public Domain: Citation Requested (the Treasury-side sentence is UNVERIFIED)",
    "attribution": "U.S. Department of the Treasury, High Quality Market (HQM) Corporate Bond Yield Curve",
    "access": "xls download, no key", "cases": ["C12"],
    "unverified": ["an explicit copyright or public-domain sentence on home.treasury.gov"],
}


def hqm_url(name: str) -> str:
    return HQM_BASE + name


def _download(url: str, timeout: float = 120.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https, public sources)
        return resp.read()


def _row(raw: Path, name: str, url: str, retrieved: str) -> dict[str, Any]:
    body = _download(url)
    (raw / name).write_bytes(body)
    return {"name": name, "url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "retrieved": retrieved}


def fetch(data_root: str | Path, today: str | None = None, last_year: int | None = None) -> dict[str, list[dict[str, Any]]]:
    """Download the Treasury par years ``FETCH_FROM_YEAR`` to ``last_year`` (default the current year) and the HQM blocks."""
    root = Path(data_root) / "raw"
    when = today or dt.date.today().isoformat()
    last = last_year or dt.date.fromisoformat(when).year
    out: dict[str, list[dict[str, Any]]] = {}
    for folder, files, sidecar in (
        (TREASURY_DIR, [(treasury.file_name(y), treasury.url(y)) for y in range(FETCH_FROM_YEAR, last + 1)], C12_PROVENANCE),
        (HQM_DIR, [(n, hqm_url(n)) for n in HQM_FILES], PROVENANCE),
    ):
        d = root / folder
        d.mkdir(parents=True, exist_ok=True)
        rows = [_row(d, name, url, when) for name, url in files]
        (d / sidecar).write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
        out[folder] = rows
    return out


def _sidecar(folder: Path, names: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for side in names:
        p = folder / side
        if p.exists():
            for r in json.loads(p.read_text(encoding="utf-8")):
                out[r["name"]] = r
    return out


def _records(folder: Path, files: list[Path], urls: dict[str, str], sidecars: tuple[str, ...]) -> list[dict[str, Any]]:
    """One record per file, hashes measured on the bytes; the retrieval date is the sidecar's where a sidecar names the file,
    else the file's modification date (a file another unit fetched without one). A sidecar record whose hash differs from the
    bytes refuses the file."""
    recorded = _sidecar(folder, sidecars)
    out = []
    for f in files:
        rec = treasury.describe(f, urls[f.name], recorded.get(f.name, {}).get("retrieved")).to_json()
        old = recorded.get(f.name)
        if old is not None and (old["sha256"] != rec["sha256"] or old["bytes"] != rec["bytes"]):
            raise ValueError(f"{f}: differs from its provenance record (sha256 {rec['sha256']})")
        out.append(rec)
    return out


def load_provenance(data_root: str | Path, first_year: int = FIRST_TREASURY_YEAR) -> dict[str, list[dict[str, Any]]]:
    """The provenance record of every raw file the bake reads. A file that is not in the data root raises
    :class:`~pipeline.io.treasury.DeclaredAbsence` naming the URL it is fetched from."""
    root = Path(data_root) / "raw"
    hint = "python data-pipeline/pipeline/cases/c12/fetch.py --data-root <root>"
    tdir, hdir = root / TREASURY_DIR, root / HQM_DIR
    years = sorted({int(p.stem.rsplit("-", 1)[1]) for p in tdir.glob("daily-treasury-par-*.csv")})
    if not years or years[0] > first_year:
        treasury.need(tdir / treasury.file_name(first_year), treasury.url(first_year), hint)
    for y in range(first_year, years[-1] + 1):
        treasury.need(tdir / treasury.file_name(y), treasury.url(y), hint)
    files = [tdir / treasury.file_name(y) for y in range(first_year, years[-1] + 1)]
    hfiles = [treasury.need(hdir / n, hqm_url(n), hint) for n in HQM_FILES]
    return {
        TREASURY_DIR: _records(tdir, files, {f.name: treasury.url(int(f.stem.rsplit("-", 1)[1])) for f in files},
                               (PROVENANCE, C12_PROVENANCE)),
        HQM_DIR: _records(hdir, hfiles, {n: hqm_url(n) for n in HQM_FILES}, (PROVENANCE,)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.cases.c12.fetch")
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--today", default=None, help="ISO retrieval date recorded in the sidecars (default: today)")
    args = ap.parse_args()
    for folder, rows in fetch(args.data_root, args.today).items():
        for r in rows:
            print(f"{folder}/{r['name']}: {r['bytes']:,} bytes sha256 {r['sha256'][:12]}")


if __name__ == "__main__":
    main()
