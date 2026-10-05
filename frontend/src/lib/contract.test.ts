// T11: the committed artifacts against the web's declared contract, in both directions, types included.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { conform, INDEX, MANIFEST, SCHEMAS, TRACE, TRACE_SUMMARY, type CaseIndex, type CaseManifest } from './contract.types';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = (rel: string): unknown => JSON.parse(readFileSync(new URL(rel, derived), 'utf8'));

describe('CONTRACT 2: the committed artifacts are exactly what the web declares', () => {
  const index = read('manifests/index.json') as CaseIndex;
  it('the index conforms and names a baked default case', () => {
    expect(conform(index, { object: INDEX })).toEqual([]);
    expect(index.schema).toBe(SCHEMAS.index);
    expect(index.n_cases).toBe(index.cases.length);
    expect(index.cases.map((c) => c.case_id)).toContain(index.default_case);
  });
  for (const entry of index.cases) {
    it(`${entry.case_id}: manifest and trace conform`, () => {
      const m = read(entry.manifest_path) as CaseManifest;
      expect(conform(m, { object: MANIFEST })).toEqual([]);
      expect(m.schema).toBe(SCHEMAS.manifest);
      expect(m.case_id).toBe(entry.case_id);
      expect(conform(read(m.artifact.path), { object: TRACE })).toEqual([]);
      // the bake enforces the expected ranges; the committed summary must lie inside them
      const s = (read(m.artifact.path) as { summary: Record<string, number> }).summary;
      for (const [metric, [lo, hi]] of Object.entries(m.expect)) {
        expect(s[metric]).toBeGreaterThanOrEqual(lo - 0.005);
        expect(s[metric]).toBeLessThanOrEqual(hi + 0.005);
      }
    });
  }
  it('the checker fails on a drifted document: a boolean is not a number, and extra and missing keys are named', () => {
    const problems = conform({ peak_I: true, t_peak: 3, extra: 1 }, { object: TRACE_SUMMARY }).join('\n');
    expect(problems).toMatch(/peak_I: expected a finite number/);
    expect(problems).toMatch(/extra: written by the pipeline, not declared/);
    expect(problems).toMatch(/attack_rate: declared by the web, not written/);
  });
});
