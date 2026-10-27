// U16-F12f (fix round 5), C22: the p-value panels and the numbered-curves note under them share one flow column (`c22-flow.css`),
// so the grid takes the height left above the note and the card body no longer cuts the note (U16-R4 c26, c27).
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { START } from './instrument';
import type { C22Sel } from './selection';
import { PValuesView } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const variants = manifest.artifacts.filter((a) => a.role === 'variant');

describe('U16-F12f C22 p-value panels', () => {
  it('every family puts its panel grid in the flow column, and the numbered-curves note after the grid inside it', () => {
    let withNote = 0;
    for (const a of variants) {
      const data: CaseData = { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) };
      const sel: C22Sel = { data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } };
      const markup = renderToStaticMarkup(<MemoryRouter><PValuesView sel={sel} /></MemoryRouter>);
      const flow = markup.indexOf('class="ct-c22-flow"');
      if (flow < 0) continue; // a family with no panel prints no grid
      const grid = markup.indexOf('class="ct-panels-fill"', flow);
      expect(grid, a.variant_id).toBeGreaterThan(flow);
      const note = markup.indexOf('data-list="numbered-curves"');
      if (note >= 0) {
        withNote += 1;
        expect(note, a.variant_id).toBeGreaterThan(grid);
        // the note is inside the column: the column's close comes after it
        expect(markup.indexOf('</ul></div>', note), a.variant_id).toBeGreaterThan(note);
      }
    }
    expect(withNote, 'a committed family carries the note').toBeGreaterThan(0);
  });
});
