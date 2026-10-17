"""CT-1501 to CT-1503: the Banco Central de Chile BDE reader and its fetch (``pipeline.io.bcch``).

The samples under ``tests/c15/samples/`` are answers of the BDE as served (Latin-1 bytes), cut to the first 18 days of September 2026;
no test reads the network or the device data root. The fetch runs against a fake transport.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.io import bcch

SAMPLES = Path(__file__).resolve().parent / "c15" / "samples"
UF10 = SAMPLES / "uf-an10-2026-09-01-2026-09-18.json"
CLP5 = SAMPLES / "clp-an05-2026-09-01-2026-09-18.json"
UFV = SAMPLES / "uf-value-2026-09-01-2026-09-18.json"
SEARCH = SAMPLES / "search-daily-subset.json"


def answer(code: str, rows: list[tuple[str, str, str]], title: str = "Tasa de interés, bonos a 5 años") -> bytes:
    """A GetSeries answer in the BDE's shape, encoded as Latin-1 the way the server sends it."""
    body = {"Codigo": 0, "Descripcion": "Success",
            "Series": {"descripEsp": title, "descripIng": "English title", "seriesId": code,
                       "Obs": [{"indexDateString": d, "value": v, "statusCode": s} for d, v, s in rows]}}
    return json.dumps(body, ensure_ascii=False).encode("latin-1")


def test_the_answer_is_decoded_as_latin_1_and_dated_day_month_year() -> None:
    raw = UF10.read_bytes()
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8")                                    # the served bytes are not UTF-8: a UTF-8 reader fails on 0xE9
    s = bcch.parse_series(raw)
    assert s.series_id == "F022.BUF.TIS.AN10.UF.Z.D"
    assert s.title_es == "Tasa de interés mercado secundario, bonos en UF a 10 años (BCU, BTU)"
    assert s.title_en.startswith("10-year interest rate secondary market")
    first = s.observations[0]
    assert (first.date, first.value, first.status) == ("2026-09-01", 2.54, "OK")      # 01-09-2026 is the first of September
    assert s.values()["2026-09-15"] == 2.6 and s.values()["2026-09-16"] == 2.62
    assert all(o.date.startswith("2026-09-") for o in s.observations)
    assert bcch.parse_series(UFV.read_bytes()).values()["2026-09-01"] == 40875.09
    assert bcch.tenor_years("F022.BUF.TIS.AN10.UF.Z.D") == 10.0 and bcch.tenor_years("F073.UFF.PRE.Z.D") is None


def test_a_non_zero_codigo_is_refused_and_names_no_credential() -> None:
    body = json.dumps({"Codigo": -5, "Descripcion": "Invalid username or password", "Series": {"Obs": None}}).encode("ascii")
    with pytest.raises(bcch.BcchError) as e:
        bcch.parse_series(body)
    assert e.value.codigo == -5 and "-5" in str(e.value) and "Invalid username or password" in str(e.value)
    assert "pass=" not in str(e.value) and "user=" not in str(e.value)
    with pytest.raises(bcch.BcchError, match="not a BDE answer"):
        bcch.parse_series(b"<html>ErrorPage</html>")


def test_a_nan_observation_is_missing_listed_and_never_filled() -> None:
    s = bcch.parse_series(UF10.read_bytes())
    assert "2026-09-05" in s.missing() and "2026-09-09" in s.missing()
    assert "2026-09-05" not in s.values() and "2026-09-09" not in s.values()
    assert s.values(up_to="2026-09-04") == {"2026-09-01": 2.54, "2026-09-02": 2.55, "2026-09-03": 2.54, "2026-09-04": 2.53}
    odd = bcch.parse_series(answer("X", [("01-09-2026", "NaN", "OK"), ("02-09-2026", "1.5", "ND"), ("03-09-2026", "2.5", "OK")]))
    assert odd.values() == {"2026-09-03": 2.5} and odd.missing() == ["2026-09-01", "2026-09-02"]


