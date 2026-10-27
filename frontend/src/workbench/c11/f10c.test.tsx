// U16-F10c (R3 batch c12, C11): the reasons the producer now writes without a plan-unit code or a decision id read in Spanish on the
// Spanish page (B2), the Spanish page writes the words the view owns in Spanish (no "Backtest"), and the minors of the batch: one day
// is "1 día", the refits say they count both tail levels, the Z2 panel names no colour its marks do not carry, the expected count is
// written as in its table, the FZ0 hint keeps one gender, the titles do not capitalise a model name inside a sentence, the traffic
// light's axis starts at 0, a window with nothing to draw shows no empty stage, the MAR32.9 caption and the rung sources are Spanish,
// and the tables take the room under a drawing of fixed height. Reads the committed documents, in both languages.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { C11ContextView, C11VariantsTable, ModelReadout, TestReadout } from './C11Common';
import { ChampionView, DmView } from './ComparisonViews';
import { TimelineView, ZonesView } from './ExceedanceViews';
import { EsBacktestView, TestsView } from './BacktestViews';
import { useInstrument } from './instrument';
import { defaultSel, reasonText, rungSourceText, type C11Outputs, type C11Sel } from './selection';

const bars = vi.hoisted(() => [] as BarChartProps[]);
const lines = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => (bars.push(p), mod.BarChart(p)) };
});
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return { ...mod, UPlotChart: (p: UPlotChartProps) => (lines.push(p), mod.UPlotChart(p)) };
});

const TITLE = { en: 'Market VaR and ES back-testing', es: 'Pruebas retrospectivas de VaR y ES de mercado' };
const WINDOWS = ['calm-2004-06', 'equity-2007-09', 'equity-2020', 'fx-2008', 'mixed-2023', 'rates-2022'];
const selOf = (w: string) => defaultSel(committedData('C11', `${w}.json`, 'models-ladder.json', TITLE)) as C11Sel;

/** A committed window with every Spanish text the producer wrote blanked: what a Spanish view still prints is its own. */
function viewWordsOnly(w: string) {
  const blank = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(blank);
    if (x && typeof x === 'object') {
      const o = x as Record<string, unknown>;
      if (typeof o.en === 'string' && typeof o.es === 'string') return { ...o, es: '·' };
      return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, blank(v)]));
    }
    return x;
  };
  return defaultSel(fixtureData('C11', blank(committed<VariantArtifact>('C11', `${w}.json`)) as VariantArtifact, blank(committed<ModelsArtifact>('C11', 'models-ladder.json')) as ModelsArtifact, TITLE)) as C11Sel;
}
function Rail({ sel }: { sel: C11Sel }) {
  const inst = useInstrument(sel.data, () => undefined);
  return <div>{inst ? inst.rail.map((r) => <section key={r.id}>{r.content}</section>) : null}</div>;
}
function Tabs({ sel }: { sel: C11Sel }) {
  const inst = useInstrument(sel.data, () => undefined);
  return <div>{inst ? inst.groups.filter((g) => g.id !== 'findings').map((g) => <section key={g.id}>{g.content}</section>) : null}</div>;
}

