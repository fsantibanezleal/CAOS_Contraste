# Guide: calibrate a PD curve, and estimate low-default PDs

Case C05 runs these on published data; this guide is the same work on your own rating system, with riskvalidation
0.2.0 in Python (nothing here needs the web). Grades are always passed best first.

## 1. Your rating system as a model

From one period's counts by grade you get the whole model the calibration needs: the rating profile, the grade
default rates, the unconditional PD, the two conditional profiles and the accuracy ratio.

```python
from riskvalidation.engines import pd_curve as pc

m0 = pc.model_from_counts(obligors_2025, defaults_2025)           # one count per grade, best grade first
print(m0["pd"], m0["accuracy_ratio"])
```

Observed default rates are noisy and often zero in good grades; smooth them first. Quasi moment matching fits a robust
logistic curve whose unconditional PD and accuracy ratio equal the targets you give (here the observed ones):

```python
q0 = pc.qmm(m0["profile"], m0["pd"], m0["accuracy_ratio"], survival_profile=m0["survival_profile"])
curve0, pd0 = q0["pd_curve"], q0["pd"]
```

## 2. Carry it to the next period

What you know at the start of the forecast period picks the approach (Tasche 2013, section 4):

| You know | Approaches | Call |
|---|---|---|
| the new profile and a PD for it (a forecast, a TTC target or a stress PD) | invariant default profile; invariant accuracy ratio; scaled PDs; scaled likelihood ratio | `invariant_default_profile(m0["default_profile"], profile_1, pd_1)`; `invariant_accuracy_ratio(profile_1, pd_1, m0["accuracy_ratio"])`; `scaled_pds(curve0, profile_1, pd_1)`; `scaled_likelihood_ratio(curve0, pd0, profile_1, pd_1)` |
| only the PD | invariant likelihood ratio | `invariant_likelihood_ratio(curve0, pd0, pd_1=pd_1)` |
| only the profile | invariant PD curve; invariant conditional profiles; invariant likelihood ratio | `invariant_pd_curve(curve0, profile_1)`; `invariant_conditional_profiles(dp0, sp0, profile_1, fit="least_squares")`; `invariant_likelihood_ratio(curve0, pd0, profile_1=profile_1)` |

Every result carries the curve, its constants and the equations it used; an approach that cannot give a proper model
raises `pd_curve.ImproperModel` instead of returning one (for example scaled PDs that lift a grade above one). The
evidence of the paper's own example and its backtest favours the scaled likelihood ratio and warns against scaled PDs,
which carry the estimation period's PD into the forecast; C05 shows the same on 2010.

## 3. Test it when the period closes

The paper's test is the chi-square of the implied default profile against the defaults by grade, given their number:
it sees the curve's shape, not its level. The p-value is a Monte Carlo one, because good grades expect a fraction of a
default.

```python
from riskvalidation.validation.calibration import pd_default_profile, pd_jeffreys_grades

r = pd_default_profile(obligors_2026, defaults_2026, forecast["pd_curve"], n_sim=100_000, seed=2013)
print(r.p_value, r.extras["mc_standard_error"], r.light)
for t in pd_jeffreys_grades(obligors_2026, defaults_2026, forecast["pd_curve"]):  # the level, grade by grade
    print(t.segment, t.p_value, t.light)
```

## 4. A portfolio with almost no defaults

Bound each grade's PD by pooling it with every worse grade (Pluto and Tasche 2005), independent or with an asset
correlation, scaled to the portfolio's own bound (their proposal), or over several years:

```python
from riskvalidation.engines import low_default as ldp

b = ldp.most_prudent_pd((100, 400, 300), (0, 2, 1), gamma=0.75)                       # independent
c = ldp.most_prudent_pd((100, 400, 300), (0, 2, 1), gamma=0.75, rho=0.12)             # correlated
s = ldp.most_prudent_pd_scaled((100, 400, 300), (0, 2, 1), 0.75, target="upper_bound") # section 5
y = ldp.most_prudent_pd_multiperiod((100, 400, 300), (0, 2, 1), 0.75, rho=0.12, theta=0.3, years=5)
```

Choose a moderate level: the paper argues that averages of historical default rates, the usual alternative, carry a
comparable probability of underestimating the PD. And read the tests with care. C05's generated years show the
binomial and Jeffreys tests rejecting true PDs too often when defaults are correlated, while the Vasicek binomial,
which keeps its size, rarely catches a model at half the truth. In a low-default portfolio the bound informs a
calibration; it does not prove one.

## 5. What it costs

```python
from riskvalidation.regulatory import capital_requirement

rw = [capital_requirement("corporate", p, 0.45, maturity=2.5, regime="basel3").risk_weight for p in forecast["pd_curve"]]
```

The regime is data (`basel3`, `crr3`, `basel2`, `cl_ran21_6`), with its floors, scaling and references in the result;
C05's Impact group shows that the calibration choice moves capital by double digits.
