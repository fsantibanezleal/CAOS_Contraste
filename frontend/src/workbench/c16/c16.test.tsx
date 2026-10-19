// U11-W: the C16 instrument rendered on the server from the c16-outputs, c16-outputs-reverse and c16-models fixtures
// (docs/contracts/fixtures/c16). The views are built on the reviewed contracts while the engine and the bake are built,
// so every assertion reads what the fixture holds: the survival convention (a day count, or "survives the horizon" with
// the horizon and no number), the LCR as a Basel formula on call-report aggregates and never the bank's reported ratio,
// the synthetic deposits, both denominators of the realised run, every named convention with its label, "not available"
// with a reason for every null, and no number that the document does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';
import { C16_FIT, C16_OUTPUTS, C16_OUTPUTS_REVERSE } from './descriptor';
import { useC16Instrument } from './instrument';
import { defaultSel, fitOf, outputsOf, reverseOf, survivalText, type C16Sel } from './selection';
import { BaseReadout, C16ContextView, C16FindingsView, C16TestsView, C16VariantsTable, DayReadout, DenominatorReadout, MappingReadout, RowReadout } from './C16Common';
import { CbcStackView, LadderView, RunSpeedsView, RunoffView } from './LadderViews';
import { CbcView, HtmView, LcrView, TimeBlockView } from './BufferViews';
import { HtmLossView, ReverseBasesView, ReverseCurveView, UninsuredShareView } from './SensitivityViews';

type Outputs = components['schemas']['c16Outputs'];
type Reverse = components['schemas']['c16ReverseOutputs'];

const fixture = <T,>(name: string): T => JSON.parse(readFileSync(new URL(`../../../../docs/contracts/fixtures/c16/${name}-fixture.json`, import.meta.url), 'utf8')) as T;
const lcrV = fixture<VariantArtifact<Outputs>>('variant-scenario-lcr-standard');
const adverseV = fixture<VariantArtifact<Outputs>>('variant-scenario-list-adverse');
const extremeV = fixture<VariantArtifact<Outputs>>('variant-scenario-list-extreme');
const fastV = fixture<VariantArtifact<Outputs>>('variant-scenario-fast-run');
const htmV = fixture<VariantArtifact<Outputs>>('variant-scenario-htm-losses');
const reverseV = fixture<VariantArtifact<Reverse>>('variant-reverse');
const models = fixture<ModelsArtifact>('models');
const title = { en: 'Liquidity stress, LCR and the March 2023 run', es: 'Estrés de liquidez, LCR y la corrida de marzo de 2023' };
const dataOf = (v: VariantArtifact<Outputs> | VariantArtifact<Reverse>): CaseData => fixtureData('C16', v as unknown as VariantArtifact, models, title);
const selOf = (v: VariantArtifact<Outputs> | VariantArtifact<Reverse>, patch: Partial<C16Sel> = {}): C16Sel => ({ ...(defaultSel(dataOf(v)) as C16Sel), ...patch });
const clone = <T,>(v: T): T => structuredClone(v);

const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const cell = (v: number | null, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { decimals: 0 });
const NA = formatNumber(null, 'en');
const text = (t: { en: string; es: string }, lang: 'en' | 'es' = 'en') => escapeHtml(t[lang]);

const SCENARIO_VIEWS: Array<[string, (p: { sel: C16Sel | null }) => ReactElement]> = [
  ['Ladder', LadderView], ['CBC stack', CbcStackView], ['Run-off', RunoffView], ['Run speeds', RunSpeedsView],
  ['CBC', CbcView], ['HTM', HtmView], ['LCR', LcrView], ['Time block', TimeBlockView],
  ['Uninsured share', UninsuredShareView], ['HTM loss', HtmLossView], ['Tests', C16TestsView], ['Findings', C16FindingsView], ['Context', C16ContextView],
];
const REVERSE_VIEWS: Array<[string, (p: { sel: C16Sel | null }) => ReactElement]> = [
  ['Reverse curve', ReverseCurveView], ['Reverse bases', ReverseBasesView], ['Tests', C16TestsView], ['Findings', C16FindingsView], ['Context', C16ContextView],
];

