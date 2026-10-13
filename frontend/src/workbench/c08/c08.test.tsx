// U6-W: the C08 instrument rendered on the server from the c08-outputs and c08-models fixtures
// (docs/contracts/fixtures/c08). A loss given default outside [0, 1] is shown with its flag and never clipped; the
// proxy is named a proxy with its bias; the floors' bite and the downturn add-on are the document's numbers; a rung
// without a number says why; a test that did not run shows its reason.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, readFixture, setLang } from '../c03/u6-testkit';
import { useC08Instrument } from './instrument';
import { defaultSel, outputsOf, type C08Sel } from './selection';
import { C08ContextView, C08FindingsView, C08VariantsTable, CohortReadout, EndpointReadout, FloorReadout, RungReadout } from './C08Common';
import { DistributionView, ProxyView } from './SeverityViews';
import { CalibrationView, EndpointsView, RealisedView, RungsView } from './ModelViews';
import { DownturnView, FloorsView } from './DownturnViews';

type Outputs = components['schemas']['c08Outputs'];

const variant = readFixture<VariantArtifact<Outputs>>('c08', 'variant-default-cohort-fixture.json');
const models = readFixture<ModelsArtifact>('c08', 'models-fixture.json');
const data = fixtureData('C08', variant as unknown as VariantArtifact, models, { en: 'LGD and downturn LGD', es: 'LGD y LGD de recesión' });
const o = variant.outputs;
const sel = defaultSel(data) as C08Sel;
const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const NA = formatNumber(null, 'en');

const VIEWS: Array<[string, (p: { sel: C08Sel | null }) => ReactElement]> = [
  ['Distribution', DistributionView], ['Proxy', ProxyView], ['Rungs', RungsView], ['Realised', RealisedView], ['Calibration', CalibrationView],
  ['Endpoints', EndpointsView], ['Downturn', DownturnView], ['Floors', FloorsView], ['Findings', C08FindingsView], ['Context', C08ContextView],
];

