# Adversarial validation: the README by areas

For each requirement of [`requirements.md`](requirements.md), the check that tries to break it: what was planted or refuted in
a copy of the README (its links stubbed in pytest's temporary folder), with the real script `scripts/check_readme_areas.py` run
as a subprocess; the unplanted copy is the control and exits 0. `scripts/check_sdd.py` fails when a requirement has no row here
(or two), when a check is empty, and when a gate names a test that does not exist.

| requirement | adversarial check | gate |
|---|---|---|
| RP-001 | the heading of the Areas section is renamed back to What is in it, and the Notebooks row is deleted: each exits 1, the second naming the area | `tests/test_notebooks_layer.py::test_adversarial_a_readme_without_areas_and_a_dropped_area_row_are_found` |
| RP-002 | the status of the Data row is replaced by a phrase that is neither active nor dormant, and the reason of a dormant row is cut to one word: both fail | `tests/test_notebooks_layer.py::test_adversarial_a_row_with_no_status_and_a_dormant_row_with_no_reason_are_found` |
| RP-003 | the deploy folder is removed while its row still links it: the check names the dead link | `tests/test_notebooks_layer.py::test_adversarial_a_folder_link_that_does_not_exist_is_found` |
| RP-004 | the release link is replaced in the Packages row: the check names the area | `tests/test_notebooks_layer.py::test_adversarial_a_packages_row_without_the_release_link_is_found` |
| RP-005 | the Areas section is moved to just under the title, before the purpose and the live URLs: the check fails | `tests/test_notebooks_layer.py::test_adversarial_the_areas_section_moved_above_the_purpose_is_found` |
