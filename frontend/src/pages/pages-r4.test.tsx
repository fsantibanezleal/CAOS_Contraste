// U16-F12p (the fourth capture review, R4 c28 to c31): the documentation routes on the committed documents, in both languages.
// Benchmark and Experiments (c28): a reason the engine writes in English reads in Spanish (C11); the case facts name the
// pipeline, never print the manifest's engine key; the C21 groups read in Spanish and each group is a row of its own, so no row
// holds eighteen groups at 390; the C02 single-variable rung names its codebook field; the C04 findings print their titles; an
// English quotation carries its Spanish rendering and the paper's cell labels read in Spanish (C22); the dependency map's
// read-out wraps. Introduction and Methodology (c30): the capital gaps of the boosting text follow the committed C01 documents;
// no symbol carries an English subscript and no calculator label or document string is an English word in Spanish.
import { appendFileSync, readFileSync, readdirSync } from 'node:fs';
import type { ReactNode } from 'react';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { CITATIONS } from '../content/citations';
import { WithQuotes } from '../content/bi';
import { html, setLang } from '../workbench/c03/u6-testkit';
import type { GovInventory } from '../workbench/governance/model';

type TabDef = { id: string; label: ReactNode; content: ReactNode };

// every tab of every tab row is rendered, so one render reads the whole page (the shell draws only the active one)
vi.mock('@fasl-work/caos-app-shell', async (importOriginal) => {
  const shell = await importOriginal<Record<string, unknown>>();
  const all = ({ tabs }: { tabs: TabDef[] }) => (
    <>
      {tabs.map((t) => (
        <section key={t.id} data-test-tab={t.id}>
          <h2>{t.label}</h2>
          {t.content}
        </section>
      ))}
    </>
  );
  const groups = ({ groups: gs }: { groups: Array<{ id: string; label: ReactNode; tabs: TabDef[] }> }) => (
    <>
      {gs.map((g) => (
        <section key={g.id} data-test-group={g.id}>
          <h2>{g.label}</h2>
          {all({ tabs: g.tabs })}
        </section>
      ))}
    </>
  );
  return { ...shell, Tabs: all, SubTabs: all, TabGroups: groups };
});

const { Methodology } = await import('./Methodology');
const { BoostingExtra } = await import('./MethodologyExtras');
const { RegulationBody } = await import('./methodology/regulation');
const { CaseFacts } = await import('./Experiments');
const { familyShows } = await import('./C04Sections');
const { goldenCellLabel } = await import('./C22Sections');
const { batch3BenchmarkTables, batch3ExperimentTables } = await import('./Batch3Sections');
const { wave2ExperimentTables } = await import('./Wave2Sections');
const { DependencyMap, MapReadout } = await import('../workbench/governance/DependencyMap');

const root = new URL('../../../data/derived/', import.meta.url);
const json = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, root), 'utf8')) as T;
const manifest = (id: string) => json<CaseManifest>(`manifests/${id}.json`);
const variants = (m: CaseManifest) => m.artifacts.filter((a) => a.role === 'variant').map((a) => json<VariantArtifact<unknown>>(a.path));
const cellText = (c: unknown): string => (typeof c === 'string' ? c : renderToStaticMarkup(c as never).replace(/<[^>]+>/g, ''));
const cells = (tables: Array<{ head: string[]; rows: unknown[][]; note?: string; title?: string }>) =>
  tables.flatMap((t) => [t.title ?? '', ...t.head, t.note ?? '', ...t.rows.flat().map(cellText)]).join(' | ');
const decode = (s: string) => s.replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;|&#160;|&#xa0;/g, ' ').replace(/&amp;/g, '&');
const LANGS = ['en', 'es'] as const;
const CASES = readdirSync(new URL('manifests/', root)).filter((f) => /^C\d\d\.json$/.test(f)).map((f) => f.slice(0, 3));

