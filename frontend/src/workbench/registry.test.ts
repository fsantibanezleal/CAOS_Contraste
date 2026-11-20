// The discovery registries that let a wave 2 unit add its files without editing anyone else's: the instruments of
// workbench/cNN/instrument.tsx (loaded on demand, one case at a time), the Methodology sections of
// pages/methodology/<name>.meta.ts and <name>.tsx (the tab list from the metadata, the body on demand), the citations of
// content/citations/*.ts and the coverage of content/coverage/*.ts. Each refuses what would be silently wrong: a module
// without its export, a metadata file without a body or the reverse, an unknown Methodology group, a citation or a case
// defined twice.
import { existsSync, readdirSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { CITATIONS, mergeCitations } from '../content/citations';
import { CASES, CATEGORY_TITLES, mergeCoverage } from '../content/coverage';
import { collectSections, METHODOLOGY_GROUPS, REGISTERED_SECTIONS } from '../pages/methodologyRegistry';
import { createInstrumentLoader, instrumentLoaders, INSTRUMENT_LOADERS, instrumentOf, loadInstrument } from './registry';

const hook = () => null;
const ls = (path: string) => readdirSync(new URL(path, import.meta.url));
/** A loader the way `import.meta.glob` makes one: a function that imports the module. */
const loader = (fn: () => Promise<unknown>) => fn;

describe('the instrument registry', () => {
  it('maps every case directory with an instrument.tsx to its loader, none twice', () => {
    const dirs = ls('./').filter((d) => /^c\d\d$/.test(d) && existsSync(new URL(`./${d}/instrument.tsx`, import.meta.url)));
    expect(dirs.length).toBeGreaterThan(15);
    expect(Object.keys(INSTRUMENT_LOADERS).sort()).toEqual(dirs.map((d) => d.toUpperCase()).sort());
    expect(Object.keys(INSTRUMENT_LOADERS)).toEqual(expect.arrayContaining(['C04', 'C05', 'C11', 'C22']));
    expect(Object.keys(INSTRUMENT_LOADERS)).not.toContain('C01');
  });
  it('keys the loaders by case id, from the path', () => {
    const got = instrumentLoaders({ './c22/instrument.tsx': loader(async () => ({ useInstrument: hook })), './c06/instrument.tsx': loader(async () => ({ useInstrument: hook })) });
    expect(Object.keys(got).sort()).toEqual(['C06', 'C22']);
  });
  it('refuses a path that is not a case instrument, and two paths for one case', () => {
    expect(() => instrumentLoaders({ './x/instrument.tsx': loader(async () => ({})) })).toThrow(/x\/instrument\.tsx/);
    expect(() => instrumentLoaders({ './c06/instrument.tsx': loader(async () => ({})), './C06/instrument.tsx': loader(async () => ({})) })).toThrow(/C06.*twice|twice.*C06/);
  });
  it('fails a module without useInstrument, naming the file', async () => {
    const l = createInstrumentLoader(instrumentLoaders({ './c09/instrument.tsx': loader(async () => ({ useC09Instrument: hook })) }));
    await expect(l.load('C09')).rejects.toThrow(/c09\/instrument\.tsx.*useInstrument/);
    const l2 = createInstrumentLoader(instrumentLoaders({ './c09/instrument.tsx': loader(async () => ({ useInstrument: 'not a function' })) }));
    await expect(l2.load('C09')).rejects.toThrow(/useInstrument/);
  });
  it('loads one case on demand, keeps the loaded module and retries after a failure', async () => {
    let calls = 0;
    let fail = true;
    const l = createInstrumentLoader(
      instrumentLoaders({
        './c06/instrument.tsx': loader(async () => {
          calls += 1;
          if (fail) throw new Error('offline');
          return { useInstrument: hook };
        }),
      }),
    );
    expect(l.has('C06')).toBe(true);
    expect(l.has('C01')).toBe(false);
    expect(l.peek('C06')).toBeNull();
    await expect(l.load('C06')).rejects.toThrow('offline');
    expect(l.peek('C06')).toBeNull();
    fail = false;
    expect(await l.load('C06')).toBe(hook);
    expect(await l.load('C06')).toBe(hook);
    expect(calls).toBe(2);
    expect(l.peek('C06')).toBe(hook);
  });
  it('rejects a case with no instrument file (C01), naming the case', async () => {
    await expect(loadInstrument('C01')).rejects.toThrow(/C01/);
    expect(instrumentOf('C01')).toBeNull();
  });
  it('loads the real module of one case through the glob and no other', async () => {
    const h = await loadInstrument('C11');
    expect(typeof h).toBe('function');
    expect(instrumentOf('C11')).toBe(h);
    expect(instrumentOf('C12')).toBeNull();
  });
});

describe('the Methodology registry', () => {
  const Body = () => null as never;
  const meta = (over: Record<string, unknown> = {}) => ({ id: 's1', group: 'tests', order: 10, title: { en: 'T', es: 'T' }, ...over });
  const metas = (entries: Record<string, Record<string, unknown>>) => Object.fromEntries(Object.entries(entries).map(([stem, m]) => [`./methodology/${stem}.meta.ts`, { methodologyMeta: m }]));
  const bodies = (...stems: string[]) => Object.fromEntries(stems.map((stem) => [`./methodology/${stem}.tsx`, loader(async () => ({ methodologySection: { ...meta(), Body } }))]));
  it('starts from the existing groups and registers sections by group, ordered, from their metadata', () => {
    // grouped by the question family since the wave 2 integration (2026-10-14), at most six top-level groups
    expect(METHODOLOGY_GROUPS).toEqual(['models', 'tests', 'loss', 'capital', 'market', 'balance']);
    const got = collectSections(metas({ b: meta({ id: 'b', order: 20 }), a: meta({ id: 'a', order: 10 }) }), bodies('a', 'b'), METHODOLOGY_GROUPS);
    expect(got.map((s) => s.id)).toEqual(['a', 'b']);
    expect(typeof got[0].load).toBe('function');
  });
  it('pairs every metadata file with its body by stem, on the real files', () => {
    const files = ls('../pages/methodology/');
    const stems = files.filter((f) => f.endsWith('.meta.ts')).map((f) => f.replace('.meta.ts', '')).sort();
    const bodyStems = files.filter((f) => f.endsWith('.tsx')).map((f) => f.replace('.tsx', '')).sort();
    expect(stems.length).toBe(18);
    expect(stems).toEqual(bodyStems);
    expect(REGISTERED_SECTIONS.length).toBe(stems.length);
  });
  it('keeps the tab order of the page (order, then id)', () => {
    const ids = REGISTERED_SECTIONS.map((s) => s.id);
    const byGroup = (g: string) => REGISTERED_SECTIONS.filter((s) => s.group === g).map((s) => s.id);
    expect(ids).toEqual([...REGISTERED_SECTIONS].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id)).map((s) => s.id));
    expect(byGroup('models')).toEqual(['governance', 'reject-inference']);
    expect(byGroup('tests')).toEqual(['ml-validation']);
    expect(byGroup('loss')).toEqual(['provisions', 'lgd-ead', 'pc-hazard', 'withdrawals-anchored-pd']);
    expect(byGroup('capital')).toEqual(['portfolio-capital', 'aggregation-stress', 'oprisk', 'regulation']);
    expect(byGroup('market')).toEqual(['market', 'ccr', 'conformal-var', 'pla-complement', 'sequential-monitors']);
    expect(byGroup('balance')).toEqual(['irrbb', 'liquidity']);
  });
  it('fails a metadata file without its body, naming the file', () => {
    expect(() => collectSections(metas({ a: meta() }), {}, METHODOLOGY_GROUPS)).toThrow(/methodology\/a\.meta\.ts.*body/);
  });
  it('fails a body without its metadata file, naming the file', () => {
    expect(() => collectSections({}, bodies('a'), METHODOLOGY_GROUPS)).toThrow(/methodology\/a\.tsx.*meta/);
  });
  it('fails an unknown group', () => {
    expect(() => collectSections(metas({ x: meta({ group: 'nowhere' }) }), bodies('x'), METHODOLOGY_GROUPS)).toThrow(/unknown group "nowhere"/);
  });
  it('fails a metadata file without methodologyMeta, and a duplicate section id', () => {
    expect(() => collectSections({ './methodology/x.meta.ts': {} }, bodies('x'), METHODOLOGY_GROUPS)).toThrow(/methodology\/x\.meta\.ts.*methodologyMeta/);
    expect(() => collectSections(metas({ x: meta(), y: meta() }), bodies('x', 'y'), METHODOLOGY_GROUPS)).toThrow(/duplicate/);
  });
  it('loads a body on demand and fails naming the file when the module has none', async () => {
    const [s] = collectSections(metas({ a: meta() }), bodies('a'), METHODOLOGY_GROUPS);
    expect(await s.load()).toBe(Body);
    const [bad] = collectSections(metas({ a: meta() }), { './methodology/a.tsx': loader(async () => ({})) }, METHODOLOGY_GROUPS);
    await expect(bad.load()).rejects.toThrow(/methodology\/a\.tsx.*methodologySection/);
  });
});

