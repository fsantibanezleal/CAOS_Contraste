- Contracts as code: one JSON Schema 2020-12 file per document kind under docs/contracts/schemas/ (common, c01, c04,
  c05, c22) with the enumerations and the ranges the design states, and a catalog docs/contracts/catalog.md with one
  row per boundary (contract 1 and contract 2 of ADR-0057 are rows, not a second system).
- Producer tests (tests/contracts) validate every committed document of data/derived and the three registries against
  exactly one schema chosen by discovery (no file or case list) and refuse a removed key and an unknown key; the
  consumer test frontend/src/lib/contract.test.ts does the same.
- TypeScript types are generated from the schemas (frontend/src/lib/contract.gen.ts through
  docs/contracts/api.openapi.json); contract.types.ts exports them as aliases and keeps the run-time descriptors tied to
  them with satisfies, so a schema change the descriptors miss fails tsc.
- New commands: npm run gen:contracts and npm run check:contracts (fails naming the stale generated file); vendored
  scripts/check_contracts.py and scripts/check_skeleton.py from the template at v0.04.000.
