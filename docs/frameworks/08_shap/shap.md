# Framework card, `shap`

## What and why

Shapley-value attributions, f(x) = phi_0 + sum_j phi_j(x) (Lundberg and Lee 2017), with the exact polynomial-time
algorithm for trees, TreeSHAP (Lundberg et al. 2020, DOI 10.1038/s42256-019-0138-9). A credit decision taken on a
machine-learning score still owes the applicant its principal reasons: Regulation B asks for the specific reasons and
its commentary says more than four are not likely to help (12 CFR 1002.9, comment 9(b)(2)-1; dossier 04 J.1). For a
scorecard the reasons are the point shortfalls; for a tree ensemble they are the largest risk-raising Shapley
contributions.

## Install (exact, verified)

`shap==0.52.0` in `data-pipeline/requirements.txt`. Verified 2026-10-05.

## Usage

```python
import shap

phi = shap.TreeExplainer(booster).shap_values(M)   # booster: a LightGBM model; M: its input matrix
top4 = (-phi).argsort(axis=1)[:, :4]               # the four inputs that raise the risk most, per record
```

## Applying it here

`data-pipeline/pipeline/model/gbm.py` computes, for the LightGBM challenger, the four reason codes of 200 holdout
records on the log-odds scale, and their stability: the mean overlap of the top four between the model and ten models
refitted on bootstrap resamples of the training slice. Both go into the models artifact and the Model group.

## Caveats and licence

MIT. Correlated inputs share credit arbitrarily, which is why the stability is measured and shown rather than
assumed (dossier 04 J.2). The attributions are path-dependent TreeSHAP values (no background sample), not
shortfalls against the Regulation B reference population (all applicants, or those at or just above the cut-off);
that is why an applicant's reasons in the App come from the scorecard's points, and the GBM's reason codes are
reported as a stability measure.
