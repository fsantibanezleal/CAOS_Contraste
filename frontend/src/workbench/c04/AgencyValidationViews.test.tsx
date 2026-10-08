// CT-412, CT-407 and CT-415 for the agency variants' PD views (AgencyValidationViews), rendered on the server from the
// committed artifacts of S&P, Moody's and Fitch, in English and Spanish: every view is a card with its lane and its
// provenance, never waits as if loading, draws no empty chart (the series the chart receives are captured and read),
// names its definitions with ESMA's statement and its agency with CEREP's attribution, prints the artifact's numbers,
// and marks what matters (the rail's grade, the years the definitions differ most, the widest lifetime gap). Keep's
// long-run average, which the bake leaves out, is the pipeline's arithmetic: the same function reproduces every baked
// average, and the live ports that bound it reproduce the baked intervals.
import { readFileSync } from 'node:fs';
import { formatNumber, pick, useLangStore } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import { pdAgrestiCoull, pdJeffreys, pdWald } from '../../engine/transitions';
import type { C04AgencyOutputs, CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import {
  ByYearView,
  DefinitionsView,
  LifetimeView,
  PdByGradeView,
  averageOfYears,
  cohortGaps,
  emptyDefaultYears,
  lifetimeChart,
  pdByGradeChart,
  pdTable,
  widestYears,
} from './AgencyValidationViews';
import { DEFINITION_LABEL, ESMA_DEFINITIONS, GRADES, definitionsOf, gradeCounts, isAgency, makeSel, type AgencyVariant, type C04Sel } from './selection';

/** A value the artifact must hold: a null fails the test instead of reaching a comparison as 0. */
const nn = (x: number | null | undefined): number => {
  if (x === null || x === undefined) throw new Error('a null where the artifact must hold a number');
  return x;
};

// every chart the views draw is the shell's, rendered as it is; its props are kept for the assertions on what it draws
const captured = vi.hoisted(() => [] as UPlotChartProps[]);
vi.mock('@fasl-work/caos-app-shell/chart', async (importOriginal) => {
  const mod = await importOriginal<typeof import('@fasl-work/caos-app-shell/chart')>();
  return {
    ...mod,
    UPlotChart: (p: UPlotChartProps) => {
      captured.push(p);
      return mod.UPlotChart(p);
    },
  };
});

type Lang = 'en' | 'es';
/** The em-dash, the en-dash and the arrow, by code point (the house text never holds them). */
const DASHES = [0x2014, 0x2013, 0x2192].map((c) => String.fromCharCode(c));
const LANGS: Lang[] = ['en', 'es'];

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const all: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: a.variant_id, data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));
const agencies = all.filter((c) => isAgency(c.data.variant as VariantArtifact<unknown>));
const agencyOf = (id: string): AgencyVariant => all.find((c) => c.id === id)!.data.variant as unknown as AgencyVariant;
const dataOf = (id: string): CaseData => all.find((c) => c.id === id)!.data;

/** Server rendering reads zustand's initial state (useSyncExternalStore's server snapshot), not its current one: the
 * language is set on both for the render and put back after it. */
function html(el: ReactElement, lang: Lang = 'en'): string {
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

const decode = (s: string) => s.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const text = (s: string) => decode(s.replace(/<[^>]+>/g, ''));

interface Card {
  title: string;
  lane: string;
  provenance: string;
  body: string;
  note: string;
}
function figures(markup: string): Card[] {
  return [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)" data-lane="([^"]*)" data-provenance="([^"]*)"[^>]*>([\s\S]*?)<\/figure>/g)].map((m) => ({
    title: decode(m[1]),
    lane: m[2],
    provenance: m[3],
    body: m[4],
    note: text(/<p class="caos-plot-note">([\s\S]*?)<\/p>/.exec(m[4])?.[1] ?? ''),
  }));
}
function charts(markup: string): Array<{ series: number; axes: string[] }> {
  return [...markup.matchAll(/class="caos-chart[^"]*" data-series="(\d+)" data-axis-titles="([^"]*)"/g)].map((m) => ({ series: Number(m[1]), axes: decode(m[2]).split('|') }));
}
/** The cells of one table row, by the row's attribute (data-grade, data-year, data-row), as text. */
function row(markup: string, table: string, attr: string, value: string): Record<string, string> & { cells: string[]; className: string } {
  const t = new RegExp(`data-table="${table}"[\\s\\S]*?</table>`).exec(markup)?.[0] ?? '';
  const r = new RegExp(`<tr ${attr}="${value}"( class="([^"]*)")?>([\\s\\S]*?)</tr>`).exec(t);
  if (!r) throw new Error(`no row ${attr}="${value}" in ${table}`);
  const cells = [...r[3].matchAll(/<td([^>]*)>([\s\S]*?)<\/td>/g)];
  const out: Record<string, string> = {};
  for (const c of cells) {
    const col = /data-col="([^"]+)"/.exec(c[1])?.[1];
    if (col) out[col] = text(c[2]);
  }
  return Object.assign(out, { cells: cells.map((c) => text(c[2])), className: r[2] ?? '' });
}

