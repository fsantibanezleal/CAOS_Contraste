"""The raw inputs of C18 that no other case fetches, and the provenance of all of them.

``fetch`` writes into the device data root (``<root>/raw/<source>/``, never the repository): the EBA/ESRB 2025 macro-financial
workbook of the EBA page, the NGFS Phase 5 Baseline and Delayed transition runs of the NiGEM model through the IIASA Manager API (an
anonymous token, read as the API issues it), and the BCCh EUR to CLP series (through ``pipeline.io.bcch``, with the account in the
process environment only). ``record_existing`` writes the sidecar of the Federal Reserve files the other cases fetched (the files
are read, never rewritten). Every folder holds a ``provenance.json`` (URL, size, SHA-256, retrieval date) which the bake copies
into ``data/derived/C18/raw-sources.txt`` (rows of ``data/sources/manifest.json``) and verifies on every read.

    python -m pipeline.cases.c18.fetch --data-root <root> [--fx]     run from data-pipeline/; --fx needs BCCH_USER and BCCH_PASSWORD
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...io import bcch
from ...io import sba as fed_sba
from ..c10 import fed as chargeoff
from . import params as P

USER_AGENT = "Mozilla/5.0 (Contraste data fetch; contact: Contraste maintainers)"
PROVENANCE = "provenance.json"

EBA_DIR = "eba-esrb-stress-2025"
EBA_URL = ("https://www.eba.europa.eu/sites/default/files/2025-03/d0668400-aed7-40d7-b668-1f77eb24b934/"
           "2025%20EU-wide%20stress%20test%20-%20Macro%20financial%20scenario%20%28updated%2026%20February%202025%29-incl%20disclaimer"
           "%20for%20EBA%20%285%29.xlsx")
EBA_PAGE = "https://www.eba.europa.eu/eu-wide-stress-test-2025"
EBA_NAME = "macro-financial-scenario-updated-2025-02-26.xlsx"
EBA_VINTAGE = "2025-02-26"

NGFS_DIR = "ngfs-phase-v"
IIASA_TOKEN_URL = "https://api.manager.ece.iiasa.ac.at/legacy/anonym/"
IIASA_CONFIG_URL = "https://api.manager.ece.iiasa.ac.at/legacy/applications/IXSE_NGFS_PHASE_5/config"
NGFS_BASE = "https://db1.ene.iiasa.ac.at/ngfs-phase-5-api/rest/v2.1"
NGFS_UI = "https://data.ene.iiasa.ac.at/ngfs"
NGFS_MODEL = "NiGEM NGFS v1.24.2[GCAM 6.0 NGFS]"
#: the NiGEM runs (addendum F8): 137 the Baseline (levels), 140 the Delayed transition (deviations from the baseline)
NGFS_RUNS = {"baseline": 137, "delayed-transition": 140}
NGFS_VINTAGE = "2024-11-01"        # NGFS Phase V, November 2024 (technical documentation V5.0)
NGFS_REGION = "NiGEM NGFS v1.24.2|United States"

FX_DIR = "bcch-f072-eur"
FED_HIST_DIR = fed_sba.FED_FOLDER
CHARGEOFF_DIR = "fed-chargeoff"
CHARGEOFF_NAME = "chgallsa.htm"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _get(url: str, headers: dict[str, str] | None = None, timeout: float = 300.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https, public sources)
        return resp.read()


def iiasa_token() -> str:
    """The anonymous (guest) token the IIASA Manager API issues without credentials."""
    return _get(IIASA_TOKEN_URL, timeout=60.0).decode("ascii").strip().strip('"')


def ngfs_url(run_id: int) -> str:
    return f"{NGFS_BASE}/runs/{run_id}/ts"


def ngfs_name(run_id: int) -> str:
    return f"nigem-run-{run_id}.json"


def _row(raw: Path, name: str, url: str, retrieved: str) -> dict[str, Any]:
    path = raw / name
    return {"name": name, "url": url, "bytes": path.stat().st_size, "sha256": sha256_of(path), "retrieved": retrieved}


def _write_sidecar(folder: Path, rows: list[dict[str, Any]]) -> None:
    (folder / PROVENANCE).write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")


def fetch(data_root: str | Path, today: str | None = None, download: Callable[..., bytes] = _get) -> dict[str, list[dict[str, Any]]]:
    """Download the EBA workbook and the two NGFS runs into ``<root>/raw`` and write their provenance sidecars."""
    root = Path(data_root) / "raw"
    when = today or dt.date.today().isoformat()
    out: dict[str, list[dict[str, Any]]] = {}
    d = root / EBA_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / EBA_NAME).write_bytes(download(EBA_URL))
    out[EBA_DIR] = [_row(d, EBA_NAME, EBA_URL, when)]
    _write_sidecar(d, out[EBA_DIR])
    d = root / NGFS_DIR
    d.mkdir(parents=True, exist_ok=True)
    token = iiasa_token() if download is _get else "test"
    rows = []
    for rid in NGFS_RUNS.values():
        (d / ngfs_name(rid)).write_bytes(download(ngfs_url(rid), {"Authorization": f"Bearer {token}"}))
        rows.append(_row(d, ngfs_name(rid), ngfs_url(rid), when))
    out[NGFS_DIR] = rows
    _write_sidecar(d, rows)
    return out


def fetch_fx(data_root: str | Path, user: str, password: str, today: str | None = None, transport: Callable[..., bytes] | None = None
             ) -> list[dict[str, Any]]:
    """The BCCh EUR to CLP series of August 2026, written beside (not into) the C15 folder, so C15's provenance is untouched."""
    when = today or dt.date.today().isoformat()
    folder = Path(data_root) / "raw" / FX_DIR
    folder.mkdir(parents=True, exist_ok=True)
    send = transport or bcch._http
    body = bcch.guarded(send, "GetSeries", user, password, timeseries=P.FX_SERIES, firstdate=P.FX_FIRST, lastdate=P.FX_LAST)
    name = bcch.file_name(P.FX_SERIES, P.FX_FIRST, P.FX_LAST)
    (folder / name).write_bytes(body)
    rows = [_row(folder, name, bcch.request_url("GetSeries", timeseries=P.FX_SERIES, firstdate=P.FX_FIRST, lastdate=P.FX_LAST), when)]
    _write_sidecar(folder, rows)
    return rows


