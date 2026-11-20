// GATE-15B: the Benchmark page as groups of tabs. Every section of the page sits in exactly one tab, there are at most six
// groups and six tabs in a group (ADR-0071), every case lands in a group by an explicit family (never by the fallback),
// and a tab or group with no section is not drawn.
import { MAX_PEER_TABS, pick } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import { CASES } from '../content/coverage';
import { QUESTION_HOME } from '../lib/methodsCompared';
import { FAMILY_GROUP, NO_BENCHMARK, benchGroupOf, benchmarkPlan, planViolations } from './Benchmark';
import { familyOf } from './experiments/families';

const ids = CASES.map((c) => c.id);
const shown = ids.filter((id) => !(id in NO_BENCHMARK));
// the cases whose tab holds only the methods-compared section of their question (C06 left the list of cases with no benchmark)
const BUILT_SHOWN = ['C01', 'C02', 'C03', 'C04', 'C05', 'C08', 'C09', 'C10', 'C11', 'C12', 'C13', 'C17', 'C18', 'C20', 'C22'];
const QUESTIONS = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6', 'Q7', 'Q8', 'Q9', 'Q10', 'Q11', 'Q12'];

describe('the Benchmark groups of tabs', () => {
  const plan = benchmarkPlan(shown, true, true);
  const tabs = plan.flatMap((g) => g.tabs);
  it('holds at most six groups of at most six tabs, each labelled in both languages', () => {
    expect(plan.length).toBeGreaterThan(1);
    expect(plan.length).toBeLessThanOrEqual(MAX_PEER_TABS);
    for (const g of plan) {
      expect(g.tabs.length, g.id).toBeLessThanOrEqual(MAX_PEER_TABS);
      expect(pick(g.label, 'en').length, g.id).toBeGreaterThan(0);
      expect(pick(g.label, 'es'), g.id).not.toBe(pick(g.label, 'en'));
    }
    expect(plan.map((g) => g.id)).toEqual(['reading', 'pd', 'losses', 'capital', 'market', 'validation']);
  });
  it('puts every section of the page in exactly one tab, the questions included', () => {
    const expected = ['how', 'excluded', 'limits', 'robustness', 'provenance', 'methods', ...shown.filter((id) => id !== 'C06').map((id) => `case:${id}`), ...QUESTIONS.map((q) => `methods:${q}`)].sort();
    const all = tabs.flatMap((t) => t.sections);
    expect([...all].sort()).toEqual(expected);
    expect(new Set(all).size).toBe(all.length);
    expect(new Set(tabs.map((t) => t.id)).size).toBe(tabs.length);
  });
  it('opens on the reading group: the guide, the excluded cases and the limits, then the robustness, the provenance and the methods compared', () => {
    expect(plan[0].id).toBe('reading');
    expect(plan[0].tabs.map((t) => t.sections)).toEqual([['how', 'excluded', 'limits'], ['robustness'], ['provenance'], ['methods']]);
    expect(pick(plan[0].tabs[3].label, 'en')).toBe('Methods compared');
    expect(pick(plan[0].tabs[3].label, 'es')).toBe('Métodos comparados');
  });
  it('gives each built case a tab of its own, in the group of its question family, its questions after its comparison', () => {
    const withQuestions: Record<string, string[]> = { C01: ['Q5', 'Q12'], C04: ['Q4'], C08: ['Q7'], C11: ['Q1'], C13: ['Q3'], C17: ['Q8'], C20: ['Q11'], C22: ['Q2'] };
    for (const c of BUILT_SHOWN) {
      const g = plan.find((x) => x.tabs.some((t) => t.sections.includes(`case:${c}`)));
      expect(g?.id, c).toBe(benchGroupOf(c));
      expect(g?.tabs.find((t) => t.sections.includes(`case:${c}`))?.sections, c).toEqual([`case:${c}`, ...(withQuestions[c] ?? []).map((q) => `methods:${q}`)]);
    }
  });
  it('takes C06 out of the cases with no benchmark: a tab of its own in the credit-losses group, holding Q6 alone', () => {
    expect('C06' in NO_BENCHMARK).toBe(false);
    const g = plan.find((x) => x.id === 'losses')!;
    expect(g.tabs.find((t) => t.id === 'case-c06')?.sections).toEqual(['methods:Q6']);
    expect(g.tabs.length).toBeLessThanOrEqual(MAX_PEER_TABS);
  });
  it('gives C14 and C16, which have no champion comparison, a tab that holds only their question', () => {
    const g = plan.find((x) => x.id === 'market')!;
    expect(g.tabs.find((t) => t.id === 'case-c14')?.sections).toEqual(['methods:Q9']);
    expect(g.tabs.find((t) => t.id === 'case-c16')?.sections).toEqual(['methods:Q10']);
    expect('C14' in NO_BENCHMARK && 'C16' in NO_BENCHMARK).toBe(true);
  });
  it('reaches every question: each of the twelve is a section of exactly one tab, in the tab of its home case', () => {
    for (const q of QUESTIONS) {
      const home = tabs.filter((t) => t.sections.includes(`methods:${q}`));
      expect(home.length, q).toBe(1);
      expect(home[0].id, q).toBe(`case-${QUESTION_HOME[q].toLowerCase()}`);
    }
  });
  it('holds every bound of the plan: no violation', () => {
    expect(planViolations(plan)).toEqual([]);
  });
  it('adversarial: a seventh group, a seventh tab, a section in two tabs and a tab with no section are each named by the plan check', () => {
    const grown = benchmarkPlan(shown, true, true).map((g) => ({ ...g, tabs: g.tabs.map((t) => ({ ...t, sections: [...t.sections] })) }));
    const group = grown[0];
    expect(planViolations([...grown, { ...group, id: 'pd' as const }])).toEqual(expect.arrayContaining(['7 groups']));
    const tab = grown[1].tabs[0];
    grown[1].tabs.push(...Array.from({ length: 3 }, (_, i) => ({ ...tab, id: `extra-${i}`, sections: [`extra:${i}`] })));
    expect(planViolations(grown).join(' ')).toMatch(/group pd has 8 tabs/);
    const twice = benchmarkPlan(shown, true, true);
    twice[1].tabs[0].sections.push('methods:Q1');
    expect(planViolations(twice).join(' ')).toMatch(/section methods:Q1 is in 2 tabs/);
    const empty = benchmarkPlan(shown, true, true);
    empty[0].tabs[0].sections = [];
    expect(planViolations(empty).join(' ')).toMatch(/has no section/);
  });
  it('places every case by its question family, never by the fallback', () => {
    for (const id of ids) {
      expect(Object.keys(FAMILY_GROUP), id).toContain(familyOf(id).id);
      expect(benchGroupOf(id)).toBe(FAMILY_GROUP[familyOf(id).id]);
    }
  });
  it('draws no group or tab without a section and drops the sections that do not exist', () => {
    const none = benchmarkPlan([], false, false, []);
    expect(none.map((g) => g.id)).toEqual(['reading']);
    expect(none[0].tabs.map((t) => t.sections)).toEqual([['how', 'limits'], ['provenance'], ['methods']]);
  });
});
