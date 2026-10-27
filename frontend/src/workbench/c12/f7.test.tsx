// U16-F7 (the U16-R2 capture review, batch b06, C12): the minors of the counterparty views, read on the committed documents.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { VariantArtifact } from '../../lib/contract.types';
import { setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { C12ContextView, C12TestsView } from './C12Common';
import { PitView } from './BacktestViews';
import { CvaView, WwrView } from './CreditViews';
import { ProfileView } from './ExposureViews';
import { GirrView, SaCcrView } from './RegulatoryViews';
import { defaultSel, segmentText, type C12Sel, type Peers } from './selection';

const bars = vi.hoisted(() => [] as BarChartProps[]);
const narrowNow = vi.hoisted(() => ({ on: false }));
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => { bars.push(p); return mod.BarChart(p); } };
});
vi.mock('../../lib/useMedia', () => ({ useMedia: () => narrowNow.on, useFindingsShares: () => [2, 1] }));

const title = { en: 'Counterparty credit risk', es: 'Riesgo de crédito de contraparte' };
const MODELS = 'models-hw1f-treasury-2000-2025.json';
const NAMES = ['single-swap', 'netting-set', 'csa-mpor-10d', 'csa-mpor-20d', 'with-im', 'wrong-way-risk'];
const data = (name: string) => committedData('C12', `${name}.json`, MODELS, title);
const peers: Peers = Object.fromEntries(
  NAMES.map((n) => {
    const d = committed<VariantArtifact>('C12', `${n}.json`);
    return [n, { variantId: d.variant_id, title: { en: n, es: n }, o: d.outputs }];
  }),
) as unknown as Peers;
const sel = (name: string, patch: Partial<C12Sel> = {}): C12Sel => ({ ...(defaultSel(data(name), peers) as C12Sel), ...patch });

describe('U16-F7 C12 (b06 minors)', () => {
  afterEach(() => { setLang('en'); narrowNow.on = false; bars.length = 0; });

  it('m1: the GIRR bars plot the table\'s whole dollars, never floating noise like 5.685E-8', () => {
    view(<GirrView sel={sel('netting-set')} />);
    const g = bars.find((b) => /Weighted sensitivities/.test(String((b.title as { en: string }).en)))!;
    const raw = (committed<VariantArtifact>('C12', 'netting-set.json').outputs as any).girr.weighted_sensitivities as number[];
    expect(raw.some((v) => v !== 0 && Math.abs(v) < 0.5)).toBe(true);
    const values = g.data.map((d) => d.value ?? 0);
    raw.forEach((r, i) => { if (Math.abs(r) < 0.5) expect(values[i], `tenor ${i}`).toBe(0); });
    expect(values.every((v) => !Object.is(v, -0))).toBe(true);
  });

  it('m2: the wrong-way note says the ORE limit once, and names the variant when the sweep is drawn from another', () => {
    const text = view(<WwrView sel={sel('netting-set')} />);
    expect(text.match(/no ORE reconciliation/g) ?? [], text.slice(0, 700)).toHaveLength(1);
    expect(text).toMatch(/Wrong-way variant:/);
    const own = view(<WwrView sel={sel('wrong-way-risk')} />);
    expect(own.match(/no ORE reconciliation/g) ?? []).toHaveLength(1);
    expect(own).not.toMatch(/Wrong-way variant:/);
    setLang('es');
    const es = view(<WwrView sel={sel('netting-set')} />);
    expect(es.match(/no tiene conciliación con ORE/g) ?? []).toHaveLength(1);
    expect(es).toMatch(/Variante de correlación adversa:/);
  });

  it('m3: the tests table names the segment of every row, so no two rows read alike', () => {
    expect(segmentText('book-10bd-q90', 'en')).toBe('Book, 10 business days, quantile 90 %'); // R4 c15 n5: a no-break space before the sign
    expect(segmentText('risk factor-10bd', 'es')).toBe('Tasa, 10 días hábiles');
    const doc = committed<VariantArtifact>('C12', 'netting-set.json');
    const rows = [...view(<C12TestsView sel={sel('netting-set')} />).matchAll(/(PIT|exceedance)[^|]{0,80}/gi)];
    expect(rows.length).toBeGreaterThan(0);
    const text = view(<C12TestsView sel={sel('netting-set')} />);
    expect(doc.tests.filter((t) => t.segment).length).toBeGreaterThan(10);
    expect((text.match(/Book, 10 business days/g) ?? []).length).toBeGreaterThanOrEqual(2);
    expect(text).toMatch(/Rate, 10 business days/);
    expect(text).not.toMatch(/Reason or note/);
  });

  it('m6: the Spanish words: the live replica, the standard error spelled out, one first year', () => {
    setLang('es');
    const a = view(<SaCcrView sel={sel('netting-set')} />);
    expect(a).not.toMatch(/puerto/);
    expect(a).toMatch(/réplica en vivo/);
    for (const V of [ProfileView, CvaView]) expect(view(<V sel={sel('netting-set')} />)).not.toMatch(/\bES de Monte Carlo/);
    expect(view(<ProfileView sel={sel('netting-set')} />)).toMatch(/error estándar de Monte Carlo/);
    const one = sel('netting-set');
    const doc = structuredClone(one.data.variant) as any;
    doc.outputs.exposure.eepe_horizon_years = 1;
    const mini = { ...one, data: { ...one.data, variant: doc } } as C12Sel;
    expect(view(<ProfileView sel={mini} />)).toMatch(/primer año/);
    expect(view(<ProfileView sel={mini} />)).not.toMatch(/primeros 1 años/);
  });

  it('m7: the context does not end the title with "?." and writes the named parameters without a doubled unit', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const text = view(<C12ContextView sel={sel('netting-set')} />);
      expect(text, lang).not.toMatch(/\?\./);
      expect(text).not.toMatch(/receiver payer or receiver|receptor pagador o receptor/);
      expect(text).not.toMatch(/10 bp rule|10 pb regla/);
      expect(text).not.toMatch(/SW-1 trade id|SW-1 identificador/);
    }
  });

  it('m10: at a phone width the PIT classes are named by their lower edge', () => {
    narrowNow.on = true;
    view(<PitView sel={sel('netting-set')} />);
    const b = bars.find((x) => /PIT class/.test(String((x.title as { en: string }).en)))!;
    expect(b.data.map((d) => (d.label as { en: string }).en)).toEqual(['0.0', '0.1', '0.2', '0.3', '0.4', '0.5', '0.6', '0.7', '0.8', '0.9']);
  });

  it('m12: with RC = 0 the live SA-CCR says the PFE line lies under the EAD line', () => {
    const text = view(<SaCcrView sel={sel('netting-set')} />);
    expect(text).toMatch(/PFE line lies under the EAD line/);
    setLang('es');
    expect(view(<SaCcrView sel={sel('netting-set')} />)).toMatch(/la línea del PFE queda bajo la del EAD/);
  });
});
