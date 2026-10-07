"""ESMA CEREP: the paced, cached, pinned fetcher and the reader (CT-401, CT-402)."""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pytest

from pipeline.io import cerep
from pipeline.io import fetch as f
from pipeline.io import sources as s

PLAN = {"endpoint": "https://example.org/cerep/", "cras": ["STPGB"], "rating_type": "C", "horizon": "L",
        "years": [2010, 2011], "semester_years": [2011, 2011], "tabs": [2, 4], "pace_seconds": 4.5}

SP_LABELS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "R", "SD", "D", "NR", "Withdrawals"]
MDY_LABELS = ["Aaa", "Aa", "A", "Baa", "Ba", "B", "Caa", "Ca", "C", "WR", "Withdrawals"]
FIT_LABELS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "RD", "D", "WD", "NR", "Withdrawals"]


def _registry(tmp_path, plan=PLAN):
    entry = {"id": "toy-cerep", "name": "Toy CEREP", "publisher": "Test", "landing": "https://example.org/cerep/",
             "licence": "Reproduction authorised, source acknowledged", "class": "mirror-allowed", "access": "interface",
             "cases": ["C04"], "unverified": [], "fetch": {"kind": "cerep", "plan": plan}}
    p = tmp_path / "sources.json"
    p.write_text(json.dumps({"schema": s.SCHEMA, "sources": [entry]}), encoding="utf-8")
    return s.load(p)


def _filters(years=range(2009, 2013)):
    begin = [dt.date(y, m, 1) for y in years for m in (1, 7)]
    end = [dt.date(y, 6, 30) for y in years] + [dt.date(y, 12, 31) for y in years]
    return {"filters": {
        "begOfPrd": {"filterList": [{"code": cerep.date_code(d), "name": d.strftime("%d/%m/%Y")} for d in begin]},
        "endOfPrd": {"filterList": [{"code": cerep.date_code(d), "name": d.strftime("%d/%m/%Y")} for d in end]}}}


class FakeInterface:
    """Answers the two endpoints and records every request and wait."""

    def __init__(self, version=1):
        self.calls: list[tuple[str, dict]] = []
        self.version = version

    def post(self, path, body):
        self.calls.append((path, body))
        if path == "filters":
            return json.dumps(_filters()).encode()
        tab = int(path.rsplit("/", 1)[1])
        return json.dumps({"tab": tab, "version": self.version, "filters": body["filters"]}).encode()


def test_fetch_plan_paced_and_cached(tmp_path):
    """CT-401: the plan's queries, the interface's body, the pacing, the cache and the pin."""
    reg = _registry(tmp_path)
    root, man = tmp_path / "data", tmp_path / "manifest.json"
    fake, waits = FakeInterface(), []
    row = f.fetch("toy-cerep", root=root, manifest_path=man, reg=reg, post=fake.post, sleep=waits.append,
                  today=dt.date(2026, 10, 6))
    # the filters answer, then 2 years x 2 tabs and 2 semesters of tab 4
    paths = [c[0] for c in fake.calls]
    assert paths == ["filters"] + ["searchStatistics/2", "searchStatistics/4"] * 2 + ["searchStatistics/4"] * 2
    names = [x["name"] for x in row["files"]]
    assert names[0] == cerep.FILTERS_FILE and "t4_STPGB_20110701_20111231.json" in names and len(names) == 7
    assert all((root / "raw" / "toy-cerep" / n).exists() for n in names)
    # the body the interface itself sends: one list of "C" and "N" under both format keys; the period's codes
    body = fake.calls[1][1]["filters"]
    assert body["categories"] == body["number"] == {"filterList": [{"code": "C", "selected": True},
                                                                   {"code": "N", "selected": True}]}
    assert body["begOfPrd"]["filterList"][0]["code"] == cerep.date_code(dt.date(2010, 1, 1)) == 1262304000000
    assert body["cra"]["filterList"][0]["code"] == "STPGB" and body["ratingType"]["filterList"][0]["code"] == "C"
    # paced: no two requests closer than the plan's pace (the fake answers at once, so every gap is a wait)
    assert len(waits) == len(fake.calls) - 1 and min(waits) > 4.4
    manifest = json.loads(man.read_text(encoding="utf-8"))["sources"]["toy-cerep"]
    assert manifest["access"] == "cerep" and all(len(x["sha256"]) == 64 for x in manifest["files"])
    # cached: a second run asks nothing
    again = FakeInterface()
    f.fetch("toy-cerep", root=root, manifest_path=man, reg=reg, post=again.post, sleep=waits.append)
    assert again.calls == []
    # pinned: an answer whose bytes differ from the pin fails, until a refresh refetches everything and records it
    (root / "raw" / "toy-cerep" / names[1]).write_bytes(b"{}")
    with pytest.raises(f.FetchError, match="bytes changed"):
        f.fetch("toy-cerep", root=root, manifest_path=man, reg=reg, post=FakeInterface().post, sleep=waits.append)
    redo = FakeInterface(version=2)
    row2 = f.fetch("toy-cerep", root=root, manifest_path=man, reg=reg, post=redo.post, sleep=waits.append,
                   refresh=True, today=dt.date(2026, 10, 7))
    assert len(redo.calls) == 7 and any(x["retrieved"] == "2026-10-07" for x in row2["files"])


