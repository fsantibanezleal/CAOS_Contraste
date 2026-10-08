// CT-411, CT-412: C04's Impact group, rendered on the server from the committed artifacts. On every agency and every
// generator family, in English and in Spanish: Drift, Intervals and Capital are live cards with the variant's
// provenance and a note, never a loading placeholder, every chart with both axis titles and no series without a value;
// the numbers they print are the ports' on the artifact's inputs; Moody's, whose transition page has no default
// category, draws the composition only and says why; the marks are year 1 and the largest gap to the TTC rate.
import { readFileSync } from 'node:fs';
import { formatNumber, pick, useLangStore } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import { effectiveN, pdAgrestiCoull, pdJeffreys, pdWald, portfolioRiskWeight, project } from '../../engine/transitions';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { provenanceOf } from '../model';
import { CapitalView, DriftView, ImpactView, IntervalsView, driftPoints, intervalSeries, largestGap, useDrift, widthSeries } from './LiveViews';
import {
  DEFINITION_LABEL,
  ESMA_DEFINITIONS,
  GRADES,
  familyCountsText,
  gradeCounts,
  isAgency,
  isFamily,
  liveChain,
  makeSel,
  startPortfolio,
  type AgencyVariant,
  type C04Sel,
  type FamilyVariant,
  type GradeIntervals,
} from './selection';

type Lang = 'en' | 'es';

/** Keep's long-run average, computed here from its yearly rates (the mean over the cohorts where the grade has one),
 * independently of the view's helper. */
function keepAverage(o: AgencyVariant['outputs']): (number | null)[] {
  return GRADES.map((_, g) => {
    const xs = (o.pd.keep ?? []).map((row) => row[g]).filter((x): x is number => x !== null);
    return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
  });
}
const LANGS: Lang[] = ['en', 'es'];

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const cases: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: a.variant_id, data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));
const variant = (data: CaseData) => data.variant as VariantArtifact<unknown>;
const agencies = cases.filter((c) => isAgency(variant(c.data)));
const families = cases.filter((c) => isFamily(variant(c.data)));
const byId = (id: string) => {
  const c = cases.find((x) => x.id === id);
  if (!c) throw new Error(`no variant ${id}`);
  return c.data;
};
const agencyOf = (data: CaseData) => data.variant as unknown as AgencyVariant;
const familyOf = (data: CaseData) => data.variant as unknown as FamilyVariant;

// Server rendering reads a zustand store through React's server snapshot, which is the store's initial state: the
// language is set there for one render and put back after it.
const langState = useLangStore.getInitialState() as { lang: Lang };
function html(el: ReactElement, lang: Lang = 'en'): string {
  const before = langState.lang;
  langState.lang = lang;
  try {
    return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  } finally {
    langState.lang = before;
  }
}

/** Text as React escapes it in markup. */
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const unesc = (s: string) => s.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&');

