"""Write ``references.bib`` from the records of the works the text cites.

    python manuscripts/adaptive-conformal-recalibration-of-var/fetch_references.py

Every cited key of ``main.tex`` and ``sections/*.tex`` is looked up in ``WORKS`` below. A work with a DOI is fetched from
``https://doi.org/<doi>`` with ``Accept: application/x-bibtex`` (the publisher's own record); a preprint is fetched from the
arXiv API (``export.arxiv.org``); a standard of the Basel Committee is written with its stable URL, checked to answer 200.
The script refuses a key that is cited and not listed, and a record that does not carry the expected title words.
"""
from __future__ import annotations

import pathlib
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent

#: key -> (kind, identifier, words the fetched title must contain)
WORKS = {
    "kupiec1995": ("doi", "10.3905/jod.1995.407942", "verifying"),
    "christoffersen1998": ("doi", "10.2307/2527341", "interval forecasts"),
    "christoffersenpelletier2004": ("doi", "10.1093/jjfinec/nbh004", "duration"),
    "engle2004": ("doi", "10.1198/073500104000000370", "caviar"),
    "fissler2016": ("doi", "10.1214/16-AOS1439", "elicitability"),
    "pattonziegelchen2019": ("doi", "10.1016/j.jeconom.2018.10.008", "semiparametric"),
    "gneiting2011": ("doi", "10.1198/jasa.2011.r10138", "point forecasts"),
    "noldeziegel2017": ("doi", "10.1214/17-AOAS1041", "backtesting"),
    "hansen2011": ("doi", "10.3982/ECTA5771", "confidence set"),
    "diebold1995": ("doi", "10.1080/07350015.1995.10524599", "predictive accuracy"),
    "duescanciano2017": ("doi", "10.1287/mnsc.2015.2342", "backtesting expected shortfall"),
    "kratz2018": ("doi", "10.1016/j.jbankfin.2018.01.002", "multinomial"),
    "barone1999": ("doi", "10.1002/(sici)1096-9934(199908)19:5<583::aid-fut5>3.0.co;2-s", "correlations"),
    "boudoukh1998": ("doi", "10.2139/ssrn.51420", "best of both worlds"),
    "hullwhite1998": ("doi", "10.21314/JOR.1998.001", "volatility updating"),
    "mcneilfrey2000": ("doi", "10.1016/S0927-5398(00)00012-8", "tail-related"),
    "bollerslev1986": ("doi", "10.1016/0304-4076(86)90063-1", "heteroskedasticity"),
    "gjr1993": ("doi", "10.1111/j.1540-6261.1993.tb05128.x", "expected value"),
    "nelson1991": ("doi", "10.2307/2938260", "heteroskedasticity"),
    "taylor2019": ("doi", "10.1080/07350015.2017.1281815", "semiparametric"),
    "pritsker2006": ("doi", "10.1016/j.jbankfin.2005.04.013", "historical simulation"),
    "berkowitz2002": ("doi", "10.1111/1540-6261.00455", "accurate"),
    "perignon2008": ("doi", "10.1016/j.jbankfin.2007.05.014", "overstate"),
    "perignon2010": ("doi", "10.1016/j.jbankfin.2009.08.009", "disclosure"),
    "escanciano2012": ("doi", "10.1016/j.jbankfin.2012.04.004", "pitfalls"),
    "berkowitz2011": ("doi", "10.1287/mnsc.1080.0964", "desk-level"),
    "kuester2006": ("doi", "10.1093/jjfinec/nbj002", "value-at-risk prediction"),
    "bayer2022": ("doi", "10.1093/jjfinec/nbaa013", "regression-based"),
    "acerbitasche2002": ("doi", "10.1016/S0378-4266(02)00283-2", "coherence"),
    "artzner1999": ("doi", "10.1111/1467-9965.00068", "coherent"),
    "vovk2005": ("doi", "10.1007/b106715", ""),
    "lei2018": ("doi", "10.1080/01621459.2017.1307116", "distribution-free"),
    "barber2023": ("doi", "10.1214/23-AOS2276", "exchangeability"),
    "angelopoulosbates2023": ("doi", "10.1561/2200000101", "conformal prediction"),
    "fantazzini2024": ("doi", "10.3390/jrfm17060248", "conformal inference"),
    "koenker1978": ("doi", "10.2307/1913643", "regression quantiles"),
    "robbins1951": ("doi", "10.1214/aoms/1177729586", "stochastic approximation"),
    "wilson1927": ("doi", "10.1080/01621459.1927.10502953", "probable inference"),
    "brown2001": ("doi", "10.1214/ss/1009213286", "binomial"),
    "kunsch1989": ("doi", "10.1214/aos/1176347265", "jackknife"),
    "politis1994": ("doi", "10.1080/01621459.1994.10476870", "stationary bootstrap"),
    "morris2019": ("doi", "10.1002/sim.8086", "simulation studies"),
    "fama1993": ("doi", "10.1016/0304-405X(93)90023-5", "risk factors"),
    "ziegel2016": ("doi", "10.1111/mafi.12080", "elicitability"),
    "engle1982": ("doi", "10.2307/1912773", "heteroscedasticity"),
    "efron1979": ("doi", "10.1214/aos/1176344552", "bootstrap"),
    "gibbs2021": ("arxiv", "2106.00170", "adaptive conformal"),
    "gibbs2024": ("arxiv", "2208.08401", "online prediction"),
    "zaffran2022": ("arxiv", "2202.07282", "adaptive conformal"),
    "angelopoulos2023": ("arxiv", "2307.16895", "pid"),
    "romano2019": ("arxiv", "1905.03222", "quantile"),
    "xu2021": ("arxiv", "2010.09107", "time series"),
    "bhatnagar2023": ("arxiv", "2302.07869", "online conformal"),
    "angelopoulos2024": ("arxiv", "2402.01139", "step sizes"),
    "tibshirani2019": ("arxiv", "1904.06019", "covariate shift"),
    "wang2022": ("arxiv", "2209.00991", "backtesting"),
    "fisslerziegelgneiting2016": ("arxiv", "1507.00244", "jointly elicitable"),
    "aich2025": ("arxiv", "2507.05470", "temporal conformal"),
    "bcbs1996": ("url", "https://www.bis.org/publ/bcbs22.htm",
                 "Supervisory framework for the use of backtesting in conjunction with the internal models approach to market risk capital requirements|"
                 "Basel Committee on Banking Supervision|1996"),
    "bcbsmar32": ("url", "https://www.bis.org/basel_framework/chapter/MAR/32.htm",
                  "Basel Framework, market risk, chapter MAR32: internal models approach, backtesting and profit and loss attribution requirements|"
                  "Basel Committee on Banking Supervision|2020"),
    "cfr217204": ("url", "https://www.ecfr.gov/current/title-12/chapter-II/subchapter-A/part-217/subpart-F/section-217.204",
                  "12 CFR 217.204, Measure for market risk (Table 1: multiplication factors based on results of backtesting)|"
                  "Board of Governors of the Federal Reserve System|2025"),
    "acerbiszekely2014": ("manual", "", ""),
    "bcbsmar33": ("url", "https://www.bis.org/basel_framework/chapter/MAR/33.htm",
                  "Basel Framework, market risk, chapter MAR33: internal models approach, capital requirements|Basel Committee on Banking Supervision|2020"),
}


