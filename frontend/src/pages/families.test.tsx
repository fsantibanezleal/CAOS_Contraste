// Integration of the built cases into the cross-case pages: the Experiments case tabs are grouped by the question family
// (ADR-0071 rule 5: at most six peer tabs), and the headline row of every case that is not the C01 scorecard shape is
// read from its own artifact (here the contract fixtures), with no "not available" where the fixture holds a number.
import { readFileSync } from 'node:fs';
import { pick } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { groupCases } from './Experiments';
import { U6_BENCHMARK_CASES, U6_CASES, experimentRows } from './U6Sections';

const NOT_AVAILABLE = /not available|no disponible/i;
const fixture = (dir: string, file: string) => JSON.parse(readFileSync(new URL(`../../../docs/contracts/fixtures/${dir}/${file}`, import.meta.url), 'utf8')) as VariantArtifact<unknown>;
const manifestOf = (id: string, v: VariantArtifact<unknown>) => ({ case_id: id, artifacts: [{ role: 'variant', variant_id: v.variant_id, title: { en: 'A long title of the fixture variant, with 1.25 inside', es: 'Un título largo con 1.25 dentro' }, short_title: { en: 'Fixture variant', es: 'Variante de prueba' } }] }) as unknown as CaseManifest;

const BUILT = ['c01', 'c03', 'c04', 'c05', 'c06', 'c07', 'c08', 'c09', 'c22'];
const tabs = BUILT.map((id) => ({ id, label: id.toUpperCase(), content: null }));

describe('the Experiments case tabs are grouped by the question family', () => {
  const groups = groupCases(tabs);
  it('holds no group above six peer tabs and loses no case', () => {
    for (const g of groups) expect(g.tabs.length, g.id).toBeLessThanOrEqual(6);
    expect(groups.flatMap((g) => g.tabs.map((t) => t.id)).sort()).toEqual([...BUILT].sort());
  });
  it('groups credit scoring and PD, provisions, loss severity and exposure, and validating the validator', () => {
    const by = Object.fromEntries(groups.map((g) => [pick(g.label, 'en'), g.tabs.map((t) => t.id)]));
    expect(by).toEqual({
      'Credit scoring and PD': ['c01', 'c03', 'c04', 'c05'],
      'Credit losses: provisions, severity and exposure': ['c06', 'c07', 'c08', 'c09'],
      'Validating the validator': ['c22'],
    });
    for (const g of groups) expect(pick(g.label, 'es').length).toBeGreaterThan(0);
  });
  it('keeps a case that is not in the coverage registry in a group of its own', () => {
    const g = groupCases([{ id: 'c99', label: 'C99', content: null }]);
    expect(g).toHaveLength(1);
    expect(pick(g[0].label, 'en')).toBe('Other cases');
  });
  it('joins C18 to the capital family, relabelled (batch 3 family decision, 2026-10-20)', () => {
    const g = groupCases([{ id: 'c18', label: 'C18', content: null }]);
    expect(g).toHaveLength(1);
    expect(g[0].id).toBe('capital');
    expect(pick(g[0].label, 'en')).toBe('Capital, aggregation and stress');
  });
});

describe('the headline row of a case that is not the C01 shape comes from its own artifact', () => {
  const cases: Array<[string, string, string, number]> = [
    ['C03', 'c03', 'variant-vintage-cohort-fixture.json', 6],
    ['C06', 'c06', 'variant-reporting-date-fixture.json', 6],
    ['C07', 'c07', 'variant-three-regime-fixture.json', 4],
    ['C08', 'c08', 'variant-default-cohort-fixture.json', 6],
    ['C09', 'c09', 'variant-acceleration-level-fixture.json', 5],
  ];
  for (const [id, dir, file, cols] of cases) {
    it(`${id}: ${cols} cells, the variant title first, a number in every other cell, both languages`, () => {
      const v = fixture(dir, file);
      for (const lang of ['en', 'es'] as const) {
        const [row] = experimentRows(manifestOf(id, v), [v], lang);
        expect(row.length).toBe(cols);
        expect(row[0]).toBe(lang === 'en' ? 'Fixture variant' : 'Variante de prueba');
        for (const cell of row.slice(1)) {
          expect(String(cell), `${id} ${lang}`).toMatch(/\d/);
          expect(String(cell), `${id} ${lang}`).not.toMatch(NOT_AVAILABLE);
          expect(String(cell)).not.toMatch(/NaN|undefined|Infinity/);
        }
      }
    });
  }
  it('registers the cases so that none falls through to the scorecard table', () => {
    expect([...U6_CASES].sort()).toEqual(['C03', 'C06', 'C07', 'C08', 'C09']);
    expect([...U6_BENCHMARK_CASES].sort()).toEqual(['C03', 'C08', 'C09']);
  });
});
