# Engine governance API contract: `engine-governance-api` 1.0.0

Owner: U15-S (unit sizing `plans/contraste/units/U15-sizing.md`, CAOS_MANAGE). Implemented by U15-E in `riskvalidation.governance` and
`riskvalidation.validation.governance` (repository CAOS_RiskValidation, released with the engine tag that follows v0.08.000, R1 of the sizing);
called by the governance bake (U15-P, `data-pipeline/pipeline/governance/`). The tests of every function are written by U15-E against this file: a
function exists with exactly the signature below, and each golden value or invariant is a test. Changing a signature, a unit or a golden value is a breaking change (a new major version of this contract). Sources: dossier 06 (`wip/contraste/06-model-risk-management-and-validation-2026-10-04.md`:
B.1 the scope test l.523-537, B.2 the inventory attributes l.539-551, B.3 the tiering rubric l.553-574, B.4 the lifecycle l.576-583, B.6 approval and
the model risk appetite l.601-612, B.7 findings severity and remediation l.614-628, B.8 frequency by tier l.630-640, I.3 the validation report
l.1219-1237, I.6 what not to claim l.1261-1277), the U15 research addendum (`wip/contraste/u15-research-addendum-2026-10-20.md`, D1 to D6) and the
unit sizing decisions W15-1 to W15-9.

Scope. The engine computes; it approves nothing and certifies nothing (SDD non-goal 1; 06 I.6). Every tier count, band, deadline, frequency and
threshold of this contract is a stated convention (item 30 of the dossier UNVERIFIED list, l.1321-1322): a named parameter that carries the label
`convention` and its basis, passed to the function as an argument with the default below, and never presented as a value taken from a regulation.
The opinion levels and the 5 and 10 percent cut points of an RWEA anchor are the ECB's (Instructions of February 2019, section 2.4.2, confirmed in A
D6); the rule that turns findings into a level is a convention (W15-7). UNVERIFIED, carried from the dossier: the SS1/23 2026 text against the 2023
text (not diffed), the OSFI 2017 rescission, the EU AI Act Annex III 5(b) reading, a post-2019 ECB reporting instruction, the EBA draft RTS on
material model changes. OSFI's transition is "an 18-month transition period" in OSFI's own words.

