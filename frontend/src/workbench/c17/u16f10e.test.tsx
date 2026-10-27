// U16-F10e (fix round 4, the third capture review R3, batch c18): on the four committed documents, in both languages. The Spanish
// golden reference of the SMA is Spanish, the SMA ILM test row shows the jump that decides its light, the capital tables write their
// money in the scale of the table so the last column fits at 1280, the Spanish header of the by-years table is short enough to leave
// the drawing its axis title, no Spanish view says "benchmark", and the minors of the batch (the capital-stability row shows its
// dispersion, a single-cell view lists the tests of its cell, no negative zero, the coarse Panjer grid said).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { ByMethodView, ByYearsView, ScenarioView, influenceFormat } from './CapitalViews';
import { ExceedanceView, TailIndexView } from './LossViews';
import { LadderView, SmaSpecView } from './ModelViews';
import { ResponseView, SmaView } from './SmaViews';
import { C17ContextView, C17FindingsView } from './C17Common';
import { cellOf, defaultSel, outputsOf, type C17Sel } from './selection';

const NAMES = ['xi-0-6', 'xi-0-8', 'xi-0-96', 'xi-1-1'] as const;
const models = committedDoc<ModelsArtifact>('C17', 'models-generator');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const selOf = (name: string): C17Sel => defaultSel(fixtureData('C17', committedDoc<VariantArtifact>('C17', name), models, title)) as C17Sel;
const VIEWS = [ExceedanceView, TailIndexView, ByMethodView, ByYearsView, ScenarioView, SmaView, ResponseView, LadderView, SmaSpecView, C17FindingsView, C17ContextView];

