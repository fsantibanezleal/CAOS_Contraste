// U6-W: the C09 instrument rendered on the server from the c09-outputs and c09-models fixtures
// (docs/contracts/fixtures/c09). The known CCF of the generator is drawn against every estimate; a CCF outside [0, 1]
// is shown with its flag and never clipped; the EAD back-test is in currency by utilisation band; a test that did not
// run shows its reason; no view draws a number the fixture does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, readFixture, setLang } from '../c03/u6-testkit';
import { useC09Instrument } from './instrument';
import { defaultSel, outputsOf, type C09Sel } from './selection';
import { BandReadout, C09ContextView, C09FindingsView, C09VariantsTable, DesignReadout, ModelReadout, TreatmentReadout } from './C09Common';
import { ByDesignView, DistributionView } from './CcfViews';
import { BacktestView, FloorsView, ModelsView } from './EadViews';

type Outputs = components['schemas']['c09Outputs'];

const variant = readFixture<VariantArtifact<Outputs>>('c09', 'variant-acceleration-level-fixture.json');
const models = readFixture<ModelsArtifact>('c09', 'models-fixture.json');
const data = fixtureData('C09', variant as unknown as VariantArtifact, models, { en: 'EAD and CCF for revolving lines', es: 'EAD y CCF de líneas rotativas' });
const o = variant.outputs;
const sel = defaultSel(data) as C09Sel;
const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const NA = formatNumber(null, 'en');

const VIEWS: Array<[string, (p: { sel: C09Sel | null }) => ReactElement]> = [
  ['By design', ByDesignView], ['Distribution', DistributionView], ['Back-test', BacktestView], ['Models', ModelsView], ['Floors', FloorsView],
  ['Findings', C09FindingsView], ['Context', C09ContextView],
];