const pct3 = (v: number | null, l: Lang) => formatNumber(nn(v) * 100, l, { digits: 3 });
const int = (v: number, l: Lang) => formatNumber(v, l, { decimals: 0 });
const pair = (lo: number | null, hi: number | null, l: Lang) => (l === 'en' ? `[${pct3(lo, l)}, ${pct3(hi, l)}]` : `[${pct3(lo, l)}; ${pct3(hi, l)}]`);

type View = (p: { sel: C04Sel | null }) => ReactElement;
const VIEWS: Array<[string, View]> = [
  ['PD by grade', PdByGradeView],
  ['By year', ByYearView],
  ['Definitions', DefinitionsView],
  ['Lifetime', LifetimeView],
];

beforeEach(() => {
  captured.length = 0;
});

describe('the agency variants: PD by grade, By year, Definitions, Lifetime', () => {
  it('are rendered for the three agencies of the case', () => {
    expect(agencies.map((c) => c.id)).toEqual(['sp', 'moodys', 'fitch']);
  });

  for (const c of agencies) {
    for (const lang of LANGS) {
      it(`every view is a card with its lane and provenance, never pending, never an empty chart, its agency and attribution named: ${c.id}, ${lang}`, () => {
        const o = (c.data.variant as unknown as AgencyVariant).outputs;
        for (const [name, View] of VIEWS) {
          captured.length = 0;
          const markup = html(<View sel={makeSel(c.data)} />, lang);
          const what = `${c.id} ${lang} ${name}`;
          const found = figures(markup);
          expect(found.length, `${what}: no card`).toBeGreaterThan(0);
          expect(markup, `${what}: waits as if loading`).not.toContain('data-state="loading"');
          for (const card of found) {
            expect(['replay', 'live'], `${what} ${card.title}: lane`).toContain(card.lane);
            expect(card.provenance, `${what} ${card.title}: provenance`).toBe('real');
            expect(card.body, `${what} ${card.title}: lane badge`).toMatch(/class="badge caos-lane caos-lane-(replay|live)"/);
            expect(card.note.length, `${what} ${card.title}: a card without its note`).toBeGreaterThan(80);
            expect(card.note, `${what} ${card.title}: attribution`).toContain(o.attribution);
            expect(card.note, `${what} ${card.title}: entity`).toContain(`${o.agency.name} (${o.agency.code}`);
          }
          const drawn = charts(markup);
          expect(drawn.length, `${what}: a chart`).toBe(captured.length);
          for (const ch of drawn) {
            expect(ch.series, `${what}: an empty chart`).toBeGreaterThan(0);
            expect(ch.axes.every((a) => a.trim().length > 3), `${what}: an axis without its title`).toBe(true);
          }
          for (const p of captured) {
            for (const s of p.series) expect(s.values.some((x) => x !== null), `${what}: a series with nothing to draw (${pick(s.label, 'en')})`).toBe(true);
            if (p.y.log) for (const s of p.series) expect(s.values.every((x) => x === null || x > 0), `${what}: a value of 0 on a log axis`).toBe(true);
          }
          const plain = text(markup);
          for (const bad of [...DASHES, 'NaN', 'undefined', 'Infinity', 'not available', 'no disponible']) {
            expect(plain.includes(bad), `${what}: "${bad}" in the view`).toBe(false);
          }
          // the language is the one asked for, all through
          if (lang === 'es') {
            expect(plain, what).toMatch(/cohorte|Cohorte/);
            expect(plain, what).not.toMatch(/\b(the cohort|Long-run average|Five-year window|cohort by cohort|What each definition counts)\b/);
          } else {
            expect(plain, what).not.toMatch(/\b(la cohorte|Promedio de largo plazo|Ventana de cinco años)\b/);
          }
        }
      });
    }
  }

  it('the views that compare definitions repeat ESMA\'s statement and name each definition', () => {
    for (const c of agencies) {
      for (const lang of LANGS) {
        for (const [name, View] of VIEWS) {
          const plain = text(html(<View sel={makeSel(c.data)} />, lang));
          expect(plain, `${c.id} ${lang} ${name}`).toContain(pick(ESMA_DEFINITIONS, lang));
        }
        const pd = text(html(<PdByGradeView sel={makeSel(c.data)} />, lang));
        for (const d of definitionsOf((c.data.variant as unknown as AgencyVariant).outputs)) expect(pd, `${c.id} ${lang} ${d}`).toContain(pick(DEFINITION_LABEL[d], lang));
      }
    }
  });

  it('a view on a variant that is not an agency says so instead of waiting, and only a missing selection is pending', () => {
    for (const id of ['markov', 'published']) {
      for (const [name, View] of VIEWS) {
        const markup = html(<View sel={makeSel(dataOf(id))} />);
        expect(markup, `${id} ${name}`).not.toContain('data-state="loading"');
        expect(figures(markup).length, `${id} ${name}`).toBe(1);
        expect(text(markup)).toContain('carries no CEREP cohorts');
      }
    }
    for (const [, View] of VIEWS) expect(html(<View sel={null} />)).toContain('data-state="loading"');
  });
});

