// CT-411 and CT-412 for C04's generator families: the Model view and every family's Validation views, rendered on the
// server from the committed artifacts in English and in Spanish. Every view is a card with its lane (replay) and its
// provenance (synthetic), never a loading placeholder; every chart has at least one series and every series a value it
// can draw; the numbers a view prints and draws are the artifact's; the marks the rubric asks for are on the charts;
// the constants the views state (S&P's entity, dos Reis et al.'s coefficient, the empirical rung, the size bound) are
// the ones the artifacts carry.
import { readFileSync } from 'node:fs';
import { formatNumber, useLangStore } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type {
  C04AgencyOutputs,
  C04CycleRung,
  C04Family,
  C04MarkovRung,
  C04MomentumRung,
  C04ThinRung,
  C04WithdrawalsRung,
  CaseManifest,
  ModelsArtifact,
  VariantArtifact,
} from '../../lib/contract.types';
import {
  DOS_REIS_C,
  EMPIRICAL_ALPHA,
  FAMILY_VIEWS,
  FamilyValidationView,
  GeneratorView,
  MarkovEstimatorsView,
  MomentumProjectionView,
  SP_ENTITY,
  drawable,
  generatorCharts,
  meanSe,
  rateSe,
  relativeSe,
  sizeBound,
  trueYearProfile,
  type ChartSpec,
} from './FamilyViews';
import { ESTIMATORS, GRADES, isFamily, makeSel, type C04Sel, type FamilyVariant } from './selection';

type Lang = 'en' | 'es';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

const manifest = read<CaseManifest>('manifests/C04.json');
const all: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: a.variant_id, data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));
const families = all.filter((c) => isFamily(c.data.variant as VariantArtifact<unknown>));
const family = (id: C04Family) => {
  const c = families.find((x) => x.id === id);
  if (!c) throw new Error(`no ${id} family in the manifest`);
  return { data: c.data, v: c.data.variant as unknown as FamilyVariant };
};
const attribution = manifest.source_details['esma-cerep'].attribution;

/** Server rendering reads the language store's initial state (the server snapshot of useSyncExternalStore), so the
 * language is set there for one render and put back after it. */
function render(el: ReactElement, lang: Lang = 'en'): string {
  const init = useLangStore.getInitialState() as { lang: Lang };
  const before = init.lang;
  init.lang = lang;
  try {
    return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  } finally {
    init.lang = before;
  }
}

/** A string as the server markup writes it in text and attributes. */
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');

/** Every card of a markup: its title, lane and provenance, as PlotCard writes them. */
function cards(markup: string): Array<{ title: string; lane: string; provenance: string }> {
  return [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)" data-lane="([^"]*)" data-provenance="([^"]*)"/g)].map((m) => ({
    title: m[1],
    lane: m[2],
    provenance: m[3],
  }));
}

/** The series count of every chart in a markup (UPlotChart's data-series). */
const chartSeries = (markup: string) => [...markup.matchAll(/data-series="(\d+)"/g)].map((m) => Number(m[1]));

/** En and em dashes and arrows (U+2013, U+2014, U+2190 to U+21FF), which no reader-facing text may hold; built from
 * their codes, so this file holds none of them. */
const BANNED = new RegExp(`[${String.fromCharCode(0x2013, 0x2014, 0x2190)}-${String.fromCharCode(0x21ff)}]`);

/** What every rendered view of this module must hold. */
function expectSound(markup: string, where: string) {
  const found = cards(markup);
  expect(found.length, `${where}: no card`).toBeGreaterThan(0);
  for (const c of found) {
    expect(c.lane, `${where}: ${c.title} lane`).toBe('replay');
    expect(c.provenance, `${where}: ${c.title} provenance`).toBe('synthetic');
    expect(c.title.trim().length, `${where}: a card without a title`).toBeGreaterThan(0);
  }
  expect(markup, `${where}: a loading placeholder`).not.toContain('data-state="loading"');
  for (const n of chartSeries(markup)) expect(n, `${where}: a chart without a series`).toBeGreaterThan(0);
  // no em-dash, en-dash or arrow anywhere a reader sees
  expect(markup, `${where}: a dash or an arrow`).not.toMatch(BANNED);
  expect(markup, `${where}: a value not available`).not.toMatch(/not available|no disponible|NaN/);
  // every card says what is drawn: a note under it
  expect((markup.match(/class="caos-plot-note"/g) ?? []).length, `${where}: a card without its note`).toBe(found.length);
}

