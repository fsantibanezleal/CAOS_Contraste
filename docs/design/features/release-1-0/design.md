# Design: the generated convergence verdict of release 1.0 (unit U16-V)

ADR-0075 section 4 says convergence is an explicit check against the SDD: it enumerates each requirement, names its gate and records the
result of the gate. Before this unit only 5 of the 26 feature folders of this product and 5 of the 21 of the engine carried a verdict, each
a dated paragraph written by hand. Release 1.0 states the verdict for every requirement of both repositories, so it is generated (decision
D16-2) and never written by hand: the document [`verdict.md`](verdict.md) is the output of `scripts/convergence_verdict.py` on the result
files of the release run.

## Inputs

| input | where it comes from | what the verdict reads |
|---|---|---|
| requirement rows of the product | `docs/design/features/*/requirements.md` | the rows `\| ID \| statement \| gate \|`, parsed by `requirement_rows` of `scripts/check_sdd.py` (imported, never copied) |
| requirement rows of the engine | the same path in the engine repository (`--engine-repo`, read only) | the same rows, the same parser |
| `--product-junit` | `python -m pytest tests --junitxml=FILE` in this repository | one case per test, by test file, name and parameter |
| `--engine-junit` | `python -m pytest tests --junitxml=FILE` in the engine repository | the same, for the engine rows only |
| `--vitest` | `npx vitest run --reporter=json --outputFile=FILE` in `frontend/` | one assertion per test, by test file and title |
| gate scripts | the scripts a gate names (`scripts/check_skeleton.py`, `scripts/check_readiness.py`, the guards) | the exit code; the script runs in its own repository with a timeout (`--script-timeout`, 600 s) |

A gate cell names its tests in backticks, as `scripts/check_sdd.py` requires: `path::test_name` for a Python or a TypeScript test, a plain
test file (every case of the file), or a plain script. `scripts/check_skeleton.py` needs the catalog as an argument, which a backticked path
cannot carry, so the script keeps a small table (`SCRIPT_ARGS`) and a test holds it to scripts that exist.

## Results

| result | meaning |
|---|---|
| `passed` | every test the gate names ran and passed (a parametrized test passes only if every parameter passed; a gate that names several tests passes only if all pass), or the script exited 0 |
| `failed` | a named test failed or errored, or the script exited nonzero or timed out |
| `skipped` | a named test was skipped; the reason the run gave is listed. A skip never counts as passed |
| `absent` | the gate is in no result file, or the script does not exist. A name that is only the prefix of a test that ran is absent |

A gate that names several parts takes the worst of them (failed, then absent, then skipped, then passed). The engine's rows are looked up
in the engine's file and the product's in the product's, never the other way round.

## The verdict

`CONVERGED` needs: every row passed; no feature folder without requirement rows; and no skip, except a skip whose reason is a device
precondition (`requires_raw`, the data root, `CONTRASTE_DATA`) when the release run states the device with `--device`. Anything else is
`NOT CONVERGED`. A folder whose `requirements.md` says `Status: superseded` is not a feature of the release and is left out; a `planned`
folder is read like a live one, so its gates read absent until they exist.

Exit codes: 0 converged, 1 not converged, 2 a result file or a repository is missing. With exit 2 the script prints the file and the
command that writes it, and writes no verdict (an earlier `verdict.md` is left as it was).

## The format of `verdict.md`

1. Line 1: `# Convergence verdict: Contraste release 1.0`, followed by `(SAMPLE RUN)` when the run used `--sample`.
2. A line `Verdict: **CONVERGED**` or `Verdict: **NOT CONVERGED**`, the run date (the latest date in the result files, never the clock), the
   device the run stated, and the number of rows.
3. A table of counts by result, and a table of counts by repository.
4. The section `Features with no requirement rows`.
5. The section `Requirement IDs used by more than one feature`: an ID two features of one repository both use is named, and both rows stay in the table.
6. The section `Requirements`: the table `| repository | feature | id | gate | result | detail |`, sorted by repository, feature and id, one row for
   every requirement row of both repositories. The detail is the number of cases for a pass, the reason for a skip, and the failure or the
   script's exit code and first line of output otherwise.

The document is deterministic: the same result files give the same bytes.

## The release procedure

Run on the device that has the raw data root, with the engine repository checked out at the release the product pins (read only). Every
file goes to the temp root, never into a repository.

1. `python -m pytest tests -p no:cacheprovider --junitxml=<temp>/product.xml` (the whole suite, including `tests/adversarial`).
2. In the engine repository: `python -m pytest tests -p no:cacheprovider --junitxml=<temp>/engine.xml`.
3. In `frontend/`: `npx vitest run --reporter=json --outputFile=<temp>/vitest.json`, then `npm run build`, because the gates
   `frontend/scripts/gate.mjs` of the web requirements run the measured browser gate on the built site and take minutes.
4. `python scripts/convergence_verdict.py --script-timeout 3600 --product-junit <temp>/product.xml --engine-junit <temp>/engine.xml --engine-repo <engine checkout> --vitest <temp>/vitest.json --device "<the device and its data root>"`.
5. The exit code must be 0. The script rewrote `verdict.md`; the release commits it.

`verdict.md` in the repository is a sample until step 4 has run for the release: it was written by `--sample` from small partial result files
(the contract tests of unit U15, the readiness test, the engine's governance tests and the vitest tests of `frontend/src/engine`), so it is
honestly NOT CONVERGED, and says so on its first line.

## Boundaries

The verdict reads and runs; it never writes outside its output file, never fetches, and never runs in CI (ADR-0074): the full suites take
longer than the CI budget and need the raw data root. It does not judge a requirement's text, only what its gate did in the run.
