"""The Banco Central de Chile BDE reader and its fetch, shared by the cases that read the Central Bank's series (C15 now).

The BDE answers ``SieteRestWS.ashx`` with JSON in Latin-1 (ISO-8859-1), never UTF-8. A ``GetSeries`` answer carries the series title in
Spanish and English and its observations (``indexDateString`` as day-month-year, ``value`` as text, ``statusCode``); a day the BCCh has
no value for is ``NaN`` with the status ``ND``. A ``SearchSeries`` answer lists the series of a frequency with their first and last
observation. ``Codigo`` is 0 for success (``-5``: the account is refused).

Terms (https://si3.bcentral.cl/estadisticas/Principal1/Web_Services/terminos_condiciones.html): the information may be consulted,
reproduced, published or adapted naming the Banco Central as its owner; an adaptation is labelled as its author's. The account allows at
most 5 series per second. The credentials are read from the environment variables ``BCCH_USER`` and ``BCCH_PASSWORD`` and nowhere
else; they go into the request and never into a file, a log, a message or a provenance record (the recorded URL has neither).

A series is read as **missing** where the BCCh has no value, listed and never filled (:meth:`Series.missing`). The dating rule is
:meth:`Series.values` with ``up_to`` (nothing after a date) and :func:`last_common_date` (the last business day with a value in every
series of a set).

    BCCH_USER=... BCCH_PASSWORD=... python -m pipeline.io.bcch fetch --data-root <root> --first 2026-09-01 --last 2026-09-30

writes ``<root>/raw/bcch-f022/`` (one file per series, the search answer, ``provenance.json``). Run it from ``data-pipeline/``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .treasury import need, sha256_of

BCCH_DIR = "bcch-f022"
PROVENANCE = "provenance.json"
SEARCH_FILE = "search-daily.json"
ENDPOINT = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
LANDING = "https://si3.bcentral.cl/Siete/es/Siete/API"
ENV_USER = "BCCH_USER"
ENV_PASSWORD = "BCCH_PASSWORD"
#: the BCCh allows 5 series per second per account: a pause of a quarter of a second keeps every window of one second at four requests
MIN_INTERVAL = 0.25
TIMEOUT = 90.0
USER_AGENT = "Mozilla/5.0 (Contraste data fetch; contact: Contraste maintainers)"
#: the secondary-market yields of the F022 table: Central Bank and Treasury bonds in pesos (BCLP) and in UF (BUF), by tenor in years
YIELD_PATTERN = re.compile(r"^F022\.(?P<family>BUF|BCLP)\.TIS\.AN(?P<years>\d{2})\.(?P<unit>UF|NO)\.Z\.D$")
#: the curve a family belongs to: the pesos curve (CLP) and the UF-indexed one (UR, the currency of RAN 21-13 Annex 1)
FAMILY_CURVE = {"BCLP": "CLP", "BUF": "UR"}
_TENOR = re.compile(r"\.AN(\d{2})\.")


class BcchError(RuntimeError):
    """The BDE refused a request or the answer is not a BDE answer. ``codigo`` is the ``Codigo`` of the answer, when there is one.
    The message never carries the request URL (which holds the credentials)."""

    def __init__(self, message: str, codigo: int | None = None) -> None:
        super().__init__(message)
        self.codigo = codigo


# ---------------------------------------------------------------------------------------------------------------- URLs

def request_url(function: str, *, user: str | None = None, password: str | None = None, **params: str) -> str:
    """The URL of one BDE request. With ``user`` and ``password`` it is the URL that is sent; without them it is the URL that is recorded."""
    query: dict[str, str] = {}
    if user is not None or password is not None:
        query = {"user": user or "", "pass": password or ""}
    query["function"] = function
    query.update(params)
    return f"{ENDPOINT}?{urllib.parse.urlencode(query)}"


def credentials_from_env(environ: dict[str, str] | None = None) -> tuple[str, str]:
    """``(user, password)`` from ``BCCH_USER`` and ``BCCH_PASSWORD``; a missing one is an error that names the variables, never a value."""
    env = os.environ if environ is None else environ
    user, password = env.get(ENV_USER), env.get(ENV_PASSWORD)
    if not user or not password:
        raise BcchError(f"the BCCh credentials are read from the environment variables {ENV_USER} and {ENV_PASSWORD} only; one is not set "
                        f"(register at {LANDING})")
    return user, password


def file_name(series_id: str, first: str, last: str) -> str:
    return f"{series_id}-{first}-{last}.json"


# ---------------------------------------------------------------------------------------------------------------- answers

def parse_answer(body: bytes) -> dict[str, Any]:
    """The JSON of an answer decoded as Latin-1; refuses a body that is not a BDE answer and an answer whose ``Codigo`` is not 0."""
    try:
        doc = json.loads(body.decode("latin-1"))
    except ValueError as exc:
        raise BcchError(f"not a BDE answer (not JSON: {type(exc).__name__})") from None
    if not isinstance(doc, dict) or "Codigo" not in doc:
        raise BcchError("not a BDE answer (no Codigo)")
    if doc["Codigo"] != 0:
        raise BcchError(f"the BDE refused the request: Codigo {doc['Codigo']}, {doc.get('Descripcion')!r}", int(doc["Codigo"]))
    return doc


def _iso(day_month_year: str) -> str:
    return dt.datetime.strptime(day_month_year, "%d-%m-%Y").date().isoformat()


@dataclass(frozen=True)
class Observation:
    date: str                    # ISO
    value: float | None          # as published (percent for a yield); None where the BCCh has no value
    status: str


@dataclass(frozen=True)
class Series:
    series_id: str
    title_es: str
    title_en: str
    observations: tuple[Observation, ...]

    def values(self, up_to: str | None = None) -> dict[str, float]:
        """``{ISO date: value}`` of the days with a value, in date order; with ``up_to`` nothing dated after it (the dating rule)."""
        return {o.date: o.value for o in sorted(self.observations, key=lambda o: o.date)
                if o.value is not None and (up_to is None or o.date <= up_to)}

    def missing(self) -> list[str]:
        """The days the BCCh lists without a value (never filled), in date order."""
        return sorted(o.date for o in self.observations if o.value is None)


def parse_series(body: bytes) -> Series:
    """A ``GetSeries`` answer. An observation is missing when its status is not ``OK`` or its value is not a number."""
    doc = parse_answer(body)
    s = doc.get("Series") or {}
    obs: list[Observation] = []
    for o in s.get("Obs") or []:
        try:
            value: float | None = float(o["value"])
        except (TypeError, ValueError):
            value = None
        status = str(o.get("statusCode", ""))
        if status != "OK" or value is None or value != value:
            value = None
        obs.append(Observation(_iso(o["indexDateString"]), value, status))
    return Series(str(s.get("seriesId") or ""), str(s.get("descripEsp") or ""), str(s.get("descripIng") or ""), tuple(obs))


@dataclass(frozen=True)
class SeriesInfo:
    series_id: str
    frequency: str
    title_es: str
    title_en: str
    first_observation: str | None
    last_observation: str | None


def _opt_iso(text: str | None) -> str | None:
    """An ISO date from a listing cell, or None where the cell is empty or says ``ND`` (the BCCh lists some series without a date)."""
    try:
        return _iso(text) if text else None
    except ValueError:
        return None


def parse_search(body: bytes) -> list[SeriesInfo]:
    """A ``SearchSeries`` answer: the series of the frequency with their first and last observation (ISO), in the order served."""
    doc = parse_answer(body)
    return [SeriesInfo(i["seriesId"], str(i.get("frequencyCode") or ""), str(i.get("spanishTitle") or ""), str(i.get("englishTitle") or ""),
                       _opt_iso(i.get("firstObservation")), _opt_iso(i.get("lastObservation"))) for i in doc.get("SeriesInfos") or []]


def tenor_years(series_id: str) -> float | None:
    """The tenor of a series of the ``AN<years>`` form (``F022.BUF.TIS.AN10.UF.Z.D`` is 10 years); None for any other series."""
    m = _TENOR.search(series_id)
    return float(m.group(1)) if m else None


@dataclass(frozen=True)
class YieldSeries:
    series_id: str
    curve: str                   # CLP or UR
    tenor_years: float
    info: SeriesInfo


def yield_series(infos: Sequence[SeriesInfo]) -> list[YieldSeries]:
    """The daily secondary-market yield series of the F022 table (pesos and UF bonds) among a search answer, with their curve and tenor."""
    out = []
    for i in infos:
        m = YIELD_PATTERN.match(i.series_id)
        if m and i.frequency == "DAILY":
            out.append(YieldSeries(i.series_id, FAMILY_CURVE[m["family"]], float(m["years"]), i))
    return sorted(out, key=lambda y: (y.curve, y.tenor_years))


def last_common_date(series: Sequence[Series], first: str, last: str) -> str | None:
    """The last business day (Monday to Friday) in ``[first, last]`` on which every series has a value, or None when there is none."""
    if not series:
        return None
    days: set[str] | None = None
    for s in series:
        have = {d for d in s.values() if first <= d <= last}
        days = have if days is None else days & have
    weekdays = [d for d in sorted(days or ()) if dt.date.fromisoformat(d).weekday() < 5]
    return weekdays[-1] if weekdays else None


# ---------------------------------------------------------------------------------------------------------------- fetch

Transport = Callable[[str], bytes]


def _http(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 (https, the account's own API)
        return resp.read()


def fetch(data_root: str | Path, series_ids: Sequence[str], first: str, last: str, *, user: str, password: str, today: str | None = None,
          transport: Transport | None = None, sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic,
          search: bool = True) -> list[dict[str, Any]]:
    """Write the raw answers into ``<data root>/raw/bcch-f022/`` and their provenance record; return the records.

    The first request is the ``SearchSeries`` answer of the daily frequency (the record of which series exist, ``search``), then one
    ``GetSeries`` per series for the days ``first`` to ``last``. The bytes are written as the server sent them. Requests are paced to at
    most 5 per second. The record of a file holds the URL without user and password, the size, the SHA-256 and the retrieval date."""
    send = transport or _http
    folder = Path(data_root) / "raw" / BCCH_DIR
    folder.mkdir(parents=True, exist_ok=True)
    when = today or dt.date.today().isoformat()
    state = {"last": None}

    def call(function: str, **params: str) -> tuple[bytes, str]:
        if state["last"] is not None:
            wait = MIN_INTERVAL - (clock() - state["last"])
            if wait > 0:
                sleep(wait)
        state["last"] = clock()
        try:
            body = send(request_url(function, user=user, password=password, **params))
        except Exception as exc:  # noqa: BLE001  (the message of a transport error can carry the URL, so only its type is kept)
            raise BcchError(f"the request {function} failed: {type(exc).__name__}") from None
        parse_answer(body)                                  # a refused answer is never written as a raw file
        return body, request_url(function, **params)

    rows: list[dict[str, Any]] = []
    plan: list[tuple[str, str, dict[str, str]]] = []
    if search:
        plan.append((SEARCH_FILE, "SearchSeries", {"frequency": "DAILY"}))
    plan += [(file_name(sid, first, last), "GetSeries", {"timeseries": sid, "firstdate": first, "lastdate": last}) for sid in series_ids]
    for name, function, params in plan:
        body, url = call(function, **params)
        (folder / name).write_bytes(body)
        rows.append({"name": name, "url": url, "bytes": len(body), "sha256": sha256_of(folder / name), "retrieved": when})
    (folder / PROVENANCE).write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
    return rows


def load_provenance(data_root: str | Path) -> list[dict[str, Any]]:
    """The provenance record, with every file's hash and size recomputed: a file that differs from its record is refused."""
    folder = Path(data_root) / "raw" / BCCH_DIR
    side = folder / PROVENANCE
    if not side.exists():
        raise FileNotFoundError(f"{side}: not fetched; run `python -m pipeline.io.bcch fetch --data-root {data_root} --first <day> --last <day>` "
                                f"from data-pipeline/ with {ENV_USER} and {ENV_PASSWORD} set")
    rows = json.loads(side.read_text(encoding="utf-8"))
    for r in rows:
        path = need(folder / r["name"], r["url"], "bcch fetch")
        if sha256_of(path) != r["sha256"] or path.stat().st_size != r["bytes"]:
            raise ValueError(f"{path}: differs from its provenance record (sha256 {sha256_of(path)})")
    return rows


