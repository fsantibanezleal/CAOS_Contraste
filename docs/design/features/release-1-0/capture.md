# Capture: the tool behind the full capture review

Parent: [`../../SDD.md`](../../SDD.md). Decision D16-3 of unit U16 (Contraste 1.00.000): before the release every App view and
every documentation page is captured and read. This page states what the tool captures, how it runs and how a reviewer reads
what it wrote. The tool is `frontend/scripts/capture.mjs`, run as `npm run capture` from `frontend/`. It measures nothing and
judges nothing: the shell gate (`npm run gate`, ADR-0078) measures, and the reviewers read the captures against
`conventions/interactive-visualization-rubric.md` and the committed numbers of each case (U16-R2).

## What is captured

- **A view** is one case, one top group of the workbench and one sub-view (tab) of that group, in one capture. A group with no
  sub-view is one view. Deeper tab lists, where a page has them, add one level to the trail and the leaf is the view.
- **The routes:** every route of the header navigation except the App, which is walked case by case. Each tab of a documentation
  route is a view, at every depth (a list inside a documentation section included); a route with no tab list (Benchmark) is one
  view. Today that is the Introduction, Methodology, Implementation, Experiments and Benchmark routes.
- **The captures** (decision D16-3): light English and dark Spanish at 1280 x 800, and light English at 390 x 844. The theme and
  the language are set through the shell's storage keys before the first frame, and the row records a warning when the document
  came back in another mode.
- **A capture** is the PNG of the viewport after the view settles, scrolled to the top, with finite animations stopped. Settled is
  the shell's idle state that the gate waits for: the shell has rendered, no element declares `data-state="loading"`, no view
  declares `data-stale="1"`, no stage declares `data-drawn="0"`, no finite animation runs, on two reads in a row. The tool reads
  the shell's public DOM only; it imports nothing private from it.
- **Every built case** is walked, each from a fresh page load of `?case=<id>`, so no state leaks from one case to the next. A case
  whose manifest is not in the build (C19, planned, the reason U13 decision E1 records) is listed as not built, with the reason
  the readiness document gives, and is never captured as an empty view.
- **What the tool leaves out:** the controls rail of a case (its tab list is a control, not a view of the case) and the
  Focus-mode overlay. A viewport capture at 390 wide shows the top of a long page; `--full-page true` captures the whole
  scrollable page instead (the same file names, `capture.full_page: true` in the row).

## How to run it

Build first (`npm ci`, `npm run build`), with the Playwright browsers on the device's browsers root (`PLAYWRIGHT_BROWSERS_PATH`)
and, in Git Bash, `MSYS_NO_PATHCONV=1`.

| Command | What it captures |
|---|---|
| `npm run capture -- --out <dir>` | every built case and every route at the three captures (the full review; 337 views and 1,011 PNGs on 0.15.000, about two minutes) |
| `--cases C01,C02` | those cases only, and no documentation route (a reviewer batch) |
| `--routes /methodology,/benchmark` | those routes only (add `/app` to walk the cases as well; `--routes none` for no route) |
| `--captures 1280x800:light:en` | the captures named, `WxH:theme:lang`, comma separated, instead of the three |
| `--variants all` or `--variants id,id` | every variant of each case (or those named), not only the default one (decision D16-20; see below) |
| `--url https://<domain>` | the deployed origin instead of `dist/` |
| `--dist <dir>`, `--base-path /Repo/` | another build, or a project-page base path |
| `--settle-ms 15000`, `--workers 4`, `--full-page true` | the settle time (the gate's default), parallel pages, whole-page captures |

- The output folder is `--out`, required, and never inside the repository: the tool refuses it. The review writes to the device's
  temp root, for example `<temp root>/u16-r-capture-review/<run>`. The tool writes nothing into the repository, `dist/` included.
- It never runs in CI (ADR-0074) and changes nothing in the shell (ADR-0078).
- Exit code 0 when every view was walked, 1 when a walk failed (listed after the summary line), 2 on a wrong option or an
  output folder inside the repository.

## The variant walk (decision D16-20)

The capture review also walks every variant of each case at 1280 x 800 light English, so the views that exist only on some variants
(C18 reverse stress, C20 Fed shift) and the numbers of every variant are read. The three captures of D16-3 stay on the default
variant (no `--variants`). The workbench keeps the variant in React state, not in the URL, so the tool selects it through the
rendered control, as a reader does.

- **A variant walk** is one case and one variant: load `?case=<id>`, click the variant's chip in the rail (`[data-control="variant"]`,
  the chips in the order of the case manifest's `variant` artifacts), wait for the shell's idle state, check the chip is checked,
  then walk every group and sub-view as on the default walk. The default variant is already selected and is not clicked.
- `--variants all` walks every variant of every selected case; `--variants id,id` walks the ids named, where a case has them. An id
  that no selected case offers is a wrong option (exit 2). A case with one variant walks it once. A variant whose view set differs
  is walked as it renders. A variant that does not settle is captured and flagged `settled: false`; a variant document that
  answers 404 is captured and its path is in `not_found`.
- A chip that cannot be clicked, or that is not checked after the click, is a failure of that variant's walk (listed after the
  summary line, exit 1); nothing is captured for it as another variant.
