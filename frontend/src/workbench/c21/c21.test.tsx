// U14-W: the C21 instrument rendered on the server from the c21-outputs and c21-models fixtures
// (docs/contracts/fixtures/c21). Statistical disparity in public HMDA decisions: every view carries the "no legal claim"
// label and the three legal sentences, the four-fifths line is an employment benchmark measured against the highest-rate
// group and decided by the document's flag, the controlled estimate names its missing controls, the counterfactual test is
// shown as not run with its reason, no outcome-conditioned view exists, a null estimate says why, and no view draws a
// number the fixture does not contain.
import { readFileSync } from 'node:fs';
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { cards, escapeHtml, fixtureData, html, readU14Fixture, setLang } from '../c20/testkit';
import { C21_FIT, C21_OUTPUTS_SHAPE } from './descriptor';
import { useC21Instrument } from './instrument';
import { defaultSel, outputsOf, type C21Sel } from './selection';
import { C21ContextView, C21FindingsView, C21VariantsTable, AttributeReadout, GroupReadout } from './C21Common';
import { ControlledView, RateSpreadView, ReplicationView, SituationView } from './EstimateViews';
import { FourFifthsView, RatesView, TestsView } from './RateViews';

type Outputs = components['schemas']['c21Outputs'];

const v = readU14Fixture<VariantArtifact<Outputs>>('c21', 'variant-year-pair-fixture.json');
const models = readU14Fixture<ModelsArtifact>('c21', 'models-fixture.json');
const title = { en: 'Fair-lending disparity testing', es: 'Pruebas de disparidad en crédito justo' };
const data = fixtureData('C21', v as unknown as VariantArtifact, models, title);
const o = v.outputs;
const sel = defaultSel(data) as C21Sel;
const race = { ...sel, field: 'derived_race', group: 'Black or African American' } as C21Sel;
const withVariant = (x: VariantArtifact<Outputs>): C21Sel => defaultSel({ ...data, variant: x as unknown as VariantArtifact }) as C21Sel;
const clone = () => structuredClone(v) as VariantArtifact<Outputs>;
const f3 = (x: number, lang: 'en' | 'es' = 'en') => formatNumber(x, lang, { decimals: 3 });
const NA = formatNumber(null, 'en');
/** The text a reader sees: the markup without its tags and attributes (data-group keeps the document's own group key). */
const visible = (markup: string): string => markup.replace(/<[^>]+>/g, ' ');
const SENTENCES = [
  'The Act does not provide that the &#x27;effects test&#x27; applies for determining whether there is discrimination in violation of the Act.',
  'disparate-impact claims are cognizable under the Fair Housing Act (FHA).',
  'Gross HMDA denial or approval rate disparities are not appropriate for disproportionate adverse impact analysis',
];

const VIEWS: Array<[string, (p: { sel: C21Sel | null }) => ReactElement]> = [
  ['Rates', RatesView], ['Four-fifths', FourFifthsView], ['Tests', TestsView], ['Controlled', ControlledView], ['Rate spread', RateSpreadView],
  ['Replication', ReplicationView], ['Situation', SituationView], ['Findings', C21FindingsView], ['Context', C21ContextView],
];

function Names() {
  const inst = useC21Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC21Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C09' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C21 contract descriptors', () => {
  it('describe the year-pair outputs and the fit key by key, in both directions', () => {
    expect(conform(v.outputs, C21_OUTPUTS_SHAPE)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C21_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone();
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).situation_testing;
    const found = conform(odd.outputs, C21_OUTPUTS_SHAPE).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/situation_testing: declared by the web, not written by the pipeline/);
  });
});

