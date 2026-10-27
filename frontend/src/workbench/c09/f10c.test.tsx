// U16-F10c (R3 batch c10, C09): at 1280 the Distribution chart gets a row per bin (M1: 16 bins in 15.8 rem scrolled inside the
// drawing and hid the bins above 1 and the value axis); By design, Back-test and Floor are split, not scrolled (M2: the estimates and the
// tests shared one 42 % box that showed one row): the tests are a card of their own and the tables take the room under a drawing of
// fixed height. With the minors of the batch fixed in the view. Reads the committed documents, in both languages.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { ByDesignView, DistributionView, EstimatorTestsView } from './CcfViews';
import { BacktestTestsView, BacktestView, FloorsView, ModelsView } from './EadViews';
import { C09ContextView, C09VariantsTable } from './C09Common';
import { useC09Instrument } from './instrument';
import { defaultSel, outputsOf, type C09Outputs, type C09Sel } from './selection';

const bars = vi.hoisted(() => [] as BarChartProps[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => (bars.push(p), mod.BarChart(p)) };
});

const TITLE = { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' };
const LEVELS = [0, 1, 2, 3, 4, 5];
const selOf = (n: number) => defaultSel(committedData('C09', `level-${n}.json`, 'models-generator.json', TITLE)) as C09Sel;

/** The cards of a markup, each as its markup. */
const cardsOf = (m: string) => m.split('<figure class="caos-plot').slice(1);

/** A committed level with every Spanish text the producer wrote blanked: what a Spanish view still prints is its own. */
function viewWordsOnly(n: number) {
  const blank = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(blank);
    if (x && typeof x === 'object') {
      const o = x as Record<string, unknown>;
      if (typeof o.en === 'string' && typeof o.es === 'string') return { ...o, es: '·' };
      return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, blank(v)]));
    }
    return x;
  };
  return defaultSel(fixtureData('C09', blank(committed<VariantArtifact>('C09', `level-${n}.json`)) as VariantArtifact, blank(committed<ModelsArtifact>('C09', 'models-generator.json')) as ModelsArtifact, TITLE)) as C09Sel;
}
function Groups({ sel }: { sel: C09Sel }) {
  const inst = useC09Instrument(sel.data, () => undefined);
  // the Findings card prints the names of the shared names module (names/tests.ts, U16-F10a's file); its own words are tested there
  const groups = inst ? inst.groups.filter((g) => g.id !== 'findings') : [];
  return <div>{inst ? [...groups.map((g) => <section key={g.id}>{g.content}</section>), ...inst.rail.map((r) => <section key={r.id}>{r.content}</section>)] : null}</div>;
}

