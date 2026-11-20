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


def test_a_null_prediction_is_missing_recorded_and_never_checked():
    # the main session's ruling (2026-11-15): a null is a missing value, counted as an advisory, never range-checked, never
    # blocking; NaN and infinity, which the bake meets in memory before any null is written, stay non-finite and blocking
    r = run(pair(), {"pred": [15.0, None], "target": [10, 20]})
    assert r.violations == []
    assert [(a["class"], a["blocking"]) for a in r.advisories] == [("missing_prediction", False)]
    assert "1 of 2 predictions are null" in r.advisories[0]["detail"]
    only = run(pair(), {"pred": [None, None], "target": [10, 20]})
    assert only.violations == [] and [a["class"] for a in only.advisories] == ["missing_prediction"]
    outside = run(pair(), {"pred": [500.0, None], "target": [10, 20]})
    assert [v["class"] for v in outside.violations] == ["prediction_outside_observable"]
    assert [a["class"] for a in outside.advisories] == ["missing_prediction"]
    nan = run(pair(), {"pred": [float("nan"), None], "target": [10, 20]})
    assert [v["class"] for v in nan.violations] == ["non_finite_prediction"]


def test_adversarial_a_target_of_nulls_only_is_an_error_and_a_null_target_value_is_left_out():
    with pytest.raises(ug.UnitGateError, match="nulls only"):
        run(pair(), {"pred": [15.0], "target": [None, None]})
    r = run(pair(), {"pred": [15.0], "target": [10, None, 20]})
    assert r.violations == [] and r.advisories == []


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


# ---- M15 T2 (CT-2405): the specification of every built case -----------------------------------------------------------

import fnmatch  # noqa: E402

from pipeline import registry  # noqa: E402

ROOT = MODULE.parents[3]
SPEC_PATH = ROOT / "data-pipeline" / "config" / "unit_pairs.json"
DERIVED = ROOT / "data" / "derived"


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    assert not dup, f"duplicate key(s) {dup} in {SPEC_PATH.name}"
    return dict(pairs)


def load_spec():
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)


def committed(case):
    return sorted(p.name for p in (DERIVED / case).glob("*.json"))


def pairs_of(spec, keys=("pairs", "withheld")):
    for case, entry in spec.items():
        for key in keys:
            for p in entry.get(key, []):
                yield case, key, p


def matched_files(case, p):
    return [f for f in committed(case) if fnmatch.fnmatchcase(f, p["file"])]


def read(case, rel):
    return json.loads((DERIVED / case / rel).read_text(encoding="utf-8"))


def test_every_built_case_is_covered():
    spec = load_spec()
    built = [c.id for c in registry.built_cases()]
    assert sorted(spec) == sorted(built), (
        f"missing from unit_pairs.json: {sorted(set(built) - set(spec))}; not a built case: {sorted(set(spec) - set(built))}")
    for case, entry in spec.items():
        assert set(entry) <= set(ug.ENTRY_KINDS), case
        assert entry.keys() & {"pairs", "bake_only", "not_applicable"}, f"{case} has no pairs, bake_only or not_applicable"


def test_the_specification_is_valid():
    ug.validate_spec(load_spec())


def test_a_bound_pair_without_a_reason_is_invalid():
    bound = {"id": "b", "file": "*.json", "prediction": "x", "target": None, "kind": "bound", "unit": "probability", "domain": [0, 1]}
    with pytest.raises(ug.UnitGateError, match="reason"):
        ug.validate_spec({"CX": {"pairs": [bound]}})
    ug.validate_spec({"CX": {"pairs": [{**bound, "reason": "an upper bound is conservative by design"}]}})


def test_an_unknown_kind_and_an_unknown_field_are_invalid():
    base = {"id": "p", "file": "*.json", "prediction": "x", "target": "y", "kind": "series", "unit": "USD"}
    with pytest.raises(ug.UnitGateError, match="kind"):
        ug.validate_spec({"CX": {"pairs": [{**base, "kind": "ratio"}]}})
    with pytest.raises(ug.UnitGateError, match="unknown field"):
        ug.validate_spec({"CX": {"pairs": [{**base, "tolerance": 0.1}]}})


