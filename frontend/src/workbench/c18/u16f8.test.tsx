// U16-F8 (D16-21, shell 0.19.0), on the committed C18 documents: the two waterfalls of the capital stack (the layers of the internal
// target with the effective equity against it, and the legal minimum stack) and the Euler allocation of the expected shortfall are the
// shell BarChart with floating bars. Each layer is a span from the running sum of the layers before it, its value the layer's size; a
// total and a reference bar span zero to the document's own figure. No C18 view draws its own <svg>.
import { readFileSync, readdirSync } from 'node:fs';
import { pick } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang } from '../c14/testkit';
import { PCT, cell } from './C18Common';
import { aggOf, axisOf, defaultSel, fitOf, outputsOf, type C18Sel } from './selection';
import { StackView } from './CapitalViews';
import { EulerView } from './AggregationViews';

type Datum = { id: string; label: { en: string; es: string }; value: number | null; tone?: string; span?: [number, number] };
type Props = { title: { en: string; es: string }; data: Datum[]; axis: { label: { en: string; es: string }; format?: { percent?: boolean; decimals?: number } } };
const bars = vi.hoisted(() => [] as Props[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: never) => (bars.push(p), mod.BarChart(p)) };
});

const models = committedDoc<ModelsArtifact>('C18', 'models-banco-andino');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
const selOf = (name: string): C18Sel => defaultSel(fixtureData('C18', committedDoc<VariantArtifact>('C18', name), models, title)) as C18Sel;
const SCENARIOS = ['baseline', 'eba-2025-adverse', 'fed-2026-severely-adverse', 'ngfs-delayed-transition'];
const AGGREGATION = [...SCENARIOS, 't-copula-baseline'];
const LANGS = ['en', 'es'] as const;

function charts(lang: 'en' | 'es', el: Parameters<typeof html>[0]): { markup: string; props: Props[] } {
  setLang(lang);
  bars.length = 0;
  const markup = html(el);
  return { markup, props: [...bars] };
}

/** The spans of consecutive layers chain from zero, each as long as its value. */
function expectChain(data: Datum[], sizes: number[]) {
  let run = 0;
  sizes.forEach((size, i) => {
    expect(data[i].value).toBeCloseTo(size, 12);
    expect(data[i].span![0]).toBeCloseTo(run, 12);
    run += size;
    expect(data[i].span![1]).toBeCloseTo(run, 12);
  });
}

describe('U16-F8 C18: the shell draws the waterfalls', () => {
  afterEach(() => setLang('en'));

  it('no C18 view draws its own <svg>, and the hand-drawn waterfall is gone', () => {
    const dir = new URL('./', import.meta.url);
    for (const f of readdirSync(dir).filter((x) => /\.tsx$/.test(x) && !/\.test\./.test(x))) {
      expect(readFileSync(new URL(f, dir), 'utf8'), f).not.toMatch(/<svg/);
    }
    expect(readFileSync(new URL('./Waterfall.tsx', dir), 'utf8')).not.toMatch(/HWaterfall|<Stage\b/);
  });

  for (const name of SCENARIOS) {
    for (const lang of LANGS) {
      it(`${name}, ${lang}: the capital stack is two floating BarCharts with the document's layers, the OI and the legal stack`, () => {
        const s = selOf(name);
        const o = outputsOf(s)!;
        const t = o.internal_capital_target;
        const { markup, props } = charts(lang, <StackView sel={s} />);
        expect(markup).not.toContain('ct-map-stage');
        expect(markup.split('caos-bars-host').length - 1).toBeGreaterThanOrEqual(2);
        const oi = props.find((p) => p.data.some((d) => d.id === 'min_pe'));
        expect(oi, 'the OI chart').toBeDefined();
        const sizes = [t.min_pe, t.c_dsib, t.c_p2.value, t.c_ccob, t.c_ccyb, t.c_d.value];
        expectChain(oi!.data, sizes);
        // c_P2 and c_d are case assumptions, drawn in the warning tone
        expect(oi!.data.map((d) => d.tone).slice(0, 6)).toEqual(['accent', 'accent', 'warn', 'accent', 'accent', 'warn']);
        const total = oi!.data.find((d) => d.id === 'oi')!;
        expect(total.value).toBeCloseTo(t.oi, 12);
        expect(total.span).toEqual([0, total.value]);
        // the effective equity against it: the document's ratios from zero
        const pe = oi!.data.find((d) => d.id === 'pe-start')!;
        expect(pe.value).toBeCloseTo(o.capital_start.pe_ratio, 12);
        expect(pe.span).toEqual([0, pe.value]);
        expect(oi!.axis.format?.percent).toBe(true);
        for (const d of oi!.data) expect(d.label[lang].length).toBeGreaterThan(0);
        // the legal stack carries the CET1 share of Pillar 2
        const fit = fitOf(s)!;
        const legal = props.find((p) => p.data.some((d) => d.id === 'cet1_min'));
        expect(legal, 'the legal chart').toBeDefined();
        const st = fit.bank_anchors.chilean_stack;
        expectChain(legal!.data, [st.cet1_min, st.c_ccob, st.c_ccyb, st.c_dsib, fit.named_parameters.reverse_p2_cet1.value ?? st.p2r]);
        // the table keeps every layer in the language
        for (const v of [...sizes, t.oi]) expect(markup).toContain(PCT(v, lang, 3));
      });
    }
  }

  for (const name of AGGREGATION) {
    for (const lang of LANGS) {
      it(`${name}, ${lang}: the Euler allocation is a floating BarChart of the contributions that ends in the aggregate expected shortfall`, () => {
        const s = selOf(name);
        const a = aggOf(s)!;
        const e = a.euler;
        const scale = axisOf([e.es_total_clp_m, ...e.allocation.map((x) => x.contribution_clp_m)]);
        const { markup, props } = charts(lang, <EulerView sel={s} />);
        expect(markup).not.toContain('ct-map-stage');
        expect(markup).toContain('caos-bars-host');
        const chart = props.find((p) => p.data.some((d) => d.id === 'total'));
        expect(chart, 'the Euler chart').toBeDefined();
        expectChain(chart!.data, e.allocation.map((x) => x.contribution_clp_m / scale.div));
        e.allocation.forEach((x, i) => expect(chart!.data[i].tone).toBe(x.risk === s.risk ? 'warn' : 'accent'));
        const total = chart!.data[chart!.data.length - 1];
        expect(total.id).toBe('total');
        expect(total.value).toBeCloseTo(e.es_total_clp_m / scale.div, 12);
        expect(total.span).toEqual([0, total.value]);
        expect(chart!.axis.label[lang]).toContain(pick(scale.unit, lang));
        for (const x of e.allocation) expect(markup).toContain(cell(x.contribution_clp_m, lang));
      });
    }
  }
});