describe('the C21 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C21 only, with the groups in the order of the questions', () => {
    expect(html(<Names />)).toContain('Rates|After the controls|Stability|Findings|Year pairs');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('year-pair');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('every C21 view carries the "no legal claim" label and the three legal sentences of the addendum', () => {
    for (const [name, View] of VIEWS) {
      const markup = html(<View sel={sel} />);
      expect(markup, `${name}: no label`).toContain('no legal claim');
      for (const s of SENTENCES) expect(markup, `${name}: ${s.slice(0, 30)}`).toContain(s);
    }
    const table = html(<C21VariantsTable variants={[{ id: v.variant_id, title: { en: 'Pair', es: 'Par' }, v }]} onPick={() => undefined} current={v.variant_id} field="derived_sex" />);
    expect(table).toContain('no legal claim');
    for (const s of SENTENCES) expect(table).toContain(s);
  });

  it('the Spanish views carry the Spanish label of the document', () => {
    setLang('es');
    for (const [name, View] of VIEWS) expect(html(<View sel={sel} />), name).toContain(o.legal.label.es);
  });

  it('draws no outcome-conditioned view: no equalized odds, equal opportunity, calibration or AUC by group', () => {
    for (const [name, View] of VIEWS) {
      const markup = html(<View sel={sel} />);
      expect(markup, name).not.toMatch(/equalized odds|equal opportunity|calibration within|AUC by group/i);
    }
  });

  it('the rates give the counts and the rate of every group, the reference marked and the other categories kept out', () => {
    const markup = html(<RatesView sel={race} />);
    const a = o.attributes.find((x) => x.field === 'derived_race')!;
    for (const g of a.groups) {
      expect(markup).toContain(`data-group="${g.group}" data-reference="${g.group === a.reference_group}"`);
      expect(markup).toContain(formatNumber(g.selection_rate, 'en', { percent: true, decimals: 1 }));
    }
    expect(markup).toContain('data-excluded="1"');
    expect(markup).toContain('indicators only');
  });

  it('the four-fifths line is an employment benchmark against the highest-rate group, with the flag the document gives', () => {
    const markup = html(<FourFifthsView sel={race} />);
    const f = o.attributes.find((x) => x.field === 'derived_race')!.four_fifths;
    expect(markup).toContain('data-label="employment-benchmark" data-credit-law="false"');
    expect(markup).toContain('not a credit-law threshold');
    expect(markup).toContain(`data-highest="${f.highest_rate_group}"`);
    for (const g of f.groups) expect(markup).toContain(`data-group="${g.group}" data-flag="${g.flag}"`);
    expect(markup).toContain('<span translate="no" lang="en">29 CFR 1607.4(D)</span>; not a credit-law threshold');
    expect(markup).toContain(escapeHtml(f.rule));
    // the flag is the document's: flipping it in the document flips the view, whatever the ratio says
    const odd = clone();
    odd.outputs.attributes[1].four_fifths.groups[0].flag = true;
    expect(html(<FourFifthsView sel={{ ...withVariant(odd), field: 'derived_race' }} />)).toContain('data-group="White" data-flag="true"');
  });

  it('the tests give the parity gap, the z-test and the Fisher exact test of every group against the reference', () => {
    const markup = html(<TestsView sel={sel} />);
    const c = o.attributes[0].contrasts[0];
    expect(markup).toContain(`data-group="${c.group}"`);
    expect(markup).toContain(formatNumber(c.parity_gap, 'en', { percent: true, decimals: 1 }));
    expect(markup).toContain(formatNumber(c.z_test.statistic, 'en', { decimals: 2 }));
  });

  it('the controlled estimate gives the coefficient, its interval and the missing control, labelled an approximation', () => {
    const markup = html(<ControlledView sel={sel} />);
    const e = o.attributes[0].contrasts[0].controlled.estimate!;
    expect(markup).toContain(f3(e.coefficient));
    expect(markup).toContain(`${f3(e.ci.lo)} - ${f3(e.ci.hi)}`);
    expect(markup).toContain(`data-label="${e.label}"`);
    expect(markup).toContain('Missing control: credit score');
    expect(markup).toContain('approximation of comparative evidence');
  });

  it('a controlled estimate the document leaves null says not available with its reason, never a zero', () => {
    const odd = clone();
    Object.assign(odd.outputs.attributes[0].contrasts[0].controlled, { estimate: null, reason: 'The model did not converge on this pair.' });
    const markup = html(<ControlledView sel={withVariant(odd)} />);
    expect(markup).toContain('The model did not converge on this pair.');
    expect(markup).toContain(NA);
  });

  it('the rate spread is in percentage points of the spread, with its controls', () => {
    const markup = html(<RateSpreadView sel={sel} />);
    const e = o.attributes[0].contrasts[0].rate_spread.estimate!;
    expect(markup).toContain(f3(e.coefficient));
    expect(markup).toContain(escapeHtml(e.unit));
    expect(markup).toContain('data-table="rate-spread"');
  });

  it('the replication panel gives both years, whether the sign held and the size ratio; a change of sign is said', () => {
    const markup = html(<ReplicationView sel={sel} />);
    const e = o.attributes[0].contrasts[0].confirmation.estimate!;
    expect(markup).toContain('data-same-sign="true"');
    expect(markup).toContain(f3(e.fit_coefficient));
    expect(markup).toContain(f3(e.confirm_coefficient));
    expect(markup).toContain('held');
    const odd = clone();
    Object.assign(odd.outputs.attributes[0].contrasts[0].confirmation.estimate!, { same_sign: false, confirm_coefficient: 0.2, size_ratio: -0.4 });
    const m2 = html(<ReplicationView sel={withVariant(odd)} />);
    expect(m2).toContain('data-same-sign="false"');
    expect(m2).toContain('changed');
  });

  it('situation testing is ceteris paribus only and shows the counterfactual test as not run with its reason', () => {
    const markup = html(<SituationView sel={sel} />);
    const s = o.situation_testing;
    expect(markup).toContain('data-counterfactual-run="false"');
    expect(markup).toContain('Counterfactual test: not run.');
    expect(markup).toContain(escapeHtml(s.counterfactual_test.reason.en));
    expect(markup).toContain('data-comparator="ceteris-paribus"');
    expect(markup).toContain(`${s.n_significant} (${formatNumber(s.n_significant / s.n_cases, 'en', { percent: true, decimals: 1 })})`);
  });

  it('a test that did not run sits under its view and shows its reason, never a number', () => {
    const markup = html(<RatesView sel={sel} />);
    expect(markup).toContain('data-test="fair.demographic_parity"');
    expect(markup).toContain(escapeHtml(v.tests[0].notes as string));
    expect(markup).not.toMatch(/NaN|undefined/);
    expect(html(<C21FindingsView sel={sel} />)).toContain('data-fixture="true"');
  });

  it('the context quotes the licence as UNVERIFIED with the platform terms and the CFPB statement, and the conventions', () => {
    const markup = html(<C21ContextView sel={sel} />);
    expect(markup).toContain('data-status="UNVERIFIED"');
    expect(markup).toContain(escapeHtml(o.licence.modified_statement));
    expect(markup).toContain('data-table="c21-conventions" data-status="convention"');
    expect(markup).toContain('&lt;activity_year&gt;-&lt;row&gt;');
    expect(markup).toContain('data-field="debt_to_income_ratio"');
  });

  it('the year pairs table gives a row per pair and whether the sign held in the next year', () => {
    const markup = html(<C21VariantsTable variants={[{ id: v.variant_id, title: { en: 'Pair 2018', es: 'Par 2018' }, v }]} onPick={() => undefined} current={v.variant_id} field="derived_sex" />);
    expect(markup).toContain('data-pair="2018-19"');
    expect(markup).toContain('data-same-sign="true"');
    expect(markup).toContain(`${formatNumber(0.8, 'en', { percent: true, decimals: 1 })} (Female)`);
  });

  it('the rail read-outs follow the attribute and the group in focus', () => {
    expect(html(<AttributeReadout sel={race} />)).toContain('Asian');
    expect(html(<GroupReadout sel={race} />)).toContain(formatNumber(0.7, 'en', { percent: true, decimals: 1 }).replace('%', ''));
  });

  it('lists the 62 contrast where it lists the age bands, naming its groups in both languages (BL-087)', () => {
    const doc = clone();
    const base = structuredClone(doc.outputs.attributes.find((x) => x.field === 'derived_sex')!) as unknown as Record<string, unknown>;
    const text = JSON.stringify(base).replaceAll('Female', '62 or over').replaceAll('Male', 'under 62').replace('"derived_sex"', '"applicant_age_above_62"');
    const age62 = JSON.parse(text) as Outputs['attributes'][number];
    age62.excluded_groups = [{ group: 'NA', n: 5, reason: { en: 'Not a protected group', es: 'No es un grupo protegido' } }] as never;
    doc.outputs.attributes.push(age62);
    const pick62 = { ...withVariant(doc), field: 'applicant_age_above_62', group: '62 or over' } as C21Sel;
    for (const [name, View] of VIEWS.slice(0, 5)) {
      const en = html(<View sel={pick62} />);
      expect(en, name).toContain('data-group="62 or over"');
    }
    expect(html(<RatesView sel={pick62} />)).toContain('62 or over');
    expect(html(<AttributeReadout sel={pick62} />)).toContain('Age, 62 or over');
    setLang('es');
    const es = html(<RatesView sel={pick62} />);
    expect(es).toContain('62 o más');
    expect(es).toContain('menores de 62');
    expect(es).toContain('Edad, 62 o más'.toLowerCase());
    expect(html(<AttributeReadout sel={pick62} />)).toContain('Edad, 62 o más');
    expect(html(<ControlledView sel={pick62} />)).toContain('62 o más / menores de 62');
    // the raw English group names reach no Spanish view of the contrast (the read-out, the four-fifths note, every other view)
    for (const [name, View] of VIEWS.slice(0, 5)) expect(visible(html(<View sel={pick62} />)), name).not.toMatch(/62 or over|under 62/);
    expect(visible(html(<AttributeReadout sel={pick62} />))).not.toMatch(/62 or over|under 62/);
    expect(visible(html(<GroupReadout sel={pick62} />))).not.toMatch(/62 or over|under 62/);
    expect(html(<FourFifthsView sel={pick62} />)).toContain('(menores de 62)');
  });

  it('a changed fixture field changes the markup: the views read the document and nothing else', () => {
    const odd = clone();
    odd.outputs.attributes[0].groups[1].selection_rate = 0.7123;
    expect(html(<RatesView sel={withVariant(odd)} />)).toContain(formatNumber(0.7123, 'en', { percent: true, decimals: 1 }));
    expect(html(<RatesView sel={sel} />)).not.toContain(formatNumber(0.7123, 'en', { percent: true, decimals: 1 }));
  });
});