describe('the citation registry', () => {
  const cite = (id: string) => ({ id, label: id, citation: `${id}.`, doi: '10.1000/x' });
  it('merges the base list and every other file, each id once', () => {
    expect(new Set(CITATIONS.map((c) => c.id)).size).toBe(CITATIONS.length);
    expect(CITATIONS.some((c) => c.id === 'sr117')).toBe(true);
    const merged = mergeCitations({ './citations/base.ts': { CITATIONS: [cite('a')] }, './citations/c06.ts': { CITATIONS: [cite('b')] } });
    expect(merged.map((c) => c.id)).toEqual(['a', 'b']);
  });
  it('fails a citation defined twice across files, naming both files', () => {
    expect(() => mergeCitations({ './citations/base.ts': { CITATIONS: [cite('a')] }, './citations/c06.ts': { CITATIONS: [cite('a')] } })).toThrow(/"a".*base\.ts.*c06\.ts/);
  });
});

describe('the coverage registry', () => {
  const planned = (id: string) => ({ id, category: 'provisions', title: { en: id, es: id }, data: { en: 'd', es: 'd' }, truth: { en: 't', es: 't' }, unit: 'u' });
  it('keeps the existing coverage as base and merges the others', () => {
    expect(CASES.length).toBeGreaterThan(0);
    expect(Object.keys(CATEGORY_TITLES)).toContain('credit-scoring');
    const merged = mergeCoverage({ './coverage/base.ts': { CASES: [planned('C01')], CATEGORY_TITLES: { a: 'A' } }, './coverage/more.ts': { CASES: [planned('C02')], CATEGORY_TITLES: { b: 'B' } } });
    expect(merged.CASES.map((c) => c.id)).toEqual(['C01', 'C02']);
    expect(Object.keys(merged.CATEGORY_TITLES)).toEqual(['a', 'b']);
  });
  it('lets a later file replace the row of a case the unit builds, once, and the title of a category', () => {
    const built = { ...planned('C06'), unit: 'CD-06' };
    const merged = mergeCoverage({ './coverage/base.ts': { CASES: [planned('C06'), planned('C07')], CATEGORY_TITLES: { a: 'A' } }, './coverage/cd06.ts': { CASES: [built], CATEGORY_TITLES: { a: 'B' } } });
    expect(merged.CASES.map((c) => [c.id, c.unit])).toEqual([['C06', 'CD-06'], ['C07', 'u']]);
    expect(merged.CATEGORY_TITLES).toEqual({ a: 'B' });
  });
  it('fails a coverage file that exports no list', () => {
    expect(() => mergeCoverage({ './coverage/x.ts': { CASES: 'no' as never } })).toThrow(/CASES/);
  });
});
