"""Write ``references.bib`` from the records of the works the text cites.

    python manuscripts/provisions-reconciliation-identities/fetch_references.py

Every cited key of ``main.tex`` and ``sections/*.tex`` is looked up in ``WORKS`` below. A work with a DOI is fetched from
``https://doi.org/<doi>`` with ``Accept: application/x-bibtex`` (the publisher's own record, through the DOI resolver), with the
Crossref record of the same DOI as the fallback; a preprint is fetched from the arXiv API; a standard, a supervisory text or a
dataset page is written with its stable URL, checked to answer 200, and the title of the page it answers is printed so that it
can be compared with the title written here. The script refuses a key that is cited and not listed, and a record whose title does
not carry the expected words.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent

#: key -> (kind, identifier, words the fetched title must contain, or for a url: title|author|year)
WORKS = {
    # standards, supervisory texts and datasets (stable URLs)
    "ifrs9eu": ("url", "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32016R2067",
                "Commission Regulation (EU) 2016/2067 of 22 November 2016 amending Regulation (EC) No 1126/2008 as regards International Financial Reporting Standard 9, "
                "with the amendments to IFRS 7|European Commission|2016"),
    "bcbsd350": ("url", "https://www.bis.org/bcbs/publ/d350.htm",
                 "Guidance on credit risk and accounting for expected credit losses|Basel Committee on Banking Supervision|2015"),
    "bcbs2005": ("url", "https://www.bis.org/bcbs/irbriskweight.htm",
                 "An explanatory note on the Basel II IRB risk weight functions|Basel Committee on Banking Supervision|2005"),
    "gppc2016": ("url", "https://www.globalpublicpolicycommittee.org/wp-content/uploads/2022/12/gppc-ifrs9-implementation-considerations-20160617.pdf",
                 "The implementation of IFRS 9 impairment requirements by banks: considerations for those charged with governance of systemically important banks|"
                 "Global Public Policy Committee|2016"),
    "ecb2024": ("url", "https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.IFRS9novelrisks_202407~5e0eb30b5c.en.pdf",
                "IFRS 9 overlays and model improvements for novel risks: identifying best practices for capturing novel risks in loan loss provisions|"
                "European Central Bank, Banking Supervision|2024"),
    "eba2021": ("url", "https://www.eba.europa.eu/sites/default/files/document_library/Publications/Reports/2021/1024609/IFRS9%20monitoring%20report.pdf",
                "IFRS 9 implementation by EU institutions: monitoring report, EBA/Rep/2021/35|European Banking Authority|2021"),
    "eba2023": ("url", "https://www.eba.europa.eu/sites/default/files/2023-11/25b12d35-9c28-4335-a589-166c77198920/Final%20Report%20on%20IFRS9%20implementation%20by%20EU%20institutions.pdf",
                "IFRS 9 implementation by EU institutions: 2023 monitoring report, EBA/Rep/2023/36|European Banking Authority|2023"),
    "cmfcncb": ("url", "https://www.cmfchile.cl/portal/normativa/624/articles-29177_doc_pdf.pdf",
                "Compendio de Normas Contables para Bancos, chapters A-2 and B-1|Comisi{\\'o}n para el Mercado Financiero de Chile|2022"),
    "boe2017": ("url", "https://www.boe.es/buscar/doc.php?id=BOE-A-2017-14334",
                "Circular 4/2017, de 27 de noviembre, del Banco de Espa{\\~n}a, a entidades de cr{\\'e}dito, sobre normas de informaci{\\'o}n financiera p{\\'u}blica y reservada y modelos de estados financieros|Banco de Espa{\\~n}a|2017"),
    "boe2021": ("url", "https://www.boe.es/buscar/doc.php?id=BOE-A-2021-21666",
                "Circular 6/2021, de 22 de diciembre, por la que se modifica la Circular 4/2017|Banco de Espa{\\~n}a|2021"),
    "sr117": ("url", "https://www.federalreserve.gov/boarddocs/srletters/2011/sr1107.htm",
              "Supervisory guidance on model risk management, SR 11-7|Board of Governors of the Federal Reserve System|2011"),
    "cohenedwards2017": ("url", "https://www.bis.org/publ/qtrpdf/r_qt1703f.htm",
                         "The new era of expected credit loss provisioning|Cohen, Benjamin H. and Edwards, Jr., Gerald A.|2017|BIS Quarterly Review, March 2017"),
    "sba7a": ("url", "https://data.sba.gov/sites/default/files/uploaded_resources/7a_504_foia_data_dictionary.xlsx",
              "7(a) and 504 FOIA loan data, data dictionary of the quarterly release|U.S. Small Business Administration|2026"),
    # credit loss modelling under IFRS 9
    "bellini2019": ("doi", "10.1016/C2017-0-02756-8", "IFRS 9 and CECL"),
    "skoglund2017": ("doi", "10.69554/ICHC6682", "term-structures"),
    "miuozdemir2017": ("doi", "10.21314/JCR.2017.224", "Basel II"),
    "kruger2018": ("doi", "10.1016/j.jfs.2018.02.009", "loan loss provisioning"),
    "novotny2016": ("doi", "10.1080/17449480.2016.1210180", "expected loss"),
    "breeden2016": ("doi", "10.1016/j.ejor.2016.06.008", "lifecycle"),
    "cox1972": ("doi", "10.1111/j.2517-6161.1972.tb00899.x", "regression models"),
    "bothaverster2025": ("arxiv", "2507.15441", "term-structure"),
    "bothasicr2025": ("doi", "10.1007/s10479-025-06546-3", "SICR"),
    "perederiy2015": ("arxiv", "1507.05415", "lifetime pd"),
    # one-factor model and convexity
    "gordy2003": ("doi", "10.1016/S1042-9573(03)00040-8", "risk-factor model"),
    "merton1974": ("doi", "10.1111/j.1540-6261.1974.tb03058.x", "pricing of corporate debt"),
    "jensen1906": ("doi", "10.1007/BF02418571", "fonctions convexes"),
    "golubwelsch1969": ("doi", "10.1090/S0025-5718-69-99647-1", "Gauss quadrature"),
    # testing of software and of error detection
    "demillo1978": ("doi", "10.1109/C-M.1978.218136", "test data selection"),
    "jia2011": ("doi", "10.1109/TSE.2010.62", "mutation testing"),
    "chen2018": ("doi", "10.1145/3143561", "metamorphic testing"),
    "segura2016": ("doi", "10.1109/TSE.2016.2532875", "metamorphic testing"),
    "claessen2000": ("doi", "10.1145/351240.351266", "quickcheck"),
    "hamming1950": ("doi", "10.1002/j.1538-7305.1950.tb00463.x", "error detecting"),
    # statistics
    "wilson1927": ("doi", "10.1080/01621459.1927.10502953", "probable inference"),
    "brown2001": ("doi", "10.1214/ss/1009213286", "binomial"),
    "efron1979": ("doi", "10.1214/aos/1176344552", "bootstrap"),
    "morris2019": ("doi", "10.1002/sim.8086", "simulation studies"),
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
            .replace("\u00a0", " "))


def crossref_entry(key: str, doi: str) -> str:
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
        try:
            raw = clean(get("https://doi.org/" + ident, "application/x-bibtex").decode("utf-8"))
        except RuntimeError:
            raw = crossref_entry(key, ident)
        title = re.search(r"[,{ ]title\s*=\s*\{(.+?)\}\s*[,}]", raw, re.S)
        if not title:                                   # a publisher record without a title: use the Crossref record of the same DOI
            raw = crossref_entry(key, ident)
            title = re.search(r"title\s*=\s*\{(.+?)\}\s*,", raw, re.S)
        if words and (not title or words.lower() not in title.group(1).lower()):
            raise RuntimeError(f"{key}: the record {ident} has title {title.group(1) if title else raw[:80]!r}, expected words {words!r}")
        print(f"{key:20s} {title.group(1)[:90] if title else ''}")
        if key == "bellini2019":
            raw = re.sub(r"(title\s*=)", "author = {Bellini, Tiziano},\n  publisher = {Academic Press},\n  \\1", raw, count=1)  # the book record carries no author
        raw = re.sub(r"^\s*@(\w+)\{[^,]*,", lambda m: f"@{'book' if key == 'bellini2019' else m.group(1)}{{{key},", raw.strip(), count=1)  # a book is not an article
        return raw + "\n"
    if kind == "arxiv":
        xml = get("http://export.arxiv.org/api/query?id_list=" + ident).decode("utf-8")
        ns = {"a": "http://www.w3.org/2005/Atom"}
        e = ET.fromstring(xml).find("a:entry", ns)
        title = " ".join(e.find("a:title", ns).text.split())
        if words.lower() not in title.lower():
            raise RuntimeError(f"{key}: arXiv {ident} has title {title!r}, expected words {words!r}")
        print(f"{key:20s} {title[:90]}")
        authors = " and ".join(a.find("a:name", ns).text for a in e.findall("a:author", ns))
        year = e.find("a:published", ns).text[:4]
        return (f"@misc{{{key},\n  author = {{{authors}}},\n  title = {{{title}}},\n  year = {{{year}}},\n  eprint = {{{ident}}},\n"
                f"  archivePrefix = {{arXiv}},\n  url = {{https://arxiv.org/abs/{ident}}}\n}}\n")
    title, author, year, *venue = words.split("|")
    req = urllib.request.Request(ident, headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=40)
    if resp.status != 200:
        raise RuntimeError(f"{key}: {ident} answered {resp.status}")
    page = resp.read(200000).decode("utf-8", errors="replace")
    seen = re.search(r"<title[^>]*>(.*?)</title>", page, re.S | re.I)
    print(f"{key:20s} url 200; page title: {' '.join(seen.group(1).split())[:100] if seen else '(a document without a title element)'}")
    names = f"{{{author}}}" if " and " in author else f"{{{{{author}}}}}"  # persons are listed one by one, a corporate author in double braces
    where = f"  howpublished = {{{venue[0]}}},\n" if venue else ""
    return f"@misc{{{key},\n  author = {names},\n  title = {{{title}}},\n{where}  year = {{{year}}},\n  url = {{{ident}}}\n}}\n"


def main() -> int:
    keys = cited() if "--all" not in sys.argv else set(WORKS)
    missing = sorted(keys - set(WORKS))
    if missing:
        print("cited but not listed:", missing)
        return 1
    out = ["% The works this manuscript cites, written by fetch_references.py from the publishers' records (DOI), the arXiv API and the pages of the standards.\n"]
    for key in sorted(keys):
        out.append(entry(key, *WORKS[key]))
    target = HERE / ("references.all.check" if "--all" in sys.argv else "references.bib")
    target.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote {target.name} with {len(keys)} works; listed but not cited: {sorted(set(WORKS) - keys)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
