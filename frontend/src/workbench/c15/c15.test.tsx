// U10-W: the C15 instrument rendered on the server from the c15-outputs and c15-models fixtures
// (docs/contracts/fixtures/c15). C15 stays on its fixtures until the BCCh account exists (owner prerequisite 7); its views
// must still show the CLP and UR legs, the offset and the indexation charge separately (the charge is never folded into
// the rate result), the floors' effect and the prioritised-bank thresholds as lines, a shock size that is a Contraste
// estimate with its label, and "not available" with a reason for every null.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, readIrrbbFixture, setLang } from '../c14/testkit';
import { C15_FIT, C15_OUTPUTS } from './descriptor';
import { useC15Instrument } from './instrument';
import { amount, defaultSel, moneyDoc, outputsOf, worst, type C15Sel } from './selection';
import { C15ContextView, C15FindingsView, C15VariantsTable, LegReadout, OffsetReadout, ShockReadout } from './C15Common';
import { DynamicLegView, EarEvarLegView, EveByLegView, PositionsView } from './LegViews';
import { IndexationView, NiiView } from './RateViews';
import { FloorsView, ThresholdsView, thresholdsChart } from './FloorViews';

type Outputs = components['schemas']['c15Outputs'];

const longUf = readIrrbbFixture<VariantArtifact<Outputs>>('c15', 'variant-annex1-variant-long-uf-fixture.json');
const cpi = readIrrbbFixture<VariantArtifact<Outputs>>('c15', 'variant-annex1-variant-cpi-surprise-fixture.json');
const offsetV = readIrrbbFixture<VariantArtifact<Outputs>>('c15', 'variant-annex1-variant-offset-on-off-fixture.json');
const models = readIrrbbFixture<ModelsArtifact>('c15', 'models-fixture.json');
const title = { en: 'IRRBB on a CLP and UF balance sheet', es: 'IRRBB sobre un balance en CLP y UF' };
const dataOf = (v: VariantArtifact<Outputs>) => fixtureData('C15', v as unknown as VariantArtifact, models, title);
const data = dataOf(longUf);
const o = longUf.outputs;
const sel = defaultSel(data) as C15Sel;
const selOf = (v: VariantArtifact<Outputs>, patch: Partial<C15Sel> = {}): C15Sel => ({ ...(defaultSel(dataOf(v)) as C15Sel), ...patch });
const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const cell = (v: number | null, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { decimals: 0 });
const NA = formatNumber(null, 'en');
const clone = () => structuredClone(longUf) as VariantArtifact<Outputs>;

const VIEWS: Array<[string, (p: { sel: C15Sel | null }) => ReactElement]> = [
  ['Delta EVE by leg', EveByLegView], ['Positions', PositionsView], ['Dynamic NII', DynamicLegView], ['EaR and EVaR', EarEvarLegView],
  ['Delta NII', NiiView], ['Indexation', IndexationView], ['Floors', FloorsView], ['Thresholds', ThresholdsView],
  ['Findings', C15FindingsView], ['Context', C15ContextView],
];

function Names() {
  const inst = useC15Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC15Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C14' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C15 contract descriptors', () => {
  it('describe the fixtures key by key, in both directions', () => {
    for (const v of [longUf, cpi, offsetV]) expect(conform(v.outputs, C15_OUTPUTS)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C15_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone();
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).indexation_charge;
    const found = conform(odd.outputs, C15_OUTPUTS).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/indexation_charge: declared by the web, not written by the pipeline/);
  });
});

