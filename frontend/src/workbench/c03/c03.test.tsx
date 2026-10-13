// U6-W: the C03 instrument rendered on the server from the c03-outputs and c03-models fixtures
// (docs/contracts/fixtures/c03). The vintage curves keep what is not yet observed as a gap with its reason, never a
// zero; the five-year mark of a vintage is read only at its mark; the training window of each test cohort ends before
// the cohort starts; a test that did not run shows its reason; no view draws a number the fixture does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { useC03Instrument } from './instrument';
import { defaultSel, outputsOf, type C03Sel } from './selection';
import { C03ContextView, C03FindingsView, C03VariantsTable, HorizonReadout, ModelReadout, VintageReadout } from './C03Common';
import { CurvesView, FiveYearView, StabilityView } from './VintageViews';
import { CalibrationView, RungsView, TrainingView } from './ModelViews';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, readFixture, setLang } from './u6-testkit';

type Outputs = components['schemas']['c03Outputs'];

const variant = readFixture<VariantArtifact<Outputs>>('c03', 'variant-vintage-cohort-fixture.json');
const models = readFixture<ModelsArtifact>('c03', 'models-fixture.json');
const data = fixtureData('C03', variant as unknown as VariantArtifact, models, { en: 'SME PD by vintage', es: 'PD pyme por cosecha' });
const o = variant.outputs;
const sel = defaultSel(data) as C03Sel;
const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const NA = formatNumber(null, 'en');

const VIEWS: Array<[string, (p: { sel: C03Sel | null }) => ReactElement]> = [
  ['Curves', CurvesView], ['Five-year mark', FiveYearView], ['Stability', StabilityView], ['Rungs', RungsView],
  ['Calibration', CalibrationView], ['Training', TrainingView], ['Findings', C03FindingsView], ['Context', C03ContextView],
];

