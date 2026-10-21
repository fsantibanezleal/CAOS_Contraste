- Contract c18-models 2.1.0 (minor, additive): the aggregation block of the C18 models document gains the optional `quantile_grid`, the
  quantile function of each of the four marginals on a named probability grid (1,961 points, p = Phi(z) for z from -4.9 to 4.9 in steps of
  0.005, in CLP millions), so the marginals the band was run on can be rebuilt from the repository alone (review MA5 of the U17 sample).
  The schema generator, the fixture generator, the catalog and History rows, the c18-models entry of `versions.lock.json`, the generated
  `docs/contracts/api.openapi.json` and `frontend/src/lib/contract.gen.ts` and the contract test `tests/c18/test_c18_quantile_grid.py`
  follow; the integrator bumps the api catalog row (additive, minor) and runs `scripts/check_contract_versions.py --update`.
- C18 re-baked with `python data-pipeline/run.py C18`: the six variant documents are unchanged field by field; only the models document
  gains `fit.aggregation.quantile_grid`, and its bytes, its checksum line and the manifest's size fields follow.
- Notebooks of topic 12, in English and Spanish: notebooks 02, 03 and 08 rebuild the marginals from the committed quantile grids instead of
  fitting stand-ins (decision N3 holds), and reproduce the committed copula rows, the lower bound, the worst case and the
  Glasserman-Xu worst case; notebook 09 shows that the five documents carry one and the same aggregation block, so BS-9 rests on two
  distinct aggregates and not six (review MA4); the `\nu` of two result lists that a newline had replaced is restored; the lower bound is
  described as the best possible VaR of the sum (m11); the Joint Forum wording cites the BIS press release and no longer says UNVERIFIED
  (m8).
- Spanish tree of topic 12: Python's True and False print as sí and no; the engine's English messages and the EBA paragraphs print in
  Spanish through a table in the notebook that fails if the engine changes its text (review m10 and the English-in-Spanish pattern).
- SDD, the BS-9 claim block: two distinct aggregates, the marginals' quantile grids, the BIS press release.
