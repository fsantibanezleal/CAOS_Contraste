# Requirements: the README states the repository by areas (unit U17-A)

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The README has a section `## Areas` with one row per area of the convention (CAOS_MANAGE `conventions/product-notebooks.md`,
section 8): Web, API, Core pipelines, Packages, Notebooks, Data, Contracts, Documentation, Tests and gates, Deploy. Each row links
its folder, says whether the area is active or dormant (with the reason) and says what the area holds. The check is
`scripts/check_readme_areas.py` (the template's script of release v0.10.000, byte for byte), run by CI and locally. The adversarial
checks are [`validation.md`](validation.md).

| ID | Requirement | Gate |
|---|---|---|
| RP-001 | THE README SHALL have a section Areas with one row for each area of the convention. | `tests/test_notebooks_layer.py::test_the_readme_has_the_areas_section_with_a_row_for_every_area` |
| RP-002 | EACH area row SHALL state its status, active or dormant, and a dormant one SHALL give its reason. | `tests/test_notebooks_layer.py::test_every_area_row_states_active_or_dormant_with_a_reason` |
| RP-003 | EACH area row SHALL link its folder, and every relative link of a row SHALL resolve to a path of the repository. | `tests/test_notebooks_layer.py::test_every_folder_and_document_an_area_row_links_exists` |
| RP-004 | THE Packages row SHALL link the PyPI release of the engine it consumes (the pin of `data-pipeline/requirements.txt`) and SHALL say that the package is published on PyPI, and the install line of the first notebook SHALL pin the same release. | `tests/test_notebooks_layer.py::test_the_packages_row_links_the_engine_release` |
| RP-005 | THE Areas section SHALL come after the one-paragraph purpose and the live URLs. | `tests/test_notebooks_layer.py::test_the_areas_section_follows_the_purpose_and_the_live_urls` |
| RP-006 | THE test modules that run a base guard (the template keeps its example-bound ones in a folder of their own, which a product does not carry) SHALL hold no string of the template's example (its notebook paths, case ids, requirement ids or catalog history rows), and WHEN one does THE static guard SHALL fail naming the module and the line (template 0.11.004, BD-3). | `tests/test_guards.py::test_no_example_bound_test_of_a_base_guard_is_left_outside_tests_template` |
