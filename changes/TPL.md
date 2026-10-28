- Template adoption, CAOS_PRODUCT_TEMPLATE 0.11.000 to 0.12.000 (`.template-version`), every change that is not a notebook: the base guards' own updates
  (`scripts/check_ci_budget.py`, `scripts/check_content_standards.py` with its UTF-8 diagnostics, `scripts/instantiate.py`), the base guards' tests
  (`tests/test_guards.py` with the static example-bound guard, `tests/test_check_artifacts.py`, `tests/test_check_notebooks.py`,
  `tests/test_check_readme_areas.py`, `tests/test_spec_guards.py`, the shared adversarial fixtures `adversarial_fixtures.py`, `planting.py` and
  `notebook_bar_helpers.py`, the notebook bar's refutations), the CI steps of the tag (technology matrix, contract versions, contract catalog,
  readiness, provider rows), Vite pinned at 8.3.5 (the Windows command-execution advisories), the five documentation routes and the workbench
  lazy-loaded behind one Suspense, and React and KaTeX split into shared runtime chunks.
- Kept as Contraste's own: katex stays at 0.16.47 (the SDD records that 0.19.0 was not adopted), the shell stays at 0.19.5, the example-bound
  tests of the base guards stay out of `tests/` (the product has no example), and the planted-defect suite is not a CI step (it holds the
  product's own plants, which need the pipeline; it runs locally, ADR-0074).
