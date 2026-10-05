// T11: the committed artifacts against the web's declared contract, in both directions, types included.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  conform,
  CONTRACT_INDEX,
  CONTRACT_SCHEMA,
  FAMILY_CONTRACT,
  INDEX,
  MANIFEST,
  SCHEMAS,
  TRACE,
  TRACE_SUMMARY,
  type CaseIndex,
  type CaseManifest,
  type ContractIndex,
  type FamilyContract,
} from './contract.types';

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

describe('CONTRACT 1: the exported family contracts are exactly what the web declares', () => {
  const index = read('contract/index.json') as ContractIndex;
  it('the index conforms and lists the eight families', () => {
    expect(conform(index, { object: CONTRACT_INDEX })).toEqual([]);
    expect(index.schema).toBe(CONTRACT_SCHEMA);
    expect(index.families.map((f) => f.family).sort()).toEqual(
      ['balance_sheet', 'curve', 'loan_panel', 'loss_events', 'macro_path', 'market_series', 'rating_history', 'scored_sample'],
    );
  });
  for (const entry of index.families) {
    it(`${entry.family}: the declaration conforms, with typed kinds and policies`, () => {
      const fam = read(`contract/${entry.path}`) as FamilyContract;
      expect(conform(fam, { object: FAMILY_CONTRACT })).toEqual([]);
      expect(fam.family).toBe(entry.family);
      for (const f of fam.fields) {
        expect(['str', 'int', 'float', 'flag', 'date', 'enum']).toContain(f.kind);
        expect(['reject', 'flag']).toContain(f.on_missing);
        if (f.kind === 'enum') expect(f.values.length > 0 || f.values_param !== null).toBe(true);
      }
      for (const r of fam.rules) expect(['reject', 'flag', 'exclude']).toContain(r.policy);
    });
  }
  it('a nullable bound accepts null and refuses a string', () => {
    expect(conform(null, { nullable: 'number' })).toEqual([]);
    expect(conform('0', { nullable: 'number' }).join('')).toMatch(/expected a finite number/);
  });
});
