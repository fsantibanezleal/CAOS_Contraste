// U16-F9c (fix round 3, the partial R2b review of C22, report c22), on every committed variant: a second p-value curve of one test
// is named by where its null holds, never by the key's suffix; the one-report view writes the generator configuration as code.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { render, textOf } from '../c03/u16f2-kit';
import { START } from './instrument';
import type { C22Sel } from './selection';
import { PValuesView, SpecimenView } from './Views';

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C22.json');
const variants = manifest.artifacts.filter((a) => a.role === 'variant');
const selOf = (id: string): C22Sel => {
  const entry = variants.find((a) => a.variant_id === id)!;
  const data: CaseData = { manifest, variant: read<VariantArtifact>(entry.path), models: read<ModelsArtifact>(entry.models_ref as string) };
  return { data, alphas: COMMITTED, level: 0.05, portfolio: { ...START } };
};

describe('U16-F9c C22', () => {
  for (const { variant_id: id } of variants) {
    for (const lang of ['en', 'es'] as const) {
      it(`${id} (${lang}): the p-value curves carry no key suffix`, () => {
        expect(textOf(render(<PValuesView sel={selOf(id)} />, lang))).not.toMatch(/\((fitted|dev\d+|n\d+|null-\d+)\)/);
      });
    }

    it(`${id}: the one-report view writes each generator configuration as code`, () => {
      const markup = render(<SpecimenView sel={selOf(id)} />, 'en');
      const t = markup.match(/<table[^>]*data-table="specimen"[\s\S]*?<\/table>/)?.[0] ?? '';
      const rows = (t.match(/<tr>/g) ?? []).length - 1;
      expect((t.match(/<code translate="no">/g) ?? []).length).toBe(rows);
    });
  }
});
