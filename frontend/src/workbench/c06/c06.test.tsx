// U5-W: the C06 instrument rendered on the server from the c06-outputs and c06-models fixtures
// (docs/contracts/fixtures/c06). Every view carries its lane and its numbers are the fixture's, read back from the
// markup; a field the contract allows to be null says "not available" with its reason, never an empty chart.
import { readFileSync } from 'node:fs';
import { formatNumber, useLangStore } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { useC06Instrument } from './instrument';
import { axisScale, compactMoney } from './format';
import { truthStatusText } from '../c05/selection';
import { defaultSel, liveEcl, outputsOf, rescaled, scenarioEcl, type C06Sel } from './selection';
import { C06ContextView, C06FindingsView, C06VariantsTable, CurveReadout, WeightReadout } from './C06Common';
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
    // the shell throws on more than six peers (ADR-0071 rule 5): the groups, the variants view and the context are six
    function Count() {
      const inst = useC06Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>6</p>');
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
    for (const r of o.rung_comparison) if (r.reason) expect(rungs).toContain(r.reason.en);
  });

  it('the context says the data is a fixture and why Freddie Mac is not there', () => {
    const markup = html(<C06ContextView sel={sel} />);
    expect(markup).toContain(o.data_status.freddie_mac_reason!.en);
    expect(markup).toContain(o.data_status.notice.en);
    expect(markup).toContain(truthStatusText(variant.provenance.truth_status).en);
  });

  it('the identities close on the one tolerance basis', () => {
    const markup = html(<IdentitiesView sel={sel} />);
    for (const r of o.reconciliation.allowance) expect(markup).toContain(`data-stage="${r.stage}"`);
    expect(markup).not.toContain('data-closes="false"');
    expect(outputsOf(sel)?.kind).toBe('reporting-date');
  });

  it('the reporting dates table lists each variant with its model ECL by stage and the overlays apart', () => {
    const markup = html(<C06VariantsTable variants={[{ id: variant.variant_id, title: { en: '2020-06', es: '2020-06' }, v: variant }]} onPick={() => undefined} current={variant.variant_id} />);
    expect(markup).toContain(`data-variant="${variant.variant_id}"`);
    for (const r of o.stage_summary.rows) expect(markup).toContain(money(r.ecl));
    expect(markup).toContain(money(o.overlays.reduce((a, x) => a + x.amount, 0)));
    expect(markup).toContain(o.reporting_date);
  });

  it('a variant without overlays and without Freddie Mac says so, not a chart of zeros', () => {
    const bare = { ...sel, data: { ...data, variant: { ...variant, outputs: { ...o, overlays: [] } } as unknown as VariantArtifact } } as C06Sel;
    expect(html(<WaterfallView sel={bare} />)).toContain('This variant carries no overlay.');
  });
});

// The gate on the real committed bake (U5-P1) failed in the rail and in two drawings: these tests read the real
// document, whose scenario labels are long and whose amounts have eleven digits.
const realDir = new URL('../../../../data/derived/C06/', import.meta.url);
const realVariant = JSON.parse(readFileSync(new URL('rd-2020-06.json', realDir), 'utf8')) as VariantArtifact<Outputs>;
const realModels = JSON.parse(readFileSync(new URL('models-rd-2020-06.json', realDir), 'utf8')) as ModelsArtifact;
const realData = { manifest, variant: realVariant as unknown as VariantArtifact, models: realModels } as CaseData;
const escape = (t: string) => t.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;');
const setLang = (lang: 'en' | 'es') => {
  (useLangStore.getInitialState() as { lang: string }).lang = lang;
  useLangStore.setState({ lang });
};

function RailSection({ at }: { at: number }) {
  const inst = useC06Instrument(realData, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};
const RAW_AMOUNT = /\d{1,3}(?:[,. ]\d{3}){3,}/;

describe('the C06 rail on the real document', () => {
  afterEach(() => setLang('en'));

  it('prints no raw amount in the rail: money is compact with its unit, in both languages', () => {
    for (const at of [0, 1, 2, 3]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
    expect(railHtml(0)).toContain('bn USD');
    expect(railHtml(0, 'es')).toContain('mil M USD');
    expect(railHtml(3)).toContain('bn USD');
  });

  it('compact money keeps the unit with the value and leaves a null as null', () => {
    expect(compactMoney(19_584_239_970.51, 'USD').unit).toEqual({ en: 'bn USD', es: 'mil M USD' });
    expect(compactMoney(19_584_239_970.51, 'USD').value).toBeCloseTo(19.58423997, 6);
    expect(compactMoney(590_890_026.3, 'CLP').unit).toEqual({ en: 'm CLP', es: 'M CLP' });
    expect(compactMoney(1234.5, 'USD').unit).toEqual({ en: 'USD', es: 'USD' });
    expect(compactMoney(null, 'USD').value).toBeNull();
    expect(axisScale(30_000_000_000, 'USD')).toEqual({ div: 1e9, unit: { en: 'bn USD', es: 'mil M USD' } });
  });

  it('the scenario, the segment and the account are one select control each, not columns of chips', () => {
    const scenarios = railHtml(0);
    expect(scenarios).toMatch(/data-control="c06-scenario"[^>]*><label[^>]*>Scenario<\/label><select/);
    const curves = railHtml(1);
    expect(curves).toMatch(/data-control="c06-segment"[^>]*><label[^>]*>Segment<\/label><select/);
    const account = railHtml(2);
    expect(account).toMatch(/data-control="c06-account"[^>]*><label[^>]*>Account<\/label><select/);
    expect(account.match(/<option/g)?.length).toBe(realVariant.outputs.account_curves.length);
    // the measure keeps its three chips: a small choice
    expect(curves).toMatch(/data-control="c06-measure"[^>]*><span[^>]*>Measure<\/span><div class="caos-chip-row"/);
  });

  it('a long scenario label is shortened in the option and the whole label is its title', () => {
    const long = realVariant.outputs.scenarios.find((x) => x.id === 'adverse')!.label.en;
    expect(long.length).toBeGreaterThan(40);
    const markup = railHtml(0);
    expect(markup).toContain(`title="${escape(long)}`);
    expect(markup).not.toContain(`>${escape(long)}</option>`);
    expect(markup).toContain('…');
  });

  it('the rail is split in sections that each fit the rail: one control group and one read-out apiece', () => {
    function Sections() {
      const inst = useC06Instrument(realData, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('scenarios|curves|account|simplex');
    for (const at of [0, 1, 2, 3]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('the curve read-out moves with the measure and the segment', () => {
    function Curve({ measure }: { measure: 'cumulative' | 'hazard' }) {
      const base = defaultSel(realData) as C06Sel;
      return <CurveReadout sel={{ ...base, measure }} />;
    }
    const f = html(<Curve measure="cumulative" />);
    expect(f).toContain('F(12 m)');
    expect(html(<Curve measure="hazard" />)).toContain('h(12 m)');
    expect(f).not.toContain('not available');
  });

  it('a read-out label never carries a scenario name from the document', () => {
    expect(railHtml(0)).not.toMatch(/Weight, [A-Z]/);
    expect(railHtml(0, 'es')).not.toMatch(/Peso, [A-Z]/);
  });

  it('the findings card fills its stage, so the drawn views keep the floor of ADR-0071 rule 8', () => {
    expect(html(<C06FindingsView sel={defaultSel(realData)} />)).toMatch(/<figure class="caos-plot fill"/);
  });
});