function Names() {
  const inst = useC03Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC03Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C08' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C03 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C03 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('Vintages|Model|Validation|Findings|Variants');
    function Count() {
      const inst = useC03Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>6</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('vintage-cohort');
  });

  it('every view renders and carries its lane; with no selection each says loading, not an empty chart', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('the curves list every vintage with its predicted and observed cumulative PD; a month not observed is not available, never zero', () => {
    const markup = html(<CurvesView sel={sel} />);
    for (const c of o.vintage_curves) {
      expect(markup).toContain(`data-vintage="${c.fiscal_year}"`);
      const last = c.predicted_cumulative_pd.length - 1;
      expect(markup).toContain(pct(c.predicted_cumulative_pd[last]));
    }
    const fy2019 = o.vintage_curves.find((c) => c.fiscal_year === 2019)!;
    expect(fy2019.observed_cumulative_pd[4]).toBeNull();
    expect(markup).toMatch(/data-vintage="2019"[^>]*data-observed="partial"/);
    expect(markup).toContain(escapeHtml(fy2019.reason as string));
    expect(markup).toMatch(/data-vintage="2018"[^>]*data-observed="complete"/);
    expect(markup).toContain(NA);
  });

  it('the five-year mark is read only at the mark: an unobserved mark shows its date, the gap as not available and its reason', () => {
    const markup = html(<FiveYearView sel={sel} />);
    for (const r of o.vintage_summary.rows) {
      expect(markup).toContain(`data-vintage="${r.fiscal_year}"`);
      expect(markup).toContain(`data-mark-observed="${r.mark_observed}"`);
      expect(markup).toContain(r.five_year_mark_date);
      expect(markup).toContain(pct(r.predicted_5y_pd));
      if (r.mark_observed) expect(markup).toContain(pct(r.observed_5y_pd as number));
      else expect(markup).toContain(escapeHtml(r.reason as string));
    }
    expect(markup).toMatch(/data-vintage="2019"[^>]*data-mark-observed="false"[\s\S]*?data-na="true"/);
    // the loans exempt from the target (still active) are counted apart from the resolved ones
    expect(markup).toContain(formatNumber(o.vintage_summary.rows[0].n_exempt_censored, 'en', { decimals: 0 }));
  });

  it('the stability view gives the PSI of each vintage and the document\'s own note on the conventions', () => {
    const markup = html(<StabilityView sel={sel} />);
    for (const r of o.stability.rows) {
      expect(markup).toContain(`data-vintage="${r.fiscal_year}"`);
      expect(markup).toContain(formatNumber(r.psi, 'en', { digits: 3 }));
    }
    expect(markup).toContain(escapeHtml(o.stability.psi_note.en));
    expect(markup).toContain(pct(o.stability.training_mean_5y_pd));
  });

  it('the rungs show AUC with its interval; a rung not fitted on this cohort says so with its reason', () => {
    const markup = html(<RungsView sel={sel} />);
    for (const r of o.rung_comparison) expect(markup).toContain(`data-rung="${r.rung_id}"`);
    const fitted = o.rung_comparison[0];
    expect(markup).toContain(formatNumber(fitted.auc, 'en', { digits: 3 }));
    expect(markup).toContain(formatNumber(fitted.auc_ci_low, 'en', { digits: 3 }));
    const none = o.rung_comparison.find((r) => r.auc === null)!;
    expect(markup).toContain(escapeHtml(none.reason as string));
    expect(markup).toMatch(new RegExp(`data-rung="${none.rung_id}"[\\s\\S]*?data-na="true"`));
  });

  it('the calibration gives every decile, its interval and the scope of the vintages it covers', () => {
    const markup = html(<CalibrationView sel={sel} />);
    for (const d of o.calibration.rows) expect(markup).toContain(`data-decile="${d.decile}"`);
    expect(markup).toContain(escapeHtml(o.calibration.scope));
    expect(markup).toContain(pct(o.calibration.rows[0].ci_high));
  });

  it('the training view shows the window of this cohort and of every test cohort, each ending before its cohort starts', () => {
    const markup = html(<TrainingView sel={sel} />);
    expect(markup).toContain(`data-training="${o.cohort.id}"`);
    expect(markup).toContain(formatNumber(o.training.n_loans, 'en', { decimals: 0 }));
    expect(markup).toContain(escapeHtml(o.training.rationale.en));
    const windows = (models as unknown as { fit: components['schemas']['c03Fit'] }).fit.cohort_windows;
    for (const w of windows) {
      expect(markup).toContain(`data-window="${w.id}"`);
      expect(w.training.last_fy).toBeLessThanOrEqual(w.first_fy - 6);
    }
    expect(markup).toContain(o.training.cutoff_date);
    // crisis in the training is said in words, not left to a colour
    expect(markup).toMatch(/data-crisis="true"/);
  });

  it('the calibration view carries the tests of the engine: one that did not run shows its reason and no number', () => {
    const markup = html(<CalibrationView sel={sel} />);
    const t = variant.tests[0];
    expect(t.light).toBe('not_evaluated');
    expect(markup).toContain(`data-test="${t.test_id}"`);
    expect(markup).toContain(escapeHtml(t.notes as string));
    expect(markup).not.toMatch(/NaN|undefined/);
  });

  it('the findings card says there is none, and states that the numbers are a fixture', () => {
    const markup = html(<C03FindingsView sel={sel} />);
    expect(markup).toContain('No finding is recorded in this variant.');
    expect(markup).toContain('data-fixture="true"');
    expect(markup).toMatch(/<figure class="caos-plot fill"/);
  });

  it('the context gives the target, the vintage definition, the source and its as-of date', () => {
    const markup = html(<C03ContextView sel={sel} />);
    expect(markup).toContain(escapeHtml(o.target.definition.en));
    expect(markup).toContain(o.data_status.files_as_of);
    expect(markup).toContain(escapeHtml(o.data_status.notice.en));
    expect(markup).toContain(`${o.target.horizon_months}`);
  });

  it('the cohorts table lists a row per test cohort with the champion AUC and the training window', () => {
    const markup = html(<C03VariantsTable variants={[{ id: variant.variant_id, title: { en: 'FY2018-20', es: 'AF2018-20' }, v: variant }]} onPick={() => undefined} current={variant.variant_id} />);
    expect(markup).toContain(`data-variant="${variant.variant_id}"`);
    expect(markup).toContain(formatNumber(o.rung_comparison[0].auc, 'en', { digits: 3 }));
    expect(markup).toContain(`${o.training.first_fy}`);
    expect(markup).toContain(`${o.training.last_fy}`);
  });

  it('the Spanish view is written in Spanish, not the English string', () => {
    setLang('es');
    const markup = html(<CurvesView sel={sel} />);
    expect(markup).toContain('PD acumulada por cosecha');
    expect(markup).not.toContain('Cumulative PD by vintage');
    expect(html(<FiveYearView sel={sel} />)).toContain('marca de cinco años');
  });
});

