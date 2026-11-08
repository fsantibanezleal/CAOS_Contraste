"""Rebuilds ``references.bib``: every journal or book record is fetched from https://doi.org/<doi> with the header
``Accept: application/x-bibtex`` (the Crossref record), and the fields are rewritten as BibTeX with the title protected from case
changes. The works without a DOI are listed at the end with the stable URL that was opened. Needs network access.

    python manuscripts/dependence-band-with-every-aggregate/fetch_references.py
"""
from __future__ import annotations

import html
import pathlib
import re
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent

DOIS = {
    "rosenberg2006": "10.1016/j.jfineco.2005.03.001",
    "epr2013": "10.1016/j.jbankfin.2013.03.014",
    "ems2002": "10.1017/CBO9780511615337.008",
    "kuritzkes2003": "10.1353/pfs.2003.0005",
    "barrieu2015": "10.1016/j.ejor.2014.10.032",
    "glasserman2014": "10.1080/14697688.2013.822989",
    "acerbi2002": "10.1016/S0378-4266(02)00283-2",
    "demarta2005": "10.1111/j.1751-5823.2005.tb00254.x",
    "li2000": "10.3905/jfi.2000.319253",
    "frey2003": "10.21314/jor.2003.089",
    "puccetti2012": "10.1016/j.cam.2011.10.015",
    "ewang2015": "10.1007/s00780-015-0273-z",
    "wpy2013": "10.1007/s00780-012-0200-5",
    "artzner1999": "10.1111/1467-9965.00068",
    "aas2009": "10.1016/j.insmatheco.2007.02.001",
    "elw2008": "10.1007/s10687-008-0071-5",
    "bjw2014": "10.1016/j.insmatheco.2013.11.005",
    "brv2015": "10.1111/jori.12108",
    "danielsson2013": "10.1016/j.jeconom.2012.08.011",
    "cont2006": "10.1111/j.1467-9965.2006.00281.x",
    "kerkhof2010": "10.1016/j.jbankfin.2009.07.025",
    "brockmann2010": "10.21314/jor.2010.208",
    "boucher2014": "10.1016/j.jbankfin.2014.03.019",
    "dimakos2004": "10.1191/1471082x04st079oa",
    "ruschendorf1982": "10.2307/1426677",
    "makarov1981": "10.1137/1126086",
    "academic2014": "10.3390/risks2010025",
    "worstvar2005": "10.1016/j.insmatheco.2005.01.006",
    "pww2013": "10.1016/j.insmatheco.2013.09.017",
    "lindskog2003": "10.1007/978-3-642-59365-9_8",
    "glasserman2003": "10.1007/978-0-387-21617-1",
    "ruschendorf2013": "10.1007/978-3-642-33590-7",
    "hofert2020": "10.3390/risks8020047",
    "aas2007": "10.1057/palgrave.rm.8250027",
    "elm2003": "10.1016/b978-044450896-6.50010-8",
}

MANUAL = """
@misc{tasche2008,
  title = {{Capital allocation to business units and sub-portfolios: the Euler principle}},
  author = {Tasche, Dirk},
  year = {2008}, howpublished = {arXiv:0708.2542},
  url = {https://arxiv.org/abs/0708.2542}
}

@misc{hofert2015,
  title = {{Improved algorithms for computing worst Value-at-Risk: numerical challenges and the adaptive rearrangement algorithm}},
  author = {Hofert, Marius and Memartoluie, Amir and Saunders, David and Wirjanto, Tony},
  year = {2015}, howpublished = {arXiv:1505.02281},
  url = {https://arxiv.org/abs/1505.02281}
}

@misc{alexander2004,
  title = {{On the aggregation of firm-wide market and credit risks}},
  author = {Alexander, Carol and Pezier, Jacques},
  year = {2004}, howpublished = {SSRN working paper 478381},
  doi = {10.2139/ssrn.478381}, url = {https://doi.org/10.2139/ssrn.478381}
}

@techreport{jointforum2010,
  title = {{Developments in modelling risk aggregation}},
  author = {{Joint Forum}},
  institution = {Bank for International Settlements}, year = {2010},
  url = {https://www.bis.org/publ/joint25.pdf}
}

@techreport{bcbs2009,
  title = {{Range of practices and issues in economic capital frameworks}},
  author = {{Basel Committee on Banking Supervision}},
  institution = {Bank for International Settlements}, year = {2009},
  url = {https://www.bis.org/publ/bcbs152.htm}
}
"""


def fetch(doi: str) -> str:
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://doi.org/" + doi, headers={"Accept": "application/x-bibtex"})
            return html.unescape(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"no record for {doi}")


def field(text: str, name: str) -> str:
    m = re.search(name + r"\s*=\s*\{(.*?)\}\s*(,|\})", text, re.S | re.I)
    return m.group(1).strip() if m else ""


def clean(s: str) -> str:
    s = s.replace("‐", "-").replace("‑", "-").replace("–", "--").replace("—", "-").replace("’", "'")
    s = s.replace("‘", "'").replace("&", "\\&")
    return re.sub(r"\s+", " ", s)


def main() -> None:
    out = ["% The works this manuscript cites. Journal and book records fetched from https://doi.org/<doi> with the header",
           "% Accept: application/x-bibtex; the five works without a journal record carry the URL that was opened.", ""]
    for key, doi in DOIS.items():
        t = fetch(doi)
        kind = re.search(r"@(\w+)", t).group(1).lower()
        kind = "incollection" if kind == "inbook" else kind
        title, author = clean(field(t, "title")), clean(field(t, "author"))
        journal = clean(field(t, "journal") or field(t, "booktitle"))
        lines = [f"@{kind}{{{key},", f"  title = {{{{{title}}}}},", f"  author = {{{author}}},"]
        if kind == "article":
            lines.append(f"  journal = {{{journal}}},")
        elif kind in ("incollection", "inproceedings", "inbook") and journal:
            lines.append(f"  booktitle = {{{journal}}},")
        for f in ("volume", "number", "pages", "year", "publisher"):
            v = clean(field(t, f))
            if v:
                lines.append(f"  {f} = {{{v}}},")
        lines.append(f"  doi = {{{doi}}}, url = {{https://doi.org/{doi}}}")
        lines.append("}")
        out.append("\n".join(lines))
        out.append("")
        print("ok", key, flush=True)
        time.sleep(0.5)
    out.append(MANUAL.strip())
    (HERE / "references.bib").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