describe('PD by grade', () => {
  it("draws every definition's long-run average, and for the rail's definition its pooled rate inside its Jeffreys bounds and its last five cohorts, the values the artifact holds, the rail's grade marked", () => {
    // the lines of every definition the agency has, then the rail's definition's pooled rate, its two bounds and its
    // last five cohorts (the intervals bound the pooled rate, so they are drawn with it, not with the average)
    const expected: Record<string, number> = { sp: 8, moodys: 6, fitch: 8 };
    for (const c of agencies) {
      const v = c.data.variant as unknown as AgencyVariant;
      const o = v.outputs;
      for (const chosen of ['d2', 'd4'] as const) {
        if (!o.lra[chosen]) continue;
        captured.length = 0;
        const markup = html(<PdByGradeView sel={makeSel(c.data, { grade: 4, definition: chosen })} />);
        // the main chart, and the tall screen's chart of the three intervals under the table
        expect(captured.length, c.id).toBe(2);
        const [p] = captured;
        expect(p.y.log).toBe(true);
        expect(p.series.length, `${c.id} ${chosen}`).toBe(expected[c.id]);
        expect(charts(markup)[0].series).toBe(expected[c.id]);
        expect(p.marks).toEqual([{ x: 5, label: 'BB' }]);
        // the seven grades and nothing else: every x is a grade the read-out can name
        expect(p.x.values).toEqual([1, 2, 3, 4, 5, 6, 7]);
        const named = (label: string) => p.series.find((s) => pick(s.label, 'en') === label)?.values;
        const drawable = (xs: Array<number | null>) => xs.map((x) => (x !== null && x > 0 ? x : null));
        for (const d of ['d2', 'd3', 'd4'] as const) {
          const l = o.lra[d];
          if (l) expect(named(pick(DEFINITION_LABEL[d], 'en')), `${c.id} ${d}`).toEqual(drawable(l.rate));
        }
        if (o.pd.keep) {
          const keep = GRADES.map((_, g) => averageOfYears(o.pd.keep!, g));
          expect(named(pick(DEFINITION_LABEL.keep, 'en')), c.id).toEqual(drawable(keep.map((a) => a.rate)));
        }
        const l = o.lra[chosen]!;
        const code = chosen.toUpperCase();
        expect(named(`${code}: pooled rate, defaults / n`), `${c.id} ${chosen}`).toEqual(drawable(l.pooled_rate));
        expect(named(`${code}: Jeffreys 95% of the pooled rate, upper`), `${c.id} ${chosen}`).toEqual(drawable(l.jeffreys.upper));
        expect(named(`${code}: Jeffreys 95% of the pooled rate, lower`), `${c.id} ${chosen}`).toEqual(drawable(l.jeffreys.lower));
        expect(named(`${code}: last five cohorts`), `${c.id} ${chosen}`).toEqual(drawable(l.last5));
        // no other definition's bounds are drawn
        const others = ['D2', 'D3', 'D4', 'Keep'].filter((x) => x !== code);
        expect(p.series.some((s) => others.some((x) => pick(s.label, 'en').startsWith(`${x}: `))), `${c.id} ${chosen}`).toBe(false);
        // the rail's definition is drawn thicker than the others
        const width = (label: string) => p.series.find((s) => pick(s.label, 'en') === label)?.width ?? 0;
        const other = chosen === 'd2' ? 'd3' : 'd2';
        expect(width(pick(DEFINITION_LABEL[chosen], 'en'))).toBeGreaterThan(width(pick(DEFINITION_LABEL[other], 'en')));
        // the tall screen's chart: the pooled rate and its three intervals, the long-run average a line
        const q = captured[1];
        expect(q.x.values).toEqual([1, 2, 3, 4, 5, 6, 7]);
        expect(q.series.find((s) => pick(s.label, 'en') === 'Pooled, defaults / n')?.values, `${c.id} ${chosen}`).toEqual(drawable(l.pooled_rate));
        expect(q.series.find((s) => pick(s.label, 'en') === 'Wald 95%, upper')?.values, `${c.id} ${chosen}`).toEqual(drawable(l.wald.upper));
        expect(q.series.find((s) => pick(s.label, 'en') === 'Agresti-Coull 95%, upper')?.values, `${c.id} ${chosen}`).toEqual(drawable(l.agresti_coull.upper));
      }
    }
  });

  it("prints the rail's definition grade by grade as the artifact holds it: the average, the pooled counts and the three intervals", () => {
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      for (const d of ['d2', 'd3', 'd4'] as const) {
        const l = o.lra[d];
        if (!l) continue;
        for (const lang of LANGS) {
          const markup = html(<PdByGradeView sel={makeSel(c.data, { definition: d })} />, lang);
          expect(markup).toContain(`data-table="lra" data-definition="${d}"`);
          const tableCard = figures(markup)[1];
          expect(tableCard.lane, `${c.id} ${d}`).toBe('replay');
          GRADES.forEach((g, i) => {
            const r = row(markup, 'lra', 'data-grade', g);
            const what = `${c.id} ${d} ${lang} ${g}`;
            expect(r.rate, what).toBe(pct3(l.rate[i], lang));
            expect(r.counts, what).toBe(`${int(l.defaults[i], lang)} / ${int(l.n[i], lang)}`);
            expect(r.jeffreys, what).toBe(pair(l.jeffreys.lower[i], l.jeffreys.upper[i], lang));
            expect(r.wald, what).toBe(pair(l.wald.lower[i], l.wald.upper[i], lang));
            expect(r['agresti-coull'], what).toBe(pair(l.agresti_coull.lower[i], l.agresti_coull.upper[i], lang));
            expect(r.cohorts, what).toBe(int(l.cohorts[i], lang));
            expect(r.pooled, what).toBe(pct3(l.pooled_rate[i], lang));
            expect(r.last5, what).toBe(pct3(l.last5[i], lang));
            expect(r.className, what).toBe(i === 6 ? 'ct-current' : '');
          });
        }
      }
    }
  });

  it('says where the average of the yearly rates lies outside the interval of the pooled counts', () => {
    // S&P's B under D2: the average of its yearly rates, 2.96%, against the pooled 2.63% and its interval
    const sp = dataOf('sp');
    const note = figures(html(<PdByGradeView sel={makeSel(sp)} />))[1].note;
    expect(note).toContain("B's average, 2.96\u00a0%, lies outside [2.47, 2.79]\u00a0%");
    expect(note).toContain('each grade\'s average is over 26 cohorts');
  });

  it("Keep's long-run average is the pipeline's arithmetic: it reproduces every baked average, cohort count and last-five mean", () => {
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      for (const d of ['d2', 'd3', 'd4'] as const) {
        const l = o.lra[d];
        const grid = o.pd[d];
        if (!l || !grid) continue;
        GRADES.forEach((_, g) => {
          const a = averageOfYears(grid, g);
          const what = `${c.id} ${d} ${GRADES[g]}`;
          expect(a.cohorts, what).toBe(l.cohorts[g]);
          // the artifact keeps nine significant digits (stages/export.py, SIG = 9): the yearly rates and the baked mean
          // each carry half a unit of the ninth digit
          expect(Math.abs((a.rate as number) - nn(l.rate[g])), what).toBeLessThanOrEqual(1e-8 * nn(l.rate[g]) + 1e-15);
          expect(Math.abs((a.last5 as number) - nn(l.last5[g])), what).toBeLessThanOrEqual(1e-8 * nn(l.last5[g]) + 1e-15);
        });
      }
    }
  });

  it("Keep's table is live: its counts are the transition page's defaults over the whole cohorts, bounded by the ports that reproduce the baked intervals", () => {
    for (const id of ['sp', 'fitch']) {
      const v = agencyOf(id);
      const o = v.outputs;
      // the ports reproduce the bake's own intervals from the bake's own counts (D4, the same page as Keep), within the
      // artifact's nine significant digits
      const l4 = o.lra.d4!;
      GRADES.forEach((_, g) => {
        const close = (a: number, b: number | null) => expect(Math.abs(a - nn(b)), `${id} ${GRADES[g]}`).toBeLessThanOrEqual(1e-8 * Math.abs(nn(b)) + 1e-15);
        const w = pdWald(l4.defaults[g], l4.n[g], { level: 0.95 });
        const ac = pdAgrestiCoull(l4.defaults[g], l4.n[g], { level: 0.95 });
        const j = pdJeffreys(l4.defaults[g], l4.n[g], { level: 0.95 });
        close(w.lower, l4.wald.lower[g]);
        close(w.upper, l4.wald.upper[g]);
        close(ac.lower, l4.agresti_coull.lower[g]);
        close(ac.upper, l4.agresti_coull.upper[g]);
        close(j.lower, l4.jeffreys.lower[g]);
        close(j.upper, l4.jeffreys.upper[g]);
      });
      const keep = pdTable(v, 'keep');
      expect(keep.live).toBe(true);
      keep.rows.forEach((r, g) => {
        const counts = gradeCounts(v, 'keep', g)!;
        expect(r.defaults).toBe(l4.defaults[g]);
        expect(r.n).toBe(o.cohorts.reduce((s, c) => s + c.size[g], 0));
        expect(r.n).toBe(counts.n);
        expect(r.jeffreys).toEqual({ lower: pdJeffreys(counts.defaults, counts.n).lower, upper: pdJeffreys(counts.defaults, counts.n).upper });
        expect(r.rate).toBe(averageOfYears(o.pd.keep!, g).rate);
      });
      const markup = html(<PdByGradeView sel={makeSel(dataOf(id), { definition: 'keep' })} />);
      const [chartCard, tableCard] = figures(markup);
      expect(chartCard.lane).toBe('replay');
      expect(tableCard.lane).toBe('live');
      expect(tableCard.note).toContain('computed in your browser');
      expect(row(markup, 'lra', 'data-grade', 'CCC-C').jeffreys).toBe(pair(keep.rows[6].jeffreys.lower!, keep.rows[6].jeffreys.upper!, 'en'));
    }
  });

  it("Moody's has no D4 or Keep: a rail left on either shows D2 and says why; its chart draws D2 and D3 only", () => {
    for (const d of ['d4', 'keep'] as const) {
      const markup = html(<PdByGradeView sel={makeSel(dataOf('moodys'), { definition: d })} />);
      expect(markup).toContain('data-table="lra" data-definition="d2"');
      expect(figures(markup)[1].note).toContain("The transition page of Moody's has no default category");
    }
    // the two definitions' averages, and the rail's (D2) pooled rate, bounds and last five cohorts: nothing of D4 or Keep
    const chart = pdByGradeChart(agencyOf('moodys'), 'd2');
    expect(new Set(chart.series.map((s) => pick(s.label, 'en').split(':')[0]))).toEqual(new Set([pick(DEFINITION_LABEL.d2, 'en'), pick(DEFINITION_LABEL.d3, 'en'), 'D2']));
  });

  it("says which values a log axis cannot hold, and a grade's name picks it", () => {
    const sp = agencyOf('sp');
    const chart = pdByGradeChart(sp, 'd2');
    expect(chart.zeroRates).toEqual([{ grade: 0, defs: ['d2', 'd3', 'd4', 'keep'] }]);
    const markup = html(<PdByGradeView sel={makeSel(dataOf('sp'))} />);
    expect(figures(markup)[0].note).toContain('is left out (the table prints it): the long-run average of AAA under D2, D3, D4 and Keep');
    // grades that share their definitions are named together: Fitch's transition page has no default in AAA, AA and A
    expect(pdByGradeChart(agencyOf('fitch'), 'd2').zeroRates).toEqual([0, 1, 2].map((grade) => ({ grade, defs: ['d4', 'keep'] })));
    expect(figures(html(<PdByGradeView sel={makeSel(dataOf('fitch'))} />))[0].note).toContain('the long-run average of AAA, AA and A under D4 and Keep');
    expect(figures(html(<PdByGradeView sel={makeSel(dataOf('fitch'))} />, 'es'))[0].note).toContain('el promedio de largo plazo de AAA, AA y A bajo D4 y Con retiros');
    // every grade's name is a button that picks it (sel.act.setGrade); the rail's is pressed
    const buttons = [...markup.matchAll(/<button type="button" class="ct-linkbutton" aria-pressed="(true|false)">([^<]+)<\/button>/g)];
    expect(buttons.map((b) => b[2])).toEqual([...GRADES]);
    expect(buttons.filter((b) => b[1] === 'true').map((b) => b[2])).toEqual(['CCC-C']);
  });
});