def test_every_bound_of_the_specification_has_its_reason_and_domain():
    bounds = [(c, p) for c, _, p in pairs_of(load_spec()) if p["kind"] == "bound"]
    assert bounds
    for case, p in bounds:
        assert p["reason"].strip().endswith("."), (case, p["id"])
        assert p["target"] is None and len(p["domain"]) == 2, (case, p["id"])


def test_a_case_missing_from_the_specification_is_detected():
    spec = load_spec()
    built = {c.id for c in registry.built_cases()}
    spec.pop("C01")
    assert built - set(spec) == {"C01"}


def test_every_file_glob_matches_a_committed_file():
    for case, key, p in pairs_of(load_spec()):
        assert matched_files(case, p), f"{case} {p['id']}: the glob {p['file']!r} matches no committed file"


def test_every_pair_resolves_on_every_committed_file_it_matches():
    for case, key, p in pairs_of(load_spec(), ("pairs",)):
        for rel in matched_files(case, p):
            try:
                ug.check_pair(case, rel, read(case, rel), p)
            except ug.UnitGateError as exc:
                pytest.fail(f"{case} {p['id']} on {rel}: {exc}")


def test_a_withheld_pair_resolves_its_prediction_on_the_committed_file_and_its_target_is_withheld():
    for case, key, p in pairs_of(load_spec(), ("withheld",)):
        for rel in matched_files(case, p):
            doc = read(case, rel)
            assert ug._collect(doc, p["prediction"], p["id"], "prediction", "", (None, None, ())), (rel, p["id"])
            with pytest.raises(ug.UnitGateError, match="nulls only"):
                ug.check_pair(case, rel, doc, p)  # the committed artifact never carries the withheld series


def test_a_path_that_resolves_to_nothing_on_its_committed_file_fails():
    spec = load_spec()
    case, p = "C03", next(p for c, _, p in pairs_of(spec) if p["id"] == "c03-vintage-5y")
    rel = matched_files(case, p)[0]
    doc = read(case, rel)
    del doc["outputs"]["vintage_summary"]["rows"][0]["predicted_5y_pd"]
    del doc["outputs"]["vintage_summary"]["rows"][1:]
    with pytest.raises(ug.UnitGateError, match="resolves to nothing"):
        ug.check_document(case, rel, doc, spec)


def test_the_committed_artifacts_pass_the_gate_and_every_pair_is_checked():
    spec = load_spec()
    checked = {p["id"]: 0 for _, _, p in pairs_of(spec, ("pairs",))}
    for case, entry in spec.items():
        for rel in committed(case):
            result = ug.check_document(case, rel, read(case, rel), spec)
            assert result.violations == [], (case, rel, result.violations)
            for p in entry.get("pairs", []):
                if fnmatch.fnmatchcase(rel, p["file"]):
                    checked[p["id"]] += 1
    assert all(n > 0 for n in checked.values()), [i for i, n in checked.items() if n == 0]
    assert ug.check_document("C21", "pair-2018-19.json", {}, spec).entry == "not_applicable"
    assert ug.check_document("C13", "none.json", {}, spec).entry == "bake_only"


# a defect planted in a committed document: every prediction of the pair is multiplied (a fraction written in percent)

