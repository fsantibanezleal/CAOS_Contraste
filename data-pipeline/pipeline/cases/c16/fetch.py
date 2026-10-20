"""The raw inputs of C16 and their fetch: the FDIC BankFind financials of one bank over the wider span, the Federal Reserve H.8
release pages, the Federal Reserve review of the supervision of SVB (the event anchors are checked against its text), and (read only, fetched by C14) the US Treasury par yield curves.

The sources are public and registered (``fdic-bankfind``, ``fed-h8``, ``treasury-par-curve``, class mirror-allowed). The bake reads
files from the device data root and never the network; ``fetch`` writes them there, with a sidecar ``provenance-c16.json`` per
source folder (URL, size, SHA-256, retrieval date), which the bake copies into ``data/derived/C16/raw-sources.txt``. C16 writes
its own FDIC file and its own sidecar next to C14's and never touches C14's file or sidecar (U11 sizing R2); the Treasury files
are C14's and are read through their own sidecar ``provenance.json``.

    python data-pipeline/pipeline/cases/c16/fetch.py --data-root <root>      writes them
    python data-pipeline/run.py C16 --data-root <root>                       reads  <root>/raw/fdic-financials/, fed-h8/, treasury-par/
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ...io import treasury

CERT = 24735
BANK = "Silicon Valley Bank"
FDIC_DIR = "fdic-financials"
H8_DIR = "fed-h8"
SVB_DIR = "fed-svb-review"
SVB_NAME = "svb-review-20230428.pdf"
SVB_URL = "https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf"
TREASURY_DIR = treasury.TREASURY_DIR
PROVENANCE = "provenance-c16.json"
TREASURY_PROVENANCE = "provenance.json"      # the sidecar of C14's Treasury fetch, read here and never written
FIRST_REPDTE = "20091231"
LAST_REPDTE = "20221231"
USER_AGENT = "Mozilla/5.0 (Contraste data fetch; contact: Contraste maintainers)"
#: the Friday of the first March 2023 release, the 28-day stride back to the first release of the 52-week calibration window, and the
#: releases that carry the weeks of March 2023 (each page lists four Wednesdays, so a 28-day stride tiles the window without a gap)
H8_ANCHOR = dt.date(2023, 3, 3)
H8_STRIDES = 14
H8_EVENT_RELEASES = ("20230310", "20230317", "20230324", "20230331", "20230407")
#: one request every PAUSE_SECONDS (a polite rate), and at most RETRIES attempts with a growing wait on a 429 or a server error
PAUSE_SECONDS = 1.0
RETRIES = 5

#: every field the C16 bake reads from the FDIC financials (names as in the BankFind Suite RISVIEW dictionary, addendum L3)
FDIC_FIELDS = (
    "CERT", "REPDTE", "NAME", "ASSET", "LIAB", "EQ", "RBCT1J",
    "DEP", "DEPDOM", "DEPFOR", "DEPNIDOM", "DEPIDOM", "DEPNIFOR", "DEPIFOR", "DEPINS", "DEPUNA", "DEPSMAMT", "DEPSMB", "DEPLGAMT", "DEPLGB",
    "NTRTIME", "CD3LES", "CD3T12", "CD1T3", "CDOV3", "CD3LESS", "CD3T12S", "CD1T3S", "CDOV3S",
    "CHBAL", "FREPO", "FREPP", "SC", "SCRDEBT", "SCAF", "SCAA", "SCHA", "SCHF",
    "SCUST", "SCUS", "SCAGE", "SCASPNSUM", "SCASPNHA", "SCASPNAF", "SCSPN", "SCMTGBK", "SCGTY", "SCCOL", "SCCMOT", "SCMUNI", "SCDOMO",
    "SCFORD", "SCEQFV", "SCPLEDGE", "SCHTMRES",
    "SCNM3LES", "SCNM3T12", "SCNM1T3", "SCNM3T5", "SCNM5T15", "SCNMOV15",
    "SCPT3LES", "SCPT3T12", "SCPT1T3", "SCPT3T5", "SCPT5T15", "SCPTOV15", "SCO3YLES", "SCOOV3Y",
    "LNLSGR", "LNLSNET", "LNATRES",
    "LNRS3LES", "LNRS3T12", "LNRS1T3", "LNRS3T5", "LNRS5T15", "LNRSOV15",
    "LNOT3LES", "LNOT3T12", "LNOT1T3", "LNOT3T5", "LNOT5T15", "LNOTOV15",
    "OTHBFHLB", "OTHBFH1L", "OTBFH1T3", "OTBFH3T5", "OTBFHOV5", "OTHBRF", "OTBOT1L", "OTBOT1T3", "OTBOT3T5", "OTBOTOV5", "SUBND",
)


def fdic_url(cert: int = CERT) -> str:
    query = urllib.parse.urlencode({
        "filters": f"CERT:{cert} AND REPDTE:[{FIRST_REPDTE} TO {LAST_REPDTE}]", "fields": ",".join(FDIC_FIELDS),
        "sort_by": "REPDTE", "sort_order": "ASC", "limit": "100"}, quote_via=urllib.parse.quote)
    return f"https://api.fdic.gov/banks/financials?{query}"


def fdic_name(cert: int = CERT) -> str:
    return f"financials-cert{cert}-{FIRST_REPDTE}-{LAST_REPDTE}.json"


def h8_release_dates() -> tuple[str, ...]:
    """The release Fridays fetched: the 52-week calibration window at a 28-day stride (the first release of March 2023 and back), then
    the releases that carry the Wednesdays of March 2023 and the first week of April (the last Wednesday of March is in 20230407)."""
    window = [(H8_ANCHOR - dt.timedelta(days=28 * k)).strftime("%Y%m%d") for k in range(H8_STRIDES - 1, -1, -1)]
    return (*window, *H8_EVENT_RELEASES)


def h8_url(release: str) -> str:
    return f"https://www.federalreserve.gov/releases/h8/{release}/"


def h8_name(release: str) -> str:
    return f"h8-{release}.html"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def describe(path: Path, url: str, retrieved: str) -> dict[str, Any]:
    """The provenance record of a raw file: name, URL, size, SHA-256 and retrieval date."""
    path = Path(path)
    return {"name": path.name, "url": url, "bytes": path.stat().st_size, "sha256": sha256_of(path), "retrieved": retrieved}


def _download(url: str, timeout: float = 90.0) -> bytes:
    """One GET; a 429 or 5xx is retried (at most RETRIES attempts, a wait of 10, 20, 30 ... seconds). A 403 or 404 is the caller's:
    the Board's CDN answers 403 for a release date that has no page (a Friday holiday), which the caller reads as 'not this day'."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https, public sources)
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == RETRIES:
                raise
            time.sleep(10.0 * attempt)
    raise AssertionError("unreachable")


