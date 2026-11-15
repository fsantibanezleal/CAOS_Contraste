- C17: each variant's finding F-5 says its hypothesis verdict holds at that tail index only ("at this tail index") and states the verdict of the S-3
  hypothesis over all 16 cells (4 tail indices x 4 cells) with the pooled counts, so a reader of one variant no longer reads a verdict the hypothesis
  does not have (it is inconclusive: both robust rungs have the smaller spread in 16 of 16 cells and the smaller bias in 8 and 9). The bake computes
  every variant's cells before it writes any variant document and records the overall counts and verdict once in the models document
  (`fit.s3_overall`, `c17-models` 1.2.0, optional so every 1.1.0 document stays valid; `api` 35.1.0).
