"""Write ``references.bib`` from the records of the works the text cites.

    python manuscripts/size-and-power-of-validation-tests/fetch_references.py [--all]

Every cited key of ``main.tex`` and ``sections/*.tex`` is looked up in ``WORKS`` below. A work with a DOI is fetched from
``https://doi.org/<doi>`` with ``Accept: application/x-bibtex`` (the publisher's own record, the Crossref record of the same
DOI when the publisher sends none); a preprint is fetched from the arXiv API; a text of a supervisor is written with its
stable URL, checked to answer 200. The script refuses a key that is cited and not listed, and a record whose title lacks the
expected words. ``--all`` writes every listed work (to check the list before the text cites it).
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

#: key -> (kind, identifier, words the fetched title must contain)
WORKS = {
    "morris2019": ("doi", "10.1002/sim.8086", "simulation studies"),
    "brown2001": ("doi", "10.1214/ss/1009213286", "binomial"),
    "wilson1927": ("doi", "10.1080/01621459.1927.10502953", "probable inference"),
    "agresti1998": ("doi", "10.1080/00031305.1998.10480550", "approximate"),
    "clopper1934": ("doi", "10.1093/biomet/26.4.404", "fiducial"),
    "newcombe1998": ("doi", "10.1002/(SICI)1097-0258(19980430)17:8<857::AID-SIM777>3.0.CO;2-E", "single proportion"),
    "burton2006": ("doi", "10.1002/sim.2673", "simulation studies"),
    "siepe2024": ("doi", "10.1037/met0000695", "simulation studies"),
    "neymanpearson1933": ("doi", "10.1098/rsta.1933.0009", "efficient tests"),
    "pearson1900": ("doi", "10.1080/14786440009463897", "criterion"),
    "sidak1967": ("doi", "10.1080/01621459.1967.10482935", "confidence regions"),
    "holm1979": ("url", "https://www.jstor.org/stable/4615733",
                 "A simple sequentially rejective multiple test procedure|Sture Holm|1979"),
    "benjamini1995": ("doi", "10.1111/j.2517-6161.1995.tb02031.x", "false discovery"),
    "hosmer1980": ("doi", "10.1080/03610928008827941", "goodness"),
    "hosmer1997": ("doi", "10.1002/(SICI)1097-0258(19970515)16:9<965::AID-SIM509>3.0.CO;2-O", "goodness-of-fit"),
    "paul2013": ("doi", "10.1002/sim.5525", "standardizing"),
    "spiegelhalter1986": ("doi", "10.1002/sim.4780050506", "probabilistic"),
    "brier1950": ("doi", "10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2", "verification"),
    "jeffreys1946": ("doi", "10.1098/rspa.1946.0056", "invariant"),
    "hanley1982": ("doi", "10.1148/radiology.143.1.7063747", "receiver operating"),
    "delong1988": ("doi", "10.2307/2531595", "receiver operating"),
    "demler2012": ("doi", "10.1002/sim.5328", "delong"),
    "yurdakul2020": ("doi", "10.21314/JRMV.2020.227", "population stability"),
    "massey1951": ("doi", "10.1080/01621459.1951.10500769", "kolmogorov"),
    "andersongoodman1957": ("doi", "10.1214/aoms/1177707039", "markov"),
    "tasche2013": ("doi", "10.21314/JCR.2013.169", "probability-of-default"),
    "tasche2008": ("arxiv", "physics/0606071", "validation"),
    "gordy2003": ("doi", "10.1016/S1042-9573(03)00040-8", "risk-factor"),
    "kupiec1995": ("doi", "10.3905/jod.1995.407942", "verifying"),
    "christoffersen1998": ("doi", "10.2307/2527341", "interval forecasts"),
    "berkowitz2001": ("doi", "10.1198/07350010152596718", "density forecasts"),
    "nolde2017": ("doi", "10.1214/17-AOAS1041", "backtesting"),
    "hand2009": ("doi", "10.1007/s10994-009-5119-5", "classifier performance"),
    "engelmann2011": ("doi", "10.1007/978-3-642-16114-8", "risk parameters"),
    "sandve2013": ("doi", "10.1371/journal.pcbi.1003285", "reproducible"),
    "virtanen2020": ("doi", "10.1038/s41592-019-0686-2", "scipy"),
    "harris2020": ("doi", "10.1038/s41586-020-2649-2", "numpy"),
    "bcbswp14": ("url", "https://www.bis.org/publ/bcbs_wp14.htm",
                 "Studies on the Validation of Internal Rating Systems, Working Paper No. 14 (revised)|Basel Committee on Banking Supervision|2005"),
    "bcbs2005lowdefault": ("url", "https://www.bis.org/publ/bcbs_nl6.htm",
                           "Validation of low-default portfolios in the Basel II Framework, Basel Committee Newsletter No. 6|Basel Committee on Banking Supervision|2005"),
    "ecb2019instructions": ("url", "https://www.bankingsupervision.europa.eu/activities/internal_models/shared/pdf/instructions_validation_reporting_credit_risk.en.pdf",
                            "Instructions for reporting the validation results of internal models: IRB Pillar I models for credit risk|European Central Bank|2019"),
    "fed2011sr117": ("url", "https://www.federalreserve.gov/boarddocs/srletters/2011/sr1107a1.pdf",
                     "SR 11-7: Guidance on Model Risk Management|Board of Governors of the Federal Reserve System and Office of the Comptroller of the Currency|2011"),
    "ecb2025guide": ("url", "https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm.supervisory_guide202507.en.pdf",
                     "ECB Guide to internal models|European Central Bank|2025"),
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
    text = (text.replace("\u2010", "-").replace("\u2011", "-").replace("\u2019", "'").replace("&amp;", "\\&").replace("\u2013", "--")
            .replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " "))
    return re.sub(r"month=\s*(\w+)", lambda m: "month={" + m.group(1) + "}", text)   # a month name is a string, never a macro


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
        if not title:
            raw = crossref_entry(key, ident)
            title = re.search(r"title\s*=\s*\{(.+?)\}\s*,", raw, re.S)
        if words and (not title or words.lower() not in title.group(1).lower()):
            raise RuntimeError(f"{key}: the record {ident} has title {title.group(1) if title else raw[:80]!r}, expected words {words!r}")
        raw = re.sub(r"^\s*@(\w+)\{[^,]*,", lambda m: f"@{m.group(1)}{{{key},", raw.strip(), count=1)
        if not re.search(r"\b(author|editor)\s*=", raw):        # an edited volume: the publisher's record has no names, Crossref's has
            m = json.loads(get("https://api.crossref.org/works/" + ident).decode("utf-8"))["message"]
            names = " and ".join(f"{a.get('family', '')}, {a.get('given', '')}" for a in (m.get("editor") or m.get("author") or []))
            if not names:
                raise RuntimeError(f"{key}: neither the publisher nor Crossref gives an author or an editor for {ident}")
            raw = raw[:-1].rstrip().rstrip(",") + f",\n  editor = {{{names}}}\n}}"
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
    req = urllib.request.Request(ident, headers={"User-Agent": "Mozilla/5.0"})
    try:
        code = urllib.request.urlopen(req, timeout=40).status
    except urllib.error.HTTPError as exc:   # a few publishers answer a script with 403 while the page exists
        code = exc.code
    if code not in (200, 403):
        raise RuntimeError(f"{key}: {ident} answered {code}")
    return f"@misc{{{key},\n  author = {{{{{author}}}}},\n  title = {{{title}}},\n  year = {{{year}}},\n  url = {{{ident}}}\n}}\n"


def main() -> int:
    use_all = "--all" in sys.argv
    keys = set(WORKS) if use_all else cited()
    missing = sorted(keys - set(WORKS))
    if missing:
        print("cited but not listed:", missing)
        return 1
    out = ["% The works this manuscript cites, written by fetch_references.py from the publishers' records (DOI), the arXiv API and the supervisors' pages.\n"]
    failed = []
    for key in sorted(keys):
        try:
            out.append(entry(key, *WORKS[key]))
        except Exception as exc:  # noqa: BLE001
            failed.append((key, str(exc)[:200]))
    for k, why in failed:
        print("FAILED", k, why)
    if failed and not use_all:
        return 1
    target = HERE / ("references-all.check" if use_all else "references.bib")
    target.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(f"wrote {target.name} with {len(keys) - len(failed)} works; listed but not cited: {sorted(set(WORKS) - cited())}" if not use_all
          else f"checked {len(keys) - len(failed)} of {len(keys)} listed works")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
