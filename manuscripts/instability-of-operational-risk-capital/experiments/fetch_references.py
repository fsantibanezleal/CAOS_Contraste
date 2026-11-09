"""Write ``references.bib`` from the records of the cited works.

Every entry with a DOI is the BibTeX that ``https://doi.org/<doi>`` returns for ``Accept: application/x-bibtex``, with the key
replaced by the key the manuscript cites; an entry without a DOI is a document at a stable URL, fetched (HTTP status 200) and
written from the title and the publisher the page states. The script prints what it fetched and exits non-zero on any failure, so a
reference whose record cannot be fetched is not cited.

Run from the repository root::

    python manuscripts/instability-of-operational-risk-capital/experiments/fetch_references.py
"""
from __future__ import annotations

import pathlib
import re
import sys
import time
import unicodedata
import urllib.request

OUT = pathlib.Path(__file__).resolve().parents[1] / "references.bib"

#: key -> DOI of the cited work
DOIS: dict[str, str] = {
    "shevchenko2010": "10.21314/JOP.2010.077",
    "panjer1981": "10.1017/S0515036100006796",
    "chavez2006": "10.1016/j.jbankfin.2005.11.008",
    "mignola2007": "10.21314/JOP.2006.019",
    "cope2009": "10.21314/JOP.2009.069",
    "degen2010": "10.21314/JOP.2010.084",
    "shevchenko2006": "10.21314/JOP.2006.016",
    "shevchenko2011": "10.1007/978-3-642-15923-7",
    "mignola2016": "10.21314/JOP.2016.184",
    "peters2016": "10.21314/jop.2016.177",
    "embrechts1997": "10.1007/978-3-642-33483-2",
    "hampel1986": "10.1002/9781118186435",
    "grimshaw1993": "10.1080/00401706.1993.10485040",
    "opdyke2012": "10.21314/jop.2012.111",
    "neslehova2006": "10.21314/JOP.2006.001",
    "pickands1975": "10.1214/aos/1176343003",
    "balkema1974": "10.1214/aop/1176996548",
    "hill1975": "10.1214/aos/1176343247",
    "smith1987": "10.1214/aos/1176350499",
    "hosking1987": "10.1080/00401706.1987.10488243",
    "davison1990": "10.1111/j.2517-6161.1990.tb01796.x",
    "efron1979": "10.1214/aos/1176344552",
    "wilson1927": "10.1080/01621459.1927.10502953",
    "dehaan2006": "10.1007/0-387-34471-3",
    "drees2004": "10.1214/105051604000000279",
    "embrechts1999": "10.1080/10920277.1999.10595797",
    "zhang2009": "10.1198/tech.2009.08017",
    "cruz2015": "10.1002/9781118573013",
    "embrechts2014": "10.1146/annurev-statistics-022513-115631",
    "hyndman1996": "10.1080/00031305.1996.10473566",
    "morris2019": "10.1002/sim.8086",
    "diciccio1996": "10.1214/ss/1032280214",
    "danielsson2002": "10.1016/S0378-4266(02)00263-7",
    "huber2009": "10.1002/9780470434697",
}

#: documents with a stable URL and no DOI: key -> (type, author, title, year, publisher or note, url)
URLS: dict[str, tuple[str, str, str, str, str, str]] = {
    "bcbs160": ("techreport", "{Basel Committee on Banking Supervision}", "Results from the 2008 Loss Data Collection Exercise for Operational Risk",
                "2009", "Bank for International Settlements", "https://www.bis.org/publ/bcbs160.htm"),
    "bcbs196": ("techreport", "{Basel Committee on Banking Supervision}", "Operational Risk: Supervisory Guidelines for the Advanced Measurement Approaches",
                "2011", "Bank for International Settlements", "https://www.bis.org/publ/bcbs196.htm"),
    "bcbsd355": ("techreport", "{Basel Committee on Banking Supervision}", "Standardised Measurement Approach for operational risk",
                 "2016", "Bank for International Settlements", "https://www.bis.org/bcbs/publ/d355.htm"),
    "bcbsd424": ("techreport", "{Basel Committee on Banking Supervision}", "Basel III: Finalising post-crisis reforms",
                 "2017", "Bank for International Settlements", "https://www.bis.org/bcbs/publ/d424.htm"),
    "ope25": ("misc", "{Basel Committee on Banking Supervision}", "Basel Framework, OPE25: Standardised approach",
              "2023", "Bank for International Settlements", "https://www.bis.org/basel_framework/chapter/OPE/25.htm"),
    "peters2013": ("misc", "Peters, Gareth W. and Targino, Rodrigo S. and Shevchenko, Pavel V.", "Understanding operational risk capital approximations: first and second orders",
                   "2013", "arXiv:1303.2910", "https://arxiv.org/abs/1303.2910"),
}


def get(url: str, accept: str | None = None, retries: int = 3) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": accept or "text/html", "User-Agent": "contraste-manuscript-references/1.0 (mailto:fsantibanez@gmail.com)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (attempt + 1))
    raise SystemExit(f"cannot fetch {url}: {last}")


def main() -> int:
    chunks = ["% The works this manuscript cites. A DOI entry is the BibTeX returned by https://doi.org/<doi> (Accept: application/x-bibtex)",
              "% with the key replaced by the key the text cites; a URL entry is a document fetched at its stable URL.\n"]
    for key, doi in DOIS.items():
        status, text = get(f"https://doi.org/{doi}", "application/x-bibtex")
        text = text.strip()
        if status != 200 or not text.startswith("@"):
            raise SystemExit(f"{key}: no BibTeX record for {doi}")
        text = re.sub(r"^(@\w+)\{[^,]*,", lambda m: f"{m.group(1)}{{{key},", text, count=1)
        text = text.replace("\n", "\n").replace("&amp;", "\\&")
        chunks.append(text + "\n")
        print(f"{key}: {doi}: {re.search(r'title *= *[{]+([^}]*)', text, re.I).group(1)[:90] if re.search(r'title *=', text, re.I) else '?'}")
    for key, (kind, author, title, year, publisher, url) in URLS.items():
        status, page = get(url)
        if status != 200:
            raise SystemExit(f"{key}: {url} answered {status}")
        words = [w for w in re.findall(r"[A-Za-z]{5,}", title)][:2]
        if not all(w.lower() in page.lower() for w in words):
            raise SystemExit(f"{key}: the page at {url} does not carry the title words {words}")
        field = "institution" if kind == "techreport" else "howpublished"
        chunks.append(f"@{kind}{{{key},\n  author = {{{author}}},\n  title = {{{title}}},\n  year = {{{year}}},\n  {field} = {{{publisher}}},\n  url = {{{url}}}\n}}\n")
        print(f"{key}: {url}: HTTP {status}, the page carries the title")
    # one record writes i with an acute accent as a dotless i and a combining accent, which pdflatex does not set up
    text = unicodedata.normalize("NFC", "\n".join(chunks).replace("ı́", "í"))
    months = {"jan": "January", "feb": "February", "mar": "March", "apr": "April", "may": "May", "jun": "June", "june": "June", "jul": "July", "july": "July",
              "aug": "August", "sep": "September", "sept": "September", "oct": "October", "nov": "November", "dec": "December"}
    text = re.sub(r"month\s*=\s*([A-Za-z]+)", lambda m: "month={" + months.get(m.group(1).lower(), m.group(1)) + "}", text)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.name}: {len(DOIS) + len(URLS)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
