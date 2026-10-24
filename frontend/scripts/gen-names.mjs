// The names the committed documents give the ids a finding cites, by case: each variant document's models (`model[]`, its short
// title, else its title when the short title is the id itself or a class name), C04's agencies by their CEREP code (the variant's
// short title in the case manifest), the configuration of each measured rate (`rate:<key>`; C22: the simulation's scenario), and
// each variant's title in the case manifest, and each source by its published name (`source_details[id].name` of the manifests).
// The views of a case read the names from the document they load; the governance views, which load no case document, and the
// findings evidence of every case read them from src/workbench/names/models.gen.json, which this script writes. The names gate
// (names.test.ts) checks that the committed file equals what this script collects, so a re-bake that renames a model fails until
// the file is rewritten.
//
//   node scripts/gen-names.mjs           write src/workbench/names/models.gen.json
//   node scripts/gen-names.mjs --check   exit 1 when the committed file differs from the documents
import { existsSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const repo = resolve(here, '..', '..');
export const OUT = join(repo, 'frontend', 'src', 'workbench', 'names', 'models.gen.json');

const isCode = (s, id) => s === id || /^[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+$/.test(s) || /^[a-z0-9]+(?:[-_.][a-z0-9]+)+$/.test(s);
const text = (t) => (t && typeof t === 'object' && typeof t.en === 'string' && typeof t.es === 'string' ? { en: t.en, es: t.es } : null);
const sorted = (o) => Object.fromEntries(Object.entries(o).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0)));

/** { models, rates, variants, sources }: the first three { case: { id: { en, es } } }, sources { id: name }, from the committed
 * documents under `root`. */
export function collectModelNames(root = join(repo, 'data', 'derived')) {
  const out = { models: {}, rates: {}, variants: {}, sources: {} };
  const cases = readdirSync(root).filter((d) => /^C\d\d$/.test(d)).sort();
  for (const c of cases) {
    const names = {};
    const rates = {};
    const manifestPath = join(root, 'manifests', `${c}.json`);
    const manifest = existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : null;
    // the sources by their published name (the governance report lists a fit's sources)
    for (const [id, d] of Object.entries(manifest?.source_details ?? {})) {
      if (typeof d?.name === 'string' && !out.sources[id]) out.sources[id] = d.name;
    }
    // the variants by their manifest title (the governance report names the variant of its test rows)
    const variants = {};
    for (const a of manifest?.artifacts ?? []) {
      const name = text(a.title) ?? text(a.short_title);
      if (a.role === 'variant' && typeof a.variant_id === 'string' && name && !variants[a.variant_id]) variants[a.variant_id] = name;
    }
    for (const f of readdirSync(join(root, c)).filter((x) => x.endsWith('.json')).sort()) {
      let doc;
      try {
        doc = JSON.parse(readFileSync(join(root, c, f), 'utf8'));
      } catch {
        continue;
      }
      if (!doc || typeof doc !== 'object') continue;
      for (const m of Array.isArray(doc.model) ? doc.model : []) {
        const short = text(m.short_title);
        const name = short && !isCode(short.en, m.id) ? short : text(m.title) ?? short;
        if (typeof m.id === 'string' && name && !names[m.id]) names[m.id] = name;
      }
      for (const sim of Array.isArray(doc.outputs?.simulations) ? doc.outputs.simulations : []) {
        const scenario = text(sim?.scenario);
        if (typeof sim?.key === 'string' && scenario && !rates[sim.key]) rates[sim.key] = scenario;
      }
      const code = doc.outputs?.agency?.code;
      if (typeof code === 'string' && manifest) {
        const art = (manifest.artifacts ?? []).find((a) => a.role === 'variant' && a.variant_id === doc.variant_id);
        const name = text(art?.short_title);
        if (name && !names[code]) names[code] = name;
      }
    }
    if (Object.keys(names).length) out.models[c] = sorted(names);
    if (Object.keys(rates).length) out.rates[c] = sorted(rates);
    if (Object.keys(variants).length) out.variants[c] = sorted(variants);
  }
  out.sources = sorted(out.sources);
  return out;
}

export const serialise = (names) => `${JSON.stringify(names, null, 1)}\n`;

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const body = serialise(collectModelNames());
  if (process.argv.includes('--check')) {
    const now = existsSync(OUT) ? readFileSync(OUT, 'utf8') : '';
    if (now !== body) {
      console.error('models.gen.json differs from the committed documents: run node scripts/gen-names.mjs');
      process.exit(1);
    }
    console.log('models.gen.json matches the committed documents');
  } else {
    writeFileSync(OUT, body, 'utf8');
    const doc = JSON.parse(body);
    const n = (o) => Object.values(o).reduce((a, m) => a + Object.keys(m).length, 0);
    console.log(`wrote ${OUT} (${n(doc.models)} models, ${n(doc.rates)} rates)`);
  }
}
