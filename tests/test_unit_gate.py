"""M15 T1: the unit gate (CONTRACT 3 of CAOS_MANAGE conventions/units-gate.md), on synthetic documents and pairs.

CT-2402 (the four target kinds) and CT-2403 (a constant prediction is advisory) are the requirements these tests gate;
the path expressions, the spec errors, the ordering and the standard-library rule are the module's own contract.
"""
from __future__ import annotations

import ast
import copy
import json
import pathlib
import random

import pytest

from pipeline.stages import unit_gate as ug

MODULE = pathlib.Path(ug.__file__)


def pair(**kw):
    base = {"id": "p", "file": "*.json", "prediction": "pred", "target": "target", "kind": "series", "unit": "USD"}
    base.update(kw)
    return base


def run(pair_spec, doc, case="CX", rel="a.json"):
    return ug.check_document(case, rel, doc, {case: {"pairs": [pair_spec]}})


def classes(result):
    return sorted(v["class"] for v in result.violations + result.advisories)


# ---- CT-2402: the four kinds ---------------------------------------------------------------------------------------

def test_target_kinds():
    # series: [lo - span, hi + span] = [10 - 10, 20 + 10] = [0, 30]
    series = pair(kind="series")
    assert run(series, {"pred": [29.0], "target": [10, 20]}).violations == []
    assert run(series, {"pred": [-0.5], "target": [10, 20]}).violations[0]["class"] == "prediction_outside_observable"
    assert run(series, {"pred": [30.5], "target": [10, 20]}).violations[0]["class"] == "prediction_outside_observable"
    v = run(series, {"pred": [100.0, 200.0], "target": [10, 20]}).violations[0]
    assert v["target_range"] == [0.0, 30.0] and v["prediction_range"] == [100.0, 200.0] and v["blocking"] is True
    assert v["unit"] == "USD" and v["pair"] == "p" and v["case"] == "CX" and v["file"] == "a.json" and v["method"] is None

    # binary: the label domain [0, 1] widened by its span is [-1, 2]; a PD written in percent fails, a fraction passes
    binary = pair(kind="binary")
    assert run(binary, {"pred": [0.22, 0.5], "target": [0.1, 0.2]}).violations == []
    assert run(binary, {"pred": [1.9], "target": [0.1, 0.2]}).violations == []
    pct = run(binary, {"pred": [22.0, 25.0], "target": [0.1, 0.2]}).violations
    assert [v["class"] for v in pct] == ["prediction_outside_observable"] and pct[0]["target_range"] == [-1.0, 2.0]
    # a binary pair needs no published target
    assert run(pair(kind="binary", target=None), {"pred": [0.3, 0.4]}).violations == []
    assert run(pair(kind="binary", target=None), {"pred": [22.0]}).violations != []

    # scalar: [t - |t|, t + |t|]
    scalar = pair(kind="scalar")
    assert run(scalar, {"pred": [1.9], "target": 1.0}).violations == []
    assert run(scalar, {"pred": [2.1], "target": 1.0}).violations[0]["target_range"] == [0.0, 2.0]
    assert run(scalar, {"pred": [-1.9], "target": -1.0}).violations == []  # t negative: [-2, 0]
    assert run(scalar, {"pred": [-2.5], "target": -1.0}).violations[0]["target_range"] == [-2.0, 0.0]
    # scalar 0: the pair's zero_scale, else a spec error
    assert run(pair(kind="scalar", zero_scale=0.5), {"pred": [0.4], "target": 0.0}).violations == []
    z = run(pair(kind="scalar", zero_scale=0.5), {"pred": [0.6], "target": 0.0}).violations[0]
    assert z["target_range"] == [-0.5, 0.5]
    with pytest.raises(ug.UnitGateError, match="zero_scale"):
        run(scalar, {"pred": [0.1], "target": 0.0})

    # bound: finite and inside the domain, an open end is null, never compared with a target
    bound = pair(kind="bound", domain=[0, 1], reason="an upper confidence bound after few defaults", target=None)
    assert run(bound, {"pred": [0.0, 0.4, 1.0]}).violations == []
    b = run(bound, {"pred": [0.4, 22.0]}).violations  # a bound is checked value by value
    assert [v["class"] for v in b] == ["prediction_outside_observable"] and b[0]["target_range"] == [0.0, 1.0]
    open_end = pair(kind="bound", domain=[0, None], reason="a non-negative amount", target=None)
    assert run(open_end, {"pred": [0.0, 1e12]}).violations == []
    assert run(open_end, {"pred": [-1.0]}).violations != []
    # a bound is never compared with a target even when one is declared
    with_target = pair(kind="bound", domain=[0, 1], reason="conservative by design")
    assert run(with_target, {"pred": [0.9], "target": [1000.0]}).violations == []