describe('By year', () => {
  it("draws the rail's grade under every definition, cohort by cohort, the years where the definitions differ most marked", () => {
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      const defs = definitionsOf(o);
      for (const g of [0, 3, 6]) {
        captured.length = 0;
        html(<ByYearView sel={makeSel(c.data, { grade: g })} />);
        const [p] = captured;
        const what = `${c.id} ${GRADES[g]}`;
        expect(p.series.map((s) => s.label), what).toEqual(defs.map((d) => DEFINITION_LABEL[d]));
        // the cohorts' calendar years (written without a group separator), and nothing drawn outside them
        defs.forEach((d, i) => expect(p.series[i].values, `${what} ${d}`).toEqual(o.pd[d]!.map((r) => r[g])));
        expect(p.x.values, what).toEqual(o.cohorts.map((k) => Number(k.label)));
        expect(p.x.format, what).toEqual({ decimals: 0, grouping: false });
        expect(p.y.log, what).toBeFalsy();
        // the marked years: the three widest gaps between the definitions, recomputed here from the artifact
        const spread = o.cohorts.map((_, k) => {
          // a definition without a rate that year (no rated obligors in the grade) is skipped, as in the view
          const vals = defs.map((d) => o.pd[d]![k][g]).filter((x): x is number => x !== null);
          return vals.length > 1 ? Math.max(...vals) - Math.min(...vals) : 0;
        });
        const top = spread
          .map((s, k) => ({ s, k }))
          .filter((e) => e.s > 0)
          .sort((a, b) => b.s - a.s || a.k - b.k)
          .slice(0, 3)
          .map((e) => e.k)
          .sort((a, b) => a - b);
        expect(widestYears(o, g).widest, what).toEqual(top);
        // a run of consecutive marked years shares one label, so neighbouring labels never print over each other
        const marks = top.map((k, i) => {
          const year = Number(o.cohorts[k].label);
          if (i > 0 && k === top[i - 1] + 1) return { x: year, label: '' };
          let end = i;
          while (end + 1 < top.length && top[end + 1] === top[end] + 1) end++;
          return { x: year, label: end > i ? `${year}-${o.cohorts[top[end]].label}` : String(year) };
        });
        expect(p.marks, what).toEqual(marks);
        if (c.id === 'sp' && g === 6) expect(p.marks).toEqual([{ x: 2009, label: '2009' }, { x: 2019, label: '2019-2020' }, { x: 2020, label: '' }]);
      }
    }
  });

  it('prints each cohort: its size and each definition\'s rate, the marked years highlighted', () => {
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      const defs = definitionsOf(o);
      for (const lang of LANGS) {
        const markup = html(<ByYearView sel={makeSel(c.data)} />, lang);
        const marked = new Set(widestYears(o, 6).widest);
        o.cohorts.forEach((k, i) => {
          const r = row(markup, 'by-year', 'data-year', k.label);
          const what = `${c.id} ${lang} ${k.label}`;
          expect(r.size, what).toBe(int(k.size[6], lang));
          for (const d of defs) expect(r[d], `${what} ${d}`).toBe(pct3(o.pd[d]![i][6], lang));
          expect(r['tab2-cohort'], what).toBe(int(k.defaulted_cohort![6], lang));
          expect(r.defaulted, what).toBe(int(k.defaulted![6], lang));
          expect(r.withdrawn, what).toBe(int(k.withdrawn[6], lang));
          expect(r.className === 'ct-current', what).toBe(marked.has(i));
        });
      }
    }
  });

  it("says where Fitch's transition page has no default at all while its default-rate page has, and where nothing defaulted", () => {
    expect(emptyDefaultYears(agencyOf('fitch').outputs).map((y) => y.year)).toEqual([2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014]);
    expect(emptyDefaultYears(agencyOf('sp').outputs)).toEqual([]);
    expect(emptyDefaultYears(agencyOf('moodys').outputs)).toEqual([]);
    // the empty years and the rated defaulters the default-rate page counts in them, from the artifact
    const n = emptyDefaultYears(agencyOf('fitch').outputs).reduce((s, y) => s + y.defaulted, 0);
    expect(n).toBe(189);
    const fitch = figures(html(<ByYearView sel={makeSel(dataOf('fitch'))} />)).map((f) => f.note).join(' ');
    expect(fitch).toContain(`From 2006 to 2014 the transition page counts no rating in default at the year's end in any grade, while the default-rate page counts ${n} rated defaulters`);
    const spAaa = figures(html(<ByYearView sel={makeSel(dataOf('sp'), { grade: 0 })} />))[0].note;
    expect(spAaa).toContain('No rating in AAA defaulted in any cohort under any definition');
    const es = figures(html(<ByYearView sel={makeSel(dataOf('fitch'))} />, 'es')).map((f) => f.note).join(' ');
    expect(es).toContain('De 2006 a 2014 la página de transiciones no cuenta ninguna calificación en incumplimiento');
  });
});

