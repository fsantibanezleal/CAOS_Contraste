// U16-F13e (fix round 6, the fifth capture review R5, batch c23), on the four committed documents in both languages: every row of
// every C17 tests table names its method and cell, and the benchmark row of no segment its scope in words (R5 ruling 2); the
// Context's definition lists give the value its width at 390 (m10); the response chart's value axis starts at zero, so it carries
// labelled ticks, and it marks the added loss its red ILM test reads (n2, n3); and the tail view keeps its thresholds table above
// the infinite-mean callout (n4).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C17ContextView } from './C17Common';
import { TailIndexView } from './LossViews';
import { responseMarks, responseYRange } from './SmaViews';
import { C17TestsTable, type TestHost } from './Tests';
import { defaultSel, outputsOf, type C17Sel } from './selection';

const NAMES = ['xi-0-6', 'xi-0-8', 'xi-0-96', 'xi-1-1'] as const;
const HOSTS: TestHost[] = ['exceedance', 'tail', 'method', 'response', 'scenario', 'ladder'];
const models = committedDoc<ModelsArtifact>('C17', 'models-generator');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const doc = (name: string) => committedDoc<VariantArtifact>('C17', name);
const selOf = (name: string): C17Sel => defaultSel(fixtureData('C17', doc(name), models, title)) as C17Sel;
const LANGS = ['en', 'es'] as const;

describe('U16-F13e C17', () => {
  afterEach(() => setLang('en'));

  it('ruling 2: every row of every C17 tests table names its segment, the benchmark row its scope in words', () => {
    let benchmark = 0;
    for (const name of NAMES) {
      for (const lang of LANGS) {
        let rows = 0;
        for (const host of HOSTS) {
          const html = render(<C17TestsTable variant={doc(name)} host={host} />, lang);
          for (const m of html.matchAll(/<tr data-test="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/g)) {
            rows += 1;
            expect(m[2], `${name} ${lang} ${m[1]}`).toMatch(/class="ct-row-detail"[^>]*data-scope="[^"]+"[^>]*>[^<]+</);
            if (m[1] === 'oprisk.benchmark_reproduction') {
              expect(textOf(m[2]), `${name} ${lang}`).toContain(lang === 'en' ? "the generator's true loss distribution" : 'la distribución verdadera de pérdidas del generador');
              benchmark += 1;
            }
          }
        }
        expect(rows, `${name} ${lang}`).toBe(doc(name).tests.length);
      }
    }
    expect(benchmark).toBe(8);
  });

  it('m10: the Context definition lists cap their label column, so a value is not squeezed at 390', () => {
    for (const lang of LANGS) {
      const html = render(<C17ContextView sel={selOf('xi-0-8')} />, lang);
      const dls = [...html.matchAll(/<dl class="ct-defs"([^>]*)>/g)];
      expect(dls.length, lang).toBe(3);
      for (const m of dls) expect(m[1], lang).toContain('grid-template-columns:fit-content(min(14rem, 38%)) minmax(0, 1fr)');
    }
  });

  it('n2: the response chart\'s value axis starts at zero and holds every capital', () => {
    for (const name of NAMES) {
      const o = outputsOf(selOf(name))!;
      const div = 1e6;
      const [lo, hi] = responseYRange(o.sma_response.rows, div);
      expect(lo, name).toBe(0);
      const top = Math.max(...o.sma_response.rows.flatMap((r) => [r.orc_eur, r.lda_capital_eur])) / div;
      expect(hi, name).toBeGreaterThanOrEqual(top);
    }
  });

  it('n3: the response chart marks the added loss its red ILM test reads', () => {
    for (const name of NAMES) {
      const v = doc(name);
      const t = v.tests.find((r) => r.test_id === 'oprisk.sma_ilm_response')!;
      const loss = (t.extras as { added_loss: number }).added_loss;
      const marks = responseMarks(v);
      expect(marks, name).toEqual([{ x: loss / 1e6, label: { en: 'ILM test point', es: 'Punto de la prueba del ILM' } }]);
    }
  });

  it('n4: the thresholds table comes before the infinite-mean callout', () => {
    for (const lang of LANGS) {
      const html = render(<TailIndexView sel={selOf('xi-1-1')} />, lang);
      const table = html.indexOf('data-table="threshold-stability"');
      const callout = html.indexOf('data-infinite-mean="true"');
      expect(table, lang).toBeGreaterThan(0);
      expect(callout, lang).toBeGreaterThan(table);
    }
  });
});
