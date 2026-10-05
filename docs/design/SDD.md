# Software design document: the template's example product

This is the SDD of the example the template ships (ADR-0075): an SIR epidemic model, replayed and re-run live.
It exists so the structure, the contracts, the lanes and the gates are exercised by something real on the first
day. A product writes its own SDD here, after its research and its plan and before it instantiates, and the
guard `scripts/check_sdd.py` holds every requirement to a gate that exists.

## Problem and non-goals

Problem: show, end to end, how a CAOS product turns cases into committed artifacts, replays them, re-runs them
live, and proves each step: a pipeline that bakes and checks cases, a web workbench that reads and recomputes
them, documentation transcribed from sources, and gates that fail when any of it breaks.

Non-goals, each something a reader could reasonably assume:

- Epidemiology. The SIR model is a placeholder with textbook assumptions (closed, homogeneous, deterministic);
  it is not a forecasting tool and carries no real data.
- A choice of integrator. Forward Euler at a quarter-day step is enough to show parity and convergence; a
  product picks its scheme from its own error budget.
- A backend. `app/` is a dormant read-only API; the example is a static site.
- A learned model of record. The surrogate exists to show where a trained model sits in the pipeline and how its
  held-out error is reported.

## Contracts

- Ingestion (contract 1, `data-pipeline/pipeline/io/contract.py`): each case's parameters are validated before a
  run. A missing, non-numeric, NaN or out-of-range value is rejected with its reason, never coerced; an unusual
  value (R0 above 20) is accepted and flagged into the manifest.
- Artifacts (contract 2): `data/derived/manifests/index.json` (`example.index/v2`: cases with bilingual titles
  and categories, the default case), one manifest per case (`example.manifest/v3`: parameters, seed, engine and
  version, artifact, lane verdict, metrics, expected ranges, bilingual expected band) and one trace per case
  (`example.trace/v1`: 200 points, two decimals, summary). The web declares the same shapes in
  `frontend/src/lib/contract.types.ts`, and `frontend/src/lib/contract.test.ts` reads every committed artifact
  against them in both directions.

## Lanes

- Offline: `data-pipeline/run.py` bakes every case (about a millisecond each) and checks it against its expected
  ranges; it runs on a workstation, never in CI and never in the browser.
- Replay: the committed artifacts, copied into the site by `frontend/scripts/copy-data.mjs` (exactly the declared
  files) and fetched with the version in the address.
- Live: `frontend/src/engine/sir.ts`, a step-for-step port of the Python engine. The basis for putting it in the
  browser is measured, not assumed: the lane gate (`data-pipeline/pipeline/core/gate.py`) gives each case a run
  budget of 1500 ms and a trace budget of 256 KiB, and the Benchmark page measures the live engine against that
  budget in the reader's browser (a median of 0.02 to 0.08 ms per case under Node 24 on the development workstation, 2026-10-04).

## Method ladder

One method, the example engine, with one acceptance criterion: the live engine reproduces every baked trace to
the trace rounding (0.005 people), and both converge to the final-size relation at first order in the step.
Gates: `frontend/src/engine/sir.parity.test.ts`. A product's ladder (classical, state of the art, learned,
frontier) gets one criterion per method here, each with its gate, per ADR-0069.

## Cases

Five cases in two categories. Outbreak regimes: sub-critical (R0 0.72, no outbreak), epidemic (R0 2.75), fast burn
(R0 6), slow spread (R0 1.2, still running when the horizon ends). Controls: no initial infection (R0 2, nothing
happens). Each exists to test a different part of the engine and the views: the threshold, a full epidemic, a
sharp early peak, a horizon that cuts the run, and the degenerate start. Every case states numeric expected
ranges, enforced by `data-pipeline/pipeline/core/expect.py`. Variants: immunisation of 0%, 30% and 60% at the
start, computed live.

## Oracles

- The final-size relation z = 1 - exp(-R0 z) (Kermack and McKendrick 1927; Miller 2012), independent of the time
  course: a run that ends inside its horizon must reach it, to first order in the step.
- The threshold R0 = 1 and the herd threshold 1 - 1/R0 (Diekmann, Heesterbeek and Metz 1990): a sub-critical case
  must not grow, and an immunisation above the threshold must prevent the outbreak.
- Parity: the Python engine is the reference for the live engine, to the trace rounding.
None of these is a model judging a model.

## Deploy driver

GitHub Pages: a static site with every artifact committed, no secret and no server. The measurement behind it is
the lane gate above (every case is live-eligible) and the site size (1.8 MB of assets, most of it KaTeX
fonts, and 34 KB of artifacts, measured on the 2026-10-04 build). The target is written in `deploy/TARGET` and checked by `scripts/check_deploy_place.py`.

## Risks and kill criteria

- Risk: an instantiated product keeps pieces of the example. Kill: `scripts/check_template_residue.py` fails.
- Risk: the two engines drift. Kill: the parity test fails.
- Risk: a test rewrites the committed artifacts. Kill: the session guard in `tests/conftest.py` fails the run.
- Risk: the site looks right and is not (a blank drawing, a dead control, a broken deep link). Kill: the measured
  gate (`npm run gate`) fails before a deploy.

## ADR fit

How the example meets the ADRs it is bound by, and where the base carries the rule (ADR-0078):

| ADR | Rule | Carried by |
|---|---|---|
| ADR-0057 | two contracts, named stages, lanes | `data-pipeline/`, `frontend/src/lib/contract.types.ts` |
| ADR-0058 | architecture modal, five themed bilingual tabs | `frontend/src/architecture/`, validated by the shell on mount |
| ADR-0069 | method vertical with its acceptance criterion | this SDD, the parity and convergence tests |
| ADR-0071 | the page is the viewport; one tab row; drawing at least half the viewport | the shell's `CaseWorkbench`; the gate (G5, G6) |
| ADR-0074 | CI runs cheap checks only | `.github/workflows/ci.yml`, `scripts/check_ci_budget.py` |
| ADR-0075 | every requirement names its gate | `docs/design/features/`, `scripts/check_sdd.py` |
| ADR-0078 | rules live in the base | shell 0.7 and this template; no product re-implements them |
