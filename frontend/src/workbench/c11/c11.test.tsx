// U8-W: the C11 instrument rendered on the server from the c11-outputs and c11-models fixtures
// (docs/contracts/fixtures/c11). Every VaR and ES is a positive loss with the convention named once per view; the
// exceedance timeline and the rolling 250-day count are drawn in the MAR32.9 bands; the ES back-test shows the model's own
// simulated critical values and the published reference only as a reference; a test that did not run shows its reason;
// the hyperparameter span is shown before any test window; no view draws a number the fixture does not contain. The
// series each chart receives are captured from the shell's chart and read against the fixture's JSON.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';
import { noteText } from '../c08/notes';
import { C11_FIT, C11_OUTPUTS } from './descriptor';
import { C11ContextView, C11FindingsView, C11VariantsTable, LevelReadout, ModelReadout, TestReadout } from './C11Common';
import { EsBacktestView, TestsView } from './BacktestViews';
import { ChampionView, DmView } from './ComparisonViews';
import { TimelineView, ZonesView } from './ExceedanceViews';
import { useC11Instrument } from './instrument';
import { defaultSel, outputsOf, rollingCounts, seconds, type C11Sel } from './selection';

type Outputs = components['schemas']['c11Outputs'];

// every chart the views draw is the shell's, rendered as it is; its props are kept to read what it was given
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

const fixture = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(`../../../../docs/contracts/fixtures/c11/${rel}`, import.meta.url), 'utf8')) as T;
const variant = fixture<VariantArtifact<Outputs>>('variant-window-fixture.json');
const models = fixture<ModelsArtifact>('models-fixture.json');
const data = fixtureData('C11', variant as unknown as VariantArtifact, models, { en: 'Market VaR and ES back-testing', es: 'Backtesting de VaR y ES de mercado' });
const o = variant.outputs;
const fit = (models as unknown as { fit: components['schemas']['c11Fit'] }).fit;
const sel = defaultSel(data) as C11Sel;
const en = (b: unknown): string => (b as { en: string } | undefined)?.en ?? '';
const NA = formatNumber(null, 'en');
const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const count = (v: number) => formatNumber(v, 'en', { decimals: 0 });
const chartOf = (el: ReactElement) => {
  captured.length = 0;
  const markup = html(el);
  return { markup, charts: [...captured] };
};
const levelOf = (model: string, alpha: number) => o.models.find((m) => m.model_id === model)!.by_level.find((l) => l.alpha === alpha)!;
const values = (c: UPlotChartProps, label: string, lang: 'en' | 'es' = 'en') => c.series.find((s) => (s.label as { en: string; es: string })[lang] === label)?.values;

const VIEWS: Array<[string, (p: { sel: C11Sel | null }) => ReactElement]> = [
  ['Timeline', TimelineView], ['Zones', ZonesView], ['Tests', TestsView], ['ES back-test', EsBacktestView],
  ['Champion', ChampionView], ['DM', DmView], ['Findings', C11FindingsView], ['Context', C11ContextView],
];

function Names() {
  const inst = useC11Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC11Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C09' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C11 documents against their descriptors', () => {
  it('the outputs and the fit conform to the run-time descriptors, in both directions', () => {
    expect(conform(variant.outputs, C11_OUTPUTS)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C11_FIT)).toEqual([]);
  });
});