describe('U16-F10e C17', () => {
  afterEach(() => setLang('en'));

  it('c18 B1: the Spanish golden value of the SMA cites its reference in Spanish', () => {
    for (const name of NAMES) {
      const es = textOf(render(<SmaSpecView sel={selOf(name)} />, 'es'));
      expect(es, name).not.toMatch(/footnote/);
      expect(es, name).toContain('OPE25.7 nota 2');
      expect(textOf(render(<SmaSpecView sel={selOf(name)} />, 'en')), name).toContain('OPE25.7 footnote 2');
    }
  });

  it('c18 M3: the SMA ILM test row shows the jump that decides its light, the ILM before and after and the loss added', () => {
    for (const name of NAMES) {
      const sel = selOf(name);
      const t = sel.data.variant.tests.find((x) => x.test_id === 'oprisk.sma_ilm_response')!;
      const ex = t.extras as { ilm_before: number; ilm_after: number; added_loss: number };
      for (const lang of ['en', 'es'] as const) {
        const html = render(<ResponseView sel={sel} />, lang);
        const row = /<tr[^>]*data-test="oprisk\.sma_ilm_response"[\s\S]*?<\/tr>/.exec(html)![0];
        const text = textOf(row);
        const f = (v: number) => new Intl.NumberFormat(lang === 'en' ? 'en-US' : 'es-CL', { maximumSignificantDigits: 3 }).format(v);
        // the statistic column shows the jump (metric), never the ILM after the loss as if it were the jump
        expect(text, `${name} ${lang}`).toContain(f(t.metric!));
        expect(text, `${name} ${lang}`).toContain(f(ex.ilm_before));
        expect(text, `${name} ${lang}`).toContain(f(ex.ilm_after));
        expect(text, `${name} ${lang}`).toContain(new Intl.NumberFormat(lang === 'en' ? 'en-US' : 'es-CL').format(ex.added_loss));
        expect(text, `${name} ${lang}`).toMatch(lang === 'en' ? /jump/ : /salto/);
      }
    }
  });

  it('c18 M2: the capital tables write their money in the scale of the table, so no cell carries an 11-digit amount', () => {
    for (const name of NAMES) {
      for (const lang of ['en', 'es'] as const) {
        for (const View of [ByYearsView, ByMethodView]) {
          const html = render(<View sel={selOf(name)} />, lang);
          const table = /<table[^>]*data-table="capital-by-(?:cell|rung)"[\s\S]*?<\/table>/.exec(html)![0];
          expect(textOf(table), `${name} ${lang}`).not.toMatch(/\d{1,3}(?:[.,]\d{3}){3,}/);
          expect(textOf(table), `${name} ${lang}`).toMatch(/\((?:m EUR|mn EUR|M EUR|bn EUR|mil M EUR)\)/);
        }
      }
    }
  });

  it('c18 M1: the Spanish by-years header is short (the four-line header took the drawing its axis title)', () => {
    const es = textOf(render(<ByYearsView sel={selOf('xi-0-8')} />, 'es'));
    expect(es).not.toContain('Definido para este método');
    expect(es).toContain('Con capital');
  });

  it('no Spanish view of C17 says "benchmark" (ruling 2026-10-27: translated in prose)', () => {
    for (const name of NAMES) for (const View of VIEWS) expect(textOf(render(<View sel={selOf(name)} />, 'es')), name).not.toMatch(/benchmark/i);
  });

  it('m2: a capital-stability row shows the dispersion that decides its light beside the bias', () => {
    const sel = selOf('xi-0-8');
    const html = render(<ByMethodView sel={sel} />, 'en');
    const row = /<tr[^>]*data-test="oprisk\.capital_stability"[\s\S]*?<\/tr>/.exec(html)![0];
    expect(textOf(row)).toMatch(/dispersion [\d.]+/);
    expect(textOf(render(<ByMethodView sel={sel} />, 'es'))).toMatch(/dispersión [\d,]+/);
  });

  it('m4: a view of one cell lists the tests of that cell only', () => {
    for (const name of NAMES) {
      const sel = selOf(name);
      const cell = cellOf(outputsOf(sel)!, sel.years, sel.threshold);
      for (const View of [ByMethodView, TailIndexView]) {
        const html = render(<View sel={sel} />, 'en');
        const segments = [...html.matchAll(/data-segment="([^"]+)"/g)].map((m) => m[1]);
        expect(segments.length, name).toBeGreaterThan(0);
        expect(new Set(segments), name).toEqual(new Set([cell.id]));
      }
    }
  });

  it('m5: an influence under half a percent is never written as a negative zero', () => {
    expect(influenceFormat(-0.0037)).toEqual({ percent: true, decimals: 1 });
    expect(influenceFormat(0.083)).toEqual({ percent: true, decimals: 0 });
    for (const name of NAMES) expect(textOf(render(<ScenarioView sel={selOf(name)} />, 'en')), name).not.toMatch(/-0 %|-0%/);
  });

  it('m1: the benchmark-reproduction row says its statistic is the share of the tolerance used', () => {
    const html = render(<ExceedanceView sel={selOf('xi-0-8')} />, 'en');
    const row = /<tr[^>]*data-test="oprisk\.benchmark_reproduction"[\s\S]*?<\/tr>/.exec(html)![0];
    expect(textOf(row)).toMatch(/share of the tolerance/);
    const es = render(<ExceedanceView sel={selOf('xi-0-8')} />, 'es');
    expect(textOf(/<tr[^>]*data-test="oprisk\.benchmark_reproduction"[\s\S]*?<\/tr>/.exec(es)![0])).toMatch(/parte de la tolerancia/);
  });

  it('m13: the methods table is the first thing of its box, the notes under it', () => {
    for (const name of NAMES) {
      const html = render(<ByMethodView sel={selOf(name)} />, 'en');
      expect(html.indexOf('data-table="capital-by-rung"'), name).toBeLessThan(html.indexOf('data-bar-truth'));
    }
  });

  it('m10: the exceedance note says the Panjer cross-check runs on a coarser grid', () => {
    expect(textOf(render(<ExceedanceView sel={selOf('xi-1-1')} />, 'en'))).toMatch(/coarser grid/);
    expect(textOf(render(<ExceedanceView sel={selOf('xi-1-1')} />, 'es'))).toMatch(/grilla más gruesa/);
  });
});
