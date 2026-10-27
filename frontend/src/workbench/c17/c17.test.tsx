// U12-W: the C17 instrument rendered on the server from the c17-outputs and c17-models fixtures
// (docs/contracts/fixtures/c17). The true 99.9 percent quantile is drawn against every LDA estimate; the exceedance curve
// is on a log scale; a tail index of 1 or more shows the infinite-mean flag and no mean; the mean-corrected SLA carries
// its UNVERIFIED label; the LDCE targets are derived-only with their source; the bank is synthetic; a test that did not
// run shows its reason; no view draws a number the fixture does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { RAW_AMOUNT, cards, escapeHtml, fixtureData, html, setLang } from '../c03/u6-testkit';
import { C17_FIT, C17_OUTPUTS } from './descriptor';
import { useC17Instrument } from './instrument';
import { defaultSel, outputsOf, type C17Sel } from './selection';
import { C17ContextView, C17FindingsView, C17VariantsTable, RungReadout, ScenarioReadout, ThresholdReadout, YearsReadout } from './C17Common';
import { ByMethodView, ByYearsView, ScenarioView } from './CapitalViews';
import { ExceedanceView, TailIndexView, exceedanceChart, stabilityChart } from './LossViews';
import { LadderView, SmaSpecView } from './ModelViews';
import { ResponseView, SmaView } from './SmaViews';

type Outputs = components['schemas']['c17Outputs'];

const read = <T,>(name: string): T => JSON.parse(readFileSync(new URL(`../../../../docs/contracts/fixtures/c17/${name}`, import.meta.url), 'utf8')) as T;
const variant = read<VariantArtifact<Outputs>>('variant-tail-index-fixture.json');
const infinite = read<VariantArtifact<Outputs>>('variant-tail-index-infinite-mean-fixture.json');
const models = read<ModelsArtifact>('models-fixture.json');
const title = { en: 'Operational risk: LDA vs SMA', es: 'Riesgo operacional: LDA vs SMA' };
const data = fixtureData('C17', variant as unknown as VariantArtifact, models, title);
const dataInf = fixtureData('C17', infinite as unknown as VariantArtifact, models, title);
const o = variant.outputs;
const sel = defaultSel(data) as C17Sel;
// the first cell of the document (5 years, threshold 10,000), where the scenario rung was not evaluated
const sel5: C17Sel = { ...sel, years: 5, threshold: 10000 };
const selInf = defaultSel(dataInf) as C17Sel;
const NA = formatNumber(null, 'en');
const num = (v: number, decimals = 0) => formatNumber(v, 'en', { decimals });
const pct = (v: number, decimals = 2) => formatNumber(v, 'en', { percent: true, decimals });

const VIEWS: Array<[string, (p: { sel: C17Sel | null }) => ReactElement]> = [
  ['Exceedance', ExceedanceView], ['Tail index', TailIndexView], ['By method', ByMethodView], ['By years', ByYearsView], ['Scenarios', ScenarioView],
  ['SMA', SmaView], ['Response', ResponseView], ['Ladder', LadderView], ['Spec', SmaSpecView], ['Findings', C17FindingsView], ['Context', C17ContextView],
];

function Names() {
  const inst = useC17Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC17Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C09' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C17 descriptors', () => {
  it('describe every key of the committed documents and no other, both ways', () => {
    expect(conform(variant.outputs, C17_OUTPUTS)).toEqual([]);
    expect(conform(infinite.outputs, C17_OUTPUTS)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C17_FIT)).toEqual([]);
  });
});

