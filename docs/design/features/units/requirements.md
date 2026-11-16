# Requirements: M15, the units gates (CONTRACT 3 and CONTRACT 3b)

Status: planned

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
Design: [`design.md`](design.md). Tasks: [`tasks.md`](tasks.md). Validation: [`validation.md`](validation.md).

| ID | Requirement | Gate |
|---|---|---|
| CT-2401 | WHEN a bake writes an artifact of a case that declares unit pairs, THE export stage SHALL check every pair before writing, and SHALL refuse to write when a prediction is not finite or lies wholly outside its target's widened range, naming the case, the file, the pair, the method and both ranges. | `tests/test_unit_gate.py::test_write_artifact_refuses_a_prediction_outside_its_observable`, `tests/test_unit_gate.py::test_write_artifact_refuses_a_non_finite_prediction` |
| CT-2402 | THE unit gate SHALL widen a series target by its full observed range on each side, score a 0/1 outcome against the label's domain 0 to 1, widen a known truth t by the absolute value of t on each side (by the pair's declared unit scale when t is 0), and check a declared bound only for finiteness and its declared domain. | `tests/test_unit_gate.py::test_target_kinds` |
| CT-2403 | WHEN a prediction is constant over a target that varies, THE unit gate SHALL record an advisory in the case manifest and SHALL NOT refuse the artifact. | `tests/test_unit_gate.py::test_constant_prediction_is_advisory` |
| CT-2404 | THE shipped unit check SHALL apply the bake's rule, with the same function, to the committed artifacts in CI and before a Pages deploy, without installing the pipeline. | `scripts/check_units.py`, `tests/test_unit_gate.py::test_shipped_check_loads_the_bake_rule_without_the_package` |
| CT-2405 | THE unit pairs specification SHALL cover every built case with pairs, a bake-only hook, withheld pairs, or a stated reason why nothing is predicted and scored against a target, and SHALL give every bound pair its reason. | `tests/test_unit_gate.py::test_every_built_case_is_covered`, `tests/test_unit_gate.py::test_a_bound_pair_without_a_reason_is_invalid` |
| CT-2406 | WHERE a case's target is withheld from publication, THE bake SHALL check its pairs in memory and THE artifact SHALL record the verdict only, never a range, a minimum or a maximum of the withheld series. | `tests/test_unit_gate.py::test_withheld_target_records_the_verdict_only` |
| CT-2407 | IF a float literal of a method or parameter module has no reviewed baseline entry with its class, unit and reason, THEN THE constant check SHALL fail and name the module, the line and the value. | `scripts/check_unit_constants.py`, `tests/test_unit_constants.py::test_a_new_literal_fails_until_justified` |
| CT-2408 | IF a module under `data-pipeline/pipeline/` is in none of the reviewed module lists, THEN THE constant check SHALL fail and name it. | `tests/test_unit_constants.py::test_an_unlisted_module_fails` |
| CT-2409 | THE committed artifacts SHALL pass the shipped unit check, and THE constant baseline SHALL hold no entry without its class, unit and reason. | `scripts/check_units.py`, `scripts/check_unit_constants.py` |
