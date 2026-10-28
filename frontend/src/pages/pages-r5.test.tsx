// U16-F13p (the fifth capture review, R5 c30 to c33): the documentation routes on the committed documents, in both languages.
// Benchmark and Experiments (c30): the C04 papers' locators and symbols read in Spanish, the C18 reverse stress gives its own
// reason, the long text columns keep a readable width at 390, a tail probability far below 0.01 % is not printed as zero, the
// C05 estimators and tests are named; Implementation (c31): the paths and branch names are code; Methodology (c32, c33): no
// contract id, no developer word, no ASCII exponent and none of the slips the term replacement left.
import { readFileSync, readdirSync } from 'node:fs';
import type { ReactElement, ReactNode } from 'react';
import { CitationsProvider, pick } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { CITATIONS } from '../content/citations';
import { C04VariantsProvider } from '../content/cases/C04Results';
import { CASES as BASE_CASES } from '../content/coverage/base';
import { CASES as U5_CASES } from '../content/coverage/U5';
import { html, setLang } from '../workbench/c03/u6-testkit';
import type { GovInventory, GovReport } from '../workbench/governance/model';

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
const { RegulationBody } = await import('./methodology/regulation');
const { Implementation } = await import('./Implementation');
const { CaseFacts } = await import('./Experiments');
const { C04Benchmark, C04Experiments } = await import('./C04Sections');
const { C05ExperimentsSection, C05_ESTIMATOR, c05TestName } = await import('./C05Sections');
const { C22ExperimentsSection } = await import('./C22Sections');
const { RobustnessTable } = await import('./Benchmark');
const { Table } = await import('./U6Sections');
const { batch3ExperimentTables } = await import('./Batch3Sections');
const { wave2ExperimentTables } = await import('./Wave2Sections');
const { MapDrawing } = await import('../workbench/governance/DependencyMap');
const { ReportDocument } = await import('../workbench/governance/ReportView');

const root = new URL('../../../data/derived/', import.meta.url);
const json = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, root), 'utf8')) as T;
const manifest = (id: string) => json<CaseManifest>(`manifests/${id}.json`);
const variants = (m: CaseManifest) => m.artifacts.filter((a) => a.role === 'variant').map((a) => json<VariantArtifact<unknown>>(a.path));
const decode = (s: string) => s.replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;|&#160;|&#xa0;/g, ' ').replace(/&amp;/g, '&');
const plain = (m: string) => decode(m.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ');
const cellText = (c: unknown): string => (typeof c === 'string' ? c : plain(html(c as ReactElement)));
const LANGS = ['en', 'es'] as const;
type Lang = (typeof LANGS)[number];

/** The reader text of a markup: tags out, the reference lists, the marked quotations and KaTeX's copy of the TeX left out. */
function readerText(m: string, lang: Lang): string {
  const other = lang === 'es' ? 'l-en' : 'l-es';
  let s = m
    .replace(/<section class="caos-doc-references"[\s\S]*?<\/section>/g, ' ')
    .replace(/<annotation[\s\S]*?<\/annotation>/g, ' ')
    .replace(/<style[\s\S]*?<\/style>/g, ' ')
    .replace(new RegExp(`<(text|tspan)[^>]*class="[^"]*\\b${other}\\b[^"]*"[^>]*>[\\s\\S]*?</\\1>`, 'g'), ' ');
  for (let i = 0; i < 4; i++) s = s.replace(/<span[^>]*translate="no"[^>]*>[^<]*<\/span>/g, ' ');
  return decode(s.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ');
}
const around = (text: string, re: RegExp) => [...text.matchAll(re)].map((m) => text.slice(Math.max(0, (m.index ?? 0) - 50), (m.index ?? 0) + 50));

const methodology = (lang: Lang) => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <Methodology />
    </CitationsProvider>,
  );
};
type RegDoc = { provenance: { inputs: Array<{ class: string }> } };
const regulatoryDoc = () => json<RegDoc>('regulatory/calculators.json');
const regulation = (lang: Lang, doc: unknown = regulatoryDoc()) => {
  setLang(lang);
  return html(
    <CitationsProvider items={CITATIONS}>
      <RegulationBody doc={doc as never} />
    </CitationsProvider>,
  );
};
/** The C04 sections render from the variants their provider holds (the page loads them once). */
const c04 = (el: ReactElement, lang: Lang) => {
  setLang(lang);
  const m = manifest('C04');
  return html(<C04VariantsProvider variants={variants(m) as never}>{el}</C04VariantsProvider>);
};
/** The hyphenated contract ids of the lock file: an id of one word ("api", "readiness") is also a plain word. */
const CONTRACT_IDS = Object.keys(JSON.parse(readFileSync(new URL('../../../docs/contracts/versions.lock.json', import.meta.url), 'utf8')) as Record<string, unknown>).filter((k) => k.includes('-'));