def test_a_prediction_partly_inside_the_widened_range_passes():
    for kind, doc in (("series", {"pred": [15.0, 500.0], "target": [10, 20]}),
                      ("scalar", {"pred": [1.5, 90.0], "target": 1.0}),
                      ("binary", {"pred": [0.2, 22.0], "target": [0.1, 0.2]})):
        assert run(pair(kind=kind), doc).violations == [], kind
    # every prediction outside, on both sides, still fails
    assert run(pair(kind="series"), {"pred": [-50.0, 500.0], "target": [10, 20]}).violations != []


def test_the_range_slack_is_one_full_range():
    assert ug.RANGE_SLACK == 1.0


def test_series_with_zero_span_needs_zero_scale():
    flat = {"pred": [10.5], "target": [10.0, 10.0]}
    with pytest.raises(ug.UnitGateError, match="zero_scale"):
        run(pair(kind="series"), flat)
    assert run(pair(kind="series", zero_scale=1.0), flat).violations == []
    assert run(pair(kind="series", zero_scale=1.0), {"pred": [12.0], "target": [10.0, 10.0]}).violations != []


# ---- CT-2403: a constant prediction ---------------------------------------------------------------------------------

def test_constant_prediction_is_advisory():
    r = run(pair(kind="series"), {"pred": [15.0, 15.0, 15.0], "target": [10, 20]})
    assert r.violations == []
    assert [a["class"] for a in r.advisories] == ["degenerate_constant_prediction"]
    assert r.advisories[0]["blocking"] is False
    assert ug.blocking(r.advisories) == []
    # a constant over a target that does not vary is no advisory (a scalar truth never varies)
    assert run(pair(kind="scalar"), {"pred": [1.0, 1.0], "target": 1.0}).advisories == []
    # one prediction is not constant over anything
    assert run(pair(kind="series"), {"pred": [15.0], "target": [10, 20]}).advisories == []
    # a constant that lies outside is the blocking class only
    assert classes(run(pair(kind="series"), {"pred": [99.0, 99.0], "target": [10, 20]})) == ["prediction_outside_observable"]


# ---- non-finite -----------------------------------------------------------------------------------------------------

def test_a_non_finite_prediction_blocks():
    for bad in (float("nan"), float("inf"), float("-inf")):
        r = run(pair(kind="series"), {"pred": [15.0, bad], "target": [10, 20]})
        assert [v["class"] for v in r.violations] == ["non_finite_prediction"], bad
        assert r.violations[0]["blocking"] is True
    # on a bound too
    b = pair(kind="bound", domain=[0, 1], reason="r", target=None)
    assert [v["class"] for v in run(b, {"pred": [float("nan")]}).violations] == ["non_finite_prediction"]


def test_booleans_and_text_are_not_numbers():
    with pytest.raises(ug.UnitGateError, match="not a number"):
        run(pair(), {"pred": [True], "target": [10, 20]})
    with pytest.raises(ug.UnitGateError, match="not a number"):
        run(pair(), {"pred": [1.0], "target": [True, 20]})
    with pytest.raises(ug.UnitGateError, match="not a number"):
        run(pair(), {"pred": ["0.2"], "target": [10, 20]})


def test_a_null_in_a_prediction_is_refused_never_passed():
    # the rule and the design do not class a JSON null (how an artifact writes NaN); the gate refuses it loudly
    with pytest.raises(ug.UnitGateError, match="null"):
        run(pair(), {"pred": [15.0, None], "target": [10, 20]})