describe('the C11 instrument', () => {
  afterEach(() => setLang('en'));
  beforeEach(() => {
    captured.length = 0;
  });

  it('answers for C11 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('Exceedances|Back-tests|Comparison|Findings|Variants');
    function Count() {
      const inst = useC11Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>6</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('window');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('every view states the sign convention once and prints no NaN, undefined or internal id in a title', () => {
    for (const [name, View] of VIEWS.filter(([n]) => !['Findings', 'Context'].includes(n))) {
      const markup = html(<View sel={sel} />);
      expect(markup.match(/data-convention="true"/g)?.length, `${name}: the convention`).toBe(1);
      expect(markup, name).not.toMatch(/NaN|undefined|Infinity/);
    }
  });
});

describe('the exceedance timeline', () => {
  afterEach(() => setLang('en'));

  it('draws the VaR and the ES of the model chosen as the document gives them, positive, and a point on each exceedance at the realised loss', () => {
    for (const alpha of [0.01, 0.025] as const) {
      const lv = levelOf('ewma-094', alpha);
      const { markup, charts } = chartOf(<TimelineView sel={{ ...sel, alpha, model: 'ewma-094' }} />);
      const c = charts[0];
      expect(c.x.time).toBe(true);
      expect(c.x.values).toEqual(o.grid.dates.map(seconds));
      expect(values(c, 'VaR')).toEqual(lv.var);
      expect(values(c, 'ES')).toEqual(lv.es);
      for (const v of lv.var) expect(v).toBeGreaterThan(0);
      const pts = values(c, 'Exceedance')!;
      expect(pts.filter((v) => v !== null).length).toBe(lv.n_exceedances);
      for (const d of lv.exceedance_days) expect(pts[d]).toBe(o.grid.realised_loss.loss![d]);
      expect(values(c, 'Realised loss')).toEqual(o.grid.realised_loss.loss);
      // every number the chart holds is one of the document's
      const known = new Set<number>([...lv.var, ...(lv.es as number[]), ...(o.grid.realised_loss.loss as number[])]);
      for (const s of c.series) for (const v of s.values) if (v !== null) expect(known.has(v), `${en(s.label)}: ${v}`).toBe(true);
      expect(markup).toContain(`data-level="${alpha}"`);
      for (const d of lv.exceedance_days) expect(markup).toContain(`data-exceedance-day="${o.grid.dates[d]}"`);
      expect(markup).toContain(pct(lv.var[lv.exceedance_days[0]]));
    }
  });

  it('states the hyperparameter span, never tuned on a test window, and the days the public series skipped', () => {
    const markup = html(<TimelineView sel={sel} />);
    expect(markup).toContain(o.hyperparameters.fixed_on.start);
    expect(markup).toContain(o.hyperparameters.fixed_on.end);
    expect(markup).toContain('never tuned on a test window');
    expect(markup).toContain(count(o.data_status.missing_days.count));
  });

  it('a model that forecasts no ES draws no ES line and says why; a day with no ES is a gap, not a zero', () => {
    const none = chartOf(<TimelineView sel={{ ...sel, model: 'caviar-sav' }} />);
    expect(none.charts[0].series.find((s) => en(s.label) === 'ES')).toBeUndefined();
    expect(none.markup).toContain('forecasts no ES');
    const evt = levelOf('evt-mf', 0.01);
    const { charts } = chartOf(<TimelineView sel={{ ...sel, model: 'evt-mf' }} />);
    expect(values(charts[0], 'ES')).toEqual(evt.es);
  });

  it('a realised series withheld for a derived-only component is not drawn, and the exceedances sit on the VaR with the reason', () => {
    const odd = structuredClone(variant) as VariantArtifact<Outputs>;
    odd.outputs.grid.realised_loss = { status: 'withheld-derived-only', loss: null, reason: 'a component is derived-only: the series is not committed' };
    const s = defaultSel({ ...data, variant: odd as unknown as VariantArtifact }) as C11Sel;
    const { markup, charts } = chartOf(<TimelineView sel={s} />);
    expect(charts[0].series.find((x) => en(x.label) === 'Realised loss')).toBeUndefined();
    const lv = levelOf('ewma-094', 0.01);
    const pts = values(charts[0], 'Exceedance')!;
    for (const d of lv.exceedance_days) expect(pts[d]).toBe(lv.var[d]);
    expect(markup).toContain('a component is derived-only: the series is not committed');
  });

  it('is written in Spanish in the Spanish interface', () => {
    setLang('es');
    const { markup, charts } = chartOf(<TimelineView sel={sel} />);
    expect(markup).toContain('pérdidas positivas');
    expect(markup).not.toContain('positive losses');
    expect(values(charts[0], 'Pérdida realizada', 'es')).toEqual(o.grid.realised_loss.loss);
  });
});

describe('the traffic light', () => {
  afterEach(() => setLang('en'));

  it('rolling counts tally the exceedance days and agree with the document maximum and final count, for every model', () => {
    for (const m of o.models) {
      const lv = m.by_level.find((l) => l.alpha === 0.01)!;
      const rc = rollingCounts(lv.exceedance_days, o.grid.dates.length, 250);
      expect(rc.length).toBe(lv.traffic_light!.n_windows);
      expect(Math.max(...rc)).toBe(lv.traffic_light!.max_rolling_exceedances);
      expect(rc[rc.length - 1]).toBe(lv.traffic_light!.final_rolling_exceedances);
    }
  });

  it('draws the rolling count with the amber and red starts of MAR32.9, and gives the table with its counts, multipliers and probabilities', () => {
    const lv = levelOf('hs-250', 0.01);
    const { markup, charts } = chartOf(<ZonesView sel={{ ...sel, model: 'hs-250' }} />);
    const c = charts[0];
    expect(c.series[0].values).toEqual(rollingCounts(lv.exceedance_days, o.grid.dates.length, 250));
    expect(c.yMarks?.map((m) => m.y)).toEqual([5, 10]);
    expect(c.x.values).toEqual(lv.traffic_light!.n_windows ? Array.from({ length: lv.traffic_light!.n_windows }, (_, i) => 250 + i) : []);
    for (const r of fit.traffic_light.rows) {
      expect(markup).toContain(`data-exceptions="${r.exceptions}"`);
      expect(markup).toContain(`data-zone="${r.zone}"`);
      expect(markup).toContain(formatNumber(r.frtb_multiplier, 'en', { decimals: 2 }));
      expect(markup).toContain(formatNumber(r.us_multiplier, 'en', { decimals: 2 }));
      expect(markup).toContain(formatNumber(r.cumulative_probability_pct, 'en', { decimals: 2 }));
    }
    expect(markup).toContain(count(lv.traffic_light!.max_rolling_exceedances!));
    expect(markup).toContain('MAR32.9');
    expect(markup).toMatch(/data-final-zone="red"/);
  });

  it('is not defined at the 2.5 percent level: it says so, with no chart', () => {
    const { markup, charts } = chartOf(<ZonesView sel={{ ...sel, alpha: 0.025 }} />);
    expect(charts.length).toBe(0);
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).toContain('99');
  });

  it('a window under 250 days is not evaluated and shows its reason, never a zone or a number', () => {
    const odd = structuredClone(variant) as VariantArtifact<Outputs>;
    for (const m of odd.outputs.models) {
      const l = m.by_level.find((x) => x.alpha === 0.01)!;
      l.traffic_light = { window_days: 250, n_windows: 0, max_rolling_exceedances: null, final_rolling_exceedances: null, final_zone: 'not_evaluated', days_green: null, days_amber: null, days_red: null, reason: 'the window has 120 forecast days; MAR32.9 is defined on 250' } as never;
    }
    const s = defaultSel({ ...data, variant: odd as unknown as VariantArtifact }) as C11Sel;
    const { markup, charts } = chartOf(<ZonesView sel={s} />);
    expect(charts.length).toBe(0);
    expect(markup).toContain('the window has 120 forecast days; MAR32.9 is defined on 250');
    expect(markup).toContain('data-final-zone="not_evaluated"');
  });
});

describe('the back-tests', () => {
  afterEach(() => setLang('en'));

  it('the tests view gives every test row of the model and level, in words, and the eligibility with its failed gates', () => {
    const markup = html(<TestsView sel={{ ...sel, model: 'hs-250' }} />);
    const rows = variant.tests.filter((t) => t.model_id === 'hs-250' && t.segment === 'alpha=0.01');
    expect(rows.length).toBeGreaterThan(0);
    for (const t of rows) {
      expect(markup).toContain(`data-test="${t.test_id}"`);
      expect(markup).toContain(`data-light="${t.light}"`);
    }
    expect(markup).toContain('Kupiec proportion of failures');
    expect(markup).not.toContain('>market.kupiec_pof<');
    expect(markup).toContain('data-eligible="false"');
    expect(markup).toContain('Christoffersen conditional coverage');
    expect(markup).toContain(formatNumber(25.310346, 'en', { digits: 4 }));
  });

  it('a test that did not run shows its reason and no number', () => {
    const markup = html(<TestsView sel={{ ...sel, model: 'evt-mf' }} />);
    const dead = variant.tests.find((t) => t.model_id === 'evt-mf' && t.test_id === 'market.duration_test')!;
    expect(dead.light).toBe('not_evaluated');
    const row = markup.slice(markup.indexOf('data-test="market.duration_test"'));
    const cells = row.slice(0, row.indexOf('</tr>'));
    expect(cells).toContain(escapeHtml(dead.notes as string));
    expect(cells.match(new RegExp(NA, 'g'))?.length).toBeGreaterThanOrEqual(2);
  });

  it('the ES back-test draws the null distribution, the realised statistic and the model critical values, and the published points only as a reference', () => {
    const lvl = 0.025;
    const es = o.es_backtests.find((e) => e.model_id === 'hs-250' && e.alpha === lvl)!;
    const { markup, charts } = chartOf(<EsBacktestView sel={{ ...sel, alpha: lvl, model: 'hs-250' }} />);
    const c = charts[0];
    const centers = es.histogram.counts.map((_, i) => (es.histogram.edges[i] + es.histogram.edges[i + 1]) / 2);
    const drawn = c.x.values.map((x, i) => [x, c.series[0].values[i]] as const).filter(([, y]) => y !== null);
    expect(drawn.map(([x]) => x)).toEqual(centers);
    expect(drawn.map(([, y]) => y)).toEqual(es.histogram.counts);
    const marks = c.marks ?? [];
    const at = (x: number) => marks.find((m) => m.x === x);
    expect(en(at(es.realised)?.label)).toContain('Z2');
    expect(en(at(es.critical_5pct)?.label)).toContain('5%');
    expect(en(at(es.critical_0_01pct)?.label)).toContain('0.01%');
    expect(en(at(fit.es_reference.yellow)?.label)).toContain('Ref.');
    expect(en(at(fit.es_reference.red)?.label)).toContain('Ref.');
    expect(markup).toContain(formatNumber(es.critical_5pct, 'en', { digits: 4 }));
    expect(markup).toContain(formatNumber(es.critical_0_01pct, 'en', { digits: 4 }));
    expect(markup).toContain(count(es.n_draws));
    expect(markup).toContain('not a regulatory');
    // the reference is printed with its sign, as the document holds it
    expect(markup).toContain(formatNumber(fit.es_reference.yellow, 'en', { decimals: 2 }));
    expect(markup).toContain(formatNumber(fit.es_reference.red, 'en', { decimals: 2 }));
    expect(markup).toContain('data-zone="red"');
  });

  it('a model with no ES back-test gives the reason of its not-evaluated row, and the 1 percent level shows Z2 at the 2.5 percent tail', () => {
    const none = chartOf(<EsBacktestView sel={{ ...sel, alpha: 0.025, model: 'evt-mf' }} />);
    expect(none.charts.length).toBe(0);
    const dead = variant.tests.find((t) => t.model_id === 'evt-mf' && t.test_id === 'market.acerbi_szekely')!;
    expect(none.markup).toContain(escapeHtml(dead.notes as string));
    // Z2 is defined at the 2.5 percent tail: with the 1 percent level in focus the view shows it at the level the document has
    const one = chartOf(<EsBacktestView sel={{ ...sel, alpha: 0.01, model: 'ewma-094' }} />);
    expect(one.charts.length).toBe(1);
    expect(one.markup).toContain('data-level="0.025"');
  });
});

describe('the comparison', () => {
  afterEach(() => setLang('en'));

  it('the champion view gives the champion, each model in the set with its p-value, the FZ0 average and the reason of a missing one', () => {
    const markup = html(<ChampionView sel={sel} />);
    const mcs = o.comparison.mcs.find((m) => m.alpha === 0.01)!;
    for (const mem of mcs.members) {
      expect(markup).toContain(`data-in-set="${mem.in_set}"`);
      expect(markup).toContain(formatNumber(mem.p_value, 'en', { digits: 2 }));
    }
    expect(markup).toMatch(/data-champion="true"/);
    expect(markup.match(/data-champion="true"/g)?.length).toBe(1);
    for (const m of o.models) {
      const lv = m.by_level.find((l) => l.alpha === 0.01)!;
      if (lv.fz0_mean !== null) expect(markup).toContain(formatNumber(lv.fz0_mean, 'en', { digits: 4 }));
      else expect(markup).toContain(escapeHtml(lv.fz0_reason as string));
    }
    expect(markup).toContain(escapeHtml(fit.scoring.selection_rule.en));
    expect(markup).toContain(formatNumber(mcs.confidence, 'en', { percent: true, decimals: 0 }));
  });

  it('the Diebold-Mariano view gives the statistic, p-value and direction against the champion, and the reason of a comparison that could not run', () => {
    const markup = html(<DmView sel={sel} />);
    for (const d of o.comparison.dm.filter((x) => x.alpha === 0.01)) {
      expect(markup).toContain(`data-dm="${d.model_id}-${d.loss}"`);
      if (d.dm_statistic !== null) expect(markup).toContain(formatNumber(d.dm_statistic, 'en', { digits: 4 }));
    }
    const dead = o.comparison.dm.find((d) => d.direction === 'not-evaluated' && d.alpha === 0.01)!;
    expect(markup).toContain(escapeHtml(dead.not_evaluated_reason as string));
    expect(markup).toContain(`${o.comparison.hac_lags}`);
    expect(markup).not.toContain('data-dm="ewma-094-');
  });
});

describe('the windows, the context and the findings', () => {
  afterEach(() => setLang('en'));

  it('the windows table gives each window with the champion exceedances against the expected count and the zone', () => {
    const markup = html(<C11VariantsTable variants={[{ id: variant.variant_id, title: { en: 'Rates 2022', es: 'Tasas 2022' }, v: variant }]} onPick={() => undefined} current={variant.variant_id} />);
    const lv = levelOf('ewma-094', 0.01);
    expect(markup).toContain(`data-variant="${variant.variant_id}"`);
    expect(markup).toContain(count(lv.n_exceedances));
    expect(markup).toContain(formatNumber(lv.expected_exceedances, 'en', { decimals: 2 }));
    expect(markup).toContain(count(o.window.n_forecast_days));
    expect(markup).toContain('data-zone="green"');
  });

  it('the context shows the span before the window, the hyperparameters, the portfolio, the data, the ladder and the convention', () => {
    const markup = html(<C11ContextView sel={sel} />);
    expect(markup.indexOf(o.hyperparameters.fixed_on.end)).toBeLessThan(markup.indexOf(o.window.start_date));
    expect(markup).toContain(formatNumber(o.hyperparameters.ewma_lambda, 'en', { decimals: 2 }));
    expect(markup).toContain(escapeHtml(o.sign_convention.definition.en));
    expect(markup).toContain(escapeHtml(o.portfolio.components[0].label.en));
    expect(markup).toContain(count(o.data_status.n_observed_days));
    for (const s of fit.data_sources) expect(markup).toContain(escapeHtml(s.url));
    const challenger = fit.ladder.find((r) => r.status === 'challenger-not-run')!;
    // the reason as the reader reads it: no plan unit ("the U8 bake", R3 c12 B2; U16-F10a)
    expect(markup).toContain(escapeHtml(noteText(challenger.not_run_reason as string, 'en')));
    expect(markup).toContain(escapeHtml(fit.ladder[0].title.en));
    expect(markup).toContain('data-fixture="true"');
  });

  it('the findings carry the fixture notice and the finding', () => {
    const markup = html(<C11FindingsView sel={sel} />);
    expect(markup).toContain('data-fixture="true"');
    expect(markup).toContain(escapeHtml(variant.findings[0].title.en));
  });
});

function RailSection({ at }: { at: number }) {
  const inst = useC11Instrument(data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C11 rail', () => {
  afterEach(() => setLang('en'));

  it('has three sections, each with one control and one read-out', () => {
    function Sections() {
      const inst = useC11Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('level|model|test');
    for (const at of [0, 1, 2]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('the level keeps its two chips; the model and the test are one select each, named in words and never by id', () => {
    expect(railHtml(0)).toMatch(/data-control="c11-level"/);
    expect(railHtml(0).match(/caos-chip"/g)?.length ?? railHtml(0).match(/<button/g)?.length).toBe(2);
    expect(railHtml(1)).toMatch(/data-control="c11-model"[^>]*><label[^>]*>Model<\/label><select/);
    expect(railHtml(2)).toMatch(/data-control="c11-test"[^>]*><label[^>]*>Back-test<\/label><select/);
    expect(railHtml(1).match(/<option/g)?.length).toBe(o.models.length);
    expect(railHtml(2).match(/<option/g)?.length).toBe(levelOf('ewma-094', 0.01).test_ids.length);
    for (const at of [1, 2]) for (const id of ['hs-250', 'ewma-094', 'evt-mf', 'caviar-sav', 'market.kupiec_pof']) expect(railHtml(at), `${at} ${id}`).not.toContain(`>${id}<`);
    expect(railHtml(1)).toContain('Historical simulation');
  });

  it('the level read-out gives the exceedances against the expected count and the zone; the model read-out the eligibility and the FZ0; the test read-out its light', () => {
    const lv = levelOf('ewma-094', 0.01);
    const a = html(<LevelReadout sel={sel} />);
    expect(a).toContain(count(lv.n_exceedances));
    expect(a).toContain(formatNumber(lv.expected_exceedances, 'en', { decimals: 2 }));
    expect(a).toContain('Green');
    const hs = html(<ModelReadout sel={{ ...sel, model: 'hs-250' }} />);
    expect(hs).toContain('No');
    expect(hs).toContain(formatNumber(levelOf('hs-250', 0.01).fz0_mean!, 'en', { digits: 4 }));
    expect(html(<ModelReadout sel={{ ...sel, model: 'caviar-sav' }} />)).toContain(NA);
    const t = html(<TestReadout sel={{ ...sel, test: 'market.kupiec_pof' }} />);
    expect(t).toContain('Green');
    const dead = html(<TestReadout sel={{ ...sel, model: 'evt-mf', test: 'market.duration_test' }} />);
    expect(dead).toContain(NA);
    expect(dead).toContain('Not evaluated');
  });

  it('is written in Spanish', () => {
    expect(railHtml(0, 'es')).toContain(`Cola de ${formatNumber(0.01, 'es', { percent: true, decimals: 0 })}`);
    expect(railHtml(1, 'es')).toContain('Modelo');
    expect(railHtml(2, 'es')).toContain('Backtest');
  });
});
