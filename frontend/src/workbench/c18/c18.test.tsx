// U13-W: the C18 instrument rendered on the server from the c18-outputs, c18-outputs-aggregation, c18-outputs-reverse and
// c18-models fixtures (docs/contracts/fixtures/c18). The views are built on the reviewed contracts while the engine and the
// bake are built, so every assertion reads what the fixture holds: the headline capital is the simple sum and every diversified
// or bound figure says it is information and never capital; the scenarios are US-calibrated adaptations transposed onto
// Banco Andino; the P2G proxy is a Contraste approximation; a realised charge-off rate that is negative stays negative; a test
// that did not run shows its reason; a null shows "not available" with its reason; and no number is drawn that the document
// does not contain. C19 stays planned and none of its content is on a view.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';
import { C18_FIT, C18_OUTPUTS, C18_OUTPUTS_AGGREGATION, C18_OUTPUTS_REVERSE } from './descriptor';
import { useC18Instrument } from './instrument';
import { defaultSel, fitOf, outputsOf, reverseOf, aggDocOf, aggOf, type C18Sel } from './selection';
import { C18ContextView, C18FindingsView, C18TestsView, C18VariantsTable, CapitalReadout, FactorReadout, LoanReadout, MatrixReadout, PathReadout, RiskReadout, RowReadout, StartReadout } from './C18Common';
import { Annex3View, FanView, StackView } from './CapitalViews';
import { BackcastView, LossesView, PathsView, SatellitesView, SeverityView } from './StressViews';
import { BandView, EulerView, MarginalsView, SensitivityView } from './AggregationViews';
import { ReverseSearchView, ReverseSolutionView } from './ReverseViews';

type Outputs = components['schemas']['c18Outputs'];
type Agg = components['schemas']['c18AggOutputs'];
type Reverse = components['schemas']['c18RevOutputs'];

const fixture = <T,>(name: string): T => JSON.parse(readFileSync(new URL(`../../../../docs/contracts/fixtures/c18/${name}-fixture.json`, import.meta.url), 'utf8')) as T;
const baselineV = fixture<VariantArtifact<Outputs>>('variant-scenario-baseline');
const ebaV = fixture<VariantArtifact<Outputs>>('variant-scenario-eba-2025-adverse');
const fedV = fixture<VariantArtifact<Outputs>>('variant-scenario-fed-2026-severely-adverse');
const ngfsV = fixture<VariantArtifact<Outputs>>('variant-scenario-ngfs-delayed-transition');
const aggV = fixture<VariantArtifact<Agg>>('variant-aggregation');
const reverseV = fixture<VariantArtifact<Reverse>>('variant-reverse');
const models = fixture<ModelsArtifact>('models');
const title = { en: 'ICAAP and IAPE capital aggregation under macro scenarios', es: 'Agregación de capital ICAAP e IAPE bajo escenarios macro' };
type AnyV = VariantArtifact<Outputs> | VariantArtifact<Agg> | VariantArtifact<Reverse>;
const dataOf = (v: AnyV, m: ModelsArtifact = models): CaseData => fixtureData('C18', v as unknown as VariantArtifact, m, title);
const selOf = (v: AnyV, patch: Partial<C18Sel> = {}): C18Sel => ({ ...(defaultSel(dataOf(v)) as C18Sel), ...patch });
const clone = <T,>(v: T): T => structuredClone(v);

afterEach(() => setLang('en'));

type Lang = 'en' | 'es';
const pct = (v: number, lang: Lang = 'en', decimals = 2) => formatNumber(v, lang, { percent: true, decimals });
const cell = (v: number | null, lang: Lang = 'en') => formatNumber(v, lang, { decimals: 0 });
const NA = formatNumber(null, 'en');
const text = (t: { en: string; es: string }, lang: Lang = 'en') => escapeHtml(t[lang]);

