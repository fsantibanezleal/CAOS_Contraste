// The raw-id scan (U16-R2b: a raw id shown where the product has a name is a blocker). It reads the text the capture tool saved
// beside each view (`npm run capture -- --text true`) and reports every id of the committed documents that a reader can see: a
// string value of a document shaped like an id (words joined by '-', '_' or '.', or a CamelCase class name), found as a whole word
// in a view's text. An engine function the C10 ladder names on purpose (its "Engine function" column) is listed apart.
//
//   node scripts/scan-raw-ids.mjs <capture out folder> [--json <file>]
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const derived = resolve(here, '..', '..', 'data', 'derived');
const ID = /^[a-z][a-z0-9]*(?:[-_.][a-z0-9]+)+$|^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+$/;
// keys whose values are prose, numbers or references a reader is meant to see as written (a URL, a path, a DOI, a hash)
const SKIP_KEYS = new Set(['sha256', 'path', 'url', 'landing', 'doi', 'basis', 'href', 'engine_version', 'version', 'schema']);

const files = (dir) => readdirSync(dir).flatMap((f) => {
  const p = join(dir, f);
  return statSync(p).isDirectory() ? files(p) : f.endsWith('.json') ? [p] : [];
});

/** Every id-shaped string value of the committed documents, with the cases that carry it. */
export function documentIds(root = derived) {
  const ids = new Map();
  for (const f of files(root)) {
    const c = relative(root, f).split(/[\\/]/)[0];
    let doc;
    try {
      doc = JSON.parse(readFileSync(f, 'utf8'));
    } catch {
      continue;
    }
    const walk = (o, key) => {
      if (Array.isArray(o)) return o.forEach((x) => walk(x, key));
      if (o && typeof o === 'object') return Object.entries(o).forEach(([k, v]) => walk(v, k));
      if (typeof o !== 'string' || SKIP_KEYS.has(key) || o.length < 4 || o.length > 60 || !ID.test(o)) return;
      if (/^\d/.test(o) || /^v?\d+(\.\d+)+$/.test(o)) return;
      if (!ids.has(o)) ids.set(o, new Set());
      ids.get(o).add(c);
    };
    walk(doc, '');
  }
  return ids;
}

const texts = (dir) => readdirSync(dir).flatMap((f) => {
  const p = join(dir, f);
  return statSync(p).isDirectory() ? texts(p) : f.endsWith('.txt') ? [p] : [];
});

export function scan(outDir) {
  const ids = documentIds();
  const hits = [];
  for (const f of texts(join(outDir, 'shots'))) {
    const t = readFileSync(f, 'utf8');
    for (const [id] of ids) {
      if (t.length < id.length) continue;
      const re = new RegExp(`(^|[^A-Za-z0-9_.-])${id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}($|[^A-Za-z0-9_-])`);
      if (re.test(t)) hits.push({ view: relative(outDir, f).replaceAll('\\', '/'), id, engine: id.startsWith('riskvalidation.') });
    }
  }
  return hits;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const out = process.argv[2];
  if (!out || !existsSync(join(out, 'shots'))) {
    console.error('usage: node scripts/scan-raw-ids.mjs <capture out folder> [--json <file>]');
    process.exit(2);
  }
  const hits = scan(out);
  const byId = new Map();
  for (const h of hits) byId.set(h.id, [...(byId.get(h.id) ?? []), h.view]);
  const rows = [...byId.entries()].sort((a, b) => b[1].length - a[1].length);
  for (const [id, views] of rows) console.log(`${String(views.length).padStart(4)}  ${id}  e.g. ${views[0]}`);
  console.log(`${rows.length} ids seen in ${new Set(hits.map((h) => h.view)).size} views`);
  const j = process.argv.indexOf('--json');
  if (j > 0) writeFileSync(process.argv[j + 1], JSON.stringify(rows.map(([id, views]) => ({ id, views })), null, 1));
}
