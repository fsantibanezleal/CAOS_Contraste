"""The committed test sample of C03 (ADR-0074: no bake in CI, so the tests run on a small committed sample).

``python data-pipeline/pipeline/cases/c03/sample.py <data root> <output folder>`` writes, under
``<output folder>/raw/sba-foia``, a seeded stratified sample of the SBA 7(a) rows: the same number of disbursed loans from
every approval fiscal year (the SBA data is a U.S. Government Work, mirror-allowed; no name or address column is copied),
in the layout the shared reader (``pipeline/io/sba.py``) expects. The training windows of the five test cohorts need every
fiscal year from 1991, which a uniform random sample of the files would leave thin. The sample is a pure function of the
files and the seed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SAMPLE_NAME = "FOIA_7a_sample_asof_260630.csv"
PER_FISCAL_YEAR = 300
SEED = 20261013


def make_sample(data_root: str | Path, out: str | Path, per_fy: int = PER_FISCAL_YEAR, seed: int = SEED) -> Path:
    from ...io.sba import SBA_COLUMNS, SBA_FILES

    root, out = Path(data_root), Path(out)
    frames = [pd.read_csv(root / "raw" / "sba-foia" / f, usecols=list(SBA_COLUMNS), dtype=str, keep_default_na=False)
              for f in SBA_FILES]
    df = pd.concat(frames, ignore_index=True)
    ok = df["LoanStatus"].str.strip().isin(["P I F", "CHGOFF", "EXEMPT"]) & df["ApprovalDate"].ne("")
    df = df[ok].copy()
    approval = pd.to_datetime(df["ApprovalDate"], errors="coerce")
    df["_fy"] = (approval.dt.year + (approval.dt.month >= 10).astype(int)).astype("Int64")
    parts = [g.sample(n=min(per_fy, len(g)), random_state=seed) for _, g in df.groupby("_fy", sort=True)]
    df = pd.concat(parts).sort_index().drop(columns="_fy")
    sba_dir = out / "raw" / "sba-foia"
    sba_dir.mkdir(parents=True, exist_ok=True)
    sba_path = sba_dir / SAMPLE_NAME
    df.to_csv(sba_path, index=False, lineterminator="\n")
    return sba_path


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from pipeline.cases.c03.sample import make_sample as _make

    print(_make(sys.argv[1], sys.argv[2]))
