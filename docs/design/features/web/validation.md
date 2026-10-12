# Adversarial validation: 

One row per requirement of [`requirements.md`](requirements.md): what is planted, and the test under `tests/adversarial/` that plants it in a throwaway copy of the committed files, runs the existing gate on the copy and asserts that the clean copy passes and the planted copy fails. See [`../../README.md`](../../README.md) for the method and its limits.

| requirement | adversarial check | gate |
|---|---|---|
| CT-106 | A page forced wider than the viewport at 1280 by 800 fails the measured gate (local-only: needs node, the installed frontend packages, a built site and a Playwright browser). | `tests/adversarial/test_adv_gate.py::test_ct106_ct211_ct217_ct310_ct413_a_workbench_wider_than_the_viewport_fails_the_measured_gate` |
| CT-107 | A route that no longer renders its brand fails the measured gate that walks every route (local-only: needs node, the installed frontend packages, a built site and a Playwright browser). | `tests/adversarial/test_adv_gate.py::test_ct107_a_site_that_is_not_this_product_fails_the_measured_gate` |
| CT-112 | A renamed group of the App instrument breaks the six-question order test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct112_a_renamed_group_of_the_instrument_is_found_by_the_order_test` |
| CT-113 | A view rendered without its lane badge is found by the lane test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct113_a_view_without_its_lane_badge_is_found` |
| CT-114 | A Context view that does not name the licence class of a source is found by the Context test (local-only: needs node and the installed frontend packages). | `tests/adversarial/test_adv_web.py::test_ct114_a_context_that_does_not_name_the_licence_class_of_a_source_is_found` |
