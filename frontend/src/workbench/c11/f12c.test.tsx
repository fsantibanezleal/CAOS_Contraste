// U16-F12c (R4 batch c14, C11): the Spanish champion and DM tables say "pérdida cuantílica", never "pérdida tick" (NB2); with the
// minors of the batch the view owns: the FZ0 reason in one gender in the tables and the rail (m16, n4), the MAR32.9 caption and the rung
// sources in Spanish, tested on the caption itself (m11, n3), "1 fallido" (n1), the traffic light's reason printed once (n2), names for
// the acronyms in Spanish (n5), "Simulaciones por tramo" (n6), the p-values with the same three significant digits in the bars and the
// tables (m4, n7), the tail level in the back-test and DM titles (n8) and no blank stage when there is no champion (m3). Reads the
// committed documents, in both languages.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { C11ContextView, ModelReadout } from './C11Common';
import { ChampionView, DmView } from './ComparisonViews';
import { ZonesView } from './ExceedanceViews';
import { EsBacktestView, TestsView } from './BacktestViews';
import { defaultSel, outputsOf, reasonText, rungSourceText, tableRefText, type C11Sel } from './selection';

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
const NBSP = ' ';

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

describe('U16-F12c, C11 (R4 c14)', () => {
  afterEach(() => setLang('en'));

  it('NB2: the Spanish champion and DM tables say "pérdida cuantílica", never "tick"', () => {
    setLang('es');
    for (const w of WINDOWS) {
      const sel = selOf(w);
      const text = view(<ChampionView sel={sel} />) + view(<DmView sel={sel} />);
      expect(text, w).not.toMatch(/\btick\b/i);
    }
    expect(view(<ChampionView sel={selOf('rates-2022')} />)).toContain('Pérdida cuantílica media');
    expect(view(<DmView sel={selOf('rates-2022')} />)).toContain('Pérdida cuantílica');
  });

  it('m16 and n4: the FZ0 reason has one gender in the tables and in the rail', () => {
    expect(reasonText('the model forecasts no ES: FZ0 is not defined', 'es')).toBe('el modelo no pronostica ES: FZ0 no está definido');
    setLang('es');
    // a window whose ladder has a model without an ES: its champion table and its rail read-out on that model
    for (const w of WINDOWS) {
      const sel = selOf(w);
      const noEs = outputsOf(sel)!.models.find((m) => m.by_level.some((l) => l.fz0_reason));
      if (!noEs) continue;
      const tables = view(<ChampionView sel={sel} />);
      const rail = html(<ModelReadout sel={{ ...sel, model: noEs.model_id }} />); // the hint is an attribute: read the markup
      expect(tables + rail, w).not.toContain('FZ0 no está definida');
      expect(tables, w).toContain('FZ0 no está definido');
      expect(rail, w).toContain('FZ0 no está definido');
    }
  });

  it('m11 and n3: the MAR32.9 caption itself is Spanish, with its dossier locators', () => {
    const ref = 'MAR32.9 Table 1 (dossier 01 D.4); 12 CFR 217.204 Table 1 (dossier 05 B.4)';
    expect(tableRefText(ref, 'es')).toBe('Tabla 1 de MAR32.9 (dossier 01 D.4); Tabla 1 de 12 CFR 217.204 (dossier 05 B.4)');
    expect(tableRefText(ref, 'en')).toBe(ref);
    setLang('es');
    const markup = html(<ZonesView sel={selOf('calm-2004-06')} />);
    const caption = /<p class="ct-note" data-caption="mar32-9"[^>]*>(.*?)<\/p>/s.exec(markup)?.[1] ?? '';
    expect(caption).toContain('Tabla 1 de MAR32.9');
    expect(caption).not.toContain('Table');
  });

  it('m11: a rung source joins two authors with "y" also when a name has a capital inside it (McNeil)', () => {
    expect(rungSourceText('McNeil and Frey 2000, eq 3', 'es')).toBe('McNeil y Frey 2000, ec. 3');
    expect(rungSourceText('Engle, McNeil and Frey 2000', 'es')).toBe('Engle, McNeil y Frey 2000');
  });

  it('n1: one failed refit is singular in Spanish', () => {
    setLang('es');
    const text = view(<C11ContextView sel={selOf('rates-2022')} />);
    expect(text).toMatch(/\(1 fallido\)/);
    expect(text).not.toMatch(/\(1 fallidos\)/);
  });

  it('n2: a traffic light that is not evaluated states its reason once', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const sel = selOf('rates-2022');
      const o = outputsOf(sel)!;
      const tl = o.models.find((m) => m.model_id === sel.model)!.by_level.find((l) => l.alpha === sel.alpha)!.traffic_light!;
      expect(tl.reason).toBeTruthy();
      const why = reasonText(tl.reason, lang);
      const text = view(<ZonesView sel={sel} />);
      expect(text.split(why).length - 1, lang).toBe(1);
    }
  });

  // the view's own words (the selection rule is the producer's text: tests/c11/test_c11_f12c_texts.py, until the integrator re-bakes)
  it('n5: the Spanish champion view and the Context name the set in words, not POF or MCS', () => {
    setLang('es');
    const text = view(<ChampionView sel={viewWordsOnly('rates-2022')} />);
    expect(text).not.toMatch(/\bPOF\b|\bMCS\b/);
    expect(text).toContain('Valor p del conjunto de confianza');
    const ctx = view(<C11ContextView sel={selOf('rates-2022')} />);
    expect(ctx).not.toMatch(/\bMCS\b/);
  });

  it('n6: the Spanish Z2 axis says what is counted per bin', () => {
    setLang('es');
    lines.length = 0;
    html(<EsBacktestView sel={selOf('rates-2022')} />);
    expect((lines.at(-1)!.y.label as { es: string }).es).toBe('Simulaciones por tramo');
  });

  it('m4 and n7: the p-values read three significant digits in the bars and in the tables (0.0495 and 0.0511 do not both read 0.05)', () => {
    bars.length = 0;
    const sel = selOf('equity-2020');
    html(<TestsView sel={sel} />);
    html(<ChampionView sel={sel} />);
    html(<DmView sel={sel} />);
    expect(bars).toHaveLength(3);
    for (const b of bars) expect(b.axis.format).toEqual({ digits: 3 });
    const champion = html(<ChampionView sel={sel} />);
    const mcs = outputsOf(sel)!.comparison.mcs.find((m) => m.alpha === sel.alpha)!;
    const m = mcs.members.find((x) => x.p_value > 0.1 && x.p_value < 1 && Math.round(x.p_value * 1000) % 10 !== 0);
    if (m) expect(champion).toContain(String(Number(m.p_value.toPrecision(3))));
  });

  it('n8: the back-test and DM cards name their tail level in the title', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const sel = selOf('rates-2022');
      const tail = lang === 'en' ? `1${NBSP}% tail` : `cola de 1${NBSP}%`;
      expect(html(<TestsView sel={sel} />)).toMatch(new RegExp(`class="caos-plot-title">[^<]*${tail}`));
      expect(html(<DmView sel={sel} />)).toMatch(new RegExp(`class="caos-plot-title">[^<]*${tail}`));
    }
  });

  it('m3: with no champion the DM card is as tall as its reason, not a filling card with a blank stage', () => {
    const sel = selOf('equity-2007-09');
    expect(outputsOf(sel)!.comparison.champions.find((c) => c.alpha === sel.alpha)!.model_id).toBeNull();
    const markup = html(<DmView sel={sel} />);
    expect(markup).toMatch(/<figure class="caos-plot"/);
    expect(markup).not.toMatch(/<figure class="caos-plot fill"/);
  });
});
