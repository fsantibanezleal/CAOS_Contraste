- C21 Findings view draws the evidence of each finding (`frontend/src/workbench/c21/FindingsEvidence.tsx`): a second card, "The evidence of each finding", beside
  the findings table. It plots the controlled odds ratio of every `fair.conditional_disparity` row a finding cites (grouped and coloured by finding, the line at 1)
  and the rate-spread coefficient of every `fair.rate_spread_disparity` row (the line at 0), with a table under the charts whose values are the `metric` of the
  document's rows; a cited row the document lacks is listed as not available with its id, and accepted limits that cite only a design limit draw nothing and are
  named. The note is bilingual and says "no legal claim". The three legal sentences move under the evidence so the two cards take the height of the group, and the
  group meets the 50 percent drawing floor of the shell gate at 1280 x 800.
