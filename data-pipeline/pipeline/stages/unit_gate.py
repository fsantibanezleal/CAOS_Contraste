"""CONTRACT 3 of CAOS_MANAGE conventions/units-gate.md: a method must answer in the units of its question.

Every other gate of the product asks whether the pipeline ran. This one asks whether a prediction lies in the observable
of its target, and nothing more: a method may be badly wrong and be reported as badly wrong; it may not answer a different
question (a PD written in percent, a capital in thousands) while being scored as if it answered this one. It is never an
accuracy gate.

Standard library only (``math``, ``json``, ``fnmatch``, ``dataclasses``, ``typing``, ``re``) and nothing from the package, so
the bake (``stages/export.py``) and the shipped check (``scripts/check_units.py``, which loads this file by path) judge with
one function. ``tests/test_unit_gate.py`` asserts both.

Violation classes (a violation is a dict, see below)
    non_finite_prediction            a prediction is NaN or infinite                                      blocking
    prediction_outside_observable    EVERY prediction lies outside the target's widened range             blocking
                                     (a prediction partly inside passes; for a ``bound``, any value
                                     outside the declared domain)
    degenerate_constant_prediction   two or more predictions, all equal, over a target that varies        advisory

Target kinds (``RANGE_SLACK = 1.0``: one full range on each side)
    series   an observed series: [lo - span, hi + span]. A span of 0 needs the pair's ``zero_scale`` (then [lo - zs, hi + zs]).
    binary   a 0/1 outcome reported as bin or cohort rates: the label domain [0, 1] widened by its span, so [-1, 2]. The
             target is optional (the default indicator is rarely published); a PD written in percent (22) still fails.
    scalar   one known truth t: [t - |t|, t + |t|]; when t is 0, [-zero_scale, zero_scale]. The target must resolve to
             exactly one value.
    bound    a prediction that is not an estimate of its target: never compared with a target, only finite and inside the
             pair's ``domain`` ([lo, hi], ``null`` an open end). A ``reason`` (one sentence) is required.

Specification (``data-pipeline/config/unit_pairs.json`` loaded as a dict, and passed in; this module reads no file)
    {case: {"pairs": [pair, ...]}                         the pairs checked against the documents of the case
            | {"bake_only": {"hook", "reason"}}           predictions never reach an artifact with their target
            | {"withheld": [pair, ...]}                   checked in memory by the bake (the target may not be published)
            | {"not_applicable": "<why>"}}                nothing is predicted and scored against a target
    pair = {id, file, prediction, target, kind, unit, group_by?, zero_scale?, domain?, reason?}
    ``file`` is an ``fnmatch`` glob matched against the document's path relative to ``data/derived/<case>/``.
    A case with no entry, or an entry without ``pairs``, makes ``check_document`` return an empty result whose ``entry`` says
    ``none``, ``bake_only``, ``withheld`` or ``not_applicable``; what to do with that is the caller's (T3, T4).

Path expressions (dotted)
    ``a.b``      a key of a map
    ``a[]``      walks every element of the list at ``a`` (``a[][]`` two levels)
    ``<m>``      walks the keys of a map in sorted order and binds the key as the method id a violation names
    ``pd_*``     a segment with ``*`` or ``?`` walks the map keys it matches (``fnmatch``, sorted); when the path has no
                 ``<m>``, the matched key is the method id
    A leaf may be a number or a list of numbers (nested lists flatten). A key missing in an element is skipped; a path that
    resolves to NO value at all is a specification error naming the pair and the path (``UnitGateError``), never a pass.
    A boolean, a string or a JSON null where a number is expected is a ``UnitGateError`` too: the rule and the design do not
    class a null inside a prediction (an artifact writes NaN as null), so the gate refuses it loudly until they do.

``group_by``  a path prefix ending in ``[]`` that the prediction and the target share (C04: ``outputs.rungs[]``, each rung
    with its own ``truth``). Each element is checked as its own pair with the remainder of both paths; its violations carry
    ``element`` (the index of the last list walked by the prefix).

Interface
    check_document(case, rel, doc, spec) -> Result        every pair of the case whose ``file`` glob matches ``rel``
    check_pair(case, rel, doc, pair)     -> list[dict]    one pair (violations and advisories together, sorted)
    validate_pair(pair), validate_spec(spec)              raise UnitGateError on a malformed specification
    blocking(violations) -> list[dict]                    the subset that must stop a bake
    Result(violations, advisories, pairs_checked, entry)  ``violations`` blocking, ``advisories`` not
    UnitGateError(ValueError)                             a malformed specification or a document that is not numeric
    RANGE_SLACK

A violation dict: ``case``, ``file``, ``pair``, ``method`` (or None), ``element`` (or None), ``class``, ``blocking``,
``kind``, ``unit``, ``prediction_range`` ([min, max] of the finite predictions, or None), ``target_range`` (the widened
range; for a ``bound`` its domain, ``None`` for an open end), ``n_predictions``, ``detail``. Violations are sorted by pair,
method, element and class, whatever the dict order of the input document.
"""
from __future__ import annotations

