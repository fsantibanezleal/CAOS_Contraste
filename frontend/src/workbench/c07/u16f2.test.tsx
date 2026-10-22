// U16-F2 (the R2 fix round, C07), on the committed documents: the Anejo 9 header and the truth status in Spanish, the B-1 reason said once,
// the table captions and axis ids in words, the bars never narrower than a pixel and each with a readout.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { committedData, render, textOf, variantIds } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { C07ContextView, C07VariantsTable } from './C07Common';
import { B1View, SegmentsView, ThreeRegimeView } from './RegimeViews';
import { TablesView } from './ValidationViews';
import { defaultSel, type C07Sel } from './selection';
import type { VariantArtifact } from '../../lib/contract.types';
import type { components } from '../../lib/contract.gen';

const bars = vi.hoisted(() => [] as Array<{ data: Array<{ value: number | null }>; axis: { label: { es: string } } }>);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: never) => (bars.push(p), mod.BarChart(p)) };
});

const ids = variantIds('C07');
const selOf = (id: string) => defaultSel(committedData('C07', id)) as C07Sel;

describe('U16-F2 C07', () => {
  afterEach(() => setLang('en'));

  it('V07-2: the Spanish views write the BdE annex and the truth status in Spanish', () => {
    const s = selOf('base');
    const es = [render(<ThreeRegimeView sel={s} />, 'es'), render(<SegmentsView sel={s} />, 'es'), render(<C07ContextView sel={s} />, 'es')].join(' ');
    expect(es).not.toContain('BdE Annex 9');
    expect(es).not.toContain('synthetic-calibrated');
    expect(textOf(es)).toContain('Anejo 9 del BdE');
    expect(textOf(es)).toContain('sintético, calibrado');
  });

  it('PR-C07-1 / M8: the reason the internal method is missing is said once under the table, in the language', () => {
    const s = selOf('base');
    const es = textOf(render(<B1View sel={s} />, 'es'));
    expect(es.split('no tiene método interno').length - 1).toBe(1);
    expect(es).not.toContain('has no internal method');
    const en = textOf(render(<B1View sel={s} />, 'en'));
    expect(en.split('has no internal method').length - 1).toBe(1);
  });

  it('V07-1: the B-1 tables carry a Spanish caption and no id of the document', () => {
    const es = render(<TablesView sel={selOf('base')} />, 'es');
    for (const raw of ['mortgage-pe', 'consumer-pi', 'mortgage-no-arrears', 'no-guarantee', 'CMF CNCB Chapter']) expect(es, raw).not.toContain(`>${raw}`);
    expect(textOf(es)).toContain('Capítulo B-1');
    expect(textOf(es)).toContain('sin garantía');
  });

  it('V07-3: the bars of the regime chart are never given a negative width (the stage has no width in a server render: the clamp is Math.max in the view)', () => {
    const markup = render(<ThreeRegimeView sel={selOf('base')} />, 'en');
    expect(markup).not.toMatch(/<rect[^>]* width="-/);
  });

  it('V07-4: the scenario bars are drawn in billions, not in full pesos', () => {
    type Out = components['schemas']['c07Outputs'];
    const variants = ids.filter((v) => !v.startsWith('models')).map((id) => {
      const v = committedData('C07', id).variant as unknown as VariantArtifact<Out>;
      return { id, title: { en: id, es: id }, v };
    });
    bars.length = 0;
    render(<C07VariantsTable variants={variants} onPick={() => undefined} current="base" />, 'es');
    const chart = bars.at(-1)!;
    expect(chart.axis.label.es).toBe('Total IFRS 9 (mil M CLP)');
    for (const d of chart.data) expect(d.value === null || Math.abs(d.value) < 1e6).toBe(true);
  });
});
