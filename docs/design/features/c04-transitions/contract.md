# C04 artifact contract (the outputs block of each variant, and the live parity)

Design: [`design.md`](design.md). This file fixes the shape of `outputs` for each kind of C04 variant, the module
that computes it, and the parity block the live ports are held to. Every number is computed by `riskvalidation`
0.4.0 (`transitions`, `validation.transitions`, `generators.paths`, `harness`, `regulatory`); a module never
re-implements an engine formula. All arrays are plain lists (JSON); probabilities are fractions, not percentages.

## Conventions

- `GRADES = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC-C"]`, `STATES = GRADES + ["D"]` (default last, absorbing).
- A CEREP cohort is `pipeline.io.cerep.Cohort`: `counts` 7 x 8 (performing grades at the beginning by grades and
  default at the end), `withdrawn` 7, `defaulted` 7 or None (tab 2), `events` 7 or None (tab 3), `size` 7 (the cohort,
  withdrawals included), `has_default_column` (False on Moody's).
- The engine's square input is 8 x 8: `np.vstack([cohort.counts, np.zeros(8)])` (the default row empty; the engine
  makes it absorbing).
- A cohort's label is `"2010"` (annual) or `"2010H1"` / `"2010H2"` (semester).
- Test results are `TestResult.to_dict()` and go in the artifact's `tests` list, each with `model_id` set (the agency
  code or the family) and `segment` set (the cohort label, the rung, or `"pooled"`).
