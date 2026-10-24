// U16-F2 (the R2 fix round, C04), on the committed documents: ESMA's attribution in Spanish in the Spanish view with the source
// name verbatim (ruling of 2026-10-22), the short reference labels, the five-year window axis, and the tables beside the semester charts.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { committedData, render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { SemestersView } from './AgencyTestsViews';
import { DefinitionsView, LifetimeView } from './AgencyValidationViews';
import { attributionIn, cerepSource, makeSel, type AgencyVariant } from './selection';
import { pValueChart } from './C04Common';

const captured = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return {
    ...mod,
    UPlotChart: (p: UPlotChartProps) => {
      captured.push(p);
      return mod.UPlotChart(p);
    },
  };
});

const EN = 'Source: ESMA CEREP; tables transformed by Contraste';
const ES = 'Fuente: ESMA CEREP; tablas transformadas por Contraste';
const sp = () => committedData('C04', 'sp');
const outputs = () => (sp().variant as unknown as AgencyVariant).outputs;

describe('U16-F2 C04', () => {
  afterEach(() => setLang('en'));

  it('PR-C04: the attribution is Spanish in the Spanish view, the source name verbatim, and English as declared in English', () => {
    expect(attributionIn(EN, 'en')).toBe(EN);
    expect(attributionIn(EN, 'es')).toBe(ES);
    expect(attributionIn('Another attribution', 'es')).toBe('Another attribution');
    expect(outputs().attribution).toBe(EN);                                // the document keeps the registry's own wording
    expect(cerepSource(outputs(), 'es')).toContain(ES);
    expect(cerepSource(outputs(), 'es')).not.toContain('Source:');
    expect(cerepSource(outputs(), 'en')).toContain(EN);
  });

  it('PR-C04: a Spanish view carries the Spanish attribution and no English one', () => {
    const markup = textOf(render(<DefinitionsView sel={makeSel(sp())} />, 'es'));
    expect(markup).toContain(ES);
    expect(markup).not.toContain('tables transformed by Contraste');
  });

  it('V04-1 and R2b c05 M1: the reference line of the ratio to D2 carries no label, so it never covers the curves', () => {
    captured.length = 0;
    render(<DefinitionsView sel={makeSel(sp())} />, 'en');
    const marks = captured.flatMap((p) => p.yMarks ?? []);
    expect(marks.some((m) => m.y === 1)).toBe(true);
    // a short label still covered the D3/D2 line at CCC-C; the note says what the dotted line at 1 is
    for (const m of marks.filter((x) => x.y === 1)) expect(m.label, JSON.stringify(m)).toBeUndefined();
  });

  it('V04-3: the five-year window axis names the number only, the windows are listed in the note', () => {
    captured.length = 0;
    const es = textOf(render(<LifetimeView sel={makeSel(sp())} />, 'es'));
    const p = captured.at(0)!;
    expect((p.x.label as { es: string }).es.length).toBeLessThanOrEqual(36);
    expect(es).toContain('Ventanas: 1 ');
  });

  it('V04-4: the semester charts keep a table of the numbers they draw', () => {
    const markup = render(<SemestersView sel={makeSel(sp(), { grade: 3 })} />, 'en');
    expect(markup).toContain('data-table="semesters-l1"');
    expect(markup).toContain('data-table="semesters-pd"');
  });

  it('V04-2: the threshold labels of the p-value chart are short', () => {
    const chart = pValueChart([{ cited: { kind: 'test', row: { test_id: 'x', p_value: 0.2, alpha_amber: 0.05, alpha_red: 0.01, policy_version: 'p', segment: null, extras: {}, statistic: 1 } } } as never]);
    const labels = (chart?.yMarks ?? []).map((m) => (m.label as { en: string }).en);
    expect(labels).toEqual(['Amber 0.05', 'Red 0.01']);
  });
});
