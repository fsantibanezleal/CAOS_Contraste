// CT-309: the C22 instrument, rendered on the server from the committed artifacts. Every view of every family carries
// its lane; the groups are the six questions in order; the Context names the papers, their licence classes, the
// generators and each family's truth status; the rail's read-out changes with every control of both sections.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { COMMITTED } from '../lib/policy';
import { START, useC22Instrument } from './c22/instrument';
import { isC22, type C22Sel } from './c22/selection';
import {
  C22ContextView,
  C22FindingsView,
  EstimatorsView,
  GeneratorsView,
  LiveCalculatorView,
  PValuesView,
  PaperView,
  PortfolioReadout,
  PowerView,
  RatesTableView,
  SizeView,
  SpecimenView,
  familyCell,
} from './c22/Views';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);

const manifest = read<CaseManifest>('manifests/C22.json');
const cases: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: a.variant_id, data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));

const base = (data: CaseData): C22Sel => ({ data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } });
const variantOf = (data: CaseData) => {
  const v = data.variant as VariantArtifact<unknown>;
  if (!isC22(v)) throw new Error(`${v.variant_id} is not a C22 family`);
  return v;
};

function cards(markup: string): Array<{ lane: boolean }> {
  return markup
    .split('class="caos-plot-head"')
    .slice(1)
    .map((rest) => ({ lane: /data-lane="(live|replay|offline)"/.test(rest.slice(0, rest.indexOf('</figcaption>'))) }));
}

type View = (sel: C22Sel) => ReactElement;
const COMMON: Array<[string, View]> = [
  ['Generators', (sel) => <GeneratorsView sel={sel} />],
  ['One report', (sel) => <SpecimenView sel={sel} />],
  ['Impact', (sel) => <LiveCalculatorView sel={sel} />],
  ['Findings', (sel) => <C22FindingsView sel={sel} />],
  ['Context', (sel) => <C22ContextView sel={sel} />],
];
const NULL_VIEWS: Array<[string, View]> = [
  ['Size', (sel) => <SizeView sel={sel} />],
  ['p-values', (sel) => <PValuesView sel={sel} />],
  ['Estimators', (sel) => <EstimatorsView sel={sel} />],
];
const DEFECT_VIEWS: Array<[string, View]> = [
  ['Power', (sel) => <PowerView sel={sel} />],
  ['Rates', (sel) => <RatesTableView sel={sel} />],
];

function Groups({ data }: { data: CaseData }) {
  const inst = useC22Instrument(data, () => undefined);
  return (
    <p>
      {inst
        ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') +
          ` rail:${inst.rail.map((r) => r.id).join(',')}`
        : 'none'}
    </p>
  );
}

