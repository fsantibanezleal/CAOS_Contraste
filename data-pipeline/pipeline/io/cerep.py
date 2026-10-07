"""ESMA CEREP: the fetch plan, the paced fetcher and the reader (CT-401, CT-402).

CEREP publishes the rating agencies' statistics as aggregates only, built on "a stock concept model, so that
intra-period rating activity is derived from a comparison of ratings at the beginning and the end of a period" (ESMA,
CEREP help file, ESMA65-8-10634). Its publication interface (https://registers.esma.europa.eu/cerep-publication/,
script ``js/cerep.js``) calls two JSON endpoints by POST with a body ``{"filters": {...}}``, each filter a
``{"filterList": [{"code": ..., "selected": true}]}``: ``filters`` (the options a selection allows, among them the
semi-annual beginnings and ends of period with their codes) and ``searchStatistics/{tab}`` (tab 1 rating activity, 2
default rates, 3 defaults by category, 4 transitions). The interface puts one list holding the categories-or-notches
choice ("C") and the number-or-percentage choice ("N") under both ``categories`` and ``number``; the fetcher sends the
same body. A period's codes are the epoch milliseconds of its dates at midnight UTC (01/01/2019 is 1546300800000), and
the fetcher checks each against the ``filters`` answer.

The service reset the connection after some fifteen requests a second apart (dossier 13): requests are paced
(``pace_seconds``, at least four), retried with a growing wait, and every answer is written to the device data root and
pinned in the licence manifest, so a bake never refetches.

What the pages count (help file, sections 4.2 to 4.4): tab 2, "The distinct number of ratings included in the
'number of defaults' ... divided by the total number of ratings belonging in the initial cohort"; tab 3, rows the
category at the beginning of the period and columns "the category or notch of the rating at the placement of the
default event", "all default events will be counted"; tab 4, rows the category at the beginning and columns at the
end, a rating withdrawn by the end "included in the 'Withdrawals' column according to the Category or Notch it was
rated with at the start". "For the purposes of reporting into the CEREP, no deterministic definition of a default event
has been set up. Therefore, the definitions might differ for various CRAs".
"""
from __future__ import annotations

import datetime as dt
import hashlib
import http.cookiejar
import json
import shutil
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ENDPOINT = "https://registers.esma.europa.eu/cerep-publication/"
USER_AGENT = "Mozilla/5.0 (compatible; Contraste-pipeline/1.0; +https://github.com/fsantibanezleal/CAOS_Contraste)"
MIN_PACE = 4.0
TABS = (2, 3, 4)
FILTERS_FILE = "filters.json"

#: the agencies' EU entities C04 reads, with the labels of their statistics rating scales
AGENCIES = {
    "STPGB": "Standard & Poor's Credit Market Services Europe Limited",
    "MDYGB": "Moody's Investors Service Ltd",
    "FITGB": "Fitch Ratings Limited",
}

#: the common scale: seven performing grades, then default
GRADES = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC-C")
DEFAULT = "D"
#: each agency's label to a common grade index (0 to 6), "D" (default) or "W" (withdrawn at the end)
SCALE = {
    "STPGB": {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "B": 5, "CCC": 6, "CC": 6, "C": 6,
              "R": "D", "SD": "D", "D": "D", "NR": "W", "Withdrawals": "W"},
    "FITGB": {"AAA": 0, "AA": 1, "A": 2, "BBB": 3, "BB": 4, "B": 5, "CCC": 6, "CC": 6, "C": 6,
              "RD": "D", "D": "D", "WD": "W", "NR": "W", "Withdrawals": "W"},
    "MDYGB": {"Aaa": 0, "Aa": 1, "A": 2, "Baa": 3, "Ba": 4, "B": 5, "Caa": 6, "Ca": 6, "C": 6,
              "WR": "W", "Withdrawals": "W"},
}


class CerepError(RuntimeError):
    """A CEREP request failed, an answer is malformed, or a label is not on the agency's scale."""


@dataclass(frozen=True)
class Query:
    name: str
    tab: int
    cra: str
    begin: dt.date
    end: dt.date


def date_code(d: dt.date) -> int:
    """The interface's code of a date: epoch milliseconds at midnight UTC."""
    return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000)


def query_name(tab: int, cra: str, begin: dt.date, end: dt.date) -> str:
    return f"t{tab}_{cra}_{begin:%Y%m%d}_{end:%Y%m%d}.json"


