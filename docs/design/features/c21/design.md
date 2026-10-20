# Design: U14-P3, case C21 (fair-lending disparity testing on HMDA decisions, Delaware, 2018 to 2024)

Status: live. Unit sizing `plans/contraste/units/U14-sizing.md` (CAOS_MANAGE), decisions Q1 to Q4, Q13, C1 to C7, V1 to V4, G9 to G13.
Contracts: `c21-outputs`, `c21-models` (`docs/contracts/schemas/c21/`), `engine-fairness-api` 1.2.0
(`docs/contracts/engine/fairness-api.md`), `contract-family-scored_sample` (bumped, `outcome: none` with `decision`).

## Question

Do approval disparities by protected class exist in public HMDA decisions, do they persist after the permitted controls, and is the
finding stable from one year to the next? The scope is one state, Delaware, and the six year pairs 2018-19 to 2023-24, each fitted on
year t and confirmed on t + 1. The case measures statistical disparity in public decisions about people and scores nobody: every
document carries the label "no legal claim", the sentences of decision C4 and `is_a_finding_of_violation: false`.

## What is real and what is a convention

The rows are the CFPB / FFIEC Data Browser CSV of each activity year (the registry source `hmda`, mirror-allowed). The data licence
sentence is UNVERIFIED (decision C7): the documents quote the platform software terms and the CFPB statement that the public data are
modified. Everything else that shapes a number and is not in a source is a named convention, labelled so in the documents:

- the decision: approval is action taken 1 and 2, denial is 3, codes 4 to 8 are left out and counted by code (decision C3);
- the identity: `id = <activity_year>-<row>` (the 1-based position of the data row in the file) and the observation date
  `<activity_year>-12-31` (decision V3);
- the Joint, Not Available and Free Form Text Only categories (and the age code 8888) are their own excluded groups, never in a
  pairwise test (decision C2);
- the debt-to-income field is recoded to six published bins (`<20%`, `20%-<30%`, `30%-<36%`, `36%-49%`, `50%-60%`, `>60%`; the exact
  whole percents 36 to 49 are one bin);
- the reference group of each attribute: White, Not Hispanic or Latino, Male and, for age, 35-44 (the contract fixture's choice; no
  source names a reference age band);
- the design of the controls, below.

## The estimates (all `riskvalidation`, ADR-0069)

Per attribute and per year pair, on the fit year t: the selection rates (`group_selection_rates`), the parity gap and ratio and the
adverse impact ratio against the reference group, the four-fifths flag against the highest-rate group (`four_fifths_flag`, decided on the
counts in exact arithmetic, decision V1), the pooled z-test and the Fisher exact test of each group against the reference group.
Then per group against the reference group (a pairwise fit on the rows of those two groups):

- the controlled decision estimate: `fit_decision_model` with the protected indicator at index 1 (decision G9) and its 95 percent Wald
  interval (`protected_effect`);
- the rate-spread estimate: `fit_rate_spread_model` on the loans of codes 1 and 2 that carry a rate spread;
- the confirmation: the same two estimates refitted on year t + 1; `replicate_effect` compares the fit with the refit by sign and size.
  The contract holds one confirmation per contrast, the controlled decision estimate; the rate-spread confirmation is the
  `fair.replication` row whose segment ends `|rate_spread`.

Situation testing runs once per pair, on Black or African American applicants against White applicants in the fit year (decision G15: the
attribute with the persistent gap; sex has none): the ceteris paribus comparator only, k = 30, alpha 0.05,
tau 0, the range normalization (decisions V4 and C6), the nominal `loan_type`, `loan_purpose`, `lien_status` and `occupancy_type`
marked categorical and the binned debt-to-income entering as its bin index (decision G10). The counterfactual test is not run: public
HMDA gives no counterfactual dataset. The document holds one situation block, so one attribute is tested.

The controlled estimates are an approximation of comparative evidence. Public HMDA has no credit score (CFPB policy guidance, addendum
H1 2.5), the main underwriting control, so every controlled estimate names it in `missing_controls`.

## The design of the controls (a named convention)

The permitted controls are the nine underwriting fields the contract enumerates (the six of decision Q4 plus the three nominal ones that
the situation test also uses). In the fits they enter as: the debt-to-income bin as indicators (the 36 to 49 bin is the reference), the
natural logarithm of the combined loan-to-value ratio, the income, the loan amount and the property value (a logarithm tames the
unbounded, outlier-heavy values and is the usual form), and the indicators of the loan type, the loan purpose, the lien status and the
occupancy type (the first code is the reference). A row whose control is missing or not positive is left out of the controlled fits;
`data_notes` counts the missing values and, in its reason, the values that are present and not positive; the unconditional rates use every decision row. Two refusals keep a fit honest: a column that is constant in the
pair of groups is dropped (it is collinear with the intercept), and an indicator whose rows all share one decision is dropped (it would
separate the classes completely); a fit that still does not converge, or cannot be made, has `estimate: null` and a reason. Nothing is
imputed.

