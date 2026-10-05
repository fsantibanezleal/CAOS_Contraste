"""CONTRACT 1, ingestion (raw to pipeline): one declared family per kind of source data (SDD section 2.1).

Every record of a dataset either validates or is rejected with the failing field, the value, the expected range and
the policy that applied. Nothing is coerced: a value is parsed strictly by its declared kind (text from a CSV is read
as the declared number or date, or rejected), never clipped, filled or guessed. Three policies apply:

- ``reject``: the record is refused, and every violation is reported;
- ``flag``: the record is accepted and the flag is reported (it reaches the manifest);
- ``exclude``: the record is valid but outside the use the case makes of it (a workout still open at the cutoff, a
  withdrawn rating under the "exclude" convention); it is removed from the accepted set and counted.

The same declarations are exported to ``data/derived/contract/<family>.json`` for the web (bring-your-own-data runs
in the browser against them) and mirrored by ``frontend/src/lib/contract.types.ts``.

Sources of the controlled vocabularies: the 19 repricing time bands and their midpoints, SRP31.96 Table 3; the caps
on core non-maturity deposits, SRP31 Table 4 (BCBS d368 Table 2); the seven Level 1 loss event types, OPE25.17
Table 2; the loss collection threshold, OPE25.18. All transcribed from the research dossiers, 2026-10-04.
"""
from __future__ import annotations

import datetime as dt
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

SCHEMA = "contraste.contract/v1"

Text = dict  # {"en": str, "es": str}: every reader-facing string is bilingual at the source (ADR-0011)

KINDS = ("str", "int", "float", "flag", "date", "enum")
POLICIES = ("reject", "flag", "exclude")


class ContractError(ValueError):
    """The dataset cannot be validated at all: an unknown family, or a missing or invalid dataset parameter."""


# --- controlled vocabularies -------------------------------------------------------------------------------------

#: SRP31.96 Table 3: the 19 time bands of the standardised IRRBB framework and their midpoints in years.
REPRICING_BANDS: tuple[tuple[str, float], ...] = (
    ("ON", 0.0028), ("ON-1M", 0.0417), ("1M-3M", 0.1667), ("3M-6M", 0.375), ("6M-9M", 0.625), ("9M-1Y", 0.875),
    ("1Y-1.5Y", 1.25), ("1.5Y-2Y", 1.75), ("2Y-3Y", 2.5), ("3Y-4Y", 3.5), ("4Y-5Y", 4.5), ("5Y-6Y", 5.5),
    ("6Y-7Y", 6.5), ("7Y-8Y", 7.5), ("8Y-9Y", 8.5), ("9Y-10Y", 9.5), ("10Y-15Y", 12.5), ("15Y-20Y", 17.5),
    ("20Y+", 25.0),
)

#: SRP31 Table 4 (BCBS d368 Table 2): cap on the core share and on the average maturity of core, per NMD category.
NMD_CAPS: dict[str, tuple[float, float]] = {
    "nmd_retail_transactional": (0.90, 5.0),
    "nmd_retail_non_transactional": (0.70, 4.5),
    "nmd_wholesale": (0.50, 4.0),
}

BEHAVIOURAL_CLASSES: tuple[str, ...] = (
    "contractual", *NMD_CAPS, "prepayable_fixed_rate_loan", "redeemable_term_deposit",
)

#: OPE25.17 Table 2: the seven Level 1 loss event types.
EVENT_TYPES: tuple[str, ...] = (
    "internal_fraud", "external_fraud", "employment_practices_and_workplace_safety",
    "clients_products_and_business_practices", "damage_to_physical_assets",
    "business_disruption_and_system_failures", "execution_delivery_and_process_management",
)

CURRENCIES: tuple[str, ...] = ("USD", "CLP", "CLF", "EUR")
COMPOUNDING: tuple[str, ...] = ("continuous", "annual", "semiannual", "quarterly", "monthly", "simple")
SERIES_UNITS: tuple[str, ...] = ("return", "log_return", "level", "rate")
WR_CONVENTIONS: tuple[str, ...] = ("exclude", "censor", "state")

MISSING = object()  # sentinel: the field is absent, empty or NaN


# --- declarations ------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Field:
    """One declared column: its kind, unit, range or allowed values, and what happens when it is missing."""

    name: str
    kind: str
    meaning: Text
    unit: str = ""
    lo: float | None = None
    hi: float | None = None
    lo_open: bool = False
    hi_open: bool = False
    values: tuple[str, ...] = ()
    values_param: str = ""  # the allowed values come from a dataset parameter (a declared grade scale)
    required: bool = True
    on_missing: str = "reject"

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"field {self.name}: unknown kind {self.kind!r}")
        if self.on_missing not in ("reject", "flag"):
            raise ValueError(f"field {self.name}: on_missing must be reject or flag")
        if self.kind == "enum" and not (self.values or self.values_param):
            raise ValueError(f"field {self.name}: an enum declares its values or the parameter that holds them")

    def expected(self, params: Mapping[str, Any] | None = None) -> str:
        """The expected range in words, as written in a rejection."""
        if self.kind == "date":
            return "an ISO date YYYY-MM-DD"
        if self.kind == "flag":
            return "0 or 1"
        if self.kind == "enum":
            vals = self.allowed(params)
            return "one of {" + ", ".join(vals) + "}" if vals else f"one of the values of parameter {self.values_param!r}"
        if self.kind == "str":
            return "a non-empty text"
        lo = "-inf" if self.lo is None else f"{self.lo:g}"
        hi = "+inf" if self.hi is None else f"{self.hi:g}"
        left = "(" if (self.lo is None or self.lo_open) else "["
        right = ")" if (self.hi is None or self.hi_open) else "]"
        noun = "an integer" if self.kind == "int" else "a finite number"
        return f"{noun} in {left}{lo}, {hi}{right}" + (f" ({self.unit})" if self.unit else "")

    def allowed(self, params: Mapping[str, Any] | None = None) -> tuple[str, ...]:
        if self.values_param:
            extra = tuple((params or {}).get(self.values_param) or ())
            return tuple(dict.fromkeys((*extra, *self.values)))
        return self.values

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name, "kind": self.kind, "meaning": self.meaning, "unit": self.unit,
            "lo": self.lo, "hi": self.hi, "lo_open": self.lo_open, "hi_open": self.hi_open,
            "values": list(self.values), "values_param": self.values_param or None,
            "required": self.required, "on_missing": self.on_missing, "expected": self.expected(),
        }


