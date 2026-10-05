"""The model rungs of each family (scorecard, penalised LR, EBM, monotone GBM, ...): thin, pinned wrappers over the
real engines named in docs/frameworks/, each returning the model record that contract 2 writes. The validation
tests and the regulatory calculators come from the engine package `riskvalidation`, never from here."""