def record_existing(data_root: str | Path) -> dict[str, list[dict[str, Any]]]:
    """Write the sidecar of the Federal Reserve files the other cases fetched (the retrieval date is the file's last write)."""
    root = Path(data_root) / "raw"
    out: dict[str, list[dict[str, Any]]] = {}
    folder = root / FED_HIST_DIR
    rows = []
    for name in fed_sba.FED_FILES:
        path = folder / name
        when = dt.date.fromtimestamp(path.stat().st_mtime).isoformat()
        rows.append(_row(folder, name, fed_sba.FED_URLS[name], when))
    _write_sidecar(folder, rows)
    out[FED_HIST_DIR] = rows
    folder = root / CHARGEOFF_DIR
    path = folder / CHARGEOFF_NAME
    rows = [_row(folder, CHARGEOFF_NAME, chargeoff.URL, dt.date.fromtimestamp(path.stat().st_mtime).isoformat())]
    _write_sidecar(folder, rows)
    out[CHARGEOFF_DIR] = rows
    return out


def load_provenance(data_root: str | Path, folders: tuple[str, ...] | None = None) -> dict[str, list[dict[str, Any]]]:
    """The sidecars, with every file's size and hash recomputed: a file that differs from its record is refused."""
    root = Path(data_root) / "raw"
    want = folders or (FED_HIST_DIR, CHARGEOFF_DIR, EBA_DIR, NGFS_DIR, FX_DIR)
    out: dict[str, list[dict[str, Any]]] = {}
    for folder in want:
        side = root / folder / PROVENANCE
        if not side.exists():
            raise FileNotFoundError(f"{side}: not fetched; run `python -m pipeline.cases.c18.fetch --data-root {data_root}` from data-pipeline/")
        rows = json.loads(side.read_text(encoding="utf-8"))
        for r in rows:
            path = root / folder / r["name"]
            if not path.exists():
                raise FileNotFoundError(f"{path}: not in the data root; fetch it from {r['url']}")
            if path.stat().st_size != r["bytes"] or sha256_of(path) != r["sha256"]:
                raise ValueError(f"{path}: differs from its provenance record (sha256 {sha256_of(path)})")
        out[folder] = rows
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.cases.c18.fetch")
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--fx", action="store_true", help="fetch the BCCh EUR to CLP series (BCCH_USER and BCCH_PASSWORD in the environment)")
    ap.add_argument("--skip-ngfs-eba", action="store_true")
    args = ap.parse_args(argv)
    rows: dict[str, list[dict[str, Any]]] = {}
    if not args.skip_ngfs_eba:
        rows.update(fetch(args.data_root))
    rows.update(record_existing(args.data_root))
    if args.fx:
        user, password = bcch.credentials_from_env()
        rows[FX_DIR] = fetch_fx(args.data_root, user, password)
    for folder, rs in rows.items():
        for r in rs:
            print(f"{folder}/{r['name']}: {r['bytes']:,} bytes sha256 {r['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