def _scale_leaf(value, factor):
    if isinstance(value, list):
        return [_scale_leaf(v, factor) for v in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value * factor
    return value


def _apply(node, depth, fn):
    if depth == 0:
        return fn(node)
    return [_apply(e, depth - 1, fn) for e in node] if isinstance(node, list) else node


def _scale(node, segments, i, factor):
    if i == len(segments):
        return _scale_leaf(node, factor)
    if not isinstance(node, dict):
        return node
    seg = segments[i]
    if seg.kind == "key":
        keys = [seg.name] if seg.name in node else []
    else:
        keys = [k for k in sorted(node, key=str) if seg.kind == "map" or fnmatch.fnmatchcase(str(k), seg.name)]
    for k in keys:
        node[k] = _apply(node[k], seg.depth, lambda x: _scale(x, segments, i + 1, factor))
    return node


def plant(doc, p, factor):
    out = copy.deepcopy(doc)
    _scale(out, ug._parse(p["prediction"], p["id"], "prediction"), 0, factor)
    return out


def _planted_ids():
    # an absent specification yields no parameters here; test_every_built_case_is_covered reports the absence
    return [(c, p["id"]) for c, _, p in pairs_of(load_spec(), ("pairs",))] if SPEC_PATH.exists() else []


# A percent-for-fraction defect (x100) is seen when the nonzero predictions all lie outside the widened range (an exact zero carries
# no evidence about scale, M15 T2b) or when one prediction lies outside the declared domain of a bounded observable (a probability,
# a share, a cumulative PD: [0, 1]). Only a bound whose values stay below 1/100 (c05 scaled central tendency, PDs near 0.005) stays
# inside [0, 1] at x100: no rule about units can see it, and the test pins the factor that does. The ladder is x100, x1000, x1e6;
# a sign flip is the defect of a non-negative bound.
NEEDS_MORE_THAN_PERCENT = {"c05-bound-scaled-central": 1000.0}
ALL_NULL = {"c04-moodys-generators"}  # moodys.json ships null estimator vectors: nothing to plant, the pair stays for the day it ships values


def first_detecting_factor(case, p, spec):
    ladder = (-1.0,) if p["kind"] == "bound" and p["domain"][1] is None else (100.0, 1000.0, 1e6)
    for factor in ladder:
        for rel in matched_files(case, p):
            result = ug.check_document(case, rel, plant(read(case, rel), p, factor), spec)
            if any(v["pair"] == p["id"] and v["class"] in (ug.CLASS_OUTSIDE, ug.CLASS_DOMAIN) for v in result.violations):
                return factor
    return None


@pytest.mark.parametrize("case,pair_id", _planted_ids())
def test_a_percent_for_fraction_defect_planted_in_a_committed_document_fails_the_pair(case, pair_id):
    spec = load_spec()
    p = next(q for c, _, q in pairs_of(spec, ("pairs",)) if c == case and q["id"] == pair_id)
    if pair_id in ALL_NULL:
        assert all(plant(read(case, rel), p, 100.0) == read(case, rel) for rel in matched_files(case, p))
        return
    expected = -1.0 if p["kind"] == "bound" and p["domain"][1] is None else NEEDS_MORE_THAN_PERCENT.get(pair_id, 100.0)
    assert first_detecting_factor(case, p, spec) == expected, f"{case} {pair_id}"


def test_a_withheld_pair_fails_a_planted_defect_on_the_in_memory_document():
    spec = load_spec()
    for case, key, p in pairs_of(spec, ("withheld",)):
        field = p["prediction"].rsplit(".", 1)[1]
        for rel in matched_files(case, p):
            doc = read(case, rel)
            levels = doc["outputs"]["models"][0]["by_level"]
            doc["outputs"]["grid"]["realised_loss"]["loss"] = list(levels[0][field])  # the bake holds the series in memory
            assert [v for v in ug.check_pair(case, rel, doc, p) if v["blocking"]] == [], (rel, p["id"])
            planted = [v for f in (100.0, 1000.0) for v in ug.check_pair(case, rel, plant(doc, p, f), p) if v["blocking"]]
            assert planted and {v["class"] for v in planted} == {ug.CLASS_OUTSIDE}, (rel, p["id"])


# ---- M15 T2b (CT-2402, CT-2410): an exact zero carries no evidence about scale; a bounded observable checks every prediction ----

def _pd_pair(**kw):
    return pair(kind="binary", target=None, unit="probability", **kw)


def test_a_percent_pd_vector_with_one_exact_zero_is_refused():
    # 0 is the same number in every unit, so the nonzero predictions judge: 22 and 25 lie outside [-1, 2]
    v = run(_pd_pair(), {"pred": [0.0, 22.0, 25.0]}).violations
    assert [x["class"] for x in v] == ["prediction_outside_observable"]
    assert run(pair(kind="series"), {"pred": [0.0, 5000.0], "target": [10, 20]}).violations != []  # thousands with a zero
    assert run(pair(kind="scalar"), {"pred": [0.0, 5000.0], "target": 1.0}).violations != []


def test_a_zero_with_an_honest_nonzero_prediction_passes():
    assert run(_pd_pair(), {"pred": [0.0, 0.3]}).violations == []
    assert run(_pd_pair(), {"pred": [0.0, 0.3, 22.0]}).violations == []  # partly inside still passes


def test_an_all_zero_prediction_stays_advisory_and_never_blocks():
    r = run(pair(kind="series"), {"pred": [0.0, 0.0, 0.0], "target": [10, 20]})
    assert r.violations == [] and [a["class"] for a in r.advisories] == ["degenerate_constant_prediction"]
    assert run(_pd_pair(), {"pred": [0.0]}).violations == []
    # zeros mixed with nulls: nothing nonzero to judge, the null is the advisory
    mixed = run(pair(kind="series"), {"pred": [0.0, None], "target": [10, 20]})
    assert mixed.violations == [] and [a["class"] for a in mixed.advisories] == ["missing_prediction"]


def test_the_nonzero_rule_judges_nonzero_values_among_nulls():
    assert run(_pd_pair(), {"pred": [0.0, None, 22.0]}).violations != []


def test_a_bounded_observable_checks_every_prediction_against_its_domain():
    p = _pd_pair(domain=[0, 1], domain_reason="A probability lies in [0, 1] by definition.")
    assert run(p, {"pred": [0.0, 0.5, 1.0]}).violations == []  # the edges are inside
    # a PD in percent whose smallest value is 0.01: the 0.01 stays inside [-1, 2] but 22 is outside the domain
    v = run(p, {"pred": [0.01, 22.0]}).violations
    assert [x["class"] for x in v] == ["prediction_outside_domain"] and v[0]["blocking"] is True
    assert v[0]["target_range"] == [0, 1] and v[0]["prediction_range"] == [0.01, 22.0]
    assert run(p, {"pred": [0.2, 1.0000001]}).violations != []
    assert run(p, {"pred": [-0.0001, 0.2]}).violations != []


def test_a_domain_with_an_open_end_and_the_element_by_element_check():
    p = pair(kind="series", domain=[0, None], domain_reason="An exposure is non-negative by definition.")
    assert run(p, {"pred": [0.0, 25.0], "target": [10, 20]}).violations == []
    assert run(p, {"pred": [15.0, -3.0], "target": [10, 20]}).violations[0]["class"] == "prediction_outside_domain"
    g = pair(kind="binary", target=None, group_by="rungs[]", prediction="rungs[].pd", domain=[0, 1],
             domain_reason="A probability lies in [0, 1] by definition.")
    doc = {"rungs": [{"pd": [0.1, 0.2]}, {"pd": [0.3, 40.0]}]}
    v = run(g, doc).violations
    assert [(x["class"], x["element"]) for x in v] == [("prediction_outside_domain", 1)]


def test_a_nan_is_not_finite_before_it_is_outside_a_domain():
    p = _pd_pair(domain=[0, 1], domain_reason="A probability lies in [0, 1] by definition.")
    assert [v["class"] for v in run(p, {"pred": [float("nan"), 0.2]}).violations] == ["non_finite_prediction"]


def test_domain_and_domain_reason_validity():
    base = {"id": "p", "file": "*.json", "prediction": "x", "target": "y", "kind": "series", "unit": "USD"}
    ok = {**base, "domain": [0, None], "domain_reason": "An exposure is non-negative by definition."}
    ug.validate_spec({"CX": {"pairs": [ok]}})
    with pytest.raises(ug.UnitGateError, match="domain_reason"):
        ug.validate_spec({"CX": {"pairs": [{**base, "domain": [0, 1]}]}})  # a domain without its reason
    with pytest.raises(ug.UnitGateError, match="domain_reason"):
        ug.validate_spec({"CX": {"pairs": [{**base, "domain_reason": "A reason alone."}]}})  # a reason without a domain
    with pytest.raises(ug.UnitGateError, match="domain_reason"):
        ug.validate_spec({"CX": {"pairs": [{**ok, "domain_reason": "  "}]}})
    with pytest.raises(ug.UnitGateError, match="domain"):
        ug.validate_spec({"CX": {"pairs": [{**ok, "domain": [1, 0]}]}})
    with pytest.raises(ug.UnitGateError, match="domain"):
        ug.validate_spec({"CX": {"pairs": [{**ok, "domain": [0]}]}})


def test_an_unknown_violation_class_is_not_in_the_gate():
    assert ug.CLASS_DOMAIN == "prediction_outside_domain"
    assert ug.CLASS_DOMAIN not in (ug.CLASS_OUTSIDE, ug.CLASS_NON_FINITE, ug.CLASS_CONSTANT, ug.CLASS_MISSING)


def test_every_domain_of_the_specification_has_its_reason_and_is_a_bounded_unit():
    declared = [(c, p) for c, _, p in pairs_of(load_spec()) if p["kind"] != "bound" and "domain" in p]
    assert declared
    for case, p in declared:
        assert p["domain_reason"].strip().endswith("."), (case, p["id"])
        assert p["unit"].split()[0] in ("probability", "cumulative", "share", "USD"), (case, p["id"], p["unit"])


def test_adversarial_ct2410_a_percent_defect_passes_when_the_domain_is_removed_and_fails_when_it_is_declared():
    # the plant of CT-2410 on a committed document: C03's calibration rows hold PDs below 0.01 beside larger ones, so written in
    # percent one prediction stays inside the widened range [-1, 2] and only the domain sees the error
    spec = load_spec()
    case, p = "C03", next(q for c, _, q in pairs_of(spec) if q["id"] == "c03-calibration-rows")
    stripped = {k: v for k, v in p.items() if k not in ("domain", "domain_reason")}
    for rel in matched_files(case, p):
        planted = plant(read(case, rel), p, 100.0)
        with_domain = ug.check_pair(case, rel, planted, p)
        without = ug.check_pair(case, rel, planted, stripped)
        assert [v["class"] for v in with_domain if v["blocking"]] == [ug.CLASS_DOMAIN], rel
        assert [v for v in without if v["blocking"]] == [], rel  # the defect ships when the domain check is removed
        assert [v for v in ug.check_pair(case, rel, read(case, rel), p) if v["blocking"]] == [], rel  # the clean copy passes


# ---- M15 T4 (CT-2404, CT-2409): the shipped check applies the bake's rule to the committed artifacts --------------------------

import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

CHECK = ROOT / "scripts" / "check_units.py"
# runs the script as __main__ under -I and reports whether the pipeline package was imported by it
_WRAP = ("import runpy, sys\n"
         "sys.argv = sys.argv[1:]\n"
         "try:\n"
         "    runpy.run_path(sys.argv[0], run_name='__main__')\n"
         "except SystemExit as e:\n"
         "    code = e.code or 0\n"
         "else:\n"
         "    code = 0\n"
         "print('PIPELINE_IMPORTED=' + str(any(m == 'pipeline' or m.startswith('pipeline.') for m in sys.modules)))\n"
         "sys.exit(code)\n")


def run_check(repo_root, tmp_path, *extra):
    """The script under ``python -I`` from a temp folder: no PYTHONPATH, no cwd, no script directory on the path."""
    cwd = tmp_path / "cwd"
    cwd.mkdir(exist_ok=True)
    return subprocess.run([sys.executable, "-I", "-c", _WRAP, str(CHECK), str(repo_root), *extra], cwd=cwd,
                          capture_output=True, text=True, encoding="utf-8", timeout=120)


def planted_tree(tmp_path, case, rel, mutate):
    """A copy of what the script reads (the specification, the rule, ``data/derived/``) with one document changed."""
    root = tmp_path / "tree"
    (root / "data-pipeline" / "config").mkdir(parents=True)
    (root / "data-pipeline" / "pipeline" / "stages").mkdir(parents=True)
    shutil.copy(SPEC_PATH, root / "data-pipeline" / "config" / "unit_pairs.json")
    shutil.copy(MODULE, root / "data-pipeline" / "pipeline" / "stages" / "unit_gate.py")
    shutil.copytree(DERIVED, root / "data" / "derived")
    path = root / "data" / "derived" / case / rel
    doc = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(mutate(doc)), encoding="utf-8")
    return root


