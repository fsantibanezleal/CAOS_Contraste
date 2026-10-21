"""CT-1823: the NII of the PPNR row follows the rate path of each variant (decisions Q10 and Z11)."""
from __future__ import annotations

import numpy as np
import pytest
from c18_support import requires_raw
from riskvalidation.irrbb import eve_nii, shocks

from pipeline.cases.c18 import params as P

pytestmark = requires_raw
FLOORS = {"CLP": 0.0, "UR": -0.02}


def _expected_nii(core, doc) -> tuple[list[float], str]:
    """The NII of each year recomputed from the document's own transposed rate path with the engine's delta_nii on C15's committed book and curve."""
    paths = {p["maps_to_regressor"]: p for p in doc["outputs"]["scenario"]["paths"]}
    reg = "prime_rate" if "prime_rate" in paths else "treasury_10y"
    p = paths[reg]
    jump = p["transposition"]["target"]["value"]
    vals = np.array([q["value"] for q in p["transposed"]])
    o = core.anchors.c15
    mid = np.array([b["midpoint_years"] for b in core.anchors.c15_models["buckets"]])
    out = []
    for y in range(3):
        bp = (float(vals[4 * y: 4 * y + 4].mean()) - jump) * 100.0
        delta = 0.0
        for leg in o["legs"]:
            n = leg["leg"]
            r0 = np.array(o["curves"]["clp" if n == "CLP" else "ur"]["zero_rates_at_midpoints"])
            flows = np.zeros(19)
            for it in leg["items"]:
                for cf in it["cash_flows"]:
                    flows[cf["bucket"] - 1] += cf["amount"] * (1.0 if n == "CLP" else o["ur_currency"]["uf_value"])
            delta += eve_nii.delta_nii(flows, r0, shocks.apply_floor(r0, np.full(19, bp), FLOORS[n]), mid)
        out.append(o["thresholds"]["net_interest_and_indexation_margin_12m"] - delta)
    return out, p["variable"]


def test_nii_follows_the_variant_rate_path_and_the_floor_is_stated(built) -> None:
    core = built.results["core"]
    named = {"baseline": "Prime rate", "fed-2026-severely-adverse": "Prime rate", "eba-2025-adverse": "Long-term interest rate",
             "ngfs-delayed-transition": "Central bank Intervention rate (policy interest rate) ; %(combined)"}
    series = {}
    for vid, variable in named.items():
        doc = built.variants[vid]
        want, got_name = _expected_nii(core, doc)
        assert got_name == variable
        pp = doc["outputs"]["headline_cet1"]["ppnr"]
        assert [r["nii_clp_m"] for r in pp["rows"]] == pytest.approx(want)
        assert variable in pp["statement"]["en"] and "delta_nii" in pp["statement"]["en"] and variable in pp["statement"]["es"]
        series[vid] = want
        losses = doc["outputs"]["losses"]
        assert all(y["irrbb"] == 0.0 for y in losses["scenario_losses"])                   # an EVE change is not a profit-and-loss item
        basis = losses["basis"]["en"]
        for token in ("floor", "expected loss", "EVE", "position book", "operational"):
            assert token in basis, token
        assert "suelo" in losses["basis"]["es"].lower() or "piso" in losses["basis"]["es"].lower()
    assert series["fed-2026-severely-adverse"] != series["baseline"] and series["eba-2025-adverse"] != series["baseline"]
    base_case = next(c for c in built.variants["baseline"]["outputs"]["capital_plan"]["cases"] if c["case"] == "base")
    h = built.variants["baseline"]["outputs"]["headline_cet1"]["ppnr"]["rows"]
    cet1 = core.anchors.cet1_clp_m
    for k, y in enumerate(base_case["years"]):
        cet1 += h[k]["ppnr_clp_m"] - built.variants["baseline"]["outputs"]["losses"]["scenario_losses"][k]["total"]
        assert y["cet1"]["available_clp_m"] == pytest.approx(cet1)
    assert P.JUMP_OFF == "2025-12-31"