/** The direct children of a markup's first div (by div depth; React writes no self-closing divs). */
function divChildren(markup: string): string[] {
  const re = /<(\/?)div\b[^>]*>/g;
  const out: string[] = [];
  let depth = 0;
  let start = -1;
  for (let m = re.exec(markup); m; m = re.exec(markup)) {
    if (m[1] === '') {
      depth += 1;
      if (depth === 2) start = m.index;
    } else {
      if (depth === 2 && start >= 0) {
        out.push(markup.slice(start, m.index + m[0].length));
        start = -1;
      }
      depth -= 1;
    }
  }
  return out;
}

/** The layout measured in the app (the gate's stage floor, and a readable chart at 1280 x 800): a row of two columns,
 * the left drawing a chart or the matrix map; every card fills and holds a drawing (a chart, the map or a table); a
 * right column with two cards holds the chart over the table, three shares to two. */
function expectFilled(markup: string, where: string) {
  expect(markup.startsWith('<div class="caos-views-row" data-views="2">'), `${where}: not a row of cards`).toBe(true);
  const [left, right, ...rest] = divChildren(markup);
  expect(rest.length, `${where}: more than two columns`).toBe(0);
  expect(/data-series="\d+"|data-stage=/.test(left), `${where}: the left column draws nothing`).toBe(true);
  for (const f of markup.split('<figure class="caos-plot').slice(1)) {
    expect(f.startsWith(' fill"'), `${where}: a card that does not fill`).toBe(true);
    expect(/data-series="\d+"|data-stage=|<table/.test(f), `${where}: a card without a drawing`).toBe(true);
  }
  if ((right.match(/<figure /g) ?? []).length === 2) {
    const [top, bottom] = divChildren(right);
    expect(top.startsWith('<div class="ct-part ct-part-3">') && /data-series="\d+"/.test(top), `${where}: no chart over the table`).toBe(true);
    expect(bottom.startsWith('<div class="ct-part ct-part-2">') && bottom.includes('<table'), `${where}: no table under the chart`).toBe(true);
  }
}

/** Every chart spec draws: as many values per series as x values, every series with a drawable value (positive on a
 * log axis), axis titles in both languages. */
function expectDrawn(spec: ChartSpec, where: string) {
  const d = drawable(spec);
  expect(d.series.length, `${where} ${spec.key}: a series without a drawable value`).toBe(spec.series.length);
  expect(d.dropped, `${where} ${spec.key}: a value dropped from a log axis`).toBe(0);
  for (const s of spec.series) expect(s.values.length, `${where} ${spec.key}: ${JSON.stringify(s.label)}`).toBe(spec.x.values.length);
  for (const l of ['en', 'es'] as const) {
    for (const axis of [spec.x.label, spec.y.label]) {
      const text = typeof axis === 'string' ? axis : axis[l];
      expect(text.trim().length, `${where} ${spec.key}: an axis without a title`).toBeGreaterThan(0);
    }
    for (const s of spec.series) expect((typeof s.label === 'string' ? s.label : s.label[l]).trim().length).toBeGreaterThan(0);
    const texts = [spec.x.label, spec.y.label, ...spec.series.map((s) => s.label), ...(spec.marks ?? []).map((m) => m.label)];
    for (const x of texts) expect(typeof x === 'string' ? x : x[l], `${where} ${spec.key}: a dash or an arrow`).not.toMatch(BANNED);
  }
  if (spec.y.log) for (const s of spec.series) expect(s.values.some((x) => x !== null && x > 0), `${where} ${spec.key}`).toBe(true);
}

