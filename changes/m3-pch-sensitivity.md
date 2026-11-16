- C06: the hyper-parameter sensitivity of the PC-Hazard rung (S-4), reported beside the pre-registered verdict. At every reporting date the
  rung is refitted under nine settings, one hyper-parameter moved at a time around the defaults and never a grid: the interval width 1.5, 3
  and 6 months with the interval count 120, 60 and 30 (every grid covers the same 180 months), the hidden layers (16, 16), (32, 32) and
  (64, 64), the weight decay 1e-5, 1e-4 and 1e-3 and the learning rate 0.003, 0.01 and 0.03. Each refit trains on the same loans, hold-out
  split and seed as the main fit and is judged by `s4_evaluation` on the same out-of-time accounts: the integrated Brier score, the mean
  absolute decile gap, the c-index and both criteria per setting and date; a fit that fails or runs to the epoch cap is recorded with its
  status and reason, never dropped. Each setting gets the verdict `s4_verdict` gives its dates; the verdict of the case stays the default's
  and the documents count the settings whose verdict agrees with it. No setting is chosen. Contracts `c06-models` 3.0.0
  (`fit.pch_sensitivity`, a newly required object, so major by the ADR-0080 floor) and `api` 38.0.0; `fit_pch` takes the settings as keyword
  arguments (defaults unchanged); requirements CT-521 to CT-523; the PC-Hazard view and the case page print the nine settings and the count
  in English and Spanish.
