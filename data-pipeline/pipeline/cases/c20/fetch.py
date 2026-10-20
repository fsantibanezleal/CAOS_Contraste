"""The raw inputs of C20 that no shared registry fetches: the SGCD files at the pinned commit and the Fed 2025 corporate portfolios.

SGCD (registry id ``santanderai-sgcd``) comes from the SantanderAI ``sota-stressed-datasets`` repository at commit ``8403fa9`` (data CC BY
4.0), four files: the records, the generation metadata, the codebook and the dataset card. The Fed portfolios (registry id
``fed-stress-tests``) are the three 200-loan hypothetical corporate portfolios of the 2025 stress test methodology data, in the public
domain by the Board's statement. The UCI German, Taiwan and Polish files are fetched by ``data-pipeline/fetch.py`` and pinned in
``data/sources/manifest.json``; this module does not touch them.

The bake reads files from the device data root and never the network; ``fetch`` writes them there with a sidecar (``provenance.json`` for
SGCD, ``provenance-c20.json`` for the Fed files, which share their folder with the files of C19) holding URL, size, SHA-256 and retrieval
date. A source that does not answer is listed with its URL; the variants that need it are named and nothing is written for them
(``missing_for``).

    python data-pipeline/pipeline/cases/c20/fetch.py --data-root <root>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ...io.fetch import USER_AGENT
from .conv import SGCD_COMMIT

SGCD_ID = "santanderai-sgcd"
FED_ID = "fed-stress-tests"
SGCD_BASE = f"https://raw.githubusercontent.com/SantanderAI/sota-stressed-datasets/{SGCD_COMMIT}/datasets/stressed_german_credit_dataset"
SGCD_FILES = (("SGCDataset.jsonl", "data/SGCDataset.jsonl"), ("SGCDataset_metadata.json", "data/SGCDataset_metadata.json"),
              ("codebook.md", "data/codebook.md"), ("README.md", "README.md"))
FED_BASE = "https://www.federalreserve.gov/supervisionreg/files"
FED_FILES = (("typical", "corporate-typical-risk-2025.csv"), ("higher-risk", "corporate-high-risk-2025.csv"),
             ("lower-risk", "corporate-low-risk-2025.csv"))
PROVENANCE = {SGCD_ID: "provenance.json", FED_ID: "provenance-c20.json"}
TIMEOUT = 120.0
ATTEMPTS = 3
PAUSE = 3.0

#: the variants each source feeds, named when the source does not answer
NEEDED_BY = {SGCD_ID: ("sgcd-seen", "sgcd-held-out"), FED_ID: ("fed-shift",)}


def sgcd_url(name: str) -> str:
    return f"{SGCD_BASE}/{dict(SGCD_FILES)[name]}"


def fed_url(name: str) -> str:
    return f"{FED_BASE}/{name}"


def _targets() -> dict[str, list[tuple[str, str]]]:
    return {SGCD_ID: [(n, sgcd_url(n)) for n, _ in SGCD_FILES], FED_ID: [(f, fed_url(f)) for _, f in FED_FILES]}


def _download(url: str, timeout: float = TIMEOUT) -> bytes:
    """GitHub answers the client's default user agent; the Board's host refuses it (403) and answers the shared fetch agent."""
    headers = {"User-Agent": USER_AGENT} if url.startswith(FED_BASE) else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as resp:  # noqa: S310 (https, public sources)
        return resp.read()


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(data_root: str | Path, today: str | None = None, download: Callable[[str], bytes] | None = None, attempts: int = ATTEMPTS,
          pause: float = PAUSE, sources: tuple[str, ...] = (SGCD_ID, FED_ID)) -> dict[str, Any]:
    """Download the files into ``<root>/raw/<source>`` and write each source's sidecar.

    Returns ``{"files": {source: [record, ...]}, "unavailable": [{"source", "name", "url", "reason"}, ...]}``. A source with a file that
    fails after ``attempts`` tries gets no sidecar; the other source is kept.
    """
    get = download or _download
    when = today or dt.date.today().isoformat()
    out: dict[str, list[dict[str, Any]]] = {}
    unavailable: list[dict[str, Any]] = []
    for sid in sources:
        d = Path(data_root) / "raw" / sid
        d.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, Any]] = []
        failed = False
        for name, url in _targets()[sid]:
            body, reason = None, ""
            for k in range(attempts):
                try:
                    body = get(url)
                    break
                except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                    reason = f"{type(exc).__name__}: {exc}"
                    if k + 1 < attempts:
                        time.sleep(pause)
            if body is None:
                unavailable.append({"source": sid, "name": name, "url": url, "reason": reason})
                failed = True
                continue
            (d / name).write_bytes(body)
            records.append({"name": name, "url": url, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "retrieved": when})
        if not failed:
            (d / PROVENANCE[sid]).write_text(json.dumps(records, indent=1), encoding="utf-8", newline="\n")
        out[sid] = records
    return {"files": out, "unavailable": unavailable}


def load_provenance(data_root: str | Path, source: str) -> list[dict[str, Any]]:
    """The sidecar of a source with every file's hash recomputed: a file that differs from its record is refused."""
    d = Path(data_root) / "raw" / source
    side = d / PROVENANCE[source]
    if not side.exists():
        raise FileNotFoundError(f"{side}: not fetched; run `python data-pipeline/pipeline/cases/c20/fetch.py --data-root {data_root}` "
                                f"(the variants {', '.join(NEEDED_BY[source])} need {source})")
    rows = json.loads(side.read_text(encoding="utf-8"))
    for r in rows:
        path = d / r["name"]
        if not path.exists():
            raise FileNotFoundError(f"{path}: recorded in {side} and absent")
        got = sha256_of(path)
        if got != r["sha256"] or path.stat().st_size != r["bytes"]:
            raise ValueError(f"{path}: differs from its provenance record (sha256 {got})")
    return rows


def missing_for(data_root: str | Path) -> list[dict[str, Any]]:
    """The sources not in the data root, each with the variants that wait for it and the URLs to fetch."""
    out = []
    for sid, targets in _targets().items():
        side = Path(data_root) / "raw" / sid / PROVENANCE[sid]
        if not side.exists():
            out.append({"source": sid, "variants": list(NEEDED_BY[sid]), "urls": [u for _, u in targets]})
    return out


def path_of(data_root: str | Path, source: str, name: str) -> Path:
    return Path(data_root) / "raw" / source / name


def main() -> None:
    ap = argparse.ArgumentParser(prog="pipeline.cases.c20.fetch")
    ap.add_argument("--data-root", required=True)
    args = ap.parse_args()
    res = fetch(args.data_root)
    for sid, recs in res["files"].items():
        for r in recs:
            print(f"{sid}/{r['name']}: {r['bytes']:,} bytes sha256 {r['sha256'][:12]}")
    for u in res["unavailable"]:
        print(f"{u['source']}: {u['name']} did not answer ({u['reason']}); {u['url']}; variants waiting: {', '.join(NEEDED_BY[u['source']])}")
    if res["unavailable"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
