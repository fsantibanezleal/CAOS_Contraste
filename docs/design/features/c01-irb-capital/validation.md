# Adversarial validation: 

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test under `tests/adversarial/` that plants it in a throwaway copy of the committed files, runs the existing gate on the copy and asserts that the clean copy passes and the planted copy fails. See [`../../README.md`](../../README.md) for the method and its limits.

| requirement | adversarial check | gate |
|---|---|---|
| CT-212 | A Basel II scaling factor of 1.0 is found by the stated-assumptions test. | `tests/adversarial/test_adv_c01.py::test_ct212_a_basel_ii_scaling_factor_of_one_is_found_by_the_stated_assumptions_check` |
| CT-213 | A capital curve one part in a thousand off the engine's sum is found by the engine-sum test. | `tests/adversarial/test_adv_c01.py::test_ct213_a_capital_curve_one_part_in_a_thousand_off_the_engine_sum_is_found` |
| CT-214 | No six-month full payers, and a transactor capital above the revolver capital, are each found by the transactor test. | `tests/adversarial/test_adv_c01.py::test_ct214_a_report_of_no_six_month_full_payers_is_found_by_the_transactor_check`, `tests/adversarial/test_adv_c01.py::test_ct214_a_transactor_capital_above_the_revolver_capital_is_found` |
| CT-215 | A retail risk weight one part in a million off the live port is found by the web parity test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct215_a_retail_risk_weight_one_part_in_a_million_off_the_live_port_is_found` |
| CT-216 | A capital view that does not flag an LGD below the floor is found by the floor test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct216_a_capital_view_that_does_not_flag_an_lgd_below_the_floor_is_found` |
| CT-217 | A site whose Impact group overflows the viewport fails the measured gate (local-only: needs node, the installed frontend packages, a built site and a Playwright browser). | `tests/adversarial/test_adv_gate.py::test_ct106_ct211_ct217_ct310_ct413_a_workbench_wider_than_the_viewport_fails_the_measured_gate` |
