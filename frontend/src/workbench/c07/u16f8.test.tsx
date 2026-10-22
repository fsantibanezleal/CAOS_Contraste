// U16-F8 (D16-21, shell 0.19.0), on the committed C07 documents: the provision by segment is the shell BarChart with grouped bars
// (one band a segment, one bar a regime, the legend naming the regimes), and the bridge from the B-1 total to the IFRS 9 total is
// the shell BarChart with floating bars: the two totals as dots on an axis that does not start at zero, each step a span from the
// running total, red when it adds and green when it subtracts. Every number the chart is given is a field of the document, and the
// bridge closes on the IFRS 9 total. No view draws its own <svg>: the chart, its readout, keyboard, zoom and table are the shell's.
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { BridgeView, SegmentsView, ThreeRegimeView } from './RegimeViews';
import { money } from '../c06/format';
import { defaultSel, outputsOf, type C07Sel } from './selection';

type Datum = { id: string; label: { en: string; es: string }; value: number | null; tone?: string; span?: [number, number]; group?: { id: string; label: { en: string; es: string } } };
type Props = { title: { en: string; es: string }; data: Datum[]; axis: { label: { en: string; es: string }; unit?: { en: string; es: string }; range?: [number, number] }; legend?: Array<{ tone: string; label: { en: string; es: string } }>; onSelect?: unknown };
const bars = vi.hoisted(() => [] as Props[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: never) => (bars.push(p), mod.BarChart(p)) };
});

const ids = variantIds('C07');
const selOf = (id: string) => defaultSel(committedData('C07', id)) as C07Sel;
const LANGS = ['en', 'es'] as const;
const M = 1e6;

function charts(markup: () => string): { markup: string; props: Props[] } {
  bars.length = 0;
  const m = markup();
  return { markup: m, props: [...bars] };
}

describe('U16-F8 C07: the shell draws the grouped bars and the bridge', () => {
  afterEach(() => setLang('en'));

  it('no C07 view draws its own <svg>: the two hand-drawn charts are gone from the source', () => {
    const src = readFileSync(new URL('./RegimeViews.tsx', import.meta.url), 'utf8');
    expect(src).not.toMatch(/<svg/);
    expect(src).not.toMatch(/<Stage\b/);
  });

  for (const id of ids) {
    for (const lang of LANGS) {
      it(`${id}, ${lang}: the provision by segment is a grouped BarChart of the three regimes, with the document's provisions`, () => {
        const s = selOf(id);
        const o = outputsOf(s)!;
        for (const View of [SegmentsView, ThreeRegimeView]) {
          const { markup, props } = charts(() => render(<View sel={s} />, lang));
          expect(markup).not.toContain('ct-map-stage');
          expect(markup).toContain('caos-bars-host');
          const grouped = props.find((p) => p.data.some((d) => d.group));
          expect(grouped, 'a grouped chart').toBeDefined();
          const want = o.comparison.rows.flatMap((r) => [
            { seg: r.segment_id, tone: 'accent', v: r.cmf_b1_provision },
            { seg: r.segment_id, tone: 'warn', v: r.ifrs9_provision },
            { seg: r.segment_id, tone: 'good', v: r.bde_annex9_provision },
          ]);
          expect(grouped!.data).toHaveLength(want.length);
          grouped!.data.forEach((d, i) => {
            expect(d.group?.id).toBe(want[i].seg);
            expect(d.tone).toBe(want[i].tone);
            expect(d.value).toBeCloseTo(want[i].v / M, 9);
            expect(d.label[lang].length).toBeGreaterThan(0);
            expect(d.group!.label[lang].length).toBeGreaterThan(0);
          });
          expect(grouped!.legend?.map((l) => l.tone)).toEqual(['accent', 'warn', 'good']);
          expect(grouped!.legend?.every((l) => l.label.en && l.label.es)).toBe(true);
          expect(typeof grouped!.onSelect).toBe('function');
          // the table beside it keeps every provision, in the language
          if (View === SegmentsView) for (const r of o.comparison.rows) expect(textOf(markup)).toContain(money(r.ifrs9_provision, lang, o.comparison.currency));
        }
      });

      it(`${id}, ${lang}: the bridge is a floating BarChart that closes on the IFRS 9 total, the totals as dots off zero`, () => {
        const s = selOf(id);
        const o = outputsOf(s)!;
        const b = o.gap_bridge;
        const from = o.regimes.find((r) => r.regime === b.from_regime)!;
        const to = o.regimes.find((r) => r.regime === b.to_regime)!;
        const { markup, props } = charts(() => render(<BridgeView sel={s} />, lang));
        expect(markup).not.toContain('ct-map-stage');
        expect(markup).toContain('caos-bars-host');
        expect(markup).toContain('data-closes="true"');
        const chart = props.find((p) => p.data.some((d) => d.span));
        expect(chart, 'a floating chart').toBeDefined();
        const d = chart!.data;
        expect(d).toHaveLength(b.steps.length + 2);
        expect(d[0].id).toBe('from');
        expect(d[0].value).toBeCloseTo(from.total_provision / M, 9);
        expect(d[0].span![0]).toBeCloseTo(from.total_provision / M, 9);
        expect(d[0].span![1]).toBeCloseTo(from.total_provision / M, 9);
        expect(d[0].tone).toBe('accent');
        let run = from.total_provision / M;
        b.steps.forEach((st, i) => {
          const x = d[i + 1];
          expect(x.id).toBe(st.id);
          expect(x.value).toBeCloseTo(st.amount / M, 9);
          expect(x.span![0]).toBeCloseTo(run, 9);
          run += st.amount / M;
          expect(x.span![1]).toBeCloseTo(run, 9);
          expect(x.tone).toBe(st.amount >= 0 ? 'bad' : 'good');
          expect(x.label[lang]).toBe(st.label[lang]);
        });
        const last = d[d.length - 1];
        expect(last.id).toBe('to');
        expect(last.value).toBeCloseTo(to.total_provision / M, 9);
        expect(last.span![0]).toBeCloseTo(last.span![1], 12);
        expect(last.tone).toBe('warn');
        // the bridge closes: the from-total plus the steps is the to-total
        expect(run).toBeCloseTo(to.total_provision / M, 6);
        // the axis does not start at zero and holds every end
        const range = chart!.axis.range!;
        expect(range[0]).toBeGreaterThan(0);
        const ends = d.flatMap((x) => x.span!);
        expect(Math.min(...ends)).toBeGreaterThanOrEqual(range[0]);
        expect(Math.max(...ends)).toBeLessThanOrEqual(range[1]);
        expect(typeof chart!.onSelect).toBe('function');
        // the table keeps every step in the language
        for (const st of b.steps) expect(textOf(markup)).toContain(money(st.amount, lang, b.currency));
      });
    }
  }
});