def read_raw(data_root: str | Path) -> tuple[dict[str, Series], list[SeriesInfo], list[dict[str, Any]]]:
    """Every series file of the raw folder (verified against its record), the search listing and the records."""
    rows = load_provenance(data_root)
    folder = Path(data_root) / "raw" / BCCH_DIR
    series: dict[str, Series] = {}
    infos: list[SeriesInfo] = []
    for r in rows:
        body = (folder / r["name"]).read_bytes()
        if r["name"] == SEARCH_FILE:
            infos = parse_search(body)
        else:
            s = parse_series(body)
            series[s.series_id] = s
    return series, infos, rows


# ---------------------------------------------------------------------------------------------------------------- command line

#: the series C15 reads besides the yields of the search: the policy rate (the short anchor of the pesos curve) and the UF value
EXTRA_SERIES = ("F022.TPM.TIN.D001.NO.Z.D", "F073.UFF.PRE.Z.D")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipeline.io.bcch", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    f = sub.add_parser("fetch", help="fetch the F022 yields of a period, the policy rate and the UF value")
    f.add_argument("--data-root", required=True)
    f.add_argument("--first", required=True, help="first day, ISO")
    f.add_argument("--last", required=True, help="last day, ISO")
    f.add_argument("--series", nargs="*", help="series codes; by default the daily yields found by SearchSeries plus " + ", ".join(EXTRA_SERIES))
    args = ap.parse_args(argv)
    user, password = credentials_from_env()
    codes = args.series
    if not codes:
        body = _http(request_url("SearchSeries", user=user, password=password, frequency="DAILY"))
        found = [y.series_id for y in yield_series(parse_search(body))]
        codes = [*found, *EXTRA_SERIES]
        time.sleep(MIN_INTERVAL)
    rows = fetch(args.data_root, codes, args.first, args.last, user=user, password=password)
    for r in rows:
        print(f"{r['name']}: {r['bytes']:,} bytes sha256 {r['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
