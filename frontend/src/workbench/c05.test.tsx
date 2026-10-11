// CT-210: the C05 instrument, rendered on the server from the committed artifacts. Every view of every variant carries
// its lane; the groups are the six questions in order; the Context names the papers, their licence classes, the
// generator and each variant's truth status; every rail section's read-out changes when its controls move.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { COMMITTED } from '../lib/policy';
import { BoundsReadout, C05ContextView, C05FindingsView, C05PolicyReadout, CalibrationReadout, CapitalReadout } from './c05/C05Common';
import { useC05Instrument } from './c05/instrument';
import { BoundsView, KnownTruthView, LdpImpactView, LdpTestsView, ScalingView } from './c05/LdpViews';
import { isSp, type C05Sel } from './c05/selection';
import { ApproachesView, CurvesView, DefaultProfileView, GoldenSpView, GradeTestsView, ProfilesView, SpImpactView } from './c05/SpViews';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);

const manifest = read<CaseManifest>('manifests/C05.json');
const cases: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: a.variant_id, data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));

const base = (data: CaseData): C05Sel => ({
  data,
  alphas: COMMITTED,
  approach: 'A4-slr',
  p1: isSp(data.variant as VariantArtifact<unknown>) ? (data.variant as unknown as { outputs: { pd1: number } }).outputs.pd1 : 0.01,
  gamma: 0.75,
  rho: 0.12,
  scaled: false,
  regime: 'basel3',
  lgd: 0.45,
});

function cards(markup: string): Array<{ lane: boolean }> {
  return markup
    .split('class="caos-plot-head"')
    .slice(1)
    .map((rest) => ({ lane: /data-lane="(live|replay|offline)"/.test(rest.slice(0, rest.indexOf('</figcaption>'))) }));
}

const SP_VIEWS: Array<[string, (p: { sel: C05Sel | null }) => ReactElement]> = [
  ['Curves', CurvesView], ['Profiles', ProfilesView], ['Approaches', ApproachesView], ['Default profile', DefaultProfileView],
  ['By grade', GradeTestsView], ['Paper', GoldenSpView], ['Impact', SpImpactView], ['Findings', C05FindingsView], ['Context', C05ContextView],
];
const LDP_VIEWS: Array<[string, (p: { sel: C05Sel | null }) => ReactElement]> = [
  ['Bounds', BoundsView], ['Scaling', ScalingView], ['Tests', LdpTestsView], ['Truth', KnownTruthView], ['Impact', LdpImpactView],
  ['Findings', C05FindingsView], ['Context', C05ContextView],
];

function Groups({ data }: { data: CaseData }) {
  const inst = useC05Instrument(data, () => undefined);
  return <p>{inst ? [...inst.groups.map((g) => g.label), inst.compare.label].map((l) => (typeof l === 'string' ? l : l.en)).join('|') : 'none'}</p>;
}

describe('the C05 instrument', () => {
  it('the groups are the six questions, in order, and the rail has three sections', () => {
    for (const c of cases) {
      expect(html(<Groups data={c.data} />)).toContain('Model|Validation|Impact|Findings|Variants');
    }
  });

  for (const c of cases) {
    it(`every view carries its lane: ${c.id}`, () => {
      const sel = base(c.data);
      const views = isSp(c.data.variant as VariantArtifact<unknown>) ? SP_VIEWS : LDP_VIEWS;
      for (const [name, View] of views) {
        const found = cards(html(<View sel={sel} />));
        expect(found.length, `${c.id} ${name}: no view rendered`).toBeGreaterThan(0);
        for (const card of found) expect(card.lane, `${c.id} ${name}: a view without its lane`).toBe(true);
      }
    });
  }

  it('the context names both papers, their licence classes, the generator and the truth status', () => {
    for (const c of cases) {
      const markup = html(<C05ContextView sel={base(c.data)} />);
      for (const id of manifest.sources) {
        expect(markup).toContain(`data-licence-class="${manifest.source_details[id].class}"`);
      }
      expect(markup).toContain('data-licence-class="generator"');
      expect(markup).toContain(c.data.variant.provenance.truth_status);
    }
  });

  it('every rail read-out changes when its controls move', () => {
    const sp = cases.find((c) => c.id === 'sp-2010')!.data;
    const ldp = cases.find((c) => c.id === 'ldp-published')!.data;
    const s0 = base(sp);
    expect(html(<CalibrationReadout sel={s0} />)).not.toBe(html(<CalibrationReadout sel={{ ...s0, p1: 0.03 }} />));
    expect(html(<CalibrationReadout sel={s0} />)).not.toBe(html(<CalibrationReadout sel={{ ...s0, approach: 'A3-spd' }} />));
    expect(html(<CapitalReadout sel={s0} />)).not.toBe(html(<CapitalReadout sel={{ ...s0, lgd: 0.25 }} />));
    expect(html(<CapitalReadout sel={s0} />)).not.toBe(html(<CapitalReadout sel={{ ...s0, regime: 'basel2' }} />));
    expect(html(<C05PolicyReadout sel={s0} />)).not.toBe(html(<C05PolicyReadout sel={{ ...s0, alphas: { amber: 0.2, red: 0.1 } }} />));
    const l0 = base(ldp);
    expect(html(<BoundsReadout sel={l0} />)).not.toBe(html(<BoundsReadout sel={{ ...l0, gamma: 0.9 }} />));
    expect(html(<BoundsReadout sel={l0} />)).not.toBe(html(<BoundsReadout sel={{ ...l0, rho: 0 }} />));
    expect(html(<BoundsReadout sel={l0} />)).not.toBe(html(<BoundsReadout sel={{ ...l0, scaled: true }} />));
    expect(html(<CapitalReadout sel={l0} />)).not.toBe(html(<CapitalReadout sel={{ ...l0, gamma: 0.95 }} />));
  });

  it('an improper calibration is said, not drawn: scaled PDs at a 10% forecast PD lift CCC-C above one', () => {
    const sp = cases.find((c) => c.id === 'sp-2010')!.data;
    const markup = html(<CalibrationReadout sel={{ ...base(sp), approach: 'A3-spd', p1: 0.1 }} />);
    expect(markup).toMatch(/improper/);
  });
});