function Names() {
  const inst = useC08Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC08Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C03' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C08 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C08 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('Severity|Models|Downturn and floors|Findings|Variants');
    function Count() {
      const inst = useC08Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>6</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('default-cohort');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('the distribution shows the masses at 0 and 1 and the values outside [0, 1] with their flags, unclipped', () => {
    const markup = html(<DistributionView sel={sel} />);
    const d = o.lgd_distribution;
    expect(markup).toContain(`data-mass="zero"`);
    expect(markup).toContain(formatNumber(d.mass_at_zero.n, 'en', { decimals: 0 }));
    expect(markup).toContain(pct(d.mass_at_one.share));
    expect(markup).toContain(`data-range="below-zero"`);
    expect(markup).toContain(formatNumber(d.n_below_zero, 'en', { decimals: 0 }));
    expect(markup).toContain(pct(d.share_above_one));
    // the lowest is below zero and the highest above one: both printed as they are, with the flag
    expect(d.lowest.flag).toBe('below-zero');
    expect(d.highest.flag).toBe('above-one');
    expect(markup).toMatch(/data-extreme="lowest"[^>]*data-flag="below-zero"/);
    expect(markup).toMatch(/data-extreme="highest"[^>]*data-flag="above-one"/);
    expect(markup).toContain(pct(d.highest.value));
    expect(markup).toContain(pct(d.lowest.value));
    expect(markup).toContain(`data-treatment="${d.treatment}"`);
    for (let i = 0; i < d.bins.length; i++) expect(markup).toContain(`data-bin="${i}"`);
  });

  it('the proxy is said to be a proxy, with its formula, its fields, its bias and its exposure in full', () => {
    const markup = html(<ProxyView sel={sel} />);
    expect(markup).toContain(escapeHtml(o.lgd_proxy.formula));
    expect(markup).toContain(escapeHtml(o.lgd_proxy.definition.en));
    expect(markup).toContain(escapeHtml(o.lgd_proxy.bias_statement.en));
    expect(markup).toContain('data-bias="downward"');
    expect(markup).toContain(o.lgd_proxy.exposure_field);
    expect(markup).toContain(formatNumber(o.exposure.gross_approval_total, 'en', { decimals: 0 }));
    expect(markup).toContain(formatNumber(o.exposure.gross_charge_off_total, 'en', { decimals: 0 }));
    expect(markup).toContain('data-freddie-mac="false"');
    expect(markup).toContain(escapeHtml(o.data_status.freddie_mac_reason as string));
  });

  it('the rungs give R2, RMSE, MAE, Spearman and the calibration gap; a missing value is not available with its reason', () => {
    const markup = html(<RungsView sel={sel} />);
    for (const r of o.rung_comparison) expect(markup).toContain(`data-rung="${r.rung_id}"`);
    expect(markup).toContain(formatNumber(0.15, 'en', { digits: 3 }));
    const beta = o.rung_comparison.find((r) => r.r2 === null)!;
    expect(markup).toContain(escapeHtml(beta.reason as string));
    expect(markup).toMatch(new RegExp(`data-rung="${beta.rung_id}"[\\s\\S]*?data-na="true"`));
  });

  it('realised against predicted gives each cohort of the rung chosen, with the interval and the gap', () => {
    const markup = html(<RealisedView sel={sel} />);
    const rows = o.realised_vs_predicted.filter((r) => r.rung_id === sel.rung);
    expect(rows.length).toBeGreaterThan(0);
    for (const r of rows) {
      expect(markup).toContain(`data-cohort="${r.cohort_id}"`);
      expect(markup).toContain(pct(r.realised.value));
      expect(markup).toContain(pct(r.predicted.value));
      expect(markup).toContain(pct(r.ci_high));
    }
    // a rung that has no row in this document says so, it is not an empty chart
    const none = html(<RealisedView sel={{ ...sel, rung: 'L3-beta' }} />);
    expect(none).toContain('data-state="unavailable"');
  });

  it('the calibration by bucket gives each bucket of the rung; a rung without buckets says so', () => {
    const markup = html(<CalibrationView sel={{ ...sel, rung: 'L2-fractional-logit' }} />);
    for (const b of o.calibration_by_bucket) expect(markup).toContain(`data-bucket="${b.bucket}"`);
    expect(html(<CalibrationView sel={{ ...sel, rung: 'L1-ols' }} />)).toContain('data-state="unavailable"');
  });

  it('the endpoint sensitivity gives every epsilon with the mean prediction and the RMSE', () => {
    const markup = html(<EndpointsView sel={sel} />);
    for (const e of o.endpoint_sensitivity) {
      expect(markup).toContain(`data-epsilon="${e.epsilon}"`);
      expect(markup).toContain(pct(e.mean_predicted.value));
    }
  });

  it('the downturn view gives the add-on, the crisis loss and whether the add-on covered it, with the shortfall', () => {
    const markup = html(<DownturnView sel={sel} />);
    for (const r of o.downturn.rows) {
      expect(markup).toContain(`data-cohort="${r.cohort_id}"`);
      expect(markup).toContain(`data-covered="${r.covered}"`);
      expect(markup).toContain(pct(r.add_on));
      expect(markup).toContain(pct(r.crisis_realised_lgd.value));
    }
    expect(markup).toContain(pct(o.downturn.coverage.share_covered));
    expect(markup).toContain(escapeHtml(o.downturn.period.macro_source));
    expect(markup).toContain(escapeHtml(o.downturn.approach.en));
  });

  it('the floors view gives the bite of each floor and the transcribed cells with their paragraph', () => {
    const markup = html(<FloorsView sel={sel} />);
    for (const r of o.floors_bite.rows) {
      expect(markup).toContain(`data-floor="${r.floor_id}"`);
      expect(markup).toContain(pct(r.share_binding));
      expect(markup).toContain(pct(r.uplift));
    }
    const fit = (models as unknown as { fit: components['schemas']['c08Fit'] }).fit;
    for (const c of fit.floors.cells) expect(markup).toContain(`data-cell="${c.id}"`);
    expect(markup).toContain('CRE32.16');
    expect(markup).toContain(escapeHtml(o.floors_bite.note.en));
  });

  it('the models view carries the tests of the engine: one that did not run shows its reason and no number', () => {
    const markup = html(<RungsView sel={sel} />);
    const t = variant.tests[0];
    expect(markup).toContain(`data-test="${t.test_id}"`);
    expect(markup).toContain(escapeHtml(t.notes as string));
    expect(markup).not.toMatch(/NaN|undefined/);
  });

  it('the findings and the context state the fixture, the training rule, the workout treatment and the Freddie Mac slot', () => {
    expect(html(<C08FindingsView sel={sel} />)).toContain('data-fixture="true"');
    const markup = html(<C08ContextView sel={sel} />);
    expect(markup).toContain(o.training.cutoff_date);
    expect(markup).toContain(escapeHtml(o.training.closure_rule.en));
    expect(markup).toContain(escapeHtml(o.workout.incomplete_workouts.reason as string));
    expect(markup).toContain('data-freddie-mac="false"');
    expect(markup).toContain(escapeHtml(o.data_status.notice.en));
  });

  it('the cohorts table gives the mean LGD proxy of each default cohort with its flag', () => {
    const markup = html(<C08VariantsTable variants={[{ id: variant.variant_id, title: { en: 'Defaults 2009-10', es: 'Incumplimientos 2009-10' }, v: variant }]} onPick={() => undefined} current={variant.variant_id} />);
    expect(markup).toContain(`data-variant="${variant.variant_id}"`);
    expect(markup).toContain(pct(o.lgd_distribution.mean.value));
    expect(markup).toContain(pct(o.lgd_distribution.median.value));
  });

  it('the Spanish view is written in Spanish', () => {
    setLang('es');
    expect(html(<DistributionView sel={sel} />)).toContain('Distribución de la LGD');
    expect(html(<DistributionView sel={sel} />)).not.toContain('LGD distribution');
    expect(html(<ProxyView sel={sel} />)).toContain('es un proxy');
  });
});

