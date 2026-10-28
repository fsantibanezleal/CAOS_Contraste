// U16-F13c (R5 batches c13 and c14, C10): every row of C10's tests tables names its segment, never "-" (M1, R5 ruling 2): the tail
// back-test row names the whole portfolio at its primary level, the CreditRisk+ row the whole portfolio. With the minors of the batches
// fixed in the view: a known correlation of the size-power rows written as the cell table writes it, a percent (c13 N3); a size or power
// row says what its light grades, the rejection rate (c13 N4); the second moment written "E[L²]" (c13 N5); and the profile likelihood
// read with two decimals (c14 N2). Reads the committed documents, in both languages.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { html, setLang } from '../c03/u6-testkit';
import { committedData } from '../c08/spanish-testkit';
import { BacktestView, CorrelationView } from './FitViews';
import { RungsView } from './CapitalViews';
import { SizePowerView } from './SimulatorViews';
import { segmentText } from './C10Common';
import { defaultSel, referenceNote, type C10Sel } from './selection';

const lines = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (lines.push(p), mod.UPlotChart(p)) };
});

const TITLE = { en: 'Portfolio credit capital', es: 'Capital de crédito de cartera' };
const LOANS = ['commercial-industrial', 'commercial-real-estate', 'credit-cards', 'other-consumer', 'residential'];
const GRIDS = ['grid-22', 'grid-40'];
const selOf = (v: string) => defaultSel(committedData('C10', `${v}.json`, 'models-c10.json', TITLE)) as C10Sel;
const NBSP = ' ';
const rowsOf = (markup: string) => [...markup.matchAll(/<tr [^>]*data-test="([^"]+)"[^>]*>([\s\S]*?)<\/tr>/g)].map((m) => ({ test: m[1], cells: [...m[2].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((c) => c[1].replace(/<[^>]*>/g, '')) }));

describe('U16-F13c, C10 (R5 c13 and c14)', () => {
  afterEach(() => setLang('en'));

  it('M1: no Segment cell of a C10 tests table reads "-": the tail back-test and the CreditRisk+ rows name the whole portfolio', () => {
    const want = {
      en: { tail: `whole portfolio, the 99${NBSP}% level`, crp: 'whole portfolio' },
      es: { tail: `toda la cartera, nivel de 99${NBSP}%`, crp: 'toda la cartera' },
    };
    for (const v of LOANS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        const rows = [...rowsOf(html(<BacktestView sel={selOf(v)} />)), ...rowsOf(html(<RungsView sel={selOf(v)} />))];
        expect(rows.length, v).toBeGreaterThan(1);
        for (const r of rows) expect(r.cells[2], `${v} ${lang} ${r.test}`).not.toBe('-');
        expect(rows.find((r) => r.test === 'portfolio.tail_backtest')!.cells[2], v).toBe(want[lang].tail);
        expect(rows.find((r) => r.test === 'portfolio.crp_recursion_vs_mc')!.cells[2], v).toBe(want[lang].crp);
      }
    }
    expect(segmentText(null, 'en')).toBe('whole portfolio');
    expect(segmentText(null, 'es')).toBe('toda la cartera');
  });

  it('N3: a known correlation of the size-power rows is a percent, as the cell table writes it', () => {
    expect(segmentText('rho=0.02/maximum-likelihood', 'en')).toBe(`known correlation 2.0${NBSP}%, maximum likelihood`);
    expect(segmentText('rho=0.12/moments', 'es')).toBe(`correlación conocida 12,0${NBSP}%, método de momentos`);
    for (const g of GRIDS) {
      for (const lang of ['en', 'es'] as const) {
        setLang(lang);
        for (const r of rowsOf(html(<SizePowerView sel={selOf(g)} />))) expect(r.cells[2], g).toMatch(/\d %, /);
      }
    }
  });

  it('N4: a size or power row says what its light grades: the rejection rate, against alpha or the power thresholds', () => {
    for (const g of GRIDS) {
      for (const [lang, size, power] of [['en', 'size: rejection rate', 'power: rejection rate'], ['es', 'tamaño: tasa de rechazo', 'potencia: tasa de rechazo']] as const) {
        setLang(lang);
        const rows = rowsOf(html(<SizePowerView sel={selOf(g)} />));
        expect(rows.length, g).toBeGreaterThan(0);
        for (const r of rows) expect(r.cells.at(-1), `${g} ${lang}`).toMatch(new RegExp(`^(${size}|${power}) \\d`));
        expect(rows.some((r) => r.cells.at(-1)!.startsWith(size)), g).toBe(true);
      }
    }
  });

  it('N5: the reference of the method of moments writes the second moment "E[L²]" in both languages', () => {
    for (const ref of ['dossier 04 C.4 (E[L^2] = joint default probability)', 'dossier 04 C.4 (E[L²] = joint default probability)']) {
      expect(referenceNote(ref, 'en')).toBe('dossier 04 C.4 (E[L²] = joint default probability)');
      expect(referenceNote(ref, 'es')).toBe('dossier 04 C.4 (E[L²] = probabilidad conjunta de incumplimiento)');
    }
  });

  it('c14 N2: the profile likelihood reads with two decimals, so the maximum and the cutoff crossing are told apart', () => {
    lines.length = 0;
    html(<CorrelationView sel={selOf('other-consumer')} />);
    expect(lines.at(-1)!.y.format).toEqual({ decimals: 2 });
  });
});
