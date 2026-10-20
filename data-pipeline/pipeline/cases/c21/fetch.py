"""The raw inputs of C21 and their fetch: HMDA loan-level rows for Delaware, one file per activity year 2018 to 2024.

The source is the CFPB / FFIEC HMDA Data Browser CSV endpoint (registered as ``hmda``, class mirror-allowed, the data licence sentence
UNVERIFIED; decisions Q2 and C1 of the U14 sizing). A request names the state, the year and the eight ``action_taken`` codes; the
endpoint answers 301 to a cached CSV on ``files.ffiec.cfpb.gov``, which the HTTP client follows. The request is sent with the HTTP
client's default user agent: a browser user agent gets 403 (the cause of the block recorded in R7 of the sizing).

The bake reads files from the device data root and never the network; ``fetch`` writes them there, with a sidecar ``provenance.json``
(URL, size, SHA-256, retrieval date), which the bake copies into ``data/derived/C21/raw-sources.txt`` (rows of
``data/sources/manifest.json``). A year that does not answer is listed with its URL and reason; the pairs that need it are blocked
(``pairs_status``) and nothing is written for them.

    python data-pipeline/pipeline/cases/c21/fetch.py --data-root <root>      writes them
    python data-pipeline/run.py C21 --data-root <root>                       reads  <root>/raw/hmda/
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

SOURCE_ID = "hmda"
HMDA_DIR = "hmda"
PROVENANCE = "provenance.json"
STATE = "DE"
YEARS = (2018, 2019, 2020, 2021, 2022, 2023, 2024)
#: the six year pairs: fitted on year t and confirmed on t + 1 (SDD l.393)
PAIRS: tuple[tuple[str, int, int], ...] = tuple((f"{y}-{str(y + 1)[2:]}", y, y + 1) for y in YEARS[:-1])
ACTIONS = "1,2,3,4,5,6,7,8"
BASE = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"
TIMEOUT = 600.0
ATTEMPTS = 3
PAUSE = 5.0


def url(year: int) -> str:
    """The Data Browser request of one year: Delaware, every action taken (the convention leaves codes 4 to 8 out in the reader)."""
    return f"{BASE}?states={STATE}&years={year}&actions_taken={ACTIONS}"


def file_name(year: int) -> str:
    return f"hmda-{STATE.lower()}-{year}.csv"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _download(target: str, timeout: float = TIMEOUT) -> bytes:
    """The request with the client's default user agent (no header is added; a browser user agent is refused with 403)."""
    req = urllib.request.Request(target)
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https, public source)
        return resp.read()


def fetch(data_root: str | Path, today: str | None = None, years: Iterable[int] = YEARS,
          download: Callable[[str], bytes] | None = None, attempts: int = ATTEMPTS, pause: float = PAUSE) -> dict[str, Any]:
    """Download the yearly files into ``<root>/raw/hmda`` and write the provenance sidecar.

    Returns ``{"files": [record, ...], "unavailable": [{"year", "url", "reason"}, ...]}``. A year whose download fails after
    ``attempts`` tries is listed in ``unavailable`` and has no file and no record; the other years are kept.
    """
    get = download or _download
    d = Path(data_root) / "raw" / HMDA_DIR
    d.mkdir(parents=True, exist_ok=True)
    when = today or dt.date.today().isoformat()
    files: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    for y in years:
        body, reason = None, ""
        for k in range(attempts):
            try:
                body = get(url(y))
                break
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:  # HTTPError is a URLError
                reason = f"{type(exc).__name__}: {exc}"
                if k + 1 < attempts:
                    time.sleep(pause)
        if body is None:
            unavailable.append({"year": y, "url": url(y), "reason": reason})
            continue
        (d / file_name(y)).write_bytes(body)
        files.append({"name": file_name(y), "url": url(y), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "retrieved": when})
    (d / PROVENANCE).write_text(json.dumps(files, indent=1), encoding="utf-8", newline="\n")
    return {"files": files, "unavailable": unavailable}


def load_provenance(data_root: str | Path) -> list[dict[str, Any]]:
    """The sidecar, with every file's hash recomputed: a file that differs from its record is refused."""
    d = Path(data_root) / "raw" / HMDA_DIR
    side = d / PROVENANCE
    if not side.exists():
        raise FileNotFoundError(f"{side}: not fetched; run `python data-pipeline/pipeline/cases/c21/fetch.py --data-root {data_root}`")
    rows = json.loads(side.read_text(encoding="utf-8"))
    for r in rows:
        path = d / r["name"]
        if not path.exists():
            raise FileNotFoundError(f"{path}: recorded in {side} and absent")
        got = sha256_of(path)
        if got != r["sha256"] or path.stat().st_size != r["bytes"]:
            raise ValueError(f"{path}: differs from its provenance record (sha256 {got})")
    return rows


def year_of(record: dict[str, Any]) -> int:
    return int(record["name"].removeprefix(f"hmda-{STATE.lower()}-").removesuffix(".csv"))


def pairs_status(available_years: Iterable[int]) -> tuple[list[tuple[str, int, int]], list[dict[str, Any]]]:
    """The pairs whose two years are present, and the blocked ones with the missing years and their URLs."""
    have = set(available_years)
    ok: list[tuple[str, int, int]] = []
    blocked: list[dict[str, Any]] = []
    for pid, a, b in PAIRS:
        missing = [y for y in (a, b) if y not in have]
        if missing:
            blocked.append({"pair_id": pid, "missing_years": missing, "urls": [url(y) for y in missing]})
        else:
            ok.append((pid, a, b))
    return ok, blocked


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.cases.c21.fetch")
    ap.add_argument("--data-root", required=True)
    args = ap.parse_args()
    out = fetch(args.data_root)
    for r in out["files"]:
        print(f"{HMDA_DIR}/{r['name']}: {r['bytes']:,} bytes sha256 {r['sha256'][:12]}")
    for u in out["unavailable"]:
        print(f"{HMDA_DIR}: year {u['year']} did not answer ({u['reason']}); {u['url']}")
    if out["unavailable"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
