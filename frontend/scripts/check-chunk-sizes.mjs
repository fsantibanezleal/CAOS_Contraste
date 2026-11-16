// The chunk-size gate (BL-102): after `npm run build`, every application JS chunk of dist/assets is under 500 KB, the
// product template's target per code chunk (vendor chunks count too). Prints the list, largest first; exits 1 with the
// chunks at or over the limit. Run: `node scripts/check-chunk-sizes.mjs [dist]` (default frontend/dist).
import { existsSync, readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const LIMIT_BYTES = 500_000;

/** The `.js` chunks of `<dist>/assets` with their byte counts, largest first, and those at or over the limit. */
export function checkChunkSizes(dist) {
  const assets = join(dist, 'assets');
  if (!existsSync(assets)) throw new Error(`${assets}: no assets folder; run npm run build first`);
  const chunks = readdirSync(assets)
    .filter((n) => n.endsWith('.js'))
    .map((name) => ({ name, bytes: statSync(join(assets, name)).size }))
    .sort((a, b) => b.bytes - a.bytes || a.name.localeCompare(b.name));
  return { chunks, failures: chunks.filter((c) => c.bytes >= LIMIT_BYTES) };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dist = resolve(process.argv[2] ?? fileURLToPath(new URL('../dist', import.meta.url)));
  const { chunks, failures } = checkChunkSizes(dist);
  for (const c of chunks) console.log(`${String(c.bytes).padStart(9)}  ${c.name}${c.bytes >= LIMIT_BYTES ? '  OVER' : ''}`);
  if (failures.length) {
    console.error(`${failures.length} chunk(s) at or over ${LIMIT_BYTES} bytes: ${failures.map((f) => f.name).join(', ')}`);
    process.exit(1);
  }
  console.log(`all ${chunks.length} chunks are under ${LIMIT_BYTES} bytes`);
}
