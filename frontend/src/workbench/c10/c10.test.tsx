// U7-W: the C10 instrument rendered on the server from the c10-outputs, c10-outputs-grid and c10-models fixtures
// (docs/contracts/fixtures/c10). Every loss distribution shows EL, VaR and ES with their Monte Carlo error and the LHP
// overlay is labelled as the infinitely granular approximation; the simulator's known correlation is always read beside
// its estimates; the portfolio is labelled illustrative on every view that uses it; a rung or a test that did not run
// shows its reason and no number; no view draws a number the fixture does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';
import { useInstrument } from './instrument';
import { defaultSel, eulerOf, gridOf, outputsOf, rungOf, type C10Sel } from './selection';
import { barMin } from './format';
import { C10ContextView, C10FindingsView, C10VariantsTable, EstimatorReadout, GroupReadout, LevelReadout, RungReadout, CellReadout } from './C10Common';
import { BacktestView, CorrelationView, FittedView, IrbView } from './FitViews';
import { ContributionsView, GranularityView, LossView, RungsView, lossMarks } from './CapitalViews';
import { EstimatesView, SizePowerView } from './SimulatorViews';
import { EstimatorsView, LadderView, PortfolioView } from './ModelViews';

type LoanOutputs = components['schemas']['c10LoanTypeOutputs'];
type GridOutputs = components['schemas']['c10GridOutputs'];

const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, new URL('../../../../docs/contracts/fixtures/c10/', import.meta.url)), 'utf8')) as T;
const loan = read<VariantArtifact<LoanOutputs>>('variant-loan-type-fixture.json');
const grid = read<VariantArtifact<GridOutputs>>('variant-correlation-grid-fixture.json');
const models = read<ModelsArtifact>('models-fixture.json');
const title = { en: 'Portfolio credit capital', es: 'Capital de crédito de cartera' };
const data = fixtureData('C10', loan as unknown as VariantArtifact, models, title);
const gridData = fixtureData('C10', grid as unknown as VariantArtifact, models, title);
const o = loan.outputs;
const g = grid.outputs;
const sel = defaultSel(data) as C10Sel;
const gsel = defaultSel(gridData) as C10Sel;
const pct = (v: number, d = 2, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: d });
const NA = formatNumber(null, 'en');

const LOAN_VIEWS: Array<[string, (p: { sel: C10Sel | null }) => ReactElement]> = [
  ['Fitted', FittedView], ['Correlation', CorrelationView], ['Back-test', BacktestView], ['IRB', IrbView],
  ['Loss', LossView], ['Rungs', RungsView], ['Contributions', ContributionsView], ['Granularity', GranularityView],
  ['Ladder', LadderView], ['Portfolio', PortfolioView], ['Estimators', EstimatorsView],
  ['Findings', C10FindingsView], ['Context', C10ContextView],
];
const GRID_VIEWS: Array<[string, (p: { sel: C10Sel | null }) => ReactElement]> = [
  ['Size and power', SizePowerView], ['Estimates', EstimatesView], ['Ladder', LadderView], ['Estimators', EstimatorsView], ['Findings', C10FindingsView], ['Context', C10ContextView],
];