def plan_queries(plan: dict[str, Any]) -> list[Query]:
    """Every calendar-year cohort in ``years`` for every tab in ``tabs``, and every semester in ``semester_years`` for
    tab 4, for every agency in ``cras``."""
    out: list[Query] = []
    y0, y1 = plan["years"]
    s0, s1 = plan["semester_years"]
    for cra in plan["cras"]:
        for y in range(y0, y1 + 1):
            for tab in plan["tabs"]:
                b, e = dt.date(y, 1, 1), dt.date(y, 12, 31)
                out.append(Query(query_name(tab, cra, b, e), tab, cra, b, e))
        for y in range(s0, s1 + 1):
            for b, e in ((dt.date(y, 1, 1), dt.date(y, 6, 30)), (dt.date(y, 7, 1), dt.date(y, 12, 31))):
                out.append(Query(query_name(4, cra, b, e), 4, cra, b, e))
    return out


def check_plan(plan: Any) -> list[str]:
    """Problems with a fetch plan (the registry calls it)."""
    if not isinstance(plan, dict):
        return ["a cerep fetch names its plan"]
    out = []
    if not plan.get("cras") or not set(plan["cras"]) <= set(AGENCIES):
        out.append(f"the plan's agencies are among {sorted(AGENCIES)}")
    for key in ("years", "semester_years"):
        v = plan.get(key)
        if not (isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) for x in v) and v[0] <= v[1]):
            out.append(f"the plan's {key} is [first, last]")
    if not plan.get("tabs") or not set(plan["tabs"]) <= set(TABS):
        out.append(f"the plan's tabs are among {list(TABS)}")
    if plan.get("rating_type") != "C" or plan.get("horizon") != "L":
        out.append("the plan reads corporate (C) long-term (L) ratings")
    if not isinstance(plan.get("pace_seconds"), (int, float)) or plan["pace_seconds"] < MIN_PACE:
        out.append(f"the plan paces requests at least {MIN_PACE:g} s apart")
    return out


def _fl(*codes: Any) -> dict[str, Any]:
    return {"filterList": [{"code": c, "selected": True} for c in codes]}


def search_body(q: Query, plan: dict[str, Any]) -> dict[str, Any]:
    fmt = _fl("C", "N")  # the interface's own list: categories (C) and number (N), under both keys
    return {"filters": {"categories": fmt, "number": fmt, "cra": _fl(q.cra), "begOfPrd": _fl(date_code(q.begin)),
                        "endOfPrd": _fl(date_code(q.end)), "ratingType": _fl(plan["rating_type"]),
                        "timeHorizon": _fl(plan["horizon"])}}


# A post takes a path below the endpoint and a JSON body, and returns the answer's bytes (tests pass their own).
Post = Callable[[str, dict[str, Any]], bytes]