def test_the_search_lists_the_daily_series_with_their_tenors() -> None:
    infos = bcch.parse_search(SEARCH.read_bytes())
    assert [i.series_id for i in infos] == ["F022.BCLP.TIS.AN05.NO.Z.D", "F022.BUF.TIS.AN01.UF.Z.D", "F022.BUF.TIS.AN10.UF.Z.D", "F073.UFF.PRE.Z.D"]
    assert all(i.frequency == "DAILY" for i in infos)
    assert infos[1].last_observation == "2025-12-26" and infos[1].title_es.endswith("a 1 año (BCU, BTU)")
    nd = json.dumps({"Codigo": 0, "Descripcion": "Success", "SeriesInfos": [
        {"seriesId": "F022.BUF.TIS.AN05.UF.Z.D", "frequencyCode": "DAILY", "spanishTitle": "t", "englishTitle": "t", "firstObservation": "ND",
         "lastObservation": None}]}).encode("ascii")
    assert bcch.parse_search(nd)[0].first_observation is None and bcch.parse_search(nd)[0].last_observation is None
    found = bcch.yield_series(infos)
    assert [(f.series_id, f.curve, f.tenor_years) for f in found] == [
        ("F022.BCLP.TIS.AN05.NO.Z.D", "CLP", 5.0), ("F022.BUF.TIS.AN01.UF.Z.D", "UR", 1.0), ("F022.BUF.TIS.AN10.UF.Z.D", "UR", 10.0)]


def test_the_valuation_date_is_the_last_day_every_chosen_series_has_a_value() -> None:
    a = bcch.parse_series(answer("A", [("01-09-2026", "1", "OK"), ("02-09-2026", "1", "OK"), ("03-09-2026", "1", "OK"), ("04-09-2026", "1", "OK")]))
    b = bcch.parse_series(answer("B", [("01-09-2026", "2", "OK"), ("02-09-2026", "2", "OK"), ("03-09-2026", "2", "OK"), ("04-09-2026", "NaN", "ND")]))
    c = bcch.parse_series(answer("C", [("01-09-2026", "3", "OK"), ("02-09-2026", "NaN", "ND"), ("03-09-2026", "3", "OK")]))
    assert bcch.last_common_date([a, b, c], "2026-09-01", "2026-09-30") == "2026-09-03"
    assert bcch.last_common_date([a, b], "2026-09-01", "2026-09-30") == "2026-09-03"
    assert bcch.last_common_date([a], "2026-09-01", "2026-09-30") == "2026-09-04"
    assert bcch.last_common_date([a, b, c], "2026-09-01", "2026-09-02") == "2026-09-01"          # the window ends the search
    assert bcch.last_common_date([a, c], "2026-09-02", "2026-09-02") is None                       # no day in the window has all
    # a value on a Saturday is not a business day
    sat = bcch.parse_series(answer("S", [("05-09-2026", "1", "OK")]))
    assert bcch.last_common_date([sat], "2026-09-01", "2026-09-30") is None
    # the first and last 18 days of the sample series: the rule on real answers
    real = [bcch.parse_series(UF10.read_bytes()), bcch.parse_series(CLP5.read_bytes())]
    last = bcch.last_common_date(real, "2026-09-01", "2026-09-18")
    assert last is not None and all(last in s.values() for s in real) and last <= "2026-09-18"


class Transport:
    """A fake BDE: records the requests (URL, time on a fake clock) and answers from a table."""

    def __init__(self, answers: dict[str, bytes]) -> None:
        self.answers, self.log, self.now = answers, [], 1000.0

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def __call__(self, url: str) -> bytes:
        self.log.append((url, self.now))
        for key, body in self.answers.items():
            if key in url:
                return body
        raise AssertionError(f"no answer for {url}")


