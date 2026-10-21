- Notebook environment: `notebooks/requirements.txt` pins `arch==8.0.0`, `pandas==3.0.6`, `mapie==1.5.0` and `fairlearn==0.15.0` (the engine's own
  test references) and `scikit-learn==1.9.1` (the interface both need); the SDD technology table gains the rows for `arch`, `mapie` and `fairlearn`.
- Notebook 07 of topic 07 (state of the art, dynamic semiparametric ES), in English and Spanish: step 3 fits the GARCH-t on the committed
  realised returns of `fx-2008` with the engine and with a direct `arch` call (identical to the printed digits, stable to the optimiser's start),
  and states that `rates-2022` commits 249 returns, one below the engine's minimum, and that the committed GARCH-t forecasts cannot be reproduced.
- Notebook 08 of topic 13 (state of the art, outcome-testing toolkits), in English and Spanish: the split-conformal quantile is compared with the
  MAPIE 1.5.0 package run (227 of 38,567 answered pairs differ, each by the naive float rule's score, one order statistic above), which corrects the
  earlier attribution of the NumPy `higher` call to MAPIE; the selection rates, parity difference and parity ratio are compared with fairlearn
  0.15.0 on the committed HMDA counts (difference at most 5.6e-17).