describe('the C15 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C15 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('Legs|Rate and indexation|Floors and thresholds|Findings|Variants');
    function Count() {
      const inst = useC15Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 1 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>5</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('annex1-variant');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('delta EVE gives the CLP leg and the UR leg apart, then the pair without and with the offset, with the convention named', () => {
    const markup = html(<EveByLegView sel={selOf(offsetV)} />);
    for (const r of offsetV.outputs.eve.rows) {
      expect(markup).toContain(`data-shock="${r.shock}"`);
      expect(markup).toContain(cell(r.clp.delta_eve));
      expect(markup).toContain(cell(r.ur.delta_eve));
      expect(markup).toContain(cell(r.pair.without_offset));
      expect(markup).toContain(cell(r.pair.with_offset));
    }
    expect(markup).toContain('data-opposite="true"');
    expect(markup).toContain('data-leg="CLP"');
    expect(markup).toContain('data-leg="UR"');
    expect(markup).toContain(escapeHtml(offsetV.outputs.sign_convention.statement.en));
    expect(markup).toContain(escapeHtml(offsetV.outputs.offset_rule.rule.en));
    expect(markup).toContain('CLP millions');
  });

  it('the offset choice picks the pair field and the largest of the six: on is the document measure, off is the larger sum of positive parts', () => {
    const v = offsetV.outputs;
    const on = html(<EveByLegView sel={selOf(offsetV, { offset: 'on' })} />);
    const off = html(<EveByLegView sel={selOf(offsetV, { offset: 'off' })} />);
    expect(worst(v.eve.rows, (r) => r.pair, 'on')).toBe(v.eve.delta_eve);
    expect(on).toContain(`data-measure="${v.eve.delta_eve}"`);
    const offMeasure = worst(v.eve.rows, (r) => r.pair, 'off');
    expect(offMeasure).toBeGreaterThan(v.eve.delta_eve);
    expect(off).toContain(`data-measure="${offMeasure}"`);
    expect(off).toContain(cell(offMeasure));
  });

  it('a measure with no loss in any shock is zero and says so', () => {
    const odd = clone();
    for (const r of odd.outputs.eve.rows) Object.assign(r.pair, { with_offset: 0, without_offset: 0, used: 0 });
    expect(worst(odd.outputs.eve.rows, (r) => r.pair, 'on')).toBe(0);
  });

  it('delta NII is the rate result plus the indexation charge, each shown apart, with the 300 bp size of Annex 1', () => {
    const markup = html(<NiiView sel={selOf(offsetV)} />);
    const n = offsetV.outputs.nii;
    expect(markup).toContain(`data-part="rate"`);
    expect(markup).toContain(`data-part="indexation"`);
    expect(markup).toContain(`data-part="total"`);
    expect(markup).toContain(cell(n.max_pair));
    expect(markup).toContain(cell(n.indexation_charge));
    expect(markup).toContain(cell(n.delta_nii));
    expect(n.delta_nii).toBeCloseTo(n.max_pair + n.indexation_charge, 6);
    for (const r of n.rows) {
      expect(markup).toContain(`data-shock="${r.shock}"`);
      expect(markup).toContain(cell(r.clp.delta_nii));
      expect(markup).toContain(cell(r.ur.delta_nii));
    }
    expect(markup).toContain('300 bp');
    expect(markup).toContain('CMF RAN 21-13 Annex 1');
    expect(markup).toContain(escapeHtml(offsetV.outputs.sign_convention.statement.en));
  });

  it('the indexation charge is derived from the net UF position and is never folded into the rate result', () => {
    const markup = html(<IndexationView sel={sel} />);
    const c = o.indexation_charge;
    expect(markup).toContain(escapeHtml(c.formula));
    expect(markup).toContain(formatNumber(c.net_position_uf_units, 'en', { digits: 4 }));
    expect(markup).toContain(cell(c.pn_ur));
    expect(markup).toContain(cell(c.charge));
    expect(markup).toContain(pct(c.rate));
    expect(markup).toContain(escapeHtml(c.note.en));
    expect(markup).toContain(cell(o.nii.max_pair));
    expect(markup).toContain(cell(o.nii.delta_nii));
  });

  it('a CPI surprise is shown with its effect; a variant without one says not available with the reason', () => {
    const withCpi = html(<IndexationView sel={selOf(cpi)} />);
    const s = cpi.outputs.cpi_scenario!;
    expect(withCpi).toContain('data-cpi="present"');
    expect(withCpi).toContain(escapeHtml(s.formula));
    expect(withCpi).toContain(cell(s.effect));
    expect(withCpi).toContain(formatNumber(s.surprise_pp, 'en', { digits: 4 }));
    const without = html(<IndexationView sel={sel} />);
    expect(without).toContain('data-cpi="absent"');
    expect(without).toContain(NA);
    expect(without).toContain('carries no CPI surprise');
  });

  it('the positions give each leg in its own currency, the UF value used and the items of the leg in focus', () => {
    const markup = html(<PositionsView sel={sel} />);
    for (const leg of o.legs) {
      expect(markup).toContain(`data-leg="${leg.leg}"`);
      expect(markup).toContain(cell(leg.assets_total));
      expect(markup).toContain(cell(leg.net_position));
    }
    expect(markup).toContain('CLF');
    expect(markup).toContain(cell(o.ur_currency.uf_value));
    expect(markup).toContain(o.ur_currency.uf_date);
    for (const i of o.legs[0].items) expect(markup).toContain(`data-item="${i.item_id}"`);
    expect(markup).not.toContain(`data-item="${o.legs[1].items[0].item_id}"`);
    expect(html(<PositionsView sel={{ ...sel, leg: 'UR' }} />)).toContain(`data-item="${o.legs[1].items[0].item_id}"`);
  });

  it('the dynamic NII of a leg gives the three paths, their totals and the loss against the base, in the reporting currency', () => {
    const markup = html(<DynamicLegView sel={{ ...sel, leg: 'UR' }} />);
    const leg = o.dynamic_nii.legs.find((l) => l.leg === 'UR')!;
    expect(markup).toContain(`data-horizon="${o.dynamic_nii.horizon_months}"`);
    for (const s of leg.scenarios) {
      expect(markup).toContain(`data-scenario="${s.scenario}"`);
      expect(markup).toContain(cell(s.total));
    }
    expect(markup).toContain(escapeHtml(o.dynamic_nii.balance_sheet_assumption.description.en));
    for (const i of leg.items) expect(markup).toContain(`data-item="${i.item_id}"`);
    expect(markup).toContain('converted at the UF value');
    expect(markup).not.toContain(`data-item="${o.dynamic_nii.legs[0].items[0].item_id}"`);
  });

  it('the EaR and EVaR of the leg in focus give both levels with their Monte Carlo errors, the method, the parameters, the paths and the seed', () => {
    for (const leg of ['CLP', 'UR'] as const) {
      const e = o.ear_evar.find((x) => x.leg === leg)!;
      const markup = html(<EarEvarLegView sel={{ ...sel, leg }} />);
      expect(markup).toContain(`data-leg="${leg}"`);
      for (const l of e.levels) {
        expect(markup).toContain(`data-level="${l.level}"`);
        expect(markup).toContain(`data-ear-se="${l.ear_se}"`);
        expect(markup).toContain(`data-evar-se="${l.evar_se}"`);
        expect(markup).toContain(cell(l.ear));
        expect(markup).toContain(cell(l.evar));
      }
      for (const p of e.parameters) expect(markup).toContain(`data-parameter="${p.name}"`);
      expect(markup).toContain(`data-seed="${e.seed}"`);
      expect(markup).toContain(`data-mc-method="${e.mc_error_method}"`);
      expect(markup).toContain('Hull-White one-factor');
      expect(markup).toContain(cell(e.base_nii));
      expect(markup).toContain(cell(e.base_eve));
    }
    expect(html(<EarEvarLegView sel={{ ...sel, leg: 'UR' }} />)).toContain('converted at the UF value');
    expect(html(<EarEvarLegView sel={{ ...sel, leg: 'CLP' }} />)).not.toContain('converted at the UF value');
    expect(html(<DynamicLegView sel={{ ...sel, leg: 'UR' }} />)).not.toContain('wait for the BCCh');
  });

  it('a document without the EaR and EVaR of a leg says not available with the reason and shows no number', () => {
    const odd = clone();
    (odd.outputs as unknown as { ear_evar: unknown[] }).ear_evar = odd.outputs.ear_evar.filter((x) => x.leg !== 'UR');
    const markup = html(<EarEvarLegView sel={selOf(odd, { leg: 'UR' })} />);
    expect(markup).toContain('Not available: this document has no EaR and EVaR for this leg.');
    expect(markup).not.toContain('data-table="ear-evar"');
    expect(html(<EarEvarLegView sel={selOf(odd, { leg: 'CLP' })} />)).toContain('data-table="ear-evar"');
  });

  it('refuses a document whose EaR and EVaR block lacks a key or carries one the web does not declare', () => {
    const lacks = clone();
    delete (lacks.outputs.ear_evar[0] as unknown as Record<string, unknown>).n_batches;
    expect(conform(lacks.outputs, C15_OUTPUTS).length).toBeGreaterThan(0);
    const extra = clone();
    (extra.outputs.ear_evar[1].levels[0] as unknown as Record<string, unknown>).planted = 1;
    expect(conform(extra.outputs, C15_OUTPUTS).length).toBeGreaterThan(0);
    const none = clone();
    delete (none.outputs as unknown as Record<string, unknown>).ear_evar;
    expect(conform(none.outputs, C15_OUTPUTS).length).toBeGreaterThan(0);
    const noDist = clone();
    delete (noDist.outputs.floors as unknown as Record<string, unknown>).distances;
    expect(conform(noDist.outputs, C15_OUTPUTS).length).toBeGreaterThan(0);
    const noMonth = clone();
    delete (noMonth.outputs as unknown as Record<string, unknown>).calibration_month;
    expect(conform(noMonth.outputs, C15_OUTPUTS).length).toBeGreaterThan(0);
  });

  it('the floors give the rule, the two floors and the effect on each leg and shock where one binds', () => {
    const markup = html(<FloorsView sel={sel} />);
    expect(markup).toContain(escapeHtml(o.floors.rule.en));
    expect(markup).toContain(pct(o.floors.ur_floor));
    expect(markup).toContain(pct(o.floors.other_floor));
    expect(o.floors.effects.length).toBeGreaterThan(0);
    for (const e of o.floors.effects) {
      expect(markup).toContain(`data-leg="${e.leg}" data-measure="${e.measure}" data-shock="${e.shock}"`);
      expect(markup).toContain(cell(e.delta_with_floor));
      expect(markup).toContain(cell(e.delta_without_floor));
      expect(markup).toContain(formatNumber(e.effect, 'en', { decimals: 0 }));
    }
  });

  it('the floors draw the distance of every leg and shock to its floor, with the binding rows marked and the closest one named', () => {
    const markup = html(<FloorsView sel={sel} />);
    expect(o.floors.distances).toHaveLength(16);
    for (const x of o.floors.distances) {
      expect(markup).toContain(`data-leg="${x.leg}" data-measure="${x.measure}" data-shock="${x.shock}" data-binds="${x.binds}"`);
      expect(markup).toContain(formatNumber(x.distance_bp, 'en', { digits: 4 }));
    }
    const nBind = o.floors.distances.filter((x) => x.binds).length;
    expect(nBind).toBeGreaterThan(0);
    expect(markup).toContain(`data-binding="${nBind}"`);
    expect(markup).toContain('data-table="floor-distances"');
    expect(markup).toContain('Each bar is the distance of a leg and a shock to its floor');
    expect(html(<FloorsView sel={null} />)).toContain('data-state="loading"');
  });

  it('a variant where no floor binds still draws the distances and says how far the closest one is', () => {
    const odd = clone();
    odd.outputs.floors.effects = [];
    odd.outputs.floors.distances = odd.outputs.floors.distances.map((x) => ({ ...x, binds: false, distance_bp: Math.abs(x.distance_bp) + 20 }));
    const markup = html(<FloorsView sel={selOf(odd)} />);
    expect(markup).not.toContain('No floor binds in this variant');
    expect(markup).toContain('Each bar is the distance of a leg and a shock to its floor');
    expect(markup).toContain('data-binding="0"');
    expect(markup).toContain('above the floor');
  });

  it('the prioritised-bank thresholds are lines: 5, 15 and 18 percent, each test with its ratio and whether it fired', () => {
    const chart = thresholdsChart(sel);
    expect(chart?.x.values).toEqual([1, 2, 3]);
    expect(chart?.series.map((s) => s.values)).toEqual([o.thresholds.tests.map((t) => t.ratio), [0.05, 0.15, 0.18]]);
    expect(chart?.series[1].mode).not.toBe('points');
    const markup = html(<ThresholdsView sel={sel} />);
    for (const t of o.thresholds.tests) {
      expect(markup).toContain(`data-test-id="${t.id}"`);
      expect(markup).toContain(pct(t.ratio));
      expect(markup).toContain(pct(t.threshold));
      expect(markup).toContain(cell(t.measure));
      expect(markup).toContain(cell(t.base));
    }
    expect(markup).toContain('data-breached="false"');
    expect(markup).toContain('data-prioritised="false"');
    expect(markup).toContain(escapeHtml(o.thresholds.reference));
    expect(thresholdsChart(null)).toBeNull();
  });

  it('a breached threshold is stated, and a prioritised bank says so', () => {
    const odd = clone();
    odd.outputs.thresholds.tests[1].breached = true;
    odd.outputs.thresholds.tests[1].ratio = 0.2;
    odd.outputs.thresholds.prioritised = true;
    const markup = html(<ThresholdsView sel={selOf(odd)} />);
    expect(markup).toContain('data-breached="true"');
    expect(markup).toContain('data-prioritised="true"');
    expect(markup).toContain('prioritised');
  });

  it('the tests of the engine sit under the view they belong to: one that did not run shows its reason and no number', () => {
    const eve = html(<EveByLegView sel={sel} />);
    for (const t of longUf.tests) {
      expect(eve).toContain(`data-test="${t.test_id}"`);
      expect(eve).toContain(escapeHtml(t.notes as string));
    }
    expect(eve).not.toMatch(/NaN|undefined/);
    expect(eve).not.toContain('>irrbb.');
  });

  it('the context labels the synthetic bank, the UR currency, the UF value, the curves as an adaptation and every assumption', () => {
    const markup = html(<C15ContextView sel={sel} />);
    expect(markup).toContain(escapeHtml(o.bank.notice.en));
    expect(markup).toContain('data-synthetic="true"');
    expect(markup).toContain(escapeHtml(o.ur_currency.definition.en));
    expect(markup).toContain(escapeHtml(o.ur_currency.uf_source));
    for (const c of [o.curves.clp, o.curves.ur]) {
      expect(markup).toContain(escapeHtml(c.attribution));
      expect(markup).toContain(c.month);
    }
    expect(markup).toContain(escapeHtml(o.variant.description.en));
    expect(markup).toContain('data-assumption="deposit_beta"');
    expect(markup).toContain('synthetic, stated');
    expect(html(<C15FindingsView sel={sel} />)).toContain('data-fixture="true"');
  });

  it('the Annex 1 shock sizes are named with their origin; a size that is a Contraste estimate carries its label and method', () => {
    const markup = html(<C15ContextView sel={sel} />);
    for (const z of o.eve_shock_sizes) {
      expect(markup).toContain(`data-size-currency="${z.currency}"`);
      expect(markup).toContain(`${z.parallel_bp} bp`);
    }
    expect(markup).toContain('CMF RAN 21-13 Annex 1');
    const odd = clone();
    Object.assign(odd.outputs.eve_shock_sizes[0], { origin: 'contraste-estimate', label: { en: 'Desk estimate of the CLP shock', es: 'Estimación de la mesa del choque CLP' }, method: 'rolling six-month changes' });
    const labelled = html(<C15ContextView sel={selOf(odd)} />);
    expect(labelled).toContain('Desk estimate of the CLP shock');
    expect(labelled).toContain('rolling six-month changes');
    expect(labelled).toContain('not a regulatory parameter');
  });

  it('an NMD segment whose request exceeded the cap is shown capped, with the request and the value used', () => {
    const markup = html(<C15ContextView sel={selOf(cpi)} />);
    const s = cpi.outputs.nmd_segments[0];
    expect(s.cap_applied).toBe(true);
    expect(markup).toContain('data-cap-applied="true"');
    expect(markup).toContain(pct(s.requested_core_share));
    expect(markup).toContain(pct(s.core_share_used));
    expect(markup).toContain('capped');
  });

  it('the variants table gives each SDD variant with its delta EVE, delta NII, indexation charge and whether the bank is prioritised', () => {
    const entry = (v: VariantArtifact<Outputs>) => ({ id: v.variant_id, title: v.outputs.variant.label, v });
    const markup = html(<C15VariantsTable variants={[entry(longUf), entry(cpi), entry(offsetV)]} onPick={() => undefined} current={longUf.variant_id} />);
    for (const v of [longUf, cpi, offsetV]) {
      expect(markup).toContain(`data-variant="${v.variant_id}"`);
      expect(markup).toContain(cell(v.outputs.eve.delta_eve));
      expect(markup).toContain(cell(v.outputs.nii.indexation_charge));
    }
  });

  it('the Spanish view is written in Spanish', () => {
    setLang('es');
    const eve = html(<EveByLegView sel={sel} />);
    expect(eve).toContain('Paralelo al alza');
    expect(eve).not.toContain('Parallel up');
    expect(eve).toContain(escapeHtml(o.sign_convention.statement.es));
    expect(html(<NiiView sel={sel} />)).toContain('reajustabilidad');
    expect(html(<IndexationView sel={sel} />)).toContain(formatNumber(null, 'es'));
    const floors = html(<FloorsView sel={sel} />);
    expect(floors).toContain('Cada barra es la distancia de un tramo y un choque a su piso');
    expect(floors).toContain('Pisos que rigen');
    expect(floors).not.toContain('Lowest rate');
    const ear = html(<EarEvarLegView sel={sel} />);
    expect(ear).toContain('Ganancias en riesgo y valor económico en riesgo');
    expect(ear).toContain('Hull-White de un factor');
    expect(ear).not.toContain('Confidence level');
  });
});