function Names({ v }: { v: VariantArtifact<Outputs> | VariantArtifact<Reverse> }) {
  const inst = useC16Instrument(dataOf(v), () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Rail({ v }: { v: VariantArtifact<Outputs> | VariantArtifact<Reverse> }) {
  const inst = useC16Instrument(dataOf(v), () => undefined);
  return <div>{inst ? inst.rail.map((s) => (typeof s.label === 'string' ? s.label : s.label.en)).join('|') : 'none'}</div>;
}
function Other() {
  const inst = useC16Instrument({ ...dataOf(htmV), manifest: { ...dataOf(htmV).manifest, case_id: 'C15' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C16 contract descriptors', () => {
  it('describe the five scenario fixtures, the reverse-stress fixture and the models fit key by key, in both directions', () => {
    for (const v of [lcrV, adverseV, extremeV, fastV, htmV]) expect(conform(v.outputs, C16_OUTPUTS), v.variant_id).toEqual([]);
    expect(conform(reverseV.outputs, C16_OUTPUTS_REVERSE)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C16_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone(htmV);
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).sensitivities;
    const found = conform(odd.outputs, C16_OUTPUTS).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/sensitivities: declared by the web, not written by the pipeline/);
  });
});

describe('the survival convention', () => {
  it('writes a day count, or "survives the horizon" with the horizon and never a number for the second', () => {
    expect(survivalText({ kind: 'day', day: 48, horizon_days: 125 }, 'en')).toBe('day 48');
    expect(survivalText({ kind: 'survives-horizon', day: null, horizon_days: 125 }, 'en')).toBe('survives the 125-day horizon');
    expect(survivalText({ kind: 'survives-horizon', day: null, horizon_days: 125 }, 'es')).toBe('sobrevive el horizonte de 125 días');
    expect(survivalText({ kind: 'survives-horizon', day: null, horizon_days: 5 }, 'en')).not.toMatch(/\bday \d/);
    expect(survivalText(null, 'en')).toBe(NA);
  });
});

describe('the C16 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C16 only, with at most four groups in the validator order, then Variants', () => {
    expect(html(<Names v={htmV} />)).toContain('Survival|Buffer and LCR|Sensitivities|Tests and findings|Variants');
    expect(html(<Names v={reverseV} />)).toContain('Reverse stress|Tests and findings|Variants');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(selOf(htmV))?.kind).toBe('scenario');
    expect(reverseOf(selOf(reverseV))?.kind).toBe('reverse-stress');
    expect(outputsOf(selOf(reverseV))).toBeNull();
  });

  it('the rail of a daily-path variant, of the LCR variant and of the reverse stress each holds its controls and a read-out with no raw amount', () => {
    expect(html(<Rail v={htmV} />)).toContain('Day|Run|Row');
    expect(html(<Rail v={lcrV} />)).toContain('Mapping|Run|Row');
    expect(html(<Rail v={reverseV} />)).toContain('Base|Multiplier');
    function Controls() {
      const inst = useC16Instrument(dataOf(htmV), () => undefined);
      return <pre>{JSON.stringify(inst?.controls)}</pre>;
    }
    expect(html(<Controls />)).toContain('&quot;day&quot;');
    for (const [name, el] of [
      ['day', <DayReadout sel={selOf(htmV)} />], ['day, survives', <DayReadout sel={selOf(fastV)} />], ['run', <DenominatorReadout sel={selOf(htmV)} />],
      ['row', <RowReadout sel={selOf(htmV)} />], ['mapping', <MappingReadout sel={selOf(lcrV)} />], ['base', <BaseReadout sel={selOf(reverseV)} />],
    ] as Array<[string, ReactElement]>) {
      const markup = html(el);
      expect(markup, name).toContain('caos-readout');
      expect(RAW_AMOUNT.test(markup), `${name}: a raw amount in a rail read-out`).toBe(false);
    }
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of SCENARIO_VIEWS) {
      const found = cards(html(<View sel={selOf(htmV)} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
    for (const [name, View] of REVERSE_VIEWS) {
      const found = cards(html(<View sel={selOf(reverseV)} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
    }
  });

  it('a scenario view given the reverse document, and the reverse view given a scenario, say not available and draw nothing', () => {
    expect(html(<LadderView sel={selOf(reverseV)} />)).toContain('data-state="unavailable"');
    expect(html(<ReverseCurveView sel={selOf(htmV)} />)).toContain('data-state="unavailable"');
  });

  it('the survival ladder gives the NLP by day, the CBC and the cumulative outflow, with the survival day marked', () => {
    const markup = html(<LadderView sel={selOf(htmV)} />);
    const p = htmV.outputs.path!;
    expect(markup).toContain('data-survival-kind="day"');
    expect(markup).toContain('data-survival-day="48"');
    expect(markup).toContain(cell(p.minimum_nlp.day));
    expect(markup).toContain('data-series="');
    expect(markup).toContain('data-drawn');
    expect(markup).toContain(text(htmV.outputs.variant.label));
    // the cliff diagnostic is a ratio the document holds
    expect(markup).toContain(pct(p.cliff!.value));
  });

  it('a variant that survives its horizon says so with the horizon and prints no survival day', () => {
    const markup = html(<LadderView sel={selOf(fastV)} />);
    expect(markup).toContain('data-survival-kind="survives-horizon"');
    expect(markup).not.toContain('data-survival-day');
    expect(markup).toContain('Survives the 5-day horizon');
    // the cliff is not stated for a ladder shorter than 35 days: the reason, never a number
    expect(markup).toContain(text(fastV.outputs.path!.cliff_reason!));
  });

  it('the LCR variant has no daily path: every ladder view says why and draws no chart', () => {
    for (const View of [LadderView, CbcStackView]) {
      const markup = html(<View sel={selOf(lcrV)} />);
      expect(markup).toContain('data-state="unavailable"');
      expect(markup).toContain(text(lcrV.outputs.path_reason!));
      expect(markup).not.toContain('data-series=');
    }
  });

  it('the CBC stack draws every class and the total from the ladder', () => {
    const markup = html(<CbcStackView sel={selOf(htmV)} />);
    const stack = htmV.outputs.path!.ladder as unknown as { cbc_stack: Array<{ class_id: string }> };
    expect(stack.cbc_stack.length).toBe(6);
    expect(markup).toContain('data-series="7"');
  });

  it('the run-off view puts the curves against both denominators of the realised run and the LCR 30-day rates', () => {
    const markup = html(<RunoffView sel={selOf(htmV)} />);
    const s = htmV.outputs.scoring;
    for (const d of s.denominators) {
      expect(markup).toContain(`data-denominator="${d.id}"`);
      expect(markup).toContain(pct(d.realised_share));
      expect(markup).toContain(pct(d.modelled_share));
      expect(markup).toContain(`data-light="${d.light}"`);
      expect(markup).toContain(text(d.label));
    }
    expect(markup).toContain(pct(0.03));
    expect(markup).toContain(pct(0.4));
    expect(markup).toContain('LCR');
    expect(markup).toContain(text(s.svb_anchor.label));
    expect(markup).toContain(pct(s.svb_anchor.implied_daily_rate));
    expect(markup).toContain('data-forecast-claim="false"');
  });

  it('the chosen denominator moves the realised line; the other stays in the table', () => {
    const a = html(<RunoffView sel={selOf(htmV, { denominator: 'board-stated-share' })} />);
    const b = html(<RunoffView sel={selOf(htmV, { denominator: 'call-report-dep' })} />);
    expect(a).toContain('data-chosen="board-stated-share"');
    expect(b).toContain('data-chosen="call-report-dep"');
    expect(a).not.toBe(b);
  });

  it('the LCR run-off view compares at the model horizon and the daily variants at the event horizon, said in words', () => {
    expect(html(<RunoffView sel={selOf(lcrV)} />)).toContain('data-compared-at="model-horizon"');
    expect(html(<RunoffView sel={selOf(htmV)} />)).toContain('data-compared-at="event-horizon"');
  });

  it('the run speeds give the nine Table A.1 rows, the LiST medians as reference markers, and a null modelled share with its reason', () => {
    const markup = html(<RunSpeedsView sel={selOf(fastV)} />);
    for (const r of fastV.outputs.scoring.table_a1_scoring) {
      expect(markup).toContain(`data-row="${r.row_id}"`);
      expect(markup).toContain(pct(r.observed_share));
    }
    expect(markup).toContain('data-median="adverse"');
    expect(markup).toContain('176');
    expect(markup).toContain('data-median="extreme"');
    expect(markup).toContain('122');
    expect(markup).toContain('103');
    const first = fastV.outputs.scoring.table_a1_scoring.find((r) => r.modelled_share === null)!;
    expect(markup).toContain(text(first.reason!));
    expect(markup).toContain('data-role="calibration"');
    expect(markup).toContain('data-role="scored"');
  });

  it('the CBC view gives each class with its haircut and rule, the pledged securities and the valuation basis', () => {
    const markup = html(<CbcView sel={selOf(htmV)} />);
    for (const c of htmV.outputs.cbc.classes) {
      expect(markup).toContain(`data-class="${c.class_id}"`);
      expect(markup).toContain(text(c.label));
      expect(markup).toContain(cell(c.liquidity_value));
    }
    expect(markup).toContain('data-basis="fair-value"');
    expect(markup).toContain(pct(htmV.outputs.cbc.pledged.share_of_securities));
    expect(markup).toContain(text(htmV.outputs.cbc.haircut_framework.label));
  });

  it('the HTM view gives the CBC with and without the loss and labels the BTFP par row a counterfactual after the run', () => {
    const markup = html(<HtmView sel={selOf(htmV)} />);
    const h = htmV.outputs.htm!;
    expect(markup).toContain('data-row="without-loss"');
    expect(markup).toContain('data-row="with-loss"');
    expect(markup).toContain('data-row="btfp-par"');
    expect(markup).toContain('data-counterfactual="true"');
    expect(markup).toContain(text(h.btfp_par.label));
    expect(markup).toContain('2023-03-12');
    expect(markup).toContain(cell(h.reported.htm_unrealised));
    expect(markup).toContain(text(h.application.statement));
    expect(markup).toContain(cell(h.revaluation.model_fair_value));
  });

  it('a revaluation that did not run shows its reason and no number', () => {
    const odd = clone(htmV);
    odd.outputs.htm!.revaluation = { status: 'not_evaluated', engine_ref: 'engine-irrbb-api', curve_source: 'x', curve_date: null, model_fair_value: null, reported_fair_value: 76168000, difference: null, relative_difference: null, reason: { en: 'The Treasury curve was not read.', es: 'No se leyó la curva del Tesoro.' } } as never;
    const markup = html(<HtmView sel={selOf(odd)} />);
    expect(markup).toContain('The Treasury curve was not read.');
    expect(markup).toContain('data-revaluation="not_evaluated"');
  });

  it('a variant without the HTM block says why instead of an empty chart', () => {
    const markup = html(<HtmView sel={selOf(adverseV)} />);
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).toContain(text(adverseV.outputs.htm_reason!));
    expect(markup).not.toContain('data-series=');
    expect(markup).not.toContain('data-bar=');
  });

  it('the LCR view is a Basel formula on call-report aggregates and never the bank\'s reported ratio, with the 75 percent cap', () => {
    const markup = html(<LcrView sel={selOf(lcrV)} />);
    const l = lcrV.outputs.lcr!;
    expect(markup).toContain('data-reported-or-regulatory="false"');
    expect(markup).toContain(text(l.statement));
    expect(markup).toContain('not the bank');
    expect(markup).toContain(pct(l.ratio));
    expect(markup).toContain(pct(l.inflow_cap));
    expect(markup).toContain(cell(l.inflows_counted));
    expect(markup).toContain(cell(l.net_outflows));
    for (const r of l.outflows) expect(markup).toContain(`data-category="${r.category}"`);
    for (const m of l.mapping_sensitivity) {
      expect(markup).toContain(`data-mapping="${m.mapping_id}"`);
      expect(markup).toContain(pct(m.ratio));
    }
    expect(markup).toContain(text(l.below_100_note));
  });

  it('the chosen deposit mapping marks its row of the sensitivity band', () => {
    const l = lcrV.outputs.lcr!;
    const id = l.mapping_sensitivity[1].mapping_id;
    expect(html(<LcrView sel={selOf(lcrV, { mapping: id })} />)).toContain(`data-mapping="${id}" data-chosen="true"`);
  });

  it('a variant without an LCR says why', () => {
    const markup = html(<LcrView sel={selOf(htmV)} />);
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).toContain(text(htmV.outputs.lcr_reason!));
    expect(markup).not.toContain('data-reported-or-regulatory');
  });

  it('the time block gives 2021-12-31 and 2022-06-30 with the CBC on both bases, the HTM loss, the survival and a null LCR as not available', () => {
    const markup = html(<TimeBlockView sel={selOf(htmV)} />);
    for (const t of htmV.outputs.time_block) {
      expect(markup).toContain(`data-date="${t.as_of}"`);
      expect(markup).toContain(cell(t.cbc_amortised_basis));
      expect(markup).toContain(cell(t.cbc_fair_value_basis));
      expect(markup).toContain(cell(t.htm_unrealised_loss));
      expect(markup).toContain(pct(t.deposits.uninsured_share_of_dep));
      expect(markup).toContain(pct(t.deposits.uninsured_share_of_depdom));
    }
    expect(markup).toContain('survives the 125-day horizon');
    expect(markup).toContain('day 80');
    expect(markup).toContain(NA);
    const lcr = html(<TimeBlockView sel={selOf(lcrV)} />);
    expect(lcr).toContain(pct(2.5));
    expect(lcr).toContain(pct(1.9));
  });

  it('the uninsured-share sensitivity gives the survival period at every grid point and a survival of the horizon is never a number', () => {
    const adv = html(<UninsuredShareView sel={selOf(adverseV)} />);
    for (const r of adverseV.outputs.sensitivities.uninsured_share!) expect(adv).toContain(`data-share="${r.share}"`);
    expect(adv).toContain('day 87');
    const fast = html(<UninsuredShareView sel={selOf(fastV)} />);
    expect(fast).toContain('survives the 5-day horizon');
    expect(fast).not.toMatch(/data-survival-day="\d/);
    const lcr = html(<UninsuredShareView sel={selOf(lcrV)} />);
    expect(lcr).toContain('data-state="unavailable"');
    expect(lcr).toContain(text(lcrV.outputs.sensitivities.uninsured_share_reason!));
  });

  it('the HTM-loss sensitivity gives the multiple, the loss, the CBC and the survival period, and says why when the variant has none', () => {
    const markup = html(<HtmLossView sel={selOf(htmV)} />);
    for (const r of htmV.outputs.sensitivities.htm_loss!) {
      expect(markup).toContain(`data-multiple="${r.multiple}"`);
      expect(markup).toContain(cell(r.cbc));
    }
    expect(markup).toContain('day 31');
    const lcr = html(<HtmLossView sel={selOf(lcrV)} />);
    expect(lcr).toContain(text(lcrV.outputs.sensitivities.htm_loss_reason!));
  });

  it('the reverse stress gives the curve against the 30-day target, the solved multiplier of each base and the refusal with its reason', () => {
    const markup = html(<ReverseCurveView sel={selOf(reverseV, { base: 'list-adverse' })} />);
    const adv = reverseV.outputs.bases[0];
    expect(markup).toContain('data-target="30"');
    expect(markup).toContain(formatNumber(adv.solved.multiplier, 'en', { digits: 4 }));
    expect(markup).toContain(text(reverseV.outputs.target.statement));
    for (const c of adv.curve) expect(markup).toContain(`data-multiplier="${c.multiplier}"`);
    const bases = html(<ReverseBasesView sel={selOf(reverseV)} />);
    for (const b of reverseV.outputs.bases) expect(bases).toContain(`data-base="${b.base_id}"`);
    const fast = reverseV.outputs.bases[2];
    expect(bases).toContain('data-solved="refused"');
    expect(bases).toContain(text(fast.solved.refusal_reason!));
    expect(bases).toContain(text(reverseV.outputs.cap_rule.statement));
    expect(bases).toContain(formatNumber(adv.max_multiplier, 'en', { digits: 4 }));
  });

  it('the reverse curve of a base that survives the horizon prints no survival day for it', () => {
    const markup = html(<ReverseCurveView sel={selOf(reverseV, { base: 'fast-run' })} />);
    expect(markup).toContain('survives the 5-day horizon');
    expect(markup).toContain('data-solved="refused"');
  });

  it('the tests table shows a test that did not run with its reason and no number', () => {
    const markup = html(<C16TestsView sel={selOf(fastV)} />);
    expect(markup).toContain('data-light="not_evaluated"');
    const nr = fastV.tests.find((t) => t.light === 'not_evaluated')!;
    expect(markup).toContain(escapeHtml(nr.notes ?? ''));
    expect(markup).toContain('data-test="liq.runoff_adequacy_back_test"');
    expect(markup).toContain('The back-test of the run-off against the realised run');
  });

  it('the variants table sets the survival period, the LCR and the modelled run of the five variants side by side', () => {
    const variants = [lcrV, adverseV, extremeV, fastV, htmV].map((v) => ({ id: v.variant_id, title: v.outputs.variant.label, v }));
    const markup = html(<C16VariantsTable variants={variants} onPick={() => undefined} current={htmV.variant_id} />);
    for (const { id } of variants) expect(markup).toContain(`data-variant="${id}"`);
    expect(markup).toContain('day 68');
    expect(markup).toContain('day 44');
    expect(markup).toContain('survives the 5-day horizon');
    expect(markup).toContain(pct(lcrV.outputs.lcr!.ratio));
    expect(markup).toContain('data-survival-kind="survives-horizon"');
  });

  it('the context names what the case is: real aggregates, synthetic behaviour, synthetic deposits, both denominators and every convention as a convention', () => {
    const markup = html(<C16ContextView sel={selOf(htmV)} />);
    const o = htmV.outputs;
    expect(markup).toContain('data-fixture="true"');
    expect(markup).toContain(text(o.bank.notice));
    expect(markup).toContain('data-bank-aggregates="real"');
    expect(markup).toContain('data-bank-behaviour="synthetic"');
    expect(markup).toContain('data-bank-deposits="synthetic"');
    expect(markup).toContain('DEPDOM');
    expect(markup).toContain('DEP');
    expect(markup).toContain(pct(o.balance_sheet.deposits.uninsured_share_of_dep));
    expect(markup).toContain(pct(o.balance_sheet.deposits.uninsured_share_of_depdom));
    expect(markup).toContain('USD thousands');
    expect(markup).toContain(o.data.data_cutoff);
    const conventions = (markup.match(/data-status="convention"/g) ?? []).length;
    expect(conventions).toBeGreaterThanOrEqual(20);
    expect(markup).not.toContain('data-status="regulatory"');
    // the models artifact: parameter sets with their source, the calibration and the generator
    const fit = fitOf(selOf(htmV))!;
    for (const p of fit.parameter_sets) expect(markup).toContain(`data-parameter-set="${p.set_id}"`);
    expect(markup).toContain(text(fit.calibration.statement));
    expect(markup).toContain(text(fit.list_parameters.results_annex.statement));
    for (const s of fit.sources) expect(markup).toContain(`data-source="${s.source_id}"`);
    expect(markup).toContain('data-unverified="true"');
  });

  it('the Spanish rendering reads as Spanish and keeps the number format of the language', () => {
    setLang('es');
    const ladder = html(<LadderView sel={selOf(fastV)} />);
    expect(ladder).toContain('Sobrevive el horizonte de 5 días');
    const run = html(<RunoffView sel={selOf(htmV)} />);
    expect(run).toContain(pct(0.85, 'es'));
    const lcr = html(<LcrView sel={selOf(lcrV)} />);
    expect(lcr).toContain('no el LCR reportado del banco');
    expect(lcr).toContain(pct(lcrV.outputs.lcr!.ratio, 'es'));
    const ctx = html(<C16ContextView sel={selOf(htmV)} />);
    expect(ctx).toContain('convención');
    expect(ctx).toContain('miles de USD');
  });

  it('every view reads its number from the document: a changed field changes the markup', () => {
    const odd = clone(htmV);
    odd.outputs.htm!.cbc_removed = 12345678;
    odd.outputs.htm!.cbc_with_loss = odd.outputs.htm!.cbc_without_loss - 12345678;
    expect(html(<HtmView sel={selOf(odd)} />)).toContain(cell(12345678));
    expect(html(<HtmView sel={selOf(htmV)} />)).not.toContain(cell(12345678));
    const run = clone(htmV);
    run.outputs.scoring.denominators[0].modelled_share = 0.1234;
    expect(html(<RunoffView sel={selOf(run)} />)).toContain(pct(0.1234));
  });
});
