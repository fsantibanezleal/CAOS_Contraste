// The consumer test of readiness 1.0.0 (docs/contracts/catalog.md, Missing-data states; ADR-0080 decision 3): a
// fixture document valid under the schema, and the committed data/derived/readiness.json when present, give each
// view the state its rows say; each of the six states maps to the behavior the catalog names; the planned cases are
// the manifests the `case-manifest` partial row lists as missing; and a readiness that is absent or invalid is
// "readiness unknown", never a crash and never a fetch of a manifest the document declares absent.
import Ajv2020 from '@redocly/ajv/dist/2020.js';
import { existsSync, readFileSync } from 'node:fs';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ArtifactUnavailable, loadCase, loadIndex } from '../api/artifacts';
import { NoteLine } from './ReadinessNote';
import { behavior, entryFor, isPlanned, isUnavailable, loadReadiness, plannedCaseIds, resetReadiness, rowsForCase, SEVERITY, viewState } from './readiness';
import type { ContractState, Readiness, ReadinessEntry } from './types';

vi.stubGlobal('__APP_VERSION__', 'test-version');

const root = new URL('../../../', import.meta.url);
const read = (rel: string): Readiness => JSON.parse(readFileSync(new URL(rel, root), 'utf8'));
const fixture = JSON.parse(readFileSync(new URL('./__fixtures__/readiness.partial.json', import.meta.url), 'utf8')) as Readiness;
const committedUrl = new URL('data/derived/readiness.json', root);
const committed = existsSync(committedUrl) ? read('data/derived/readiness.json') : null;

const ajv = new Ajv2020({ strict: true, strictTypes: false, strictRequired: false, allErrors: true });
const schema = JSON.parse(readFileSync(new URL('docs/contracts/schemas/common/readiness.schema.json', root), 'utf8'));
const validate = ajv.compile(schema);

const entry = (id: string, state: ContractState, over: Partial<ReadinessEntry> = {}): ReadinessEntry => ({
  id,
  version: '1.0.0',
  status: 'real',
  provenance: state === 'missing' ? null : 'real',
  state,
  reason: state === 'available' ? null : { en: `${id} is ${state}`, es: `${id} está ${state}` },
  missing: state === 'partial' ? ['x/y.json'] : [],
  ...over,
});
const doc = (...entries: ReadinessEntry[]): Readiness => ({ schema: 'example.readiness/v1', product_version: '9.99.999', catalog_sha256: '0'.repeat(64), contracts: entries });

describe('the documents this side reads', () => {
  const docs: Array<[string, Readiness]> = [['fixture', fixture], ...(committed ? ([['committed bake', committed]] as Array<[string, Readiness]>) : [])];
  it.each(docs)('%s is valid under readiness.schema.json', (_n, d) => {
    expect(validate(d), JSON.stringify(validate.errors)).toBe(true);
  });
  it('the fixture says partial for the 18 planned manifests', () => {
    const row = entryFor(fixture, 'case-manifest');
    expect(row?.state).toBe('partial');
    expect(row?.missing).toHaveLength(18);
    expect(row?.missing.every((m) => /^manifests\/C\d\d\.json$/.test(m))).toBe(true);
  });
});

describe('the six states', () => {
  it('order: missing, partial, training, provider, stale, available; the most severe wins', () => {
    expect(SEVERITY).toEqual(['missing', 'partial', 'training', 'provider', 'stale', 'available']);
    const d = doc(entry('a', 'stale'), entry('b', 'partial'), entry('c', 'available'));
    expect(viewState(d, ['a', 'b', 'c']).state).toBe('partial');
    expect(viewState(doc(entry('a', 'available')), ['a'])).toEqual({ state: 'available', rows: [] });
  });
  it.each<[ContractState, boolean, boolean]>([
    ['available', true, false],
    ['partial', true, true],
    ['stale', true, true],
    ['provider', true, true],
    ['training', true, true],
    ['missing', false, true],
  ])('%s: shows the result %s, with a note %s, from the document and in Spanish too', (state, showsResult, note) => {
    expect(behavior(state)).toEqual({ showsResult, note });
    const view = viewState(doc(entry('a', state)), ['a']);
    for (const [lang, text] of [['en', `a is ${state}`], ['es', `a está ${state}`]] as const) {
      const html = renderToStaticMarkup(createElement(NoteLine, { view, lang }));
      if (note) {
        expect(html).toContain(`data-readiness="${state}"`);
        expect(html).toContain(text);
      } else {
        expect(html).toBe('');
      }
    }
  });
  it('a row of the view that is not in the document is ignored; a view with none of its rows is unknown', () => {
    expect(viewState(doc(entry('a', 'stale')), ['a', 'zzz']).state).toBe('stale');
    expect(viewState(doc(entry('a', 'stale')), ['zzz']).state).toBe('unknown');
  });
  it('a case reads the shared rows and the rows prefixed with its id', () => {
    const d = doc(entry('case-index', 'available'), entry('c04-agency', 'stale'), entry('c05-sp', 'available'), entry('test-result', 'available'));
    expect(rowsForCase(d, 'C04')).toEqual(['case-index', 'test-result', 'c04-agency']);
    expect(rowsForCase(null, 'C04')).toEqual([]);
    // the partial case-manifest row is about the other cases: a built case does not carry its note
    expect(rowsForCase(doc(entry('case-manifest', 'partial'), entry('c04-agency', 'available')), 'C04')).toEqual(['c04-agency']);
  });
});

