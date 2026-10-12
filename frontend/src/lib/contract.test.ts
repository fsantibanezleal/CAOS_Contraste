// T11 and CT-004: the committed artifacts against the web's declared contract, in both directions, types included.
// Then the same artifacts against the JSON Schema files of docs/contracts/schemas (catalog.md), the consumer side of
// every document row: the same discovery rule as tests/contracts/contract_schemas.py picks the schema of a document.
import Ajv2020 from '@redocly/ajv/dist/2020.js'; // already in node_modules (a dependency of openapi-typescript); no runtime dependency is added
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  conform,
  CONTRACT_INDEX,
  CONTRACT_SCHEMA,
  EBM_EXPORT,
  FAMILY_CONTRACT,
  INDEX,
  MANIFEST,
  MODELS_ENTRY,
  SCHEMAS,
  SCORECARD_DETAILS,
  VARIANT_ENTRY,
  modelsKind,
  variantKind,
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
          expect(conform(doc, { object: modelsKind(doc as { case_id?: string; fit_id?: string }) })).toEqual([]);
          const models = doc as ModelsArtifact;
          expect(models.schema).toBe(SCHEMAS.models);
          const sc = models.model.find((x) => x.id === 'P1-scorecard');
          if (sc) expect(conform(sc.details, { object: SCORECARD_DETAILS })).toEqual([]);
          const ebm = models.model.find((x) => x.id === 'P3-ebm');
          if (ebm) expect(conform((ebm.details as { export: unknown }).export, { object: EBM_EXPORT })).toEqual([]);
        } else {
          expect(conform(doc, { object: variantKind(doc as { outputs?: { kind?: string } }) })).toEqual([]);
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

// --- the JSON Schema files: every committed document validates against exactly one, both ways ------------------------

const repo = fileURLToPath(new URL('../../../', import.meta.url));
const schemasDir = join(repo, 'docs', 'contracts', 'schemas');

type Json = Record<string, unknown>;
const loadJson = (path: string): Json => JSON.parse(readFileSync(path, 'utf8')) as Json;
function walk(dir: string): string[] {
  return readdirSync(dir).sort().flatMap((n) => {
    const full = join(dir, n);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}
const posix = (p: string) => p.split(sep).join('/');
const schemaPaths = walk(schemasDir).filter((p) => p.endsWith('.schema.json'));
const schemaDocs = new Map(schemaPaths.map((p) => [posix(relative(schemasDir, p)).replace(/\.schema\.json$/, ''), loadJson(p)]));

const ajv = new Ajv2020({ strict: false, allErrors: false });
/** A copy with every relative file `$ref` made absolute against the schema's `$id` (this Ajv build does not resolve `..`). */
const absolute = (node: unknown, id: string): unknown => {
  if (Array.isArray(node)) return node.map((x) => absolute(x, id));
  if (node === null || typeof node !== 'object') return node;
  return Object.fromEntries(
    Object.entries(node as Json).map(([k, v]) => [k, k === '$ref' && typeof v === 'string' && !v.startsWith('#') ? new URL(v, id).href : absolute(v, id)]),
  );
};
for (const doc of schemaDocs.values()) ajv.addSchema(absolute(doc, doc.$id as string) as Json);

/** The selectors a schema declares (const of schema, case_id, fit_id, outputs.kind), through allOf and relative refs. */
function selectors(doc: Json, from: string): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  const props = (doc.properties ?? {}) as Record<string, Json>;
  for (const k of ['schema', 'case_id', 'fit_id']) if (props[k] && 'const' in props[k]) out[k] = props[k].const;
  const kind = ((props.outputs?.properties ?? {}) as Record<string, Json>).kind;
  if (kind && 'const' in kind) out['outputs.kind'] = kind.const;
  for (const member of (doc.allOf ?? []) as Json[]) {
    const ref = member.$ref as string | undefined;
    if (ref && !ref.startsWith('#')) {
      const target = posix(join(from.includes('/') ? from.slice(0, from.lastIndexOf('/')) : '', ref.replace(/\.schema\.json$/, '')));
      const norm = target.split('/').reduce<string[]>((acc, p) => (p === '..' ? (acc.pop(), acc) : (acc.push(p), acc)), []).join('/');
      const inner = schemaDocs.get(norm);
      if (inner) Object.assign(out, selectors(inner, norm));
    } else Object.assign(out, selectors(member, from));
  }
  return out;
}
const candidates = [...schemaDocs.entries()]
  .filter(([name]) => !name.endsWith('-envelope'))
  .map(([name, doc]) => ({ name, consts: selectors(doc, name), location: doc['x-location'] as string | undefined }))
  .filter((c) => c.consts.schema !== undefined || c.location !== undefined);

const globToRegExp = (g: string) => new RegExp(`^${g.replace(/[.+^${}()|\\]/g, '\\$&').replace(/\*/g, '[^/]*')}$`);

/** The schema name of a document: the matching candidate with the most selectors; zero or a tie throws. */
function schemaFor(relPath: string, doc: Json): string {
  const outputs = (doc.outputs ?? null) as Json | null;
  const docKind = outputs && typeof outputs === 'object' ? (outputs.kind as string | undefined) : undefined;
  const scored: Array<[number, string]> = [];
  for (const c of candidates) {
    let points = 0;
    if (c.location !== undefined) {
      if (!globToRegExp(c.location).test(relPath)) continue;
      points += 1 + (/[*?[]/.test(c.location) ? 0 : 1);
    }
    let ok = true;
    for (const k of ['schema', 'case_id', 'fit_id']) {
      if (k in c.consts) {
        if (doc[k] !== c.consts[k]) ok = false;
        else points += 1;
      }
    }
    if ('outputs.kind' in c.consts) {
      if (docKind !== c.consts['outputs.kind']) ok = false;
      else points += 1;
    } else if (c.consts.schema === 'contraste.case/v1' && docKind !== undefined) ok = false;
    if (ok) scored.push([points, c.name]);
  }
  if (!scored.length) throw new Error(`${relPath}: matches no schema`);
  const best = Math.max(...scored.map(([s]) => s));
  const top = scored.filter(([s]) => s === best).map(([, n]) => n).sort();
  if (top.length > 1) throw new Error(`${relPath}: matches ${top.length} schemas equally: ${top.join(', ')}`);
  return top[0];
}
const validatorFor = (name: string) => {
  const v = ajv.getSchema(schemaDocs.get(name)!.$id as string);
  if (!v) throw new Error(`no validator for ${name}`);
  return v;
};
const problems = (name: string, doc: unknown): string[] => {
  const v = validatorFor(name);
  return v(doc) ? [] : (v.errors ?? []).map((e) => `${e.instancePath || '$'}: ${e.message}`);
};

const committed = [
  ...walk(join(repo, 'data', 'derived')).filter((p) => p.endsWith('.json')),
  join(repo, 'data-pipeline', 'config', 'sources.json'),
  join(repo, 'data-pipeline', 'config', 'licences.json'),
  join(repo, 'data', 'sources', 'manifest.json'),
];

describe('JSON Schema files: every committed document validates against exactly one, strictly', () => {
  it('there are schemas and documents to cover', () => {
    expect(schemaDocs.size).toBeGreaterThanOrEqual(30);
    expect(committed.length).toBeGreaterThanOrEqual(54);
  });
  for (const path of committed) {
    const rel = posix(relative(repo, path));
    it(`${rel} matches one schema and conforms to it`, () => {
      const doc = loadJson(path);
      const name = schemaFor(rel, doc);
      expect(problems(name, doc), `${rel} against ${name}`).toEqual([]);
    });
  }
  it('a removed key and an unknown key are both refused (plants on in-memory copies)', () => {
    const rel = 'data/derived/manifests/C04.json';
    const doc = loadJson(join(repo, rel));
    const name = schemaFor(rel, doc);
    const removed = structuredClone(doc);
    delete (removed.engine as Json).pipeline;
    expect(problems(name, removed).join('')).toMatch(/pipeline/);
    const added = structuredClone(doc);
    (added.engine as Json).planted = 1;
    expect(problems(name, added).join('')).toMatch(/additional properties/);
    const variantRel = 'data/derived/C05/ldp-published.json';
    const variant = loadJson(join(repo, variantRel));
    const vname = schemaFor(variantRel, variant);
    const withUnknown = structuredClone(variant);
    (withUnknown.outputs as Json).planted = 1;
    expect(problems(vname, withUnknown)).not.toEqual([]);
    const unknownTop = structuredClone(variant);
    unknownTop.planted = 1;
    expect(problems(vname, unknownTop)).not.toEqual([]);
  });
  it('a document of an unknown kind matches no schema', () => {
    expect(() => schemaFor('data/derived/C99/x.json', { schema: 'contraste.case/v1', case_id: 'C99', outputs: { kind: 'nothing' } })).toThrow(/matches no schema/);
  });
  it('the generated OpenAPI document has one component per schema file', () => {
    const openapi = loadJson(join(repo, 'docs', 'contracts', 'api.openapi.json')) as { components: { schemas: Record<string, unknown> } };
    for (const name of schemaDocs.keys()) expect(Object.keys(openapi.components.schemas), name).toContain(name.replace(/\//g, '-'));
  });
});

// The generated types and the descriptors are one contract: these lines fail `tsc` (npm run build) when a schema
// change reaches contract.gen.ts and the descriptors of contract.types.ts do not follow (satisfies Record<keyof ..>).
const _kind: CaseIndex['cases'][number]['kind'] = 'real';
const _light: import('./contract.types').Light = 'amber';
void [_kind, _light];