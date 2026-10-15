// U10-W: the C14 instrument rendered on the server from the c14-outputs and c14-models fixtures
// (docs/contracts/fixtures/c14). A positive delta EVE or delta NII is shown as a loss with the convention named; every
// result can be read with and without the behavioural deposit assumptions; the outlier threshold is a line; the NMD caps
// are shown with and without the cap; a null field says "not available" with its reason; no view draws a number the
// fixture does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, readIrrbbFixture, setLang } from './testkit';
import { C14_FIT, C14_OUTPUTS } from './descriptor';
import { useC14Instrument } from './instrument';
import { amount, cell, defaultSel, nmdModelOf, outputsOf, scenarioOf, type C14Sel } from './selection';
import { C14ContextView, C14FindingsView, C14VariantsTable, CalibrationReadout, NmdReadout, SegmentReadout, ShockReadout } from './C14Common';
import { EveByShockView, OutlierView, ShapesView, outlierChart } from './ShockViews';
import { CapsView, ChangesView, ReplicatingView, WithWithoutView } from './BehaviouralViews';
import { DynamicNiiView, EarEvarView, GapView } from './NiiViews';

type Outputs = components['schemas']['c14Outputs'];

const variant = readIrrbbFixture<VariantArtifact<Outputs>>('c14', 'variant-valuation-date-2021-q4-fixture.json');
const variant22 = readIrrbbFixture<VariantArtifact<Outputs>>('c14', 'variant-valuation-date-2022-q4-fixture.json');
const models = readIrrbbFixture<ModelsArtifact>('c14', 'models-fixture.json');
const title = { en: 'IRRBB on a USD balance sheet', es: 'IRRBB sobre un balance en USD' };
const data = fixtureData('C14', variant as unknown as VariantArtifact, models, title);
const o = variant.outputs;
const sel = defaultSel(data) as C14Sel;
const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const NA = formatNumber(null, 'en');
const withVariant = (v: VariantArtifact<Outputs>): C14Sel => defaultSel({ ...data, variant: v as unknown as VariantArtifact }) as C14Sel;
const clone = () => structuredClone(variant) as VariantArtifact<Outputs>;

const VIEWS: Array<[string, (p: { sel: C14Sel | null }) => ReactElement]> = [
  ['Delta EVE by shock', EveByShockView], ['Shock shapes', ShapesView], ['Outlier test', OutlierView],
  ['With and without', WithWithoutView], ['Replicating portfolio', ReplicatingView], ['Caps', CapsView], ['Changes', ChangesView],
  ['Gap', GapView], ['Dynamic NII', DynamicNiiView], ['EaR and EVaR', EarEvarView],
  ['Findings', C14FindingsView], ['Context', C14ContextView],
];

function Names() {
  const inst = useC14Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC14Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C09' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C14 contract descriptors', () => {
  it('describe the fixtures key by key, in both directions', () => {
    for (const v of [variant, variant22]) expect(conform(v.outputs, C14_OUTPUTS)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C14_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone();
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).ear_evar;
    const found = conform(odd.outputs, C14_OUTPUTS).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/ear_evar: declared by the web, not written by the pipeline/);
  });
});

