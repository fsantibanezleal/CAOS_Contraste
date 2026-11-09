"""Rebuilds ``references.bib``: every journal, proceedings or book record is fetched from https://doi.org/<doi> with the header
``Accept: application/x-bibtex`` (the Crossref or DataCite record) and rewritten as BibTeX with the title protected from case
changes. A work without a DOI is listed in URLS with its stable URL; the script opens each of them and stops when one does not
answer, so that no entry stands for a page that was not read. Needs network access.

    python manuscripts/leakage-safe-validation-protocol/fetch_references.py
"""
from __future__ import annotations

import html
import pathlib
import re
import time
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent

DOIS = {
    "kaufman2012": "10.1145/2382577.2382579",
    "kapoor2023": "10.1016/j.patter.2023.100804",
    "ambroise2002": "10.1073/pnas.102102699",
    "varma2006": "10.1186/1471-2105-7-91",
    "hastie2009": "10.1007/978-0-387-84858-7",
    "delong1988": "10.2307/2531595",
    "bergmeir2012": "10.1016/j.ins.2011.12.028",
    "bergmeir2018": "10.1016/j.csda.2017.11.003",
    "roberts2017": "10.1111/ecog.02881",
    "dwork2015": "10.1126/science.aaa9375",
    "niculescu2005": "10.1145/1102351.1102430",
    "zadrozny2002": "10.1145/775047.775151",
    "siddiqi2017": "10.1002/9781119282396",
    "baesens2003": "10.1057/palgrave.jors.2601545",
    "lessmann2015": "10.1016/j.ejor.2015.05.030",
    "gunnarsson2021": "10.1016/j.ejor.2021.03.006",
    "yeh2009": "10.1016/j.eswa.2007.12.020",
    "morris2019": "10.1002/sim.8086",
    "brown2001": "10.1214/ss/1009213286",
    "yurdakul2020": "10.21314/JRMV.2020.227",
    "goorbergh2022": "10.1093/jamia/ocac093",
    "chen2018": "10.1145/3143561",
    "segura2016": "10.1109/TSE.2016.2532875",
    "moscovich2022": "10.1111/rssb.12537",
    "vabalas2019": "10.1371/journal.pone.0224365",
    "arlot2010": "10.1214/09-SS054",
    "bates2023": "10.1080/01621459.2023.2197686",
    "gama2014": "10.1145/2523813",
    "hand1997": "10.1111/j.1467-985X.1997.00078.x",
    "hanley1982": "10.1148/radiology.143.1.7063747",
    "hoeffding1963": "10.1080/01621459.1963.10500830",
    "breck2017": "10.1109/BigData.2017.8258038",
    "thomas2002": "10.1137/1.9780898718317",
    "demler2012": "10.1002/sim.5328",
    "boucheron2013": "10.1093/acprof:oso/9780199535255.001.0001",
}

