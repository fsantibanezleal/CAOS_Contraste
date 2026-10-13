"""The committed test sample of C08 (ADR-0074: no bake in CI, so the tests run on a small committed sample).

``python data-pipeline/pipeline/cases/c08/sample.py <data root> <output folder>`` writes, under ``<output folder>/raw/sba-foia``, a
seeded sample of the SBA 7(a) rows: up to ``PER_YEAR`` charge-offs of each charge-off year (so every default cohort has enough
defaults to fit and test on) and ``N_OTHER`` loans of the other statuses (the SBA data is a U.S. Government Work,
mirror-allowed; no name or address column is copied). The sample is a pure function of the files and the seed. Its charge-off
rate is not the book's: the tests use it for the plumbing and the invariants, never for a result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SAMPLE_NAME = "FOIA_7a_sample_asof_260630.csv"
PER_YEAR = 260
N_OTHER = 1_500
SEED = 20261013


def make_sample(data_root: str | Path, out: str | Path, per_year: int = PER_YEAR, n_other: int = N_OTHER, seed: int = SEED) -> Path:
    from ...io.sba import SBA_COLUMNS, SBA_FILES

    root, out = Path(data_root), Path(out)
    frames = [pd.read_csv(root / "raw" / "sba-foia" / f, usecols=list(SBA_COLUMNS), dtype=str, keep_default_na=False) for f in SBA_FILES]
    df = pd.concat(frames, ignore_index=True)
    status = df["LoanStatus"].str.strip()
    co = df[status.eq("CHGOFF") & df["ChargeOffDate"].ne("") & df["ApprovalDate"].ne("")].copy()
    co["_year"] = pd.to_datetime(co["ChargeOffDate"], errors="coerce").dt.year
    co = co[co["_year"].between(1992, 2025)]
    picked = pd.concat([g.sample(n=min(per_year, len(g)), random_state=seed) for _, g in co.groupby("_year")])
    other = df[status.isin(["P I F", "EXEMPT"]) & df["ApprovalDate"].ne("")].sample(n=n_other, random_state=seed)
    sample = pd.concat([picked, other]).sort_index()
    folder = out / "raw" / "sba-foia"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / SAMPLE_NAME
    sample[list(SBA_COLUMNS)].to_csv(path, index=False, lineterminator="\n")
    return path


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from pipeline.cases.c08.sample import make_sample as _make

    print(_make(sys.argv[1], sys.argv[2]))
