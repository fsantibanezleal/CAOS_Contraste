// CT-105: where a live recompute is offered, the live result equals the committed artifact (integer points and
// scores exactly, probabilities and logits within 1e-9), and the live policy reproduces every committed light.
import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import type { CaseIndex, CaseManifest, EbmExport, ModelsArtifact, ScorecardDetails, VariantArtifact } from '../lib/contract.types';
import { bandEvaluated, COMMITTED, lightUnder, ownPolicyEvaluated, PACKAGED_POLICY, relight, thresholdLabel } from '../lib/policy';
import { ebmLogit, scoreScorecard } from './scorer';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

const index = read<CaseIndex>('manifests/index.json');

describe('the live scorers reproduce the pipeline on every committed sample', () => {
  // a planned case has no manifest by design (readiness: case-manifest partial)
  for (const entry of index.cases.filter((c) => existsSync(new URL(c.manifest_path, derived)))) {
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
  // a planned case has no manifest by design (readiness: case-manifest partial)
  for (const entry of index.cases.filter((c) => existsSync(new URL(c.manifest_path, derived)))) {
    const manifest = read<CaseManifest>(entry.manifest_path);
    const variants = manifest.artifacts.filter((x) => x.role === 'variant');
    // a case whose tests are all metric thresholds (C07's regime comparison: no p-value) has no significance alphas
    const statistical = variants.some((a) => read<VariantArtifact>(a.path).tests.some((t) => t.p_value !== null));
    it(`${manifest.case_id}: some variant carries a committed light`, () => {
      if (statistical) expect(variants.some((a) => read<VariantArtifact>(a.path).tests.some((t) => t.alpha_amber !== null))).toBe(true);
    });
    for (const a of variants) {
      it(`${manifest.case_id}/${a.variant_id}`, () => {
        const variant = read<VariantArtifact>(a.path);
        // a variant whose results are measured rates (C04's known-truth families, its papers) carries no test rows;
        // one that carries a statistical test (a p-value) must have lights evaluated under the policy
        const evaluated = variant.tests.filter((t) => t.alpha_amber !== null);
        if (variant.tests.some((t) => t.p_value !== null)) expect(evaluated.length).toBeGreaterThan(0);
        for (const t of variant.tests) {
          if (t.alpha_amber !== null && ownPolicyEvaluated(t)) {
            // a test family's own policy (C11's market back-tests): never the engine's default policy, a packaged battery
            // label of riskvalidation 1.0.0 (the levels in the row), and the committed light reproduced under them
            expect(t.policy_version.startsWith('riskvalidation-default')).toBe(false);
            expect(t.policy_version).toMatch(PACKAGED_POLICY);
            expect(lightUnder(t, { amber: t.alpha_amber, red: t.alpha_red as number })).toBe(t.light);
          } else if (t.alpha_amber !== null) {
            expect(t.alpha_amber).toBe(COMMITTED.amber);
            expect(t.alpha_red).toBe(COMMITTED.red);
          }
          expect(relight(t, COMMITTED)).toBe(t.light);
        }
      });
    }
  }
  it('a row under the own policy of its test family keeps its committed light whatever the rail says, and says so', () => {
    const row = { alpha_amber: 0.1, alpha_red: 0.05, light: 'amber', p_value: 0.07, extras: {},
      policy_version: 'contraste-market-battery-1.0.0; alpha_amber=0.1; alpha_red=0.05' } as never;
    expect(ownPolicyEvaluated(row)).toBe(true);
    expect(relight(row, COMMITTED)).toBe('amber');
    expect(relight(row, { amber: 0.01, red: 0.001 })).toBe('amber');
    expect(lightUnder(row, COMMITTED)).toBe('green');
    expect(thresholdLabel(row, COMMITTED).en).toContain('the policy rail does not change it');
    const product = { ...(row as object), alpha_amber: 0.05, alpha_red: 0.01, light: 'green' } as never;
    expect(ownPolicyEvaluated(product)).toBe(false);
    expect(relight(product, { amber: 0.1, red: 0.05 })).toBe('amber');
    // riskvalidation 1.0.0 writes the packaged label, its levels in the row (D16-17), and `+custom` for other cut points
    for (const label of ['contraste-market-battery 1.0.0', 'contraste-market-battery 1.0.0+custom']) {
      const packaged = { ...(row as object), policy_version: label } as never;
      expect(ownPolicyEvaluated(packaged)).toBe(true);
      expect(relight(packaged, { amber: 0.01, red: 0.001 })).toBe('amber');
      expect(ownPolicyEvaluated({ ...(packaged as object), alpha_amber: 0.05, alpha_red: 0.01 } as never)).toBe(false);
    }
    expect(ownPolicyEvaluated({ ...(row as object), policy_version: 'contraste-market-battery' } as never)).toBe(false);
  });
  it('a stricter red threshold can only turn lights red, never green', () => {
    const row = { alpha_amber: 0.05, alpha_red: 0.01, light: 'amber', p_value: 0.02 } as never;
    expect(relight(row, { amber: 0.05, red: 0.03 })).toBe('red');
    expect(relight(row, { amber: 0.01, red: 0.001 })).toBe('green');
  });
  it('a band-lit row (alphas without a p-value, the lifetime PD backtest) keeps its committed light under any policy', () => {
    const row = { alpha_amber: 0.05, alpha_red: 0.01, light: 'amber', p_value: null, policy_version: 'p' } as never;
    expect(bandEvaluated(row)).toBe(true);
    expect(relight(row, { amber: 0.2, red: 0.1 })).toBe('amber');
    expect(relight(row, { amber: 0.001, red: 0.0001 })).toBe('amber');
    expect(thresholdLabel(row, COMMITTED).en).toMatch(/^Policy acceptance band, not regulatory/);
  });
});