const series = (spec: ChartSpec, en: string) => {
  const s = spec.series.find((x) => (typeof x.label === 'string' ? x.label : x.label.en) === en);
  if (!s) throw new Error(`${spec.key}: no series ${en} in ${spec.series.map((x) => (typeof x.label === 'string' ? x.label : x.label.en)).join(' | ')}`);
  return s.values;
};
const specOf = (specs: ChartSpec[], key: string) => {
  const s = specs.find((x) => x.key === key);
  if (!s) throw new Error(`no chart ${key}`);
  return s;
};
const sel = (data: CaseData, over: Partial<C04Sel> = {}) => makeSel(data, over);
/** A family's view by its tab id. */
function defOf(f: C04Family, id: string) {
  const d = FAMILY_VIEWS[f].find((x) => x.id === id);
  if (!d) throw new Error(`${f}: no view ${id}`);
  return d;
}
const chartsOf = (f: C04Family, id: string) => defOf(f, id).charts;
function viewEl(f: C04Family, id: string, s: C04Sel): ReactElement {
  const View = defOf(f, id).View;
  return <View sel={s} />;
}

describe('C04 generator families: the views', () => {
  it('reads the five families of the design', () => {
    expect(families.map((c) => c.id)).toEqual(['markov', 'momentum', 'cycle', 'withdrawals', 'thin']);
    for (const c of families) expect(Object.keys(FAMILY_VIEWS)).toContain((c.data.variant as unknown as FamilyVariant).outputs.family);
  });

  for (const c of families) {
    const v = c.data.variant as unknown as FamilyVariant;
    const defs = FAMILY_VIEWS[v.outputs.family];
    for (const lang of ['en', 'es'] as const) {
      it(`${c.id}, ${lang}: the Model view and every Validation view render with their lane and provenance`, () => {
        const s = sel(c.data);
        const model = render(<GeneratorView sel={s} />, lang);
        expectSound(model, `${c.id} ${lang} Model`);
        expectFilled(model, `${c.id} ${lang} Model`);
        expect(cards(model).length).toBe(3);
        expect(model).toContain('data-stage=');
        expect(model).toContain('data-control="c04-map-scale"');
        for (const d of defs) {
          const markup = render(<d.View sel={s} />, lang);
          expectSound(markup, `${c.id} ${lang} ${d.id}`);
          expectFilled(markup, `${c.id} ${lang} ${d.id}`);
          expect(markup, `${c.id} ${d.id}: names its truth`).toContain(esc(SP_ENTITY.name));
        }
      });
    }

    it(`${c.id}: the Spanish views are Spanish`, () => {
      const s = sel(c.data);
      for (const d of defs) {
        const en = render(<d.View sel={s} />, 'en');
        const es = render(<d.View sel={s} />, 'es');
        expect(es).not.toBe(en);
        expect(es).toMatch(/repeticiones|exacta|exacto|deudores/);
        expect(es).not.toMatch(/ repetitions| obligors per grade/);
      }
    });

    it(`${c.id}: the Validation group nests one sub-tab per view, in order`, () => {
      const markup = render(<FamilyValidationView sel={sel(c.data)} />);
      expect(markup).toContain('role="tablist"');
      const tabs = [...markup.matchAll(/data-tab="([^"]+)"/g)].map((m) => m[1]);
      expect(tabs).toEqual(defs.map((d) => d.id));
      expect(tabs.length).toBeLessThanOrEqual(6);
      expectSound(markup, `${c.id} Validation`);
    });

    it(`${c.id}: every chart draws every series, at every grade and estimator`, () => {
      for (let g = 0; g < GRADES.length; g++) {
        for (const e of v.outputs.family === 'markov' ? ESTIMATORS : (['em'] as const)) {
          const s = sel(c.data, { grade: g, estimator: e });
          for (const spec of generatorCharts(v, s)) expectDrawn(spec, `${c.id} model`);
          for (const d of defs) {
            const specs = d.charts(v, s);
            expect(specs.length, `${c.id} ${d.id}: no chart`).toBeGreaterThan(0);
            for (const spec of specs) expectDrawn(spec, `${c.id} ${d.id} grade ${GRADES[g]}`);
          }
        }
      }
    });
  }

  it('a selection without data waits for it; a variant that is not a family says so', () => {
    const { data } = family('markov');
    expect(render(<GeneratorView sel={null} />)).toContain('data-state="loading"');
    expect(render(<FamilyValidationView sel={null} />)).toContain('data-state="loading"');
    const sp = all.find((c) => c.id === 'sp')!.data;
    for (const el of [<GeneratorView sel={sel(sp)} />, <FamilyValidationView sel={sel(sp)} />, <MarkovEstimatorsView sel={sel(family('momentum').data)} />]) {
      const markup = render(el);
      expect(markup).toContain('class="ct-note"');
      expect(markup).not.toContain('data-state="loading"');
      expect(cards(markup).length).toBe(0);
    }
    expect(render(<MarkovEstimatorsView sel={sel(data)} />)).not.toContain('class="ct-note"');
  });
});

