// The discovery registries that let a wave 2 unit add its files without editing anyone else's: the instruments of
// workbench/cNN/instrument.tsx, the Methodology sections of pages/methodology/*.tsx, the citations of
// content/citations/*.ts and the coverage of content/coverage/*.ts. Each refuses what would be silently wrong: a module
// without its export, an unknown Methodology group, a citation or a case defined twice.
import { describe, expect, it } from 'vitest';
import { CITATIONS, mergeCitations } from '../content/citations';
import { CASES, CATEGORY_TITLES, mergeCoverage } from '../content/coverage';
import { collectSections, METHODOLOGY_GROUPS, REGISTERED_SECTIONS } from '../pages/methodologyRegistry';
import { collectInstruments, INSTRUMENTS } from './registry';

const hook = () => null;

describe('the instrument registry', () => {
  it('finds the instruments of C04, C05 and C22 in sorted path order', () => {
    const paths = INSTRUMENTS.map((i) => i.path);
    expect(paths).toEqual([...paths].sort());
    for (const p of ['./c04/instrument.tsx', './c05/instrument.tsx', './c22/instrument.tsx']) expect(paths).toContain(p);
    expect(INSTRUMENTS.every((i) => typeof i.useInstrument === 'function')).toBe(true);
  });
  it('sorts the modules it is given by path', () => {
    const got = collectInstruments({ './c22/instrument.tsx': { useInstrument: hook }, './c06/instrument.tsx': { useInstrument: hook } });
    expect(got.map((g) => g.path)).toEqual(['./c06/instrument.tsx', './c22/instrument.tsx']);
  });
  it('refuses an instrument file that does not export useInstrument, naming the file', () => {
    expect(() => collectInstruments({ './c09/instrument.tsx': { useC09Instrument: hook } })).toThrow(/c09\/instrument\.tsx.*useInstrument/);
    expect(() => collectInstruments({ './c09/instrument.tsx': { useInstrument: 'not a function' } })).toThrow(/useInstrument/);
  });
});

describe('the Methodology registry', () => {
  const Body = () => null as never;
  const section = (over: Record<string, unknown> = {}) => ({ id: 's1', group: 'tests', order: 10, title: { en: 'T', es: 'T' }, Body, ...over });
  it('starts from the two existing groups and registers sections by group, ordered', () => {
    expect(METHODOLOGY_GROUPS).toEqual(['models', 'tests', 'loss']);
    expect(Array.isArray(REGISTERED_SECTIONS)).toBe(true);
    const got = collectSections({ './methodology/b.tsx': { methodologySection: section({ id: 'b', order: 20 }) }, './methodology/a.tsx': { methodologySection: section({ id: 'a', order: 10 }) } }, METHODOLOGY_GROUPS);
    expect(got.map((s) => s.id)).toEqual(['a', 'b']);
  });
  it('fails an unknown group', () => {
    expect(() => collectSections({ './methodology/x.tsx': { methodologySection: section({ group: 'nowhere' }) } }, METHODOLOGY_GROUPS)).toThrow(/unknown group "nowhere"/);
  });
  it('fails a file without methodologySection, and a duplicate section id', () => {
    expect(() => collectSections({ './methodology/x.tsx': {} }, METHODOLOGY_GROUPS)).toThrow(/methodologySection/);
    expect(() =>
      collectSections({ './methodology/x.tsx': { methodologySection: section() }, './methodology/y.tsx': { methodologySection: section() } }, METHODOLOGY_GROUPS),
    ).toThrow(/duplicate/);
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