describe('Definitions', () => {
  it('draws the pooled ratios to D2 the artifact holds, against 1, the rail\'s grade marked', () => {
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      captured.length = 0;
      html(<DefinitionsView sel={makeSel(c.data, { grade: 5 })} />);
      const [p] = captured;
      const gap = o.definition_gap;
      const want = [...(gap.d4_over_d2 ? [gap.d4_over_d2] : []), ...(gap.d3_over_d2 ? [gap.d3_over_d2] : [])];
      expect(p.series.map((s) => s.values), c.id).toEqual([...want, [1, 1, 1, 1, 1, 1, 1]]);
      expect(p.x.values).toEqual([1, 2, 3, 4, 5, 6, 7]);
      expect(p.marks).toEqual([{ x: 6, label: 'B' }]);
    }
  });

  it("lists every year where tab 2's cohort differs from tab 4's, grade by grade, with the label gap", () => {
    // recomputed here from the cohorts: S&P 18 of 26, Moody's 7 of 26, Fitch 9 of 24 (CT-402)
    const counts: Record<string, string> = { sp: '18 of 26', moodys: '7 of 26', fitch: '9 of 24' };
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      const years = o.cohorts.filter((k) => k.defaulted_cohort && k.defaulted_cohort.some((x, g) => x !== k.size[g]));
      expect(cohortGaps(o).map((x) => x.label), c.id).toEqual(years.map((k) => k.label));
      for (const lang of LANGS) {
        const markup = html(<DefinitionsView sel={makeSel(c.data)} />, lang);
        const rows = [...(new RegExp('data-table="tab2-cohorts"[\\s\\S]*?</table>').exec(markup)?.[0] ?? '').matchAll(/<tr data-year="(\d+)"/g)].map((m) => m[1]);
        expect(rows, `${c.id} ${lang}`).toEqual(years.map((k) => k.label));
        for (const k of years) {
          const r = row(markup, 'tab2-cohorts', 'data-year', k.label);
          const gap = k.tab2_gap as number;
          expect(r.gap, `${c.id} ${k.label}`).toBe(`${gap > 0 ? '+' : ''}${pct3(gap, lang)}`);
          const cells = GRADES.map((g, i) => ({ g, a: k.defaulted_cohort![i], b: k.size[i] })).filter((x) => x.a !== x.b);
          expect(r.cells[1]).toBe(cells.map((x) => `${x.g} ${int(x.a, lang)} ${lang === 'en' ? 'against' : 'contra'} ${int(x.b, lang)}`).join('; '));
          expect(r.className === 'ct-current').toBe(k.defaulted_cohort![6] !== k.size[6]);
        }
        if (lang === 'en') expect(figures(markup)[2].note).toContain(counts[c.id]);
      }
    }
  });

  it("states what each definition counts with ESMA's statement, and the rates and ratios at the rail's grade", () => {
    for (const c of agencies) {
      const v = c.data.variant as unknown as AgencyVariant;
      const o = v.outputs;
      const markup = html(<DefinitionsView sel={makeSel(c.data)} />);
      expect(markup).toContain('data-esma="definitions"');
      for (const d of ['d2', 'd3', 'd4'] as const) {
        const r = new RegExp(`<tr data-definition="${d}"[^>]*>([\\s\\S]*?)</tr>`).exec(markup)![1];
        const l = o.lra[d];
        if (!l) {
          expect(text(r), c.id).toContain('not on these pages');
          continue;
        }
        expect(text(r)).toContain(pct3(l.pooled_rate[6], 'en'));
      }
      const d3 = new RegExp('<tr data-definition="d3"[^>]*>([\\s\\S]*?)</tr>').exec(markup)![1];
      expect(text(d3)).toContain(formatNumber(o.definition_gap.d3_over_d2![6] as number, 'en', { decimals: 3 }));
      const keep = new RegExp('<tr data-definition="keep"[^>]*>([\\s\\S]*?)</tr>').exec(markup)![1];
      if (o.pd.keep) {
        const k = gradeCounts(v, 'keep', 6)!;
        expect(text(keep)).toContain(pct3(k.defaults / k.n, 'en'));
      }
    }
    // in CEREP's data tab 3's events are tab 2's defaulted ratings, so D3 over D2 is a ratio of cohorts: said, not drawn
    const note = figures(html(<DefinitionsView sel={makeSel(dataOf('sp'))} />))[0].note;
    expect(note).toContain("D3 over D2 is tab 2's pooled cohort over tab 4's");
    expect(note).toContain("At CCC-C the transition page's default column holds 29.4\u00a0% of D2's pooled rate");
  });
});

