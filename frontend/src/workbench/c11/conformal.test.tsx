// BS-16 (method tiers): the views of the adaptive conformal recalibration. They draw what `outputs.conformal` carries and nothing the document
// lacks: the wrapped VaR, the ladder's own VaR beside it, a point on each exceedance of the wrapped VaR, the scores of the wrapped and the
// unwrapped run, and the hypothesis with its measured cells and its verdict, whether it holds or not. The committed windows are read in both
// languages; the fixture holds one wrapped model, the committed documents three.
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, setLang } from '../c03/u6-testkit';
import { committed, committedData } from '../c08/spanish-testkit';
import { C11ContextView } from './C11Common';
import { ConformalVerdictView, ConformalView, wrappedFocus } from './ConformalViews';
import { useInstrument } from './instrument';
import { defaultSel, outputsOf, type C11Sel } from './selection';

type Outputs = components['schemas']['c11Outputs'];

const lines = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (lines.push(p), mod.UPlotChart(p)) };
});

const TITLE = { en: 'Market VaR and ES back-testing', es: 'Pruebas retrospectivas de VaR y ES de mercado' };
const WINDOWS = ['calm-2004-06', 'equity-2007-09', 'equity-2020', 'fx-2008', 'mixed-2023', 'rates-2022'];
const WRAPPED = ['hs-250', 'garch-t', 'fhs'];
const selOf = (w: string) => defaultSel(committedData('C11', `${w}.json`, 'models-ladder.json', TITLE)) as C11Sel;
const fixture = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(`../../../../docs/contracts/fixtures/c11/${rel}`, import.meta.url), 'utf8')) as T;
const fixtureSel = (): C11Sel => {
  const data = fixtureData('C11', fixture<VariantArtifact>('variant-window-fixture.json'), fixture<ModelsArtifact>('models-fixture.json'), TITLE);
  return defaultSel(data) as C11Sel;
};
const values = (c: UPlotChartProps, label: string) => c.series.find((s) => (s.label as { en: string }).en === label)?.values;

describe('BS-16, the conformal views on the fixture', () => {
  afterEach(() => setLang('en'));

  it('draws the wrapped VaR, the unwrapped VaR of the ladder and the exceedances of the wrapped VaR as the document gives them', () => {
    const base = fixtureSel();
    const o = outputsOf(base) as Outputs;
    for (const alpha of [0.01, 0.025] as const) {
      lines.length = 0;
      const markup = html(<ConformalView sel={{ ...base, alpha, model: 'hs-250' }} />);
      const row = o.conformal!.rows.find((r) => r.model_id === 'hs-250' && r.alpha === alpha)!;
      const own = o.models.find((m) => m.model_id === 'hs-250')!.by_level.find((l) => l.alpha === alpha)!;
      const c = lines[0];
      expect(values(c, 'VaR, wrapped')).toEqual(row.series.var);
      expect(values(c, 'VaR, unwrapped')).toEqual(own.var);
      const pts = values(c, 'Exceedance of the wrapped VaR')!;
      expect(pts.filter((v) => v !== null).length).toBe(row.wrapped.n_exceedances);
      expect(markup).toContain(`data-row="hs-250-wrapped"`);
      expect(markup).toContain(`data-row="hs-250-unwrapped"`);
      expect(markup).not.toMatch(/NaN|undefined|Infinity/);
    }
  });

  it('a model that is not wrapped draws the first wrapped model and says so', () => {
    const base = fixtureSel();
    const conf = (outputsOf(base) as Outputs).conformal!;
    expect(wrappedFocus(conf, 'ewma-094')).toBe('hs-250');
    expect(html(<ConformalView sel={{ ...base, model: 'ewma-094' }} />)).toContain('is not wrapped');
    expect(html(<ConformalView sel={null} />)).toContain('data-state="loading"');
  });

  it('a window without the block says so instead of drawing an empty stage', () => {
    const base = fixtureSel();
    const bare = structuredClone(base.data) as typeof base.data;
    (bare.variant as unknown as { outputs: Outputs }).outputs.conformal = null;
    const sel = { ...base, data: bare };
    expect(html(<ConformalView sel={sel} />)).toContain('data-state="unavailable"');
    expect(html(<ConformalVerdictView sel={sel} />)).toContain('data-state="unavailable"');
  });
});

