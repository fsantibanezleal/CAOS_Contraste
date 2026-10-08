// CT-412, the agency variants' Markov checks (web.md, "Agency variants": Markov tests, Mobility, Semesters), rendered
// on the server from the committed artifacts in English and in Spanish: every card states its lane and provenance and
// names the agency's entity with CEREP's attribution; nothing waits as Pending; no chart is drawn empty, and a log axis
// is never given a value below LOG_FLOOR (uPlot's log ticks never end below about 1e-23: measured, a frozen page and a
// blank chart). Every number printed or drawn is checked against the artifact's JSON, computed here, never through the
// module's own helpers; the lights are recomputed from the p-values and the committed thresholds. The series each
// chart receives are captured from the shell's chart and read.
import { formatNumber, pick, useLangStore } from '@fasl-work/caos-app-shell';
import type { UPlotChartProps } from '@fasl-work/caos-app-shell/chart';
import { readFileSync } from 'node:fs';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { C04AgencyOutputs, CaseManifest, ModelsArtifact, TestRow, VariantArtifact } from '../../lib/contract.types';
import { COMMITTED } from '../../lib/policy';
import { FMT, LOG_FLOOR, MobilityView, SemestersView, TestsView, YEAR0, YEAR_FORMAT } from './AgencyTestsViews';
import { DEFINITION_LABEL, isAgency, makeSel, type AgencyVariant, type C04Sel } from './selection';

/** A value the artifact must hold: a null fails the test instead of reaching a comparison as 0. */
const nn = (x: number | null | undefined): number => {
  if (x === null || x === undefined) throw new Error('a null where the artifact must hold a number');
  return x;
};

// every chart the views draw is the shell's, rendered as it is; its props are kept to read what it was given
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
const LANGS: Lang[] = ['en', 'es'];
const GRADES = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC-C'];

/** The formats the views print with, written out here: a changed format is a change to both files. */
const F = {
  statistic: { digits: 4 },
  dof: { decimals: 0 },
  perDof: { decimals: 1 },
  p: { digits: 2 },
  evidence: { digits: 3 },
  index: { decimals: 3 },
  rate: { percent: true, decimals: 2 },
  count: { decimals: 0 },
  l1: { decimals: 3 },
  pd: { percent: true, digits: 3 },
} as const;
const AMBER = 0.05;
const RED = 0.01;
const FLOOR = 1e-20;

/** The en-dash, the em-dash and the arrows (U+2190 to U+21FF, U+27F5 to U+27FF), by code point: the house text never
 * holds them, and neither does this file. */
const cp = (...c: number[]) => String.fromCharCode(...c);
const DASHES = new RegExp(`[${cp(0x2013, 0x2014)}${cp(0x2190)}-${cp(0x21ff)}${cp(0x27f5)}-${cp(0x27ff)}]`);

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const variants: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: String(a.variant_id), data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));

interface Agency {
  id: string;
  data: CaseData;
  v: AgencyVariant;
  o: C04AgencyOutputs;
}
const agencies: Agency[] = variants
  .filter((c) => isAgency(c.data.variant as VariantArtifact<unknown>))
  .map((c) => ({ id: c.id, data: c.data, v: c.data.variant as unknown as AgencyVariant, o: (c.data.variant as unknown as AgencyVariant).outputs }));
const agency = (id: string): Agency => {
  const a = agencies.find((x) => x.id === id);
  if (!a) throw new Error(`no agency variant ${id}`);
  return a;
};
/** An agency variant changed in memory (a deep copy): the cases the committed artifacts do not reach. */
function altered(a: Agency, change: (v: AgencyVariant) => void): Agency {
  const v = structuredClone(a.v);
  change(v);
  return { id: `${a.id}-altered`, data: { ...a.data, variant: v as unknown as VariantArtifact }, v, o: v.outputs };
}

/** Server markup in a language: the shell's store answers a server render with its initial state. */
function html(el: ReactElement, lang: Lang = 'en'): string {
  const init = useLangStore.getInitialState() as { lang: Lang };
  const was = init.lang;
  init.lang = lang;
  try {
    return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  } finally {
    init.lang = was;
  }
}
/** The markup and the charts it drew. */
function render(el: ReactElement, lang: Lang = 'en'): { markup: string; drawn: UPlotChartProps[] } {
  captured.length = 0;
  const markup = html(el, lang);
  return { markup, drawn: [...captured] };
}

/** React's escaping of text and attribute values, and its inverse. */
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const unesc = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
const text = (markup: string) => unesc(markup.replace(/<[^>]+>/g, ' ')).replace(/[ \t\r\n]+/g, ' ');