def get(url: str, accept: str | None = None) -> bytes:
    last = None
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (contraste-references)", **({"Accept": accept} if accept else {})})
            return urllib.request.urlopen(req, timeout=40).read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2)
    raise RuntimeError(f"{url}: {last}")


#: Fields corrected from the works' own records where Crossref's author list is incomplete (checked on OpenAlex and RePEc, 2026-11-07), and
#: the one work without a DOI (Risk, December 2014; the page range was not confirmed on a primary source and is left out).
OVERRIDES = {
    "christoffersenpelletier2004": {"author": "Christoffersen, Peter and Pelletier, Denis"},
    "kuester2006": {"author": "Kuester, Keith and Mittnik, Stefan and Paolella, Marc S.", "year": "2006"},
    "hansen2011": {"author": "Hansen, Peter R. and Lunde, Asger and Nason, James M."},
    "vovk2005": {"@type": "book", "author": "Vovk, Vladimir and Gammerman, Alex and Shafer, Glenn", "publisher": "Springer"},
    "boudoukh1998": {"author": "Boudoukh, Jacob and Richardson, Matthew P. and Whitelaw, Robert F.", "journal": "Risk"},
}
MANUAL = {
    "acerbiszekely2014": (
        "@article{acerbiszekely2014,\n  author = {Acerbi, Carlo and Sz{\\'e}kely, Bal{\\'a}zs},\n  title = {Back-testing Expected Shortfall},\n"
        "  journal = {Risk},\n  year = {2014},\n  month = dec,\n"
        "  url = {https://www.risk.net/risk-management/2381658/back-testing-expected-shortfall}\n}\n"),
}


