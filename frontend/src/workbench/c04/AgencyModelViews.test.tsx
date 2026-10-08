// CT-411 and CT-412 for the agency variants' Model group: the matrix view and the generators view of S&P, Moody's and
// Fitch, rendered on the server from the committed artifacts in English and in Spanish. Every card carries its lane, its
// provenance and CEREP's attribution with the agency's entity; no view waits as if loading; no chart is drawn empty;
// every number printed is the artifact's, read in its place (each PD beside its own definition, each tail beside its
// own grade), for every grade and for pooled and annual matrices; Fitch's empty default columns (2006 to 2014, finding
// F-D4-EMPTY) are said where a PD is read from them; Moody's, whose transition page has no default category, has no D
// column and no PD series, and one card gives its verdict, distances and diagnostics.
import { readFileSync } from 'node:fs';
import { formatNumber, pick, useLangStore, type Lang } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { describe, expect, it, vi } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import type { C04AgencyOutputs, CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import {
  GeneratorsView,
  MatrixView,
  closestText,
  cohortOfKnob,
  distinct,
  emLine,
  emptyCohortText,
  emptyColumnCohorts,
  emptyPooledText,
  knobOfCohort,
  mapProps,
  matrixData,
  pdChart,
  pdRange,
  pdSeries,
  possessive,
  scaleTexts,
  sourceText,
  verdict,
  zeroDefaultText,
} from './AgencyModelViews';
import { emptyDefaultYears } from './AgencyValidationViews';
import { MatrixDrawing } from './MatrixMap';
import { DEFINITION_LABEL, ESMA_DEFINITIONS, ESTIMATOR_LABEL, GENERATOR_KEYS, GRADES, isAgency, makeSel, type AgencyVariant, type C04Sel, type GeneratorKey } from './selection';

/** A value the artifact must hold: a null fails the test instead of reaching a comparison as 0. */
const nn = (x: number | null | undefined): number => {
  if (x === null || x === undefined) throw new Error('a null where the artifact must hold a number');
  return x;
};

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const variants: Array<{ id: string; data: CaseData }> = manifest.artifacts
  .filter((a) => a.role === 'variant')
  .map((a) => ({ id: a.variant_id, data: { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) } }));
const agencies = variants.filter((c) => isAgency(c.data.variant as VariantArtifact<unknown>));
const outputsOf = (data: CaseData) => (data.variant as unknown as AgencyVariant).outputs;
const dataOf = (id: string) => agencies.find((c) => c.id === id)!.data;
const LANGS: Lang[] = ['en', 'es'];

/** Server rendering reads the language store's initial state (zustand's server snapshot is `getInitialState()`), so the
 * language of a render is set there for the render and put back after it. */
function html(el: ReactElement, lang: Lang): string {
  const initial = useLangStore.getInitialState();
  const before = initial.lang;
  initial.lang = lang;
  try {
    return renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
  } finally {
    initial.lang = before;
  }
}

/** React's escaping of text and attribute values in server markup, and back. */
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
const unesc = (s: string) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
/** The text a reader sees, tags removed. */
const text = (markup: string) => unesc(markup.replace(/<[^>]+>/g, ' '));
const reEsc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

interface Card {
  title: string;
  lane: string;
  provenance: string;
  markup: string;
  note: string;
}
function cards(markup: string): Card[] {
  return [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)" data-lane="([^"]*)" data-provenance="([^"]*)"[^>]*>([\s\S]*?)<\/figure>/g)].map((m) => ({
    title: unesc(m[1]),
    lane: m[2],
    provenance: m[3],
    markup: m[4],
    note: unesc(/<p class="caos-plot-note">([\s\S]*?)<\/p>/.exec(m[4])?.[1] ?? ''),
  }));
}

