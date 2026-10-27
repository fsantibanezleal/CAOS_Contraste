// U16-F10p (the third capture review, R3 c24, c25 and c26): the documentation pages (Introduction, Implementation and
// Methodology) read whole, every tab and sub-tab at once, in both languages. The Spanish page carries no English technical
// word (the ruling of 2026-10-27: translated, except the acronyms the Spanish literature uses, the program and package
// names and the route name Benchmark), no plan-unit code or internal decision id in reader text in either language, no code
// identifier where the product has a name, and the sentences follow the committed numbers they describe. A quotation kept in
// the source's English (translate="no") and the bibliographic entries of the reference lists are the sources' own words and
// are not read here.
import { appendFileSync, readFileSync } from 'node:fs';
import type { ReactNode } from 'react';
import { CitationsProvider } from '@fasl-work/caos-app-shell';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CITATIONS } from '../content/citations';
import { html, setLang } from '../workbench/c03/u6-testkit';

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

const { Introduction } = await import('./Introduction');
const { Implementation } = await import('./Implementation');
const { Methodology } = await import('./Methodology');
const { architecture } = await import('../architecture');

const PAGES = { Introduction, Implementation, Methodology } as const;
const markup = (page: keyof typeof PAGES, lang: 'en' | 'es') => {
  setLang(lang);
  const Page = PAGES[page];
  return html(
    <CitationsProvider items={CITATIONS}>
      <Page />
    </CitationsProvider>,
  );
};

