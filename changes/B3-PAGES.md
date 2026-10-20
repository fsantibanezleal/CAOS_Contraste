- Experiments and Benchmark, wave 2 batch 3 (B3-PAGES): C02, C12, C16, C18, C20 and C21 each get an Experiments table with one headline row per variant in
  the case's own measures (`frontend/src/pages/Batch3Sections.tsx`): C02 the horizon, records, defaults, the AUC of the champion and of the best rung, the
  calibration light and the transfer change; C12 the EEPE, CVA, SA-CCR EAD, the effect of the initial margin or of the wrong-way factor and the signed ORE gap;
  C16 the survival period (a day, or surviving the horizon), the LCR and the run-off multiplier per base; C18 the CET1 ratio with losses only and with PPNR,
  the simple-sum capital, the dependence band and the reverse distance and tail probability; C20 the headline of each kind of variant; C21 the adverse impact
  ratio, the employment-benchmark flag, the conditional disparity and its replication. A field a document leaves null reads "not available" with its reason.
- Benchmark: C12 against ORE (one row per variant), C18 across the dependence band, C02 and C20 across their rungs; C16 and C21 are excluded with a
  bilingual reason (C21 added to `NO_BENCHMARK`).
- Families: C18 joins the capital family, relabelled "Capital, aggregation and stress"; C20 and C21 form the new "ML and AI risk" family; no group holds more
  than six tabs. The top row, the design group and six families, holds seven (open question in the report, kept as an expected-failure test).
- The C01 scorecard table of Experiments is for C01 only (`sectionKindOf`); any other case without a section gets the generic table of its impact items.