def test_plan_and_dates_checked(tmp_path):
    """CT-401: a plan out of bounds is refused by the registry; a period the interface does not offer is skipped."""
    with pytest.raises(s.RegistryError, match="at least 4 s apart"):
        _registry(tmp_path, {**PLAN, "pace_seconds": 1})
    with pytest.raises(s.RegistryError, match="agencies"):
        _registry(tmp_path, {**PLAN, "cras": ["XXXGB"]})
    reg = _registry(tmp_path, {**PLAN, "years": [2010, 2013]})  # the fake offers dates to 2012
    fake = FakeInterface()
    row = f.fetch("toy-cerep", root=tmp_path / "d", manifest_path=tmp_path / "m.json", reg=reg, post=fake.post,
                  sleep=lambda _: None)
    assert not any("2013" in x["name"] for x in row["files"])
    assert cerep.date_code(dt.date(2019, 1, 1)) == 1546300800000 and cerep.date_code(dt.date(2019, 12, 31)) == 1577750400000


def _t4(labels, rows):
    return {"transitionMatricesNumberOfTransitions": rows, "transitionMatricesHeaderColumnLabels": labels,
            "emptyCatLabels": False}


def _write_cohort(folder, cra, labels, t4_rows, t2=None, t3=None, year=2010):
    b, e = dt.date(year, 1, 1), dt.date(year, 12, 31)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / cerep.query_name(4, cra, b, e)).write_text(json.dumps(_t4(labels, t4_rows)), encoding="utf-8")
    if t2 is not None:
        (folder / cerep.query_name(2, cra, b, e)).write_text(json.dumps({"defaultRates": {"defMap": t2}}),
                                                            encoding="utf-8")
    if t3 is not None:
        (folder / cerep.query_name(3, cra, b, e)).write_text(json.dumps(
            {"transitionMatricesDefaultsNumberOfDefaultsCategories": t3,
             "transitionMatricesDefaultsHeaderColumnLabels": labels[:-1]}), encoding="utf-8")
    return b, e


def _cell(n, size):
    return {"nameOfRatingActivity": "", "numberOfRatings": n, "averageNumberOfRatings": 0.0,
            "percentageOfRatings": round(100.0 * n / size, 2) if size else 0.0}


