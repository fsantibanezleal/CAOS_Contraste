// CT-104: the web labels every threshold as a policy threshold, and never as a regulatory one unless the artifact
// carries a regulatory paragraph reference for it.
import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseIndex, CaseManifest, TestRow, VariantArtifact } from './contract.types';
import { COMMITTED, regulatoryReference, thresholdLabel, toleranceOf } from './policy';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

describe('threshold labels', () => {
  const index = read<CaseIndex>('manifests/index.json');
  // a planned case has no manifest by design (readiness: case-manifest partial)
  for (const entry of index.cases.filter((c) => existsSync(new URL(c.manifest_path, derived)))) {
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
            // a p-value threshold; the acceptance band of a row lit without a p-value (the lifetime PD backtest); or the
            // tolerance of a row lit by a tolerance on its metric, whose p-value is informative (the C09 CCF bias)
            const kind = toleranceOf(t) !== null ? 'tolerance' : t.p_value === null ? 'band' : 'p';
            const en = { tolerance: /^Policy tolerance, not regulatory/, band: /^Policy acceptance band, not regulatory/, p: /^Policy threshold, not regulatory/ }[kind];
            const es = { tolerance: /^Tolerancia de política, no regulatoria/, band: /^Banda de aceptación de política, no regulatoria/, p: /^Umbral de política, no regulatorio/ }[kind];
            expect(label.en).toMatch(en);
            expect(label.en).toContain(t.policy_version);
            expect(label.es).toMatch(es);
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
