// U14-W: the C20 instrument rendered on the server from the c20 fixtures (docs/contracts/fixtures/c20): the five kinds of
// variant, the models fit. SGCD views carry the dataset card's prohibited-use sentence, the shipped and the
// Contraste-applied blocks stay apart, the rule-of-thumb lines are labelled conventions, the CBPE row is an estimate, a
// null field says "not available" with its reason, a view given a variant of another kind says so, and no view draws a
// number the fixture does not contain.
import { formatNumber } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import type { components } from '../../lib/contract.gen';
import { conform, type ModelsArtifact, type VariantArtifact } from '../../lib/contract.types';
import { cards, escapeHtml, fixtureData, html, readU14Fixture, setLang } from './testkit';
import { C20_FIT, C20_OUTPUTS, C20_OUTPUTS_LEAKAGE, C20_OUTPUTS_PERTURBATION, C20_OUTPUTS_SEEDS, C20_OUTPUTS_SHIFT } from './descriptor';
import { useC20Instrument } from './instrument';
import { defaultSel, outputsOf, type C20Sel } from './selection';
import { C20ContextView, C20FindingsView, C20VariantsTable, SgcdNotice } from './C20Common';
import { DegradationView, DriftView, QualityView } from './ShockViews';
import { CbpeView, ConformalView, RealDriftView, SyntheticShiftView } from './ShiftViews';
import { ExplainerView, LeakageView, PerturbationView, SeedsView } from './RobustnessViews';
import { DecisionFlipView, FairnessView } from './FairnessViews';

type S = components['schemas'];
const fx = <T,>(f: string) => readU14Fixture<VariantArtifact<T>>('c20', `variant-${f}-fixture.json`);
const shock = fx<S['c20Outputs']>('shock');
const shift = fx<S['c20OutputsShift']>('shift');
const seeds = fx<S['c20OutputsSeeds']>('seeds');
const pert = fx<S['c20OutputsPerturbation']>('perturbation');
const leak = fx<S['c20OutputsLeakage']>('leakage');
const models = readU14Fixture<ModelsArtifact>('c20', 'models-fixture.json');
const title = { en: 'ML model validation', es: 'Validación de modelos de ML' };
const mk = (v: VariantArtifact<unknown>) => fixtureData('C20', v as unknown as VariantArtifact, models, title);
const selOf = (v: VariantArtifact<unknown>) => defaultSel(mk(v)) as C20Sel;
const sShock = selOf(shock);
const sShift = selOf(shift);
const sSeeds = selOf(seeds);
const sPert = selOf(pert);
const sLeak = selOf(leak);
const f3 = (v: number, lang: 'en' | 'es' = 'en') => formatNumber(v, lang, { decimals: 3 });
const NA = formatNumber(null, 'en');
const PROHIBITED = 'must not be used for real-world credit scoring or any production decision-making about individuals';
const clone = <T,>(v: VariantArtifact<T>) => structuredClone(v);

const OF_KIND: Array<[string, (p: { sel: C20Sel | null }) => ReactElement, C20Sel]> = [
  ['Degradation', DegradationView, sShock], ['Drift', DriftView, sShock], ['Quality', QualityView, sShock],
  ['Real drift', RealDriftView, sShift], ['Synthetic shift', SyntheticShiftView, sShift], ['Conformal', ConformalView, sShift], ['CBPE', CbpeView, sShift],
  ['Noise', PerturbationView, sPert], ['Seeds', SeedsView, sSeeds], ['Explainers', ExplainerView, sSeeds], ['Leakage', LeakageView, sLeak],
  ['Fairness', FairnessView, sSeeds], ['Flips', DecisionFlipView, sShock], ['Findings', C20FindingsView, sShock], ['Context', C20ContextView, sShock],
];

