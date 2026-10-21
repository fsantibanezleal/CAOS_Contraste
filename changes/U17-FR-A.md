- Notebooks, topics 02 to 07, fix round after the Opus sample review: the Spanish trees print "sí" and "no" where they printed Python's
  `True` and `False`, and the engine's traffic lights and data statuses in Spanish; the Spanish tables follow the English numbers
  (labels with a dot, a variable no longer named like an English label); every notebook re-executed on `riskvalidation` 0.8.1.
- Notebook 11 of topic 03 (claim BS-2): the p-values of the Jeffreys and binomial tests are checked against a quadrature of the Beta
  density and an exact rational sum, not against the SciPy calls the engine makes (the earlier difference of 0 held by construction);
  the Hull-White reconciliation against ORE is no longer called "not run" (topic 08 demonstrates it); the equality of the cohort
  estimator with `transitionMatrix` is reported as an engine test (RV-415) that no notebook reruns; the Schuermann and Hanson gap is
  printed in basis points.
- Notebook 08 of topic 03: the same correction on `transitionMatrix` (the engine's tests do reconcile with it since 0.8.0).
- Notebook 10 of topic 03 (claim BS-4): the standard error of the mean of the 26 yearly rates beside the Jeffreys interval, the
  reading of the bias at k = 0, and the LGD and correlation of the IRB example stated against CRE32.6 and CRE31.7.
- Notebook 07 of topic 03: the LGD note of the IRB assumptions (45% is the financial-institutions value; CRE31.7 multiplier absent).
- Notebook 05 of topic 07: the model confidence set of the two windows that commit their returns is recomputed with `arch` (seed 42)
  and equals the committed p-values; the notebook declares `arch` and `pandas`. Notebook 02 of topic 07, 02 and 06 of topic 02: the
  sentences about packages the notebook environment lacks are corrected against `notebooks/requirements.txt`.
- SDD: the claim BS-2 names the independent recomputations of the p-values and the engine test against `transitionMatrix`.