interface Card {
  title: string;
  lane: string;
  provenance: string;
  body: string;
  note: string;
}
function cards(markup: string): Card[] {
  return [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)" data-lane="([^"]*)" data-provenance="([^"]*)"[^>]*>([\s\S]*?)<\/figure>/g)].map((m) => ({
    title: unesc(m[1]),
    lane: m[2],
    provenance: m[3],
    body: m[4],
    note: text(m[4].match(/class="caos-plot-note"[^>]*>([\s\S]*?)<\/p>/)?.[1] ?? ''),
  }));
}
const card = (markup: string, title: string): Card => {
  const c = cards(markup).find((x) => x.title === title);
  if (!c) throw new Error(`no card "${title}" in ${cards(markup).map((x) => x.title).join(' | ')}`);
  return c;
};
const hostCharts = (markup: string) => [...markup.matchAll(/data-series="(\d+)" data-axis-titles="([^"]*)"/g)].map((m) => ({ series: Number(m[1]), axes: m[2].split('|') }));
/** The markup of one table row, by an attribute of the row (data-year, data-segment). */
function rowOf(markup: string, table: string, attr: string, value: string): string {
  const t = markup.match(new RegExp(`data-table="${table}"[\\s\\S]*?</table>`))?.[0] ?? '';
  return t.match(new RegExp(`<tr ${attr}="${value}"[^>]*>[\\s\\S]*?</tr>`))?.[0] ?? '';
}
/** A row's cells: their attributes and their text. */
const cellsOf = (row: string) => [...row.matchAll(/<td([^>]*)>([\s\S]*?)<\/td>/g)].map((m) => ({ attrs: m[1], text: text(m[2]).trim() }));
const lightAttr = (attrs: string) => attrs.match(/data-light="([^"]+)"/)?.[1];
const chartBy = (drawn: UPlotChartProps[], yLabel: string) => drawn.find((p) => pick(p.y.label, 'en') === yLabel);

/** The artifact's numbers, read here. */
const testRow = (a: Agency, id: string, segment: string): TestRow | undefined => a.v.tests.find((t) => t.test_id === id && t.model_id === a.o.agency.code && t.segment === segment);
const lightByP = (p: number | null | undefined) => (p === null || p === undefined ? 'not_evaluated' : p < RED ? 'red' : p < AMBER ? 'amber' : 'green');
const LIGHT_WORD: Record<string, Record<Lang, string>> = { red: { en: 'red', es: 'rojo' }, amber: { en: 'amber', es: 'ámbar' }, green: { en: 'green', es: 'verde' } };
const pPrinted = (p: number, lang: Lang) => (p === 0 ? '< 1E-300' : formatNumber(p, lang, F.p));
const size = (c: { size: number[] } | undefined) => (c ? c.size.reduce((s, x) => s + x, 0) : null);
const yearsOf = (labels: string[]) => labels.map(Number);
/** "2001 and 2021", "2008 to 2009": the house's list of years. */
function listOf(years: number[], lang: Lang): string {
  const ys = [...years].sort((a, b) => a - b);
  const runs: string[] = [];
  for (let i = 0; i < ys.length; ) {
    let j = i;
    while (j + 1 < ys.length && ys[j + 1] === ys[j] + 1) j++;
    runs.push(j > i ? `${ys[i]} ${lang === 'en' ? 'to' : 'a'} ${ys[j]}` : String(ys[i]));
    i = j + 1;
  }
  return runs.length < 2 ? runs.join('') : `${runs.slice(0, -1).join(', ')} ${lang === 'en' ? 'and' : 'y'} ${runs[runs.length - 1]}`;
}
/** The grade with the largest statistic per degree of freedom, in the form the row reports. */
function furthest(row: TestRow): { grade: string; ratio: number } {
  const form = row.extras.form as string;
  const rows = row.extras.rows as Array<Record<string, number>>;
  let best = { grade: '', ratio: -1 };
  for (const r of rows) if (r.dof > 0 && r[form] / r.dof > best.ratio) best = { grade: GRADES[r.row], ratio: r[form] / r.dof };
  return best;
}

const VIEWS: Array<[string, (p: { sel: C04Sel | null }) => ReactElement, number]> = [
  ['Tests', TestsView, 2],
  ['Mobility', MobilityView, 2],
  ['Semesters', SemestersView, 2],
];
const TESTS_Y = '-log10 p (2 is p = 0.01)';
const MOBILITY_Y = 'Index, or default rate as a share';
const L1_Y = 'L1 distance (sum over the cells)';
const PD_Y = (g: string) => `PD of ${g} (%, log scale)`;

/** What every chart was given: data series with a value, one value per x, a title on both axes, a height that fills
 * its card, marks on the axis, and on a log axis no value below the floor. */