class Session:
    """A cookie session with the publication interface: the landing page first, then paced POSTs."""

    def __init__(self, endpoint: str = ENDPOINT, *, retries: int = 4, timeout: float = 90.0,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        if not endpoint.startswith("https://"):
            raise CerepError("the CEREP endpoint is https")
        self.endpoint, self.retries, self.timeout, self.sleep = endpoint, retries, timeout, sleep
        self._open()

    def _open(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.opener.addheaders = [("User-Agent", USER_AGENT)]
        self.opener.open(self.endpoint, timeout=self.timeout).read()

    def post(self, path: str, body: dict[str, Any]) -> bytes:
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                req = urllib.request.Request(self.endpoint + path, data=json.dumps(body).encode("utf-8"),
                                             headers={"Content-Type": "application/json"})
                with self.opener.open(req, timeout=self.timeout) as resp:  # noqa: S310 (https, checked above)
                    return resp.read()
            except (OSError, urllib.error.URLError) as exc:  # resets, timeouts, DNS
                last = exc
                self.sleep(15.0 * (attempt + 1))
                try:
                    self._open()
                except OSError as again:
                    last = again
        raise CerepError(f"POST {path} failed after {self.retries} attempts: {last}")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_plan(src: Any, *, root: Path, pinned: dict[str, dict[str, Any]], refresh: bool, stamp: str,
               post: Post | None = None, sleep: Callable[[float], None] = time.sleep,
               log: Callable[[str], None] = print) -> list[dict[str, Any]]:
    """Fetch the filters answer and every query of the plan not already in the data root (all of them with
    ``refresh``), pacing the requests; return the manifest's file rows. A file whose bytes differ from its pin fails
    unless ``refresh``."""
    plan = src.plan
    endpoint = plan.get("endpoint", ENDPOINT)
    folder = root / "raw" / src.id
    folder.mkdir(parents=True, exist_ok=True)
    session_post = post
    last_request = [float("-inf")]

    def paced(path: str, body: dict[str, Any]) -> bytes:
        nonlocal session_post
        if session_post is None:
            session_post = Session(endpoint, sleep=sleep).post
        wait = plan["pace_seconds"] - (time.monotonic() - last_request[0])
        if wait > 0:
            sleep(wait)
        try:
            return session_post(path, body)
        finally:
            last_request[0] = time.monotonic()

    def get(name: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        dest = folder / name
        if dest.exists() and not refresh:
            data = dest.read_bytes()
        else:
            data = paced(path, body)
            if not data:
                raise CerepError(f"{name}: the service answered no bytes")
            json.loads(data)  # an answer that is not JSON is an error page, never pinned
            part = dest.with_name(dest.name + ".part")
            part.write_bytes(data)
            shutil.move(str(part), dest)
        sha = _sha(data)
        old = pinned.get(name)
        if old is not None and old["sha256"] != sha and not refresh:
            raise CerepError(f"{src.id}/{name}: the bytes changed (pinned {old['sha256'][:12]}, now {sha[:12]}); "
                             "fetch again with --refresh to accept ESMA's new publication")
        same = old is not None and old["sha256"] == sha
        return {"name": name, "url": endpoint + path, "sha256": sha, "bytes": len(data),
                "retrieved": old["retrieved"] if same else stamp}

    fmt = _fl("C", "N")
    rows = [get(FILTERS_FILE, "filters", {"filters": {"categories": fmt, "number": fmt}})]
    offered = _offered_dates(json.loads((folder / FILTERS_FILE).read_bytes()))
    queries = plan_queries(plan)
    for i, q in enumerate(queries, 1):
        if offered and (q.begin not in offered["begin"] or q.end not in offered["end"]):
            log(f"  {q.name}: not offered by the interface, skipped")
            continue
        rows.append(get(q.name, f"searchStatistics/{q.tab}", search_body(q, plan)))
        if i % 25 == 0:
            log(f"  {i} of {len(queries)} queries")
    return rows


def _offered_dates(filters: dict[str, Any]) -> dict[str, set[dt.date]] | None:
    f = filters.get("filters") or {}
    if "begOfPrd" not in f or "endOfPrd" not in f:
        return None

    def dates(key: str) -> set[dt.date]:
        return {dt.datetime.strptime(x["name"], "%d/%m/%Y").date() for x in f[key]["filterList"]}

    return {"begin": dates("begOfPrd"), "end": dates("endOfPrd")}


# ---------------------------------------------------------------------------------------------------------------------
# the reader (CT-402)


@dataclass(frozen=True)
class Cohort:
    """One cohort of one agency on the common scale: ``counts`` (7 x 8, the performing grades at the beginning by the
    grades and default at the end), ``withdrawn`` (7), ``defaulted`` (7, tab 2's distinct defaulted ratings),
    ``events`` (7, tab 3's default events), ``size`` (7, the cohort by grade); ``has_default_column`` is False where
    the transition page has no default category (Moody's)."""

    cra: str
    begin: dt.date
    end: dt.date
    counts: np.ndarray
    withdrawn: np.ndarray
    defaulted: np.ndarray | None
    events: np.ndarray | None
    size: np.ndarray
    has_default_column: bool

    @property
    def label(self) -> str:
        if self.begin.month == 1 and self.end.month == 12:
            return f"{self.begin.year}"
        return f"{self.begin.year}H{1 if self.begin.month == 1 else 2}"


def _map(cra: str, label: str) -> int | str:
    try:
        return SCALE[cra][label]
    except KeyError:
        raise CerepError(f"{cra}: the label {label!r} is not on the agency's scale") from None


def _transition_page(cra: str, data: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, bool, dict[str, float]] | None:
    m = data.get("transitionMatricesNumberOfTransitions")
    labels = data.get("transitionMatricesHeaderColumnLabels")
    if m is None or labels is None:
        return None
    a = np.asarray(m, dtype=float)
    if a.shape != (len(labels) - 1, len(labels)) or labels[-1] != "Withdrawals":
        raise CerepError(f"{cra}: a transition page of shape {a.shape} with {len(labels)} labels")
    cols = [_map(cra, x) for x in labels]
    rows = cols[:-1]
    counts = np.zeros((7, 8))
    withdrawn = np.zeros(7)
    label_sizes = {labels[i]: float(a[i].sum()) for i in range(len(rows))}
    for i, r in enumerate(rows):
        if not isinstance(r, int):
            continue  # ratings in default or withdrawn at the beginning are not in a performing cohort
        for j, c in enumerate(cols):
            if a[i, j] == 0:
                continue
            if c == "W":
                withdrawn[r] += a[i, j]
            elif c == "D":
                counts[r, 7] += a[i, j]
            else:
                counts[r, c] += a[i, j]
    return counts, withdrawn, "D" in cols, label_sizes


def _default_rate_page(cra: str, data: dict[str, Any]) -> np.ndarray | None:
    page = (data.get("defaultRates") or {}).get("defMap")
    if page is None:
        return None
    out = np.zeros(7)
    for label, cell in page.items():
        g = _map(cra, label)
        if isinstance(g, int):
            out[g] += float(cell["numberOfRatings"])
    return out


def _defaults_page(cra: str, data: dict[str, Any]) -> np.ndarray | None:
    m = data.get("transitionMatricesDefaultsNumberOfDefaultsCategories")
    labels = data.get("transitionMatricesDefaultsHeaderColumnLabels")
    if m is None or labels is None:
        return None
    a = np.asarray(m, dtype=float)
    if a.shape != (len(labels), len(labels)):
        raise CerepError(f"{cra}: a defaults page of shape {a.shape} with {len(labels)} labels")
    out = np.zeros(7)
    for i, label in enumerate(labels):
        g = _map(cra, label)
        if isinstance(g, int):
            out[g] += a[i].sum()  # rows: the category at the beginning; every default event counted
    return out


def read_cohort(folder: Path, cra: str, begin: dt.date, end: dt.date) -> Cohort | None:
    """One cohort from the raw answers; None when the transition page is empty (no ratings in that period)."""
    def load(tab: int) -> dict[str, Any] | None:
        p = folder / query_name(tab, cra, begin, end)
        return json.loads(p.read_bytes()) if p.exists() else None

    t4 = load(4)
    page = _transition_page(cra, t4) if t4 else None
    if page is None:
        return None
    counts, withdrawn, has_d, label_sizes = page
    size = counts.sum(axis=1) + withdrawn
    if size.sum() == 0:
        return None
    t2, t3 = load(2), load(3)
    defaulted = _default_rate_page(cra, t2) if t2 else None
    events = _defaults_page(cra, t3) if t3 else None
    for label, cell in ((t2 or {}).get("defaultRates") or {}).get("defMap", {}).items():
        n = label_sizes.get(label, 0.0)
        if n > 0 and isinstance(_map(cra, label), int):
            # tab 2's percentage is its count over the label's cohort on tab 4, printed to two decimals
            implied = 100.0 * float(cell["numberOfRatings"]) / n
            if abs(implied - float(cell["percentageOfRatings"])) > 0.0051:
                raise CerepError(f"{cra} {begin}: tab 2 gives {cell['percentageOfRatings']}% for {label}, its count "
                                 f"over tab 4's cohort {implied:.4f}%")
    return Cohort(cra, begin, end, counts, withdrawn, defaulted, events, size, has_d)


def read_agency(root: Path, cra: str, years: range, semester_years: range,
                source_id: str = "esma-cerep") -> dict[str, list[Cohort]]:
    """Every annual and semester cohort of an agency with data."""
    folder = Path(root) / "raw" / source_id
    annual = [c for y in years if (c := read_cohort(folder, cra, dt.date(y, 1, 1), dt.date(y, 12, 31))) is not None]
    semesters = []
    for y in semester_years:
        for b, e in ((dt.date(y, 1, 1), dt.date(y, 6, 30)), (dt.date(y, 7, 1), dt.date(y, 12, 31))):
            c = read_cohort(folder, cra, b, e)
            if c is not None:
                semesters.append(c)
    return {"annual": annual, "semesters": semesters}