function Names({ d }: { d: typeof data }) {
  const inst = useInstrument(d, () => undefined);
  return <p>{inst ? [...inst.groups.map((x) => x.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useInstrument({ ...data, manifest: { ...data.manifest, case_id: 'C09' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C10 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C10 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names d={data} />)).toContain('Fit|Capital|Model|Findings|Variants');
    expect(html(<Names d={gridData} />)).toContain('Size and power|Model|Findings|Variants');
    function Count() {
      const inst = useInstrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>6</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('loan-type');
    expect(gridOf(gsel)?.kind).toBe('correlation-grid');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of LOAN_VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
    for (const [name, View] of GRID_VIEWS) {
      const found = cards(html(<View sel={gsel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
    }
  });

  it('a loan-type view on a grid document, and a grid view on a loan-type one, says loading and draws nothing', () => {
    expect(html(<LossView sel={gsel} />)).toContain('data-state="loading"');
    expect(html(<SizePowerView sel={sel} />)).toContain('data-state="loading"');
  });

  it('the portfolio is labelled illustrative, with its notice, on every view that uses it', () => {
    for (const [name, View] of [['Loss', LossView], ['Rungs', RungsView], ['Contributions', ContributionsView], ['Granularity', GranularityView], ['Portfolio', PortfolioView]] as const) {
      const markup = html(<View sel={sel} />);
      expect(markup, name).toContain('data-portfolio="illustrative"');
      expect(markup, name).toContain(escapeHtml(o.portfolio.notice.en));
    }
    expect(html(<PortfolioView sel={gsel} />)).toContain('data-portfolio="illustrative"');
  });

  it('the loss distribution has the EL, VaR and ES markers of the rung at the level, each with its Monte Carlo error', () => {
    const rung = rungOf(o, 'c2-gaussian-1f')!;
    const marks = lossMarks(rung, 0.999, o.currency);
    expect(marks.map((m) => m.kind)).toEqual(['el', 'var', 'es']);
    const m = rung.measures!.find((x) => x.level === 0.999)!;
    expect(marks.map((x) => x.x)).toEqual([m.el, m.var, m.es]);
    expect(marks[1].label.en).toContain('±');
    expect(marks[2].label.en).toContain('±');
    expect(marks[0].label.en).not.toContain('±');
    // an analytic rung has no sampling error and says so
    const analytic = lossMarks(rungOf(o, 'c1-lhp')!, 0.99, o.currency);
    expect(analytic[1].label.en).not.toContain('±');
    // a rung that did not run has no marker
    expect(lossMarks(rungOf(o, 'c6-is-student-t')!, 0.99, o.currency)).toEqual([]);
  });

  it('the loss view gives EL, VaR, ES, EC and the standard errors of the rung and labels the LHP overlay as the infinitely granular approximation', () => {
    const markup = html(<LossView sel={sel} />);
    const rung = rungOf(o, sel.rung)!;
    const m = rung.measures!.find((x) => x.level === 0.999)!;
    for (const v of [m.el, m.var, m.es as number, m.ec, m.var_se as number, m.es_se as number]) expect(markup).toContain(formatNumber(v, 'en', { decimals: 0 }));
    expect(markup).toContain('data-marker="el"');
    expect(markup).toContain('data-marker="var"');
    expect(markup).toContain('data-marker="es"');
    expect(markup).toMatch(/infinitely granular/);
    expect(markup).toContain(`data-rung="${rung.id}"`);
    expect(markup).toContain(o.currency);
    // the LHP rung itself carries no overlay and no sampling error
    const lhp = html(<LossView sel={{ ...sel, rung: 'c1-lhp' }} />);
    expect(lhp).toContain('data-overlay="none"');
    expect(markup).toContain('data-overlay="lhp"');
  });

  it('a rung that did not run says why in the loss view and draws no number', () => {
    const markup = html(<LossView sel={{ ...sel, rung: 'c6-is-student-t' }} />);
    const r = rungOf(o, 'c6-is-student-t')!;
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).toContain(escapeHtml(r.reason as string));
    expect(markup).not.toMatch(/data-marker=/);
  });

  it('a rung that defines no expected shortfall (the granularity adjustment) shows its reason, in the loss view and the rungs view, and draws no ES marker', () => {
    const rung = rungOf(o, 'c5-granularity')!;
    const reason = rung.measures!.find((m) => m.level === 0.999)!.es_reason as string;
    expect(lossMarks(rung, 0.999, o.currency).map((m) => m.kind)).toEqual(['el', 'var']);
    const loss = html(<LossView sel={{ ...sel, rung: 'c5-granularity' }} />);
    expect(loss).toContain(escapeHtml(reason));
    expect(loss).toMatch(/data-marker="es" data-na="true"/);
    const rungs = html(<RungsView sel={sel} />);
    expect(rungs).toContain(`data-es-reason="c5-granularity"`);
    expect(rungs).toContain(escapeHtml(reason));
  });

  it('the rungs view lists every rung with its measures and errors; the one that did not run shows its reason and no number', () => {
    const markup = html(<RungsView sel={sel} />);
    for (const r of o.rungs) {
      expect(markup).toContain(`data-rung="${r.id}"`);
      if (!r.evaluated) {
        expect(markup).toContain(escapeHtml(r.reason as string));
        continue;
      }
      const m = r.measures!.find((x) => x.level === 0.999)!;
      expect(markup).toContain(formatNumber(m.var, 'en', { decimals: 0 }));
    }
    const mc = rungOf(o, 'c2-gaussian-1f')!.measures!.find((x) => x.level === 0.999)!;
    expect(markup).toContain(formatNumber(mc.var_se as number, 'en', { decimals: 0 }));
    expect(markup).not.toMatch(/NaN|undefined/);
  });

  it('every horizontal bar chart is given the height its rows need, so none scrolls inside its drawing (2.2 rem a row and 3 rem, for a label that wraps on a phone)', () => {
    expect(barMin(8)).toBe('20.6rem');
    expect(html(<RungsView sel={sel} />)).toContain('min-height:20.6rem');
    expect(html(<BacktestView sel={sel} />)).toContain(`min-height:${barMin(6)}`);
    expect(html(<LadderView sel={sel} />)).toContain('min-height:20.6rem');
    expect(html(<ContributionsView sel={{ ...sel, rung: 'c2-gaussian-1f' }} />)).toContain(`min-height:${barMin(6)}`);
    expect(html(<PortfolioView sel={sel} />)).toContain(`min-height:${barMin(3)}`);
  });

  it('the tests of the engine sit under the view they belong to; one that did not run shows its reason and no number', () => {
    const rungs = html(<RungsView sel={sel} />);
    const contributions = html(<ContributionsView sel={sel} />);
    const back = html(<BacktestView sel={sel} />);
    const host: Record<string, string> = {
      'portfolio.mc_convergence': rungs,
      'portfolio.crp_recursion_vs_mc': rungs,
      'portfolio.euler_additivity': contributions,
      'portfolio.tail_backtest': back,
    };
    for (const t of loan.tests) {
      expect(host[t.test_id], t.test_id).toContain(`data-test="${t.test_id}"`);
      expect(host[t.test_id], t.test_id).toContain(escapeHtml(t.notes as string));
      expect(host[t.test_id], t.test_id).not.toContain(`>${t.test_id}<`);
    }
    expect(rungs).toMatch(/data-test="portfolio.mc_convergence" data-light="not_evaluated"/);
    expect(rungs + contributions + back).not.toMatch(/NaN|undefined/);
  });

  it('the fitted distribution places every year of the series in it with the fit and evaluation windows marked', () => {
    const markup = html(<FittedView sel={sel} />);
    for (const a of o.annual_rates) {
      expect(markup).toContain(`data-year="${a.year}"`);
      expect(markup).toContain(`data-window="${a.window}"`);
      if (a.loss_rate !== null) expect(markup).toContain(pct(a.loss_rate));
    }
    const hot = o.annual_rates.find((a) => a.exceeds_999)!;
    expect(markup).toMatch(new RegExp(`data-year="${hot.year}"[^>]*data-exceeds-999="true"`));
    expect(markup).toContain(pct(o.fitted_distribution.rho, 1));
    expect(markup).toContain(pct(o.fitted_distribution.pd, 2));
  });

  it('a year without a rate shows not available with the reason, never a zero', () => {
    const odd = structuredClone(loan) as VariantArtifact<LoanOutputs>;
    const i = odd.outputs.annual_rates.findIndex((a) => a.year === 1990);
    odd.outputs.annual_rates[i] = { year: 1990, window: 'fit', n_quarters: 3, loss_rate: null, reason: 'the table lacks 1990Q3', fitted_cdf: null, implied_factor: null, exceeds_99: null, exceeds_999: null };
    const markup = html(<FittedView sel={defaultSel({ ...data, variant: odd as unknown as VariantArtifact }) as C10Sel} />);
    expect(markup).toMatch(/data-year="1990"/);
    expect(markup).toContain('the table lacks 1990Q3');
    expect(markup).toContain(NA);
  });

  it('the correlation view gives both estimators with their intervals and methods, and the profile likelihood cutoff', () => {
    const markup = html(<CorrelationView sel={sel} />);
    const ml = o.fit.maximum_likelihood;
    const mo = o.fit.moments;
    for (const v of [ml.rho.estimate, ml.rho.ci_low, ml.rho.ci_high, mo.rho.estimate, mo.rho.ci_low, mo.rho.ci_high]) expect(markup).toContain(pct(v, 1));
    for (const v of [ml.pd.estimate, ml.pd.ci_low, ml.pd.ci_high, mo.pd.estimate]) expect(markup).toContain(pct(v, 2));
    expect(markup).toContain('data-estimator="maximum-likelihood"');
    expect(markup).toContain('data-estimator="moments"');
    expect(markup).toContain('profile likelihood');
    expect(markup).toContain('parametric bootstrap');
    expect(markup).toContain(formatNumber(o.profile_likelihood.cutoff, 'en', { digits: 4 }));
    expect(markup).toContain(formatNumber(mo.n_bootstrap, 'en', { decimals: 0 }));
  });

  it('the back-test gives each level with the fitted quantile, expected and observed years, the p-value, the light and the years', () => {
    const markup = html(<BacktestView sel={sel} />);
    for (const r of o.backtest.rows) {
      expect(markup).toContain(`data-level="${r.level}"`);
      expect(markup).toContain(pct(r.fitted_quantile));
      expect(markup).toContain(formatNumber(r.observed_exceedances, 'en', { decimals: 0 }));
      expect(markup).toContain(`data-light="${r.light}"`);
      for (const y of r.years_exceeding) expect(markup).toContain(String(y));
    }
    expect(markup).toContain(formatNumber(o.backtest.n_years_evaluated, 'en', { decimals: 0 }));
  });

  it('the IRB view compares the fitted correlation and capital with the IRB ones, in words, with the class and the regime', () => {
    const markup = html(<IrbView sel={sel} />);
    const x = o.irb_reference;
    expect(markup).toContain(pct(x.irb_correlation, 1));
    expect(markup).toContain(pct(x.fitted_correlation, 1));
    expect(markup).toContain(pct(x.k_irb));
    expect(markup).toContain(pct(x.ec_lhp_fitted));
    expect(markup).toContain(formatNumber(x.ratio_fitted_to_irb, 'en', { digits: 3 }));
    expect(markup).toContain('Residential mortgage');
    expect(markup).toContain('Basel III');
    expect(markup).toContain(x.reference);
    // a retail class has no maturity: the view says so, it does not print a zero
    expect(markup).toMatch(/data-maturity="none"/);
    const corp = structuredClone(loan) as VariantArtifact<LoanOutputs>;
    corp.outputs.irb_reference = { ...corp.outputs.irb_reference, asset_class: 'corporate', maturity: 2.5, maturity_adjustment: 1.1 } as LoanOutputs['irb_reference'];
    const m = html(<IrbView sel={defaultSel({ ...data, variant: corp as unknown as VariantArtifact }) as C10Sel} />);
    expect(m).toContain('data-maturity="2.5"');
  });

  it('the contributions give the money and the share of every group at the level, and the asymptotic anchor', () => {
    const markup = html(<ContributionsView sel={{ ...sel, rung: 'c2-gaussian-1f' }} />);
    const lv = eulerOf(o, rungOf(o, 'c2-gaussian-1f'))!.levels.find((l) => l.level === 0.999)!;
    for (const r of lv.rows) {
      expect(markup).toContain(`data-group="${r.group_id}"`);
      expect(markup).toContain(formatNumber(r.rc_var, 'en', { decimals: 0 }));
      expect(markup).toContain(formatNumber(r.rc_es, 'en', { decimals: 0 }));
      expect(markup).toContain(pct(r.share_var));
    }
    expect(markup).toContain(formatNumber(lv.anchor!.asrf_var, 'en', { decimals: 0 }));
    expect(markup).toContain(formatNumber(lv.var_total, 'en', { decimals: 0 }));
    expect(markup).toContain('kernel estimate');
  });

  it('a rung with no Euler block says so and shows the block of the first rung that has one', () => {
    const markup = html(<ContributionsView sel={{ ...sel, rung: 'c1-lhp' }} />);
    expect(markup).toContain('data-state="fallback"');
    expect(markup).toContain('data-euler="gaussian-copula-one-factor"');
  });

  it('an anchor that is null shows its reason', () => {
    const odd = structuredClone(loan) as VariantArtifact<LoanOutputs>;
    const lv = odd.outputs.euler[1].levels[0];
    lv.anchor = null;
    lv.anchor_reason = 'no closed form for the Student-t copula';
    const s = defaultSel({ ...data, variant: odd as unknown as VariantArtifact }) as C10Sel;
    expect(html(<ContributionsView sel={{ ...s, rung: 'c3-student-t', level: 0.99 }} />)).toContain('no closed form for the Student-t copula');
  });

  it('the granularity view gives the adjustment per level, the golden delta, and the adjustment against the number of names with its recursion truth or its reason', () => {
    const markup = html(<GranularityView sel={sel} />);
    const gr = o.granularity;
    for (const l of gr.levels) {
      expect(markup).toContain(`data-ga-level="${l.q}"`);
      expect(markup).toContain(formatNumber(l.delta, 'en', { digits: 4 }));
      expect(markup).toContain(formatNumber(l.ga_money, 'en', { decimals: 0 }));
    }
    expect(markup).toContain('4.83');
    for (const r of gr.by_n_names) {
      expect(markup).toContain(`data-names="${r.n_names}"`);
      if (r.truth_reason) expect(markup).toContain(escapeHtml(r.truth_reason));
    }
    expect(markup).toMatch(/share of (the )?EAD/);
  });

  it('the size and power view draws the known correlation against every estimate and gives size, power and the intervals', () => {
    const markup = html(<SizePowerView sel={gsel} />);
    for (const c of g.cells) {
      expect(markup).toContain(`data-known-rho="${c.known_rho}"`);
      expect(markup).toContain(`data-role="${c.role}"`);
      for (const e of c.estimators) {
        expect(markup).toContain(pct(e.rejection_rate, 1));
        expect(markup).toContain(pct(e.rejection_ci_low, 1));
      }
    }
    expect(markup).toContain(pct(g.generator.null_rho, 0));
    expect(markup).toContain(escapeHtml(g.size_power_definition.en));
    expect(markup).toContain(escapeHtml(g.generator.notice.en));
    expect(markup).toContain('data-test="portfolio.correlation_size_power"');
  });

  it('the estimates view draws the known correlation beside the mean estimate of every estimator, with bias, rmse and coverage', () => {
    const markup = html(<EstimatesView sel={gsel} />);
    for (const c of g.cells) {
      expect(markup).toContain(`data-known-rho="${c.known_rho}"`);
      for (const e of c.estimators) {
        expect(markup).toContain(pct(e.mean_estimate, 1));
        expect(markup).toContain(pct(e.coverage, 1));
        // the RMSE in percent, as the bias beside it (R3 c11 m-U)
        expect(markup).toContain(formatNumber(e.rmse, 'en', { percent: true, decimals: 2 }));
      }
      expect(markup).toContain(formatNumber(c.n_failed, 'en', { decimals: 0 }));
    }
    expect(markup).toContain('data-truth="known"');
  });

  it('the ladder gives every rung with its estimator, scenarios, function and reference; the models view gives the estimators and loan types', () => {
    const fit = (models as unknown as { fit: components['schemas']['c10ModelsFit'] }).fit;
    const markup = html(<LadderView sel={sel} />);
    for (const r of fit.ladder) {
      expect(markup).toContain(`data-rung="${r.id}"`);
      expect(markup).toContain(r.engine_function);
      expect(markup).toContain(escapeHtml(r.reference));
    }
    const est = html(<EstimatorsView sel={sel} />);
    for (const e of fit.estimators) expect(est).toContain(e.engine_function);
    for (const l of fit.loan_types) {
      expect(est).toContain(`data-loan-type="${l.id}"`);
      expect(est).toContain(l.irb_reference);
    }
    expect(est).toContain('Corporate');
    expect(est).toContain(pct(fit.simulator.null_rho, 0));
  });

  it('the portfolio view gives the groups, the concentration measures and the calibration, labelled illustrative', () => {
    const markup = html(<PortfolioView sel={sel} />);
    for (const gr of o.portfolio.groups) {
      expect(markup).toContain(`data-group="${gr.id}"`);
      expect(markup).toContain(escapeHtml(gr.label.en));
    }
    expect(markup).toContain(formatNumber(o.portfolio.effective_names, 'en', { digits: 4 }));
    expect(markup).toContain(pct(o.portfolio.largest_share));
    expect(markup).toContain(formatNumber(o.portfolio.n_names, 'en', { decimals: 0 }));
  });

  it('the context gives the case, the Federal Reserve table and its missing quarters, the windows and the fixture notice', () => {
    const markup = html(<C10ContextView sel={sel} />);
    expect(markup).toContain(escapeHtml(o.loss_rate_definition.en));
    expect(markup).toContain(o.data_status.table);
    for (const q of o.data_status.missing_quarters) {
      expect(markup).toContain(q.quarter);
      expect(markup).toContain(escapeHtml(q.reason));
    }
    expect(markup).toContain('1985');
    expect(markup).toContain('2012');
    expect(markup).toContain('data-fixture="true"');
    const gc = html(<C10ContextView sel={gsel} />);
    expect(gc).toContain(g.generator.shaped_on);
    expect(gc).toContain(String(g.generator.seed));
  });

  it('the variants table gives the fitted correlation of each loan type and the size and power of each simulator length', () => {
    const markup = html(<C10VariantsTable variants={[{ id: loan.variant_id, title: { en: 'Residential', es: 'Hipotecario' }, v: loan as never }, { id: grid.variant_id, title: { en: 'Simulator, 22 years', es: 'Simulador, 22 años' }, v: grid as never }]} onPick={() => undefined} current={loan.variant_id} />);
    expect(markup).toContain(`data-variant="${loan.variant_id}"`);
    expect(markup).toContain(`data-variant="${grid.variant_id}"`);
    expect(markup).toContain(pct(o.fit.maximum_likelihood.rho.estimate, 1));
    expect(markup).toContain('ct-current');
  });

  it('the Spanish views are written in Spanish', () => {
    setLang('es');
    const a = html(<LossView sel={sel} />);
    expect(a).toContain('infinitamente granular');
    expect(a).not.toContain('infinitely granular');
    const b = html(<SizePowerView sel={gsel} />);
    expect(b).toContain('Correlación conocida');
    expect(b).not.toContain('Known correlation');
    expect(html(<IrbView sel={sel} />)).toContain('Hipotecario residencial');
    expect(html(<GranularityView sel={sel} />)).toMatch(/de la EAD/);
  });
});

function RailSection({ at, d = data }: { at: number; d?: typeof data }) {
  const inst = useInstrument(d, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en', d = data) => {
  setLang(lang);
  return html(<RailSection at={at} d={d} />);
};

describe('the C10 rail', () => {
  afterEach(() => setLang('en'));

  it('has four sections for a loan type and two for the simulator, each with one control and one read-out', () => {
    function Sections({ d }: { d: typeof data }) {
      const inst = useInstrument(d, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections d={data} />)).toContain('rung|level|estimator|group');
    expect(html(<Sections d={gridData} />)).toContain('cell|estimator');
    for (const at of [0, 1, 2, 3]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
    for (const at of [0, 1]) expect(railHtml(at, 'en', gridData).match(/class="caos-readout"/g)?.length, `grid section ${at}`).toBe(1);
  });

  it('the level and the estimator keep their chips; the rung, the group and the known correlation are one select each', () => {
    expect(railHtml(0)).toMatch(/data-control="c10-rung"[^>]*><label[^>]*>Rung of the ladder<\/label><select/);
    expect(railHtml(1)).toMatch(/data-control="c10-level"[^>]*><span[^>]*>Confidence level<\/span><div class="caos-chip-row"/);
    expect(railHtml(2)).toMatch(/data-control="c10-estimator"[^>]*><span[^>]*>Correlation estimator<\/span><div class="caos-chip-row"/);
    expect(railHtml(3)).toMatch(/data-control="c10-group"[^>]*><label[^>]*>Group of the portfolio<\/label><select/);
    expect(railHtml(0, 'en', gridData)).toMatch(/data-control="c10-cell"[^>]*><label[^>]*>Known correlation<\/label><select/);
    expect(railHtml(0).match(/<option/g)?.length).toBe(o.rungs.length);
    expect(railHtml(3).match(/<option/g)?.length).toBe(o.portfolio.groups.length);
  });

  it('names rungs and groups in words, never an internal id, and prints no raw amount', () => {
    expect(railHtml(0)).not.toContain('>c2-gaussian-1f<');
    expect(railHtml(0)).toContain('Gaussian copula');
    expect(railHtml(3)).not.toContain('>g-large<');
    for (const at of [0, 1, 2, 3]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
  });

  it('the rung read-out gives EL, VaR and ES of the rung in a compact unit (the Monte Carlo error is on the loss chart since 736d4d6)', () => {
    const base = defaultSel(data) as C10Sel;
    const markup = html(<RungReadout sel={{ ...base, rung: 'c2-gaussian-1f' }} />);
    expect(markup).toContain('USD');
    expect(markup).not.toMatch(RAW_AMOUNT);
    expect(markup).toMatch(/0\.8738/);
    expect(markup).toContain('m USD');
    expect(html(<RungReadout sel={{ ...base, rung: 'c6-is-student-t' }} />)).toContain(NA);
  });

  it('the level read-out gives the fitted quantile and the years above it', () => {
    const base = defaultSel(data) as C10Sel;
    const markup = html(<LevelReadout sel={{ ...base, level: 0.99 }} />);
    expect(markup).toContain(pct(0.012339884));
    expect(markup).toContain('2');
  });

  it('the estimator read-out gives the correlation, its interval and the fitted PD of the estimator chosen', () => {
    const base = defaultSel(data) as C10Sel;
    const ml = html(<EstimatorReadout sel={base} />);
    expect(ml).toContain(pct(o.fit.maximum_likelihood.rho.estimate, 1));
    const mo = html(<EstimatorReadout sel={{ ...base, estimator: 'moments' }} />);
    expect(mo).toContain(pct(o.fit.moments.rho.estimate, 1));
  });

  it('the group read-out gives the share of the group in the VaR and the ES at the level', () => {
    const base = defaultSel(data) as C10Sel;
    const markup = html(<GroupReadout sel={{ ...base, rung: 'c2-gaussian-1f', group: 'g-small', level: 0.999 }} />);
    expect(markup).toContain(pct(0.582319998));
    expect(markup).toContain(pct(0.57));
  });

  it('the cell read-out gives the role, the rejection rate and the coverage of the estimator at the known correlation', () => {
    const base = defaultSel(gridData) as C10Sel;
    const cell = g.cells[0];
    const e = cell.estimators[0];
    const markup = html(<CellReadout sel={{ ...base, cell: String(cell.known_rho), estimator: e.estimator }} />);
    expect(markup).toContain(pct(e.rejection_rate, 1));
    expect(markup).toContain(pct(e.coverage, 1));
    expect(html(<CellReadout sel={{ ...base, cell: '0.999' }} />)).toContain(NA);
  });
});