function RailSection({ at, doc = data }: { at: number; doc?: typeof data }) {
  const inst = useC08Instrument(doc, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C08 rail', () => {
  afterEach(() => setLang('en'));

  it('has four sections, each with one control group and one read-out', () => {
    function Sections() {
      const inst = useC08Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('rung|endpoint|cohort|floor');
    for (const at of [0, 1, 2, 3]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('the rung, the cohort and the floor are one select each; the endpoint keeps its few chips', () => {
    expect(railHtml(0)).toMatch(/data-control="c08-rung"[^>]*><label[^>]*>Model<\/label><select/);
    expect(railHtml(2)).toMatch(/data-control="c08-cohort"[^>]*><label[^>]*>Default cohort<\/label><select/);
    expect(railHtml(3)).toMatch(/data-control="c08-segment"[^>]*><label[^>]*>Segment<\/label><select/);
    expect(railHtml(1)).toMatch(/data-control="c08-epsilon"[^>]*><span[^>]*>Endpoint shift<\/span><div class="caos-chip-row"/);
    expect(railHtml(0).match(/<option/g)?.length).toBe(o.rung_comparison.length);
  });

  it('shows a model by its name, never its internal id, and no raw amount in either language', () => {
    expect(railHtml(0)).toContain('Fractional logit');
    expect(railHtml(0)).not.toContain('>L2-fractional-logit<');
    for (const at of [0, 1, 2, 3]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
  });

  it('the rung read-out gives its numbers and a missing one as not available', () => {
    const base = defaultSel(data) as C08Sel;
    expect(html(<RungReadout sel={{ ...base, rung: 'L2-fractional-logit' }} />)).toContain(formatNumber(0.38, 'en', { digits: 3 }));
    expect(html(<RungReadout sel={{ ...base, rung: 'L3-beta' }} />)).toContain(NA);
  });

  it('the endpoint read-out moves with the shift chosen', () => {
    const base = defaultSel(data) as C08Sel;
    expect(html(<EndpointReadout sel={{ ...base, epsilon: 0.0001 }} />)).toContain(pct(0.6));
    expect(html(<EndpointReadout sel={{ ...base, epsilon: 0.01 }} />)).toContain(pct(0.66));
  });

  it('the cohort read-out gives realised, predicted and the gap, and an LGD above one keeps its value and its flag', () => {
    const base = defaultSel(data) as C08Sel;
    const markup = html(<CohortReadout sel={{ ...base, rung: 'L2-fractional-logit', cohort: '2009-10' }} />);
    expect(markup).toContain(pct(0.74));
    expect(markup).toContain(pct(0.71));
    const hot = structuredClone(variant) as VariantArtifact<Outputs>;
    hot.outputs.realised_vs_predicted[5] = { ...hot.outputs.realised_vs_predicted[5], realised: { value: 1.08, flag: 'above-one' } };
    const hotData = { ...data, variant: hot as unknown as VariantArtifact };
    const shown = html(<CohortReadout sel={{ ...(defaultSel(hotData) as C08Sel), rung: 'L2-fractional-logit', cohort: '2009-10' }} />);
    expect(shown).toContain(pct(1.08));
    expect(shown).toContain('above 1');
    expect(shown).not.toContain(pct(1));
  });

  it('the floor read-out gives the floor, how often it binds and the mean before and after', () => {
    const base = defaultSel(data) as C08Sel;
    const markup = html(<FloorReadout sel={{ ...base, segment: 'sme-unsecured' }} />);
    expect(markup).toContain(pct(0.25));
    expect(markup).toContain(pct(0.12));
    expect(markup).toContain(pct(0.63));
  });
});