import fnmatch
import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterator

RANGE_SLACK = 1.0
# a target "varies" and a prediction is "constant" at this fraction of their scale (Fragua's FLAT_SERIES_REL)
FLAT_REL = 1e-6

KINDS = ("series", "binary", "scalar", "bound")
CLASS_NON_FINITE = "non_finite_prediction"
CLASS_OUTSIDE = "prediction_outside_observable"
CLASS_CONSTANT = "degenerate_constant_prediction"
ENTRY_KINDS = ("pairs", "bake_only", "withheld", "not_applicable")
_PAIR_KEYS = {"id", "file", "prediction", "target", "kind", "unit", "group_by", "zero_scale", "domain", "reason"}
_SEGMENT = re.compile(r"^(?P<name>[^\[\]]+)(?P<arrays>(?:\[\])*)$")


class UnitGateError(ValueError):
    """A malformed specification, a path that finds nothing, or a document value that is not a number."""


@dataclass
class Result:
    violations: list[dict] = field(default_factory=list)  # blocking
    advisories: list[dict] = field(default_factory=list)  # recorded, not blocking
    pairs_checked: int = 0
    entry: str = "none"  # the case entry's kind: none, pairs, bake_only, withheld or not_applicable


# ---- the specification --------------------------------------------------------------------------------------------

def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_pair(pair: Any) -> None:
    """Raise ``UnitGateError`` naming the pair when its specification is malformed."""
    if not isinstance(pair, dict):
        raise UnitGateError(f"a pair is not an object: {pair!r}")
    name = pair.get("id") if _text(pair.get("id")) else "<no id>"

    def bad(why: str) -> UnitGateError:
        return UnitGateError(f"pair {name!r}: {why}")

    for key in ("id", "file", "prediction", "kind", "unit"):
        if not _text(pair.get(key)):
            raise bad(f"the field {key!r} is required")
    unknown = sorted(set(pair) - _PAIR_KEYS)
    if unknown:
        raise bad(f"unknown field(s) {unknown}")
    kind = pair["kind"]
    if kind not in KINDS:
        raise bad(f"kind {kind!r} is none of {list(KINDS)}")
    if kind in ("series", "scalar") and not _text(pair.get("target")):
        raise bad(f"kind {kind!r} needs its 'target' path")
    if pair.get("target") is not None and not _text(pair["target"]):
        raise bad("'target' is a path or null")
    if "zero_scale" in pair and not (_number(pair["zero_scale"]) and pair["zero_scale"] > 0):
        raise bad("'zero_scale' is a finite number above 0")
    if kind == "bound":
        if not _text(pair.get("reason")):
            raise bad("a bound pair needs its 'reason' (one sentence: why this prediction is not an estimate of a target)")
        domain = pair.get("domain")
        if (not isinstance(domain, (list, tuple)) or len(domain) != 2
                or any(d is not None and not _number(d) for d in domain)
                or (domain[0] is not None and domain[1] is not None and domain[0] > domain[1])):
            raise bad("a bound pair needs its 'domain' as [lo, hi] with null for an open end and lo <= hi")
    group = pair.get("group_by")
    if group is not None:
        if not _text(group) or not group.endswith("[]"):
            raise bad(f"group_by {group!r} must be a path prefix ending in '[]'")
        for role in ("prediction", "target"):
            path = pair.get(role)
            if path is None or (role == "target" and kind == "bound"):
                continue
            if not path.startswith(group) or path[len(group):][:1] not in ("", "."):
                raise bad(f"group_by {group!r} is not a path prefix of the {role} {path!r}")
    for role in ("prediction", "target"):
        if pair.get(role) is not None and not (role == "target" and kind == "bound"):
            _parse(pair[role], name, role)


