"""Write ``references.bib`` from the records of the works the text cites.

    python manuscripts/reverse-liquidity-stress-with-a-refusal-rule/fetch_references.py

Every cited key of ``main.tex`` and ``sections/*.tex`` is looked up in ``WORKS`` below. A work with a DOI is fetched from
``https://doi.org/<doi>`` with ``Accept: application/x-bibtex`` (the publisher's own record, with the Crossref record as the
fallback when it carries no title); a document with a stable address is written with that address, checked to answer 200.
The script refuses a key that is cited and not listed, and a record that does not carry the expected title words.
"""
from __future__ import annotations

import pathlib
import re
import sys
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent

#: key -> (kind, identifier, words the fetched title must contain)
WORKS = {
    "diamond1983": ("doi", "10.1086/261155", "bank runs"),
    "goldsteinpauzner2005": ("doi", "10.1111/j.1540-6261.2005.00762.x", "probability of bank runs"),
    "brunnermeierpedersen2009": ("doi", "10.1093/rfs/hhn098", "market liquidity"),
    "drehmannnikolaou2013": ("doi", "10.1016/j.jbankfin.2012.01.002", "funding liquidity"),
    "iyerpuri2012": ("doi", "10.1257/aer.102.4.1414", "bank runs"),
    "acharyamora2015": ("doi", "10.1111/jofi.12182", "liquidity providers"),
    "gortonmetrick2012": ("doi", "10.1016/j.jfineco.2011.03.016", "repo"),
    "tirole2011": ("doi", "10.1257/jel.49.2.287", "illiquidity"),
    "jiang2024": ("doi", "10.1016/j.jfineco.2024.103899", "monetary tightening"),
    "cookson2026": ("doi", "10.1016/j.jfineco.2025.104218", "social media"),
    "cipriani2024": ("doi", "10.59576/sr.1104", "tracing bank runs"),
    "drechsler2023": ("doi", "10.3386/w31138", "deposit franchise"),
    "glasserman2015": ("doi", "10.1080/14697688.2014.926019", "stress scenario selection"),
    "flood2015": ("doi", "10.1080/14697688.2014.926018", "scenario selection"),
    "breuercsiszar2013": ("doi", "10.1016/j.jbankfin.2012.04.013", "entropic"),
    "mcneilsmith2012": ("doi", "10.1016/j.insmatheco.2011.12.005", "multivariate stress"),
    "grundke2018": ("doi", "10.1007/s11156-017-0655-8", "reverse stress"),
    "almehed2021": ("doi", "10.1515/9783110647907-006", "reverse liquidity"),
    "gann2021": ("doi", "10.1515/9783110647907-002", "reverse stress testing"),
    "bellini2017": ("doi", "10.1016/b978-0-12-803590-0.00008-4", "reverse stress"),
    "vandenend2009": ("doi", "10.1093/cesifo/ifp005", "stress-tester"),
    "puhr2012": ("doi", "10.5089/9781475502466.001", "liquidity stress testing"),
    "cont2020": ("doi", "10.1016/j.jbankfin.2020.105871", "liquidity at risk"),
    "borio2014": ("doi", "10.1016/j.jfs.2013.06.001", "macro stress testing"),
    "schuermann2014": ("doi", "10.1016/j.ijforecast.2013.10.003", "stress testing banks"),
    "virtanen2020": ("doi", "10.1038/s41592-019-0686-2", "scipy"),
    "efron1979": ("doi", "10.1214/aos/1176344552", "bootstrap"),
    "brown2001": ("doi", "10.1214/ss/1009213286", "binomial"),
    "morris2019": ("doi", "10.1002/sim.8086", "simulation studies"),
    "bcbs144": ("url", "https://www.bis.org/publ/bcbs144.htm",
                "Principles for sound liquidity risk management and supervision|Basel Committee on Banking Supervision|2008"),
    "bcbs155": ("url", "https://www.bis.org/publ/bcbs155.htm",
                "Principles for sound stress testing practices and supervision|Basel Committee on Banking Supervision|2009"),
    "bcbs238": ("url", "https://www.bis.org/publ/bcbs238.htm",
                "Basel III: The liquidity coverage ratio and liquidity risk monitoring tools|Basel Committee on Banking Supervision|2013"),
    "bcbs295": ("url", "https://www.bis.org/bcbs/publ/d295.htm",
                "Basel III: the net stable funding ratio|Basel Committee on Banking Supervision|2014"),
    "bcbs555": ("url", "https://www.bis.org/bcbs/publ/d555.htm",
                "Report on the 2023 banking turmoil|Basel Committee on Banking Supervision|2023"),
    "ecblist2019": ("url", "https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.ECB_sensitivity_analysis_of_liquidity_risk-stress_test_2019-"
                           "methodological_note_20190206~6771e88926.en.pdf",
                    "Sensitivity analysis of liquidity risk, stress test 2019, methodological note|European Central Bank, Banking Supervision|2019"),
    "ecbannex2019": ("url", "https://www.bankingsupervision.europa.eu/press/pr/date/2019/html/ssm.pr191007_annex~537c259b6d.en.pdf",
                     "Sensitivity analysis of liquidity risk, stress test 2019, final results annex|European Central Bank, Banking Supervision|2019"),
    "fedsvb2023": ("url", "https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf",
                   "Review of the Federal Reserve's supervision and regulation of Silicon Valley Bank|Board of Governors of the Federal Reserve System|2023"),
    "scipybrentq": ("url", "https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html",
                    "scipy.optimize.brentq, SciPy reference guide|The SciPy community|2025"),
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


def clean(text: str) -> str:
    return (text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2019", "'").replace("&amp;", "\\&").replace("\u2013", "--")
            .replace("\u00a0", " ").replace("\u2014", "--"))


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
    if kind == "doi":
        raw = clean(get("https://doi.org/" + ident, "application/x-bibtex").decode("utf-8"))
        raw = re.sub(r"month=(\w{3})\w*", lambda m: "month=" + m.group(1).lower(), raw)  # plainnat knows jan..dec, not june or sept
        title = re.search(r"[,{ ]title\s*=\s*\{(.+?)\}\s*[,}]", raw, re.S)
        if not title:                                   # a publisher record without a title: use the Crossref record of the same DOI
            raw = crossref_entry(key, ident)
            title = re.search(r"title\s*=\s*\{(.+?)\}\s*,", raw, re.S)
        if words and (not title or words.lower() not in title.group(1).lower()):
            raise RuntimeError(f"{key}: the record {ident} has title {title.group(1) if title else raw[:80]!r}, expected words {words!r}")
        raw = re.sub(r"^\s*@(\w+)\{[^,]*,", lambda m: f"@{m.group(1)}{{{key},", raw.strip(), count=1)
        return raw + "\n"
    title, author, year = words.split("|")
    code = urllib.request.urlopen(urllib.request.Request(ident, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).status
    if code != 200:
        raise RuntimeError(f"{key}: {ident} answered {code}")
    return f"@misc{{{key},\n  author = {{{{{author}}}}},\n  title = {{{title}}},\n  year = {{{year}}},\n  url = {{{ident}}}\n}}\n"


def main() -> int:
    keys = cited()
    missing = sorted(keys - set(WORKS))
    if missing:
        print("cited but not listed:", missing)
        return 1
    out = ["% The works this manuscript cites, written by fetch_references.py from the publishers' records (DOI) and the stable addresses of the documents.\n"]
    for key in sorted(keys):
        out.append(entry(key, *WORKS[key]))
    (HERE / "references.bib").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote references.bib with {len(keys)} works; listed but not cited: {sorted(set(WORKS) - keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