function RailSection({ at }: { at: number }) {
  const inst = useC15Instrument(data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C15 rail', () => {
  afterEach(() => setLang('en'));

  it('has three sections, each with one control and one read-out', () => {
    function Sections() {
      const inst = useC15Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('shock|offset|leg');
    for (const at of [0, 1, 2]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('keeps the small choices as chips and the six shocks as one select', () => {
    expect(railHtml(0)).toMatch(/data-control="c15-shock"[^>]*><label[^>]*>Prescribed shock<\/label><select/);
    expect(railHtml(0).match(/<option/g)?.length).toBe(6);
    expect(railHtml(1)).toMatch(/data-control="c15-offset"[^>]*><span[^>]*>CLP and CLF offset<\/span><div class="caos-chip-row"/);
    expect(railHtml(2)).toMatch(/data-control="c15-leg"[^>]*><span[^>]*>Leg of the book<\/span><div class="caos-chip-row"/);
  });

  it('keeps the rail inside 1280 x 800 in Spanish: the offset chips are one short word each, and a read-out names its money unit once, in its title', () => {
    const es = railHtml(1, 'es');
    expect(es).toMatch(/<button[^>]*>Activa<\/button>/);
    expect(es).toMatch(/<button[^>]*>Inactiva<\/button>/);
    expect(railHtml(1)).toMatch(/<button[^>]*>On<\/button>/);
    for (const at of [0, 1]) {
      expect(railHtml(at), `section ${at}`).toContain('(bn CLP)');
      expect(railHtml(at).match(/bn CLP/g)?.length, `section ${at}`).toBe(1);
    }
  });

  it('names shocks in words, never an internal id, and prints no raw amount', () => {
    expect(railHtml(0)).toContain('Parallel up');
    expect(railHtml(0)).not.toContain('>parallel-up<');
    for (const at of [0, 1, 2]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
  });

  it('the shock read-out gives the two legs apart and the pair, in compact money in the reporting currency', () => {
    const s = selOf(offsetV, { shock: 'parallel-down' });
    const row = offsetV.outputs.eve.rows[1];
    const markup = html(<ShockReadout sel={s} />);
    const clp = amount(moneyDoc(offsetV.outputs), row.clp.delta_eve);
    expect(markup).toContain(formatNumber(clp.value, 'en', clp.format));
    expect(markup).toContain('bn CLP');
    const ur = amount(moneyDoc(offsetV.outputs), row.ur.delta_eve);
    expect(markup).toContain(formatNumber(ur.value, 'en', ur.format));
  });

  it('the offset read-out gives the measure with and without the offset and what the offset removes', () => {
    const v = offsetV.outputs;
    const markup = html(<OffsetReadout sel={selOf(offsetV)} />);
    const on = amount(moneyDoc(v), worst(v.eve.rows, (r) => r.pair, 'on'));
    const off = amount(moneyDoc(v), worst(v.eve.rows, (r) => r.pair, 'off'));
    expect(markup).toContain(formatNumber(on.value, 'en', on.format));
    expect(markup).toContain(formatNumber(off.value, 'en', off.format));
    expect(markup).toContain(formatNumber(v.offset_rule.share, 'en', { percent: true, decimals: 0 }));
  });

  it('the leg read-out gives the assets, the liabilities and the net position of the leg in its own currency', () => {
    const markup = html(<LegReadout sel={{ ...sel, leg: 'UR' }} />);
    const leg = o.legs[1];
    const a = amount(moneyDoc(o), leg.assets_total, leg.currency);
    expect(markup).toContain(formatNumber(a.value, 'en', a.format));
    expect(markup).toContain('CLF');
    expect(html(<LegReadout sel={sel} />)).toContain('CLP');
  });
});
