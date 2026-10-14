- C10, portfolio credit capital (U7-P): the real producer of `c10-outputs`, `c10-outputs-grid` and `c10-models` 1.0.0. The Vasicek distribution is fitted
  to the Federal Reserve net charge-off rates of five loan types on 1985-2006 and the 2007-2012 tail is placed in it; an illustrative portfolio per loan
  type gets its loss distribution by the six rungs of the ladder (LHP, Gaussian copula, Student-t copula, CreditRisk+, granularity adjustment,
  importance sampling) with Euler contributions; a known-correlation simulator gives the size and power of the correlation estimates. Every number
  comes from `riskvalidation.portfolio` (pinned in `data-pipeline/requirements.txt` by commit 502652b of `task/u7-portfolio` until the release is tagged).
  Case page `docs/cases/C10.md`, requirements CT-1101 to CT-1112, tests `tests/c10/`, documents `data/derived/C10/`.