function Names() {
  const inst = useC09Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC09Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C08' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C09 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C09 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('CCF|EAD|Findings|Variants');
    function Count() {
      const inst = useC09Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>5</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('acceleration-level');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('the known CCF is drawn against every estimate of the rail design, with the estimator, the bias, the interval and the shares outside [0, 1]', () => {
    const designs = [...new Set(o.ccf_by_design.rows.map((r) => r.design))];
    const all: string[] = [];
    for (const design of designs) {
      const markup = html(<ByDesignView sel={{ ...sel, design }} />);
      all.push(markup);
      expect(markup).toContain(`data-truth="${o.generator.true_ccf.value}"`);
      expect(markup).toContain(pct(o.generator.true_ccf.value));
      expect(markup).toContain(escapeHtml(o.generator.notice.en));
      expect(markup).toContain(pct(o.ccf_by_design.tolerance));
      for (const r of o.ccf_by_design.rows) {
        const row = `data-design="${r.design}" data-treatment="${r.treatment}" data-estimator="${r.estimator}"`;
        if (r.design !== design) {
          expect(markup, `${design}: a row of ${r.design}`).not.toContain(`data-design="${r.design}"`);
          continue;
        }
        expect(markup).toContain(row);
        expect(markup).toContain(pct(r.estimate.value));
        expect(markup).toContain(pct(r.bias));
        expect(markup).toContain(pct(r.ci_low));
        expect(markup).toContain(pct(r.share_above_one));
      }
    }
    expect(all.join('')).toContain(`data-tolerance="true"`);
    expect(all.join('')).toContain(`data-tolerance="false"`);
  });

  it('an estimate above one is printed as it is, with its flag, never clipped', () => {
    const markup = html(<ByDesignView sel={sel} />);
    const hot = o.ccf_by_design.rows.find((r) => r.estimate.flag === 'above-one')!;
    expect(hot.estimate.value).toBeGreaterThan(1);
    expect(markup).toMatch(/data-estimate-flag="above-one"/);
    expect(markup).toContain(pct(hot.estimate.value));
  });

  it('the distribution gives every bin, the counts below zero and above one, and states that nothing is clipped', () => {
    const markup = html(<DistributionView sel={sel} />);
    const d = o.ccf_distribution;
    for (let i = 0; i < d.counts.length; i++) expect(markup).toContain(`data-bin="${i}"`);
    expect(markup).toContain(`data-range="below-zero"`);
    expect(markup).toContain(formatNumber(d.n_below_zero, 'en', { decimals: 0 }));
    expect(markup).toContain(`data-range="above-one"`);
    expect(markup).toContain(formatNumber(d.n_above_one, 'en', { decimals: 0 }));
    expect(markup).toMatch(/never clipped|not clipped/);
  });

  it('the back-test gives each utilisation band of the model chosen in currency, with the gap and the light', () => {
    const markup = html(<BacktestView sel={sel} />);
    const rows = o.ead_backtest.rows.filter((r) => r.model_id === sel.model);
    expect(rows.length).toBeGreaterThan(0);
    for (const r of rows) {
      expect(markup).toContain(`data-band="${r.band_id}"`);
      expect(markup).toContain(formatNumber(r.predicted_ead, 'en', { decimals: 0 }));
      expect(markup).toContain(formatNumber(r.realised_ead, 'en', { decimals: 0 }));
      expect(markup).toContain(`data-light="${r.light}"`);
    }
    expect(markup).toContain(o.ead_backtest.currency);
  });

  it('a model with no back-test row says so; a prediction outside its range is flagged', () => {
    expect(html(<BacktestView sel={{ ...sel, model: 'm-utilisation' }} />)).toContain('data-state="unavailable"');
    const odd = structuredClone(variant) as VariantArtifact<Outputs>;
    odd.outputs.ead_backtest.rows[0] = { ...odd.outputs.ead_backtest.rows[0], prediction_flag: 'outside-range' };
    const markup = html(<BacktestView sel={{ ...(defaultSel({ ...data, variant: odd as unknown as VariantArtifact }) as C09Sel), model: 'm-fixed' }} />);
    expect(markup).toContain('data-flag="outside-range"');
  });

  it('the models table gives the kind, the design, the treatment, and the clipped counts of a direct EAD model only', () => {
    const markup = html(<ModelsView sel={sel} />);
    for (const m of o.ead_models) expect(markup).toContain(`data-model="${m.model_id}"`);
    const direct = o.ead_models.find((m) => m.kind === 'direct-ead')!;
    expect(markup).toContain(formatNumber(direct.n_clipped_below as number, 'en', { decimals: 0 }));
    expect(markup).toContain(formatNumber(direct.n_clipped_above as number, 'en', { decimals: 0 }));
    expect(markup).toContain(NA);
  });

  it('the floors give the supervisory CCF of each facility class, the binding share and the small-undrawn rule', () => {
    const markup = html(<FloorsView sel={sel} />);
    for (const r of o.ead_floor.rows) {
      expect(markup).toContain(`data-class="${r.facility_class}"`);
      expect(markup).toContain(pct(r.sa_ccf));
      expect(markup).toContain(pct(r.share_binding));
      expect(markup).toContain(r.reference);
    }
    expect(markup).toContain(escapeHtml(o.ead_floor.rule.en));
    expect(markup).toContain(escapeHtml(o.small_undrawn.reference));
    expect(markup).toContain(formatNumber(o.small_undrawn.n_switched, 'en', { decimals: 0 }));
  });

  it('the tests of the engine sit under the view they belong to: one that did not run shows its reason and no number', () => {
    // the CCF bias test sits under the estimates, the EAD back-test under the back-test
    const ccf = html(<ByDesignView sel={sel} />);
    const ead = html(<BacktestView sel={sel} />);
    for (const t of variant.tests) {
      const host = t.test_id.includes('ead') ? ead : ccf;
      expect(host).toContain(`data-test="${t.test_id}"`);
      expect(host).toContain(escapeHtml(t.notes as string));
    }
    expect(ccf + ead).not.toMatch(/NaN|undefined/);
  });

  it('the context gives the convention with its US terms, the generator, the level and the replications', () => {
    const markup = html(<C09ContextView sel={sel} />);
    expect(markup).toContain(escapeHtml(o.convention.formula));
    expect(markup).toContain(escapeHtml(o.convention.us_terms.en));
    expect(markup).toContain(escapeHtml(o.level_description.en));
    expect(markup).toContain(o.generator.shaped_on);
    expect(markup).toContain(o.replications.test.seeds.join(', '));
    expect(markup).toContain(formatNumber(o.replications.test.n_defaults, 'en', { decimals: 0 }));
    expect(html(<C09FindingsView sel={sel} />)).toContain('data-fixture="true"');
  });

  it('the levels table gives the bias of the untreated fixed-horizon CCF at each acceleration level', () => {
    const markup = html(<C09VariantsTable variants={[{ id: variant.variant_id, title: { en: 'Level 5', es: 'Nivel 5' }, v: variant }]} onPick={() => undefined} current={variant.variant_id} />);
    expect(markup).toContain(`data-variant="${variant.variant_id}"`);
    expect(markup).toContain(pct(0.44));
    expect(markup).toContain(`${o.level}`);
  });

  it('the Spanish view is written in Spanish', () => {
    setLang('es');
    expect(html(<ByDesignView sel={sel} />)).toContain('CCF conocido');
    expect(html(<ByDesignView sel={sel} />)).not.toContain('Known CCF');
  });
});