describe('C04 generator families: the constants the views state are the artifacts\'', () => {
  it("S&P's EU entity is sp.json's agency, and the attribution is the manifest's", () => {
    const sp = all.find((c) => c.id === 'sp')!.data.variant as unknown as VariantArtifact<C04AgencyOutputs>;
    expect(SP_ENTITY.code).toBe(sp.outputs.agency.code);
    expect(SP_ENTITY.name).toBe(sp.outputs.agency.name);
    expect(attribution).toBe(sp.outputs.attribution);
    for (const c of families) {
      expect((c.data.variant as unknown as FamilyVariant).outputs.generator.source).toMatch(/EM generator .*S&P's pooled annual CEREP counts/);
      for (const lang of ['en', 'es'] as const) {
        const markup = render(<GeneratorView sel={sel(c.data)} />, lang);
        expect(markup).toContain(esc(attribution));
        expect(markup).toContain(esc(SP_ENTITY.name));
      }
    }
  });

  it("the size bound is riskvalidation's: C22's null family wrote it at 4,000 repetitions", () => {
    const c22 = read<VariantArtifact<{ size_bounds: Record<string, number>; simulations: Array<{ n_rep: number }> }>>('C22/null.json');
    const n = c22.outputs.simulations[0].n_rep;
    expect(sizeBound(0.05, n)).toBeCloseTo(c22.outputs.size_bounds['p<0.05'], 9);
    expect(sizeBound(0.01, n)).toBeCloseTo(c22.outputs.size_bounds['p<0.01'], 9);
  });

  it("the empirical rung and dos Reis et al.'s coefficient are the momentum family's", () => {
    const { v } = family('momentum');
    expect(v.outputs.ladder?.values).toContain(EMPIRICAL_ALPHA);
    expect(v.findings.some((f) => f.title.en.includes(`dos Reis et al. estimate ${DOS_REIS_C} on Moody's data`))).toBe(true);
    expect(v.findings.some((f) => f.title.en.includes(`alpha ${EMPIRICAL_ALPHA}`))).toBe(true);
  });
});

describe('C04 generator families: the numbers are the artifacts\'', () => {
  it('Model: the true PDs, the matrix rows and the design', () => {
    const { data, v } = family('markov');
    const s = sel(data, { grade: 4 });
    const [pd] = generatorCharts(v, s);
    expect(series(pd, 'One year, exp(Q)')).toEqual(v.outputs.generator.pd_1y);
    expect(series(pd, 'Five years, exp(5Q)')).toEqual(v.outputs.generator.pd_5y);
    expect(pd.marks).toEqual([{ x: 5, label: 'BB' }]);
    const markup = render(<GeneratorView sel={s} />);
    for (let g = 0; g < GRADES.length; g++) {
      expect(markup).toContain(`<td>${formatNumber(v.outputs.generator.obligors[g], 'en')}</td>`);
      expect(markup).toContain(`<td>${formatNumber(-v.outputs.generator.q[g][g], 'en', { digits: 3 })}</td>`);
      expect(markup).toContain(`<td>${formatNumber(100 * v.outputs.generator.pd_1y[g], 'en', { digits: 3 })}</td>`);
    }
    expect(markup).toContain('<tr class="ct-current"><td class="ct-text">BB</td>');
    expect(markup).toContain(`<td class="ct-text">${formatNumber(v.outputs.design.reps, 'en')}</td>`);
    const thin = family('thin');
    expect(render(<GeneratorView sel={sel(thin.data)} />)).toContain('none: exact, by enumerating the binomial counts');
  });

  it('markov: each estimator\'s RMSE and bias by grade, and the chosen grade\'s table', () => {
    const { data, v } = family('markov');
    const r = v.outputs.rungs[0] as C04MarkovRung;
    const truth = v.outputs.generator.pd_1y;
    const s = sel(data, { grade: 6, estimator: 'em' });
    const specs = chartsOf('markov', 'estimators')(v, s);
    for (const e of ESTIMATORS) {
      const label = { cohort: 'Cohort', duration: 'Duration', em: 'EM', diagonal: 'Diagonal', weighted: 'Weighted', jlt: 'JLT' }[e];
      expect(series(specOf(specs, 'rmse'), label)).toEqual(r.estimators[e].rmse);
      expect(series(specOf(specs, 'bias'), label)).toEqual(r.estimators[e].bias.map((b, g) => (b === null ? null : b / truth[g])));
    }
    expect(series(specOf(specs, 'rmse'), 'True one-year PD')).toEqual(truth);
    expect(specOf(specs, 'rmse').marks).toEqual([{ x: 7, label: 'CCC-C' }]);
    const markup = render(<MarkovEstimatorsView sel={s} />);
    for (const e of ESTIMATORS) {
      const p = r.estimators[e];
      expect(markup).toContain(`<td>${meanSe('en', p.rmse[6], p.rmse_mcse[6])}</td>`);
      expect(markup).toContain(`<td>${meanSe('en', p.bias[6], p.bias_mcse[6])}</td>`);
      expect(markup).toContain(`<td>${rateSe('en', p.zero[6])}</td>`);
    }
    expect(markup).toContain('data-estimator="em" class="ct-current"');
    // the rail's estimator is the thick line, and its bias carries its Monte Carlo band
    const bias = specOf(chartsOf('markov', 'estimators')(v, sel(data, { estimator: 'cohort' })), 'bias');
    expect(bias.series.find((x) => (x.label as { en: string }).en === 'Cohort')?.width).toBe(3);
    expect(series(bias, 'Cohort - 2 MC SE')[0]).toBeCloseTo((r.estimators.cohort.bias[0]! - 2 * r.estimators.cohort.bias_mcse[0]!) / truth[0], 12);
  });

  it('markov: the zero shares, the size verdicts and the coverage', () => {
    const { data, v } = family('markov');
    const r = v.outputs.rungs[0] as C04MarkovRung;
    const s = sel(data);
    const zeros = specOf(chartsOf('markov', 'zeros')(v, s), 'zeros');
    expect(series(zeros, 'Cohort')).toEqual(r.estimators.cohort.zero.map((z) => z.rate));
    const expected = specOf(chartsOf('markov', 'zeros')(v, s), 'expected-defaults');
    expect(series(expected, 'Obligor-years times the true PD')).toEqual(r.obligor_years.map((n, g) => n * v.outputs.generator.pd_1y[g]));
    expect(expected.y.log).toBe(true);
    expect(expected.marks).toEqual([{ x: 7, label: 'CCC-C' }]);
    const zm = render(viewEl('markov', 'zeros', s));
    expect(rateSe('en', r.estimators.cohort.zero[0])).toBe('99.00 (0.70)');
    expect(zm).toContain('<td>99.00 (0.70)</td>');

    const size = render(viewEl('markov', 'size', s));
    const verdict = (key: string) => new RegExp(`data-sim="${key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"[^]*?data-holds="(yes|no)"`).exec(size)?.[1];
    expect(verdict('rating.time_homogeneity@null')).toBe('yes');
    expect(verdict('rating.markov_order@null')).toBe('no');
    expect(verdict('rating.matrix_reference@null')).toBe('yes');
    expect(verdict('rating.momentum@null')).toBe('yes');
    expect(verdict('rating.markov_order@form-chi2')).toBe('no');
    expect(verdict('rating.markov_order@form-lr')).toBe('yes');
    for (const sim of v.outputs.simulations) expect(size).toContain(`<td>${rateSe('en', sim.rates['p<0.05'])}</td>`);
    const [at5, at1] = chartsOf('markov', 'size')(v, s);
    const rates5 = series(at5, 'Rejection rate').filter((x) => x !== null);
    expect(rates5).toEqual(v.outputs.simulations.map((x) => x.rates['p<0.05'].rate));
    expect(series(at1, 'Rejection rate').filter((x) => x !== null)).toEqual(v.outputs.simulations.map((x) => x.rates['p<0.01'].rate));
    // the bound breaks between the 200-repetition tests and the 2,000-repetition forms
    expect(series(at5, 'Size bound')).toContain(null);

    const coverage = specOf(chartsOf('markov', 'coverage')(v, s), 'coverage');
    expect(series(coverage, 'Wald')).toEqual(r.coverage.wald.map((x) => x.rate));
    expect(series(coverage, 'Bootstrap')).toEqual(r.coverage.bootstrap.map((x) => x.rate));
    const atGrade = specOf(chartsOf('markov', 'coverage')(v, sel(data, { grade: 1 })), 'coverage-grade');
    const methods = ['wald', 'agresti_coull', 'jeffreys', 'bootstrap'] as const;
    expect(series(atGrade, 'Coverage').filter((x) => x !== null)).toEqual(methods.map((m) => r.coverage[m][1].rate));
    expect(series(atGrade, 'Wilson 95\u00a0%, low').filter((x) => x !== null)).toEqual(methods.map((m) => r.coverage[m][1].wilson_low));
    expect(series(atGrade, 'Wilson 95\u00a0%, high').filter((x) => x !== null)).toEqual(methods.map((m) => r.coverage[m][1].wilson_high));
    const cm = render(viewEl('markov', 'coverage', s));
    expect(cm).toContain(`<td>${rateSe('en', r.coverage.wald[0])}</td>`);
    expect(rateSe('en', r.coverage.wald[0])).toBe('1.00 (0.70)');
  });

  it('momentum: the tests and the coefficient along alpha, the projections for the chosen grade', () => {
    const { data, v } = family('momentum');
    const rungs = v.outputs.rungs as C04MomentumRung[];
    const s = sel(data, { grade: 3 });
    const [rates, coefficient] = chartsOf('momentum', 'power')(v, s);
    expect(rates.x.values).toEqual(v.outputs.ladder?.values);
    for (const [tid, name] of [['rating.time_homogeneity', 'Time homogeneity'], ['rating.markov_order', 'Markov order'], ['rating.momentum', 'Momentum hazard']] as const) {
      expect(series(rates, `${name}, at 5\u00a0%`)).toEqual(rungs.map((r) => v.outputs.simulations.find((x) => x.test_id === tid && x.rung === r.value)!.rates['p<0.05'].rate));
      expect(series(rates, `${name}, at 1\u00a0%`)).toEqual(rungs.map((r) => v.outputs.simulations.find((x) => x.test_id === tid && x.rung === r.value)!.rates['p<0.01'].rate));
    }
    expect(series(coefficient, 'Fitted c, mean')).toEqual(rungs.map((r) => r.coefficient?.mean ?? null));
    expect(series(coefficient, "dos Reis et al., Moody's: 0.33")).toEqual(rungs.map(() => DOS_REIS_C));
    for (const spec of [rates, coefficient]) expect(spec.marks?.map((m) => m.x)).toEqual([EMPIRICAL_ALPHA]);
    const power = render(viewEl('momentum', 'power', s));
    const at = rungs.find((r) => r.value === EMPIRICAL_ALPHA)!;
    expect(power).toContain('<td>0.3389 (0.0037)</td>');
    expect(formatNumber(at.coefficient!.mean, 'en', { decimals: 3 })).toBe('0.339');

    const [five, error] = chartsOf('momentum', 'projection')(v, s);
    expect(series(five, 'Default frequency of the momentum chain')).toEqual(rungs.map((r) => r.pd_5y_frequency.mean[3]));
    expect(series(five, 'Cohort matrix to the fifth power')).toEqual(rungs.map((r) => r.pd_5y_cohort_power.mean[3]));
    expect(series(five, 'exp(5Q), duration generator')).toEqual(rungs.map((r) => r.pd_5y_duration.mean[3]));
    expect(series(five, 'Plain chain, no momentum')).toEqual(rungs.map((r) => r.pd_5y_frequency.truth[3]));
    expect(series(error, 'Cohort matrix to the fifth power')).toEqual(rungs.map((r) => 100 * r.error_cohort_power.mean[3]!));
    expect(series(error, 'exp(5Q), duration generator')).toEqual(rungs.map((r) => 100 * r.error_duration.mean[3]!));
    const projection = render(<MomentumProjectionView sel={s} />);
    expect(projection).toContain(`<td>${meanSe('en', at.pd_5y_frequency.mean[3], at.pd_5y_frequency.bias_mcse[3])}</td>`);
    expect(projection).toContain(`<td>${meanSe('en', at.error_cohort_power.mean[3], at.error_cohort_power.bias_mcse[3])}</td>`);
    // the projection follows the rail's grade
    expect(render(<MomentumProjectionView sel={sel(data, { grade: 5 })} />)).not.toBe(projection);
  });

  it('cycle: the tests along k, the stressed year against the average and the truth, the true PD by year', () => {
    const { data, v } = family('cycle');
    const rungs = v.outputs.rungs as C04CycleRung[];
    const s = sel(data, { grade: 4 });
    const [th, ref] = chartsOf('cycle', 'power')(v, s);
    expect(series(th, 'Time homogeneity, at 5\u00a0%')).toEqual(rungs.map((r) => v.outputs.simulations.find((x) => x.test_id === 'rating.time_homogeneity' && x.rung === r.value)!.rates['p<0.05'].rate));
    expect(series(ref, 'Against the reference matrix, at 1\u00a0%')).toEqual(rungs.map((r) => v.outputs.simulations.find((x) => x.test_id === 'rating.matrix_reference' && x.rung === r.value)!.rates['p<0.01'].rate));
    const power = render(viewEl('cycle', 'power', s));
    for (const sim of v.outputs.simulations) expect(power).toContain(`<td>${rateSe('en', sim.rates['p<0.05'])}</td>`);
    const [pit, byYear] = chartsOf('cycle', 'pit-ttc')(v, s);
    expect(series(pit, "The stressed year's cohort PD")).toEqual(rungs.map((r) => r.pd_stressed_year.mean[4]));
    expect(series(pit, 'True PD of the stressed year')).toEqual(rungs.map((r) => r.pd_true_stressed[4]));
    expect(series(pit, 'Long-run average (EBA paragraph 84)')).toEqual(rungs.map((r) => r.pd_lra.mean[4]));
    expect(series(pit, 'True five-year average')).toEqual(rungs.map((r) => r.pd_true_average[4]));
    expect(series(pit, 'Pooled PD (Anderson and Goodman)')).toEqual(rungs.map((r) => r.pd_pooled.mean[4]));
    expect(series(pit, 'Stable chain, exp(Q)')).toEqual(rungs.map((r) => r.pd_true_base[4]));
    // the year profile is the family's truth: its mean over the five years is the artifact's true average
    for (const r of rungs) {
      for (let g = 0; g < GRADES.length; g++) {
        const profile = trueYearProfile(r, g, v.outputs.design.years);
        const mean = profile.reduce((a, b) => a + b, 0) / profile.length;
        expect(Math.abs(mean - r.pd_true_average[g]) / r.pd_true_average[g]).toBeLessThan(1e-7);
      }
    }
    expect(byYear.marks).toEqual([{ x: 3, label: { en: 'stressed year', es: 'año de estrés' } }]);
    const markup = render(viewEl('cycle', 'pit-ttc', s));
    const r2 = rungs.find((r) => r.value === 2)!;
    expect(markup).toContain(`<td>${meanSe('en', r2.pd_stressed_year.mean[4], r2.pd_stressed_year.bias_mcse[4])}</td>`);
  });

  it('withdrawals: the three treatments against the truth, the withdrawn share, the tests', () => {
    const { data, v } = family('withdrawals');
    const rungs = v.outputs.rungs as C04WithdrawalsRung[];
    const s = sel(data, { grade: 5 });
    const [pd, share] = chartsOf('withdrawals', 'bias')(v, s);
    expect(series(pd, 'Removed (D4 matrix column)')).toEqual(rungs.map((r) => r.pd_removed.mean[5]));
    expect(series(pd, 'Kept in the denominator (Keep withdrawals)')).toEqual(rungs.map((r) => r.pd_kept.mean[5]));
    expect(series(pd, 'Followed to the year end (EBA paragraphs 73 and 76)')).toEqual(rungs.map((r) => r.pd_followed.mean[5]));
    expect(series(pd, 'True one-year PD')).toEqual(rungs.map((r) => r.pd_removed.truth[5]));
    expect(series(share, 'Withdrawn share')).toEqual(rungs.map((r) => r.withdrawn_share.mean[5]));
    const markup = render(viewEl('withdrawals', 'bias', s));
    const k9 = rungs.find((r) => r.value === 9)!;
    const removed = relativeSe('en', k9.pd_removed.bias[5], k9.pd_removed.bias_mcse[5], k9.pd_removed.truth[5]);
    expect(removed).toBe('-33.88 (0.75)');
    expect(markup).toContain(`<td>${removed}</td>`);
    expect(markup).toContain('no deterministic definition of a default event');
    const [tests, reference] = chartsOf('withdrawals', 'tests')(v, s);
    expect(series(tests, 'Time homogeneity, at 5\u00a0%')).toEqual(rungs.map((r) => v.outputs.simulations.find((x) => x.test_id === 'rating.time_homogeneity' && x.rung === r.value)!.rates['p<0.05'].rate));
    expect(series(reference, 'Against the reference matrix, at 5\u00a0%')).toEqual(rungs.map((r) => v.outputs.simulations.find((x) => x.test_id === 'rating.matrix_reference' && x.rung === r.value)!.rates['p<0.05'].rate));
    const tm = render(viewEl('withdrawals', 'tests', s));
    for (const sim of v.outputs.simulations) {
      expect(tm).toContain(`<td>${rateSe('en', sim.rates['p<0.05'])}</td>`);
      expect(tm).toContain(`<td>${rateSe('en', sim.rates['p<0.01'])}</td>`);
    }
  });

  it('thin: the exact coverage and length by cohort size, the overlap of adjacent grades', () => {
    const { data, v } = family('thin');
    const rungs = v.outputs.rungs as C04ThinRung[];
    const s = sel(data, { grade: 0 });
    const [coverage, length] = chartsOf('thin', 'coverage')(v, s);
    for (const [m, name] of [['wald', 'Wald'], ['agresti_coull', 'Agresti-Coull'], ['jeffreys', 'Jeffreys']] as const) {
      expect(series(coverage, name)).toEqual(rungs.map((r) => r.coverage[m][0]));
      expect(series(length, name)).toEqual(rungs.map((r) => r.length[m][0]));
    }
    expect(length.y.log).toBe(true);
    const markup = render(viewEl('thin', 'coverage', s));
    expect(markup).toContain(`<td>${formatNumber(100 * rungs[0].coverage.wald[0], 'en', { decimals: 2 })}</td>`);
    expect(formatNumber(100 * rungs[0].coverage.wald[0], 'en', { decimals: 2 })).toBe('0.33');
    const [overlap] = chartsOf('thin', 'overlap')(v, sel(data, { grade: 6 }));
    rungs.forEach((r) => expect(series(overlap, `${formatNumber(r.value, 'en')} obligors`)).toEqual([null, ...r.overlap_jeffreys, null]));
    expect(overlap.x.values).toEqual([1, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7]);
    expect(overlap.marks).toEqual([{ x: 7, label: 'CCC-C' }]);
    const expectedDefaults = specOf(chartsOf('thin', 'overlap')(v, sel(data, { grade: 6 })), 'expected-defaults');
    rungs.forEach((r) => expect(series(expectedDefaults, `${formatNumber(r.value, 'en')} obligors`)).toEqual(r.expected_defaults));
    expect(expectedDefaults.y.log).toBe(true);
    const om = render(viewEl('thin', 'overlap', s));
    for (const r of rungs) for (const p of r.overlap_jeffreys) expect(om).toContain(`<td>${formatNumber(p, 'en', { digits: 4 })}</td>`);
  });
});