// ------------------------------------------------------------------------------------------------------------- c30

describe('Benchmark and Experiments (R5 c30)', () => {
  afterEach(() => setLang('en'));

  it('B1: the Spanish C04 Experiments table writes the papers\' locators in Spanish; the English one keeps the registry\'s words', () => {
    const es = plain(c04(<C04Experiments manifest={manifest('C04')} />, 'es'));
    expect(around(es, /authors' version|, section \d|, Table \d/g)).toEqual([]);
    expect(es).toContain('(versión de los autores), sección 4');
    expect(es).toMatch(/\(FRBNY Staff Report 190\), [Tt]abla 5/);
    const en = plain(c04(<C04Experiments manifest={manifest('C04')} />, 'en'));
    expect(en).toContain("(authors' version), section 4");
  });

  it('B2: the C18 reverse stress gives its own reason for the CET1 columns, never "runs the aggregation only"; the aggregation keeps that reason', () => {
    const m = manifest('C18');
    for (const lang of LANGS) {
      const [table] = batch3ExperimentTables(m, variants(m), lang);
      const name = (id: string) => {
        const a = m.artifacts.find((x) => x.variant_id === id)!;
        return cellText(table.rows.find((r) => cellText(r[0]) === cellText((a.short_title ?? a.title)[lang]) || cellText(r[0]) === cellText(a.title[lang]))?.[0] ?? '');
      };
      const rowOf = (kind: string) => {
        const v = variants(m).find((x) => (x.outputs as { kind?: string }).kind === kind)!;
        const r = table.rows.find((row) => cellText(row[0]) === name(v.variant_id));
        expect(r, `${lang} ${kind}`).toBeTruthy();
        return r!.map(cellText);
      };
      const rev = rowOf('reverse');
      for (const c of [rev[1], rev[2]]) {
        expect(c, lang).not.toMatch(/aggregation only|solo la agregación/);
        expect(c, lang).toMatch(lang === 'es' ? /la tensión inversa resuelve un escenario/ : /the reverse stress solves for a scenario/);
      }
      const agg = rowOf('aggregation');
      expect(agg[1], lang).toMatch(lang === 'es' ? /solo la agregación/ : /aggregation only/);
    }
  });

  it('c30 m6: the reverse-stress tail probability of 2.4e-15 is written in powers of ten, not as 0.00 %', () => {
    const m = manifest('C18');
    for (const lang of LANGS) {
      const [table] = batch3ExperimentTables(m, variants(m), lang);
      const tails = table.rows.map((r) => cellText(r[6]));
      expect(tails.some((c) => /^0[.,]00\s?%$/.test(c)), `${lang} ${tails.join(' | ')}`).toBe(false);
      expect(tails.join(' | '), lang).toMatch(lang === 'es' ? /2,41 × 10⁻¹³\s%/ : /2\.41 × 10⁻¹³\s%/);
    }
  });

  it('B3: the Benchmark C04 papers table writes the symbols Ŵ, W̃ and W with a Spanish subscript, never "W hat", "W tilde" or "W_init"', () => {
    for (const lang of LANGS) {
      const m = c04(<C04Benchmark manifest={manifest('C04')} />, lang);
      const box = m.slice(m.indexOf('data-table="bench-engelmann"'));
      const table = box.slice(0, box.indexOf('</table>'));
      const text = plain(table);
      expect(around(text, /W hat|W tilde|W_init|W_ttc/g), lang).toEqual([]);
      expect(text, lang).toContain('Ŵ');
      expect(text, lang).toContain('W̃');
      expect(table, lang).toContain(lang === 'es' ? 'W<sub>inicial</sub>' : 'W<sub>init</sub>');
      expect(table, lang).toContain('W<sub>TTC</sub>');
    }
  });

  it('M1: the C04 Experiments "What the variant shows" column keeps a readable width, so its long cells do not run 1,900 px tall at 390', () => {
    const m = c04(<C04Experiments manifest={manifest('C04')} />, 'en');
    const head = m.slice(m.indexOf('data-table="c04-variants"')).match(/<thead>[\s\S]*?<\/thead>/)?.[0] ?? '';
    const ths = head.match(/<th(?:\s[^>]*)?>/g) ?? [];
    expect(ths).toHaveLength(4);
    expect(ths[3]).toMatch(/min-width:\s*2[0-9](\.\d+)?rem/);
    expect(ths[2]).toMatch(/min-width:/);
  });

  it('c30 m2: the Truth column of the C04 and C05 Experiments tables is a text column, header and cells', () => {
    const c04m = c04(<C04Experiments manifest={manifest('C04')} />, 'en');
    // the C05 section loads its variants after its first render, so its table is read from the source
    const c05 = readFileSync(new URL('./C05Sections.tsx', import.meta.url), 'utf8');
    expect(c05).toContain("<th className=\"caos-col-text\">{t('Truth', 'Verdad')}</th>");
    expect(c05).toMatch(/<td className="caos-col-text">\{pick\(TRUTH_TEXT\[v\.provenance\.truth_status\]/);
    void C05ExperimentsSection;
    for (const m of [c04m]) {
      const head = m.match(/<thead>[\s\S]*?<\/thead>/)?.[0] ?? '';
      expect((head.match(/<th(?:\s[^>]*)?>/g) ?? [])[1]).toMatch(/caos-col-text/);
      const row = m.match(/<tbody>\s*<tr[^>]*>([\s\S]*?)<\/tr>/)?.[1] ?? '';
      expect((row.match(/<td[^>]*>/g) ?? [])[1]).toMatch(/caos-col-text/);
    }
  });

  it('c30 m3: the Check column of the Engelmann table keeps a width, so the W-hat row is not 490 px tall at 390', () => {
    const m = c04(<C04Benchmark manifest={manifest('C04')} />, 'en');
    const box = m.slice(m.indexOf('data-table="bench-engelmann"'));
    const ths = box.match(/<thead>[\s\S]*?<\/thead>/)?.[0].match(/<th(?:\s[^>]*)?>/g) ?? [];
    expect(ths[3]).toMatch(/min-width:\s*1[2-9]rem/);
  });

  it('c30 m7: the Spanish C04 Benchmark verdicts join every percent to its sign with a space', () => {
    const es = plain(c04(<C04Benchmark manifest={manifest('C04')} />, 'es')).replace(/ /g, ' ');
    expect(around(es, /\d%/g)).toEqual([]);
    expect(es).toContain('80 % de potencia al 5 %');
  });

  it('c30 m7: the Spanish C11 reason joins "99 %" with its space (the five "VaR al 99%" cells)', () => {
    const m = manifest('C11');
    const es = wave2ExperimentTables(m, variants(m), 'es').flatMap((t) => t.rows.flat().map(cellText)).join(' | ').replace(/ /g, ' ');
    expect(es).toContain('el semáforo de Basilea se define solo para el VaR al 99 %');
    expect(around(es, /\d%/g)).toEqual([]);
  });

  it('c30 m8: a long text column of a comparison table keeps a readable width; the robustness headers do not wrap one word a line', () => {
    const long = 'a reason long enough to wrap one word per line in a narrow column at 390 px wide';
    const m = html(<Table head={['Variant', 'EEPE', 'Reason']} rows={[['one', '1', long]]} />);
    const ths = m.match(/<th(?:\s[^>]*)?>/g) ?? [];
    expect(ths[2]).toMatch(/min-width:/);
    expect(ths[1]).not.toMatch(/min-width:/);
    setLang('en');
    const r = html(<RobustnessTable rows={[{ n: 1, title: 'Holdout', scorecard: 0.7, best: 0.8, bestRung: 'P4' }]} />);
    const rh = r.match(/<th(?:\s[^>]*)?>/g) ?? [];
    expect(rh[2]).toMatch(/min-width:/);
    expect(rh[4]).toMatch(/min-width:/);
  });

  it('c30 m4: the Coverage row of C06 names the case the manifest builds (public small-business loans), not mortgages', () => {
    const want = manifest('C06').title;
    for (const rows of [BASE_CASES, U5_CASES]) {
      const row = rows.find((c) => c.id === 'C06')!;
      expect(row.title).toEqual(want);
    }
  });

  it('c30 m1: the C22 families table scrolls in its own box and each family\'s findings run under its row across the table, so no row is a 1,800 px band at 390', () => {
    setLang('en');
    const markup = html(<C22ExperimentsSection manifest={manifest('C22')} />);
    // the section loads its families after its first render (the server render shows its loading line), so the table is read
    // from the source
    expect(markup).toMatch(/data-state="loading"/);
    const src = readFileSync(new URL('./C22Sections.tsx', import.meta.url), 'utf8');
    const start = src.indexOf('data-table="families"');
    const block = src.slice(start - 600, src.indexOf('</table>', start));
    expect(block).toMatch(/<div className="ct-scroll" data-caos-flow="">\s*<table className="caos-table ct-wrap-head ct-top" data-table="families">/);
    // four columns; the findings are a row of their own spanning them, never a fifth column
    expect(block.match(/<th[ >]/g)).toHaveLength(4);
    expect(block).toMatch(/data-family-findings=\{v\.variant_id\}>[\s\S]*?<td className="caos-col-text" colSpan=\{4\}>/);
  });

  it('the C05 Benchmark names its estimators and tests, never the keys "independent", "scaled_correlated" or "jeffreys_A"', () => {
    const m = manifest('C05');
    const vs = variants(m);
    const src = readFileSync(new URL('./C05Sections.tsx', import.meta.url), 'utf8');
    // the section reads its variants on load; the names are a table of the section, read here
    expect(src).not.toMatch(/m\.replace\('_', ', '\)|k\.replace\('_', ', '\)/);
    for (const lang of LANGS) {
      for (const k of ['independent', 'correlated', 'scaled', 'scaled_correlated'] as const) expect(pick(C05_ESTIMATOR[k], lang), k).not.toMatch(/_/);
      const kt = (vs.map((v) => (v.outputs as { known_truth?: { tests: { true: Record<string, unknown> } } } | null)?.known_truth).find(Boolean))!;
      for (const k of Object.keys(kt.tests.true)) {
        const n = (c05TestName as (k: string, l: Lang) => string)(k, lang);
        expect(n, k).not.toMatch(/_|\bportfolio\b.*es|jeffreys/);
        if (lang === 'es') expect(n, k).not.toMatch(/portfolio|grade/);
      }
    }
    expect(c05TestName('jeffreys_A', 'es')).toBe('Jeffreys, grado A');
    expect(c05TestName('vasicek_portfolio', 'es')).toBe('Binomial con corrección de Vasicek, cartera');
    expect(pick(C05_ESTIMATOR.scaled_correlated, 'es')).toBe('Escalada y correlacionada');
  });

  it('c30 m10: the zoom buttons of the dependency map sit in a band of their own above the level labels', () => {
    const inv = json<GovInventory>('governance/inventory.json');
    setLang('en');
    const m = html(<MapDrawing inv={inv} width={360} height={400} />);
    const ys = [...m.matchAll(/<text[^>]*y="([\d.]+)"[^>]*>(Level \d+|riskvalidation)<\/text>/g)].map((x) => Number(x[1]));
    expect(ys.length).toBeGreaterThan(1);
    for (const y of ys) expect(y).toBeGreaterThanOrEqual(40);
  });

  it('the case facts say the case was computed, not baked', () => {
    setLang('en');
    const text = plain(html(<CaseFacts m={manifest('C01')} />));
    expect(text).not.toMatch(/\bbake[ds]?\b/);
    expect(text).toMatch(/expected ranges it declared before it was computed/);
  });

  it('the C15 Experiments note names its example inputs, not the fixtures', () => {
    const m = manifest('C15');
    const en = wave2ExperimentTables(m, variants(m), 'en').map((t) => t.note ?? '').join(' ');
    expect(en).not.toMatch(/fixture/);
    expect(en).toMatch(/example inputs/);
  });

  it('the report of an inline battery says why its direction is absent, with no backlog id', () => {
    const reports = readdirSync(new URL('governance/reports/', root)).filter((f) => f.endsWith('.json'));
    expect(reports.length).toBeGreaterThan(0);
    for (const lang of LANGS) {
      setLang(lang);
      for (const f of reports) {
        const text = plain(html(<ReportDocument report={json<GovReport>(`governance/reports/${f}`)} />));
        expect(around(text, /BL-\d+|backlog|\bthe bake\b/g), `${lang} ${f}`).toEqual([]);
      }
    }
  });
});

// ------------------------------------------------------------------------------------------------------------- c31

describe('Implementation (R5 c31)', () => {
  afterEach(() => setLang('en'));
  const page = (lang: Lang) => {
    setLang(lang);
    return html(
      <CitationsProvider items={CITATIONS}>
        <Implementation />
      </CitationsProvider>,
    );
  };

  it('n1: the Spanish page keeps the path data-pipeline/ verbatim, never "data-cadena"', () => {
    const es = page('es');
    expect(es).not.toMatch(/data-cadena/);
    expect(es).toMatch(/<code translate="no">data-pipeline\/<\/code>/);
  });

  it('n3: VERSION, main and build.json are code in both languages', () => {
    for (const lang of LANGS) {
      const m = page(lang);
      for (const w of ['VERSION', 'main', 'build.json', 'data-pipeline/']) expect(m, `${lang} ${w}`).toContain(`<code translate="no">${w}</code>`);
    }
  });

  it('n2: the engines equation breaks at its comma, so p(x) is on a line of its own at 390', () => {
    for (const lang of LANGS) {
      const m = page(lang);
      const ann = [...m.matchAll(/<annotation encoding="application\/x-tex">([\s\S]*?)<\/annotation>/g)].map((x) => decode(x[1]));
      const eq = ann.find((a) => a.includes('k^*'));
      expect(eq, lang).toBeTruthy();
      expect(eq!, lang).toMatch(/\\begin\{gathered\}[\s\S]*\\\\[\s\S]*p\(x\) =/);
    }
  });
});

// ------------------------------------------------------------------------------------------------------------- c32, c33

describe('Methodology (R5 c32, c33)', () => {
  afterEach(() => setLang('en'));

  it('c33 B1: no contract id in the reader text of the methodology page or of the regulatory calculators, in either language', () => {
    expect(CONTRACT_IDS).toContain('regulatory-calculators');
    for (const lang of LANGS) {
      const text = `${readerText(methodology(lang), lang)} ${readerText(regulation(lang), lang)}`;
      const hits = CONTRACT_IDS.flatMap((id) => around(text, new RegExp(`(?<![\\w-])${id}(?![\\w-])`, 'g')));
      expect(hits, lang).toEqual([]);
    }
    expect(readerText(regulation('en'), 'en')).toContain('the regulatory calculators document');
  });

  it('c33 B1: the fixture note of the calculators names the document in words', () => {
    const doc = regulatoryDoc();
    const fixture = { ...doc, provenance: { ...doc.provenance, inputs: [...doc.provenance.inputs, { ...doc.provenance.inputs[0], class: 'fixture' }] } };
    for (const lang of LANGS) {
      const m = regulation(lang, fixture);
      const note = plain(m.match(/<p class="ct-note" data-fixture="true">[\s\S]*?<\/p>/)?.[0] ?? '');
      expect(note, lang).not.toBe('');
      expect(note, lang).not.toMatch(/regulatory-calculators|\bbake\b|fixture/);
    }
  });

  it('the calculators that wait for their document say so with no file name and no "hornea"', () => {
    for (const lang of LANGS) {
      const text = plain(regulation(lang, null));
      expect(text, lang).not.toMatch(/calculators\.json|hornea|\bbake\b/);
      expect(text, lang).toMatch(lang === 'es' ? /Aún no disponible/ : /Not available yet/);
    }
  });

  it('c33 n1: no developer word in the English methodology text: the live ports, the port of a class, the fixtures', () => {
    const text = `${readerText(methodology('en'), 'en')} ${readerText(regulation('en'), 'en')}`;
    expect(around(text, /\bports?\b|\bfixtures?\b/g)).toEqual([]);
    expect(text).toMatch(/the browser implementations/);
    expect(text).toMatch(/C15 shows its example inputs/);
  });

  it('c33 n2: the operational-risk benchmark states the quantile once, without correcting a reading the page no longer gives', () => {
    for (const lang of LANGS) {
      const text = readerText(methodology(lang), lang);
      expect(text, lang).not.toMatch(/the first value belongs to|el primer valor corresponde a/);
      expect(text, lang).toMatch(lang === 'es' ? /el cuantil 99,9 por ciento es 5\.849\./ : /the 99\.9 percent quantile is 5,849\./);
    }
    expect(readerText(methodology('es'), 'es')).not.toMatch(/del referencia/);
  });

  it('c32 n1: the TabPFN weights keep their licence name, "Prior Labs License v1.1", in Spanish', () => {
    const es = methodology('es');
    expect(es).not.toMatch(/A priori Labs/);
    expect(plain(es)).toContain('Prior Labs License v1.1');
  });

  it('c32 n2, n3, n4, n6, n7: the slips of the term replacement are gone from the Spanish page', () => {
    const text = `${readerText(methodology('es'), 'es')} ${readerText(regulation('es'), 'es')}`;
    const slips = /\bdla\b|es la logaritmo|muestras remuestreo|\bpuertos?\b|según Regulation B|para a la vista|la a priori de/g;
    expect(around(text, slips)).toEqual([]);
    expect(text).toContain('según la Regulación B');
    expect(text).toContain('con la distribución a priori de Jeffreys');
  });

  it('c32 n5: no ASCII exponent ("1e-9", "1e-124") in the reader text of either language', () => {
    for (const lang of LANGS) {
      const text = `${readerText(methodology(lang), lang)} ${readerText(regulation(lang), lang)}`;
      expect(around(text, /\d[eE]-\d+/g), lang).toEqual([]);
      expect(text, lang).toContain('10⁻⁹');
    }
    expect(readerText(methodology('en'), 'en')).toContain('10⁻¹²⁴');
  });
});