# ---- path expressions -----------------------------------------------------------------------------------------------

def test_array_walk_and_method_binding():
    doc = {"outputs": {"rungs": {"m_a": {"reliability": [{"pd": 0.2}, {"pd": 0.3}]},
                                 "m_b": {"reliability": [{"pd": 22.0}, {"pd": 25.0}]}},
                       "obs": [{"rate": 0.1}, {"rate": 0.2}]}}
    p = pair(kind="binary", prediction="outputs.rungs.<m>.reliability[].pd", target="outputs.obs[].rate", unit="probability")
    r = run(p, doc)
    assert [(v["method"], v["class"]) for v in r.violations] == [("m_b", "prediction_outside_observable")]
    assert r.pairs_checked == 1


def test_method_binding_names_the_method_in_every_violation():
    doc = {"o": {f"m{i}": {"v": [900.0 + i]} for i in range(5)}, "t": [1.0, 2.0]}
    r = run(pair(prediction="o.<m>.v", target="t"), doc)
    assert [v["method"] for v in r.violations] == [f"m{i}" for i in range(5)]
    assert all(v["method"] is not None for v in r.violations)


def test_a_glob_segment_walks_the_matching_keys_and_names_them():
    doc = {"o": {"pd_a": {"mean": 5.0}, "pd_b": {"mean": 900.0}, "other": {"mean": 900.0}}, "t": 5.0}
    r = run(pair(kind="scalar", prediction="o.pd_*.mean", target="t"), doc)
    assert [(v["method"]) for v in r.violations] == ["pd_b"]  # `other` is not matched; `pd_a` is inside


def test_a_leaf_list_is_an_array_and_nested_arrays_flatten():
    doc = {"o": {"m": {"v": [0.1, 0.2]}}, "g": [{"v": [1.0, 2.0]}, {"v": [3.0]}]}
    assert run(pair(prediction="o.<m>.v", target="g[].v", kind="series"), doc).violations == []


def test_group_by_checks_each_element_as_its_own_pair():
    # C04 style: each rung carries its own truth; a pooled series would hide rung 1 inside rung 0's range
    doc = {"outputs": {"rungs": [
        {"truth": 1.0, "estimators": {"ml": {"mean": 150.0}, "mom": {"mean": 1.1}}},
        {"truth": 100.0, "estimators": {"ml": {"mean": 150.0}, "mom": {"mean": 130.0}}},
    ]}}
    p = pair(kind="scalar", group_by="outputs.rungs[]", prediction="outputs.rungs[].estimators.<m>.mean",
             target="outputs.rungs[].truth")
    r = run(p, doc)
    assert [(v["element"], v["method"]) for v in r.violations] == [(0, "ml")]  # 150 is inside rung 1's range only
    assert r.violations[0]["target_range"] == [0.0, 2.0] and r.violations[0]["prediction_range"] == [150.0, 150.0]
    assert r.pairs_checked == 1
    # the same pair without group_by sees one pooled target series of two scalars: a spec error for a scalar
    with pytest.raises(ug.UnitGateError, match="exactly one"):
        run(pair(kind="scalar", prediction="outputs.rungs[].estimators.<m>.mean", target="outputs.rungs[].truth"), doc)


def test_group_by_must_be_a_prefix_of_both_paths_and_end_in_an_array():
    doc = {"a": [{"p": 1.0, "t": 1.0}]}
    with pytest.raises(ug.UnitGateError, match="group_by"):
        run(pair(kind="scalar", group_by="a", prediction="a[].p", target="a[].t"), doc)
    with pytest.raises(ug.UnitGateError, match="group_by"):
        run(pair(kind="scalar", group_by="b[]", prediction="a[].p", target="a[].t"), doc)


# ---- spec errors ----------------------------------------------------------------------------------------------------

