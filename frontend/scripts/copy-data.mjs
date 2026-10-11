// Prebuild (T3): copy into public/data/ exactly the files the index declares (see declared.mjs: the index, every
// manifest, every artifact each manifest names, and the index's further `files`), and fail on any that is missing.
// The canonical copies live in ../data/derived; this overlay is rebuilt from scratch every time, so a file removed
// from the bake never lingers in the site (failure class 9: a filter by extension shipped stale files and missed
// declared ones).
import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { declaredFiles, INDEX_REL } from './declared.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const derived = join(here, '..', '..', 'data', 'derived');
const out = join(here, '..', 'public', 'data');

if (!existsSync(join(derived, INDEX_REL))) {
  console.error(`[copy-data] ${INDEX_REL} is missing under data/derived: run the pipeline first (scripts/precompute)`);
  process.exit(1);
}
const { index, declared, missing, problems } = declaredFiles(derived);
if (missing.length || problems.length) {
  if (missing.length) console.error(`[copy-data] declared but missing under data/derived:\n  ${missing.join('\n  ')}`);
  if (problems.length) console.error(`[copy-data] ${problems.join('\n  ')}`);
  process.exit(1);
}
rmSync(out, { recursive: true, force: true });
for (const rel of declared) {
  mkdirSync(dirname(join(out, rel)), { recursive: true });
  cpSync(join(derived, rel), join(out, rel));
}
console.log(`[copy-data] ${declared.length} declared files (${index.cases.length} cases) -> public/data`);