describe('U16-F10c, C11 (R3 c12)', () => {
  afterEach(() => setLang('en'));

  it('B2: the reasons the producer writes now (no "U8 bake", no decision id) read in Spanish', () => {
    const cases: Array<[string, string]> = [
      ['challenger only: it must enter the 90 percent MCS on FZ0 out of sample, and the published run does not train it', 'solo retador: debe entrar al MCS de 90 por ciento sobre FZ0 fuera de muestra, y la corrida publicada no lo entrena'],
      ['fewer than 250 forecast days (104): the Basel traffic light of MAR32.9 is defined on 250 observations and the window has no lead-in', 'menos de 250 días de pronóstico (104): el semáforo de Basilea de MAR32.9 se define sobre 250 observaciones y la ventana no tiene período previo'],
      ['no model is eligible: every model fails at least one gate', 'ningún modelo es elegible: cada modelo falla al menos una compuerta'],
    ];
    for (const [en, es] of cases) {
      expect(reasonText(en, 'en')).toBe(en);
      expect(reasonText(en, 'es')).toBe(es);
    }
    // the committed reason keeps its translation until the integrator re-bakes the ladder, and no plan-unit code reaches the Spanish page
    const ladder = committed<ModelsArtifact>('C11', 'models-ladder.json');
    const patched = structuredClone(ladder) as unknown as { fit: { ladder: Array<{ not_run_reason: string | null }> } };
    for (const r of patched.fit.ladder) if (r.not_run_reason) r.not_run_reason = cases[0][0];
    setLang('es');
    const ctx = view(<C11ContextView sel={defaultSel(fixtureData('C11', committed<VariantArtifact>('C11', 'rates-2022.json'), patched as unknown as ModelsArtifact, TITLE))} />);
    expect(ctx).toContain('la corrida publicada no lo entrena');
    expect(ctx).not.toMatch(/\bU\d+\b/);
  });

  it('the Spanish page writes the words the view owns in Spanish: no Backtest', () => {
    setLang('es');
    for (const w of ['rates-2022', 'calm-2004-06']) {
      const sel = viewWordsOnly(w);
      const own = [<Tabs key="t" sel={sel} />, <Rail key="r" sel={sel} />, <TestsView key="b" sel={sel} />, <EsBacktestView key="e" sel={sel} />, <TestReadout key="tr" sel={sel} />]
        .map((el) => view(el))
        .join(' ');
      expect(own, w).not.toMatch(/\bback-?tests?\b/i);
    }
  });

  it('m2: one day is "1 día", never "1 días"', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const ctx = view(<C11ContextView sel={selOf('rates-2022')} />);
      expect(ctx).not.toMatch(lang === 'es' ? /\b1 días\b/ : /\b1 days\b/);
    }
  });

  it('m12: the refits column says it counts both tail levels', () => {
    expect(view(<C11ContextView sel={selOf('rates-2022')} />)).toContain('Refits here, both tail levels');
    setLang('es');
    expect(view(<C11ContextView sel={selOf('rates-2022')} />)).toContain('Reajustes aquí, ambos niveles de cola');
  });

  it('m13: the Z2 panel names the zone each critical value bounds, not a colour its marks do not carry', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const sel = { ...selOf('rates-2022'), alpha: 0.025 } as C11Sel;
      const z = view(<EsBacktestView sel={sel} />);
      expect(z).not.toMatch(/critical value \((yellow|red)\)|crítico del modelo al [\d,]+ % \((amarillo|rojo)\)/);
    }
  });

  it('m15: the expected count of a window is written with two decimals on its bar, as in its table', () => {
    const variants = WINDOWS.map((id) => ({ id, title: { en: id, es: id }, v: committed<VariantArtifact<C11Outputs>>('C11', `${id}.json`) }));
    bars.length = 0;
    html(<C11VariantsTable variants={variants} onPick={() => undefined} current="calm-2004-06" />);
    const expected = bars.at(-1)!.data.filter((d) => d.id.endsWith('-expected'));
    expect(expected.length).toBe(WINDOWS.length);
    for (const d of expected) expect(d.format, d.id).toEqual({ decimals: 2 });
  });

  it('m16: the FZ0 hint of the rail keeps the gender of the tables ("FZ0 no está definida")', () => {
    setLang('es');
    for (const w of WINDOWS) {
      const sel = selOf(w);
      const o = sel.data.variant.outputs as unknown as C11Outputs;
      const m = o.models.find((x) => x.by_level.some((l) => l.fz0_reason));
      if (!m) continue;
      const markup = html(<ModelReadout sel={{ ...sel, model: m.model_id, alpha: m.by_level.find((l) => l.fz0_reason)!.alpha as C11Sel['alpha'] }} />);
      expect(markup).not.toContain('FZ0 no está definido');
      expect(markup).toContain('FZ0 no está definida');
      return;
    }
  });

  it('m18: a title names its model after a colon, never as a capitalised word inside a sentence', () => {
    const t = view(<TestsView sel={selOf('rates-2022')} />);
    expect(t).not.toMatch(/Back-tests of [A-Z]/);
    expect(view(<TimelineView sel={selOf('rates-2022')} />)).not.toMatch(/VaR and ES of [A-Z]/);
  });

  it('m8: the traffic light axis starts at 0, so a count of 5 is not on the bottom edge', () => {
    lines.length = 0;
    html(<ZonesView sel={selOf('fx-2008')} />);
    const p = lines.at(-1)!;
    expect(p.y.range?.[0]).toBe(0);
  });

  it('m3: a window with no traffic light draws no empty stage; it states its reason', () => {
    const markup = html(<ZonesView sel={selOf('equity-2020')} />);
    expect(markup).not.toContain('ct-stack-chart');
    expect(markup).toContain('data-state="unavailable"');
    const dm = html(<DmView sel={selOf('equity-2007-09')} />);
    expect(dm).not.toContain('ct-stack-chart');
  });

  it('m11: the MAR32.9 caption and the rung sources are written in Spanish; the citations stay', () => {
    setLang('es');
    expect(view(<ZonesView sel={selOf('fx-2008')} />)).toContain('Tabla 1 de MAR32.9');
    expect(rungSourceText('Patton, Ziegel and Chen 2019, J. Econometrics 211(2), eq 27', 'es')).toBe('Patton, Ziegel y Chen 2019, J. Econometrics 211(2), ec. 27');
    expect(rungSourceText('arXiv 2606.04576 (preprint; challenger only)', 'es')).toBe('arXiv 2606.04576 (preimpresión; solo retador)');
    expect(rungSourceText('historical simulation (textbook; Pritsker 2001)', 'es')).toBe('simulación histórica (libro de texto; Pritsker 2001)');
  });

  it('m1: the back-test, champion, DM and Variants tables take the room under a drawing of fixed height', () => {
    const variants = WINDOWS.map((id) => ({ id, title: { en: id, es: id }, v: committed<VariantArtifact<C11Outputs>>('C11', `${id}.json`) }));
    for (const markup of [html(<TestsView sel={selOf('rates-2022')} />), html(<ChampionView sel={selOf('rates-2022')} />), html(<DmView sel={selOf('rates-2022')} />), html(<C11VariantsTable variants={variants} onPick={() => undefined} current="rates-2022" />)]) {
      expect(markup).toContain('ct-stack-rest');
      expect(markup).not.toContain('ct-stack-table');
    }
  });
});