function expectDrawable(p: UPlotChartProps, where: string, lang: Lang) {
  expect(p.height, where).toBe('fill');
  expect(pick(p.x.label, lang).length, `${where}: the x axis title`).toBeGreaterThan(0);
  expect(pick(p.y.label, lang).length, `${where}: the y axis title`).toBeGreaterThan(0);
  expect(p.series.length, `${where}: no series`).toBeGreaterThan(0);
  for (const s of p.series) {
    const at = `${where}, ${pick(s.label, 'en')}`;
    expect(s.values.length, at).toBe(p.x.values.length);
    const vals = s.values.filter((x): x is number => x !== null);
    expect(vals.length, `${at}: an empty series`).toBeGreaterThan(0);
    for (const x of vals) {
      expect(Number.isFinite(x), at).toBe(true);
      if (p.y.log) expect(x, `${at}: a value below the log axis floor`).toBeGreaterThanOrEqual(FLOOR);
    }
  }
  for (const m of p.marks ?? []) expect(p.x.values.includes(m.x), `${where}: a mark off the axis`).toBe(true);
}

describe('C04 agency views: Tests, Mobility, Semesters', () => {
  it('reads the three agency variants, with the formats, thresholds and floor these tests assume', () => {
    expect(agencies.map((a) => a.id).sort()).toEqual(['fitch', 'moodys', 'sp']);
    expect(FMT).toEqual(F);
    expect(COMMITTED).toEqual({ amber: AMBER, red: RED });
    expect(LOG_FLOOR).toBe(FLOOR);
    // the year axes are calendar years written without a group separator (shell 0.9.0's grouping option)
    expect(YEAR0).toBe(0);
    expect(YEAR_FORMAT).toEqual({ decimals: 0, grouping: false });
  });

  for (const a of agencies) {
    for (const lang of LANGS) {
      it(`every view renders for ${a.id} in ${lang}: lane, provenance, entity and attribution on every card, no Pending, no empty chart`, () => {
        for (const [name, View, n] of VIEWS) {
          for (const grade of name === 'Semesters' ? [0, 1, 2, 3, 4, 5, 6] : [6]) {
            const { markup, drawn } = render(<View sel={makeSel(a.data, { grade })} />, lang);
            const where = `${a.id} ${name} ${GRADES[grade]} ${lang}`;
            expect(markup, `${where}: a Pending`).not.toContain('data-state="loading"');
            expect(markup.startsWith('<div class="caos-views-row" data-views="2">'), `${where}: not a row of cards`).toBe(true);
            expect(drawn.length, `${where}: the charts drawn`).toBe(hostCharts(markup).length);
            expect(drawn.length, `${where}: no chart`).toBeGreaterThan(0);
            for (const p of drawn) expectDrawable(p, `${where}, ${pick(p.y.label, 'en')}`, lang);
            const found = cards(markup);
            expect(found.length, `${where}: cards`).toBe(n);
            for (const c of found) {
              expect(c.lane, `${where} ${c.title}`).toBe('replay');
              expect(c.provenance, `${where} ${c.title}`).toBe('real');
              expect(c.note, `${where} ${c.title}: the entity`).toContain(a.o.agency.name);
              expect(c.note, `${where} ${c.title}: the attribution`).toContain(a.o.attribution);
            }
            for (const ch of hostCharts(markup)) {
              expect(ch.series, `${where}: a chart without series`).toBeGreaterThan(0);
              expect(ch.axes.length).toBe(2);
              for (const t of ch.axes) expect(t.trim().length, `${where}: an axis without its title`).toBeGreaterThan(0);
            }
            // no em-dash, en-dash or arrow anywhere; Spanish without English left in it (the attribution is verbatim)
            expect(markup).not.toMatch(DASHES);
            if (lang === 'es') expect(text(markup).replace(a.o.attribution, ''), `${where}: English in the Spanish view`).not.toMatch(/\b(the|and|of)\b/);
            if (lang === 'en') expect(text(markup), `${where}: Spanish in the English view`).not.toMatch(/\b(el|los|las|del|año)\b/);
          }
        }
      });
    }
  }

  it('the Tests chart draws -log10 p of each year against the pooled matrix, in the series of its light, with the policy as lines', () => {
    for (const a of agencies) {
      const o = a.o;
      const years = yearsOf(o.cohorts.map((c) => c.label));
      const refs = years.map((y) => o.homogeneity.reference.find((r) => r.label === String(y)));
      const { drawn } = render(<TestsView sel={makeSel(a.data)} />);
      const ch = chartBy(drawn, TESTS_Y);
      expect(ch, `${a.id}: the chart`).toBeDefined();
      const p = ch as UPlotChartProps;
      expect(p.y.log, `${a.id}: a linear axis`).toBeFalsy();
      expect(p.x.values).toEqual(years);
      const lines = p.series.slice(-2);
      const data = p.series.slice(0, -2);
      // the policy's thresholds at their -log10 p, labelled as the policy's
      expect(lines.map((s) => [...new Set(s.values)])).toEqual([[-Math.log10(AMBER)], [-Math.log10(RED)]]);
      for (const s of lines) expect(pick(s.label, 'en')).toContain('policy threshold');
      // each year drawn once, at -log10 of the artifact's p, in the series of its light; a p of 0 is a mark instead
      refs.forEach((r, i) => {
        const pv = r?.p_value ?? null;
        const at = data.filter((s) => s.values[i] !== null);
        if (pv !== null && pv > 0) {
          expect(at.length, `${a.id} ${years[i]}`).toBe(1);
          expect(at[0].values[i] as number).toBeCloseTo(pv >= 1 ? 0 : -Math.log10(pv), 10);
          expect(pick(at[0].label, 'en').toLowerCase().startsWith(lightByP(pv)), `${a.id} ${years[i]}: the light`).toBe(true);
          expect(testRow(a, 'rating.matrix_reference', String(years[i]))?.light).toBe(lightByP(pv));
        } else {
          expect(at.length, `${a.id} ${years[i]}: nothing drawn for p = ${pv}`).toBe(0);
        }
      });
      const zeros = years.filter((_, i) => refs[i]?.p_value === 0);
      expect((p.marks ?? []).map((m) => m.x)).toEqual(zeros);
      for (const m of p.marks ?? []) expect(pick(m.label, 'en')).toBe('p < 1E-300');
      // the counts in the legend: lights over the years with a p-value
      const tested = refs.filter((r) => r && r.p_value !== null) as Array<{ p_value: number }>;
      for (const light of ['red', 'amber', 'green'] as const) {
        const k = tested.filter((r) => lightByP(r.p_value) === light).length;
        const s = data.find((x) => pick(x.label, 'en').toLowerCase().startsWith(light));
        if (k === 0) expect(s, `${a.id}: an empty ${light} series`).toBeUndefined();
        else expect(pick(s!.label, 'en'), `${a.id} ${light}`).toContain(`: ${k} of ${tested.length}`);
      }
      // the axis starts at p = 1 and holds every point and the red line
      const top = Math.max(-Math.log10(RED), ...data.flatMap((s) => s.values.filter((x): x is number => x !== null)));
      expect(p.y.range?.[0]).toBe(0);
      expect(p.y.range?.[1]).toBeGreaterThan(top);
    }
    // S&P: 2002's p of 1.9e-124 is drawn at 123.7 on the linear axis; 2021's underflows to 0 and is marked
    const sp = render(<TestsView sel={makeSel(agency('sp').data)} />).drawn;
    const pts = chartBy(sp, TESTS_Y)!.series.slice(0, -2).flatMap((s) => s.values.filter((x): x is number => x !== null));
    expect(Math.max(...pts)).toBeCloseTo(-Math.log10(nn(agency('sp').o.homogeneity.reference.find((r) => r.label === '2002')!.p_value)), 10);
    expect((chartBy(sp, TESTS_Y)!.marks ?? []).map((m) => m.x)).toEqual([2021]);
  });

  it('the Tests table prints the artifact\'s time homogeneity and every year\'s tests, with the lights of the committed policy', () => {
    for (const a of agencies) {
      const o = a.o;
      for (const lang of LANGS) {
        const { markup } = render(<TestsView sel={makeSel(a.data)} />, lang);
        // time homogeneity: the periods, statistic / dof, p and light, per dof, the row furthest in the row's own form
        for (const [seg, h, cohorts] of [
          ['annual', o.homogeneity.annual, o.cohorts],
          ['semesters', o.homogeneity.semesters, o.semesters],
        ] as const) {
          const row = rowOf(markup, 'time-homogeneity', 'data-segment', seg);
          expect(row, `${a.id} ${lang} ${seg}`).not.toBe('');
          if (!h) continue;
          const tr = testRow(a, 'rating.time_homogeneity', seg) as TestRow;
          const c = cellsOf(row);
          const unit = seg === 'annual' ? { en: 'years', es: 'años' } : { en: 'semesters', es: 'semestres' };
          expect(c[0].text).toBe(`${h.periods} ${unit[lang]}`);
          expect(c[0].attrs).toContain(esc(`${h.periods} ${unit[lang]}, ${cohorts[0].label} ${lang === 'en' ? 'to' : 'a'} ${cohorts[cohorts.length - 1].label}`));
          expect(c[1].text).toBe(`${formatNumber(h.statistic, lang, F.statistic)} / ${formatNumber(h.dof, lang, F.dof)}`);
          expect(lightAttr(c[2].attrs)).toBe(lightByP(h.p_value));
          expect(tr.light).toBe(lightByP(h.p_value));
          expect(c[2].text).toBe(`${pPrinted(nn(h.p_value), lang)} ${LIGHT_WORD[lightByP(nn(h.p_value))][lang]}`);
          expect(c[3].text).toBe(formatNumber(nn(h.statistic) / h.dof, lang, F.perDof));
          const w = furthest(tr);
          expect(c[4].text).toBe(`${w.grade} (${formatNumber(w.ratio, lang, F.perDof)})`);
          expect(tr.extras.form).toBe('chi2');
        }
        expect(markup).toContain(lang === 'en' ? '>Chi-square / dof<' : '>Chi-cuadrado / gl<');
        expect(markup).toContain(lang === 'en' ? 'The same matrix for every period?' : '¿Una sola matriz para todos los períodos?');
        // every year: LR per dof, the pooled test's p and light, the z-tests' p and light, the two bandwidths
        for (const c of o.cohorts) {
          const ref = o.homogeneity.reference.find((r) => r.label === c.label)!;
          const ecb = o.ecb.find((e) => e.label === c.label)!;
          const cells = cellsOf(rowOf(markup, 'tests-by-year', 'data-year', c.label));
          expect(cells.length, `${a.id} ${lang} ${c.label}: its row`).toBe(6);
          expect(cells[0].text).toBe(c.label);
          expect(cells[1].text, `${a.id} ${c.label} LR per dof`).toBe(formatNumber(nn(ref.statistic) / ref.dof, lang, F.perDof));
          expect(lightAttr(cells[2].attrs)).toBe(lightByP(ref.p_value));
          expect(cells[2].text).toBe(`${pPrinted(nn(ref.p_value), lang)} ${LIGHT_WORD[lightByP(nn(ref.p_value))][lang]}`);
          expect(testRow(a, 'rating.migration_ztests', c.label)?.light).toBe(lightByP(ecb.ztests_p));
          expect(lightAttr(cells[3].attrs)).toBe(lightByP(ecb.ztests_p));
          expect(cells[3].text).toBe(`${pPrinted(ecb.ztests_p as number, lang)} ${LIGHT_WORD[lightByP(ecb.ztests_p)][lang]}`);
          expect(cells[4].text).toBe(formatNumber(ecb.mwb_upper, lang, F.index));
          expect(cells[5].text).toBe(formatNumber(ecb.mwb_lower, lang, F.index));
        }
        expect(markup).toContain(lang === 'en' ? '>LR / dof<' : '>RV / gl<');
      }
    }
  });

  it('the Tests notes state the artifact\'s cohorts, degrees of freedom, statistic, underflows and the z-tests\' lit years', () => {
    for (const a of agencies) {
      const o = a.o;
      const dofs = [...new Set(o.homogeneity.reference.map((r) => r.dof))];
      expect(dofs.length).toBe(1);
      const forms = [...new Set(o.cohorts.map((c) => testRow(a, 'rating.matrix_reference', c.label)?.extras.form))];
      expect(forms).toEqual(['lr']);
      const under = o.homogeneity.reference.filter((r) => r.p_value === 0).map((r) => Number(r.label));
      const lit = (light: string) => o.ecb.filter((e) => lightByP(e.ztests_p) === light).map((e) => Number(e.label));
      for (const lang of LANGS) {
        const { markup } = render(<TestsView sel={makeSel(a.data)} />, lang);
        const chartNote = card(markup, lang === 'en' ? 'Each year against the pooled matrix' : 'Cada año contra la matriz agrupada').note;
        expect(chartNote).toContain(lang === 'en' ? `pooled over its ${o.pooled.cohorts} cohorts (likelihood ratio, ${dofs[0]} dof)` : `agrupada sobre sus ${o.pooled.cohorts} cohortes (razón de verosimilitud, ${dofs[0]} gl)`);
        if (under.length) expect(chartNote).toContain(lang === 'en' ? `Dashed: ${listOf(under, 'en')}, p below 1E-300` : `: ${listOf(under, 'es')}, p bajo 1E-300`);
        else expect(chartNote).not.toContain('1E-300');
        const tableNote = card(markup, lang === 'en' ? "Every year's tests" : 'Las pruebas de cada año').note;
        const LIT = { red: { en: 'red', es: 'roja' }, amber: { en: 'amber', es: 'ámbar' } };
        const parts = (['red', 'amber'] as const).filter((l) => lit(l).length).map((l) => `${LIT[l][lang]} ${lang === 'en' ? 'in' : 'en'} ${listOf(lit(l), lang)}`);
        const zText = parts.length ? `${lang === 'en' ? 'lit' : 'con luz'} ${parts.join(lang === 'en' ? ' and ' : ' y ')}` : lang === 'en' ? 'lit amber or red in no year' : 'sin luz ámbar ni roja en ningún año';
        expect(tableNote, `${a.id} ${lang}`).toContain(zText);
        expect(tableNote).toContain(lang === 'en' ? 'policy thresholds, not regulatory' : 'umbrales de política, no regulatorios');
      }
    }
    // S&P's z-tests are lit red in 2001 and 2021; Moody's and Fitch's in no year
    expect(card(html(<TestsView sel={makeSel(agency('sp').data)} />), "Every year's tests").note).toContain('lit red in 2001 and 2021');
    expect(card(html(<TestsView sel={makeSel(agency('fitch').data)} />), "Every year's tests").note).toContain('lit amber or red in no year');
  });

  it('the Tests view names each statistic by the form its row reports', () => {
    // the annual time-homogeneity row reported as a likelihood ratio: the header no longer names one statistic, and
    // each cell names its own
    const sp = agency('sp');
    const lr = altered(sp, (v) => {
      const row = v.tests.find((t) => t.test_id === 'rating.time_homogeneity' && t.segment === 'annual')!;
      row.extras = { ...row.extras, form: 'lr' };
    });
    const markup = html(<TestsView sel={makeSel(lr.data)} />);
    expect(markup).toContain('>Statistic / dof<');
    const annual = cellsOf(rowOf(markup, 'time-homogeneity', 'data-segment', 'annual'));
    expect(annual[1].text).toBe(`likelihood ratio ${formatNumber(sp.o.homogeneity.annual.statistic, 'en', F.statistic)} / ${formatNumber(sp.o.homogeneity.annual.dof, 'en', F.dof)}`);
    // the row furthest is then read in the LR form
    const row = lr.v.tests.find((t) => t.test_id === 'rating.time_homogeneity' && t.segment === 'annual') as TestRow;
    const w = furthest(row);
    expect(annual[4].text).toBe(`${w.grade} (${formatNumber(w.ratio, 'en', F.perDof)})`);
    expect(w.ratio).not.toBeCloseTo(furthest(testRow(sp, 'rating.time_homogeneity', 'annual') as TestRow).ratio, 3);
  });

  it('the Mobility chart draws the artifact\'s M_SVD, trace index and speculative-grade default rate on one axis, with the stress years marked', () => {
    for (const a of agencies) {
      const o = a.o;
      const years = yearsOf(o.mobility.labels);
      const stress: Array<[number, string]> = [];
      if (years.includes(2001)) stress.push([2001, '2001']);
      if (years.includes(2008)) stress.push([2008, years.includes(2009) ? '2008 to 2009' : '2008']);
      if (years.includes(2009)) stress.push([2009, years.includes(2008) ? '' : '2009']);
      if (years.includes(2020)) stress.push([2020, '2020']);
      for (const lang of LANGS) {
        const { markup, drawn } = render(<MobilityView sel={makeSel(a.data)} />, lang);
        expect(drawn.length).toBe(1);
        const p = chartBy(drawn, MOBILITY_Y) as UPlotChartProps;
        expect(p.x.values).toEqual(years);
        expect(p.series.map((s) => s.values)).toEqual([o.mobility.svd, o.mobility.trace, o.mobility.spec_default_rate].map((s) => s.map((x) => (Number.isFinite(x) ? x : null))));
        expect(pick(p.series[2].label, lang)).toContain(pick(DEFINITION_LABEL.d2, lang));
        expect((p.marks ?? []).map((m) => [m.x, pick(m.label, 'en')])).toEqual(stress);
        const note = card(markup, lang === 'en' ? "Mobility of each year's matrix and the default rate" : 'Movilidad de la matriz de cada año y la tasa de incumplimiento').note;
        const named = [2001, 2008, 2009, 2020].filter((y) => years.includes(y));
        expect(note).toContain(lang === 'en' ? `Dashed: the stress years ${listOf(named, 'en')}.` : `Segmentadas: los años de tensión ${listOf(named, 'es')}.`);
        expect(note).toContain(lang === 'en' ? 'on the same axis (0.10 is 10%)' : 'en el mismo eje (0,10 es 10%)');
        // the table: the chart's numbers and each cohort's ratings at the start
        o.mobility.labels.forEach((label, i) => {
          const cells = cellsOf(rowOf(markup, 'mobility', 'data-year', label));
          expect(cells.length, `${a.id} ${lang} ${label}`).toBe(5);
          expect(cells[0].text).toBe(label);
          expect(cells[1].text).toBe(formatNumber(o.mobility.svd[i], lang, F.index));
          expect(cells[2].text).toBe(formatNumber(o.mobility.trace[i], lang, F.index));
          expect(cells[3].text).toBe(formatNumber(o.mobility.spec_default_rate[i], lang, F.rate));
          expect(cells[4].text).toBe(formatNumber(size(o.cohorts.find((c) => c.label === label)), lang, F.count));
        });
        const tableNote = card(markup, lang === 'en' ? 'Mobility and defaults by year' : 'Movilidad e incumplimientos por año').note;
        expect(tableNote).toContain(lang === 'en' ? 'The default rate is D2 rated defaulters: the ratings with at least one default event' : 'La tasa de incumplimiento es D2 calificaciones incumplidas: las calificaciones con al menos un evento');
      }
    }
    // Fitch's cohorts start in 2002: no 2001 line
    expect((chartBy(render(<MobilityView sel={makeSel(agency('fitch').data)} />).drawn, MOBILITY_Y)!.marks ?? []).map((m) => m.x)).toEqual([2008, 2009, 2020]);
  });

  it('the Semesters view draws the artifact\'s distances and the chosen grade\'s PDs, or says why it cannot', () => {
    for (const a of agencies) {
      const o = a.o;
      const s = o.semesters_vs_year;
      const xs = s.map((r) => r.year);
      let largest = s[0];
      for (const r of s) if (nn(r.l1) > nn(largest.l1)) largest = r;
      const marks: Array<[number, string]> = [];
      if (s.some((r) => r.year === 2020)) marks.push([2020, largest.year === 2020 ? '2020, the largest' : '2020']);
      if (largest.year !== 2020) marks.push([largest.year, 'the largest']);
      const empty = s.filter((r) => r.pd_annual.every((p) => p === 0)).map((r) => r.year);
      for (let g = 0; g < 7; g++) {
        const { markup, drawn } = render(<SemestersView sel={makeSel(a.data, { grade: g })} />);
        const where = `${a.id} ${GRADES[g]}`;
        const l1 = chartBy(drawn, L1_Y) as UPlotChartProps;
        expect(l1.x.values).toEqual(xs);
        expect(l1.series[0].values).toEqual(s.map((r) => r.l1));
        expect((l1.marks ?? []).map((m) => [m.x, pick(m.label, 'en')]), where).toEqual(marks);
        const product = s.map((r) => r.pd_product[g]);
        const annual = s.map((r) => r.pd_annual[g]);
        const pdChart = chartBy(drawn, PD_Y(GRADES[g]));
        if (o.pd.d4 === null) {
          // no default category: the cohorts behind each distance
          expect(pdChart, where).toBeUndefined();
          expect(markup).toContain('no default category');
          for (const r of s) {
            const cells = cellsOf(rowOf(markup, 'semesters-cohorts', 'data-year', String(r.year)));
            expect(cells.map((c) => c.text)).toEqual([
              String(r.year),
              formatNumber(r.l1, 'en', F.l1),
              formatNumber(size(o.semesters.find((c) => c.label === `${r.year}H1`)), 'en', F.count),
              formatNumber(size(o.semesters.find((c) => c.label === `${r.year}H2`)), 'en', F.count),
              formatNumber(size(o.cohorts.find((c) => c.label === String(r.year))), 'en', F.count),
            ]);
          }
          continue;
        }
        const pdNote = cards(markup)[1].note;
        if (empty.length) expect(pdNote, where).toContain(`The year's default column is empty in every grade in ${listOf(empty, 'en')}.`);
        if (![...product, ...annual].some((p) => p !== null && p >= FLOOR)) {
          // nothing a log axis can draw: a table of the PDs
          expect(pdChart, where).toBeUndefined();
          for (const [i, r] of s.entries()) {
            const cells = cellsOf(rowOf(markup, 'semesters-pd', 'data-year', String(r.year)));
            expect(cells.map((c) => c.text)).toEqual([String(r.year), formatNumber(product[i], 'en', F.pd), formatNumber(annual[i], 'en', F.pd), formatNumber(r.l1, 'en', F.l1)]);
          }
          continue;
        }
        const p = pdChart as UPlotChartProps;
        expect(p, where).toBeDefined();
        expect(p.y.log).toBe(true);
        const want = (v: Array<number | null>) => v.map((x) => (x !== null && x >= FLOOR ? x : null));
        const expected = [want(product), want(annual)].filter((v) => v.some((x) => x !== null));
        expect(p.series.map((x) => x.values), where).toEqual(expected);
        // the note's counts: the years compared, above and below, the zeros of each
        const pairs = s.filter((_, i) => product[i] !== null && annual[i] !== null && ((product[i] as number) > 0 || (annual[i] as number) > 0));
        const idx = (r: (typeof s)[number]) => s.indexOf(r);
        const above = pairs.filter((r) => (product[idx(r)] as number) > (annual[idx(r)] as number)).length;
        const below = pairs.filter((r) => (product[idx(r)] as number) < (annual[idx(r)] as number)).length;
        if (pairs.length) expect(pdNote, where).toContain(`The product's is above the year's in ${above} and below it in ${below} of the ${pairs.length} years with a default in either`);
        expect(pdNote.includes('one possible reason'), where).toBe(above > below);
        const za = annual.filter((x) => x === 0).length;
        const zp = product.filter((x) => x === 0).length;
        if (za + zp) expect(pdNote, where).toContain(`PDs of 0, which a log axis cannot draw: ${za} of the year's and ${zp} of the product's.`);
        else expect(pdNote).not.toContain('PDs of 0');
        expect(pdNote).toContain(`${pick(DEFINITION_LABEL.d4, 'en')}: the default column over the cohort less its withdrawals`);
        expect(pdNote, `${where}: another agency's caveat`).not.toContain("Moody's");
      }
    }
    // S&P's CCC-C: the product above the year in each of its 16 years; its AAA never defaults: a table of zeros
    const sp = agency('sp');
    expect(cards(html(<SemestersView sel={makeSel(sp.data, { grade: 6 })} />))[1].note).toContain("The product's is above the year's in 16 and below it in 0 of the 16 years");
    expect(html(<SemestersView sel={makeSel(sp.data, { grade: 0 })} />)).toContain('data-table="semesters-pd"');
    // S&P's BB: 8 of the year's PDs are 0 and none of the product's (the counts are not swapped)
    expect(cards(html(<SemestersView sel={makeSel(sp.data, { grade: 4 })} />))[1].note).toContain("8 of the year's and 0 of the product's");
    // Fitch's year matrices have an empty default column in every grade from 2010 to 2014 (its transition pages)
    expect(cards(html(<SemestersView sel={makeSel(agency('fitch').data, { grade: 6 })} />))[1].note).toContain('in every grade in 2010 to 2014.');
    // Moody's, in Spanish: the cohorts' table and the reason
    const es = html(<SemestersView sel={makeSel(agency('moodys').data, { grade: 6 })} />, 'es');
    expect(es).toContain('no tiene categoría de incumplimiento');
    expect(es).toContain('>Calif., H1<');
  });

  it('the Semesters PD card tells an agency without a default category from a grade whose PDs are undefined or below the floor', () => {
    const sp = agency('sp');
    // S&P with AAA's PDs undefined in every year: not "no default category" (S&P's page has one), but undefined rows
    const undefinedAaa = altered(sp, (v) => {
      for (const r of v.outputs.semesters_vs_year) {
        r.pd_product[0] = null;
        r.pd_annual[0] = null;
      }
    });
    const u = html(<SemestersView sel={makeSel(undefinedAaa.data, { grade: 0 })} />);
    expect(u).not.toContain('no default category');
    expect(u).toContain('No AAA PD is defined in any year');
    expect(u).toContain('data-table="semesters-pd"');
    // Moody's with a PD written into its rows still has no default category: the reason is the agency's page
    const moodys = altered(agency('moodys'), (v) => {
      v.outputs.semesters_vs_year[0].pd_annual[6] = 0.2;
    });
    expect(html(<SemestersView sel={makeSel(moodys.data, { grade: 6 })} />)).toContain('no default category');
    // a PD below the floor is left out of the log axis and counted in the note; the rest is drawn
    const tiny = altered(sp, (v) => {
      v.outputs.semesters_vs_year[0].pd_product[6] = 1e-25;
    });
    const { markup, drawn } = render(<SemestersView sel={makeSel(tiny.data, { grade: 6 })} />);
    const p = chartBy(drawn, PD_Y('CCC-C')) as UPlotChartProps;
    expect(p.series[0].values[0]).toBeNull();
    expect(cards(markup)[1].note).toContain('A PD below 1E-20 is left out as well');
    // a grade whose only positive PDs are below the floor: a table, and the reason
    const allTiny = altered(sp, (v) => {
      for (const r of v.outputs.semesters_vs_year) {
        r.pd_product[0] = 1e-30;
        r.pd_annual[0] = 0;
      }
    });
    const t = html(<SemestersView sel={makeSel(allTiny.data, { grade: 0 })} />);
    expect(t).toContain('No AAA PD reaches 1E-20 in any year');
    expect(t).toContain('data-table="semesters-pd"');
  });

  it('the views follow the selection: the grade moves the Semesters view, the cohort marks its year', () => {
    const sp = agency('sp');
    expect(html(<SemestersView sel={makeSel(sp.data, { grade: 6 })} />)).not.toBe(html(<SemestersView sel={makeSel(sp.data, { grade: 4 })} />));
    const k = sp.o.cohorts.findIndex((c) => c.label === '2021');
    for (const View of [TestsView, MobilityView]) {
      const markup = html(<View sel={makeSel(sp.data, { cohort: k })} />);
      expect(markup).toMatch(/<tr data-year="2021" class="ct-current">/);
      expect(markup.match(/class="ct-current"/g)?.length).toBe(1);
      expect(markup).toContain('aria-current="true"');
      expect(html(<View sel={makeSel(sp.data)} />)).not.toContain('class="ct-current"');
      // every year is a button that picks its cohort for the Matrix view
      expect(markup.match(/<button type="button" class="ct-linkbutton"/g)?.length).toBe(sp.o.cohorts.length);
    }
  });

  it('waits only while the data loads, and says so on a variant that is not an agency\'s', () => {
    for (const [, View] of VIEWS) {
      expect(html(<View sel={null} />)).toContain('data-state="loading"');
      const markov = variants.find((c) => c.id === 'markov');
      expect(markov).toBeDefined();
      const markup = html(<View sel={makeSel(markov!.data)} />);
      expect(markup).not.toContain('data-state="loading"');
      expect(markup).toContain('data-not-agency="markov"');
      const found = cards(markup);
      expect(found.length).toBe(1);
      expect(found[0].lane).toBe('replay');
      expect(found[0].provenance).toBe('synthetic');
    }
  });
});

describe('the text of these views', () => {
  it('has no em-dash, en-dash or arrow anywhere in its source', () => {
    for (const file of ['AgencyTestsViews.tsx', 'AgencyTestsViews.test.tsx']) {
      expect(DASHES.test(readFileSync(new URL(file, import.meta.url), 'utf8')), file).toBe(false);
    }
  });
});
