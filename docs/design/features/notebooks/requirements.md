# Requirements: the product notebooks (unit U17-A)

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
The notebooks are the product's didactic layer (CAOS_MANAGE `conventions/product-notebooks.md`, Felipe 2026-10-20): the folder
`notebooks/` holds two trees, `en/` and `es/`, with the same notebooks at the same relative paths, by topic and from simple to
complex (level 1 fundamentals, 2 the method in practice, 3 state of the art, 4 beyond it). They import the engine
`riskvalidation` and the pipeline's readers and never re-implement a method. The layer is the template 0.10.000 layer, adapted:
the static check `scripts/check_notebooks.py` (CI and local) and the runner `scripts/run_notebooks.py` are the template's scripts
byte for byte; the execution (`run_notebooks.py --check`) is a local release gate that never runs in CI (ADR-0074). The
description of the layer is [`notebooks/README.md`](../../../../notebooks/README.md); the adversarial checks are
[`validation.md`](validation.md). U17-A delivers the scaffold, topic 01 and the SDD claims; each later unit adds its topic folder.

| ID | Requirement | Gate |
|---|---|---|
| NB-001 | THE notebooks folder SHALL hold `README.md`, `requirements.txt`, `en/README.md` and `es/README.md`, and each topic folder SHALL hold only notebooks. | `tests/test_notebooks_layer.py::test_the_notebooks_layout_is_complete` |
| NB-002 | THE two language trees SHALL hold the same relative paths. | `tests/test_notebooks_layer.py::test_the_two_trees_mirror_each_other` |
| NB-003 | THE topics and the notebooks SHALL be numbered with two digits, contiguous from 01. | `tests/test_notebooks_layer.py::test_topics_and_notebooks_are_numbered_without_gaps` |
| NB-004 | THE level of a notebook SHALL never be lower than the level of the notebook before it in its topic, and EVERY topic SHALL have a level 1 and a level 2 notebook. | `tests/test_notebooks_layer.py::test_levels_never_decrease_and_every_topic_has_levels_one_and_two` |
| NB-005 | IF a topic has no level 3 notebook, THEN its row of each language's index SHALL give the reason, and EACH index SHALL list every notebook of its tree. | `tests/test_notebooks_layer.py::test_every_index_row_gives_its_reason_and_lists_every_notebook` |
| NB-006 | EVERY claim of the SDD section Beyond the state of the art SHALL be covered by a level 4 notebook in each language, except the claims whose topic unit has not landed, which the test names. | `tests/test_notebooks_layer.py::test_every_sdd_claim_is_covered_by_a_level_four_notebook_or_is_pending` |
| NB-007 | EVERY claim of the SDD section Beyond the state of the art SHALL name at least one committed evidence path, and every path SHALL exist. | `tests/test_notebooks_layer.py::test_every_sdd_claim_names_its_committed_evidence` |
| NB-008 | EACH notebook SHALL begin with a markdown cell and carry the second-level sections its level requires, in its tree's language and in order. | `tests/test_notebooks_layer.py::test_every_notebook_has_the_anatomy_of_its_level` |
| NB-009 | EVERY code cell SHALL be directly preceded by a markdown cell and SHALL carry a comment line. | `tests/test_notebooks_layer.py::test_every_code_cell_is_explained_and_commented` |
| NB-010 | THE caos metadata of a notebook SHALL agree with its tree, its folder, the pins of `notebooks/requirements.txt` and the repository's files, and the notebook metadata SHALL hold only kernelspec, language_info and caos. | `tests/test_notebooks_layer.py::test_the_metadata_agrees_with_the_tree_the_pins_and_the_repository` |
| NB-011 | THE execution counts of a notebook SHALL run 1, 2, 3 in order, and NO notebook SHALL hold an error output, a stderr stream, a machine path or a token. | `tests/test_notebooks_layer.py::test_the_committed_outputs_are_clean_and_in_order` |
| NB-012 | A notebook SHALL stay within the size limit of a notebook and each image within the limit of an image. | `tests/test_notebooks_layer.py::test_the_committed_outputs_are_clean_and_in_order` |
| NB-013 | A notebook and its counterpart in the other language SHALL carry the same level, packages, data and beyond claims, the same sequence of cell kinds and the same printed outputs. | `tests/test_notebooks_layer.py::test_a_spanish_notebook_has_the_cells_and_the_numbers_the_english_one_has` |
| NB-014 | A notebook SHALL never run `pip` or `conda`, SHALL read only committed files (never the data root), SHALL write nothing into the repository, and ITS Setup section SHALL show `pip install -r notebooks/requirements.txt`. | `tests/test_notebooks_layer.py::test_a_notebook_never_installs_and_never_needs_the_data_root_or_writes_the_repository` |
| NB-015 | EVERY source a notebook names in its metadata SHALL be a source the SDD lists and SHALL appear in its References section. | `tests/test_notebooks_layer.py::test_every_source_a_notebook_cites_is_listed_in_the_sdd_and_in_its_references` |
| NB-016 | THE pins of `notebooks/requirements.txt` SHALL be exact and SHALL be rows of the SDD technology table (the engine by its row). | `tests/test_notebooks_layer.py::test_the_notebook_pins_are_exact_and_the_sdd_technology_table_holds_them` |
| NB-017 | THE CI SHALL run `check_notebooks.py` and `check_readme_areas.py` and SHALL never execute the notebooks. | `tests/test_notebooks_layer.py::test_the_ci_runs_the_static_checks_and_never_the_notebooks` |
| NB-018 | THE three adopted scripts SHALL be the template's scripts of release v0.10.000, byte for byte. | `tests/test_notebooks_layer.py::test_the_adopted_scripts_are_the_template_scripts_byte_for_byte` |
| NB-019 | EVERY notebook SHALL execute top to bottom in a fresh kernel with committed outputs equal to a fresh run, as a local release gate. | `tests/test_notebooks_layer.py::test_every_notebook_runs_top_to_bottom_in_a_fresh_kernel` |
| NB-020 | A notebook that reads the test rows of a committed artifact SHALL print the engine version that baked it beside the installed version, and SHALL never rewrite a committed document. | `tests/test_notebooks_layer.py::test_a_notebook_that_reads_test_rows_prints_the_engine_version_that_baked_them` |
| NB-021 | TOPIC 01 SHALL hold four notebooks in each language, of levels 1, 1, 1 and 2. | `tests/test_notebooks_layer.py::test_topic_one_has_its_four_notebooks_in_both_languages` |