/** The reader text of a markup: tags out, the reference lists, the marked quotations and KaTeX's copy of the TeX left out. */
function readerText(m: string, lang: 'en' | 'es'): string {
  const other = lang === 'es' ? 'l-en' : 'l-es';
  let s = m
    .replace(/<section class="caos-doc-references"[\s\S]*?<\/section>/g, ' ')
    .replace(/<annotation[\s\S]*?<\/annotation>/g, ' ')
    .replace(/<style[\s\S]*?<\/style>/g, ' ')
    .replace(new RegExp(`<(text|tspan)[^>]*class="[^"]*\\b${other}\\b[^"]*"[^>]*>[\\s\\S]*?</\\1>`, 'g'), ' ');
  for (let i = 0; i < 4; i++) s = s.replace(/<span[^>]*translate="no"[^>]*>[^<]*<\/span>/g, ' ');
  return decode(s.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ');
}

/** The words of ruling 6 of 2026-10-27 (examples, not a closed set) and the other English words the R4 Spanish captures showed. */
const RULED = ['swap', 'swaps', 'swaption', 'swaptions', 'spread', 'spreads', 'spot', 'forward', 'forwards', 'commodities', 'commodity', 'bucket', 'buckets', 'prior', 'test', 'tests', 'tick', 'hash', 'port', 'ports', 'shell', 'benchmark', 'pipeline', 'puertos'];
/** A ruled word, standing alone or joined to a symbol by "_" (the Spanish guard skipped "α_amber", c30 B2). */
const ruledIn = (text: string): string[] =>
  [...text.matchAll(new RegExp(`(?<![\\p{L}-])(${RULED.join('|')})(?![\\p{L}-])`, 'giu'))].map((m) => `${m[1]} :: ${text.slice(Math.max(0, (m.index ?? 0) - 40), (m.index ?? 0) + 40)}`);
/** English words written as a subscript of a symbol: in a caption ("α_amber", "<sub>red</sub>") or in plain text ("K_reduced"). */
const EN_SUBSCRIPTS = ['red', 'amber', 'green', 'upper', 'lower', 'full', 'nominated', 'reduced', 'hedged', 'only', 'init', 'curr', 'rec', 'pay'];
function englishSubscripts(markup: string, text: string): string[] {
  const words = EN_SUBSCRIPTS.join('|');
  const sub = [...markup.matchAll(new RegExp(`<sub>(${words})</sub>`, 'g'))].map((m) => `<sub>${m[1]}</sub>`);
  const joined = [...text.matchAll(new RegExp(`[\\p{L}\\p{N})]_(${words}|SA-only)(?![\\p{L}])`, 'gu'))].map((m) => `${m[0]} :: ${text.slice(Math.max(0, (m.index ?? 0) - 30), (m.index ?? 0) + 30)}`);
  // an English symbol name with a subscript ("Score_ref", "odds_ref", c30 B2): the equation it names reads Puntaje_ref, razón_ref
  const named = [...text.matchAll(/(?<!\p{L})(Score|odds)_\p{L}+/gu)].map((m) => m[0]);
  return [...sub, ...joined, ...named];
}

/** Writes the offenders of a check to the file R4_DUMP names (a local aid while fixing; nothing is written otherwise). */
function dump(name: string, rows: string[]) {
  const f = process.env.R4_DUMP;
  if (f && rows.length) appendFileSync(f, `## ${name}\n${rows.join('\n')}\n`);
  return rows;
}

/** The whole Methodology page in one language. */
const methodology = (lang: 'en' | 'es') => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <Methodology />
    </CitationsProvider>,
  );
};

/** The regulatory calculators on the committed document, with the titles and statements the producer copies from its inputs. */
function regulatoryDoc() {
  const doc = json<{ official_examples: Array<{ id: string; title: unknown; statement: unknown }>; invariant_cases: Array<{ id: string; title: unknown; statement: unknown }>; parameter_tables: Array<{ id: string; title: unknown }> }>('regulatory/calculators.json');
  const inputs = JSON.parse(readFileSync(new URL('../../../data-pipeline/pipeline/regulatory/inputs.json', import.meta.url), 'utf8')) as typeof doc;
  for (const k of ['official_examples', 'invariant_cases'] as const) {
    for (const e of doc[k]) {
      const src = inputs[k].find((x) => x.id === e.id);
      if (src) Object.assign(e, { title: src.title, statement: (src as { statement?: unknown }).statement ?? e.statement });
    }
  }
  for (const t of doc.parameter_tables) {
    const src = inputs.parameter_tables.find((x) => x.id === t.id);
    if (src) t.title = src.title;
  }
  return doc;
}
const regulation = (lang: 'en' | 'es') => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <RegulationBody doc={regulatoryDoc() as never} />
    </CitationsProvider>,
  );
};

// ------------------------------------------------------------------------------------------------------------- c28

