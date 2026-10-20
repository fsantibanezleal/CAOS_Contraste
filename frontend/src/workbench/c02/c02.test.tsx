// U14-W: the C02 instrument rendered on the server from the c02-outputs and c02-models fixtures
// (docs/contracts/fixtures/c02). Corporate PD across 1 to 5 year horizons: ROC and CAP with AUC, Gini and KS, the DeLong
// differences between rungs, calibration by decile, the overfit gap, the exploratory transfer heat map and term
// structure and the exploratory ECL effect (each labelled exploratory), the discrimination by horizon; a null field
// says "not available" with its reason; no view draws a number the fixture does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { cards, escapeHtml, fixtureData, html, readU14Fixture, setLang } from '../c20/testkit';
import { C02_FIT, C02_OUTPUTS } from './descriptor';
import { useC02Instrument } from './instrument';
import { defaultSel, outputsOf, type C02Sel } from './selection';
import { C02ContextView, C02FindingsView, C02VariantsTable, ChallengerReadout, RungReadout } from './C02Common';
import { CalibrationView, RocCapView, RungsView, StabilityView, rocChart } from './DiscriminationViews';
import { EclImpactView, TermStructureView, TransferView } from './HorizonViews';

type Outputs = components['schemas']['c02Outputs'];

const h1 = readU14Fixture<VariantArtifact<Outputs>>('c02', 'variant-horizon-h1-fixture.json');
const pooled = readU14Fixture<VariantArtifact<Outputs>>('c02', 'variant-horizon-pooled-fixture.json');
const models = readU14Fixture<ModelsArtifact>('c02', 'models-fixture.json');
const title = { en: 'Corporate PD across horizons', es: 'PD corporativa a distintos horizontes' };
const data = fixtureData('C02', h1 as unknown as VariantArtifact, models, title);
const o = h1.outputs;
const sel = defaultSel(data) as C02Sel;
const f3 = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { decimals: 3 });
const pct = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { percent: true, decimals: 2 });
const NA = formatNumber(null, 'en');
const withVariant = (v: VariantArtifact<Outputs>): C02Sel => defaultSel({ ...data, variant: v as unknown as VariantArtifact }) as C02Sel;
const clone = () => structuredClone(h1) as VariantArtifact<Outputs>;

const VIEWS: Array<[string, (p: { sel: C02Sel | null }) => ReactElement]> = [
  ['ROC and CAP', RocCapView], ['Rungs compared', RungsView], ['Calibration', CalibrationView], ['Overfit and stability', StabilityView],
  ['Transfer', TransferView], ['Term structure', TermStructureView], ['ECL effect', EclImpactView],
  ['Findings', C02FindingsView], ['Context', C02ContextView],
];

