// U16-F12e (fix round 5, the fourth capture review R4, batch c21): on the four committed documents, in both languages. The sentence
// beside a curve that stops says which point is the last one inside its grid (never that the grid ends there: the committed step
// and point count put the end later), the FFT gaps past its grid are drawn as gaps, the English money unit is spelled one way, the
// by-years header uses the case's term, the authors keep their umlauts in English, the Spanish names the LDCE once, and the 390
// key tables keep a date whole and give the value its width.
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { ByYearsView } from './CapitalViews';
import { ExceedanceView, exceedanceChart } from './LossViews';
import { LadderView, SmaSpecView } from './ModelViews';
import { ResponseView, SmaView } from './SmaViews';
import { C17ContextView } from './C17Common';
import { defaultSel, outputsOf, type C17Sel } from './selection';

const NAMES = ['xi-0-6', 'xi-0-8', 'xi-0-96', 'xi-1-1'] as const;
const models = committedDoc<ModelsArtifact>('C17', 'models-generator');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const selOf = (name: string): C17Sel => defaultSel(fixtureData('C17', committedDoc<VariantArtifact>('C17', name), models, title)) as C17Sel;
const whole = (v: number, lang: 'en' | 'es') => new Intl.NumberFormat(lang === 'en' ? 'en-US' : 'es-CL', { maximumFractionDigits: 0 }).format(v);
const lastInside = (values: Array<number | null>): number => values.map((v) => v !== null).lastIndexOf(true);

describe('U16-F12e C17', () => {
  afterEach(() => setLang('en'));

  it('c21 B1: a curve that stops names its last point inside the grid, never the end of the grid', () => {
    let stops = 0;
    for (const name of NAMES) {
      const e = outputsOf(selOf(name))!.exceedance;
      for (const lang of ['en', 'es'] as const) {
        const html = render(<ExceedanceView sel={selOf(name)} />, lang);
        const text = textOf(html);
        expect(text, `${name} ${lang}`).not.toMatch(/grid ends at|grilla de la recursión termina en|grilla de la FFT termina en/);
        for (const [id, values] of [['panjer', e.panjer.exceedance], ['fft', e.fft.exceedance]] as const) {
          const last = lastInside(values as Array<number | null>);
          if (last < 0 || last === e.grid_eur.length - 1) continue;
          stops += 1;
          const row = textOf(new RegExp(`<tr[^>]*data-method="${id}"[\\s\\S]*?</tr>`).exec(html)![0]);
          const said = lang === 'en' ? `last point inside the grid is ${whole(e.grid_eur[last], 'en')} EUR` : `último punto dentro de la grilla es ${whole(e.grid_eur[last], 'es')} EUR`;
          expect(row, `${name} ${lang} ${id}`).toContain(said);
        }
      }
    }
    // the Panjer curve stops on every variant and the FFT on xi 0.96 and 1.1: 6 curves, each in two languages
    expect(stops).toBe(12);
  });

  it('c21 m12: the FFT exceedance past its grid is null in the documents of xi 0.96 and 1.1 and drawn as a gap', () => {
    for (const name of ['xi-0-96', 'xi-1-1']) {
      const o = outputsOf(selOf(name))!;
      const points = o.exceedance.fft.exceedance as Array<number | null>;
      const last = lastInside(points);
      expect(last, name).toBeLessThan(points.length - 1);
      expect(points.slice(last + 1).every((v) => v === null), name).toBe(true);
      const values = exceedanceChart(o.exceedance, o.truth).series.find((s) => (s.label as { en: string }).en === 'FFT')!.values;
      for (let i = last + 1; i < points.length; i++) expect(values[i], `${name} ${i}`).toBeNull();
    }
  });

  it('c21 m2: the English money unit is spelled "mn EUR" on every axis, never "m EUR"', () => {
    for (const name of NAMES) {
      const o = outputsOf(selOf(name))!;
      expect(exceedanceChart(o.exceedance, o.truth).x.unit, name).toEqual({ en: 'mn EUR', es: 'M EUR' });
      for (const View of [ExceedanceView, ResponseView, SmaView]) expect(textOf(render(<View sel={selOf(name)} />, 'en')), name).not.toMatch(/\bm EUR\b/);
    }
  });

  it('c21 m5: the English by-years header uses the case\'s term "With a capital"', () => {
    const en = textOf(render(<ByYearsView sel={selOf('xi-0-8')} />, 'en'));
    expect(en).not.toContain('Defined for this method');
    expect(en).toContain('With a capital');
  });

  it('c21 m7: the English references write Böcker and Wüthrich as published', () => {
    for (const name of NAMES) {
      const en = textOf(render(<LadderView sel={selOf(name)} />, 'en'));
      expect(en, name).not.toMatch(/Bocker|Wuthrich/);
      expect(en, name).toContain('Böcker and Sprittulla');
      expect(en, name).toContain('Shevchenko and Wüthrich');
    }
  });

  it('c21 m9: the Spanish Context names the LDCE one way', () => {
    const es = textOf(render(<C17ContextView sel={selOf('xi-0-8')} />, 'es'));
    expect(es).not.toContain('Datos de Pérdida 2008');
    expect(es).toContain('Ejercicio de Recolección de Datos de Pérdidas');
  });

  it('c21 m10, m11: a key table keeps a date whole and its label column narrow at 390', () => {
    const html = render(<SmaSpecView sel={selOf('xi-0-8')} />, 'es');
    expect(html).toMatch(/<span style="white-space:nowrap">2024-07-05<\/span>/);
    expect(html).not.toMatch(/min-width:11rem/);
  });
});