def test_a_path_that_resolves_to_nothing_is_a_spec_error_naming_pair_and_path():
    doc = {"pred": [1.0], "target": [1.0, 2.0]}
    with pytest.raises(ug.UnitGateError) as e:
        run(pair(id="the-pair", prediction="nope.x[]"), doc)
    assert "the-pair" in str(e.value) and "nope.x[]" in str(e.value)
    with pytest.raises(ug.UnitGateError) as e:
        run(pair(id="the-pair", target="gone"), doc)
    assert "the-pair" in str(e.value) and "gone" in str(e.value)
    with pytest.raises(ug.UnitGateError, match="<m>"):
        run(pair(prediction="pred.<m>.v"), doc)  # a map walk over a list finds nothing
    # an empty array resolves to nothing too
    with pytest.raises(ug.UnitGateError):
        run(pair(), {"pred": [], "target": [1.0, 2.0]})


def test_group_by_names_the_element_whose_path_resolves_to_nothing():
    doc = {"a": [{"p": 1.0, "t": 1.0}, {"t": 1.0}]}
    with pytest.raises(ug.UnitGateError, match=r"element 1"):
        run(pair(kind="scalar", group_by="a[]", prediction="a[].p", target="a[].t"), doc)


def test_pair_specification_errors():
    doc = {"pred": [1.0], "target": [1.0, 2.0]}
    with pytest.raises(ug.UnitGateError, match="kind"):
        run(pair(kind="ratio"), doc)
    with pytest.raises(ug.UnitGateError, match="reason"):
        run(pair(kind="bound", domain=[0, 1], target=None), doc)
    with pytest.raises(ug.UnitGateError, match="reason"):
        run(pair(kind="bound", domain=[0, 1], reason="  ", target=None), doc)
    with pytest.raises(ug.UnitGateError, match="domain"):
        run(pair(kind="bound", reason="r", target=None), doc)
    with pytest.raises(ug.UnitGateError, match="domain"):
        run(pair(kind="bound", reason="r", domain=[1, 0], target=None), doc)
    for missing in ("id", "file", "prediction", "kind", "unit"):
        bad = pair()
        del bad[missing]
        with pytest.raises(ug.UnitGateError, match=missing):
            run(bad, doc)
    with pytest.raises(ug.UnitGateError, match="target"):
        run(pair(target=None), doc)  # series and scalar need their target
    with pytest.raises(ug.UnitGateError, match="zero_scale"):
        run(pair(zero_scale=-1.0), doc)


def test_validate_spec_names_the_case_and_pair():
    good = {"C1": {"pairs": [pair()]}, "C2": {"not_applicable": "nothing is predicted"}}
    ug.validate_spec(good)
    bad = {"C1": {"pairs": [pair(kind="bound", domain=[0, 1], target=None)]}}
    with pytest.raises(ug.UnitGateError, match=r"C1.*p.*reason"):
        ug.validate_spec(bad)
    with pytest.raises(ug.UnitGateError, match="C3"):
        ug.validate_spec({"C3": {"unknown_key": 1}})
    with pytest.raises(ug.UnitGateError, match="C4"):
        ug.validate_spec({"C4": {"pairs": [pair(), pair()]}})  # duplicate pair id


# ---- the document, the case entry and the file glob -----------------------------------------------------------------

def test_a_case_without_pairs_checks_nothing_and_records_its_entry_kind():
    doc = {"pred": [999.0], "target": [1.0, 2.0]}
    spec = {"CB": {"bake_only": {"hook": "cases/c13/measure.py", "reason": "r"}},
            "CW": {"withheld": [pair()]},
            "CN": {"not_applicable": "nothing is predicted and scored against a target"},
            "CP": {"pairs": [pair(file="other.json")]}}
    for case, kind in (("CB", "bake_only"), ("CW", "withheld"), ("CN", "not_applicable"), ("CX", "none")):
        r = ug.check_document(case, "a.json", doc, spec)
        assert (r.violations, r.advisories, r.pairs_checked, r.entry) == ([], [], 0, kind), case
    # a file that matches no pair's glob checks nothing
    r = ug.check_document("CP", "a.json", doc, spec)
    assert (r.violations, r.pairs_checked, r.entry) == ([], 0, "pairs")


