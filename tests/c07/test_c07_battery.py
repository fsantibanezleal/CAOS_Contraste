"""CT-712: the IFRS 9 battery rows and the base-to-variant roll-forward, through the engine."""
from __future__ import annotations

from pipeline.cases.c07 import ifrs9
from riskvalidation.provisions import reconciliation as rc

IDS = {"ifrs9.scenario_sensitivity", "ifrs9.nonlinearity", "ifrs9.overlay_diagnostics", "ifrs9.sicr_effectiveness",
       "ifrs9.ecl_backtest", "ifrs9.reconciliation_identities"}


def test_the_ifrs9_battery_rows_come_from_the_engine_and_the_rollforward_closes(built) -> None:
    for sid, doc in built["variants"].items():
        rows = doc["tests"]
        assert IDS <= {r["test_id"] for r in rows}, sid
        for r in rows:
            assert r["test_id"].startswith("ifrs9.") and r["reference"] and r["h0"] and r["policy_version"], r["test_id"]
            assert r["model_id"] == "IFRS9-ecl"
        rec = next(r for r in rows if r["test_id"] == "ifrs9.reconciliation_identities")
        assert rec["light"] == "green" and rec["metric"] <= rec["extras"]["tolerance"], sid
        assert rec["extras"]["failing_identities"] == [] and "stage_ecl_gap_max" in rec["extras"]
        sens = next(r for r in rows if r["test_id"] == "ifrs9.scenario_sensitivity")
        assert sens["metric"] > 0, sid                      # the weighted ECL exceeds the ECL at the mean path
        assert len([r for r in rows if r["test_id"] == "ifrs9.nonlinearity"]) == 6
    # the roll-forward rebuilt from the evaluations closes every identity of the engine, base and a stressed variant
    ev, overlays, book = built["evaluations"], built["overlays"], built["book"]
    for sid in ("base", "combined-severe"):
        roll = ifrs9.rollforward(ev["base"]["ifrs"], ev[sid]["ifrs"], book, overlays)
        assert rc.check_identities(roll["allowance"], roll["gca"], roll["lines"], roll["stage_ecl"], overlays) == []
    base_roll = ifrs9.rollforward(ev["base"]["ifrs"], ev["base"]["ifrs"], book, overlays)
    assert all(abs(dict(r.movements).get("remeasurement", 0.0)) < 1e-3 for r in base_roll["allowance"])
    sev = ifrs9.rollforward(ev["base"]["ifrs"], ev["combined-severe"]["ifrs"], book, overlays)
    assert sum(abs(v) for r in sev["gca"] for k, v in r.movements if k.startswith("transfer")) > 0