type View = (p: { sel: C18Sel | null }) => ReactElement;
const SCENARIO_VIEWS: Array<[string, View]> = [
  ['Fan', FanView], ['Stack', StackView], ['Annex 3', Annex3View], ['Paths', PathsView], ['Satellites', SatellitesView], ['Back-cast', BackcastView],
  ['Severity', SeverityView], ['Losses', LossesView], ['Band', BandView], ['Euler', EulerView], ['Marginals', MarginalsView], ['Tests', C18TestsView], ['Findings', C18FindingsView], ['Context', C18ContextView],
];
const AGG_VIEWS: Array<[string, View]> = [['Band', BandView], ['Euler', EulerView], ['Marginals', MarginalsView], ['Sensitivity', SensitivityView], ['Tests', C18TestsView], ['Findings', C18FindingsView], ['Context', C18ContextView]];
const REVERSE_VIEWS: Array<[string, View]> = [['Solution', ReverseSolutionView], ['Search', ReverseSearchView], ['Tests', C18TestsView], ['Findings', C18FindingsView], ['Context', C18ContextView]];

function Names({ v }: { v: AnyV }) {
  const inst = useC18Instrument(dataOf(v), () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Rail({ v }: { v: AnyV }) {
  const inst = useC18Instrument(dataOf(v), () => undefined);
  return <div>{inst ? inst.rail.map((s) => (typeof s.label === 'string' ? s.label : s.label.en)).join('|') : 'none'}</div>;
}
function Other() {
  const inst = useC18Instrument({ ...dataOf(fedV), manifest: { ...dataOf(fedV).manifest, case_id: 'C16' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C18 contract descriptors', () => {
  it('describe the four scenario fixtures, the aggregation fixture, the reverse fixture and the models fit key by key, in both directions', () => {
    for (const v of [baselineV, ebaV, fedV, ngfsV]) expect(conform(v.outputs, C18_OUTPUTS), v.variant_id).toEqual([]);
    expect(conform(aggV.outputs, C18_OUTPUTS_AGGREGATION)).toEqual([]);
    expect(conform(reverseV.outputs, C18_OUTPUTS_REVERSE)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C18_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone(fedV);
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).backcast;
    const found = conform(odd.outputs, C18_OUTPUTS).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/backcast: declared by the web, not written by the pipeline/);
  });
});

describe('the C18 instrument', () => {
  it('answers for C18 only, with the groups in the validator order, then Variants', () => {
    expect(html(<Names v={fedV} />)).toContain('Capital|Stress|Aggregation|Tests and findings|Variants');
    expect(html(<Names v={aggV} />)).toContain('Aggregation|Tests and findings|Variants');
    expect(html(<Names v={reverseV} />)).toContain('Reverse stress|Tests and findings|Variants');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(selOf(fedV))?.kind).toBe('scenario');
    expect(aggDocOf(selOf(aggV))?.kind).toBe('aggregation');
    expect(reverseOf(selOf(reverseV))?.kind).toBe('reverse');
    expect(outputsOf(selOf(reverseV))).toBeNull();
    expect(fitOf(selOf(fedV))?.currency).toBe('CLP');
  });

  it('the rail of each document holds its controls and a read-out with no raw amount', () => {
    expect(html(<Rail v={fedV} />)).toContain('Year|Path|Loan|Risk');
    expect(html(<Rail v={aggV} />)).toContain('Matrix|Row|Risk');
    expect(html(<Rail v={reverseV} />)).toContain('Factor|Start');
    function Controls() {
      const inst = useC18Instrument(dataOf(fedV), () => undefined);
      return <pre>{JSON.stringify(inst?.controls)}</pre>;
    }
    expect(html(<Controls />)).toContain('&quot;year&quot;');
    for (const [name, el] of [
      ['capital', <CapitalReadout sel={selOf(fedV, { year: 3 })} />], ['path', <PathReadout sel={selOf(fedV)} />], ['loan', <LoanReadout sel={selOf(fedV, { loan: 'residential' })} />],
      ['risk', <RiskReadout sel={selOf(fedV)} />], ['risk agg', <RiskReadout sel={selOf(aggV)} />], ['matrix', <MatrixReadout sel={selOf(aggV)} />], ['row', <RowReadout sel={selOf(aggV)} />],
      ['factor', <FactorReadout sel={selOf(reverseV)} />], ['start', <StartReadout sel={selOf(reverseV)} />],
    ] as Array<[string, ReactElement]>) {
      const markup = html(el);
      expect(markup, name).toContain('caos-readout');
      expect(RAW_AMOUNT.test(markup), `${name}: a raw amount in a rail read-out`).toBe(false);
    }
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    const groups: Array<[AnyV, Array<[string, View]>]> = [[fedV, SCENARIO_VIEWS], [aggV, AGG_VIEWS], [reverseV, REVERSE_VIEWS]];
    for (const [v, views] of groups) {
      for (const [name, View] of views) {
        const found = cards(html(<View sel={selOf(v)} />));
        expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
        for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
        expect(html(<View sel={null} />), name).toContain('data-state="loading"');
      }
    }
  });

  it('a view given a document of another kind says not available and draws nothing', () => {
    expect(html(<FanView sel={selOf(reverseV)} />)).toContain('data-state="unavailable"');
    expect(html(<BackcastView sel={selOf(aggV)} />)).toContain('data-state="unavailable"');
    expect(html(<ReverseSolutionView sel={selOf(fedV)} />)).toContain('data-state="unavailable"');
    expect(html(<SensitivityView sel={selOf(fedV)} />)).toContain('data-state="unavailable"');
    expect(html(<BandView sel={selOf(reverseV)} />)).toContain('data-state="unavailable"');
  });
});

describe('the capital group', () => {
  const o = fedV.outputs;
  it('the fan draws the CET1 over RWA of the base, the stress without mitigation and the stress with mitigation, against the layers of the OI', () => {
    const markup = html(<FanView sel={selOf(fedV)} />);
    for (const c of o.capital_plan.cases) {
      expect(markup, c.case).toContain(`data-plan="${c.case}"`);
      for (const y of c.years) expect(markup).toContain(pct(y.cet1.pct_of_rwa));
    }
    expect(markup).toContain(pct(o.capital_start.cet1_ratio));
    expect(markup).toContain(pct(o.internal_capital_target.oi));
    expect(markup).toContain('data-layers="oi"');
    // the PPNR path is a labelled row apart from the headline
    expect(markup).toContain('data-ppnr="labelled-row"');
    expect(markup).toContain(text({ en: 'labelled row', es: 'fila rotulada' }));
    // the headline is the loss-only depletion
    expect(markup).toContain('data-headline="loss-only-depletion"');
    expect(markup).toContain(pct(o.headline_cet1.rows[2].cet1_ratio));
  });

  it('the stack builds the OI from its layers, labels c_P2 and c_d as case assumptions and the P2G proxy as a Contraste approximation', () => {
    const markup = html(<StackView sel={selOf(fedV)} />);
    const t = o.internal_capital_target;
    for (const v of [t.min_pe, t.c_dsib, t.c_p2.value, t.c_ccob, t.c_ccyb, t.c_d.value, t.oi]) expect(markup).toContain(pct(v, 'en', 3));
    expect(markup).toContain('data-layer="c_p2"');
    expect(markup).toMatch(/data-layer="c_p2"[^>]*data-label="case assumption"/);
    expect(markup).toMatch(/data-layer="c_d"[^>]*data-label="case assumption"/);
    expect(markup).toContain('data-p2g="contraste-approximation"');
    expect(markup).toContain(pct(o.p2g_proxy.value, 'en', 3));
    expect(markup).toContain(text({ en: 'A Contraste approximation: the CMF calibration of the P2G is not public.', es: 'Una aproximación de Contraste: la calibración de la P2G de la CMF no es pública.' }));
    // the legal minimum stack comes from the models artifact
    expect(markup).toContain(pct(fitOf(selOf(fedV))?.bank_anchors.chilean_stack.cet1_min ?? 0));
    // only the Chilean stack is drawn: the documents hold no EU or SSM figure, and the view says no comparison is made
    expect(markup).toContain('no comparison with them is made');
  });

  it('the Annex 3 summary shows the 34 rows with RI, not to be filled and not applicable in words', () => {
    const markup = html(<Annex3View sel={selOf(fedV)} />);
    expect(o.annex3.rows).toHaveLength(34);
    expect((markup.match(/data-annex-row="/g) ?? []).length).toBe(34);
    expect(markup).toContain('RI (immaterial risk)');
    expect(markup).toContain('not to be filled');
    expect(markup).toContain('not applicable');
    expect(markup).toContain(pct(o.annex3.rows.find((r) => r.row_id === '12')?.a.value ?? 0, 'en', 3));
    expect(markup).toContain(cell(1133452.8));
    setLang('es');
    const es = html(<Annex3View sel={selOf(fedV)} />);
    expect(es).toContain('RI (riesgo inmaterial)');
    expect(es).toContain('Ratios de capital');
  });
});

describe('the stress group', () => {
  const o = fedV.outputs;
  it('the paths say they are a US-calibrated adaptation transposed onto the jump-off of Banco Andino', () => {
    const markup = html(<PathsView sel={selOf(fedV)} />);
    expect(markup).toContain(text(o.scenario.adaptation_statement));
    expect(markup).toContain('data-transposition="transposed-onto-banco-andino-jump-off"');
    expect(markup).toContain(o.scenario.vintage_date);
    // a path is named by the regressor it feeds, not by its raw id
    expect(markup).toContain('Unemployment rate');
    expect(markup).not.toMatch(/maps_to_regressor/);
  });

  it('an NGFS path shows the rule that builds its levels and the three-year window in which the policy shock acts', () => {
    const markup = html(<PathsView sel={selOf(ngfsV, { path: 3 })} />);
    expect(markup).toContain('baseline times the published percent deviation');
    expect(markup).toContain('2031');
    expect(markup).toContain('2033');
    expect(markup).toContain('data-window="2031-2033"');
  });

  it('the satellites list the five Fed loan types with their link and the Banco Andino classes as an adaptation', () => {
    const markup = html(<SatellitesView sel={selOf(fedV)} />);
    for (const f of o.satellites.fed_loan_types) expect(markup).toContain(`data-loan="${f.fed_loan_type}"`);
    for (const c of o.satellites.banco_andino_classes) {
      expect(markup).toContain(`data-class="${c.banco_andino_class}"`);
      expect(markup).toContain(pct(c.weights[0], 'en', 0));
    }
    expect(markup).toContain('US-calibrated adaptation');
    expect(markup).toContain('identity (a signed rate)');
  });

  it('the back-cast keeps a negative realised rate negative, shows the zero, and starts the real estate windows in 1991', () => {
    const resid = o.backcast.per_loan_type.find((b) => b.fed_loan_type === 'residential');
    expect(resid?.quarters.some((q) => q.realised < 0)).toBe(true);
    const markup = html(<BackcastView sel={selOf(fedV, { loan: 'residential' })} />);
    const neg = resid?.quarters.find((q) => q.realised < 0)?.realised ?? 0;
    expect(markup).toContain(formatNumber(neg, 'en', { percent: true, decimals: 3 }));
    expect(markup).toMatch(/data-realised="-/);
    expect(markup).toContain('data-fit-start="1991-03-31"');
    expect(markup).toContain('data-signed-rate="true"');
    // the 2026 rows are descriptive and make no forecast claim; the true zero of 2026 stays a zero
    expect(markup).toContain('data-forecast-claim="false"');
    expect(markup).toContain(formatNumber(0, 'en', { percent: true, decimals: 3 }));
    // the commercial and industrial window starts in 1985 and records no non-positive quarter
    expect(html(<BackcastView sel={selOf(fedV, { loan: 'commercial-industrial' })} />)).toContain('data-fit-start="1985-03-31"');
  });

  it('the back-cast of a rate the bake wrote as negative is never floored: a changed fixture value changes the markup', () => {
    const planted = clone(fedV);
    const q = planted.outputs.backcast.per_loan_type.find((b) => b.fed_loan_type === 'residential')?.quarters[0];
    if (q) q.realised = -0.0421;
    const markup = html(<BackcastView sel={selOf(planted, { loan: 'residential' })} />);
    expect(markup).toContain(formatNumber(-0.0421, 'en', { percent: true, decimals: 3 }));
  });

  it('the severity compares each path with the global financial crisis and flags one below the minimum ratio', () => {
    const markup = html(<SeverityView sel={selOf(fedV)} />);
    for (const r of o.severity.rows) expect(markup).toContain(`data-severity="${r.maps_to_regressor}"`);
    expect(markup).toContain(formatNumber(o.severity.minimum_ratio, 'en', { digits: 4 }));
    expect(markup).toContain('convention');
    // PR-C18-2: the column judges the ratio against the minimum; is_stress is the scenario's kind, never the verdict
    const weak = clone(fedV);
    weak.outputs.severity.rows[0].ratio = 0.5;
    weak.outputs.severity.rows[0].is_stress = true;
    const weakMarkup = html(<SeverityView sel={selOf(weak)} />);
    expect(weakMarkup).toMatch(/data-severity="unemployment_rate"[^>]*data-severe="false"/);
    expect(weakMarkup).toContain('no, below the minimum');
    const strong = clone(fedV);
    strong.outputs.severity.rows[0].ratio = 1.2;
    strong.outputs.severity.rows[0].is_stress = true;
    expect(html(<SeverityView sel={selOf(strong)} />)).toMatch(/data-severity="unemployment_rate"[^>]*data-severe="true"/);
    const base = clone(fedV);
    base.outputs.severity.rows[0].is_stress = false;
    const baseMarkup = html(<SeverityView sel={selOf(base)} />);
    expect(baseMarkup).toMatch(/data-severity="unemployment_rate"[^>]*data-severe="not-judged"/);
    expect(baseMarkup).toContain('not judged (baseline)');
  });

  it('the losses are listed by risk and year, with the total', () => {
    const markup = html(<LossesView sel={selOf(fedV)} />);
    for (const y of o.losses.scenario_losses) {
      expect(markup).toContain(`data-year="${y.year}"`);
      expect(markup).toContain(cell(y.total));
    }
  });
});

describe('the aggregation group', () => {
  const a = fedV.outputs.aggregation;
  it('the band shows the simple sum as the headline capital and every other figure as information, never capital', () => {
    const markup = html(<BandView sel={selOf(fedV)} />);
    expect(markup).toContain('data-headline="simple-sum"');
    expect(markup).toContain(cell(a.headline.capital_clp_m));
    expect((markup.match(/data-status="information-not-capital"/g) ?? []).length).toBeGreaterThanOrEqual(a.band.filter((b) => b.status === 'information-not-capital').length);
    expect(markup).toContain(text({ en: 'Information, not capital: only the simple sum is the capital of this case.', es: 'Información, no capital: solo la suma simple es el capital de este caso.' }));
    for (const b of a.band) expect(markup).toContain(cell(b.capital_clp_m));
    // the model risk measures sit beside the band as sensitivity information
    expect(markup).toContain(formatNumber(a.model_risk.barrieu_scandolo.am, 'en', { digits: 4 }));
    expect(markup).toContain(formatNumber(a.model_risk.barrieu_scandolo.rm, 'en', { digits: 4 }));
    // no row of the band is drawn as the headline but the simple sum
    expect((markup.match(/data-band-status="headline-capital"/g) ?? []).length).toBe(1);
  });

  it('a diversified row above the simple sum is shown as it is, never repaired', () => {
    const planted = clone(fedV);
    const row = planted.outputs.aggregation.band.find((b) => b.method === 'gaussian-copula');
    if (row) row.capital_clp_m = planted.outputs.aggregation.headline.capital_clp_m * 1.1;
    expect(html(<BandView sel={selOf(planted)} />)).toContain(cell(planted.outputs.aggregation.headline.capital_clp_m * 1.1));
  });

  it('the Euler allocation is a waterfall of the expected shortfall, labelled information, with its additivity', () => {
    const markup = html(<EulerView sel={selOf(fedV)} />);
    for (const r of a.euler.allocation) {
      expect(markup).toContain(`data-bar="${r.risk}"`);
      expect(markup).toContain(cell(r.contribution_clp_m));
    }
    expect(markup).toContain(cell(a.euler.es_total_clp_m));
    expect(markup).toContain('data-status="information-not-capital"');
    expect(markup).toContain('data-additivity="true"');
  });

  it('a marginal whose mean is infinite shows the expected loss as not available with its reason, and its capital as the VaR alone', () => {
    const planted = clone(fedV);
    const m = planted.outputs.aggregation.marginals.find((x) => x.risk === 'operational');
    if (m) {
      m.el_clp_m = null;
      m.el_status = 'undefined (infinite mean)';
      m.ec_basis = 'var-alone-infinite-mean';
      m.ec_label = { en: 'The mean is infinite, so the capital is the VaR alone', es: 'La media es infinita, así que el capital es el VaR solo' };
    }
    const markup = html(<MarginalsView sel={selOf(planted)} />);
    expect(markup).toContain(NA);
    expect(markup).toContain('data-el-status="undefined (infinite mean)"');
    expect(markup).toContain('The mean is infinite, so the capital is the VaR alone');
    // the finite marginals show their expected loss
    expect(html(<MarginalsView sel={selOf(fedV)} />)).toContain(cell(a.marginals[0].el_clp_m));
  });

  it('the aggregation variant adds the stressed matrix, the copula sensitivity and the Rosenberg and Schuermann reference that is not a gate', () => {
    const base = html(<BandView sel={selOf(aggV)} />);
    const stress = html(<BandView sel={selOf(aggV, { matrix: 'stress' })} />);
    expect(base).toContain('data-matrix="correlation_matrix_base"');
    expect(stress).toContain('data-matrix="correlation_matrix_stress"');
    expect(aggOf(selOf(aggV, { matrix: 'stress' }))?.correlation.name).toBe('correlation_matrix_stress');
    const sens = html(<SensitivityView sel={selOf(aggV)} />);
    for (const r of aggV.outputs.copula_sensitivity) expect(sens).toContain(`data-nu="${r.nu}"`);
    expect(sens).toContain('data-role="reference-not-a-gate"');
    expect(sens).toContain(pct(aggV.outputs.rosenberg_schuermann.case_additive_overestimate, 'en', 1));
    expect(sens).toContain('data-within-published-range="false"');
  });
});

describe('the reverse stress', () => {
  const r = reverseV.outputs;
  it('shows the minimum Mahalanobis distance scenario, its plausibility and the failure point as Contraste\'s own formulation', () => {
    const markup = html(<ReverseSolutionView sel={selOf(reverseV)} />);
    expect(markup).toContain('data-failure-point="contraste-formulation-not-regulatory"');
    expect(markup).toContain(formatNumber(r.solution.mahalanobis_distance, 'en', { digits: 4 }));
    expect(markup).toContain(pct(r.solution.plausibility.tail_probability));
    for (const f of r.factor_space.factors) expect(markup).toContain(`data-factor="${f.id}"`);
    expect(markup).toContain(pct(r.failure_point.stack.total, 'en', 3));
    expect(markup).toContain('closed form, linear loss');
  });
  it('a nonlinear loss model has no gradient and says so; the starts are listed with their convergence', () => {
    const planted = clone(reverseV);
    planted.outputs.loss_model.kind = 'nonlinear';
    planted.outputs.loss_model.gradient_clp_m_per_unit = null;
    planted.outputs.solution.method = 'scipy-optimize';
    const markup = html(<ReverseSolutionView sel={selOf(planted)} />);
    expect(markup).toContain(NA);
    expect(markup).toContain('numerical optimisation');
    const search = html(<ReverseSearchView sel={selOf(reverseV)} />);
    for (const s of r.starts) expect(search).toContain(`data-start="${s.start_id}"`);
    expect(search).toContain(cell(r.solution.loss_threshold_clp_m));
  });
});

describe('tests, findings, variants and context', () => {
  it('a test that did not run shows its reason and no number', () => {
    const markup = html(<C18TestsView sel={selOf(fedV)} />);
    expect((markup.match(/data-light="not_evaluated"/g) ?? []).length).toBe(fedV.tests.length);
    expect(markup).toContain('fixture: the test did not run, no number stands in for it');
    expect(markup).toContain('The Euler contributions add up to the total');
    expect(markup).not.toMatch(/data-test="[^"]*"[^>]*><td[^>]*>[^<]*<\/td><td[^>]*>[0-9]/);
  });

  it('the variants table lists the loaded variants with the headline capital, the end CET1 ratio and the headroom', () => {
    const entries = [fedV, baselineV].map((v) => ({ id: v.variant_id, title: { en: v.variant_id, es: v.variant_id }, v: v as VariantArtifact<Outputs> }));
    const markup = html(<C18VariantsTable variants={entries} aggregation={aggV} reverse={reverseV} onPick={() => undefined} current={fedV.variant_id} />);
    for (const e of entries) expect(markup).toContain(`data-variant="${e.id}"`);
    expect(markup).toContain(cell(fedV.outputs.aggregation.headline.capital_clp_m));
    expect(markup).toContain(pct(fedV.impact.cet1_ratio_end_stress.value ?? 0));
    expect(markup).toContain('data-variant="fixture-reverse-stress"');
    expect(markup).toContain('data-variant="fixture-t-copula-aggregation"');
  });

  it('the context names the synthetic bank, the adaptation, the capital basis and every convention and case assumption as such, and shows no C19 content', () => {
    const markup = html(<C18ContextView sel={selOf(fedV)} />);
    expect(markup).toContain('Banco Andino');
    expect(markup).toContain(text(fedV.outputs.bank.notice));
    expect(markup).toContain('US-calibrated adaptation');
    expect(markup).toContain('economic capital, VaR less expected loss');
    expect((markup.match(/data-status="(convention|case assumption)"/g) ?? []).length).toBeGreaterThanOrEqual(12);
    expect(markup).not.toMatch(/C19|supervisory stress model replication|hypothetical portfolio/i);
    expect(markup).toContain(escapeHtml('The market share of the 20-F RWA mix'.slice(0, 20)));
  });

  it('the Spanish views are Spanish', () => {
    setLang('es');
    const band = html(<BandView sel={selOf(fedV)} />);
    expect(band).toContain('Suma simple');
    expect(band).toContain('Información, no capital');
    const fan = html(<FanView sel={selOf(fedV)} />);
    expect(fan).toContain(pct(fedV.outputs.capital_plan.cases[1].years[2].cet1.pct_of_rwa, 'es'));
    expect(html(<PathsView sel={selOf(fedV)} />)).toContain('adaptación calibrada en EE. UU.'.slice(0, 20));
  });
});