def _write(folder: Path, name: str, url: str, retrieved: str, body: bytes) -> dict[str, Any]:
    (folder / name).write_bytes(body)
    return describe(folder / name, url, retrieved)


def fetch(data_root: str | Path, today: str | None = None, *, download: Callable[..., bytes] = _download,
          releases: Sequence[str] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Download the FDIC wide-span financials and the H.8 release pages into ``<root>/raw`` and write the C16 sidecars. A release
    Friday without a page (a holiday, answered 403 or 404) is tried on the Thursday before it."""
    root = Path(data_root) / "raw"
    when = today or dt.date.today().isoformat()
    out: dict[str, list[dict[str, Any]]] = {}
    fd = root / FDIC_DIR
    fd.mkdir(parents=True, exist_ok=True)
    out[FDIC_DIR] = [_write(fd, fdic_name(), fdic_url(), when, download(fdic_url()))]
    (fd / PROVENANCE).write_text(json.dumps(out[FDIC_DIR], indent=1), encoding="utf-8", newline="\n")
    hd = root / H8_DIR
    hd.mkdir(parents=True, exist_ok=True)
    rows = []
    for rel in releases if releases is not None else h8_release_dates():
        if download is _download:
            time.sleep(PAUSE_SECONDS)
        thursday = (dt.datetime.strptime(rel, "%Y%m%d") - dt.timedelta(days=1)).strftime("%Y%m%d")
        for cand in (rel, thursday):
            try:
                body = download(h8_url(cand))
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 404) and cand == rel:
                    continue    # no page on that Friday: the Board moved the release to the Thursday
                raise
            rows.append(_write(hd, h8_name(cand), h8_url(cand), when, body))
            break
    out[H8_DIR] = rows
    (hd / PROVENANCE).write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
    sd = root / SVB_DIR
    sd.mkdir(parents=True, exist_ok=True)
    if download is _download:
        time.sleep(PAUSE_SECONDS)
    out[SVB_DIR] = [_write(sd, SVB_NAME, SVB_URL, when, download(SVB_URL))]
    (sd / PROVENANCE).write_text(json.dumps(out[SVB_DIR], indent=1), encoding="utf-8", newline="\n")
    return out


def load_provenance(data_root: str | Path) -> dict[str, list[dict[str, Any]]]:
    """The sidecars with every file's hash and size recomputed: a file that differs from its record is refused."""
    root = Path(data_root) / "raw"
    out: dict[str, list[dict[str, Any]]] = {}
    for folder, sidecar in ((FDIC_DIR, PROVENANCE), (H8_DIR, PROVENANCE), (SVB_DIR, PROVENANCE), (TREASURY_DIR, TREASURY_PROVENANCE)):
        side = root / folder / sidecar
        if not side.exists():
            raise FileNotFoundError(f"{side}: not fetched; run `python data-pipeline/pipeline/cases/c16/fetch.py --data-root {data_root}`")
        rows = json.loads(side.read_text(encoding="utf-8"))
        for r in rows:
            f = root / folder / r["name"]
            if not f.exists() or sha256_of(f) != r["sha256"] or f.stat().st_size != r["bytes"]:
                raise ValueError(f"{f}: differs from its provenance record (the file or its sha256 {sha256_of(f) if f.exists() else 'absent'})")
        out[folder] = rows
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.cases.c16.fetch")
    ap.add_argument("--data-root", required=True)
    args = ap.parse_args()
    for folder, rows in fetch(args.data_root).items():
        for r in rows:
            print(f"{folder}/{r['name']}: {r['bytes']:,} bytes sha256 {r['sha256'][:12]}")


if __name__ == "__main__":
    main()
