// U16-F12c (R4 batch c11, C09): the Spanish By design view at 1280 gives its chart and its estimates the room they need (M1: the chart
// scrolled in its box and cut its axis title; M2: the estimates showed 7 of 8 rows) by writing each sentence once: the chart card's
// title and note in fewer lines, the light rule only on the Tests sub-view it belongs to. With the minors of the batch fixed in the
// view: the band back-test states its light rule and the largest band gap it reads (m3), a taller back-test drawing (m7), a floor card
// wide enough for its five rows (m6) and the reference date as a real subscript (m8). Reads the committed documents, in both languages.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { ByDesignView, EstimatorTestsView } from './CcfViews';
import { BacktestTestsView, BacktestView, FloorsView } from './EadViews';
import { C09ContextView } from './C09Common';
import { defaultSel, outputsOf, type C09Sel } from './selection';
import type { VariantArtifact } from '../../lib/contract.types';

const TITLE = { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' };
const LEVELS = [0, 1, 2, 3, 4, 5];
const selOf = (n: number) => defaultSel(committedData('C09', `level-${n}.json`, 'models-generator.json', TITLE)) as C09Sel;
const cardsOf = (m: string) => m.split('<figure class="caos-plot').slice(1);
// the text without its tags; the no-break space before a percent sign is kept (a plain \s would fold it)
const text = (m: string) => m.replace(/<[^>]*>/g, ' ').replace(/[ \t\r\n]+/g, ' ');

describe('U16-F12c, C09 (R4 c11)', () => {
  afterEach(() => setLang('en'));

  it('M1: the Spanish chart card of By design has a short title and a note of one sentence (the legend names the tones)', () => {
    setLang('es');
    const card = cardsOf(html(<ByDesignView sel={selOf(3)} />))[0];
    expect(card).toContain('El CCF estimado y el conocido');
    expect(card).not.toContain('Las estimaciones de CCF contra el CCF conocido');
    const note = /<p class="caos-plot-note">(.*?)<\/p>/s.exec(card)?.[1] ?? text(card);
    expect(note).not.toContain('Verde es una estimación');
    expect(text(note).length).toBeLessThanOrEqual(180);
  });

  it('M2: the estimates card does not repeat the light rule of the Tests sub-view; the Tests sub-view keeps it', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const sel = selOf(3);
      const card = text(cardsOf(html(<ByDesignView sel={sel} />))[1]);
      expect(card).not.toMatch(/The light of each test|La luz de cada prueba/);
      expect(card).not.toMatch(/A red bar is an estimate|Una barra roja es/);
      expect(view(<EstimatorTestsView sel={sel} />)).toMatch(lang === 'en' ? /green within it, amber up to twice it and red beyond/ : /verde dentro de ella, ámbar hasta el doble y rojo más allá/);
    }
  });

  it('m3: the band back-test states its light rule and shows the largest band gap that decides each light, in both languages', () => {
    for (const n of LEVELS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const sel = selOf(n);
        const v = committed<VariantArtifact>('C09', `level-${n}.json`);
        const rows = v.tests.filter((t) => t.test_id === 'lgd_ead.ead_backtest_by_band');
        const markup = html(<BacktestTestsView sel={sel} />);
        const words = text(markup);
        const th = (rows[0].extras as { thresholds: { gap_amber: number; gap_red: number } }).thresholds;
        expect(words).toContain(formatNumber(th.gap_amber, lang, { percent: true, decimals: 0 }));
        expect(words).toContain(formatNumber(th.gap_red, lang, { percent: true, decimals: 0 }));
        expect(words).toContain(lang === 'en' ? 'Largest band gap' : 'Mayor brecha de un tramo');
        for (const r of rows) expect(words, `level ${n} ${r.model_id}`).toContain(formatNumber(r.metric as number, lang, { percent: true, decimals: 2 }));
        expect(markup).toContain('data-table="ead-band-gap"');
      }
    }
  });

  it('m7: the back-test drawing is 16 rem tall at 1280, so its value axis carries more than one tick', () => {
    expect(html(<BacktestView sel={selOf(3)} />)).toContain('--ct-chart-min:16rem');
  });

  it('m6: the floor card and the supervisory CCF card share the row evenly', () => {
    const markup = html(<FloorsView sel={selOf(3)} />);
    const shares = [...markup.matchAll(/class="caos-views-col" data-share="([\d.]+)"/g)].map((m) => Number(m[1]));
    expect(shares).toEqual([1, 1]);
  });

  it('m8: the reference date of the convention is a subscript element, not the tiny letter "ᵣ"', () => {
    const sel = selOf(3);
    const markup = html(<C09ContextView sel={sel} />);
    expect(outputsOf(sel)!.convention.formula).toContain('t_r');
    expect(markup).toContain('t<sub>r</sub>');
    expect(markup).not.toContain('ᵣ');
  });
});
