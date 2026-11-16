- Every application chunk of the build is under 500 KB (the largest is the shell index at 361 KB): the Workbench chunk went from 1,652,474 to
  135,002 bytes and the Methodology chunk from 913,096 to 119,121 bytes, with no change to what any page shows. Each case's instrument loads
  when the case is selected (a lazy glob keyed by case id; the component that calls its `useInstrument` is keyed by the case id, so one hook
  runs per mount, and a loaded module is kept) and each Methodology section's body loads when its tab opens. While a module loads the stage
  shows the shell's pending state; a failed import shows the absent instrument or the section's absence with its reason.
- A Methodology section is now two files, `<name>.meta.ts` (`methodologyMeta`: id, group, order, title; eager) and `<name>.tsx` (the lazy
  body, `methodologySection`); the registry pairs them by stem and fails at load, naming the file, on an orphan on either side.
- `npm run check:chunks` is not wired yet; `frontend/scripts/check-chunk-sizes.mjs` lists the chunks of `dist/assets` and exits 1 for any at or over 500,000 bytes.