describe('the planned cases', () => {
  const index = { cases: [{ case_id: 'C01', manifest_path: 'manifests/C01.json' }, { case_id: 'C02', manifest_path: 'manifests/C02.json' }, { case_id: 'C03', manifest_path: 'manifests/C03.json' }] };
  it('are the index entries whose manifest the case-manifest partial row lists as missing', () => {
    const d = doc(entry('case-manifest', 'partial', { missing: ['manifests/C02.json', 'manifests/C03.json'] }));
    expect(plannedCaseIds(d, index)).toEqual(['C02', 'C03']);
    expect(isPlanned(d, index.cases[1])).toBe(true);
    expect(isPlanned(d, index.cases[0])).toBe(false);
  });
  it('the fixture marks exactly the 18 of the committed index', () => {
    const committedIndex = JSON.parse(readFileSync(new URL('data/derived/manifests/index.json', root), 'utf8')) as typeof index;
    const planned = plannedCaseIds(fixture, committedIndex);
    expect(planned).toHaveLength(18);
    expect(planned).not.toContain('C01');
    expect(planned).not.toContain('C22');
  });
  it('none are planned when the readiness is unknown, or when the row is not partial', () => {
    expect(plannedCaseIds(null, index)).toEqual([]);
    expect(plannedCaseIds(doc(entry('case-manifest', 'available')), index)).toEqual([]);
    expect(plannedCaseIds(doc(entry('other', 'partial', { missing: ['manifests/C02.json'] })), index)).toEqual([]);
  });
});

describe('a missing or invalid readiness document', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('a null document is readiness unknown, in both languages', () => {
    const view = viewState(null, ['case-index']);
    expect(view.state).toBe('unknown');
    expect(renderToStaticMarkup(createElement(NoteLine, { view, lang: 'en' }))).toMatch(/data-readiness="unknown".*Readiness unknown/);
    expect(renderToStaticMarkup(createElement(NoteLine, { view, lang: 'es' }))).toMatch(/data-readiness="unknown".*Disponibilidad desconocida/);
  });
  it('a fetch that fails resolves to null, names the cause on the console, and is asked for once', async () => {
    resetReadiness();
    const fetch = vi.fn(async () => ({ ok: false, status: 404, headers: new Headers({ 'content-type': 'text/html' }), json: async () => ({}) }));
    vi.stubGlobal('fetch', fetch);
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(loadReadiness()).resolves.toBeNull();
    await expect(loadReadiness()).resolves.toBeNull();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(err.mock.calls.flat().join(' ')).toMatch(/readiness\.json: HTTP 404/);
    err.mockRestore();
  });
  it('a document without a contracts list is treated as unreadable', async () => {
    resetReadiness();
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, headers: new Headers({ 'content-type': 'application/json' }), json: async () => ({ nope: 1 }) })));
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await expect(loadReadiness()).resolves.toBeNull();
    err.mockRestore();
  });
});

describe('a manifest the document lists as absent', () => {
  const MANIFEST = { case_id: 'C1', artifacts: [{ role: 'variant', variant_id: 'v', path: 'C1/v.json', models_ref: 'C1/m.json' }], default_variant: 'v' };
  function serve(readiness: unknown) {
    const answers: Record<string, unknown> = { 'readiness.json': readiness, 'manifests/C1.json': MANIFEST, 'manifests/index.json': { cases: [] } };
    const fetch = vi.fn(async (url: string) => {
      const rel = Object.keys(answers).find((k) => url.includes(`/data/${k}`));
      return { ok: !!rel, status: rel ? 200 : 404, headers: new Headers({ 'content-type': 'application/json' }), json: async () => answers[rel ?? ''] };
    });
    vi.stubGlobal('fetch', fetch);
    vi.stubGlobal('__APP_VERSION__', 'test-version');
    return fetch;
  }
  beforeEach(() => resetReadiness());
  afterEach(() => vi.unstubAllGlobals());

  it('isUnavailable: a path a row lists in missing, and every path when the case-index row is missing', () => {
    const d = doc(entry('case-manifest', 'partial', { missing: ['manifests/C1.json'] }), entry('case-index', 'available'));
    expect(isUnavailable(d, 'manifests/C1.json')).toBe(true);
    expect(isUnavailable(d, 'manifests/C2.json')).toBe(false);
    expect(isUnavailable(doc(entry('case-index', 'missing')), 'anything.json')).toBe(true);
    expect(isUnavailable(null, 'manifests/C1.json')).toBe(false);
  });
  it('loadCase rejects with ArtifactUnavailable in both languages and never fetches the manifest', async () => {
    const fetch = serve(doc(entry('case-manifest', 'partial', { missing: ['manifests/C1.json'] })));
    const e = await loadCase('C1', null).catch((x: unknown) => x);
    expect(e).toBeInstanceOf(ArtifactUnavailable);
    expect((e as ArtifactUnavailable).reason.en).toContain('manifests/C1.json');
    expect((e as ArtifactUnavailable).reason.es).toContain('manifests/C1.json');
    expect((e as ArtifactUnavailable).reason.es).toContain('case-manifest está');
    expect(fetch.mock.calls.some((c) => String(c[0]).includes('manifests/C1.json'))).toBe(false);
  });
  it('loadIndex rejects with ArtifactUnavailable when the case-index row is missing', async () => {
    serve(doc(entry('case-index', 'missing')));
    await expect(loadIndex()).rejects.toBeInstanceOf(ArtifactUnavailable);
  });
  it('an unreadable document refuses nothing: the manifest is fetched', async () => {
    const fetch = serve({ nope: 1 });
    const err = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    await loadCase('C1', null).catch(() => undefined); // the variant files are not served: only the manifest fetch matters
    expect(fetch.mock.calls.some((c) => String(c[0]).includes('manifests/C1.json'))).toBe(true);
    err.mockRestore();
  });
});
