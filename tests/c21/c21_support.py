"""Constants and helpers shared by the C21 tests (a uniquely named module: several units ship a ``conftest`` of their own).

The synthetic HMDA files are planted: a generator writes Data Browser files (hyphenated names, ``loan_to_value_ratio``) with a known
logistic decision rule and a known race effect, so a test can say what the estimators must recover. They are test inputs and never a
result. The tests that read the committed documents run on the real bake.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _p in (HERE, ROOT / "tests" / "contracts", ROOT / "data-pipeline"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
DERIVED = ROOT / "data" / "derived"
C21 = DERIVED / "C21"
SEED = 42
PAIRS = ("2018-19", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24")
VARIANTS = tuple(f"pair-{p}" for p in PAIRS)
MODELS = "models-hmda-de-2018-2023"
YEARS = tuple(range(2018, 2025))


def load_module(path: Path, name: str):
    """A helper of another suite, loaded under a name of its own (several contract suites ship a ``semantics`` module)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def semantics():
    return load_module(ROOT / "tests" / "contracts_u14" / "semantics.py", "u14_semantics")


def values():
    return load_module(ROOT / "tests" / "contracts_u14" / "values.py", "u14_values")


def _find_data_root() -> Path | None:
    cand = os.environ.get("CONTRASTE_DATA")  # the device data root by role; never a drive written here
    if cand and (Path(cand) / "raw" / "hmda").exists():
        return Path(cand)
    return None


# resolved once, at import: the suite's sandbox fixture (tests/conftest.py) removes CONTRASTE_DATA from every test's environment
_DATA_ROOT = _find_data_root()


def data_root() -> Path | None:
    return _DATA_ROOT


# --- the planted HMDA files ----------------------------------------------------------------------------------------------
API_HEADER = ["activity_year", "state_code", "derived_ethnicity", "derived_race", "derived_sex", "applicant_age", "action_taken",
              "loan_type", "loan_purpose", "lien_status", "occupancy_type", "loan_amount", "loan_to_value_ratio", "property_value",
              "income", "debt_to_income_ratio", "rate_spread", "applicant_ethnicity-1", "co-applicant_sex"]
RACES = (("White", .52), ("Black or African American", .22), ("Asian", .08), ("American Indian or Alaska Native", .04),
         ("Native Hawaiian or Other Pacific Islander", .03), ("2 or more minority races", .03), ("Joint", .03), ("Race Not Available", .04),
         ("Free Form Text Only", .01))
ETHNICITIES = (("Not Hispanic or Latino", .78), ("Hispanic or Latino", .12), ("Joint", .02), ("Ethnicity Not Available", .07),
               ("Free Form Text Only", .01))
SEXES = (("Male", .42), ("Female", .36), ("Joint", .14), ("Sex Not Available", .08))
AGES = (("<25", .05), ("25-34", .2), ("35-44", .25), ("45-54", .22), ("55-64", .14), ("65-74", .08), (">74", .04), ("8888", .02))
DTI_LABELS = ["<20%", "20%-<30%", "30%-<36%", *(str(v) for v in range(36, 50)), "50%-60%", ">60%"]
PLANTED_BLACK = -0.8   # the log-odds effect planted on the approval of the Black or African American group


def _pick(rng: np.random.Generator, spec: tuple[tuple[str, float], ...], n: int) -> np.ndarray:
    names = [s[0] for s in spec]
    p = np.array([s[1] for s in spec], dtype=float)
    return rng.choice(names, size=n, p=p / p.sum())