def test_shipped_check_loads_the_bake_rule_without_the_package(tmp_path):
    # CT-2404: no pipeline importable, the same function judges, and a planted copy fails with the class the bake raises
    spec = load_spec()
    case, p = "C03", next(q for c, _, q in pairs_of(spec) if q["id"] == "c03-calibration-rows")
    rel = matched_files(case, p)[0]
    root = planted_tree(tmp_path, case, rel, lambda doc: plant(doc, p, 100.0))
    bake = ug.check_document(case, rel, json.loads((root / "data" / "derived" / case / rel).read_text(encoding="utf-8")), spec)
    assert [v["class"] for v in bake.violations] == [ug.CLASS_DOMAIN]
    done = run_check(root, tmp_path)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "PIPELINE_IMPORTED=False" in done.stdout
    assert ug.CLASS_DOMAIN in done.stdout and case in done.stdout and rel in done.stdout and p["id"] in done.stdout
    assert bake.violations[0]["detail"] in done.stdout  # the very message the bake raises


def test_the_shipped_check_reads_every_case_and_a_capital_in_the_wrong_unit_fails(tmp_path):
    # CT-2404, the plant of validation.md: one C17 capital quantile multiplied by 1,000 fails when every case is read
    spec = load_spec()
    p = next(q for c, _, q in pairs_of(spec, ("pairs",)) if c == "C17")
    rel = matched_files("C17", p)[0]
    root = planted_tree(tmp_path, "C17", rel, lambda doc: plant(doc, p, 1000.0))
    done = run_check(root, tmp_path)
    assert done.returncode == 1 and "C17" in done.stdout and rel in done.stdout, done.stdout
    for case in spec:  # every case of the specification is reported, none skipped silently
        assert f"{case} " in done.stdout, case


