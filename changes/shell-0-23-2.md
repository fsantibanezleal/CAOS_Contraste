- Shell: `@fasl-work/caos-app-shell` moves from 0.23.1 to 0.23.2, pinned exactly (it closes shell known defect 57: a story panel taller
  than the layout no longer shrinks the step row). The story's product rule that kept the header and the stepper from shrinking is
  deleted, so `scripts/check_web_baseline.py` passes with no restyled shell class.