@dataclass(frozen=True)
class Param:
    """A dataset-level parameter a family needs (a grade scale, a cutoff, a collection threshold)."""

    name: str
    kind: str  # "date", "float", "enum", "list"
    meaning: Text
    required: bool = True
    values: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "meaning": self.meaning, "required": self.required,
                "values": list(self.values)}


# A record rule sees one parsed record and the dataset parameters; it returns a violation reason or None.
RecordCheck = Callable[[Mapping[str, Any], Mapping[str, Any]], "str | None"]
# A group rule sees the (index, record) pairs of one group, in order; it returns (index, reason) per violation.
GroupCheck = Callable[[Sequence[tuple[int, Mapping[str, Any]]], Mapping[str, Any]], "list[tuple[int, str]]"]


@dataclass(frozen=True)
class Rule:
    """A rule across fields of one record (scope ``record``) or across the records of a group (scope ``group``)."""

    id: str
    scope: str
    policy: str
    field: str  # the field a violation is reported against
    statement: Text
    check: Callable[..., Any] = field(repr=False, compare=False)
    group_by: tuple[str, ...] = ()
    order_by: str = ""

    def __post_init__(self) -> None:
        if self.scope not in ("record", "group"):
            raise ValueError(f"rule {self.id}: scope is record or group")
        if self.policy not in POLICIES:
            raise ValueError(f"rule {self.id}: unknown policy {self.policy!r}")
        if self.scope == "group" and not self.group_by:
            raise ValueError(f"rule {self.id}: a group rule names its group key")

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "scope": self.scope, "policy": self.policy, "field": self.field,
                "statement": self.statement, "group_by": list(self.group_by), "order_by": self.order_by or None}


@dataclass(frozen=True)
class Family:
    """One ingestion family: the fields, the rules, the dataset parameters, and what uses it."""

    name: str
    title: Text
    used_by: Text
    fields: tuple[Field, ...]
    rules: tuple[Rule, ...] = ()
    params: tuple[Param, ...] = ()
    open_fields: bool = False  # the case declares further fields (the features of a scored sample)
    notes: tuple[Text, ...] = ()
    # dataset-level checks on the parameters: (statement, check returning a reason or None)
    param_checks: tuple[tuple[Text, Callable[[Mapping[str, Any]], "str | None"]], ...] = ()

    def field(self, name: str) -> Field | None:
        return next((f for f in self.fields if f.name == name), None)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "family": self.name, "title": self.title, "used_by": self.used_by,
            "fields": [f.to_json() for f in self.fields], "rules": [r.to_json() for r in self.rules],
            "params": [p.to_json() for p in self.params], "open_fields": self.open_fields,
            "notes": list(self.notes), "param_checks": [statement for statement, _ in self.param_checks],
        }


# --- the report --------------------------------------------------------------------------------------------------


@dataclass
class ContractReport:
    """What validation did to a dataset. ``accepted`` holds the parsed records, in input order."""

    family: str
    n_input: int = 0
    accepted: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, Any]] = field(default_factory=list)
    flagged: list[dict[str, Any]] = field(default_factory=list)
    excluded: list[dict[str, Any]] = field(default_factory=list)
    ignored_columns: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.accepted)

    def counts(self) -> dict[str, int]:
        return {"input": self.n_input, "accepted": len(self.accepted), "rejected": len(self.rejected),
                "flagged": len(self.flagged), "excluded": len(self.excluded)}

    def by_rule(self) -> dict[str, dict[str, int]]:
        """How many entries each rule (or field, for a field violation) produced, per kind."""
        out: dict[str, dict[str, int]] = {"rejected": {}, "flagged": {}, "excluded": {}}
        for kind, entries in (("flagged", self.flagged), ("excluded", self.excluded)):
            for e in entries:
                key = e.get("rule") or e["field"]
                out[kind][key] = out[kind].get(key, 0) + 1
        for r in self.rejected:
            for v in r["violations"]:
                key = v.get("rule") or v["field"]
                out["rejected"][key] = out["rejected"].get(key, 0) + 1
        return {k: dict(sorted(v.items())) for k, v in out.items()}

    def examples(self, limit: int = 5) -> list[dict[str, Any]]:
        """The first entries of each kind, one shape for all: kind, row, key, field, value (as text), expected,
        policy, reason, rule (None for a field violation)."""
        out: list[dict[str, Any]] = []

        def one(kind: str, row: int, key: str, e: dict[str, Any]) -> dict[str, Any]:
            v = e.get("value")
            return {"kind": kind, "row": int(row), "key": str(key), "field": e["field"],
                    "value": None if v is None else str(v), "expected": e["expected"], "policy": e["policy"],
                    "reason": e["reason"], "rule": e.get("rule")}

        for r in self.rejected[:limit]:
            out.append(one("rejected", r["row"], r["key"], r["violations"][0]))
        for kind, entries in (("flagged", self.flagged), ("excluded", self.excluded)):
            out.extend(one(kind, e["row"], e["key"], e) for e in entries[:limit])
        return out

    def summary(self, limit: int = 5) -> dict[str, Any]:
        """The compact, JSON-safe form written into a manifest: the counts, the counts per rule, the ignored
        columns and the first entries of each kind."""
        return {"family": self.family, "counts": self.counts(), "by_rule": self.by_rule(),
                "ignored_columns": list(self.ignored_columns), "examples": self.examples(limit)}


