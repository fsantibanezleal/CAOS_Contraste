# Design: SHOW-1, the guided story and the visualization catalog

Status: live. Binding text: ADR-0082 (showcase-grade visualization), ADR-0071 (sized containers, one navigation row), ADR-0078
(compose the shell's parts), ADR-0070 (a deep link per step). The decided catalog and story are in CAOS_MANAGE
`plans/contraste/showcase-plan.md`; the catalog is the SDD section `## Visualization catalog`.

## Question

What does a validator or an executive see first about a bank's model risk, and can they follow it to a decision? Five steps along the
analytical flow: **inventory** (where the validated models sit and which families carry the most severe findings), **back-test**
(is the VaR model in the green, amber or red zone of the Basel light), **crisis** (how the losses and the VaR forecasts moved),
**recalibrate** (how the proposed adaptive conformal recalibration corrects the VaR day by day) and **decide** (which VaR model the
bank keeps). Each headline is a finding with its number read from the artifacts, at most 12 words.

## Composition

- The route `/story/:step` and `immersiveRoutes: ['/story']` in `frontend/src/App.tsx`; the page `frontend/src/pages/Story.tsx` composes
  the shell's `StoryFrame` (stepper, play and pause, keyboard, deep links, exit), `SceneCallouts` (three anchored callouts per stage,
  header placement) and `useLinkedView` (one selection for the scene and the panel, one shared day cursor). Nothing of those is
  hand-rolled (ADR-0078). The App is not changed; the Introduction links to the story (`Introduction.tsx`, the section how to read the
  App), and the story's exit returns to `from` (`/app?case=C11` by default).
- The views are SVGs the product owns (`frontend/src/story/`), sized from their measured box and drawn from the documents: `FlowView`
  (V1), the family panel (V2), `TrafficLightView` (V3), `CrisisView` (V4), `RecalibrationView` (V5), `DecisionView` (V6). Every
  number comes from `model.ts`, the one module that reads the documents; the views and the panels draw what it returns.
- The artifacts are read through the product's loaders: `loadGovernance` (`workbench/governance/model.ts`) for the inventory and the
  register and `loadCase('C11', window)` (`api/artifacts.ts`) for a window. A document that does not load is the declared unavailable
  state of the step, with the reason; the other steps work. The story adds no artifact and no fetch path.

## What is real and what is a convention

- Real, read: the 34 inventory entries and the 732 findings; per window the VaR and ES paths, the exceedance days, the traffic light, the
  gates, the confidence set, the champion, the expected-shortfall back-tests and the conformal block. The Basel zone cuts are the table of
  the models document (`fit.traffic_light`, MAR32.9 Table 1; BCBS 1996).
- A stated convention of Contraste, labelled on the views: the placing of a case in the flow (its exposure, family and output, read from the
  exposure and regulatory-use basis of its inventory entry); the element of SR 11-7 (conceptual soundness, ongoing monitoring, outcomes
  analysis) a finding's first test evidences, by the test's namespace; the Wilson interval, a function of the exception count and the days.
- Computed in the page from the documents: the exceptions in the trailing 250 days, a tally of the exceedance days the document lists
  (the tests compare its maximum, final count and days per zone with the document's own for every model and window).
- The realised loss series is committed only where the data licence class allows (rates 2022 and FX 2008). In the equity windows it is
  withheld, and the story does not add it: the contract keeps its licence (decision of the producer, dossier 08 C.5); the exceedance days
  the document lists are marked on the VaR and the view says why. The C11 contract and the bake are unchanged.
- V2 has no physical component to open (a bank's models have no asset), so it is replaced by the selected family opened by the three
  elements of SR 11-7 (ADR-0082 rule 1). The flow has a thirteenth family, the validation of the tests (case C22, no bank balance), that sets
  nothing, so no entry is dropped.

## Motion, performance and the phone

Step changes use the shell's eased and staged transition (`StoryFrame`); reduced motion makes it instant or a fade under 150 ms, and the
day player of the recalibration is then off (the day is moved by hand). The day player advances a few days every 90 ms and stops on any input.
At 390 px the panel sits below the stage and the callouts are the three of each step; every drawing re-lays itself out from its measured width.
The measured gate numbers (stage share, LCP, frame rate, latency) are in the unit report.

## Missing data

An artifact that does not load is the unavailable state with its reason. A window of fewer than 250 days has no Basel light (not
evaluated, with the document's reason). A window without a champion says why in the document's words. A window without exceptions is
drawn in the green zone at zero. A number the documents do not hold is shown as not available, never typed.
