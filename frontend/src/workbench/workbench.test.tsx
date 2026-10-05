// CT-112 to CT-114: the App's instrument, rendered on the server from the committed artifacts. The six groups in
// their order; a lane badge on every view of every group; the Context naming the sources, their licence classes and
// the truth status of every variant.
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { describe, expect, it } from 'vitest';
import type { CaseIndex, CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { COMMITTED } from '../lib/policy';
import { ContextView } from './ContextView';
import { FindingsView } from './FindingsView';
import { ImpactView } from './ImpactView';
import { defaultChallenger, type Selection } from './model';
import { EbmView, GbmView, LadderView, PenalisedView, ScorecardView, TabPfnView } from './ModelViews';
import { BatteryView, CalibrationView, DiscriminationView, GroupsView, StabilityView } from './ValidationViews';
import { Workbench } from './Workbench';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const html = (el: ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);

const index = read<CaseIndex>('manifests/index.json');

function selections(): Array<{ label: string; sel: Selection }> {
  const out: Array<{ label: string; sel: Selection }> = [];
  for (const entry of index.cases) {
    const manifest = read<CaseManifest>(entry.manifest_path);
    for (const a of manifest.artifacts.filter((x) => x.role === 'variant')) {
      const variant = read<VariantArtifact>(a.path);
      const models = read<ModelsArtifact>(a.models_ref as string);
      out.push({
        label: `${manifest.case_id}/${a.variant_id}`,
        sel: { data: { manifest, variant, models }, challenger: defaultChallenger(variant), alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 },
      });
    }
  }
  return out;
}

/** Every PlotCard of the markup, with whether its head carries a lane badge. */
function cards(markup: string): Array<{ head: string; lane: boolean }> {
  return markup
    .split('class="caos-plot-head"')
    .slice(1)
    .map((rest) => {
      const head = rest.slice(0, rest.indexOf('</figcaption>'));
      return { head, lane: /data-lane="(live|replay|offline)"/.test(head) };
    });
}

describe('the App instrument', () => {
  it('the instrument groups are the six questions, in order', () => {
    const markup = html(<Workbench />);
    const labels = ['Model', 'Validation', 'Impact', 'Findings', 'Variants', 'Context'];
    const at = labels.map((l) => markup.indexOf(`>${l}<`));
    expect(at.every((i) => i >= 0), `missing a group: ${labels.filter((_, k) => at[k] < 0).join(', ')}`).toBe(true);
    expect([...at].sort((a, b) => a - b)).toEqual(at);
  });

  const all = selections();
  const views: Array<[string, (p: { sel: Selection | null }) => ReactElement]> = [
    ['Ladder', LadderView],
    ['Scorecard', ScorecardView],
    ['EBM', EbmView],
    ['GBM', GbmView],
    ['L1 and PLTR', PenalisedView],
    ['Battery', BatteryView],
    ['Calibration', CalibrationView],
    ['Discrimination', DiscriminationView],
    ['Stability', StabilityView],
    ['By group', GroupsView],
    ['Impact', ImpactView],
    ['Findings', FindingsView],
    ['Context', ContextView],
  ];
  for (const { label, sel } of all) {
    it(`every view carries its lane: ${label}`, () => {
      for (const [name, View] of views) {
        const found = cards(html(<View sel={sel} />));
        expect(found.length, `${label} ${name}: no view rendered`).toBeGreaterThan(0);
        for (const c of found) expect(c.lane, `${label} ${name}: a view without its lane`).toBe(true);
      }
      if (sel.data.models.model.some((m) => m.id === 'P5-tabpfn')) {
        const tab = html(<TabPfnView sel={sel} />);
        expect(tab).toContain('Prior Labs License');
      }
    });
  }

  for (const { label, sel } of all.filter((s) => s.label.endsWith('/holdout') || s.label.endsWith('/german-twin'))) {
    it(`context names sources, licences and truth status: ${label}`, () => {
      const markup = html(<ContextView sel={sel} />);
      const m = sel.data.manifest;
      for (const id of m.sources) {
        const s = m.source_details[id];
        expect(markup).toContain(s.name.replace(/&/g, '&amp;'));
        expect(markup).toContain(`data-licence-class="${s.class}"`);
        expect(markup).toContain(s.licence.replace(/&/g, '&amp;').replace(/"/g, '&quot;'));
      }
      for (const a of m.artifacts.filter((x) => x.role === 'variant')) expect(markup).toContain(`data-truth="${a.truth_status}"`);
    });
  }
});