def validate_spec(spec: Any) -> None:
    """Raise ``UnitGateError`` naming the case and the pair when the specification is malformed."""
    if not isinstance(spec, dict):
        raise UnitGateError("the unit pairs specification is not an object keyed by case")
    for case, entry in spec.items():
        try:
            if not isinstance(entry, dict) or not entry:
                raise UnitGateError("the entry is not a non-empty object")
            unknown = sorted(set(entry) - set(ENTRY_KINDS))
            if unknown:
                raise UnitGateError(f"unknown entry key(s) {unknown}; the kinds are {list(ENTRY_KINDS)}")
            ids: set[str] = set()
            for key in ("pairs", "withheld"):
                if key in entry:
                    if not isinstance(entry[key], list) or not entry[key]:
                        raise UnitGateError(f"{key!r} is a non-empty list of pairs")
                    for p in entry[key]:
                        validate_pair(p)
                        if p["id"] in ids:
                            raise UnitGateError(f"pair id {p['id']!r} is used twice")
                        ids.add(p["id"])
            if "bake_only" in entry:
                b = entry["bake_only"]
                if not (isinstance(b, dict) and _text(b.get("hook")) and _text(b.get("reason"))):
                    raise UnitGateError("'bake_only' needs a 'hook' and a 'reason'")
            if "not_applicable" in entry and not _text(entry["not_applicable"]):
                raise UnitGateError("'not_applicable' is one sentence on why nothing is predicted and scored")
        except UnitGateError as exc:
            raise UnitGateError(f"case {case}: {exc}") from None


# ---- path expressions ---------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class _Segment:
    kind: str  # key, map or glob
    name: str
    depth: int  # the number of trailing []


