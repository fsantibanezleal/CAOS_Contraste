// U16-F5: the shared views and the pages, fix round 2. One describe per row or minor of the U16-R2 triage that this unit
// owns; each fails on the defect the second capture review found, in both languages where the defect is a language one.
import { CitationsProvider, useLangStore } from '@fasl-work/caos-app-shell';
import { readFileSync, readdirSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router';
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { C04VariantsProvider } from '../content/cases/C04Results';
import { CITATIONS } from '../content/citations';
import type { CaseManifest, VariantArtifact } from '../lib/contract.types';
import { C04Benchmark, C04Experiments } from '../pages/C04Sections';
import * as BenchmarkPage from '../pages/Benchmark';
import * as U6 from '../pages/U6Sections';

const here = (rel: string) => new URL(rel, import.meta.url);
const text = (rel: string) => readFileSync(here(rel), 'utf8');
const css = text('../styles/contraste.css');
const derived = new URL('../../../data/derived/', import.meta.url);
const read = <T,>(rel: string): T => JSON.parse(readFileSync(new URL(rel, derived), 'utf8')) as T;

type Lang = 'en' | 'es';
function setLang(lang: Lang) {
  (useLangStore.getInitialState() as { lang: Lang }).lang = lang;
  useLangStore.setState({ lang });
}
afterEach(() => setLang('en'));
/** A server render as the app mounts it, in one language. */
const html = (el: ReactElement, lang: Lang = 'en', extra: ReactElement | null = null): string => {
  setLang(lang);
  return renderToStaticMarkup(
    <MemoryRouter>
      <CitationsProvider items={CITATIONS}>{extra ?? el}</CitationsProvider>
    </MemoryRouter>,
  );
};
const plain = (markup: string) => markup.replace(/<[^>]*>/g, ' ').replace(/&#x27;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/\s+/g, ' ');

/** The rules inside every `@media (<feature>: <px>px)` block of the product stylesheet, braces balanced. */
function media(feature: 'max-width' | 'min-width', px: number): string {
  const out: string[] = [];
  const re = new RegExp(`@media \\(${feature}: ${px}px\\)\\s*\\{`, 'g');
  for (let m = re.exec(css); m; m = re.exec(css)) {
    let depth = 1;
    let i = m.index + m[0].length;
    const start = i;
    while (i < css.length && depth) depth += css[i] === '{' ? 1 : css[i] === '}' ? -1 : 0, i++;
    out.push(css.slice(start, i - 1));
  }
  return out.join('\n');
}

describe('VS-1, V02-4, V06-5, V21-1: a table of a filling card keeps its rows at 390', () => {
  const narrow = media('max-width', 900);
  it('a scroll box (.ct-scroll, also inside a stack) flows below 900 px instead of keeping the clamp of the card', () => {
    expect(narrow).toMatch(/\.ct-scroll[^{]*\{[^}]*height:\s*auto/);
    expect(narrow).toMatch(/\.ct-stack\s*>\s*\.ct-scroll[^{]*\{[^}]*flex:\s*none/);
  });
  it('the card body that holds a scroll box grows with it', () => {
    expect(narrow).toMatch(/:has\(\.ct-scroll\)[^{]*\{[^}]*height:\s*auto/);
  });
});

describe('V21-4: each evidence chart keeps room for at least three y ticks, its title, legend and readout', () => {
  const src = text('./c21/FindingsEvidence.tsx');
  it('asks for at least 21 rem a chart (the plot kept 76 px of 15 rem at 1280 x 800)', () => {
    const m = /'--ct-chart-min': '(\d+(?:\.\d+)?)rem'/.exec(src);
    expect(m).not.toBeNull();
    expect(Number(m![1])).toBeGreaterThanOrEqual(21);
  });
  it('the card of the evidence is not shorter than its drawings below 900 px either', () => {
    expect(media('max-width', 900)).toMatch(/finding-evidence[^{]*\.ct-stack-chart[^{]*\{[^}]*height:/);
  });
});

describe('V21-5: a scroll box never ends in a line cut through its middle', () => {
  const wide = media('min-width', 901);
  for (const cls of ['.ct-stack-table', '.ct-stack-rest', '.ct-stack-fill', '.ct-scroll']) {
    it(`${cls} fades its bottom edge and keeps a gap under its last row`, () => {
      const rule = new RegExp(`${cls.replace('.', '\\.')}[^{}]*\\{[^}]*\\}`, 'g');
      const rules = (wide.match(rule) ?? []).join('\n');
      expect(rules).toMatch(/mask-image:\s*linear-gradient/);
      expect(rules).toMatch(/padding-bottom:/);
    });
  }
});

describe('PR-C04: the Experiments and Benchmark copy of C04 in Spanish carries the Spanish attribution', () => {
  const manifest = read<CaseManifest>('manifests/C04.json');
  const variants = manifest.artifacts.filter((a) => a.role === 'variant').map((a) => read<VariantArtifact>(a.path));
  const page = (el: ReactElement, lang: Lang) => html(el, lang, <C04VariantsProvider variants={variants}>{el}</C04VariantsProvider>);
  for (const [name, el] of [['Experiments', <C04Experiments manifest={manifest} />], ['Benchmark', <C04Benchmark manifest={manifest} />]] as const) {
    it(`${name}: no English attribution sentence in the Spanish view, the Spanish one in its place`, () => {
      const es = plain(page(el, 'es'));
      expect(es).not.toContain('Source: ESMA CEREP');
      expect(es).toContain('Fuente: ESMA CEREP; tablas transformadas por Contraste');
    });
    it(`${name}: the English view keeps the source registry's wording`, () => {
      expect(plain(page(el, 'en'))).toContain('Source: ESMA CEREP; tables transformed by Contraste');
    });
  }
});

describe('b11 m1: Spanish never renders git "commit" as "comprometer"', () => {
  const dirs = ['../pages/', '../pages/methodology/', '../architecture/'];
  const files = dirs.flatMap((d) => readdirSync(here(d)).filter((f) => /\.(tsx|ts|svg)$/.test(f) && !/\.test\./.test(f)).map((f) => `${d}${f}`));
  const COMMIT_SENSE = /artefactos? comprometid|muestras? comprometid|umbrales comprometid|documentos? comprometid|política comprometida|compromete el pipeline|pipeline compromete|pipeline comprometió|puede(?:n)? comprometerse|se compromete|Compromiso:|manifiesto de licencias comprometido|\(comprometido\)/;
  it('reads the files of the pages and the figures', () => expect(files.length).toBeGreaterThan(20));
  for (const f of files) {
    it(`${f.replace('../', '')} uses versionar for what the pipeline commits`, () => {
      expect(COMMIT_SENSE.exec(text(f))?.[0] ?? null).toBeNull();
    });
  }
});

describe('b11 m2 and m3, b12 m3, b13 m3: a box that scrolls sideways at a phone shows a cue', () => {
  const narrow = media('max-width', 900);
  for (const sel of ['.prose table', '.equation', '.ct-fig-scroll']) {
    it(`${sel} fades its right edge and keeps a gap after its last column`, () => {
      const rules = (narrow.match(new RegExp(`${sel.replace('.', '\.').replace('.', '\.')}[^{}]*\{[^}]*\}`, 'g')) ?? []).join('\n');
      expect(rules).toMatch(/mask-image:\s*linear-gradient\(to right/);
      expect(rules).toMatch(/padding-right:/);
    });
  }
});

describe('b11 m4 and m5: no negative zero, one p-value format on the pages', () => {
  it('num rounds a tiny negative to an unsigned zero, in both languages', async () => {
    const { num, pct } = await import('../pages/U6Sections');
    for (const lang of ['en', 'es'] as const) {
      expect(num(-2.95e-5, lang, 4)).toBe(lang === 'en' ? '0.0000' : '0,0000');
      expect(num(-0.0004, lang, 3)).toBe(lang === 'en' ? '0.000' : '0,000');
      expect(num(-0.0016, lang, 3)).toMatch(/^-0[.,]002$/);
      expect(pct(-0.000245, lang, 1)).not.toContain('-');
      expect(pct(-0.0261, lang, 1)).toContain('-');
    }
  });
  it('pval keeps three significant digits where num with three decimals printed 0.000', async () => {
    const { pval, num } = await import('../pages/U6Sections');
    expect(num(1.0e-91, 'en', 3)).toBe('0.000');
    expect(pval(1.0e-91, 'en')).not.toBe('0.000');
    expect(pval(0.314, 'en')).toBe('0.314');
    expect(pval(0.314, 'es')).toBe('0,314');
  });
  it('the C02 and C11 page rows read their p-values through pval', () => {
    expect(text('../pages/Batch3Sections.tsx')).toMatch(/pval\(r\.calibration\.hosmer_lemeshow\.p_value/);
    expect(text('../pages/Batch3Sections.tsx')).toMatch(/pval\(pair\.delong_p_value/);
    expect(text('../pages/Wave2Sections.tsx')).toMatch(/pval\(dm\.p_value/);
  });
  it('the Benchmark difference to P1 goes through num', () => {
    expect(text('../pages/Benchmark.tsx')).toMatch(/num\(r\.auc !== null && champ\?\.auc != null \? r\.auc - champ\.auc : null, lang, 4\)/);
  });
});

describe('b11 m6 and m10: one label per rung, the best rung named', () => {
  const c01 = read<CaseManifest>('manifests/C01.json');
  const holdout = read<VariantArtifact>(c01.artifacts.find((a) => a.role === 'variant' && a.variant_id === 'holdout')!.path);
  const c08 = read<CaseManifest>('manifests/C08.json');
  const c08v = read<VariantArtifact>(c08.artifacts.find((a) => a.role === 'variant')!.path);
  const Comparison = BenchmarkPage.Comparison;
  for (const lang of ['en', 'es'] as const) {
    it(`the Benchmark verdict names the rungs the way its table does, never by id (${lang})`, () => {
      const text = plain(html(<Comparison v={holdout} title="C01" />, lang));
      for (const m of holdout.model) expect(text, m.id).not.toContain(m.id);
      const labels = holdout.model.filter((m) => m.id !== 'P0-constant').map((m) => m.short_title[lang]);
      expect(new Set(labels).size).toBe(labels.length);
      for (const l of labels) expect(text).toContain(l);
    });
  }
  it('a rung reads its short title, not "beta Beta regression"', () => {
    const rungName = U6.rungName;
    expect(rungName(c08v as VariantArtifact<unknown>, 'L3-beta', 'en')).toBe('L3 Beta');
    expect(rungName(c08v as VariantArtifact<unknown>, 'L3-beta', 'es')).toBe(c08v.model.find((m) => m.id === 'L3-beta')!.short_title.es);
  });
  it('a rung the document declares absent is named, not shown by its id', () => {
    expect(U6.rungName(c08v as VariantArtifact<unknown>, 'P5-tabpfn', 'es')).toBe('P5 TabPFN');
  });
  it('the robustness table names the best rung of each variant', () => {
    const T = (BenchmarkPage as unknown as { RobustnessTable: (p: { rows: Array<{ n: number; title: string; scorecard: number | null; best: number; bestRung: string }> }) => ReactElement }).RobustnessTable;
    const markup = html(<T rows={[{ n: 1, title: 'Drift', scorecard: 0.7123, best: 0.7456, bestRung: 'P4 LightGBM' }]} />);
    expect(plain(markup)).toContain('P4 LightGBM');
  });
});
