# Frameworks

One card per engine the pipeline uses: what it is and why the research chose it, the exact pinned version, a
runnable snippet, where Contraste applies it, and its caveats and licence. Every engine has a card here and an exact
pin in `data-pipeline/requirements.txt` (or the optional `requirements-tabpfn.txt`), and its licence is verified in
`data-pipeline/config/licences.json` (CT-005). The research behind the choices is dossier 04, section K (versions,
licences and maintenance as of 2026-10).

| # | Engine | Role | Licence |
|---|---|---|---|
| 01 | [riskvalidation](frameworks/01_riskvalidation/riskvalidation.md) | every validation test (the engine of the product) | MIT |
| 02 | [optbinning](frameworks/02_optbinning/optbinning.md) | optimal monotone binning, WoE, IV (P1, P0, P2) | Apache-2.0 |
| 03 | [statsmodels](frameworks/03_statsmodels/statsmodels.md) | the scorecard's logistic regression with inference (P1) | BSD-3-Clause |
| 04 | [scikit-learn](frameworks/04_scikit-learn/scikit-learn.md) | the split and folds, L1 and PLTR (P2), isotonic calibration | BSD-3-Clause |
| 05 | [interpret](frameworks/05_interpret/interpret.md) | the explainable boosting machine (P3) | MIT |
| 06 | [lightgbm](frameworks/06_lightgbm/lightgbm.md) | the monotone gradient-boosting challenger (P4) | MIT |
| 07 | [xgboost](frameworks/07_xgboost/xgboost.md) | the engine cross-check of P4 | Apache-2.0 |
| 08 | [shap](frameworks/08_shap/shap.md) | TreeSHAP reason codes and their stability | MIT |
| 09 | [tabpfn](frameworks/09_tabpfn/tabpfn.md) | the tabular foundation model on the small case (P5, optional extra) | Apache-2.0 code; v2 weights under the Prior Labs License v1.1 |

The numerical base (numpy, scipy, pandas, and xlrd to read the Taiwan workbook) is pinned in the same file and
carries no card. A new engine gets its card from [the template](frameworks/00_TEMPLATE.md) in the commit that pins
it.
