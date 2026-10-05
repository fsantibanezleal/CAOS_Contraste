# Tasks: U1, the six-route web companion

| # | Task | Requirement | State |
|---|---|---|---|
| 1 | The App workbench: the rail with its three sections and live read-outs, the six groups in order | CT-112 | done |
| 2 | The views of every group, each with its lane and provenance | CT-113, CT-114 | done |
| 3 | The five documentation routes and the architecture modal, from the dossiers, with verified citations | - | done |
| 4 | The layout that fills the panel at 1280x800 and fits at 390 and 768 | CT-106 | done |
| 5 | The measured gate over the whole matrix | CT-107 | done |

## Convergence verdict (2026-10-05)

Converged on the build: `caos-shell-gate: OK, 655 measured states` (five sizes, both themes, both languages; every
route, group, sub-tab, rail section and variant). The first run failed 583 states and found 13 base defects, fixed
upstream first: template 0.02.003 and shell 0.7.1 (tag v0.07.001). The verdict holds on shell 0.7.1; until 0.7.1 is on
npm, `package.json` stays on ^0.7.0, where p-values print in fixed notation and multi-series charts have no key.

2026-10-05 (night): 0.7.1 and then 0.7.2 are on npm. Contraste 0.02.000 depends on ^0.7.2, so the build that ships is
the build the gate measured; the C05 chart key that bridged known shell defect 17 was removed with it. On 0.7.0 the
same tree had failed 88 of 686 states, every C01 and documentation failure among them one of the defects 0.7.1
carries. The screenshots on 0.7.1 then showed what no gate check read: every integer axis repeated its tick labels
(C01's AUC across the variants read 1, 2, 2, 3, 3, ...), known shell defect 21, fixed upstream in 0.7.2 together with
the gate check that now fails it (G6).
