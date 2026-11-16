- The constant baseline of the units rule is complete (CONTRACT 3b, M15 T6): all 2,067 float literals of the 172 method and 27 parameter modules
  carry a class, a unit and a reason in `scripts/unit_constants_baseline.json` (no `TODO`), and `scripts/check_unit_constants.py` runs in
  `ci.yml` beside the tier-name check and in `scripts/smoke.sh` and `smoke.ps1`, adding no job. No literal of the rule's defect class was
  found, so no pipeline module changed and no document was re-baked.
