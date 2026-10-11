// CT-105: where a live recompute is offered, the live result equals the committed artifact (integer points and
// scores exactly, probabilities and logits within 1e-9), and the live policy reproduces every committed light.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseIndex, CaseManifest, EbmExport, ModelsArtifact, ScorecardDetails, VariantArtifact } from '../lib/contract.types';
import { COMMITTED, relight } from '../lib/policy';
import { ebmLogit, scoreScorecard } from './scorer';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

const index = read<CaseIndex>('manifests/index.json');

describe('the live scorers reproduce the pipeline on every committed sample', () => {
  for (const entry of index.cases) {
    const manifest = read<CaseManifest>(entry.manifest_path);
    for (const a of manifest.artifacts.filter((x) => x.role === 'variant')) {
      const variant = read<VariantArtifact>(a.path);
      const sample = variant.outputs.sample;
      if (!sample) continue;
      const models = read<ModelsArtifact>(a.models_ref as string);
      const sc = models.model.find((m) => m.id === 'P1-scorecard')?.details as ScorecardDetails;
      const ebm = (models.model.find((m) => m.id === 'P3-ebm')?.details as { export: EbmExport }).export;
      it(`${manifest.case_id}/${a.variant_id}: scorecard points, scores and PDs`, () => {
        sample.ids.forEach((_, i) => {
          const inputs = Object.fromEntries(Object.entries(sample.inputs).map(([k, v]) => [k, v[i]]));
          const live = scoreScorecard(sc, inputs);
          expect(live.points).toEqual(sample.scorecard_points[i]);
          expect(live.score).toBe(sample.scorecard_score[i]);
          expect(Math.abs(live.pd - sample.scorecard_pd[i])).toBeLessThan(1e-9);
        });
      });
      it(`${manifest.case_id}/${a.variant_id}: EBM additive logits`, () => {
        sample.ids.forEach((_, i) => {
          const inputs = Object.fromEntries(Object.entries(sample.inputs).map(([k, v]) => [k, v[i]]));
          expect(Math.abs(ebmLogit(ebm, inputs).logit - sample.ebm_logit[i])).toBeLessThan(1e-9);
        });
      });
    }
  }
});

describe('the live policy reproduces every committed light under the committed alphas', () => {
  for (const entry of index.cases) {
    const manifest = read<CaseManifest>(entry.manifest_path);
    const variants = manifest.artifacts.filter((x) => x.role === 'variant');
    it(`${manifest.case_id}: some variant carries a committed light`, () => {
      expect(variants.some((a) => read<VariantArtifact>(a.path).tests.some((t) => t.alpha_amber !== null))).toBe(true);
    });
    for (const a of variants) {
      it(`${manifest.case_id}/${a.variant_id}`, () => {
        const variant = read<VariantArtifact>(a.path);
        // a variant whose results are measured rates (C04's known-truth families, its papers) carries no test rows;
        // one that carries them must have lights evaluated under the policy
        const evaluated = variant.tests.filter((t) => t.alpha_amber !== null);
        if (variant.tests.length) expect(evaluated.length).toBeGreaterThan(0);
        for (const t of variant.tests) {
          if (t.alpha_amber !== null) {
            expect(t.alpha_amber).toBe(COMMITTED.amber);
            expect(t.alpha_red).toBe(COMMITTED.red);
          }
          expect(relight(t, COMMITTED)).toBe(t.light);
        }
      });
    }
  }
  it('a stricter red threshold can only turn lights red, never green', () => {
    const row = { alpha_amber: 0.05, alpha_red: 0.01, light: 'amber', p_value: 0.02 } as never;
    expect(relight(row, { amber: 0.05, red: 0.03 })).toBe('red');
    expect(relight(row, { amber: 0.01, red: 0.001 })).toBe('green');
  });
});