Version history: 1.0.0, the first contract (2026-10-20). Still unreleased, so the version stays 1.0.0: the fix round after the Opus review of 2026-10-20 (decisions
W15-11 to W15-15 and the review's B1, M1 to M6, m1 to m11) amends it in place before U15-E writes its tests from it.

## Conventions (all functions)

- Dates are `datetime.date`; the documents write them as ISO strings. No function reads the clock, the environment or a file: the as-of date is
  an argument, and every raised date is the release date of a committed code version (R4 of the sizing). Inputs are never mutated.
- Money is never converted; shares and ratios are decimals (a share of 5 percent is `0.05`); a day count is an integer; a month count is an integer
  of calendar months (an addition clamps the day to the end of the target month).
- Severities are the product's `"S1"` (critical) to `"S4"` (minor), with the ECB F equivalent beside them (W15-2). Tiers are integers 1 to 4. The
  seven finding states are `open`, `action_plan_agreed`, `in_progress`, `submitted_for_closure`, `validated_closed`, `overdue`, `risk_accepted`
  (06 l.624-628). The lifecycle states are the twelve of B.4.
- Dataclasses are frozen. A function that cannot compute a value raises `ValueError` with the reason; nothing returns a placeholder number. The
  `gov.` validation functions return one `TestResult` (`core/result.py`), serialised by `TestResult.to_dict()` into a row that validates against
  `common/test-result`.
- The as-of date (W15-13): every document carries `as_of` and `as_of_basis` (label `convention`, a basis in English and Spanish). The production rule is the date of the newest release
  heading of `CHANGELOG.md` when the bake runs: committed (R4), never later than publication, never earlier than a raised date (the checker refuses an `as_of` before the newest
  raised date or last validation date). A fixture says its date is "a fixture date chosen after the due dates to exercise the overdue rule; not the date of publication".
- Text rules: no string of a governance document states that a model is approved, certified or compliant (the checker's `approval_claims`, English and Spanish, the fixed negations
  "Contraste approves no model" and "no approval" exempt), and none calls a convention a requirement of a regulator or supervisor (`regulatory_claims`).
- The named convention parameters, each labelled `convention` with its basis in the document that carries it:
  - the exposure band cut points `EXPOSURE_BAND_CUTS = (0.25, 0.10, 0.02)` (share of the stated balance: 25 percent or more is 4, 10 percent 3,
    2 percent 2, below 1; 06 B.3 fixes no cut-offs);
  - the deadline table `DEADLINE_DAYS` in days from the raised date, severity S1 to S4 by tier 1 to 4: S1 `(30, 45, 60, 90)`, S2
    `(60, 90, 120, 180)`, S3 `(90, 120, 180, 270)`, S4 `(180, 270, 365, 365)` (06 B.7: no source prescribes days);
  - the frequency table `FREQUENCY` in months, tier to (review, full revalidation, monitoring): `1: (12, 36, 3)`, `2: (12, 36, 6)`,
    `3: (24, None, 12)`, `4: (36, None, None)` where tier 4 is an attestation (06 l.636-640);
  - the appetite thresholds, direction with a green limit and an amber limit, in `appetite_metrics`;
  - the regulatory-use grades (graded 4, 3, 2, 1; literal 4, 2 for compliance monitoring, or 1; the literal grade is never below the graded one), the complexity aggregation (the mean rounded half up) and the adopted reading B.

## Reused engine functions

Reused unchanged from the engine; this contract names them and never restates them.

| Function | Used by |
|---|---|
| `riskvalidation.core.result.TestResult` | every `gov.` validation function and the test rows the report reads |
| `riskvalidation.core.policy.Policy`, `riskvalidation.core.policy.Threshold` | `policy.resolve_policy` (the threshold kinds `p_value`, `upper_bad`, `lower_bad`) |
| `riskvalidation.core.policy.load_policy`, `riskvalidation.core.policy.default_policy` | `policy.resolve_policy` (a packaged label resolves through the policy file) |
| `riskvalidation.core.registry.catalogue`, `riskvalidation.core.registry.spec` | `report.build_report` (the definition of a test row, section 6) and `policy.resolve_policy` (the family) |
| `riskvalidation.core.suite.SuiteRun` | `report.executive_counts` (the same counting of lights) |
| `riskvalidation.core.hashing.inputs_hash` | `report.build_report` (the reproducibility manifest, section 12) |

## Module `riskvalidation/governance/scope.py`

The B.1 scope test (06 l.523-537): four answers and a jurisdiction profile give the in-scope decision with its rationale.

### `riskvalidation.governance.scope.ScopeAnswers`

```python
@dataclass(frozen=True)
class ScopeAnswers:
    applies_theory: bool            # (a) statistical, economic, financial or mathematical theory is applied
    output_is_estimate: bool        # (b) the output is an estimate
    deterministic: bool             # (c) a deterministic rule set
    generative_or_agentic: bool     # (d) a generative or agentic AI model
```

- Units: four booleans.
- Invariants: immutable; the four answers are all recorded, including the one a profile does not read.

### `riskvalidation.governance.scope.ScopeDecision`

```python
@dataclass(frozen=True)
class ScopeDecision:
    profile: str                    # "us-2026", "pra", "osfi-2027" or "ecb"
    in_scope: bool
    rationale: str                  # English; the bake adds the Spanish text
```

- Units: a profile name, a boolean, a sentence.
- Invariants: immutable; the rationale names the answers that decided it.

### `riskvalidation.governance.scope.scope_test`

```python
def scope_test(answers: ScopeAnswers, profile: str) -> ScopeDecision: ...
```

- Units: answers and a profile name.
- Rules (a reading of the B.1 table, UNVERIFIED beyond it): `us-2026` (SR 26-2) is in scope when (a) and (b) hold and not (d), so a deterministic rule
  set without theory (`applies_theory` false) and generative or agentic AI are out (A D6); `pra` (SS1/23 Principle 1.1) is in scope when (a) holds, the
  output need not be quantitative; `osfi-2027` (E-23) and `ecb` are in scope when (a) and (b) hold.
- Golden: `scope_test(ScopeAnswers(True, True, False, False), "us-2026").in_scope = True`; `scope_test(ScopeAnswers(True, True, False, True), "us-2026").in_scope = False`
  (generative or agentic); `scope_test(ScopeAnswers(False, True, True, False), "us-2026").in_scope = False` (a deterministic rule set with no theory);
  `scope_test(ScopeAnswers(True, False, False, False), "pra").in_scope = True`; `scope_test(ScopeAnswers(True, False, False, False), "ecb").in_scope = False`.
- Invariants: `ValueError` for an unknown profile.

### `riskvalidation.governance.scope.scope_record`

```python
def scope_record(answers: ScopeAnswers) -> tuple[ScopeDecision, ...]: ...
```

- Units: answers; returns the four decisions in the order `us-2026`, `pra`, `osfi-2027`, `ecb`.
- Golden: `scope_record(ScopeAnswers(True, True, False, False))` is four decisions, all in scope; with `generative_or_agentic` true the `us-2026` decision
  is out of scope and the other three are unchanged.
- Invariants: always four decisions in that order; the inventory field `scope.profiles` is this tuple (the description of the schema property names this function).

## Module `riskvalidation/governance/inventory.py`

The inventory (06 B.2, I.2): entries keyed `case_id/fit_id` (W15-1), their components, the dependency edges (W15-8) and the graph checks.

### `riskvalidation.governance.inventory.Component`

```python
@dataclass(frozen=True)
class Component:
    case_id: str
    fit_id: str
    model_id: str
    role: str                       # "champion", "challenger", "benchmark" or "reference"
    # key: property, f"{case_id}/{fit_id}/{model_id}"
```

- Units: identifiers and a role name.
- Invariants: the key is the triple, because model ids repeat across cases (A D1 A01); `ValueError` for a role outside the four.

### `riskvalidation.governance.inventory.Entry`

```python
@dataclass(frozen=True)
class Entry:
    case_id: str
    fit_id: str
    attributes: dict[str, dict]     # "A01" to "A40" -> {"value": ..., "status": ..., "basis": ...}
    variants: tuple[tuple[str, str], ...]   # (variant_id, basis of the assignment to this fit)
    components: tuple[Component, ...]
    # key: property, f"{case_id}/{fit_id}"
```

- Units: the 40 attributes of B.2, each an object with a value, a status and a basis; never a bare value.
- Invariants: the status is one of `present`, `derivable`, `convention`, `not-applicable`, `missing`; a `present` attribute has a basis naming a JSON
  pointer (`path#/pointer`); a `not-applicable` attribute has a reason of at least eight characters; a `missing` or `not-applicable` attribute has
  value `None`; A32 (approver) and A33 (approval date and authority) are `not-applicable` with value `None` because Contraste approves no model (SDD
  non-goal 1); `ValueError` names the attribute that breaks a rule. `variants` lists the variant documents of the entry with the basis of each assignment (W15-15, `assign_variant`);
  a register row's variant is always in its entry's list.

### `riskvalidation.governance.inventory.Edge`

```python
@dataclass(frozen=True)
class Edge:
    upstream: str                   # an entry key
    downstream: str                 # an entry key
    kind: str                       # "document" (a document read) or "code" (an import)
    stated_source: str              # the file and line, or the document field, that states it
```

- Units: two entry keys, a kind, a source string.
- Invariants: the stated source is non-empty; page statements, shared methods and shared sources are "related" links, never edges (W15-8).

### `riskvalidation.governance.inventory.Inventory`

```python
@dataclass(frozen=True)
class Inventory:
    entries: tuple[Entry, ...]
    edges: tuple[Edge, ...]
```

- Units: entries and edges, in the order given.
- Invariants: produced only by `build_inventory`; entry keys are unique; every component key is unique across the inventory; every edge joins two
  entries; the graph is acyclic.

### `riskvalidation.governance.inventory.assign_variant`

```python
def assign_variant(variant_sources: Sequence[str], fits: Mapping[str, Sequence[str]]) -> tuple[str | None, str]: ...
```

- Units: the source names the variant document's provenance reads, and the fits of its case as fit id to the source names of that fit; returns (fit id or `None`, basis or reason).
- Rule (W15-15): a case with one fit gives its variants to that fit ("the single models document of the case"); otherwise the fit whose sources contain all the variant's sources, when exactly
  one does. Any other variant is returned as `(None, reason)` and goes to the inventory's `excluded` list with that reason (a `variant_id` set), never assigned by guess.
- Golden: `assign_variant(['uci-german'], {'german': ['uci-german'], 'taiwan': ['uci-taiwan']}) = ('german', "the variant's provenance reads uci-german, the sources of the fit german")`;
  `assign_variant([], {'german': ['uci-german'], 'taiwan': ['uci-taiwan']})` is `(None, reason)`; `assign_variant(['x'], {'only': ['y']}) = ('only', 'the single models document of the case')`.
- Invariants: deterministic; the same variant never goes to two fits; the cross check holds every register row's variant in its entry's `variants`.

### `riskvalidation.governance.inventory.build_inventory`

```python
def build_inventory(entries: Sequence[Entry], edges: Sequence[Edge]) -> Inventory: ...
```

- Units: entries and edges.
- Golden: three entries with keys `A`, `B`, `C` and edges (`A`, `B`), (`B`, `C`), (`C`, `A`) raise `ValueError("dependency cycle: A, B, C, A")`: the cycle in
  dependency order, from its smallest key, closed on that key; a related link to an absent entry raises `ValueError("related link A and Z: unknown entry Z")`; an edge to an absent entry raises `ValueError("edge A to Z: unknown entry Z")`; two
  entries whose components share a key raise `ValueError("component key 'C01/german/P0' repeats")`.
- Invariants: a repeated entry key raises `ValueError`; a repeated edge (same upstream, downstream and kind) raises `ValueError`; zero entries raise `ValueError("the inventory holds no entry")`; a self edge raises `ValueError`; the order of entries and edges is kept; the engine node is not
  an entry (the engine edges are implicit: every entry depends on `riskvalidation`, W15-8).

### `riskvalidation.governance.inventory.topological_order`

```python
def topological_order(keys: Sequence[str], edges: Sequence[tuple[str, str]]) -> list[list[str]]: ...
```

- Units: keys and (upstream, downstream) pairs; returns the generations of Kahn's algorithm, each sorted.
- Golden: `topological_order(['A', 'B', 'C'], [('A', 'B'), ('B', 'C')]) = [['A'], ['B'], ['C']]`;
  `topological_order(['A', 'B', 'C'], [('A', 'C'), ('B', 'C')]) = [['A', 'B'], ['C']]`.
- Invariants: a cycle raises the `ValueError("dependency cycle: ...")` of `build_inventory`; the index of a key's generation is its depth.

### `riskvalidation.governance.inventory.graph_metrics`

```python
def graph_metrics(inventory: Inventory) -> dict[str, tuple[int, int, int]]: ...
```

- Units: returns entry key to (depth, fan-in, fan-out), counts of entries; the depth is the length of the longest dependency path to the entry.
- Golden: for the fixture inventory (edges C07/banco-andino to C18/banco-andino and C01/german to C22/generators): C01/german (0, 0, 1),
  C07/banco-andino (0, 0, 1), C18/banco-andino (1, 1, 0), C22/generators (1, 1, 0).
- Invariants: a source has depth 0; depth is the generation of `topological_order`; fan-in and fan-out count distinct entries.

### `riskvalidation.governance.inventory.attribute_completeness`

```python
def attribute_completeness(entries: Sequence[Entry]) -> dict[str, dict[str, int]]: ...
```

- Units: returns, for each of A01 to A40, the number of entries per status (`present`, `derivable`, `convention`, `not_applicable`, `missing`).
- Golden: for the four fixture entries A32 is `{"present": 0, "derivable": 0, "convention": 0, "not_applicable": 4, "missing": 0}` and A10 is
  `{"present": 0, "derivable": 0, "convention": 0, "not_applicable": 0, "missing": 4}`.
- Invariants: the five counts of an attribute sum to the number of entries.

## Module `riskvalidation/governance/tiering.py`

The tiering rubric (06 B.3 l.553-574): materiality, complexity, the 4 by 4 matrix, the override and the sensitivity of the tier to the rubric's readings (A D2).

### `riskvalidation.governance.tiering.exposure_band`

```python
def exposure_band(share: float | None, cuts: tuple[float, float, float] = EXPOSURE_BAND_CUTS) -> int: ...
```

- Units: `share` is a decimal share of the stated balance; `None` where no balance exists; returns 1 to 4. The exposure band cut points are a convention.
- Golden: `exposure_band(1.0) = 4`; `exposure_band(0.25) = 4`; `exposure_band(0.2499) = 3`; `exposure_band(0.1) = 3`; `exposure_band(0.0999) = 2`;
  `exposure_band(0.02) = 2`; `exposure_band(0.0199) = 1`; `exposure_band(0.0) = 1`; `exposure_band(None) = 1` (no balance: the floor).
- Invariants: monotone non-decreasing in the share; `ValueError` for a share outside [0, 1] or cut points that are not decreasing in (0, 1].

### `riskvalidation.governance.tiering.materiality`

```python
def materiality(band: int, regulatory_use: int, decision_criticality: int) -> int: ...
```

- Units: three scores 1 to 4; returns 1 to 4.
- Golden: `materiality(2, 3, 3) = 3` (C01, graded); `materiality(2, 4, 3) = 4` (C01, literal); `materiality(1, 1, 1) = 1` (C22).
- Invariants: the maximum of the three (06 l.563-566); `ValueError` for a score outside 1 to 4.

### `riskvalidation.governance.tiering.complexity`

```python
def complexity(scores: Sequence[int], aggregation: str = "mean", rounding: str = "half-up") -> int: ...
```

- Units: the scored factors, each 1 to 4 (an unscored factor is left out, never counted as 1); `aggregation` is `"mean"` or `"maximum"`; returns 1 to 4.
- Golden: `complexity([4, 2, 3, 1, 1, 1]) = 2` (mean 2.00, C01); `complexity([2, 2, 1, 1, 2, 1]) = 2` (mean 1.50 rounds up, C15);
  `complexity([2, 2, 1, 1, 1, 1]) = 1` (mean 1.33); `complexity([3, 3, 3, 2, 2, 2]) = 3` (mean 2.50 rounds up); `complexity([2, 1, 1, 1, 1, 1]) = 1`;
  `complexity([4, 2, 3, 1, 1, 1], aggregation="maximum") = 4`.
- Invariants: the mean is rounded half up in integer arithmetic, `(2 * sum + n) // (2 * n)`, so no floating point decides a boundary; `ValueError` for
  an empty list, a score outside 1 to 4 or an unknown aggregation or rounding.

### `riskvalidation.governance.tiering.matrix_tier`

```python
def matrix_tier(m: int, c: int) -> int: ...
```

- Units: materiality and complexity, each 1 to 4; returns the tier 1 to 4 (1 is the highest): Tier 1 if M is 4 or (M is 3 and C is 3 or more); Tier 2 if M is 3
  or (M is 2 and C is 3 or more); Tier 3 if M is 2 or (M is 1 and C is 3 or more); Tier 4 otherwise (06 l.571-574).
- Golden, the whole matrix:
- `M=4: C1=1 C2=1 C3=1 C4=1`
- `M=3: C1=2 C2=2 C3=1 C4=1`
- `M=2: C1=3 C2=3 C3=2 C4=2`
- `M=1: C1=4 C2=4 C3=3 C4=3`
- Invariants: the tier never worsens when M or C rises; `ValueError` for a value outside 1 to 4.

### `riskvalidation.governance.tiering.apply_override`

```python
def apply_override(computed_tier: int, override: tuple[int, str, str] | None = None) -> int: ...
```

- Units: the computed tier and an optional override (to_tier, rationale, approver).
- Golden: `apply_override(2, None) = 2`; `apply_override(2, (1, "the model feeds the stress test", "Chief Risk Officer")) = 1`.
- Invariants: an override with an empty rationale or an empty approver raises `ValueError("an override needs a rationale and an approver")`, never
  silent (SS1/23 Principle 1.3(d)(e)); the computed tier stays in the document beside the final tier.

### `riskvalidation.governance.tiering.tier_sensitivity`

```python
def tier_sensitivity(share: float | None, regulatory_use_literal: int, regulatory_use_graded: int, decision_criticality: int,
                     scores: Sequence[int], cuts: tuple[float, float, float] = EXPOSURE_BAND_CUTS) -> tuple[tuple[str, str, str, int, int, int], ...]: ...
```

- Units: returns four rows (reading, regulatory use, complexity aggregation, M, C, tier) for the readings A (literal, mean), B (graded, mean), C (literal,
  maximum) and D (graded, maximum); B is the adopted reading (W15-3).
- Golden, the tiers A to D of the 19 built cases from the stated inputs of A D2 (3.2, 3.3 and the table 3.4 of the U15 research addendum):
```
C01: A=1 B=2 C=1 D=1
C03: A=1 B=2 C=1 D=1
C04: A=1 B=1 C=1 D=1
C05: A=1 B=1 C=1 D=1
C06: A=1 B=1 C=1 D=1
C07: A=1 B=1 C=1 D=1
C08: A=1 B=2 C=1 D=1
C09: A=1 B=2 C=1 D=2
C10: A=1 B=1 C=1 D=1
C11: A=1 B=2 C=1 D=1
C12: A=1 B=1 C=1 D=1
C13: A=1 B=2 C=1 D=2
C14: A=1 B=1 C=1 D=1
C15: A=1 B=1 C=1 D=1
C16: A=1 B=1 C=1 D=1
C17: A=1 B=1 C=1 D=1
C18: A=1 B=1 C=1 D=1
C21: A=1 B=1 C=1 D=1
C22: A=4 B=4 C=4 D=4
reading A: 18/0/0/1
reading B: 12/6/0/1
reading C: 18/0/0/1
reading D: 16/2/0/1
```
- Invariants: the rows are in the order A, B, C, D; each tier is `matrix_tier` of its own M and C; reading A never gives a higher tier number than reading B for the
  same inputs (literal regulatory use is never below graded, so `ValueError` when the literal grade is below the graded one); the inputs a case lacks (history against horizon) are unscored, never counted.

### `riskvalidation.governance.tiering.tier_counts`

```python
def tier_counts(tiers: Sequence[int]) -> tuple[int, int, int, int]: ...
```

- Units: tiers 1 to 4; returns the number of entries in tiers 1, 2, 3 and 4.
- Golden: `tier_counts([1, 2, 1, 4]) = (2, 1, 0, 1)`; `tier_counts([]) = (0, 0, 0, 0)`.
- Invariants: the counts sum to the number of tiers; `ValueError` for a tier outside 1 to 4.

## Module `riskvalidation/governance/lifecycle.py`

The B.4 states and transitions (06 l.576-583), a convention synthesised from SS1/23 para 2.10, OSFI E-23 and SR 11-7.

### `riskvalidation.governance.lifecycle.allowed_next`

```python
def allowed_next(state: str) -> tuple[str, ...]: ...
```

- Units: a state name; returns the states reachable in one step without an exception record.
- Golden, every allowed transition (the other pairs of the twelve states are refused):
- allowed: proposed to in_development
- allowed: in_development to submitted_for_validation
- allowed: submitted_for_validation to in_validation
- allowed: in_validation to approved
- allowed: in_validation to approved_with_conditions
- allowed: in_validation to in_development
- allowed: approved to in_use
- allowed: approved_with_conditions to in_use
- allowed: in_use to under_monitoring_alert
- allowed: in_use to material_change_pending
- allowed: in_use to in_validation
- allowed: in_use to restricted
- allowed: in_use to decommissioned
- allowed: under_monitoring_alert to in_use
- allowed: under_monitoring_alert to restricted
- allowed: under_monitoring_alert to in_remediation
- allowed: restricted to in_remediation
- allowed: restricted to in_use
- allowed: restricted to decommissioned
- allowed: in_remediation to in_validation
- allowed: in_remediation to restricted
- allowed: in_remediation to decommissioned
- allowed: material_change_pending to submitted_for_validation
- allowed: material_change_pending to in_use
- Invariants: decommissioned is terminal (`allowed_next("decommissioned") = ()`); a decommissioned model may serve as a challenger but does not re-enter
  the lifecycle; `ValueError` for an unknown state.

### `riskvalidation.governance.lifecycle.transition`

```python
def transition(state: str, to: str, exception: tuple[str, str, date] | None = None) -> str: ...
```

- Units: two states and an optional exception record (type, approver, expiry date).
- Golden: `transition("proposed", "in_development") = "in_development"`; `transition("proposed", "in_use")` raises
  `ValueError("cannot move from 'proposed' to 'in_use'")`; `transition("in_validation", "in_use")` raises the same error with its two states;
  `transition("in_validation", "in_use", ("use before validation", "Chief Risk Officer", date(2027, 1, 31))) = "in_use"`.
- Invariants: use before validation, from `in_development`, `submitted_for_validation` or `in_validation` to `in_use`, is allowed only with an exception
  record whose three fields are present, with an exception record (SR 11-7 page 9; SR 26-2 Section V; SS1/23 Principle 5.3, where exceptions are
  "temporary"); a refused transition names both states.

## Module `riskvalidation/governance/findings.py`

The B.7 findings workflow (06 l.614-628) over the product's findings (W15-2, W15-5): the severity map, the status map, the deadline, ageing, overdue,
the seven-state transitions, the anchor and the register counts.

### `riskvalidation.governance.findings.Finding`

```python
@dataclass(frozen=True)
class Finding:
    case_id: str
    variant_id: str
    id: str
    severity: str                   # "S1" to "S4"
    product_status: str             # "open", "accepted" or "closed"
    evidence: tuple[str, ...]
    raised: date
    tier: int
    status: str                     # one of the seven B.7 states
    rwea_share: float | None        # from rwea_share_of_anchor; None where no RWEA level applies
    # key: property, f"{case_id}/{variant_id}/{id}"
```

- Units: identifiers, a severity, dates, a tier.
- Invariants: the key is the triple (the same finding repeats in each variant of a case, A D3 4.2); `status` is the mapped product status unless the
  workflow has moved it; `evidence` is non-empty.

### `riskvalidation.governance.findings.severity_to_ecb`

```python
def severity_to_ecb(severity: str) -> str: ...
```

- Units: a product severity; returns the ECB TRIM equivalent (06 l.616-617).
- Golden: `severity_to_ecb("S1") = "F4"`; `severity_to_ecb("S2") = "F3"`; `severity_to_ecb("S3") = "F2"`; `severity_to_ecb("S4") = "F1"`.
- Invariants: the product direction stays S1 critical to S4 minor (W15-2); `ValueError` for another string.

### `riskvalidation.governance.findings.map_product_status`

```python
def map_product_status(status: str) -> str: ...
```

- Units: a product status; returns a B.7 state (W15-5).
- Golden: `map_product_status("open") = "open"`; `map_product_status("accepted") = "risk_accepted"`; `map_product_status("closed") = "validated_closed"`.
- Invariants: `overdue` is never returned here: it is computed from the due date and the as-of date by `is_overdue`; `ValueError` for another string.

### `riskvalidation.governance.findings.deadline_days`

```python
def deadline_days(severity: str, tier: int, table: Mapping[str, Sequence[int]] = DEADLINE_DAYS) -> int: ...
```

- Units: a severity, a tier 1 to 4 and the deadline table (a convention); returns days from the raised date.
- Golden, the default table:
- `deadline_days('S1', 1) = 30`
- `deadline_days('S1', 2) = 45`
- `deadline_days('S1', 3) = 60`
- `deadline_days('S1', 4) = 90`
- `deadline_days('S2', 1) = 60`
- `deadline_days('S2', 2) = 90`
- `deadline_days('S2', 3) = 120`
- `deadline_days('S2', 4) = 180`
- `deadline_days('S3', 1) = 90`
- `deadline_days('S3', 2) = 120`
- `deadline_days('S3', 3) = 180`
- `deadline_days('S3', 4) = 270`
- `deadline_days('S4', 1) = 180`
- `deadline_days('S4', 2) = 270`
- `deadline_days('S4', 3) = 365`
- `deadline_days('S4', 4) = 365`
- Invariants: non-decreasing in the tier number and in the severity number (a lower tier or a more severe finding is never given more days with the
  default table); `ValueError` for an unknown severity, a tier outside 1 to 4 or a row that does not hold four values.

### `riskvalidation.governance.findings.due_date`

```python
def due_date(raised: date, days: int) -> date: ...
```

- Units: a date and a number of calendar days; returns the due date.
- Golden: `due_date(2026-10-12, 30) = 2026-11-11`; `due_date(2026-10-16, 60) = 2026-12-15`.
- Invariants: `due_date(r, d) - r` is exactly `d` days; `ValueError` for a negative number of days.

### `riskvalidation.governance.findings.ageing_days`

```python
def ageing_days(raised: date, as_of: date) -> int: ...
```

- Units: two dates; returns the whole days from the raised date to the as-of date.
- Golden: `ageing_days(2026-10-12, 2026-12-31) = 80`; `ageing_days(2026-10-16, 2026-10-16) = 0`.
- Invariants: never negative; `ValueError` when the as-of date is before the raised date.

### `riskvalidation.governance.findings.is_overdue`

```python
def is_overdue(status: str, due: date, as_of: date) -> bool: ...
```

- Units: a B.7 state, the due date and the as-of date.
- Golden: `is_overdue('open', 2026-11-11, 2026-11-11) = False` (on the due date); `is_overdue('open', 2026-11-11, 2026-11-12) = True`;
  `is_overdue('in_progress', 2026-11-11, 2026-12-31) = True`; `is_overdue('risk_accepted', 2026-11-11, 2027-06-01) = False`;
  `is_overdue('validated_closed', 2026-11-11, 2027-06-01) = False`.
- Invariants: true only for the states `open`, `action_plan_agreed`, `in_progress`, `submitted_for_closure` and `overdue`, and only when the as-of date is
  after the due date; a risk-accepted or closed finding is never overdue.

### `riskvalidation.governance.findings.transition_finding`

```python
def transition_finding(state: str, to: str, risk_acceptance: Mapping[str, object] | None = None) -> str: ...
```

- Units: two B.7 states and, for `risk_accepted`, the acceptance record (an `approver` field and an `expiry` field; the register writes `"not-applicable"` and
  `None` with a reason each for a stated limit of a synthetic case, W15-5).
- The B.7 transition graph is a convention (06 l.624-628 names the seven states and no transition; the graph below is this contract's proposal, item 30), as the B.4 graph is.
- Golden: 16 allowed pairs and 33 refused pairs of the 49 ordered pairs of the seven states (the 7 self pairs and 26 others are refused); a refused pair raises
  `ValueError("cannot move from 'validated_closed' to 'open'")`. The allowed pairs:
- allowed: open to action_plan_agreed
- allowed: open to risk_accepted
- allowed: open to overdue
- allowed: action_plan_agreed to in_progress
- allowed: action_plan_agreed to risk_accepted
- allowed: action_plan_agreed to overdue
- allowed: in_progress to submitted_for_closure
- allowed: in_progress to risk_accepted
- allowed: in_progress to overdue
- allowed: submitted_for_closure to validated_closed
- allowed: submitted_for_closure to in_progress
- allowed: submitted_for_closure to overdue
- allowed: overdue to in_progress
- allowed: overdue to submitted_for_closure
- allowed: overdue to risk_accepted
- allowed: risk_accepted to open
- Refused, by example: refused: validated_closed to open; refused: open to open; refused: open to in_progress; refused: open to validated_closed;
  refused: action_plan_agreed to validated_closed; refused: risk_accepted to validated_closed; refused: validated_closed to overdue. Every other ordered pair
  of the seven states is refused.
- Invariants: `validated_closed` is terminal (a reopened finding is a new finding); `risk_accepted` leaves only to `open`, when its expiry or its basis lapses;
  entering `risk_accepted` without an acceptance record that has an `approver` field and an `expiry` field raises `ValueError`; `overdue` is reached from any
  open state when the as-of date passes the due date and leaves to `in_progress`, `submitted_for_closure` or `risk_accepted`.

### `riskvalidation.governance.findings.anchor_from_test_row`

```python
def anchor_from_test_row(evidence: Sequence[str], tests: Sequence[Mapping[str, object]]) -> tuple[dict | None, str | None]: ...
```

- Units: the finding's evidence strings and the test rows of its variant; returns (anchor, reason): exactly one is `None`. An anchor is `{"metric": "statistic"
  or "metric", "test_id", "model_id", "segment", "value", "unit", "basis"}`, the first non-null of the cited row's statistic and metric.
- Golden: evidence `["pd.hosmer_lemeshow@P1-scorecard"]` over a row of that test and model with statistic 12.5 gives an anchor with metric `statistic`, value 12.5 and
  unit `test statistic (dimensionless)`; evidence `["design:b1-minimum-normal-individual"]` or `["rate:rating.migration_ztests@r2-n500"]` gives `(None, reason)`; a cited
  row whose statistic and metric are both null gives `(None, reason)`.
- Invariants: only evidence of the form `test_id@model_id` or `test_id@model_id@segment` is cited, the first one in the list; the basis is the pointer to the row
  and field read; the unit of a metric is the unit its test defines (the report states it), never guessed.

### `riskvalidation.governance.findings.rwea_share_of_anchor`

```python
def rwea_share_of_anchor(anchor: Mapping[str, object] | None, rwea_total: float | None = None) -> tuple[float | None, str | None]: ...
```

- Units: an anchor (as `anchor_from_test_row` returns it) and, optionally, the RWEA total in the anchor's currency; returns (share, reason): exactly one is `None`. The share is a decimal (0.05 is 5 percent).
- Rule (W15-11): non-null only where the anchor's unit states a share of RWEA (`share-of-rwea`: the share is the anchor's value) or an RWEA amount (`rwea-amount`: the value over `rwea_total`, which must be given and positive).
  A statistic or a metric in any other unit, or no anchor, gives `(None, reason)`; the basis is the anchor's own basis. The register row carries the share and its reason; the report's open findings carry
  the register's share, and the cross check compares them.
- Golden: `rwea_share_of_anchor({'unit': 'share-of-rwea', 'value': 0.08}) = (0.08, None)`; `rwea_share_of_anchor({'unit': 'rwea-amount', 'value': 750000.0}, 7492853.0) = (0.1001, None)` (to 4 decimals);
  `rwea_share_of_anchor({'unit': 'test statistic (dimensionless)', 'value': 12.5})` and `rwea_share_of_anchor(None)` are `(None, reason)`.
- Invariants: never a share without an anchor; a share is never negative; `ValueError` for an `rwea-amount` anchor with no total.

### `riskvalidation.governance.findings.register_counts`

```python
def register_counts(rows: Sequence[Mapping[str, object]]) -> dict: ...
```

- Units: register rows; returns `total`, `by_severity` (S1 to S4), `by_status` (the seven states), `overdue` and `by_case`, a list sorted by case id with the same four counts.
- Golden: for the fixture register: total 81, by_severity S1 2, S2 14, S3 41, S4 24, by_status open 49, validated_closed 4, risk_accepted 28 (the other four states 0), overdue 7.
- Invariants: each of `by_severity` and `by_status` sums to `total`; the `by_case` totals sum to `total`.

## Module `riskvalidation/governance/schedule.py`

The B.8 dates (06 l.630-640): the next review, the next full revalidation and the next monitoring date.

### `riskvalidation.governance.schedule.add_months`

```python
def add_months(d: date, n: int) -> date: ...
```

- Units: a date and calendar months.
- Golden: `add_months(2026-08-31, 6) = 2027-02-28`; `add_months(2024-01-31, 1) = 2024-02-29`; `add_months(2026-10-12, 12) = 2027-10-12`; `add_months(2026-10-12, 0) = 2026-10-12`.
- Invariants: the day is clamped to the end of the target month; the year rolls over; `ValueError` for a negative number of months.

### `riskvalidation.governance.schedule.next_dates`

```python
def next_dates(tier: int, last_validation: date, table: Mapping[int, tuple[int, int | None, int | None]] = FREQUENCY,
               profile: str = "default") -> tuple[date, date | None, date | None]: ...
```

- Units: a tier 1 to 4, the date of the last validation, the frequency table (a convention) and a profile; returns the next review, the next full revalidation (`None` where the
  table states none) and the next monitoring date (`None` where none).
- Golden, the default table and profile (tier 4 is an attestation every three years):
- `next_dates(1, 2026-10-12) = (2027-10-12, 2029-10-12, 2027-01-12)`
- `next_dates(2, 2026-10-12) = (2027-10-12, 2029-10-12, 2027-04-12)`
- `next_dates(3, 2026-10-12) = (2028-10-12, None, 2027-10-12)`
- `next_dates(4, 2026-10-12) = (2029-10-12, None, None)`
- Invariants: with `profile="ecb"` the review interval is at most 12 months and the full revalidation at most 36 months (the minimum applies even where the table states none) (06 l.633-636,
  Delegated Regulation 2022/439 Article 11); `next_dates(1, 2026-10-12, profile="ecb")` equals the default for tier 1; `ValueError` for an unknown tier or profile.

## Module `riskvalidation/governance/opinion.py`

The overall opinion on the ECB four-level scale (06 l.620-623) and the recommendation rule (W15-7).

### `riskvalidation.governance.opinion.finding_level`

```python
def finding_level(severity: str, rwea_share: float | None = None) -> int: ...
```

- Units: a severity and, where the finding's anchor is a share of RWEA, that share as a decimal (0.05 is 5 percent); returns the level 2 to 4 that one open finding gives.
- Golden: `finding_level('S1') = 4`; `finding_level('S2') = 3`; `finding_level('S3') = 2`; `finding_level('S4') = 2`; `finding_level('S4', rwea_share=0.0499) = 2`;
  `finding_level('S4', rwea_share=0.05) = 3`; `finding_level('S3', rwea_share=0.0999) = 3`; `finding_level('S3', rwea_share=0.10) = 4`; `finding_level('S1', rwea_share=0.0499) = 4`;
  `finding_level('S2', rwea_share=0.10) = 4`.
- Invariants (W15-11): the maximum of the severity level (S1 4, S2 3, S3 and S4 2) and the RWEA level (3 from 5 percent, 4 from 10 percent, none below 5 percent; ECB Instructions 2019,
  section 2.4.2), so an anchor can only raise a level and a critical finding is never downgraded by a small share; `ValueError` for a negative share or an unknown severity.

### `riskvalidation.governance.opinion.opinion_level`

```python
def opinion_level(open_findings: Sequence[tuple[str, float | None]]) -> int: ...
```

- Units: the open findings as (severity, RWEA share or `None`) pairs; returns the level 1 to 4. The goldens write the severities only.
- Golden: `opinion_level([]) = 1`; `opinion_level([S4, S3]) = 2`; `opinion_level([S3, S2]) = 3`; `opinion_level([S2, S1]) = 4`;
  `opinion_level([(S3, 0.0499), (S4, None)]) = 2`; `opinion_level([(S3, 0.05)]) = 3`; `opinion_level([(S4, 0.10)]) = 4`; `opinion_level([(S1, 0.01)]) = 4`.
- Invariants: the maximum of the findings' levels, and 1 with none; the caller passes only the open findings: a `risk_accepted` or `validated_closed` finding is not one (W15-7),
  an `overdue` finding is; the rule is a convention (item 30).

### `riskvalidation.governance.opinion.recommendation`

```python
def recommendation(level: int) -> tuple[str, str, str]: ...
```

- Units: a level 1 to 4; returns (outcome, text, label).
- Golden: level 1 gives outcome `approve`; level 2 `approve with conditions`; levels 3 and 4 `remediate before use`; the label is always
  `the rule's output on the evidence; Contraste approves no model`.
- Invariants: the text states the rule's output and never an approval; `ValueError` for a level outside 1 to 4.

## Module `riskvalidation/governance/appetite.py`

The model risk appetite metrics (06 B.6 l.606-612), each with its value, unit, numerator, denominator and a light under a stated threshold (a convention).

### `riskvalidation.governance.appetite.light`

```python
def light(value: float | None, direction: str, green_limit: float, amber_limit: float) -> str: ...
```

- Units: a metric value and its threshold; `direction` is `"lower-is-better"` or `"higher-is-better"`; returns `green`, `amber`, `red` or `not_evaluated`.
- Golden: `light(0, 'lower-is-better', 0, 3) = 'green'`; `light(3, 'lower-is-better', 0, 3) = 'amber'`; `light(4, 'lower-is-better', 0, 3) = 'red'`;
  `light(0.9, 'higher-is-better', 0.9, 0.75) = 'green'`; `light(0.8999, 'higher-is-better', 0.9, 0.75) = 'amber'`; `light(0.75, 'higher-is-better', 0.9, 0.75) = 'amber'`;
  `light(0.7499, 'higher-is-better', 0.9, 0.75) = 'red'`; `light(None, 'lower-is-better', 0, 3) = 'not_evaluated'`.
- Invariants: the limits are inclusive on the good side; `ValueError` for an unknown direction.

### `riskvalidation.governance.appetite.tier1_validated_on_time`

```python
def tier1_validated_on_time(entries: Sequence[Mapping], as_of: date) -> tuple[float | None, float | None, float | None]: ...
```

- Units: entries with a tier and a next review date; returns (numerator, denominator, value): the Tier 1 entries whose next review is on or after the as-of date, the Tier 1 entries, and
  their share (a decimal).
- Golden: for the fixture entries at 2026-12-31: (2, 2, 1.0).
- Invariants: value `None` (not evaluated, with a reason) when there is no Tier 1 entry.

### `riskvalidation.governance.appetite.open_high_severity`

```python
def open_high_severity(rows: Sequence[Mapping]) -> tuple[float, float, float, int]: ...
```

- Units: register rows; returns (numerator, denominator, value, register rows): the distinct (entry, id) findings with a row in status `open`, `action_plan_agreed`, `in_progress`, `submitted_for_closure` or
  `overdue` and severity S1 or S2; the distinct (entry, id) findings of the register; the count (value equals the numerator); and the number of register rows behind the numerator.
- Golden: for the fixture register: (4, 39, 4, 8).
- Invariants (W15-14): a finding repeated in n variants of an entry counts once (B.6 counts findings, 06 l.609-611); the row count is the secondary number in the same metric object (`register_rows`).

### `riskvalidation.governance.appetite.overdue_remediation`

```python
def overdue_remediation(rows: Sequence[Mapping]) -> tuple[float, float, float, int]: ...
```

- Units: register rows; returns (numerator, denominator, value, register rows): the distinct (entry, id) findings with an overdue row, the distinct findings of the register, the count, and the overdue rows.
- Golden: for the fixture register: (3, 39, 3, 7).
- Invariants: the row count equals the number of rows `is_overdue` flags at the as-of date; a finding counts once per entry.

### `riskvalidation.governance.appetite.entries_under_exception`

```python
def entries_under_exception(entries: Sequence[Mapping]) -> tuple[float, float, float]: ...
```

- Units: entries; returns (numerator, denominator, value): the entries whose lifecycle holds an exception record, the entries, the count.
- Golden: for the fixture entries: (0, 4, 0).
- Invariants: an entry in use before validation without an exception record is a refused lifecycle state, not a count.

### `riskvalidation.governance.appetite.entries_in_breach`

```python
def entries_in_breach(entries: Sequence[Mapping]) -> tuple[float, float, float]: ...
```

- Units: entries with the lights of their test rows; returns (numerator, denominator, value): the entries with at least one red test row, the entries, the count.
- Golden: for the fixture entries: (3, 4, 3) (C01/german 13 red rows, C18/banco-andino 24, C22/generators 8; C07/banco-andino 0).
- Invariants: a red row on any variant of the entry counts the entry once.

### `riskvalidation.governance.appetite.pma_magnitude`

```python
def pma_magnitude(entries: Sequence[Mapping]) -> tuple[float | None, float | None, float | None]: ...
```

- Units: entries with a PMA (attribute A26 present with an `overlays_total` and the `model_output` it adjusts, in one currency); returns (numerator, denominator, value): the sum of
  the overlays, the sum of the model outputs and their ratio (a decimal share of the model output).
- Golden: for the fixture entries only C07/banco-andino holds one: (324129997.0, 97592002519.53, 0.0033213).
- Invariants: value `None` (not evaluated, with a reason) when no entry holds a PMA with an amount; amounts in different currencies raise `ValueError`.

### `riskvalidation.governance.appetite.owner_and_complete_record`

```python
def owner_and_complete_record(entries: Sequence[Mapping]) -> tuple[float, float, float]: ...
```

- Units: entries; returns (numerator, denominator, value): the entries whose owner attribute (A28) is present, derivable or convention and none of whose 40 attributes is `missing`, the entries,
  and their share.
- Golden: for the fixture entries: (0, 4, 0.0) (each entry has missing attributes).
- Invariants: complete means no attribute with status `missing`; `not-applicable` is complete.

### `riskvalidation.governance.appetite.appetite_metrics`

```python
def appetite_metrics(entries: Sequence[Mapping], rows: Sequence[Mapping], as_of: date,
                     thresholds: Mapping[str, tuple[str, float, float]] = APPETITE_THRESHOLDS) -> tuple[dict, ...]: ...
```

- Units: entries, register rows, the as-of date and the appetite thresholds (a convention); returns the seven metric records in the order `tier1-validated-on-time`, `open-high-severity`,
  `overdue-remediation`, `entries-under-exception`, `entries-in-breach`, `pma-magnitude`, `owner-and-complete-record`, each with `value`, `unit`, `numerator`, `denominator`, `register_rows` (a number for the two distinct-finding count metrics, `None` for the others), `threshold` and `light`; the document's `population` holds `entries`, `findings`, `distinct_findings` and `tier1_entries`.
- Golden, the default thresholds (direction, green limit, amber limit): tier1 `('higher-is-better', 0.9, 0.75)`; open-high-severity `('lower-is-better', 0, 3)`; overdue-remediation
  `('lower-is-better', 0, 3)`; entries-under-exception `('lower-is-better', 0, 1)`; entries-in-breach `('lower-is-better', 0, 1)`; pma-magnitude `('lower-is-better', 0.01, 0.03)`;
  owner-and-complete-record `('higher-is-better', 0.9, 0.5)`. For the fixture: lights green, red, amber, green, red, green, red.
- Invariants: a share equals numerator over denominator, a count equals its numerator; a metric with no value has light `not_evaluated` and a reason; every threshold carries the label `convention`.

## Module `riskvalidation/governance/policy.py`

The policy identity of a test row (W15-6): the source of every threshold the report states.

### `riskvalidation.governance.policy.resolve_policy`

```python
def resolve_policy(policy_version: str, test_id: str, alpha_amber: float | None = None,
                   alpha_red: float | None = None) -> tuple[dict | None, str | None]: ...
```

- Units: the row's `policy_version`, its `test_id` and its alphas; returns (identity, reason): exactly one is `None`. An identity is `{"label", "kind", "kind_reason", "direction", "direction_reason",
  "alpha_amber", "alpha_red", "parameters", "version", "source"}` with `source` one of `packaged-policy`, `inline-battery`. The `kind` is `spec(test_id).decision`, `p_value` or `metric` (W15-12; engine
  `core/registry.py`), and `None` with its `kind_reason` where the test is not registered (`spec` raises `KeyError`; at the batch 3 head the ifrs9, stress, aggregation and portfolio tests are not
  registered). The `direction` (`upper_bad` or `lower_bad`) is read from the policy file where one resolves, and is `None` with `direction_reason` "no policy file (BL-085)" for an inline battery string.
- Golden: a packaged label `"riskvalidation-default 2026.10.1"` resolves through `load_policy` and `default_policy`: source `packaged-policy`, version `2026.10.1`, the kind from the packaged
  threshold of the test; an inline string `"contraste-ifrs9-battery-1.0.0; nl_amber=1.0; nl_red=3.0"` is parsed: source `inline-battery`, version `1.0.0`, parameters
  `{"nl_amber": 1.0, "nl_red": 3.0}`, kind `None` (`ifrs9.scenario_sensitivity` is not registered) and direction `None` with "no policy file (BL-085)"; the same string for the registered `pd.jeffreys` has kind `p_value`
  and the same null direction and reason; the string `"x"` is `unresolved`: it returns `(None, reason)` with the reason stated.
- Invariants: a parameter value that is not a number stays a string (`rule=red-on-any`); the family is the part of the test id before the first dot; the report states the source of every threshold; a
  packaged policy file per battery is backlog BL-085, done when the cases are next re-baked (U16).

## Module `riskvalidation/governance/report.py`

The I.3 validation report (06 l.1219-1237) as a structured document: twelve sections, each filled from the inputs it names or absent with its reason.

### `riskvalidation.governance.report.executive_counts`

```python
def executive_counts(rows: Sequence[Mapping[str, object]]) -> dict[str, int]: ...
```

- Units: test rows; returns the counts of the lights `green`, `amber`, `red`, `not_evaluated`, `error`.
- Golden: for the default variant of C18/banco-andino (`baseline`, 17 rows): `{"green": 6, "amber": 2, "red": 6, "not_evaluated": 3, "error": 0}`.
- Invariants: the counts sum to the number of rows; the same counting as `SuiteRun.counts`.

### `riskvalidation.governance.report.build_report`

```python
def build_report(entry: Mapping, inventory: Mapping, register: Sequence[Mapping], variants: Sequence[Mapping], as_of: date) -> dict: ...
```

- Units: the inventory entry, the inventory, the register rows of the entry, the variant documents of the entry (the first is the default) and the as-of date; returns a document that validates
  against `governance-report`.
- Golden: for C18/banco-andino in the fixture: 12 sections in the order of the schema; section 8 absent with its reason; section 11 level 4 (an S1 finding is open), outcome
  `remediate before use`, 29 open findings; section 1 repeats the level; for C07/banco-andino level 3 (an S2 finding is open) and section 8 filled from the PMA overlays.
- Invariants: deterministic (the same inputs give a byte-identical document); a section is `filled` exactly when it names at least one input, otherwise `absent` with a non-empty reason; section 6 lists
  every test row of the default variant with its definition (`catalogue()` and `spec()`) and its policy identity (`resolve_policy`); section 10 lists the entry's register rows; section 11 is `opinion_level`
  and `recommendation` over the entry's open findings with the label; section 12 lists the sha256 of every document read; no section states an approval or a certification (06 I.6).

## Module `riskvalidation/validation/governance.py`

The `gov.` tests: each returns one `TestResult`, with its H0, its reference and its policy rows `gov.` in `policies/default.json` (a convention, none from a regulation).

### `riskvalidation.validation.governance.inventory_completeness`

```python
def inventory_completeness(inventory: Mapping) -> TestResult: ...
```

- test_id = "gov.inventory_completeness"; model_id and segment are `None`.
- H0: every one of the 40 attributes of every entry has a status other than `missing`.
- Reference: dossier 06 B.2 l.539-551; SS1/23 Principle 1.2; OSFI E-23 Appendix 1.
- Units: `metric` is the share of (entry, attribute) pairs whose status is not `missing` (a decimal); `n` the pairs; `n_events` the missing pairs.
- Light: `lower_bad`: amber below 0.9, red below 0.7 (a convention).
- Golden: the fixture inventory: n = 160, n_events = 46, metric = 0.7125, light `amber`.
- Invariants: `statistic` and `p_value` are `None`; an inventory with no entry returns `not_evaluated` with its reason.

### `riskvalidation.validation.governance.findings_overdue`

```python
def findings_overdue(register: Sequence[Mapping], as_of: date) -> TestResult: ...
```

- test_id = "gov.findings_overdue"; model_id and segment are `None`.
- H0: no open finding is past its due date.
- Reference: dossier 06 B.7 l.614-628.
- Units: `metric` is the share of open-state rows that are overdue; `n` the open-state rows; `n_events` the overdue rows.
- Light: `upper_bad`: amber above 0, red above 0.25 (a convention).
- Golden: the fixture register at 2026-12-31: n = 49, n_events = 7, metric = 0.1429, light `amber`.
- Invariants: no open-state row returns `not_evaluated`; the overdue count equals `is_overdue` over the rows.

### `riskvalidation.validation.governance.validation_due`

```python
def validation_due(inventory: Mapping, as_of: date) -> TestResult: ...
```

- test_id = "gov.validation_due"; model_id and segment are `None`.
- H0: no entry is past its next review date.
- Reference: dossier 06 B.8 l.630-640.
- Units: `metric` is the number of entries whose next review date is before the as-of date; `n` the entries.
- Light: `upper_bad`: amber at 1, red at 2 or more (a convention).
- Golden: the fixture inventory at 2026-12-31: n = 4, metric = 0, light `green`.
- Invariants: `n_events` equals the metric.

### `riskvalidation.validation.governance.tier_override_documented`

```python
def tier_override_documented(inventory: Mapping) -> TestResult: ...
```

- test_id = "gov.tier_override_documented"; model_id and segment are `None`.
- H0: every tier override has a rationale and an approver.
- Reference: dossier 06 B.3 l.574-575; SS1/23 Principle 1.3(d)(e).
- Units: `metric` is the number of overrides without a rationale or an approver; `n` the overrides.
- Light: `upper_bad`: red at 1 or more (a convention).
- Golden: the fixture inventory (no override): n = 0, metric = 0, light `green`.
- Invariants: with no override the row is `green` with `n` 0, not `not_evaluated`.

### `riskvalidation.validation.governance.edges_acyclic`

```python
def edges_acyclic(inventory: Mapping) -> TestResult: ...
```

- test_id = "gov.edges_acyclic"; model_id and segment are `None`.
- H0: the dependency graph has no cycle and every edge joins two entries.
- Reference: dossier 06 I.2; SR 11-7 on model dependencies.
- Units: `metric` is the number of entries on a cycle plus the number of edges to an unknown entry; `n` the edges.
- Light: `upper_bad`: red at 1 or more (a convention).
- Golden: the fixture inventory: n = 2, metric = 0, light `green`; a cycle among three entries gives metric = 3, light `red`.
- Invariants: the cycle is named in `notes` the way `build_inventory` names it.
