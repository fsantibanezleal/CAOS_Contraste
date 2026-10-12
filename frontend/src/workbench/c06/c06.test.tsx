// U5-W: the C06 instrument rendered on the server from the c06-outputs and c06-models fixtures
// (docs/contracts/fixtures/c06). Every view carries its lane and its numbers are the fixture's, read back from the
// markup; a field the contract allows to be null says "not available" with its reason, never an empty chart.
import { readFileSync } from 'node:fs';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { useC06Instrument } from './instrument';
import { defaultSel, liveEcl, outputsOf, rescaled, scenarioEcl, type C06Sel } from './selection';
import { C06ContextView, C06FindingsView, WeightReadout } from './C06Common';
import { NonLinearityView, SicrView, TermStructureView } from './TermViews';
import { StageFlowView, StageSummaryView, WaterfallView, WeightsView } from './ImpactViews';
import { BacktestView, DecileView, IdentitiesView, LadderView, RungsView, TestsView } from './ValidationViews';

type Outputs = components['schemas']['c06Outputs'];

const fixtures = new URL('../../../../docs/contracts/fixtures/c06/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, fixtures), 'utf8')) as T;
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const money = (v: number) => formatNumber(v, 'en', { decimals: 2 });

const variant = read<VariantArtifact<Outputs>>('variant-reporting-date-fixture.json');
const models = read<ModelsArtifact>('models-fixture.json');
const manifest = {
  schema: 'contraste.manifest/v1',
  case_id: 'C06',
  title: { en: 'Mortgage lifetime PD, IFRS 9 staging and ECL', es: 'PD de vida de hipotecas, etapas y PCE de IFRS 9' },
  category: { en: 'Provisions', es: 'Provisiones' },
  question: { en: 'What does the allowance move by?', es: 'Por qué se mueve la cobertura?' },
  sources: [],
  source_details: {},
  seed: 0,
  engine: { pipeline: 'fixture', riskvalidation: 'fixture' },
  default_variant: variant.variant_id,
  artifacts: [{ role: 'variant', variant_id: variant.variant_id, path: 'C06/fixture.json', models_ref: 'C06/models.json', truth_status: 'real-outcomes', title: { en: 'Fixture 2020-06', es: 'Ejemplo 2020-06' }, short_title: { en: '2020-06', es: '2020-06' } }],
  contract: {},
  expect: {},
} as unknown as CaseManifest;
const data = { manifest, variant: variant as unknown as VariantArtifact, models } as CaseData;
const o = variant.outputs;
const sel = defaultSel(data) as C06Sel;

function cards(markup: string): Array<{ lane: boolean }> {
  return markup
    .split('class="caos-plot-head"')
    .slice(1)
    .map((rest) => ({ lane: /data-lane="(live|replay|offline)"/.test(rest.slice(0, rest.indexOf('</figcaption>'))) }));
}

const VIEWS: Array<[string, (p: { sel: C06Sel | null }) => ReactElement]> = [
  ['Term structures', TermStructureView], ['SICR', SicrView], ['Non-linearity', NonLinearityView], ['Ladder', LadderView],
  ['Backtest', BacktestView], ['Deciles', DecileView], ['Rungs', RungsView], ['Identities', IdentitiesView], ['Tests', TestsView],
  ['Stage flow', StageFlowView], ['Waterfall', WaterfallView], ['Weights', WeightsView], ['Stage summary', StageSummaryView],
  ['Findings', C06FindingsView], ['Context', C06ContextView],
];

function Groups() {
  const inst = useC06Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}

function Other() {
  const inst = useC06Instrument({ ...data, manifest: { ...manifest, case_id: 'C05' } as CaseManifest }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C06 instrument', () => {
  it('the instrument answers for C06 only, with the groups in the validator order', () => {
    expect(html(<Groups />)).toContain('Model|Validation|Impact|Findings|Variants');
    expect(html(<Other />)).toContain('null');
  });

  it('every view renders and carries its lane', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
    }
  });

  it('a view with no selection says loading, not an empty chart', () => {
    for (const [name, View] of VIEWS) expect(html(<View sel={null} />), name).toContain('data-state="loading"');
  });

  it('the term structures list every scenario and the weighted curve, with the cumulative PD of the fixture', () => {
    const markup = html(<TermStructureView sel={sel} />);
    for (const s of [...o.scenarios.map((x) => x.id), 'weighted']) expect(markup).toContain(`data-scenario="${s}"`);
    const w = o.term_structures.find((t) => t.scenario_id === 'weighted' && t.segment_id === sel.segment)!;
    expect(markup).toContain(formatNumber(w.cumulative_pd[w.cumulative_pd.length - 1], 'en', { percent: true, decimals: 3 }));
    expect(html(<TermStructureView sel={{ ...sel, measure: 'hazard' }} />)).not.toBe(markup);
  });

  it('the SICR view names the multiplier schedule, the absolute floor, the threefold backstop and each trigger', () => {
    const markup = html(<SicrView sel={sel} />);
    for (const m of o.settings.sicr.multiplier_schedule) expect(markup).toContain(`data-multiplier="${m.multiplier}"`);
    expect(markup).toContain(`data-threefold="${o.settings.sicr.threefold_ratio}"`);
    expect(markup).toContain('data-floor=');
    for (const p of o.sicr_points) expect(markup).toContain(`data-account="${p.account_id}" data-trigger="${p.trigger}"`);
  });

  it('the waterfall draws every line, the overlays as their own lines apart from the model ECL', () => {
    const markup = html(<WaterfallView sel={sel} />);
    for (const l of o.waterfall.lines) expect(markup).toContain(`data-line="${l.id}"`);
    for (const ov of o.overlays) {
      expect(markup).toContain(`data-overlay="${ov.id}"`);
      expect(markup).toContain(money(ov.amount));
    }
    const model = o.stage_summary.rows.reduce((a, r) => a + r.ecl, 0);
    expect(markup).toContain('data-total="model-ecl"');
    expect(markup).toContain(money(model));
    expect(markup).toContain('data-total="overlays"');
    // the overlay amount is never inside the model ECL line
    expect(model + o.overlays.reduce((a, x) => a + x.amount, 0)).toBeCloseTo(o.waterfall.lines.find((l) => l.kind === 'closing')!.amount, 2);
  });

  it('the stage flow lists every flow of the fixture with its accounts and gross carrying amount', () => {
    const markup = html(<StageFlowView sel={sel} />);
    for (const f of o.stage_flows.flows) expect(markup).toContain(`data-flow="${f.source}:${f.target}"`);
    expect(markup).toContain(o.stage_flows.from_date);
    expect(markup).toContain(o.stage_flows.to_date);
  });

  it('the weights: the live ECL is the weighted sum of the scenario ECLs and moves with the weight', () => {
    const by = scenarioEcl(o);
    const contract = o.scenarios.reduce((a, s) => a + s.weight * by[s.id], 0);
    expect(liveEcl(sel)).toBeCloseTo(contract, 6);
    expect(contract).toBeCloseTo(o.stage_summary.rows.reduce((a, r) => a + r.ecl, 0), 2);
    const down = o.scenarios.find((s) => s.id === 'down')!;
    const moved: C06Sel = { ...sel, scenario: 'down', weight: 0.6 };
    expect(rescaled(o, 'down', 0.6).reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12);
    expect(rescaled(o, 'down', down.weight)).toEqual(o.scenarios.map((s) => s.weight));
    expect(liveEcl(moved)).toBeGreaterThan(liveEcl(sel));
    expect(html(<WeightReadout sel={sel} />)).not.toBe(html(<WeightReadout sel={moved} />));
    expect(html(<WeightReadout sel={sel} />)).toContain('data-lane="live"');
  });

  it('the simplex lists every grid point with staging recomputed against frozen', () => {
    const markup = html(<WeightsView sel={sel} />);
    expect(markup.match(/data-weights="/g)?.length).toBe(o.weight_grid.points.length);
    const p = o.weight_grid.points[1];
    expect(markup).toContain(money(p.ecl_recomputed));
    expect(markup).toContain(money(p.ecl_frozen));
    expect(html(<WeightsView sel={{ ...sel, surface: 'stage2' }} />)).not.toBe(markup);
  });

  it('the non-linearity panel reads the contract values', () => {
    const markup = html(<NonLinearityView sel={sel} />);
    const n = o.non_linearity;
    expect(markup).toContain(formatNumber(n.pd_weighted, 'en', { percent: true, decimals: 3 }));
    expect(markup).toContain(formatNumber(n.pd_at_mean_z, 'en', { percent: true, decimals: 3 }));
    expect(markup).toContain(money(n.ecl_weighted));
    expect(markup).toContain(money(n.ecl_at_mean_path));
  });

  it('an unobserved horizon is not available with its reason, never a zero', () => {
    const rows = o.lifetime_backtest.rows.map((r, i) => (i === 0 ? { ...r, observed_cumulative_pd: null, gap: null, brier: null, reason: 'the cohort is younger than the horizon' } : r));
    const gapped = { ...sel, data: { ...data, variant: { ...variant, outputs: { ...o, lifetime_backtest: { rows } } } as unknown as VariantArtifact } } as C06Sel;
    const markup = html(<BacktestView sel={gapped} />);
    expect(markup).toContain('the cohort is younger than the horizon');
    expect(markup).toContain('not available');
    const rungs = html(<RungsView sel={sel} />);
    for (const r of o.rung_comparison) if (r.reason) expect(rungs).toContain(r.reason);
  });

  it('the context says the data is a fixture and why Freddie Mac is not there', () => {
    const markup = html(<C06ContextView sel={sel} />);
    expect(markup).toContain(o.data_status.freddie_mac_reason as string);
    expect(markup).toContain(o.data_status.notice.en);
    expect(markup).toContain(variant.provenance.truth_status);
  });

  it('the identities close on the one tolerance basis', () => {
    const markup = html(<IdentitiesView sel={sel} />);
    for (const r of o.reconciliation.allowance) expect(markup).toContain(`data-stage="${r.stage}"`);
    expect(markup).not.toContain('data-closes="false"');
    expect(outputsOf(sel)?.kind).toBe('reporting-date');
  });
});
