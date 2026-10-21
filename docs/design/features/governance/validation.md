# Validation: U15-P, the governance bake

Adversarial checks: what was planted, and the gate that must refuse it. Each gate is a test under `tests/adversarial/` or named `test_adversarial_*`.

| requirement | adversarial check | gate |
|---|---|---|
| CT-2301 | A document planted with an edge to an unknown entry or a cycle is refused by the checker and nothing is published. | `tests/governance/test_adversarial_governance.py::test_adversarial_an_edge_to_an_unknown_entry_or_a_cycle_is_refused` |
| CT-2302 | With the assignment extensions off the C06 and C08 variants have no fit, so each is listed in `excluded` and no entry is published without a variant. | `tests/governance/test_governance_failures.py::test_adversarial_the_pure_rule_leaves_a_variant_it_cannot_place_in_the_excluded_list_with_the_engines_reason` |
| CT-2303 | C05 ldp-sim-0 shares only a name prefix with a fit and must stay excluded. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_variant_assigned_to_a_fit_by_name_similarity_alone_stays_excluded` |
| CT-2304 | `matrix_tier` is forced to 4: the documents disagree with the independent checker and the bake publishes nothing. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_tier_the_engine_did_not_compute_is_refused` |
| CT-2305 | The tiers of the 19 cases of the addendum and of C02 and C20 are fixed by value, so a changed input fails. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_changed_tier_input_changes_the_entry_and_is_found` |
| CT-2306 | A row planted with a key no variant document holds is found by the checker. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_register_row_without_its_variant_document_is_found` |
| CT-2307 | `due_date` is shifted by one day: the bake refuses its documents. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_due_date_the_engine_did_not_compute_is_refused` |
| CT-2308 | A findings document dated before its raised dates, and an inventory dated after the changelog, are refused. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_wall_clock_as_of_date_is_refused` |
| CT-2309 | A changelog without the heading of a code version in use stops the bake instead of inventing a date. | `tests/governance/test_governance_failures.py::test_adversarial_a_release_the_changelog_does_not_know_stops_the_bake` |
| CT-2310 | The committed documents (written by another process, with another hash seed) must equal a fresh bake, so an order that depends on a set is found. | `tests/governance/test_governance_determinism.py::test_adversarial_the_committed_documents_are_what_the_bake_writes` |
| CT-2311 | The downstream file loses the line that names the upstream document: the check names the edge and the missing line. | `tests/governance/test_governance_edges.py::test_adversarial_an_edge_whose_downstream_file_stops_naming_the_upstream_fails_the_check` |
| CT-2312 | A variant document the manifest names is deleted: the bake stops naming the file and writes nothing. | `tests/governance/test_governance_failures.py::test_adversarial_a_variant_document_the_manifest_names_but_is_absent_stops_the_bake_and_writes_nothing` |
| CT-2313 | An approval, a Spanish approval and a compliance statement are planted in three documents; each is refused. | `tests/governance/test_adversarial_governance.py::test_adversarial_an_approval_text_planted_in_any_document_is_refused` |
| CT-2314 | A frequency table labelled regulatory and one whose basis names a regulatory requirement are planted; both are refused. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_convention_called_regulatory_is_refused` |
| CT-2315 | Unaccented Spanish is planted; the check finds it and the restoration table repairs it. | `tests/governance/test_governance_text.py::test_adversarial_an_unaccented_spanish_text_is_found_by_the_check_and_restored_by_the_table` |
| CT-2316 | A pointer emptied, a tag replaced by a guess, a factor pointer removed and a basis emptied are planted; each stops the bake naming the case. | `tests/governance/test_adversarial_governance.py::test_adversarial_an_input_without_its_pointer_or_tag_is_refused` |
| CT-2317 | A schedule that the engine did not compute is refused, so a local reimplementation would not survive. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_schedule_the_engine_did_not_compute_is_refused` |
| CT-2318 | The page is compared with a fresh render and must list the excluded variants; a typed figure fails. | `tests/governance/test_governance_page.py::test_adversarial_the_page_block_is_regenerated_not_typed` |
| CT-2319 | An unnamed difference fails the test, so a silently changed field is found; a changed input changes the entry. | `tests/governance/test_adversarial_governance.py::test_adversarial_a_tier_the_engine_did_not_compute_is_refused` |
| CT-2320 | An opinion forced to level 1 disagrees with the register's open findings and is refused. | `tests/governance/test_adversarial_governance.py::test_adversarial_an_opinion_the_engine_did_not_compute_is_refused` |