def test_the_file_glob_is_matched_against_the_relative_path():
    doc = {"pred": [999.0], "target": [1.0, 2.0]}
    spec = {"CX": {"pairs": [pair(file="xi-*.json")]}}
    assert ug.check_document("CX", "xi-0-96.json", doc, spec).violations != []
    assert ug.check_document("CX", "other.json", doc, spec).pairs_checked == 0
    assert ug.check_document("CX", "sub/xi-0-96.json", doc, spec).pairs_checked == 0


def test_check_pair_returns_the_violations_and_advisories_of_one_pair():
    out = ug.check_pair("CX", "a.json", {"pred": [15.0, 15.0], "target": [10, 20]}, pair())
    assert [v["class"] for v in out] == ["degenerate_constant_prediction"]


def test_the_input_document_is_not_modified():
    doc = {"o": {"m": {"v": [900.0]}}, "t": [1.0, 2.0]}
    before = copy.deepcopy(doc)
    run(pair(prediction="o.<m>.v", target="t"), doc)
    assert doc == before


# ---- determinism ----------------------------------------------------------------------------------------------------

def _shuffled(node, rng):
    if isinstance(node, dict):
        items = [(k, _shuffled(v, rng)) for k, v in node.items()]
        rng.shuffle(items)
        return dict(items)
    if isinstance(node, list):
        return [_shuffled(v, rng) for v in node]
    return node


def test_violations_are_ordered_by_pair_method_and_element_whatever_the_dict_order():
    doc = {"o": {f"m{i}": {"v": [900.0 + i]} for i in range(6)}, "q": {f"n{i}": {"v": [-900.0]} for i in range(3)},
           "t": [1.0, 2.0]}
    spec = {"CX": {"pairs": [pair(id="zeta", prediction="o.<m>.v", target="t"), pair(id="alpha", prediction="q.<m>.v", target="t")]}}
    base = ug.check_document("CX", "a.json", doc, spec)
    order = [(v["pair"], v["method"]) for v in base.violations]
    assert order == sorted(order) and order[0][0] == "alpha" and len(order) == 9
    for seed in range(8):
        shuffled = _shuffled(doc, random.Random(seed))
        again = ug.check_document("CX", "a.json", shuffled, spec)
        assert json.dumps(again.violations, sort_keys=False) == json.dumps(base.violations, sort_keys=False)


def test_group_by_elements_are_ordered_by_index():
    doc = {"a": [{"p": 900.0, "t": 1.0} for _ in range(4)]}
    r = run(pair(kind="scalar", group_by="a[]", prediction="a[].p", target="a[].t"), doc)
    assert [v["element"] for v in r.violations] == [0, 1, 2, 3]


# ---- blocking -------------------------------------------------------------------------------------------------------

def test_blocking_selects_the_blocking_subset():
    vs = [{"blocking": True, "class": "a"}, {"blocking": False, "class": "b"}, {"class": "c"}]
    assert [v["class"] for v in ug.blocking(vs)] == ["a", "c"]


# ---- the standard-library rule --------------------------------------------------------------------------------------

def test_the_module_imports_nothing_outside_the_standard_library_subset():
    allowed = {"math", "json", "fnmatch", "dataclasses", "typing", "re", "__future__"}
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    seen: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            seen.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "a relative import reaches into the package"
            seen.add((node.module or "").split(".")[0])
    assert seen and seen <= allowed, sorted(seen - allowed)


def test_the_module_loads_by_path_without_the_package():
    import importlib.util

    spec = importlib.util.spec_from_file_location("unit_gate_by_path", MODULE)
    mod = importlib.util.module_from_spec(spec)
    import sys
    sys.modules["unit_gate_by_path"] = mod  # dataclasses resolve their module through sys.modules
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop("unit_gate_by_path", None)
    r = mod.check_document("CX", "a.json", {"pred": [999.0], "target": [1.0, 2.0]},
                           {"CX": {"pairs": [pair()]}})
    assert [v["class"] for v in r.violations] == ["prediction_outside_observable"]