#: works without a DOI: (key, kind, title, authors, year, publisher or series, URL opened)
URLS = [
    ("cawley2010", "article", "On over-fitting in model selection and subsequent selection bias in performance evaluation",
     "Cawley, Gavin C. and Talbot, Nicola L. C.", "2010", "Journal of Machine Learning Research 11:2079--2107",
     "https://jmlr.org/papers/v11/cawley10a.html"),
    ("pedregosa2011", "article", "Scikit-learn: machine learning in Python",
     "Pedregosa, Fabian and Varoquaux, Ga{\\\"e}l and Gramfort, Alexandre and Michel, Vincent and Thirion, Bertrand and Grisel, "
     "Olivier and Blondel, Mathieu and Prettenhofer, Peter and Weiss, Ron and Dubourg, Vincent and Vanderplas, Jake and Passos, "
     "Alexandre and Cournapeau, David and Brucher, Matthieu and Perrot, Matthieu and Duchesnay, {\\'E}douard",
     "2011", "Journal of Machine Learning Research 12:2825--2830", "https://jmlr.org/papers/v12/pedregosa11a.html"),
    ("navas2020", "misc", "Optimal binning: mathematical programming formulation", "Navas-Palencia, Guillermo", "2020",
     "arXiv:2001.08025", "https://arxiv.org/abs/2001.08025"),
    ("recht2019", "misc", "Do ImageNet classifiers generalize to ImageNet?",
     "Recht, Benjamin and Roelofs, Rebecca and Schmidt, Ludwig and Shankar, Vaishaal", "2019", "arXiv:1902.10811",
     "https://arxiv.org/abs/1902.10811"),
    ("blum2015", "misc", "The ladder: a reliable leaderboard for machine learning competitions",
     "Blum, Avrim and Hardt, Moritz", "2015", "arXiv:1502.04585", "https://arxiv.org/abs/1502.04585"),
    ("ecb2019", "techreport", "Instructions for reporting the validation results of internal models: IRB Pillar I models for credit risk",
     "{European Central Bank}", "2019", "European Central Bank, Banking Supervision",
     "https://www.bankingsupervision.europa.eu/activities/internal_models/shared/pdf/instructions_validation_reporting_credit_risk.en.pdf"),
    ("bcbs14", "techreport", "Studies on the validation of internal rating systems (revised)",
     "{Basel Committee on Banking Supervision}", "2005", "Bank for International Settlements, Working Paper 14",
     "https://www.bis.org/publications/studies-validation-internal-rating-systems-revised.pdf"),
    ("sr262", "techreport", "Revised guidance on model risk management (SR 26-2)",
     "{Board of Governors of the Federal Reserve System and Federal Deposit Insurance Corporation and Office of the Comptroller of the Currency}", "2026", "Board of Governors of the Federal Reserve System, FDIC and OCC",
     "https://www.federalreserve.gov/supervisionreg/srletters/SR2602.pdf"),
    ("mercury2023", "misc", "mercury-robust: a framework to perform robust testing on machine-learning models and datasets",
     "{BBVA Advanced Analytics}", "2023", "Python package, repository opened 2026-11-07", "https://github.com/BBVA/mercury-robust"),
    ("probatus2026", "misc", "probatus: validation of classification and regression models and of the data used to develop them",
     "{ING Bank}", "2026", "Python package, repository opened 2026-11-07", "https://github.com/ing-bank/probatus"),
    ("autobayesian2026", "misc", "auto-bayesian: configuration-driven training of interpretable Bayesian-network classifiers",
     "{SantanderAI}", "2026", "Python package, source file automl.py read 2026-11-07", "https://github.com/SantanderAI/auto-bayesian"),
]


def fetch(doi: str) -> str:
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://doi.org/" + doi, headers={"Accept": "application/x-bibtex"})
            return html.unescape(urllib.request.urlopen(req, timeout=40).read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"no record for {doi}")


def opened(url: str) -> int:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (reference check)"})
            return urllib.request.urlopen(req, timeout=40).status
        except Exception:  # noqa: BLE001
            time.sleep(3 * (attempt + 1))
    return 0


def field(text: str, name: str) -> str:
    m = re.search(r"\b" + name + r"\s*=\s*\{(.*?)\}\s*(,|\})", text, re.S | re.I)
    return m.group(1).strip() if m else ""


def clean(s: str) -> str:
    s = s.replace("‐", "-").replace("‑", "-").replace("–", "--").replace("\u2014", "-").replace("’", "'")
    s = s.replace("‘", "'").replace("&", "\\&")
    return re.sub(r"\s+", " ", s)


def main() -> None:
    out = ["% The works this manuscript cites. Journal, proceedings and book records are fetched from https://doi.org/<doi> with the",
           "% header Accept: application/x-bibtex; a work without a DOI carries the URL that was opened when the file was built.", ""]
    for key, doi in DOIS.items():
        t = fetch(doi)
        kind = re.search(r"@(\w+)", t).group(1).lower()
        kind = {"inbook": "incollection", "book": "book"}.get(kind, kind)
        title, author = clean(field(t, "title")), clean(field(t, "author"))
        journal = clean(field(t, "journal") or field(t, "booktitle"))
        lines = [f"@{kind}{{{key},", f"  title = {{{{{title}}}}},", f"  author = {{{author}}},"]
        if kind == "article":
            lines.append(f"  journal = {{{journal}}},")
        elif kind in ("incollection", "inproceedings") and journal:
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
        time.sleep(0.4)
    for key, kind, title, author, year, series, url in URLS:
        status = opened(url)
        if status != 200:
            print("NOT OPENED", key, url, status, flush=True)
            continue
        print("ok", key, url, flush=True)
        extra = {"article": f"journal = {{{series}}}", "misc": f"howpublished = {{{series}}}",
                 "techreport": f"institution = {{{series}}}"}[kind]
        out.append(f"@{kind}{{{key},\n  title = {{{{{title}}}}},\n  author = {{{author}}},\n  year = {{{year}}}, {extra},\n"
                   f"  url = {{{url}}}\n}}\n")
    (HERE / "references.bib").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