/** Every chart in the markup: its series count, its axis titles and its keys. */
function charts(markup: string): Array<{ series: number; axes: string[] }> {
  return [...markup.matchAll(/class="caos-chart[^"]*" data-series="(\d+)" data-axis-titles="([^"]*)"/g)].map((m) => ({ series: Number(m[1]), axes: m[2].split('|') }));
}

/** The text cells of the table row marked `attr="value"`. */
function cells(markup: string, attr: string, value: string): string[] {
  const row = new RegExp(`<tr ${attr}="${value}"[^>]*>([\\s\\S]*?)</tr>`).exec(markup);
  if (!row) return [];
  return [...row[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((m) => unesc(m[1]));
}

/** The text of the paragraph marked `attr="value"`, or null where there is none. */
function para(markup: string, attr: string, value: string): string | null {
  const m = new RegExp(`<p class="ct-note" ${attr}="${value}">([\\s\\S]*?)</p>`).exec(markup);
  return m ? unesc(m[1]) : null;
}

/** One of the generator diagnostics: its value, its reading and its source. */
function diagnostic(markup: string, id: string): { value: string; text: string; source: string } {
  const row = new RegExp(`<tr data-diagnostic="${id}">([\\s\\S]*?)</tr>`).exec(markup)?.[1] ?? '';
  return {
    value: unesc(new RegExp(`<span data-value="${id}">([^<]*)</span>`).exec(row)?.[1] ?? ''),
    text: text(row).replace(/[ \t\r\n]+/g, ' '),
    source: unesc(new RegExp(`<span class="ct-note" data-source="${id}">([^<]*)</span>`).exec(row)?.[1] ?? ''),
  };
}

// the view prints '-' where the pipeline wrote null (a value that is not finite); the helpers do the same
const share = (v: number | null | undefined, lang: Lang) => (v === null || v === undefined ? '-' : formatNumber(v, lang, { percent: true, digits: 3 }));
/** A share in percent without its sign (a column whose header carries the unit). */
const pc = (v: number | null | undefined, lang: Lang) => (v === null || v === undefined ? '-' : formatNumber(v * 100, lang, { digits: 3 }));
const count = (v: number, lang: Lang) => formatNumber(v, lang, { decimals: 0 });
const l1 = (v: number | null | undefined, lang: Lang) => (v === null || v === undefined ? '-' : formatNumber(v, lang, { digits: 4 }));
const sum = (a: readonly number[]) => a.reduce((s, x) => s + x, 0);
const and = (lang: Lang) => (lang === 'en' ? 'and' : 'y');
const list = (items: string[], lang: Lang) => (items.length <= 1 ? items.join('') : `${items.slice(0, -1).join(', ')} ${and(lang)} ${items[items.length - 1]}`);
/** The column of a state in `pooled.matrix_state` (the seven grades, D, W). */
const stateIndex = (col: string) => (col === 'W' ? 8 : col === 'D' ? 7 : GRADES.indexOf(col as (typeof GRADES)[number]));
/** An en-dash, an em-dash or an arrow (U+2190 to U+21FF, U+27F5 to U+27FF), written as escapes. */
const FORBIDDEN = /[\u2013\u2014\u2190-\u21ff\u27f5-\u27ff]/;
const EMPTY_MARK: Record<Lang, string> = { en: ' (empty default column)', es: ' (columna de incumplimiento vacía)' };

/** The two sentences under the row table, parsed: the cohort's size, withdrawals and their share, the rated at the end;
 * and the two PDs, each captured beside its own definition's label. */
function cohortSentence(markup: string, lang: Lang) {
  const s = para(markup, 'data-summary', 'cohort') ?? '';
  const m = (lang === 'en'
    ? /^(\S+) ratings in (\S+) at the start (.+?); (\S+) withdrawn by the end of the year \((.+?)\), (\S+) rated at the end\.$/
    : /^(\S+) calificaciones en (\S+) al inicio (.+?); (\S+) retiradas antes del fin del año \((.+?)\), (\S+) calificadas al final\.$/
  ).exec(s);
  return m ? { size: m[1], grade: m[2], where: m[3], withdrawn: m[4], withdrawnShare: m[5], rated: m[6] } : null;
}
function pdSentence(markup: string, lang: Lang) {
  const s = para(markup, 'data-summary', 'pd') ?? '';
  const keep = reEsc(pick(DEFINITION_LABEL.keep, lang));
  const d4 = reEsc(pick(DEFINITION_LABEL.d4, lang));
  const m = (lang === 'en'
    ? new RegExp(`^One-year PD of (\\S+): (.+?) under "${keep}" \\(over the whole cohort\\), (.+?) under "${d4}" \\(over the (\\S+) rated at the end\\)\\.$`)
    : new RegExp(`^PD a un año de (\\S+): (.+?) con "${keep}" \\(sobre toda la cohorte\\), (.+?) con "${d4}" \\(sobre las (\\S+) calificadas al final\\)\\.$`)
  ).exec(s);
  return m ? { grade: m[1], keep: m[2], d4: m[3], rated: m[4] } : null;
}

/** No English left in a Spanish render, no Spanish in an English one (the attribution is verbatim, in English). */
function oneLanguage(markup: string, o: C04AgencyOutputs, lang: Lang, where: string) {
  const t = text(markup).replace(o.attribution, '');
  if (lang === 'es') expect(t, `${where}: English in the Spanish view`).not.toMatch(/\b(the|and|of|under|over|with)\b/);
  else expect(t, `${where}: Spanish in the English view`).not.toMatch(/\b(el|los|las|del|año|con|sobre)\b/);
}

describe('the agency Model group of C04', () => {
  it('applies to the three agency variants of the design', () => {
    expect(agencies.map((c) => c.id)).toEqual(['sp', 'moodys', 'fitch']);
  });

  for (const c of agencies) {
    for (const lang of LANGS) {
      it(`the matrix view of ${c.id} in ${lang}, pooled, every grade: two replayed cards with the attribution, the controls, the map, and the grade's row with its sentences in their places`, () => {
        const o = outputsOf(c.data);
        const n = o.cohorts.length;
        const short = pick(c.data.manifest.artifacts.find((a) => a.variant_id === c.id)!.short_title, lang);
        for (let g = 0; g < GRADES.length; g++) {
          const where = `${c.id} ${GRADES[g]} ${lang}`;
          const markup = html(<MatrixView sel={makeSel(c.data, { grade: g })} />, lang);
          expect(markup).not.toContain('data-state="loading"');
          expect(markup).not.toMatch(FORBIDDEN);
          oneLanguage(markup, o, lang, where);
          const found = cards(markup);
          expect(found).toHaveLength(2);
          for (const card of found) {
            expect(card.lane).toBe('replay');
            expect(card.provenance).toBe('real');
            expect(card.markup).toContain(esc(o.attribution));
            expect(card.markup).toContain(esc(o.agency.name));
          }
          expect(found[0].title).toBe(
            lang === 'en' ? `${short}: the pooled one-year matrix, ${o.cohorts[0].label} to ${o.cohorts[n - 1].label}` : `${short}: la matriz anual agrupada, ${o.cohorts[0].label} a ${o.cohorts[n - 1].label}`,
          );
          expect(found[1].title).toBe(lang === 'en' ? `Where ${GRADES[g]} ended the year` : `Dónde quedó ${GRADES[g]} al final del año`);
          // the cohort knob and the colour scale, registered controls side by side above the map (ct-row); the map and
          // its readout
          expect(markup).toMatch(/<div class="ct-row" data-controls="c04-map"><div class="caos-knob" data-control="c04-map-cohort"/);
          expect(markup).toContain('data-control="c04-map-scale"');
          expect(markup).toContain('class="ct-map"');
          expect(markup).toContain('data-readout="matrix"');
          // the grade's row: every state's share of the cohort and its count, as the artifact has them, the row first
          const cols = o.pd.d4 ? [...GRADES, 'D', 'W'] : [...GRADES, 'W'];
          expect(markup.includes('data-state="D"')).toBe(o.pd.d4 !== null);
          for (const col of cols) {
            const j = stateIndex(col);
            const expected = [share(o.pooled.matrix_state[g][j], lang), count(j === 8 ? o.pooled.withdrawn[g] : o.pooled.counts[g][j], lang)];
            expect(cells(markup, 'data-state', col).slice(1), `${where} ${col}`).toEqual(expected);
          }
          expect(markup).toContain(`<tr data-state="${GRADES[g]}" class="ct-current">`);
          const size = sum(o.pooled.counts[g]) + o.pooled.withdrawn[g];
          const wd = o.pooled.withdrawn[g];
          expect(cells(markup, 'data-state', 'all').slice(1)).toEqual([share(1, lang), count(size, lang)]);
          expect(markup.indexOf('data-table="c04-matrix-row"')).toBeLessThan(markup.indexOf('data-summary="cohort"'));
          // the cohort's size, its withdrawals, their share of the size and the rated at the end, each in its place
          expect(cohortSentence(markup, lang), where).toEqual({
            size: count(size, lang),
            grade: GRADES[g],
            where: lang === 'en' ? `over the ${n} cohorts ${o.cohorts[0].label} to ${o.cohorts[n - 1].label}` : `en las ${n} cohortes ${o.cohorts[0].label} a ${o.cohorts[n - 1].label}`,
            withdrawn: count(wd, lang),
            withdrawnShare: share(wd / size, lang),
            rated: count(size - wd, lang),
          });
          if (o.pd.d4) {
            // Keep (D over the whole cohort, matrix_state) and D4 (D over the rated at the end, matrix), each beside its
            // own definition, with ESMA's statement
            expect(pdSentence(markup, lang), where).toEqual({ grade: GRADES[g], keep: share(o.pooled.matrix_state[g][7], lang), d4: share(o.pooled.matrix[g][7], lang), rated: count(size - wd, lang) });
            // the matrix's default column is D4's pooled rate (the artifact writes the rates at nine significant digits)
            expect(o.pooled.matrix[g][7]).toBeCloseTo(nn(o.lra.d4!.pooled_rate[g]), 9);
            expect(markup).toContain(esc(pick(ESMA_DEFINITIONS, lang)));
          } else {
            expect(pdSentence(markup, lang)).toBeNull();
            expect(para(markup, 'data-summary', 'pd')).toBe(
              lang === 'en'
                ? "Moody's transition page has no default category: its PDs by grade come from the default pages (D2 and D3), in the Validation group."
                : "La página de transiciones de Moody's no tiene categoría de incumplimiento: sus PD por grado vienen de las páginas de incumplimientos (D2 y D3), en el grupo Validación.",
            );
          }
          // the pooled matrix says which cohorts have an empty default column (Fitch's): in full under the row, short in
          // the map's note
          const empty = emptyPooledText(o, 'row');
          expect(para(markup, 'data-summary', 'empty')).toBe(empty.en ? pick(empty, lang) : null);
          const mapEmpty = emptyPooledText(o, 'map');
          if (mapEmpty.en) expect(found[0].note).toContain(pick(mapEmpty, lang));
          else expect(found[0].note).not.toContain(lang === 'en' ? '(in W here)' : '(aquí en W)');
          expect(Boolean(mapEmpty.en)).toBe(c.id === 'fitch');
        }
      });
    }
  }

  it("Fitch's empty default columns: 2006 to 2014, 189 rated defaulters, the same cohorts AgencyValidationViews names", () => {
    for (const c of agencies) {
      const o = outputsOf(c.data);
      const mine = emptyColumnCohorts(o);
      expect(
        mine.map((e) => ({ year: Number(o.cohorts[e.cohort].begin.slice(0, 4)), defaulted: e.defaulted })),
        c.id,
      ).toEqual(emptyDefaultYears(o));
      for (const e of mine) {
        expect(o.cohorts[e.cohort].label).toBe(e.label);
        expect(o.cohorts[e.cohort].counts.every((row) => row[7] === 0)).toBe(true);
      }
    }
    const fitch = outputsOf(dataOf('fitch'));
    const empty = emptyColumnCohorts(fitch);
    expect(empty.map((e) => e.label)).toEqual(['2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014']);
    expect(sum(empty.map((e) => e.defaulted))).toBe(189);
    expect(emptyColumnCohorts(outputsOf(dataOf('sp')))).toEqual([]);
    expect(emptyColumnCohorts(outputsOf(dataOf('moodys')))).toEqual([]);
    expect(emptyPooledText(fitch, 'row').en).toBe(
      'The pooled default column includes the cohorts 2006 to 2014, in which the transition page holds no rating in default in any grade while the default page counts 189 rated defaulters: the transition page counts them as withdrawn, so the pooled D column, and the D4 and Keep PDs read from it, understate the defaults the default page counts.',
    );
    expect(emptyPooledText(fitch, 'row').es).toBe(
      'La columna de incumplimiento agrupada incluye las cohortes 2006 a 2014, en las que la página de transiciones no tiene ninguna calificación en incumplimiento en ningún grado mientras la página de incumplimientos cuenta 189 calificaciones incumplidas: la página de transiciones las cuenta como retiradas, así que la columna D agrupada, y las PD con D4 y Con retiros que se leen de ella, subestiman los incumplimientos que cuenta la página de incumplimientos.',
    );
    expect(emptyPooledText(fitch, 'map')).toEqual({
      en: "D includes 2006 to 2014, when the transition page counts no rating in default while the default page counts 189 rated defaulters (in W here): D understates that page's defaults.",
      es: 'D incluye 2006 a 2014, cuando la página de transiciones no cuenta ninguna calificación en incumplimiento mientras la página de incumplimientos cuenta 189 calificaciones incumplidas (aquí en W): D subestima los incumplimientos de esa página.',
    });
    expect(emptyPooledText(fitch, 'generators')).toEqual({
      en: "The pooled matrix includes 2006 to 2014, when the transition page counts no rating in default while the default page counts 189 rated defaulters: these PDs understate that page's.",
      es: 'La matriz agrupada incluye 2006 a 2014, cuando la página de transiciones no cuenta ninguna calificación en incumplimiento mientras la página de incumplimientos cuenta 189 calificaciones incumplidas: estas PD subestiman las de esa página.',
    });
    for (const scope of ['row', 'map', 'generators'] as const) {
      expect(emptyPooledText(outputsOf(dataOf('sp')), scope)).toEqual({ en: '', es: '' });
      expect(emptyPooledText(outputsOf(dataOf('moodys')), scope)).toEqual({ en: '', es: '' });
    }
    // the cohort 2009 at CCC-C: 77 rated defaulters on the default page, 34 of them in CCC-C (D2 43.6%), 0 by the
    // transition page; at AAA none of them
    const k = fitch.cohorts.findIndex((x) => x.label === '2009');
    expect(emptyCohortText(fitch, k, 6).en).toBe(
      `In 2009 the transition page holds no rating in default in any grade while the default page counts 77 rated defaulters, 34 of them in CCC-C (${share(fitch.pd.d2![k][6], 'en')} under "D2 rated defaulters"): the transition page counts them as withdrawn (W), so the D column, D4 and Keep read 0 by the page, not by the cohort.`,
    );
    expect(share(fitch.pd.d2![k][6], 'en')).toBe('43.6\u00a0%');
    expect(emptyCohortText(fitch, k, 0).es).toContain('77 calificaciones incumplidas, ninguna de ellas en AAA:');
    expect(emptyCohortText(fitch, k, null)).toEqual({
      en: 'In 2009 the transition page counts no rating in default while the default page counts 77 rated defaulters (in W here): D reads 0 by the page, not by the cohort.',
      es: 'En 2009 la página de transiciones no cuenta ninguna calificación en incumplimiento mientras la página de incumplimientos cuenta 77 calificaciones incumplidas (aquí en W): D marca 0 por la página, no por la cohorte.',
    });
    expect(emptyCohortText(fitch, fitch.cohorts.findIndex((x) => x.label === '2005'), 6)).toEqual({ en: '', es: '' });
  });

  for (const c of agencies) {
    it(`the matrix view of ${c.id}, one cohort's own matrix at every grade, both languages: its counts over its size, its PDs beside their definitions, an empty default column said`, () => {
      const o = outputsOf(c.data);
      const n = o.cohorts.length;
      const empty = new Set(emptyColumnCohorts(o).map((e) => e.cohort));
      const ks = [...new Set([0, Math.floor(n / 2), n - 1, ...empty, ...(c.id === 'fitch' ? [3, 13] : [])])];
      for (const k of ks) {
        const cohort = o.cohorts[k];
        for (const lang of LANGS) {
          for (let g = 0; g < GRADES.length; g++) {
            const where = `${c.id} ${cohort.label} ${GRADES[g]} ${lang}`;
            const markup = html(<MatrixView sel={makeSel(c.data, { cohort: k, grade: g })} />, lang);
            expect(markup, where).not.toMatch(FORBIDDEN);
            const found = cards(markup);
            expect(found[0].title).toBe(lang === 'en' ? `${pick(c.data.manifest.artifacts.find((a) => a.variant_id === c.id)!.short_title, 'en')}: the ${cohort.label} cohort's one-year matrix` : `${pick(c.data.manifest.artifacts.find((a) => a.variant_id === c.id)!.short_title, 'es')}: la matriz anual de la cohorte ${cohort.label}`);
            expect(markup).toContain(`<span class="caos-knob-value">${count(k + 1, lang)}\u00a0(${cohort.label})</span>`);
            const size = cohort.size[g];
            const wd = cohort.withdrawn[g];
            for (const col of o.pd.d4 ? [...GRADES, 'D', 'W'] : [...GRADES, 'W']) {
              const j = stateIndex(col);
              const x = j === 8 ? wd : cohort.counts[g][j];
              expect(cells(markup, 'data-state', col).slice(1), `${where} ${col}`).toEqual([size > 0 ? share(x / size, lang) : '-', count(x, lang)]);
            }
            expect(cells(markup, 'data-state', 'all').slice(1)).toEqual([size > 0 ? share(1, lang) : '-', count(size, lang)]);
            if (size > 0) {
              expect(cohortSentence(markup, lang), where).toEqual({
                size: count(size, lang),
                grade: GRADES[g],
                where: lang === 'en' ? `in the ${cohort.label} cohort` : `en la cohorte ${cohort.label}`,
                withdrawn: count(wd, lang),
                withdrawnShare: share(wd / size, lang),
                rated: count(size - wd, lang),
              });
            }
            const isEmpty = empty.has(k);
            if (o.pd.d4) {
              const mark = isEmpty ? EMPTY_MARK[lang] : '';
              expect(pdSentence(markup, lang), where).toEqual({
                grade: GRADES[g],
                keep: `${share(o.pd.keep![k][g], lang)}${mark}`,
                d4: `${share(o.pd.d4[k][g], lang)}${mark}`,
                rated: count(size - wd, lang),
              });
              // Keep is D over the whole cohort, D4 D over the rated at the end: the artifact's rates are the counts'
              expect(o.pd.keep![k][g]).toBeCloseTo(cohort.counts[g][7] / size, 9);
              expect(o.pd.d4[k][g]).toBeCloseTo(cohort.counts[g][7] / (size - wd), 9);
            }
            // an empty default column is said under the row, for its grade, and in the map's note, for the cohort
            expect(para(markup, 'data-summary', 'empty'), where).toBe(isEmpty ? pick(emptyCohortText(o, k, g), lang) : null);
            if (isEmpty) {
              expect(found[0].note).toContain(pick(emptyCohortText(o, k, null), lang));
              // the cohort's rated defaulters on the default page, the grade's among them and their D2 rate (not D3's:
              // the two differ at CCC-C in 2008), each in its place
              const ng = cohort.defaulted![g];
              const d2 = pick(DEFINITION_LABEL.d2, lang);
              const grade = GRADES[g];
              const total = count(sum(cohort.defaulted!), lang);
              const clause =
                lang === 'en'
                  ? ng > 0
                    ? `counts ${total} rated defaulters, ${count(ng, lang)} of them in ${grade} (${share(o.pd.d2![k][g], lang)} under "${d2}"): `
                    : `counts ${total} rated defaulters, none of them in ${grade}: `
                  : ng > 0
                    ? `cuenta ${total} calificaciones incumplidas, ${count(ng, lang)} de ellas en ${grade} (${share(o.pd.d2![k][g], lang)} con "${d2}"): `
                    : `cuenta ${total} calificaciones incumplidas, ninguna de ellas en ${grade}: `;
              expect(para(markup, 'data-summary', 'empty')).toContain(lang === 'en' ? `In ${cohort.label} the transition page` : `En ${cohort.label} la página de transiciones`);
              expect(para(markup, 'data-summary', 'empty'), where).toContain(clause);
            } else {
              expect(found[0].note).not.toContain(lang === 'en' ? '(in W here)' : '(aquí en W)');
            }
          }
        }
      }
      // an index outside the cohorts reads as the pooled matrix
      expect(matrixData(o, n).cohort).toBeNull();
      expect(matrixData(o, -1).label).toBeNull();
    });
  }

  it('the cohort knob: 0 is the pooled matrix, i + 1 the cohort i, a position beyond the last cohort is the last', () => {
    expect(knobOfCohort(null)).toBe(0);
    expect(knobOfCohort(4)).toBe(5);
    expect(cohortOfKnob(0, 26)).toBeNull();
    expect(cohortOfKnob(5, 26)).toBe(4);
    expect(cohortOfKnob(2.6, 26)).toBe(2);
    expect(cohortOfKnob(40, 26)).toBe(25);
    expect(cohortOfKnob(3, 0)).toBeNull();
    const markup = html(<MatrixView sel={makeSel(dataOf('sp'))} />, 'es');
    expect(markup).toContain('<span class="caos-knob-value">0\u00a0(agrupada)</span>');
    expect(markup).toContain('title="0 es la matriz agrupada sobre las 26 cohortes anuales; 1 a 26 la matriz propia de una cohorte');
  });

  it("the map draws one cell per state, keeps W out of the migrations scale, marks the rail's grade, and a picked row sets the rail's grade", () => {
    for (const c of agencies) {
      const o = outputsOf(c.data);
      const setGrade = vi.fn();
      const base = makeSel(c.data);
      const sel: C04Sel = { ...base, grade: 2, act: { ...base.act, setGrade } };
      const m = matrixData(o, null);
      const props = mapProps(sel, m, { en: 'test', es: 'prueba' });
      expect(props.outside).toEqual([m.cols.length - 1]);
      expect(m.cols[props.outside![0]]).toBe('W');
      const drawing = renderToStaticMarkup(<MatrixDrawing p={props} width={720} height={400} hover={null} setHover={() => undefined} />);
      expect(drawing).toContain(`data-cells="${7 * (o.pd.d4 ? 9 : 8)}"`);
      expect(drawing).toContain('data-row="A" data-selected="1"');
      expect(props.scale).toBe('migrations');
      // the diagonal and W grey, out of the migrations range; every cell coloured on the linear scale
      expect(drawing.match(/fill="var\(--color-surface-2\)"/g)).toHaveLength(14);
      const linear = renderToStaticMarkup(<MatrixDrawing p={{ ...props, scale: 'linear' }} width={720} height={400} hover={null} setHover={() => undefined} />);
      expect(linear.match(/fill="var\(--color-surface-2\)"/g)).toBeNull();
      props.onPickRow?.(5);
      expect(setGrade).toHaveBeenCalledWith(5);
    }
    // the scale's text says what it keeps out, and names D among the migrations only where the page has a default category
    expect(scaleTexts(true)[0].note).toEqual({ en: 'Colour: viridis, linear over the migrations, D included; the diagonal and W grey and out of the range.', es: 'Color: viridis, lineal sobre las migraciones, D incluida; la diagonal y W en gris y fuera del rango.' });
    expect(scaleTexts(false)[0].note.en).toBe('Colour: viridis, linear over the migrations; the diagonal and W grey and out of the range.');
    expect(scaleTexts(true).map((s) => s.id)).toEqual(['migrations', 'linear', 'log']);
  });

  it('the cohort, the scale and the grade each change what the matrix view shows', () => {
    const data = dataOf('fitch');
    const s0 = makeSel(data);
    const base = html(<MatrixView sel={s0} />, 'en');
    expect(html(<MatrixView sel={{ ...s0, cohort: 3 }} />, 'en')).not.toBe(base);
    expect(html(<MatrixView sel={{ ...s0, mapScale: 'log' }} />, 'en')).not.toBe(base);
    expect(html(<MatrixView sel={{ ...s0, grade: 3 }} />, 'en')).not.toBe(base);
    expect(html(<GeneratorsView sel={{ ...s0, grade: 3 }} />, 'en')).not.toBe(html(<GeneratorsView sel={s0} />, 'en'));
  });

  for (const c of agencies) {
    for (const lang of LANGS) {
      it(`the generators view of ${c.id} in ${lang}, every grade: the PD chart (or one card without a default category), the verdict, the diagnostics and the distances in their places`, () => {
        const o = outputsOf(c.data);
        const e = o.embedding;
        const short = pick(c.data.manifest.artifacts.find((a) => a.variant_id === c.id)!.short_title, lang);
        for (let g = 0; g < GRADES.length; g++) {
          const where = `${c.id} ${GRADES[g]} ${lang}`;
          const markup = html(<GeneratorsView sel={makeSel(c.data, { grade: g })} />, lang);
          expect(markup).not.toContain('data-state="loading"');
          expect(markup).not.toMatch(FORBIDDEN);
          oneLanguage(markup, o, lang, where);
          const found = cards(markup);
          for (const card of found) {
            expect(card.lane).toBe('replay');
            expect(card.provenance).toBe('real');
            expect(card.markup).toContain(esc(o.attribution));
            expect(card.markup).toContain(esc(o.agency.name));
            expect(card.note).toContain(`Israel, Rosenthal ${and(lang)} Wei`);
          }
          // the methods' source in full, with its DOI, in the note of the card that names the methods (the first)
          expect(found[0].note).toContain(`Israel, Rosenthal ${and(lang)} Wei (2001), Mathematical Finance 11(2), 245-265, doi:10.1111/1467-9965.00114`);
          expect(found[0].note).toContain(lang === 'en' ? 'Bladt and Sørensen 2005' : 'Bladt y Sørensen 2005');
          const series = pdSeries(o);
          const drawn = charts(markup);
          const emptyGen = emptyPooledText(o, 'generators');
          if (o.pd.d4) {
            // a chart of the pooled matrix and the four generators, none of them empty, both axes titled; beside it the
            // verdict, the diagnostics, then the distances and EM's fit
            expect(found).toHaveLength(2);
            expect(drawn).toHaveLength(1);
            expect(series.length).toBe(5);
            expect(drawn[0].series).toBe(series.length);
            for (const s of series) {
              expect(s.values.some((x) => x !== null && x > 0), pick(s.label, 'en')).toBe(true);
              expect(markup).toContain(esc(pick(s.label, lang)));
            }
            for (const axis of drawn[0].axes) expect(axis.trim().length).toBeGreaterThan(0);
            expect(found[0].note).toContain(lang === 'en' ? 'under "D4 matrix column"' : 'con "D4 columna de la matriz"');
            expect(found[1].title).toBe(lang === 'en' ? 'Diagnostics and distances' : 'Diagnósticos y distancias');
            const second = found[1].markup;
            const at = (s: string) => second.indexOf(s);
            expect(at('data-verdict=')).toBeGreaterThanOrEqual(0);
            expect(at('data-verdict=')).toBeLessThan(at('data-table="c04-embedding"'));
            expect(at('data-table="c04-embedding"')).toBeLessThan(at('data-table="c04-generators"'));
            expect(at('data-table="c04-generators"')).toBeLessThan(at('data-em=""'));
            // the PD column names its definition and unit; the grade's one-year PD beside every generator's L1, as the
            // artifact has them, in percent without the sign
            expect(second).toContain(`<th data-col="pd">${lang === 'en' ? `One-year PD (D4, %), ${GRADES[g]}` : `PD a un año (D4, %), ${GRADES[g]}`}</th>`);
            expect(found[1].note).toContain(lang === 'en' ? 'its PD under "D4 matrix column", in percent.' : 'su PD con "D4 columna de la matriz", en porcentaje.');
            expect(cells(markup, 'data-generator', 'pooled').slice(1, 3)).toEqual(['-', pc(o.pooled.matrix[g][7], lang)]);
            for (const k of GENERATOR_KEYS) {
              const gen = o.generators[k]!;
              expect(cells(markup, 'data-generator', k).slice(1, 3), `${where} ${k}`).toEqual([l1(gen.l1, lang), pc(gen.pd_1y[g]!, lang)]);
            }
            // the chart's note says which grades have no point, and Fitch's empty default columns; so does the second
            // card, under the distances whose PDs they lower
            const zero = zeroDefaultText(o);
            expect(zero.en.length).toBeGreaterThan(0);
            expect(found[0].note).toContain(pick(zero, lang));
            expect(Boolean(emptyGen.en)).toBe(c.id === 'fitch');
            if (emptyGen.en) {
              expect(found[0].note).toContain(pick(emptyGen, lang));
              expect(para(second, 'data-empty', '')).toBe(pick(emptyGen, lang));
              expect(at('data-table="c04-generators"')).toBeLessThan(at('data-empty=""'));
            } else {
              expect(second).not.toContain('data-empty=""');
            }
          } else {
            // Moody's: no PD can be drawn; one card at the row's width says why and gives the verdict, the distances,
            // EM's fit and the diagnostics, in that order
            expect(series).toHaveLength(0);
            expect(drawn).toHaveLength(0);
            expect(found).toHaveLength(1);
            expect(markup).toContain('<div class="caos-views-row" data-views="1">');
            expect(found[0].title).toBe(lang === 'en' ? `${short}: the generators of the pooled matrix, their distances and diagnostics` : `${short}: los generadores de la matriz agrupada, sus distancias y diagnósticos`);
            expect(found[0].note).toContain(lang === 'en' ? 'has no default category' : 'no tiene categoría de incumplimiento');
            const card = found[0].markup;
            const at = (s: string) => card.indexOf(s);
            expect(at('data-verdict=')).toBeGreaterThanOrEqual(0);
            expect(at('data-verdict=')).toBeLessThan(at('data-table="c04-generators"'));
            expect(at('data-table="c04-generators"')).toBeLessThan(at('data-em=""'));
            expect(at('data-em=""')).toBeLessThan(at('data-table="c04-embedding"'));
            expect(markup).not.toContain('data-generator="pooled"');
            expect(markup).not.toContain('data-col="pd"');
            for (const k of GENERATOR_KEYS) expect(cells(markup, 'data-generator', k)[1], k).toBe(l1(o.generators[k]!.l1, lang));
            expect(emptyGen).toEqual({ en: '', es: '' });
          }
          // the verdict with Theorem 3's count of moves, and the generators closest to and farthest from the pooled matrix
          const present = GENERATOR_KEYS.filter((k) => o.generators[k]).map((k) => ({ k, l1: o.generators[k]!.l1 }));
          const byL1 = [...present].sort((a, b) => nn(a.l1) - nn(b.l1));
          const verdictPara = para(markup, 'data-verdict', e.exact_generator_excluded ? 'excluded' : 'open');
          expect(verdictPara).toBe(`${pick(verdict(o), lang)} ${pick(closestText(o), lang)}`);
          expect(verdictPara).toContain(lang === 'en' ? `(c) ${count(e.theorem3.c.length, lang)} moves reachable but never observed` : `(c) ${count(e.theorem3.c.length, lang)} movimientos alcanzables nunca observados`);
          expect(verdictPara).toMatch(new RegExp(`${lang === 'en' ? 'Closest' : 'Más cerca'}[^;]*\\(L1 ${reEsc(l1(byL1[0].l1, lang))}\\); ${lang === 'en' ? 'farthest' : 'más lejos'}[^;]*\\(L1 ${reEsc(l1(byL1[byL1.length - 1].l1, lang))}\\)\\.$`));
          // EM's fit
          expect(para(markup, 'data-em', '')).toBe(
            lang === 'en'
              ? `EM: ${count(o.generators.em.iterations, lang)} iterations, ${o.generators.em.converged ? 'converged' : 'not converged'}; log-likelihood ${formatNumber(o.generators.em.loglik, lang, { decimals: 1 })}.`
              : `EM: ${count(o.generators.em.iterations, lang)} iteraciones, ${o.generators.em.converged ? 'convergió' : 'no convergió'}; log-verosimilitud ${formatNumber(o.generators.em.loglik, lang, { decimals: 1 })}.`,
          );
          // Israel, Rosenthal and Wei's diagnostics with the artifact's values, each with its source; the moves never
          // observed named in the artifact's order; each break of monotonicity with its two tails in their places
          for (const id of ['S', 'det', 'c', 'monotone']) expect(diagnostic(markup, id).source, id).toMatch(/Israel et al\. \(2001\)/);
          expect(diagnostic(markup, 'S').value).toBe(l1(e.S, lang));
          expect(diagnostic(markup, 'det').value).toBe(`${l1(e.det, lang)} ${lang === 'en' ? 'against' : 'contra'} ${l1(e.prod_diagonal, lang)}`);
          const moves = diagnostic(markup, 'c');
          expect(moves.value).toBe(count(e.theorem3.c.length, lang));
          const named = e.theorem3.c.map(([i, j]) => `${o.states[i]} ${lang === 'en' ? 'to' : 'a'} ${o.states[j]}`);
          expect(moves.text).toContain(`${list(named, lang)}: ${lang === 'en' ? 'no exact generator, by (c).' : 'sin generador exacto, por (c).'}`);
          const monotone = diagnostic(markup, 'monotone');
          const breaks = e.monotonicity_violations.length;
          expect(monotone.value).toBe(e.stochastically_monotone ? (lang === 'en' ? 'yes' : 'sí') : `no, ${count(breaks, lang)} ${lang === 'en' ? (breaks === 1 ? 'break' : 'breaks') : breaks === 1 ? 'quiebre' : 'quiebres'}`);
          const sentences = e.monotonicity_violations.map((x) => {
            const [a, b] = x.tail !== null && x.next_tail !== null ? distinct(x.tail, x.next_tail, lang) : [share(x.tail, lang), share(x.next_tail, lang)];
            const end = x.column === 7 ? 'D' : `${o.states[x.column]} ${lang === 'en' ? 'or worse' : 'o peor'}`;
            return lang === 'en' ? `${o.states[x.row]} ${a} and ${o.states[x.next_row]} ${b} end in ${end}` : `${o.states[x.row]} ${a} y ${o.states[x.next_row]} ${b} terminan en ${end}`;
          });
          expect(monotone.text).toContain(`${lang === 'en' ? 'A grade ends lower more often than the next worse one:' : 'Un grado termina más abajo con más frecuencia que el siguiente peor:'} ${sentences.join('; ')}.`);
          expect(markup).toContain(`data-verdict="${e.exact_generator_excluded ? 'excluded' : 'open'}"`);
          // a name that is already a possessive keeps it (Moody's transition page, never Moody's's)
          expect(markup).not.toContain(esc("Moody's's"));
        }
      });
    }
  }

  it("the PD chart: the grades and the room after them, the artifact's series with a gap there, the log axis in whole decades holding every PD, the rail's grade marked at its own x", () => {
    for (const c of agencies) {
      const o = outputsOf(c.data);
      const series = pdSeries(o);
      for (let g = 0; g < GRADES.length; g++) {
        const chart = pdChart(o, g);
        expect(chart.x).toEqual([1, 2, 3, 4, 5, 6, 7, 7.9]);
        expect(chart.series.map((s) => s.values)).toEqual(series.map((s) => [...s.values, null]));
        expect(chart.marks).toEqual([{ x: g + 1, label: { en: GRADES[g], es: GRADES[g] } }]);
        expect(chart.range).toEqual(pdRange(series));
      }
      const values = series.flatMap((s) => s.values.filter((x): x is number => x !== null && x > 0));
      const range = pdRange(series);
      if (!values.length) {
        expect(range).toBeNull();
        continue;
      }
      const [lo, hi] = range!;
      expect(lo).toBeLessThanOrEqual(Math.min(...values));
      expect(lo * 10).toBeGreaterThan(Math.min(...values));
      expect(Number.isInteger(Math.round(Math.log10(lo) * 1e9) / 1e9)).toBe(true);
      expect(hi).toBeGreaterThanOrEqual(Math.max(...values));
      expect(Number.isInteger(Math.round(Math.log10(hi) * 1e9) / 1e9)).toBe(true);
    }
    // S&P: the smallest PD is EM's at AA (4.9e-5), under the decade 1e-4: the axis starts at 1e-5 and ends at 100%
    expect(pdRange(pdSeries(outputsOf(dataOf('sp'))))).toEqual([1e-5, 1]);
    // every PD below 1%: the top is a decade above the largest
    expect(pdRange([{ label: 'x', values: [0.0005, 0.003, null] }])).toEqual([1e-4, 0.1]);
    expect(pdRange([])).toBeNull();
  });

  it("the PD series are the artifact's: the pooled matrix's default column and each generator's one-year PD, gaps where a PD is not positive", () => {
    for (const c of agencies) {
      const o = outputsOf(c.data);
      const series = pdSeries(o);
      if (!o.pd.d4) {
        expect(series).toEqual([]);
        continue;
      }
      expect(series[0].values).toEqual(o.pooled.matrix.slice(0, 7).map((r) => (r[7] > 0 ? r[7] : null)));
      expect(series[0].mode).toBe('points');
      GENERATOR_KEYS.forEach((k, i) => {
        expect(series[i + 1].label).toEqual(ESTIMATOR_LABEL[k]);
        expect(series[i + 1].values).toEqual(o.generators[k]!.pd_1y.map((p) => (p !== null && p > 0 ? p : null)));
      });
    }
  });

  it("the grades without a default in the pooled matrix are named, with the generators' positive PDs for them", () => {
    const sp = outputsOf(dataOf('sp'));
    const fitch = outputsOf(dataOf('fitch'));
    expect(sp.pooled.matrix.slice(0, 7).map((r) => r[7] === 0)).toEqual([true, false, false, false, false, false, false]);
    expect(zeroDefaultText(sp)).toEqual({
      en: 'AAA has no default in the pooled matrix, so no point on the log axis; every generator gives it a positive PD, through moves to lower grades within the year.',
      es: 'AAA no tiene incumplimientos en la matriz agrupada, así que no tiene punto en el eje logarítmico; cada generador le da una PD positiva, por movimientos a grados peores dentro del año.',
    });
    expect(fitch.pooled.matrix.slice(0, 7).map((r) => r[7] === 0)).toEqual([true, true, true, false, false, false, false]);
    expect(zeroDefaultText(fitch).en).toBe('AAA, AA and A have no default in the pooled matrix, so no point on the log axis; every generator gives them a positive PD, through moves to lower grades within the year.');
    expect(zeroDefaultText(fitch).es).toBe('AAA, AA y A no tienen incumplimientos en la matriz agrupada, así que no tienen punto en el eje logarítmico; cada generador les da una PD positiva, por movimientos a grados peores dentro del año.');
    for (const o of [sp, fitch]) for (const k of GENERATOR_KEYS) expect(o.generators[k]!.pd_1y[0]!).toBeGreaterThan(0);
    // without a default category there is no default column to read
    expect(zeroDefaultText(outputsOf(dataOf('moodys')))).toEqual({ en: '', es: '' });
  });

  it("Theorem 3's verdict names its conditions and counts the moves; the closest and the farthest generator by L1", () => {
    const sp = outputsOf(dataOf('sp'));
    expect(sp.embedding.theorem3).toEqual({ a: false, b: false, c: [[0, 3], [0, 4], [0, 7], [5, 0], [6, 0], [6, 1]] });
    expect(verdict(sp)).toEqual({
      en: 'No exact generator: exp(Q) = P has no solution with Q a generator, by (c) 6 moves reachable but never observed. Every generator here is an approximation, judged by its L1 distance.',
      es: 'Sin generador exacto: exp(Q) = P no tiene solución con Q un generador, por (c) 6 movimientos alcanzables nunca observados. Cada generador aquí es una aproximación, juzgada por su distancia L1.',
    });
    const fitch = outputsOf(dataOf('fitch'));
    expect(verdict(fitch).en).toContain('by (c) 15 moves reachable but never observed.');
    // the other conditions, and a matrix Theorem 3 leaves open
    const both = { ...sp, embedding: { ...sp.embedding, theorem3: { a: true, b: true, c: [] } } };
    expect(verdict(both).en).toBe('No exact generator: exp(Q) = P has no solution with Q a generator, by (a) det P is not positive and (b) det P is above the product of the diagonal. Every generator here is an approximation, judged by its L1 distance.');
    const open = { ...sp, embedding: { ...sp.embedding, exact_generator_excluded: false } };
    expect(verdict(open).en).toBe('Theorem 3 does not rule out an exact generator of the pooled matrix.');
    expect(closestText(sp)).toEqual({
      en: "Closest to the pooled matrix: the weighted repair (L1 0.009801); farthest: JLT's approximation (L1 0.09891).",
      es: 'Más cerca de la matriz agrupada: la reparación ponderada (L1 0,009801); más lejos: la aproximación de JLT (L1 0,09891).',
    });
    for (const c of agencies) {
      const o = outputsOf(c.data);
      const L1 = (k: GeneratorKey) => o.generators[k]?.l1 ?? NaN;
      const byL1 = (GENERATOR_KEYS as GeneratorKey[]).filter((k) => Number.isFinite(L1(k))).sort((a, b) => L1(a) - L1(b));
      expect(closestText(o).en).toContain(`(L1 ${l1(o.generators[byL1[0]]!.l1, 'en')}); farthest`);
      expect(closestText(o).en.endsWith(`(L1 ${l1(o.generators[byL1[byL1.length - 1]]!.l1, 'en')}).`)).toBe(true);
    }
    // EM's fit, as the artifact has it
    expect(emLine(sp)).toEqual({
      en: `EM: ${sp.generators.em.iterations} iterations, converged; log-likelihood -67,129.1.`,
      es: `EM: ${sp.generators.em.iterations} iteraciones, convergió; log-verosimilitud -67.129,1.`,
    });
    expect(sp.generators.em.iterations).toBe(116);
  });

  it('two tails are written with as many digits as it takes to tell them apart', () => {
    expect(distinct(0.0036939314, 0.000396196513, 'en')).toEqual(['0.369\u00a0%', '0.0396\u00a0%']);
    expect(distinct(0.999929995, 0.999919491, 'en')).toEqual(['99.993\u00a0%', '99.992\u00a0%']);
    expect(distinct(0.999929995, 0.999919491, 'es')).toEqual(['99,993\u00a0%', '99,992\u00a0%']);
    // equal at every precision: eight digits, the same string
    expect(distinct(0.5, 0.5, 'en')).toEqual(['50\u00a0%', '50\u00a0%']);
    for (const c of agencies) {
      for (const x of outputsOf(c.data).embedding.monotonicity_violations) {
        if (x.tail === null || x.next_tail === null) continue;
        const [a, b] = distinct(x.tail, x.next_tail, 'en');
        expect(a, `${c.id} ${x.row} ${x.column}`).not.toBe(b);
      }
    }
  });

  it("names the entity whose tables these are and CEREP's attribution, in both languages", () => {
    const o = outputsOf(agencies[0].data);
    expect(sourceText(o).en).toBe("Source: ESMA CEREP; tables transformed by Contraste. Entity: Standard & Poor's Credit Market Services Europe Limited (STPGB), corporate long-term ratings by category.");
    expect(sourceText(o).es).toBe("Source: ESMA CEREP; tables transformed by Contraste. Entidad: Standard & Poor's Credit Market Services Europe Limited (STPGB), calificaciones corporativas de largo plazo por categoría.");
    expect(['S&P', "Moody's", 'Fitch'].map(possessive)).toEqual(["S&P's", "Moody's", "Fitch's"]);
  });

  it('waits only while the case loads, and says so on a variant that is not an agency', () => {
    expect(html(<MatrixView sel={null} />, 'en')).toContain('data-state="loading"');
    expect(html(<GeneratorsView sel={null} />, 'en')).toContain('data-state="loading"');
    const markov = variants.find((c) => c.id === 'markov')!.data;
    for (const View of [MatrixView, GeneratorsView]) {
      const markup = html(<View sel={makeSel(markov)} />, 'es');
      expect(markup).not.toContain('data-state="loading"');
      const found = cards(markup);
      expect(found).toHaveLength(1);
      expect(found[0].lane).toBe('replay');
      expect(found[0].provenance).toBe('synthetic');
      expect(charts(markup)).toHaveLength(0);
    }
  });
});