describe('U16-F10c, C09 (R3 c10)', () => {
  afterEach(() => setLang('en'));

  it('M1: the Distribution chart is given 1.5 rem a bin, and no table box under it takes its height', () => {
    for (const n of LEVELS) {
      const sel = selOf(n);
      bars.length = 0;
      const bins = outputsOf(sel)!.ccf_distribution.counts.length;
      const markup = html(<DistributionView sel={sel} />);
      const min = Number(/--ct-chart-min:([\d.]+)rem/.exec(markup)?.[1]);
      expect(min, `level ${n}`).toBeGreaterThanOrEqual(bins * 1.5);
      // the bins are the chart's (its labels and its hidden table); no box of tables is stacked under it at 1280
      expect(markup).not.toContain('ct-stack-table');
      expect(markup).not.toMatch(/data-bin="/);
      // every bin is a bar with its count and its range; a bin outside 0 to 1 says so in its label
      const chart = bars.at(-1)!;
      expect(chart.data.map((x) => x.value)).toEqual(outputsOf(sel)!.ccf_distribution.counts);
      expect(chart.data.some((x) => typeof x.label !== 'string' && x.label.en.endsWith('(above 1)'))).toBe(true);
      // the totals stay on screen, in the card's note
      const d = outputsOf(sel)!.ccf_distribution;
      expect(view(<DistributionView sel={sel} />)).toContain(`${formatNumber(d.n, 'en', { decimals: 0 })} defaults in the design: ${formatNumber(d.n_below_zero, 'en', { decimals: 0 })} below 0 and ${formatNumber(d.n_above_one, 'en', { decimals: 0 })} above 1`);
    }
  });

  it('M2: By design draws its chart whole in a card beside its estimates; its tests are a sub-view of their own', () => {
    const sel = selOf(3);
    const markup = html(<ByDesignView sel={sel} />);
    const cards = cardsOf(markup);
    expect(cards).toHaveLength(2);
    expect(cards[0]).not.toContain('data-table=');
    expect(Number(/--ct-chart-min:([\d.]+)rem/.exec(cards[0])?.[1])).toBeGreaterThanOrEqual(9 * 1.5);
    expect(cards[1]).toContain('data-table="ccf-by-design"');
    expect(markup).not.toContain('data-table="tests"');
    expect(markup).not.toContain('ct-stack-table');
    const tests = html(<EstimatorTestsView sel={sel} />);
    expect((tests.match(/data-test="lgd_ead\.ccf_estimator_bias"/g) ?? []).length).toBe(8);
    // the generator notice is the Context's, not repeated over the estimates
    expect(view(<ByDesignView sel={sel} />)).not.toContain(outputsOf(sel)!.generator.notice.en);
  });

  it('M2: the Back-test puts its bands under a drawing of fixed height; its tests are a sub-view of their own', () => {
    const markup = html(<BacktestView sel={selOf(3)} />);
    expect(cardsOf(markup)).toHaveLength(1);
    expect(markup).toContain('data-table="ead-backtest"');
    expect(markup).toContain('ct-stack-rest');
    expect(markup).not.toContain('data-table="tests"');
    expect((html(<BacktestTestsView sel={selOf(3)} />).match(/data-test="lgd_ead\.ead_backtest_by_band"/g) ?? []).length).toBe(8);
  });

  it('M2: the Floor table takes the room under a drawing of fixed height, in both languages', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const card = cardsOf(html(<FloorsView sel={selOf(3)} />))[0];
      expect(card).toContain('ct-stack-rest');
      expect(card).not.toContain('ct-stack-table');
    }
  });

  it('m1: the by-design note states the whole light rule of the tests and what a red bar means', () => {
    const markup = view(<EstimatorTestsView sel={selOf(3)} />);
    expect(markup).toContain('green within it, amber up to twice it and red beyond');
    setLang('es');
    expect(view(<EstimatorTestsView sel={selOf(3)} />)).toContain('verde dentro de ella, ámbar hasta el doble y rojo más allá');
  });

  it('m3: a CCF model clips nothing by design: "not applicable", never "not available"', () => {
    const sel = selOf(3);
    const markup = html(<ModelsView sel={sel} />);
    for (const m of outputsOf(sel)!.ead_models) {
      const row = new RegExp(`<tr[^>]*data-model="${m.model_id}"[^>]*>(.*?)</tr>`).exec(markup)?.[1] ?? '';
      // the last two cells are the clipped counts
      const clipped = [...row.matchAll(/<td[^>]*>(.*?)<\/td>/g)].slice(-2).map((c) => c[1]);
      expect(clipped, m.model_id).toHaveLength(2);
      for (const c of clipped) {
        if (m.kind === 'direct-ead') expect(c, m.model_id).not.toMatch(/not applicable|not available/);
        else expect(c, m.model_id).toBe('not applicable');
      }
    }
  });

  it('m8: the supervisory CCF caption says the run recorded them, not the bake', () => {
    const markup = view(<FloorsView sel={selOf(3)} />);
    expect(markup).not.toMatch(/\bbake\b/);
    expect(markup).toContain('as the run recorded them');
  });

  it('m10: the by-design bars write two decimals, so the known 71.42 % and the estimate 71.28 % read apart', () => {
    bars.length = 0;
    html(<ByDesignView sel={selOf(3)} />);
    const p = bars.at(-1)!;
    for (const d of p.data) expect(d.format, d.id).toEqual({ percent: true, decimals: 2 });
  });

  it('m11: the Spanish floor header says "EAD media", as every other Spanish EAD', () => {
    setLang('es');
    const markup = view(<FloorsView sel={selOf(3)} />);
    expect(markup).toContain('EAD media antes');
    expect(markup).not.toMatch(/EAD medio/);
  });

  it('m12: the Variants table takes the room under a drawing of fixed height (the Level 5 row was under the fade)', () => {
    const variants = LEVELS.map((n) => ({ id: `level-${n}`, title: { en: `Level ${n}`, es: `Nivel ${n}` }, v: committed<VariantArtifact<C09Outputs>>('C09', `level-${n}.json`) }));
    const markup = html(<C09VariantsTable variants={variants} onPick={() => undefined} current="level-3" />);
    expect(markup).toContain('ct-stack-rest');
    expect(markup).not.toContain('ct-stack-table');
  });

  it('m9: the Context writes the formula with its reference date as a subscript, not ASCII t_r', () => {
    const markup = view(<C09ContextView sel={selOf(3)} />);
    expect(markup).toContain('CCF = (EAD - E(tᵣ)) / (L(tᵣ) - E(tᵣ))');
    expect(markup).not.toContain('t_r');
  });

  it('the Spanish page writes the words the view owns in Spanish: no "Backtest"', () => {
    setLang('es');
    const sel = viewWordsOnly(3);
    // the tests tables print the names of the shared tests table (c03/U6Shared.tsx TEST_TEXT, U16-F10b's file), left out here
    const own = (el: Parameters<typeof html>[0]) => html(el).replace(/<table[^>]*data-table="tests"[^>]*>.*?<\/table>/gs, ' ').replace(/<[^>]*>/g, ' ');
    const markup = own(<Groups sel={sel} />) + own(<BacktestView sel={sel} />) + own(<FloorsView sel={sel} />);
    expect(markup).not.toMatch(/\bback-?tests?\b/i);
    expect(markup).toContain('Prueba retrospectiva de la EAD por tramo de utilización');
  });
});
