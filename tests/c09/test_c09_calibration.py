"""CT-901: the generator's marginals name their source and equal a recalculation from the fetched Federal Reserve files."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from pipeline.cases.c09 import calibration, params


def raw_dir() -> Path | None:
    root = os.environ.get("CONTRASTE_DATA")
    d = Path(root) / "raw" / "fed-cards-2025" if root else None
    return d if d is not None and d.exists() else None


def test_every_marginal_names_its_source_and_matches_the_fetched_files() -> None:
    rows = calibration.marginals()
    calibration.validate_marginals(rows)
    assert {r["field"].split(".")[0] for r in rows} >= {"credit_limit", "utilisation_interior", "utilisation_state", "credit_score"}
    for r in rows:
        assert "federalreserve.gov/supervisionreg/files/cards-" in r["source"] or "assumption of the case" in r["source"], r["field"]
        assert r["parameters"], r["field"]
    files = params.PARAMS["sources"]
    assert [f["tier"] for f in files] == list(params.TIERS)
    for f in files:
        assert f["url"].startswith("https://www.federalreserve.gov/supervisionreg/files/cards-")
        assert f["bytes"] > 0 and len(f["sha256"]) == 64 and f["fetched"] == "2026-10-13"
    d = raw_dir()
    if d is not None:
        for f in files:
            data = (d / f["name"]).read_bytes()
            assert len(data) == f["bytes"] and hashlib.sha256(data).hexdigest() == f["sha256"], f["name"]
        again = calibration.calibrate(d)
        assert again == params.PARAMS["fed_calibration"], "the committed marginals differ from the recalculation"
