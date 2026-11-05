// U16-F10c (R3 batch c14, C13): the minors of the batch fixed in the view. The Spanish page writes the words the view owns in Spanish
// (no "Backtest"), the desk mean bar has the decimal of its table, the flagged desk back-test says it counts either level, the control
// does not repeat itself and its intended test is "not applicable" with its reason, every C13 view states the convention of the desk
// notional, the generator's parameters start with a capital and say their unit once, the 390 desk bars have whole labels, a list of
// counts is not separated by the thousands comma, and an interval does not break at its hyphen. Reads the committed documents.
import type { BarChartProps } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { fixtureData, html, setLang } from '../c03/u6-testkit';
import { committed, committedData, view } from '../c08/spanish-testkit';
import { C13ContextView, C13VariantsTable, KnownBanner } from './C13Common';
import { DeskView } from './DeskViews';
import { DetectionView, EcdfView, RanksView, ZonesView } from './PlaViews';
import { useInstrument } from './instrument';
import { defaultSel, outputsOf, type C13Outputs, type C13Sel } from './selection';

const bars = vi.hoisted(() => [] as BarChartProps[]);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return { ...mod, BarChart: (p: BarChartProps) => (bars.push(p), mod.BarChart(p)) };
});

const TITLE = { en: 'FRTB desk eligibility', es: 'Elegibilidad de mesas FRTB' };
const VARIANTS = ['none', 'missing-basis', 'omitted-factor', 'stale-volatility', 'time-misalignment', 'wrong-correlation'];
const selOf = (v: string) => defaultSel(committedData('C13', `${v}.json`, 'models-generator.json', TITLE)) as C13Sel;

function viewWordsOnly(v: string) {
  const blank = (x: unknown): unknown => {
    if (Array.isArray(x)) return x.map(blank);
    if (x && typeof x === 'object') {
      const o = x as Record<string, unknown>;
      if (typeof o.en === 'string' && typeof o.es === 'string') return { ...o, es: '·' };
      return Object.fromEntries(Object.entries(o).map(([k, val]) => [k, blank(val)]));
    }
    return x;
  };
  return defaultSel(fixtureData('C13', blank(committed<VariantArtifact>('C13', `${v}.json`)) as VariantArtifact, blank(committed<ModelsArtifact>('C13', 'models-generator.json')) as ModelsArtifact, TITLE)) as C13Sel;
}
function Groups({ sel }: { sel: C13Sel }) {
  const inst = useInstrument(sel.data, () => undefined);
  // the Findings card prints the evidence names of the shared names module (names/tests.ts, U16-F10a's file)
  return <div>{inst ? [...inst.groups.filter((g) => g.id !== 'findings').map((g) => <section key={g.id}>{g.content}</section>), ...inst.rail.map((r) => <section key={r.id}>{r.content}</section>)] : null}</div>;
}

describe('U16-F10c, C13 (R3 c14)', () => {
  afterEach(() => setLang('en'));

  it('the Spanish page writes the words the view owns in Spanish: no Backtest', () => {
    setLang('es');
    const sel = viewWordsOnly('wrong-correlation');
    const own = [<Groups key="g" sel={sel} />, <DeskView key="d" sel={sel} />, <DetectionView key="t" sel={sel} />].map((el) => view(el)).join(' ');
    expect(own).not.toMatch(/\bback-?tests?\b/i);
  });

  it('m2: the desk mean bar writes one decimal, as the table', () => {
    bars.length = 0;
    html(<DeskView sel={selOf('time-misalignment')} />);
    const mean = bars.at(-1)!.data.find((d) => d.id === 'mean')!;
    expect(mean.format).toEqual({ decimals: 1 });
  });

  it('m4: the flagged desk back-test says it counts a replication over the limit at either level', () => {
    bars.length = 0;
    html(<DetectionView sel={selOf('wrong-correlation')} />);
    const desk = bars.at(-1)!.data.find((d) => d.id === 'desk')!;
    expect(typeof desk.label === 'string' ? desk.label : desk.label.en).toBe('Desk back-test flagged, at either level');
  });

  it('m6: the control names its truth once ("No deficiency planted: the risk model is exact ...")', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const o = outputsOf(selOf('none'))!;
      const text = view(<KnownBanner o={o} />);
      expect(text).not.toMatch(/No deficiency planted: No deficiency|Sin deficiencia sembrada: Sin deficiencia/);
    }
  });

  it('m7: the control\'s intended test is "not applicable" with its reason inline', () => {
    const text = view(<DetectionView sel={selOf('none')} />);
    expect(text).toContain('Flagged by the test meant to catch it not applicable: no deficiency planted, so no test is meant to catch it');
  });

  it('m8: every C13 view states the convention of the desk notional, not the portfolio value, and Spanish says "nocional"', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const sel = selOf('missing-basis');
      for (const el of [<RanksView key="r" sel={sel} />, <EcdfView key="e" sel={sel} />, <ZonesView key="z" sel={sel} />, <DeskView key="d" sel={sel} />]) {
        const text = view(el);
        expect(text).not.toMatch(/portfolio value|valor de la cartera/);
        expect(text).toMatch(lang === 'en' ? /desk notional/ : /nocional de la mesa/);
      }
    }
  });

  it('m9: a generator parameter starts with a capital and says its unit once', () => {
    const text = view(<C13ContextView sel={selOf('missing-basis')} />);
    expect(text).not.toMatch(/of the HPL deviation [\d.]+ of the HPL deviation/);
    expect(text).toMatch(/Loading of factor 1/);
    expect(text).not.toMatch(/ loading of factor 1/);
  });

  it('m10: the desk bars have labels short enough for a 390 px chart', () => {
    bars.length = 0;
    html(<DeskView sel={selOf('missing-basis')} />);
    for (const d of bars.at(-1)!.data) {
      const label = typeof d.label === 'string' ? d.label : d.label.en;
      expect(label.length, label).toBeLessThanOrEqual(8);
    }
  });

  it('m11: a list of counts is separated by " / ", never by the comma that groups thousands', () => {
    const text = view(<DetectionView sel={selOf('wrong-correlation')} />);
    const d = outputsOf(selOf('wrong-correlation'))!.detection.by_test;
    expect(text).toContain(`${d.spearman_flagged.toLocaleString('en-US')} / ${d.ks_flagged.toLocaleString('en-US')} / ${d.desk_backtest_flagged.toLocaleString('en-US')}`);
  });

  it('m14: an interval is written "a to b" with no-break spaces, so a phone does not break it at a hyphen', () => {
    const variants = VARIANTS.map((id) => ({ id, title: { en: id, es: id }, v: committed<VariantArtifact<C13Outputs>>('C13', `${id}.json`) }));
    const markup = html(<C13VariantsTable variants={variants} onPick={() => undefined} current="none" />);
    expect(markup).not.toMatch(/% - \d/);
    expect(markup).toMatch(/% to \d/);
  });
});
