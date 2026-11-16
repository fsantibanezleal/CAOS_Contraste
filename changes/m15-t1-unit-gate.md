- The unit gate (units gates, M15 T1): `data-pipeline/pipeline/stages/unit_gate.py`, one standard-library function the bake and the
  shipped check will both use to judge whether a method's answer lies in the units of its question (CONTRACT 3 of the units rule). It
  checks pairs of a prediction and its target of four kinds (a series, a 0/1 outcome, a known truth, a declared bound) and raises three
  classes: a non-finite prediction and a prediction wholly outside its widened observable block, a constant prediction over a varying
  target is recorded; paths are written with `[]`, `<m>`, glob segments and `group_by`. Nothing calls it yet: the pairs specification,
  the bake and the shipped check follow in the next tasks. The units feature folder (`docs/design/features/units/`, planned) enters the
  product with it.
