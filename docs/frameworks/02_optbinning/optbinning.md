# Framework card, `optbinning`

## What and why

Optimal binning as mathematical programming (Navas-Palencia, arXiv 2001.08025): pre-binning, then a binary program
over which consecutive pre-bins merge, maximising the information value under monotonicity, bin-size and bin-count
constraints. It is the reference implementation of the formulation, it supports every trend shape a scorecard needs
(ascending, descending, concave, convex, peak, valley, automatic) and it solves with a MIP, a CP or a local-search
solver. The alternatives (scorecardpy, toad, skorecard) are unmaintained on PyPI or use heuristic binning; dossier 04
section K compares them.

## Install (exact, verified)

`optbinning==1.0.0` in `data-pipeline/requirements.txt` (Python 3.11 or newer; it brings `ortools` and `ropwr`, both
Apache 2.0). Verified 2026-10-05.

## Usage

```python
import numpy as np
from optbinning import OptimalBinning

rng = np.random.default_rng(0)
x = rng.normal(size=5000)
y = (rng.uniform(size=5000) < 1 / (1 + np.exp(1.5 - x))).astype(int)
ob = OptimalBinning(name="x", dtype="numerical", solver="cp", monotonic_trend="ascending",
                    min_bin_size=0.05, max_n_prebins=20).fit(x, y)
print(ob.binning_table.build()[["Bin", "Count", "Event rate", "WoE", "IV"]])
woe = ob.transform(x, metric="woe")
```

## Applying it here

`data-pipeline/pipeline/model/scorecard.py` (P1) bins every characteristic on the training slice with the CP solver,
the declared monotone trend (or `auto_asc_desc` where no direction is declared), each bin at least 5% of the records
and at most 20 pre-bins. The binning table gives the WoE and the information value; a characteristic below IV 0.02 is
dropped. The WoE (sign convention: non-events over events, so a higher WoE is a lower risk) feeds the logistic
regression; the bins, as split points or category sets, go into the models artifact so the live scorer finds the same
row. The single-variable benchmark (P0) and PLTR's categorical inputs (P2b) reuse these binnings.

## Caveats and licence

Apache 2.0. A category unseen at fit time falls in the table's "Missing" row, whose WoE is zero; the live scorer does
the same. The IV rule of thumb (0.02) is attributed to Siddiqi (2017) and is UNVERIFIED against the book text.
