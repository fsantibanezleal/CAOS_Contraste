// U8-W: the C13 instrument rendered on the server from the c13-outputs and c13-models fixtures
// (docs/contracts/fixtures/c13). The known deficiency is named on every view of its variant; the rank scatter and the
// two ECDFs are drawn from the example replication and recompute its Spearman and KS statistic; the zone counts, the
// detection rate and the desk back-test are the document's; the synthetic label is on every view; a desk with no
// deficiency is the control and says so. The series each chart receives are captured and read against the fixture.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';
import { C13_FIT, C13_OUTPUTS } from './descriptor';
import { C13ContextView, C13FindingsView, C13VariantsTable, LevelReadout, StatisticReadout } from './C13Common';
import { DeskView } from './DeskViews';
import { DetectionView, EcdfView, RanksView, ZonesView } from './PlaViews';
import { useC13Instrument } from './instrument';
import { defaultSel, ecdfGap, outputsOf, rankSeries, seedText, spearmanOf, type C13Sel } from './selection';

type Outputs = components['schemas']['c13Outputs'];

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

const fixture = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(`../../../../docs/contracts/fixtures/c13/${rel}`, import.meta.url), 'utf8')) as T;
const variant = fixture<VariantArtifact<Outputs>>('variant-deficiency-fixture.json');
const models = fixture<ModelsArtifact>('models-fixture.json');
const data = fixtureData('C13', variant as unknown as VariantArtifact, models, { en: 'FRTB desk eligibility', es: 'Elegibilidad FRTB de mesas' });
const o = variant.outputs;
const fit = (models as unknown as { fit: components['schemas']['c13Fit'] }).fit;
const sel = defaultSel(data) as C13Sel;
const en = (b: unknown): string => (b as { en: string } | undefined)?.en ?? '';
const NA = formatNumber(null, 'en');
const pct = (v: number, d = 1) => formatNumber(v, 'en', { percent: true, decimals: d });
const count = (v: number) => formatNumber(v, 'en', { decimals: 0 });
const chartOf = (el: ReactElement) => {
  captured.length = 0;
  const markup = html(el);
  return { markup, charts: [...captured] };
};

const VIEWS: Array<[string, (p: { sel: C13Sel | null }) => ReactElement]> = [
  ['Ranks', RanksView], ['ECDFs', EcdfView], ['Zones', ZonesView], ['Detection', DetectionView], ['Desk', DeskView],
  ['Findings', C13FindingsView], ['Context', C13ContextView],
];

function Names() {
  const inst = useC13Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC13Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C11' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C13 documents against their descriptors', () => {
  it('the outputs and the fit conform to the run-time descriptors, in both directions', () => {
    expect(conform(variant.outputs, C13_OUTPUTS)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C13_FIT)).toEqual([]);
  });
});