- Without `--variants` the output is the same as before, with the added `variant` field (the default variant's id).

## What it writes

```
<out>/index.json     the index: one row per view and capture, plus one row per planned case (a JSON array)
<out>/index.html     a grid by case and by route: one row per view, one thumbnail per capture, the documents of the view
<out>/run.json       the run: the build (version, commit), the captures, the cases, the counts, the wall time, the failures
<out>/shots/<capture>/<route>/<case>/<group>__<sub-view>.png             default walk (no --variants)
<out>/shots/<capture>/app/<case>/<variant>/<group>__<sub-view>.png     variant walk (--variants)
```

File names are deterministic from the view's identity: `<capture>` is `1280x800-light-en`, `<route>` is the route without its
slash (`app`, `methodology`), `<case>` is absent on a documentation route, and each tab contributes `NN-<data-tab>`, where `NN`
is its position in its list and `data-tab` is the id the shell gives the tab (`tab` when it has none). The names do not depend on
the language, so the three captures of one view share their name in three folders.

## The index format (produced contract)

`index.json` is an array. A captured row has these fields:

| Field | Meaning |
|---|---|
| `id` | `<capture>`, `<route>`, `<case or ->`, `v:<variant>` (variant walk only) and the tab keys, joined by a vertical bar; unique |
| `route`, `case`, `case_title` | the route, the case id (null off the App) and the case's English title |
| `variant` | the variant id; on the default walk the case's default variant (`default_variant` of its manifest); null off the App |
| `group` | `{id, label, key}` of the top group: the tab id, its text in the capture's language, its file-name part; null on a route with no tab list |
| `sub_view` | the same for the sub-view; null when the group has none |
| `deeper` | the same for any further level, a list |
| `capture` | `{id, size, width, height, theme, lang, full_page}` |
| `built`, `captured` | true for a captured row |
| `file` | the PNG, relative to the output folder |
| `settled`, `unsettled_reason`, `settle_ms` | whether the view reached the idle state within the settle time, why not, and how long it took |
| `documents` | the committed documents (`data/...`) the page requested while this view settled, in request order |
| `not_found` | the paths that answered an error while this view settled, with the status (`path (404)`); the view is captured anyway |
| `case_documents`, `case_not_found` | the same, accumulated over the case's page from its load up to and including this view |
| `console_errors` | console errors and page errors raised while this view settled |
| `warnings` | the route did not answer 200, the workbench shows another case than the one asked for, or the document came back in another theme or language than asked |

A planned case is one row with `built: false`, `captured: false`, `file: null` and `reason`, and no capture. The number of
views is the number of distinct `id` values without their capture part; the number of PNGs is the number of captured rows.

## How a reviewer reads it

1. Open `index.html`, take the case, and read its views in the three captures side by side; or read `index.json` for the batch.
2. A row with `settled: false` was captured before the idle state: read it, and say so in the finding when the picture is
   incomplete. A row with a `not_found` path is a view whose document is missing from the build: a finding by itself.
3. `documents` names what the view shows from the committed artifacts. The review's rule R4 (U16 sizing) applies: read the
   numbers on the picture against those documents; a view that is right by the gate and wrong by its numbers is a blocker.
4. `case_documents` is the full set the case loaded, including the readiness, the case index and the manifest. A document
   already loaded by an earlier view of the same case is in `case_documents` only.
5. A reviewer batch is `--cases` of its own cases at the three captures into a folder of its own, so batches never overwrite each other.

## Measured (0.15.000)

The full run on the 0.15.000 build, at the three captures, four workers: 21 built cases (242 views), five routes (95 views),
337 views, 1,011 PNGs, 1 case not built (C19), 0 not settled, 0 with a 404, 106 seconds. The test
(`frontend/src/lib/capture.test.ts`) runs the tool on C01 and C02 at one capture and on the edge cases (a planned case, an
unknown case, an output folder inside the repository, a view that does not settle, a document that answers 404).