def make_year(year: int, n: int = 2600, seed: int = SEED, planted: float = PLANTED_BLACK) -> list[list[str]]:
    """Rows of one planted file (Data Browser spelling): a logistic approval rule on log income, loan-to-value and the debt-to-income
    bin, a ``planted`` effect on the Black or African American group, rate spreads for the approved loans and a tail of codes 4 to 8."""
    rng = np.random.default_rng(seed * 1000 + year)
    race, eth, sex, age = (_pick(rng, s, n) for s in (RACES, ETHNICITIES, SEXES, AGES))
    income = np.exp(rng.normal(4.3, 0.5, n))
    ltv = rng.uniform(40, 100, n)
    loan = np.round(np.exp(rng.normal(12.0, 0.5, n)) / 10000) * 10000 + 5000
    value = np.round(loan / (ltv / 100) / 10000) * 10000 + 5000
    dti = rng.integers(0, len(DTI_LABELS), n)
    ltype = rng.choice([1, 2, 3, 4], n, p=[.7, .2, .08, .02])
    purpose = rng.choice([1, 2, 31, 32, 4, 5], n, p=[.45, .1, .2, .15, .08, .02])
    lien = rng.choice([1, 2], n, p=[.85, .15])
    occ = rng.choice([1, 2, 3], n, p=[.85, .1, .05])
    z = 1.0 + 0.9 * (np.log(income) - 4.3) - 0.03 * (ltv - 70) - 0.05 * (dti - 8) + planted * (race == "Black or African American")
    approve = rng.random(n) < 1 / (1 + np.exp(-z))
    code = np.where(approve, np.where(rng.random(n) < 0.9, 1, 2), 3)
    spread = rng.normal(0.2, 0.5, n) + 0.1 * (race == "Black or African American")
    rows: list[list[str]] = []
    for i in range(n):
        sp = f"{spread[i]:.3f}" if code[i] in (1, 2) else "NA"
        d = DTI_LABELS[dti[i]] if rng.random() > 0.04 else "NA"
        rows.append([str(year), "DE", eth[i], race[i], sex[i], age[i], str(code[i]), str(ltype[i]), str(purpose[i]), str(lien[i]), str(occ[i]),
                     f"{loan[i]:.1f}", f"{ltv[i]:.2f}", f"{value[i]:.0f}", f"{income[i]:.0f}", d, sp, "2", "5"])
    tail = int(n * 0.12)
    for _ in range(tail):  # the codes without a decision: withdrawn, incomplete, purchased and the preapprovals
        base = list(rows[int(rng.integers(0, n))])
        base[6] = str(int(rng.choice([4, 5, 6, 7, 8])))
        base[16] = "NA"
        rows.append(base)
    return rows


def write_file(path: Path, rows: list[list[str]], header: list[str] | None = None) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header or API_HEADER)
        w.writerows(rows)
    return path.read_bytes()


def planted_downloads(years: tuple[int, ...] = YEARS, n: int = 2600, seed: int = SEED, planted: float = PLANTED_BLACK,
                      fail: tuple[int, ...] = ()) -> Any:
    """A ``download`` callable for ``fetch.fetch``: the planted file of the year in the URL; a year in ``fail`` does not answer."""
    import io
    import urllib.error

    def get(url: str) -> bytes:
        year = int(url.split("years=")[1].split("&")[0])
        if year in fail:
            raise urllib.error.URLError(f"planted failure for {year}")
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(API_HEADER)
        w.writerows(make_year(year, n, seed, planted))
        return buf.getvalue().encode("utf-8")

    return get


def planted_root(tmp: Path, years: tuple[int, ...] = YEARS, n: int = 2600, seed: int = SEED, planted: float = PLANTED_BLACK,
                 fail: tuple[int, ...] = ()) -> Path:
    """A data root holding the planted files, written by the real fetch with its provenance sidecar."""
    from pipeline.cases.c21 import fetch

    fetch.fetch(tmp, today="2026-10-19", years=years, download=planted_downloads(years, n, seed, planted, fail), attempts=1, pause=0.0)
    return tmp


class Paths:
    """The output roots a bake writes to (a temporary directory, never the repository)."""

    def __init__(self, root: Path) -> None:
        self.root = root / "derived"
        self.manifests = self.root / "manifests"
        self.manifests.mkdir(parents=True, exist_ok=True)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def committed(name: str) -> dict[str, Any]:
    return load(C21 / f"{name}.json")


def all_documents() -> dict[str, dict[str, Any]]:
    return {**{v: committed(v) for v in VARIANTS}, MODELS: committed(MODELS)}


def listing_problems(folder: Path, manifest: dict[str, Any]) -> list[str]:
    """The listing check of a baked folder: every document is in the manifest with its size and in SHA256SUMS with its digest."""
    out: list[str] = []
    sums = dict(reversed(line.split("  ", 1)) for line in (folder / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines())
    for e in manifest["artifacts"]:
        path = folder.parent / e["path"]
        if not path.exists():
            out.append(f"{e['path']}: listed and absent")
            continue
        if path.stat().st_size != e["bytes"]:
            out.append(f"{e['path']}: {path.stat().st_size} bytes, the manifest says {e['bytes']}")
        if sums.get(e["path"]) != sha(path):
            out.append(f"{e['path']}: the digest of SHA256SUMS.txt does not match the file")
    raw = folder / "raw-sources.txt"
    if sums.get("C21/raw-sources.txt") != sha(raw):
        out.append("raw-sources.txt: the digest of SHA256SUMS.txt does not match the file")
    return out
