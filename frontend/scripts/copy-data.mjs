// Prebuild (T3): copy into public/data/ exactly the artifacts the index declares (the index, every manifest, every
// artifact each manifest names), and fail on any that is missing. The canonical copies live in ../data/derived; this
// overlay is rebuilt from scratch every time, so a file removed from the bake never lingers in the site (failure
// class 9: a filter by extension shipped stale files and missed declared ones).
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const derived = join(here, '..', '..', 'data', 'derived');
const out = join(here, '..', 'public', 'data');

const indexRel = 'manifests/index.json';
if (!existsSync(join(derived, indexRel))) {
  console.error(`[copy-data] ${indexRel} is missing under data/derived: run the pipeline first (scripts/precompute)`);
  process.exit(1);
}
const index = JSON.parse(readFileSync(join(derived, indexRel), 'utf8'));
const declared = [indexRel];
for (const entry of index.cases) {
  declared.push(entry.manifest_path);
  const manifest = JSON.parse(readFileSync(join(derived, entry.manifest_path), 'utf8'));
  declared.push(manifest.artifact.path);
}
const missing = declared.filter((rel) => !existsSync(join(derived, rel)));
if (missing.length) {
  console.error(`[copy-data] declared but missing under data/derived:\n  ${missing.join('\n  ')}`);
  process.exit(1);
}
rmSync(out, { recursive: true, force: true });
for (const rel of declared) {
  mkdirSync(dirname(join(out, rel)), { recursive: true });
  cpSync(join(derived, rel), join(out, rel));
}
console.log(`[copy-data] ${declared.length} declared files (${index.cases.length} cases) -> public/data`);
