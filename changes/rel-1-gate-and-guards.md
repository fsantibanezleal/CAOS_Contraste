- Shell: `@fasl-work/caos-app-shell` moves from 0.23.0 to 0.23.1, pinned exactly (it closes shell known defect 55: the gate's document
  traversal grants each scrollport its own sample budget). The pin test in `frontend/src/workbench/workbench.test.tsx` follows. The full
  product gate on the built site reports 3889 measured states and zero failures, the C04 Benchmark tab included.
- Docs: the manuscript-depth fixture README no longer links to a `templates/manuscripts` folder this product does not carry
  (`scripts/check_doc_paths.py` passes).
