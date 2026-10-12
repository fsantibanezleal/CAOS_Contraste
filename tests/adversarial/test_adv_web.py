"""Plants for the requirements whose gate is a web test (vitest): CT-004, CT-104, CT-105, CT-112 to CT-114, CT-209,
CT-210, CT-215, CT-216, CT-308, CT-309, CT-410 to CT-412. Each plants one defect in a copy (a committed artifact or a
source file of the frontend), runs the web test on the copy with the installed packages linked in, and asserts the clean
copy passes and the planted one fails naming the check.

They need node and `npm ci` in frontend/ (the validation rows say `local-only`); the pipeline-side twin of each exists
in the other test_adv_* files wherever the requirement has a pipeline side."""
from __future__ import annotations

from pathlib import Path

import pytest
from planting import WEB_READY, edit, edit_json, prune_planned_cases, refute_web

pytestmark = pytest.mark.skipif(not WEB_READY, reason="needs node and `npm ci` in frontend/")


def _json(rel: str, fn):
    return lambda r: edit_json(r, rel, fn)


def test_ct004_an_undeclared_key_in_a_committed_index_is_found_by_the_contract_test(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["invented_key"] = 1

    refute_web(repo, "src/lib/contract.test.ts", _json("data/derived/manifests/index.json", mutate), "CONTRACT 2",
               prepare=prune_planned_cases)


def test_ct004_a_family_contract_key_the_web_does_not_declare_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["invented_key"] = 1

    refute_web(repo, "src/lib/contract.test.ts", _json("data/derived/contract/scored_sample.json", mutate), "CONTRACT 1",
               prepare=prune_planned_cases)


def test_ct104_a_threshold_labelled_regulatory_without_a_paragraph_reference_is_found(repo: Path) -> None:
    refute_web(repo, "src/lib/labels.test.ts",
               lambda r: edit(r, "frontend/src/lib/policy.ts", "Policy threshold, not regulatory", "Regulatory threshold"),
               "threshold labels", prepare=prune_planned_cases)


def test_ct105_a_committed_score_one_point_off_the_live_scorecard_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["sample"]["scorecard_score"][0] += 1

    refute_web(repo, "src/engine/parity.test.ts", _json("data/derived/C01/holdout.json", mutate), "scorecard points, scores and PDs",
               prepare=prune_planned_cases)


def test_ct112_a_renamed_group_of_the_instrument_is_found_by_the_order_test(repo: Path) -> None:
    refute_web(repo, "src/workbench/workbench.test.tsx",
               lambda r: edit(r, "frontend/src/workbench/Workbench.tsx", "label: { en: 'Validation', es: 'Validación' }",
                              "label: { en: 'Checks', es: 'Validación' }"),
               "the instrument groups are the six questions, in order")


def test_ct113_a_view_without_its_lane_badge_is_found(repo: Path) -> None:
    refute_web(repo, "src/workbench/workbench.test.tsx",
               lambda r: edit(r, "frontend/src/workbench/ContextView.tsx",
                              "<PlotCard title={{ en: 'The case', es: 'El caso' }} lane={REPLAY}",
                              "<PlotCard title={{ en: 'The case', es: 'El caso' }}"),
               "a view without its lane")


def test_ct114_a_context_that_does_not_name_the_licence_class_of_a_source_is_found(repo: Path) -> None:
    refute_web(repo, "src/workbench/workbench.test.tsx",
               lambda r: edit(r, "frontend/src/workbench/ContextView.tsx", "data-licence-class={s?.class}", 'data-licence-class="unstated"'),
               "context names sources, licences and truth status")


def test_ct209_an_irb_risk_weight_one_part_in_a_million_off_the_live_port_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["parity"]["irb"][0]["risk_weight"] *= 1.000001

    refute_web(repo, "src/engine/credit.test.ts", _json("data/derived/C05/sp-2010.json", mutate), "the IRB risk weight equals regulatory.irb")


def test_ct210_a_renamed_group_of_the_c05_instrument_is_found_by_the_order_test(repo: Path) -> None:
    refute_web(repo, "src/workbench/c05.test.tsx",
               lambda r: edit(r, "frontend/src/workbench/c05/instrument.tsx", "label: { en: 'Validation', es: 'Validación' }",
                              "label: { en: 'Checks', es: 'Validación' }"),
               "the groups are the six questions, in order")


def test_ct215_a_retail_risk_weight_one_part_in_a_million_off_the_live_port_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["outputs"]["irb"]["parity"][0]["risk_weight"] *= 1.000001

    refute_web(repo, "src/engine/credit.test.ts", _json("data/derived/C01/holdout.json", mutate), "retail risk weight equals regulatory.irb")


def test_ct216_a_capital_view_that_does_not_flag_an_lgd_below_the_floor_is_found(repo: Path) -> None:
    refute_web(repo, "src/workbench/workbench.test.tsx",
               lambda r: edit(r, "frontend/src/workbench/CapitalView.tsx", 'data-lgd-floor="below"', 'data-lgd-floor="ok"'),
               "flags a rail LGD below the Basel III input floor")


def test_ct308_an_exact_rejection_probability_one_part_in_a_million_off_the_live_port_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["fit"]["parity"][0]["probability"] *= 1.000001

    refute_web(repo, "src/engine/sizepower.test.ts", _json("data/derived/C22/models-generators.json", mutate), "CT-308")


def test_ct309_a_renamed_group_of_the_c22_instrument_is_found_by_the_order_test(repo: Path) -> None:
    refute_web(repo, "src/workbench/c22.test.tsx",
               lambda r: edit(r, "frontend/src/workbench/c22/instrument.tsx", "label: { en: 'Validation', es: 'Validación' }",
                              "label: { en: 'Checks', es: 'Validación' }"),
               "the groups are the six questions, in order")


def test_ct410_a_projected_default_rate_one_part_in_a_million_off_the_live_port_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["fit"]["parity"]["projection"][0]["default_rate"][3] *= 1.000001

    refute_web(repo, "src/engine/transitions.test.ts", _json("data/derived/C04/models-transitions.json", mutate), "transitions.test.ts")


def test_ct411_an_interval_bound_one_part_in_a_million_off_the_live_port_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["fit"]["parity"]["intervals"][0]["agresti_coull"][1] *= 1.000001

    refute_web(repo, "src/engine/transitions.test.ts", _json("data/derived/C04/models-transitions.json", mutate), "transitions.test.ts")


def test_ct411_a_capital_risk_weight_one_part_in_a_million_off_the_live_port_is_found(repo: Path) -> None:
    def mutate(d: dict) -> None:
        d["fit"]["parity"]["capital"][0]["risk_weight"] *= 1.000001

    refute_web(repo, "src/engine/transitions.test.ts", _json("data/derived/C04/models-transitions.json", mutate), "transitions.test.ts")


def test_ct412_a_renamed_group_of_the_c04_instrument_is_found_by_the_order_test(repo: Path) -> None:
    refute_web(repo, "src/workbench/c04.test.tsx",
               lambda r: edit(r, "frontend/src/workbench/c04/instrument.tsx", "label: { en: 'Validation', es: 'Validación' }",
                              "label: { en: 'Checks', es: 'Validación' }"),
               "the groups are the six questions, in order")