def override(raw: str, fields: dict) -> str:
    """Replace or add the given fields of one BibTeX entry (balanced braces)."""
    for name, value in fields.items():
        if name == "@type":
            raw = re.sub(r"^\s*@\w+", "@" + value, raw.strip(), count=1) + "\n"
            continue
        m = re.search(r"(?<![A-Za-z])" + name + r"\s*=\s*\{", raw, re.I)
        if m:
            depth, i = 1, m.end()
            while depth:
                depth += {"{": 1, "}": -1}.get(raw[i], 0)
                i += 1
            raw = raw[:m.start()] + f"{name}={{{value}}}" + raw[i:]
        else:
            k = raw.rstrip().rfind("}")
            raw = raw[:k].rstrip().rstrip(",") + f",\n  {name} = {{{value}}}\n}}\n"
    return raw


def clean(text: str) -> str:
    return (text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2019", "'").replace("&amp;", "\\&").replace("\u2013", "--")
            .replace("\u00a0", " "))


def crossref_entry(key: str, doi: str) -> str:
    import json

    m = json.loads(get("https://api.crossref.org/works/" + doi).decode("utf-8"))["message"]
    authors = " and ".join(f"{a.get('family', '')}, {a.get('given', '')}" for a in m.get("author", []))
    year = m["issued"]["date-parts"][0][0]
    fields = [("author", authors), ("title", clean(m["title"][0])), ("journal", clean((m.get("container-title") or [""])[0])),
              ("year", str(year)), ("volume", m.get("volume", "")), ("number", m.get("issue", "")), ("pages", clean(m.get("page", "")).replace("-", "--")),
              ("doi", doi), ("url", "https://doi.org/" + doi)]
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v)
    return f"@article{{{key},\n{body}\n}}"


def cited() -> set[str]:
    keys: set[str] = set()
    files = [HERE / "main.tex", *sorted((HERE / "sections").glob("*.tex"))]
    for f in files:
        for m in re.finditer(r"\\cite[a-z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}", f.read_text(encoding="utf-8")):
            keys.update(k.strip() for k in m.group(1).split(","))
    return keys


def entry(key: str, kind: str, ident: str, words: str) -> str:
    if kind == "manual":
        return MANUAL[key]
    if kind == "doi":
        raw = clean(get("https://doi.org/" + ident, "application/x-bibtex").decode("utf-8"))
        title = re.search(r"[,{ ]title\s*=\s*\{(.+?)\}\s*[,}]", raw, re.S)
        if not title:                                   # a publisher record without a title: use the Crossref record of the same DOI
            raw = crossref_entry(key, ident)
            title = re.search(r"title\s*=\s*\{(.+?)\}\s*,", raw, re.S)
        if words and (not title or words.lower() not in title.group(1).lower()):
            raise RuntimeError(f"{key}: the record {ident} has title {title.group(1) if title else raw[:80]!r}, expected words {words!r}")
        raw = re.sub(r"^\s*@(\w+)\{[^,]*,", lambda m: f"@{m.group(1)}{{{key},", raw.strip(), count=1)
        return raw + "\n"
    if kind == "arxiv":
        xml = get("http://export.arxiv.org/api/query?id_list=" + ident).decode("utf-8")
        ns = {"a": "http://www.w3.org/2005/Atom"}
        e = ET.fromstring(xml).find("a:entry", ns)
        title = " ".join(e.find("a:title", ns).text.split())
        if words.lower() not in title.lower():
            raise RuntimeError(f"{key}: arXiv {ident} has title {title!r}, expected words {words!r}")
        authors = " and ".join(a.find("a:name", ns).text for a in e.findall("a:author", ns))
        year = e.find("a:published", ns).text[:4]
        return (f"@misc{{{key},\n  author = {{{authors}}},\n  title = {{{title}}},\n  year = {{{year}}},\n  eprint = {{{ident}}},\n"
                f"  archivePrefix = {{arXiv}},\n  url = {{https://arxiv.org/abs/{ident}}}\n}}\n")
    title, author, year = words.split("|")
    code = urllib.request.urlopen(urllib.request.Request(ident, headers={"User-Agent": "Mozilla/5.0"}), timeout=40).status
    if code != 200:
        raise RuntimeError(f"{key}: {ident} answered {code}")
    return f"@misc{{{key},\n  author = {{{{{author}}}}},\n  title = {{{title}}},\n  year = {{{year}}},\n  url = {{{ident}}}\n}}\n"


def main() -> int:
    keys = cited()
    missing = sorted(keys - set(WORKS))
    if missing:
        print("cited but not listed:", missing)
        return 1
    out = ["% The works this manuscript cites, written by fetch_references.py from the publishers' records (DOI), the arXiv API and the Basel Committee's pages.\n"]
    for key in sorted(keys):
        out.append(override(entry(key, *WORKS[key]), OVERRIDES.get(key, {})))
    (HERE / "references.bib").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote references.bib with {len(keys)} works; listed but not cited: {sorted(set(WORKS) - keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