The situation test uses the same coding of the controls, with the debt-to-income bin index as an ordinal column; under the range
normalization the logarithms keep an outlier from deciding the scale of a column.

## Documents

`C21/pair-2018-19.json` to `pair-2023-24.json` (`c21-outputs`, one per year pair), `C21/models-hmda-de-2018-2023.json` (`c21-models`: the
fields, the fitted pairwise models of the fit years with every term and standard error, the conventions), `C21/SHA256SUMS.txt`,
`C21/raw-sources.txt` (the rows of `data/sources/manifest.json` for the raw files) and `data/derived/manifests/C21.json`. The raw files stay in the
device data root under `raw/hmda/` with a provenance sidecar. Each pair document is validated against its schema and by
`tests/contracts_u14/semantics.py::check_c21` before it is written. A year that is not in the data root stops the pairs that need it,
which are named with the URL; nothing is written for them.

## The engine rows are the engine's (`engine-fairness-api` 1.2.0)

Under engine-fairness-api 1.2.0 the rows of `conditional_disparity`, `rate_spread_disparity` and `situation_testing` carry null alphas, with the
interval level and the share cut points in `extras.thresholds` and in the policy version, so the web gates that read the alphas of a row as
p-value thresholds hold without any change in the product. The bake therefore alters no engine row: `estimates._segment` replaces the
segment and appends "no legal claim" to the notes of a row that lacks it, and nothing else. The engine is pinned at the release tag
`v0.08.001` (since the 0.13.000 integration) that the technology row of the SDD names (`tests/engine_pin.py`).

## The reference groups (a named convention, decision G14)

The reference group of each attribute is the customary comparison group: White, Not Hispanic or Latino and Male. For age no source names
one; 35-44 stays as the reference band. Each document states this in `conventions.group_exclusion`. The alternative, contrasting 62 and over
with under 62 (`applicant_age_above_62`, Regulation B 1002.6(b)(2)), would change every age contrast and is not run.

## The findings (decision G16)

`findings.py` writes the findings of a pair document from its own test rows. A finding groups what several rows show and cites them as
`test_id@model@segment`; a stated limit cites `design:<name>`. Every title carries "no legal claim" and none states a violation.

| Id | Severity | Status | Shows | Cites |
|---|---|---|---|---|
| `F-CONTROLLED-LOWER-ODDS` | S2 | open | the controlled disparity of group contrasts whose 95 percent interval excludes 0 in the fit year, whose sign repeats on t + 1 and whose controlled odds ratio is below 1 (approved at lower controlled odds than the reference group) | the `fair.conditional_disparity` row and its `|controlled` `fair.replication` row, per contrast |
| `F-CONTROLLED-HIGHER-ODDS` | S3 | open | the same, where the odds ratio is above 1 (approved at higher controlled odds) | the same two rows |
| `F-CONTROLLED-NOT-REPEATED` | S3 | open | the controlled disparity whose interval excludes 0 and whose sign does not repeat | the same two rows |
| `F-RATE-SPREAD-HIGHER` | S3 | open | the rate-spread disparity whose interval excludes 0, whose sign repeats and whose coefficient is positive (a higher spread for the group) | the `fair.rate_spread_disparity` row and its `|rate_spread` replication row |
| `F-UNCONDITIONAL-GAP` | S4 | open | the attributes whose parity light is not green, as an indicator only, with the sentence of the Interagency Procedures; and the repeating rate-spread disparities with a lower spread for the group | the `fair.demographic_parity` and `fair.adverse_impact` rows of those attributes, and the rate-spread rows of those contrasts |
| `F-LIMIT-CREDIT-SCORE` | S4 | accepted | the credit score is missing from public HMDA | `design:credit-score-missing` |
| `F-LIMIT-COMPLETE-CASES` | S4 | accepted | the controlled fits use complete cases | `design:complete-case-selection` |

A finding whose rule matches no row is not written, and no finding mixes directions. A rate-spread interval that excludes 0 without repeating is not a finding.

## What the documents do not say

They do not say that any lender discriminated. The unconditional rates are indicators only (the Interagency procedures state that gross
HMDA approval or denial disparities are not appropriate for adverse impact analysis); the controlled disparity omits the credit score
and every non-public underwriting factor; the four-fifths line is an employment benchmark, not a credit-law threshold; Regulation B as
amended effective 2026-07-21 does not apply the effects test under ECOA, and the Fair Housing Act is a separate statute under which
disparate-impact claims are cognizable.