def _parse(expr: str, pair_id: str, role: str) -> list[_Segment]:
    segments: list[_Segment] = []
    for raw in expr.split("."):
        m = _SEGMENT.match(raw)
        if not m:
            raise UnitGateError(f"pair {pair_id!r}: the {role} path {expr!r} has a malformed segment {raw!r}")
        name = m["name"]
        kind = "map" if name == "<m>" else "glob" if ("*" in name or "?" in name) else "key"
        segments.append(_Segment(kind, name, len(m["arrays"]) // 2))
    if sum(s.kind == "map" for s in segments) > 1:
        raise UnitGateError(f"pair {pair_id!r}: the {role} path {expr!r} has more than one <m>")
    return segments


# a binding: (method id from <m>, key matched by a glob segment, the indexes of the lists walked)
_Bind = tuple[Any, Any, tuple]


def _arrays(node: Any, depth: int, bind: _Bind) -> Iterator[tuple[Any, _Bind]]:
    if depth == 0:
        yield node, bind
        return
    if not isinstance(node, list):
        return
    for i, element in enumerate(node):
        yield from _arrays(element, depth - 1, (bind[0], bind[1], bind[2] + (i,)))


def _walk(node: Any, segments: list[_Segment], i: int, bind: _Bind) -> Iterator[tuple[_Bind, Any]]:
    if i == len(segments):
        yield bind, node
        return
    seg = segments[i]
    if not isinstance(node, dict):
        return
    if seg.kind == "key":
        children = [(node[seg.name], bind)] if seg.name in node else []
    elif seg.kind == "map":
        children = [(node[k], (k, bind[1], bind[2])) for k in sorted(node, key=str)]
    else:
        children = [(node[k], (bind[0], k, bind[2])) for k in sorted(node, key=str) if fnmatch.fnmatchcase(str(k), seg.name)]
    for child, child_bind in children:
        for element, element_bind in _arrays(child, seg.depth, child_bind):
            yield from _walk(element, segments, i + 1, element_bind)


def _method(bind: _Bind) -> Any:
    return bind[0] if bind[0] is not None else bind[1]


def _numbers(value: Any, where: str) -> list[float]:
    """The numbers of a leaf: a number, or a list of numbers (nested lists flatten)."""
    if isinstance(value, bool) or isinstance(value, (str, dict)):
        raise UnitGateError(f"{where}: {value!r} is not a number")
    if value is None:
        raise UnitGateError(f"{where}: a null where a number is expected (a null is not classed: refused)")
    if isinstance(value, (list, tuple)):
        out: list[float] = []
        for v in value:
            out.extend(_numbers(v, where))
        return out
    if not isinstance(value, (int, float)):
        raise UnitGateError(f"{where}: {value!r} is not a number")
    return [float(value)]


def _collect(node: Any, expr: str, pair_id: str, role: str, where: str, base: _Bind) -> dict[Any, list[float]]:
    """Method id (or None) -> the numbers the path resolves to, in walk order; empty when it resolves to nothing."""
    out: dict[Any, list[float]] = {}
    for bind, leaf in _walk(node, _parse(expr, pair_id, role), 0, base):
        values = _numbers(leaf, f"pair {pair_id!r}: the {role} path {expr!r}{where}")
        if values:
            out.setdefault(_method(bind), []).extend(values)
    return out


# ---- the check ----------------------------------------------------------------------------------------------------

def _range(values: list[float]) -> list[float] | None:
    finite = [v for v in values if math.isfinite(v)]
    return [min(finite), max(finite)] if finite else None


def _fmt(r: list[float | None] | None) -> str:
    return "n/a" if r is None else f"[{r[0]:.6g}, {r[1]:.6g}]" if all(x is not None for x in r) else str(r)


def _target_range(pair: dict, tvals: list[float] | None, where: str) -> tuple[list[float | None], bool]:
    """The widened range of the target and whether the target varies."""
    kind, zs = pair["kind"], pair.get("zero_scale")
    if kind == "bound":
        return [pair["domain"][0], pair["domain"][1]], False
    if kind == "binary":
        varies = False
        if tvals:
            lo, hi = min(tvals), max(tvals)
            varies = hi - lo > FLAT_REL * max(abs(lo), abs(hi), 1e-12)
        return [0.0 - RANGE_SLACK, 1.0 + RANGE_SLACK], varies
    assert tvals is not None
    if any(not math.isfinite(t) for t in tvals):
        raise UnitGateError(f"pair {pair['id']!r}: the target holds a value that is not finite{where}")
    if kind == "scalar":
        if len(tvals) != 1:
            raise UnitGateError(f"pair {pair['id']!r}: a scalar target resolves to exactly one value, found {len(tvals)}"
                                f"{where} (a pair per truth needs group_by)")
        t = tvals[0]
        if t == 0.0:
            if zs is None:
                raise UnitGateError(f"pair {pair['id']!r}: the scalar target is 0 and the pair declares no zero_scale{where}")
            return [-zs, zs], False
        return [t - RANGE_SLACK * abs(t), t + RANGE_SLACK * abs(t)], False
    lo, hi = min(tvals), max(tvals)  # series
    span = hi - lo
    if span == 0.0:
        if zs is None:
            raise UnitGateError(f"pair {pair['id']!r}: the target series has span 0 and the pair declares no zero_scale{where}")
        return [lo - zs, hi + zs], False
    return [lo - RANGE_SLACK * span, hi + RANGE_SLACK * span], span > FLAT_REL * max(abs(lo), abs(hi), 1e-12)


def _judge(case: str, rel: str, pair: dict, method: Any, element: int | None, preds: list[float],
           tvals: list[float] | None, where: str) -> list[dict]:
    wide, varies = _target_range(pair, tvals, where)
    p_range = _range(preds)
    head = {"case": case, "file": rel, "pair": pair["id"], "method": method, "element": element, "kind": pair["kind"],
            "unit": pair["unit"], "prediction_range": p_range, "target_range": wide, "n_predictions": len(preds)}
    who = f"{pair['id']}" + (f" method {method}" if method is not None else "") + (f" element {element}" if element is not None else "")

    def violation(cls: str, is_blocking: bool, detail: str) -> dict:
        return {**head, "class": cls, "blocking": is_blocking, "detail": f"{who}: {detail}"}

    bad = [p for p in preds if not math.isfinite(p)]
    if bad:
        return [violation(CLASS_NON_FINITE, True, f"{len(bad)} of {len(preds)} predictions are not finite")]
    lo = -math.inf if wide[0] is None else wide[0]
    hi = math.inf if wide[1] is None else wide[1]
    inside = [p for p in preds if lo <= p <= hi]
    if pair["kind"] == "bound":
        if len(inside) != len(preds):
            return [violation(CLASS_OUTSIDE, True, f"predicts {_fmt(p_range)} {pair['unit']} but the declared domain is "
                              f"{_fmt(wide)}: a value lies outside the observable it is a bound of")]
        return []
    if not inside:
        return [violation(CLASS_OUTSIDE, True, f"predicts {_fmt(p_range)} against a widened target range {_fmt(wide)} "
                          f"{pair['unit']}: every prediction lies outside the observable, so this method is answering "
                          "a different question")]
    p_lo, p_hi = min(preds), max(preds)
    if varies and len(preds) >= 2 and p_hi - p_lo <= FLAT_REL * max(abs(p_lo), abs(p_hi), 1e-12):
        return [violation(CLASS_CONSTANT, False, f"returns the constant {p_lo:.6g} over a target that varies; recorded, "
                          "not blocking (a flat answer is legitimate when the driver does not move enough)")]
    return []


def _sort_key(v: dict) -> tuple:
    return (v["pair"], "" if v["method"] is None else str(v["method"]), -1 if v["element"] is None else v["element"],
            v["class"])


def _empty(pair: dict, role: str, expr: str, rel: str, where: str) -> UnitGateError:
    extra = " (a map walk <m> over a value that is not a map finds nothing)" if "<m>" in expr else ""
    return UnitGateError(f"pair {pair['id']!r}: the {role} path {expr!r} resolves to nothing in {rel}{where}{extra}")


def _check_scope(case: str, rel: str, scope: Any, pair: dict, element: int | None, base: _Bind,
                 pred_path: str, target_path: str | None, where: str) -> list[dict]:
    pid = pair["id"]
    preds = _collect(scope, pred_path, pid, "prediction", where, base) if pred_path else {}
    if not preds:
        raise _empty(pair, "prediction", pred_path, rel, where)
    targets: dict[Any, list[float]] = {}
    if target_path is not None and pair["kind"] != "bound":
        targets = _collect(scope, target_path, pid, "target", where, base)
        if not targets:
            raise _empty(pair, "target", target_path, rel, where)
    out: list[dict] = []
    for method in sorted(preds, key=lambda m: "" if m is None else str(m)):
        if not targets:
            tvals = None
        elif list(targets) == [None]:
            tvals = targets[None]
        elif method in targets:
            tvals = targets[method]
        else:
            raise UnitGateError(f"pair {pid!r}: the target path {target_path!r} binds methods and none is {method!r}{where}")
        out.extend(_judge(case, rel, pair, method, element, preds[method], tvals, where))
    return out


def check_pair(case: str, rel: str, doc: Any, pair: dict) -> list[dict]:
    """Check one pair against one document; its violations and advisories, sorted. ``UnitGateError`` on a bad pair or path."""
    validate_pair(pair)
    pred_path, target_path = pair["prediction"], pair.get("target")
    group = pair.get("group_by")
    if group is None:
        out = _check_scope(case, rel, doc, pair, None, (None, None, ()), pred_path, target_path, "")
    else:
        elements = list(_walk(doc, _parse(group, pair["id"], "group_by"), 0, (None, None, ())))
        if not elements:
            raise _empty(pair, "group_by", group, rel, "")
        out = []
        for bind, element in elements:
            index = bind[2][-1]
            cut = len(group)
            rest = lambda p: None if p is None else p[cut:].lstrip(".")  # noqa: E731
            where = f" (element {index} of {group!r})"
            out.extend(_check_scope(case, rel, element, pair, index, bind, rest(pred_path), rest(target_path), where))
    return sorted(out, key=_sort_key)


def blocking(violations: list[dict]) -> list[dict]:
    """The subset that must stop a bake, as opposed to being recorded."""
    return [v for v in violations if v.get("blocking", True)]


def check_document(case: str, rel: str, doc: Any, spec: dict) -> Result:
    """Check every pair of ``case`` whose ``file`` glob matches ``rel`` against ``doc``.

    ``spec`` maps a case id to its entry (see the module docstring). A case without an entry, or an entry without
    ``pairs``, returns an empty result whose ``entry`` records what it is; a file matching no glob checks nothing.
    """
    entry = spec.get(case)
    if entry is None:
        return Result()
    if not isinstance(entry, dict):
        raise UnitGateError(f"case {case}: the entry is not an object")
    if "pairs" not in entry:
        kind = next((k for k in ("bake_only", "withheld", "not_applicable") if k in entry), None)
        if kind is None:
            raise UnitGateError(f"case {case}: the entry holds none of {list(ENTRY_KINDS)}")
        return Result(entry=kind)
    result = Result(entry="pairs")
    found: list[dict] = []
    for pair in entry["pairs"]:
        validate_pair(pair)
        if fnmatch.fnmatchcase(rel, pair["file"]):
            result.pairs_checked += 1
            found.extend(check_pair(case, rel, doc, pair))
    found.sort(key=_sort_key)
    result.violations = [v for v in found if v["blocking"]]
    result.advisories = [v for v in found if not v["blocking"]]
    return result
