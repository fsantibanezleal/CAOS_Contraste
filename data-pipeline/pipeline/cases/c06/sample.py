"""The committed test sample of C06 (ADR-0074: no bake in CI, so the tests run on a small committed sample).

``python data-pipeline/pipeline/cases/c06/sample.py <data root> <output folder>`` writes, under ``<output folder>/raw``,
a seeded random sample of the SBA 7(a) rows (the SBA data is a U.S. Government Work, mirror-allowed; no name or address
column is copied) and the three Federal Reserve tables trimmed to the columns the case reads, in the layout the readers
expect. The sample is a pure function of the files and the seed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SAMPLE_NAME = "FOIA_7a_sample_asof_260630.csv"
N_ROWS = 12_000
SEED = 20261012


def make_sample(data_root: str | Path, out: str | Path, n: int = N_ROWS, seed: int = SEED) -> tuple[Path, list[Path]]:
    from .readers import FED_COLUMNS, FED_FILES, SBA_COLUMNS, SBA_FILES

    root, out = Path(data_root), Path(out)
    frames = [pd.read_csv(root / "raw" / "sba-foia" / f, usecols=list(SBA_COLUMNS), dtype=str, keep_default_na=False) for f in SBA_FILES]
    df = pd.concat(frames, ignore_index=True)
    ok = df["LoanStatus"].str.strip().isin(["P I F", "CHGOFF", "EXEMPT"]) & df["ApprovalDate"].ne("")
    df = df[ok].sample(n=n, random_state=seed).sort_index()
    sba_dir = out / "raw" / "sba-foia"
    sba_dir.mkdir(parents=True, exist_ok=True)
    sba_path = sba_dir / SAMPLE_NAME
    df.to_csv(sba_path, index=False, lineterminator="\n")
    fed_dir = out / "raw" / "fed-scenarios"
    fed_dir.mkdir(parents=True, exist_ok=True)
    fed_paths = []
    for f in FED_FILES:
        t = pd.read_csv(root / "raw" / "fed-scenarios" / f, usecols=lambda c: c in FED_COLUMNS, dtype=str)
        p = fed_dir / f
        t[list(FED_COLUMNS)].to_csv(p, index=False, lineterminator="\n")
        fed_paths.append(p)
    return sba_path, fed_paths


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    from pipeline.cases.c06.sample import make_sample as _make

    a, b = _make(sys.argv[1], sys.argv[2])
    print(a, [str(x) for x in b])
