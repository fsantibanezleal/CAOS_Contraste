// CT-406, CT-412: the published variant's views, rendered on the server from the committed artifact, in English and in
// Spanish. Papers (replay) sets every print beside its recomputation with its agreement, the stated reason where one
// does not agree, and Engelmann's projected paths with the printed extremes marked; Model (replay) says what each paper
// computes and why its matrices are not shown; Impact (live) recomputes Table 5 in the browser, which agrees with the
// print and with riskvalidation's recomputation, and follows the rail's correlation and level.
import { readFileSync } from 'node:fs';
import { formatNumber, useLangStore } from '@fasl-work/caos-app-shell';
import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import type { CaseData } from '../../api/artifacts';
import { effectiveN, pdAgrestiCoull, pdJeffreys, pdWald } from '../../engine/transitions';
import type { CaseManifest, ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import {
  PapersView,
  PublishedImpactView,
  PublishedModelView,
  RHO_GRID,
  TABLE5_LEVEL,
  engelmannAgreement,
  engelmannRows,
  formatBpRange,
  irwReason,
  pathChart,
  printsAs,
  table5Chart,
  table5Live,
} from './PublishedViews';
import { makeSel, type C04Sel, type PublishedVariant } from './selection';

type Lang = 'en' | 'es';
const LANGS: Lang[] = ['en', 'es'];

const derived = new URL('../../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;
const manifest = read<CaseManifest>('manifests/C04.json');
const dataOf = (id: string): CaseData => {
  const a = manifest.artifacts.find((x) => x.variant_id === id);
  if (!a) throw new Error(`no variant ${id}`);
  return { manifest, variant: read<VariantArtifact>(a.path), models: read<ModelsArtifact>(a.models_ref as string) };
};
const data = dataOf('published');
const o = (data.variant as unknown as PublishedVariant).outputs;

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
const unesc = (s: string) => s.replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&gt;/g, '>').replace(/&lt;/g, '<').replace(/&amp;/g, '&');

interface Card {
  title: string;
  lane: string;
  provenance: string;
  note: string;
}
function cards(markup: string): Card[] {
  return [...markup.matchAll(/<figure class="caos-plot[^"]*" data-plot="([^"]*)" data-lane="([^"]*)" data-provenance="([^"]*)"[\s\S]*?<\/figure>/g)].map((m) => ({
    title: unesc(m[1]),
    lane: m[2],
    provenance: m[3],
    note: unesc(/<p class="caos-plot-note">([\s\S]*?)<\/p>/.exec(m[0])?.[1] ?? ''),
  }));
}
function charts(markup: string): Array<{ series: number; axes: string[]; keys: string[] }> {
  return [...markup.matchAll(/<div class="caos-chart[^"]*" data-series="(\d+)" data-axis-titles="([^"]*)"[\s\S]*?<p class="caos-chart-readout"/g)].map((m) => ({
    series: Number(m[1]),
    axes: unesc(m[2]).split('|'),
    keys: [...m[0].matchAll(/<li class="caos-chart-key"[^>]*><span[^>]*><\/span>([\s\S]*?)<\/li>/g)].map((k) => unesc(k[1])),
  }));
}
/** The body rows of a table by its data-table name, each cell's text. */
function table(markup: string, name: string): string[][] {
  const m = new RegExp(`<table[^>]*data-table="${name}"[^>]*>([\\s\\S]*?)</table>`).exec(markup);
  if (!m) return [];
  const body = m[1].split('<tbody>')[1] ?? '';
  return [...body.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => [...r[1].matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((c) => unesc(c[1].replace(/<[^>]+>/g, ''))));
}

const sel = (over: Partial<C04Sel> = {}) => makeSel(data, over);
const VIEWS = [
  ['Papers', PapersView, 'replay', 2, [5]],
  ['Model', PublishedModelView, 'replay', 2, [2]],
  ['Impact', PublishedImpactView, 'live', 2, [8]],
] as const;

describe('the published variant: three papers recomputed', () => {
  for (const lang of LANGS) {
    it(`every view carries its lane and the published provenance, and draws: ${lang}`, () => {
      for (const [name, View, lane, nCards, series] of VIEWS) {
        const markup = html(<View sel={sel()} />, lang);
        expect(markup, `${name}: a loading placeholder`).not.toContain('data-state="loading"');
        expect(markup, `${name}: an unformatted value`).not.toMatch(/NaN|not available|no disponible|undefined/);
        expect(markup, `${name}: an em-dash, en-dash or arrow`).not.toMatch(/[\u2013\u2014\u2190-\u21ff]/);
        const found = cards(markup);
        expect(found, `${name}: cards`).toHaveLength(nCards);
        for (const c of found) {
          expect(c.lane, `${name} "${c.title}"`).toBe(lane);
          expect(c.provenance, `${name} "${c.title}"`).toBe('published');
          expect(c.note.length, `${name} "${c.title}": no note`).toBeGreaterThan(80);
        }
        const drawn = charts(markup);
        expect(drawn.map((c) => c.series), `${name}: the series drawn`).toEqual([...series]);
        for (const c of drawn) {
          expect(c.axes.every((a) => a.length > 0), `${name}: an axis without its title`).toBe(true);
          expect(c.keys).toHaveLength(c.series);
        }
      }
    });
  }

  it('speaks Spanish in Spanish', () => {
    const papers = html(<PapersView sel={sel()} />, 'es');
    expect(papers).toContain('Tres artículos: cada valor impreso junto a su recálculo');
    expect(papers).not.toMatch(/does not agree|>agrees<|Recomputed|Printed/);
    const model = html(<PublishedModelView sel={sel()} />, 'es');
    expect(model).toContain('Qué calcula cada artículo');
    expect(model).toContain('Clase de licencia: solo derivados');
    expect(model).not.toMatch(/What it computes|Licence class/);
    const impact = html(<PublishedImpactView sel={sel()} />, 'es');
    expect(impact).toContain('En vivo contra lo impreso');
    expect(impact).not.toMatch(/Live against the print|>agrees</);
  });

  it('Israel et al.: nine distances, eight agree, and the ninth says why it does not', () => {
    expect(o.irw.rows).toHaveLength(9);
    for (const lang of LANGS) {
      const rows = table(html(<PapersView sel={sel()} />, lang), 'irw');
      expect(rows).toHaveLength(9);
      o.irw.rows.forEach((r, k) => {
        expect(rows[k][0]).toBe(r.matrix);
        expect(rows[k].slice(2, 4)).toEqual([formatNumber(r.printed, lang, { decimals: 6 }), formatNumber(r.recomputed, lang, { decimals: 8 })]);
        if (r.agrees) expect(rows[k][4]).toBe(lang === 'en' ? 'agrees' : 'concuerda');
      });
      const jlt = rows[o.irw.rows.findIndex((r) => !r.agrees)];
      expect(jlt[4]).toContain(lang === 'en' ? 'does not agree: equation (3) on the printed matrix gives' : 'no concuerda: la ecuación (3) sobre la matriz impresa da');
      expect(jlt[4]).toContain(formatNumber(o.irw.jlt_from_printed_generator, lang, { decimals: 6 }));
    }
    expect(o.irw.rows.filter((r) => r.agrees)).toHaveLength(8);
    const off = o.irw.rows.find((r) => !r.agrees);
    expect(off && irwReason(o, off)).not.toBeNull();
    for (const r of o.irw.rows.filter((x) => x.agrees)) expect(irwReason(o, r)).toBeNull();
  });

  it("Schuermann and Hanson's Table 5: six intervals and three N dagger, each beside the print", () => {
    for (const lang of LANGS) {
      const rows = table(html(<PapersView sel={sel()} />, lang), 'sr190');
      expect(rows).toHaveLength(o.sr190.rows.length + o.sr190.n_dagger.printed.length);
      o.sr190.rows.forEach((r, k) => {
        expect(rows[k].slice(2)).toEqual([
          formatBpRange(lang, r.printed[0], r.printed[1], 2),
          formatBpRange(lang, r.recomputed[0], r.recomputed[1], 3),
          formatNumber(r.printed[2] * 1e4, lang, { decimals: 2 }),
          formatNumber(r.recomputed[2] * 1e4, lang, { decimals: 3 }),
          lang === 'en' ? 'agrees' : 'concuerda',
        ]);
      });
      o.sr190.n_dagger.printed.forEach((p, k) => {
        const row = rows[o.sr190.rows.length + k];
        expect(row.slice(2)).toEqual([
          formatNumber(p, lang, { decimals: o.sr190.n_dagger.decimals[k] }),
          formatNumber(o.sr190.n_dagger.recomputed[k], lang, { decimals: o.sr190.n_dagger.decimals[k] + 2 }),
          '',
          '',
          lang === 'en' ? 'agrees' : 'concuerda',
        ]);
      });
    }
  });

  it("Engelmann's section 4: W_ttc, the TTC PD, each portfolio's PD and extreme; W hat within the rounding of its entries", () => {
    const rows = engelmannRows(o);
    // eight entries of W_ttc, its PD, four starting portfolios and the two extremes the paper prints
    expect(rows).toHaveLength(o.engelmann.w_ttc.printed.length + 1 + o.engelmann.portfolios.length + o.engelmann.portfolios.filter((p) => p.extreme).length);
    expect(rows).toHaveLength(15);
    for (const r of rows) {
      if (r.check === 'printed digits') expect(printsAs(r.recomputed, r.printed, r.decimals), r.key).toBe(true);
    }
    const hat = rows.find((r) => r.check === 'entry rounding');
    expect(hat?.key).toBe('W hat-pd0');
    expect(printsAs((hat as NonNullable<typeof hat>).recomputed, (hat as NonNullable<typeof hat>).printed, (hat as NonNullable<typeof hat>).decimals)).toBe(false);
    for (const lang of LANGS) {
      const cells = table(html(<PapersView sel={sel()} />, lang), 'engelmann');
      expect(cells).toHaveLength(rows.length);
      rows.forEach((r, k) => {
        expect(cells[k][0]).toBe(r.label[lang]);
        expect(cells[k][3]).toBe(engelmannAgreement(r, lang));
      });
      // the TTC PD as printed (1.198%) and recomputed, in percent
      const ttc = cells[rows.findIndex((r) => r.key === 'ttc-pd')];
      expect(ttc.slice(1, 3)).toEqual([formatNumber(o.engelmann.ttc_pd.printed, lang, { percent: true, decimals: 3 }), formatNumber(o.engelmann.ttc_pd.recomputed, lang, { percent: true, decimals: 5 })]);
      expect(cells[rows.indexOf(hat as NonNullable<typeof hat>)][3]).toContain(lang === 'en' ? 'within the rounding of its printed entries' : 'dentro del redondeo de sus entradas impresas');
    }
  });

  it('agrees as the pipeline does: within half a unit of the last printed digit, both ends inclusive', () => {
    expect(printsAs(0.027245, 0.02725, 5)).toBe(true);
    expect(printsAs(0.027255, 0.02725, 5)).toBe(true);
    expect(printsAs(0.027244, 0.02725, 5)).toBe(false);
    expect(printsAs(0.116900352, 0.1169, 6)).toBe(true);
    expect(printsAs(0.116476511, 0.1169, 6)).toBe(false);
  });

  it("Engelmann's paths: four portfolios and the TTC PD, the printed extremes marked at their years", () => {
    const chart = pathChart(o);
    expect(chart.years).toEqual(Array.from({ length: 50 }, (_, i) => i + 1));
    expect(chart.series).toHaveLength(o.engelmann.portfolios.length + 1);
    for (const s of chart.series) expect(s.values.every((x) => x !== null && Number.isFinite(x))).toBe(true);
    const at = (name: string, kind: 'min' | 'max') => {
      const path = o.engelmann.portfolios.find((p) => p.name === name)?.pd_path ?? [];
      const target = kind === 'min' ? Math.min(...path) : Math.max(...path);
      return path.indexOf(target) + 1;
    };
    // short labels: the shell draws a mark's label beside its line, and the printed values are in the table
    expect(chart.marks).toEqual([
      { x: at('W_init 2', 'min'), label: { en: 'W_init 2, min', es: 'W_init 2, mín' } },
      { x: at('W tilde', 'max'), label: { en: 'W tilde, max', es: 'W tilde, máx' } },
    ]);
    expect(chart.marks.map((m) => m.x)).toEqual([21, 5]);
    const keys = charts(html(<PapersView sel={sel()} />))[0].keys;
    expect(keys).toEqual([...o.engelmann.portfolios.map((p) => p.name), `TTC PD ${formatNumber(o.engelmann.ttc_pd.recomputed, 'en', { percent: true, digits: 4 })}`]);
  });

  it('the Model view names each paper, its licence class and why its matrices are not shown', () => {
    for (const lang of LANGS) {
      const markup = html(<PublishedModelView sel={sel()} />, lang);
      const rows = table(markup, 'papers');
      expect(rows).toHaveLength(3);
      for (const source of ['israel-rosenthal-wei-2001', 'schuermann-hanson-2004', 'engelmann-2024']) {
        expect(markup).toContain(`data-source="${source}" data-licence-class="derived-only"`);
      }
      expect(rows[0][2]).toContain(lang === 'en' ? 'never written to an artifact' : 'nunca se escriben en un artefacto');
      expect(rows[2][2]).toContain(lang === 'en' ? 'Trueck and Rachev (2009)' : 'Trueck y Rachev (2009)');
      expect(rows[1][1]).toContain(`${formatNumber(0.01, lang, { percent: true, decimals: 0 })} ${lang === 'en' ? 'and' : 'y'} ${formatNumber(0.02, lang, { percent: true, decimals: 0 })}`);
      expect(rows[0][0]).toContain(lang === 'en' ? 'Licence class: derived-only' : 'Clase de licencia: solo derivados');
      // each paper's citation from the source registry under its title, its address a short link to its landing page
      ['israel-rosenthal-wei-2001', 'schuermann-hanson-2004', 'engelmann-2024'].forEach((source, k) => {
        const d = manifest.source_details[source];
        expect(rows[k][0]).toContain(d.attribution.replace(/\s*https?:\/\/\S+$/, '').replace(/\.\s*$/, ''));
        expect(rows[k][0]).not.toContain('https://');
        expect(markup).toContain(`href="${d.landing}"`);
      });
    }
  });

  it("Impact: Table 5 recomputed in the browser agrees with the print and with riskvalidation's recomputation", () => {
    const live = table5Live(o);
    expect(live).toHaveLength(6);
    for (const r of live) {
      expect(r.agrees, `${r.row.interval} ${r.row.rho}`).toBe(true);
      // the port against the pipeline's numbers (stored to about nine significant digits)
      r.live.forEach((x, k) => expect(Math.abs(x - r.row.recomputed[k]), `${r.row.interval} ${r.row.rho} ${k}`).toBeLessThan(1e-9));
    }
    o.sr190.n_dagger.recomputed.forEach((x, k) => expect(Math.abs(effectiveN(o.sr190.n, [0, 0.01, 0.02][k]) - x)).toBeLessThan(1e-6));
    for (const lang of LANGS) {
      const rows = table(html(<PublishedImpactView sel={sel()} />, lang), 'table5-live');
      expect(rows).toHaveLength(6 + 3 + 3);
      live.forEach((r, k) => {
        expect(rows[k].slice(1)).toEqual([formatBpRange(lang, r.row.printed[0], r.row.printed[1], 2), formatBpRange(lang, r.live[0], r.live[1], 3), lang === 'en' ? 'agrees' : 'concuerda']);
      });
      for (const row of rows.slice(6, 9)) expect(row[3]).toBe(lang === 'en' ? 'agrees' : 'concuerda');
    }
  });

  it("Impact: the chart passes through the printed bounds at Table 5's level and follows the rail", () => {
    const series = table5Chart(o, TABLE5_LEVEL);
    expect(series).toHaveLength(8);
    const at = (rho: number) => RHO_GRID.findIndex((x) => Math.abs(x - rho) < 1e-12);
    for (const r of o.sr190.rows) {
      const i = at(r.rho);
      expect(i).toBeGreaterThanOrEqual(0);
      const line = series.find((s) => typeof s.label !== 'string' && s.label.en === `${r.interval === 'wald' ? 'Wald' : 'Agresti-Coull'}, upper`);
      expect(printsAs((line?.values[i] ?? NaN) * 1e4, r.printed[1] * 1e4, 2)).toBe(true);
    }
    // the rail's rows are the three intervals at the rail's correlation and level
    const rails = (over: Partial<C04Sel>) => table(html(<PublishedImpactView sel={sel(over)} />), 'table5-live').slice(9);
    const s = { rho: 0.012, level: 0.99 };
    const { defaults, n } = o.sr190;
    expect(rails(s).map((r) => r[2])).toEqual([
      formatBpRange('en', pdWald(defaults, n, s).lower, pdWald(defaults, n, s).upper, 3),
      formatBpRange('en', pdAgrestiCoull(defaults, n, s).lower, pdAgrestiCoull(defaults, n, s).upper, 3),
      formatBpRange('en', pdJeffreys(defaults, n, { level: s.level }).lower, pdJeffreys(defaults, n, { level: s.level }).upper, 3),
    ]);
    const base = html(<PublishedImpactView sel={sel()} />);
    expect(base).not.toBe(html(<PublishedImpactView sel={sel({ rho: 0.02 })} />));
    const off = html(<PublishedImpactView sel={sel({ level: 0.9 })} />);
    expect(off).not.toBe(base);
    expect(cards(off)[0].note).toContain('so at 90\u00a0% the lines leave them by design');
    expect(cards(base)[0].note).not.toContain('by design');
  });

  it('on another variant the views say whose they are, and a missing selection is loading', () => {
    for (const [, View] of VIEWS) {
      const other = html(<View sel={makeSel(dataOf('sp'))} />);
      expect(other).toContain("This view reads the published variant&#x27;s papers.");
      expect(other).not.toContain('data-state="loading"');
      expect(html(<View sel={null} />)).toContain('data-state="loading"');
    }
  });
});
