# Requirements: U1, the six-route web companion

Status: live

EARS (Mavin et al., RE'09, doi:10.1109/RE.2009.9). Every requirement names the gate that fails when it is violated.

| ID | Requirement | Gate |
|---|---|---|
| CT-106 | WHILE the App route is open, THE page SHALL fit the viewport and keep navigation on one row, in both themes and both languages. | `frontend/scripts/gate.mjs` (G5, G6) |
| CT-107 | WHEN the measured gate walks every route, tab, sub-tab and case at five sizes, both themes and both languages, THE site SHALL pass every check. | `frontend/scripts/gate.mjs` (G1 to G14) |
| CT-112 | THE App instrument SHALL have one tab row of at most six groups, in the order Model, Validation, Impact, Findings, Variants, Context. | `frontend/src/workbench/workbench.test.tsx::the instrument groups are the six questions, in order` |
| CT-113 | THE web SHALL show the lane (offline, replay or live) on every view of the instrument. | `frontend/src/workbench/workbench.test.tsx::every view carries its lane` |
| CT-114 | THE Context view SHALL show the case's data sources with their licence classes and its truth status. | `frontend/src/workbench/workbench.test.tsx::context names sources, licences and truth status` |
