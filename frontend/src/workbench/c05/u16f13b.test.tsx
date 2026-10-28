// U16-F13b (fix round 6, the R5 capture review of C05, batch c07), on the committed documents in both languages: the Spanish Context
// names the Basel texts "Basilea" and says "preferente" (B1); the constants are symbols with their subscripts, never code tokens, and
// the Spanish subscript is RV (B2); the Default profile view shows the chi-square test over grades that F-RED-01 cites (M2); every
// tests row of C05 names its segment in words (M3, R5 ruling 2); "La prueba retrospectiva" (N-m1); Spanish prose percents keep the
// space (n3); the first equation is two displays, so a phone shows that the second one is there (S1).
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it } from 'vitest';
import { committedData, render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { CITATIONS } from '../../content/citations/base';
import { C05ContextView, C05VariantsView, CalibrationReadout } from './C05Common';
import { LdpTestsView } from './LdpViews';
import { ApproachesView, DefaultProfileView, GradeTestsView } from './SpViews';
import type { Case1 } from '../../engine/credit';
import type { C05Sel } from './selection';

const sel = (variant: string, approach: Case1 = 'A4-slr'): C05Sel =>
  ({ data: committedData('C05', variant), alphas: { amber: 0.05, red: 0.01 }, approach, p1: 0.0114, gamma: 0.75, rho: 0.12, scaled: false, regime: 'basel3', lgd: 0.45 }) as unknown as C05Sel;
const SP = ['sp-2010', 'sp-2011'];
const LDP = ['ldp-published', 'ldp-sim-0', 'ldp-sim-1', 'ldp-sim-3'];
const LANGS = ['en', 'es'] as const;
const SCOPE = { en: 'whole portfolio', es: 'toda la cartera' } as const;
const src = (rel: string) => readFileSync(new URL(rel, import.meta.url), 'utf8');
const tableOf = (markup: string, name: string) => markup.match(new RegExp(String.raw`<table[^>]*data-table="${name}"[\s\S]*?</table>`))?.[0] ?? '';
const bodyRows = (table: string) => [...(table.match(/<tbody>[\s\S]*?<\/tbody>/)?.[0] ?? '').matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map((m) => textOf(m[1]));
const heads = (table: string) => [...(table.match(/<thead>[\s\S]*?<\/thead>/)?.[0] ?? '').matchAll(/<th[^>]*>([\s\S]*?)<\/th>/g)].map((m) => textOf(m[1]).trim());

describe('U16-R5 c07 on the committed C05 documents', () => {
  afterEach(() => setLang('en'));

  it('B1: the Spanish Context says Basilea and preferente, never Basel or senior, and no "CRR3 (CRR3)"', () => {
    for (const v of [...SP, ...LDP]) {
      const es = textOf(render(<C05ContextView sel={sel(v)} />, 'es'));
      expect(es, v).not.toMatch(/\bBasel\b/);
      expect(es, v).not.toMatch(/\bsenior\b/i);
      expect(es, v).toContain('LGD F-IRB preferente no garantizada');
      const en = textOf(render(<C05ContextView sel={sel(v)} />, 'en'));
      expect(en, v).toContain('F-IRB senior unsecured LGD');
      // outside the shell's citation provider a citation renders as its id; the word before it is what the page adds to its label
      for (const t of [es, en]) expect(t, v).not.toMatch(/CRR3 \[crr3\]/);
    }
    // the shell prints a citation by its label in the page's language: the Basel texts carry a Spanish label
    const label = (id: string) => CITATIONS.find((c) => c.id === id)?.label;
    expect(label('cre31')).toEqual({ en: 'Basel CRE31', es: 'Basilea CRE31' });
    expect(label('cre99')).toEqual({ en: 'Basel CRE99', es: 'Basilea CRE99' });
    // the rail's LGD hint, not in a capture, says the same
    expect(src('./instrument.tsx')).not.toMatch(/es: '[^']*senior/);
  });

  it('B2: the rail names its constant in words and the approaches table writes symbols with subscripts, RV in Spanish', () => {
    for (const v of SP) {
      for (const a of ['A1-idp', 'A2-iar', 'A3-spd', 'A4-slr'] as Case1[]) {
        for (const lang of LANGS) {
          const t = textOf(render(<CalibrationReadout sel={sel(v, a)} />, lang));
          expect(t, `${v} ${a} ${lang}`).not.toMatch(/c_(LR|PD)/);
          if (lang === 'es') expect(t, `${v} ${a}`).not.toMatch(/\bAR\b/);
        }
      }
      const en = render(<ApproachesView sel={sel(v)} />, 'en');
      const es = render(<ApproachesView sel={sel(v)} />, 'es');
      for (const m of [en, es]) {
        expect(textOf(m), v).not.toMatch(/c_(LR|PD)|\balpha\b|\bbeta\b|\bAR1\b/);
        expect(m, v).toContain('<i>c</i><sub>PD</sub>');
        expect(m, v).toMatch(/α \d/);
        expect(m, v).toMatch(/β \d/);
      }
      expect(en, v).toContain('<i>c</i><sub>LR</sub>');
      expect(es, v).toContain('<i>c</i><sub>RV</sub>');
      expect(es, v).not.toContain('<sub>LR</sub>');
    }
  });

  it('M2: the Default profile view shows the chi-square test over grades, the test F-RED-01 cites, for every approach', () => {
    for (const v of SP) {
      const s = sel(v);
      const chi = s.data.variant.tests.filter((t) => t.test_id === 'pd.chi2_grades');
      expect(chi.length, v).toBe(9);
      for (const lang of LANGS) {
        const table = tableOf(render(<DefaultProfileView sel={s} />, lang), 'default-profile');
        expect(heads(table), `${v} ${lang}`).toContain(lang === 'en' ? 'Chi-square over grades, p' : 'Chi-cuadrado sobre grados, p');
        const rows = bodyRows(table);
        expect(rows.length).toBe(9);
        const tableMarkup = table.match(/<tbody>[\s\S]*<\/tbody>/)![0];
        // each row has two lights: the default-profile test, then the chi-square over grades (the fourth column)
        const cells = [...tableMarkup.matchAll(/<tr[^>]*>([\s\S]*?)<\/tr>/g)].map((r) => [...r[1].matchAll(/<td data-light="([^"]+)"/g)].map((x) => x[1])[1]);
        expect(cells, `${v} ${lang}`).toEqual(s.data.variant.model.map((m) => chi.find((t) => t.model_id === m.id)!.light));
      }
      const en = textOf(render(<DefaultProfileView sel={s} />, 'en'));
      expect(en).toContain('The chi-square test over grades (BCBS Working Paper 14)');
      const es = textOf(render(<DefaultProfileView sel={s} />, 'es'));
      expect(es).toContain('La prueba chi-cuadrado sobre grados (documento de trabajo 14 del BCBS)');
    }
  });

  it('M3 (R5 ruling 2): every tests row of C05 names its segment in words, in both languages', () => {
    for (const v of SP) {
      for (const lang of LANGS) {
        const dp = bodyRows(tableOf(render(<DefaultProfileView sel={sel(v)} />, lang), 'default-profile'));
        for (const r of dp) expect(r, `${v} ${lang} default profile`).toContain(SCOPE[lang]);
        const ap = tableOf(render(<ApproachesView sel={sel(v)} />, lang), 'approaches');
        expect(heads(ap).join(' | '), `${v} ${lang} approaches`).toContain(SCOPE[lang]);
        const jb = bodyRows(tableOf(render(<GradeTestsView sel={sel(v)} />, lang), 'jeffreys-by-grade'));
        expect(jb.at(-1), `${v} ${lang} by grade`).toMatch(lang === 'en' ? /^\s*Whole portfolio/ : /^\s*Toda la cartera/);
      }
    }
    for (const v of LDP) {
      for (const lang of LANGS) {
        const rows = bodyRows(tableOf(render(<LdpTestsView sel={sel(v)} />, lang), 'ldp-tests'));
        expect(rows.length).toBe(sel(v).data.variant.tests.length);
        for (const r of rows) expect(r, `${v} ${lang}`).toMatch(lang === 'en' ? /(whole portfolio|grade [ABC])/ : /(toda la cartera|grado [ABC])/);
      }
    }
  });

  it('N-m1 and n3: the Spanish write-up says "La prueba retrospectiva" and spaces its percents', () => {
    const es = textOf(render(<C05ContextView sel={sel('sp-2010')} />, 'es'));
    expect(es).not.toMatch(/\b(El|del) prueba\b/);
    expect(es).toContain('La prueba retrospectiva del artículo con datos de Moody');
    expect(es).toContain("La prueba retrospectiva con Moody's no se puede repetir");
    const prose = src('../../content/cases/C05.tsx').split('\n').filter((l) => /\bes[=:]/.test(l)).map((l) => l.slice(l.search(/\bes[=:]/))).join('\n');
    expect(prose).not.toMatch(/\d%/);
  });

  it('S1: the first equation of the Context is two displays, the PD curve and the likelihood ratio', () => {
    const c = src('../../content/cases/C05.tsx');
    expect(c).not.toContain(String.raw`\qquad \lambda(x) = \frac`);
    expect(c).toContain(String.raw`tex={String.raw` + '`' + String.raw`\lambda(x) = \frac{\Pr[X = x \mid N]}{\Pr[X = x \mid D]}` + '`}');
  });

  it('the variants table names the scope of its default-profile p-values', () => {
    for (const lang of LANGS) {
      const t = textOf(render(<C05VariantsView sel={sel('sp-2010')} onPick={() => undefined} />, lang));
      // the view loads every variant asynchronously; on the server it renders its pending state, so the note is read from the source
      expect(t.length).toBeGreaterThan(0);
    }
    const c = src('./C05Common.tsx');
    expect(c).toContain('The default-profile p-value of each case 1 approach, over the whole portfolio');
    expect(c).toContain('El valor p del perfil de cada enfoque del caso 1, sobre toda la cartera');
  });

  it('R3 minors m1, m12 and m13: each variants table carries its own badge; the rail says "propia"; a grade name keeps one line', () => {
    const c = src('./C05Common.tsx');
    expect(c).toMatch(/title=\{\{ en: 'The calibration variants'[^\n]*provenance=\{spProv\}/);
    expect(c).toMatch(/title=\{\{ en: 'The low-default variants'[^\n]*provenance=\{ldpProv\}/);
    const es = textOf(render(<CalibrationReadout sel={sel('sp-2010')} />, 'es'));
    expect(es).not.toContain('suma 1');
    const m = render(<GradeTestsView sel={sel('sp-2010')} />, 'en');
    const first = [...(tableOf(m, 'jeffreys-by-grade').match(/<tbody>[\s\S]*<\/tbody>/)?.[0] ?? '').matchAll(/<tr[^>]*>\s*<td([^>]*)>/g)].map((x) => x[1]);
    expect(first.length).toBe(18);
    for (const a of first) expect(a).toContain('white-space:nowrap');
  });
});