function RailSection({ at }: { at: number }) {
  const inst = useC09Instrument(data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C09 rail', () => {
  afterEach(() => setLang('en'));

  it('has four sections, each with one control and one read-out', () => {
    function Sections() {
      const inst = useC09Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('design|treatment|model|band');
    for (const at of [0, 1, 2, 3]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('the design keeps its three chips; the treatment, the model and the band are one select each', () => {
    expect(railHtml(0)).toMatch(/data-control="c09-design"[^>]*><span[^>]*>Reference-date design<\/span><div class="caos-chip-row"/);
    expect(railHtml(1)).toMatch(/data-control="c09-treatment"[^>]*><label[^>]*>Treatment of CCF outside 0 to 1<\/label><select/);
    expect(railHtml(2)).toMatch(/data-control="c09-model"[^>]*><label[^>]*>EAD model<\/label><select/);
    expect(railHtml(3)).toMatch(/data-control="c09-band"[^>]*><label[^>]*>Utilisation band<\/label><select/);
    expect(railHtml(2).match(/<option/g)?.length).toBe(o.ead_models.length);
    expect(railHtml(3).match(/<option/g)?.length).toBe(o.ead_backtest.bands.length - 1);
  });

  it('names models and bands in words, never an internal id, and prints no raw amount', () => {
    expect(railHtml(2)).not.toContain('>m-fixed<');
    expect(railHtml(2)).toContain('Fixed-horizon CCF');
    const whole = (v: number) => formatNumber(v, 'en', { percent: true, decimals: 0 });
    expect(railHtml(3)).toContain(`${whole(0)} to ${whole(0.25)}`);
    for (const at of [0, 1, 2, 3]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
  });

  it('the design read-out gives the estimate against the truth, and an estimate above one keeps its flag', () => {
    const base = defaultSel(data) as C09Sel;
    const hot = html(<DesignReadout sel={{ ...base, design: 'fixed-horizon', treatment: 'none' }} />);
    expect(hot).toContain(pct(1.04));
    expect(hot).toContain(pct(0.6));
    expect(hot).toContain('above 1');
    const cohort = html(<DesignReadout sel={{ ...base, design: 'cohort', treatment: 'bounded-scale' }} />);
    expect(cohort).toContain(pct(0.64));
    expect(cohort).not.toContain('above 1');
  });

  it('the treatment read-out gives the shares outside [0, 1] of the pair chosen', () => {
    const base = defaultSel(data) as C09Sel;
    const markup = html(<TreatmentReadout sel={{ ...base, design: 'fixed-horizon', treatment: 'none' }} />);
    expect(markup).toContain(pct(0.08));
    expect(markup).toContain(pct(0.31));
  });

  it('a pair the document does not carry is not available, not a zero', () => {
    const base = defaultSel(data) as C09Sel;
    const markup = html(<DesignReadout sel={{ ...base, design: 'cohort', treatment: 'censor' }} />);
    expect(markup).toContain(NA);
  });

  it('the model read-out gives the clipped counts of a direct model and not available for the others', () => {
    const base = defaultSel(data) as C09Sel;
    const direct = html(<ModelReadout sel={{ ...base, model: 'm-direct' }} />);
    expect(direct).toContain('12');
    expect(direct).toContain('31');
    expect(html(<ModelReadout sel={{ ...base, model: 'm-fixed' }} />)).toContain(NA);
  });

  it('the band read-out gives predicted and realised EAD, the relative gap and the light, in the currency', () => {
    const base = defaultSel(data) as C09Sel;
    const markup = html(<BandReadout sel={{ ...base, model: 'm-fixed', band: 'u1' }} />);
    expect(markup).toContain('42,400');
    expect(markup).toContain('40,000');
    expect(markup).toContain(pct(0.06));
    expect(markup).toContain('USD');
  });
});