def test_reader_maps_every_agency(tmp_path):
    """CT-402: each agency's labels on the common scale; the three default counts; tab 2 checked against tab 4."""
    folder = tmp_path / "raw" / "esma-cerep"
    # S&P: CCC, CC and C merge; R, SD and D are default; NR and Withdrawals withdrawn; a row starting in D is no cohort
    z = [0] * 14
    sp = [list(z) for _ in range(13)]
    sp[0][0], sp[0][1], sp[0][13] = 50, 5, 5                     # AAA: 50 stay, 5 to AA, 5 withdrawn
    sp[6][6], sp[6][11], sp[6][13], sp[6][10] = 70, 6, 20, 4     # CCC: 70 stay, 6 to D, 4 to SD, 20 withdrawn
    sp[7][7], sp[7][12] = 10, 2                                  # CC: 10 stay, 2 to NR
    sp[11][4], sp[11][11] = 3, 9                                 # in D at the start: not a performing cohort
    t2 = {lab: _cell(0, 0) for lab in SP_LABELS[:-1]}
    t2["CCC"], t2["CC"] = _cell(30, 100), _cell(1, 12)
    t3 = [[0] * 13 for _ in range(13)]
    t3[6][6], t3[6][11], t3[7][11] = 25, 8, 1                   # CCC: 33 default events, CC: 1
    b, e = _write_cohort(folder, "STPGB", SP_LABELS, sp, t2, t3)
    c = cerep.read_cohort(folder, "STPGB", b, e)
    assert c.size.tolist() == [60, 0, 0, 0, 0, 0, 112] and c.has_default_column and c.label == "2010"
    assert c.counts[6].tolist() == [0, 0, 0, 0, 0, 0, 80, 10] and c.withdrawn.tolist() == [5, 0, 0, 0, 0, 0, 22]
    assert c.defaulted[6] == 31 and c.events[6] == 34
    assert c.defaulted_cohort.tolist() == c.size.tolist() and c.tab2_gap == 0.0  # tab 2's rates are over tab 4's rows
    # Moody's: no default category on the transition page; WR is a withdrawal
    m = [[0] * 11 for _ in range(10)]
    m[2][2], m[2][3], m[2][10], m[2][9] = 80, 10, 8, 2
    b, e = _write_cohort(folder, "MDYGB", MDY_LABELS, m, {"A": _cell(2, 100)})
    c = cerep.read_cohort(folder, "MDYGB", b, e)
    assert not c.has_default_column and c.counts[:, 7].sum() == 0 and c.withdrawn[2] == 10 and c.defaulted[2] == 2
    # Fitch: RD and D default, WD withdrawn
    fi = [[0] * 14 for _ in range(13)]
    fi[5][5], fi[5][9], fi[5][10], fi[5][11] = 90, 1, 2, 7
    b, e = _write_cohort(folder, "FITGB", FIT_LABELS, fi)
    c = cerep.read_cohort(folder, "FITGB", b, e)
    assert c.counts[5, 7] == 3 and c.withdrawn[5] == 7 and c.defaulted is None
    # an unknown label; a tab 2 rate over a cohort larger than tab 4's row (as in S&P's 2001 to 2004 and 2008
    # cohorts: kept, the cohort taken from the printed rate, the gap recorded); a misread page; an empty period
    bad = [list(z) for _ in range(13)]
    with pytest.raises(cerep.CerepError, match="not on the agency's scale"):
        b, e = _write_cohort(folder, "STPGB", SP_LABELS[:-2] + ["XX", "Withdrawals"], bad, year=2011)
        cerep.read_cohort(folder, "STPGB", b, e)
    t2_other = dict(t2)
    t2_other["CCC"] = {**_cell(30, 100), "percentageOfRatings": 25.0}  # 30 defaults over 120 ratings, tab 4 has 100
    b, e = _write_cohort(folder, "STPGB", SP_LABELS, sp, t2_other, year=2012)
    c = cerep.read_cohort(folder, "STPGB", b, e)
    assert c.defaulted_cohort[6] == 120 + 12 and c.tab2_gap == pytest.approx(0.2) and c.size[6] == 112
    t2_bad = dict(t2)
    t2_bad["CCC"] = {**_cell(30, 100), "percentageOfRatings": 5.0}  # a cohort six times tab 4's: a shifted label
    b, e = _write_cohort(folder, "STPGB", SP_LABELS, sp, t2_bad, year=2014)
    with pytest.raises(cerep.CerepError, match="a misread page"):
        cerep.read_cohort(folder, "STPGB", b, e)
    b, e = _write_cohort(folder, "STPGB", SP_LABELS, [list(z) for _ in range(13)], year=2013)
    assert cerep.read_cohort(folder, "STPGB", b, e) is None
    # an agency's cohorts: only the periods with data
    got = cerep.read_agency(tmp_path, "MDYGB", range(2009, 2012), range(2010, 2011))
    assert [x.label for x in got["annual"]] == ["2010"] and got["semesters"] == []
    assert np.array_equal(got["annual"][0].size, [0, 0, 100, 0, 0, 0, 0])
