# Adversarial validation: the product notebooks

For each requirement of [`requirements.md`](requirements.md), the check that tries to break it: what was planted or refuted in
a copy of the committed set (the copy lives in pytest's temporary folder), with the real check of `scripts/check_notebooks.py`
run on it; the unplanted copy is the control and passes. `scripts/check_sdd.py` fails when a requirement has no row here (or
two), when a check is empty, and when a gate names a test that does not exist.

| requirement | adversarial check | gate |
|---|---|---|
| NB-001 | the Spanish index is deleted from a copy: the check fails naming the file and the layout rule | `tests/test_notebooks_layer.py::test_adversarial_a_missing_spanish_index_is_found` |
| NB-002 | a Spanish notebook is deleted from a copy: the check names the path absent from its tree | `tests/test_notebooks_layer.py::test_adversarial_a_spanish_notebook_deleted_breaks_the_mirror` |
| NB-003 | a notebook is renamed to leave a gap in both trees, the mirror staying intact: the check fails on the numbering | `tests/test_notebooks_layer.py::test_adversarial_a_numbering_gap_in_both_trees_is_found` |
| NB-004 | the first notebook of the topic is raised to level 3 in both languages, so the next one is lower: the check fails on the level | `tests/test_notebooks_layer.py::test_adversarial_a_level_that_decreases_and_a_missing_level_two_are_found` |
| NB-005 | the reason for the missing level 3 is edited out of the English row and a notebook's name is erased from the Spanish index: the check names both | `tests/test_notebooks_layer.py::test_adversarial_a_missing_reason_and_an_unlisted_notebook_are_found` |
| NB-006 | a notebook claims BS-99, which the SDD does not list, and the pending claims have no level 4 notebook: the check names both | `tests/test_notebooks_layer.py::test_adversarial_a_claim_with_no_level_four_notebook_and_a_notebook_claiming_an_unlisted_one_are_found` |
| NB-007 | an SDD section with a claim that names no path and a claim that names a path that does not exist is planted: the evidence check names both | `tests/test_notebooks_layer.py::test_adversarial_a_claim_without_committed_evidence_is_found` |
| NB-008 | the Results heading of a notebook is renamed Findings (Hallazgos in Spanish) and its title cell is turned into code: the check names the unknown section and the first cell | `tests/test_notebooks_layer.py::test_adversarial_a_renamed_section_and_a_title_cell_turned_into_code_are_found` |
| NB-009 | the comment lines are stripped from a code cell and the markdown cell before another is deleted: the check names the missing comment and the missing explanation | `tests/test_notebooks_layer.py::test_adversarial_a_code_cell_stripped_of_its_comment_and_its_explanation_is_found` |
| NB-010 | a package pin that is not in the requirements file, a data path that is no file and a widgets block with a cell timing are planted into the metadata: each fails naming the value | `tests/test_notebooks_layer.py::test_adversarial_a_package_data_path_and_widget_metadata_that_disagree_are_found` |
| NB-011 | an error output, a stderr stream, a wrong execution count, a Windows user path and a GitHub token pattern are planted: each fails | `tests/test_notebooks_layer.py::test_adversarial_an_error_a_stderr_stream_a_machine_path_and_a_token_are_found` |
| NB-012 | a 450 KB image is planted into an output: the check names the image and its limit | `tests/test_notebooks_layer.py::test_adversarial_an_image_above_the_limit_is_found` |
| NB-013 | the last cell is deleted from a Spanish notebook, so it stays a mirrored path but is no counterpart: the check fails on it | `tests/test_notebooks_layer.py::test_adversarial_a_cell_deleted_from_the_spanish_counterpart_is_found` |
| NB-014 | a pip magic is planted in a code cell, and the patterns of a data-root read and of a file write are shown to be seen by the gate: the check and the gate name them | `tests/test_notebooks_layer.py::test_adversarial_a_notebook_that_runs_pip_is_found`, `tests/test_notebooks_layer.py::test_adversarial_a_notebook_that_reads_the_data_root_or_writes_the_repository_is_seen_by_the_gate` |
| NB-015 | a DOI that the SDD does not list is planted into the sources of a notebook: the check names it as unlisted and as absent from the References | `tests/test_notebooks_layer.py::test_adversarial_a_source_the_sdd_does_not_list_and_a_reference_that_is_missing_are_found` |
| NB-016 | an unpinned line is appended to `notebooks/requirements.txt`: the check names the line | `tests/test_notebooks_layer.py::test_adversarial_an_unpinned_notebook_requirement_is_found` |
| NB-017 | a workflow that runs the notebooks is planted and the static step is removed from ci.yml: each fails | `tests/test_notebooks_layer.py::test_adversarial_a_ci_that_runs_the_notebooks_and_one_that_drops_the_static_step_are_found` |
| NB-018 | a limit of an adopted script is changed in a copy: its digest no longer equals the template's | `tests/test_notebooks_layer.py::test_adversarial_a_changed_adopted_script_is_not_the_template_script` |
| NB-019 | local-only: the execution gate needs the notebook environment, which CI does not install. An output of a notebook of a copy is edited by hand: the release gate exits 1 naming it stale | `tests/test_notebooks_layer.py::test_adversarial_a_hand_edited_output_fails_the_release_gate` |
| NB-020 | a code cell that reads the test rows of an artifact and never prints the baked version is planted: the gate sees it, and adding the print clears it | `tests/test_notebooks_layer.py::test_adversarial_a_notebook_that_recomputes_without_the_baked_version_is_seen_by_the_gate` |
| NB-021 | the last notebook of topic 01 is deleted in both languages (the mirror stays intact): the level plan 1, 1, 1, 2 is lost | `tests/test_notebooks_layer.py::test_adversarial_topic_one_with_a_dropped_notebook_loses_its_plan` |