def test_committed_tree_passes_the_shipped_check(tmp_path):
    # CT-2409
    start = time.perf_counter()
    done = run_check(ROOT, tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    assert time.perf_counter() - start < 10  # the script alone reads the tree in under two seconds (measured in the report)
    assert "PIPELINE_IMPORTED=False" in done.stdout
    assert "BLOCKING" not in done.stdout
    assert "bake_only" in done.stdout and "not_applicable" in done.stdout


def test_a_glob_that_matches_no_committed_file_fails(tmp_path):
    root = planted_tree(tmp_path, "C01", next(iter(committed("C01"))), lambda d: d)
    spec_path = root / "data-pipeline" / "config" / "unit_pairs.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["C01"]["pairs"][0]["file"] = "no-such-file-*.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    done = run_check(root, tmp_path)
    assert done.returncode == 1 and "matches no committed file" in done.stdout, done.stdout


def test_a_case_folder_without_an_entry_fails(tmp_path):
    root = planted_tree(tmp_path, "C01", next(iter(committed("C01"))), lambda d: d)
    (root / "data" / "derived" / "C99").mkdir()
    (root / "data" / "derived" / "C99" / "a.json").write_text("{}", encoding="utf-8")
    done = run_check(root, tmp_path)
    assert done.returncode == 1 and "C99" in done.stdout and "no entry" in done.stdout, done.stdout


def test_a_withheld_verdict_recording_a_blocking_violation_fails(tmp_path):
    # the committed manifests carry no verdict yet (T3 is in release 1.02.000), so the test plants its own fixture document
    root = planted_tree(tmp_path, "C01", next(iter(committed("C01"))), lambda d: d)
    clean = run_check(root, tmp_path)
    assert clean.returncode == 0 and "no verdict recorded" in clean.stdout, clean.stdout
    path = root / "data" / "derived" / "manifests" / "C11.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    verdict = {"pairs_checked": 8, "violations": [], "advisories": 0}
    manifest["contract"]["units"] = {"withheld": {"calm-2004-06.json": {"c11-withheld-var": verdict}}}
    path.write_text(json.dumps(manifest), encoding="utf-8")
    ok = run_check(root, tmp_path)
    assert ok.returncode == 0 and "verdict recorded" in ok.stdout and "no verdict recorded" not in ok.stdout, ok.stdout
    verdict["violations"] = [{"class": ug.CLASS_OUTSIDE, "pair": "c11-withheld-var", "method": "historical"}]
    path.write_text(json.dumps(manifest), encoding="utf-8")
    bad = run_check(root, tmp_path)
    assert bad.returncode == 1 and "BLOCKING" in bad.stdout and "c11-withheld-var" in bad.stdout and "calm-2004-06.json" in bad.stdout, bad.stdout
