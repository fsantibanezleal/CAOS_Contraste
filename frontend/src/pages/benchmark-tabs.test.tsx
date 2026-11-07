// GATE-15B: the Benchmark page as groups of tabs. Every section of the page sits in exactly one tab, there are at most six
// groups and six tabs in a group (ADR-0071), every case lands in a group by an explicit family (never by the fallback),
// and a tab or group with no section is not drawn.
import { MAX_PEER_TABS, pick } from '@fasl-work/caos-app-shell';
import { describe, expect, it } from 'vitest';
import { CASES } from '../content/coverage';
import { FAMILY_GROUP, NO_BENCHMARK, benchGroupOf, benchmarkPlan } from './Benchmark';
import { familyOf } from './experiments/families';

const ids = CASES.map((c) => c.id);
const shown = ids.filter((id) => !(id in NO_BENCHMARK));
const BUILT_SHOWN = ['C01', 'C02', 'C03', 'C04', 'C05', 'C08', 'C09', 'C10', 'C11', 'C12', 'C13', 'C17', 'C18', 'C20', 'C22'];

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
  });
  it('puts every section of the page in exactly one tab', () => {
    const expected = ['how', 'excluded', 'limits', 'robustness', 'provenance', ...shown.map((id) => `case:${id}`)].sort();
    const all = tabs.flatMap((t) => t.sections);
    expect([...all].sort()).toEqual(expected);
    expect(new Set(all).size).toBe(all.length);
    expect(new Set(tabs.map((t) => t.id)).size).toBe(tabs.length);
  });
  it('opens on the reading group: the guide, the excluded cases and the limits, then the robustness and the provenance', () => {
    expect(plan[0].id).toBe('reading');
    expect(plan[0].tabs.map((t) => t.sections)).toEqual([['how', 'excluded', 'limits'], ['robustness'], ['provenance']]);
  });
  it('gives each built case a tab of its own, in the group of its question family', () => {
    for (const c of BUILT_SHOWN) {
      const g = plan.find((x) => x.tabs.some((t) => t.sections.includes(`case:${c}`)));
      expect(g?.id, c).toBe(benchGroupOf(c));
      expect(g?.tabs.find((t) => t.sections.includes(`case:${c}`))?.sections, c).toEqual([`case:${c}`]);
    }
  });
  it('places every case by its question family, never by the fallback', () => {
    for (const id of ids) {
      expect(Object.keys(FAMILY_GROUP), id).toContain(familyOf(id).id);
      expect(benchGroupOf(id)).toBe(FAMILY_GROUP[familyOf(id).id]);
    }
  });
  it('draws no group or tab without a section and drops the sections that do not exist', () => {
    const none = benchmarkPlan([], false, false);
    expect(none.map((g) => g.id)).toEqual(['reading']);
    expect(none[0].tabs.map((t) => t.sections)).toEqual([['how', 'limits'], ['provenance']]);
  });
});