# --- parsing -----------------------------------------------------------------------------------------------------


def _is_missing(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "") or (isinstance(v, float) and math.isnan(v))


def _jsonable(v: Any) -> Any:
    if v is MISSING or v is None:
        return None
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float) and not math.isfinite(v):
        return str(v)
    if isinstance(v, (str, int, float, bool)):
        return v
    return repr(v)


def _parse(f: Field, raw: Any, params: Mapping[str, Any]) -> tuple[Any, str | None]:
    """Parse one value strictly by its declared kind. Return (value, None) or (raw, reason)."""
    if f.kind == "str":
        if isinstance(raw, str) and raw.strip():
            return raw.strip(), None
        return raw, "not a non-empty text"
    if f.kind == "date":
        if isinstance(raw, dt.datetime):
            return raw.date(), None
        if isinstance(raw, dt.date):
            return raw, None
        if isinstance(raw, str):
            try:
                return dt.date.fromisoformat(raw.strip()), None
            except ValueError:
                pass
        return raw, "not an ISO date"
    if f.kind == "flag":
        if isinstance(raw, bool):
            return raw, "a boolean where 0 or 1 is declared"
        if isinstance(raw, int) and raw in (0, 1):
            return raw, None
        if isinstance(raw, float) and raw in (0.0, 1.0):
            return int(raw), None
        if isinstance(raw, str) and raw.strip() in ("0", "1"):
            return int(raw.strip()), None
        return raw, "not 0 or 1"
    if f.kind == "enum":
        allowed = f.allowed(params)
        if not allowed:
            return raw, f"no value set declared (parameter {f.values_param!r} is missing)"
        v = raw.strip() if isinstance(raw, str) else raw
        if isinstance(v, str) and v in allowed:
            return v, None
        return raw, "not an allowed value"
    # numbers
    if isinstance(raw, bool):
        return raw, "a boolean where a number is declared"
    if isinstance(raw, str):
        try:
            num: float = float(raw.strip())
        except ValueError:
            return raw, "not a number"
    elif isinstance(raw, (int, float)):
        num = raw
    elif hasattr(raw, "item"):  # numpy scalar
        num = raw.item()
    else:
        return raw, "not a number"
    if isinstance(num, float) and not math.isfinite(num):
        return raw, "not finite"
    if f.kind == "int":
        if isinstance(num, float):
            if not num.is_integer():
                return raw, "not an integer"
            num = int(num)
        value: float = num
    else:
        value = float(num)
    lo_bad = f.lo is not None and (value <= f.lo if f.lo_open else value < f.lo)
    hi_bad = f.hi is not None and (value >= f.hi if f.hi_open else value > f.hi)
    if lo_bad or hi_bad:
        return raw, "out of range"
    return value, None


def _check_params(family: Family, params: Mapping[str, Any]) -> None:
    for p in family.params:
        v = params.get(p.name)
        if v is None:
            if p.required:
                raise ContractError(f"{family.name}: the dataset parameter {p.name!r} is required ({p.meaning['en']})")
            continue
        if p.kind == "date" and not isinstance(v, dt.date):
            try:
                dt.date.fromisoformat(str(v))
            except ValueError as exc:
                raise ContractError(f"{family.name}: parameter {p.name!r} is not an ISO date: {v!r}") from exc
        if p.kind == "float" and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)):
            raise ContractError(f"{family.name}: parameter {p.name!r} is not a finite number: {v!r}")
        if p.kind == "enum" and v not in p.values:
            raise ContractError(f"{family.name}: parameter {p.name!r} must be one of {list(p.values)}, got {v!r}")
        if p.kind == "list" and (isinstance(v, str) or not all(isinstance(x, str) and x for x in v)):
            raise ContractError(f"{family.name}: parameter {p.name!r} is a list of non-empty texts")
    for _statement, check in family.param_checks:
        reason = check(params)
        if reason:
            raise ContractError(f"{family.name}: {reason}")


def _param_date(params: Mapping[str, Any], name: str) -> dt.date | None:
    v = params.get(name)
    if v is None:
        return None
    return v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))


# --- validation --------------------------------------------------------------------------------------------------