function Names() {
  const inst = useC02Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const inst = useC02Instrument({ ...data, manifest: { ...data.manifest, case_id: 'C09' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}

describe('the C02 contract descriptors', () => {
  it('describe the fixtures key by key, in both directions', () => {
    for (const v of [h1, pooled]) expect(conform(v.outputs, C02_OUTPUTS)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C02_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone();
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).term_structure;
    const found = conform(odd.outputs, C02_OUTPUTS).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/term_structure: declared by the web, not written by the pipeline/);
  });
});

describe('the C02 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C02 only, with the groups in the validator order and no more than six peers', () => {
    expect(html(<Names />)).toContain('Validation|Exploratory horizons|Impact|Findings|By horizon');
    function Count() {
      const inst = useC02Instrument(data, () => undefined);
      return <p>{inst ? inst.groups.length + 2 : 0}</p>;
    }
    expect(Number(/<p>(\d+)<\/p>/.exec(html(<Count />))?.[1])).toBeLessThanOrEqual(6);
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sel)?.kind).toBe('horizon');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View] of VIEWS) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('ROC and CAP give AUC, its DeLong interval, Gini and KS of every rung, and one ROC and one CAP curve per rung', () => {
    const markup = html(<RocCapView sel={sel} />);
    for (const r of o.rungs) {
      expect(markup).toContain(`data-rung="${r.model_id}"`);
      expect(markup).toContain(f3(r.discrimination.auc));
      expect(markup).toContain(f3(r.discrimination.auc_ci.lo));
      expect(markup).toContain(f3(r.discrimination.auc_ci.hi));
      expect(markup).toContain(f3(r.discrimination.gini));
      expect(markup).toContain(f3(r.discrimination.ks));
    }
    expect(markup).toContain('DeLong');
    const chart = rocChart(sel, 'roc');
    expect(chart?.series.length).toBe(o.rungs.length + 1);
    expect(chart?.x.values).toEqual([0, 0.1, 0.3, 1]);
    expect(rocChart(sel, 'cap')?.series.length).toBe(o.rungs.length + 1);
    expect(rocChart(null, 'roc')).toBeNull();
  });

  it('the rungs compared give the AUC difference with its DeLong interval and p, the Brier difference and the grade disagreement', () => {
    const markup = html(<RungsView sel={sel} />);
    const c = o.challenger[0];
    expect(markup).toContain(`data-champion="${c.champion}" data-challenger="${c.challenger}"`);
    expect(markup).toContain(f3(c.auc_diff));
    expect(markup).toContain(f3(c.auc_diff_ci.lo));
    expect(markup).toContain(f3(c.auc_diff_ci.hi));
    expect(markup).toContain(formatNumber(c.delong_p_value, 'en', { digits: 2 }));
    expect(markup).toContain(formatNumber(c.brier_diff, 'en', { decimals: 4 }));
    expect(markup).toContain(pct(c.grade_disagreement_share));
    expect(markup).toContain('paired bootstrap');
  });

  it('the calibration view gives every decile of the rung in focus with its interval and the Hosmer-Lemeshow test', () => {
    const markup = html(<CalibrationView sel={sel} />);
    const r = o.rungs.find((x) => x.model_id === sel.rung)!;
    expect(markup.match(/data-bin="/g)?.length).toBe(r.reliability.length);
    for (const b of r.reliability) {
      expect(markup).toContain(pct(b.pd));
      expect(markup).toContain(pct(b.dr));
      expect(markup).toContain(pct(b.hi));
    }
    expect(markup).toContain(formatNumber(r.calibration.hosmer_lemeshow.statistic, 'en', { decimals: 2 }));
    expect(markup).toContain(f3(r.calibration.brier));
    expect(markup).toContain(f3(r.calibration.ece));
  });

  it('a rung with no reliability bin says not available with a reason, never an empty chart', () => {
    const odd = clone();
    odd.outputs.rungs[0].reliability = [];
    const markup = html(<CalibrationView sel={{ ...withVariant(odd), rung: odd.outputs.rungs[0].model_id }} />);
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).not.toContain('data-bin="');
  });

  it('the overfit gap shows each rung against its tolerance, labelled a convention, with the stability of the holdout', () => {
    const markup = html(<StabilityView sel={sel} />);
    for (const r of o.rungs) {
      expect(markup).toContain(`data-rung="${r.model_id}" data-flag="${r.overfit.flag}"`);
      expect(markup).toContain(f3(r.overfit.train_auc));
      expect(markup).toContain(f3(r.overfit.holdout_auc));
      expect(markup).toContain(f3(r.stability.psi));
    }
    expect(markup).toContain('convention');
    expect(markup).toContain(escapeHtml(o.parameters[0].basis));
    const odd = clone();
    Object.assign(odd.outputs.rungs[0].overfit, { gap: 0.09, flag: true });
    expect(html(<StabilityView sel={withVariant(odd)} />)).toContain('data-flag="true"');
  });

  it('the transfer heat map is labelled exploratory with its reason, one cell per fitted and scored horizon', () => {
    const c = o.transfer.cells[0];
    const markup = html(<TransferView sel={{ ...sel, rung: o.rungs.find((r) => r.rung === c.rung)!.model_id }} />);
    expect(markup).toContain('data-label="exploratory"');
    expect(markup).toContain(escapeHtml(o.transfer.reason.en));
    expect(markup).toContain(`data-fitted="${c.fitted_on_years}" data-scored="${c.scored_on_years}"`);
    expect(markup).toContain(f3(c.auc));
  });

  it('the pooled variant has no transfer cell: not available with the reason, no heat map', () => {
    const markup = html(<TransferView sel={withVariant(pooled)} />);
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).toContain(escapeHtml(pooled.outputs.transfer.reason.en));
    expect(markup).not.toContain('data-fitted="');
  });

  it('a rung with no transfer cell in a variant that has some says so, and draws no map for it', () => {
    const p4 = o.rungs.find((r) => r.rung === 'P4')!.model_id;
    const markup = html(<TransferView sel={{ ...sel, rung: p4 }} />);
    expect(markup).toContain('data-state="unavailable"');
    expect(markup).toContain('no transfer cell for the rung in focus');
  });

  it('the term structure is labelled exploratory and gives each year with its cumulative PD and hazard', () => {
    const markup = html(<TermStructureView sel={sel} />);
    expect(markup).toContain('data-label="exploratory"');
    expect(markup).toContain(escapeHtml(o.term_structure.reason.en));
    for (const p of o.term_structure.points) {
      expect(markup).toContain(`data-years="${p.years}"`);
      expect(markup).toContain(pct(p.cumulative_pd));
    }
    expect(markup).toContain('data-nondecreasing="true"');
    const odd = clone();
    odd.outputs.term_structure.cumulative_nondecreasing = false;
    expect(html(<TermStructureView sel={withVariant(odd)} />)).toContain('data-nondecreasing="false"');
  });

  it('the ECL effect is labelled exploratory, in the document unit, with the LGD named an assumption', () => {
    const markup = html(<EclImpactView sel={sel} />);
    expect(markup).toContain('data-label="exploratory"');
    expect(markup).toContain('caos-bars');
    expect(markup).toContain(formatNumber(o.impact_detail.ecl_12m_effect, 'en', { digits: 4 }));
    expect(markup).toContain(formatNumber(o.impact_detail.ecl_lifetime_effect, 'en', { digits: 4 }));
    expect(markup).toContain(escapeHtml(o.impact_detail.unit));
    expect(markup).toContain('assumption');
    expect(markup).toContain(escapeHtml(o.impact_detail.pd_basis));
  });

  it('an ECL effect the document leaves null says not available with its reason, never a zero', () => {
    const odd = clone();
    Object.assign(odd.outputs.impact_detail, { ecl_12m_effect: null, ecl_lifetime_effect: null, reason_if_null: 'The provisions engine did not run for this file.' });
    const markup = html(<EclImpactView sel={withVariant(odd)} />);
    expect(markup).toContain('The provisions engine did not run for this file.');
    expect(markup).toContain(NA);
    expect(markup).not.toContain('caos-bars');
  });

  it('the findings view says a test that did not run and shows its reason, never a number', () => {
    const markup = html(<C02FindingsView sel={sel} />);
    expect(markup).toContain('data-test="disc.auc"');
    expect(markup).toContain(escapeHtml(h1.tests[0].notes as string));
    expect(markup).toContain('data-fixture="true"');
    expect(markup).not.toMatch(/NaN|undefined/);
  });

  it('the discrimination by horizon gives one row per file and the chart of the rung across the years, the pooled file apart', () => {
    const at = (years: number, shift: number) => {
      const v = clone();
      Object.assign(v.outputs, { horizon_id: `h${years}`, years });
      v.variant_id = `fixture-h${years}`;
      for (const r of v.outputs.rungs) r.discrimination.auc = Math.round((r.discrimination.auc - shift) * 1000) / 1000;
      return v;
    };
    const variants = [at(1, 0), at(2, 0.02), at(3, 0.04), at(4, 0.05), at(5, 0.07), pooled].map((v) => ({ id: v.variant_id, title: { en: v.variant_id, es: v.variant_id }, v }));
    const markup = html(<C02VariantsTable variants={variants} onPick={() => undefined} current="fixture-h1" rung="P4" />);
    for (const years of [1, 2, 3, 4, 5]) expect(markup).toContain(`data-years="${years}"`);
    expect(markup).toContain('data-years="pooled"');
    expect(markup).toContain(f3(0.88 - 0.07));
    expect(markup).toContain('different samples');
  });

  it('the context gives the counts, the leakage-safe protocol, the pooled caveat and every named parameter as a convention', () => {
    const markup = html(<C02ContextView sel={sel} />);
    expect(markup).toContain(formatNumber(o.counts.rows, 'en', { decimals: 0 }));
    expect(markup).toContain(formatNumber(o.counts.events, 'en', { decimals: 0 }));
    expect(markup).toContain(escapeHtml(o.counts.event_definition.en));
    expect(markup).toContain('data-out-of-time="false"');
    expect(markup).toContain('data-parameter="overfit_tolerance"');
    expect(markup).toContain('data-status="convention"');
    expect(html(<C02ContextView sel={withVariant(pooled)} />)).toContain(escapeHtml(pooled.outputs.firm_overlap_caveat!.en));
  });

  it('the rail read-outs follow the rung and the challenger in focus', () => {
    const r = o.rungs[1];
    const markup = html(<RungReadout sel={{ ...sel, rung: r.model_id }} />);
    expect(markup).toContain(f3(r.discrimination.auc));
    const c = o.challenger[0];
    expect(html(<ChallengerReadout sel={{ ...sel, challenger: c.challenger }} />)).toContain(f3(c.auc_diff));
  });

  it('renders in Spanish with decimal commas and Spanish words', () => {
    setLang('es');
    const p1 = o.rungs.find((r) => r.rung === 'P1')!.model_id;
    const markup = html(<RocCapView sel={sel} />) + html(<TransferView sel={{ ...sel, rung: p1 }} />) + html(<EclImpactView sel={sel} />);
    expect(markup).toContain(f3(o.rungs[0].discrimination.auc, 'es'));
    expect(markup).toContain('exploratorio');
    expect(markup).toContain('Gini');
    expect(markup).not.toMatch(/\d\.\d{3}\b/);
  });

  it('a changed fixture field changes the markup: the views read the document and nothing else', () => {
    const odd = clone();
    odd.outputs.rungs[0].discrimination.auc = 0.8123;
    expect(html(<RocCapView sel={withVariant(odd)} />)).toContain(f3(0.8123));
    expect(html(<RocCapView sel={sel} />)).not.toContain(f3(0.8123));
  });
});
