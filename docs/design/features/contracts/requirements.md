# Requirements: U0, the contracts, the sources and their licences

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.
Design: [`design.md`](design.md). Tasks: [`tasks.md`](tasks.md).

| ID | Requirement | Gate |
|---|---|---|
| CT-001 | WHEN an ingested record violates its family contract, THE ingest stage SHALL reject it and report the field, the expected range and the policy applied. | `tests/test_contract.py::test_reject_out_of_range` |
| CT-002 | WHEN an artifact's lineage includes a link-only or unusable source, THE export stage SHALL refuse to write it. | `tests/test_licence_lineage.py::test_refuses_link_only_source` |
| CT-003 | THE export stage SHALL write `truth_status` and the licence class of every input into every artifact. | `tests/test_licence_lineage.py::test_export_writes_provenance`, `scripts/check_provenance.py` |
| CT-004 | THE TypeScript artifact and contract types SHALL mirror what the pipeline writes, in both directions. | `frontend/src/lib/contract.test.ts::CONTRACT 1: the exported family contracts are exactly what the web declares` |
| CT-005 | THE default install SHALL contain no AGPL, GPL or BSL package. | `scripts/check_licences.py` |
| CT-006 | THE repository SHALL not commit raw rows from a derived-only, link-only or unusable source. | `scripts/check_data_classes.py` |
| CT-007 | THE public content SHALL contain no em-dash and no emoji. | `scripts/check_content_standards.py` |
| CT-008 | WHEN a source is fetched, THE fetcher SHALL write a licence-manifest row with the URL, the retrieval date, the licence class, the licence text and the SHA-256 and byte count of every file. | `tests/test_sources.py::test_fetch_writes_manifest_row` |
| CT-009 | THE source registry SHALL give every source one of the four licence classes and a verbatim licence fragment, and SHALL refuse to load a case that reads a link-only or unusable source. | `tests/test_sources.py::test_registry_classes_valid` |
| CT-010 | THE fetcher SHALL write raw files under the device data root and SHALL refuse a data root inside the repository. | `tests/test_sources.py::test_data_root_outside_repository` |
| CT-011 | IF a fetched file's hash differs from the hash the manifest pins, THEN THE fetcher SHALL fail and name the file, unless the refresh is explicit. | `tests/test_sources.py::test_hash_drift_fails` |
| CT-012 | THE examples of the bring-your-own-model guide SHALL be a pure function of their seed, so regenerating them writes identical bytes. | `tests/test_own_sample.py::test_examples_regenerate_identically` |
| CT-013 | WHEN a reader's scored sample is validated, THE battery SHALL find the known truth of the committed examples: the calibrated sample green on every level test, the shifted and under-estimated sample red on the PSI and on every level test and green on the AUC against the initial validation. | `tests/test_own_sample.py::test_calibrated_sample_passes_the_level_tests`, `tests/test_own_sample.py::test_shifted_underestimated_sample_is_found` |
| CT-014 | WHEN a reader's scored sample is validated, THE tool SHALL pass every record through contract 1 before the battery and SHALL write its report only outside the repository. | `tests/test_own_sample.py::test_contract_rejects_before_the_battery`, `tests/test_own_sample.py::test_report_never_written_inside_the_repository` |
