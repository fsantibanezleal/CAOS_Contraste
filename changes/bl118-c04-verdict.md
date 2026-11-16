- C04: BS-14's committed verdict now carries the whole pre-registered refutation rule and says refuted, as the SDD and the published
  manuscript do. `c04_bounds.verdict` compared the anchored interval only with the removed, kept and followed treatments and never read
  the stability clause, so `outputs.bounds_verdict.summary.refuted` was false and the view printed "the hypothesis is not refuted"
  since 1.00.000. The bake now computes both clauses itself, from the engine on the committed generator and the real cohorts, and reads
  no manuscript result file: the coverage clause at informative 9 on 1,000 repetitions (the first-year, pooled and ten-fold designs; the
  anchored interval against the best of the removed, kept, followed and Manski identified-band treatments, +0.0, -0.8 and +0.0 points,
  the band covering as often or more often at 3.8 to 9.3 times the width) and the stability clause (the share of the annual cohorts
  whose k band holds the pooled k against 80%, per source and grade: S&P's B 0.68 and CCC to C 0.64 and Fitch's B 0.70 fail; a grade
  with fewer than five usable cohorts is not judged and never passes). Contract `c04-family` 2.0.0 (two newly required objects and
  `refuted_on` in `summary`, so major by the ADR-0080 floor) and `api` 39.0.0; requirement CT-416; the case page, the finding F-WITHDRAW-BOUNDS
  and the Anchored bounds view state the verdict with each clause in English and Spanish. Every other C04 number is byte-equal.