describe('the C13 instrument', () => {
  afterEach(() => setLang('en'));
  beforeEach(() => {
    captured.length = 0;
  });

  it('answers for C13 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('PLA|Desk back-test|Findings|Variants');
    function Count() {
      const inst = useC13Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>5</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('deficiency');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('every view of the variant names the known deficiency, its mechanism and the synthetic label', () => {
    for (const [name, View] of VIEWS) {
      const markup = html(<View sel={sel} />);
      expect(markup, `${name}: the known deficiency`).toContain(`data-known-deficiency="${o.known_deficiency.deficiency_id}"`);
      expect(markup, `${name}: the mechanism`).toContain(escapeHtml(o.known_deficiency.mechanism.en));
      expect(markup, `${name}: the synthetic label`).toContain('data-synthetic="true"');
      expect(markup, name).not.toMatch(/NaN|undefined|Infinity/);
    }
  });

  it('a desk with no planted deficiency is the control: it says so, and the detection is the size', () => {
    const odd = structuredClone(variant) as VariantArtifact<Outputs>;
    odd.outputs.known_deficiency = { deficiency_id: 'none', planted: false, mechanism: { en: 'No deficiency: the risk model is exact.', es: 'Sin deficiencia: el modelo de riesgo es exacto.' }, parameters: [], intended_to_fail: 'none' };
    odd.outputs.detection = { ...odd.outputs.detection, role: 'size', intended_test_flagged: null };
    const s = defaultSel({ ...data, variant: odd as unknown as VariantArtifact }) as C13Sel;
    const markup = html(<DetectionView sel={s} />);
    expect(markup).toContain('data-known-deficiency="none"');
    expect(markup).toContain('No deficiency planted');
    expect(markup).toContain('false-alarm');
    expect(markup).toContain(NA);
  });
});

describe('the PLA statistics of the example replication', () => {
  afterEach(() => setLang('en'));

  it('the example recomputes its Spearman and its KS statistic, in integer steps, from the two series', () => {
    expect(spearmanOf(o.example.hpl, o.example.rtpl)).toBeCloseTo(o.example.spearman, 5);
    expect(ecdfGap(o.example.hpl, o.example.rtpl).gap).toBeCloseTo(o.example.ks, 12);
  });

  it('the rank scatter draws the 250 pairs of ranks as points, with the same-rank diagonal, with the Spearman and its zone', () => {
    const { markup, charts } = chartOf(<RanksView sel={sel} />);
    const c = charts[0];
    const { x, y } = rankSeries(o.example.hpl, o.example.rtpl);
    expect(c.parity).toBeUndefined();
    expect(c.x.values).toEqual(x);
    expect(c.series[0].mode).toBe('points');
    expect(c.series[0].values).toEqual(y);
    expect(c.series[1].values).toEqual(x);
    expect(x.length).toBe(o.generator.window_days);
    expect(markup).toContain(formatNumber(o.example.spearman, 'en', { decimals: 3 }));
    expect(markup).toContain(formatNumber(o.pla.thresholds.spearman_green, 'en', { decimals: 2 }));
    expect(markup).toContain(formatNumber(o.pla.thresholds.spearman_red, 'en', { decimals: 2 }));
    expect(markup).toContain(`data-zone="${o.example.zone}"`);
    expect(markup).toContain(count(o.example.replication_index));
  });

  it('the ECDF view draws the two ECDFs on the step of the document and marks the largest gap, with the KS and its thresholds', () => {
    const { markup, charts } = chartOf(<EcdfView sel={sel} />);
    const c = charts[0];
    const g = ecdfGap(o.example.hpl, o.example.rtpl);
    expect(c.series.map((s) => en(s.label))).toEqual(['HPL', 'RTPL']);
    for (const s of c.series) {
      expect(s.values.length).toBe(c.x.values.length);
      expect(Math.max(...(s.values as number[]))).toBeCloseTo(1, 12);
      expect(Math.min(...(s.values as number[]))).toBeGreaterThanOrEqual(0);
    }
    expect(c.marks?.some((m) => m.x === g.at && /gap/i.test(en(m.label)))).toBe(true);
    expect(markup).toContain(formatNumber(o.example.ks, 'en', { decimals: 3 }));
    expect(markup).toContain(formatNumber(o.pla.thresholds.ks_green, 'en', { decimals: 2 }));
    expect(markup).toContain(formatNumber(o.pla.thresholds.ks_red, 'en', { decimals: 2 }));
    expect(markup).toContain(formatNumber(o.pla.thresholds.ecdf_step, 'en', { decimals: 3 }));
    expect(markup).toContain('MAR32.42');
  });
});

describe('the zones, the detection and the desk back-test', () => {
  afterEach(() => setLang('en'));

  it('the zones view gives the counts of the joint zone and of each statistic across the replications, and the distributions', () => {
    const markup = html(<ZonesView sel={sel} />);
    for (const [k, z] of Object.entries({ overall: o.pla.zones.overall, spearman: o.pla.zones.spearman, ks: o.pla.zones.ks })) {
      for (const zone of ['green', 'amber', 'red'] as const) expect(markup).toContain(`data-count="${k}-${zone}-${z[zone]}"`);
    }
    for (const d of [o.pla.spearman, o.pla.ks]) {
      expect(markup).toContain(formatNumber(d.q05, 'en', { decimals: 3 }));
      expect(markup).toContain(formatNumber(d.q95, 'en', { decimals: 3 }));
    }
    expect(markup).toContain(count(o.pla.zones.n));
    // the statistic chosen on the rail sets the bars
    const ks = chartOf(<ZonesView sel={{ ...sel, statistic: 'ks' }} />);
    expect(ks.markup).toContain('data-statistic="ks"');
  });

  it('the detection view gives the share caught with its interval, the replications and the tests that flagged the desk', () => {
    const d = o.detection;
    const markup = html(<DetectionView sel={sel} />);
    expect(markup).toContain(pct(d.share_amber_or_red, 2));
    expect(markup).toContain(pct(d.ci_low, 2));
    expect(markup).toContain(pct(d.ci_high, 2));
    expect(markup).toContain(count(d.n_replications));
    expect(markup).toContain(count(d.by_test.spearman_flagged));
    expect(markup).toContain(count(d.by_test.ks_flagged));
    expect(markup).toContain(count(d.by_test.desk_backtest_flagged));
    expect(markup).toContain(count(d.intended_test_flagged as number));
    expect(markup).toContain(escapeHtml(d.rule.en));
    expect(markup).toContain('power');
  });

  it('the desk view gives the exceptions of the level chosen against the MAR32.18 limit, and the share of replications over it', () => {
    for (const lvl of o.desk_backtest) {
      const { markup, charts } = chartOf(<DeskView sel={{ ...sel, alpha: lvl.alpha }} />);
      expect(markup).toContain(`data-level="${lvl.alpha}"`);
      expect(markup).toContain(count(lvl.limit_exceptions));
      expect(markup).toContain(count(lvl.n_over_limit));
      expect(markup).toContain(pct(lvl.share_over_limit, 1));
      expect(markup).toContain(formatNumber(lvl.exceptions.q95, 'en', { decimals: 1 }));
      expect(markup).toContain('MAR32.18');
      expect(markup).toContain(lvl.basis);
      expect(charts.length).toBe(0);
    }
  });

  it('the variants table gives the deficiency, the share caught with its interval and the intended test', () => {
    const markup = html(<C13VariantsTable variants={[{ id: variant.variant_id, title: { en: 'Missing basis', es: 'Base omitida' }, v: variant }]} onPick={() => undefined} current={variant.variant_id} />);
    expect(markup).toContain(`data-variant="${variant.variant_id}"`);
    expect(markup).toContain(pct(o.detection.share_amber_or_red, 1));
    expect(markup).toContain('Spearman');
    expect(markup).toContain('data-synthetic="true"');
  });

  it('the context gives the generator and its true model, the thresholds with MAR32.42, the limits and all six deficiencies, and the synthetic notice', () => {
    const markup = html(<C13ContextView sel={sel} />);
    expect(markup).toContain(escapeHtml(fit.generator.true_risk_model.en));
    expect(markup).toContain(escapeHtml(fit.generator.notice.en));
    expect(markup).toContain('MAR32.42');
    for (const d of fit.deficiencies) expect(markup).toContain(`data-deficiency="${d.deficiency_id}"`);
    for (const l of fit.desk_limits) expect(markup).toContain(l.reference);
    expect(markup).toContain(escapeHtml(o.sign_convention.definition.en));
    expect(markup).toContain(seedText(fit.replication_plan.seed_base, 'en')); // a seed is an identifier, written whole (U16-R2 b06 m7)
    expect(markup).toContain('data-fixture="true"');
  });

  it('the findings carry the fixture notice and the finding', () => {
    const markup = html(<C13FindingsView sel={sel} />);
    expect(markup).toContain('data-fixture="true"');
    expect(markup).toContain(escapeHtml(variant.findings[0].title.en));
  });

  it('is written in Spanish in the Spanish interface', () => {
    setLang('es');
    const markup = html(<DetectionView sel={sel} />);
    expect(markup).toContain('Deficiencia conocida');
    expect(markup).not.toContain('Known deficiency');
    expect(markup).toContain(formatNumber(o.detection.share_amber_or_red, 'es', { percent: true, decimals: 2 }));
  });
});

function RailSection({ at }: { at: number }) {
  const inst = useC13Instrument(data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C13 rail', () => {
  afterEach(() => setLang('en'));

  it('has two sections, each with one control and one read-out', () => {
    function Sections() {
      const inst = useC13Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('level|statistic');
    for (const at of [0, 1]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
    expect(railHtml(0)).toContain('data-control="c13-level"');
    expect(railHtml(1)).toContain('data-control="c13-statistic"');
  });

  it('the level read-out gives the exceptions against the limit; the statistic read-out the zone counts of the statistic chosen', () => {
    const lvl = o.desk_backtest.find((l) => l.alpha === sel.alpha)!;
    const a = html(<LevelReadout sel={sel} />);
    expect(a).toContain(count(lvl.limit_exceptions));
    expect(a).toContain(pct(lvl.share_over_limit, 1));
    const z = o.pla.zones.spearman;
    const b = html(<StatisticReadout sel={{ ...sel, statistic: 'spearman' }} />);
    expect(b).toContain(count(z.green));
    expect(b).toContain(count(z.amber));
    expect(b).toContain(count(z.red));
  });

  it('is written in Spanish', () => {
    expect(railHtml(1, 'es')).toContain('Estadístico');
  });
});