def test_the_fetch_records_the_url_without_credentials_the_size_the_hash_and_the_date(tmp_path: Path) -> None:
    tr = Transport({"function=SearchSeries": SEARCH.read_bytes(), "F022.BUF.TIS.AN10": UF10.read_bytes(), "F073.UFF": UFV.read_bytes()})
    rows = bcch.fetch(tmp_path, ["F022.BUF.TIS.AN10.UF.Z.D", "F073.UFF.PRE.Z.D"], "2026-09-01", "2026-09-18",
                      user="the-user", password="the-secret", today="2026-10-16", transport=tr, sleep=tr.sleep, clock=tr.clock)
    folder = tmp_path / "raw" / bcch.BCCH_DIR
    names = sorted(r["name"] for r in rows)
    assert names == ["F022.BUF.TIS.AN10.UF.Z.D-2026-09-01-2026-09-18.json", "F073.UFF.PRE.Z.D-2026-09-01-2026-09-18.json", "search-daily.json"]
    for r in rows:
        data = (folder / r["name"]).read_bytes()
        assert r["bytes"] == len(data) and r["sha256"] == bcch.sha256_of(folder / r["name"]) and r["retrieved"] == "2026-10-16"
        assert r["url"].startswith("https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?")
        assert "user" not in r["url"].lower().replace("function", "") and "pass" not in r["url"].lower()
        assert "the-user" not in r["url"] and "the-secret" not in r["url"]
    side = json.loads((folder / bcch.PROVENANCE).read_text(encoding="utf-8"))
    assert side == rows
    assert "the-user" not in (folder / bcch.PROVENANCE).read_text(encoding="utf-8")
    assert all("the-secret" not in p.read_text(encoding="latin-1") for p in folder.iterdir())
    assert bcch.load_provenance(tmp_path) == rows
    # the files are the bytes the server sent, never re-encoded
    assert (folder / names[0]).read_bytes() == UF10.read_bytes()
    # a changed byte is refused by the loader
    path = folder / names[0]
    path.write_bytes(path.read_bytes().replace(b"2.54", b"2.55", 1))
    with pytest.raises(ValueError, match="differs from its provenance record"):
        bcch.load_provenance(tmp_path)


def test_the_fetch_reads_the_credentials_from_the_environment_only_and_paces_requests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BCCH_USER", raising=False)
    monkeypatch.delenv("BCCH_PASSWORD", raising=False)
    with pytest.raises(bcch.BcchError, match="BCCH_USER and BCCH_PASSWORD"):
        bcch.credentials_from_env()
    monkeypatch.setenv("BCCH_USER", "u@example.org")
    monkeypatch.setenv("BCCH_PASSWORD", "s3cret")
    assert bcch.credentials_from_env() == ("u@example.org", "s3cret")
    # the request URL carries the credentials; the recorded one does not
    sent = bcch.request_url("GetSeries", user="u@example.org", password="s3cret", timeseries="X", firstdate="2026-09-01", lastdate="2026-09-30")
    kept = bcch.request_url("GetSeries", timeseries="X", firstdate="2026-09-01", lastdate="2026-09-30")
    assert "user=u%40example.org" in sent and "pass=s3cret" in sent and "user=" not in kept and "pass=" not in kept
    assert kept == "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?function=GetSeries&timeseries=X&firstdate=2026-09-01&lastdate=2026-09-30"
    # at most 5 requests per second: any 6 consecutive requests span more than one second on the fake clock
    codes = [f"F022.BUF.TIS.AN{k:02d}.UF.Z.D" for k in range(1, 13)]
    tr = Transport({"function=SearchSeries": SEARCH.read_bytes(), **{c: answer(c, [("01-09-2026", "2.5", "OK")]) for c in codes}})
    bcch.fetch(tmp_path, codes, "2026-09-01", "2026-09-30", user="u", password="p", today="2026-10-16", transport=tr, sleep=tr.sleep, clock=tr.clock)
    times = [t for _, t in tr.log]
    assert len(times) == 13 and all(times[k + 5] - times[k] > 1.0 for k in range(len(times) - 5))
    # a transport failure is reported without the URL (which carries the credentials)

    def boom(url: str) -> bytes:
        raise OSError(f"cannot reach {url}")

    with pytest.raises(bcch.BcchError) as e:
        bcch.fetch(tmp_path, codes[:1], "2026-09-01", "2026-09-30", user="u", password="s3cret", today="2026-10-16", transport=boom,
                   sleep=lambda s: None, clock=lambda: 0.0)
    assert "s3cret" not in str(e.value) and "pass=" not in str(e.value) and "OSError" in str(e.value)
