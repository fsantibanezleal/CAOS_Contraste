// U16-R2b (batches c01 and c02, C01): the pipeline's exact figures compare the champion with the pipeline's own challenger, so their
// column names that model whatever the rail picked (c02 B2: picking EBM labelled LightGBM's numbers "P3 EBM"), and the live-figures
// note no longer says the two can differ only in the second decimal (c01 M3: 26.50 % against 27.12 % in drift-severe).
import { readFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../lib/contract.types';
import { COMMITTED } from '../lib/policy';
import { setLang } from './c03/u6-testkit';
import { ImpactView } from './ImpactView';
import { defaultChallenger } from './model';
import { binText } from './ModelViews';

const json = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, import.meta.url), 'utf8')) as T;
const index = json<{ cases: Array<{ case_id: string; manifest_path: string }> }>('../../../data/derived/manifests/index.json');
const manifest = json<CaseManifest>(`../../../data/derived/${index.cases.find((c) => c.case_id === 'C01')!.manifest_path}`);
const a = manifest.artifacts.find((x) => x.role === 'variant' && x.variant_id === 'drift-severe')!;
const variant = json<VariantArtifact>(`../../../data/derived/${a.path}`);
const models = json<ModelsArtifact>(`../../../data/derived/${a.models_ref}`);
const sel = (challenger: string) => ({ data: { manifest, variant, models }, challenger, alphas: COMMITTED, approval: 0.8, lgd: 0.5, applicant: 0 });
const html = (challenger: string) => renderToStaticMarkup(<MemoryRouter><ImpactView sel={sel(challenger) as never} /></MemoryRouter>);
afterEach(() => setLang('en'));

describe('U16-R2b C01 Impact', () => {
  it('c02 B2: with EBM on the rail the pipeline table still names LightGBM, and says it is the pipeline\'s challenger', () => {
    expect(defaultChallenger(variant)).toBe('P4-lightgbm');
    const m = html('P3-ebm');
    const head = m.slice(m.indexOf('Champion, then challenger'), m.indexOf('</thead>', m.indexOf('Champion, then challenger')));
    expect(head).toContain('P4 LightGBM');
    expect(head).not.toContain('P3 EBM');
    expect(m).toContain("the pipeline&#x27;s challenger, not the rail&#x27;s");
  });
  it('c01 M3: the note on the live figures states the gap can be a point or more', () => {
    const m = html('P4-lightgbm');
    expect(m).not.toContain('second decimal');
    expect(m).toContain('can differ by a point or more');
  });
});

describe('U16-R2b C01 German twin (c01 B2)', () => {
  it('names the UCI codes of a scorecard bin by the codebook, in both languages, and leaves an interval as it is', () => {
    expect(binText('{A14}', 'en')).toBe('no checking account');
    expect(binText('{A14}', 'es')).toBe('sin cuenta corriente');
    expect(binText('{A43, A44, A48}', 'en')).toBe('radio or television or domestic appliances or retraining');
    expect(binText('{A33}', 'es')).toBe('atrasos en pagos pasados');
    // an interval keeps its form (its numbers formatted, never read as codes)
    expect(binText('[1000.0, 2000.0)', 'en')).toBe('[1000.0, 2000.0)');
  });
  it('every code of the committed German models document has a meaning', () => {
    const m = json<{ model: Array<{ details?: { points_table?: Array<{ bin: string }> } }> }>('../../../data/derived/C01/models-german.json');
    const bins = m.model.flatMap((x) => x.details?.points_table ?? []).map((r) => r.bin).filter((b) => b.startsWith('{'));
    expect(bins.length).toBeGreaterThan(20);
    for (const b of bins) expect(binText(b, 'en'), b).not.toMatch(/A\d+/);
  });
});
