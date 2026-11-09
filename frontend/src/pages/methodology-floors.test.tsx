// ADR-0017 section 2.1 and ADR-0071 rule 5 on the Methodology page (gate ADR-0017.2 and G3): every topic of the method area names its
// kind, holds at least two captioned equations and a captioned figure, in both languages; every figure drawn from a table reads the
// same numbers as the table beside it; and no row of tabs of the page holds more than six peers.
import { useLangStore } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { methodologySection as conformal } from './methodology/market-conformal';
import { methodologySection as pla } from './methodology/market-pla-complement';
import { methodologySection as pcHazard } from './methodology/pc-hazard';
import { methodologySection as reject } from './methodology/reject-inference';
import { methodologySection as sequential } from './methodology/sequential-monitors';
import { methodologySection as withdrawals } from './methodology/withdrawals-anchored-pd';
import type { MethodologySection } from './methodologyRegistry';
import { REGISTERED_SECTIONS } from './methodologyRegistry';

const rows = vi.hoisted(() => [] as Array<{ id: string; tabs: Array<{ id: string }> }[]>);
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell')>();
  return {
    ...mod,
    TabGroups: ({ groups }: { groups: Array<{ id: string; tabs: Array<{ id: string }> }> }) => {
      rows.push(groups);
      return null;
    },
  };
});
// the import after the mock: the page reads the mocked TabGroups
const { Methodology } = await import('./Methodology');

type Lang = 'en' | 'es';
function html(el: ReactElement, lang: Lang): string {
  const initial = useLangStore.getInitialState();
  const before = initial.lang;
  initial.lang = lang;
  useLangStore.setState({ lang });
  try {
    return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  } finally {
    initial.lang = before;
    useLangStore.setState({ lang: before });
  }
}
afterEach(() => useLangStore.setState({ lang: 'en' }));

/** The topics that gained a figure, a second equation or a kind with the gate-15 unit. */
const TOPICS: MethodologySection[] = [pcHazard, withdrawals, sequential, conformal, pla, reject];
const numbers = (text: string): number[] => (text.match(/[+-]?\d+(?:[.,]\d+)?/g) ?? []).map((n) => parseFloat(n.replace(',', '.')));

describe('every topic of the method area carries its kind, two captioned equations and a captioned figure (ADR-0017.2)', () => {
  for (const topic of TOPICS) {
    for (const lang of ['en', 'es'] as const) {
      it(`${topic.id} (${lang})`, () => {
        const m = html(<topic.Body />, lang);
        expect(m).toMatch(/data-method-kind="(classical|learned)"/);
        expect((m.match(/class="equation-caption"/g) ?? []).length).toBeGreaterThanOrEqual(2);
        expect((m.match(/<figure class="figure">[\s\S]*?<figcaption/g) ?? []).length).toBeGreaterThanOrEqual(1);
        expect(m).not.toMatch(/NaN|undefined|Infinity/);
      });
    }
  }

  it('names the kind that fits the method: the neural survival rung is learned, the statistical ones are classical', () => {
    expect(html(<pcHazard.Body />, 'en')).toContain('data-method-kind="learned"');
    for (const topic of [withdrawals, sequential, conformal, pla, reject]) expect(html(<topic.Body />, 'en')).toContain('data-method-kind="classical"');
  });
});

describe('a measured figure reads the numbers of the table beside it, and nothing else (no unsourced value)', () => {
  for (const topic of TOPICS) {
    for (const lang of ['en', 'es'] as const) {
      it(`${topic.id} (${lang})`, () => {
        const m = html(<topic.Body />, lang);
        const bars = [...m.matchAll(/<rect data-series="([^"]+)" data-group="([^"]*)" data-value="([^"]+)"/g)];
        expect(bars.length, 'the figure draws bars').toBeGreaterThan(0);
        const table = [...m.matchAll(/<table[\s\S]*?<\/table>/g)].map((x) => x[0].replace(/<[^>]+>/g, ' ')).join(' ');
        const inTable = numbers(table);
        for (const [, series, group, value] of bars) {
          const v = Number(value);
          expect(
            inTable.some((n) => Math.abs(n - v) < 1e-9),
            `${topic.id} ${series} / ${group}: ${v} is not a number of the topic's tables`,
          ).toBe(true);
        }
      });
    }
  }
});

describe('no row of tabs of the Methodology page holds more than six peers (ADR-0071 rule 5, gate G3)', () => {
  it('the groups and the tabs of each, with every topic reachable once', () => {
    rows.length = 0;
    html(<Methodology />, 'en');
    const groups = rows[0];
    expect(groups.length).toBeLessThanOrEqual(6);
    for (const g of groups) expect(g.tabs.length, `${g.id}: ${g.tabs.map((x) => x.id).join(', ')}`).toBeLessThanOrEqual(6);
    const ids = groups.flatMap((g) => g.tabs.map((x) => x.id));
    expect(new Set(ids).size).toBe(ids.length);
    for (const s of REGISTERED_SECTIONS) expect(ids, `${s.id} is reachable`).toContain(s.id);
    for (const own of ['model-risk', 'scorecards', 'glass-box', 'boosting', 'migrations', 'discrimination', 'calibration', 'stability', 'transitions', 'size-and-power']) expect(ids).toContain(own);
  });

  it('the group of a section is the group the page lists it under', () => {
    rows.length = 0;
    html(<Methodology />, 'en');
    const where = new Map(rows[0].flatMap((g) => g.tabs.map((t) => [t.id, g.id] as const)));
    expect(where.get('migrations')).toBe('loss');
    expect(where.get('withdrawals-anchored-pd')).toBe('loss');
    expect(where.get('sequential-monitors')).toBe('market');
    expect(where.get('ml-validation')).toBe('tests');
    expect(where.get('governance')).toBe('models');
  });
});