interface Card {
  title: string;
  lane: string;
  provenance: string;
  note: string;
  html: string;
}
function cards(markup: string): Card[] {
  return [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)" data-lane="([^"]*)" data-provenance="([^"]*)"[\s\S]*?<\/figure>/g)].map((m) => ({
    title: unesc(m[1]),
    lane: m[2],
    provenance: m[3],
    note: unesc(/<p class="caos-plot-note">([\s\S]*?)<\/p>/.exec(m[0])?.[1] ?? ''),
    html: m[0],
  }));
}
interface Chart {
  series: number;
  axes: [string, string];
  keys: string[];
}
function charts(markup: string): Chart[] {
  return [...markup.matchAll(/<div class="caos-chart[^"]*" data-series="(\d+)" data-axis-titles="([^"]*)"[\s\S]*?<p class="caos-chart-readout"/g)].map((m) => {
    const [x, y] = unesc(m[2]).split('|');
    return { series: Number(m[1]), axes: [x, y], keys: [...m[0].matchAll(/<li class="caos-chart-key"[^>]*><span[^>]*><\/span>([\s\S]*?)<\/li>/g)].map((k) => unesc(k[1])) };
  });
}
/** The body rows of a table by its data-table name, each cell's text. */
function table(markup: string, name: string): string[][] {
  const m = new RegExp(`<table[^>]*data-table="${name}"[^>]*>([\\s\\S]*?)</table>`).exec(markup);
  if (!m) return [];
  const body = m[1].split('<tbody>')[1] ?? '';
  return [...body.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => [...r[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((c) => unesc(c[1].replace(/<[^>]+>/g, ''))));
}

const pctd = (lang: Lang, v: number | null | undefined, digits = 3) => formatNumber(v, lang, { percent: true, digits });

/** What every view of this module must be: live cards with the variant's provenance and a note, never a loading
 * placeholder, no unformatted value, no em-dash or arrow, every chart with both axis titles and a key per series. */
function checkView(markup: string, v: VariantArtifact<unknown>, where: string): Card[] {
  expect(markup, `${where}: a loading placeholder`).not.toContain('data-state="loading"');
  expect(markup, `${where}: an unformatted value`).not.toMatch(/NaN|not available|no disponible|undefined/);
  expect(markup, `${where}: an em-dash, en-dash or arrow`).not.toMatch(/[\u2013\u2014\u2190-\u21ff]/);
  const found = cards(markup);
  expect(found.length, `${where}: no card`).toBeGreaterThan(0);
  for (const c of found) {
    expect(c.lane, `${where} "${c.title}": lane`).toBe('live');
    expect(c.provenance, `${where} "${c.title}": provenance`).toBe(provenanceOf(v.provenance.truth_status));
    expect(c.note.length, `${where} "${c.title}": no note`).toBeGreaterThan(40);
  }
  for (const ch of charts(markup)) {
    expect(ch.series, `${where}: an empty chart`).toBeGreaterThan(0);
    expect(ch.axes[0].length > 0 && ch.axes[1].length > 0, `${where}: an axis without its title`).toBe(true);
    if (ch.series > 1) expect(ch.keys.length, `${where}: a series without its key`).toBe(ch.series);
  }
  return found;
}

/** The intervals of every grade with counts, recomputed here from the artifact and the ports (not the view's hook). */
function expectedIntervals(sel: C04Sel): GradeIntervals[] {
  const v = variant(sel.data);
  const out: GradeIntervals[] = [];
  for (let g = 0; g < GRADES.length; g++) {
    const c = gradeCounts(v, sel.definition, g);
    if (!c) continue;
    out.push({
      grade: g,
      ...c,
      nEffective: effectiveN(c.n, sel.rho),
      wald: pdWald(c.defaults, c.n, { level: sel.level, rho: sel.rho }),
      agrestiCoull: pdAgrestiCoull(c.defaults, c.n, { level: sel.level, rho: sel.rho }),
      jeffreys: pdJeffreys(c.defaults, c.n, { level: sel.level }),
    });
  }
  return out;
}

describe('the C04 Impact group (live)', () => {
  it('reads the eight variants it serves: three agencies and five generator families', () => {
    expect(agencies.map((c) => c.id)).toEqual(['sp', 'moodys', 'fitch']);
    expect(families.map((c) => c.id)).toEqual(['markov', 'momentum', 'cycle', 'withdrawals', 'thin']);
  });

  for (const c of [...agencies, ...families]) {
    for (const lang of LANGS) {
      it(`every view is live, sourced and drawn: ${c.id}, ${lang}`, () => {
        const v = variant(c.data);
        const sel = makeSel(c.data);
        for (const [name, View] of [
          ['Drift', DriftView],
          ['Intervals', IntervalsView],
          ['Capital', CapitalView],
        ] as const) {
          const markup = html(<View sel={sel} />, lang);
          const found = checkView(markup, v, `${c.id} ${name} ${lang}`);
          // a CEREP-derived card names its source: the attribution verbatim, and the entity on an agency
          const note = found[0].note;
          const att = 'Source: ESMA CEREP; tables transformed by Contraste';
          const cited = { en: isAgency(v) ? `${att}.` : `(${att})`, es: isAgency(v) ? `Atribución: "${att}".` : `(atribución: "${att}")` };
          expect(note).toContain(cited[lang]);
          if (isAgency(v)) expect(note).toContain(`${lang === 'en' ? 'Entity' : 'Entidad'}: ${v.outputs.agency.name} (${v.outputs.agency.code}).`);
        }
      });
    }
  }

  it('the group holds Drift, Intervals and Capital, Drift first; on the published variant it is Table 5 live', () => {
    const markup = html(<ImpactView sel={makeSel(byId('sp'))} />);
    for (const label of ['Drift', 'Intervals', 'Capital']) expect(markup).toContain(`>${label}</button>`);
    expect(markup).toContain('data-table="ttc-portfolio"');
    const es = html(<ImpactView sel={makeSel(byId('sp'))} />, 'es');
    for (const label of ['Deriva', 'Intervalos', 'Capital']) expect(es).toContain(`>${label}</button>`);
    const pub = html(<ImpactView sel={makeSel(byId('published'))} />);
    expect(pub).toContain('data-table="table5-live"');
    expect(html(<ImpactView sel={null} />)).toContain('data-state="loading"');
  });

  it('speaks Spanish in Spanish', () => {
    const sel = makeSel(byId('sp'));
    const drift = html(<DriftView sel={sel} />, 'es');
    expect(drift).toContain('Tasa proyectada, inicio: Originación');
    expect(drift).toContain('Engelmann (2024), (9): el inicio proyectado');
    expect(drift).not.toMatch(/Projected default rate|Share of the balance|Year of the projection/);
    const intervals = html(<IntervalsView sel={sel} />, 'es');
    expect(intervals).toContain('no tiene corrección por correlación');
    expect(intervals).not.toMatch(/Counts, effective|no correlation correction|PD bound/);
    const capital = html(<CapitalView sel={sel} />, 'es');
    expect(capital).toContain('Ponderadores por definición');
    expect(capital).toContain(esc(pick(ESMA_DEFINITIONS, 'es')));
    expect(capital).not.toMatch(/Risk weights by definition|Average risk weight/);
  });

  describe('Drift', () => {
    it("projects S&P's portfolio under its pooled matrix, as the port does on the artifact's inputs", () => {
      const data = byId('sp');
      const o = agencyOf(data).outputs;
      for (const [start, horizon] of [['origination', 20], ['speculative', 35], ['best', 5]] as const) {
        const sel = makeSel(data, { start, horizon });
        const w0 = startPortfolio(start, o.origination);
        const p = project(o.pooled.matrix, w0, o.origination, horizon);
        for (const lang of LANGS) {
          const markup = html(<DriftView sel={sel} />, lang);
          const [rate, mix] = charts(markup);
          const gap = largestGap(p.defaultRate, p.ttc.defaultRate);
          // the projection, the TTC rate, and year 1 and the largest gap as points (one point when they coincide)
          expect(rate.series).toBe(gap.year === 1 ? 3 : 4);
          expect(rate.keys[1]).toContain(pctd(lang, p.ttc.defaultRate));
          expect(rate.keys[2]).toContain(pctd(lang, p.defaultRate[0]));
          expect(mix.series).toBe(7);
          // the start, the horizon and the TTC portfolio across the grades, each with its L1 distance to the TTC
          const rows = table(markup, 'ttc-portfolio');
          expect(rows).toHaveLength(3);
          expect(rows[0]).toEqual([lang === 'en' ? 'Start' : 'Inicio', ...w0.slice(0, 7).map((x) => pctd(lang, x)), formatNumber(p.distanceToTtc[0], lang, { decimals: 3 })]);
          expect(rows[1].slice(1)).toEqual([...p.portfolio[horizon].slice(0, 7).map((x) => pctd(lang, x)), formatNumber(p.distanceToTtc[horizon], lang, { decimals: 3 })]);
          expect(rows[2].slice(1, 8)).toEqual(p.ttc.portfolio.slice(0, 7).map((x) => pctd(lang, x)));
          expect(cards(markup)[0].note).toContain(`${lang === 'en' ? 'year' : 'año'} ${gap.year}`);
        }
      }
    });

    it("projects a family's portfolio under the generator's true one-year matrix and its cohort sizes", () => {
      const data = byId('markov');
      const g = familyOf(data).outputs.generator;
      const chain = liveChain(variant(data));
      expect(chain?.matrix).toEqual(g.one_year_matrix);
      const total = g.obligors.reduce((a, b) => a + b, 0);
      const origination = [...g.obligors.map((n) => n / total), 0];
      const p = project(g.one_year_matrix, origination, origination, 20);
      const markup = html(<DriftView sel={makeSel(data)} />);
      expect(charts(markup)[0].keys[1]).toContain(pctd('en', p.ttc.defaultRate));
      expect(table(markup, 'ttc-portfolio')[2][7]).toBe(pctd('en', p.ttc.portfolio[6]));
      expect(cards(markup)[0].note).toContain("the generator's true one-year matrix exp(Q)");
    });

    it("Moody's has no route to default: the composition only, its long-run mix, and the reason", () => {
      const data = byId('moodys');
      const o = agencyOf(data).outputs;
      expect(liveChain(variant(data))).toBeNull();
      const p = project(o.pooled.matrix, o.origination, o.origination, 20);
      expect(p.defaultRate.every((r) => r === 0)).toBe(true);
      for (const lang of LANGS) {
        const markup = html(<DriftView sel={makeSel(data)} />, lang);
        const found = cards(markup);
        // the composition and its table: no default-rate chart
        expect(found).toHaveLength(2);
        expect(found[0].note).toContain(lang === 'en' ? 'has no default category' : 'no tiene categoría de incumplimiento');
        expect(found[0].note).toContain(lang === 'en' ? 'needs a default column' : 'necesita una columna de incumplimiento');
        const all = charts(markup);
        expect(all).toHaveLength(1);
        expect(all[0].series).toBe(7);
        expect(markup).toContain(lang === 'en' ? 'Long-run mix' : 'Mezcla de largo plazo');
        expect(table(markup, 'ttc-portfolio')[2][7]).toBe(pctd(lang, p.ttc.portfolio[6]));
      }
    });

    it('marks year 1 and the largest gap as points, one point when they coincide', () => {
      const one = driftPoints([0.01, 0.008, 0.007], 0.006);
      expect(one).toHaveLength(1);
      expect(one[0].values).toEqual([0.01, null, null]);
      expect(one[0].mode).toBe('points');
      expect(one[0].label).toEqual({ en: `Year 1: ${pctd('en', 0.01)}, largest gap +0.4 pp`, es: `Año 1: ${pctd('es', 0.01)}, mayor diferencia +0,4 pp` });
      // a path that rises above the TTC rate and comes back (Engelmann's W_init): the gap is later than year 1
      const two = driftPoints([0.0116, 0.0138, 0.0169, 0.015], 0.012);
      expect(two.map((s) => s.values)).toEqual([
        [0.0116, null, null, null],
        [null, null, 0.0169, null],
      ]);
      expect(two[1].label).toEqual({ en: 'Year 3: largest gap +0.49 pp', es: 'Año 3: mayor diferencia +0,49 pp' });
      expect(largestGap([0.5, 0.3, 0.8], 0.5)).toEqual({ year: 3, gap: 0.30000000000000004 });
      expect(largestGap([0.4, 0.6], 0.5).year).toBe(1);
    });

    it('moves with the rail: the start, the horizon and the grade change what is drawn', () => {
      const data = byId('fitch');
      const at = (over: Partial<C04Sel>) => html(<DriftView sel={makeSel(data, over)} />);
      expect(at({})).not.toBe(at({ start: 'uniform' }));
      expect(at({})).not.toBe(at({ horizon: 40 }));
      expect(at({})).not.toBe(at({ grade: 2 }));
    });

    it('waits only for data: a missing selection is loading, never an empty card', () => {
      expect(html(<DriftView sel={null} />)).toContain('data-state="loading"');
      function Probe() {
        return <p>{useDrift(null) === null ? 'none' : 'some'}</p>;
      }
      expect(html(<Probe />)).toContain('none');
    });
  });

  describe('Intervals', () => {
    it("bounds each grade's pooled counts under the rail's definition, correlation and level", () => {
      const data = byId('sp');
      for (const over of [{}, { definition: 'd4' as const, rho: 0.02, level: 0.99 }, { definition: 'keep' as const, rho: 0.005, level: 0.9, grade: 3 }]) {
        const sel = makeSel(data, over);
        const rows = expectedIntervals(sel);
        expect(rows).toHaveLength(7);
        for (const lang of LANGS) {
          const markup = html(<IntervalsView sel={sel} />, lang);
          const cells = table(markup, 'intervals');
          rows.forEach((r, k) => {
            expect(cells[k].slice(0, 7)).toEqual([
              GRADES[r.grade],
              formatNumber(r.defaults, lang, { decimals: 0 }),
              formatNumber(r.n, lang, { decimals: 0 }),
              formatNumber(r.nEffective, lang, { digits: 4 }),
              formatNumber(r.wald.length * 100, lang, { digits: 3 }),
              formatNumber(r.agrestiCoull.length * 100, lang, { digits: 3 }),
              formatNumber(r.jeffreys.length * 100, lang, { digits: 3 }),
            ]);
          });
          const { drawn } = intervalSeries(rows, null);
          expect(charts(markup)[0].series).toBe(drawn.length);
          expect(cards(markup)[0].note).toContain(pick(DEFINITION_LABEL[sel.definition], lang));
        }
      }
    });

    it("takes the agency's long-run counts as they are in the artifact", () => {
      const data = byId('fitch');
      const o = agencyOf(data).outputs;
      const cells = table(html(<IntervalsView sel={makeSel(data, { definition: 'd3' })} />), 'intervals');
      GRADES.forEach((_, g) => expect(cells[g].slice(1, 3)).toEqual([formatNumber(o.lra.d3.defaults[g], 'en', { decimals: 0 }), formatNumber(o.lra.d3.n[g], 'en', { decimals: 0 })]));
    });

    it('a family draws its truth beside the intervals of its design counts', () => {
      for (const id of ['markov', 'thin']) {
        const data = byId(id);
        const sel = makeSel(data, { rho: 0.01 });
        const truth = familyOf(data).outputs.generator.pd_1y;
        const { drawn } = intervalSeries(expectedIntervals(sel), truth);
        const markup = html(<IntervalsView sel={sel} />);
        const [chart] = charts(markup);
        expect(chart.series).toBe(drawn.length);
        expect(chart.keys).toContain('True one-year PD');
        // the design's counts are explained beside the table, by the rule gradeCounts uses
        const f = familyOf(data);
        expect(cards(markup)[1].note).toContain(familyCountsText(f).en);
        const ns = table(markup, 'intervals').map((r) => r[2]);
        if (id === 'thin') {
          // every grade at the thin family's smallest cohort, and the note says that N
          expect(cards(markup)[1].note).toContain(`N ${formatNumber(f.outputs.ladder!.values[0], 'en', { decimals: 0 })} obligors in every grade`);
          expect(new Set(ns)).toEqual(new Set([formatNumber(f.outputs.ladder!.values[0], 'en', { decimals: 0 })]));
        } else {
          expect(cards(markup)[1].note).toContain('obligor-years');
          GRADES.forEach((_, g) => expect(ns[g]).toBe(formatNumber(gradeCounts(f, 'd2', g)!.n, 'en', { decimals: 0 })));
        }
      }
    });

    it('leaves out a series whose every value is 0 on the log axis, and names it in the note', () => {
      // with a correlation the effective number of obligors is small and every Wald lower bound is 0 (Fitch, D4, 2%)
      const sel = makeSel(byId('fitch'), { definition: 'd4', rho: 0.02 });
      const rows = expectedIntervals(sel);
      expect(rows.every((r) => r.wald.lower === 0)).toBe(true);
      const { drawn, dropped } = intervalSeries(rows, null);
      expect(dropped.map((s) => pick(s.label, 'en'))).toContain('Wald, lower');
      for (const s of drawn) expect(s.values.some((x) => x !== null)).toBe(true);
      const markup = html(<IntervalsView sel={sel} />);
      expect(cards(markup)[1].note).toContain('Not drawn, every value 0: Wald, lower');
      expect(charts(markup)[0].keys).not.toContain('Wald, lower');
    });

    it("Moody's gives no D4 or Keep: the card says why and shows the counts it does give", () => {
      const data = byId('moodys');
      const o = agencyOf(data).outputs;
      for (const definition of ['d4', 'keep'] as const) {
        for (const lang of LANGS) {
          const markup = html(<IntervalsView sel={makeSel(data, { definition })} />, lang);
          expect(charts(markup)).toHaveLength(0);
          expect(cards(markup)[0].note).toContain(lang === 'en' ? 'has no default category' : 'no tiene categoría de incumplimiento');
          const rows = table(markup, 'counts-by-definition');
          expect(rows).toHaveLength(7);
          expect(rows[6]).toEqual([
            'CCC-C',
            `${formatNumber(o.lra.d2.defaults[6], lang, { decimals: 0 })} / ${formatNumber(o.lra.d2.n[6], lang, { decimals: 0 })}`,
            `${formatNumber(o.lra.d3.defaults[6], lang, { decimals: 0 })} / ${formatNumber(o.lra.d3.n[6], lang, { decimals: 0 })}`,
          ]);
          expect(markup).not.toContain('data-state="loading"');
        }
      }
    });

    it("a tall screen also draws how the correlation widens the chosen grade's intervals", () => {
      const data = byId('sp');
      const o = agencyOf(data).outputs;
      // CCC-C: all three widths; AAA, no default: Wald's width is 0 at every correlation, so it is left out
      const ccc = widthSeries(o.lra.d2.defaults[6], o.lra.d2.n[6], 0.95);
      expect(ccc.map((s) => pick(s.label, 'en'))).toEqual(['Wald width', 'Agresti-Coull width', 'Jeffreys width, no correlation']);
      expect(ccc[0].values[0]).toBeCloseTo(pdWald(o.lra.d2.defaults[6], o.lra.d2.n[6], { level: 0.95 }).length, 15);
      expect(new Set(ccc[2].values).size).toBe(1);
      const aaa = widthSeries(o.lra.d2.defaults[0], o.lra.d2.n[0], 0.95);
      expect(aaa.map((s) => pick(s.label, 'en'))).toEqual(['Agresti-Coull width', 'Jeffreys width, no correlation']);
      for (const [grade, series] of [[6, 3], [0, 2]] as const) {
        for (const lang of LANGS) {
          const markup = html(<IntervalsView sel={makeSel(data, { grade })} />, lang);
          expect(markup).toContain('<div class="ct-tall-only">');
          const second = charts(markup)[1];
          expect(second.series).toBe(series);
          const n = o.lra.d2.n[grade];
          expect(cards(markup)[2].note).toContain(formatNumber(effectiveN(n, 0.05), lang, { digits: 3 }));
        }
      }
    });

    it('moves with the rail: correlation, level, definition and grade', () => {
      const data = byId('sp');
      const at = (over: Partial<C04Sel>) => html(<IntervalsView sel={makeSel(data, over)} />);
      expect(at({})).not.toBe(at({ rho: 0.03 }));
      expect(at({})).not.toBe(at({ level: 0.9 }));
      expect(at({})).not.toBe(at({ definition: 'd4' }));
      expect(at({})).not.toBe(at({ grade: 0 }));
    });
  });

  describe('Capital', () => {
    it("weighs S&P's cohort mix with each definition's long-run average and each generator's PD", () => {
      const data = byId('sp');
      const o = agencyOf(data).outputs;
      for (const lgd of [0.45, 0.25]) {
        const sel = makeSel(data, { lgd });
        const irb = { assetClass: 'corporate' as const, lgd, maturity: o.irb.maturity, regime: 'basel3' as const };
        const exposure = o.origination.slice(0, 7);
        const expected: Array<(number | null)[]> = [
          o.lra.d2.rate,
          o.lra.d3.rate,
          o.lra.d4?.rate ?? [],
          keepAverage(o),
          o.generators.em.pd_1y,
          o.generators.diagonal?.pd_1y ?? [],
          o.generators.weighted?.pd_1y ?? [],
          o.generators.jlt?.pd_1y ?? [],
        ];
        for (const lang of LANGS) {
          const markup = html(<CapitalView sel={sel} />, lang);
          const rows = table(markup, 'capital');
          expect(rows).toHaveLength(expected.length);
          expected.forEach((pds, k) => {
            const rw = portfolioRiskWeight(pds, exposure, irb);
            expect(rows[k].slice(1, 4)).toEqual([pctd(lang, pds[6]), pctd(lang, rw.riskWeights[6]), pctd(lang, rw.average)]);
          });
          const [chart] = charts(markup);
          // one point per definition and generator, and the chosen grade's own risk weight
          expect(chart.series).toBe(expected.length + 1);
          expect(markup).toContain('data-control="c04-lgd"');
          expect(markup).toContain(formatNumber(lgd, lang, { percent: true, decimals: 0 }));
          expect(cards(markup)[0].note).toContain(pick(ESMA_DEFINITIONS, lang));
          // Keep's row is the mean of its yearly rates, which the artifact does not hold; the note says so
          expect(rows[3][0]).toBe(pick(DEFINITION_LABEL.keep, lang));
          expect(cards(markup)[1].note).toContain(
            lang === 'en' ? '"Keep withdrawals" has no long-run average in the artifact: its row is the mean of its yearly rates, computed here.' : '"Con retiros" no tiene promedio de largo plazo en el artefacto: su fila es la media de sus tasas anuales, calculada aquí.',
          );
        }
      }
    });

    it("Moody's generators reach no default: their rows say so and are not drawn", () => {
      const data = byId('moodys');
      const markup = html(<CapitalView sel={makeSel(data)} />);
      const rows = table(markup, 'capital');
      expect(rows.map((r) => r[0])).toEqual(['D2 rated defaulters', 'D3 default events', 'EM', 'Diagonal', 'Weighted', 'JLT']);
      for (const r of rows.slice(2)) expect(r.slice(1, 4)).toEqual(['-', '-', '-']);
      const [chart] = charts(markup);
      expect(chart.series).toBe(3);
      // the axis title is short; the key numbers the points, with each row's short name
      expect(chart.axes[0]).toBe('PD definition or generator, numbered as in the key');
      expect(chart.keys.slice(0, 2)).toEqual(['1 D2: D2 rated defaulters', '2 D3: D3 default events']);
      expect(cards(markup)[0].note).toContain("Moody's cohort mix");
      expect(cards(markup)[0].note).toContain('A row without a PD has no point (the table says why).');
      expect(cards(markup)[1].note).toContain("No PD, so no risk weight: EM, Diagonal, Weighted, JLT (Moody's transition page has no default category");
    });

    it("a family's capital is the truth's, grade by grade, with the obligor-weighted average", () => {
      const data = byId('cycle');
      const g = familyOf(data).outputs.generator;
      const rw = portfolioRiskWeight(g.pd_1y, g.obligors, { assetClass: 'corporate', lgd: 0.45, maturity: 2.5, regime: 'basel3' });
      for (const lang of LANGS) {
        const markup = html(<CapitalView sel={makeSel(data)} />, lang);
        const rows = table(markup, 'capital');
        GRADES.forEach((name, k) => expect(rows[k]).toEqual([name, formatNumber(g.obligors[k], lang, { decimals: 0 }), pctd(lang, g.pd_1y[k]), pctd(lang, rw.riskWeights[k])]));
        expect(rows[7][3]).toBe(pctd(lang, rw.average));
        expect(charts(markup)[0].series).toBe(2);
        expect(markup).toContain('data-control="c04-lgd"');
      }
    });

    it("a tall screen also draws each definition's risk weight by grade, and where a family's capital sits", () => {
      const sp = byId('sp');
      const o = agencyOf(sp).outputs;
      const irb = { assetClass: 'corporate' as const, lgd: 0.45, maturity: o.irb.maturity, regime: 'basel3' as const };
      const exposure = o.origination.slice(0, 7);
      const ccc = (
        [
          ['D2 rated defaulters', o.lra.d2.rate],
          ['D3 default events', o.lra.d3.rate],
          ['D4 matrix column', o.lra.d4?.rate ?? []],
          ['Keep withdrawals', keepAverage(o)],
          ['EM', o.generators.em.pd_1y],
          ['Diagonal', o.generators.diagonal?.pd_1y ?? []],
          ['Weighted', o.generators.weighted?.pd_1y ?? []],
          ['JLT', o.generators.jlt?.pd_1y ?? []],
        ] as Array<[string, (number | null)[]]>
      ).map(([label, pds]) => ({ label, rw: portfolioRiskWeight(pds, exposure, irb).riskWeights[6] as number }));
      const lo = ccc.reduce((a, b) => (b.rw < a.rw ? b : a));
      const hi = ccc.reduce((a, b) => (b.rw > a.rw ? b : a));
      const markup = html(<CapitalView sel={makeSel(sp)} />);
      expect(markup).toContain('<div class="ct-tall-only">');
      expect(charts(markup)[1].series).toBe(8);
      // the chosen grade's spread across the definitions and generators, from the lowest to the highest
      expect(cards(markup)[2].note).toContain(`CCC-C runs from ${pctd('en', lo.rw)} (${lo.label}) to ${pctd('en', hi.rw)} (${hi.label})`);
      expect(charts(html(<CapitalView sel={makeSel(byId('moodys'))} />))[1].series).toBe(2);
      // a family: each grade's share of the obligors and of the risk-weighted exposure
      const fam = byId('withdrawals');
      const g = familyOf(fam).outputs.generator;
      const rw = portfolioRiskWeight(g.pd_1y, g.obligors, { assetClass: 'corporate', lgd: 0.45, maturity: 2.5, regime: 'basel3' });
      const total = g.obligors.reduce((a, b) => a + b, 0);
      const speculative = [4, 5, 6];
      const obligors = speculative.reduce((a, k) => a + g.obligors[k] / total, 0);
      const capital = speculative.reduce((a, k) => a + ((g.obligors[k] / total) * (rw.riskWeights[k] as number)) / (rw.average as number), 0);
      for (const lang of LANGS) {
        const fm = html(<CapitalView sel={makeSel(fam)} />, lang);
        expect(charts(fm)[1].series).toBe(2);
        expect(cards(fm)[2].note).toContain(lang === 'en' ? `hold ${pctd('en', obligors)} of the obligors and ${pctd('en', capital)} of the capital` : `tienen ${pctd('es', obligors)} de los deudores y ${pctd('es', capital)} del capital`);
      }
    });

    it("Fitch's empty default columns of 2006 to 2014 are said wherever the pooled default column is used", () => {
      const fitch = byId('fitch');
      const o = agencyOf(fitch).outputs;
      const n = o.cohorts.filter((c) => c.counts.every((row) => row[7] === 0) && c.defaulted!.reduce((a, b) => a + b, 0) > 0).reduce((a, c) => a + c.defaulted!.reduce((x, y) => x + y, 0), 0);
      expect(n).toBe(189);
      const said = { en: 'empty default column in the years 2006 to 2014, while its default page counts 189 rated defaulters', es: 'tiene la columna de incumplimiento vacía en los años 2006 a 2014, mientras su página de incumplimientos cuenta 189 calificaciones incumplidas' };
      for (const lang of LANGS) {
        expect(cards(html(<DriftView sel={makeSel(fitch)} />, lang))[0].note).toContain(said[lang]);
        expect(cards(html(<IntervalsView sel={makeSel(fitch, { definition: 'd4' })} />, lang))[0].note).toContain(said[lang]);
        expect(cards(html(<IntervalsView sel={makeSel(fitch, { definition: 'keep' })} />, lang))[0].note).toContain(said[lang]);
        expect(cards(html(<CapitalView sel={makeSel(fitch)} />, lang))[0].note).toContain(said[lang]);
        // D2 counts the default page, which holds them: no such sentence; nor on S&P, whose columns are full
        expect(cards(html(<IntervalsView sel={makeSel(fitch, { definition: 'd2' })} />, lang))[0].note).not.toContain(said[lang]);
        expect(html(<CapitalView sel={makeSel(byId('sp'))} />, lang)).not.toContain(lang === 'en' ? 'empty default column' : 'columna de incumplimiento vacía');
      }
    });

    it("every card of every view closes with CEREP's attribution, and an agency's with its entity", () => {
      for (const id of ['sp', 'moodys', 'fitch', 'markov', 'thin']) {
        const data = byId(id);
        const v = data.variant as VariantArtifact<unknown>;
        for (const view of [DriftView, IntervalsView, CapitalView]) {
          const View = view;
          for (const card of cards(html(<View sel={makeSel(data)} />))) {
            expect(card.note, `${id} ${card.title}`).toContain('Source: ESMA CEREP; tables transformed by Contraste');
            if (isAgency(v)) expect(card.note, `${id} ${card.title}`).toContain(`Entity: ${v.outputs.agency.name}`);
          }
        }
      }
    });

    it('moves with the knob and the grade', () => {
      const data = byId('fitch');
      const at = (over: Partial<C04Sel>) => html(<CapitalView sel={makeSel(data, over)} />);
      expect(at({})).not.toBe(at({ lgd: 0.6 }));
      expect(at({})).not.toBe(at({ grade: 4 }));
    });
  });
});
