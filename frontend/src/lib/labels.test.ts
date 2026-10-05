// CT-104: the web labels every threshold as a policy threshold, and never as a regulatory one unless the artifact
// carries a regulatory paragraph reference for it.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseIndex, CaseManifest, TestRow, VariantArtifact } from './contract.types';
import { COMMITTED, regulatoryReference, thresholdLabel } from './policy';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

describe('threshold labels', () => {
  const index = read<CaseIndex>('manifests/index.json');
  for (const entry of index.cases) {
    const manifest = read<CaseManifest>(entry.manifest_path);
    for (const a of manifest.artifacts.filter((x) => x.role === 'variant')) {
      it(`${manifest.case_id}/${a.variant_id}: every threshold reads as policy`, () => {
        const variant = read<VariantArtifact>(a.path);
        for (const t of variant.tests) {
          const label = thresholdLabel(t, COMMITTED);
          if (regulatoryReference(t)) continue;
          expect(label.en.toLowerCase()).not.toMatch(/^regulatory/);
          expect(label.es.toLowerCase()).not.toMatch(/^umbral regulatorio/);
          if (t.alpha_amber !== null) {
            expect(label.en).toMatch(/^Policy threshold, not regulatory/);
            expect(label.en).toContain(t.policy_version);
            expect(label.es).toMatch(/^Umbral de política, no regulatorio/);
          }
        }
      });
    }
  }
  it('only a row with a regulatory reference reads as regulatory', () => {
    const base = { alpha_amber: 0.05, alpha_red: 0.01, light: 'green', p_value: 0.3, policy_version: 'p 1', extras: {} } as unknown as TestRow;
    expect(thresholdLabel(base, COMMITTED).en).toMatch(/^Policy threshold/);
    const reg = { ...base, extras: { regulatory_threshold_reference: 'MAR99.28' } } as TestRow;
    expect(thresholdLabel(reg, COMMITTED).en).toBe('Regulatory threshold (MAR99.28)');
  });
});
