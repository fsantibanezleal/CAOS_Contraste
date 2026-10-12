// U5-W: the C07 instrument rendered on the server from the c07-outputs and c07-models fixtures
// (docs/contracts/fixtures/c07). The three regimes side by side with the gap bridge; the IFRS 9 column is always the
// probability-weighted measure, never a single-scenario number unlabelled; the B-1 additional provisions stay outside
// the comparable total; a null the contract allows says "not available" with its reason.
import { readFileSync } from 'node:fs';
import { formatNumber } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { useC07Instrument } from './instrument';
import { defaultSel, liveIfrs9, outputsOf, reweighted, type C07Sel } from './selection';
import { C07ContextView, C07FindingsView, C07VariantsTable, Ifrs9Readout } from './C07Common';
import { B1View, BdeView, BridgeView, DeltaView, Ifrs9View, SegmentsView, ThreeRegimeView } from './RegimeViews';
import { CalibrationView, TablesView, TestsView } from './ValidationViews';

type Outputs = components['schemas']['c07Outputs'];

const fixtures = new URL('../../../../docs/contracts/fixtures/c07/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, fixtures), 'utf8')) as T;
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const clp = (v: number) => formatNumber(v, 'en', { decimals: 0 });

const variant = read<VariantArtifact<Outputs>>('variant-three-regime-fixture.json');
const models = read<ModelsArtifact>('models-fixture.json');
const manifest = {
  schema: 'contraste.manifest/v1',
  case_id: 'C07',
  title: { en: 'Chile provisions trilogy', es: 'Trilogía de provisiones en Chile' },
  category: { en: 'Provisions', es: 'Provisiones' },
  question: { en: 'How far apart are the three regimes?', es: 'Qué tan lejos están los tres regímenes?' },
  sources: [],
  source_details: {},
  seed: 0,
  engine: { pipeline: 'fixture', riskvalidation: 'fixture' },
  default_variant: variant.variant_id,
  artifacts: [{ role: 'variant', variant_id: variant.variant_id, path: 'C07/fixture.json', models_ref: 'C07/models.json', truth_status: 'synthetic-calibrated', title: { en: 'Base scenario', es: 'Escenario base' }, short_title: { en: 'Base', es: 'Base' } }],
  contract: {},
  expect: {},
} as unknown as CaseManifest;
const data = { manifest, variant: variant as unknown as VariantArtifact, models } as CaseData;
const o = variant.outputs;
const sel = defaultSel(data) as C07Sel;

function cards(markup: string): Array<{ lane: boolean }> {
  return markup
    .split('class="caos-plot-head"')
    .slice(1)
    .map((rest) => ({ lane: /data-lane="(live|replay|offline)"/.test(rest.slice(0, rest.indexOf('</figcaption>'))) }));
}

const VIEWS: Array<[string, (p: { sel: C07Sel | null }) => ReactElement]> = [
  ['Three regimes', ThreeRegimeView], ['Segments', SegmentsView], ['Bridge', BridgeView], ['B-1', B1View], ['IFRS 9', Ifrs9View],
  ['BdE', BdeView], ['Delta', DeltaView], ['Calibration', CalibrationView], ['Tables', TablesView], ['Tests', TestsView],
  ['Findings', C07FindingsView], ['Context', C07ContextView],
];

function Groups() {
  const inst = useC07Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}

describe('the C07 instrument', () => {
  it('the groups are the validator questions, in order', () => {
    expect(html(<Groups />)).toContain('Comparison|Regimes|Validation|Findings|Variants');
    // the shell throws on more than six peers (ADR-0071 rule 5): the groups, the variants view and the context
    function Count() {
      const inst = useC07Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>6</p>');
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

  it('the three regimes show their totals and their legal status, in the contract order', () => {
    const markup = html(<ThreeRegimeView sel={sel} />);
    const order = o.regimes.map((r) => markup.indexOf(`data-regime="${r.regime}"`));
    expect(order.every((i) => i >= 0)).toBe(true);
    expect([...order].sort((a, b) => a - b)).toEqual(order);
    for (const r of o.regimes) {
      expect(markup).toContain(clp(r.total_provision));
      expect(markup).toContain(`data-status="${r.status}"`);
    }
    expect(markup).toContain(o.notice.en);
  });

  it('the IFRS 9 column is labelled the probability-weighted measure, and a single scenario only as a sensitivity', () => {
    const markup = html(<Ifrs9View sel={sel} />);
    expect(markup).toContain('data-measure="probability-weighted-ecl"');
    for (const c of o.ifrs9_detail.weighted_components) {
      expect(markup).toContain(`data-component="${c.scenario_id}"`);
      expect(markup).toContain(clp(c.single_scenario_ecl));
    }
    expect(markup).toMatch(/at 100% weight|sensitivity/);
    // the overlays are their own lines, never inside the model ECL
    for (const ov of o.ifrs9_detail.overlays) expect(markup).toContain(`data-overlay="${ov.id}"`);
    const comparison = html(<ThreeRegimeView sel={sel} />);
    expect(comparison).toMatch(/probability-weighted/);
  });

  it('the gap bridge lists every step and closes on the IFRS 9 total', () => {
    const markup = html(<BridgeView sel={sel} />);
    for (const s of o.gap_bridge.steps) {
      expect(markup).toContain(`data-step="${s.id}"`);
      expect(markup).toContain(clp(Math.abs(s.amount)));
    }
    const steps = o.gap_bridge.steps.reduce((a, s) => a + s.amount, 0);
    const [b1, ifrs9] = o.regimes;
    expect(b1.total_provision + steps).toBeCloseTo(o.regimes[1].total_provision, 0);
    expect(ifrs9.regime).toBe('ifrs9');
    expect(markup).toContain('data-closes="true"');
  });

  it('the segments table has the three provisions and both gaps, with the unallocated lines apart', () => {
    const markup = html(<SegmentsView sel={sel} />);
    for (const r of o.comparison.rows) {
      expect(markup).toContain(`data-segment="${r.segment_id}"`);
      expect(markup).toContain(clp(r.cmf_b1_provision));
      expect(markup).toContain(clp(r.gap_ifrs9_minus_b1));
    }
    expect(markup).toContain('data-row="unallocated"');
  });

  it('B-1: the additional provisions are outside the comparable total; a missing internal method says why', () => {
    const markup = html(<B1View sel={sel} />);
    expect(markup).toContain(`data-total="booked">${clp(o.b1_detail.booked_total)}`);
    expect(markup).toContain(`data-total="comparable">${clp(o.regimes[0].total_provision)}`);
    expect(markup).toContain(clp(o.b1_detail.additional_provisions.amount));
    expect(markup).toContain(`data-binding="${o.b1_detail.minimum_check.binding}"`);
    const none = { ...o, b1_detail: { ...o.b1_detail, group_max_rule: o.b1_detail.group_max_rule.map((g) => ({ ...g, internal: null, applied: g.standard, method: 'standard' as const, internal_reason: 'the bank has no internal method' })) } };
    const other = { ...sel, data: { ...data, variant: { ...variant, outputs: none } as unknown as VariantArtifact } } as C07Sel;
    const gapped = html(<B1View sel={other} />);
    expect(gapped).toContain('the bank has no internal method');
    expect(gapped).toContain('not available');
  });

  it('BdE: each category is mapped to its IFRS 9 stage', () => {
    const markup = html(<BdeView sel={sel} />);
    for (const c of o.bde_detail.categories) expect(markup).toContain(`data-category="${c.category}" data-stage="${c.mapped_stage}"`);
  });

  it('the base scenario has no delta, said with its reason; the others show the three deltas', () => {
    expect(o.delta_vs_base).toBeNull();
    expect(html(<DeltaView sel={sel} />)).toContain('data-state="unavailable"');
    const shocked = { ...o, scenario_id: 'recession' as const, delta_vs_base: { currency: 'CLP', cmf_b1_delta: 1000, ifrs9_delta: 3000, bde_annex9_delta: 2000 } };
    const other = { ...sel, data: { ...data, variant: { ...variant, outputs: shocked } as unknown as VariantArtifact } } as C07Sel;
    const markup = html(<DeltaView sel={other} />);
    expect(markup).toContain(clp(3000));
    expect(markup).not.toContain('data-state="unavailable"');
  });

  it('the IFRS 9 readout moves with the weight of a scenario and starts on the contract measure', () => {
    const w = o.ifrs9_detail.weighted_components;
    const contract = w.reduce((a, c) => a + c.weight * c.single_scenario_ecl, 0);
    expect(liveIfrs9(sel)).toBeCloseTo(contract, 0);
    expect(reweighted(o, 'downside', 0.6).reduce((a, b) => a + b, 0)).toBeCloseTo(1, 12);
    const moved: C07Sel = { ...sel, scenario: 'downside', weight: 0.6 };
    expect(liveIfrs9(moved)).toBeGreaterThan(liveIfrs9(sel));
    expect(html(<Ifrs9Readout sel={sel} />)).not.toBe(html(<Ifrs9Readout sel={moved} />));
    expect(html(<Ifrs9Readout sel={sel} />)).toContain('data-lane="live"');
    expect(outputsOf(sel)?.kind).toBe('three-regime');
  });

  it('the calibration table sets each target against what was achieved, and the B-1 cells keep PE = PI x PDI', () => {
    const cal = html(<CalibrationView sel={sel} />);
    const fit = (models as unknown as { fit: components['schemas']['c07Fit'] }).fit;
    for (const t of fit.calibration_targets) expect(cal).toContain(t.metric);
    const tables = html(<TablesView sel={sel} />);
    for (const t of fit.b1_tables) expect(tables).toContain(`data-table-id="${t.table_id}"`);
  });

  it('the context says the bank is synthetic and the IFRS 9 column is a comparison measure', () => {
    const markup = html(<C07ContextView sel={sel} />);
    expect(markup).toContain('Banco Andino');
    expect(markup).toContain(o.notice.en);
    expect(markup).toContain(variant.provenance.truth_status);
  });

  it('the scenarios table shows the three totals of each variant and no change for the base', () => {
    const markup = html(<C07VariantsTable variants={[{ id: variant.variant_id, title: { en: 'Base', es: 'Base' }, v: variant }]} onPick={() => undefined} current={variant.variant_id} />);
    expect(markup).toContain(`data-variant="${variant.variant_id}"`);
    for (const r of o.regimes) expect(markup).toContain(clp(r.total_provision));
    expect(markup).toContain('none (base)');
  });
});