- Every rate from repeated simulation carries `n`, `rate` and its Monte Carlo SE `se` (`harness.Rate.to_dict()`), and a
  simulation's seed is `_seed(case_seed, key)` exactly as C22 derives it (`numpy.random.SeedSequence([case_seed,
  crc32(key)])`).

## 1. Agency variants (`kind: "agency"`), module `pipeline/cases/c04_agency.py`

`agency_outputs(code: str, annual: list[Cohort], semesters: list[Cohort]) -> dict`, the cohorts as
`pipeline.io.cerep.read_agency` returns them (only periods with data):

```text
{
  "kind": "agency",
  "agency": {"code": "STPGB", "name": <AGENCIES[code]>, "scope": "corporate, long-term, categories"},
  "attribution": "Source: ESMA CEREP; tables transformed by Contraste",
  "grades": GRADES, "states": STATES,
  "cohorts":   [{"label", "begin", "end", "size": [7], "counts": [[7 x 8]], "withdrawn": [7],
                 "defaulted": [7] | null, "events": [7] | null,
                 "defaulted_cohort": [7] | null, "tab2_gap": float | null}],   # annual, oldest first; tab 2's own
                                                                               # cohort and its largest gap to tab 4
  "semesters": [same shape],                                             # semester cohorts, oldest first
  "pd": {                                                                # one-year PD by cohort (rows) and grade
    "d2":   [[n x 7]] | null,   # tab 2: distinct defaulted ratings / tab 2's cohort (Cohort.defaulted_cohort)
    "d3":   [[n x 7]] | null,   # tab 3: default events / cohort size
    "d4":   [[n x 7]] | null,   # tab 4: default column / (size - withdrawn); null on Moody's
    "keep": [[n x 7]] | null    # tab 4: default column / size (withdrawals kept in the denominator); null on Moody's
  },                                                                     # a grade with size 0 is null in its row
  "lra": {"d2" | "d3" | "d4": {                                          # long-run average (EBA/GL/2017/16 para 84)
    "rate": [7],               # the mean of the yearly rates over the cohorts where the grade has ratings
    "cohorts": [7],            # how many cohorts entered each grade's mean
    "defaults": [7], "n": [7], # pooled counts (n: d2 tab 2's cohorts, d3 the sizes, d4 size - withdrawn)
    "pooled_rate": [7],        # defaults / n
    "wald": {"lower": [7], "upper": [7]}, "agresti_coull": {...}, "jeffreys": {...},   # 95%, on the pooled counts
    "last5": [7]               # the mean of the last five cohorts' rates (para 86's comparison)
  }},
  "pooled": {"matrix": [[8 x 8]],          # Anderson-Goodman (2.8), withdrawals removed (industry treatment)
             "matrix_state": [[9 x 9]],    # the same, withdrawals kept as an absorbing ninth state
             "counts": [[7 x 8]], "withdrawn": [7], "row_sizes": [7], "cohorts": n},
  "embedding": {"S", "series_converges", "det", "prod_diagonal",
                "theorem3": {"a": bool, "b": bool, "c": [[i, j], ...]}, "exact_generator_excluded": bool,
                "stochastically_monotone": bool, "monotonicity_violations": [...]},
  "generators": {"diagonal" | "weighted" | "jlt" | "em": {
                   "generator": [[8 x 8]], "valid": bool, "l1": float,          # L1 of exp(Q) to the pooled matrix
                   "pd_1y": [7], "pd_5y": [7]},                                 # default column of exp(tQ)
                 "em": {..., "iterations": int, "converged": bool, "loglik": float},   # EM on the annual counts, dt 1
                 "cohort_power": {"pd_5y": [7]}},                               # the pooled matrix to the fifth power
  "mobility": {"labels": [n], "svd": [n], "trace": [n],                         # per annual cohort, its own matrix
               "spec_default_rate": [n]},                                       # d2 (else d3) of BB, B, CCC-C pooled
  "ecb": [{"label", "mwb_upper", "mwb_lower", "ztests_p": float | null}],      # per annual cohort, on the 7 x 7
                                                                               # block of performing grades (rating.mwb,
                                                                               # rating.migration_ztests)
  "homogeneity": {"annual": {"statistic", "p_value", "dof", "periods"},        # rating.time_homogeneity
                  "semesters": {...} | null,
                  "reference": [{"label", "statistic", "p_value", "dof", "impossible_moves"}]},  # each cohort vs pooled
  "semesters_vs_year": [{"year", "l1", "pd_product": [7], "pd_annual": [7]}],  # P_H1 P_H2 against P_year
  "definition_gap": {"d4_over_d2": [7] | null, "d3_over_d2": [7] | null},      # pooled ratios (null where undefined)
  "lifetime": [{"label": "2010-2014", "first": 2010, "last": 2014, "size": [7],  # CT-415, one row per window with data
                "observed": {"default_end": [7], "withdrawn_end": [7],       # tab 4 over the window's fixed cohort
                             "cumulative_d2": [7] | null},                   # tab 2: rated defaulters / tab 2's cohort
                "projected": {"chain_state": [7], "chain_state_withdrawn": [7],   # the window's annual matrices, the
                              "chain_exclude": [7],                          # withdrawals a state or removed
                              "pooled_power": [7], "em": [7] | null}}]       # pooled matrix ^ years; exp(years Q_EM)
}
```

## 2. Generator families (`kind: "generator"`), module `pipeline/cases/c04_families.py`

`family_outputs(family: str, q: np.ndarray, obligors: list[int], case_seed: int, reps: int) -> dict` with `q` the
8 x 8 generator (EM on S&P's pooled annual counts, computed by the case) and `obligors` the cohort size by grade.
Families and ladders (fixed in the module, printed in the outputs):

| family | ladder | per rung |
|---|---|---|
| `markov` | none | estimators (cohort pooled over five years, duration, EM, diagonal, weighted, JLT): bias, RMSE, zero share of the one-year PD by grade, with MC SEs; the size of the four transition tests at 5% and 1% (harness `simulate`); coverage of Wald, Agresti-Coull, Jeffreys (on the pooled cohort counts) and of the duration PD's resampling bootstrap (B 500, the first 100 repetitions) |
| `momentum` | alpha 0, 0.25, 0.5, 1, 2 (beta 1, investment grades 4) | rejection rates of time homogeneity, order and momentum; per grade: the one-year cohort PD (mean), the five-year default frequency of the initial cohort (the momentum chain's truth), the Markov projections from one-year data (pooled cohort matrix to the fifth power; exp(5 Q) of the duration generator) and their errors |
| `cycle` | downgrade rates times 1, 1.25, 1.5, 2, 3 during the third year (regimes at 2 and 3) | rejection rates of time homogeneity and of the reference test of the stressed year's counts against the pooled matrix; per grade: the stressed year's cohort PD, the five-year average, the truth exp(Q) |
| `withdrawals` | withdrawal rate 6% a year, informative 0, 1, 3, 9 (window one year) | per grade: the pooled one-year PD with withdrawals removed (CEREP tab 4), kept in the denominator unfollowed, and followed (EBA paragraph 76: the latent path, the same seed without withdrawal), against the truth |
| `thin` | obligors per grade 50, 100, 200, 500, 1,000 | exact by enumeration (no simulation): coverage of Wald, Agresti-Coull and Jeffreys by grade at the true one-year PD; the probability that adjacent grades' Jeffreys intervals overlap |

Shape: `{"kind": "generator", "family", "generator": {"q": [[8 x 8]], "pd_1y": [7], "pd_5y": [7], "obligors": [7],
"source": str}, "design": {"years": 5, "snapshots": [...], "reps": int, "seed_key": str}, "ladder": {"name",
"unit", "values": [...]} | null, "rungs": [ {per rung, the quantities above, each array by grade} ], "simulations":
[C22-style rows {"key", "test_id", "rung", "rates": {"p<0.05": Rate, "p<0.01": Rate}, "seed", "n_rep"}]}`. The
`simulations` rows make the findings' `rate:` evidence (`rate:<key>`).

## 3. Published answers (`kind: "published"`), module `pipeline/cases/c04_published.py`

`published_outputs(data_root: Path) -> dict` from the three PDFs in `<data root>/raw/<source id>/`, read by
`pipeline.io.papers` (`read_irw_2001`, `read_engelmann_2024`, `read_sr190_table5`, each checking what it read
against the print and refusing otherwise). No agency matrix enters the outputs (derived-only):

```text
{"kind": "published",
 "irw": {"rows": [{"matrix": "S&P 1981-1991" | "Moody's 1980-1998" | "S&P 1999", "method": "jlt" | "diagonal" |
                   "weighted", "printed": float, "recomputed": float, "agrees": bool}],   # 9 rows, six digits
         "jlt_from_printed_generator": float,      # the first matrix's distance from the printed Q_JLT (0.116900)
         "theorem3_c": [bool, bool, bool], "series_terms": int},
 "sr190": {"defaults": 15, "n": 531, "rows": [{"rho", "interval": "wald" | "agresti_coull", "printed": [lo, hi, len],
                                               "recomputed": [lo, hi, len], "agrees": bool}], "n_dagger": [3]},
 "engelmann": {"w_ttc": {"printed": [8], "recomputed": [8]}, "ttc_pd": {"printed", "recomputed"},
               "portfolios": [{"name", "w0": [8], "pd0": {"printed", "recomputed"},
                               "extreme": {"kind": "min" | "max", "printed", "recomputed"} | null,
                               "pd_path": [50]}],             # the projected PD by year (a result, not the matrix)
               "row_sum_deviation": float}}