def validate(
    family: str | Family,
    records: Iterable[Mapping[str, Any]],
    *,
    params: Mapping[str, Any] | None = None,
    extra_fields: Sequence[Field] = (),
    extra_rules: Sequence[Rule] = (),
) -> ContractReport:
    """Apply a family contract to raw records (pure, deterministic, no I/O).

    ``params`` are the dataset parameters the family declares; ``extra_fields`` are the fields a case adds to an
    open family (the features of a scored sample), and ``extra_rules`` the rules the case declares on them (a code
    outside the documented scale, say). Columns that are neither declared nor added are ignored and listed in the
    report, never used.
    """
    fam = FAMILIES[family] if isinstance(family, str) else family
    if isinstance(family, str) and family not in FAMILIES:
        raise ContractError(f"unknown family {family!r}; known: {sorted(FAMILIES)}")
    if (extra_fields or extra_rules) and not fam.open_fields:
        raise ContractError(f"{fam.name}: this family declares all its fields; a case cannot add any")
    rules = (*fam.rules, *extra_rules)
    if len({r.id for r in rules}) != len(rules):
        raise ContractError(f"{fam.name}: a rule id is declared twice")
    params = dict(params or {})
    _check_params(fam, params)
    fields = (*fam.fields, *extra_fields)
    names = {f.name for f in fields}
    if len(names) != len(fields):
        raise ContractError(f"{fam.name}: a field is declared twice")
    report = ContractReport(family=fam.name)
    ignored: set[str] = set()
    parsed: list[tuple[int, dict[str, Any]]] = []
    for i, raw in enumerate(records):
        report.n_input += 1
        ignored.update(k for k in raw if k not in names)
        rec: dict[str, Any] = {}
        violations: list[dict[str, Any]] = []
        flags: list[dict[str, Any]] = []
        for f in fields:
            raw_v = raw.get(f.name)
            if _is_missing(raw_v):
                rec[f.name] = None
                if f.required:
                    entry = {"field": f.name, "value": None, "expected": f.expected(params),
                             "policy": f.on_missing, "reason": "missing"}
                    (violations if f.on_missing == "reject" else flags).append(entry)
                continue
            value, reason = _parse(f, raw_v, params)
            if reason is not None:
                violations.append({"field": f.name, "value": _jsonable(raw_v), "expected": f.expected(params),
                                   "policy": "reject", "reason": reason})
                rec[f.name] = None
                continue
            rec[f.name] = value
        if not violations:
            for rule in rules:
                if rule.scope != "record":
                    continue
                reason = rule.check(rec, params)
                if reason:
                    entry = {"field": rule.field, "value": _jsonable(rec.get(rule.field)), "expected": rule.statement["en"],
                             "policy": rule.policy, "reason": reason, "rule": rule.id}
                    if rule.policy == "reject":
                        violations.append(entry)
                    elif rule.policy == "flag":
                        flags.append(entry)
                    else:
                        rec.setdefault("__exclude__", []).append(entry)
        if violations:
            report.rejected.append({"row": i, "key": _key(fam, raw), "violations": violations})
            continue
        for fl in flags:
            report.flagged.append({"row": i, "key": _key(fam, raw), **fl})
        parsed.append((i, rec))

    # group rules run on the records that passed the record-level checks
    drop: dict[int, dict[str, Any]] = {}
    exclude: dict[int, list[dict[str, Any]]] = {}
    for i, rec in parsed:
        if "__exclude__" in rec:
            exclude.setdefault(i, []).extend(rec.pop("__exclude__"))
    for rule in rules:
        if rule.scope != "group":
            continue
        groups: dict[tuple, list[tuple[int, dict[str, Any]]]] = {}
        for i, rec in parsed:
            if i in drop:
                continue
            groups.setdefault(tuple(rec.get(k) for k in rule.group_by), []).append((i, rec))
        for members in groups.values():
            if rule.order_by:
                members.sort(key=lambda m: (m[1].get(rule.order_by) is None, m[1].get(rule.order_by) or 0, m[0]))
            by_row = dict(members)
            for i, reason in rule.check(members, params):
                rec = by_row[i]
                entry = {"field": rule.field, "value": _jsonable(rec.get(rule.field)), "expected": rule.statement["en"],
                         "policy": rule.policy, "reason": reason, "rule": rule.id}
                if rule.policy == "reject":
                    drop[i] = entry
                elif rule.policy == "flag":
                    report.flagged.append({"row": i, "key": _key(fam, rec), **entry})
                else:
                    exclude.setdefault(i, []).append(entry)
    for i, rec in parsed:
        if i in drop:
            report.rejected.append({"row": i, "key": _key(fam, rec), "violations": [drop[i]]})
        elif i in exclude:
            report.excluded.append({"row": i, "key": _key(fam, rec), **exclude[i][0]})
        else:
            report.accepted.append(rec)
    report.rejected.sort(key=lambda r: r["row"])
    report.flagged.sort(key=lambda r: r["row"])
    report.ignored_columns = sorted(ignored)
    return report


def _key(fam: Family, rec: Mapping[str, Any]) -> str:
    """A short identifier for a record in a report (the family's first field and, if present, its date)."""
    first = fam.fields[0].name
    date_field = next((f.name for f in fam.fields if f.kind == "date"), None)
    parts = [str(_jsonable(rec.get(first)))]
    if date_field and date_field != first:
        parts.append(str(_jsonable(rec.get(date_field))))
    return " ".join(parts)


# --- rule checks -------------------------------------------------------------------------------------------------


def _unique(members: Sequence[tuple[int, Mapping[str, Any]]], _params: Mapping[str, Any]) -> list[tuple[int, str]]:
    return [(i, "duplicate of an earlier record") for i, _ in members[1:]]


