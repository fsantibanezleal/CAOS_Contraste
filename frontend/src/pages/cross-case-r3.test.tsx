// U16-F10p (the third capture review, R3 c23): the Benchmark and Experiments pages on the committed documents, in both
// languages. A reason the engine writes in English reads in Spanish on the Spanish page (C03, C17); a rung prints its name, not
// its id (C20); a source prints its name with a Spanish locator (the case facts); the coverage status names no plan unit; and
// the shared comparison table is whole at every width (it scrolls in its own box, reads from the top of each row).
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { setLang } from '../workbench/c03/u6-testkit';
import { batch3BenchmarkTables, batch3ExperimentTables } from './Batch3Sections';
import { Coverage } from './Experiments';
import { Table, c03BenchmarkRows } from './U6Sections';
import { wave2BenchmarkTables, wave2ExperimentTables } from './Wave2Sections';
import { sourceText } from '../content/sources';

const root = new URL('../../../data/derived/', import.meta.url);
const json = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, root), 'utf8')) as T;
const manifest = (id: string) => json<CaseManifest>(`manifests/${id}.json`);
const variants = (m: CaseManifest) => m.artifacts.filter((a) => a.role === 'variant').map((a) => json<VariantArtifact<unknown>>(a.path));
const cells = (tables: Array<{ head: string[]; rows: unknown[][]; note?: string }>) => tables.flatMap((t) => [...t.head, t.note ?? '', ...t.rows.flat().map((c) => (typeof c === 'string' ? c : ''))]).join(' | ');
const LANGS = ['en', 'es'] as const;

describe('engine reasons in the reader language (R3 c23 B1)', () => {
  afterEach(() => setLang('en'));

  it('C03: the absent TabPFN challenger reads its reason in Spanish on the Spanish Benchmark', () => {
    const m = manifest('C03');
    for (const v of variants(m)) {
      const es = c03BenchmarkRows(v, 'es').flat().join(' | ');
      expect(es).not.toMatch(/is the optional extra|not installed in the bake environment/);
      expect(es).toMatch(/no disponible/);
    }
  });

  it('C17 xi 1.1: the infinite-mean reason reads in Spanish on both pages', () => {
    const m = manifest('C17');
    const vs = variants(m);
    const es = `${cells(wave2BenchmarkTables(m, vs, 'es'))} ${cells(wave2ExperimentTables(m, vs, 'es'))}`;
    expect(es).not.toMatch(/the tail index is 1 or more|infinite mean|does not exist/);
  });
});

describe('a rung by its name (R3 c23 B2)', () => {
  it('C20: no raw rung id in the Seeds rows and tables, in either language', () => {
    const m = manifest('C20');
    const vs = variants(m);
    for (const lang of LANGS) {
      const all = `${cells(batch3ExperimentTables(m, vs, lang))} ${cells(batch3BenchmarkTables(m, vs, lang))}`;
      expect(all.match(/\bP\d-(lightgbm|xgboost)\b/)?.[0] ?? null, lang).toBeNull();
      expect(all, lang).toContain('P4 LightGBM');
    }
  });
});

describe('sources by name, with the locator in the reader language (R3 c23 B4)', () => {
  it('every source of every case manifest has a Spanish name whose locator and description are Spanish', () => {
    const ids = new Set<string>();
    for (const f of ['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C20', 'C21', 'C22']) for (const s of manifest(f).sources) ids.add(s);
    expect(ids.size).toBeGreaterThan(20);
    for (const id of ids) {
      const m = Object.values(['C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C20', 'C21', 'C22'].map(manifest)).find((x) => x.sources.includes(id))!;
      const en = m.source_details[id]?.name ?? id;
      expect(sourceText(id, en, 'en'), id).toBe(en);
      const es = sourceText(id, en, 'es');
      expect(es, id).not.toMatch(/, (section|Tables?) \d|\(failures, financials\)|BDE and API|end-of-month spot rates|assets and liabilities|the simulation of|rejection rates|daily par yield|public-domain series|data library|review of the supervision|charge-off and delinquency|loan data|climate scenarios|stress test scenario|Disclosure Act data|supervisory stress test/);
    }
  });
});

describe('the coverage status names no plan unit (R3 c23 B5)', () => {
  afterEach(() => setLang('en'));

  for (const lang of LANGS) {
    it(`${lang}: a planned case reads "planned", without the unit code`, () => {
      setLang(lang);
      const m = renderToStaticMarkup(<Coverage built={new Set(['C01'])} />);
      expect(m).not.toMatch(/\(U\d+[^)]*\)/);
      expect(m).toContain(lang === 'es' ? 'planificado' : 'planned');
    });
  }
});

describe('the comparison table is whole at every width (R3 c23 M2, M3)', () => {
  it('it sits in a box that scrolls sideways with a faded edge at every width, and its rows read from the top', () => {
    const m = renderToStaticMarkup(<Table head={['A', 'B']} rows={[['x', 'y']]} />);
    expect(m).toMatch(/<div[^>]*data-table-box[^>]*style="[^"]*overflow-x:auto/);
    expect(m).toMatch(/mask-image/);
    expect(m).toMatch(/<table class="caos-table ct-top"/);
  });
});
