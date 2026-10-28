// U16-F13e (fix round 6, the fifth capture review R5, batch c27), on the six committed pair documents in both languages: the Context
// names the state, never its postal code (B1, R5 ruling 6: "DE" is Delaware, and "Estado DE" reads as a preposition in Spanish); the
// Findings evidence card is a measured scroll box whose evidence table keeps its height, so the cue says what lies below its edge
// (M1, R4 ruling 8); a count of categories takes its plural; the licence status is not a second "Estado"; a field code breaks only
// at its underscores; and every tests table of C21 names the segment of every row (R5 ruling 2).
import { afterEach, describe, expect, it } from 'vitest';
import type { ModelsArtifact, VariantArtifact } from '../../lib/contract.types';
import { render, textOf } from '../c03/u16f2-kit';
import { setLang } from '../c03/u6-testkit';
import { committedDoc, fixtureData } from '../c14/testkit';
import { C21ContextView } from './C21Common';
import { FindingsEvidenceCard } from './FindingsEvidence';
import { RatesView, TestsView } from './RateViews';
import { defaultSel, type C21Sel } from './selection';

const PAIRS = ['pair-2018-19', 'pair-2019-20', 'pair-2020-21', 'pair-2021-22', 'pair-2022-23', 'pair-2023-24'] as const;
const models = committedDoc<ModelsArtifact>('C21', 'models-hmda-de-2018-2023');
const title = { en: 'Fair lending', es: 'Préstamos justos' };
const doc = (name: string) => committedDoc<VariantArtifact>('C21', name);
const selOf = (name: string): C21Sel => defaultSel(fixtureData('C21', doc(name), models, title)) as C21Sel;
const LANGS = ['en', 'es'] as const;

describe('U16-F13e C21', () => {
  afterEach(() => setLang('en'));

  it('c27 B1: the Context names the state Delaware, never its code DE', () => {
    for (const name of PAIRS) {
      for (const lang of LANGS) {
        const html = render(<C21ContextView sel={selOf(name)} />, lang);
        const scope = /data-table="c21-scope"[\s\S]*?<\/dl>/.exec(html)![0];
        expect(scope, `${name} ${lang}`).not.toMatch(/<dd>DE<\/dd>/);
        expect(textOf(scope), `${name} ${lang}`).toContain(lang === 'en' ? 'State Delaware' : 'Estado Delaware');
      }
    }
  });

  it('c27 M1: the evidence card is a measured scroll box and its table keeps its height inside it', () => {
    for (const name of PAIRS) {
      const html = render(<FindingsEvidenceCard variant={doc(name)} />, 'en');
      const stack = /<div class="ct-stack"[^>]*data-block="finding-evidence"[^>]*>/.exec(html)![0];
      expect(stack, name).toMatch(/data-scroll-box=""/);
      expect(html, name).toMatch(/<div class="ct-stack-table" style="flex:none">\s*<table class="caos-table ct-wrap-head" data-table="finding-evidence"/);
    }
  });

  it('c27 n1: a count of categories takes its plural', () => {
    for (const lang of LANGS) {
      const text = textOf(render(<RatesView sel={selOf('pair-2023-24')} />, lang));
      expect(text, lang).not.toMatch(/category\(ies\)|categoría\(s\)/);
      expect(text, lang).toMatch(lang === 'en' ? /\d+ categor(y|ies) kept out of the pairwise tests/ : /\d+ categorías? fuera de las pruebas por pares/);
    }
  });

  it('c27 n3: the licence status is "Estado de la licencia", not a second "Estado"', () => {
    const html = render(<C21ContextView sel={selOf('pair-2023-24')} />, 'es');
    const licence = /data-table="c21-licence"[\s\S]*?<\/dl>/.exec(html)![0];
    expect(licence).toContain('<dt>Estado de la licencia</dt>');
    const en = render(<C21ContextView sel={selOf('pair-2023-24')} />, 'en');
    expect(/data-table="c21-licence"[\s\S]*?<\/dl>/.exec(en)![0]).toContain('<dt>Licence status</dt>');
  });

  it('c27 n4: a field code of the Context breaks only at its underscores', () => {
    const html = render(<C21ContextView sel={selOf('pair-2023-24')} />, 'en');
    const codes = [...html.matchAll(/<code translate="no"( style="[^"]*")?>([^<]*(?:<wbr\/>[^<]*)*)<\/code>/g)].filter((m) => m[2].includes('_') || m[2].includes('<wbr/>'));
    expect(codes.length).toBeGreaterThan(3);
    for (const m of codes) {
      expect(m[1], m[2]).toContain('overflow-wrap:normal');
      expect(m[2], m[2]).toMatch(/_<wbr\/>/);
    }
  });

  it('ruling 2: every row of every C21 tests table names its segment', () => {
    for (const name of PAIRS) {
      for (const lang of LANGS) {
        for (const html of [render(<TestsView sel={selOf(name)} />, lang), render(<RatesView sel={selOf(name)} />, lang)]) {
          const rows = [...html.matchAll(/<tr data-test="[^"]+"[^>]*>([\s\S]*?)<\/tr>/g)];
          expect(rows.length, `${name} ${lang}`).toBeGreaterThan(0);
          for (const m of rows) expect(m[1], `${name} ${lang}`).toMatch(/class="ct-row-detail" data-segment="[^"]+">[^<]+</);
        }
      }
    }
  });
});