describe('Benchmark and Experiments (R4 c28)', () => {
  afterEach(() => setLang('en'));

  it('B1: the Spanish C11 champion reason reads in Spanish ("no model is eligible" was back in English)', () => {
    const m = manifest('C11');
    const es = cells(wave2ExperimentTables(m, variants(m), 'es'));
    expect(es).not.toMatch(/no model is eligible|every model fails/);
    expect(es).toContain('ningún modelo es elegible: cada modelo falla al menos una compuerta');
  });

  it('B2: the case facts name the pipeline in words, never the manifest key "pipeline", in both languages', () => {
    for (const id of CASES) {
      for (const lang of LANGS) {
        setLang(lang);
        const text = decode(html(<CaseFacts m={manifest(id)} />).replace(/<[^>]+>/g, ' '));
        expect(text, `${id} ${lang}`).not.toMatch(/\bby pipeline\b|\bpor pipeline\b/);
        expect(text, `${id} ${lang}`).toMatch(lang === 'es' ? /la cadena de cálculo de Contraste \d/ : /the Contraste pipeline \d/);
        // the variant titles come from the case producers (C01's "Prior x1,5" is theirs, R4 c28 B8): this row is the engine key
        if (lang === 'es') expect(ruledIn(text).filter((w) => /^pipeline/i.test(w)), id).toEqual([]);
      }
    }
  });

  it('B3: the Spanish C21 table names every HMDA group in Spanish', () => {
    const m = manifest('C21');
    const es = cells(batch3ExperimentTables(m, variants(m), 'es'));
    expect(es).not.toMatch(/American Indian|Alaska Native|Black or African|Pacific Islander|\bAsian\b|\bFemale\b|Hispanic or Latino|minority races|62 or over|under 62/);
    expect(es).toContain('Mujer');
    expect(es).toContain('Indígena americano o nativo de Alaska');
  });

  it('M1 (and c29 m6, m7): each C21 group is a row of its own, so no cell lists the groups of a year pair; the attribute is printed once and the ratio with three digits', () => {
    const m = manifest('C21');
    const vs = variants(m);
    for (const lang of LANGS) {
      const tables = batch3ExperimentTables(m, vs, lang);
      // the headline table and one table of groups per year pair
      expect(tables.length, lang).toBe(vs.length + 1);
      // the longest cell left is the four-fifths flags of the five attributes, the citation once; a cell of eighteen groups ran past 1,500 characters
      for (const t of tables) for (const r of t.rows) for (const c of r) expect(cellText(c).length, `${lang} ${cellText(c).slice(0, 60)}`).toBeLessThan(360);
      const groups = tables.slice(1);
      expect(groups.every((t) => t.head.length === 5 && t.rows.length >= 10), lang).toBe(true);
      const text = cells(tables);
      expect(text).not.toMatch(/Age, 62 or over, 62 or over|Edad, 62 o más, 62 o más/);
      // the 2018-19 Black or African American ratio is 0.79604: below the four-fifths threshold, and printed so
      expect(text).toContain(lang === 'es' ? '0,796' : '0.796');
    }
  });

  it('B4: the C02 single-variable rung names its codebook field, never the column code "Attr39"', () => {
    const m = manifest('C02');
    const vs = variants(m);
    for (const lang of LANGS) {
      const all = `${cells(batch3BenchmarkTables(m, vs, lang))} ${cells(batch3ExperimentTables(m, vs, lang))}`;
      expect(all.match(/Attr\d+\w*/)?.[0] ?? null, lang).toBeNull();
      expect(all, lang).toContain(lang === 'es' ? 'variable: utilidad sobre ventas / ventas' : 'variable: profit on sales / sales');
    }
  });

  it('c28 m4: the best C02 rung names which P4 it is', () => {
    const m = manifest('C02');
    for (const lang of LANGS) expect(cells(batch3ExperimentTables(m, variants(m), lang)), lang).toMatch(/P4 (LightGBM|XGBoost) \(0[.,]9/);
  });

  it('B5: the C04 findings are printed by their titles, never their register ids', () => {
    const m = manifest('C04');
    const families = variants(m).filter((v) => Array.isArray((v as { findings?: unknown[] }).findings) && (v.outputs as { kind?: string } | null) !== null);
    let seen = 0;
    for (const v of families) {
      if (!(v as { findings: unknown[] }).findings.length) continue;
      for (const lang of LANGS) {
        let text: string;
        try {
          text = familyShows(v as never, lang);
        } catch {
          continue;
        }
        expect(text.match(/\bF-[A-Z][A-Z-]+/)?.[0] ?? null, `${v.variant_id} ${lang}`).toBeNull();
        seen++;
      }
    }
    expect(seen).toBeGreaterThan(0);
  });

  it('B6: the English quotation of the C22 published reproduction carries its Spanish rendering on the Spanish page', () => {
    const doc = json<{ outputs: { golden: Array<{ note: { en: string; es: string } }> } }>('C22/leakage.json');
    const note = doc.outputs.golden[0].note;
    const es = decode(renderToStaticMarkup(<WithQuotes text={note.es} pageLang="es" />));
    expect(es).toMatch(/<span translate="no" lang="en">"the significance level/);
    expect(es).toContain('(en español: «el nivel de significación de la prueba F');
    // the English page is unchanged
    expect(decode(renderToStaticMarkup(<WithQuotes text={note.en} pageLang="en" />))).not.toMatch(/en español/);
  });

  it('B7: the cells of the papers read in Spanish on the Spanish page (table, scenario, column), the paper\'s scenario code kept', () => {
    const golden = ['C22/clustering.json', 'C22/drift.json', 'C22/leakage.json'].flatMap((f) => json<{ outputs: { golden: Array<{ cells: Array<{ table: string; row: string; column: string; agrees: boolean }> }> } }>(f).outputs.golden);
    const all = golden.flatMap((g) => g.cells);
    expect(all.length).toBeGreaterThan(100);
    for (const c of all) {
      const es = goldenCellLabel(c, 'es');
      // an English decimal is wrong in Spanish; a locator's section number ("sección 2.3") is no decimal
      expect(es.replace(/sección \d+\.\d+/, 'sección'), JSON.stringify(c)).not.toMatch(/\bTable\b|\btraffic\b|\bshift\b|chi-square|\bnested\b|\bsection\b|\bSD\b|\d\.\d/);
      expect(goldenCellLabel(c, 'en')).toBe(`${c.table}, ${c.row}, ${c.column}`);
    }
    expect(goldenCellLabel({ table: 'Table 8', row: 'DV_LV, traffic', column: '0.001' }, 'es')).toBe('tabla 8, DV_LV, semáforo, 0,001');
    expect(goldenCellLabel({ table: 'Table 4', row: 'm 100, n 400', column: 'shift 0.25 SD, PSI > 0.10' }, 'es')).toBe('tabla 4, m 100, n 400, desplazamiento 0,25 DE, PSI > 0,10');
    expect(goldenCellLabel({ table: 'Table 4', row: 'm 200, n 200', column: 'shift 0 SD, chi-square' }, 'es')).toBe('tabla 4, m 200, n 200, desplazamiento 0 DE, chi-cuadrado');
  });

  it('M2: the dependency map read-out wraps under the drawing: no fixed height, nothing hidden, and the whole description of a node', () => {
    const inv = json<GovInventory>('governance/inventory.json');
    for (const lang of LANGS) {
      setLang(lang);
      const host = html(<DependencyMap inv={inv} />);
      const readout = host.match(/<p[^>]*data-map-readout[^>]*>/)?.[0] ?? '';
      expect(readout, lang).toMatch(/aria-live="polite"/);
      expect(readout, lang).not.toMatch(/overflow:\s*hidden/);
      expect(readout, lang).not.toMatch(/[;"]height:/);
      // the host gives the stage the drawing's height only, and the read-out sits outside it
      expect(host, lang).toMatch(/data-map-host[^>]*>[\s\S]*<\/div><p[^>]*data-map-readout/);
      const words = decode(html(<MapReadout inv={inv} current={inv.entries[12].key} />).replace(/<[^>]+>/g, ''));
      expect(words, lang).toMatch(lang === 'es' ? /alimenta a \d+$/ : /feeds \d+$/);
      expect(words.startsWith('13. '), lang).toBe(true);
    }
  });
});

// ------------------------------------------------------------------------------------------------------------- c30

describe('Introduction and Methodology (R4 c30)', () => {
  afterEach(() => setLang('en'));

  it('B1: the capital gaps of the boosting text are the committed C01 gaps (4.2 %, 10.2 %, 13.5 %), in both languages', () => {
    const gap = (v: string) => {
      const i = json<{ impact: Record<string, { value: number }> }>(`C01/${v}.json`).impact;
      return i.capital_challenger.value / i.capital_champion.value - 1;
    };
    const want = [gap('holdout'), gap('drift-severe'), gap('small-sample')].map((g) => Math.round(Math.abs(g) * 1000) / 10);
    expect(want).toEqual([4.2, 10.2, 13.5]);
    for (const lang of LANGS) {
      setLang(lang);
      const text = decode(html(<BoostingExtra />).replace(/<[^>]+>/g, ' ')).replace(/\u00a0/g, ' ');
      for (const w of want) expect(text, `${lang} ${w}`).toContain(lang === 'es' ? `${String(w).replace('.', ',')} %` : `${w}%`);
      expect(text, lang).not.toMatch(/10[.,]3\s?%/);
    }
  });

  it('B2: no symbol of the Spanish page carries an English subscript, in a caption, in prose or in a calculator', () => {
    const m = `${methodology('es')} ${regulation('es')}`;
    expect(dump('subscripts', englishSubscripts(m, readerText(m, 'es')))).toEqual([]);
  });

  it('B2: no display equation writes a bare English word as a subscript, where the Spanish translation cannot reach it', () => {
    const dir = new URL('./methodology/', import.meta.url);
    const files = [...readdirSync(dir).map((f) => new URL(f, dir)), new URL('./Methodology.tsx', import.meta.url), new URL('./MethodologyExtras.tsx', import.meta.url), new URL('./MethodologyTransitions.tsx', import.meta.url)];
    const bare: string[] = [];
    for (const f of files) {
      const src = readFileSync(f, 'utf8');
      for (const mm of src.matchAll(/_\{([a-z]{3,})\}/g)) if (EN_SUBSCRIPTS.includes(mm[1])) bare.push(`${f.pathname.split('/').pop()}: _{${mm[1]}}`);
    }
    expect(dump('bare', bare)).toEqual([]);
  });

  it('B3: no English technical word in the Spanish calculators, their labels, their tables or the document strings they print', () => {
    const text = readerText(regulation('es'), 'es');
    expect(dump('calculators', ruledIn(text))).toEqual([]);
    expect(text).toContain('tramo');
    expect(text).toMatch(/opción sobre permuta/);
  });

  it('B3: no English technical word in the Spanish Methodology page as a whole', () => {
    expect(dump('methodology', ruledIn(readerText(methodology('es'), 'es')))).toEqual([]);
  });

  it('c30 m4: the Spanish percent carries its no-break space in the prose of the methodology page (the equations are TeX, apart)', () => {
    const dir = new URL('./methodology/', import.meta.url);
    const files = [...readdirSync(dir).map((f) => new URL(f, dir)), new URL('./Methodology.tsx', import.meta.url), new URL('./MethodologyExtras.tsx', import.meta.url), new URL('./MethodologyTransitions.tsx', import.meta.url)];
    const bare: string[] = [];
    for (const f of files) {
      readFileSync(f, 'utf8').split('\n').forEach((line, i) => {
        const s = line.trimStart();
        if (s.startsWith('tex=')) return;
        const es = s.startsWith('es=') || s.startsWith('es:') ? s : line.includes(' es={') ? line.slice(line.indexOf(' es={')) : '';
        for (const m of es.matchAll(/\d%/g)) bare.push(`${f.pathname.split('/').pop()}:${i + 1}: ${es.slice(Math.max(0, (m.index ?? 0) - 30), (m.index ?? 0) + 3)}`);
      });
    }
    expect(dump('percent', bare)).toEqual([]);
  });

  it('c30 m1: the grammar the term replacement left is fixed', () => {
    const text = `${readerText(methodology('es'), 'es')} ${readerText(regulation('es'), 'es')}`;
    const slips = /(?<!\p{L})(el|un|al) pruebas?(?!\p{L})|un solo permuta|cartera potenciados|peldaño potenciados|los hornea|puertos en vivo/giu;
    expect(dump('grammar', [...text.matchAll(slips)].map((m) => text.slice(Math.max(0, (m.index ?? 0) - 60), (m.index ?? 0) + 60)))).toEqual([]);
  });

  it('c30 m8, m9, m10 and c31 S2: CRE52.72 says "not applicable", the cascade names its first subset once, the NGFS scenario by its published name, a short bar label', () => {
    const en = readerText(regulation('en'), 'en');
    const es = readerText(regulation('es'), 'es');
    expect(en).toMatch(/not applicable/);
    expect(es).toMatch(/no aplica/);
    expect(en).not.toMatch(/\bQ1\b/);
    const page = readerText(methodology('en'), 'en');
    expect(page).not.toMatch(/Below 2C\b/);
    expect(en).not.toMatch(/Cascade ES \(square root of the sum of squares\)/);
  });

  it('c31 m8: no developer word in the English reader text (the bake, the backlog, the build history)', () => {
    const page = readerText(methodology('en'), 'en');
    expect(page).not.toMatch(/\bthe bake\b|\bbakes\b|\bbacklog\b|in this build|corrected on 2026/);
  });
});
