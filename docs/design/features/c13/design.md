# Design: U8-P2, case C13 (FRTB desk eligibility: PLA and desk back-testing)

Status: live. Requirements: [`requirements.md`](requirements.md), CT-1301 to CT-1313.

## 1. What the case answers

Do the P&L attribution (PLA) test and the desk back-test of FRTB (MAR32.18 to MAR32.19, MAR32.36 to MAR32.42) detect a risk model
with a known, planted deficiency? The data are generated, so the truth is known: the case is `synthetic-known-truth`. Six variants
of one generator: no deficiency (the size of the test) and five planted deficiencies (the power). Every PLA statistic (Spearman,
Kolmogorov-Smirnov), every zone and every desk exception count is returned by `riskvalidation.market` and
`riskvalidation.validation.market` (engine contract `engine-market-api` 1.0.0); the product computes none (ADR-0069).

## 2. The generator

A two-factor spread desk (long factor 1, short factor 2). One replication simulates 550 days of which the last 250 are the
window; it is a pure function of its seed (`numpy.random.default_rng(seed)`, draws in a fixed order whatever the deficiency).

- Day scale `sigma_t = exp(mu + g_(t-1))`, a log-AR(1) (persistence 0.98, stationary log sd 0.35, `E sigma^2 = 1`) known at the
  start of the day, so the risk model's VaR is an ex-ante forecast.
- Factors `x_t = w_t L(rho)'` for orthonormal drivers `w` and the Cholesky factor of the true correlation (0.6).
- HPL = `sigma_t (l . x_t)` plus pricing noise (10 percent of the factor P&L sd); RTPL = the risk model's revaluation of the same
  moves; desk VaR at tail level alpha = `z(1 - alpha) * sd_model_t`, the model's conditional sd of the factor P&L.
- Seeds: variant k of the bake with case seed s uses `1000 s + 1000 k + index`, `index` in 0 to 999 (13000 to 18999 for s = 13):
  one seed per replication, disjoint ranges per variant, so the 6,000 replications are independent.

| Variant | What is planted (only in the risk model or the dating of its P&L) | Parameter | Meant to break |
|---|---|---|---|
| none | nothing: RTPL is exact up to the pricing noise | | none (size) |
| missing-basis | HPL carries an instrument basis the model leaves out | basis sd 0.65 of the HPL sd | Spearman |
| stale-volatility | the model scales the day's shocks with the volatility of 20 days earlier | 20 days | KS |
| wrong-correlation | the model maps the drivers to the factors with a correlation 0.3 above the true one | +0.3 points | either |
| omitted-factor | HPL is exposed to a third factor the model leaves out | 0.6 of the HPL sd | Spearman |
| time-misalignment | RTPL is dated one day off | 1 day | Spearman |

The generator's closed form (CT-1301) is the population Pearson correlation of HPL and RTPL from the parameters
(`generator.known_pearson`): the quantity the planted terms are sized in. The tests check the simulation against it on 100,000
pairs for every variant.

The strengths are the illustrative parameters of the reviewed contract fixture, except the omitted-factor share (0.6, so the
omitted factor is material at the PLA thresholds) and the factor setting (a hedged desk with a true correlation of 0.6, so a
correlation error moves its VaR). They are fixed before the bake and never tuned to a catch rate: the documents report the
rates they produce, whether or not the deficiency is caught. A deficiency the PLA does not catch is a finding, not a defect of
the bake.

## 3. The bake

Per variant: 1,000 replications. Per replication the engine computes Spearman (`frtb.pla_spearman`), KS (`frtb.pla_ks`), the
joint zone (`frtb.pla_zone`), the single-statistic zones (`pla_zone` with the other statistic held at its best value, so no
threshold is written in the product) and the exceptions of the HPL loss against the model's VaR at 97.5 and 99 percent
(`frtb.desk_exceptions`, limits from `frtb.desk_exception_limit`). The bake counts and summarises the engine's numbers. The
example replication (the one with the median Spearman) goes through `validation.market.pla_test`; each aggregate desk row is the
engine row of `validation.market.desk_backtest` for the replication with the median exception count, labelled as such. A catch
is a joint PLA zone of amber or red; the interval of the catch rate is the Wilson interval at 95 percent.

Documents: `data/derived/C13/models-generator.json`, one document per variant (`none.json`, `missing-basis.json`,
`stale-volatility.json`, `wrong-correlation.json`, `omitted-factor.json`, `time-misalignment.json`), `SHA256SUMS.txt`, and the
manifest `data/derived/manifests/C13.json`. The page `docs/cases/C13.md` carries a results table generated from them.

## 4. Limits

The desk is one stylised book, the volatility is one common stochastic scale and the risk model knows the true scale except where
a deficiency says otherwise: the catch rates are those of this generator, not of any desk. Replications are independent windows,
so the rates carry Monte Carlo error, reported as a standard error and an interval. The PLA and the desk back-test are defined on
250 days, so the windows are exactly that.

## 5. ADR fit

| ADR | Fit |
|---|---|
| ADR-0080 contract-first | the producer of `c13-models` and `c13-outputs`; the consumer of `engine-market-api` and `test-result` |
| ADR-0069 no re-implementation | no PLA, zone or back-test logic in the product |
| ADR-0074 tests in seconds | tests use a small replication count; the full bake runs locally |
| ADR-0075 SDD before development | this folder; `scripts/check_sdd.py` |
| ADR-0067 synthetic labelled | every document and the page carry the synthetic notice |