describe('the C17 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C17 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('Loss|Capital|SMA|Model|Variants');
    function Count() {
      const inst = useC17Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(html(<Count />)).toContain('<p>6</p>');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('tail-index');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('the exceedance curve is on a log scale in both axes and draws exactly the three curves of the document', () => {
    const c = exceedanceChart(o.exceedance);
    expect(c.x.log).toBe(true);
    expect(c.y.log).toBe(true);
    expect(c.x.values).toEqual(o.exceedance.grid_eur.map((v) => v / 1e6));
    expect(c.series.map((s) => s.values)).toEqual([o.exceedance.monte_carlo.exceedance, o.exceedance.panjer.exceedance, o.exceedance.fft.exceedance]);
    expect(html(<ExceedanceView sel={sel} />)).toContain('data-log-x="1"');
  });

  it('the true 99.9 percent quantile and the single loss approximation are marked on the curve, and the level is a reference line', () => {
    const c = exceedanceChart(o.exceedance, o.truth);
    const xs = (c.marks ?? []).map((m) => m.x);
    expect(xs).toContain(o.truth.annual_loss_quantile.value_eur / 1e6);
    expect(xs).toContain(o.exceedance.quantile_999_eur.sla / 1e6);
    expect((c.yMarks ?? []).map((m) => m.y)).toContain(1 - o.truth.annual_loss_quantile.level);
    const markup = html(<ExceedanceView sel={sel} />);
    for (const m of ['true', 'monte-carlo', 'panjer', 'fft', 'sla']) expect(markup).toContain(`data-method="${m}"`);
    expect(markup).toContain(num(o.exceedance.quantile_999_eur.sla));
    expect(markup).toContain(num(o.truth.annual_loss_quantile.value_eur));
    expect(markup).toContain(num(o.truth.annual_loss_quantile.mc_check.n_years));
    expect(markup).toContain(num(o.truth.annual_loss_quantile.mc_check.standard_error_eur));
  });

  it('the true quantile is a bar beside the median capital of every rung, and the mean-corrected SLA is labelled UNVERIFIED', () => {
    const markup = html(<ByMethodView sel={sel5} />);
    expect(markup).toContain('data-bar-truth');
    expect(markup).toContain(num(o.truth.annual_loss_quantile.value_eur));
    const cell = o.cells[0];
    for (const rung of ['lda-lognormal', 'lda-lognormal-truncated', 'lda-splice', 'sla', 'sla-mean-corrected', 'scenario']) expect(markup).toContain(`data-rung="${rung}"`);
    // the table writes its money in its own scale (U16-R3 c18 M2): millions of EUR here
    expect(markup).toContain(formatNumber(cell.capital.lda_splice.capital_eur.median / 1e6, 'en', { decimals: 2 }));
    expect(markup).toContain(pct(cell.capital.lda_splice.share_underestimating));
    expect(markup).toMatch(/data-rung="sla-mean-corrected"[^>]*data-status="UNVERIFIED"/);
    expect(markup).toContain('UNVERIFIED');
    // the scenario rung was not evaluated for this cell: its reason is printed, no number stands in for it
    expect(markup).toContain(escapeHtml(cell.capital.scenario.reason as string));
  });

  it('the capital across the cells of the grid gives years, threshold, the ratio to the truth and the failures', () => {
    const markup = html(<ByYearsView sel={sel} />);
    for (const c of o.cells) {
      expect(markup).toContain(`data-cell="${c.id}"`);
      expect(markup).toContain(num(c.replications.n_failed));
      expect(markup).toContain(num(c.replications.n_losses_median));
      expect(markup).toContain(formatNumber(c.capital.lda_splice.ratio_to_truth.median, 'en', { digits: 3 }));
    }
    expect(markup).toContain(pct(o.cells[0].capital.lda_splice.iqr_over_truth));
  });

  it('the threshold-stability plot has the fitted tail index with its band and the true tail index and the unit boundary as references', () => {
    const rows = o.cells[0].threshold_stability;
    const c = stabilityChart(rows, o.tail_index);
    expect(c.x.values).toEqual(rows.map((r) => r.threshold_eur / 1e3));
    expect(c.series.map((s) => s.values)).toEqual([rows.map((r) => r.tail_index.p05), rows.map((r) => r.tail_index.median), rows.map((r) => r.tail_index.p95)]);
    expect((c.yMarks ?? []).map((m) => m.y).sort()).toEqual([o.tail_index, 1].sort());
    const markup = html(<TailIndexView sel={sel5} />);
    for (const r of rows) {
      expect(markup).toContain(`data-threshold="${r.threshold_eur}"`);
      expect(markup).toContain(pct(r.share_at_least_one));
      expect(markup).toContain(num(r.n_fits));
    }
  });

  it('a tail index below 1 gives the true mean; a tail index of 1 or more gives the infinite-mean flag and no mean', () => {
    const finite = html(<TailIndexView sel={sel} />);
    expect(finite).toContain('data-infinite-mean="false"');
    expect(finite).toContain(num(o.truth.annual_loss_mean.value_eur as number));
    const markup = html(<TailIndexView sel={selInf} />);
    expect(markup).toContain('data-infinite-mean="true"');
    expect(markup).toContain(escapeHtml(infinite.outputs.truth.annual_loss_mean.reason as string));
    expect(markup).not.toContain(num(o.truth.annual_loss_mean.value_eur as number));
    expect(markup).toMatch(/data-mean="not-available"/);
    // the mean-corrected SLA needs the mean: not available, with the reason of the document
    const rung = html(<ByMethodView sel={selInf} />);
    expect(rung).toContain(escapeHtml(infinite.outputs.cells[0].capital.sla_mean_corrected.reason as string));
    expect(rung).toContain('data-infinite-mean="true"');
    expect(html(<C17ContextView sel={selInf} />)).toContain('data-infinite-mean="true"');
  });

  it('the scenario view draws the influence of each scenario, the prior and its reference; a negative influence stays negative', () => {
    const markup = html(<ScenarioView sel={sel} />);
    const s = o.scenario_influence;
    for (const sc of s.scenarios) {
      expect(markup).toContain(`data-scenario="${sc.scenario_id}"`);
      expect(markup).toContain(escapeHtml(sc.label.en));
      expect(markup).toContain(num(sc.capital_without_eur));
      expect(markup).toContain(pct(sc.influence, 1).replace('-', '-'));
    }
    expect(markup).toContain(num(s.base_capital_eur));
    expect(markup).toContain(escapeHtml(s.reference));
    expect(markup).toMatch(/gamma/i);
    expect(markup).toContain('Settlement error');
  });

  it('the SMA view gives BIC, LC, ILM and the capital of the synthetic bank against the true quantile, and says the bank is synthetic', () => {
    const markup = html(<SmaView sel={sel5} />);
    const sma = o.cells[0].sma;
    expect(markup).toContain('data-synthetic="true"');
    expect(markup).toContain(escapeHtml(o.bank.label.en));
    expect(markup).toContain(num(sma.bic_eur));
    expect(markup).toContain(num(sma.orc_eur.median));
    expect(markup).toContain(num(sma.lc_eur.p95));
    expect(markup).toContain(formatNumber(sma.ilm.median, 'en', { digits: 3 }));
    expect(markup).toContain(escapeHtml(sma.note.en));
    expect(markup).toContain(num(o.bank.business_indicator.bi_eur));
    expect(markup).not.toContain('bic-times-ilm');
    expect(markup).not.toContain('>none<');
  });

  it('one large loss moves the ILM and the SMA capital, and the LDA capital barely: every row of the document is a row of the table', () => {
    const markup = html(<ResponseView sel={sel} />);
    for (const r of o.sma_response.rows) {
      expect(markup).toContain(`data-added="${r.added_loss_eur}"`);
      expect(markup).toContain(num(r.orc_eur));
      expect(markup).toContain(num(r.lda_capital_eur));
      expect(markup).toContain(formatNumber(r.ilm, 'en', { digits: 3 }));
    }
  });

  it('the ladder gives every rung with its aggregation and status, and the tests of the engine show their reason and no number', () => {
    const markup = html(<LadderView sel={sel5} />);
    for (const r of (models as unknown as { fit: components['schemas']['c17Fit'] }).fit.ladder) {
      expect(markup).toContain(`data-rung="${r.rung_id}"`);
      expect(markup).toContain(escapeHtml(r.label.en));
    }
    expect(markup).toContain(escapeHtml(String(o.cells[0].aggregation_agreement.n_compared)));
    const all = [ExceedanceView, TailIndexView, ByMethodView, ScenarioView, ResponseView, LadderView].map((V) => html(<V sel={sel} />)).join('');
    for (const t of variant.tests) {
      expect(all, t.test_id).toContain(`data-test="${t.test_id}"`);
      expect(all).toContain(escapeHtml(t.notes as string));
    }
    expect(all).not.toMatch(/NaN|undefined/);
    // an internal test id is never the text a reader sees
    expect(all).not.toMatch(/>oprisk\.[a-z_]+</);
  });

  it('the context labels the targets derived-only with their source, and the generator, the truth and the synthetic bank', () => {
    const markup = html(<C17ContextView sel={sel} />);
    expect(markup).toContain('data-label="derived-only"');
    expect(markup).toContain(escapeHtml(o.calibration.targets.source.title));
    expect(markup).toContain(o.calibration.targets.source.url);
    for (const p of o.calibration.targets.severity_percentiles) expect(markup).toContain(num(p.loss_eur));
    expect(markup).toContain(escapeHtml(o.calibration.targets.caveat.en));
    expect(markup).toContain('data-synthetic="true"');
    expect(markup).toContain(escapeHtml(o.truth.notice.en));
    expect(markup).toContain(formatNumber(o.truth.frequency.lambda_per_year, 'en', { digits: 4 }));
    expect(html(<C17FindingsView sel={sel} />)).toContain('data-fixture="true"');
  });

  it('the tail indices table gives the dispersion of the capital at each tail index and marks the infinite mean', () => {
    const rows = [
      { id: variant.variant_id, title: { en: 'Tail index 0.8', es: 'Índice de cola 0,8' }, v: variant },
      { id: infinite.variant_id, title: { en: 'Tail index 1.1', es: 'Índice de cola 1,1' }, v: infinite },
    ];
    const markup = html(<C17VariantsTable variants={rows} sel={sel5} onPick={() => undefined} current={variant.variant_id} />);
    for (const r of rows) expect(markup).toContain(`data-variant="${r.id}"`);
    expect(markup).toContain(pct(o.cells[0].capital.lda_splice.iqr_over_truth));
    expect(markup).toContain('data-infinite-mean="true"');
    expect(markup).toContain(num(infinite.outputs.truth.annual_loss_quantile.value_eur));
  });

  it('a cell with no threshold profile, and a document with no response rows, say not available and draw no chart', () => {
    const odd = structuredClone(variant) as VariantArtifact<Outputs>;
    const cell = odd.outputs.cells.find((c) => c.years === 10 && c.collection_threshold_eur === 20000)!;
    cell.threshold_stability = [];
    odd.outputs.sma_response.rows = [];
    const d = fixtureData('C17', odd as unknown as VariantArtifact, models, title);
    const s = defaultSel(d) as C17Sel;
    const tail = html(<TailIndexView sel={s} />);
    expect(tail).toContain('data-state="unavailable"');
    expect(tail).not.toContain('caos-chart');
    const response = html(<ResponseView sel={s} />);
    expect(response).toContain('data-state="unavailable"');
    expect(response).not.toContain('caos-chart');
  });

  it('a rung the bake did not evaluate in a cell is not available with its reason in every cell of the grid, and has no bar value', () => {
    const markup = html(<ByYearsView sel={{ ...sel, rung: 'scenario' }} />);
    const without = o.cells.filter((c) => c.capital.scenario.summary === null);
    expect(without.length).toBeGreaterThan(0);
    for (const c of without) expect(markup).toContain(escapeHtml(c.capital.scenario.reason as string));
    expect(markup).toContain(NA);
    expect(markup).not.toMatch(/NaN|undefined|Infinity/);
  });

  it('the mean-corrected SLA keeps its label in the title of the by-years view and in every place it is named', () => {
    const years = html(<ByYearsView sel={{ ...sel, rung: 'sla-mean-corrected' }} />);
    expect(years).toContain('UNVERIFIED');
    expect(html(<LadderView sel={sel} />)).toContain('data-status="UNVERIFIED"');
    expect(html(<SmaSpecView sel={sel} />)).not.toContain('NaN');
  });

  it('the standardised approach as specified gives the buckets, the golden value of the standard and the discretions', () => {
    const fit = (models as unknown as { fit: components['schemas']['c17Fit'] }).fit;
    const markup = html(<SmaSpecView sel={sel} />);
    expect(markup).toContain(`data-golden="${fit.sma.golden.bic_eur}"`);
    expect(markup).toContain(num(fit.sma.golden.bic_eur));
    for (const b of fit.sma.buckets) expect(markup).toContain(`data-bucket="${b.bucket}"`);
    for (const d of fit.sma.discretions) expect(markup).toContain(`data-discretion="${d.id}"`);
    expect(markup).toContain('no upper limit');
  });

  it('the Spanish view is written in Spanish', () => {
    setLang('es');
    const markup = html(<ByMethodView sel={sel} />);
    expect(markup).toContain('Cuantil verdadero');
    expect(markup).not.toContain('True quantile');
    expect(html(<TailIndexView sel={sel} />)).toContain('Índice de cola');
    expect(html(<C17ContextView sel={sel} />)).toContain('solo derivado');
  });
});

