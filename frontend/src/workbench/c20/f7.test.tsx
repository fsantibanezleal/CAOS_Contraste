// U16-F7 (the U16-R2 capture review, batch b09, C20): the minors of the ML-validation views, read on the committed documents.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { committedDoc, fixtureData, html, setLang, visibleText } from '../c14/testkit';
import { C20VariantsTable } from './C20Common';
import { useC20Instrument } from './instrument';
import { defaultSel, type C20Sel } from './selection';
import { SyntheticShiftView } from './ShiftViews';
import { DegradationView } from './ShockViews';

const bars = vi.hoisted(() => [] as BarChartProps[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => { bars.push(p); return mod.BarChart(p); } };
});

const models = committedDoc<ModelsArtifact>('C20', 'models-c20-ladder');
const title = { en: 'ML model validation', es: 'Validación de modelos de ML' };
const data = (name: string) => fixtureData('C20', committedDoc<VariantArtifact>('C20', name), models, title);
const selOf = (name: string): C20Sel => defaultSel(data(name)) as C20Sel;
const NAMES = ['sgcd-held-out', 'sgcd-seen', 'fed-shift', 'leakage-planted', 'perturbation-grid', 'seed-sweep'];

function Groups({ name }: { name: string }) {
  const inst = useC20Instrument(data(name), () => undefined);
  return <div>{inst ? inst.groups.map((g) => g.content) : 'none'}</div>;
}

describe('U16-F7 C20 (b09 minors)', () => {
  afterEach(() => { setLang('en'); bars.length = 0; });

  it('m4: the Spanish note of the applied shocks writes "semilla 42", not "seed 42"', () => {
    setLang('es');
    const text = visibleText(html(<DegradationView sel={selOf('sgcd-seen')} />));
    expect(text).toContain('semilla 42');
    expect(text).not.toMatch(/seed 42/);
    setLang('en');
    expect(visibleText(html(<DegradationView sel={selOf('sgcd-seen')} />))).toContain('seed 42');
  });

  it('m9: a bar of zero change is a plain zero: no bar of the AUC-loss charts carries a negative zero', () => {
    for (const name of ['sgcd-seen', 'sgcd-held-out', 'fed-shift']) {
      bars.length = 0;
      html(<DegradationView sel={selOf(name)} />);
      html(<SyntheticShiftView sel={selOf(name)} />);
      for (const b of bars) for (const d of b.data) expect(Object.is(d.value, -0), `${name} ${d.id}`).toBe(false);
    }
  });

  it('m10: the variants table prints the number its bar draws, one measure and one sign per row', () => {
    const variants = NAMES.map((n) => ({ id: n, title: { en: n, es: n }, v: committedDoc<VariantArtifact>('C20', n) as never }));
    const markup = html(<C20VariantsTable variants={variants} onPick={() => undefined} current="sgcd-seen" />);
    const chart = bars.find((b) => /Largest AUC loss by variant/.test((b.title as { en: string }).en))!;
    expect(chart.data.length).toBeGreaterThan(0);
    for (const d of chart.data) {
      const row = markup.split(`data-variant="${d.id}"`)[1].split('</tr>')[0];
      const cells = [...row.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((m) => m[1].replace(/<[^>]*>/g, ''));
      const shown = Number(cells[cells.length - 1]);
      expect(shown, String(d.id)).toBeCloseTo(d.value as number, 3);
      expect(shown, String(d.id)).toBeGreaterThanOrEqual(0);
    }
    expect(markup).toContain('Largest AUC loss over the noise scales');
  });

  it('m12: the unavailable message names the variants that carry the views', () => {
    setLang('en');
    expect(visibleText(html(<Groups name="sgcd-seen" />))).toContain('pick Noise, Seeds or Leakage for these views');
    setLang('es');
    expect(visibleText(html(<Groups name="sgcd-seen" />))).toContain('elija Ruido, Semillas o Fuga');
  });
});