function Names() {
  const inst = useC20Instrument(mk(shock), () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}
function Other() {
  const d = mk(shock);
  const inst = useC20Instrument({ ...d, manifest: { ...d.manifest, case_id: 'C09' } }, () => undefined);
  return <p>{inst ? 'some' : 'null'}</p>;
}
function Rail({ v }: { v: VariantArtifact<unknown> }) {
  const inst = useC20Instrument(mk(v), () => undefined);
  return <p>{inst ? inst.rail.map((r) => (typeof r.label === 'string' ? r.label : r.label.en)).join('|') : 'none'}</p>;
}

describe('the C20 contract descriptors', () => {
  it('describe the five kinds of variant and the fit key by key, in both directions', () => {
    expect(conform(shock.outputs, C20_OUTPUTS)).toEqual([]);
    expect(conform(shift.outputs, C20_OUTPUTS_SHIFT)).toEqual([]);
    expect(conform(seeds.outputs, C20_OUTPUTS_SEEDS)).toEqual([]);
    expect(conform(pert.outputs, C20_OUTPUTS_PERTURBATION)).toEqual([]);
    expect(conform(leak.outputs, C20_OUTPUTS_LEAKAGE)).toEqual([]);
    expect(conform((models as unknown as { fit: unknown }).fit, C20_FIT)).toEqual([]);
  });
  it('refuse a document with a key the web does not declare and one it lacks', () => {
    const odd = clone(leak);
    (odd.outputs as unknown as Record<string, unknown>).planted = 1;
    delete (odd.outputs as unknown as Record<string, unknown>).caught;
    const found = conform(odd.outputs, C20_OUTPUTS_LEAKAGE).join('\n');
    expect(found).toMatch(/planted: written by the pipeline, not declared by the web/);
    expect(found).toMatch(/caught: declared by the web, not written by the pipeline/);
  });
});

describe('the C20 instrument', () => {
  afterEach(() => setLang('en'));

  it('answers for C20 only, with at most four groups before the Variants view', () => {
    expect(html(<Names />)).toContain('Shocks and shifts|Robustness|Fairness and impact|Findings|Variants');
    expect(html(<Other />)).toContain('null');
    expect(outputsOf(sShock)?.kind).toBe('shock');
  });

  it('the rail follows the kind of variant and adds the fairness section only where the document carries the battery', () => {
    expect(html(<Rail v={shock} />)).toContain('<p>Shock</p>');
    expect(html(<Rail v={shift} />)).toContain('<p>Shift</p>');
    expect(html(<Rail v={seeds} />)).toContain('Rung|Fairness');
    expect(html(<Rail v={pert} />)).toContain('Noise|Fairness');
    expect(html(<Rail v={leak} />)).toContain('Screen|Fairness');
  });

  it('every view renders and carries its lane; with no selection each says loading', () => {
    for (const [name, View, sel] of OF_KIND) {
      const found = cards(html(<View sel={sel} />));
      expect(found.length, `${name}: no view rendered`).toBeGreaterThan(0);
      for (const card of found) expect(card.lane, `${name}: a view without its lane`).toBe(true);
      expect(html(<View sel={null} />), name).toContain('data-state="loading"');
    }
  });

  it('a view given a variant of another kind says so, names the kind that carries it and draws no chart', () => {
    for (const View of [DegradationView, DriftView, QualityView]) {
      const markup = html(<View sel={sSeeds} />);
      expect(markup).toContain('data-state="unavailable"');
      expect(markup).toContain('Pick the &quot;SGCD shocks&quot; variant');
      expect(markup).not.toContain('caos-bars');
    }
    expect(html(<LeakageView sel={sShock} />)).toContain('data-state="unavailable"');
    expect(html(<CbpeView sel={sPert} />)).toContain('data-state="unavailable"');
  });

  it('every SGCD view carries the dataset card prohibited-use sentence; a view of another dataset does not', () => {
    for (const [name, View, sel] of OF_KIND.filter(([, , s]) => s === sShock)) {
      if (name === 'Findings' || name === 'Context' || name === 'Degradation' || name === 'Drift' || name === 'Quality' || name === 'Flips') {
        expect(html(<View sel={sel} />), name).toContain(PROHIBITED);
      }
    }
    expect(html(<SgcdNotice sel={sSeeds} />)).toBe('');
    expect(html(<LeakageView sel={sLeak} />)).not.toContain(PROHIBITED);
    // a document without its own notice falls back to the one of the models artifact, so the sentence is never lost
    const odd = clone(shock);
    odd.outputs.sgcd_notice = null;
    expect(html(<SgcdNotice sel={selOf(odd)} />)).toContain(PROHIBITED);
  });

  it('degradation keeps the shipped and the Contraste-applied blocks apart, with the records that reach the model', () => {
    const markup = html(<DegradationView sel={sShock} />);
    expect(markup).toContain('data-block="shipped"');
    expect(markup).toContain('data-block="applied"');
    expect(markup).toContain('shocks the model has seen');
    for (const r of shock.outputs.shipped.rows) {
      expect(markup).toContain(`data-shock="${r.shock_id}" data-reach="${r.n_reaching_structured_view}"`);
      expect(markup).toContain(f3(r.performance.auc));
    }
    expect(markup).toContain(escapeHtml(shock.outputs.applied.parameters_source));
    const held = clone(shock);
    held.outputs.seen_or_held_out = 'held-out';
    expect(html(<DegradationView sel={selOf(held)} />)).toContain('shocks held out of the model');
  });

  it('drift draws the rule-of-thumb lines labelled conventions, with the chi-square test and the inputs of the shock', () => {
    const markup = html(<DriftView sel={sShock} />);
    expect(markup).toContain('legacy rule of thumb');
    expect(markup).toContain('not a regulatory threshold');
    const r = shock.outputs.shipped.rows[0];
    expect(markup).toContain(f3(r.drift.psi_max));
    for (const v of r.drift.variables) expect(markup).toContain(`data-input="${v.name}"`);
    expect(markup).toContain('data-benchmark="within"');
    expect(markup).toContain(NA);
    const applied = html(<DriftView sel={{ ...sShock, block: 'applied' }} />);
    expect(applied).toContain('data-block="applied"');
  });

  it('quality gives completeness, and consistency or attribution not available with the reason', () => {
    const markup = html(<QualityView sel={sShock} />);
    expect(markup).toContain('needs both views');
    expect(markup).toContain(formatNumber(shock.outputs.shipped.rows[0].data_quality.completeness, 'en', { percent: true, decimals: 1 }));
    expect(markup).toContain(f3(shock.outputs.shipped.rows[0].attribution_rank_correlation as number));
    const odd = clone(shock);
    odd.outputs.shipped.rows[0].attribution_rank_correlation = null;
    expect(html(<QualityView sel={selOf(odd)} />)).toContain('no attribution on this shock');
  });

  it('real drift is labelled as drift with no model and gives the PSI, CSI, KS and test of each variable', () => {
    const markup = html(<RealDriftView sel={sShift} />);
    expect(markup).toContain('data-label="real-drift-no-model"');
    const v = shift.outputs.real_drift.pairs[0].variables[0];
    expect(markup).toContain(`data-input="${v.name}"`);
    expect(markup).toContain(f3(v.psi));
    expect(markup).toContain(f3(v.ks));
      });

  it('the synthetic shift names its reference portfolio, labelled, and gives each shift and the worst subsample', () => {
    const markup = html(<SyntheticShiftView sel={sShift} />);
    expect(markup).toContain('data-label="synthetic-shift-fed-reference"');
    expect(markup).toContain('higher risk portfolio');
    const s = shift.outputs.synthetic_shift;
    expect(markup).toContain(`data-shift="${s.shifts[0].shift_id}"`);
    expect(markup).toContain(f3(s.worst_subsample.metric.auc));
    expect(markup).toContain('data-shift="worst-subsample"');
    expect(markup).toContain('A stress test, not a forecast');
  });

  it('conformal coverage marks the window below its target and labels alpha a convention', () => {
    const markup = html(<ConformalView sel={sShift} />);
    const c = shift.outputs.synthetic_shift.label_free.conformal;
    for (const w of c.coverage_by_window) expect(markup).toContain(`data-window="${w.window}" data-below-target="${w.coverage < c.target_coverage}"`);
    expect(markup).toContain('data-label="convention"');
    expect(markup).toContain('a convention');
  });

  it('CBPE is an estimate with its four assumptions and is never called measured', () => {
    const markup = html(<CbpeView sel={sShift} />);
    expect(markup).toContain('data-label="estimate"');
    const e = shift.outputs.synthetic_shift.label_free.cbpe;
    expect(markup).toContain(f3(e.estimated_auc));
    expect(markup.match(/data-assumption="/g)?.length).toBe(4);
    expect(markup).toContain('never a measurement');
  });

  it('the perturbation curve gives each scale, the preset scale and the tolerance named a convention', () => {
    const markup = html(<PerturbationView sel={sPert} />);
    for (const r of pert.outputs.rows) expect(markup).toContain(`data-eps="${r.eps}" data-finding="${r.finding}" data-preset="${r.eps === pert.outputs.preset_eps}"`);
    expect(markup).toContain('Tolerance (convention)');
    const odd = clone(pert);
    odd.outputs.rows[1].finding = true;
    expect(html(<PerturbationView sel={selOf(odd)} />)).toContain('finding at the preset scale');
  });

  it('the seed sweep gives the dispersion of the AUC, the grades changed and the top-four reason overlap', () => {
    const markup = html(<SeedsView sel={sSeeds} />);
    const r = seeds.outputs.rows[0];
    expect(markup).toContain(`data-rung="${r.rung}"`);
    expect(markup).toContain(formatNumber(r.auc.sd, 'en', { decimals: 4 }));
    expect(markup).toContain(`data-top-k="${r.reason_code_overlap.top_k}"`);
    expect(markup).toContain('convention');
  });

  it('the explainer agreement gives the rank correlation, and a null one says why', () => {
    const markup = html(<ExplainerView sel={sSeeds} />);
    expect(markup).toContain(f3(seeds.outputs.explainer_agreement[0].rank_correlation as number));
    expect(markup).toContain('data-feature="PAY_0"');
    const odd = clone(seeds);
    Object.assign(odd.outputs.explainer_agreement[0], { rank_correlation: null, reason_if_null: 'Fewer than three features carry an effect curve.' });
    const m2 = html(<ExplainerView sel={selOf(odd)} />);
    expect(m2).toContain('data-rank-null="true"');
    expect(m2).toContain('Fewer than three features carry an effect curve.');
  });

  it('the leakage screen shows the four screens, the limits as conventions and whether the planted leak was caught', () => {
    const markup = html(<LeakageView sel={sLeak} />);
    for (const k of ['temporal', 'single', 'overlap', 'resemblance']) expect(markup).toContain(`data-screen="${k}"`);
    expect(markup).toContain('data-caught="true"');
    expect(markup).toContain('data-screen="single" data-raised="true"');
    expect(markup).toContain('data-screen="temporal" data-raised="false"');
    expect(markup).toContain('convention');
    const odd = clone(leak);
    odd.outputs.caught = false;
    expect(html(<LeakageView sel={selOf(odd)} />)).toContain('NOT caught');
  });

  it('the fairness battery is labelled evidence on the Taiwan model, one row per attribute, never a compliance statement', () => {
    const markup = html(<FairnessView sel={sSeeds} />);
    expect(markup).toContain('data-label="labelled-fairness-battery"');
    expect(markup).toContain('not a compliance statement');
    for (const a of ['sex', 'age', 'marital_status']) expect(markup).toContain(`data-attribute="${a}"`);
    expect(html(<FairnessView sel={{ ...sSeeds, test: 'fair.auc_by_group' }} />)).toContain('data-test="fair.auc_by_group"');
    expect(html(<FairnessView sel={sShock} />)).toContain('data-state="unavailable"');
  });

  it('the decision-flip impact gives the share per shift and the cut-off as a convention', () => {
    const markup = html(<DecisionFlipView sel={sShift} />);
    const d = shift.outputs.impact_detail;
    expect(markup).toContain(`data-shift="${d.rows[0].shift_id}"`);
    expect(markup).toContain(formatNumber(d.rows[0].flip_share, 'en', { percent: true, decimals: 1 }));
    expect(markup).toContain('data-status="convention"');
    expect(markup).toContain('data-label="decision-flip"');
  });

  it('the variants table gives one row per kind with its headline, and the SGCD notice once', () => {
    const variants = [shock, shift, seeds, pert, leak].map((v) => ({ id: v.variant_id, title: { en: v.variant_id, es: v.variant_id }, v: v as unknown as VariantArtifact<S['c20Outputs']> }));
    const markup = html(<C20VariantsTable variants={variants} onPick={() => undefined} current={shock.variant_id} />);
    for (const k of ['shock', 'shift', 'seeds', 'perturbation', 'leakage']) expect(markup).toContain(`data-kind="${k}"`);
    expect(markup).toContain(PROHIBITED);
    expect(markup.match(/data-notice="sgcd"/g)?.length).toBe(1);
  });

  it('the context names the data and the model, the named parameters as conventions and the SGCD commit', () => {
    const markup = html(<C20ContextView sel={sShock} />);
    expect(markup).toContain('data-dataset="sgcd"');
    expect(markup).toContain('data-sgcd-commit="8403fa9048f7159d51a0cec5a2d9a2e9712662bd"');
    expect(markup).toContain('data-parameter="perturbation_tolerance"');
    expect(markup).toContain('data-status="convention"');
    expect(markup).toContain('data-fixture="true"');
  });

  it('renders in Spanish with Spanish words and no decimal point in a number', () => {
    setLang('es');
    const markup = [DegradationView, DriftView].map((V) => html(<V sel={sShock} />)).join('') + html(<LeakageView sel={sLeak} />) + html(<FairnessView sel={sSeeds} />);
    expect(markup).toContain('Cambio del AUC');
    expect(markup).toContain(f3(shock.outputs.shipped.rows[0].performance.auc, 'es'));
    expect(markup).not.toMatch(/>\d\.\d{3}</);
    expect(markup).toContain('no una declaración de cumplimiento');
  });

  it('a changed fixture field changes the markup: the views read the document and nothing else', () => {
    const odd = clone(shock);
    odd.outputs.shipped.rows[0].performance.auc = 0.7123;
    expect(html(<DegradationView sel={selOf(odd)} />)).toContain(f3(0.7123));
    expect(html(<DegradationView sel={sShock} />)).not.toContain(f3(0.7123));
  });
});