```

## 4. Live parity, module `pipeline/cases/c04_parity.py`, ports `frontend/src/engine/transitions.ts`

`parity(agency_matrices: dict[str, np.ndarray], origination: list[float]) -> dict` for the models artifact
`data/derived/C04/models-transitions.json` (`fit.parity`), which `frontend/src/engine/transitions.test.ts` reads
(the path overridable by the environment variable `C04_PARITY` for development):

```text
{"projection": [{"agency", "matrix": [[8 x 8]], "origination": [8], "w0": [8], "years": 20,
                 "default_rate": [20], "portfolio_last": [8], "ttc": [8], "ttc_default_rate": float}],
 "intervals": [{"defaults", "n", "rho", "level", "wald": [lo, hi], "agresti_coull": [lo, hi], "jeffreys": [lo, hi],
                "n_effective": float}],
 "capital": [{"pd", "lgd", "maturity", "regime", "asset_class", "risk_weight"}]}
```

The TypeScript ports: `project(T, w0, origination, years)` and `ttcPortfolio(T, origination)` (Engelmann (9) at unit
balance, power iteration to 1e-14), `pdWald`, `pdAgrestiCoull`, `effectiveN` (Schuermann and Hanson (2.2), (3.3),
(3.4)), `pdJeffreys` (the Beta quantile by bisection on `betaCdf` from `sizepower.ts`), and the IRB risk weight from
`credit.ts` (`irbCapital`); each equal to the parity points within 1e-9 relative (1e-12 absolute below that).