// The rail: a control and a live read-out per section, the long choices as selects (ADR-0071 rule 7), no raw amount.
function RailSection({ at, base = sel }: { at: number; base?: C03Sel }) {
  const inst = useC03Instrument({ ...data, variant: base.data.variant }, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C03 rail', () => {
  afterEach(() => setLang('en'));

  it('has three sections, each with one control and one read-out', () => {
    function Sections() {
      const inst = useC03Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('vintage|horizon|model');
    for (const at of [0, 1, 2]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('the vintage, the horizon and the model are one select each, with the whole label as title', () => {
    expect(railHtml(0)).toMatch(/data-control="c03-vintage"[^>]*><label[^>]*>Vintage<\/label><select/);
    expect(railHtml(1)).toMatch(/data-control="c03-horizon"[^>]*><label[^>]*>Horizon<\/label><select/);
    expect(railHtml(2)).toMatch(/data-control="c03-model"[^>]*><label[^>]*>Model<\/label><select/);
    expect(railHtml(0).match(/<option/g)?.length).toBe(o.vintage_curves.length);
    expect(railHtml(1).match(/<option/g)?.length).toBe(o.vintage_curves[0].months.length);
    expect(railHtml(2).match(/<option/g)?.length).toBe(o.rung_comparison.length);
  });

  it('prints no raw amount in either language and no internal id as a label', () => {
    for (const at of [0, 1, 2]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
    expect(railHtml(2)).not.toContain('>P1-woe-scorecard<');
  });

  it('the vintage read-out gives the mark of the vintage chosen; an unobserved mark is not available, with its reason', () => {
    const base = defaultSel(data) as C03Sel;
    const observed = html(<VintageReadout sel={{ ...base, vintage: 2018 }} />);
    expect(observed).toContain(pct(0.092));
    const open = html(<VintageReadout sel={{ ...base, vintage: 2019 }} />);
    expect(open).toContain(NA);
    expect(open).toContain(pct(0.083));
  });

  it('the horizon read-out moves with the month, and an unobserved month is not available', () => {
    const base = defaultSel(data) as C03Sel;
    const at24 = html(<HorizonReadout sel={{ ...base, vintage: 2019, horizon: 24 }} />);
    expect(at24).toContain(pct(0.029));
    expect(at24).toContain(pct(0.026));
    const at60 = html(<HorizonReadout sel={{ ...base, vintage: 2019, horizon: 60 }} />);
    expect(at60).toContain(pct(0.083));
    expect(at60).toContain(NA);
  });

  it('the model read-out gives the rung\'s numbers; a rung not fitted is not available', () => {
    const base = defaultSel(data) as C03Sel;
    expect(html(<ModelReadout sel={{ ...base, rung: 'P4-monotone-gbm' }} />)).toContain(formatNumber(0.74, 'en', { digits: 3 }));
    expect(html(<ModelReadout sel={{ ...base, rung: 'P2-penalised-logit' }} />)).toContain(NA);
  });
});
