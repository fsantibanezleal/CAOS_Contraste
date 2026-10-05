// T11 and CT-004: the committed artifacts against the web's declared contract, in both directions, types included.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  conform,
  CONTRACT_INDEX,
  CONTRACT_SCHEMA,
  EBM_EXPORT,
  FAMILY_CONTRACT,
  INDEX,
  MANIFEST,
  MODELS,
  MODELS_ENTRY,
  SCHEMAS,
  SCORECARD_DETAILS,
  VARIANT,
  VARIANT_ENTRY,
  type CaseIndex,
  type CaseManifest,
  type ContractIndex,
  type FamilyContract,
  type ModelsArtifact,
  type VariantArtifact,
} from './contract.types';

const derived = new URL('../../../data/derived/', import.meta.url);
const read = (rel: string): unknown => JSON.parse(readFileSync(new URL(rel, derived), 'utf8'));

describe('CONTRACT 2: the committed artifacts are exactly what the web declares', () => {
  const index = read('manifests/index.json') as CaseIndex;
  it('the index conforms, names a baked default case and declares the contract files', () => {
    expect(conform(index, { object: INDEX })).toEqual([]);
    expect(index.schema).toBe(SCHEMAS.index);
    expect(index.n_cases).toBe(index.cases.length);
    expect(index.cases.map((c) => c.case_id)).toContain(index.default_case);
    expect(index.files).toContain('contract/index.json');
  });
  for (const entry of index.cases) {
    const m = read(entry.manifest_path) as CaseManifest;
    it(`${entry.case_id}: the manifest conforms, entry by entry`, () => {
      expect(conform(m, { object: MANIFEST })).toEqual([]);
      expect(m.schema).toBe(SCHEMAS.manifest);
      expect(m.case_id).toBe(entry.case_id);
      for (const a of m.artifacts) {
        const kind = a.role === 'models' ? MODELS_ENTRY : VARIANT_ENTRY;
        expect(conform(a, { object: kind }), `${a.variant_id}`).toEqual([]);
      }
      const variants = m.artifacts.filter((a) => a.role === 'variant').map((a) => a.variant_id);
      expect(variants).toContain(m.default_variant);
    });
    for (const a of m.artifacts) {
      it(`${entry.case_id}/${a.variant_id}: the ${a.role} artifact conforms`, () => {
        const doc = read(a.path);
        if (a.role === 'models') {
          expect(conform(doc, { object: MODELS })).toEqual([]);
          const models = doc as ModelsArtifact;
          expect(models.schema).toBe(SCHEMAS.models);
          const sc = models.model.find((x) => x.id === 'P1-scorecard');
          if (sc) expect(conform(sc.details, { object: SCORECARD_DETAILS })).toEqual([]);
          const ebm = models.model.find((x) => x.id === 'P3-ebm');
          if (ebm) expect(conform((ebm.details as { export: unknown }).export, { object: EBM_EXPORT })).toEqual([]);
        } else {
          expect(conform(doc, { object: VARIANT })).toEqual([]);
          const v = doc as VariantArtifact;
          expect(v.schema).toBe(SCHEMAS.variant);
          expect(v.variant_id).toBe(a.variant_id);
          expect(v.provenance.truth_status).toBe(a.truth_status);
        }
      });
    }
  }
  it('the checker fails on a drifted document: a boolean is not a number, and extra and missing keys are named', () => {
    const problems = conform({ n: true, pd: 3, extra: 1 }, { object: { n: 'integer', pd: 'number', dr: 'number' } }).join('\n');
    expect(problems).toMatch(/n: expected an integer/);
    expect(problems).toMatch(/extra: written by the pipeline, not declared/);
    expect(problems).toMatch(/dr: declared by the web, not written/);
  });
  it('anyOf accepts one of its kinds, and json accepts any JSON value', () => {
    expect(conform('A11', { anyOf: ['number', 'string'] })).toEqual([]);
    expect(conform(true, { anyOf: ['number', 'string'] }).join('')).toMatch(/matches none/);
    expect(conform({ any: [1, 'x', null] }, 'json')).toEqual([]);
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