describe('the C22 instrument', () => {
  it('has the eight families of the design, the null first', () => {
    expect(cases.map((c) => c.id)).toEqual(['null', 'miscalibration', 'clustering', 'drift', 'discrimination-decay', 'leakage', 'broken-monotonicity', 'concentration']);
  });

  it('the groups are the six questions, in order, and the rail has two sections', () => {
    for (const c of cases) {
      const markup = html(<Groups data={c.data} />);
      expect(markup).toContain('Model|Validation|Impact|Findings|Variants');
      expect(markup).toContain('rail:portfolio,tests');
    }
  });

  for (const c of cases) {
    it(`every view carries its lane: ${c.id}`, () => {
      const v = variantOf(c.data);
      const sel = base(c.data);
      const views = [...COMMON, ...(v.outputs.ladder === null ? NULL_VIEWS : DEFECT_VIEWS), ...(v.outputs.golden.length ? ([['Papers', (s: C22Sel) => <PaperView sel={s} />]] as Array<[string, View]>) : [])];
      for (const [name, render] of views) {
        const found = cards(html(render(sel)));
        expect(found.length, `${c.id} ${name}: no view rendered`).toBeGreaterThan(0);
        for (const card of found) expect(card.lane, `${c.id} ${name}: a view without its lane`).toBe(true);
      }
    });

    it(`every panel of the family is drawn at once: ${c.id}`, () => {
      const v = variantOf(c.data);
      const markup = html(v.outputs.ladder === null ? <PValuesView sel={base(c.data)} /> : <PowerView sel={base(c.data)} />);
      const drawn = v.outputs.panels.filter((p) => v.outputs.ladder !== null || v.outputs.simulations.some((s) => s.panel === p.id && s.p_histogram));
      for (const p of drawn) expect(markup, `${c.id}: panel ${p.id} not drawn`).toContain(`data-panel="${p.id}"`);
    });
  }

  it('the Impact group is live and every replayed view is replay', () => {
    const c = cases[0];
    const markup = html(<LiveCalculatorView sel={base(c.data)} />);
    expect(markup).toContain('data-lane="live"');
    expect(html(<SizeView sel={base(c.data)} />)).toContain('data-lane="replay"');
  });

  it('the context names the papers, their licence classes, the generators and the truth status', () => {
    for (const c of cases) {
      const markup = html(<C22ContextView sel={base(c.data)} />);
      for (const id of manifest.sources) {
        expect(markup).toContain(`data-licence-class="${manifest.source_details[id].class}"`);
      }
      expect(markup).toContain('data-licence-class="generator"');
      expect(markup).toContain(c.data.variant.provenance.truth_status);
    }
  });

  it('every rail read-out changes when its controls move', () => {
    const s0 = base(cases[0].data);
    const portfolio = (p: Partial<C22Sel['portfolio']>) => ({ ...s0, portfolio: { ...s0.portfolio, ...p } });
    const at = (sel: C22Sel) => html(<PortfolioReadout sel={sel} />);
    expect(at(s0)).not.toBe(at(portfolio({ n: 5000 })));
    expect(at(s0)).not.toBe(at(portfolio({ pd: 0.03 })));
    expect(at(s0)).not.toBe(at(portfolio({ ratio: 1.5 })));
    expect(at(s0)).not.toBe(at(portfolio({ rhoTrue: 0.1 })));
    expect(at(s0)).not.toBe(at(portfolio({ rhoAssumed: 0.24 })));
    expect(at(s0)).not.toBe(at({ ...s0, level: 0.01 }));
  });

  it('the detection matrix tells power from false alarms', () => {
    const fam = (id: string) => variantOf(cases.find((c) => c.id === id)!.data);
    // the PDs are right under clustering: a rejection is a false alarm
    expect(familyCell(fam('clustering'), 'pd.binomial', 'p<0.05')?.kind).toBe('size');
    expect(familyCell(fam('miscalibration'), 'pd.binomial', 'p<0.05')?.kind).toBe('power');
    // the swap of two grades is a defect on the panel's own axis
    expect(familyCell(fam('broken-monotonicity'), 'pd.default_profile', 'p<0.05')?.kind).toBe('power');
    // decay's AUC test is read on the ECB panel, not on the development panel where nothing changed
    const decay = familyCell(fam('discrimination-decay'), 'disc.auc_vs_initial', 'p<0.05');
    expect(decay?.kind).toBe('power');
    expect(decay?.rate).toBeGreaterThan(0.9);
    // drift moves the population, not the calibration of a right model
    expect(familyCell(fam('drift'), 'pd.hosmer_lemeshow', 'p<0.05')?.kind).toBe('size');
    expect(familyCell(fam('drift'), 'stability.psi', 'p<0.05')?.kind).toBe('power');
  });

  it('the size read-out says size at a ratio of one and power above it', () => {
    const s0 = base(cases[0].data);
    expect(html(<PortfolioReadout sel={s0} />)).toMatch(/Size \(exact\)/);
    expect(html(<PortfolioReadout sel={{ ...s0, portfolio: { ...s0.portfolio, ratio: 2 } }} />)).toMatch(/Power \(exact\)/);
  });
});