const decode = (s: string) => s.replace(/&#x27;|&#39;/g, "'").replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;|&#160;|&#xa0;/g, ' ').replace(/&amp;/g, '&');

/** The reader text of a page in one language: tags out, the reference lists, the source quotations (translate="no"), the
 * other language's diagram labels and KaTeX's copy of the TeX source left out. */
export function readerText(m: string, lang: 'en' | 'es'): string {
  const other = lang === 'es' ? 'l-en' : 'l-es';
  let s = m
    .replace(/<section class="caos-doc-references"[\s\S]*?<\/section>/g, ' ')
    .replace(/<annotation[\s\S]*?<\/annotation>/g, ' ')
    .replace(/<style[\s\S]*?<\/style>/g, ' ')
    .replace(new RegExp(`<(text|tspan)[^>]*class="[^"]*\\b${other}\\b[^"]*"[^>]*>[\\s\\S]*?</\\1>`, 'g'), ' ');
  // a quotation or a source's own locator, kept as the source writes it; innermost first so nested spans close right
  for (let i = 0; i < 4; i++) s = s.replace(/<span[^>]*translate="no"[^>]*>[^<]*<\/span>/g, ' ');
  return decode(s.replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ');
}

/** English technical words the Spanish pages translate (R3 c24 B2, c25 B2; the ruling of 2026-10-27), and English words
 * that were left inside Spanish display equations (R3 c25 B1). Case-insensitive, whole words. */
const EN_WORDS = [
  'pipeline', 'pipelines', 'scorecard', 'scorecards', 'boosting', 'boosted', 'gradient', 'kernel', 'port', 'hash', 'hashes', 'hashea',
  'shell', 'commit', 'proxy', 'proxies', 'backtest', 'backtests', 'backtesting', 'back-test', 'back-tests', 'spread', 'spreads',
  'bucket', 'buckets', 'bootstrap', 'odds', 'log-odds', 'prior', 'stock', 'stocks', 'swap', 'swaps', 'swaption', 'swaptions',
  'forward', 'forwards', 'commodities', 'momentum', 'solver', 'offset', 'scorer', 'suite', 'bake', 'backlog', 'aliasing', 'tick',
  'hedged', 'spot', 'shock', 'shocks', 'add-on', 'back-cast', 'hazard', 'roll-off', 'offline', 'scoring', 'vine', 'logits',
  'explainable', 'machine', 'rejection', 'outflows', 'inflows', 'otherwise', 'unless', 'iff', 'cliff', 'steep', 'flat', 'none',
  'exposure', 'horizon', 'voluntary', 'usable', 'buffers', 'mitigation', 'bank', 'product', 'other', 'full', 'cap',
  'reduced', 'hedged', 'if', 'else', 'for', 'each', 'feature', 'when', 'flag', 'and', 'or', 'the', 'of', 'at', 'least', 'one',
  'risk', 'measure', 'net', 'amber', 'green', 'tier', 'points', 'score', 'short', 'long', 'default', 'loss', 'sum',
  'benchmark', 'benchmarks', 'output', 'floor', 'core', 'nominated', 'only', 'with',
];
const EN_RE = new RegExp(`(?<![\\p{L}_-])(${EN_WORDS.join('|')})(?![\\p{L}_-])`, 'giu');
/** Names that hold one of those words and stay as written: program and package names, the route name, published titles. */
const KEEP = [
  /Benchmark(?= )/g, /LightGBM|XGBoost|TabPFN|QuantLib|riskvalidation|ORE|Open Source Risk Engine/g,
  // an acronym the Spanish literature uses (the cumulative accuracy profile), a book, a journal and a bank by their names, the
  // NGFS scenarios by their names, and a symbol of an exponent (e^{-2at})
  /\bCAP\b/g, /Quantitative Risk Management/g, /\(Risk, \d{4}\)/g, /Silicon Valley Bank/g,
  /Low Demand|Net Zero 2050|Below 2\s?°?C|Delayed transition|Current Policies|Fragmented World|Nationally Determined Contributions/g,
  /-2a[tT]\b/g,
];

/** Writes the offenders of a check to the file DOCS_DUMP names (a local aid while fixing; nothing is written otherwise). */
function dump(name: string, rows: string[]) {
  const f = process.env.DOCS_DUMP;
  if (f && rows.length) appendFileSync(f, `## ${name}\n${rows.join('\n')}\n`);
  return rows;
}

function englishIn(text: string): string[] {
  let s = text;
  for (const k of KEEP) s = s.replace(k, ' ');
  const out: string[] = [];
  for (const m of s.matchAll(EN_RE)) {
    // the Spanish pages keep the route name Benchmark capitalised (the ruling); lower-case "benchmark" in prose is English
    if (m[1] === 'Benchmark') continue;
    out.push(`${m[1]} :: ${s.slice(Math.max(0, (m.index ?? 0) - 50), (m.index ?? 0) + 50)}`);
  }
  return out;
}

/** A plan-unit code, brief id or internal decision id in reader text (the ruling of 2026-10-27): "U13", "U2", "W15-13", "(Q13)". */
const PLAN_CODE = /(?<![\p{L}\d.-])(U\d{1,2}(?:-[A-Z]\d?)?|W\d{2}-\d+|BL-\d+)(?![\p{L}\d])/gu;
/** Code identifiers where the product has a name (R3 c24 B4): engine and component type names and the contract-1 family codes. */
const CODE_IDS = /\b(TestResult|PlotCard|Readout|scored_sample|loan_panel|rating_history|market_series|balance_sheet|loss_events|macro_path)\b/g;

describe('the documentation pages in Spanish (R3 c24 B2, c25 B1 and B2)', () => {
  afterEach(() => setLang('en'));

  for (const page of Object.keys(PAGES) as Array<keyof typeof PAGES>) {
    it(`${page}: no English technical word, and no English word inside an equation, in the Spanish reader text`, () => {
      expect(dump(page, englishIn(readerText(markup(page, 'es'), 'es')))).toEqual([]);
    });
  }

  it('the architecture modal: no English technical word in the Spanish bodies and tab names', () => {
    const es = architecture.tabs.map((t) => `${t.es} ${t.body_es}`).join(' ');
    expect(dump('architecture', englishIn(es))).toEqual([]);
  });
});

describe('no plan code and no code identifier in reader text, in either language (R3 c24 B4, c25 B4, c26 B1)', () => {
  afterEach(() => setLang('en'));

  for (const page of Object.keys(PAGES) as Array<keyof typeof PAGES>) {
    for (const lang of ['en', 'es'] as const) {
      it(`${page} ${lang}: no plan-unit code`, () => {
        const text = readerText(markup(page, lang), lang);
        expect([...text.matchAll(PLAN_CODE)].map((m) => `${m[1]} :: ${text.slice(Math.max(0, (m.index ?? 0) - 40), (m.index ?? 0) + 40)}`)).toEqual([]);
      });
      it(`${page} ${lang}: no engine or component type name, no contract family code`, () => {
        const text = readerText(markup(page, lang), lang);
        expect([...text.matchAll(CODE_IDS)].map((m) => m[1])).toEqual([]);
      });
    }
  }
});

describe('an English quotation in a Spanish view has its Spanish rendering (R3 c25 B3, the ruling of 2026-10-27)', () => {
  afterEach(() => setLang('en'));

  it('every quotation kept in English (translate="no", six words or more) is followed by its rendering in brackets', () => {
    const m = markup('Methodology', 'es');
    const bare: string[] = [];
    for (const q of m.matchAll(/<span[^>]*translate="no"[^>]*>(&quot;|")([^<]*)<\/span>([\s\S]{0,40})/g)) {
      if (q[2].split(/\s+/).length >= 6 && !/^\s*\(/.test(decode(q[3]))) bare.push(decode(q[2]).slice(0, 60));
    }
    expect(bare.join(' | ')).toBe('');
  });
});

describe('the references in Spanish (R3 c24 B3, c25 m4)', () => {
  it('no English annotation inside a bibliographic entry, and the cite labels in Spanish', () => {
    expect(CITATIONS.filter((c) => /Superseded|superseded/.test(c.citation)).map((c) => c.id)).toEqual([]);
    const label = (id: string) => {
      const l = CITATIONS.find((c) => c.id === id)?.label;
      return typeof l === 'string' ? l : l?.es;
    };
    for (const id of ['osfie23letter', 'osfibackgrounder', 'ecblist']) {
      expect(label(id), id).toBeDefined();
      expect(label(id), id).not.toMatch(/\b(letter|backgrounder)\b|^ECB LiST 2019$/);
    }
  });
});

describe('a sentence follows the committed number it describes (R3 c26 B2)', () => {
  afterEach(() => setLang('en'));

  it('the caution on the ECB test: one in six at C01 slice sizes, about one in nine at equal sizes (C22 discrimination-decay @m1 0.112, @m0.467 0.170)', () => {
    const doc = JSON.parse(readFileSync(new URL('../../../data/derived/C22/discrimination-decay.json', import.meta.url), 'utf8')) as { outputs: { simulations: Array<{ key: string; rates: Record<string, { rate: number }> }> } };
    const rate = (k: string) => doc.outputs.simulations.find((s) => s.key === `disc.auc_vs_initial${k}`)?.rates['p<0.05'].rate ?? NaN;
    expect(rate('@m1')).toBeLessThan(1 / 8);
    expect(rate('@m0.467')).toBeGreaterThan(1 / 7);
    const en = readerText(markup('Methodology', 'en'), 'en');
    const es = readerText(markup('Methodology', 'es'), 'es');
    expect(en).not.toMatch(/similar size the test rejects about one time in six/);
    expect(es).not.toMatch(/tamaño similar[^.]*una vez de cada seis/);
    expect(en).toMatch(/about one in nine at equal sizes/);
    expect(es).toMatch(/una de cada nueve con tamaños iguales/);
  });
});

describe('the layout of the documentation pages (R3 c25 M1, c26 M1)', () => {
  afterEach(() => setLang('en'));

  it('the regulation calculators print every option name whole: their selects are not in a rail, so nothing fits them to its width', async () => {
    const src = readFileSync(new URL('./methodology/regulation.tsx', import.meta.url), 'utf8');
    expect(src).not.toMatch(/<RailSelect/);
    const { DocSelect } = await import('./methodology/regulation');
    const long = { en: 'Direct credit substitutes, such as general guarantees of indebtedness', es: 'Sustitutos directos de crédito, como las garantías generales de endeudamiento' };
    for (const lang of ['en', 'es'] as const) {
      setLang(lang);
      const m = html(<DocSelect id="x" label={{ en: 'Item', es: 'Partida' }} options={[{ id: 'a', label: long }]} value="a" onChange={() => undefined} />);
      const options = [...m.matchAll(/<option[^>]*>([^<]*)<\/option>/g)].map((x) => decode(x[1]));
      expect(options, lang).toEqual([long[lang]]);
      expect(m, lang).toContain('data-control="x"');
    }
  });

  it('the SA-CCR and HQLA equations break onto two lines, so neither is wider than its box at 1280', () => {
    const ccr = readFileSync(new URL('./methodology/ccr.tsx', import.meta.url), 'utf8');
    const lcr = readFileSync(new URL('./methodology/liquidity.tsx', import.meta.url), 'utf8');
    const line = (src: string, marker: RegExp) => src.split('\n').find((l) => marker.test(l)) ?? '';
    // a TeX line break, written `\\` in the String.raw source
    expect(line(ccr, /EN\}_\{HS\}/)).toMatch(/\\\\/);
    expect(line(lcr, /Adj\}_\{15/)).toMatch(/\\\\/);
  });
});