function RailSection({ at }: { at: number }) {
  const inst = useC17Instrument(data, () => undefined);
  return <div>{inst ? inst.rail[at].content : null}</div>;
}
const railHtml = (at: number, lang: 'en' | 'es' = 'en') => {
  setLang(lang);
  return html(<RailSection at={at} />);
};

describe('the C17 rail', () => {
  afterEach(() => setLang('en'));

  it('has four sections, each with one control and one read-out', () => {
    function Sections() {
      const inst = useC17Instrument(data, () => undefined);
      return <p>{inst ? inst.rail.map((r) => r.id).join('|') : 'none'}</p>;
    }
    expect(html(<Sections />)).toContain('years|threshold|rung|scenario');
    for (const at of [0, 1, 2, 3]) expect(railHtml(at).match(/class="caos-readout"/g)?.length, `section ${at}`).toBe(1);
  });

  it('keeps the two small choices as chips and the rung and the scenario as one select each, named in words', () => {
    expect(railHtml(0)).toMatch(/data-control="c17-years"[^>]*><span[^>]*>Years of data<\/span><div class="caos-chip-row"/);
    expect(railHtml(1)).toMatch(/data-control="c17-threshold"[^>]*><span[^>]*>Collection threshold<\/span><div class="caos-chip-row"/);
    expect(railHtml(2)).toMatch(/data-control="c17-rung"[^>]*><label[^>]*>Method<\/label><select/);
    expect(railHtml(3)).toMatch(/data-control="c17-scenario"[^>]*><label[^>]*>Scenario<\/label><select/);
    expect(railHtml(2).match(/<option/g)?.length).toBe(6);
    expect(railHtml(3).match(/<option/g)?.length).toBe(o.scenario_influence.scenarios.length);
    expect(railHtml(2)).not.toContain('>lda-splice<');
    expect(railHtml(3)).not.toContain('>S1<');
    for (const at of [0, 1, 2, 3]) for (const lang of ['en', 'es'] as const) expect(railHtml(at, lang), `section ${at} ${lang}`).not.toMatch(RAW_AMOUNT);
  });

  it('the years and threshold read-outs give the histories and the tail index of the cell chosen', () => {
    const base = defaultSel(data) as C17Sel;
    const cell = o.cells.find((c) => c.years === 10 && c.collection_threshold_eur === 20000)!;
    const years = html(<YearsReadout sel={{ ...base, years: 10, threshold: 20000 }} />);
    expect(years).toContain(num(cell.replications.n_replications));
    expect(years).toContain(num(cell.replications.n_losses_median));
    const thr = html(<ThresholdReadout sel={{ ...base, years: 10, threshold: 20000 }} />);
    expect(thr).toContain(pct(cell.threshold_stability[0].share_at_least_one));
  });

  it('the rung read-out gives the aggregation, the status and the ratio to the truth; the unverified rung says so; a rung with no value is not available', () => {
    const base = defaultSel(data) as C17Sel;
    const splice = html(<RungReadout sel={{ ...base, years: 5, threshold: 10000, rung: 'lda-splice' }} />);
    expect(splice).toContain(formatNumber(o.cells[0].capital.lda_splice.ratio_to_truth.median, 'en', { digits: 3 }));
    expect(html(<RungReadout sel={{ ...base, years: 5, threshold: 10000, rung: 'sla-mean-corrected' }} />)).toContain('UNVERIFIED');
    expect(html(<RungReadout sel={{ ...base, years: 5, threshold: 10000, rung: 'scenario' }} />)).toContain(NA);
  });

  it('the scenario read-out gives the loss, the frequency and the influence of the scenario chosen', () => {
    const base = defaultSel(data) as C17Sel;
    const sc = o.scenario_influence.scenarios[0];
    const markup = html(<ScenarioReadout sel={{ ...base, scenario: sc.scenario_id }} />);
    expect(markup).toContain(pct(sc.influence, 1));
    expect(markup).toContain(formatNumber(sc.exceedance_frequency_per_year, 'en', { digits: 3 }));
  });
});
