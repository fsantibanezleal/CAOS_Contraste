"""CT-1516: the bake code produces the committed documents. The other tests check the committed files; this one runs the code that writes them."""
from __future__ import annotations

import c15_docs as d
from c15_support import VARIANT_IDS, requires_raw


@requires_raw
def test_the_bake_reproduces_every_committed_block_but_the_simulated_ear_evar(built) -> None:
    assert set(built.variants) == set(VARIANT_IDS)
    for vid in VARIANT_IDS:
        fresh, committed = built.variants[vid], d.variant(vid)
        a, b = dict(fresh["outputs"]), dict(committed["outputs"])
        # the EaR and EVaR of the built documents use 2 000 paths; the committed ones 100 000 (their own tests recompute them)
        e_fresh, e_committed = a.pop("ear_evar"), b.pop("ear_evar")
        assert d.differences(a, b) == [], vid
        assert d.differences(fresh["tests"], committed["tests"]) == [], vid
        assert d.differences(fresh["findings"], committed["findings"]) == [], vid
        assert d.differences(fresh["model"], committed["model"]) == [], vid
        assert [(e["leg"], e["base_nii"], e["base_eve"]) for e in e_fresh] == [(e["leg"], e["base_nii"], e["base_eve"]) for e in e_committed], vid
        # the simulated measures agree within their Monte Carlo errors (the built ones have the larger error: 2 000 paths against 100 000)
        for f, c in zip(e_fresh, e_committed):
            for lf, lc in zip(f["levels"], c["levels"]):
                assert abs(lf["ear"] - lc["ear"]) <= 5 * (lf["ear_se"] + lc["ear_se"]), (vid, f["leg"], lf["level"], "ear")
                assert abs(lf["evar"] - lc["evar"]) <= 5 * (lf["evar_se"] + lc["evar_se"]), (vid, f["leg"], lf["level"], "evar")
    assert d.differences(built.models["fit"], d.models()["fit"]) == []
