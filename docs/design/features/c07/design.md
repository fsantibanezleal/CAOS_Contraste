# Design: U5-P2, case C07, the Chile provisions trilogy

Requirements: [`requirements.md`](requirements.md). Parent: [`../../SDD.md`](../../SDD.md) sections 4 and 5. The case page, with
the executive brief, the calibration sources and the result read from the committed documents, is
[`../../../cases/C07.md`](../../../cases/C07.md); the contracts are `docs/contracts/schemas/c07/` and the engine contract is
`docs/contracts/engine/provisions-api.md`.

## The question

Chilean banks do not book IFRS 9 expected credit losses on loans: CNCB Chapter A-2 N 5 leaves loans and contingent credits to
Chapters B-1 to B-3. The case puts the statutory provision (CMF B-1), the IFRS 9 one and the Spanish alternative solution (BdE
Circular 4/2017 Annex 9) on one synthetic loan book, so that their gap is a number and not a debate.

## Method

1. **Calibration** (`cases/c07/sources.py`, `generator.py`): the CMF Informe del Desempeno of August 2026 gives the system loan mix,
   the provision index and the 90-day delinquency ratio by portfolio. The generator assigns account states by quota (the 90-day
   ratio is its target), solves one tier share per B-1 portfolio from the engine's own B-1 factors so that the exposure-weighted
   provision index equals the CMF index, and scales exposures by class so that the mix, the ratio and the index match at any size.
2. **Scenarios** (`scenarios.py`, `book.py`): six variants, scenario conditioning only. The accounts are fixed per seed; a variant
   moves the systematic factor, moves each account's own fixed draw into arrears or default (nested: a harsher variant moves a
   superset) and moves real-estate collateral values with the house price index.
3. **Regimes** (`b1.py`, `ifrs9.py`, `bde.py`): B-1 through `riskvalidation.provisions.local_cl`, IFRS 9 through `term_structure`,
   `staging`, `ecl`, `overlays`, `reconciliation` and `validation.ifrs9`, Annex 9 through `local_es`. The product selects the
   function for each account and adds up; it carries no B-1, Annex 9, staging or ECL table or rule (ADR-0069).
4. **Documents** (`documents.py`, `bake.py`): `c07-models` once, `c07-outputs` per variant, the checksums file and the manifest.
   Money is CLP rounded to the centavo, so every identity of the contract holds on the written values.

## Decisions of the unit (each also stated on the case page)

- IFRS 9 is the probability-weighted ECL over the weighting scenarios of dossier 02 B.4 (factors +1, 0, -2; weights 25, 50, 25 per
  cent) shifted by the variant's factor; staging is frozen at the weighted conditions.
- The gap bridge from B-1 to IFRS 9 telescopes through engine allowances: measurement basis (the part the two methods do not
  share, closed to the centavo and checked against the engine ladder), Stage 2 lifetime, probability weighting, discounting, the
  B-1 minimum top-up and the overlays. The B-1 additional provisions are outside both totals.
- One reporting date has no opening balance: the 35H and 35I tables are roll-forwards from the base variant.
- The calibration sources are committed in `sources.py` with their file hashes; the fetched files stay in the device data root.
  The manifest lists no source id (`sources: []`): there is no third-party input file, and the provenance check requires the
  manifest sources to equal the artifacts' inputs.

## Limits

Synthetic; no compliance claim; the IFRS 9 side uses the case's own PD, LGD, EIR and recovery parameters (labelled assumptions);
the Annex 9 collateral haircut table is not transcribed in the engine, so the case applies a stated 20 per cent haircut; the
lifetime PD backtest, the stage migration backtest and the SICR threshold stability are not run (one reporting date); the CMF
Bancos API key is absent, so the targets come from the CMF public web publication.