def _months_between(a: dt.date, b: dt.date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def _business_days_between(a: dt.date, b: dt.date) -> int:
    """Weekdays strictly after ``a`` up to and including ``b`` (no holiday calendar)."""
    days = (b - a).days
    weeks, rest = divmod(days, 7)
    count = weeks * 5
    for k in range(1, rest + 1):
        if (a + dt.timedelta(days=k)).weekday() < 5:
            count += 1
    return count


def _dpd_jumps(members: Sequence[tuple[int, Mapping[str, Any]]], _params: Mapping[str, Any]) -> list[tuple[int, str]]:
    out = []
    for (_, prev), (i, cur) in zip(members, members[1:]):
        months = max(1, _months_between(prev["reporting_date"], cur["reporting_date"]))
        jump = cur["dpd"] - prev["dpd"]
        if jump > 31 * months:
            out.append((i, f"days past due rose by {jump} in {months} month(s)"))
    return out


def _open_workouts(members: Sequence[tuple[int, Mapping[str, Any]]], params: Mapping[str, Any]) -> list[tuple[int, str]]:
    cutoff = _param_date(params, "workout_cutoff")
    if cutoff is None:
        return []
    defaulted = any(r.get("default_flag") == 1 and r["reporting_date"] <= cutoff for _, r in members)
    if not defaulted:
        return []
    closed = any(r.get("workout_closed") == 1 and r["reporting_date"] <= cutoff for _, r in members)
    if closed:
        return []
    return [(i, f"the workout is still open at the cutoff {cutoff.isoformat()}") for i, _ in members]


def _gaps(members: Sequence[tuple[int, Mapping[str, Any]]], _params: Mapping[str, Any]) -> list[tuple[int, str]]:
    out = []
    for (_, prev), (i, cur) in zip(members, members[1:]):
        gap = _business_days_between(prev["date"], cur["date"])
        if gap > 5:
            out.append((i, f"{gap} business days since the previous observation"))
    return out


def _monotone_tenors(members: Sequence[tuple[int, Mapping[str, Any]]], _params: Mapping[str, Any]) -> list[tuple[int, str]]:
    out = []
    last = -math.inf
    for i, rec in members:
        if rec["tenor_years"] <= last:
            out.append((i, f"tenor {rec['tenor_years']:g} after tenor {last:g}"))
        else:
            last = rec["tenor_years"]
    return out


def _orig_before_report(rec: Mapping[str, Any], _p: Mapping[str, Any]) -> str | None:
    if rec["origination_date"] > rec["reporting_date"]:
        return f"origination {rec['origination_date']} after reporting {rec['reporting_date']}"
    return None


def _limit_covers_balance(rec: Mapping[str, Any], _p: Mapping[str, Any]) -> str | None:
    if rec.get("revolving") != 1:
        return None
    if rec.get("limit") is None:
        return "a revolving line without a limit"
    if rec["limit"] < rec["balance"]:
        return f"limit {rec['limit']:g} below balance {rec['balance']:g}"
    return None


def _cashflow_dated(rec: Mapping[str, Any], _p: Mapping[str, Any]) -> str | None:
    if rec.get("workout_cashflow") is None:
        return None
    when = rec.get("workout_cashflow_date")
    if when is None:
        return "a workout cash flow without its date"
    if when < rec["origination_date"]:
        return f"a workout cash flow dated {when} before origination"
    return None


def _withdrawn(rec: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
    if rec["grade"] == "WR" and params.get("wr_convention") in ("exclude", "censor"):
        return f"withdrawn rating, handled by the {params['wr_convention']!r} convention"
    return None


def _withdrawn_excluded(rec: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
    return _withdrawn(rec, params) if params.get("wr_convention") == "exclude" else None


def _withdrawn_censored(rec: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
    return _withdrawn(rec, params) if params.get("wr_convention") == "censor" else None


def _rate_plausible(rec: Mapping[str, Any], _p: Mapping[str, Any]) -> str | None:
    if not -0.05 <= rec["rate"] <= 0.30:
        return f"rate {rec['rate']:g} outside [-0.05, 0.30] (a rate in percent, or a stressed curve?)"
    return None


def _nmd_caps(rec: Mapping[str, Any], _p: Mapping[str, Any]) -> str | None:
    caps = NMD_CAPS.get(rec["behavioural_class"])
    if caps is None:
        return None
    share_cap, maturity_cap = caps
    found = []
    if rec.get("core_share") is not None and rec["core_share"] > share_cap:
        found.append(f"core share {rec['core_share']:g} above the cap {share_cap:g}")
    if rec.get("core_avg_maturity_years") is not None and rec["core_avg_maturity_years"] > maturity_cap:
        found.append(f"average maturity of core {rec['core_avg_maturity_years']:g} y above the cap {maturity_cap:g} y")
    return "; ".join(found) + "; the engine applies the cap" if found else None


def _above_threshold(rec: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
    threshold = float(params["collection_threshold"])
    if rec["gross_loss"] < threshold:
        return f"gross loss {rec['gross_loss']:g} below the collection threshold {threshold:g}"
    return None


def _recovery_within_loss(rec: Mapping[str, Any], _p: Mapping[str, Any]) -> str | None:
    if rec.get("recovery") is not None and rec["recovery"] > rec["gross_loss"]:
        return f"recovery {rec['recovery']:g} exceeds the gross loss {rec['gross_loss']:g}"
    return None


def _vintage_known(rec: Mapping[str, Any], params: Mapping[str, Any]) -> str | None:
    obs = _param_date(params, "observation_date")
    if obs is not None and rec["vintage_date"] > obs:
        return f"vintage {rec['vintage_date']} after the observation date {obs}"
    return None


def _scale_has_default(params: Mapping[str, Any]) -> str | None:
    grades = list(params.get("grades") or ())
    if "D" not in grades:
        return "the declared grade scale has no default grade 'D'"
    if "WR" in grades:
        return "'WR' is not a grade of the scale; it is handled by wr_convention"
    if len(set(grades)) != len(grades):
        return "the declared grade scale repeats a grade"
    return None


# --- the eight families ------------------------------------------------------------------------------------------


def _t(en: str, es: str) -> Text:
    return {"en": en, "es": es}


_FLAG = dict(kind="flag")

SCORED_SAMPLE = Family(
    name="scored_sample",
    title=_t("Scored sample", "Muestra puntuada"),
    used_by=_t("Every PD and ML case: one row per obligor or account at its observation date.",
               "Todo caso de PD y de ML: una fila por deudor o cuenta en su fecha de observación."),
    fields=(
        Field("id", "str", _t("Obligor or account identifier", "Identificador del deudor o de la cuenta")),
        Field("observation_date", "date", _t("Date at which the features are observed",
                                             "Fecha en que se observan las variables")),
        Field("target", "flag", _t("Default (1) or not (0) over the case's horizon",
                                   "Incumplimiento (1) o no (0) en el horizonte del caso")),
        Field("score", "float", _t("Model score, in the units the case declares", "Puntaje del modelo, en las unidades que declara el caso"),
              required=False),
        Field("pd", "float", _t("Probability of default", "Probabilidad de incumplimiento"), unit="probability",
              lo=0.0, hi=1.0, lo_open=True, hi_open=True, required=False),
        Field("grade", "enum", _t("Rating grade, from the declared scale", "Grado de calificación, de la escala declarada"),
              values_param="grades", required=False),
        Field("segment", "str", _t("Segment for the per-segment tests", "Segmento para las pruebas por segmento"),
              required=False),
        Field("protected_attr", "str", _t("Protected attribute, for the fairness tests only; never a model input",
                                          "Atributo protegido, solo para las pruebas de equidad; nunca una entrada del modelo"),
              required=False),
    ),
    rules=(
        Rule("SS-UNIQUE", "group", "reject", "id",
             _t("Each identifier appears once per observation date.",
                "Cada identificador aparece una vez por fecha de observación."),
             _unique, group_by=("id", "observation_date")),
    ),
    params=(Param("grades", "list", _t("The grade scale, best to worst", "La escala de grados, de mejor a peor"),
                  required=False),),
    open_fields=True,
    notes=(_t("The case declares its features with their units; a missing feature is flagged, and imputation is "
              "fitted on the training slice only.",
              "El caso declara sus variables con sus unidades; una variable faltante se marca, y la imputación se "
              "ajusta solo con el tramo de entrenamiento."),),
)

LOAN_PANEL = Family(
    name="loan_panel",
    title=_t("Loan panel", "Panel de préstamos"),
    used_by=_t("Lifetime PD, IFRS 9 staging and ECL, LGD and EAD: one row per account per reporting date.",
               "PD de vida completa, etapas y PCE de IFRS 9, LGD y EAD: una fila por cuenta y fecha de reporte."),
    fields=(
        Field("account_id", "str", _t("Account identifier", "Identificador de la cuenta")),
        Field("reporting_date", "date", _t("Reporting date of the row", "Fecha de reporte de la fila")),
        Field("origination_date", "date", _t("Origination date of the account", "Fecha de originación de la cuenta")),
        Field("balance", "float", _t("Outstanding balance", "Saldo vigente"), unit="currency", lo=0.0),
        Field("limit", "float", _t("Credit limit (revolving lines)", "Límite de crédito (líneas rotativas)"),
              unit="currency", lo=0.0, required=False),
        Field("revolving", "flag", _t("Revolving line (1) or amortising loan (0)", "Línea rotativa (1) o préstamo amortizable (0)")),
        Field("eir", "float", _t("Effective interest rate", "Tasa de interés efectiva"), unit="annual, decimal",
              lo=0.0, hi=1.0),
        Field("dpd", "int", _t("Days past due", "Días de mora"), unit="days", lo=0),
        Field("default_flag", "flag", _t("In default at this date", "En incumplimiento en esta fecha")),
        Field("prepay_flag", "flag", _t("Prepaid at this date", "Prepagado en esta fecha")),
        Field("writeoff_flag", "flag", _t("Written off at this date", "Castigado en esta fecha")),
        Field("workout_cashflow", "float", _t("Workout cash flow (recoveries positive, costs negative)",
                                              "Flujo de recuperación (recuperos positivos, costos negativos)"),
              unit="currency", required=False),
        Field("workout_cashflow_date", "date", _t("Date of the workout cash flow", "Fecha del flujo de recuperación"),
              required=False),
        Field("workout_closed", "flag", _t("The workout is closed", "La recuperación está cerrada"), required=False),
    ),
    rules=(
        Rule("LP-DATES", "record", "reject", "origination_date",
             _t("The origination date is on or before the reporting date.",
                "La fecha de originación es anterior o igual a la fecha de reporte."), _orig_before_report),
        Rule("LP-LIMIT", "record", "reject", "limit",
             _t("A revolving line has a limit at least as large as its balance.",
                "Una línea rotativa tiene un límite al menos igual a su saldo."), _limit_covers_balance),
        Rule("LP-CASHFLOW", "record", "reject", "workout_cashflow_date",
             _t("A workout cash flow carries its date, on or after origination.",
                "Un flujo de recuperación lleva su fecha, igual o posterior a la originación."), _cashflow_dated),
        Rule("LP-UNIQUE", "group", "reject", "reporting_date",
             _t("One row per account and reporting date.", "Una fila por cuenta y fecha de reporte."),
             _unique, group_by=("account_id", "reporting_date")),
        Rule("LP-DPD-JUMP", "group", "flag", "dpd",
             _t("Days past due rise by at most 31 per month between reports.",
                "Los días de mora suben como máximo 31 por mes entre reportes."),
             _dpd_jumps, group_by=("account_id",), order_by="reporting_date"),
        Rule("LP-WORKOUT-OPEN", "group", "exclude", "workout_closed",
             _t("A defaulted account whose workout is still open at the cutoff is excluded from LGD and counted.",
                "Una cuenta en incumplimiento cuya recuperación sigue abierta al corte se excluye de la LGD y se cuenta."),
             _open_workouts, group_by=("account_id",), order_by="reporting_date"),
    ),
    params=(Param("workout_cutoff", "date", _t("Cutoff date for closed workouts (LGD cases)",
                                               "Fecha de corte para recuperaciones cerradas (casos de LGD)"),
                  required=False),),
)

RATING_HISTORY = Family(
    name="rating_history",
    title=_t("Rating history", "Historia de calificaciones"),
    used_by=_t("Transition matrices, default rates by grade and TTC calibration.",
               "Matrices de transición, tasas de incumplimiento por grado y calibración TTC."),
    fields=(
        Field("obligor_id", "str", _t("Obligor identifier", "Identificador del deudor")),
        Field("date", "date", _t("Date of the rating", "Fecha de la calificación")),
        Field("grade", "enum", _t("Grade from the declared scale, the default grade D, or WR (withdrawn)",
                                  "Grado de la escala declarada, el grado de incumplimiento D, o WR (retirada)"),
              values=("WR",), values_param="grades"),
    ),
    rules=(
        Rule("RH-WR-EXCLUDE", "record", "exclude", "grade",
             _t("Under the exclude convention a withdrawn rating is removed and counted.",
                "Con la convención de exclusión, una calificación retirada se elimina y se cuenta."), _withdrawn_excluded),
        Rule("RH-WR-CENSOR", "record", "flag", "grade",
             _t("Under the censor convention a withdrawn rating censors the obligor at that date, and is counted.",
                "Con la convención de censura, una calificación retirada censura al deudor en esa fecha, y se cuenta."),
             _withdrawn_censored),
        Rule("RH-UNIQUE", "group", "reject", "date",
             _t("One rating per obligor and date.", "Una calificación por deudor y fecha."),
             _unique, group_by=("obligor_id", "date")),
    ),
    params=(
        Param("grades", "list", _t("The grade scale, best to worst, including D", "La escala de grados, de mejor a peor, con D")),
        Param("wr_convention", "enum", _t("How a withdrawn rating is handled", "Cómo se trata una calificación retirada"),
              values=WR_CONVENTIONS),
    ),
    param_checks=((_t("The declared grade scale includes the default grade D, does not list WR, and repeats no grade.",
                      "La escala de grados declarada incluye el grado de incumplimiento D, no incluye WR y no repite "
                      "grados."), _scale_has_default),),
)

MARKET_SERIES = Family(
    name="market_series",
    title=_t("Market series", "Serie de mercado"),
    used_by=_t("VaR and ES, backtests and stress windows: one row per series and date.",
               "VaR y ES, backtests y ventanas de estrés: una fila por serie y fecha."),
    fields=(
        Field("date", "date", _t("Observation date", "Fecha de observación")),
        Field("series_id", "str", _t("Series identifier", "Identificador de la serie")),
        Field("value", "float", _t("Observed value, in the declared unit", "Valor observado, en la unidad declarada")),
        Field("unit", "enum", _t("Unit: a simple or log return, a level, or a rate in decimal",
                                 "Unidad: un retorno simple o logarítmico, un nivel, o una tasa en decimal"),
              values=SERIES_UNITS),
    ),
    rules=(
        Rule("MS-UNIQUE", "group", "reject", "date",
             _t("One value per series and date.", "Un valor por serie y fecha."),
             _unique, group_by=("series_id", "date")),
        Rule("MS-GAP", "group", "flag", "date",
             _t("Consecutive observations are at most 5 business days apart.",
                "Las observaciones consecutivas distan como máximo 5 días hábiles."),
             _gaps, group_by=("series_id",), order_by="date"),
    ),
    notes=(_t("No value is forward-filled across a forecast date: a forecast for day t uses data up to t-1 only.",
              "Ningún valor se arrastra hacia adelante a través de una fecha de pronóstico: el pronóstico del día t "
              "usa datos hasta t-1."),),
)

CURVE = Family(
    name="curve",
    title=_t("Yield curve", "Curva de tasas"),
    used_by=_t("IRRBB, rates VaR, exposure simulation: one row per curve date and tenor.",
               "IRRBB, VaR de tasas, simulación de exposición: una fila por fecha de curva y plazo."),
    fields=(
        Field("date", "date", _t("Curve date", "Fecha de la curva")),
        Field("tenor_years", "float", _t("Tenor", "Plazo"), unit="years", lo=0.0, lo_open=True),
        Field("rate", "float", _t("Rate in decimal", "Tasa en decimal"), unit="decimal"),
        Field("compounding", "enum", _t("Compounding convention", "Convención de capitalización"), values=COMPOUNDING),
    ),
    rules=(
        Rule("CV-MONOTONE", "group", "reject", "tenor_years",
             _t("Within a curve date, tenors are strictly increasing.",
                "Dentro de una fecha de curva, los plazos son estrictamente crecientes."),
             _monotone_tenors, group_by=("date",)),
        Rule("CV-RANGE", "record", "flag", "rate",
             _t("Rates lie in [-0.05, 0.30].", "Las tasas están en [-0,05; 0,30]."), _rate_plausible),
    ),
)

BALANCE_SHEET = Family(
    name="balance_sheet",
    title=_t("Balance sheet", "Balance"),
    used_by=_t("IRRBB and liquidity: one row per item, currency and repricing band.",
               "IRRBB y liquidez: una fila por partida, moneda y banda de reprecio."),
    fields=(
        Field("as_of", "date", _t("Balance-sheet date", "Fecha del balance")),
        Field("item", "str", _t("Balance-sheet item", "Partida del balance")),
        Field("currency", "enum", _t("Currency (CLF is the UF)", "Moneda (CLF es la UF)"), values=CURRENCIES),
        Field("amount", "float", _t("Amount, assets positive and liabilities negative",
                                    "Monto, activos positivos y pasivos negativos"), unit="currency"),
        Field("repricing_bucket", "enum", _t("Repricing time band (SRP31.96 Table 3)",
                                             "Banda temporal de reprecio (SRP31.96 Tabla 3)"),
              values=tuple(b for b, _ in REPRICING_BANDS)),
        Field("behavioural_class", "enum", _t("Behavioural class", "Clase de comportamiento"), values=BEHAVIOURAL_CLASSES),
        Field("core_share", "float", _t("Core share of a non-maturity deposit", "Porción estable de un depósito a la vista"),
              unit="fraction", lo=0.0, hi=1.0, required=False),
        Field("core_avg_maturity_years", "float", _t("Average maturity of the core", "Plazo promedio de la porción estable"),
              unit="years", lo=0.0, required=False),
    ),
    rules=(
        Rule("BS-NMD-CAPS", "record", "flag", "core_share",
             _t("Core non-maturity deposits respect the caps of SRP31 Table 4; above them the engine applies the cap.",
                "Los depósitos a la vista estables respetan los topes de SRP31 Tabla 4; sobre ellos el motor aplica el tope."),
             _nmd_caps),
    ),
    notes=(_t("Band midpoints in years, SRP31.96 Table 3: " + ", ".join(f"{b} {m:g}" for b, m in REPRICING_BANDS) + ".",
              "Puntos medios de las bandas en años, SRP31.96 Tabla 3: "
              + ", ".join(f"{b} {str(m).replace('.', ',')}" for b, m in REPRICING_BANDS) + "."),),
)

LOSS_EVENTS = Family(
    name="loss_events",
    title=_t("Operational loss events", "Eventos de pérdida operacional"),
    used_by=_t("Operational risk LDA and SMA: one row per loss event.",
               "LDA y SMA de riesgo operacional: una fila por evento de pérdida."),
    fields=(
        Field("event_id", "str", _t("Event identifier", "Identificador del evento")),
        Field("date", "date", _t("Accounting date of the loss (OPE25.19)", "Fecha contable de la pérdida (OPE25.19)")),
        Field("business_line", "str", _t("Business line, from the case's vocabulary", "Línea de negocio, del vocabulario del caso")),
        Field("event_type", "enum", _t("Level 1 event type (OPE25.17 Table 2)", "Tipo de evento de nivel 1 (OPE25.17 Tabla 2)"),
              values=EVENT_TYPES),
        Field("gross_loss", "float", _t("Gross loss", "Pérdida bruta"), unit="currency", lo=0.0, lo_open=True),
        Field("recovery", "float", _t("Recovery", "Recupero"), unit="currency", lo=0.0, required=False),
    ),
    rules=(
        Rule("LE-THRESHOLD", "record", "reject", "gross_loss",
             _t("A loss is at or above the collection threshold; truncation is modelled, not silently kept.",
                "Una pérdida está en o sobre el umbral de recolección; el truncamiento se modela, no se oculta."),
             _above_threshold),
        Rule("LE-RECOVERY", "record", "flag", "recovery",
             _t("A recovery does not exceed its gross loss.", "Un recupero no supera su pérdida bruta."),
             _recovery_within_loss),
        Rule("LE-UNIQUE", "group", "reject", "event_id",
             _t("Each event appears once.", "Cada evento aparece una vez."), _unique, group_by=("event_id",)),
    ),
    params=(
        Param("collection_threshold", "float", _t("Loss collection threshold (OPE25.18: EUR 20,000)",
                                                  "Umbral de recolección de pérdidas (OPE25.18: EUR 20.000)")),
        Param("currency", "enum", _t("Currency of the amounts", "Moneda de los montos"), values=CURRENCIES),
    ),
)

MACRO_PATH = Family(
    name="macro_path",
    title=_t("Macro path", "Trayectoria macro"),
    used_by=_t("Stress testing, IFRS 9 scenarios, satellites: one row per scenario, variable and date.",
               "Pruebas de tensión, escenarios de IFRS 9, satélites: una fila por escenario, variable y fecha."),
    fields=(
        Field("scenario", "str", _t("Scenario name", "Nombre del escenario")),
        Field("date", "date", _t("Date of the value", "Fecha del valor")),
        Field("variable", "str", _t("Macro variable", "Variable macro")),
        Field("value", "float", _t("Value, in the stated unit", "Valor, en la unidad indicada")),
        Field("unit", "str", _t("Unit of the value", "Unidad del valor")),
        Field("vintage_date", "date", _t("Date the path was published", "Fecha de publicación de la trayectoria")),
    ),
    rules=(
        Rule("MP-VINTAGE", "record", "reject", "vintage_date",
             _t("A path is published on or before the model's observation date (no look-ahead).",
                "Una trayectoria se publica antes o en la fecha de observación del modelo (sin mirar al futuro)."),
             _vintage_known),
        Rule("MP-UNIQUE", "group", "reject", "date",
             _t("One value per scenario, variable and date.", "Un valor por escenario, variable y fecha."),
             _unique, group_by=("scenario", "variable", "date")),
    ),
    params=(Param("observation_date", "date", _t("The model's observation date", "La fecha de observación del modelo")),),
)

FAMILIES: dict[str, Family] = {
    f.name: f for f in (SCORED_SAMPLE, LOAN_PANEL, RATING_HISTORY, MARKET_SERIES, CURVE, BALANCE_SHEET, LOSS_EVENTS,
                        MACRO_PATH)
}


def export_contracts(out_dir: Any) -> list[str]:
    """Write every family to ``<out_dir>/<family>.json`` and an ``index.json``; return the file names written."""
    from pathlib import Path

    from .formats import write_json

    out = Path(out_dir)
    names = []
    for fam in FAMILIES.values():
        write_json(out / f"{fam.name}.json", fam.to_json())
        names.append(f"{fam.name}.json")
    write_json(out / "index.json", {"schema": SCHEMA, "families": [
        {"family": f.name, "title": f.title, "path": f"{f.name}.json"} for f in FAMILIES.values()]})
    return [*names, "index.json"]
