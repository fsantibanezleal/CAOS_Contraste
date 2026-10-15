"""The raw inputs of C14 and their fetch: the FDIC BankFind financials of one bank and the US Treasury par yield curves.

Both sources are public and registered (``fdic-bankfind``, ``treasury-par-curve``, class mirror-allowed). The bake reads files
from the device data root and never the network; ``fetch`` writes them there, with a sidecar ``provenance.json`` per source
folder (URL, size, SHA-256, retrieval date), which the bake copies into ``data/derived/C14/raw-sources.txt`` (rows of ``data/sources/manifest.json``).

    python data-pipeline/pipeline/cases/c14/fetch.py --data-root <root>      writes them
    python data-pipeline/run.py C14 --data-root <root>                       reads  <root>/raw/fdic-financials/ and <root>/raw/treasury-par/
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from ...io import treasury

CERT = 24735
BANK = "Silicon Valley Bank"
FDIC_DIR = "fdic-financials"
TREASURY_DIR = treasury.TREASURY_DIR
PROVENANCE = "provenance.json"
FIRST_REPDTE = "20121231"
LAST_REPDTE = "20221231"
FIRST_TREASURY_YEAR = 2012
LAST_TREASURY_YEAR = 2022
USER_AGENT = "Mozilla/5.0 (Contraste data fetch; contact: Contraste maintainers)"

#: every field the C14 bake reads from the FDIC financials (names as in the BankFind Suite RISVIEW dictionary)
FDIC_FIELDS = (
    "CERT", "REPDTE", "NAME", "ASSET", "LIAB", "EQ", "RBCT1J",
    "DEP", "DEPDOM", "DEPFOR", "DEPNIDOM", "DEPIDOM", "DEPNIFOR", "DEPIFOR", "DEPINS", "DEPUNA", "DEPSMAMT", "DEPSMB", "DEPLGAMT", "DEPLGB",
    "NTRTIME", "CD3LES", "CD3T12", "CD1T3", "CDOV3", "CD3LESS", "CD3T12S", "CD1T3S", "CDOV3S",
    "CHBAL", "FREPO", "FREPP", "SC", "SCRDEBT", "SCAF", "SCAA", "SCHA", "SCHF",
    "SCNM3LES", "SCNM3T12", "SCNM1T3", "SCNM3T5", "SCNM5T15", "SCNMOV15",
    "SCPT3LES", "SCPT3T12", "SCPT1T3", "SCPT3T5", "SCPT5T15", "SCPTOV15", "SCO3YLES", "SCOOV3Y",
    "LNLSGR", "LNLSNET", "LNATRES",
    "LNRS3LES", "LNRS3T12", "LNRS1T3", "LNRS3T5", "LNRS5T15", "LNRSOV15",
    "LNOT3LES", "LNOT3T12", "LNOT1T3", "LNOT3T5", "LNOT5T15", "LNOTOV15",
    "OTHBFHLB", "OTHBFH1L", "OTBFH1T3", "OTBFH3T5", "OTBFHOV5", "OTHBRF", "OTBOT1L", "OTBOT1T3", "OTBOT3T5", "OTBOTOV5", "SUBND",
    "INTINC", "EINTEXP", "NIM", "EDEP", "ISC", "ILNDOM", "ICHBAL", "IFREPO", "EFREPP",
)


def fdic_url(cert: int = CERT) -> str:
    query = urllib.parse.urlencode({
        "filters": f"CERT:{cert} AND REPDTE:[{FIRST_REPDTE} TO {LAST_REPDTE}]", "fields": ",".join(FDIC_FIELDS),
        "sort_by": "REPDTE", "sort_order": "ASC", "limit": "100"}, quote_via=urllib.parse.quote)
    return f"https://api.fdic.gov/banks/financials?{query}"


def treasury_url(year: int) -> str:
    return treasury.url(year)


def fdic_name(cert: int = CERT) -> str:
    return f"financials-cert{cert}-{FIRST_REPDTE}-{LAST_REPDTE}.json"


def treasury_name(year: int) -> str:
    return treasury.file_name(year)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _download(url: str, timeout: float = 90.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https, public sources)
        return resp.read()


def _fetch_one(raw: Path, name: str, url: str, retrieved: str) -> dict[str, Any]:
    body = _download(url)
    (raw / name).write_bytes(body)
    return {"name": name, "url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "retrieved": retrieved}


def fetch(data_root: str | Path, today: str | None = None) -> dict[str, list[dict[str, Any]]]:
    """Download the FDIC financials and the Treasury yearly files into ``<root>/raw`` and write the provenance sidecars."""
    root = Path(data_root) / "raw"
    when = today or dt.date.today().isoformat()
    out: dict[str, list[dict[str, Any]]] = {}
    for folder, files in (
        (FDIC_DIR, [(fdic_name(), fdic_url())]),
        (TREASURY_DIR, [(treasury_name(y), treasury_url(y)) for y in range(FIRST_TREASURY_YEAR, LAST_TREASURY_YEAR + 1)]),
    ):
        d = root / folder
        d.mkdir(parents=True, exist_ok=True)
        rows = [_fetch_one(d, name, url, when) for name, url in files]
        (d / PROVENANCE).write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
        out[folder] = rows
    return out


def load_provenance(data_root: str | Path) -> dict[str, list[dict[str, Any]]]:
    """The sidecars, with every file's hash recomputed: a file that differs from its record is refused."""
    root = Path(data_root) / "raw"
    out: dict[str, list[dict[str, Any]]] = {}
    for folder in (FDIC_DIR, TREASURY_DIR):
        side = root / folder / PROVENANCE
        if not side.exists():
            raise FileNotFoundError(f"{side}: not fetched; run `python data-pipeline/pipeline/cases/c14/fetch.py --data-root {data_root}`")
        rows = json.loads(side.read_text(encoding="utf-8"))
        for r in rows:
            got = sha256_of(root / folder / r["name"])
            if got != r["sha256"] or (root / folder / r["name"]).stat().st_size != r["bytes"]:
                raise ValueError(f"{root / folder / r['name']}: differs from its provenance record (sha256 {got})")
        out[folder] = rows
    return out


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.cases.c14.fetch")
    ap.add_argument("--data-root", required=True)
    args = ap.parse_args()
    for folder, rows in fetch(args.data_root).items():
        for r in rows:
            print(f"{folder}/{r['name']}: {r['bytes']:,} bytes sha256 {r['sha256'][:12]}")


if __name__ == "__main__":
    main()
