# Guide: the dormant API

Contraste has no backend. Its deploy place is GitHub Pages (`deploy/TARGET`): the web replays the committed artifacts
and computes the live views in the browser, and no ADR-0002 trigger applies (no server-side processing of uploaded
data, no private data, no paid heavy compute; SDD section 7). A reader's own scored sample is validated on the
reader's machine ([guide 02](02_validate-your-own-model.md)), never uploaded.

The template's `app/` stays in the repository, dormant, so a future trigger has a starting point: a FastAPI app that
serves the committed documents read-only and unchanged, `GET /api/cases` (the index), `GET /api/cases/{id}/manifest`
and `GET /api/artifacts/{path}` (any artifact a manifest names, by its path under `data/derived`), and nothing outside
`data/derived` (`tests/test_dormant_api.py`, which runs without the API lane installed).

Activating it would not be a configuration change: a backend moves the deploy place to the VPS and removes Pages
(one place, never two), so it is a re-plan of the deploy section of the plan, with `requirements-api.txt` pinned and
verified at that time.
