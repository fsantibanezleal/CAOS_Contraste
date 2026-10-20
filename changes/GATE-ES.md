- Release gate, Spanish rendering (GATE-ES): the C21 rows of the Experiments table keep the regulation citation (`29 CFR 1607.4`) marked `translate="no"` through
  the `Marked` helper (`frontend/src/pages/Batch3Sections.tsx`); C03 shows the validation engine's English-only notes in Spanish with the correlation written with a
  comma (`engineNote`, `frontend/src/workbench/c03/U6Shared.tsx`); C18 marks the annex row references of its mitigation reason and of the Annex 3 labels (`Marked`
  now also keeps `row N.N` / `fila N.N` and the row arithmetic of a label `(4.4+4.5)`, `(1.1 - 5)`) and writes the interpolation rule's call and formula as code.
  English rendering and every number are unchanged.
- C18 producer Spanish (needs the re-bake of the C18 documents and manifest): the mitigation reason, the base and stress correlation bases, the market scaling
  statement and bases, and the findings now write their decimals with a comma (`params.es`), and the Spanish short title of the Fed 2026 scenario chip is
  "Fed 2026 severo" so the chip fits the rail in the wide font (ADR-0071). Tests: `tests/c18/test_c18_spanish_text.py`, `frontend/src/workbench/c21/marked-es.test.tsx`.
