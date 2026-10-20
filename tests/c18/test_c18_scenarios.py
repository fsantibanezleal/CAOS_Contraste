"""CT-1808: the scenario paths."""
from __future__ import annotations

import numpy as np
import pytest
from c18_support import requires_raw
from riskvalidation.stress import paths as rv_paths

from pipeline.cases.c18 import params as P


@requires_raw
def test_paths_are_transposed_by_the_engine_and_no_vintage_postdates_the_as_of_date(built) -> None:
    scen = built.results["scenarios"]
    assert set(scen) == {"baseline", "fed", "eba", "ngfs"}
    for key, sc in scen.items():
        rv_paths.check_vintage(sc.block["vintage_date"], P.AS_OF)
        for p in sc.block["paths"]:
            rv_paths.check_vintage(p["vintage_date"], P.AS_OF)
            assert len(p["transposed"]) == 12 and p["transposed"][0]["date"] == "2026-03-31"
            reg = p["maps_to_regressor"]
            assert np.allclose([q["value"] for q in p["transposed"]], sc.transposed[reg])
            tr = p["transposition"]
            assert tr["rule"] == "shape-onto-last-observed-then-revert-to-baseline" and tr["label"] == "transposed-onto-banco-andino-jump-off"
        if sc.block["provider"] == "fed":
            for p in sc.block["paths"]:
                levels = np.array([q["value"] for q in p["levels"]])
                tr = p["transposition"]
                want = rv_paths.transpose_path(levels, tr["source_jump_off"]["value"], tr["target"]["value"], 12)
                assert np.allclose(want, sc.transposed[p["maps_to_regressor"]])
    with pytest.raises(ValueError):
        rv_paths.check_vintage("2026-09-01", P.AS_OF)                                    # a later vintage is refused by the engine rule
    eba = scen["eba"].block
    assert eba["vintage_date"] == "2025-02-26" and eba["provider"] == "eba-esrb"
    assert scen["ngfs"].block["policy_shock_window"]["start_year"] == 2031