describe('Lifetime (CT-415)', () => {
  it('draws what each window lived against the projections, the widest gap marked; Moody\'s tab 2 alone', () => {
    const expected: Record<string, number> = { sp: 6, moodys: 1, fitch: 6 };
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      captured.length = 0;
      html(<LifetimeView sel={makeSel(c.data)} />);
      const [p] = captured;
      expect(p.series.length, c.id).toBe(expected[c.id]);
      const n = o.lifetime.length;
      expect(p.x.values).toEqual(o.lifetime.map((_, i) => i + 1));
      expect(n).toBeGreaterThan(0);
      const lived = p.series[0];
      expect(lived.mode).toBe('points');
      expect(lived.values).toEqual(o.lifetime.map((w) => w.observed.cumulative_d2![6]));
      if (c.id !== 'moodys') {
        const chained = p.series.find((s) => pick(s.label, 'en') === 'Chained, withdrawals a state')!;
        expect(chained.values).toEqual(o.lifetime.map((w) => w.projected.chain_state[6]));
        const gaps = o.lifetime.map((w) => Math.abs(nn(w.observed.cumulative_d2![6]) - (w.projected.chain_state[6] as number)));
        const k = gaps.indexOf(Math.max(...gaps));
        expect(lifetimeChart(o, 6).marked).toBe(k);
        expect(p.marks).toEqual([{ x: k + 1, label: { en: 'widest gap', es: 'mayor brecha' } }]);
      } else {
        expect(p.marks).toEqual([]);
        expect(figures(html(<LifetimeView sel={makeSel(c.data)} />))[0].note).toContain("The transition page of Moody's has no default category");
      }
    }
  });

  it('prints every window as the artifact holds it, and says what each default share counts', () => {
    for (const c of agencies) {
      const o = (c.data.variant as unknown as AgencyVariant).outputs;
      for (const lang of LANGS) {
        const markup = html(<LifetimeView sel={makeSel(c.data, { grade: 5 })} />, lang);
        const cells = (key: string) => row(markup, 'lifetime', 'data-row', key).cells.slice(1);
        const shares = (vals: Array<number | null>) => vals.map((x) => (x === null ? '-' : pct3(x, lang)));
        // every row the artifact gives for some window, in the chart's order; a row it gives for none is left out
        const expectRow = (key: string, vals: Array<number | null>) => {
          if (vals.every((x) => x === null)) expect(markup, `${c.id} ${lang} ${key}`).not.toContain(`data-row="${key}"`);
          else expect(cells(key), `${c.id} ${lang} ${key}`).toEqual(shares(vals));
        };
        expect(cells('size')).toEqual(o.lifetime.map((w) => int(w.size[5], lang)));
        expectRow('cumulative_d2', o.lifetime.map((w) => w.observed.cumulative_d2![5]));
        expectRow('default_end', o.lifetime.map((w) => w.observed.default_end[5]));
        expectRow('withdrawn_end', o.lifetime.map((w) => w.observed.withdrawn_end[5]));
        for (const k of ['chain_state', 'chain_exclude', 'pooled_power', 'em', 'chain_state_withdrawn'] as const) {
          expectRow(k, o.lifetime.map((w) => w.projected[k][5]));
        }
        const order = [...markup.matchAll(/<tr data-row="([^"]+)"/g)].map((m) => m[1]);
        expect(order, `${c.id} ${lang}`).toEqual(
          c.id === 'moodys'
            ? ['size', 'cumulative_d2', 'withdrawn_end', 'chain_state_withdrawn']
            : ['size', 'cumulative_d2', 'default_end', 'chain_state', 'chain_exclude', 'pooled_power', 'em', 'withdrawn_end', 'chain_state_withdrawn'],
        );
      }
      const [chartCard] = figures(html(<LifetimeView sel={makeSel(c.data)} />));
      if (c.id === 'moodys') {
        // no default category: neither a share in default at the end nor a chain to read it from, said and titled so
        expect(chartCard.title).toBe("Moody's CCC-C: rated defaulters within each five-year window (tab 2)");
        expect(chartCard.note).toContain("has no default category, so there is no share in default at a window's end and no projection of one");
        expect(chartCard.note).not.toContain('Lines, projected');
        continue;
      }
      expect(chartCard.title).toBe(`${c.id === 'sp' ? 'S&P' : 'Fitch'} CCC-C: five years lived against the chained one-year matrices`);
      expect(chartCard.note).toContain('The chained default column counts ratings in default at some year-end');
      expect(chartCard.note).toContain('a rating that defaulted and was then withdrawn leaves it');
      expect(chartCard.note).toContain('the same in every window');
    }
    const fitch = figures(html(<LifetimeView sel={makeSel(dataOf('fitch'))} />))[0].note;
    // Fitch's annual transition pages hold no default from 2006 to 2014: the 2010-2014 window lies wholly inside, and
    // its own five-year page shows no default at its end either (read from the artifact, not assumed)
    expect(agencyOf('fitch').outputs.lifetime[0].observed.default_end.every((x) => x === 0)).toBe(true);
    expect(fitch).toContain(
      "The transition pages hold no default from 2006 to 2014: the chain never defaults in 2010-2014, nor does its own page show one; a 0 there is the page's, not the cohort's.",
    );
    expect(figures(html(<LifetimeView sel={makeSel(dataOf('sp'))} />))[0].note).not.toContain("the page's, not the cohort's");
  });
});

