// U16-F4 (the U16-R2 capture review, batch b10): the generator keys of the C22 model view are code, not body words, and the rate chart
// draws its interval ends under the rate (m V22-1, V22-2).
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { START } from './instrument';
import type { C22Sel } from './selection';
import { GeneratorsView } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const entry = manifest.artifacts.find((a) => a.role === 'variant' && a.variant_id === 'null')!;
const data: CaseData = { manifest, variant: read<VariantArtifact>(entry.path), models: read<ModelsArtifact>(entry.models_ref as string) };
const sel: C22Sel = { data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } };

describe('U16-F4 C22', () => {
  it('V22-2: the keys of a generator configuration are written as code in the model view', () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter>
        <GeneratorsView sel={sel} />
      </MemoryRouter>,
    );
    expect(markup).toMatch(/<code translate="no">obligors<\/code>/);
    expect(markup).not.toMatch(/<td class="ct-text">obligors /);
  });
});