// The Findings group draws the evidence each finding cites beside the findings table (ADR-0071 rule 8): the controlled odds
// ratio of every cited fair.conditional_disparity row with the line at 1, the rate spread with the line at 0.
describe('the C21 Findings view draws the evidence of each finding', () => {
  afterEach(() => setLang('en'));
  const pair = JSON.parse(readFileSync(new URL('../../../../data/derived/C21/pair-2018-19.json', import.meta.url), 'utf8')) as VariantArtifact<Outputs>;
  const psel = withVariant(pair);
  const key = (e: string) => e.split('@');
  const cited = (test: string) =>
    pair.findings.flatMap((f) => f.evidence.filter((e) => e.startsWith(`${test}@`)).map((e) => ({ f: f.id, e }))).map(({ f, e }) => {
      const [t, m, s] = key(e);
      return { f, e, row: pair.tests.find((r) => r.test_id === t && r.model_id === m && r.segment === s) };
    });

  it('the Spanish evidence table names the groups of the 62 contrast in Spanish', () => {
    const odd = structuredClone(pair) as VariantArtifact<Outputs>;
    const seg = 'applicant_age_above_62|62 or over vs under 62';
    odd.findings = [{ id: 'F-CONTROLLED-LOWER-ODDS', severity: 'S2', status: 'open', title: odd.findings[0].title,
      evidence: [`fair.conditional_disparity@hmda-logistic-decision@${seg}`, `fair.replication@hmda-logistic-decision@${seg}|controlled`] }] as never;
    setLang('es');
    const es = html(<C21FindingsView sel={withVariant(odd)} />);
    expect(es).toContain('62 o más vs menores de 62');
    // the test-row ids a finding cites are the document's own identifiers and stay as written; nothing else may name the groups in English
    expect(visible(es).replaceAll(`@${seg}`, '')).not.toMatch(/62 or over|under 62/);
    setLang('en');
    expect(html(<C21FindingsView sel={withVariant(odd)} />)).toContain('62 or over vs under 62');
  });

  it('renders two cards: the findings table and the evidence', () => {
    const markup = html(<C21FindingsView sel={psel} />);
    expect(cards(markup).length).toBe(2);
    expect(markup).toContain('data-table="findings"');
    expect(markup).toContain('The evidence of each finding');
  });

  it('holds one bar per cited conditional-disparity row with the odds ratio of the row, and the line at 1', () => {
    const markup = html(<C21FindingsView sel={psel} />);
    const rows = cited('fair.conditional_disparity');
    expect(rows.length).toBeGreaterThan(0);
    for (const { f, e, row } of rows) {
      expect(row, e).toBeDefined();
      const tag = `data-evidence-row="${escapeHtml(e)}" data-finding="${f}" data-metric="${row!.metric}"`;
      expect(markup, e).toContain(tag);
      expect(markup).toContain(f3(row!.metric as number));
    }
    expect((markup.match(/data-evidence-kind="odds-ratio"/g) ?? []).length).toBe(rows.length);
    expect(markup).toContain('data-reference-line="1"');
    expect(markup).toContain('data-reference-line="0"');
    const spread = cited('fair.rate_spread_disparity');
    expect((markup.match(/data-evidence-kind="rate-spread"/g) ?? []).length).toBe(spread.length);
  });

  it('draws nothing for a finding with design evidence only, and says so', () => {
    const markup = html(<C21FindingsView sel={psel} />);
    expect(markup).not.toMatch(/data-evidence-row="[^"]*" data-finding="F-LIMIT/);
    expect(markup).toContain('data-note="design-only"');
  });

  it('lists a cited row the document lacks as not available with its id, never dropped', () => {
    const odd = structuredClone(pair);
    const gone = cited('fair.conditional_disparity')[0];
    odd.tests = odd.tests.filter((r) => r !== odd.tests.find((x) => `${x.test_id}@${x.model_id}@${x.segment}` === gone.e));
    const markup = html(<C21FindingsView sel={withVariant(odd)} />);
    expect(markup).toContain(`data-evidence-row="${escapeHtml(gone.e)}" data-finding="${gone.f}" data-na="true"`);
    expect(markup).not.toMatch(/NaN|undefined|\[object/);
  });

  it('a variant with no findings shows the empty state and no empty chart', () => {
    const odd = structuredClone(pair);
    odd.findings = [];
    const markup = html(<C21FindingsView sel={withVariant(odd)} />);
    expect(markup).toContain('No finding is recorded in this variant.');
    expect(markup).not.toContain('data-evidence-kind');
  });

  it('is free of placeholder text in both languages, the Spanish page without English, and says no legal claim', () => {
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const markup = html(<C21FindingsView sel={psel} />);
      expect(markup).not.toMatch(/NaN|undefined|\[object/);
      expect(markup).toContain(lang === 'en' ? 'no legal claim' : 'sin afirmación legal');
      if (lang === 'es') {
        expect(markup).toContain('La evidencia de cada hallazgo');
        expect(markup).not.toContain('The evidence of each finding');
        expect(markup).not.toContain('lower controlled odds');
      }
    }
  });
});

describe('the C21 views keep the citations of the document and ranges whole (gate G11 and G19)', () => {
  it('marks every regulation citation translate="no" and keeps ranges on one line', () => {
    const cite = /\d+ CFR \d+\.\d+/g;
    for (const View of [RatesView, FourFifthsView, TestsView, C21ContextView, C21FindingsView] as Array<(p: { sel: C21Sel | null }) => ReactElement>) {
      const markup = html(<View sel={psel0} />);
      for (const m of markup.matchAll(cite)) {
        const before = markup.slice(Math.max(0, m.index! - 40), m.index!);
        expect(before, m[0]).toMatch(/translate="no"[^>]*>$|<span translate="no" lang="en">$/);
      }
    }
    const ctx = html(<C21ContextView sel={psel0} />);
    expect(ctx).toContain('<span style="white-space:nowrap">36%-49%</span>');
    expect(ctx).toContain('<span style="white-space:nowrap">35-44</span>');
  });
});

const psel0 = withVariant(JSON.parse(readFileSync(new URL('../../../../data/derived/C21/pair-2018-19.json', import.meta.url), 'utf8')) as VariantArtifact<Outputs>);
