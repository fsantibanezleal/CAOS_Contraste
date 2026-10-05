# Design: U1, the six-route web companion

## Routes

The shell's six routes (`STANDARD_ROUTES`): the App, Introduction, Methodology, Implementation, Experiments and
Benchmark, in English and Spanish, light and dark, on `@fasl-work/caos-app-shell`.

## The App

One `CaseWorkbench`. The rail holds the case picker, the variants (chips with the artifacts' short titles, the active
variant's full name under them) and three sections shown one at a time, each with a live read-out (ADR-0017 rule 3):
the decision (the challenger, the approval rate and the LGD; the bad rate of the approved for both models), the policy
(the amber and red thresholds, the light counts and the champion's Jeffreys light; the reset next to the knobs), the
applicant (one of the 50 scored holdout applicants with its live scores; a note where a variant has none). The
instrument holds the six groups in order (CT-112): Model, Validation, Impact, Findings, Variants, Context.

## Layout

Every view fills the panel at 1280x800 and wider (ADR-0071 rule 8): a row of cards (`.caos-views-row`), a table beside
or above the drawing of the same numbers, wrappers (`.ct-col`, `.ct-share-*`) giving each card its share; a long table
scrolls inside its filling card (`.ct-scroll`). Below 900 px the shell stacks the row and the document scrolls; phone
columns that do not fit are hidden (`.ct-wide-only`), and columns that need a wide instrument appear from 1500 px
(`.ct-room-only`). Tall screens (1100 px and more) add a second drawing where a table would leave a card mostly empty
(`.ct-tall-only`: the ladder's calibration of every rung, the expected-loss curve).

## Lanes

Every view carries its lane badge (CT-113): replay for what the pipeline computed, live for what the browser computes
from the committed artifacts (the scorecard and EBM scores, the policy lights, the decision at the reader's approval
rate and LGD).

## The gate

`npm run gate` (the shell's `caos-shell-gate`) serves the build as GitHub Pages does and walks every route, group,
sub-tab, rail section, case and variant at five sizes, both themes and both languages (CT-106, CT-107).