describe('BS-16, the committed windows', () => {
  afterEach(() => setLang('en'));

  it('every committed window carries three wrapped models at two levels and the same verdict', () => {
    const verdicts = new Set<string>();
    for (const w of WINDOWS) {
      const conf = (outputsOf(selOf(w)) as Outputs).conformal;
      expect(conf, w).not.toBeNull();
      expect(conf!.rows.map((r) => `${r.model_id}@${r.alpha}`).sort(), w).toEqual(WRAPPED.flatMap((m) => [`${m}@0.01`, `${m}@0.025`]).sort());
      verdicts.add(JSON.stringify(conf!.hypothesis));
    }
    expect(verdicts.size).toBe(1);
  });

  it('the verdict view states the measured counts and the refutation test in both languages', () => {
    const sel = selOf('equity-2007-09');
    const h = (outputsOf(sel) as Outputs).conformal!.hypothesis;
    const en = html(<ConformalVerdictView sel={sel} />);
    expect(en).toContain(`data-holds="${h.holds}"`);
    expect(en).toContain(h.verdict.en.replace(/&/g, '&amp;'));
    for (const c of h.cells) expect(en).toContain(`data-cell="${c.model_id}-${c.alpha}"`);
    expect(en.match(/data-independence=/g)?.length).toBe(6);
    setLang('es');
    const es = html(<ConformalVerdictView sel={selOf('equity-2007-09')} />);
    expect(es).toContain('Se refuta si');
    expect(es).toContain(h.verdict.es.replace(/&/g, '&amp;'));
    expect(es).not.toMatch(/NaN|undefined|Infinity|Windows passed/);
  });

  it('the wrapped view of each committed window draws the path of the model in focus in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      for (const w of WINDOWS) {
        const base = selOf(w);
        for (const m of WRAPPED) {
          lines.length = 0;
          const markup = html(<ConformalView sel={{ ...base, model: m }} />);
          const row = (outputsOf(base) as Outputs).conformal!.rows.find((r) => r.model_id === m && r.alpha === base.alpha)!;
          const label = lang === 'en' ? 'VaR, wrapped' : 'VaR, envuelto';
          const c = lines[0];
          expect(c.series.find((s) => (s.label as { en: string; es: string })[lang] === label)?.values, `${w} ${m}`).toEqual(row.series.var);
          expect(markup, `${w} ${m}`).toContain('data-table="c11-conformal"');
          expect(markup).not.toMatch(/NaN|undefined|Infinity/);
        }
      }
    }
  });

  it('the ladder card of the Context view carries the beyond-tier row, named in both languages', () => {
    const sel = selOf('rates-2022');
    expect(html(<C11ContextView sel={sel} />)).toContain('data-rung="BS-16"');
    expect(html(<C11ContextView sel={sel} />)).toContain('Adaptive conformal recalibration of the VaR');
    setLang('es');
    expect(html(<C11ContextView sel={selOf('rates-2022')} />)).toContain('Recalibración conforme adaptativa del VaR');
  });

  it('the Comparison group lists the two conformal tabs', () => {
    function Names() {
      const inst = useInstrument(selOf('rates-2022').data, () => undefined);
      return <div>{inst ? inst.groups.find((g) => g.id === 'comparison')?.content : null}</div>;
    }
    const markup = html(<Names />);
    expect(markup).toContain('Conformal recalibration');
    expect(markup).toContain('Conformal hypothesis');
    expect(committed<VariantArtifact>('C11', 'rates-2022.json')).toBeTruthy();
  });
});
