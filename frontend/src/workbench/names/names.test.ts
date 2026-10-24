// The names gate (U16-F9a, the ruling of 2026-10-24: a raw id shown where the product has a name is a blocker). It walks every
// committed document, the cases and the governance documents, and fails on any evidence key, test id or model id the names
// module does not name in both languages, or names with a raw id; on any test the engine registers without a name; and on a
// names table (models.gen.json) that no longer matches the documents.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
// @ts-expect-error the generator is plain JavaScript, run by node (scripts/gen-names.mjs)
import { collectModelNames, serialise } from '../../../scripts/gen-names.mjs';
import { TEST_NAMES, evidenceLabel, modelName, segmentName, testName, type NameContext } from './index';
import committed from './models.gen.json';
import registry from './registry.json';

const derived = fileURLToPath(new URL('../../../../data/derived/', import.meta.url));
const files = (dir: string): string[] =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : f.endsWith('.json') ? [p] : [];
  });
const docs = files(derived)
  .filter((p) => !p.includes(`${'manifests'}`) && !p.includes('contract') && !p.includes('regulatory'))
  .map((p) => ({ path: p.slice(derived.length).replaceAll('\\', '/'), doc: JSON.parse(readFileSync(p, 'utf8')) as unknown }));

type Obj = Record<string, unknown>;
interface Cited { path: string; caseId: string; models: NameContext['models']; key: string }
interface Row { path: string; caseId: string; models: NameContext['models']; test: string; model: string | null }

/** Every evidence key of every finding and every tests row, with the case and model list of the document that holds it. */
function collect(): { cited: Cited[]; rows: Row[] } {
  const cited: Cited[] = [];
  const rows: Row[] = [];
  for (const { path, doc } of docs) {
    const top = doc as Obj;
    const models = Array.isArray(top.model) ? (top.model as NameContext['models']) : undefined;
    const walk = (o: unknown, caseId: string) => {
      if (Array.isArray(o)) return o.forEach((x) => walk(x, caseId));
      if (!o || typeof o !== 'object') return;
      const x = o as Obj;
      // a governance report holds one inventory entry ("C01/german"): its rows are that case's
      const entry = typeof x.entry_key === 'string' ? /^(C\d\d)\//.exec(x.entry_key)?.[1] : undefined;
      const c = typeof x.case_id === 'string' && /^C\d\d$/.test(x.case_id) ? x.case_id : entry ?? caseId;
      if (Array.isArray(x.evidence) && typeof x.severity === 'string') {
        for (const k of x.evidence) if (typeof k === 'string') cited.push({ path, caseId: c, models: c === caseId ? models : undefined, key: k });
      }
      if (typeof x.test_id === 'string' && 'light' in x) {
        rows.push({ path, caseId: c, models: c === caseId ? models : undefined, test: x.test_id, model: typeof x.model_id === 'string' ? x.model_id : null });
      }
      for (const v of Object.values(x)) walk(v, c);
    };
    walk(doc, typeof top.case_id === 'string' ? top.case_id : '');
  }
  return { cited, rows };
}

const { cited, rows } = collect();
const RAW = /@|\bdesign:|\brate:|\bcontract:/;

describe('the names gate: every id a reader can meet has a name', () => {
  it('reads the committed documents (cases and governance)', () => {
    expect(docs.length).toBeGreaterThan(100);
    expect(cited.length).toBeGreaterThan(2000);
    expect(rows.length).toBeGreaterThan(1000);
  });

  it('names every test the engine registers', () => {
    const missing = (registry as { tests: Array<{ test_id: string }> }).tests.map((t) => t.test_id).filter((id) => !TEST_NAMES[id]);
    expect(missing).toEqual([]);
  });

  it('names every evidence key of every finding, in both languages, with no raw id', () => {
    const bad = new Set<string>();
    for (const c of cited) {
      const l = evidenceLabel(c.key, { caseId: c.caseId, models: c.models });
      if (!l) {
        bad.add(`${c.caseId} ${c.key} (unnamed)`);
        continue;
      }
      for (const lang of ['en', 'es'] as const) {
        const t = l.text[lang];
        const leaks = [c.key, l.testId, l.modelId !== undefined && modelName(l.modelId, { caseId: c.caseId, models: c.models })?.[lang] !== l.modelId ? l.modelId : undefined]
          .filter((s): s is string => typeof s === 'string' && s.length > 2 && t.includes(s));
        if (!t || RAW.test(t) || leaks.length) bad.add(`${c.caseId} ${c.key} (${lang}: ${t})`);
      }
    }
    expect([...bad].slice(0, 40)).toEqual([]);
  });

  it('names the test and the model of every tests row', () => {
    const bad = new Set<string>();
    for (const r of rows) {
      if (!testName(r.test)) bad.add(`${r.caseId} test ${r.test}`);
      if (r.model !== null && !modelName(r.model, { caseId: r.caseId, models: r.models })) bad.add(`${r.caseId} model ${r.model}`);
    }
    expect([...bad].slice(0, 40)).toEqual([]);
  });

  it('names the input (segment) of every row the U14 tests table shows (C02, C20)', () => {
    const bad = new Set<string>();
    for (const { path, doc } of docs) {
      const caseId = (doc as Obj).case_id;
      if (caseId !== 'C02' && caseId !== 'C20') continue;
      for (const t of ((doc as Obj).tests as Array<Obj> | undefined) ?? []) {
        const seg = t.segment;
        if (typeof seg === 'string' && seg !== 'portfolio' && !segmentName(seg, { caseId })) bad.add(`${path} ${seg}`);
      }
    }
    expect([...bad].slice(0, 40)).toEqual([]);
  });

  it('keeps models.gen.json equal to what the documents say (node scripts/gen-names.mjs)', () => {
    expect(serialise(committed)).toBe(serialise(collectModelNames(derived)));
  });
});