describe('the reader\'s selection reaches every view', () => {
  it('a grade or a definition picked on the rail changes what the view shows', () => {
    const sp = dataOf('sp');
    for (const [name, View] of VIEWS) {
      expect(html(<View sel={makeSel(sp, { grade: 6 })} />), name).not.toBe(html(<View sel={makeSel(sp, { grade: 4 })} />));
    }
    for (const [name, View] of VIEWS.slice(0, 2)) {
      expect(html(<View sel={makeSel(sp, { definition: 'd2' })} />), name).not.toBe(html(<View sel={makeSel(sp, { definition: 'd4' })} />));
    }
  });
});

describe('the text of these views', () => {
  it('has no em-dash, en-dash or arrow anywhere in its source', () => {
    for (const file of ['AgencyValidationViews.tsx', 'AgencyValidationViews.test.tsx']) {
      const src = readFileSync(new URL(file, import.meta.url), 'utf8');
      for (const bad of DASHES) expect(src.includes(bad), `${file}: ${bad}`).toBe(false);
    }
  });

  it('every output the views read exists in each agency artifact', () => {
    for (const c of agencies) {
      const o: C04AgencyOutputs = (c.data.variant as unknown as AgencyVariant).outputs;
      for (const key of ['pd', 'lra', 'cohorts', 'definition_gap', 'lifetime', 'agency', 'attribution'] as const) expect(o[key], `${c.id} ${key}`).toBeDefined();
    }
  });
});
