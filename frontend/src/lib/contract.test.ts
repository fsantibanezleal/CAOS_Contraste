// T11 and CT-004: the committed artifacts against the web's declared contract, in both directions, types included.
// Then the same artifacts against the JSON Schema files of docs/contracts/schemas (catalog.md), the consumer side of
// every document row: the same discovery rule as tests/contracts/contract_schemas.py picks the schema of a document.
import Ajv2020 from '@redocly/ajv/dist/2020.js'; // an exact devDependency (frontend/package.json): no runtime dependency is added
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  conform,
  CONTRACT_INDEX,
  CONTRACT_SCHEMA,
  CONTRACT_SUMMARY,
  EBM_EXPORT,
  FAMILY_CONTRACT,
  GATE,
  INDEX,
  MANIFEST,
  MODEL_RECORD,
  MODEL_SUMMARY,
  MODELS_ENTRY,
  PROVENANCE,
  SCHEMAS,
  SCORECARD_DETAILS,
  TEST_ROW,
  VARIANT_ENTRY,
  modelsKind,
  variantKind,
  type Kind,
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
  // a planned case has no manifest by design (readiness: case-manifest partial); its entry is read by the index test above
  for (const entry of index.cases.filter((c) => existsSync(new URL(c.manifest_path, derived)))) {
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

// Strict: a keyword the validator does not know (or a typo) fails here instead of silently accepting anything. The
// annotation keywords the schema files use are registered, so only an unknown one fails. strictTypes stays off: the
// composed case schemas put `unevaluatedProperties` at a root that gets its `type` from the envelope it references,
// and strictRequired stays off: an `if/then` that requires a key (artifact-entry: models_ref) names it in the parent.
const ajv = new Ajv2020({ strict: true, strictTypes: false, strictRequired: false, allErrors: false });
for (const kw of ['x-location', 'x-discover']) ajv.addKeyword(kw);
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
type Cand = { name: string; consts: Record<string, unknown>; location?: string };
const candidates: Cand[] = [...schemaDocs.entries()]
  .filter(([name]) => !name.endsWith('-envelope'))
  .map(([name, doc]) => ({ name, consts: selectors(doc, name), location: doc['x-location'] as string | undefined }))
  .filter((c) => c.consts.schema !== undefined || c.location !== undefined);

const globToRegExp = (g: string) => new RegExp(`^${g.replace(/[.+^${}()|\\]/g, '\\$&').replace(/\*/g, '[^/]*')}$`);

/** The variant schemas that omit the outputs.kind const, by the case_id const they declare (one per case may). */
function defaultViolations(cands: Cand[]): string[] {
  const byCase = new Map<string, string[]>();
  for (const c of cands) {
    if (c.consts.schema === 'contraste.case/v1' && !('outputs.kind' in c.consts)) {
      const key = String(c.consts.case_id);
      byCase.set(key, [...(byCase.get(key) ?? []), c.name]);
    }
  }
  return [...byCase.entries()].filter(([, names]) => names.length > 1).map(([k, names]) => `case ${k}: more than one variant schema omits the outputs.kind const: ${names.sort().join(', ')}`);
}

/** Schemas under schemas/<case>/ (any folder but common) without a case_id const equal to the folder name upper-cased. */
function caseFolderViolations(cands: Array<{ name: string; consts: Record<string, unknown> }>): string[] {
  return cands
    .filter((c) => c.name.split('/')[0] !== 'common' && c.consts.case_id !== c.name.split('/')[0].toUpperCase())
    .map((c) => `${c.name}: case_id const is ${JSON.stringify(c.consts.case_id)}, expected ${c.name.split('/')[0].toUpperCase()}`);
}

/** The schema name of a document: the matching candidate with the most selectors; zero or a tie throws. */
function schemaFor(relPath: string, doc: Json, cands: Cand[] = candidates): string {
  const bad = defaultViolations(cands);
  if (bad.length) throw new Error(bad.join('; '));
  const outputs = (doc.outputs ?? null) as Json | null;
  const docKind = outputs && typeof outputs === 'object' ? (outputs.kind as string | undefined) : undefined;
  const scored: Array<[number, string]> = [];
  for (const c of cands) {
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

/** The rows of the catalog's first table with a `schema file` and a `status` column. */
function catalogRows(): Array<Record<string, string>> {
  const rows: Array<Record<string, string>> = [];
  let header: string[] | null = null;
  for (const line of readFileSync(join(repo, 'docs', 'contracts', 'catalog.md'), 'utf8').split(/\r?\n/)) {
    if (!line.trimStart().startsWith('|')) {
      if (header && rows.length) break;
      header = null;
      continue;
    }
    const cells = line.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
    if (header === null) header = cells.includes('schema file') && cells.includes('status') ? cells : null;
    else if (!cells.every((c) => /^[:\- ]*$/.test(c))) rows.push(Object.fromEntries(cells.map((c, i) => [header![i], c])));
  }
  return rows;
}

/** Schemas allowed to have no committed document: a catalog row that is `active`, or a document under docs/contracts/fixtures/. */
function exemptFromDocuments(rows: Array<Record<string, string>>, fixtures: string[]): Set<string> {
  const prefix = 'docs/contracts/schemas/';
  const out = new Set(
    rows.filter((r) => r.status?.toLowerCase() === 'active' && r['schema file']?.startsWith(prefix)).map((r) => r['schema file'].slice(prefix.length).replace(/\.schema\.json$/, '')),
  );
  for (const f of fixtures) out.add(schemaFor(posix(relative(repo, f)), loadJson(f)));
  return out;
}
const unusedSchemas = (chosen: Set<string>, selectable: string[], exempt: Set<string>): string[] => selectable.filter((n) => !chosen.has(n) && !exempt.has(n)).sort();

const validatorFor = (name: string) => {
  const v = ajv.getSchema(schemaDocs.get(name)!.$id as string);
  if (!v) throw new Error(`no validator for ${name}`);
  return v;
};
const problems = (name: string, doc: unknown): string[] => {
  const v = validatorFor(name);
  return v(doc) ? [] : (v.errors ?? []).map((e) => `${e.instancePath || '$'}: ${e.message}`);
};

const fixturesDir = join(repo, 'docs', 'contracts', 'fixtures');
const fixtureDocs = existsSync(fixturesDir) ? walk(fixturesDir).filter((p) => p.endsWith('.json')) : [];
const committed = [
  ...walk(join(repo, 'data', 'derived')).filter((p) => p.endsWith('.json')),
  ...fixtureDocs,
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

describe('discovery: one default variant per case, case_id in every case folder, derived exemptions', () => {
  const kindless = (name: string, caseId?: string): Cand => ({ name, consts: { schema: 'contraste.case/v1', ...(caseId ? { case_id: caseId } : {}) } });
  it('the real schemas have at most one default variant per case and a case_id in every case folder', () => {
    expect(defaultViolations(candidates)).toEqual([]);
    const all = [...schemaDocs.entries()].map(([name, doc]) => ({ name, consts: selectors(doc, name) }));
    expect(caseFolderViolations(all)).toEqual([]);
  });
  it('a second kind-less schema for one case fails the selector', () => {
    const rel = 'data/derived/C01/holdout.json';
    expect(() => schemaFor(rel, loadJson(join(repo, rel)), [...candidates, kindless('c01/variant-twin', 'C01')])).toThrow(/more than one variant schema omits/);
  });
  it('a kind-less schema for another case is accepted and changes no committed document', () => {
    const cands = [...candidates, kindless('c06/variant', 'C06')];
    for (const path of committed) {
      const rel = posix(relative(repo, path));
      const doc = loadJson(path);
      expect(schemaFor(rel, doc, cands), rel).toBe(schemaFor(rel, doc));
    }
    expect(schemaFor('data/derived/C06/base.json', { schema: 'contraste.case/v1', case_id: 'C06', outputs: {} }, cands)).toBe('c06/variant');
  });
  it('a schema in a case folder without a case_id const, or with the wrong one, is reported', () => {
    const found = caseFolderViolations([{ name: 'c06/variant-agency', consts: { schema: 'contraste.case/v1' } }, { name: 'c06/models', consts: { case_id: 'C04' } }]);
    expect(found).toHaveLength(2);
    expect(found[0]).toMatch(/^c06\/variant-agency/);
  });
  it('every selectable schema has a committed document, an active catalog row or a fixture (no schema is named by hand)', () => {
    const chosen = new Set(committed.map((p) => schemaFor(posix(relative(repo, p)), loadJson(p))));
    const exempt = exemptFromDocuments(catalogRows(), fixtureDocs);
    expect(unusedSchemas(chosen, candidates.map((c) => c.name), exempt)).toEqual([]);
  });
  it('a schema with neither a document nor an exempting row is reported; an active row or a fixture exempts it', () => {
    const row = (status: string) => [{ 'schema file': 'docs/contracts/schemas/c06/variant.schema.json', status }];
    expect(unusedSchemas(new Set(['c01/variant']), ['c01/variant', 'c06/variant'], exemptFromDocuments(row('real'), []))).toEqual(['c06/variant']);
    expect(unusedSchemas(new Set(), ['c06/variant'], exemptFromDocuments(row('active'), []))).toEqual([]);
    expect(fixtureDocs.length).toBeGreaterThan(0);
    expect([...exemptFromDocuments([], fixtureDocs)]).toContain('common/readiness');
  });
});

// --- the descriptors of contract.types.ts against the schema files, at every nesting level -------------------------

type Shape =
  | { k: 'object'; keys: Record<string, Shape> }
  | { k: 'map'; value: Shape }
  | { k: 'array'; item: Shape }
  | { k: 'prim'; name: 'string' | 'number' | 'integer' | 'boolean' }
  | { k: 'nullable'; inner: Shape }
  | { k: 'union'; options: Shape[] }
  | { k: 'any' };
type Ctx = { doc: Json; id: string };
type Ref = { node: Json; ctx: Ctx };
type Facets = { props: Record<string, Ref[]>; addl?: Ref; patterns: Ref[]; items?: Ref; prefix: Ref[]; types: Set<string>; options: Ref[] };

const schemaByUrl = new Map([...schemaDocs.values()].map((d) => [d.$id as string, d]));
function follow(ref: string, ctx: Ctx): Ref {
  const url = new URL(ref, ctx.id);
  const frag = url.hash.replace(/^#/, '');
  url.hash = '';
  const doc = ref.startsWith('#') ? ctx.doc : schemaByUrl.get(url.href);
  if (!doc) throw new Error(`unresolved $ref ${ref} from ${ctx.id}`);
  let node: unknown = doc;
  for (const part of frag.split('/').filter(Boolean)) node = (node as Json)[decodeURIComponent(part)];
  return { node: node as Json, ctx: { doc, id: doc.$id as string } };
}
const jsType = (v: unknown): string => (v === null ? 'null' : Number.isInteger(v) ? 'integer' : typeof v);

function collect(node: unknown, ctx: Ctx, acc: Facets): void {
  if (node === true || node === undefined || node === null || typeof node !== 'object') return;
  const n = node as Json;
  if (typeof n.$ref === 'string') {
    const t = follow(n.$ref, ctx);
    collect(t.node, t.ctx, acc);
  }
  for (const member of (n.allOf ?? []) as unknown[]) collect(member, ctx, acc);
  // every allOf member that names a property is kept; propShape narrows by a constraint-only member, else the later replaces
  for (const [k, v] of Object.entries((n.properties ?? {}) as Json)) (acc.props[k] ??= []).push({ node: v as Json, ctx });
  if (n.additionalProperties && typeof n.additionalProperties === 'object') acc.addl = { node: n.additionalProperties as Json, ctx };
  for (const v of Object.values((n.patternProperties ?? {}) as Json)) acc.patterns.push({ node: v as Json, ctx });
  for (const v of (n.prefixItems ?? []) as Json[]) acc.prefix.push({ node: v, ctx });
  if (n.items && typeof n.items === 'object') acc.items = { node: n.items as Json, ctx };
  const types = Array.isArray(n.type) ? (n.type as string[]) : typeof n.type === 'string' ? [n.type] : [];
  for (const t of types) acc.types.add(t);
  if ('const' in n) acc.types.add(jsType(n.const));
  for (const v of (n.enum ?? []) as unknown[]) acc.types.add(jsType(v));
  for (const o of [...((n.oneOf ?? []) as Json[]), ...((n.anyOf ?? []) as Json[])]) acc.options.push({ node: o, ctx });
}

/** A constraint-only allOf member: it narrows the fields of a shape another member defines (no type, $ref, allOf, oneOf,
 * anyOf, const or enum of its own), as C10's and C17's `provenance` branch that pins `truth_status` beside the common block. */
const SHAPING = ['type', '$ref', 'allOf', 'oneOf', 'anyOf', 'const', 'enum'];
const constraintOnly = (node: unknown): boolean =>
  typeof node === 'object' && node !== null && !SHAPING.some((k) => k in (node as Json));

/** Narrow `a` by a constraint-only member's shape `b`: objects keep every key of both (narrowed key by key), an unconstrained
 * part never erases a constrained one, and anything else takes the narrower `b`. */
function narrow(a: Shape, b: Shape): Shape {
  if (b.k === 'any') return a;
  if (a.k === 'object' && b.k === 'object') {
    const keys: Record<string, Shape> = { ...a.keys };
    for (const [k, s] of Object.entries(b.keys)) keys[k] = k in keys ? narrow(keys[k], s) : s;
    return { k: 'object', keys };
  }
  return b;
}

/** A property every allOf member may name: a constraint-only member narrows the shape so far, any other later member (a
 * full shape, as C01's outputs `$ref` over the common variant) replaces it. */
const propShape = (refs: Ref[]): Shape =>
  refs.slice(1).reduce((s, r) => (constraintOnly(r.node) ? narrow(s, shapeOf(r.node, r.ctx)) : shapeOf(r.node, r.ctx)), shapeOf(refs[0].node, refs[0].ctx));

/** The element shape of an array: its `items`, else the shape the `prefixItems` (a tuple) share, else a union of them. */
function itemShape(acc: Facets): Shape {
  if (acc.items) return shapeOf(acc.items.node, acc.items.ctx);
  const shapes = acc.prefix.map((r) => shapeOf(r.node, r.ctx));
  const distinct = [...new Map(shapes.map((x) => [JSON.stringify(x), x])).values()];
  return distinct.length === 0 ? { k: 'any' } : distinct.length === 1 ? distinct[0] : { k: 'union', options: distinct };
}

function shapeOf(node: unknown, ctx: Ctx): Shape {
  const acc: Facets = { props: {}, patterns: [], prefix: [], types: new Set(), options: [] };
  collect(node, ctx, acc);
  const nullable = acc.types.has('null') || acc.options.some((o) => (o.node as Json).type === 'null');
  let core: Shape | undefined;
  const live = acc.options.filter((o) => (o.node as Json).type !== 'null');
  if (live.length === 1) core = shapeOf(live[0].node, live[0].ctx);
  else if (live.length > 1) core = { k: 'union', options: live.map((o) => shapeOf(o.node, o.ctx)) };
  if (!core) {
    const types = [...acc.types].filter((t) => t !== 'null');
    const parts: Shape[] = [];
    for (const t of types) {
      if (t === 'object') {
        const keys = Object.keys(acc.props);
        if (keys.length) parts.push({ k: 'object', keys: Object.fromEntries(keys.map((k) => [k, propShape(acc.props[k])])) });
        else if (acc.addl) parts.push({ k: 'map', value: shapeOf(acc.addl.node, acc.addl.ctx) });
        else if (acc.patterns.length) parts.push({ k: 'map', value: shapeOf(acc.patterns[0].node, acc.patterns[0].ctx) });
        else parts.push({ k: 'any' });
      } else if (t === 'array') parts.push({ k: 'array', item: itemShape(acc) });
      else if (t === 'string' || t === 'number' || t === 'integer' || t === 'boolean') parts.push({ k: 'prim', name: t });
    }
    if (!types.length && Object.keys(acc.props).length) parts.push({ k: 'object', keys: Object.fromEntries(Object.entries(acc.props).map(([k, r]) => [k, propShape(r)])) });
    core = parts.length === 1 ? parts[0] : parts.length > 1 ? { k: 'union', options: parts } : { k: 'any' };
  }
  return nullable ? { k: 'nullable', inner: core } : core;
}

/** Every way the descriptor `kind` departs from the schema `shape`: key sets and kinds, at every nesting level. */
function walk2(shape: Shape, kind: Kind, path: string, ignore: string[] = []): string[] {
  if (kind === 'json') return [];
  if (typeof kind === 'object' && 'nullable' in kind) {
    return shape.k === 'nullable' ? walk2(shape.inner, kind.nullable, path, ignore) : [`${path}: descriptor is nullable, the schema is not`];
  }
  if (shape.k === 'nullable') return [`${path}: the schema is nullable, the descriptor is not`];
  if (shape.k === 'any') return [`${path}: the schema is open (any value), the descriptor is not 'json'`];
  if (kind === 'text') {
    const ok = shape.k === 'object' && Object.keys(shape.keys).sort().join() === 'en,es' && Object.values(shape.keys).every((v) => v.k === 'prim' && v.name === 'string');
    return ok ? [] : [`${path}: descriptor 'text', schema is not a bilingual text`];
  }
  if (typeof kind === 'string') {
    if (shape.k !== 'prim') return [`${path}: descriptor '${kind}', schema is ${shape.k}`];
    const fits = kind === 'number' ? shape.name === 'number' || shape.name === 'integer' : kind === shape.name;
    return fits ? [] : [`${path}: descriptor '${kind}', schema '${shape.name}'`];
  }
  if ('anyOf' in kind) {
    if (shape.k !== 'union') return [`${path}: descriptor anyOf, schema is ${shape.k}`];
    const bad = shape.options.filter((o) => !kind.anyOf.some((k) => walk2(o, k, path).length === 0));
    return bad.length ? [`${path}: ${bad.length} schema option(s) match no descriptor kind of the anyOf`] : [];
  }
  if ('array' in kind) return shape.k === 'array' ? walk2(shape.item, kind.array, `${path}[]`) : [`${path}: descriptor array, schema is ${shape.k}`];
  if ('map' in kind) return shape.k === 'map' ? walk2(shape.value, kind.map, `${path}{}`) : [`${path}: descriptor map, schema is ${shape.k}`];
  if (shape.k !== 'object') return [`${path}: descriptor object, schema is ${shape.k}`];
  const have = Object.keys(shape.keys).filter((k) => !ignore.includes(k));
  const want = Object.keys(kind.object);
  return [
    ...have.filter((k) => !want.includes(k)).map((k) => `${path}.${k}: in the schema, not in the descriptor`),
    ...want.filter((k) => !have.includes(k)).map((k) => `${path}.${k}: in the descriptor, not in the schema`),
    ...want.filter((k) => have.includes(k)).flatMap((k) => walk2(shape.keys[k], kind.object[k], `${path}.${k}`)),
  ];
}
const schemaShape = (name: string): Shape => shapeOf(schemaDocs.get(name), { doc: schemaDocs.get(name)!, id: schemaDocs.get(name)!.$id as string });

describe('descriptors against the schema files, at every nesting level', () => {
  // the document schemas pair with their descriptor through the same selectors the committed documents use; the
  // sub-document schemas pair by name (a new case adds its descriptor to variantKind / modelsKind, not to this list)
  const fixed: Array<[string, Kind, string[]?]> = [
    ['common/case-index', { object: INDEX }],
    ['common/case-manifest', { object: MANIFEST }],
    ['common/artifact-entry', { object: MODELS_ENTRY }, ['models_ref']],
    ['common/artifact-entry', { object: VARIANT_ENTRY }],
    ['common/gate-verdict', { object: GATE }],
    ['common/contract-summary', { object: CONTRACT_SUMMARY }],
    ['common/contract-index', { object: CONTRACT_INDEX }],
    ['common/contract-family', { object: FAMILY_CONTRACT }],
    ['common/test-result', { object: TEST_ROW }],
    ['common/provenance', { object: PROVENANCE }],
    ['common/model-summary', { object: MODEL_SUMMARY }],
    ['common/model-record', { object: MODEL_RECORD }],
  ];
  for (const [name, kind, ignore] of fixed) {
    it(`${name} against its descriptor (${Object.keys((kind as { object: object }).object).length} keys)`, () => {
      expect(walk2(schemaShape(name), kind, '$', ignore ?? [])).toEqual([]);
    });
  }
  const bySchema = new Map<string, Kind>();
  for (const path of committed) {
    const rel = posix(relative(repo, path));
    const doc = loadJson(path);
    if (doc.schema === 'contraste.case/v1') bySchema.set(schemaFor(rel, doc), { object: variantKind(doc as { outputs?: { kind?: string } }) });
    if (doc.schema === 'contraste.models/v1') bySchema.set(schemaFor(rel, doc), { object: modelsKind(doc as { case_id?: string; fit_id?: string }) });
  }
  it('every variant and models schema has a descriptor', () => {
    expect(bySchema.size).toBeGreaterThanOrEqual(11);
  });
  for (const [name, kind] of bySchema) {
    it(`${name} against its descriptor`, () => {
      expect(walk2(schemaShape(name), kind, '$')).toEqual([]);
    });
  }
  it('plants: a nested key, a type change and a nullability change are each reported', () => {
    const shape = schemaShape('common/case-manifest');
    const withKey = { ...MANIFEST, engine: { object: { pipeline: 'string', riskvalidation: { nullable: 'string' }, planted: 'string' } } } as Record<string, Kind>;
    expect(walk2(shape, { object: withKey }, '$').join('\n')).toMatch(/\$\.engine\.planted: in the descriptor, not in the schema/);
    const retyped = { ...MANIFEST, seed: 'string' } as Record<string, Kind>;
    expect(walk2(shape, { object: retyped }, '$').join('\n')).toMatch(/\$\.seed: descriptor 'string', schema 'integer'/);
    const nullability = { ...MANIFEST, default_variant: { nullable: 'string' } } as Record<string, Kind>;
    expect(walk2(shape, { object: nullability }, '$').join('\n')).toMatch(/descriptor is nullable/);
    const missingNested = { ...MANIFEST, engine: { object: { pipeline: 'string' } } } as Record<string, Kind>;
    expect(walk2(shape, { object: missingNested }, '$').join('\n')).toMatch(/\$\.engine\.riskvalidation: in the schema, not in the descriptor/);
  });
});

// The generated types and the descriptors are one contract: these lines fail `tsc` (npm run build) when a schema
// change reaches contract.gen.ts and the descriptors of contract.types.ts do not follow (satisfies Record<keyof ..>).
const _kind: CaseIndex['cases'][number]['kind'] = 'real';
const _light: import('./contract.types').Light = 'amber';
void [_kind, _light];