describe('the C14 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C14 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('Shocks|Deposit behaviour|NII and dynamics|Findings|Valuation dates');
    function Count() {
      const inst = useC14Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 1 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>5</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('valuation-date');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('delta EVE by shock gives every shock in currency and as a share of Tier 1, a loss as positive, with the convention named', () => {
    const markup = html(<EveByShockView sel={sel} />);
    const s = scenarioOf(o, '2024', 'behavioural')!;
    for (const r of s.shocks) {
      expect(markup).toContain(`data-shock="${r.shock}"`);
      expect(markup).toContain(cell(r.delta_eve, 'en'));
      expect(markup).toContain(pct(r.delta_eve_share_tier1));
    }
    expect(markup).toContain(escapeHtml(o.sign_convention.statement.en));
    expect(markup).toContain('USD thousands');
    expect(markup).toContain('data-col="other-calibration"');
  });

  it('delta NII is given for the two parallel shocks only; the others say not available with the contract reason', () => {
    const markup = html(<EveByShockView sel={sel} />);
    const s = scenarioOf(o, '2024', 'behavioural')!;
    for (const r of s.shocks.filter((x) => x.delta_nii !== null)) expect(markup).toContain(cell(r.delta_nii, 'en'));
    expect(markup).toContain(NA);
    expect(markup).toContain(escapeHtml(s.shocks[2].delta_nii_reason!.en));
  });

  it('the shock sizes are named with their origin, in basis points', () => {
    const markup = html(<EveByShockView sel={sel} />);
    expect(markup).toContain('Basel SRP31 Table 2 (2024)');
    expect(markup).toContain('200 bp');
    expect(markup).toContain('300 bp');
    expect(markup).toContain('225 bp');
    expect(html(<EveByShockView sel={{ ...sel, calibration: '2016' }} />)).toContain('Basel d368 Annex 2 (2016)');
  });

  it('a shock size that is a Contraste estimate carries its label and its method', () => {
    const odd = clone();
    const sc = odd.outputs.scenarios[0];
    (sc as { shock_size: unknown }).shock_size = { currency: 'XYZ', parallel_bp: 250, short_bp: 300, long_bp: 200, origin: 'contraste-estimate', label: { en: 'Estimate of the desk', es: 'Estimación de la mesa' }, method: 'rolling six-month changes' };
    const markup = html(<EveByShockView sel={withVariant(odd)} />);
    expect(markup).toContain('Estimate of the desk');
    expect(markup).toContain('rolling six-month changes');
    expect(markup).toContain('not a regulatory parameter');
  });

  it('the contractual assumption shows the contractual numbers and not the behavioural ones', () => {
    const behavioural = html(<EveByShockView sel={sel} />);
    const contractual = html(<EveByShockView sel={{ ...sel, nmd: 'contractual' }} />);
    const sc = scenarioOf(o, '2024', 'contractual')!;
    expect(contractual).toContain(cell(sc.shocks[0].delta_eve, 'en'));
    expect(contractual).not.toContain(cell(scenarioOf(o, '2024', 'behavioural')!.shocks[0].delta_eve, 'en') + '<');
    expect(behavioural).toContain(cell(scenarioOf(o, '2024', 'behavioural')!.shocks[0].delta_eve, 'en'));
    expect(contractual).toContain('all overnight');
  });

  it('a scenario the document does not carry is unavailable, not an empty chart', () => {
    const odd = clone();
    odd.outputs.scenarios = odd.outputs.scenarios.filter((s) => s.nmd_assumption === 'behavioural') as unknown as Outputs['scenarios'];
    const markup = html(<EveByShockView sel={{ ...withVariant(odd), nmd: 'contractual' }} />);
    expect(markup).toContain('data-state="unavailable"');
  });

  it('the shock shapes give the six curves, the constants of the shape and the buckets where the floor binds', () => {
    const markup = html(<ShapesView sel={sel} />);
    const s = scenarioOf(o, '2024', 'behavioural')!;
    for (const r of s.shocks) {
      expect(markup).toContain(`data-shock="${r.shock}"`);
      expect(markup).toContain(`data-floored="${r.floor_bound_buckets.length}"`);
    }
    const shape = (models as unknown as { fit: { shock_shape: { short_form: string; long_form: string; reference: string } } }).fit.shock_shape;
    expect(markup).toContain(escapeHtml(shape.short_form));
    expect(markup).toContain(escapeHtml(shape.long_form));
    expect(markup).toContain(escapeHtml(shape.reference));
    expect(markup).toContain(pct(-0.65));
  });

  it('the outlier threshold is a line at 15 percent of Tier 1, and each scenario gives its ratio and whether it breached', () => {
    const chart = outlierChart(sel);
    expect(chart?.yMarks).toEqual([expect.objectContaining({ y: 0.15, tone: 'bad' })]);
    expect((chart?.yMarks?.[0].label as { en: string }).en).toContain('15%');
    expect(chart?.series.length).toBe(2);
    expect(chart?.x.values).toEqual([1, 2, 3, 4, 5, 6]);
    const markup = html(<OutlierView sel={sel} />);
    expect(markup).toContain('data-threshold="0.15"');
    for (const s of o.scenarios) {
      expect(markup).toContain(`data-scenario="${s.calibration}-${s.nmd_assumption}"`);
      expect(markup).toContain(pct(s.outlier.ratio));
    }
    expect(markup).toContain('data-breached="true"');
    expect(markup).toContain('data-breached="false"');
    expect(markup).toContain(escapeHtml(o.scenarios[0].outlier.reference));
    expect(outlierChart(null)).toBeNull();
  });

  it('with and without the behavioural assumption: every shock gives both numbers and the difference, for both calibrations', () => {
    const markup = html(<WithWithoutView sel={sel} />);
    expect(o.behavioural_comparison.length).toBe(12);
    for (const c of o.behavioural_comparison) {
      expect(markup).toContain(`data-calibration="${c.calibration}" data-shock="${c.shock}"`);
      expect(markup).toContain(cell(c.delta_eve_behavioural, 'en'));
      expect(markup).toContain(cell(c.delta_eve_contractual, 'en'));
      expect(markup).toContain(cell(c.difference, 'en'));
    }
    expect(markup).toContain(escapeHtml(o.sign_convention.statement.en));
    for (const t of variant.tests.filter((x) => x.test_id === 'irrbb.eve_with_without_behavioural')) {
      expect(markup).toContain(`data-test="${t.test_id}"`);
      expect(markup).toContain(escapeHtml(t.notes as string));
    }
  });

  it('the replicating portfolio gives each tranche and weight, the implied maturity, the beta and the stability across windows', () => {
    const cat = 'retail-transactional' as const;
    const m = nmdModelOf((models as unknown as { fit: never }).fit, cat, o.valuation_date)!;
    const markup = html(<ReplicatingView sel={{ ...sel, category: cat }} />);
    for (const t of m.tranches) {
      expect(markup).toContain(`data-tranche="${t.maturity_years}"`);
      expect(markup).toContain(pct(t.weight));
    }
    expect(markup).toContain(formatNumber(m.weighted_average_maturity_years, 'en', { digits: 4 }));
    expect(markup).toContain(pct(m.deposit_beta.up));
    expect(markup).toContain(pct(m.deposit_beta.down));
    for (const w of m.stability) expect(markup).toContain(`data-window="${w.window_start}"`);
    expect(markup).toContain(pct(m.margin_volatility as number));
  });

  it('a margin volatility the fit lacks says not available with its reason, never a zero', () => {
    const markup = html(<ReplicatingView sel={{ ...sel, category: 'wholesale' }} />);
    expect(markup).toContain(NA);
    expect(markup).toContain('The window holds too few margin observations for the fit.');
  });

  it('the caps are shown with and without the cap: requested, cap and used, and whether the cap bit', () => {
    const markup = html(<CapsView sel={sel} />);
    for (const s of o.nmd_segments) {
      expect(markup).toContain(`data-category="${s.category}"`);
      expect(markup).toContain(pct(s.requested_core_share));
      expect(markup).toContain(pct(s.core_share_cap));
      expect(markup).toContain(pct(s.core_share_used));
    }
    expect(markup).toContain('data-cap-applied="false"');
    const odd = clone();
    const seg = odd.outputs.nmd_segments.find((s) => s.category === 'retail-transactional')!;
    Object.assign(seg, { requested_core_share: 0.95, core_share_used: 0.9, cap_applied: true });
    const capped = html(<CapsView sel={withVariant(odd)} />);
    expect(capped).toContain('data-cap-applied="true"');
    expect(capped).toContain(pct(0.95));
    expect(capped).toContain('capped');
  });

  it('a behavioural parameter that changed in a window with a limit breach is flagged', () => {
    const markup = html(<ChangesView sel={sel} />);
    const flagged = (models as unknown as { fit: { nmd_parameter_changes: Array<{ parameter: string; flagged: boolean; note: { en: string } }> } }).fit.nmd_parameter_changes;
    for (const c of flagged) {
      expect(markup).toContain(`data-flagged="${c.flagged}"`);
      expect(markup).toContain(escapeHtml(c.note.en));
    }
    expect(markup).toContain('data-breach="true"');
    expect(markup).toContain('data-breach="false"');
  });

  it('the repricing gap gives the 19 buckets and the duration gap, under the assumption chosen', () => {
    const markup = html(<GapView sel={sel} />);
    const l = o.ladder.find((x) => x.nmd_assumption === 'behavioural')!;
    expect(markup.match(/data-bucket="/g)?.length).toBe(19);
    for (const g of l.repricing_gap.filter((x) => x.gap !== 0)) expect(markup).toContain(cell(g.gap, 'en'));
    expect(markup).toContain(formatNumber(l.duration_gap.duration_gap_years, 'en', { digits: 4 }));
    expect(markup).toContain(cell(l.duration_gap.equity_change_100bp_up, 'en'));
    expect(markup).toContain(cell(l.delta_nii_gap_100bp_up, 'en'));
    const c = o.ladder.find((x) => x.nmd_assumption === 'contractual')!;
    expect(html(<GapView sel={{ ...sel, nmd: 'contractual' }} />)).toContain(cell(c.delta_nii_gap_100bp_up, 'en'));
  });

  it('the dynamic NII gives the balance-sheet assumption, the three paths, the total and the loss against the base, and the out-of-sample row', () => {
    const markup = html(<DynamicNiiView sel={sel} />);
    const d = o.dynamic_nii;
    expect(markup).toContain(escapeHtml(d.balance_sheet_assumption.description.en));
    expect(markup).toContain(`data-horizon="${d.horizon_months}"`);
    for (const s of d.scenarios) {
      expect(markup).toContain(`data-scenario="${s.scenario}"`);
      expect(markup).toContain(cell(s.total, 'en'));
    }
    expect(markup).toContain(cell(d.scenarios[1].delta_vs_base, 'en'));
    for (const i of d.items) expect(markup).toContain(`data-item="${i.item_id}"`);
    expect(markup).toContain('data-applicable="true"');
    expect(markup).toContain(cell(o.out_of_sample.projected_delta_nii, 'en'));
    expect(markup).toContain(cell(o.out_of_sample.realised_delta_nii, 'en'));
    expect(markup).toContain(pct(o.out_of_sample.relative_error as number));
  });

  it('an out-of-sample comparison that does not apply says why and shows no number', () => {
    const markup = html(<DynamicNiiView sel={withVariant(variant22)} />);
    expect(markup).toContain('data-applicable="false"');
    expect(markup).toContain(escapeHtml(variant22.outputs.out_of_sample.reason!.en));
  });

  it('EaR and EVaR give both levels, the method and its parameters, the paths, the seed and the Monte Carlo error', () => {
    const markup = html(<EarEvarView sel={sel} />);
    const e = o.ear_evar;
    expect(markup).toContain('Hull-White one-factor');
    expect(markup).toContain(formatNumber(e.n_paths, 'en', { decimals: 0 }));
    expect(markup).toContain(`data-seed="${e.seed}"`);
    for (const l of e.levels) {
      expect(markup).toContain(`data-level="${l.level}"`);
      expect(markup).toContain(cell(l.ear, 'en'));
      expect(markup).toContain(cell(l.evar, 'en'));
    }
    for (const l of e.levels) {
      expect(markup).toContain(`data-ear-se="${l.ear_se}"`);
      expect(markup).toContain(`data-evar-se="${l.evar_se}"`);
    }
    expect(markup).toContain(`data-mc-method="${e.mc_error_method}"`);
    for (const p of e.parameters) expect(markup).toContain(escapeHtml(p.name));
    expect(markup).toContain(escapeHtml(o.sign_convention.statement.en));
  });

  it('the tests of the engine sit under the view they belong to: one that did not run shows its reason and no number', () => {
    const eve = html(<EveByShockView sel={sel} />);
    const base = html(<WithWithoutView sel={sel} />);
    for (const t of variant.tests) {
      const host = t.test_id === 'irrbb.eve_with_without_behavioural' ? base : eve;
      expect(host).toContain(`data-test="${t.test_id}"`);
      expect(host).toContain(escapeHtml(t.notes as string));
    }
    expect(eve + base).not.toMatch(/NaN|undefined/);
    expect(eve).not.toContain('>irrbb.');
  });

  it('the context labels the real aggregates and the synthetic behaviour, and gives the data cut-off, the curve and the assumptions', () => {
    const markup = html(<C14ContextView sel={sel} />);
    expect(markup).toContain(escapeHtml(o.bank.notice.en));
    expect(markup).toContain('data-aggregates="real"');
    expect(markup).toContain('data-behaviour="synthetic"');
    expect(markup).toContain(o.data.data_cutoff);
    expect(markup).toContain(escapeHtml(o.data.rule.en));
    for (const r of o.data.call_reports) expect(markup).toContain(r.report_date);
    expect(markup).toContain(escapeHtml(o.curve.interpolation));
    for (const i of o.balance_sheet.items) expect(markup).toContain(`data-item="${i.item_id}"`);
    expect(markup).toContain('synthetic, stated');
    expect(html(<C14FindingsView sel={sel} />)).toContain('data-fixture="true"');
  });

  it('an item the financials lack shows not available with its reason and the slotting assumption that replaces it', () => {
    const odd = clone();
    Object.assign(odd.outputs.balance_sheet.items[0], { reported_amount: null, reason_missing: { en: 'The call report has no such line.', es: 'El reporte no trae esa línea.' } });
    const markup = html(<C14ContextView sel={withVariant(odd)} />);
    expect(markup).toContain('The call report has no such line.');
    expect(markup).toContain(escapeHtml(odd.outputs.balance_sheet.items[0].slotting_assumption));
    expect(markup).toContain(NA);
  });

  it('the valuation dates table gives the risk measure, its ratio to Tier 1 against the threshold line and the out-of-sample error', () => {
    const entry = (v: VariantArtifact<Outputs>, name: string) => ({ id: v.variant_id, title: { en: name, es: name }, v });
    const markup = html(<C14VariantsTable variants={[entry(variant, 'Q4 2021'), entry(variant22, 'Q4 2022')]} onPick={() => undefined} current={variant.variant_id} calibration="2024" />);
    for (const v of [variant, variant22]) {
      expect(markup).toContain(`data-variant="${v.variant_id}"`);
      const s = scenarioOf(v.outputs, '2024', 'behavioural')!;
      expect(markup).toContain(pct(s.outlier.ratio));
      expect(markup).toContain(v.outputs.valuation_date);
    }
    expect(markup).toContain('data-threshold="0.15"');
    expect(markup).toContain(pct(o.out_of_sample.relative_error as number));
  });

  it('the Spanish view is written in Spanish', () => {
    setLang('es');
    const eve = html(<EveByShockView sel={sel} />);
    expect(eve).toContain('Paralelo al alza');
    expect(eve).not.toContain('Parallel up');
    expect(eve).toContain(escapeHtml(o.sign_convention.statement.es));
    expect(html(<CapsView sel={sel} />)).toContain('Parte estable');
    expect(html(<WithWithoutView sel={sel} />)).toContain('conductual');
  });
});

function RailSection({ at }: { at: number }) {
  const inst = useC14Instrument(data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C14 rail', () => {
  afterEach(() => setLang('en'));

  it('has four sections, each with one control and one read-out', () => {
    function Sections() {
      const inst = useC14Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('calibration|nmd|shock|segment');
    for (const at of [0, 1, 2, 3]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('keeps the two small choices as chips and the long ones as one select each', () => {
    expect(railHtml(0)).toMatch(/data-control="c14-calibration"[^>]*><span[^>]*>Calibration of the shock sizes<\/span><div class="caos-chip-row"/);
    expect(railHtml(1)).toMatch(/data-control="c14-nmd"[^>]*><span[^>]*>Non-maturity deposits<\/span><div class="caos-chip-row"/);
    expect(railHtml(2)).toMatch(/data-control="c14-shock"[^>]*><label[^>]*>Prescribed shock<\/label><select/);
    expect(railHtml(3)).toMatch(/data-control="c14-segment"[^>]*><label[^>]*>Deposit category<\/label><select/);
    expect(railHtml(2).match(/<option/g)?.length).toBe(6);
    expect(railHtml(3).match(/<option/g)?.length).toBe(3);
  });

  it('names shocks and categories in words, never an internal id, and prints no raw amount', () => {
    expect(railHtml(2)).toContain('Parallel up');
    expect(railHtml(2)).not.toContain('>parallel-up<');
    expect(railHtml(3)).toContain('Retail transactional');
    expect(railHtml(3)).not.toContain('>retail-transactional<');
    for (const at of [0, 1, 2, 3]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
  });

  it('the calibration read-out gives the three shock sizes in basis points and where they come from', () => {
    const base = defaultSel(data) as C14Sel;
    const markup = html(<CalibrationReadout sel={base} />);
    expect(markup).toContain('200');
    expect(markup).toContain('300');
    expect(markup).toContain('225');
    expect(markup).toContain('Basel SRP31 Table 2 (2024)');
    expect(html(<CalibrationReadout sel={{ ...base, calibration: '2016' }} />)).toContain('Basel d368 Annex 2 (2016)');
  });

  it('the NMD read-out gives the weighted core share and maturity, how many caps bit, and the risk measure in compact money', () => {
    const base = defaultSel(data) as C14Sel;
    const markup = html(<NmdReadout sel={base} />);
    expect(markup).toContain(pct(o.assumptions.nmd_core_share.value));
    expect(markup).toContain(formatNumber(o.assumptions.nmd_core_maturity_years.value, 'en', { digits: 4 }));
    const s = scenarioOf(o, '2024', 'behavioural')!;
    const a = amount(o, s.eve_risk_measure);
    expect(markup).toContain(formatNumber(a.value, 'en', a.format));
    expect(markup).toContain('bn USD');
    expect(html(<NmdReadout sel={{ ...base, nmd: 'contractual' }} />)).toContain(formatNumber(amount(o, scenarioOf(o, '2024', 'contractual')!.eve_risk_measure).value, 'en', { digits: 4 }));
  });

  it('the shock read-out gives delta EVE, its share of Tier 1, the floored buckets and delta NII only for a parallel shock', () => {
    const base = defaultSel(data) as C14Sel;
    const s = scenarioOf(o, '2024', 'behavioural')!;
    const up = html(<ShockReadout sel={base} />);
    expect(up).toContain(pct(s.shocks[0].delta_eve_share_tier1));
    expect(up).toContain(formatNumber(amount(o, s.shocks[0].delta_nii).value, 'en', { digits: 4 }));
    const steep = html(<ShockReadout sel={{ ...base, shock: 'steepener' }} />);
    expect(steep).toContain(NA);
    expect(steep).toContain(formatNumber(s.shocks[2].floor_bound_buckets.length, 'en', { decimals: 0 }));
  });

  it('the segment read-out gives the implied maturity, the betas, and not available for a missing margin volatility', () => {
    const base = defaultSel(data) as C14Sel;
    const m = nmdModelOf((models as unknown as { fit: never }).fit, 'retail-transactional', o.valuation_date)!;
    const markup = html(<SegmentReadout sel={{ ...base, category: 'retail-transactional' }} />);
    expect(markup).toContain(formatNumber(m.weighted_average_maturity_years, 'en', { digits: 4 }));
    expect(markup).toContain(pct(m.deposit_beta.up));
    expect(html(<SegmentReadout sel={{ ...base, category: 'wholesale' }} />)).toContain(NA);
  });
});
